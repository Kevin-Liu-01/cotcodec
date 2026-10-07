from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import fill_sparse_indexer_k1_manifests as filler
from scripts import preregister

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREREG = PROJECT_ROOT / "program" / "preregistrations" / f"{filler.EXPERIMENT_ID}.md"
TEXT = PREREG.read_text(encoding="utf-8")


def _frozen() -> bool:
    try:
        preregister.verify(filler.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        return False
    return True


def test_the_filler_reads_the_identity_table_and_bundle_digest() -> None:
    code, bundle = filler.registered_identity(PREREG)
    assert len(code) == 12 and filler.CONTRACT_PATH in code
    assert bundle == "919d016b87ad862f8f156e9537c9a39e2864dab0e6c605307d100d25a199dd2d"


@pytest.mark.skipif(_frozen(), reason="once frozen, receipts and the filler bind the digests")
def test_identity_table_matches_the_working_tree() -> None:
    code, _ = filler.registered_identity(PREREG)
    for path, digest in code.items():
        assert preregister.sha256_file(PROJECT_ROOT / path) == digest, path


def test_the_text_reads_correctly_once_frozen() -> None:
    # Pre-freeze audit: the frozen bytes are permanent, so no draft wording.
    status = TEXT.split("\n\n", 2)[1]
    assert status.startswith("Status: frozen in program/preregistrations/ledger.jsonl")
    for stale in ("DRAFT", "not frozen", "this draft", "the owner logs", "owner rebases"):
        assert stale not in TEXT, stale
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", TEXT)  # preregister.py's freeze check


def test_the_owner_sign_off_conditions_are_registered() -> None:
    # Program decision D16 and the audit's two blocking defects.
    flat = " ".join(TEXT.split())
    for clause in ("HOLD is terminal for this experiment id",
                   "if it finds none, the verdict stays HOLD",
                   "it is not discretionary (program decision D16)",
                   "the final verdict is INCONCLUSIVE and no second extension runs",
                   "Budget amendments are declined by default",
                   "could change only minutes and GPU-hours, never rules",
                   "A second continuation is declined by default",
                   "reports SMOKE_PASS", "PROCEED_TO_K1", "the resume test is valid"):
        assert clause in flat, clause


def test_design_decisions_are_numbered_consecutively() -> None:
    section = TEXT.split("## Design decisions", 1)[1]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section, re.M)]
    assert numbers == list(range(1, 32))
