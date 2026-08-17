#!/usr/bin/env python3
"""Validate the pinned Hermes memory-provider conformance contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_ROSTER = [
    "byterover",
    "hindsight",
    "holographic",
    "honcho",
    "mem0",
    "memori",
    "openviking",
    "retaindb",
    "supermemory",
]
EXPECTED_BUNDLED = {
    "byterover": "adapter-contract-only",
    "hindsight": "adapter-contract-plus-strict-timeout-probe",
    "holographic": "local-sqlite-contract",
    "honcho": "adapter-contract-only",
    "mem0": "adapter-contract-only",
    "openviking": "adapter-contract-without-server",
    "retaindb": "adapter-contract-only",
    "supermemory": "adapter-contract-only",
}
EXPECTED_IMAGE = (
    "ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:"
    "b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b"
)


def _mapping(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"Hermes provider contract field {field!r} must be a mapping")
    return value


def _exact_sha(value: Any, pattern: re.Pattern[str], field: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"Hermes provider contract field {field!r} is not immutable")
    return value


def load_and_validate_experiment(path: Path) -> tuple[dict[str, Any], str]:
    """Load the contract, validate its scientific boundaries, and return its hash."""

    if not path.is_file() or path.is_symlink():
        raise ValueError("Hermes provider experiment must be a regular non-symlink YAML")
    encoded = path.read_bytes()
    try:
        payload = yaml.safe_load(encoded)
    except yaml.YAMLError as exc:
        raise ValueError("Hermes provider experiment YAML is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("Hermes provider experiment must be a mapping")
    expected_header = {
        "schema_version": 1,
        "name": "stage4-hermes-provider-conformance",
        "status": "registered-cpu-provider-contract",
        "scientific_result": False,
        "protocol": "hermes-memory-provider-conformance-v1",
    }
    if any(payload.get(key) != value for key, value in expected_header.items()):
        raise ValueError("Hermes provider experiment header drifted")

    sources = _mapping(payload, "sources")
    hermes = _mapping(sources, "hermes")
    memori = _mapping(sources, "memori")
    if hermes != {
        "repository": "https://github.com/NousResearch/hermes-agent",
        "revision": "a90d5369f76c87c98547d2e283aa26d5cfabf322",
        "tree": "963eb136bfb21fd0b296a40529cbb3575c610874",
        "archive_sha256": (
            "2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514"
        ),
        "version": "0.20.1",
        "license": "MIT",
    }:
        raise ValueError("Hermes provider source contract drifted")
    if memori != {
        "repository": "https://github.com/MemoriLabs/Memori",
        "revision": "538b61f245295aa1a43df8033879f8293627f74d",
        "tree": "6efd92a1d65c49dec682850d29401899f83d6268",
        "license": "Apache-2.0",
        "integration_version": "0.1.8",
        "integration_wheel_sha256": (
            "d15840b7e4ce791c348e0e4ec366f05f221779df7a37815a6305b232b84e631f"
        ),
        "runtime_version": "3.3.6",
        "runtime_wheels": {
            "linux_aarch64_sha256": (
                "85e216a3b264a78693e11498d794c92dabdefaf55f78fa031dc834366f337a5b"
            ),
            "linux_x86_64_sha256": (
                "96405cd5095f51cbc69b565726a9938bf5cb6adc16d8834652be35e58586e483"
            ),
        },
    }:
        raise ValueError("Memori provider source contract drifted")
    for source_name, source in (("hermes", hermes), ("memori", memori)):
        _exact_sha(source["revision"], SHA40_RE, f"{source_name}.revision")
        _exact_sha(source["tree"], SHA40_RE, f"{source_name}.tree")
    _exact_sha(hermes["archive_sha256"], SHA256_RE, "hermes.archive_sha256")
    _exact_sha(
        memori["integration_wheel_sha256"],
        SHA256_RE,
        "memori.integration_wheel_sha256",
    )
    for platform_name, digest in memori["runtime_wheels"].items():
        _exact_sha(digest, SHA256_RE, f"memori.runtime_wheels.{platform_name}")

    providers = _mapping(payload, "providers")
    if providers.get("bundled") != EXPECTED_BUNDLED or providers.get("external") != {
        "memori": "package-tests-plus-real-hermes-install-and-discovery"
    }:
        raise ValueError("Hermes provider roster or evidence classes drifted")
    gates = _mapping(payload, "gates")
    if gates.get("exact_provider_roster") != EXPECTED_ROSTER or any(
        gates.get(field) is not True
        for field in (
            "every_provider_has_an_isolated_test_group",
            "memori_directory_install_and_memory_loader_discovery",
            "strict_hindsight_timeout_probe",
            "no_live_backend_claim_from_mock_or_fail_open_tests",
            "no_quality_claim_without_matched_tasks_and_actor",
        )
    ):
        raise ValueError("Hermes provider gates drifted")

    execution = _mapping(payload, "execution")
    expected_execution = {
        "container_required": True,
        "runtime_image": EXPECTED_IMAGE,
        "runtime_image_id": "sha256:" + EXPECTED_IMAGE.rsplit("sha256:", 1)[1],
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "sudo": "forbidden",
        "gpus": 0,
        "max_gpu_hours": 0,
        "cpu_time_limit_minutes": 15,
        "scheduler_required_for_model_calls": True,
        "model_compute": "h100-only",
    }
    if execution != expected_execution:
        raise ValueError("Hermes provider execution contract drifted")

    followup = _mapping(payload, "native_followup")
    if followup != {
        "local_first": ["holographic", "byterover"],
        "self_hosted": ["openviking", "mem0", "hindsight", "supermemory"],
        "credentialed_only_after_explicit_authority": ["honcho", "retaindb", "memori"],
        "lifecycle_protocol": "memory-lifecycle-v1",
        "h100_admission": "cpu-lifecycle-pass-required",
    }:
        raise ValueError("Hermes provider native follow-up contract drifted")
    forbidden = payload.get("forbidden_claims")
    if not isinstance(forbidden, list) or len(forbidden) != 5:
        raise ValueError("Hermes provider forbidden claims are incomplete")
    return payload, hashlib.sha256(encoded).hexdigest()


def validate_experiment_contract(path: Path) -> str:
    """Validate and return the exact registered experiment digest."""

    _, digest = load_and_validate_experiment(path)
    return digest
