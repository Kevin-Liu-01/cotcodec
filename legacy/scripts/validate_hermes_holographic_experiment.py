#!/usr/bin/env python3
"""Validate the frozen Hermes Holographic lifecycle falsifier contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-holographic-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_GLOBAL_SESSION_SCOPE_AND_NATIVE_SESSION_PURGE_REPRODUCED"
EXPECTED_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class HolographicExperimentError(ValueError):
    """Raised when the registered provider lifecycle contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise HolographicExperimentError("Holographic experiment must be schema_version 1")
    if payload.get("name") != "stage4-hermes-holographic-lifecycle-doctor":
        raise HolographicExperimentError("Holographic experiment name drifted")
    source = payload.get("source")
    if not isinstance(source, dict) or source.get("revision") != EXPECTED_REVISION:
        raise HolographicExperimentError("Holographic source revision drifted")
    for field in (
        "git_archive_tar_sha256",
        "license_sha256",
        "hermes_state_sha256",
        "store_sha256",
        "retrieval_sha256",
        "holographic_sha256",
        "provider_sha256",
    ):
        if not isinstance(source.get(field), str) or not SHA256_RE.fullmatch(source[field]):
            raise HolographicExperimentError(f"Holographic source {field} is not SHA-256")
    runtime = payload.get("runtime")
    if (
        not isinstance(runtime, dict)
        or runtime.get("network_mode") != "none"
        or runtime.get("read_only_root") is not True
        or runtime.get("cap_drop_all") is not True
        or runtime.get("no_new_privileges") is not True
        or runtime.get("user") != "65532:65532"
        or runtime.get("gpu_count") != 0
        or runtime.get("clean_repetitions") != 2
    ):
        raise HolographicExperimentError("Holographic containment contract drifted")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("backend") != "native-sqlite-fts5"
        or contract.get("hrr_mode") != "disabled-no-numpy"
        or contract.get("logical_fact_count") != 3
        or contract.get("phases") != ["prepare", "restart", "purge"]
        or contract.get("require_fresh_process_per_phase") is not True
        or contract.get("probe_global_session_visibility") is not True
        or contract.get("scan_sqlite_db_wal_shm_for_plaintext") is not True
        or any(
            contract.get(field) != 0
            for field in ("model_calls", "embedding_calls", "network_calls")
        )
    ):
        raise HolographicExperimentError("Holographic lifecycle contract drifted")
    expected = payload.get("expected_falsification")
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or expected.get("restart_persistence_supported") is not True
        or expected.get("session_scoped_isolation_supported") is not False
        or expected.get("native_session_purge_supported") is not False
        or expected.get("physical_zero_residue_after_logical_delete")
        != "runtime-diagnostic-not-gate"
    ):
        raise HolographicExperimentError("Holographic falsification contract drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("memory_lifecycle_h100") != "forbidden-for-this-revision"
    ):
        raise HolographicExperimentError("Holographic admission contract drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise HolographicExperimentError("Holographic claim boundary drifted")
    payload["experiment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"Hermes Holographic experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
