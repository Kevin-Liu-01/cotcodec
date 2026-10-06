#!/usr/bin/env python3
"""Probe one internal Qwen/vLLM endpoint through Hermes' OpenAI wire contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
from pathlib import Path
from typing import Any

from openai import OpenAI

EXPECTED_BASE_URL = "http://past-qwen:8000/v1"
EXPECTED_API_KEY = "cotcodec-internal-transport"
EXPECTED_MODEL = "qwen3.6-35b-a3b"
PROBE_VALUE = "COTCODEC_QWEN_NATIVE_TOOL_PROBE_42"


class ModelTransportError(RuntimeError):
    """Raised when the endpoint violates the registered transport contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _request(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Call the required function exactly once. Do not answer in prose.",
            },
            {
                "role": "user",
                "content": f"Call echo_probe with value exactly {PROBE_VALUE}.",
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "echo_probe",
                    "description": "Return the exact requested probe value.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "echo_probe"}},
        "temperature": 0.0,
        "max_tokens": 128,
    }


def _validate_tool_call(*, name: str, arguments: str) -> dict[str, Any]:
    if name != "echo_probe":
        raise ModelTransportError(f"endpoint returned unexpected tool {name!r}")
    try:
        payload = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ModelTransportError("tool arguments are not JSON") from exc
    if payload != {"value": PROBE_VALUE}:
        raise ModelTransportError(f"tool arguments drifted: {payload!r}")
    return {"name": name, "arguments": payload}


def _nonstream_probe(client: OpenAI, request: dict[str, Any]) -> dict[str, Any]:
    response = client.chat.completions.create(**request)
    if len(response.choices) != 1:
        raise ModelTransportError("non-streaming response must contain one choice")
    choice = response.choices[0]
    calls = choice.message.tool_calls or []
    if len(calls) != 1:
        raise ModelTransportError("non-streaming response did not expose one native tool call")
    tool = _validate_tool_call(
        name=str(calls[0].function.name or ""),
        arguments=str(calls[0].function.arguments or ""),
    )
    content = choice.message.content or ""
    if "<tool_call>" in content or "<function=" in content:
        raise ModelTransportError("tool call leaked as text markup")
    usage = response.usage
    return {
        "content": content,
        "finish_reason": choice.finish_reason,
        "tool_calls": [tool],
        "usage": {
            "prompt_tokens": int(usage.prompt_tokens if usage else 0),
            "completion_tokens": int(usage.completion_tokens if usage else 0),
        },
    }


def _stream_probe(client: OpenAI, request: dict[str, Any]) -> dict[str, Any]:
    content: list[str] = []
    calls: dict[int, dict[str, str]] = {}
    finish_reason: str | None = None
    saw_native_delta = False
    stream = client.chat.completions.create(**request, stream=True)
    for chunk in stream:
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.finish_reason is not None:
            finish_reason = choice.finish_reason
        delta = choice.delta
        if delta.content:
            content.append(delta.content)
        for call in delta.tool_calls or []:
            saw_native_delta = True
            index = int(call.index)
            entry = calls.setdefault(index, {"name": "", "arguments": ""})
            if call.function is not None:
                if call.function.name:
                    entry["name"] += call.function.name
                if call.function.arguments:
                    entry["arguments"] += call.function.arguments
    if not saw_native_delta or sorted(calls) != [0]:
        raise ModelTransportError("streaming response did not expose one native tool-call delta")
    tool = _validate_tool_call(name=calls[0]["name"], arguments=calls[0]["arguments"])
    merged_content = "".join(content)
    if "<tool_call>" in merged_content or "<function=" in merged_content:
        raise ModelTransportError("streaming tool call leaked as text markup")
    return {
        "content": merged_content,
        "finish_reason": finish_reason,
        "tool_calls": [tool],
    }


def _assert_no_external_egress() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=1.0):
                pass
        except OSError as exc:
            failures.append({"target": f"{host}:{port}", "error": type(exc).__name__})
        else:
            raise ModelTransportError(f"internal-only client unexpectedly reached {host}:{port}")
    return failures


def _write_no_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run_doctor(*, base_url: str, api_key: str, model: str) -> dict[str, Any]:
    if base_url != EXPECTED_BASE_URL or api_key != EXPECTED_API_KEY or model != EXPECTED_MODEL:
        raise ModelTransportError(
            "transport identity does not match the registered internal endpoint"
        )
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=300.0, max_retries=0)
    listed = sorted(item.id for item in client.models.list().data)
    if listed != [model]:
        raise ModelTransportError(f"model roster drifted: {listed!r}")
    request = _request(model)
    first = _nonstream_probe(client, request)
    second = _nonstream_probe(client, request)
    first_semantic = {key: value for key, value in first.items() if key != "usage"}
    second_semantic = {key: value for key, value in second.items() if key != "usage"}
    if first_semantic != second_semantic:
        raise ModelTransportError("two greedy non-streaming probes were not semantically identical")
    streamed = _stream_probe(client, request)
    if streamed["tool_calls"] != first_semantic["tool_calls"]:
        raise ModelTransportError("streaming and non-streaming native tool calls differ")
    return {
        "schema_version": 1,
        "status": "PAST_QWEN_INTERNAL_MODEL_TRANSPORT_DOCTOR_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "base_url": base_url,
        "model": model,
        "model_roster": listed,
        "request_sha256": _sha256(request),
        "nonstream_first": first,
        "nonstream_second": second,
        "stream": streamed,
        "semantic_aa_equal": True,
        "native_nonstream_tool_call": True,
        "native_stream_tool_call": True,
        "external_egress_blocked": _assert_no_external_egress(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_doctor(base_url=args.base_url, api_key=args.api_key, model=args.model)
    _write_no_replace(
        args.output.resolve(),
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n",
    )
    print(report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
