"""The q2-stage1-successor-e-v1 draft: it names the code and plan it runs, keeps S1a's code of
record unchanged, states the design study's numbers as they are, and cannot be frozen
half-filled."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from harness.q2_stage1e import lane as LE
from harness.q2_stage1e import plan as PE

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / LE.REGISTRATION
S1A = ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md"
LEDGER = ROOT / LE.LEDGER
DECISIONS = ROOT / "program/decisions.md"
D82_SUMMARY = ROOT / "program/evidence/2026-10-11/q2-mutation-adjudication-v2/summary.json"
R04_ID = "r04-checker-nuisance-invariance-v1"  # main's ledger row 18, frozen after E's draft
STUDY = ROOT / "program/evidence/2026-10-10/q2-next-step-design-study"
EVIDENCE = ROOT / "program/evidence/2026-10-11/q2-stage1-successor-e"
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64}|FILL)` \|$")
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402
import render_q2e_manifest as builder  # noqa: E402

E_FILES = (
    "harness/q2_stage1e/__init__.py",
    "harness/q2_stage1e/plan.py",
    "harness/q2_stage1e/records.py",
    "harness/q2_stage1e/driver.py",
    "harness/q2_stage1e/lane.py",
    "harness/q2_stage1e/analysis.py",
    "harness/q2_stage1e/section15.py",
    "scripts/render_q2e_manifest.py",
    "infra/slurm/host-single-node/q2e-vm.sbatch",
    "experiments/manifests/q2-stage1e/dev-smoke-v1.json",
    "program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json",
)
INFRA_FILES = (
    "infra/slurm/host-single-node/docker-research.sbatch",
    "scripts/verify_compute_provenance.py",
    "scripts/check_compute_env.sh",
    "scripts/fetch_open_model.py",
    "scripts/exec_research_workload.py",
    "scripts/build_vllm_overlay_on_h100.sh",
    "scripts/extract_discovery_source_archive.py",
    "ops/s1a-analysis/cpu-step.sbatch",
)
INFRA_MARK = "**Infrastructure E runs that neither table above pins.**"


def _text() -> str:
    return PREREG.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    return text.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]


def _frozen() -> bool:
    return LE.frozen(ROOT)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(section: str) -> dict[str, str]:
    out = {}
    for line in section.splitlines():
        m = ROW.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def test_s1a_code_of_record_is_unchanged():
    """G-E2: every file of S1a section 20 keeps the digest S1a states."""
    rows = _rows(_section(S1A.read_text(encoding="utf-8"), "20. Code of record"))
    assert len(rows) == 75
    changed = {p: s for p, s in rows.items() if _sha(ROOT / p) != s}
    assert not changed, f"S1a code-of-record files changed: {sorted(changed)}"


def _code_tables() -> tuple[dict[str, str], dict[str, str]]:
    """Section 23's two tables: E's own files, and the infrastructure E runs."""
    own, infra = _section(_text(), "23. Code of record").split(INFRA_MARK, 1)
    return _rows(own), _rows(infra)


def test_e_code_of_record_is_the_tree():
    rows, infra = _code_tables()
    assert tuple(rows) == E_FILES and tuple(infra) == INFRA_FILES
    for table in (rows, infra):
        assert all(v != "FILL" for v in table.values()), "section 23 has unfilled digests"
        assert {p: _sha(ROOT / p) for p in table} == table


def _module_file(name: str) -> Path | None:
    path = ROOT.joinpath(*name.split("."))
    if path.with_suffix(".py").is_file():
        return path.with_suffix(".py")
    if (path / "__init__.py").is_file():
        return path / "__init__.py"
    return None


def _imports(path: Path) -> set[Path]:
    """In-repo modules a file imports anywhere (lazy imports included), with their packages,
    and the bare-name imports of ``scripts/`` modules (the renderers put ``scripts/`` on the
    path)."""
    out: set[Path] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] not in ("harness", "scripts"):
                script = ROOT / "scripts" / f"{parts[0]}.py"
                if script.is_file():
                    out.add(script)
                continue
            for i in range(1, len(parts) + 1):
                found = _module_file(".".join(parts[:i]))
                if found is not None:
                    out.add(found)
    return out


def test_every_module_e_imports_is_pinned():
    """Every in-repo module E's Python files import, transitively, is in S1a's section 20 or
    in E's own table, so no file E runs is left unpinned."""
    s1a = _rows(_section(S1A.read_text(encoding="utf-8"), "20. Code of record"))
    own, _ = _code_tables()
    stack = [ROOT / p for p in own if p.endswith(".py")]
    seen: set[Path] = set()
    while stack:
        path = stack.pop()
        if path not in seen:
            seen.add(path)
            stack += list(_imports(path))
    needed = {p.relative_to(ROOT).as_posix() for p in seen}
    missing = sorted(needed - set(s1a) - set(own))
    assert not missing, f"section 23 lacks {missing}"
    assert (
        "harness/q2_stage1/lane.py" in needed and "scripts/render_q2_stage1_manifest.py" in needed
    )


