from __future__ import annotations

from scripts.audit_orchvar_message_action_transport import build_audit


def test_transport_audit_selects_only_two_stage_candidate() -> None:
    projection = build_audit()["projection"]
    admitted = [
        name for name, row in projection["candidates"].items() if row["admitted"]
    ]
    assert admitted == ["message_then_action_two_stage"]
    assert projection["cohorts"]["explicit_type_v1"] == {
        **projection["cohorts"]["explicit_type_v1"],
        "research_message_presence_count": 6,
        "inner_action_valid_count": 5,
        "registered_parse_valid_count": 0,
    }
    assert projection["cohorts"]["structural_v2"] == {
        **projection["cohorts"]["structural_v2"],
        "research_message_presence_count": 1,
        "inner_action_valid_count": 5,
        "registered_parse_valid_count": 1,
    }
    assert projection["external_model_calls"] == 0
