"""q2-action-path-v2 and its two addenda: the inputs they pin match the repository.

v1 (q2-action-path-v1 and its addenda) is frozen in the ledger and invalid on C2 (decision
D40); its files must stay as frozen, and v2's tables must equal v1's except for the rows
v2's sections 24 and 27 name (decisions D40 and D43).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
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
# The rows of v2's frozen tables that decisions D40 and D43 change (main section 24, item 7,
# and section 27); every other row must equal v1's.
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
D43_ROWS = {
    PREREG: set(),
    INPUTS: {
        "harness/q2/action_path/verdict.py",
        "harness/q2/vm/guest/guard.py",
        "harness/q2/vm/runner.py",
        "harness/q2/vm/suite.py",
    },
    EXECUTOR: {
        "harness/q2/vm/guest/guard.py",
        "harness/q2/vm/runner.py",
        "harness/q2/vm/suite.py",
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
def test_v2_tables_are_v1s_except_the_rows_d40_and_d43_change(doc):
    v1 = _pinned(V1[doc.stem.replace("-v2", "-v1")])
    v2 = _pinned(doc)
    assert set(v1) <= set(v2)
    differ = {path for path, digest in v2.items() if v1.get(path) != digest}
    expected = D40_ROWS[doc] | D43_ROWS[doc]
    assert differ == expected, sorted(differ ^ expected)


def test_v2_names_its_changes_from_v1_and_v1s_outcome():
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        assert "Changes from v1 (D40)" in text, doc.name
        changes = " ".join(text.split("Changes from v1 (D40)", 1)[1].split())
        for path in D40_ROWS[doc] | D43_ROWS[doc]:
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


# Decision D43: v1's C2 failure is in the tap's record of a key event queued during the
# shell's synchronous grab, and the shell received Super+d; D40 called it a transport defect.
STALE_CAUSE = ("verified real", "real at the X event level", "real in the X event record")
CORRECTED = ("queued during the shell's synchronous grab", "the shell received Super+d")


def test_v1s_c2_failure_is_stated_as_the_taps_record_not_delivery():
    """Sections 8 (C2), 24 (item 2) and 25 state the cause D43 corrected, and no part of the
    three registrations or v2's prediction file calls the failure real at the X event level."""
    prediction = ROOT / "harness/q2/action_path/l0_raw_prediction_v2.yaml"
    for path in (*DOCS, prediction):
        flat = " ".join(path.read_text(encoding="utf-8").split())
        for stale in STALE_CAUSE:
            assert stale not in flat, (path.name, stale)
        # "genuine transport defect" may appear only as the D40 reading that D43 corrects.
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
    assert "Decision D43 corrects D40's statement" in parts["section 8, C2"]
    assert "not the transport" in parts["section 8, C2"]
    assert "decision D43 corrects D40's reading" in parts["section 25"]
    assert "Re-judged with v2's judge" in parts["section 25"]
    item9 = _between(text, "9. **The cause D40 stated is corrected", "## 25.")
    assert "D43 decides instead" in item9 and "kind, keycode, keysym and order" in item9
    assert "Items 2-4 stand as drafted" in item9
    section26 = " ".join(text.split("## 26.", 1)[1].split("## 27.", 1)[0].split())
    assert "**What D43 decides, and what it leaves.**" in section26
    assert "so the exposure is gone" in section26


def test_d43_is_main_s_decision_and_the_branch_s_draft_does_not_survive():
    """D43 (main) corrects D40's cause and changes the judge; D40 is unedited; no decision on
    the action path is numbered D42 (that number is Q3's); the registrations cite D43."""
    log = (ROOT / "program/decisions.md").read_text(encoding="utf-8")
    d40 = " ".join(log.split("**D40. ", 1)[1].split("**D41. ", 1)[0].split())
    assert "D42" not in d40 and "D43" not in d40
    d42 = " ".join(log.split("**D42. ", 1)[1].split("**D43. ", 1)[0].split())
    assert d42.startswith("Q3 dense pre-check v2")
    d43 = " ".join(log.split("**D43. ", 1)[1].split("\n**D4", 1)[0].split())
    for phrase in (
        "D40's stated cause is corrected",
        "the shell did receive Super+d",
        "treats the modifier state of a key event recorded without the guard-guaranteed "
        "locked lock bits as unobservable",
        "judges it on kind, keycode, keysym and order only",
        "every other event is judged as before",
        "v2's C2 stays a reproduction test",
    ):
        assert phrase in d43, phrase
    for doc in (*DOCS, ROOT / "harness/q2/action_path/l0_raw_prediction_v2.yaml"):
        text = doc.read_text(encoding="utf-8")
        assert "D42" not in text, doc.name
        assert "D43" in text, doc.name


