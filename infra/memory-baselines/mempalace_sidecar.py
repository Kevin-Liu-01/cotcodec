#!/usr/bin/env python3
"""Pinned MemPalace raw-session adapter for the memory-system-v1 protocol."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import MemPalaceRawSessionMemorySystem  # noqa: E402
from harness.memory_trials.schema import canonical_json  # noqa: E402
from harness.memory_trials.systems import MemorySystemRequest  # noqa: E402
from scripts.mempalace_control_factory import build_verified_mempalace_control  # noqa: E402


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _response(operation: str, *, ok: bool, result: Mapping[str, Any]) -> str:
    return canonical_json(
        {
            "protocol": "memory-system-v1",
            "operation": operation,
            "ok": ok,
            "result": dict(result),
        }
    )


def _handle(
    line: str, system: MemPalaceRawSessionMemorySystem
) -> tuple[str, bool, int]:
    try:
        envelope = json.loads(line)
        if not isinstance(envelope, dict) or envelope.get("protocol") != "memory-system-v1":
            raise ValueError("unsupported protocol")
        operation = envelope.get("operation")
        payload = envelope.get("payload", {})
        if not isinstance(operation, str) or not isinstance(payload, dict):
            raise ValueError("sidecar envelope is malformed")
        if operation == "handshake":
            result = {"receipt": system.receipt.model_dump(mode="json")}
        elif operation == "select":
            request = MemorySystemRequest.model_validate(payload)
            result = {"selection": system.select(request).model_dump(mode="json")}
        elif operation == "purge":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("purge requires session_scope")
            result = {"purged": True}
        elif operation == "inspect":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("inspect requires session_scope")
            result = {"state": "stateless", "record_count": 0}
        elif operation == "shutdown":
            result = {"shutdown": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        operation = locals().get("operation", "unknown")
        return _response(operation, ok=False, result={"error": str(exc)}), False, 2
    return _response(operation, ok=True, result=result), operation == "shutdown", 0


def main() -> int:
    runtime_receipt = Path(_required_env("COTCODEC_MEMPALACE_RUNTIME_RECEIPT"))
    runtime_receipt_sha256 = _required_env(
        "COTCODEC_MEMPALACE_RUNTIME_RECEIPT_SHA256"
    )
    control = build_verified_mempalace_control(
        source_root=Path(
            os.environ.get("COTCODEC_MEMPALACE_SOURCE_ROOT", "/opt/mempalace/source")
        ),
        equivalence_root=Path(
            _required_env("COTCODEC_MEMPALACE_EQUIVALENCE_ROOT")
        ),
        expected_equivalence_contract_sha256=_required_env(
            "COTCODEC_MEMPALACE_EQUIVALENCE_CONTRACT_SHA256"
        ),
        expected_equivalence_bundle_root_sha256=_required_env(
            "COTCODEC_MEMPALACE_EQUIVALENCE_BUNDLE_ROOT_SHA256"
        ),
        direct_runtime_receipt_path=Path(
            _required_env("COTCODEC_MEMPALACE_DIRECT_RUNTIME_RECEIPT")
        ),
        expected_direct_runtime_receipt_sha256=_required_env(
            "COTCODEC_MEMPALACE_DIRECT_RUNTIME_RECEIPT_SHA256"
        ),
        port_runtime_receipt_path=runtime_receipt,
        expected_port_runtime_receipt_sha256=runtime_receipt_sha256,
        implementation_kind="oci_sidecar",
    )
    system = control.system
    persistent = os.environ.get("COTCODEC_MEMORY_PERSISTENT_PROTOCOL") == "1"
    for line in sys.stdin:
        if not line.strip():
            continue
        response, shutdown, returncode = _handle(line, system)
        print(response, flush=True)
        if returncode or shutdown or not persistent:
            return returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
