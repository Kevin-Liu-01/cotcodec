#!/usr/bin/env python3
"""Fail-closed validator for the pinned LightMem consolidation falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-lightmem-offline-consolidation-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT"
)


class LightMemExperimentError(ValueError):
    """Raised when the registered LightMem source/runtime contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise LightMemExperimentError(f"cannot load LightMem experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise LightMemExperimentError("LightMem experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-lightmem-offline-consolidation-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise LightMemExperimentError("LightMem experiment identity drifted")

    if payload.get("source") != {
        "source_id": "lightmem",
        "repository": "https://github.com/zjunlp/LightMem",
        "revision": "8fc9a9179f9170c4a40fc653fcb410375900f26e",
        "tree": "343831b5f0aa1d6dec62cb1c12ed71d9c7ab4a62",
        "version": "0.1.0",
        "license": "MIT",
        "license_sha256": (
            "5ec1877dbe08c6d6ee2213e44a64bc011bd21819b50b4172e3bca4acab4bf4e8"
        ),
        "package_metadata_license": "Apache-2.0",
        "pyproject_sha256": (
            "632334023335283070abb2eebfc5bece3eea11387724eaccb7aeda40732b97bb"
        ),
        "git_archive_tar_sha256": (
            "50830e429b65043767f485b5494829715a4c98980f98c1dd4c52c0342e588601"
        ),
        "root_dependency_lock": "absent",
    }:
        raise LightMemExperimentError("LightMem source contract drifted")

    if payload.get("runtime") != {
        "containment": "docker-network-none",
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count_inside_container": 0,
        "clean_state_repeats": 2,
        "base_image": (
            "python@sha256:"
            "ecb0ac954790dd64a0d518d699b9c61a91780c42b0d877c802dbaffd04db66f9"
        ),
    }:
        raise LightMemExperimentError("LightMem runtime contract drifted")

    if payload.get("intervention") != {
        "exact_source_methods": True,
        "dependency_adapters": "deterministic-test-doubles",
        "provider_calls": 0,
        "model_backend_calls": 0,
        "test_online_update_noop": True,
        "test_default_qdrant_reopen": True,
        "test_offline_trigger_api": True,
        "test_consolidation_embedding_consistency": True,
        "test_context_retrieval_dispatch": True,
        "test_lineage_and_purge_surface": True,
    }:
        raise LightMemExperimentError("LightMem intervention contract drifted")

    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "default_qdrant_reopen_deletes_existing_state": True,
        "official_offline_script_omits_persistence_flag": True,
        "online_update_is_noop": True,
        "automatic_offline_trigger_raises_keyword_typeerror": True,
        "offline_update_leaves_embedding_stale": True,
        "context_only_retrieval_is_broken": True,
        "source_lineage_and_scoped_purge_absent": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise LightMemExperimentError("LightMem falsification contract drifted")

    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise LightMemExperimentError("LightMem admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("LightMem offline consolidation falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
