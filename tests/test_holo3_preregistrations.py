from __future__ import annotations

import hashlib
import re
from pathlib import Path

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
