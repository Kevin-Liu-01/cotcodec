"""q2-action-path-v2 and its two addenda: the inputs they pin match the repository.

v1 (q2-action-path-v1 and its addenda) is frozen in the ledger and invalid on C2 (decision
D40); its files must stay as frozen, and v2's tables must equal v1's except for the rows
v2's section 24 names.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import corpus

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-action-path-v2.md"
INPUTS = ROOT / "program/preregistrations/q2-action-path-v2-inputs.md"
EXECUTOR = ROOT / "program/preregistrations/q2-action-path-v2-executor.md"
DOCS = (PREREG, INPUTS, EXECUTOR)
V1 = {
    "q2-action-path-v1": ROOT / "program/preregistrations/q2-action-path-v1.md",
    "q2-action-path-v1-inputs": ROOT / "program/preregistrations/q2-action-path-v1-inputs.md",
    "q2-action-path-v1-executor": ROOT / "program/preregistrations/q2-action-path-v1-executor.md",
}
# The rows of v2's frozen tables that decision D40 changes (main section 24, item 7);
# every other row must equal v1's.
D40_ROWS = {
    PREREG: {"harness/q2/action_path/l0_raw_prediction_v2.yaml"},
    INPUTS: {
        "harness/q2/action_path/order.py",
        "harness/q2/vm/manifest.py",
        "harness/q2/vm/driver.py",
        "harness/q2/action_path/acceptance.py",
    },
    EXECUTOR: {
        "harness/q2/action_path/acceptance.py",
        "scripts/render_q2_action_path_manifest.py",
        "harness/q2/vm/driver.py",
        "harness/q2/vm/manifest.py",
    },
}
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
LINT = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # scripts/preregister.py's freeze rule


def _pinned(doc: Path = PREREG) -> dict[str, str]:
    text = doc.read_text(encoding="utf-8")
    section = text.split("Frozen with this file", 1)[1].split("\n\n", 2)[1]
    rows = {}
    for line in section.splitlines():
        match = ROW.match(line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_every_pinned_input_matches_its_digest(doc):
    rows = _pinned(doc)
    assert len(rows) >= 20
    for relative, digest in rows.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == digest, f"{relative} changed; refresh {doc.name}"


FROZEN_STATUS = (
    "**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger\n"
    "row for the freeze time and `git_head_at_freeze`.**"
)
FREEZE_ORDER = ("`q2-action-path-v2`", "`q2-action-path-v2-inputs`", "`q2-action-path-v2-executor`")


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_drafts_pass_the_freeze_lint_with_the_frozen_status(doc):
    """A frozen file cannot be edited, so each status paragraph has the frozen wording
    before the freeze (decision D39, as D32 required for Q3): the ledger row, the freeze
    order and what may not run before the row exists."""
    text = doc.read_text(encoding="utf-8")
    assert not LINT.search(text)
    status = text.split("\n\n")[1]
    assert status.startswith(FROZEN_STATUS)
    for stale in ("DRAFT", "Draft", "Not frozen", "not frozen", "owner reviews", "owner freezes"):
        assert stale not in status
    positions = [status.find(name) for name in FREEZE_ORDER]
    assert -1 not in positions and positions == sorted(positions), positions
    assert "No acceptance trial" in status and "may run before this row exists" in status
    controls = "no C1 or C3" if doc == EXECUTOR else "no C2, C1 or C3"
    assert controls in status
    assert "q2-action-path-v1" not in status


def test_v1_stays_as_frozen_in_the_ledger():
    """v1's three registrations are unchanged since their ledger rows (decision D40)."""
    from scripts import preregister

    for experiment, path in V1.items():
        row = preregister.verify(experiment)
        assert row["path"] == path.relative_to(ROOT).as_posix()


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_v2_tables_are_v1s_except_the_rows_d40_changes(doc):
    v1 = _pinned(V1[doc.stem.replace("-v2", "-v1")])
    v2 = _pinned(doc)
    assert set(v1) <= set(v2)
    differ = {path for path, digest in v2.items() if v1.get(path) != digest}
    assert differ == D40_ROWS[doc], sorted(differ ^ D40_ROWS[doc])


