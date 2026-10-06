#!/usr/bin/env python3
"""Validate the exact GBrain BrainBench conformance contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gbrain-brainbench-conformance-doctor.yaml"
)
EXPECTED_SOURCE = {
    "source_id": "gbrain",
    "repository": "https://github.com/garrytan/gbrain",
    "revision": "d941e9f918236c33e10e42d8a4223f36789b02c9",
    "tree": "4d7960cc1d88c40e0642204dfb144fd988c02208",
    "license": "MIT",
    "license_sha256": "e56fbb5b3d95756f3fa1cfefa24732ec79f18ece1ad08a4e79e00df57e8b198c",
    "git_archive_tar_sha256": ("d83320b8a155f26d3b707e23fae5ba6f4245cc6c284766b382ba011521b82698"),
    "package_sha256": "30a1e103ae53c41be2713a08b6589d69fd8e86f826d1911468baa300aa5aa2f0",
    "lock_sha256": "398e282d37f78c4e40a8be050b7c9e8858c35875310f39ec30a74fd8d557f9c2",
}
EXPECTED_RUNTIME = {
    "lane": "local-darwin-arm64-bun-conformance",
    "bun_version": "1.3.13",
    "release_archive_sha256": ("5467e3f65dba526b9fea98f0cce04efafc0c63e169733ec27b876a3ad32da190"),
    "binary_sha256": "fc0b4cae13a911098f0c61d13b7d9fd6b640bdb9f6b6a0b78bdb9d778c12bc3f",
    "frozen_lockfile": True,
    "lifecycle_scripts_disabled": True,
    "provider_credentials_unset": True,
    "external_api_calls": 0,
}
EXPECTED_CORPUS = {
    "ledger_sha256": "79cca16cbafc52c81fbf6f1d4b07a921540f034cc4feb3fb7b859480f37b92b5",
    "baseline_sha256": "6566285f6a3f66b87db5b046ed2f8f14fbf806162b65db7e38d3d979f5f9774c",
    "fixtures_sha256": "76f201590dd3ad7a929e2e12efc9bf1406627b10ef4edbcfe7caf379aafd4090",
    "generated_fixtures": 135,
    "holdout_fixtures": 23,
    "gate_fixture_executions": 106,
    "gold_turns_in_generated_corpus": 241,
    "turn_rows": 786,
}
EXPECTED_CASES = {
    "exact_source_tree_and_archive": True,
    "exact_pinned_runtime_and_lock": True,
    "focused_upstream_tests": 146,
    "focused_upstream_assertions": 725,
    "same_hash_gate_repetitions": 2,
    "expected_cells": 12,
    "production_seams": ["openclaw"],
    "contract_only_seams": ["claude-code", "codex"],
    "semantic_repetitions_identical": True,
}
EXPECTED_GATES = {
    "compare_verdict": "pass",
    "compare_mode": "same-hash",
    "seed_failures": 0,
    "source_isolation_violations": 0,
    "semantic_projection_sha256": (
        "8e4ebad237c774eaeed37ee40c4b4b8a2a6a9fa9511485257655cd2f6dc1ab27"
    ),
    "matched_pull_retrieval_arm_present": False,
    "scientific_result_must_remain_false": True,
    "h100_admission_must_remain_ungranted": True,
}
EXPECTED_EXECUTION = {
    "repetitions": 2,
    "model_calls": 0,
    "embedding_calls": 0,
    "external_api_calls": 0,
    "gpus": 0,
    "max_gpu_hours": 0,
    "cpu_time_limit_minutes": 5,
    "h100_admission": "not-granted-matched-pull-arm-missing",
}
EXPECTED_CLAIM_BOUNDARY = (
    "Exact-source deterministic BrainBench conformance with one shipped OpenClaw "
    "production injection seam and two GBrain-owned contract adapters; not a "
    "matched pull-retrieval comparison, live-agent evaluation, memory-quality "
    "result, model-quality result, H100 actor admission, or publication evidence."
)
EXPECTED_FORBIDDEN_CLAIMS = [
    "GBrain push injection beats pull retrieval",
    "Claude Code and Codex production integrations were reproduced",
    "BrainBench measures live-agent answer quality",
    "GBrain memory quality was reproduced",
    "H100 actor admission passed",
    "publication ready",
]


class GBrainExperimentError(ValueError):
    """Raised when the registered GBrain conformance contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise GBrainExperimentError(f"cannot load GBrain experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise GBrainExperimentError("GBrain experiment must be a mapping")
    identity = {
        "schema_version": 1,
        "name": "stage3-gbrain-brainbench-conformance-doctor",
        "status": "registered-cpu-conformance",
        "scientific_result": False,
        "publication_ready": False,
    }
    if any(payload.get(key) != value for key, value in identity.items()):
        raise GBrainExperimentError("GBrain experiment identity drifted")
    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        raise GBrainExperimentError("GBrain description is missing")
    sections = {
        "source": EXPECTED_SOURCE,
        "runtime": EXPECTED_RUNTIME,
        "corpus": EXPECTED_CORPUS,
        "cases": EXPECTED_CASES,
        "gates": EXPECTED_GATES,
        "execution": EXPECTED_EXECUTION,
    }
    for name, expected in sections.items():
        if payload.get(name) != expected:
            raise GBrainExperimentError(f"GBrain {name} contract drifted")
    if payload.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY:
        raise GBrainExperimentError("GBrain claim boundary drifted")
    if payload.get("forbidden_claims") != EXPECTED_FORBIDDEN_CLAIMS:
        raise GBrainExperimentError("GBrain forbidden-claim roster drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("GBrain BrainBench conformance experiment contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
