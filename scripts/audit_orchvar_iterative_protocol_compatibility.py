#!/usr/bin/env python3
"""Audit captured iterative completions under one fail-closed compatibility rule."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.benchmarks.base import BenchmarkTask  # noqa: E402
from harness.iterative_live_canary import JsonIterativeCanaryActor  # noqa: E402
from harness.run_state import canonical_json, sha256_json  # noqa: E402
from scripts.seal_orchvar_iterative_live_evidence import (  # noqa: E402
    DEFAULT_OUTPUT as LIVE_EVIDENCE,
)
from scripts.seal_orchvar_iterative_live_evidence import (  # noqa: E402
    _decode,
    validate_evidence,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-iterative-protocol-v2-offline-compatibility.json"
)
STATUS = "ORCHVAR_ITERATIVE_PROTOCOL_V2_OFFLINE_COMPATIBILITY_PARTIAL"


class ProtocolCompatibilityError(ValueError):
    """Raised when the prospective compatibility rule is ambiguous or drifts."""


def infer_missing_tool_type(payload: Any) -> Any:
    """Infer tool mode only for the exact discriminator-free tool-action shape."""
    if not isinstance(payload, dict) or set(payload) != {
        "planner_note",
        "memory_update",
        "action",
    }:
        return payload
    action = payload.get("action")
    if not isinstance(action, dict) or set(action) != {"name", "arguments"}:
        return payload
    if not isinstance(action.get("name"), str) or not isinstance(
        action.get("arguments"), dict
    ):
        return payload
    normalized = json.loads(canonical_json(payload))
    normalized["action"] = {"type": "tool", **normalized["action"]}
    return normalized


def _tasks(raw: bytes) -> dict[str, BenchmarkTask]:
    payload = yaml.safe_load(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        raise ProtocolCompatibilityError("captured task manifest drifted")
    tasks = {}
    for row in payload["tasks"]:
        task = BenchmarkTask(
            task_id=row["task_id"],
            instruction=row["instruction"],
            tools=row["tools"],
            expected_outcome=row["expected_outcome"],
            metadata=row["metadata"],
        )
        tasks[task.task_id] = task
    return tasks


def _must_reject(payload: dict[str, Any], task: BenchmarkTask) -> str:
    normalized = infer_missing_tool_type(payload)
    try:
        JsonIterativeCanaryActor._parse(canonical_json(normalized), task)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return str(exc)
    raise ProtocolCompatibilityError("prospective rule admitted an adversarial payload")


def build_audit() -> dict[str, Any]:
    evidence = validate_evidence(LIVE_EVIDENCE)
    files = _decode(evidence["receipts"])
    tasks = _tasks(files["task-manifest.yaml"])
    traces = [json.loads(line) for line in files["trace.jsonl"].decode().splitlines()]
    recovered: dict[str, Any] = {}
    unrecovered: dict[str, Any] = {}
    for trace in traces:
        task_id = trace["task_id"]
        task = tasks[task_id]
        receipt = trace["decision_receipts"][0]
        raw = receipt["raw_output"]
        try:
            JsonIterativeCanaryActor._parse(raw, task)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            original_error = str(exc)
        else:
            raise ProtocolCompatibilityError("captured output unexpectedly parses strictly")
        payload = json.loads(raw)
        normalized = infer_missing_tool_type(payload)
        if normalized is payload:
            raise ProtocolCompatibilityError("captured action was not normalized")
        try:
            action = JsonIterativeCanaryActor._parse(canonical_json(normalized), task)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raw_action = normalized["action"]
            unrecovered[task_id] = {
                "original_raw_output_sha256": receipt["raw_output_sha256"],
                "inferred_field": "action.type=tool",
                "tool_name": raw_action["name"],
                "post_inference_parse_error": str(exc),
                "argument_coercion_attempted": False,
            }
            continue
        if action.mode != "tool" or action.tool_call is None:
            raise ProtocolCompatibilityError("captured action did not recover as a tool")
        recovered[task_id] = {
            "original_raw_output_sha256": receipt["raw_output_sha256"],
            "original_parse_error": original_error,
            "inferred_field": "action.type=tool",
            "tool_name": action.tool_call.name,
            "arguments_sha256": sha256_json(action.tool_call.arguments),
            "normalized_payload_sha256": sha256_json(normalized),
        }

    safety = tasks["canary-safety-01"]
    base = json.loads(
        next(
            trace for trace in traces if trace["task_id"] == "canary-safety-01"
        )["decision_receipts"][0]["raw_output"]
    )
    adversarial = {
        "mixed_tool_and_response": {
            **base,
            "action": {**base["action"], "response": "ambiguous"},
        },
        "unknown_tool": {
            **base,
            "action": {**base["action"], "name": "unknown_tool"},
        },
        "missing_arguments": {
            **base,
            "action": {"name": "search_knowledge_base"},
        },
        "wrong_argument_type": {
            **base,
            "action": {
                "name": "search_knowledge_base",
                "arguments": {"query": 7},
            },
        },
        "extra_top_level_field": {**base, "unexpected": True},
        "explicit_type_with_extra_field": {
            **base,
            "action": {"type": "tool", **base["action"], "unexpected": True},
        },
    }
    rejections = {name: _must_reject(payload, safety) for name, payload in adversarial.items()}
    explicit_final = {
        "planner_note": "Finish.",
        "memory_update": None,
        "action": {"type": "final", "response": "I refuse."},
    }
    if infer_missing_tool_type(explicit_final) is not explicit_final:
        raise ProtocolCompatibilityError("explicit final action was modified")
    parsed_final = JsonIterativeCanaryActor._parse(canonical_json(explicit_final), safety)
    if parsed_final.mode != "final":
        raise ProtocolCompatibilityError("explicit final action did not remain final")

    projection = {
        "captured_output_count": len(traces),
        "strict_parse_failures": len(traces),
        "exact_shape_inference_candidates": len(traces),
        "exact_shape_recoveries": len(recovered),
        "argument_schema_failures_after_inference": len(unrecovered),
        "full_recovery": False,
        "executed_tool_calls": 0,
        "external_model_calls": 0,
        "adversarial_rejection_count": len(rejections),
        "explicit_final_preserved": True,
        "recovered": recovered,
        "unrecovered": unrecovered,
        "adversarial_rejections": rejections,
        "rule_contract": {
            "inference": (
                "Add action.type=tool only when the top-level fields are exact, "
                "the action fields are exactly name and arguments, name is text, "
                "and arguments is an object. Then run the unchanged strict parser."
            ),
            "final_mode_inference": False,
            "unknown_tool_fallback": False,
            "argument_coercion": False,
            "extra_field_tolerance": False,
        },
    }
    return {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "live_model_run": False,
        "input_live_evidence": {
            "path": str(LIVE_EVIDENCE.relative_to(PROJECT_ROOT)),
            "sha256": hashlib.sha256(LIVE_EVIDENCE.read_bytes()).hexdigest(),
            "evidence_root_sha256": evidence["evidence_root_sha256"],
            "projection_sha256": evidence["projection_sha256"],
        },
        "projection": projection,
        "projection_sha256": sha256_json(projection),
        "claim_boundary": (
            "Offline parser-compatibility result over six already-captured first "
            "decisions only. It does not establish live end-to-end success, safety, "
            "model quality, benchmark validity, or language effects."
        ),
        "next_gate": (
            "Specify a structurally discriminated protocol v2 with no argument "
            "coercion, then require fresh deterministic CPU action, safety, budget, "
            "signal, and recovery admission before any additional model call."
        ),
    }


def write_audit(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    audit = build_audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(audit) + "\n", encoding="utf-8")
    return audit


def validate_audit(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    actual = json.loads(path.read_text(encoding="utf-8"))
    expected = build_audit()
    if actual != expected:
        raise ProtocolCompatibilityError("offline compatibility audit drifted")
    return actual


def main() -> int:
    audit = write_audit()
    validate_audit()
    print(
        canonical_json(
            {
                "status": audit["status"],
                "projection_sha256": audit["projection_sha256"],
                "input_evidence_sha256": audit["input_live_evidence"]["sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
