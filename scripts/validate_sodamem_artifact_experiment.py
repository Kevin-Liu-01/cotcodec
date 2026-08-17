#!/usr/bin/env python3
"""Validate the exact SodaMem published-artifact audit contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-sodamem-published-artifact-audit.yaml"
)
EXPECTED_SOURCE = {
    "source_id": "sodamem",
    "repository": "https://github.com/SodaMem/SodaMem",
    "revision": "b182c1a603e47d82ee6e99190aa5022db28077b5",
    "tree": "2c6f29b5bcf3a570d7f9d381ce79b8050b7d94d3",
    "license": "Apache-2.0",
    "license_sha256": ("cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"),
    "git_archive_tar_sha256": ("2abd4be8e9af9e3d05d351b5585b5d4c27adee2b93ad9b7af9ca8acfeea170bc"),
}
EXPECTED_ARTIFACTS = {
    "judged": {
        "path": "benchmarking/artifacts/sodamem_lme_judged.json",
        "sha256": ("a5f4208b544d28396e38bf0dd3784366f80a6f743194a8f670ac7afbe658df51"),
        "size": 783_441,
        "rows": 500,
    },
    "retrieved_context": {
        "path": "benchmarking/artifacts/sodamem_lme_retrieved_context.json",
        "sha256": ("c7000364da353ba91ebb491dcd9dfccc610a4bb17360db60800b7685fcefe168"),
        "size": 12_039_568,
        "rows": 500,
    },
}
EXPECTED_DATASET = {
    "repository_revision": "9e0b455f4ef0e2ab8f2e582289761153549043fc",
    "dataset_revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
    "sha256": "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
    "size": 277_383_467,
    "rows": 500,
    "abstention_rows": 30,
}
EXPECTED_RUNTIME = {
    "lane": "local-arm64-read-only-artifact-audit",
    "platform": "macos-26.4-arm64",
    "python": "3.13.14",
    "uv": "0.11.30",
    "project_lock_sha256": ("6bd99e8e302585a9c186ec03a3621983ce3a677987c6fdf0bcb71fe3709a3765"),
    "external_network_required": False,
    "source_and_dataset_mutation": "forbidden",
}
EXPECTED_CASES = {
    "exact_source_artifact_and_dataset_receipts": True,
    "exact_500_row_dataset_alignment": True,
    "stored_self_judge_score_recomputation": True,
    "answer_context_cross_file_alignment": True,
    "evidence_schema_and_source_trace_id_completeness": True,
    "official_prompt_case_hashes": True,
    "deterministic_reference_containment_diagnostic": True,
    "byte_identical_repeat": True,
}
EXPECTED_GATES = {
    "stored_self_judge_correct": 464,
    "stored_self_judge_total": 500,
    "retrieved_evidence_rows": 8_427,
    "empty_evidence_questions": 0,
    "duplicate_evidence_id_questions": 0,
    "evidence_rows_without_source_trace_ids": 0,
    "answer_rows_with_evidence_id_lists": 0,
    "answer_rows_with_boolean_evidence_sentinel": 500,
    "official_prompt_cases": 500,
    "repetitions_byte_identical": True,
    "scientific_result_must_remain_false": True,
    "h100_admission_must_remain_ungranted": True,
}
EXPECTED_EXECUTION = {
    "repetitions": 2,
    "external_api_calls": 0,
    "llm_calls": 0,
    "gpus": 0,
    "max_gpu_hours": 0,
    "cpu_time_limit_minutes": 5,
    "h100_admission": "not-granted-by-artifact-audit",
}
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned released-artifact integrity, dataset alignment, stored "
    "deepseek-v4-flash self-judge score recomputation, evidence-schema diagnostics, "
    "deterministic reference-containment diagnostics, and official-prompt case "
    "preparation; not an independent regrade, retrieval reproduction, ingest or "
    "construction reproduction, temporal-graph mechanism effect, memory-quality "
    "result, H100 actor admission, or publication evidence."
)
EXPECTED_FORBIDDEN_CLAIMS = [
    "SodaMem independently reproduces 92.8 percent",
    "the released retrieval was regenerated",
    "source_trace_ids were independently dereferenced",
    "normalized reference containment is semantic accuracy",
    "SodaMem temporal graphs caused the stored score",
    "H100 actor admission passed",
    "publication ready",
]


class SodaMemArtifactExperimentError(ValueError):
    """Raised when the registered SodaMem artifact-audit contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SodaMemArtifactExperimentError(
            f"cannot load SodaMem artifact experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SodaMemArtifactExperimentError("SodaMem experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-sodamem-published-artifact-audit",
        "status": "registered-cpu-artifact-audit",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise SodaMemArtifactExperimentError("SodaMem experiment identity drifted")
    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        raise SodaMemArtifactExperimentError("SodaMem description is missing")
    exact_sections = {
        "source": EXPECTED_SOURCE,
        "artifacts": EXPECTED_ARTIFACTS,
        "dataset": EXPECTED_DATASET,
        "runtime": EXPECTED_RUNTIME,
        "cases": EXPECTED_CASES,
        "gates": EXPECTED_GATES,
        "execution": EXPECTED_EXECUTION,
    }
    for name, expected in exact_sections.items():
        if payload.get(name) != expected:
            raise SodaMemArtifactExperimentError(f"SodaMem {name} contract drifted")
    if payload.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY:
        raise SodaMemArtifactExperimentError("SodaMem claim boundary drifted")
    if payload.get("forbidden_claims") != EXPECTED_FORBIDDEN_CLAIMS:
        raise SodaMemArtifactExperimentError("SodaMem forbidden-claim roster drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("SodaMem published-artifact experiment contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