def test_the_registration_names_the_committed_plan():
    plan = PE.load_plan(ROOT / PE.PLAN_FILE)
    text = _text()
    assert LE.PLAN_LINE.format(sha=plan["plan_sha256"]) in text
    assert _sha(ROOT / PE.PLAN_FILE) in text
    assert PE.render_plan(ROOT) == plan
    assert PE.COST_MODEL_SHA256 in text and PE.S1A_PLAN_SHA256 in text


def test_caps_stated_are_the_plans():
    plan = PE.load_plan(ROOT / PE.PLAN_FILE)
    section = " ".join(_section(_text(), "7. Jobs, caps and the 8 GPU-h count").split())
    assert plan["caps_minutes"] == {"E-9B": 52, "E-4B": 48, "OE": 3, "OE_retry": 3}
    assert "| 9B | 185.426773 | 104.60958 | 2,199.93 | 2,885.10 | 51.09 | **52** |" in section
    assert "| 4B | 173.047879 | 92.870499 | 2,048.31 | 2,694.06 | 47.90 | **48** |" in section
    assert f"**{plan['total_cap_minutes']} (6.767 GPU-h)**" in section


NUM = r"([\d.]+)"
CAL_ROW = re.compile(
    rf"^\| (P0|PR|P4|P4sf) \| {NUM} \({NUM} / {NUM}\) \| {NUM} \({NUM} / {NUM}\) "
    rf"\| {NUM} \| {NUM} \| {NUM} / {NUM} / {NUM} \| {NUM} / {NUM} \| {NUM} \|$"
)


def test_power_statement_is_the_design_studys():
    """Section 12's per-calibration rows equal the design study's merged outputs for E."""
    section = _section(_text(), "12. Operating characteristics: the registered power statement")
    rows = [CAL_ROW.match(line.strip()) for line in section.splitlines()]
    rows = [m for m in rows if m]
    assert [m.group(1) for m in rows] == ["P0", "PR", "P4", "P4sf"]
    for m in rows:
        cells = json.loads((STUDY / f"designs-{m.group(1)}.json").read_text())["cells"]
        fit, pim, null, two = (cells[f"E-K113-S4R1|{s}"]["summary"]
                               for s in ("fitted", "piM", "null", "pi2M"))  # fmt: skip
        expected = [
            fit["P_DR2_decisive"], fit["DR2"]["Present"], fit["DR2"]["Near-equivalent"],
            fit["P_DR5_decisive"], fit["DR5"]["NO-GO"], fit["DR5"]["GO"],
            fit["P_both_inconclusive"], pim["P_DR5_decisive"], null["DR2"]["Near-equivalent"],
            null["DR5"]["NO-GO"], null["DR2"]["Present"], two["P_DR2_decisive"], two["DR5"]["GO"],
        ]  # fmt: skip
        stated = [float(m.group(i)) for i in range(2, 15)]
        assert stated == [round(v + 1e-9, 2) for v in expected], m.group(1)
        assert float(m.group(15)) == round(fit["delta_ci90_width"]["median"] * 100 + 1e-9, 1)
        assert cells["E-K113-S4R1|fitted"]["cost"]["caps_min"] == 406


