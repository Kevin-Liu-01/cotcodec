#!/usr/bin/env python3
"""Exercise the exact Hermes Hindsight provider against a native service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from plugins.memory.hindsight import HindsightMemoryProvider


def _parse_tool_output(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Hermes tool output is not JSON: {raw!r}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Hermes tool output is not a mapping")
    if "error" in payload or payload.get("status") == "error":
        raise RuntimeError(f"Hermes tool failed: {payload}")
    return payload


def _write_config(root: Path, args: argparse.Namespace) -> None:
    config_dir = root / "hindsight"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "mode": "local_external",
        "api_url": args.api_url,
        "bank_id": "hermes",
        "bank_id_template": "hermes-{user}",
        "recall_budget": "low",
        "recall_types": "world,experience,observation",
        "recall_max_tokens": 512,
        "recall_max_input_chars": 512,
        "recall_sync": True,
        "auto_recall": True,
        "auto_retain": True,
        "retain_async": False,
        "retain_every_n_turns": 1,
        "retain_source": "cotcodec-hermes-hindsight-doctor",
        "memory_mode": "hybrid",
        "timeout": 20,
    }
    (config_dir / "config.json").write_text(
        json.dumps(config, sort_keys=True) + "\n", encoding="utf-8"
    )


def _recall(provider: HindsightMemoryProvider, query: str) -> dict[str, Any]:
    return _parse_tool_output(provider.handle_tool_call("hindsight_recall", {"query": query}))


def _wait_for_canary(
    provider: HindsightMemoryProvider,
    canary: str,
    *,
    present: bool,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while True:
        last = _recall(provider, canary)
        found = canary.lower() in str(last.get("result", "")).lower()
        if found is present:
            return last
        if time.monotonic() >= deadline:
            raise RuntimeError(f"recall did not reach present={present}; last={last!r}")
        time.sleep(0.25)


def _run(args: argparse.Namespace) -> dict[str, Any]:
    hermes_home = Path(args.hermes_home)
    hermes_home.mkdir(parents=True, exist_ok=True)
    _write_config(hermes_home, args)
    os.environ["HERMES_HOME"] = str(hermes_home)

    provider = HindsightMemoryProvider()
    provider.initialize(
        args.session_id,
        platform="doctor",
        user_id=args.user,
        agent_identity="cotcodec-doctor",
        agent_workspace="contained-native-hindsight",
    )
    try:
        if provider._mode != "local_external":  # noqa: SLF001
            raise RuntimeError(f"unexpected provider mode: {provider._mode}")  # noqa: SLF001
        expected_bank = f"hermes-{args.user}"
        if provider._bank_id != expected_bank:  # noqa: SLF001
            raise RuntimeError(
                f"bank isolation template drifted: {provider._bank_id!r} != {expected_bank!r}"  # noqa: SLF001
            )
        prompt = provider.system_prompt_block()
        if "Hindsight Memory" not in prompt:
            raise RuntimeError("Hindsight prompt integration is inactive")
        tool_names = [item.get("name") for item in provider.get_tool_schemas()]
        if tool_names != [
            "hindsight_retain",
            "hindsight_recall",
            "hindsight_reflect",
        ]:
            raise RuntimeError(f"Hindsight tool roster drifted: {tool_names!r}")

        base = {
            "action": args.action,
            "bank_id": expected_bank,
            "prompt_active": True,
            "tool_names": tool_names,
            "purge_tool_exposed": False,
        }
        if args.action == "write":
            stored = _parse_tool_output(
                provider.handle_tool_call(
                    "hindsight_retain",
                    {
                        "content": args.canary,
                        "context": "cotcodec native lifecycle canary",
                        "tags": ["cotcodec-doctor", f"tenant:{args.user}"],
                    },
                )
            )
            recalled = _wait_for_canary(provider, args.canary, present=True)
            return {**base, "stored": stored, "recalled": recalled}

        if args.action == "search":
            recalled = _wait_for_canary(provider, args.canary, present=args.expect_present)
            return {
                **base,
                "recalled": recalled,
                "expected_present": args.expect_present,
            }

        if args.action == "prefetch":
            context = provider.prefetch(args.canary, session_id=args.session_id)
            status = provider.recall_status()
            if args.canary.lower() not in context.lower():
                raise RuntimeError("synchronous auto-recall did not inject the canary")
            if status is None or status.count < 1:
                raise RuntimeError("recall status did not report injected memory")
            return {
                **base,
                "context": context,
                "recall_status": {
                    "provider_label": status.provider_label,
                    "count": status.count,
                    "glyph": status.glyph,
                },
            }

        if args.action == "sync-turn":
            provider.sync_turn(
                f"Please remember {args.canary}",
                f"I will remember {args.canary}",
                session_id=args.session_id,
            )
            provider.shutdown()
            provider = None
            return {**base, "sync_turn_dispatched": True}

        if args.action == "admin-delete":
            provider._run_hindsight_operation(  # noqa: SLF001
                lambda client: client.adelete_bank(provider._bank_id)  # noqa: SLF001
            )
            recalled = _wait_for_canary(provider, args.canary, present=False)
            return {
                **base,
                "native_admin_delete": True,
                "hermes_purge_tool_used": False,
                "recalled": recalled,
            }

        raise RuntimeError(f"unsupported action: {args.action}")
    finally:
        if provider is not None:
            provider.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action",
        choices=("write", "search", "prefetch", "sync-turn", "admin-delete"),
        required=True,
    )
    parser.add_argument("--api-url", default="http://hindsight:8888")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--hermes-home", default="/state/hermes")
    parser.add_argument("--canary", default="")
    parser.add_argument("--expect-present", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    try:
        result = _run(args)
    except Exception as exc:  # noqa: BLE001 - preserve one machine-readable failure
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "PASS", "result": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
