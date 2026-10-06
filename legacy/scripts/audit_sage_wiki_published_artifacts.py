#!/usr/bin/env python3
# ruff: noqa: E501 -- immutable hashes and exact claim-boundary text are kept inline.
"""Audit Sage Wiki's exact committed benchmark artifacts without rerunning models.

The audit binds the source checkout, recomputes every stored aggregate from
per-question rows, checks the report annotations, and aligns LoCoMo and
LongMemEval rows to independently pinned datasets. It cannot reproduce the
missing retrieval payloads, compiled projects, provider responses, or binary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAGE_REPOSITORY = "https://github.com/xoai/sage-wiki"
SAGE_REVISION = "78b71575834750962d14265550a099ac64426d91"
SAGE_TREE = "f04621c7f2821bd70fa2da27f5736473d1662a42"
SAGE_TAG = "v0.2.9"
SAGE_ARCHIVE_SHA256 = "1f9c349efb2fac7a20b790b8e6dee66f03c773522e5cd36905c07b06cbfbcf44"
STATUS = "SAGE_WIKI_RELEASED_ARTIFACTS_AUDITED_BINARY_AND_RETRIEVAL_PROVENANCE_MISSING"
UNBOUND_BINARY = "sage-wiki dev (commit none, built unknown)"
LME_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
LME_SIZE = 277_383_467
LOCOMO_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
LOCOMO_SIZE = 2_805_274
GO_SUMMARY_SHA256 = "46dca2195c9e56b78a1735421bb865a026cb5fce7cd13d59ef5ed569d8039d65"
PYTEST_JUNIT_SHA256 = "2d40f5a1702e02c8948a3ba3c72df89a9a55b71e13dc51510f543faf15a0985b"
GO_TOOLCHAIN_ARCHIVE_SHA256 = "e7d0678e7861d22c375ce7f55713d4a783b9771a1a0fc5d0542aac64e02e491b"
GO_BINARY_SHA256 = "a1c83801d1756c3eca78366c6b585f2c21c20694fb1c7eb92c446a0580420412"

SOURCE_FILES = {
    ".github/workflows/ci.yml": "6270048d3b562566941fe590d28b71be2df398689919f556f1202346e70a1d79",
    "LICENSE": "a0488807e16c1976de2d2408e793af5cd5e889de35f7fa4a11086c1da4683615",
    "README.md": "df03ae72971e96bf427738dba769af4553422e4ae0a16dddd930d3942231a8e4",
    "eval/benchmarks/README.md": "cfa00d5b28bd2dc9514d3ab17d10fd12d4f8bb14a66d1eb2d9cca3f3aa1ac39a",
    "eval/benchmarks/REPORT.md": "41cbf3ad388ea1eb5e79e024a6f4561bbf2157cd8b87f3652915701ec8d6338e",
    "eval/benchmarks/beam/run.py": "a33afcac997af4ae92f2192b309e200e2cc6a4058fb04acc8e176171eb70ca74",
    "eval/benchmarks/common/metrics.py": "6393e7d0990b1b4cbf10b8845ecafc981c86a024f8edda020083a3e73b9befa3",
    "eval/benchmarks/common/sagewiki.py": "0bdb74bdbbb6318f1b21340d2b3f367c3ec8eba857350673b3354d128d07bdf6",
    "eval/benchmarks/locomo/run.py": "a8dc6e936d763473b433d3c69095e21d806a78d759dbf264d153a166a124d62b",
    "eval/benchmarks/longmemeval/run.py": "60b79f9ab797527db5df038c813edcd9c6e9730e918c35bd08620b7388026aad",
    "eval/benchmarks/report_check.py": "59b1c532933209a976eb4897af3307095305b18716735b28e7bbb7fbd0f60445",
    "go.mod": "77eec1ba68fd524840ba204d18e0ca9ffd6732b6dc185354e3abee85490170b0",
    "go.sum": "901785e4ef8bbded4be6b1d4ba11a22c7e59baee1c491c4a26d01d932cae9986",
}

ARTIFACTS = {
    "beam_full.json": ("c2b54f558dc43dcc6d4106383dc3556d72bc0226feab53405eeb36fee3655e34", 171_908, 60),
    "beam_gpt5.json": ("ce9ac0157de5569e29f86433501503d640595c9f885a3a7caa561d0192eb299d", 811_282, 60),
    "beam_smoke.json": ("7c485a02b63adcf6ecf19d9f2a2efd8f0f8a03bc14e7e9cb5f0d026460c4ef79", 5_396, 2),
    "locomo_full.json": ("f35b4fc0aba55ef8c7a7763937f8e1f4c9e95a338ee2ad2997cb8ed137d6d5af", 1_077_842, 1_540),
    "locomo_gpt5-150.json": ("a9052b90b056b55274851b4efbb034197c6914fbbcaca337a67c5022fc55f7cd", 235_935, 150),
    "locomo_parity.json": ("d005e27b36ed0c0fd87521c884226f4df243415361b9f9c5777a259687c256d2", 1_466_418, 1_540),
    "locomo_smoke.json": ("5800fedab30760d43363066c9ecab86ddcac33126845312623913a625d2a9080", 4_756, 5),
    "longmemeval_full.json": ("c9e758c301b16a23eece0b94bbb6c2ca7f67bbf73fe3a9407761f35264bcf94f", 23_534, 30),
    "longmemeval_gpt5.json": ("e78139d9381b8faf71dbb8397233c401d4ad86c3150fbe9c9c41b951f4dc5421", 51_367, 30),
    "longmemeval_smoke.json": ("cff8dbc70aa620daee63a99ff0139db5189d2cfc19df19f54ca18e5731ee1af9", 1_714, 1),
}

GO_PACKAGES = [
    "github.com/xoai/sage-wiki/cmd/sage-wiki",
    "github.com/xoai/sage-wiki/internal/ontology",
    "github.com/xoai/sage-wiki/internal/search",
    "github.com/xoai/sage-wiki/internal/storage",
    "github.com/xoai/sage-wiki/internal/storage/postgres",
    "github.com/xoai/sage-wiki/internal/wiki",
]
LOCOMO_GROUPS = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop"}
LME_TYPES = [
    "temporal-reasoning",
    "multi-session",
    "knowledge-update",
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
]
CHECK_RE = re.compile(r"<!--\s*check:(?P<stem>[\w-]+)\s+(?P<path>[\w.\-]+)\s*=\s*(?P<expected>-?[\d.]+)\s*-->")

DEFAULT_SOURCE = PROJECT_ROOT / "raw/baselines/sage-wiki"
DEFAULT_LME = PROJECT_ROOT / "data/benchmarks/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json"
DEFAULT_LOCOMO = PROJECT_ROOT / "data/results/gaama-natural/2026-08-14-doctor-v6/source/locomo10.json"
DEFAULT_RUN_ROOT = PROJECT_ROOT / "data/results/sage-wiki-artifact-audit/2026-08-17-local-cpu-v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, expected_type: type = dict) -> Any:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"expected regular JSON file: {path}")

    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON value in {path}: {value}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, expected_type):
        raise ValueError(f"unexpected JSON shape: {path}")
    return payload


def _git(source: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        check=False,
        capture_output=True,
        text=not binary,
    )
    if result.returncode:
        stderr = result.stderr if isinstance(result.stderr, str) else result.stderr.decode()
        raise ValueError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return result.stdout


def _normalize_repository(value: str) -> str:
    value = value.strip().removesuffix("/").removesuffix(".git")
    if value.startswith("git@github.com:"):
        return "https://github.com/" + value.removeprefix("git@github.com:")
    return value


def verify_source(source: Path) -> dict[str, Any]:
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Sage Wiki source must be a regular directory")
    for relative, expected in SOURCE_FILES.items():
        path = source / relative
        if not path.is_file() or path.is_symlink() or sha256_file(path) != expected:
            raise ValueError(f"Sage Wiki source file drifted: {relative}")
    identity = {
        "repository": _normalize_repository(str(_git(source, "remote", "get-url", "origin"))),
        "revision": str(_git(source, "rev-parse", "HEAD")).strip(),
        "tree": str(_git(source, "rev-parse", "HEAD^{tree}")).strip(),
        "tag": str(_git(source, "describe", "--tags", "--exact-match", "HEAD")).strip(),
    }
    if identity != {
        "repository": SAGE_REPOSITORY,
        "revision": SAGE_REVISION,
        "tree": SAGE_TREE,
        "tag": SAGE_TAG,
    }:
        raise ValueError("Sage Wiki source identity drifted")
    if str(_git(source, "status", "--porcelain", "--untracked-files=all")).strip():
        raise ValueError("Sage Wiki source checkout must be clean")
    archive = _git(source, "archive", "--format=tar", "HEAD", binary=True)
    assert isinstance(archive, bytes)
    if sha256_bytes(archive) != SAGE_ARCHIVE_SHA256:
        raise ValueError("Sage Wiki source archive drifted")
    return {**identity, "git_archive_tar_sha256": SAGE_ARCHIVE_SHA256, "files": SOURCE_FILES}


def _scored(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("status", "ok") != "infra_error"]


def _bucket(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(row.get("score", 0.0) >= 0.5 for row in rows)
    return {
        "total": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows) * 100 if rows else 0.0,
        "avg_score": statistics.mean(row.get("score", 0.0) for row in rows) * 100 if rows else 0.0,
    }


def aggregate(rows: list[dict[str, Any]], *, beam: bool) -> dict[str, Any]:
    scored = _scored(rows)
    overall = _bucket(scored)
    overall["infra_errors"] = len(rows) - len(scored)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        groups[str(row.get("group", "unknown"))].append(row)
    by_group = {group: _bucket(group_rows) for group, group_rows in sorted(groups.items())}
    if beam:
        for group, group_rows in groups.items():
            tau_rows = [row for row in group_rows if "tau_b" in row]
            if tau_rows:
                by_group[group]["tau_b_avg"] = statistics.mean(row["tau_b"] for row in tau_rows)
                by_group[group]["score_with_tau"] = statistics.mean(
                    (row.get("score", 0.0) + (row["tau_b"] + 1.0) / 2.0) / 2.0
                    for row in tau_rows
                ) * 100
    return {"overall": overall, "by_group": by_group}


def latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(
        row["search_latency_ms"]
        for row in _scored(rows)
        if isinstance(row.get("search_latency_ms"), (int, float))
        and not isinstance(row.get("search_latency_ms"), bool)
    )
    if not values:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "avg_ms": 0.0}

    def percentile(p: float) -> float:
        if len(values) == 1:
            return values[0]
        index = p / 100 * (len(values) - 1)
        low, high = int(index), min(int(index) + 1, len(values) - 1)
        fraction = index - low
        return values[low] * (1 - fraction) + values[high] * fraction

    return {
        "count": len(values),
        "p50_ms": percentile(50),
        "p95_ms": percentile(95),
        "avg_ms": statistics.mean(values),
    }


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    return left == right


def _stratified_lme(dataset: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset:
        if row["question_type"] in LME_TYPES:
            groups[row["question_type"]].append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: row["question_id"])
    rng = random.Random(42)
    sample: list[dict[str, Any]] = []
    for group in sorted(groups):
        sample.extend(rng.sample(groups[group], min(5, len(groups[group]))))
    return sorted(sample, key=lambda row: row["question_id"])


def _stratified_locomo(dataset: list[dict[str, Any]], n: int = 150) -> list[str]:
    pool: dict[int, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    for conv_idx, conversation in enumerate(dataset):
        for question_idx, row in enumerate(conversation.get("qa", [])):
            if row.get("category") in LOCOMO_GROUPS:
                pool[row["category"]].append((conv_idx, question_idx, row))
    total = sum(len(rows) for rows in pool.values())
    exact = {category: len(rows) * n / total for category, rows in pool.items()}
    allocation = {category: int(value) for category, value in exact.items()}
    for category in sorted(pool, key=lambda item: (-(exact[item] - allocation[item]), item)):
        if sum(allocation.values()) >= n:
            break
        allocation[category] += 1
    rng = random.Random(42)
    picked: list[tuple[int, int, dict[str, Any]]] = []
    for category in sorted(pool):
        by_conversation: dict[int, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
        for item in pool[category]:
            by_conversation[item[0]].append(item)
        for rows in by_conversation.values():
            rng.shuffle(rows)
        order = sorted(by_conversation)
        rng.shuffle(order)
        taken = index = 0
        while taken < allocation[category]:
            for conv_idx in order:
                if taken >= allocation[category]:
                    break
                rows = by_conversation[conv_idx]
                if index < len(rows):
                    picked.append(rows[index])
                    taken += 1
            index += 1
    return [f"conv{conv_idx}_q{question_idx}" for conv_idx, question_idx, _ in sorted(picked)]


def verify_datasets(lme_path: Path, locomo_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    for path, expected_sha, expected_size in [
        (lme_path, LME_SHA256, LME_SIZE),
        (locomo_path, LOCOMO_SHA256, LOCOMO_SIZE),
    ]:
        if path.stat().st_size != expected_size or sha256_file(path) != expected_sha:
            raise ValueError(f"dataset receipt drifted: {path}")
    lme = load_json(lme_path, list)
    locomo = load_json(locomo_path, list)
    if len(lme) != 500 or len(locomo) != 10:
        raise ValueError("dataset row count drifted")
    return lme, locomo, {
        "longmemeval_s": {"sha256": LME_SHA256, "size": LME_SIZE, "rows": 500},
        "locomo10": {"sha256": LOCOMO_SHA256, "size": LOCOMO_SIZE, "conversations": 10},
    }


def verify_tests(run_root: Path) -> dict[str, Any]:
    junit_path = run_root / "upstream-eval-tests.junit.xml"
    go_path = run_root / "upstream-go-focused-tests.json"
    if sha256_file(junit_path) != PYTEST_JUNIT_SHA256 or sha256_file(go_path) != GO_SUMMARY_SHA256:
        raise ValueError("upstream test receipt drifted")
    root = ET.parse(junit_path).getroot()
    suites = list(root) if root.tag == "testsuites" else [root]
    pytest_counts = {
        "tests": sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        "failures": sum(int(suite.attrib.get("failures", 0)) for suite in suites),
        "errors": sum(int(suite.attrib.get("errors", 0)) for suite in suites),
        "skipped": sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
    }
    if pytest_counts != {"tests": 158, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("upstream Python test result drifted")
    go = load_json(go_path)
    expected_go = {
        "schema_version": 1,
        "go_version": "go1.26.6",
        "platform": "darwin-arm64",
        "cgo_enabled": False,
        "passed_tests": 359,
        "skipped_tests": 18,
        "failed_tests": 0,
        "passed_packages": GO_PACKAGES,
        "failed_packages": [],
    }
    if go != expected_go:
        raise ValueError("upstream focused Go test result drifted")
    return {
        "python": {**pytest_counts, "junit_sha256": PYTEST_JUNIT_SHA256},
        "go": {**go, "summary_sha256": GO_SUMMARY_SHA256},
    }


def _lookup(payload: dict[str, Any], dotted: str) -> Any:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"report annotation path is missing: {dotted}")
        current = current[part]
    return current


def verify_report_annotations(source: Path, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    report = (source / "eval/benchmarks/REPORT.md").read_text(encoding="utf-8")
    checks = list(CHECK_RE.finditer(report))
    if len(checks) != 45:
        raise ValueError("Sage Wiki report annotation count drifted")
    for check in checks:
        stem = check.group("stem")
        payload = artifacts.get(f"{stem}.json")
        if payload is None:
            raise ValueError(f"report annotation references unknown artifact: {stem}")
        actual = _lookup(payload, check.group("path"))
        if round(float(actual), 1) != round(float(check.group("expected")), 1):
            raise ValueError(f"report annotation drifted: {stem} {check.group('path')}")
    return {"checks": 45, "failures": 0, "report_sha256": SOURCE_FILES["eval/benchmarks/REPORT.md"]}


def _align_rows(
    name: str,
    payload: dict[str, Any],
    lme: list[dict[str, Any]],
    locomo: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = payload["per_question"]
    benchmark = payload["metadata"]["benchmark"]
    if benchmark == "longmemeval":
        expected = {row["question_id"]: row for row in lme}
        sample_ids = [row["question_id"] for row in _stratified_lme(lme)]
        expected_ids = sample_ids[:1] if name == "longmemeval_smoke.json" else sample_ids
        for row in rows:
            source_row = expected.get(row.get("question_id"))
            if source_row is None or {
                "question": row.get("question"),
                "ground_truth": row.get("ground_truth"),
                "group": row.get("group"),
                "question_date": row.get("question_date"),
                "is_abstention": row.get("is_abstention"),
            } != {
                "question": source_row["question"],
                "ground_truth": str(source_row["answer"]),
                "group": source_row["question_type"],
                "question_date": source_row.get("question_date", ""),
                "is_abstention": source_row["question_id"].endswith("_abs"),
            }:
                raise ValueError(f"LongMemEval dataset alignment drifted: {name}")
        if sorted(row["question_id"] for row in rows) != sorted(expected_ids):
            raise ValueError(f"LongMemEval sample roster drifted: {name}")
        return {"dataset": "longmemeval_s", "matched_rows": len(rows), "sample_policy": "seed-42-stratified-5-per-type"}
    if benchmark == "locomo":
        expected: dict[str, dict[str, Any]] = {}
        all_ids: list[str] = []
        for conv_idx, conversation in enumerate(locomo):
            for question_idx, question in enumerate(conversation.get("qa", [])):
                if question.get("category") not in LOCOMO_GROUPS:
                    continue
                qid = f"conv{conv_idx}_q{question_idx}"
                all_ids.append(qid)
                expected[qid] = {
                    "conversation_idx": conv_idx,
                    "category": question["category"],
                    "group": LOCOMO_GROUPS[question["category"]],
                    "question": question["question"],
                    "ground_truth": str(question["answer"]),
                }
        if name == "locomo_gpt5-150.json":
            expected_ids = _stratified_locomo(locomo)
            policy = "seed-42-proportional-category-round-robin-conversation"
        elif name == "locomo_smoke.json":
            expected_ids = [qid for qid in all_ids if qid.startswith("conv0_")][:5]
            policy = "conversation-0-first-5"
        else:
            expected_ids = all_ids
            policy = "all-category-1-through-4"
        for row in rows:
            if expected.get(row.get("question_id")) != {
                key: row.get(key)
                for key in ["conversation_idx", "category", "group", "question", "ground_truth"]
            }:
                raise ValueError(f"LoCoMo dataset alignment drifted: {name}")
        if set(row["question_id"] for row in rows) != set(expected_ids) or len(rows) != len(expected_ids):
            raise ValueError(f"LoCoMo sample roster drifted: {name}")
        return {"dataset": "locomo10", "matched_rows": len(rows), "sample_policy": policy}
    return {"dataset": "beam-unpinned-mutable-huggingface-loader", "matched_rows": 0, "sample_policy": "not-independently-source-bound"}


def audit_artifact(
    name: str,
    path: Path,
    lme: list[dict[str, Any]],
    locomo: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_sha, expected_size, expected_rows = ARTIFACTS[name]
    if path.stat().st_size != expected_size or sha256_file(path) != expected_sha:
        raise ValueError(f"published artifact receipt drifted: {name}")
    payload = load_json(path)
    if set(payload) not in [
        {"metadata", "metrics", "latency", "per_question"},
        {"metadata", "metrics", "metrics_by_cutoff", "latency", "per_question"},
    ]:
        raise ValueError(f"published artifact schema drifted: {name}")
    rows = payload["per_question"]
    if not isinstance(rows, list) or len(rows) != expected_rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"published artifact row roster drifted: {name}")
    if len({row.get("question_id") for row in rows}) != len(rows):
        raise ValueError(f"duplicate question IDs in published artifact: {name}")
    metadata = payload["metadata"]
    if metadata.get("binary_version") != UNBOUND_BINARY:
        raise ValueError(f"unexpected binary provenance string: {name}")
    benchmark = metadata.get("benchmark")
    recomputed = aggregate(rows, beam=benchmark == "beam")
    if not _equal(recomputed, payload["metrics"]) or not _equal(latency(rows), payload["latency"]):
        raise ValueError(f"stored aggregate does not recompute: {name}")
    recomputed_cutoffs: dict[str, Any] = {}
    for label in sorted(payload.get("metrics_by_cutoff", {})):
        views = [
            {
                **row,
                "score": row.get("cutoff_results", {}).get(label, {}).get("score", row.get("score", 0.0)),
            }
            for row in rows
        ]
        recomputed_cutoffs[label] = aggregate(views, beam=benchmark == "beam")
    if not _equal(recomputed_cutoffs, payload.get("metrics_by_cutoff", {})):
        raise ValueError(f"stored cutoff aggregate does not recompute: {name}")
    alignment = _align_rows(name, payload, lme, locomo)
    retrieval_payload_rows = sum("retrieval" in row for row in rows)
    if retrieval_payload_rows:
        raise ValueError(f"unexpected retained retrieval payload: {name}")
    statuses = dict(sorted(Counter(row.get("status", "ok") for row in rows).items()))
    retrieved_counts = sorted({row.get("retrieved_count") for row in rows})
    projection = {
        "name": name,
        "sha256": expected_sha,
        "size": expected_size,
        "benchmark": benchmark,
        "binary_version": metadata["binary_version"],
        "models": metadata.get("models"),
        "scope": metadata.get("scope"),
        "rows": len(rows),
        "statuses": statuses,
        "metrics": payload["metrics"],
        "metrics_by_cutoff": payload.get("metrics_by_cutoff", {}),
        "latency": payload["latency"],
        "retrieval_payload_rows": retrieval_payload_rows,
        "reported_retrieved_counts": retrieved_counts,
        "alignment": alignment,
        "roster_sha256": sha256_bytes(canonical(sorted(row["question_id"] for row in rows))),
        "answer_and_judgment_sha256": sha256_bytes(
            canonical(
                [
                    {
                        key: row.get(key)
                        for key in [
                            "question_id",
                            "generated_answer",
                            "judgment",
                            "judge_reason",
                            "nugget_scores",
                            "score",
                            "cutoff_results",
                            "status",
                            "error",
                        ]
                        if key in row
                    }
                    for row in sorted(rows, key=lambda item: item["question_id"])
                ]
            )
        ),
    }
    diagnostic = {
        "name": name,
        "stored_aggregate_recomputed": True,
        "stored_cutoff_aggregates_recomputed": True,
        "latency_recomputed": True,
        "dataset_alignment": alignment,
        "retrieval_payload_retained": False,
        "binary_bound_to_revision": False,
        "provider_snapshot_bound": False,
        "raw_provider_receipts_retained": False,
    }
    return payload, {"projection": projection, "diagnostic": diagnostic}


def audit_sage_wiki(
    *,
    source: Path,
    lme_path: Path,
    locomo_path: Path,
    run_root: Path,
    receipt_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_receipt = verify_source(source)
    lme, locomo, datasets = verify_datasets(lme_path, locomo_path)
    tests = verify_tests(receipt_root or run_root)
    results_dir = source / "eval/benchmarks/results"
    payloads: dict[str, dict[str, Any]] = {}
    artifact_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for name in sorted(ARTIFACTS):
        payload, audited = audit_artifact(name, results_dir / name, lme, locomo)
        payloads[name] = payload
        artifact_rows.append(audited["projection"])
        diagnostics.append(audited["diagnostic"])
    annotations = verify_report_annotations(source, payloads)
    projection = {
        "_meta": {
            "schema_version": 1,
            "source_id": "sage-wiki",
            "revision": SAGE_REVISION,
            "status": STATUS,
        },
        "artifacts": artifact_rows,
        "datasets": datasets,
        "report_annotations": annotations,
        "tests": tests,
    }
    projection_sha = sha256_bytes(canonical(projection))
    report: dict[str, Any] = {
        "schema_version": 1,
        "source_id": "sage-wiki",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "source": source_receipt,
        "runtime": {
            "platform": "darwin-arm64",
            "go_version": "go1.26.6",
            "go_toolchain_module_zip_sha256": GO_TOOLCHAIN_ARCHIVE_SHA256,
            "go_binary_sha256": GO_BINARY_SHA256,
            "external_api_calls": 0,
            "llm_calls": 0,
            "gpus": 0,
        },
        "semantic_projection_sha256": projection_sha,
        "artifact_count": len(artifact_rows),
        "artifact_diagnostics": diagnostics,
        "claim_boundary": {
            "stored_aggregates_recomputed": True,
            "report_annotations_verified": 45,
            "longmemeval_dataset_rows_aligned": 61,
            "locomo_artifact_rows_aligned": 3_235,
            "beam_dataset_independently_pinned": False,
            "binary_bound_to_source_revision": False,
            "retrieval_ids_or_text_retained": False,
            "compiled_projects_or_databases_retained": False,
            "provider_model_snapshots_bound": False,
            "raw_provider_responses_or_request_ids_retained": False,
            "independent_rejudge_completed": False,
            "matched_flat_vs_graph_arm_present": False,
            "memory_or_graph_mechanism_effect_established": False,
        },
        "known_artifact_boundaries": {
            "locomo_full_stitched_usage_metadata": True,
            "locomo_full_rows": 1_540,
            "locomo_full_answerer_calls_reported": 152,
            "locomo_parity_scored_rows": 529,
            "locomo_parity_infra_errors": 1_011,
            "multi_cutoff_artifacts_with_zero_retrieved_count": [
                "beam_gpt5.json",
                "locomo_gpt5-150.json",
                "locomo_parity.json",
                "longmemeval_gpt5.json",
            ],
        },
        "next_gate": "Run an exact-source common-construction full-task flat versus lexical/vector versus graph comparison at matched actor, top-k, injected bytes, calls, and judge while retaining retrieval IDs/text and immutable binary, image, SBOM, dataset, and provider receipts.",
    }
    report["report_sha256"] = sha256_bytes(canonical(report))
    return report, projection


def write_outputs(report: dict[str, Any], projection: dict[str, Any], run_root: Path) -> None:
    output = run_root / "audit"
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "projection.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--longmemeval", type=Path, default=DEFAULT_LME)
    parser.add_argument("--locomo", type=Path, default=DEFAULT_LOCOMO)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--receipt-root", type=Path)
    args = parser.parse_args()
    report, projection = audit_sage_wiki(
        source=args.source,
        lme_path=args.longmemeval,
        locomo_path=args.locomo,
        run_root=args.run_root,
        receipt_root=args.receipt_root,
    )
    write_outputs(report, projection, args.run_root)
    print(f"{STATUS}: {report['semantic_projection_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