def test_cap_check_and_analysis_identity_evidence():
    caps = json.loads((EVIDENCE / "cap-sufficiency.json").read_text())
    jobs = caps["e_jobs"]
    section = " ".join(_section(_text(), "7. Jobs, caps and the 8 GPU-h count").split())
    for size in ("9B", "4B"):
        for scenario in ("as_measured", "slots_10pct_longer", "five_pct_lost_and_requeued"):
            assert jobs[f"{size}/{scenario}"]["p_complete_before_usr1"] == 1.0
    assert jobs["9B/slots_20pct_longer"]["p_complete_before_usr1"] == 1.0
    assert f"| {jobs['4B/slots_20pct_longer']['p_complete_before_usr1']} |" in section
    assert all(round(abs(v["realized_span_s"] - v["replayed_span_s"]), 1) <= 0.2
               for v in caps["s1a_replay_check"].values())  # fmt: skip
    identity = json.loads((EVIDENCE / "analysis-identity.json").read_text())
    for name, v in identity["s1a_committed_readings"].items():
        assert not v["estimates_differing"] and all(v["tests_equal"].values()), name
        assert v["DR2_equal"] and v["DR5_equal"] and v["estimates_compared"] == 18
    assert all(v["equal"] for v in identity["design_study_analyse_at_S4_R1"].values())
    assert identity["n_boot"] == identity["n_randomization"] == 10_000


def test_the_draft_cannot_be_frozen_until_every_slot_is_filled(tmp_path):
    if _frozen():
        pytest.skip("frozen: the ledger row binds the file")
    text = _text()
    assert "TBD" in text.split("\n\n", 2)[1], "the status paragraph must hold the placeholder"
    copy = tmp_path / LE.REGISTRATION
    copy.parent.mkdir(parents=True)
    copy.write_text(text, encoding="utf-8")
    with pytest.raises(preregister.PreregistrationError, match="TBD"):
        preregister.freeze(copy, LE.EXPERIMENT_ID, ledger=tmp_path / LE.LEDGER, root=tmp_path)


def test_only_the_open_slots_keep_the_draft_from_freezing_and_the_lane_then_admits_e(tmp_path):
    """With every open slot filled on a scratch copy, the guard freezes the file, and E's lane
    accepts an E1 manifest rendered from the plan on that frozen tree."""
    if _frozen():
        pytest.skip("frozen: the ledger row binds the file")
    for rel in (LE.SPLITS, PE.PLAN_FILE):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    copy = tmp_path / LE.REGISTRATION
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text(re.sub(r"\bTBD\b", "filled", _text()), encoding="utf-8")
    row = preregister.freeze(copy, LE.EXPERIMENT_ID, ledger=tmp_path / LE.LEDGER, root=tmp_path)
    assert row["experiment_id"] == LE.EXPERIMENT_ID
    assert LE.frozen_registration(tmp_path)["sha256"] == _sha(copy)
    import test_q2_stage1e as T

    m = builder.vm_manifest(host=T.HOST, source_dir=tmp_path, plan_path=PE.PLAN_FILE,
                            size="9B", session="E1")  # fmt: skip
    assert len(LE.validate_manifest(m, tmp_path)["slots"]) == 226
    with copy.open("a") as handle:
        handle.write("edited after the freeze\n")
    with pytest.raises(LE.LaneError, match="changed after the freeze"):
        LE.validate_manifest(m, tmp_path)


