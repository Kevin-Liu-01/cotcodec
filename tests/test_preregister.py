import json
from pathlib import Path

import pytest

from scripts import preregister


def _prereg(root: Path, name: str = "exp.md", text: str = "# Prereg\nseeds: 42, 43, 44\n") -> Path:
    path = root / "program" / "preregistrations" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_freeze_then_verify_round_trip(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    path = _prereg(tmp_path)
    row = preregister.freeze(path, "q3-k1-screen-v1", ledger=ledger, root=tmp_path)
    assert row["path"] == "program/preregistrations/exp.md"
    assert row["previous_hash"] == preregister.GENESIS
    verified = preregister.verify("q3-k1-screen-v1", ledger=ledger, root=tmp_path)
    assert verified["sha256"] == row["sha256"]


def test_edit_after_freeze_fails_verification(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    path = _prereg(tmp_path)
    preregister.freeze(path, "q3-k1-screen-v1", ledger=ledger, root=tmp_path)
    path.write_text(path.read_text() + "kill if shortfall < 3\n", encoding="utf-8")
    with pytest.raises(preregister.PreregistrationError, match="changed after freezing"):
        preregister.verify("q3-k1-screen-v1", ledger=ledger, root=tmp_path)


def test_refuses_duplicate_id_path_and_placeholders(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    first = _prereg(tmp_path)
    preregister.freeze(first, "q3-k1-screen-v1", ledger=ledger, root=tmp_path)
    second = _prereg(tmp_path, "other.md")
    with pytest.raises(preregister.PreregistrationError, match="already frozen"):
        preregister.freeze(second, "q3-k1-screen-v1", ledger=ledger, root=tmp_path)
    with pytest.raises(preregister.PreregistrationError, match="already frozen"):
        preregister.freeze(first, "q3-k1-screen-v2", ledger=ledger, root=tmp_path)
    draft = _prereg(tmp_path, "draft.md", "# Prereg\nminimum effect: TBD\n")
    with pytest.raises(preregister.PreregistrationError, match="placeholder"):
        preregister.freeze(draft, "q3-k1-screen-v3", ledger=ledger, root=tmp_path)


def test_tampered_ledger_row_breaks_the_chain(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    preregister.freeze(_prereg(tmp_path, "a.md"), "exp-a-v1", ledger=ledger, root=tmp_path)
    preregister.freeze(_prereg(tmp_path, "b.md"), "exp-b-v1", ledger=ledger, root=tmp_path)
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert rows[1]["previous_hash"] == rows[0]["hash"]
    rows[0]["sha256"] = "0" * 64
    ledger.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    with pytest.raises(preregister.PreregistrationError, match="row hash"):
        preregister.read_ledger(ledger)


def test_refuses_files_outside_repository(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# Prereg\n", encoding="utf-8")
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(preregister.PreregistrationError, match="inside the repository"):
        preregister.freeze(outside, "exp-x-v1", ledger=tmp_path / "l.jsonl", root=root)
