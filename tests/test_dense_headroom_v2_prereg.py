"""q3-dense-headroom-precheck-v2's registration against v1's text and the code it registers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from harness import dense_headroom_v2 as dv2
from harness import dense_headroom_v2_lanes as lanes
from scripts import fill_dense_headroom_precheck_v2_manifests as filler
from scripts import preregister
from scripts import run_dense_headroom_precheck_v2 as entry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREREGS = PROJECT_ROOT / "program" / "preregistrations"
TEXT = (PREREGS / f"{dv2.EXPERIMENT_ID}.md").read_text(encoding="utf-8")
V1_TEXT = (PREREGS / f"{dv2.V1_EXPERIMENT_ID}.md").read_text(encoding="utf-8")
DECISIONS = (PROJECT_ROOT / "program" / "decisions.md").read_text(encoding="utf-8")
PLACEHOLDER = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # scripts/preregister.py refuses these
SUBSTITUTIONS = (
    ("(`scripts/summarise_dense_headroom_precheck.py`,",
     "(`scripts/summarise_dense_headroom_precheck_v2.py`,"),
    ("is cropped back between options for Qwen3 (K1 v1's code) and deep-copied per\n"
     "option for Qwen3.5,",
     "is cropped back between options for Qwen3 (K1 v1's code) and copied per\n"
     "option for Qwen3.5 (v2's `clone_cache`, the values v1's deep copy held),"),
)
IMPORTED = {
    dv2.V1_EXPERIMENT_ID: ("harness/dense_headroom_data.py", "harness/dense_headroom_stats.py",
                           "harness/dense_headroom_torch.py",
                           "scripts/run_dense_headroom_precheck.py",
                           "scripts/run_dense_headroom_precheck_doctor.py",
                           "scripts/fill_dense_headroom_precheck_manifests.py",
                           "scripts/summarise_dense_headroom_precheck.py"),
    "q3-k1-throughput-probe-v1": ("harness/sparse_indexer_bank.py",),
    "q3-k1-localization-screen-v1": ("harness/sparse_indexer_torch.py",
                                     "harness/sparse_indexer_k1_runtime.py",
                                     "harness/sparse_indexer_k1_marker.py",
                                     "harness/sparse_indexer_k1_stats.py",
                                     "harness/sparse_indexer_data.py",
                                     "harness/translation_supervised_indexer.py"),
}


def _frozen() -> bool:
    try:
        preregister.verify(dv2.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        return False
    return True


def _section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _paragraph(text: str, start: str) -> str:
    """From ``start`` to the next blank line."""

    begin = text.index(start)
    end = text.find("\n\n", begin)
    return text[begin:end if end >= 0 else None]


def _decision_item(number: int) -> str:
    """Design decision ``number`` of this registration, title and body."""

    section = TEXT[TEXT.index("## Design decisions"):]
    begin = section.index(f"\n{number}. ") + 1
    nxt = section.find(f"\n{number + 1}. ", begin)
    return section[begin:nxt if nxt > 0 else None]


def _log_entry(number: int) -> str | None:
    """The decision log's entry D<number>, or None."""

    match = re.search(rf"^\*\*D{number}\. .*?(?=^\*\*D\d+\. |^## |\Z)", DECISIONS, re.M | re.S)
    return _flat(match.group(0)) if match else None


def _naming_decisions(paragraph: str) -> list[int]:
    """Decisions cited in ``paragraph`` that the log holds, that come after D36
    and that name this experiment."""

    found = []
    for number in sorted({int(n) for n in re.findall(r"\bD(\d+)\b", paragraph)}):
        entry = _log_entry(number)
        if number > 36 and entry and dv2.EXPERIMENT_ID in entry:
            found.append(number)
    return found


def _accepting_decisions(paragraph: str) -> list[int]:
    """Decisions cited in ``paragraph`` that the log holds, that come after D36,
    and that name this experiment and amend D36 (iii) (Freeze procedure, step 1)."""

    return [n for n in _naming_decisions(paragraph) if "D36 (iii)" in (_log_entry(n) or "")]


def test_draft_can_be_frozen() -> None:
    assert not PLACEHOLDER.search(TEXT)
    assert "@@" not in TEXT
    assert TEXT.startswith(f"# Q3 dense headroom pre-check v2 ({dv2.EXPERIMENT_ID})")


