#!/usr/bin/env python3
"""Fail-closed validator for the Palimpsest bitemporal falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-palimpsest-bitemporal-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE"
EXPECTED_SOURCE = {
    "source_id": "palimpsest-bitemporal-memory",
    "repository": "https://github.com/joe51111jwd/palimpsest",
    "revision": "0f83e166b0512a5ca9f38c2559f68749b35e994d",
    "tree": "fd25cbc074172ad0291f8a46faccaedd5deb2b48",
    "version": "0.1.0",
    "git_archive_tar_sha256": (
        "752c3fb16c9beae152c833cb0cd5e8ed67a80eba3c5fe544283f6642f9cc2be6"
    ),
    "license": "Apache-2.0",
    "license_sha256": (
        "7ecd8ce1d30b8aa26232f5c7c878cca53bc273547ce52f1678f955154746e64f"
    ),
    "pyproject_sha256": (
        "83d380afe22c2493ef634a3f871eec7b4da1e633dd5604baab6c09d82b33ec74"
    ),
}


class PalimpsestExperimentError(ValueError):
    """Raised when the registered Palimpsest contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PalimpsestExperimentError(f"cannot load Palimpsest experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise PalimpsestExperimentError("Palimpsest experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-palimpsest-bitemporal-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise PalimpsestExperimentError("Palimpsest experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise PalimpsestExperimentError("Palimpsest source contract drifted")

    runtime = payload.get("runtime")
    required_runtime = {
        "containment": "docker-network-none",
        "local_platform": "linux/arm64",
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "max_gpu_hours": 0,
        "clean_state_repeats": 2,
        "dependency_lock": "absent-upstream",
    }
    if not isinstance(runtime, dict) or any(
        runtime.get(field) != expected for field, expected in required_runtime.items()
    ):
        raise PalimpsestExperimentError("Palimpsest runtime contract drifted")

    suite = payload.get("upstream_suite")
    if not isinstance(suite, dict) or {
        field: suite.get(field) for field in ("passed", "failed", "skipped")
    } != {"passed": 274, "failed": 11, "skipped": 35}:
        raise PalimpsestExperimentError("Palimpsest upstream-suite contract drifted")

    intervention = payload.get("intervention")
    if (
        not isinstance(intervention, dict)
        or intervention.get("phases") != ["prepare", "verify-restart", "purge-probe"]
        or any(
            intervention.get(field) != 0
            for field in ("model_calls", "embedding_model_calls", "external_api_calls")
        )
    ):
        raise PalimpsestExperimentError("Palimpsest intervention contract drifted")

    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise PalimpsestExperimentError("Palimpsest expected status drifted")
    true_fields = {
        "pre_restart_valid_and_transaction_time_correct",
        "duplicate_save_row_count_idempotent",
        "restart_preserves_ordinary_valid_time_and_current_value",
        "correction_hides_canary_from_current_facts",
        "plaintext_canary_remains_in_sqlite",
        "reproduced_in_two_clean_states",
    }
    false_fields = {
        "restart_preserves_transaction_time_knowledge_cutoff",
        "restart_preserves_closed_tx",
        "restart_preserves_mixed_cardinality_continuation",
        "native_delete_or_purge_api_available",
    }
    if any(expected.get(field) is not True for field in true_fields) or any(
        expected.get(field) is not False for field in false_fields
    ):
        raise PalimpsestExperimentError("Palimpsest falsification gates drifted")
    if (
        expected.get("uninterrupted_goal_after_continuation") != ["delta"]
        or expected.get("restored_goal_after_continuation") != ["gamma", "delta"]
    ):
        raise PalimpsestExperimentError("Palimpsest continuation oracle drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
    ):
        raise PalimpsestExperimentError("Palimpsest H100 admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Palimpsest bitemporal falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