def test_open_slots_and_the_frozen_status_wording():
    text = _text()
    joined = " ".join(text.split())
    if _frozen():
        assert text.startswith("# Preregistration: q2-stage1-successor-e-v1")
        assert "**Status: frozen in `program/preregistrations/ledger.jsonl`" in text
        assert "TBD" not in text and "DRAFT" not in text.split("\n- ", 1)[0]
        return
    status = text.split("\n\n", 2)[1]
    assert status.startswith("**Status: DRAFT.") and "no ledger row" in status
    assert text.count("TBD") == 5
    for slot in ("disclosure 10). Result: TBD", "before the freeze. Result: TBD",
                 "Audit record: TBD", "(decision id): TBD"):  # fmt: skip
        assert slot in joined, slot
    frozen = _section(text, "25. Pre-freeze review log and the freeze").split("> ", 1)[1]
    assert "**Status: frozen in `program/preregistrations/ledger.jsonl`" in frozen


def test_s1a_is_not_pooled_and_its_rules_are_unchanged():
    joined = " ".join(_text().split())
    assert "E is its own sample." in joined
    assert "No E estimate, test, rule or prediction reads S1a's sessions." in joined
    assert "not registered inference; no rule, test or prediction reads it" in joined
    from harness.q2_stage1 import rules

    assert (rules.M_SMALL, rules.M_9B, rules.EQUIVALENCE_MARGIN, rules.PI_EQUIVALENCE_BOUND,
            rules.DR0_CELL_LOSS, rules.DR1_FLOOR, rules.P1_MIN_EXCESS) == (
        0.13, 0.18, 0.075, 0.12, 0.05, 0.10, 0.01)  # fmt: skip
    assert not any(line.strip().startswith(("<", "TBD")) for line in _text().splitlines())


def test_power_statement_ranges_are_the_design_studys():
    fits = [json.loads((STUDY / f"designs-{c}.json").read_text())["cells"]["E-K113-S4R1|fitted"]
            ["summary"] for c in ("P0", "PR", "P4", "P4sf")]  # fmt: skip

    def span(key, scale=1.0, digits=2):
        values = [round(f[key] * scale + 1e-9, digits) for f in fits]
        return f"{min(values):.{digits}f}-{max(values):.{digits}f}"

    joined = " ".join(_section(_text(), "12. Operating characteristics: the registered "
                               "power statement").split())  # fmt: skip
    assert f"| DR2 decisive | {span('P_DR2_decisive')} |" in joined
    assert f"| DR5 NO-GO | {span('P_DR5_decisive')} |" in joined
    assert f"| Both rules inconclusive (S1a's outcome) | {span('P_both_inconclusive')} |" in joined
    assert f"p_X ≤ 0.025 in {span('P_px_le_0025', 100, 0)}% of data sets" in joined
    assert f"p_δ ≤ 0.025 in only {span('P_pdelta_le_0025', 100, 0)}%" in joined
    assert f"falls below 0.12 in {span('P_pi_ub_below_0.12', 100, 0)}%" in joined
    assert all(f["P_DR1_drop_4B"] == 0.0 for f in fits)


# Section 21's sign-off slot: one decision id, filled just before the freeze.
SIGNOFF_SLOT = re.compile(r"^- Program sign-off of items 1-14 \(decision id\): (.*)$", re.M)
DECISION_HEADING = re.compile(r"^\*\*(D\d+)\. (.+?)\*\*", re.M | re.S)


def _decision_entries(decisions: str) -> dict[str, tuple[str, str]]:
    """Each decision of ``program/decisions.md`` by id: its bold heading and its whole entry
    (to the next decision heading), whitespace folded."""
    heads = list(DECISION_HEADING.finditer(decisions))
    out = {}
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(decisions)
        out[head.group(1)] = (
            " ".join(head.group(2).split()),
            " ".join(decisions[head.start() : end].split()),
        )
    return out


def _check_signoff(text: str, decisions: str) -> str:
    """The slot holds one decision id whose heading in ``program/decisions.md`` names this
    registration and whose entry signs items 1-14 of section 21."""
    slots = SIGNOFF_SLOT.findall(text)
    assert len(slots) == 1, "section 21 has one sign-off slot"
    decision_id = slots[0].strip()
    assert re.fullmatch(r"D\d+", decision_id), f"the slot takes one decision id: {decision_id!r}"
    entries = _decision_entries(decisions)
    assert decision_id in entries, f"{decision_id} is not a decision heading in decisions.md"
    heading, entry = entries[decision_id]
    assert f"`{LE.EXPERIMENT_ID}`" in heading, f"{decision_id}'s heading does not name E"
    assert "items 1-14" in entry, f"{decision_id} does not sign items 1-14"
    return decision_id


