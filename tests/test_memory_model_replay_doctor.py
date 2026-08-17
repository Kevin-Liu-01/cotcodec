from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_memory_model_replay_doctor import (
    _acknowledge_checkpoint,
    _expected_case_keys,
    _load_progress,
    _write_progress,
)


def _contract() -> dict:
    return {
        "schema_version": 1,
        "config_sha256": "a" * 64,
        "model_id": "qwen3.6-35b-a3b",
        "revision": "b" * 40,
        "artifact_root_sha256": "c" * 64,
        "task_manifest_sha256": "d" * 64,
        "memory_bundle_sha256": None,
        "task_ids": ["memory-000000", "memory-000004"],
        "seeds": [42, 43, 44],
        "repetitions": 3,
        "cold_reloads": 2,
        "visibilities": ["serve", "holdout"],
        "deterministic": True,
        "attention_implementation": "eager",
    }


def _row(
    *,
    seed: int = 42,
    reload_index: int = 0,
    task_id: str = "memory-000000",
    visibility: str = "serve",
) -> dict:
    return {
        "seed": seed,
        "reload": reload_index,
        "task_id": task_id,
        "visibility": visibility,
        "repetitions": 3,
        "pre_model_equal": True,
        "token_exact": True,
        "action_exact": True,
        "cross_load_seed_exact": True,
        "output_sha256s": ["e" * 64] * 3,
        "tool_trace_sha256s": ["f" * 64] * 3,
    }


def _expected(contract: dict) -> tuple[tuple[int, int, str, str], ...]:
    return _expected_case_keys(
        seeds=tuple(contract["seeds"]),
        cold_reloads=contract["cold_reloads"],
        task_ids=tuple(contract["task_ids"]),
    )


def test_replay_checkpoint_round_trips_a_contiguous_plan_prefix(tmp_path: Path) -> None:
    contract = _contract()
    rows = [_row(), _row(visibility="holdout")]
    _write_progress(tmp_path, contract=contract, rows=rows)

    assert _load_progress(
        tmp_path,
        contract=contract,
        expected_keys=_expected(contract),
    ) == rows


def test_replay_checkpoint_rejects_contract_or_plan_drift(tmp_path: Path) -> None:
    contract = _contract()
    _write_progress(
        tmp_path,
        contract=contract,
        rows=[_row(visibility="holdout")],
    )
    with pytest.raises(ValueError, match="contiguous plan prefix"):
        _load_progress(
            tmp_path,
            contract=contract,
            expected_keys=_expected(contract),
        )

    drifted = {**contract, "repetitions": 4}
    with pytest.raises(ValueError, match="contract mismatch"):
        _load_progress(
            tmp_path,
            contract=drifted,
            expected_keys=_expected(drifted),
        )


def test_replay_checkpoint_acknowledges_scheduler_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "replay-doctor"
    marker = tmp_path / "checkpoint.ready"
    monkeypatch.setenv("COTCODEC_CHECKPOINT_MARKER", str(marker))
    contract = _contract()
    rows = [_row()]

    _acknowledge_checkpoint(output_dir, contract=contract, rows=rows)

    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    assert marker_payload["status"] == "CHECKPOINT_READY"
    assert marker_payload["completed_cases"] == 1
    assert marker_payload["total_cases"] == len(_expected(contract))
    assert (output_dir / "checkpoint.json").is_file()