def test_v2_names_its_changes_from_v1_and_v1s_outcome():
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        assert "Changes from v1 (D40)" in text, doc.name
        changes = " ".join(text.split("Changes from v1 (D40)", 1)[1].split())
        for path in D40_ROWS[doc]:
            assert path.split("/")[-1] in changes, (doc.name, path)
    main = " ".join(PREREG.read_text(encoding="utf-8").split())
    assert "program/evidence/2026-10-08/q2-action-path-acceptance/" in main
    assert "not an a-priori prediction test" in main
    assert "one unpredicted failure" in main
    assert "seed-45 shuffle" in main


def _between(text: str, start: str, end: str) -> str:
    assert text.count(start) == 1, start
    part = text.split(start, 1)[1]
    assert end in part, end
    return " ".join(part.split(end, 1)[0].split())


# Decision D42: v1's C2 failure is in the tap's record of a key event queued during the
# shell's synchronous grab, and the shell received Super+d; D40 called it a transport defect.
STALE_CAUSE = ("verified real", "real at the X event level", "real in the X event record")
CORRECTED = ("queued during the shell's synchronous grab", "the shell received Super+d")


def test_v1s_c2_failure_is_stated_as_the_taps_record_not_delivery():
    """Sections 8 (C2), 24 (item 2) and 25 state the cause D42 corrected, and no part of the
    three registrations or v2's prediction file calls the failure real at the X event level."""
    prediction = ROOT / "harness/q2/action_path/l0_raw_prediction_v2.yaml"
    for path in (*DOCS, prediction):
        flat = " ".join(path.read_text(encoding="utf-8").split())
        for stale in STALE_CAUSE:
            assert stale not in flat, (path.name, stale)
        # "genuine transport defect" may appear only as the D40 reading that D42 corrects.
        for hit in re.finditer("genuine transport defect", flat):
            assert "D40" in flat[max(0, hit.start() - 120) : hit.start()], (path.name, hit)
    text = PREREG.read_text(encoding="utf-8")
    parts = {
        "section 8, C2": _between(text, "- **C2 (L0-raw failing set", "- **C3 (mutation score)"),
        "section 24, item 2": _between(
            text, "2. **C2 is a reproduction test", "3. **The manifest renderer"
        ),
        "section 25": _between(text, "- **The a-priori result.**", "- **Reported, not judged.**"),
    }
    for name, part in parts.items():
        for phrase in CORRECTED:
            assert phrase in part, (name, phrase)
    assert "recorded in the XRecord stream" in parts["section 8, C2"]
    assert "core state 0, without Mod4, in every repetition" in parts["section 8, C2"]
    assert "Decision D42 corrects D40's statement" in parts["section 8, C2"]
    assert "not the transport" in parts["section 8, C2"]
    assert "decision D42 corrects D40's reading" in parts["section 25"]
    item9 = _between(text, "9. **The cause D40 stated is corrected", "## 25.")
    assert "D42 keeps items 1-4 as drafted" in item9 and "accepts the exposure" in item9
    assert "changes no rule, number or frozen file" in item9
    section26 = " ".join(text.split("## 26.", 1)[1].split())
    assert "**What D42 decides, and what it leaves.**" in section26
    assert "D42 accepts the exposure" in section26


