"""The combined read of the dense headroom pre-check's two lane receipts."""

from __future__ import annotations

import json

import pytest

from harness import dense_headroom_data as dhd
from scripts import preregister
from scripts import summarise_dense_headroom_precheck as summary


def _decisions(lane_class: str) -> dict:
    return {"lane_class": lane_class, "anchor_confound": "PRESENT",
            "entity_control": "SUFFICIENT",
            "null_calibration": {"hs": "CENTRED", "mp": "CENTRED"},
            "floor_candidate": "VIABLE"}


@pytest.fixture()
def frozen(tmp_path):
    prereg = tmp_path / "program" / "preregistrations" / f"{dhd.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True)
    prereg.write_text("# stand-in\n", encoding="utf-8")
    ledger = prereg.parent / "ledger.jsonl"
    row = preregister.freeze(prereg, dhd.EXPERIMENT_ID, ledger=ledger, root=tmp_path)
    return tmp_path, ledger, str(row["sha256"])


def _receipt(tmp_path, lane: str, lane_class: str, prereg_sha: str, **overrides):
    payload = {"experiment_id": dhd.EXPERIMENT_ID, "status": "PRECHECK_COMPLETE",
               "lane": {"lane_id": lane}, "decisions": _decisions(lane_class),
               "hashes": {"preregistration_sha256": prereg_sha,
                          "bundle_sha256": dhd.SOURCE_BUNDLE_SHA256,
                          "dev_artifact_sha256": "e" * 64}, "slurm_job_id": "1"}
    payload.update(overrides)
    path = tmp_path / f"{lane}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_combined_read(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    paths = [_receipt(tmp_path, "qwen3-0.6b-base", "GO_ONLY_CAPABLE", sha),
             _receipt(tmp_path, "qwen3.5-4b-base", "NEGATIVE_CAPABLE", sha)]
    output = tmp_path / "combined.json"
    assert summary.main([*map(str, paths), "--output", str(output), "--ledger", str(ledger),
                         "--root", str(root)]) == 0
    combined = json.loads(output.read_text())["combined"]
    assert (combined["design"], combined["base"]) == ("NEGATIVE_CAPABLE_V3", "qwen3.5-4b-base")
    assert summary.main([*map(str, paths), "--output", str(output), "--ledger", str(ledger),
                         "--root", str(root)]) == 2  # never overwrite


def test_inconsistent_receipts_are_refused(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    small = _receipt(tmp_path, "qwen3-0.6b-base", "GO_ONLY_CAPABLE", sha)
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([small, small])
    interrupted = _receipt(tmp_path, "qwen3.5-4b-base", "NOT_VIABLE", sha,
                           status="INTERRUPTED")
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([small, interrupted])
    other = _receipt(tmp_path, "qwen3.5-4b-base", "NOT_VIABLE", "f" * 64)
    with pytest.raises(summary.SummaryError):
        summary.summarise(summary.load_receipts([small, other]), ledger=ledger, root=root)
    tiny = _receipt(tmp_path, "tiny-hybrid", "NOT_VIABLE", sha)
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([tiny])


def test_a_single_lane_is_incomplete(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    receipts = summary.load_receipts([_receipt(tmp_path, "qwen3-0.6b-base", "NOT_VIABLE",
                                               sha)])
    read = summary.summarise(receipts, ledger=ledger, root=root)
    assert read["combined"]["design"] == "INCOMPLETE"
