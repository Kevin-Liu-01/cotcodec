#!/usr/bin/env python3
"""Fail-closed validator for the Icarus lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-icarus-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE"
EXPECTED_SOURCE = {
    "source_id": "icarus-memory-infra",
    "repository": "https://github.com/esaradev/icarus-memory-infra",
    "revision": "6e348708dcddb7cf1ad47726cb287cd4c9183c40",
    "tree": "fcdbae5db3ed582f679bac2b7348818e20b6e91c",
    "version": "0.3.0",
    "git_archive_tar_sha256": (
        "e0a396bd48be2f2a30d751ed10d6ab1a2a2c80dda094e6334b33f87045d19c05"
    ),
    "license": "MIT",
    "license_sha256": (
        "15f6d225dbd3d8496c521f42454ffff7a9cbbdd3d52d2bb447de6c72440ef19c"
    ),
    "pyproject_sha256": (
        "c982050f9f5b1b46d8a854bd2b709bd4d7ca21cb6aeca19195ddb4ca3049a0c7"
    ),
}


class IcarusExperimentError(ValueError):
    """Raised when the registered Icarus experiment drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise IcarusExperimentError(f"cannot load Icarus experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise IcarusExperimentError("Icarus experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-icarus-lifecycle-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise IcarusExperimentError("Icarus experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise IcarusExperimentError("Icarus source contract drifted")

    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise IcarusExperimentError("Icarus runtime contract is missing")
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
    for field, expected in required_runtime.items():
        if runtime.get(field) != expected:
            raise IcarusExperimentError(f"Icarus runtime field {field} drifted")

    suite = payload.get("upstream_suite")
    if not isinstance(suite, dict) or {
        "passed": suite.get("passed"),
        "failed": suite.get("failed"),
        "skipped": suite.get("skipped"),
        "expected_failure": suite.get("expected_failure"),
    } != {
        "passed": 207,
        "failed": 6,
        "skipped": 39,
        "expected_failure": "mcp-major-version-path-incompatibility",
    }:
        raise IcarusExperimentError("Icarus upstream-suite contract drifted")

    intervention = payload.get("intervention")
    if not isinstance(intervention, dict):
        raise IcarusExperimentError("Icarus intervention is missing")
    if intervention.get("phases") != ["prepare", "verify-restart", "purge-probe"]:
        raise IcarusExperimentError("Icarus phase order drifted")
    if any(
        intervention.get(field) != 0
        for field in ("model_calls", "embedding_calls", "external_api_calls")
    ):
        raise IcarusExperimentError("Icarus CPU falsifier cannot call models or APIs")

    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise IcarusExperimentError("Icarus expected falsification drifted")
    required_truths = {
        "manual_promotion_reproduced",
        "duplicate_end_session_creates_extra_summary",
        "duplicate_end_session_creates_extra_wiki_link",
        "fresh_process_restart_preserves_archive_wiki_supersession_and_rollback",
        "all_plaintext_canaries_remain_physically_present",
        "reproduced_in_two_clean_states",
    }
    if any(expected.get(field) is not True for field in required_truths):
        raise IcarusExperimentError("Icarus expected positive/negative gates drifted")
    if expected.get("native_delete_or_purge_api_available") is not False:
        raise IcarusExperimentError("Icarus native purge expectation drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
    ):
        raise IcarusExperimentError("Icarus H100 admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Icarus lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