def test_section_27_records_d43_and_its_development():
    text = PREREG.read_text(encoding="utf-8")
    assert text.count("## 27. Changes for decision D43") == 1
    section = " ".join(text.split("## 27. Changes for decision D43", 1)[1].split())
    for phrase in (
        "modifier_state_observable",
        "condition (f)",
        "424 sessions",
        "for any other reason",
        "fault_drop_modifier",
        "126ff8b",
        "Jobs 834-839 repeat v1's final development runs 703-708",
        "| 832 | `q2ap-v2-d43-drop-omit-v1` |",
        "| 833 | `q2ap-v2-d43-drop-release-first-v1` |",
    ):
        assert phrase in section, phrase


# A run of eight words repeated inside one prose paragraph is how a botched edit shows: the
# D43 pass (31942e8) left a stub and a duplicated tail in section 26 ("...(none) neither
# would. A slow answer would fail an L0-fixed trial whose chord (none) neither would. Under
# v1's judge a slow answer would fail an L0-fixed trial whose chord..."). Tables are left
# out and each list item is its own paragraph. The one repeat allowed is v1's own wording
# (section 9, decision D33), which v2 keeps.
REPEATS_ALLOWED = ("the probability that some a1-a3 entry reaches its limit",)
ITEM = re.compile(r"^\s*(\d+\.|-) ")


def _prose_paragraphs(text: str) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        table = line.lstrip().startswith("|")
        if not line.strip() or table or line.startswith("#") or ITEM.match(line):
            if current:
                out.append(" ".join(current))
            current = [line] if ITEM.match(line) else []
            continue
        current.append(line)
    if current:
        out.append(" ".join(current))
    return out


def _repeated_runs(text: str, n: int = 8) -> set[str]:
    repeated = set()
    for paragraph in _prose_paragraphs(text):
        words = paragraph.lower().split()
        runs = Counter(" ".join(words[i : i + n]) for i in range(len(words) - n + 1))
        repeated |= {run for run, count in runs.items() if count > 1}
    return repeated


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_no_prose_paragraph_repeats_a_run_of_eight_words(doc):
    repeated = _repeated_runs(doc.read_text(encoding="utf-8"))
    assert {run for run in repeated if not any(run in ok for ok in REPEATS_ALLOWED)} == set()


def test_the_repeat_check_catches_the_garbled_section_26_sentence():
    garbled = (
        "probability up to 0.38 and A4's 276 almost surely, and at the observed rate\n"
        "(none) neither would. A slow answer would fail an L0-fixed trial whose chord\n"
        "(none) neither would. Under v1's judge a slow answer would fail an L0-fixed\n"
        "trial whose chord the shell received correctly, and the failure would count\n"
    )
    assert "a slow answer would fail an l0-fixed trial" in _repeated_runs(garbled)
    text = PREREG.read_text(encoding="utf-8")
    section26 = " ".join(text.split("## 26.", 1)[1].split("## 27.", 1)[0].split())
    assert "(none) neither would. Under v1's judge a slow answer" in section26
    assert section26.count("(none) neither would") == 1


