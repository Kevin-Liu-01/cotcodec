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
    assert f"{measured['projected_evaluation_and_statistics_s']:,.0f} s projected" in flat
    for phrase in ("Changes from v1 (D36)", "INCOMPLETE", "bfe4a7c3", "Slurm 766",
                   "enable_cudnn_sdp(False)", "attention_backend_check", "job.env",
                   "No budget amendment is possible under this id",
                   "Every job of a lane counts against that lane's own minutes",
                   "the first job's included", "Each filled manifest is submitted once",
                   "A1 B1 C1 D1 A2 B2 C2 D2"):
        assert phrase in flat, phrase


def test_status_and_decisions() -> None:
    status = TEXT.splitlines()[2]
    if _frozen():
        assert status.startswith("Status: frozen")
    else:
        assert status.startswith(("Status: DRAFT, not frozen.", "Status: frozen"))
    section = TEXT[TEXT.index("## Design decisions"):]
    numbers = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", section, re.M)]
    assert numbers == list(range(1, 22))
    assert "(caps amended in D36;" in section
