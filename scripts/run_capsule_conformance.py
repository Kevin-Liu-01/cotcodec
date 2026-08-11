#!/usr/bin/env python3
"""Run the deterministic reference capsule replay across two host manifests."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.capsules import (  # noqa: E402
    CapabilityManifest,
    CapsuleEvent,
    Effect,
    Hook,
    MemoryGraphCapsule,
    VerifyBeforeFinalCapsule,
    compile_capsules,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "results" / "capsule-conformance" / "reference.json"
)


def host(harness_id: str, protocol: str) -> CapabilityManifest:
    return CapabilityManifest(
        harness_id=harness_id,
        adapter_version="0.1.0",
        native_protocol=protocol,
        hooks=frozenset(
            {
                Hook.SESSION_START,
                Hook.BEFORE_MODEL,
                Hook.AFTER_TOOL,
                Hook.BEFORE_FINAL,
                Hook.SESSION_END,
            }
        ),
        effects_by_hook={
            Hook.SESSION_START: frozenset(),
            Hook.BEFORE_MODEL: frozenset({Effect.INJECT_CONTEXT}),
            Hook.AFTER_TOOL: frozenset({Effect.EMIT_MEMORY_DELTA}),
            Hook.BEFORE_FINAL: frozenset(
                {Effect.REQUEST_VERIFICATION, Effect.BLOCK}
            ),
            Hook.SESSION_END: frozenset(),
        },
        max_context_injection_bytes=4096,
        supports_blocking=True,
    )


def trace() -> list[CapsuleEvent]:
    return [
        CapsuleEvent(
            event_id="tool-1",
            session_id="reference-session",
            sequence=1,
            hook=Hook.AFTER_TOOL,
            payload={
                "tool_name": "scheduler",
                "content": "The training run requires an atomic Slurm checkpoint.",
            },
            provenance=["reference-fixture"],
            contains_untrusted_data=True,
        ),
        CapsuleEvent(
            event_id="model-1",
            session_id="reference-session",
            sequence=2,
            hook=Hook.BEFORE_MODEL,
            payload={"query": "How does the Slurm run recover?"},
            provenance=["reference-fixture"],
        ),
        CapsuleEvent(
            event_id="final-1",
            session_id="reference-session",
            sequence=3,
            hook=Hook.BEFORE_FINAL,
            payload={},
            provenance=["reference-fixture"],
        ),
    ]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


async def run(output: Path) -> dict[str, Any]:
    hosts = [
        host("cotcodec-reference", "native-python"),
        host("ahp-reference", "agent-harness-protocol-2.4"),
    ]
    fixture = trace()
    normalized: dict[str, list[dict[str, Any]]] = {}
    for capability in hosts:
        runtime = compile_capsules(
            capability,
            [MemoryGraphCapsule(), VerifyBeforeFinalCapsule()],
        )
        normalized[capability.harness_id] = [
            (await runtime.dispatch(event)).model_dump(mode="json") for event in fixture
        ]

    values = list(normalized.values())
    parity = sum(
        canonical(left) == canonical(right)
        for left, right in zip(values[0], values[1], strict=True)
    ) / len(fixture)
    payload = {
        "schema_version": 1,
        "status": "PASS" if parity == 1.0 else "FAIL",
        "scope": "synthetic manifest replay; no live framework adapters",
        "event_count": len(fixture),
        "host_count": len(hosts),
        "action_parity": parity,
        "fixture_sha256": hashlib.sha256(
            canonical([event.model_dump(mode="json") for event in fixture]).encode()
        ).hexdigest(),
        "capability_manifests": [item.model_dump(mode="json") for item in hosts],
        "results": normalized,
    }
    atomic_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = asyncio.run(run(args.output.resolve()))
    print(json.dumps({key: result[key] for key in result if key != "results"}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
