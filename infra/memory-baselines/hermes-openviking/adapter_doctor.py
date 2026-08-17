#!/usr/bin/env python3
"""Exercise the exact Hermes OpenViking provider against a native service."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from plugins.memory.openviking import OpenVikingMemoryProvider


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


def _search(provider: OpenVikingMemoryProvider, query: str) -> dict[str, Any]:
    return _parse_tool_output(
        provider.handle_tool_call(
            "viking_search",
            {"query": query, "mode": "auto", "limit": 10},
        )
    )


def _matching_uris(payload: dict[str, Any], needle: str) -> list[str]:
    matches: list[str] = []
    for row in payload.get("results", []):
        if not isinstance(row, dict):
            continue
        uri = row.get("uri")
        abstract = row.get("abstract")
        if isinstance(uri, str) and (
            needle.lower() in str(abstract or "").lower() or row.get("score", 0) > 0
        ):
            matches.append(uri)
    return sorted(set(matches))


def _wait_for_match(
    provider: OpenVikingMemoryProvider,
    query: str,
    *,
    present: bool,
    expected_uri: str = "",
    timeout_seconds: float = 30.0,
) -> tuple[dict[str, Any], list[str]]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while True:
        last = _search(provider, query)
        uris = _matching_uris(last, query)
        found = expected_uri in uris if expected_uri else bool(uris)
        if found is present:
            return last, uris
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"search did not reach present={present}; expected_uri={expected_uri!r}; "
                f"last={last!r}"
            )
        time.sleep(0.25)


def _run(args: argparse.Namespace) -> dict[str, Any]:
    hermes_home = Path(args.hermes_home)
    hermes_home.mkdir(parents=True, exist_ok=True)
    provider = OpenVikingMemoryProvider()
    provider.initialize(
        args.session_id,
        hermes_home=str(hermes_home),
        platform="doctor",
    )
    try:
        if provider._client is None:  # noqa: SLF001 - deliberate admission probe
            raise RuntimeError("Hermes provider did not accept the native OpenViking service")

        prompt_active = bool(provider.system_prompt_block())
        if args.action == "write":
            remembered = _parse_tool_output(
                provider.handle_tool_call(
                    "viking_remember",
                    {"content": args.canary, "category": "preference"},
                )
            )
            search, uris = _wait_for_match(provider, args.canary, present=True)
            if len(uris) != 1:
                raise RuntimeError(f"expected one stored URI, got {uris!r}")
            uri = uris[0]
            read = _parse_tool_output(
                provider.handle_tool_call(
                    "viking_read",
                    {"uri": uri, "level": "full"},
                )
            )
            if args.canary not in str(read.get("content", "")):
                raise RuntimeError("read-after-write lost the canary")
            return {
                "action": args.action,
                "prompt_active": prompt_active,
                "remembered": remembered,
                "search": search,
                "uri": uri,
                "read": read,
            }

        if args.action == "search":
            search, uris = _wait_for_match(
                provider,
                args.canary,
                present=args.expect_present,
                expected_uri=args.uri,
            )
            return {
                "action": args.action,
                "prompt_active": prompt_active,
                "search": search,
                "uris": uris,
                "expected_present": args.expect_present,
            }

        if args.action == "read":
            read = _parse_tool_output(
                provider.handle_tool_call(
                    "viking_read",
                    {"uri": args.uri, "level": "full"},
                )
            )
            if args.canary and args.canary not in str(read.get("content", "")):
                raise RuntimeError("read did not contain the expected canary")
            return {"action": args.action, "prompt_active": prompt_active, "read": read}

        if args.action == "forget":
            forgotten = _parse_tool_output(
                provider.handle_tool_call("viking_forget", {"uri": args.uri})
            )
            search, uris = _wait_for_match(
                provider,
                args.canary,
                present=False,
                expected_uri=args.uri,
            )
            return {
                "action": args.action,
                "prompt_active": prompt_active,
                "forgotten": forgotten,
                "search": search,
                "uris": uris,
            }

        raise RuntimeError(f"unsupported action: {args.action}")
    finally:
        provider.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("write", "search", "read", "forget"), required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--hermes-home", default="/state/hermes")
    parser.add_argument("--canary", default="")
    parser.add_argument("--uri", default="")
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