def test_the_signoff_slot_names_the_decision_that_signs_items_1_14():
    """Frozen: section 21's id is a decision of ``program/decisions.md`` that names E and
    signs items 1-14. Draft: a decision of that form passes on a scratch copy filled as the
    freeze fills it, and an id that is not such a decision is refused."""
    decisions = DECISIONS.read_text(encoding="utf-8")
    text = _text()
    if _frozen():
        _check_signoff(text, decisions)
        return
    slot = "- Program sign-off of items 1-14 (decision id): TBD"
    assert text.count(slot) == 1
    signed = decisions + (
        f"\n**D999. Q2 successor E `{LE.EXPERIMENT_ID}` is signed off for the freeze.**\n"
        "The program signs items 1-14 of its section 21.\n"
    )
    assert _check_signoff(text.replace(slot, slot[:-3] + "D999"), signed) == "D999"
    for wrong in ("D82", "D80", "D83", "D999, D82", "TBD"):
        with pytest.raises(AssertionError):
            _check_signoff(text.replace(slot, slot[:-3] + wrong), decisions)
    unsigned = decisions + f"\n**D998. `{LE.EXPERIMENT_ID}` noted.** Nothing signed.\n"
    with pytest.raises(AssertionError, match="does not sign"):
        _check_signoff(text.replace(slot, slot[:-3] + "D998"), unsigned)


def test_the_freeze_runs_on_a_tree_that_holds_mains_ledger():
    """E freezes on the tree with ``main`` merged, so its row follows main's rows (R04 is row
    18): a freeze on the unmerged branch would fork the hash chain."""
    rows = preregister.read_ledger(LEDGER)  # checks the hash chain end to end
    ids = [r["experiment_id"] for r in rows]
    assert R04_ID in ids, "main's ledger rows are not on this tree: merge main first"
    if _frozen():
        assert ids.count(LE.EXPERIMENT_ID) == 1
        assert ids.index(R04_ID) < ids.index(LE.EXPERIMENT_ID)
    else:
        assert LE.EXPERIMENT_ID not in ids


def test_no_draft_only_statement_outside_the_slots():
    """Statements true only while the file is a draft would survive the freeze unchecked
    (the D32 class): outside the five slots, none may remain."""
    joined = " ".join(_text().split())
    for phrase in ("entry point have not run on the host",
                   "None yet. The pre-freeze audit of G-E6 is recorded here"):  # fmt: skip
        assert phrase not in joined, phrase
    log = _section(_text(), "25. Pre-freeze review log and the freeze")
    assert "**Audit 1**" in log and "| B1 |" in log and "| N12 |" in log


def test_d82_gold_defect_tasks_are_stated_and_are_the_plans():
    """Section 9 states D82's three gold-defect tasks, as the adjudication record has them,
    and the plan carries them for the sensitivity; S1a's flagged list is unchanged."""
    gold = json.loads(D82_SUMMARY.read_text())["before_after"]["after_a"]["audit"][
        "gold_defect_tasks"
    ]
    plan = PE.load_plan(ROOT / PE.PLAN_FILE)
    assert plan["gold_defect_tasks_d82"] == gold == list(PE.D82_GOLD_DEFECT_TASKS)
    text = _text()
    for heading in ("9. Outcomes and checker corrections", "21. Design decisions for sign-off"):
        section = _section(text, heading)
        assert all(f"`{task[:8]}`" in section for task in gold), heading
    joined = " ".join(_section(text, "9. Outcomes and checker corrections").split())
    assert "changes neither the correction" not in joined
    assert "**The D82 gold-defect sensitivity**" in joined
    assert "No primary set, outcome, decision rule or DR changes" in joined
