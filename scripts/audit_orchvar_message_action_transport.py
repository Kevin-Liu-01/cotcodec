#!/usr/bin/env python3
"""Select a message/action transport design from the two sealed live negatives."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.agent_loop import TOOL_SCHEMAS  # noqa: E402
from harness.run_state import canonical_json, sha256_json  # noqa: E402
from harness.yaml_utils import load_yaml_file  # noqa: E402
from scripts.seal_orchvar_iterative_live_evidence import (  # noqa: E402
    DEFAULT_OUTPUT as EXPLICIT_EVIDENCE,
)
from scripts.seal_orchvar_iterative_live_evidence import (  # noqa: E402
    _decode as decode_explicit,
)
from scripts.seal_orchvar_iterative_live_evidence import (  # noqa: E402
    validate_evidence as validate_explicit,
)
from scripts.seal_orchvar_iterative_structural_live_evidence import (  # noqa: E402
    DEFAULT_OUTPUT as STRUCTURAL_EVIDENCE,
)
from scripts.seal_orchvar_iterative_structural_live_evidence import (  # noqa: E402
    _decode as decode_structural,
)
from scripts.seal_orchvar_iterative_structural_live_evidence import (  # noqa: E402
    validate_evidence as validate_structural,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/orchvar_message_action_transport_audit.yaml"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-message-action-transport-audit-v1.json"
)
STATUS = "ORCHVAR_MESSAGE_ACTION_TRANSPORT_TWO_STAGE_SELECTED_CPU_REQUIRED"


class MessageActionAuditError(ValueError):
    """Raised when the audit inputs or candidate decision drift."""


def _first_decisions(raw: bytes) -> list[dict[str, Any]]:
    traces = [json.loads(line) for line in raw.decode().splitlines()]
    return [
        {
            "task_id": trace["task_id"],
            "raw": json.loads(trace["decision_receipts"][0]["raw_output"]),
            "parse_status": trace["decision_receipts"][0]["action_parse_status"],
        }
        for trace in traces
    ]


def _inner_action_valid(payload: Any, task_tools: set[str]) -> tuple[bool, str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("action"), dict):
        return False, "missing_action_object"
    action = payload["action"]
    if set(action) == {"response"}:
        response = action["response"]
        return (isinstance(response, str) and bool(response.strip()), "final_shape")
    if set(action) != {"name", "arguments"}:
        return False, "ambiguous_action_shape"
    name = action["name"]
    arguments = action["arguments"]
    schema = TOOL_SCHEMAS.get(name) if isinstance(name, str) else None
    if name not in task_tools or schema is None or not isinstance(arguments, dict):
        return False, "unknown_tool_or_nonobject_arguments"
    if set(arguments) != set(schema):
        return False, "argument_fields_drifted"
    for field, expected in schema.items():
        value = arguments[field]
        valid = (
            isinstance(value, (int, float)) and not isinstance(value, bool)
            if expected is float
            else isinstance(value, expected)
        )
        if not valid:
            return False, f"argument_type_drifted:{field}"
    return True, "tool_shape_and_arguments_valid"


def build_audit() -> dict[str, Any]:
    contract = load_yaml_file(DEFAULT_EXPERIMENT)
    explicit = validate_explicit(EXPLICIT_EVIDENCE)
    structural = validate_structural(STRUCTURAL_EVIDENCE)
    explicit_files = decode_explicit(explicit["receipts"])
    structural_files = decode_structural(structural["receipts"])
    task_manifest = load_yaml_file(
        PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"
    )
    task_tools = {
        row["task_id"]: {tool["name"] for tool in row["tools"]}
        for row in task_manifest["tasks"]
    }

    cohorts = {}
    for name, decisions in (
        ("explicit_type_v1", _first_decisions(explicit_files["trace.jsonl"])),
        ("structural_v2", _first_decisions(structural_files["trace.jsonl"])),
    ):
        rows = []
        for decision in decisions:
            raw = decision["raw"]
            action_valid, action_reason = _inner_action_valid(
                raw, task_tools[decision["task_id"]]
            )
            message_present = (
                isinstance(raw, dict)
                and isinstance(raw.get("planner_note"), str)
                and bool(raw["planner_note"].strip())
                and "memory_update" in raw
                and (
                    raw["memory_update"] is None
                    or isinstance(raw["memory_update"], str)
                )
            )
            rows.append(
                {
                    "task_id": decision["task_id"],
                    "registered_parse_status": decision["parse_status"],
                    "research_message_present": message_present,
                    "inner_action_valid": action_valid,
                    "inner_action_reason": action_reason,
                }
            )
        cohorts[name] = {
            "first_decisions": rows,
            "research_message_presence_count": sum(
                row["research_message_present"] for row in rows
            ),
            "inner_action_valid_count": sum(row["inner_action_valid"] for row in rows),
            "registered_parse_valid_count": sum(
                row["registered_parse_status"] == "valid" for row in rows
            ),
        }

    candidates = {
        "coupled_required": {
            "admitted": False,
            "reason": (
                "Empirically suppresses executable actions when either research "
                "or action fields drift; registered validity was 0/6 then 1/6."
            ),
        },
        "coupled_optional_messages": {
            "admitted": False,
            "reason": (
                "Would silently turn non-random message omission into treatment "
                "dilution and make intervention compliance condition-dependent."
            ),
        },
        "action_then_message": {
            "admitted": False,
            "reason": (
                "A message generated after the action cannot causally mediate the "
                "action and is not the proposed orchestration treatment."
            ),
        },
        "message_then_action_two_stage": {
            "admitted": True,
            "reason": (
                "Separates variable-message compliance from fixed action parsing, "
                "preserves causal order, and permits independent receipts/budgets."
            ),
            "required_controls": [
                "plain_nonempty_planner_message_stage",
                "explicit_memory_stage_or_predeclared_no_update",
                "strict_action_only_json_stage",
                "no_message_synthesis",
                "no_argument_coercion",
                "transformed_messages_condition_action_stage",
                "missing_message_marks_cell_noncompliant",
                "tool_results_condition_later_message_and_action_stages",
            ],
        },
    }
    if (
        cohorts["explicit_type_v1"]["research_message_presence_count"] != 6
        or cohorts["explicit_type_v1"]["inner_action_valid_count"] != 5
        or cohorts["explicit_type_v1"]["registered_parse_valid_count"] != 0
        or cohorts["structural_v2"]["research_message_presence_count"] != 1
        or cohorts["structural_v2"]["inner_action_valid_count"] != 5
        or cohorts["structural_v2"]["registered_parse_valid_count"] != 1
        or [name for name, row in candidates.items() if row["admitted"]]
        != ["message_then_action_two_stage"]
    ):
        raise MessageActionAuditError("message/action audit projection drifted")

    projection = {
        "external_model_calls": 0,
        "local_tool_calls": 0,
        "cohorts": cohorts,
        "candidates": candidates,
        "selected_candidate": "message_then_action_two_stage",
        "selection_status": "design_selected_cpu_admission_required",
        "invariants": contract["invariants"],
        "claim_boundary": contract["claim_boundary"],
        "next_gate": (
            "Implement a two-stage CPU protocol with separate message and action "
            "receipts, pass safety/budget/SIGUSR1/fresh-resume controls, and keep "
            "H100 closed until that evidence is sealed."
        ),
    }
    return {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": hashlib.sha256(DEFAULT_EXPERIMENT.read_bytes()).hexdigest(),
        "inputs": {
            "explicit_type_v1": {
                "sha256": hashlib.sha256(EXPLICIT_EVIDENCE.read_bytes()).hexdigest(),
                "evidence_root_sha256": explicit["evidence_root_sha256"],
                "projection_sha256": explicit["projection_sha256"],
            },
            "structural_v2": {
                "sha256": hashlib.sha256(STRUCTURAL_EVIDENCE.read_bytes()).hexdigest(),
                "evidence_root_sha256": structural["evidence_root_sha256"],
                "projection_sha256": structural["projection_sha256"],
            },
        },
        "projection": projection,
        "projection_sha256": sha256_json(projection),
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
        raise MessageActionAuditError("message/action audit drifted")
    return actual


def main() -> int:
    audit = write_audit()
    validate_audit()
    print(
        canonical_json(
            {
                "status": audit["status"],
                "projection_sha256": audit["projection_sha256"],
                "selected_candidate": audit["projection"]["selected_candidate"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
