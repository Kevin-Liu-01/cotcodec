#!/usr/bin/env python3
"""Serve one memory-system-v1 request using the deterministic reference system."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.systems import (  # noqa: E402
    MemorySystemRequest,
    ReferenceMemorySystem,
)


def _response(operation: str, *, ok: bool, result: dict[str, Any]) -> str:
    return json.dumps(
        {
            "protocol": "memory-system-v1",
            "operation": operation,
            "ok": ok,
            "result": result,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _handle(line: str, system: ReferenceMemorySystem) -> tuple[str, bool, int]:
    try:
        envelope = json.loads(line)
        if envelope.get("protocol") != "memory-system-v1":
            raise ValueError("unsupported protocol")
        operation = envelope["operation"]
        payload = envelope.get("payload", {})
        if operation == "handshake":
            result = {"receipt": system.receipt.model_dump(mode="json")}
        elif operation == "select":
            request = MemorySystemRequest.model_validate(payload)
            result = {"selection": system.select(request).model_dump(mode="json")}
        elif operation == "purge":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("purge requires session_scope")
            result = {"purged": True}
        elif operation == "shutdown":
            result = {"shutdown": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        operation = locals().get("operation", "unknown")
        return _response(operation, ok=False, result={"error": str(exc)}), False, 2
    return _response(operation, ok=True, result=result), operation == "shutdown", 0


def main() -> int:
    persistent = os.environ.get("COTCODEC_MEMORY_PERSISTENT_PROTOCOL") == "1"
    system = ReferenceMemorySystem()
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
