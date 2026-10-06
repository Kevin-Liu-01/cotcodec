#!/usr/bin/env python3
"""Validate the frozen Hermes ByteRover offline compatibility falsifier."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage4-hermes-byterover-offline-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_OFFLINE_DAEMON_AND_PORTABLE_SESSION_LIFECYCLE_REPRODUCED"
HERMES_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
BYTEROVER_REVISION = "1f4609c18ca735810860b3ba9178cae2dd8a67b0"
BYTEROVER_TAG_OBJECT = "68ef7f91801e18ff50f361bd4cad5f36b8791789"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ByteRoverExperimentError(ValueError):
    """Raised when the registered ByteRover contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ByteRoverExperimentError("ByteRover experiment must be schema_version 1")
    if payload.get("name") != "stage4-hermes-byterover-offline-doctor":
        raise ByteRoverExperimentError("ByteRover experiment name drifted")
    sources = payload.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"hermes", "byterover"}:
        raise ByteRoverExperimentError("ByteRover source roster drifted")
    if (
        sources["hermes"].get("revision") != HERMES_REVISION
        or sources["byterover"].get("revision") != BYTEROVER_REVISION
        or sources["byterover"].get("tag_object") != BYTEROVER_TAG_OBJECT
        or sources["byterover"].get("license") != "Elastic-2.0"
        or sources["byterover"].get("version") != "3.16.1"
    ):
        raise ByteRoverExperimentError("ByteRover source identity drifted")
    for source in sources.values():
        for field, value in source.items():
            if field.endswith("_sha256") and (
                not isinstance(value, str) or not SHA256_RE.fullmatch(value)
            ):
                raise ByteRoverExperimentError(
                    f"ByteRover source {field} is not SHA-256"
                )
    runtime = payload.get("runtime")
    if (
        not isinstance(runtime, dict)
        or runtime.get("network_mode") != "none"
        or runtime.get("read_only_root") is not True
        or runtime.get("cap_drop_all") is not True
        or runtime.get("no_new_privileges") is not True
        or runtime.get("user") != "1000:1000"
        or runtime.get("gpu_count") != 0
        or runtime.get("command_timeout_seconds") != 7
        or runtime.get("clean_repetitions") != 2
    ):
        raise ByteRoverExperimentError("ByteRover containment contract drifted")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("phases") != ["prepare", "restart"]
        or contract.get("native_offline_command") != "search"
        or contract.get("hermes_read_command") != "query"
        or contract.get("hermes_write_command") != "curate"
        or contract.get("require_daemon_network_fatal") is not True
        or contract.get("require_global_profile_directory") is not True
        or contract.get("require_native_session_purge") is not False
        or any(
            contract.get(field) != 0
            for field in ("model_calls", "embedding_calls", "network_calls")
        )
    ):
        raise ByteRoverExperimentError("ByteRover command contract drifted")
    expected = payload.get("expected_falsification")
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or expected.get("offline_search_available_under_network_none") is not False
        or expected.get("hermes_query_available_under_network_none") is not False
        or expected.get("hermes_curate_available_under_network_none") is not False
        or expected.get("session_scoped_directory") is not False
        or expected.get("native_session_purge_supported") is not False
    ):
        raise ByteRoverExperimentError("ByteRover falsification contract drifted")
    admission = payload.get("admission")
    claims = payload.get("claims")
    if (
        not isinstance(admission, dict)
        or admission.get("memory_lifecycle_h100") != "forbidden-for-this-revision"
        or not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise ByteRoverExperimentError("ByteRover claim boundary drifted")
    payload["experiment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"Hermes ByteRover experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
