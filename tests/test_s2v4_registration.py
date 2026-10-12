"""S2 v4 registration: the committed K0 section, its code's constants and freeze hygiene."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.s2_locale import ap_delta as D
from harness.s2_locale import k0_v4 as K
from harness.s2_locale import pins_table
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "program/preregistrations/s2-arabic-cua-locale-v4.md"
EXPERIMENT_ID = "s2-arabic-cua-locale-v4"
# The SHA-256 of the K0 section's text as committed before any Phase 0 result existed. A change
# here before the freeze must be a visible, recorded decision; after any Phase 0 result has been
# read it voids the commitment (registration, section "K0").
K0_SECTION_SHA256 = "ed38b953c7934169fcede7b45ec5dc1b568afd5855c6008830aada68cf131a03"
FROZEN = ("**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the "
          "freeze time and `git_head_at_freeze`.**")  # fmt: skip


def _k0_text() -> str:
    m = re.search(r"<!-- K0:BEGIN -->\n(.*?)<!-- K0:END -->", REG.read_text(encoding="utf-8"), re.S)
    assert m, "the K0 markers are missing"
    return m.group(1)


def test_k0_section_is_the_committed_text():
    assert hashlib.sha256(_k0_text().encode()).hexdigest() == K0_SECTION_SHA256


def test_k0_code_constants_match_the_text():
    text = _k0_text()
    assert f"at least {K.K_MIN} tasks are admitted" in text
    assert "at least 95%" in text and K.SHARE == 0.95
    assert "at least 90%" in text and K.DESCRIPTOR_SHARE == 0.90
    assert f"max({K.TOL_FLOOR_PX}\npx" in text or f"max({K.TOL_FLOOR_PX} px" in text
    assert f"rows 0-{K.SHELL_ROWS - 1}" in text
    for task in K.PD_VISIBLE_DEV:
        assert f"`{task}`" in text
    for task in K.C1_TASKS:
        assert f"`{task}`" in text
    assert ", ".join(K.ADMISSION_CELLS[:-1]) + ", " + K.ADMISSION_CELLS[-1] in text


def test_freezable_and_names_itself():
    text = REG.read_text(encoding="utf-8")
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text), "freeze refuses placeholders"
    assert "@@" not in text, "an unfilled marker"
    assert ("preregister.py freeze s2-arabic-cua-locale-v4 "
            "program/preregistrations/s2-arabic-cua-locale-v4.md") in text
    assert text.startswith("# S2 v4:")


def _status_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("**Status: "))


def _row() -> dict | None:
    return L.ledger_row(ROOT)


def test_status_wording_follows_the_ledger():
    """The D32 defect class: before the freeze the status line is DRAFT, or (the status-fill
    commit) the frozen wording; once this id has a ledger row, only the frozen wording, and the
    file is the one the row froze."""
    text = REG.read_text(encoding="utf-8")
    status = _status_line(text)
    row = _row()
    if row is not None:
        assert status.startswith("**Status: frozen in") and "DRAFT" not in status
        assert row["path"] == L.REGISTRATION
        assert row["sha256"] == hashlib.sha256(REG.read_bytes()).hexdigest()
    else:
        assert status.startswith(("**Status: DRAFT", "**Status: frozen in"))
    # the freeze procedure states the frozen wording verbatim
    assert " ".join(FROZEN.split()) in " ".join(text.split())


def test_registration_freezes_against_a_scratch_ledger(tmp_path):
    """The freeze command accepts this file; the real ledger is not touched."""
    from scripts import preregister

    ledger = tmp_path / "ledger.jsonl"
    real = (ROOT / L.LEDGER).read_bytes()
    row = preregister.freeze(REG, EXPERIMENT_ID, ledger=ledger)
    assert row["path"] == L.REGISTRATION
    assert row["sha256"] == hashlib.sha256(REG.read_bytes()).hexdigest()
    assert (ROOT / L.LEDGER).read_bytes() == real


def test_code_and_inputs_of_record_table_is_the_tree():
    text = REG.read_text(encoding="utf-8")
    assert pins_table.read(text) == pins_table.digests(ROOT)


def test_code_of_record_includes_the_shared_code_the_lanes_import():
    """The table lists every repository file the lane, probe, gold slot, oracle, K0 reader and
    ap_delta import (found by walking their imports), the guest scripts, and harness/q2's closed
    world, besides the S2 v4 files."""
    from harness.q2.vm.manifest import closed_world

    listed = set(pins_table.read(REG.read_text(encoding="utf-8")))
    closure = set(pins_table.import_closure(ROOT))
    for shared in ("harness/q2_stage1/lane.py", "harness/q2_stage1/driver.py",
                   "harness/q2_stage1/osworld_live.py", "harness/q2/vm/desktop.py",
                   "harness/q2/vm/guest_http.py", "harness/q2/vm/driver.py",
                   "harness/q2_mutation_k2/executor.py", "harness/q2_mutation/controls.py",
                   "harness/q2_mutation/offline_eval.py", "harness/s2_locale/k0_v4.py"):
        assert shared in closure, shared
    assert closure | set(pins_table.GUEST) | set(closed_world(str(ROOT))) <= listed


def test_registration_states_the_pinned_digests():
    flat = " ".join(REG.read_text(encoding="utf-8").split())
    assert L.CENSUS_SHA256 in flat and L.PD_CACHE_FILES_SHA256 in flat
    assert D.K1_PLAN_SHA256 in flat
    golds = hashlib.sha256((ROOT / L.GOLDS).read_bytes()).hexdigest()
    assert golds in flat
    pins = json.loads((ROOT / L.IMAGES).read_text())
    assert pins["build"]["derived_base"]["sha256"] in flat
    for cell, entry in pins["cells"].items():
        assert f"| {cell} | `{entry['sha256']}` |" in flat, cell
    assert pins["build"]["dir"].rsplit("/", 2)[-2] in flat or pins["build"]["dir"] in flat


def test_registration_states_the_one_infrastructure_rule_everywhere():
    text = REG.read_text(encoding="utf-8")
    p07 = text.split("### P0.7", 1)[1].split("### P0.8", 1)[0]
    phase1 = text.split("## Phase 1 (", 1)[1].split("## Estimands", 1)[0]
    infra = text.split("## Infrastructure failures and exclusions", 1)[1].split("## Data rights")[0]
    for section in (p07, phase1, infra):
        flat = " ".join(section.split())
        assert "status of 500 or above" in flat and "infrastructure loss" in flat
        assert "returncode" in flat
