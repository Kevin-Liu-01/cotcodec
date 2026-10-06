from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_fidelis_zero_llm_shards import prepare_shards
from scripts.seal_fidelis_zero_llm_evidence import _compare_results
from scripts.validate_fidelis_zero_llm_evidence import (
    EXPECTED_STATUS,
    FidelisEvidenceError,
    validate_fidelis_zero_llm_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/fidelis-zero-llm-retrieval-v1.json"
)


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_prepare_shards_restores_non_abstention_order(tmp_path: Path) -> None:
    rows = [{"question_id": f"q-{index}"} for index in range(5)]
    rows.insert(2, {"question_id": "q_abs"})
    dataset = _write_json(tmp_path / "dataset.json", rows)
    output = tmp_path / "shards"

    manifest = prepare_shards(dataset, output, 2)

    assert manifest["source_row_count"] == 6
    assert manifest["non_abstention_row_count"] == 5
    assert [shard["row_count"] for shard in manifest["shards"]] == [3, 2]
    restored: list[str] = []
    for shard in manifest["shards"]:
        payload = json.loads((output / shard["relative_path"]).read_text())
        restored.extend(row["question_id"] for row in payload)
    assert restored == [f"q-{index}" for index in range(5)]
    with pytest.raises(ValueError, match="refusing to overwrite"):
        prepare_shards(dataset, output, 2)


def _result(qid: str, *, hit: bool) -> dict[str, object]:
    top5 = (
        [f"{qid}-gold", f"{qid}-other"]
        if hit
        else [f"{qid}-other", f"{qid}-gold"]
    )
    return {
        "qid": qid,
        "question": f"question {qid}",
        "qtype": "single-session-user",
        "gold_session_ids": [f"{qid}-gold"],
        "s1_top5_ids": top5,
        "s1_top5_scores": [0.9, 0.2],
        "s2_top5_ids": top5,
        "s1_hit_at_1": hit,
        "s2_hit_at_1": hit,
        "s1_hit_at_5": True,
        "s2_hit_at_5": True,
        "route_decision": "no_filter",
        "filter_called": False,
        "filter_ms": 0,
        "temporal_boost_fired": False,
        "temporal_boost_count": 0,
    }


def test_compare_results_requires_exact_upstream_projection(tmp_path: Path) -> None:
    first = _result("q-1", hit=True)
    second = _result("q-2", hit=False)
    upstream = _write_json(tmp_path / "upstream.json", [first, second])
    run_a = _write_json(tmp_path / "run-a.json", [first])
    run_b = _write_json(tmp_path / "run-b.json", [second])

    result = _compare_results(
        question_ids=["q-1", "q-2"],
        dataset_rows=[
            {
                "question_id": qid,
                "question": f"question {qid}",
                "question_type": "single-session-user",
                "answer_session_ids": [f"{qid}-gold"],
                "haystack_session_ids": [f"{qid}-gold", f"{qid}-other"],
            }
            for qid in ["q-1", "q-2"]
        ],
        run_paths=[run_a, run_b],
        expected_run_question_ids=[["q-1"], ["q-2"]],
        upstream_path=upstream,
        upstream_aggregate={
            "questions_evaluated": 2,
            "stage1b_metrics": {"recall_any": {"R@1": 0.5, "R@5": 1.0}}
        },
    )

    assert result["metrics"]["recall_any_at_1_hits"] == 1
    assert result["metrics"]["recall_any_at_5_hits"] == 2
    assert result["exact_top5_id_match_count"] == 2

    changed = _result("q-2", hit=False)
    changed["s1_top5_scores"] = [0.8, 0.2]
    _write_json(tmp_path / "changed.json", [changed])
    with pytest.raises(ValueError, match="differs from upstream"):
        _compare_results(
            question_ids=["q-1", "q-2"],
            dataset_rows=[
                {
                    "question_id": qid,
                    "question": f"question {qid}",
                    "question_type": "single-session-user",
                    "answer_session_ids": [f"{qid}-gold"],
                    "haystack_session_ids": [f"{qid}-gold", f"{qid}-other"],
                }
                for qid in ["q-1", "q-2"]
            ],
            run_paths=[run_a, tmp_path / "changed.json"],
            expected_run_question_ids=[["q-1"], ["q-2"]],
            upstream_path=upstream,
            upstream_aggregate={
                "questions_evaluated": 2,
                "stage1b_metrics": {"recall_any": {"R@1": 0.5, "R@5": 1.0}}
            },
        )


def test_committed_fidelis_evidence_is_self_contained_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    result = validate_fidelis_zero_llm_evidence(payload)

    assert result == {
        "status": EXPECTED_STATUS,
        "question_count": 470,
        "recall_any_at_1_hits": 391,
        "recall_any_at_5_hits": 462,
    }
    payload["result"]["metrics"]["recall_any_at_1_hits"] = 392
    with pytest.raises(FidelisEvidenceError, match="reproduced metrics drifted"):
        validate_fidelis_zero_llm_evidence(payload)
