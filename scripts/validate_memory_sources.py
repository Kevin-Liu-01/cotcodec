#!/usr/bin/env python3
"""Validate the pinned primary-source ledger for agent-memory research."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from yaml.resolver import BaseResolver

if __package__:
    from scripts.seal_icarus_lifecycle_evidence import (
        EvidenceError as IcarusEvidenceError,
    )
    from scripts.seal_icarus_lifecycle_evidence import (
        validate_evidence as validate_icarus_evidence,
    )
    from scripts.seal_lightmem2_context_paging_evidence import (
        EvidenceError as LightMem2EvidenceError,
    )
    from scripts.seal_lightmem2_context_paging_evidence import (
        validate_evidence as validate_lightmem2_evidence,
    )
    from scripts.seal_memory_evidence import (
        PROVIDER_ROSTER,
        EvidenceError,
        validate_allmem_files,
        validate_astra_files,
        validate_byterover_files,
        validate_gaama_files,
        validate_gaama_natural_files,
        validate_graphiti_container_files,
        validate_hermes_files,
        validate_hindsight_files,
        validate_hippo_files,
        validate_holographic_files,
        validate_magic_context_files,
        validate_mem0_lifecycle_files,
        validate_neo4j_files,
        validate_openviking_files,
        validate_supermemory_files,
        validate_total_recall_files,
    )
    from scripts.seal_mnemon_active_space_evidence import (
        EvidenceError as MnemonEvidenceError,
    )
    from scripts.seal_mnemon_active_space_evidence import (
        validate_evidence as validate_mnemon_evidence,
    )
    from scripts.seal_mnemosyne_lifecycle_evidence import (
        EvidenceError as MnemosyneEvidenceError,
    )
    from scripts.seal_mnemosyne_lifecycle_evidence import (
        validate_evidence as validate_mnemosyne_evidence,
    )
    from scripts.seal_palimpsest_bitemporal_evidence import (
        EvidenceError as PalimpsestEvidenceError,
    )
    from scripts.seal_palimpsest_bitemporal_evidence import (
        validate_evidence as validate_palimpsest_evidence,
    )
    from scripts.seal_shodh_tier_evidence import EvidenceError as ShodhEvidenceError
    from scripts.seal_shodh_tier_evidence import (
        validate_evidence as validate_shodh_evidence,
    )
    from scripts.validate_activegraph_lifecycle_evidence import (
        ActiveGraphEvidenceError,
        validate_activegraph_lifecycle_evidence,
    )
    from scripts.validate_agent_recall_lifecycle_evidence import (
        AgentRecallEvidenceError,
        validate_agent_recall_lifecycle_evidence,
    )
    from scripts.validate_agenticow_lifecycle_evidence import (
        AgenticowEvidenceError,
        validate_agenticow_lifecycle_evidence,
    )
    from scripts.validate_gaama_h100_evidence import (
        GaamaH100EvidenceError,
        validate_gaama_h100_evidence,
    )
    from scripts.validate_lightmem_offline_evidence import (
        LightMemEvidenceError,
        validate_lightmem_offline_evidence,
    )
    from scripts.validate_memforge_fresh_install_evidence import (
        MemForgeEvidenceError,
        validate_memforge_fresh_install_evidence,
    )
    from scripts.validate_memoria_lifecycle_evidence import (
        MemoriaEvidenceError,
        validate_memoria_lifecycle_evidence,
    )
    from scripts.validate_memorybank_decay_evidence import (
        MemoryBankEvidenceError,
        validate_memorybank_decay_evidence,
    )
    from scripts.validate_memorybank_h100_evidence import (
        MemoryBankH100EvidenceError,
        validate_memorybank_h100_evidence,
    )
    from scripts.validate_mnemon_h100_evidence import (
        MnemonH100EvidenceError,
        validate_mnemon_h100_evidence,
    )
    from scripts.validate_mnemosyne_cognitive_evidence import (
        MnemosyneCognitiveEvidenceError,
        validate_mnemosyne_cognitive_evidence,
    )
    from scripts.validate_neo4j_flat_parity_evidence import (
        EvidenceError as Neo4jFlatParityEvidenceError,
    )
    from scripts.validate_neo4j_flat_parity_evidence import (
        validate_evidence as validate_neo4j_flat_parity_evidence,
    )
    from scripts.validate_neo4j_h100_evidence import (
        Neo4jH100EvidenceError,
        validate_neo4j_h100_evidence,
    )
    from scripts.validate_neo4j_natural_topology_evidence import (
        EvidenceError as NaturalTopologyEvidenceError,
    )
    from scripts.validate_neo4j_natural_topology_evidence import (
        validate_evidence as validate_natural_topology_evidence,
    )
    from scripts.validate_recmem_consolidation_evidence import (
        RecMemEvidenceError,
        validate_recmem_consolidation_evidence,
    )
    from scripts.validate_timem_core_evidence import (
        TiMemEvidenceError,
        validate_timem_core_evidence,
    )
    from scripts.validate_tokenmizer_checkpoint_evidence import (
        TokenMizerEvidenceError,
        validate_tokenmizer_checkpoint_evidence,
    )
else:
    from seal_icarus_lifecycle_evidence import (  # type: ignore[no-redef]
        EvidenceError as IcarusEvidenceError,
    )
    from seal_icarus_lifecycle_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_icarus_evidence,
    )
    from seal_lightmem2_context_paging_evidence import (  # type: ignore[no-redef]
        EvidenceError as LightMem2EvidenceError,
    )
    from seal_lightmem2_context_paging_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_lightmem2_evidence,
    )
    from seal_memory_evidence import (  # type: ignore[no-redef]
        PROVIDER_ROSTER,
        EvidenceError,
        validate_allmem_files,
        validate_astra_files,
        validate_byterover_files,
        validate_gaama_files,
        validate_gaama_natural_files,
        validate_graphiti_container_files,
        validate_hermes_files,
        validate_hindsight_files,
        validate_hippo_files,
        validate_holographic_files,
        validate_magic_context_files,
        validate_mem0_lifecycle_files,
        validate_neo4j_files,
        validate_openviking_files,
        validate_supermemory_files,
        validate_total_recall_files,
    )
    from seal_mnemon_active_space_evidence import (  # type: ignore[no-redef]
        EvidenceError as MnemonEvidenceError,
    )
    from seal_mnemon_active_space_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_mnemon_evidence,
    )
    from seal_mnemosyne_lifecycle_evidence import (  # type: ignore[no-redef]
        EvidenceError as MnemosyneEvidenceError,
    )
    from seal_mnemosyne_lifecycle_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_mnemosyne_evidence,
    )
    from seal_palimpsest_bitemporal_evidence import (  # type: ignore[no-redef]
        EvidenceError as PalimpsestEvidenceError,
    )
    from seal_palimpsest_bitemporal_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_palimpsest_evidence,
    )
    from seal_shodh_tier_evidence import (  # type: ignore[no-redef]
        EvidenceError as ShodhEvidenceError,
    )
    from seal_shodh_tier_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_shodh_evidence,
    )
    from validate_activegraph_lifecycle_evidence import (  # type: ignore[no-redef]
        ActiveGraphEvidenceError,
        validate_activegraph_lifecycle_evidence,
    )
    from validate_agent_recall_lifecycle_evidence import (  # type: ignore[no-redef]
        AgentRecallEvidenceError,
        validate_agent_recall_lifecycle_evidence,
    )
    from validate_agenticow_lifecycle_evidence import (  # type: ignore[no-redef]
        AgenticowEvidenceError,
        validate_agenticow_lifecycle_evidence,
    )
    from validate_gaama_h100_evidence import (  # type: ignore[no-redef]
        GaamaH100EvidenceError,
        validate_gaama_h100_evidence,
    )
    from validate_lightmem_offline_evidence import (  # type: ignore[no-redef]
        LightMemEvidenceError,
        validate_lightmem_offline_evidence,
    )
    from validate_memforge_fresh_install_evidence import (  # type: ignore[no-redef]
        MemForgeEvidenceError,
        validate_memforge_fresh_install_evidence,
    )
    from validate_memoria_lifecycle_evidence import (  # type: ignore[no-redef]
        MemoriaEvidenceError,
        validate_memoria_lifecycle_evidence,
    )
    from validate_memorybank_decay_evidence import (  # type: ignore[no-redef]
        MemoryBankEvidenceError,
        validate_memorybank_decay_evidence,
    )
    from validate_memorybank_h100_evidence import (  # type: ignore[no-redef]
        MemoryBankH100EvidenceError,
        validate_memorybank_h100_evidence,
    )
    from validate_mnemon_h100_evidence import (  # type: ignore[no-redef]
        MnemonH100EvidenceError,
        validate_mnemon_h100_evidence,
    )
    from validate_mnemosyne_cognitive_evidence import (  # type: ignore[no-redef]
        MnemosyneCognitiveEvidenceError,
        validate_mnemosyne_cognitive_evidence,
    )
    from validate_neo4j_flat_parity_evidence import (  # type: ignore[no-redef]
        EvidenceError as Neo4jFlatParityEvidenceError,
    )
    from validate_neo4j_flat_parity_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_neo4j_flat_parity_evidence,
    )
    from validate_neo4j_h100_evidence import (  # type: ignore[no-redef]
        Neo4jH100EvidenceError,
        validate_neo4j_h100_evidence,
    )
    from validate_neo4j_natural_topology_evidence import (  # type: ignore[no-redef]
        EvidenceError as NaturalTopologyEvidenceError,
    )
    from validate_neo4j_natural_topology_evidence import (  # type: ignore[no-redef]
        validate_evidence as validate_natural_topology_evidence,
    )
    from validate_recmem_consolidation_evidence import (  # type: ignore[no-redef]
        RecMemEvidenceError,
        validate_recmem_consolidation_evidence,
    )
    from validate_timem_core_evidence import (  # type: ignore[no-redef]
        TiMemEvidenceError,
        validate_timem_core_evidence,
    )
    from validate_tokenmizer_checkpoint_evidence import (  # type: ignore[no-redef]
        TokenMizerEvidenceError,
        validate_tokenmizer_checkpoint_evidence,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = PROJECT_ROOT / "research" / "memory-sources.yaml"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EVIDENCE_GRADES = {
    "mechanism-only",
    "paper-reported",
    "vendor-reported",
    "open-harness-reported",
    "externally-reproduced",
    "local-reproduced",
    "local-conformance-reproduced",
    "local-negative-reproduced",
}
RECEIPT_GRADES = {
    "externally-reproduced",
    "local-reproduced",
    "local-conformance-reproduced",
    "local-negative-reproduced",
}
SCIENTIFIC_REPRODUCED_GRADES = {"externally-reproduced", "local-reproduced"}
RESIDENCY_TRANSITIONS = {
    "not-reviewed",
    "none",
    "bidirectional-residency",
    "active-to-inactive",
    "inactive-to-active",
    "manual-promotion",
    "chronological-context-paging",
    "one-way-consolidation",
    "representation-only",
    "separate-stores-no-transition",
}
GRAPH_SEMANTICS = {"none", "generic", "temporal-validity", "causal", "multi-graph"}


class MemorySourceError(ValueError):
    """Raised when the memory-source ledger violates its evidence contract."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses silent mapping-key overwrites."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise MemorySourceError(f"unhashable YAML mapping key: {key!r}") from exc
        if duplicate:
            raise MemorySourceError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_unique_yaml(path: Path) -> Any:
    """Load one YAML document while refusing silent duplicate mapping keys."""

    return yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)


