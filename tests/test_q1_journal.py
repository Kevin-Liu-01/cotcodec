"""Append-only verdict journal: final rows, attempts, torn lines. Pure Python."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.q1.journal import Journal, item_key
from harness.q1.schema import SchemaError, make_verdict_row


def _row(key: str, verdict: str = "accept", attempt: int = 1, final: bool = True) -> dict:
    details = {"item_key": key}
    if final:
        details["item_final"] = True
    return make_verdict_row(
        kernel_id=key.split("|")[0],
        gate=key.split("|")[1],
        config_id="native/seed-42",
        verdict=verdict,
        tf32_policy="torch-default",
        details=details,
        attempt=attempt,
        run_id="r1",
    )


def test_status_and_final_rows(tmp_path: Path) -> None:
    journal = Journal(tmp_path / "j.jsonl")
    k1, k2 = item_key("k1", "a", 42), item_key("k2", "a", 42)
    journal.append([_row(k1, final=False), _row(k1)])
    journal.append([_row(k2, "reject", final=False)])  # attempt 1 never finished
    journal.append([_row(k2, "accept", attempt=2)])
    status = journal.status()
    assert status[k1] == {"attempt": 1, "final": True, "retry_alone": False}
    assert status[k2] == {"attempt": 2, "final": True, "retry_alone": False}
    finals = journal.final_rows()
    assert [r["verdict"] for r in finals if r["details"]["item_key"] == k2] == ["accept"]
    assert len([r for r in finals if r["details"]["item_key"] == k1]) == 2


def test_torn_tail_is_isolated_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "j.jsonl"
    journal = Journal(path)
    k1 = item_key("k1", "a", 42)
    journal.append([_row(k1)])
    with path.open("ab") as handle:
        handle.write(b'{"kernel_id": "k2", "gate"')  # a killed writer
    before = path.read_bytes()
    reopened = Journal(path)
    assert path.read_bytes() == before + b"\n"  # only appended
    reopened.append([_row(item_key("k2", "a", 42))])
    rows, invalid = reopened.read()
    assert invalid == 1
    assert len(rows) == 2


def test_append_validates_rows(tmp_path: Path) -> None:
    journal = Journal(tmp_path / "j.jsonl")
    bad = _row(item_key("k1", "a", 42))
    bad["verdict"] = "pass"
    with pytest.raises(SchemaError):
        journal.append([bad])
    assert not (tmp_path / "j.jsonl").exists() or (tmp_path / "j.jsonl").read_text() == ""
