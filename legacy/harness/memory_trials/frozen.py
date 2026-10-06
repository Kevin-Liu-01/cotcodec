"""Content-addressed native-memory selections reused across actor models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.systems import (
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
)


class FrozenMemoryBundleError(ValueError):
    """Raised when a frozen selection artifact is malformed or has been changed."""


def _request_sha256(request: MemorySystemRequest) -> str:
    return sha256_text(canonical_json(request.model_dump(mode="json")))


def task_manifest_sha256(source: Any) -> str:
    """Bind exact tasks, not only a source's declared identity or revision."""

    rows = [
        {"task_id": task.task_id, "task_sha256": task.task_sha256}
        for task in (source.load(task_id) for task_id in source.ids())
    ]
    return sha256_text(canonical_json(rows))


class FrozenMemorySystem:
    """Read-only memory system backed by a sealed request-to-selection mapping."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FrozenMemoryBundleError(f"cannot read frozen bundle: {self.path}") from exc
        if not isinstance(payload, dict):
            raise FrozenMemoryBundleError("frozen bundle must be a JSON object")
        claimed_sha256 = payload.get("bundle_sha256")
        unsigned = {key: value for key, value in payload.items() if key != "bundle_sha256"}
        actual_sha256 = sha256_text(canonical_json(unsigned))
        if claimed_sha256 != actual_sha256:
            raise FrozenMemoryBundleError("frozen bundle digest mismatch")
        if payload.get("schema_version") != "1.0":
            raise FrozenMemoryBundleError("unsupported frozen bundle schema")
        if payload.get("protocol") != "memory-system-v1":
            raise FrozenMemoryBundleError("frozen bundle protocol mismatch")
        try:
            upstream = MemorySystemReceipt.model_validate(payload["upstream_receipt"])
        except (KeyError, ValidationError) as exc:
            raise FrozenMemoryBundleError("invalid upstream receipt") from exc
        entries = payload.get("entries")
        if not isinstance(entries, list) or not entries:
            raise FrozenMemoryBundleError("frozen bundle must contain selections")
        self._selections: dict[str, MemorySelection] = {}
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                raise FrozenMemoryBundleError("frozen bundle entry must be an object")
            try:
                request = MemorySystemRequest.model_validate(raw_entry["request"])
                selection = MemorySelection.model_validate(raw_entry["selection"])
            except (KeyError, ValidationError) as exc:
                raise FrozenMemoryBundleError("invalid frozen bundle entry") from exc
            request_sha256 = _request_sha256(request)
            if raw_entry.get("request_sha256") != request_sha256:
                raise FrozenMemoryBundleError("frozen request digest mismatch")
            if selection.request_id != request.request_id:
                raise FrozenMemoryBundleError("frozen selection request mismatch")
            if selection.receipt != upstream:
                raise FrozenMemoryBundleError("frozen selection changed upstream receipt")
            if request_sha256 in self._selections:
                raise FrozenMemoryBundleError("duplicate frozen request")
            self._selections[request_sha256] = selection
        upstream_sha256 = sha256_text(canonical_json(upstream.model_dump(mode="json")))
        wrapper_config = {
            "bundle_sha256": actual_sha256,
            "upstream_receipt_sha256": upstream_sha256,
            "selection_count": len(self._selections),
        }
        self.receipt = MemorySystemReceipt(
            system_id=upstream.system_id,
            implementation_kind="frozen_selection_bundle",
            implementation_revision=(
                f"frozen-selection-v1:{upstream.implementation_revision}"
            ),
            configuration_sha256=sha256_text(canonical_json(wrapper_config)),
            backend_id=f"frozen:{upstream.backend_id}",
            source_archive_sha256=upstream.source_archive_sha256,
            image_digest=upstream.image_digest,
            model_receipt_sha256s=upstream.model_receipt_sha256s,
            publication_ready=False,
        )
        self.identity = self.receipt.system_id
        self.bundle_sha256 = actual_sha256
        treatment_modes = payload.get("treatment_modes")
        if (
            not isinstance(treatment_modes, list)
            or not treatment_modes
            or not all(
                item in {"storage_and_service", "serve_only"}
                for item in treatment_modes
            )
            or len(treatment_modes) != len(set(treatment_modes))
        ):
            raise FrozenMemoryBundleError("invalid frozen treatment modes")
        admission_evidence = payload.get("admission_evidence")
        if admission_evidence is not None and not isinstance(admission_evidence, dict):
            raise FrozenMemoryBundleError("invalid frozen admission evidence")
        self.metadata: dict[str, Any] = {
            "task_source": payload.get("task_source"),
            "treatment_modes": treatment_modes,
            "selection_count": len(self._selections),
            "admission_evidence": admission_evidence,
            "admission_evidence_sha256": (
                sha256_text(canonical_json(admission_evidence))
                if admission_evidence is not None
                else None
            ),
        }

    def require_compatible(
        self,
        *,
        source_provenance: Mapping[str, Any],
        budget: Mapping[str, Any],
        treatment_mode: str,
        exact_task_manifest_sha256: str,
    ) -> None:
        if treatment_mode not in self.metadata["treatment_modes"]:
            raise FrozenMemoryBundleError(
                f"bundle does not contain treatment mode: {treatment_mode}"
            )
        task_source = self.metadata.get("task_source")
        if not isinstance(task_source, dict):
            raise FrozenMemoryBundleError("bundle has no task-source receipt")
        for key, value in source_provenance.items():
            if task_source.get(key) != value:
                raise FrozenMemoryBundleError(
                    f"bundle task source differs at field: {key}"
                )
        if task_source.get("budget") != dict(budget):
            raise FrozenMemoryBundleError("bundle memory budget differs from actor study")
        if task_source.get("task_manifest_sha256") != exact_task_manifest_sha256:
            raise FrozenMemoryBundleError("bundle task manifest differs from actor study")

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        request_sha256 = _request_sha256(request)
        selection = self._selections.get(request_sha256)
        if selection is None:
            raise FrozenMemoryBundleError(
                f"request absent from frozen bundle: {request_sha256}"
            )
        response = {
            "request_id": selection.request_id,
            "evidence": [item.model_dump(mode="json") for item in selection.evidence],
            "costs": selection.costs.model_dump(mode="json"),
            "receipt": self.receipt.model_dump(mode="json"),
        }
        return MemorySelection(
            **response,
            selection_sha256=sha256_text(canonical_json(response)),
        )
