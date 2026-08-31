from __future__ import annotations

from copy import deepcopy

from scripts.audit_orchvar_iterative_protocol_compatibility import (
    build_audit,
    infer_missing_tool_type,
)


def test_captured_outputs_show_partial_recovery_without_argument_coercion() -> None:
    audit = build_audit()
    projection = audit["projection"]
    assert projection["strict_parse_failures"] == 6
    assert projection["exact_shape_recoveries"] == 5
    assert projection["argument_schema_failures_after_inference"] == 1
    assert projection["full_recovery"] is False
    assert set(projection["unrecovered"]) == {"canary-reasoning-depth-01"}
    assert projection["adversarial_rejection_count"] == 6
    assert projection["executed_tool_calls"] == 0
    assert projection["external_model_calls"] == 0


def test_rule_only_infers_exact_discriminator_free_tool_shape() -> None:
    payload = {
        "planner_note": "Call.",
        "memory_update": None,
        "action": {"name": "lookup_reservation", "arguments": {}},
    }
    normalized = infer_missing_tool_type(payload)
    assert normalized["action"]["type"] == "tool"
    assert payload["action"] == {"name": "lookup_reservation", "arguments": {}}

    ambiguous = deepcopy(payload)
    ambiguous["action"]["response"] = "also finish"
    assert infer_missing_tool_type(ambiguous) is ambiguous