def test_the_correction_is_a_dated_decision_that_keeps_d40s_changes():
    """D42 exists in the decision log, corrects D40's cause and keeps its changes, and D40
    points to it; the registration cites the same decision."""
    log = (ROOT / "program/decisions.md").read_text(encoding="utf-8")
    d40 = " ".join(log.split("**D40. ", 1)[1].split("**D41. ", 1)[0].split())
    assert "D42 corrects the cause stated here" in d40
    head, d42 = log.split("**D42. ", 1)
    assert head.rstrip().endswith("## 2026-10-08")
    d42 = " ".join(d42.split("\n**D4", 1)[0].split())
    for phrase in (
        "D40's stated cause is corrected",
        "XIGrabModeSync",
        "the shell received Super+d",
        "not in delivery",
        "D40's three changes, and L0-raw's admission as a development layer at seed 42, "
        "stand as drafted",
        "v2 keeps the oracle's reading of events queued under a grab",
        "never makes a trial pass",
        "The remaining exposure is accepted",
        "127 of 127",
        "D40's author confirms or overrules it",
    ):
        assert phrase in d42, phrase
    assert "genuine transport defect" not in d42.split("Corrected cause:", 1)[1]
    assert "decision D42" in PREREG.read_text(encoding="utf-8")


def test_shell_grabbed_chords_have_modifier_state_after_the_grab_key():
    """Section 4.4 and D42: on the four chords GNOME Shell grabs, every reference event after
    the grab-activating key has a modifier state that is not empty, so an event the tap
    records with state 0 while it is queued under the grab can only fail its trial."""
    reference = json.loads(
        (ROOT / "harness/q2/action_path/rdev_reference.json").read_text(encoding="utf-8")
    )["entries"]
    grab_key = {
        "chord_super_d": "Super_L",
        "chord_alt_f4": "F4",
        "chord_alt_tab": "Tab",
        "chord_ctrl_alt_shift_r": "r",
    }
    for entry, key in grab_key.items():
        events = reference[entry]["events"]
        kinds = [(kind, keysym) for kind, keysym, _ in events]
        first = kinds.index(("KeyPress", key))
        after = events[first + 1 :]
        assert after and all(state for _, _, state in after), (entry, after)


CODE = {"ir.py", "vocab.py", "catalog.py", "rdev.py", "l0_raw.py", "volume.py"}
CODE |= {"build_catalog.py", "build_derived.py"}


def test_the_pins_cover_every_suite_input_file():
    main = set(_pinned(PREREG))
    every = main | set(_pinned(INPUTS)) | set(_pinned(EXECUTOR))
    folder = ROOT / "harness/q2/action_path"
    suite = {
        f"harness/q2/action_path/{p.name}"
        for p in folder.iterdir()
        if p.suffix in (".yaml", ".json", ".jinja") or p.name in CODE
    }
    assert suite <= every, suite - every
    assert {f"harness/q2/action_path/{name}" for name in CODE} <= main
    assert "harness/q2/vm/guest/xrecord_tap.py" in main
    code = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "harness/q2").rglob("*")
        if p.is_file()
        and p.suffix in (".py", ".json", ".yaml", ".md", ".jinja")
        and p.name not in ("__init__.py", "README.md")
        and "__pycache__" not in p.parts
    }
    unpinned = code - every
    assert not unpinned, sorted(unpinned)


def test_c2_cells_are_a_function_of_the_frozen_catalog():
    data = cat.load()
    cells = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
    expected = json.loads(json.dumps(corpus.l0_cells(data, cat.validate(data)["gating"])))
    assert cells["layers"]["L0-fixed"] == expected


def test_draft_passes_the_freeze_lint_and_states_the_committed_numbers():
    text = PREREG.read_text(encoding="utf-8")
    plan = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
    assert f"{plan['trials']:,} trials" in text
    assert f"{plan['sessions']:,}" in text and plan["order_sha256"] in text
    expressible = json.loads((ROOT / "harness/q2/action_path/expressible_entries.json").read_text())
    assert len(expressible["H-OSW"]["expressible"]) == 85 and "H-OSW 85" in text
    assert len(expressible["H-GA"]["expressible"]) == 79 and "H-GA 79" in text
    data = cat.load()
    certified = cat.certified_keysyms(data, cat.validate(data)["gating"])
    assert f"only the {len(certified)} keysyms" in text
    pattern = r"only the \d+ keysyms the\ngating entries use: (.*?)\n\(`catalog"
    listed = re.search(pattern, text, re.S)
    assert listed is not None
    assert sorted(re.findall(r"`([^`]+)`", listed.group(1))) == sorted(certified)
