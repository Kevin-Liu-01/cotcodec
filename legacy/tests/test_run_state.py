from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.run_state import ExecutionJournal, RunStateError


def _plan() -> list[dict[str, object]]:
    return [
        {"task_id": "a", "seed": 1},
        {"task_id": "b", "seed": 1},
    ]


def test_execution_journal_resumes_exact_contiguous_prefix(tmp_path: Path) -> None:
    root = tmp_path / "state"
    first = ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=False)
    first.append(_plan()[0], {"outcome": True})

    resumed = ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=True)
    assert resumed.completed == 1
    resumed.append(_plan()[1], {"outcome": False})
    resumed.complete()

    final = ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=True)
    assert final.completed == 2
    assert list(final.payloads()) == [{"outcome": True}, {"outcome": False}]


def test_execution_journal_rejects_contract_and_hash_drift(tmp_path: Path) -> None:
    root = tmp_path / "state"
    journal = ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=False)
    journal.append(_plan()[0], {"outcome": True})
    with pytest.raises(RunStateError, match="contract drifted"):
        ExecutionJournal(root, contract={"name": "changed"}, plan_keys=_plan(), resume=True)

    rows = (root / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    payload["payload"]["outcome"] = False
    (root / "journal.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(RunStateError, match="hash drifted"):
        ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=True)


def test_execution_journal_requires_explicit_resume(tmp_path: Path) -> None:
    root = tmp_path / "state"
    ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=False)
    with pytest.raises(RunStateError, match="not empty"):
        ExecutionJournal(root, contract={"name": "test"}, plan_keys=_plan(), resume=False)
