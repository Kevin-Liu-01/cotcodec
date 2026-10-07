from __future__ import annotations

import hashlib
import json
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


# ---- Pre-freeze audit (2026-10-07) ---------------------------------------- #

DESIGN = (
    Path(__file__).resolve().parents[1] / "program" / "evidence" / "2026-10-07" / "holo3-v2-design"
)


def _design() -> dict:
    return json.loads((DESIGN / "receipt-v2-design.json").read_text())


def test_v2_status_line_reads_correctly_once_frozen() -> None:
    text = V2.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[2].startswith("**Status: frozen in `program/preregistrations/ledger.jsonl`; see")
    for stale in ("DRAFT", "Not frozen", "not frozen", "owner's review", "Freeze it with"):
        assert stale not in text, stale
    for stale in ("needs the owner's acceptance", "If the owner withholds", "The owner decides"):
        assert stale not in text, stale


def test_v2_states_the_d15_conditions_and_audit_fixes() -> None:
    flat = " ".join(V2.read_text(encoding="utf-8").split())
    assert "nominal family-wise error rate over rules (a), (b) and (d) is therefore 0.10" in flat
    assert f'"{v2.RULE_D_BLINDING_NOTE}"' in flat
    assert "does not reproduce is reported as EXPLORATORY" in flat
    assert (
        "key named exactly `error`, `exception`, `traceback` or `tool_error` (case-sensitive)"
        in (flat)
    )
    assert "each field matched on its own (no match spans two fields)" in flat
    assert "`--tarball-receipt`" in flat and "Concordant tasks (rule (a))" in flat
    assert f"(`{v2.V1_CONFIG_BLOB_MANIFEST}`)" in flat
    decisions = V2.read_text(encoding="utf-8").split("\n## Design decisions\n", 1)[1]
    numbers = re.findall(r"^(\d+)\. \*\*", decisions, re.MULTILINE)
    assert numbers == [str(i) for i in range(1, len(numbers) + 1)] and len(numbers) >= 21


def test_design_receipt_is_from_the_current_code_and_matches_its_readme() -> None:
    receipt = _design()
    assert receipt["status"] == "PASS" and receipt["label"] == "DESIGN"
    assert receipt["code"]["code_files_dirty"] is False
    root = Path(__file__).resolve().parents[1]
    for rel, digest in receipt["code"]["files_sha256"].items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel
    readme = (DESIGN / "README.md").read_text()
    digest = hashlib.sha256((DESIGN / "receipt-v2-design.json").read_bytes()).hexdigest()
    assert f"`{digest}`" in readme and receipt["code"]["git_head"] in readme
    assert receipt["code"]["git_head"] in V2.read_text(encoding="utf-8")


def test_power_tables_in_the_registration_match_the_design_receipt() -> None:
    design = _design()["results"]["v2_design"]
    text = V2.read_text(encoding="utf-8")
    d_rows = re.findall(r"^\| (\d+), (\d+) \|(.*)\|$", text, re.MULTILINE)
    assert len(d_rows) == 7
    by_d = {
        (r["L_tasks_web"], r["L_tasks_offline"], r["odds_ratio"]): r
        for r in design["rule_d_power_exact"]
    }
    for web, off, cells in d_rows:
        for psi, cell in zip((1.0, 3.0, 5.0, 10.0, 30.0), cells.split("|"), strict=True):
            row = by_d[(int(web), int(off), psi)]
            assert cell.strip() == f"{row['power']:.3f} ({row['power_test_alone']:.3f})"
    a_rows = re.findall(
        r"^\| ([x/])(\d+(?:\.\d+)?)(, all tasks| on (\d+)% of tasks) \| (\S+) \((\S+)\) \|$",
        text,
        re.MULTILINE,
    )
    assert len(a_rows) == 14
    by_a = {
        (r["fraction_of_tasks_shifted"], r["run2_step_factor"]): r
        for r in design["rule_a_power_by_outcome"]
    }
    for sign, factor, _, percent, primary, concordant in a_rows:
        ratio = float(factor) if sign == "x" else 1 / float(factor)
        fraction = int(percent) / 100 if percent else 1.0
        row = by_a[(fraction, round(ratio, 4))]
        assert primary == f"{math.floor(row['power_mean'] * 1000 + 0.5) / 1000:.3f}", row
        concordant_value = row["power_mean_concordant_tasks"]
        assert concordant == f"{math.floor(concordant_value * 1000 + 0.5) / 1000:.3f}", row
    size = design["rule_d_size_all_allocations"]
    assert size["max_size"] < v2.ALPHA_D and f"{size['max_size']}" in text
    assert size["allocations"] == 14_455 and "14,455 allocations" in text
