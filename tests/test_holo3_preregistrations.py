from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import pytest

from harness import holo3_v2 as v2

ROOT = Path(__file__).resolve().parents[1] / "program" / "preregistrations"
V1 = ROOT / "q2-holo3-rerun-audit-v1-posthoc.md"
V2 = ROOT / "q2-holo3-rerun-audit-v2.md"
V1_SHA256 = "e9a947a303600b091f60ef3781f40dfcb52b91417b380ddcde26e01be9450b97"


def test_v1_record_holds_the_original_registration_byte_for_byte() -> None:
    text = V1.read_text(encoding="utf-8")
    assert text.startswith("# q2-holo3-rerun-audit-v1-posthoc")
    assert "**Status: POST-HOC.**" in text
    block = text.split("```text\n", 1)[1].rsplit("```\n", 1)[0]
    assert hashlib.sha256(block.encode()).hexdigest() == V1_SHA256


def test_v2_draft_freezes_the_rule_lists_the_code_uses() -> None:
    text = V2.read_text(encoding="utf-8")
    for name in sorted(v2.LIVE_OR_CLOCK_GETTERS | v2.LIVE_IF_REMOTE_URL_GETTERS | v2.CLOCK_METRICS):
        assert f"`{name}`" in text, name
    for label, _ in v2.ENV_TEXT_PATTERNS:
        assert f"`{label}`" in text, label
    assert "EXPLORATORY" in text
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text)


def test_v2_draft_states_the_thresholds_and_reference_the_code_uses() -> None:
    flat = " ".join(V2.read_text(encoding="utf-8").split())
    assert (v2.ALPHA_D, v2.ALPHA_A, v2.ALPHA_B) == (0.04, 0.01, 0.025)
    for alpha in ("0.04", "0.01", "0.025"):
        assert f"at a fixed alpha of {alpha}" in flat, alpha
    threshold = v2.SHIFT_LOG_THRESHOLD
    assert threshold == pytest.approx(math.log(1.10)) and "|m| >= ln(1.10)" in flat
    assert v2.SHARE_BAR == 0.5 and v2.SPECIFICITY_LIMIT == 0.20
    assert v2.PROBE_BYTES == 250_000_000 and "250,000,000 compressed bytes" in flat
    assert v2.PRIMARY_ENV_CRITERIA == ("tool_error", "text")
    narrow = v2.NARROW_EXPECTED_GETTERS
    assert narrow == v2.LIVE_OR_CLOCK_GETTERS - {"time_diff_range"}
    assert "with a type in the L list except `time_diff_range`" in flat
    ref = v2.REGISTERED_H_REFERENCE
    assert ref is not None
    classes = ref["classes"]
    assert sum(classes.values()) == ref["tasks"]
    assert classes.get("step_cap", 0) + classes.get("premature_answer", 0) == ref["agent_side"]
    sentence = (
        f"{ref['tasks']} unique failures: environment {ref['environment']}, step cap "
        f"{classes.get('step_cap', 0)}, premature answer {classes.get('premature_answer', 0)}, "
        f"other {classes.get('other', 0)} (agent-side {ref['agent_side']})."
    )
    assert sentence in flat
    thresholds = v2.rule_b_thresholds(14, ref)
    assert (
        f"environment at least {thresholds['environment']} of 14 (the share bar binds) and "
        f"agent-side at least {thresholds['agent_side']} of 14" in flat
    )
