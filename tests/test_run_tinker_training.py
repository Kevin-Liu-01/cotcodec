from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_tinker_training import Example, epoch_order, load_examples, select_batch


def test_epoch_order_and_batches_are_reproducible() -> None:
    examples = [Example(str(index), "prefix", "target") for index in range(5)]
    first = select_batch(examples, seed=42, epoch=0, cursor=0, batch_size=7)
    second = select_batch(examples, seed=42, epoch=0, cursor=0, batch_size=7)
    assert first == second
    assert len(first[0]) == 7
    assert epoch_order(5, 42, 0) != epoch_order(5, 42, 1)


def test_jsonl_loader_is_strict_and_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl"
    row = {"example_id": "same", "prefix": "prefix", "target": "target"}
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate example_id"):
        load_examples(path)


def test_jsonl_loader_rejects_unregistered_fields(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl"
    row = {
        "example_id": "one",
        "prefix": "prefix",
        "target": "target",
        "label_leak": "forbidden",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fields must be"):
        load_examples(path)
