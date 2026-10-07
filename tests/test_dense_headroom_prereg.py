"""The dense headroom pre-check's draft registration against the code it registers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from harness import dense_headroom_data as dhd
from harness import dense_headroom_stats as dhs
from scripts import fill_dense_headroom_precheck_manifests as filler
from scripts import preregister
from scripts import run_dense_headroom_precheck as entry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREREGS = PROJECT_ROOT / "program" / "preregistrations"
PATH = PREREGS / f"{dhd.EXPERIMENT_ID}.md"
TEXT = PATH.read_text(encoding="utf-8")
PLACEHOLDER = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # scripts/preregister.py refuses these


def _frozen() -> bool:
    try:
        preregister.verify(dhd.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        return False
    return True


def test_draft_can_be_frozen() -> None:
    assert not PLACEHOLDER.search(TEXT)
    assert TEXT.startswith(f"# Q3 dense headroom pre-check ({dhd.EXPERIMENT_ID})")


def test_code_table_binds_the_working_tree_until_frozen() -> None:
    table = entry.tabled_code(TEXT)
    assert set(entry.CODE_FILES) <= set(table)
    assert filler.SELF_PATH in table
    assert "scripts/summarise_dense_headroom_precheck.py" in table
    assert "scripts/run_dense_headroom_precheck_doctor.py" in table
    if _frozen():
        return
    for path, digest in table.items():
        actual = hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
        assert actual == digest, f"{path} changed; recompute the registration's code table"


def test_imported_files_are_the_frozen_registrations_versions() -> None:
    table = entry.tabled_code(TEXT)
    v1 = entry.tabled_code((PREREGS / "q3-k1-localization-screen-v1.md").read_text())
    probe = entry.tabled_code((PREREGS / "q3-k1-throughput-probe-v1.md").read_text())
    for path in ("harness/sparse_indexer_torch.py", "harness/sparse_indexer_k1_runtime.py",
                 "harness/sparse_indexer_k1_marker.py", "harness/sparse_indexer_k1_stats.py",
                 "harness/sparse_indexer_data.py", "harness/translation_supervised_indexer.py"):
        assert table[path] == v1[path]
    assert table["harness/sparse_indexer_bank.py"] == probe["harness/sparse_indexer_bank.py"]


def test_registered_numbers_appear_in_the_text() -> None:
    flat = " ".join(TEXT.split())
    for lane in dhd.LANES.values():
        for value in (lane.revision, lane.receipt_sha256, lane.artifact_root_sha256,
                      lane.tokenizer_sha256):
            assert value in TEXT
        assert f"| 1 x {lane.minutes} | {lane.cap_gpu_hours:.2f} |" in flat
    assert "| Total | | 0.50 |" in flat
    assert dhd.SOURCE_BUNDLE_SHA256 in TEXT and "278,818,734" in TEXT
    for phrase in ("seeds 42, 43, 44", "NumPy seed 42", "B = 10,000",
                   "sigma in {0.25, 0.5, 1, 2}", "H1_CX at least 20 with its 99 percent lower "
                   "bound at least 10", "at least 30 percent of the questions",
                   "|xi| is at most 2 points and |xi_rel| at most 0.10",
                   "within 0.5 points of the smoke receipt", "1,160 per lane"):
        assert phrase in flat, phrase
    assert tuple(float(s) for s in (0.25, 0.5, 1, 2)) == dhs.SIGMAS
    assert dhs.H1_NEGATIVE_POINTS == 20 and dhs.H1_NEGATIVE_LOWER_POINTS == 10
    assert dhs.NULL_XI_POINTS == 2 and dhs.NULL_XI_REL == 0.10 == dhs.LEX_XI_REL
    assert dhs.FLOOR_G == 0.5 and dhs.CONTROL_SHARE_MIN == 0.30
    assert dhs.SMOKE_452_TOLERANCE_POINTS == 0.5 and dhd.STOP_IDS_PER_LANGUAGE == 100


def test_not_frozen_without_the_owners_acceptance() -> None:
    # The draft is frozen only after the design decisions are accepted
    # (a decision in program/decisions.md naming this experiment id).
    decisions = (PROJECT_ROOT / "program" / "decisions.md").read_text(encoding="utf-8")
    if _frozen():
        assert dhd.EXPERIMENT_ID in decisions
    else:
        assert TEXT.splitlines()[2].startswith("Status: DRAFT, not frozen.")