def test_code_table_binds_the_working_tree_until_frozen() -> None:
    table = entry.tabled_code(TEXT)
    assert set(entry.CODE_FILES) <= set(table)
    assert set(filler.BOUND_PATHS) <= set(table)
    for path in ("scripts/run_dense_headroom_precheck_v2_doctor.py",
                 "scripts/dense_headroom_v2_signal_shim.py",
                 "scripts/summarise_dense_headroom_precheck_v2.py"):
        assert path in table
    if _frozen():
        return
    for path, digest in table.items():
        actual = hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
        assert actual == digest, f"{path} changed; recompute the registration's code table"


def test_imported_rows_are_the_frozen_registrations_versions() -> None:
    table = entry.tabled_code(TEXT)
    for experiment, paths in IMPORTED.items():
        frozen = entry.tabled_code((PREREGS / f"{experiment}.md").read_text(encoding="utf-8"))
        for path in paths:
            assert table[path] == frozen[path], path


def test_the_carried_sections_are_v1s_text() -> None:
    v1 = _section(V1_TEXT, "## Data (development partition only)", "## Compute")
    for old, new in SUBSTITUTIONS:
        assert v1.count(old) == 1
        v1 = v1.replace(old, new)
    assert v1 in TEXT
    v1_decisions = V1_TEXT[V1_TEXT.index("1. Two lanes, both run"):]
    for number in (*range(1, 12), 13, 14, 15):
        start = v1_decisions.index(f"\n{number}. " if number > 1 else "1. ")
        nxt = v1_decisions.find(f"\n{number + 1}. ", start + 1)
        item = v1_decisions[start:nxt if nxt > 0 else None].strip()
        assert item in TEXT, f"v1's decision {number} is not carried verbatim"


def test_registered_numbers_appear_in_the_text() -> None:
    flat = " ".join(TEXT.split())
    for lane in lanes.LANES.values():
        assert f"| 1 x {lane.minutes} | {lane.cap_gpu_hours:.2f} |" in flat
    assert f"| 1 x {lanes.TIMING_MINUTES} | {lanes.TIMING_CAP_GPU_HOURS:.2f} |" in flat
    assert f"| Total | | {lanes.registered_caps_total():.2f} |" in flat
    assert lanes.registered_caps_total() <= lanes.TOTAL_CAP_GPU_HOURS == 1.5
    assert dv2.V1_SMALL_LANE_RECEIPT_SHA256 in TEXT and dv2.V1_SMALL_LANE_RECEIPT in flat
    assert "within 1e-6" in flat and dv2.V1_REPRODUCTION_TOLERANCE == 1e-6
    for field in ("`report`", "`decisions`, `coverage`, `artifact_counts`, `selectors` and "
                  "`attention_layers`", "`hashes.dev_artifact_sha256`"):
        assert field in flat
    measured = lanes.LARGE_LANE_MEASURED
    assert f"{measured['evaluation_and_statistics_s']:,.0f} s" in flat
    for estimate in lanes.LARGE_LANE_ESTIMATES.values():  # D44: all three, and their minutes
        assert (f"{estimate['evaluation_and_statistics_s']:,.0f} s ({estimate['minutes']} minutes)"
                in flat)
    assert f"{measured['start_up_s']:.0f} s of start-up" in flat
    assert f"about {lanes.large_lane_break_even_unit_s():.1f} s per unit" in flat
    for phrase in ("Changes from v1 (D36)", "INCOMPLETE", "bfe4a7c3", "Slurm 766", "Slurm 810",
                   "enable_cudnn_sdp(False)", "attention_backend_check", "job.env",
                   "No budget amendment is possible under this id",
                   "Every job of a lane counts against that lane's own minutes",
                   "the first job's included", "Each filled manifest is submitted once",
                   "A1 B1 C1 D1 A2 B2 C2 D2"):
        assert phrase in flat, phrase