def _require_text(entry_id: str, entry: dict[str, Any], field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MemorySourceError(f"{entry_id}: {field} must be a non-empty string")
    return value


def _require_string_list(entry_id: str, entry: dict[str, Any], field: str) -> list[str]:
    value = entry.get(field)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise MemorySourceError(f"{entry_id}: {field} must be a non-empty string list")
    return value


def _validate_url(entry_id: str, field: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise MemorySourceError(f"{entry_id}: {field} must be an https URL")


def _validate_embedded_files(
    entry_id: str,
    files: Any,
    *,
    owner: str,
) -> dict[str, bytes]:
    if not isinstance(files, dict) or not files:
        raise MemorySourceError(f"{entry_id}: {owner} files must be a non-empty mapping")
    decoded: dict[str, bytes] = {}
    for name, receipt in files.items():
        if (
            not isinstance(name, str)
            or not name
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or not isinstance(receipt, dict)
        ):
            raise MemorySourceError(f"{entry_id}: {owner} contains an unsafe file")
        try:
            if receipt.get("encoding") == "gzip":
                if "content_base64" in receipt:
                    raise ValueError("compressed receipt also has plain content")
                compressed = base64.b64decode(
                    receipt.get("content_gzip_base64", ""), validate=True
                )
                data = gzip.decompress(compressed)
            else:
                if "content_gzip_base64" in receipt or "encoding" in receipt:
                    raise ValueError("plain receipt has compressed fields")
                data = base64.b64decode(
                    receipt.get("content_base64", ""), validate=True
                )
        except (ValueError, TypeError, gzip.BadGzipFile) as exc:
            raise MemorySourceError(
                f"{entry_id}: {owner} file {name} has invalid encoding"
            ) from exc
        if receipt.get("bytes") != len(data):
            raise MemorySourceError(
                f"{entry_id}: {owner} file {name} byte count drifted"
            )
        if receipt.get("sha256") != hashlib.sha256(data).hexdigest():
            raise MemorySourceError(
                f"{entry_id}: {owner} file {name} SHA-256 drifted"
            )
        decoded[name] = data
    return decoded


def _validate_local_evidence_bundle(
    entry_id: str,
    entry: dict[str, Any],
    artifact_bytes: bytes,
) -> None:
    try:
        bundle = json.loads(artifact_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MemorySourceError(f"{entry_id}: local evidence bundle is invalid JSON") from exc
    if not isinstance(bundle, dict) or bundle.get("schema_version") != 1:
        raise MemorySourceError(f"{entry_id}: local evidence bundle schema drifted")
    if bundle.get("source_id") != entry_id:
        raise MemorySourceError(f"{entry_id}: local evidence source_id drifted")
    if bundle.get("evidence_grade") != entry["evidence_grade"]:
        raise MemorySourceError(f"{entry_id}: local evidence grade drifted")
    if bundle.get("scientific_result") is not False:
        raise MemorySourceError(
            f"{entry_id}: conformance/negative evidence cannot be a scientific result"
        )
    expected_revisions = {
        repository["url"].rstrip("/"): repository["revision"]
        for repository in entry.get("repositories", [])
    }
    if bundle.get("source_revisions") != expected_revisions:
        raise MemorySourceError(f"{entry_id}: local evidence source revisions drifted")
    if entry["evidence_grade"] == "local-negative-reproduced":
        if entry_id == "memorybank-siliconfriend":
            try:
                validate_memorybank_h100_evidence(bundle, project_root=PROJECT_ROOT)
            except MemoryBankH100EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "icarus-memory-infra":
            try:
                validate_icarus_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except IcarusEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "lightmem2":
            try:
                validate_lightmem2_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except LightMem2EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "shodh-memory":
            try:
                validate_shodh_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except ShodhEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "mnemosyne-oss":
            try:
                validate_mnemosyne_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except MnemosyneEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "palimpsest-bitemporal-memory":
            try:
                validate_palimpsest_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except PalimpsestEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "longmemeval-natural-session-topology":
            try:
                validate_natural_topology_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except NaturalTopologyEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "mnemon":
            try:
                validate_mnemon_h100_evidence(bundle, project_root=PROJECT_ROOT)
            except MnemonH100EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "recmem":
            try:
                validate_recmem_consolidation_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except RecMemEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "lightmem":
            try:
                validate_lightmem_offline_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except LightMemEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "memoria-matrixorigin":
            try:
                validate_memoria_lifecycle_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except MemoriaEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "agent-recall":
            try:
                validate_agent_recall_lifecycle_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except AgentRecallEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "activegraph-event-sourced-runtime":
            try:
                validate_activegraph_lifecycle_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except ActiveGraphEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "agenticow":
            try:
                validate_agenticow_lifecycle_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except AgenticowEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "tokenmizer":
            try:
                validate_tokenmizer_checkpoint_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except TokenMizerEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "timem":
            try:
                validate_timem_core_evidence(bundle, project_root=PROJECT_ROOT)
            except TiMemEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "gaama":
            try:
                validate_gaama_h100_evidence(bundle, project_root=PROJECT_ROOT)
            except GaamaH100EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "hermes-observational-memory":
            if (
                bundle.get("evidence_kind")
                != "standalone-hermes-provider-lifecycle-negative"
                or bundle.get("publication_ready") is not False
                or bundle.get("status")
                != "BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE"
                or bundle.get("run_count") != 2
                or bundle.get("runtime_lane")
                != "docker-under-slurm-h100-allocation-no-container-gpu"
                or bundle.get("claim_boundary")
                != {
                    "h100_actor_admission": "forbidden-for-this-revision",
                    "memory_quality_evaluated": False,
                    "native_deletion_evaluated": True,
                    "operator_root_deletion_is_native_erasure": False,
                }
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle negative evidence contract drifted"
                )

            artifact_root_value = bundle.get("artifact_root")
            if (
                not isinstance(artifact_root_value, str)
                or not artifact_root_value
                or Path(artifact_root_value).is_absolute()
                or ".." in Path(artifact_root_value).parts
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle artifact root is unsafe"
                )
            artifact_root = PROJECT_ROOT / artifact_root_value
            expected_files = bundle.get("artifact_files")
            if not isinstance(expected_files, dict) or set(expected_files) != {
                "gpu-inventory-291.txt",
                "image-inspect-291.json",
                "job-291.receipt.json",
                "lifecycle-291/manifest.json",
                "lifecycle-291/report.json",
                "sbom-291/sbom.spdx.json",
                "source-receipt.json",
            }:
                raise MemorySourceError(
                    f"{entry_id}: lifecycle artifact roster drifted"
                )
            artifact_bytes: dict[str, bytes] = {}
            for name, expected_sha256 in expected_files.items():
                path = artifact_root / name
                if (
                    not isinstance(expected_sha256, str)
                    or not SHA256_RE.fullmatch(expected_sha256)
                    or not path.is_file()
                    or path.is_symlink()
                ):
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle artifact {name} is invalid"
                    )
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != expected_sha256:
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle artifact {name} drifted"
                    )
                artifact_bytes[name] = data

            try:
                report = json.loads(artifact_bytes["lifecycle-291/report.json"])
                manifest = json.loads(artifact_bytes["lifecycle-291/manifest.json"])
                job = json.loads(artifact_bytes["job-291.receipt.json"])
                source = json.loads(artifact_bytes["source-receipt.json"])
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise MemorySourceError(
                    f"{entry_id}: lifecycle artifact JSON is invalid"
                ) from exc

            if (
                report.get("status") != bundle["status"]
                or report.get("scientific_result") is not False
                or report.get("publication_ready") is not False
                or report.get("repeat_count") != 2
                or report.get("two_repetition_semantic_projection_match") is not True
                or report.get("explicit_note_restart_persistence") is not True
                or report.get("separate_memory_root_isolation") is not True
                or report.get("operator_scoped_root_purge") is not True
                or report.get("provider_native_delete_or_forget_tool") is not False
                or report.get("provider_native_physical_erasure_contract") is not False
                or report.get("h100_actor_admission")
                != "forbidden-for-this-revision"
                or [item.get("projection_sha256") for item in report.get("repeats", [])]
                != bundle.get("projection_sha256s")
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle report semantics drifted"
                )

            manifest_files = manifest.get("files")
            if not isinstance(manifest_files, list) or len(manifest_files) != 26:
                raise MemorySourceError(
                    f"{entry_id}: lifecycle manifest roster drifted"
                )
            seen: set[str] = set()
            lifecycle_root = artifact_root / "lifecycle-291"
            for row in manifest_files:
                if not isinstance(row, dict) or set(row) != {"bytes", "path", "sha256"}:
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle manifest row is invalid"
                    )
                name = row["path"]
                if (
                    not isinstance(name, str)
                    or not name
                    or Path(name).is_absolute()
                    or ".." in Path(name).parts
                    or name in seen
                ):
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle manifest path is unsafe"
                    )
                seen.add(name)
                path = lifecycle_root / name
                if not path.is_file() or path.is_symlink():
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle manifest file is missing"
                    )
                data = path.read_bytes()
                if (
                    row["bytes"] != len(data)
                    or row["sha256"] != hashlib.sha256(data).hexdigest()
                ):
                    raise MemorySourceError(
                        f"{entry_id}: lifecycle manifest content drifted"
                    )
            if (
                manifest.get("report_sha256")
                != expected_files["lifecycle-291/report.json"]
                or job.get("schema_version") != 1
                or job.get("slurm_job_id") != bundle.get("slurm_job_id")
                or job.get("report_sha256") != manifest.get("report_sha256")
                or job.get("image_id") != bundle.get("image_id")
                or job.get("image_archive_sha256")
                != bundle.get("image_archive_sha256")
                or job.get("sbom_sha256")
                != expected_files["sbom-291/sbom.spdx.json"]
                or job.get("gpu_inventory_sha256")
                != expected_files["gpu-inventory-291.txt"]
                or job.get("image_inspect_sha256")
                != expected_files["image-inspect-291.json"]
                or source.get("archive_sha256") != bundle.get("source_archive_sha256")
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle provenance binding drifted"
                )
            source_archive_value = bundle.get("source_archive_path")
            if (
                not isinstance(source_archive_value, str)
                or not source_archive_value
                or Path(source_archive_value).is_absolute()
                or ".." in Path(source_archive_value).parts
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle source archive path is unsafe"
                )
            source_archive = PROJECT_ROOT / source_archive_value
            if (
                not source_archive.is_file()
                or source_archive.is_symlink()
                or hashlib.sha256(source_archive.read_bytes()).hexdigest()
                != bundle.get("source_archive_sha256")
            ):
                raise MemorySourceError(
                    f"{entry_id}: lifecycle source archive drifted"
                )
            return
        if entry_id == "supermemory":
            if (
                bundle.get("evidence_kind")
                != "binary-only-native-negative-reproduction"
                or bundle.get("publication_ready") is not False
                or bundle.get("run_count") != 2
                or bundle.get("claim_boundary")
                != {
                    "binary_only": True,
                    "h100_admission": "forbidden-for-this-release",
                    "local_server_source_available": False,
                    "release_revision": (
                        "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d"
                    ),
                }
            ):
                raise MemorySourceError(
                    f"{entry_id}: binary-only negative evidence contract drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="files"
            )
            try:
                verified = validate_supermemory_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: Supermemory evidence receipt drifted"
                )
            return
        if (
            bundle.get("evidence_kind") != "native-negative-reproduction"
            or bundle.get("publication_ready") is not False
            or bundle.get("run_count") != 2
        ):
            raise MemorySourceError(f"{entry_id}: negative evidence contract drifted")
        if entry_id == "hippo-memory":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_hippo_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
            ):
                raise MemorySourceError(f"{entry_id}: Hippo evidence receipt drifted")
            return
        if entry_id == "all-mem":
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="files"
            )
            try:
                verified = validate_allmem_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_semantic_projection_sha256")
                != verified["stable_semantic_projection_sha256"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identity_sha256s"]
                or bundle.get("observed_rank_orders")
                != verified["observed_rank_orders"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: All-Mem evidence receipt drifted"
                )
            return
        if entry_id == "magic-context":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_magic_context_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: Magic Context evidence receipt drifted"
                )
            return
        if entry_id == "hermes-holographic":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_holographic_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: Holographic evidence receipt drifted"
                )
            return
        if entry_id == "hermes-byterover-cli":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_byterover_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: ByteRover evidence receipt drifted"
                )
            return
        if entry_id == "openviking":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_openviking_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("image_ids") != verified["image_ids"]
                or bundle.get("operation_count") != verified["operation_count"]
                or bundle.get("state_manifest_sha256s")
                != verified["state_manifest_sha256s"]
                or bundle.get("residue_file_counts")
                != verified["residue_file_counts"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identity_sha256s"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: OpenViking evidence receipt drifted"
                )
            return
        if entry_id == "hermes-hindsight-native":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_hindsight_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("image_ids") != verified["image_ids"]
                or bundle.get("operation_count") != verified["operation_count"]
                or bundle.get("state_manifest_sha256s")
                != verified["state_manifest_sha256s"]
                or bundle.get("residue_file_counts")
                != verified["residue_file_counts"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identity_sha256s"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: Hindsight evidence receipt drifted"
                )
            return
        if entry_id == "mem0-lifecycle-adapter":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_mem0_lifecycle_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("status") != "BLOCKED_ADAPTER_CRASH_RECOVERY"
                or bundle.get("h100_admission") != "blocked"
                or bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("stable_projection") != verified["stable_projection"]
                or bundle.get("stable_projection_sha256")
                != verified["stable_projection_sha256"]
                or bundle.get("report_sha256s") != verified["report_sha256s"]
                or bundle.get("source_receipt_sha256")
                != verified["source_receipt_sha256"]
                or bundle.get("crash_scope_plaintext_proof_roots")
                != verified["crash_scope_plaintext_proof_roots"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: Mem0 lifecycle evidence receipt drifted"
                )
            return
        if entry_id == "graphiti-native-lifecycle-adapter":
            files = _validate_embedded_files(entry_id, bundle.get("files"), owner="files")
            try:
                verified = validate_graphiti_container_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("status")
                != "BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH"
                or bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
                or bundle.get("module_architecture")
                != verified["module_architecture"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
                or bundle.get("claim_boundary")
                != {
                    "container_lifecycle_executed": False,
                    "h100_admission": "forbidden-for-this-revision-and-runtime",
                    "reason": (
                        "BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH"
                    ),
                }
            ):
                raise MemorySourceError(
                    f"{entry_id}: Graphiti negative evidence receipt drifted"
                )
            return
        if entry_id == "mnemosyne-cognitive-os":
            try:
                validate_mnemosyne_cognitive_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except MnemosyneCognitiveEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        if entry_id == "memforge":
            try:
                validate_memforge_fresh_install_evidence(
                    bundle, project_root=PROJECT_ROOT
                )
            except MemForgeEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            return
        runs = bundle.get("runs")
        if not isinstance(runs, list) or [run.get("role") for run in runs] != [
            "primary",
            "replication",
        ]:
            raise MemorySourceError(f"{entry_id}: negative evidence run roster drifted")
        execution_identities: set[str] = set()
        for index, run in enumerate(runs):
            if not isinstance(run, dict):
                raise MemorySourceError(f"{entry_id}: negative evidence run is invalid")
            files = _validate_embedded_files(
                entry_id, run.get("files"), owner=f"runs[{index}]"
            )
            try:
                verified = validate_total_recall_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                run.get("manifest_file_sha256")
                != hashlib.sha256(files["manifest.json"]).hexdigest()
                or run.get("manifest_root_sha256") != verified["manifest_root"]
                or run.get("execution_identity_sha256")
                != verified["execution_identity_sha256"]
                or verified["image_id"] != bundle.get("shared_image_id")
                or verified["projection"] != bundle.get("deterministic_projection")
            ):
                raise MemorySourceError(
                    f"{entry_id}: embedded negative semantic receipt drifted"
                )
            execution_identities.add(verified["execution_identity_sha256"])
        if len(execution_identities) != 2:
            raise MemorySourceError(
                f"{entry_id}: negative evidence must bind two distinct executions"
            )
    elif entry["evidence_grade"] == "local-conformance-reproduced":
        evidence_kind = bundle.get("evidence_kind")
        if evidence_kind == "native-control-admission":
            if entry_id != "mnemon":
                raise MemorySourceError(
                    f"{entry_id}: active-space admission source identity drifted"
                )
            try:
                validate_mnemon_evidence(
                    PROJECT_ROOT / entry["reproduction_receipt"]["artifact_path"]
                )
            except MnemonEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
        elif evidence_kind == "provider-conformance-reproduction":
            if (
                entry_id != "hermes-provider-conformance"
                or bundle.get("status") != "FAIL"
                or bundle.get("publication_ready") is not False
                or bundle.get("canonical_generation") != "v2"
            ):
                raise MemorySourceError(
                    f"{entry_id}: provider conformance evidence contract drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="bundle"
            )
            try:
                verified = validate_hermes_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("provider_roster") != PROVIDER_ROSTER
                or bundle.get("failed_groups") != verified["failed_groups"]
                or bundle.get("result_status") != verified["result_status"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: provider conformance result identity drifted"
                )
        elif evidence_kind == "native-lifecycle-conformance-reproduction":
            if (
                entry_id != "neo4j-agent-memory"
                or bundle.get("status")
                != "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS"
                or bundle.get("publication_ready") is not False
                or bundle.get("runtime_lane") != "local-arm64"
                or bundle.get("confirmation_required") is not True
                or bundle.get("run_count") != 2
            ):
                raise MemorySourceError(
                    f"{entry_id}: native lifecycle conformance contract drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="bundle"
            )
            try:
                verified = validate_neo4j_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("semantic_projection")
                != verified["semantic_projection"]
                or bundle.get("execution_state_roots")
                != verified["execution_state_roots"]
                or bundle.get("client_image_id") != verified["client_image_id"]
                or bundle.get("manifest_root_sha256")
                != verified["manifest_root"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: native lifecycle result identity drifted"
                )
        elif evidence_kind == "natural-heldout-component-reproduction":
            if (
                entry_id != "gaama"
                or bundle.get("status") != "GAAMA_NATURAL_GRAPH_PASS"
                or bundle.get("publication_ready") is not False
                or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
                or bundle.get("run_count") != 2
                or bundle.get("dataset")
                != {
                    "name": "LoCoMo-10",
                    "sha256": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
                    "license": "CC-BY-NC-4.0",
                }
            ):
                raise MemorySourceError(
                    f"{entry_id}: natural component evidence contract drifted"
                )
            prior = bundle.get("prior_component_receipt")
            prior_path = PROJECT_ROOT / "research/evidence/memory/gaama-graph-component-v1.json"
            if (
                prior
                != {
                    "artifact_path": "research/evidence/memory/gaama-graph-component-v1.json",
                    "sha256": "cf903e2bb8444e84d13ef63a13029dc8efc0ed0fea51676a317dbbb9a8d96726",
                }
                or not prior_path.is_file()
                or hashlib.sha256(prior_path.read_bytes()).hexdigest() != prior["sha256"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: prior component evidence receipt drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="bundle"
            )
            try:
                verified = validate_gaama_natural_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("outcome") != verified["outcome"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
                or bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256") != verified["manifest_root"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: natural component result identity drifted"
                )
        elif evidence_kind == "matched-component-conformance-reproduction":
            if (
                entry_id != "gaama"
                or bundle.get("status") != "GAAMA_COMPONENT_CONTRACT_PASS"
                or bundle.get("publication_ready") is not False
                or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
                or bundle.get("run_count") != 2
            ):
                raise MemorySourceError(
                    f"{entry_id}: matched component conformance contract drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="bundle"
            )
            try:
                verified = validate_gaama_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("component_summary") != verified["component_summary"]
                or bundle.get("execution_identity_sha256s")
                != verified["execution_identities"]
                or bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("manifest_root_sha256")
                != verified["manifest_root"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: matched component result identity drifted"
                )
        elif evidence_kind == "active-working-set-component-conformance-reproduction":
            if (
                entry_id != "astra-working-set"
                or bundle.get("status")
                != "ASTRA_WORKING_SET_COMPONENT_CONFORMANCE_PASS"
                or bundle.get("publication_ready") is not False
                or bundle.get("runtime_lane")
                != "local-arm64-docker-network-none"
                or bundle.get("run_count") != 2
                or bundle.get("claim_boundary")
                != {
                    "component_tests_reproduced": True,
                    "cockroachdb_lifecycle_executed": False,
                    "durable_repromotion_executed": False,
                    "actor_quality_evaluated": False,
                    "h100_admission": (
                        "requires-native-lifecycle-and-matched-freeze-first"
                    ),
                }
            ):
                raise MemorySourceError(
                    f"{entry_id}: ASTRA component conformance contract drifted"
                )
            files = _validate_embedded_files(
                entry_id, bundle.get("files"), owner="bundle"
            )
            try:
                verified = validate_astra_files(files)
            except EvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
            if (
                bundle.get("shared_image_id") != verified["image_id"]
                or bundle.get("shared_image_digest") != verified["image_digest"]
                or bundle.get("test_projection_sha256")
                != verified["projection_sha256"]
                or bundle.get("raw_run_sha256s") != verified["run_sha256s"]
            ):
                raise MemorySourceError(
                    f"{entry_id}: ASTRA component result identity drifted"
                )
        elif evidence_kind == "clean-room-mechanism-control-conformance":
            if entry_id != "memorybank-siliconfriend":
                raise MemorySourceError(
                    f"{entry_id}: clean-room mechanism evidence identity drifted"
                )
            try:
                validate_memorybank_decay_evidence(
                    bundle,
                    project_root=PROJECT_ROOT,
                )
            except MemoryBankEvidenceError as exc:
                raise MemorySourceError(f"{entry_id}: {exc}") from exc
        else:
            raise MemorySourceError(
                f"{entry_id}: unknown conformance evidence kind {evidence_kind!r}"
            )


def validate_source(
    entry_id: str,
    entry: dict[str, Any],
    *,
    allowed_layers: set[str],
) -> None:
    if not ID_RE.fullmatch(entry_id):
        raise MemorySourceError(f"invalid source id: {entry_id!r}")
    if not isinstance(entry, dict):
        raise MemorySourceError(f"{entry_id}: source must be a mapping")

    for field in ("kind", "title", "mechanism"):
        _require_text(entry_id, entry, field)
    observed_on = _require_text(entry_id, entry, "observed_on")
    if not DATE_RE.fullmatch(observed_on):
        raise MemorySourceError(f"{entry_id}: observed_on must use YYYY-MM-DD")

    primary_sources = _require_string_list(entry_id, entry, "primary_sources")
    for index, url in enumerate(primary_sources):
        _validate_url(entry_id, f"primary_sources[{index}]", url)

    layers = set(_require_string_list(entry_id, entry, "memory_layers"))
    unknown_layers = layers - allowed_layers
    if unknown_layers:
        raise MemorySourceError(
            f"{entry_id}: unknown memory_layers {sorted(unknown_layers)}"
        )
    residency_transition = entry.get("residency_transition", "not-reviewed")
    if residency_transition not in RESIDENCY_TRANSITIONS:
        raise MemorySourceError(
            f"{entry_id}: unknown residency_transition {residency_transition!r}"
        )
    graph_semantics = entry.get(
        "graph_semantics", "generic" if "temporal_graph" in layers else "none"
    )
    if graph_semantics not in GRAPH_SEMANTICS:
        raise MemorySourceError(
            f"{entry_id}: unknown graph_semantics {graph_semantics!r}"
        )
    if graph_semantics != "none" and "temporal_graph" not in layers:
        raise MemorySourceError(
            f"{entry_id}: graph_semantics requires temporal_graph memory layer"
        )
    _require_string_list(entry_id, entry, "use_as")
    _require_string_list(entry_id, entry, "limitations")

    evidence_grade = _require_text(entry_id, entry, "evidence_grade")
    if evidence_grade not in EVIDENCE_GRADES:
        raise MemorySourceError(f"{entry_id}: unknown evidence_grade {evidence_grade!r}")
    if evidence_grade in RECEIPT_GRADES:
        reproduction = entry.get("reproduction_receipt")
        if not isinstance(reproduction, dict):
            raise MemorySourceError(
                f"{entry_id}: reproduced source requires reproduction_receipt"
            )
        receipt_sha256 = reproduction.get("receipt_sha256")
        if not isinstance(receipt_sha256, str) or not SHA256_RE.fullmatch(
            receipt_sha256
        ):
            raise MemorySourceError(
                f"{entry_id}: reproduction_receipt.receipt_sha256 must be SHA-256"
            )
        artifact_path = reproduction.get("artifact_path")
        receipt_url = reproduction.get("receipt_url")
        if bool(artifact_path) == bool(receipt_url):
            raise MemorySourceError(
                f"{entry_id}: reproduction_receipt requires exactly one "
                "artifact_path or receipt_url"
            )
        if artifact_path:
            if (
                not isinstance(artifact_path, str)
                or Path(artifact_path).is_absolute()
                or ".." in Path(artifact_path).parts
            ):
                raise MemorySourceError(
                    f"{entry_id}: reproduction artifact_path must be safe and relative"
                )
            artifact = PROJECT_ROOT / artifact_path
            if not artifact.is_file() or artifact.is_symlink():
                raise MemorySourceError(
                    f"{entry_id}: reproduction artifact is missing or not regular"
                )
            artifact_bytes = artifact.read_bytes()
            if hashlib.sha256(artifact_bytes).hexdigest() != receipt_sha256:
                raise MemorySourceError(
                    f"{entry_id}: reproduction artifact SHA-256 does not match receipt"
                )
            if evidence_grade in {
                "local-conformance-reproduced",
                "local-negative-reproduced",
            }:
                _validate_local_evidence_bundle(entry_id, entry, artifact_bytes)
        else:
            if not isinstance(receipt_url, str):
                raise MemorySourceError(
                    f"{entry_id}: reproduction receipt_url must be a string"
                )
            _validate_url(entry_id, "reproduction_receipt.receipt_url", receipt_url)

    cluster_confirmation = entry.get("cluster_confirmation_receipt")
    if entry_id == "neo4j-agent-memory":
        if not isinstance(cluster_confirmation, dict):
            raise MemorySourceError(
                "neo4j-agent-memory: cluster confirmation receipt is required"
            )
        artifact_path = cluster_confirmation.get("artifact_path")
        receipt_sha256 = cluster_confirmation.get("receipt_sha256")
        if (
            not isinstance(artifact_path, str)
            or Path(artifact_path).is_absolute()
            or ".." in Path(artifact_path).parts
            or not isinstance(receipt_sha256, str)
            or not SHA256_RE.fullmatch(receipt_sha256)
        ):
            raise MemorySourceError(
                "neo4j-agent-memory: cluster confirmation receipt is invalid"
            )
        artifact = PROJECT_ROOT / artifact_path
        if not artifact.is_file() or artifact.is_symlink():
            raise MemorySourceError(
                "neo4j-agent-memory: cluster confirmation artifact is missing"
            )
        artifact_bytes = artifact.read_bytes()
        if hashlib.sha256(artifact_bytes).hexdigest() != receipt_sha256:
            raise MemorySourceError(
                "neo4j-agent-memory: cluster confirmation SHA-256 drifted"
            )
        try:
            confirmation_bundle = json.loads(artifact_bytes)
            if not isinstance(confirmation_bundle, dict):
                raise TypeError
            validate_neo4j_h100_evidence(
                confirmation_bundle, project_root=PROJECT_ROOT
            )
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise MemorySourceError(
                "neo4j-agent-memory: cluster confirmation is invalid JSON"
            ) from exc
        except Neo4jH100EvidenceError as exc:
            raise MemorySourceError(f"neo4j-agent-memory: {exc}") from exc
        component_receipt = entry.get("cluster_component_receipt")
        if not isinstance(component_receipt, dict):
            raise MemorySourceError(
                "neo4j-agent-memory: cluster component receipt is required"
            )
        component_path = component_receipt.get("artifact_path")
        component_sha256 = component_receipt.get("receipt_sha256")
        if (
            not isinstance(component_path, str)
            or Path(component_path).is_absolute()
            or ".." in Path(component_path).parts
            or not isinstance(component_sha256, str)
            or not SHA256_RE.fullmatch(component_sha256)
        ):
            raise MemorySourceError(
                "neo4j-agent-memory: cluster component receipt is invalid"
            )
        component_artifact = PROJECT_ROOT / component_path
        if component_artifact.is_symlink() or not component_artifact.is_file():
            raise MemorySourceError(
                "neo4j-agent-memory: cluster component artifact is missing"
            )
        if hashlib.sha256(component_artifact.read_bytes()).hexdigest() != component_sha256:
            raise MemorySourceError(
                "neo4j-agent-memory: cluster component SHA-256 drifted"
            )
        try:
            validate_neo4j_flat_parity_evidence(component_artifact)
        except Neo4jFlatParityEvidenceError as exc:
            raise MemorySourceError(f"neo4j-agent-memory: {exc}") from exc
    elif cluster_confirmation is not None:
        raise MemorySourceError(
            f"{entry_id}: unexpected cluster_confirmation_receipt"
        )
    elif entry.get("cluster_component_receipt") is not None:
        raise MemorySourceError(
            f"{entry_id}: unexpected cluster_component_receipt"
        )

    repositories = entry.get("repositories", [])
    if not isinstance(repositories, list):
        raise MemorySourceError(f"{entry_id}: repositories must be a list")
    for index, repository in enumerate(repositories):
        if not isinstance(repository, dict):
            raise MemorySourceError(f"{entry_id}: repositories[{index}] must be a mapping")
        for field in ("role", "url", "license"):
            _require_text(f"{entry_id}.repositories[{index}]", repository, field)
        _validate_url(entry_id, f"repositories[{index}].url", repository["url"])
        repository_url = repository["url"].rstrip("/")
        if not any(
            source_url.rstrip("/") == repository_url
            or source_url.startswith(f"{repository_url}/")
            for source_url in primary_sources
        ):
            raise MemorySourceError(
                f"{entry_id}: repositories[{index}].url must be bound by primary_sources"
            )
        revision = repository.get("revision")
        if not isinstance(revision, str) or not COMMIT_RE.fullmatch(revision):
            raise MemorySourceError(
                f"{entry_id}: repositories[{index}].revision must be a 40-char commit"
            )

    artifacts = entry.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise MemorySourceError(f"{entry_id}: artifacts must be a list")
    for index, artifact in enumerate(artifacts):
        artifact_id = f"{entry_id}.artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise MemorySourceError(f"{artifact_id} must be a mapping")
        for field in ("role", "url", "revision", "filename", "sha256", "license"):
            _require_text(artifact_id, artifact, field)
        _validate_url(entry_id, f"artifacts[{index}].url", artifact["url"])
        if not COMMIT_RE.fullmatch(artifact["revision"]):
            raise MemorySourceError(
                f"{artifact_id}.revision must be a 40-char immutable revision"
            )
        if not SHA256_RE.fullmatch(artifact["sha256"]):
            raise MemorySourceError(f"{artifact_id}.sha256 must be lowercase SHA-256")
        size = artifact.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise MemorySourceError(f"{artifact_id}.size must be a positive integer")

    claims = entry.get("benchmark_claims", [])
    if not isinstance(claims, list):
        raise MemorySourceError(f"{entry_id}: benchmark_claims must be a list")
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise MemorySourceError(f"{entry_id}: benchmark_claims[{index}] must be a mapping")
        for field in ("benchmark", "result", "source_url", "evidence_grade"):
            _require_text(f"{entry_id}.benchmark_claims[{index}]", claim, field)
        _validate_url(entry_id, f"benchmark_claims[{index}].source_url", claim["source_url"])
        if claim["evidence_grade"] not in EVIDENCE_GRADES - {"mechanism-only"}:
            raise MemorySourceError(
                f"{entry_id}: benchmark_claims[{index}] has invalid evidence_grade"
            )
        if claim["evidence_grade"] in {"externally-reproduced", "local-reproduced"}:
            reproduction = claim.get("reproduction_url") or claim.get("artifact_path")
            if not isinstance(reproduction, str) or not reproduction.strip():
                raise MemorySourceError(
                    f"{entry_id}: reproduced claim requires reproduction_url or artifact_path"
                )


def load_and_validate(path: Path = DEFAULT_LEDGER) -> dict[str, Any]:
    payload = load_unique_yaml(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise MemorySourceError("ledger must be a schema_version: 1 mapping")
    verified_at = payload.get("verified_at")
    if not isinstance(verified_at, str) or not DATE_RE.fullmatch(verified_at):
        raise MemorySourceError("verified_at must use YYYY-MM-DD")
    vocabulary = payload.get("controlled_vocabulary")
    if not isinstance(vocabulary, dict):
        raise MemorySourceError("controlled_vocabulary must be a mapping")
    allowed_layers_raw = vocabulary.get("memory_layers")
    if not isinstance(allowed_layers_raw, list) or not allowed_layers_raw:
        raise MemorySourceError("controlled_vocabulary.memory_layers must be non-empty")
    allowed_layers = set(allowed_layers_raw)
    if not all(isinstance(layer, str) and layer for layer in allowed_layers):
        raise MemorySourceError("controlled_vocabulary.memory_layers must contain strings")
    evidence_grades = vocabulary.get("evidence_grades")
    if not isinstance(evidence_grades, list) or set(evidence_grades) != EVIDENCE_GRADES:
        raise MemorySourceError(
            "controlled_vocabulary.evidence_grades must exactly match validator grades"
        )
    definitions = vocabulary.get("evidence_grade_definitions")
    if not isinstance(definitions, dict) or set(definitions) != EVIDENCE_GRADES:
        raise MemorySourceError(
            "controlled_vocabulary.evidence_grade_definitions must define every grade"
        )
    if not all(isinstance(value, str) and value.strip() for value in definitions.values()):
        raise MemorySourceError("evidence grade definitions must be non-empty strings")
    if set(vocabulary.get("residency_transitions", [])) != RESIDENCY_TRANSITIONS:
        raise MemorySourceError("controlled_vocabulary.residency_transitions drifted")
    if set(vocabulary.get("graph_semantics", [])) != GRAPH_SEMANTICS:
        raise MemorySourceError("controlled_vocabulary.graph_semantics drifted")

    sources = payload.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise MemorySourceError("sources must be a non-empty mapping")
    for entry_id, entry in sources.items():
        validate_source(entry_id, entry, allowed_layers=allowed_layers)
    return payload


def build_reproducibility_audit(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize what is executable, pinned, licensed, and still paper-only."""

    sources = payload["sources"]
    pinned_repository_sources = sorted(
        entry_id
        for entry_id, source in sources.items()
        if source.get("repositories")
    )
    pinned_artifact_sources = sorted(
        entry_id for entry_id, source in sources.items() if source.get("artifacts")
    )
    paper_only_sources = sorted(
        entry_id
        for entry_id, source in sources.items()
        if not source.get("repositories") and not source.get("artifacts")
    )
    unresolved_repositories = sorted(
        {
            f'{entry_id}:{repository["url"]}'
            for entry_id, source in sources.items()
            for repository in source.get("repositories", [])
            if repository["license"] == "unresolved"
        }
    )
    evidence_grades = Counter(
        source["evidence_grade"] for source in sources.values()
    )
    scientific_reproduced_sources = sorted(
        entry_id
        for entry_id, source in sources.items()
        if source["evidence_grade"] in SCIENTIFIC_REPRODUCED_GRADES
    )
    conformance_reproduced_sources = sorted(
        entry_id
        for entry_id, source in sources.items()
        if source["evidence_grade"] == "local-conformance-reproduced"
    )
    negative_reproduced_sources = sorted(
        entry_id
        for entry_id, source in sources.items()
        if source["evidence_grade"] == "local-negative-reproduced"
    )
    return {
        "source_count": len(sources),
        "pinned_repository_source_count": len(pinned_repository_sources),
        "pinned_repository_sources": pinned_repository_sources,
        "pinned_artifact_source_count": len(pinned_artifact_sources),
        "pinned_artifact_sources": pinned_artifact_sources,
        "paper_only_source_count": len(paper_only_sources),
        "paper_only_sources": paper_only_sources,
        "unresolved_repository_license_count": len(unresolved_repositories),
        "unresolved_repositories": unresolved_repositories,
        "scientific_result_reproduced_source_count": len(
            scientific_reproduced_sources
        ),
        "scientific_result_reproduced_sources": scientific_reproduced_sources,
        "local_conformance_reproduced_source_count": len(
            conformance_reproduced_sources
        ),
        "local_conformance_reproduced_sources": conformance_reproduced_sources,
        "local_negative_reproduced_source_count": len(negative_reproduced_sources),
        "local_negative_reproduced_sources": negative_reproduced_sources,
        "evidence_grade_counts": dict(sorted(evidence_grades.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--audit-json",
        action="store_true",
        help="emit the machine-readable reproducibility audit instead of summaries",
    )
    args = parser.parse_args()
    payload = load_and_validate(args.ledger)
    audit = build_reproducibility_audit(payload)
    if args.audit_json:
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0
    sources = payload["sources"]
    repo_count = sum(len(source.get("repositories", [])) for source in sources.values())
    artifact_count = sum(len(source.get("artifacts", [])) for source in sources.values())
    claim_count = sum(len(source.get("benchmark_claims", [])) for source in sources.values())
    print(
        f"memory source ledger PASS: {len(sources)} sources, "
        f"{repo_count} pinned repositories, {artifact_count} pinned artifacts, "
        f"{claim_count} labeled benchmark claims"
    )
    print(
        "reproducibility coverage: "
        f'{audit["pinned_repository_source_count"]} sources with pinned repositories, '
        f'{audit["paper_only_source_count"]} paper-only sources, '
        f'{audit["unresolved_repository_license_count"]} unresolved repository licenses, '
        f'{audit["scientific_result_reproduced_source_count"]} scientific results reproduced, '
        f'{audit["local_conformance_reproduced_source_count"]} conformance results reproduced, '
        f'{audit["local_negative_reproduced_source_count"]} negative findings reproduced'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
