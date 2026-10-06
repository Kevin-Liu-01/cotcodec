#!/usr/bin/env python3
# ruff: noqa: E501 -- immutable hashes and exact claim-boundary text are kept inline.
"""Audit two exact-source GBrain BrainBench runs and emit a stable projection.

This reproduces GBrain's deterministic cross-harness conformance gate. It does
not add the matched pull-retrieval arm required by the CoTCodec portfolio and
does not establish memory-quality, model-quality, or actor-admission claims.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GBRAIN_REPOSITORY = "https://github.com/garrytan/gbrain"
GBRAIN_REVISION = "d941e9f918236c33e10e42d8a4223f36789b02c9"
GBRAIN_TREE = "4d7960cc1d88c40e0642204dfb144fd988c02208"
GBRAIN_ARCHIVE_SHA256 = "d83320b8a155f26d3b707e23fae5ba6f4245cc6c284766b382ba011521b82698"
BUN_VERSION = "1.3.13"
BUN_ARCHIVE_SHA256 = "5467e3f65dba526b9fea98f0cce04efafc0c63e169733ec27b876a3ad32da190"
BUN_BINARY_SHA256 = "fc0b4cae13a911098f0c61d13b7d9fd6b640bdb9f6b6a0b78bdb9d778c12bc3f"
FIXTURES_SHA256 = "76f201590dd3ad7a929e2e12efc9bf1406627b10ef4edbcfe7caf379aafd4090"
STATUS = "GBRAIN_BRAINBENCH_CONFORMANCE_PASS_PULL_COMPARISON_MISSING"
SOURCE_FILES = {
    ".github/workflows/test.yml": "fde39b91333187214ccb09c86c1ca89e4cbbf37905174b5a9b9d5c2f8e26a493",
    "LICENSE": "e56fbb5b3d95756f3fa1cfefa24732ec79f18ece1ad08a4e79e00df57e8b198c",
    "README.md": "73005ad3c54f70e1e5b42f3921d6d82a0b078053cdd9a9ca746da6d43c78b3a2",
    "bun.lock": "398e282d37f78c4e40a8be050b7c9e8858c35875310f39ec30a74fd8d557f9c2",
    "docs/eval/BRAINBENCH.md": "b22036d99e0bba3174d4cb1375daf9385d5024d0ee0f27f83bb43d59af9c48e4",
    "evals/brainbench/README.md": "1a6663c6a3ff56db2d2ae81960b877aeab8aeda6b4bdabe4b48f6f9cd9070a9f",
    "evals/brainbench/_ledger.json": "79cca16cbafc52c81fbf6f1d4b07a921540f034cc4feb3fb7b859480f37b92b5",
    "evals/brainbench/baselines/main.json": "6566285f6a3f66b87db5b046ed2f8f14fbf806162b65db7e38d3d979f5f9774c",
    "evals/brainbench/generator/gen.ts": "7db92d1011d874bc642dcc856d2efda4cd9db2111676138e0780e36c8cfe5947",
    "package.json": "30a1e103ae53c41be2713a08b6589d69fd8e86f826d1911468baa300aa5aa2f0",
    "scripts/ci-brainbench-gate.sh": "a60a9ef3f7ed81a290308aee253fe37549d68b11786babd354ede113e82f8447",
    "src/commands/eval-brainbench.ts": "230e26a78283106bfde9da9a7d64181a888a93c7e5b9daadb097a0cd2327963f",
    "src/eval/brainbench/adapters/claude-code.ts": "a2a2acee70953202f64cb782e450929b952c027658446cfe19bef4ed69a2d3d5",
    "src/eval/brainbench/adapters/codex.ts": "fdb76a5011d7b90e43a98916b2854509fb478b594427c11d5170f02006ff5265",
    "src/eval/brainbench/adapters/openclaw.ts": "03b50667b42acff1e81f8ce358c236b21127e867e1d6d31edf1d11316b67fc60",
    "src/eval/brainbench/adapters/shared.ts": "e1ad549640841721e39e62580e900ec692711c35f45a82dfa01c1febf6f24168",
    "src/eval/brainbench/fixtures.ts": "b4c397e0193197b23fae446fa516427de76a73dc7ae9eb782212a83433496fad",
    "src/eval/brainbench/harness.ts": "56420f3b24f1d9db0b6bb4feffe7b4920a4ebfa1819fa7a2302b025195dc3f80",
    "src/eval/brainbench/metrics/continuity.ts": "15f4205299ce87746528aa1147cb1bcd6e2c715671b6efeea0260c021b0ca50e",
    "src/eval/brainbench/metrics/know-to-ask.ts": "52d17db3b60c8de656e4d9e0d02c4b5f46284d86ee8e6a19112e0054b1b4637d",
    "src/eval/brainbench/metrics/push.ts": "b3f687e401b967df0427c0f6e4488984144c7f2858650c58641686ae9f23d409",
    "src/eval/brainbench/metrics/write-back.ts": "88babba38a24657d329209128e26be924f7371d11cea82965a07e988f0676f72",
    "src/eval/brainbench/scoreboard.ts": "7b31e7111f33ab2428f6799d2f13c9136b98c0164d74bf759a463cee3a114574",
    "src/eval/brainbench/seed.ts": "d09868991e35020f8f883006fe043d4003e91e74ba0c84080e780debfb28d4ed",
    "src/eval/brainbench/types.ts": "6676be24bb055e17b33b6fdf9443c2050e07f01ed2e0c9ee63f503060b4b9705",
}
EXPECTED_CELLS = {
    "claude-code/continuity": (
        "contract",
        12,
        0,
        {"avg_injected_tokens": 75.3333, "continuity_rate": 1, "source_isolation_violations": 0},
    ),
    "claude-code/know-to-ask": (
        "contract",
        146,
        11,
        {
            "avg_injected_tokens": 30.9247,
            "false_fire_rate": 0.0233,
            "know_to_ask_failure_rate": 0.15,
            "source_isolation_violations": 0,
        },
    ),
    "claude-code/push": (
        "contract",
        94,
        32,
        {
            "avg_injected_tokens": 38.8077,
            "push_precision": 1,
            "push_recall": 0.6596,
            "source_isolation_violations": 0,
        },
    ),
    "claude-code/write-back": (
        "contract",
        58,
        0,
        {"provenance_accuracy": 1, "write_back_fidelity": 1},
    ),
    "codex/continuity": (
        "contract",
        12,
        0,
        {"avg_injected_tokens": 150.9167, "continuity_rate": 1, "source_isolation_violations": 0},
    ),
    "codex/know-to-ask": (
        "contract",
        146,
        9,
        {
            "avg_injected_tokens": 40.7123,
            "false_fire_rate": 0,
            "know_to_ask_failure_rate": 0.15,
            "source_isolation_violations": 0,
        },
    ),
    "codex/push": (
        "contract",
        94,
        52,
        {
            "avg_injected_tokens": 48.5865,
            "push_precision": 1,
            "push_recall": 0.4468,
            "source_isolation_violations": 0,
        },
    ),
    "codex/write-back": ("contract", 58, 0, {"provenance_accuracy": 1, "write_back_fidelity": 1}),
    "openclaw/continuity": (
        "production",
        12,
        0,
        {"avg_injected_tokens": 75.3333, "continuity_rate": 1, "source_isolation_violations": 0},
    ),
    "openclaw/know-to-ask": (
        "production",
        146,
        9,
        {
            "avg_injected_tokens": 33.7945,
            "false_fire_rate": 0,
            "know_to_ask_failure_rate": 0.15,
            "source_isolation_violations": 0,
        },
    ),
    "openclaw/push": (
        "production",
        94,
        18,
        {
            "avg_injected_tokens": 44.1346,
            "push_precision": 1,
            "push_recall": 0.8085,
            "source_isolation_violations": 0,
        },
    ),
    "openclaw/write-back": (
        "production",
        58,
        0,
        {"provenance_accuracy": 1, "write_back_fidelity": 1},
    ),
}
EXPECTED_TURN_COUNTS = {"continuity": 36, "know-to-ask": 438, "push": 312}
DEFAULT_SOURCE = PROJECT_ROOT / "raw/baselines/gbrain"
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "data/runtimes/bun-v1.3.13"
DEFAULT_RUN_ROOT = PROJECT_ROOT / "data/results/gbrain-brainbench/2026-08-17-local-cpu-v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"expected regular JSON file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git(source: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        check=False,
        capture_output=True,
        text=not binary,
    )
    if result.returncode:
        error = result.stderr if isinstance(result.stderr, str) else result.stderr.decode()
        raise ValueError(f"git {' '.join(args)} failed: {error.strip()}")
    return result.stdout


def _normalize_repository(value: str) -> str:
    value = value.strip().removesuffix("/").removesuffix(".git")
    if value.startswith("git@github.com:"):
        return "https://github.com/" + value.removeprefix("git@github.com:")
    return value


def verify_source(source: Path) -> dict[str, Any]:
    if not source.is_dir() or source.is_symlink():
        raise ValueError("GBrain source must be a regular directory")
    for relative, expected in SOURCE_FILES.items():
        path = source / relative
        if not path.is_file() or path.is_symlink() or sha256_file(path) != expected:
            raise ValueError(f"GBrain source file drifted: {relative}")
    identity = {
        "repository": _normalize_repository(str(_git(source, "remote", "get-url", "origin"))),
        "revision": str(_git(source, "rev-parse", "HEAD")).strip(),
        "tree": str(_git(source, "rev-parse", "HEAD^{tree}")).strip(),
    }
    if identity != {
        "repository": GBRAIN_REPOSITORY,
        "revision": GBRAIN_REVISION,
        "tree": GBRAIN_TREE,
    }:
        raise ValueError("GBrain source identity drifted")
    if str(_git(source, "status", "--porcelain", "--untracked-files=all")).strip():
        raise ValueError("GBrain source checkout must be clean")
    archive = _git(source, "archive", "--format=tar", "HEAD", binary=True)
    assert isinstance(archive, bytes)
    if sha256_bytes(archive) != GBRAIN_ARCHIVE_SHA256:
        raise ValueError("GBrain git archive drifted")
    return {**identity, "git_archive_tar_sha256": GBRAIN_ARCHIVE_SHA256, "files": SOURCE_FILES}


def verify_runtime(runtime_root: Path) -> dict[str, Any]:
    archive = runtime_root / "bun-darwin-aarch64.zip"
    binary = runtime_root / "bun-darwin-aarch64/bun"
    if (
        not archive.is_file()
        or archive.is_symlink()
        or sha256_file(archive) != BUN_ARCHIVE_SHA256
        or not binary.is_file()
        or binary.is_symlink()
        or sha256_file(binary) != BUN_BINARY_SHA256
    ):
        raise ValueError("pinned Bun runtime drifted")
    result = subprocess.run([str(binary), "--version"], check=False, capture_output=True, text=True)
    if result.returncode or result.stdout.strip() != BUN_VERSION:
        raise ValueError("pinned Bun version drifted")
    return {
        "platform": "darwin-arm64",
        "version": BUN_VERSION,
        "release_archive_sha256": BUN_ARCHIVE_SHA256,
        "binary_sha256": BUN_BINARY_SHA256,
    }


def normalize_result(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"_meta", "cells", "compare", "receipt", "seed_failures", "turn_rows"}:
        raise ValueError("BrainBench result top-level schema drifted")
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict) or {
        key: receipt.get(key)
        for key in (
            "result_schema_version",
            "fixtures_hash",
            "harness_sha",
            "seed",
            "include_holdout",
            "llm",
        )
    } != {
        "result_schema_version": 1,
        "fixtures_hash": FIXTURES_SHA256,
        "harness_sha": GBRAIN_REVISION,
        "seed": 42,
        "include_holdout": False,
        "llm": False,
    }:
        raise ValueError("BrainBench run receipt drifted")
    args = receipt.get("cmd_args")
    if (
        not isinstance(args, list)
        or len(args) != 4
        or args[:3] != ["--compare", "evals/brainbench/baselines/main.json", "--out"]
        or not isinstance(args[3], str)
        or not args[3].endswith("/brainbench.json")
    ):
        raise ValueError("BrainBench invocation receipt drifted")
    if (
        payload.get("compare")
        != {
            "verdict": "pass",
            "mode": "same-hash",
            "breaches": [],
            "notes": [],
        }
        or payload.get("seed_failures") != []
    ):
        raise ValueError("BrainBench same-hash gate did not pass cleanly")
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 12:
        raise ValueError("BrainBench cell roster drifted")
    observed: dict[str, tuple[str, int, int, dict[str, Any]]] = {}
    for cell in cells:
        if not isinstance(cell, dict) or not isinstance(cell.get("fixtures"), list):
            raise ValueError("BrainBench cell is malformed")
        key = f"{cell.get('harness')}/{cell.get('suite')}"
        observed[key] = (
            cell.get("seam"),
            cell.get("gold_total"),
            cell.get("gold_failed"),
            cell.get("metrics"),
        )
    if observed != EXPECTED_CELLS:
        raise ValueError("BrainBench cell metrics drifted")
    rows = payload.get("turn_rows")
    if not isinstance(rows, list) or len(rows) != 786:
        raise ValueError("BrainBench turn-row roster drifted")
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "cross_source_slugs",
            "fixture_id",
            "gold",
            "harness",
            "injected_slugs",
            "injected_tokens",
            "latency_ms",
            "suite",
            "turn_id",
        }:
            raise ValueError("BrainBench turn-row schema drifted")
        latency = row["latency_ms"]
        if (
            row["cross_source_slugs"] != []
            or not isinstance(latency, (int, float))
            or isinstance(latency, bool)
            or not math.isfinite(latency)
            or latency < 0
        ):
            raise ValueError("BrainBench turn-row safety or latency receipt drifted")
        counts[row["suite"]] = counts.get(row["suite"], 0) + 1
    if counts != EXPECTED_TURN_COUNTS:
        raise ValueError("BrainBench turn-row suite counts drifted")
    projection = copy.deepcopy(payload)
    projection.pop("receipt")
    for row in projection["turn_rows"]:
        row.pop("latency_ms")
    return projection


def verify_junit(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("focused upstream JUnit artifact is missing")
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("focused upstream JUnit artifact is invalid") from exc
    expected = {"tests": "146", "assertions": "725", "failures": "0", "skipped": "0"}
    if root.tag != "testsuites" or any(root.get(key) != value for key, value in expected.items()):
        raise ValueError("focused upstream test result drifted")
    suites = {node.get("file") for node in root.findall("./testsuite")}
    if len(suites) != 12:
        raise ValueError("focused upstream test file roster drifted")
    return {
        **{key: int(value) for key, value in expected.items()},
        "file_count": 12,
        "sha256": sha256_file(path),
    }


def audit_gbrain(
    *, source: Path, runtime_root: Path, run_paths: list[Path], junit_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(run_paths) != 2:
        raise ValueError("GBrain audit requires exactly two runs")
    source_receipt = verify_source(source)
    runtime_receipt = verify_runtime(runtime_root)
    projections: list[dict[str, Any]] = []
    run_receipts: list[dict[str, Any]] = []
    for path in run_paths:
        payload = load_object(path)
        projection = normalize_result(payload)
        projections.append(projection)
        run_receipts.append({"sha256": sha256_file(path), "size": path.stat().st_size})
    if canonical(projections[0]) != canonical(projections[1]):
        raise ValueError("GBrain semantic repetitions differ")
    projection = projections[0]
    semantic_sha = sha256_bytes(canonical(projection))
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "not-granted-matched-pull-arm-missing",
        "source": source_receipt,
        "runtime": runtime_receipt,
        "corpus": {
            "fixtures_sha256": FIXTURES_SHA256,
            "generated_fixtures": 135,
            "holdout_fixtures": 23,
            "gate_fixture_executions": 106,
            "gold_turns_in_generated_corpus": 241,
            "turn_rows": 786,
        },
        "focused_upstream_tests": verify_junit(junit_path),
        "runs": run_receipts,
        "semantic_projection_sha256": semantic_sha,
        "semantic_repetitions_identical": True,
        "latency_excluded_from_semantic_projection": True,
        "cell_summary": {
            key: {"seam": seam, "gold_total": total, "gold_failed": failed, "metrics": metrics}
            for key, (seam, total, failed, metrics) in EXPECTED_CELLS.items()
        },
        "claim_boundary": {
            "production_seams_reproduced": ["openclaw"],
            "contract_only_seams_reproduced": ["claude-code", "codex"],
            "matched_pull_retrieval_arm_present": False,
            "live_agent_or_model_calls": False,
            "llm_extraction_evaluated": False,
            "memory_quality_evaluated": False,
            "h100_actor_admission": False,
        },
        "limitations": [
            "Only the OpenClaw row exercises a shipped production injection seam.",
            "Claude Code and Codex rows are GBrain-owned contract adapters, not third-party production behavior.",
            "BrainBench has no matched pull-retrieval arm, so it cannot answer the registered push-versus-pull question.",
            "The deterministic corpus uses template-synthesized fictional entities and excludes holdout fixtures in gate mode.",
            "No live model, embedding provider, LLM extraction, answer quality, or external benchmark was evaluated.",
            "Per-turn latency varies locally and is retained only in raw ignored outputs, not the stable semantic projection.",
        ],
    }
    report["report_sha256"] = sha256_bytes(canonical(report))
    return report, projection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or args.run_root / "audit"
    report, projection = audit_gbrain(
        source=args.source,
        runtime_root=args.runtime_root,
        run_paths=[
            args.run_root / "run-1/brainbench.json",
            args.run_root / "run-2/brainbench.json",
        ],
        junit_path=args.run_root / "upstream-focused-tests.junit.xml",
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output / "projection.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
