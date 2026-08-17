from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_sodamem_published_artifacts import (
    CONTEXT_PATH,
    JUDGED_PATH,
    SodaMemArtifactExpectations,
    audit_sodamem_published_artifacts,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _judged_row(
    question_id: str,
    question: str,
    answer: str | int,
    question_type: str,
    *,
    correct: bool,
) -> dict[str, object]:
    return {
        "elapsed_s": 1.0,
        "evidence_ids": True,
        "golden_answer": answer,
        "hypothesis": f"The answer is {answer}.",
        "llm_judge": {"model": "deepseek-v4-flash", "correct": correct},
        "planner_steps": 2,
        "question": question,
        "question_id": question_id,
        "question_type": question_type,
        "tools_used": ["browser_search"],
        "usage_totals": {
            "calls": 4,
            "cached_input_tokens": 2,
            "completion_tokens": 3,
            "prompt_tokens": 7,
            "total_tokens": 10,
        },
    }


def _context_row(
    question_id: str, question: str, answer: str | int, question_type: str
) -> dict[str, object]:
    item_id = f"fact_{question_id}"
    return {
        "other_tools_used": [],
        "planner_queries": [question],
        "question": question,
        "question_id": question_id,
        "question_type": question_type,
        "retrieved_evidence": [
            {
                "content": f"Stored answer: {answer}",
                "evidence_id": f"ev_fact:{item_id}",
                "extracted_support_text": str(answer),
                "id": item_id,
                "kind": "fact",
                "modality": "current_state",
                "occurred_start": None,
                "session_id": f"session_{question_id}",
                "source_trace_ids": [f"span_{question_id}_0"],
                "status": "active",
                "valid_from": None,
                "valid_until": None,
            }
        ],
    }


def _fixture(
    tmp_path: Path,
) -> tuple[Path, Path, SodaMemArtifactExpectations]:
    source = tmp_path / "source"
    source.mkdir()
    license_path = source / "LICENSE"
    license_path.write_text("test license", encoding="utf-8")
    dataset = _write_json(
        tmp_path / "longmemeval.json",
        [
            {
                "question_id": "numeric-id",
                "question": "How many?",
                "answer": 3,
                "question_type": "multi-session",
            },
            {
                "question_id": "unknown_abs",
                "question": "What is unknown?",
                "answer": "No information is available.",
                "question_type": "single-session-user",
            },
        ],
    )
    judged = _write_json(
        source / JUDGED_PATH,
        [
            _judged_row(
                "q001",
                "What is unknown?",
                "No information is available.",
                "single-session-user",
                correct=False,
            ),
            _judged_row("q002", "How many?", 3, "multi-session", correct=True),
        ],
    )
    contexts = _write_json(
        source / CONTEXT_PATH,
        [
            _context_row(
                "q001",
                "What is unknown?",
                "No information is available.",
                "single-session-user",
            ),
            _context_row("q002", "How many?", 3, "multi-session"),
        ],
    )
    expectations = SodaMemArtifactExpectations(
        repository=None,
        revision=None,
        tree=None,
        source_archive_sha256=None,
        source_files={"LICENSE": _sha(license_path)},
        artifacts={
            JUDGED_PATH: {"sha256": _sha(judged), "size": judged.stat().st_size},
            CONTEXT_PATH: {
                "sha256": _sha(contexts),
                "size": contexts.stat().st_size,
            },
        },
        dataset_sha256=_sha(dataset),
        dataset_size=dataset.stat().st_size,
        row_count=2,
    )
    return source, dataset, expectations


def test_audit_aligns_numeric_answers_and_prepares_official_prompt_cases(
    tmp_path: Path,
) -> None:
    source, dataset, expectations = _fixture(tmp_path)

    report, projection = audit_sodamem_published_artifacts(
        source_root=source,
        dataset_path=dataset,
        expectations=expectations,
    )

    assert report["scientific_result"] is False
    assert report["stored_self_judge"]["correct"] == 1
    assert report["dataset"]["abstention_rows"] == 1
    assert report["retrieval_artifact"]["evidence_rows"] == 2
    assert report["retrieval_artifact"]["answer_rows_with_evidence_id_lists"] == 0
    assert report["independent_judge_cases"]["count"] == 2
    assert [row["longmemeval_question_id"] for row in projection] == [
        "unknown_abs",
        "numeric-id",
    ]
    assert all(len(row["official_prompt_sha256"]) == 64 for row in projection)


def test_audit_fails_closed_on_evidence_sentinel_or_source_drift(
    tmp_path: Path,
) -> None:
    source, dataset, expectations = _fixture(tmp_path)
    judged_path = source / JUDGED_PATH
    judged = json.loads(judged_path.read_text(encoding="utf-8"))
    judged[0]["evidence_ids"] = ["ev-1"]
    judged_path.write_text(json.dumps(judged), encoding="utf-8")
    changed_artifacts = dict(expectations.resolved_artifacts())
    changed_artifacts[JUDGED_PATH] = {
        "sha256": _sha(judged_path),
        "size": judged_path.stat().st_size,
    }
    changed = SodaMemArtifactExpectations(
        **{**expectations.__dict__, "artifacts": changed_artifacts}
    )
    with pytest.raises(ValueError, match="evidence_ids boolean sentinel"):
        audit_sodamem_published_artifacts(
            source_root=source,
            dataset_path=dataset,
            expectations=changed,
        )

    (source / "LICENSE").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        audit_sodamem_published_artifacts(
            source_root=source,
            dataset_path=dataset,
            expectations=changed,
        )
