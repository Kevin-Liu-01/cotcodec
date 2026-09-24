#!/usr/bin/env python3
"""Verify one API project's Daybreak Blue capability without retaining secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_ID = "gpt-5.6-sol"
ACCESS_PROGRAM = "daybreak_blue"
SAFETY_IDENTIFIER = "cotcodec-daybreak-doctor-v1"
PROMPT = (
    "This is a no-tool defensive-security capability check in an isolated research "
    "harness. Return the requested JSON confirming that a maintainer should validate "
    "a security patch only in an explicitly authorized test environment. Do not give "
    "exploit instructions and do not propose any external action."
)
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "const": "defensive_scope_acknowledged"},
        "action_boundary": {"type": "string", "const": "authorized_test_environment_only"},
    },
    "required": ["status", "action_boundary"],
    "additionalProperties": False,
}
DECISION_ERROR_CODES = {
    "access_program_not_enabled",
    "unsupported_access_program",
    "invalid_access_program",
    "model_not_found",
}


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _git_receipt() -> dict[str, Any]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        "git_sha": sha,
        "dirty": bool(status),
        "doctor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def build_request() -> dict[str, Any]:
    return {
        "model": MODEL_ID,
        "input": PROMPT,
        "access_programs": {"cyber": ACCESS_PROGRAM},
        "safety_identifier": SAFETY_IDENTIFIER,
        "store": False,
        "max_output_tokens": 128,
        "reasoning": {"effort": "none"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "daybreak_blue_capability",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            }
        },
    }


def _listed_model_receipt(client: Any) -> dict[str, Any]:
    response = client.models.list()
    identifiers = sorted(
        identifier
        for item in _value(response, "data", [])
        if isinstance((identifier := _value(item, "id")), str)
    )
    return {
        "requested_model_listed": MODEL_ID in identifiers,
        "listed_model_count": len(identifiers),
        "model_ids_sha256": _sha256(identifiers),
    }


def _selected_program(response: Any) -> str | None:
    programs = _value(response, "access_programs")
    selected = _value(programs, "cyber")
    return selected if isinstance(selected, str) else None


def _usage_receipt(response: Any) -> dict[str, int]:
    usage = _value(response, "usage", {})
    details = _value(usage, "input_tokens_details", {})
    return {
        "input_tokens": int(_value(usage, "input_tokens", 0)),
        "cached_tokens": int(_value(details, "cached_tokens", 0)),
        "output_tokens": int(_value(usage, "output_tokens", 0)),
        "total_tokens": int(_value(usage, "total_tokens", 0)),
    }


def _error_details(error: Exception) -> tuple[int | None, str | None]:
    status_code = getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    body = getattr(error, "body", None)
    if isinstance(body, Mapping):
        nested = body.get("error", body)
        if isinstance(nested, Mapping) and isinstance(nested.get("code"), str):
            code = nested["code"]
    clean_status = status_code if isinstance(status_code, int) else None
    clean_code = code if isinstance(code, str) else None
    return clean_status, clean_code


def run_doctor(*, client: Any, sdk_version: str) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    request = build_request()
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "doctor": "openai-daybreak-blue-capability",
        "evidence_grade": "API_PROJECT_CAPABILITY_ONLY",
        "claim_boundary": (
            "One bounded defensive Responses API call selected Daybreak Blue for the "
            "current credential. No Daybreak Red, ZDR, tool, H100, or research-quality claim."
        ),
        "requested_model": MODEL_ID,
        "requested_access_program": ACCESS_PROGRAM,
        "endpoint": "/v1/responses",
        "sdk": {"name": "openai-python", "version": sdk_version},
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "source": _git_receipt(),
        "request_sha256": _sha256(request),
        "credential": {"env": "OPENAI_API_KEY", "present": bool(os.getenv("OPENAI_API_KEY"))},
    }
    try:
        receipt["model_preflight"] = _listed_model_receipt(client)
        response = client.responses.create(**request)
    except Exception as error:  # SDK subclasses vary across pinned releases.
        status_code, code = _error_details(error)
        capability_failure = status_code == 403 or code in DECISION_ERROR_CODES
        receipt.update(
            {
                "status": (
                    "DAYBREAK_BLUE_CAPABILITY_FAIL"
                    if capability_failure
                    else "DAYBREAK_BLUE_CAPABILITY_ERROR"
                ),
                "error": {"http_status": status_code, "code": code, "type": type(error).__name__},
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return receipt, 2 if capability_failure else 3

    output_text = _value(response, "output_text")
    returned_model = _value(response, "model")
    selected_program = _selected_program(response)
    parsed: Any = None
    if isinstance(output_text, str):
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError:
            parsed = None
    content_ok = parsed == {
        "status": "defensive_scope_acknowledged",
        "action_boundary": "authorized_test_environment_only",
    }
    gates = {
        "model_listed": receipt["model_preflight"]["requested_model_listed"],
        "returned_model_exact": returned_model == MODEL_ID,
        "selected_program_exact": selected_program == ACCESS_PROGRAM,
        "structured_output_exact": content_ok,
    }
    passed = all(gates.values())
    receipt.update(
        {
            "status": (
                "DAYBREAK_BLUE_CAPABILITY_PASS"
                if passed
                else "DAYBREAK_BLUE_CAPABILITY_FAIL"
            ),
            "returned_model": returned_model,
            "selected_access_program": selected_program,
            "response_id": _value(response, "id"),
            "response_output_sha256": hashlib.sha256(
                output_text.encode() if isinstance(output_text, str) else b""
            ).hexdigest(),
            "usage": _usage_receipt(response),
            "gates": gates,
            "elapsed_seconds": time.perf_counter() - started,
        }
    )
    return receipt, 0 if passed else 2


def _write_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is not set")
    from openai import OpenAI, __version__

    receipt, exit_code = run_doctor(client=OpenAI(), sdk_version=__version__)
    _write_atomic(args.output, receipt)
    print(json.dumps({
        "status": receipt["status"],
        "requested_model": MODEL_ID,
        "selected_access_program": receipt.get("selected_access_program"),
        "gates": receipt.get("gates"),
        "usage": receipt.get("usage"),
        "receipt": str(args.output),
    }, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
