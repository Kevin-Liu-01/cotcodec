#!/usr/bin/env python3
"""Serve the deterministic ``memory-lifecycle-v1`` reference implementation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.lifecycle import (  # noqa: E402
    LIFECYCLE_PROTOCOL_VERSION,
    LifecycleCommand,
    ReferenceLifecyclePort,
)
from harness.memory_trials.schema import canonical_json  # noqa: E402


def _response(operation: str, *, ok: bool, result: dict[str, Any]) -> str:
    return canonical_json(
        {
            "protocol": LIFECYCLE_PROTOCOL_VERSION,
            "operation": operation,
            "ok": ok,
            "result": result,
        }
    )


def _handle(
    line: str, port: ReferenceLifecyclePort
) -> tuple[str, bool]:
    operation = "unknown"
    try:
        envelope = json.loads(line)
        if not isinstance(envelope, dict):
            raise ValueError("request envelope must be an object")
        if envelope.get("protocol") != LIFECYCLE_PROTOCOL_VERSION:
            raise ValueError("unsupported protocol")
        operation = envelope.get("operation")
        if not isinstance(operation, str):
            raise ValueError("operation must be a string")
        payload = envelope.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        if operation == "handshake":
            result = {"receipt": port.receipt.model_dump(mode="json")}
        elif operation == "execute":
            command = LifecycleCommand.model_validate(payload.get("command"))
            receipt = port.execute(command)
            result = {"receipt": receipt.model_dump(mode="json")}
        elif operation == "shutdown":
            port.close()
            result = {"shutdown": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        return _response(operation, ok=False, result={"error": str(exc)}), False
    return _response(operation, ok=True, result=result), operation == "shutdown"


def main() -> int:
    try:
        active_slots = int(os.environ.get("COTCODEC_LIFECYCLE_ACTIVE_SLOTS", "4"))
    except ValueError as exc:
        raise SystemExit("COTCODEC_LIFECYCLE_ACTIVE_SLOTS must be an integer") from exc
    maintenance_mode = os.environ.get("COTCODEC_LIFECYCLE_MAINTENANCE_MODE", "dedupe")
    if maintenance_mode not in {"none", "dedupe"}:
        raise SystemExit(
            "COTCODEC_LIFECYCLE_MAINTENANCE_MODE must be none or dedupe"
        )
    implementation_kind = os.environ.get(
        "COTCODEC_LIFECYCLE_IMPLEMENTATION_KIND", "subprocess_reference"
    )
    if implementation_kind not in {"subprocess_reference", "oci_sidecar"}:
        raise SystemExit(
            "COTCODEC_LIFECYCLE_IMPLEMENTATION_KIND must be subprocess_reference "
            "or oci_sidecar"
        )
    port = ReferenceLifecyclePort(
        active_slots=active_slots,
        maintenance_mode=maintenance_mode,
        implementation_kind=implementation_kind,
    )
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response, shutdown = _handle(line, port)
            print(response, flush=True)
            if shutdown:
                return 0
    finally:
        port.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