def test_v2s_changes_and_what_they_leave_are_stated_consistently():
    """The header and section 15 name the same sections as v2's, the last of which is 27;
    section 24's lists of what is unchanged name D43's reading of the tap as the exception,
    and C3's equivalence comparison as what D43 leaves (sections 8, 26 and 27)."""
    text = PREREG.read_text(encoding="utf-8")
    flat = " ".join(text.split())
    last = max(int(n) for n in re.findall(r"^## (\d+)\. ", text, flags=re.M))
    assert last == 27
    assert f"sections 24-{last} are v2's" in flat
    assert f"v2's changes are in sections 24-{last}." in flat
    item6 = _between(text, "6. **Text added without a rule change.**", "7. **Frozen tables.**")
    item8 = _between(text, "8. **What does not change.**", "9. **The cause D40 stated")
    for item in (item6, item8):
        assert "apart from D43's reading of the tap (item 9 and section 27" in item, item
    assert "every other criterion are unchanged." not in item6
    assert "C3's equivalence comparison is unchanged and still reads the recorded state" in item8
    c3 = _between(text, "- **C3 (mutation score).**", "- **C4 (R-dev agreement).**")
    assert "decision D43 leaves this comparison unchanged" in c3
    section26 = " ".join(text.split("## 26.", 1)[1].split("## 27.", 1)[0].split())
    assert "One comparison still reads the recorded state: C3's equivalence test" in section26
    section27 = " ".join(text.split("## 27.", 1)[1].split())
    assert "**What the rule does not reach: C3's equivalence test.**" in section27
    assert "up to 6.7%" in section27 and "whether D43 covers it stays with Kevin" in section27
    # 1 - (1 - 0.023)^3: the three `chord_super_d` trials of C3's H-OSW-fixed reference run
    # and M12's and M13's runs, at section 26's bound per trial.
    assert round(1 - (1 - 0.023) ** 3, 3) == 0.067


def test_the_rules_precondition_is_stated_as_observed_not_checked():
    """D43's rule reads every key event without Mod2 as queued under a grab its entry's own
    grab key activated. That held for every development event but is a property of this
    guest's clients, which neither the judge nor the guard checks: sections 4.4 and 27 and
    design decision 47 say so, and section 27 lists a grab already active before the entry
    as a sixth case (tests/test_q2_d43_judge.py checks the numbers)."""
    text = PREREG.read_text(encoding="utf-8")
    section44 = _between(text, "### 4.4 The XRecord oracle channel", "### 4.5")
    assert "That is a property of this guest's clients, not of the X server" in section44
    assert "neither the judge nor the guard checks it" in section44
    assert "each of the 280 key events recorded without Mod2 in development" in section44
    decision47 = _between(text, "47. **The judge does not read a modifier state", "48. **")
    assert "which neither the judge nor the guard checks" in decision47
    assert "(section 27, case 6)" in decision47
    section27 = " ".join(text.split("## 27.", 1)[1].split())
    assert "Among this guest's clients, as development observed them" in section27
    case6_start = "6. A synchronous grab already active when the entry's first key arrives."
    assert case6_start in section27
    case6 = section27.split(case6_start, 1)[1].split("**The prediction.**", 1)[0]
    for phrase in (
        "`GetInputFocus`",
        "`QueryKeymap`",
        "Job 833",
        "seq 3-21",
        "280",
        "whether to adopt it stays with Kevin",
        "byte-identical to `126ff8b`",
    ):
        assert phrase in case6, phrase
    for stale in (
        "A key event is queued only while a shell grab holds the keyboard, and a grab",
        "recorded without Mod2 was recorded while queued under a shell grab",
        "A queued event needs an active shell grab",
    ):
        assert stale not in " ".join(text.split()), stale
    for path in (INPUTS, ROOT / "harness/q2/action_path/l0_raw_prediction_v2.yaml"):
        flat = " ".join(path.read_text(encoding="utf-8").split())
        assert "was recorded while queued under a shell grab" not in flat, path.name
        assert "section 27, case 6" in flat, path.name


def test_shell_grabbed_chords_have_modifier_state_after_the_grab_key():
    """Section 4.4: on the four chords GNOME Shell grabs, every reference event after the
    grab-activating key has a modifier state that is not empty, so v1's judge failed every
    event the tap records with state 0 while it is queued under the grab; D43's judge reads
    those events without their state (tests/test_q2_d43_judge.py)."""
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