def test_status_and_decisions() -> None:
    status = _paragraph(TEXT, "Status: ")
    lead_in = _paragraph(TEXT, "Each states the choice and why.")
    # Both name D42, the decision that accepts decisions 16-21 and amends D36
    # (iii) for the 4B lane (decision 18), and D44, which closed D42's narrow
    # re-check, set the 4B limit at the largest estimate (decision 20) and
    # accepts decisions 16-21 as amended by D42 and D44; draft and frozen alike.
    d44 = _log_entry(44)
    assert d44 and dv2.EXPERIMENT_ID in d44 and "32 minutes" in d44 and "largest" in d44
    assert lanes.LARGE_LANE_MINUTES == 32
    for name, paragraph in (("status", status), ("lead-in", lead_in)):
        assert 42 in _accepting_decisions(paragraph), f"the {name} does not name D42"
        assert 44 in _naming_decisions(paragraph), f"the {name} does not name D44"
    if _frozen():
        # Freeze procedure, step 1: the status paragraph and the lead-in of the
        # design decisions were rewritten to the frozen wording, naming D42 and D44.
        assert status.startswith("Status: frozen")
        flat = _flat(TEXT)
        for draft in ("DRAFT", "wait for the program owner", "waits for the program owner",
                      "still to be done"):
            assert draft not in flat, f"the frozen file still says {draft!r}"
        for name, paragraph in (("status", status), ("lead-in", lead_in)):
            assert "to the frozen wording" not in _flat(paragraph), (
                f"the frozen {name} still says it is to be rewritten to the frozen wording")
    else:
        assert status.startswith("Status: DRAFT, not frozen.")
        flat_status = _flat(status)
        for phrase in ("D42", "D44", "D36 (iii)", "narrow re-check", "Slurm 810", "before the fix",
                       "rewritten to the frozen wording, naming D42 and D44"):
            assert phrase in flat_status, phrase
        assert "to the frozen wording, naming D42 and D44, is still to be done" in _flat(lead_in)
    section = TEXT[TEXT.index("## Design decisions"):]
    numbers = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", section, re.M)]
    assert numbers == list(range(1, 22))
    assert "(caps amended in D36;" in section
    step_1 = _flat(_section(TEXT, "## Freeze procedure", "\n2. This file is frozen"))
    for phrase in ("the status paragraph at the top of this file is rewritten",
                   "and so is the lead-in of the design decisions",
                   "amends D36 (iii) for that lane", "D36's timing rule",
                   "authorises a timing job of the fixed path", "D42 is that decision",
                   "D44 closed that re-check", "both name D42 and D44",
                   "do not both name D42 and D44"):
        assert phrase in step_1, phrase


def test_d36_iii_is_amended_for_the_4b_lane_and_its_limit_is_measured() -> None:
    """Decision 18 departs from D36 (iii) on the 4B lane, which D42 (i) amends;
    decisions 20 and 21 set the 4B limit from the second timing job's
    measurement of the fixed path (D42 (ii)), so D36's timing rule holds. The
    registration and the lanes module say so and never call it a projection."""

    flat = _flat(TEXT)
    d18, d19, d20, d21 = (_flat(_decision_item(n)) for n in (18, 19, 20, 21))
    title_18 = d18[:d18.index(". v2's")]
    assert "D36 (iii)" in title_18 and "departure" in title_18 and "D42 (i)" in title_18
    assert "equal to v1's" not in title_18
    for item in (d18, d19):
        assert "`attention_backend_check`" in item and "descriptive" in item
        assert "not cover" in item
    assert "a 0.6B pass says nothing about the 4B lane's attention" in d18
    assert "D42 (i) amends D36 (iii) for that lane only" in d18
    assert "Slurm 810" in d18 and "aten::_efficient_attention_forward" in d18
    assert "both lanes' measured" in d20 and "Slurm 810" in d20 and "D42 (ii)" in d20
    assert "D36's rule for the 4B limit holds unamended" in d20
    assert "at its measured speed" in d20 and "do not come from a measurement" not in d20
    assert "before the fix (cuDNN's attention on)" in d21 and "Slurm 810" in d21
    assert "code head" in d21
    compute = _flat(_section(TEXT, "## Compute", "### The development timing jobs"))
    assert "Every input is measured" in compute and "projected, not measured" not in compute
    assert "| Qwen3.5-4B-Base lane | 1 x 32 | 0.53 |" in compute
    assert "The 4B limit is the largest of the three estimates" in compute
    assert "projected, not measured" not in flat
    changes = _flat(_section(TEXT, "## Changes from v1 (D36)", "## Identity"))
    assert "departs from D36 (iii)" in changes and "D42 (i) amends D36 (iii)" in changes
    assert "Both measured" in changes
    assert not hasattr(lanes, "LARGE_LANE_PROJECTED")
    assert lanes.LARGE_LANE_MEASURED["measured"] is True
    doc = _flat(lanes.__doc__ or "")
    assert "Both lanes' inputs are measurements" in doc and "Slurm 810" in doc
    assert "is a projection, not a measurement" not in doc
