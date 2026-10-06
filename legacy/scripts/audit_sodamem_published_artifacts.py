#!/usr/bin/env python3
"""Audit SodaMem's pinned LongMemEval answer and retrieval artifacts offline.

This is artifact archaeology, not a benchmark reproduction or an independent
LLM regrade.  It binds the exact source and public dataset, recomputes the
stored self-judge score, verifies answer/context alignment, and emits a
content-addressed projection for a future independent judge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.longmemeval_judge import (  # noqa: E402
    LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
    official_answer_check_prompt,
)
from harness.memory_trials.public_sources import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
    LONGMEMEVAL_REPOSITORY_REVISION,
)

SODAMEM_REPOSITORY = "https://github.com/SodaMem/SodaMem"
SODAMEM_REVISION = "b182c1a603e47d82ee6e99190aa5022db28077b5"
SODAMEM_TREE = "2c6f29b5bcf3a570d7f9d381ce79b8050b7d94d3"
SODAMEM_SOURCE_ARCHIVE_SHA256 = "2abd4be8e9af9e3d05d351b5585b5d4c27adee2b93ad9b7af9ca8acfeea170bc"
LONGMEMEVAL_S_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
LONGMEMEVAL_S_SIZE = 277_383_467
JUDGED_PATH = "benchmarking/artifacts/sodamem_lme_judged.json"
CONTEXT_PATH = "benchmarking/artifacts/sodamem_lme_retrieved_context.json"
EXPECTED_SOURCE_FILES = {
    "LICENSE": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "README.md": "ef7939519bf2f87650eeb373056413e38ab25f4e9b46e52be117f6ea44a02242",
    "benchmarking/README.md": "bd5ce64d152990f631fd1b211e7cbbfb222eba1465d4de92c922e56f1c96de8a",
    "benchmarking/answer_one_question.py": (
        "aa21ae5dba4ac9b859f8be1b457e3d93cd455eccfb786f8698f7585a8219b373"
    ),
    "benchmarking/artifacts/README.md": (
        "19e2f439c34956ae091f1507cc8c59716329ef542a8ecb342be341dcb3bee2aa"
    ),
    "benchmarking/run_s500.py": "e1035606ec5f6f5b89174da5cadabd25fdbb7720c3c662866700cecaeebae148",
    "pyproject.toml": "7235fa819f1f4690a674bb6bb24e4aa2d0c7c1baec8b78040b0f90f36f417b83",
    "uv.lock": "a7d0fbce18ec5918d312725aba0c8e48da90b9a03a0b0df76fb79d5d0a4c40e4",
}
EXPECTED_ARTIFACTS = {
    JUDGED_PATH: {
        "sha256": "a5f4208b544d28396e38bf0dd3784366f80a6f743194a8f670ac7afbe658df51",
        "size": 783_441,
    },
    CONTEXT_PATH: {
        "sha256": "c7000364da353ba91ebb491dcd9dfccc610a4bb17360db60800b7685fcefe168",
        "size": 12_039_568,
    },
}
QUESTION_TYPES = {
    "knowledge-update",
    "multi-session",
    "single-session-assistant",
    "single-session-preference",
    "single-session-user",
    "temporal-reasoning",
}
JUDGED_KEYS = {
    "elapsed_s",
    "evidence_ids",
    "golden_answer",
    "hypothesis",
    "llm_judge",
    "planner_steps",
    "question",
    "question_id",
    "question_type",
    "tools_used",
    "usage_totals",
}
CONTEXT_KEYS = {
    "other_tools_used",
    "planner_queries",
    "question",
    "question_id",
    "question_type",
    "retrieved_evidence",
}
EVIDENCE_KEYS = {
    "content",
    "evidence_id",
    "extracted_support_text",
    "id",
    "kind",
    "modality",
    "occurred_start",
    "session_id",
    "source_trace_ids",
    "status",
    "valid_from",
    "valid_until",
}


@dataclass(frozen=True)
class SodaMemArtifactExpectations:
    repository: str | None = SODAMEM_REPOSITORY
    revision: str | None = SODAMEM_REVISION
    tree: str | None = SODAMEM_TREE
    source_archive_sha256: str | None = SODAMEM_SOURCE_ARCHIVE_SHA256
    source_files: dict[str, str] | None = None
    artifacts: dict[str, dict[str, int | str]] | None = None
    dataset_sha256: str = LONGMEMEVAL_S_SHA256
    dataset_size: int = LONGMEMEVAL_S_SIZE
    row_count: int = 500

    def resolved_source_files(self) -> dict[str, str]:
        return self.source_files or EXPECTED_SOURCE_FILES

    def resolved_artifacts(self) -> dict[str, dict[str, int | str]]:
        return self.artifacts or EXPECTED_ARTIFACTS


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path, label: str) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")
    return path


def _verify_file(path: Path, *, sha256: str, size: int | None = None) -> None:
    _regular(path, str(path))
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"artifact size mismatch: {path}")
    if _sha256_file(path) != sha256:
        raise ValueError(f"artifact SHA-256 mismatch: {path}")


def _load_array(path: Path, label: str) -> list[dict[str, Any]]:
    _regular(path, label)

    def reject(value: str) -> None:
        raise ValueError(f"{label} contains non-finite JSON value {value}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"{label} must be an array of objects")
    return payload


def _git(source_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise ValueError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def _normalize_repository(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _verify_source(source_root: Path, expectations: SodaMemArtifactExpectations) -> dict[str, Any]:
    if not source_root.is_dir() or source_root.is_symlink():
        raise ValueError("SodaMem source root must be a regular directory")
    source_files = expectations.resolved_source_files()
    for relative, expected in source_files.items():
        _verify_file(source_root / relative, sha256=expected)

    git_values = (
        expectations.repository,
        expectations.revision,
        expectations.tree,
        expectations.source_archive_sha256,
    )
    if all(value is None for value in git_values):
        return {"source_files": source_files}
    if any(value is None for value in git_values):
        raise ValueError("SodaMem git expectations must be all present or all absent")
    assert expectations.repository is not None
    assert expectations.revision is not None
    assert expectations.tree is not None
    assert expectations.source_archive_sha256 is not None
    actual = {
        "repository": _normalize_repository(_git(source_root, "remote", "get-url", "origin")),
        "revision": _git(source_root, "rev-parse", "HEAD"),
        "tree": _git(source_root, "rev-parse", "HEAD^{tree}"),
    }
    expected = {
        "repository": expectations.repository,
        "revision": expectations.revision,
        "tree": expectations.tree,
    }
    if actual != expected:
        raise ValueError("SodaMem source identity drifted")
    if _git(source_root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("SodaMem source checkout must be completely clean")
    archive = subprocess.run(
        ["git", "-C", str(source_root), "archive", "--format=tar", "HEAD"],
        check=False,
        capture_output=True,
    )
    if archive.returncode or _sha256_bytes(archive.stdout) != (expectations.source_archive_sha256):
        raise ValueError("SodaMem source archive bytes drifted")
    return {
        **actual,
        "source_archive_sha256": expectations.source_archive_sha256,
        "source_files": source_files,
    }


def _normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(
        "".join(character if character.isalnum() else " " for character in folded).split()
    )


def _contains_reference(reference: str | int | float, candidate: str) -> bool:
    normalized_reference = _normalized(str(reference))
    return bool(normalized_reference) and normalized_reference in _normalized(candidate)


def _validate_number(value: Any, label: str, *, integer: bool = False) -> None:
    expected_type = int if integer else (int, float)
    if (
        not isinstance(value, expected_type)
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or value < 0
    ):
        raise ValueError(f"{label} must be a finite non-negative number")


def _question_id(index: int) -> str:
    return f"q{index:03d}"


def _reference_key(value: Any) -> str:
    if isinstance(value, str) and value:
        return _canonical({"type": "string", "value": value}).decode()
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ):
        return _canonical({"type": "number", "value": value}).decode()
    raise ValueError("reference answer must be a non-empty string or finite number")


def _dataset_key(row: dict[str, Any]) -> tuple[str, str, str]:
    question = row.get("question")
    question_type = row.get("question_type")
    if not all(isinstance(value, str) and value for value in (question, question_type)):
        raise ValueError("LongMemEval row has an invalid question, answer, or type")
    return question, _reference_key(row.get("answer")), question_type


def _artifact_key(row: dict[str, Any]) -> tuple[str, str, str]:
    question = row.get("question")
    question_type = row.get("question_type")
    if not all(isinstance(value, str) and value for value in (question, question_type)):
        raise ValueError("SodaMem answer row has an invalid question, answer, or type")
    return question, _reference_key(row.get("golden_answer")), question_type


def audit_sodamem_published_artifacts(
    *,
    source_root: Path,
    dataset_path: Path,
    expectations: SodaMemArtifactExpectations | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify the pinned public artifacts and return a report plus claim projection."""

    expectations = expectations or SodaMemArtifactExpectations()
    source_root = source_root.resolve()
    dataset_path = dataset_path.resolve()
    source = _verify_source(source_root, expectations)
    _verify_file(
        dataset_path,
        sha256=expectations.dataset_sha256,
        size=expectations.dataset_size,
    )
    artifacts = expectations.resolved_artifacts()
    if set(artifacts) != {JUDGED_PATH, CONTEXT_PATH}:
        raise ValueError("SodaMem artifact roster drifted")
    for relative, receipt in artifacts.items():
        sha256 = receipt.get("sha256")
        size = receipt.get("size")
        if not isinstance(sha256, str) or not isinstance(size, int):
            raise ValueError("SodaMem artifact receipt is malformed")
        _verify_file(source_root / relative, sha256=sha256, size=size)

    dataset = _load_array(dataset_path, "LongMemEval dataset")
    judged = _load_array(source_root / JUDGED_PATH, "SodaMem judged artifact")
    contexts = _load_array(source_root / CONTEXT_PATH, "SodaMem context artifact")
    if not (len(dataset) == len(judged) == len(contexts) == expectations.row_count):
        raise ValueError("SodaMem artifact or dataset row count drifted")

    dataset_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    dataset_ids: set[str] = set()
    for row in dataset:
        key = _dataset_key(row)
        question_id = row.get("question_id")
        if (
            key in dataset_by_key
            or not isinstance(question_id, str)
            or not question_id
            or question_id in dataset_ids
        ):
            raise ValueError("LongMemEval alignment keys and IDs must be unique")
        dataset_by_key[key] = row
        dataset_ids.add(question_id)

    judged_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(judged, start=1):
        if set(row) != JUDGED_KEYS:
            raise ValueError("SodaMem judged row schema drifted")
        published_id = row.get("question_id")
        if published_id != _question_id(index) or published_id in judged_by_id:
            raise ValueError("SodaMem published question IDs are not contiguous and unique")
        if row.get("question_type") not in QUESTION_TYPES:
            raise ValueError("SodaMem judged row has an unsupported question type")
        hypothesis = row.get("hypothesis")
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("SodaMem judged row has an empty hypothesis")
        judge = row.get("llm_judge")
        if (
            not isinstance(judge, dict)
            or set(judge) != {"model", "correct"}
            or judge.get("model") != "deepseek-v4-flash"
            or not isinstance(judge.get("correct"), bool)
        ):
            raise ValueError("SodaMem self-judge receipt drifted")
        if row.get("evidence_ids") is not True:
            raise ValueError("SodaMem documented evidence_ids boolean sentinel drifted")
        _validate_number(row.get("elapsed_s"), "elapsed_s")
        _validate_number(row.get("planner_steps"), "planner_steps", integer=True)
        tools = row.get("tools_used")
        if (
            not isinstance(tools, list)
            or not tools
            or not all(isinstance(tool, str) and tool for tool in tools)
        ):
            raise ValueError("SodaMem tools_used is malformed")
        usage = row.get("usage_totals")
        if not isinstance(usage, dict) or set(usage) != {
            "calls",
            "cached_input_tokens",
            "completion_tokens",
            "prompt_tokens",
            "total_tokens",
        }:
            raise ValueError("SodaMem usage totals schema drifted")
        for name, value in usage.items():
            _validate_number(value, f"usage_totals.{name}", integer=True)
        if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
            raise ValueError("SodaMem total token count is internally inconsistent")
        if usage["cached_input_tokens"] > usage["prompt_tokens"]:
            raise ValueError("SodaMem cached input exceeds prompt tokens")
        judged_by_id[published_id] = row

    context_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(contexts, start=1):
        if set(row) != CONTEXT_KEYS:
            raise ValueError("SodaMem context row schema drifted")
        published_id = row.get("question_id")
        if published_id != _question_id(index) or published_id in context_by_id:
            raise ValueError("SodaMem context question IDs are not contiguous and unique")
        answer_row = judged_by_id[published_id]
        if (
            row.get("question") != answer_row["question"]
            or row.get("question_type") != answer_row["question_type"]
        ):
            raise ValueError("SodaMem answer and context artifacts are misaligned")
        queries = row.get("planner_queries")
        other_tools = row.get("other_tools_used")
        if (
            not isinstance(queries, list)
            or not queries
            or not all(isinstance(query, str) and query.strip() for query in queries)
        ):
            raise ValueError("SodaMem planner query list is malformed")
        if not isinstance(other_tools, list) or not all(
            isinstance(tool, str) and tool for tool in other_tools
        ):
            raise ValueError("SodaMem other tool list is malformed")
        if not set(other_tools).issubset(set(answer_row["tools_used"])):
            raise ValueError("SodaMem context tools exceed the judged tool trace")
        evidence = row.get("retrieved_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("SodaMem context row has no evidence")
        seen_evidence: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict) or set(item) != EVIDENCE_KEYS:
                raise ValueError("SodaMem evidence row schema drifted")
            evidence_id = item.get("evidence_id")
            item_id = item.get("id")
            content = item.get("content")
            source_trace_ids = item.get("source_trace_ids")
            if (
                not isinstance(evidence_id, str)
                or not evidence_id
                or evidence_id in seen_evidence
                or not isinstance(item_id, str)
                or not item_id
                or not evidence_id.endswith(item_id)
                or not isinstance(content, str)
                or not content
                or not isinstance(item.get("extracted_support_text"), str)
                or not isinstance(item.get("session_id"), str)
                or not item["session_id"]
                or not isinstance(item.get("kind"), str)
                or not item["kind"]
                or not isinstance(item.get("modality"), str)
                or not item["modality"]
                or not isinstance(item.get("status"), str)
                or not item["status"]
                or not isinstance(source_trace_ids, list)
                or not source_trace_ids
                or len(source_trace_ids) != len(set(source_trace_ids))
                or not all(isinstance(trace_id, str) and trace_id for trace_id in source_trace_ids)
                or any(
                    item.get(field) is not None and not isinstance(item.get(field), str)
                    for field in ("occurred_start", "valid_from", "valid_until")
                )
            ):
                raise ValueError("SodaMem evidence row is malformed")
            seen_evidence.add(evidence_id)
        context_by_id[published_id] = row

    if set(judged_by_id) != set(context_by_id):
        raise ValueError("SodaMem answer and context question rosters differ")
    artifact_keys = [_artifact_key(row) for row in judged]
    if len(set(artifact_keys)) != len(artifact_keys) or set(artifact_keys) != set(dataset_by_key):
        raise ValueError("SodaMem artifacts do not align exactly to pinned LongMemEval")

    projection: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, int | float]] = {}
    total_evidence = 0
    evidence_counts: list[int] = []
    self_judge_correct = 0
    hypothesis_reference_contains = 0
    evidence_reference_contains = 0
    non_abstention_count = 0
    non_abstention_hypothesis_contains = 0
    non_abstention_evidence_contains = 0
    planner_queries = 0
    planner_steps = 0
    provider_calls = 0
    usage_totals = Counter()
    for answer_row in judged:
        published_id = answer_row["question_id"]
        context_row = context_by_id[published_id]
        dataset_row = dataset_by_key[_artifact_key(answer_row)]
        original_id = dataset_row["question_id"]
        abstention = "_abs" in original_id
        reference = answer_row["golden_answer"]
        hypothesis_contains = _contains_reference(reference, answer_row["hypothesis"])
        evidence_text = "\n".join(
            f"{item['content']}\n{item['extracted_support_text']}"
            for item in context_row["retrieved_evidence"]
        )
        evidence_contains = _contains_reference(reference, evidence_text)
        prompt = official_answer_check_prompt(
            answer_row["question_type"],
            answer_row["question"],
            str(reference),
            answer_row["hypothesis"],
            abstention=abstention,
        )
        correct = answer_row["llm_judge"]["correct"]
        evidence_count = len(context_row["retrieved_evidence"])
        self_judge_correct += int(correct)
        hypothesis_reference_contains += int(hypothesis_contains)
        evidence_reference_contains += int(evidence_contains)
        if not abstention:
            non_abstention_count += 1
            non_abstention_hypothesis_contains += int(hypothesis_contains)
            non_abstention_evidence_contains += int(evidence_contains)
        total_evidence += evidence_count
        evidence_counts.append(evidence_count)
        planner_queries += len(context_row["planner_queries"])
        planner_steps += answer_row["planner_steps"]
        provider_calls += answer_row["usage_totals"]["calls"]
        usage_totals.update(answer_row["usage_totals"])
        cell = by_type.setdefault(
            answer_row["question_type"],
            {"count": 0, "self_judge_correct": 0},
        )
        cell["count"] = int(cell["count"]) + 1
        cell["self_judge_correct"] = int(cell["self_judge_correct"]) + int(correct)
        projection.append(
            {
                "published_question_id": published_id,
                "longmemeval_question_id": original_id,
                "question_type": answer_row["question_type"],
                "abstention": abstention,
                "self_judge_correct": correct,
                "hypothesis_contains_normalized_reference": hypothesis_contains,
                "retrieved_evidence_contains_normalized_reference": evidence_contains,
                "retrieved_evidence_count": evidence_count,
                "source_trace_ids_complete": True,
                "official_prompt_sha256": _sha256_bytes(prompt.encode()),
                "judged_row_sha256": _sha256_bytes(_canonical(answer_row)),
                "context_row_sha256": _sha256_bytes(_canonical(context_row)),
            }
        )
    for cell in by_type.values():
        cell["self_judge_accuracy"] = int(cell["self_judge_correct"]) / int(cell["count"])

    projection_sha256 = _sha256_bytes(_canonical(projection))
    dataset_id_root_sha256 = _sha256_bytes(
        _canonical([row["longmemeval_question_id"] for row in projection])
    )
    report = {
        "schema_version": 1,
        "status": "SODAMEM_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED",
        "scientific_result": False,
        "publication_ready": False,
        "claim_scope": (
            "released-artifact-integrity-score-recomputation-and-judge-case-preparation-only"
        ),
        "source": source,
        "artifacts": artifacts,
        "dataset": {
            "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
            "sha256": expectations.dataset_sha256,
            "size": expectations.dataset_size,
            "rows": len(dataset),
            "abstention_rows": len(dataset) - non_abstention_count,
            "ordered_aligned_question_id_root_sha256": dataset_id_root_sha256,
        },
        "stored_self_judge": {
            "model": "deepseek-v4-flash",
            "reader_planner_model": "deepseek-v4-flash",
            "same_model_self_grading": True,
            "correct": self_judge_correct,
            "total": len(judged),
            "accuracy": self_judge_correct / len(judged),
            "by_question_type": dict(sorted(by_type.items())),
        },
        "deterministic_diagnostics_not_accuracy_metrics": {
            "normalization": "NFKC-casefold-alphanumeric-whitespace",
            "hypothesis_contains_full_normalized_reference": hypothesis_reference_contains,
            "retrieved_evidence_contains_full_normalized_reference": evidence_reference_contains,
            "non_abstention_total": non_abstention_count,
            "non_abstention_hypothesis_contains_full_normalized_reference": (
                non_abstention_hypothesis_contains
            ),
            "non_abstention_retrieved_evidence_contains_full_normalized_reference": (
                non_abstention_evidence_contains
            ),
        },
        "retrieval_artifact": {
            "evidence_rows": total_evidence,
            "minimum_evidence_rows_per_question": min(evidence_counts),
            "maximum_evidence_rows_per_question": max(evidence_counts),
            "mean_evidence_rows_per_question": total_evidence / len(evidence_counts),
            "questions_with_no_evidence": 0,
            "questions_with_duplicate_evidence_ids": 0,
            "evidence_rows_with_no_source_trace_id": 0,
            "answer_rows_with_evidence_id_lists": 0,
            "answer_rows_with_boolean_evidence_sentinel": len(judged),
            "planner_queries": planner_queries,
        },
        "usage": {
            "planner_steps": planner_steps,
            "provider_calls": provider_calls,
            **dict(sorted(usage_totals.items())),
        },
        "independent_judge_cases": {
            "count": len(projection),
            "prompt_port_version": LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
            "evaluator_repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "evaluator_source_sha256": LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
            "projection_sha256": projection_sha256,
        },
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "limitations": [
            (
                "The stored 464/500 verdict is recomputed, not independently "
                "re-judged; reader, planner, and original judge all use "
                "deepseek-v4-flash."
            ),
            (
                "The 12 GB frozen store, ingest inputs, and pre-release code are not "
                "distributed, so retrieval and construction cannot be rerun from "
                "this revision."
            ),
            (
                "The reader prompt was not captured, so answers cannot be "
                "reconstructed exactly from the released retrieval union."
            ),
            (
                "The judged artifact documents evidence_ids but stores a boolean true "
                "for all 500 rows; cross-file evidence linkage depends on the "
                "synthetic q001-q500 IDs."
            ),
            (
                "All 8,427 evidence rows name source_trace_ids, but the source spans "
                "and raw store are not published, so provenance is syntactically "
                "complete but not independently dereferenceable."
            ),
            (
                "Normalized reference containment is a deterministic diagnostic lower "
                "bound, not an accuracy or semantic-support metric."
            ),
            (
                "The upstream documented dev-only test environment omits chroma, llm, "
                "and server extras required by collected tests; a local "
                "dev+chroma+llm+server run passed 737 tests with 19 skips."
            ),
        ],
        "next_gate": (
            "Run a provider-distinct judge over the sealed official-prompt cases, then "
            "register a common-construction SodaMem versus flat-history and temporal-graph "
            "control cell before any mechanism or publication claim."
        ),
    }
    report["report_sha256"] = _sha256_bytes(_canonical(report))
    return report, projection


def _write_once(path: Path, payload: Any) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ValueError(f"refusing to overwrite {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    args = parser.parse_args()
    try:
        report, projection = audit_sodamem_published_artifacts(
            source_root=args.source_root,
            dataset_path=args.dataset,
        )
        _write_once(args.report, report)
        _write_once(args.projection, projection)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"{report['status']} self_judge={report['stored_self_judge']['correct']}/"
        f"{report['stored_self_judge']['total']} evidence="
        f"{report['retrieval_artifact']['evidence_rows']} report="
        f"{report['report_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
