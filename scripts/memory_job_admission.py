#!/usr/bin/env python3
"""Bind memory jobs to the validated source portfolio and killed revisions."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from scripts.validate_memory_portfolio import (
    DEFAULT_PORTFOLIO,
    assert_revision_admitted,
    load_and_validate_portfolio,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_memory_workload(command: list[str], *, has_memory_bundle: bool = False) -> bool:
    return has_memory_bundle or any(
        "memory" in Path(argument).name or argument.startswith("experiments/memory/")
        for argument in command
    )


def build_memory_job_admission(
    sources: Iterable[tuple[str, str]] = (),
) -> dict[str, Any]:
    """Build the exact current admission block for a compiler-produced job."""

    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    normalized = [
        {"source_id": source_id, "revision": revision}
        for source_id, revision in sources
    ]
    return {
        "scope": "external-sources" if normalized else "internal-cotcodec",
        "portfolio_sha256": _sha256_file(DEFAULT_PORTFOLIO),
        "matrix_sha256": result["matrix_sha256"],
        "sources": normalized,
    }


def validate_memory_job_admission(
    value: Any,
    *,
    command: list[str],
    has_memory_bundle: bool = False,
) -> dict[str, Any] | None:
    """Fail closed for every memory workload before it reaches Slurm."""

    memory_workload = is_memory_workload(command, has_memory_bundle=has_memory_bundle)
    if not memory_workload:
        if value is not None:
            raise ValueError("non-memory job cannot carry memory_source_admission")
        return None
    if not isinstance(value, dict):
        raise ValueError("memory workload requires memory_source_admission")
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    if value.get("portfolio_sha256") != _sha256_file(DEFAULT_PORTFOLIO):
        raise ValueError("memory source admission portfolio SHA-256 drifted")
    if value.get("matrix_sha256") != result["matrix_sha256"]:
        raise ValueError("memory source admission matrix SHA-256 drifted")
    scope = value.get("scope")
    sources = value.get("sources")
    if scope not in {"internal-cotcodec", "external-sources"}:
        raise ValueError("memory source admission scope is invalid")
    if not isinstance(sources, list):
        raise ValueError("memory source admission sources must be a list")
    if (scope == "internal-cotcodec") != (sources == []):
        raise ValueError("memory source admission scope and source roster disagree")
    ledger_sources = load_and_validate(DEFAULT_LEDGER)["sources"]
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"source_id", "revision"}:
            raise ValueError("memory source admission row is invalid")
        source_id = source.get("source_id")
        revision = source.get("revision")
        if not isinstance(source_id, str) or not isinstance(revision, str):
            raise ValueError("memory source admission identity is invalid")
        key = (source_id, revision)
        if key in seen:
            raise ValueError("memory source admission contains a duplicate revision")
        seen.add(key)
        ledger_entry = ledger_sources.get(source_id)
        if ledger_entry is None or revision not in {
            repository["revision"] for repository in ledger_entry.get("repositories", [])
        }:
            raise ValueError("memory source admission revision is absent from the ledger")
        assert_revision_admitted(result["portfolio"], source_id, revision)
        normalized.append({"source_id": source_id, "revision": revision})
    return {
        "scope": scope,
        "portfolio_sha256": value["portfolio_sha256"],
        "matrix_sha256": value["matrix_sha256"],
        "sources": normalized,
    }
