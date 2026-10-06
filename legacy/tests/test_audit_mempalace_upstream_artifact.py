from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_mempalace_upstream_artifact import (
    ArtifactExpectations,
    audit_upstream_artifact,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, ArtifactExpectations]:
    source = tmp_path / "source"
    (source / "benchmarks").mkdir(parents=True)
    files = {
        "benchmarks/longmemeval_bench.py": b"runner",
        "uv.lock": b"lock",
        "LICENSE": b"license",
        "pyproject.toml": b"project",
    }
    for relative, content in files.items():
        (source / relative).write_bytes(content)
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "question_id": "normal-question",
                    "question": "Where?",
                    "answer": "Here",
                    "haystack_session_ids": [
                        "s1",
                        "s1",
                        "s2",
                        "s3",
                        "s4",
                        "s5",
                        "s6",
                    ],
                    "haystack_sessions": [
                        [{"role": "user", "content": session_id}]
                        for session_id in ["s1", "s1", "s2", "s3", "s4", "s5", "s6"]
                    ],
                    "answer_session_ids": ["s1", "s2"],
                },
                {
                    "question_id": "negative_abs",
                    "question": "Unknown?",
                    "answer": "I don't know",
                    "haystack_session_ids": ["a1", "a2"],
                    "haystack_sessions": [
                        [{"role": "user", "content": "a1"}],
                        [{"role": "user", "content": "a2"}],
                    ],
                    "answer_session_ids": [],
                },
            ]
        ),
        encoding="utf-8",
    )
    result = tmp_path / "result.jsonl"
    rows = [
        {
            "question_id": "normal-question",
            "question": "Where?",
            "answer": "Here",
            "retrieval_results": {
                "ranked_items": [
                    {"corpus_id": item, "text": item, "timestamp": "date"}
                    for item in ["s1", "s3", "s4", "s5", "s6", "s1", "s2"]
                ],
                "metrics": {
                    "session": {"recall_any@5": 1.0, "recall_any@10": 1.0}
                },
            },
        },
        {
            "question_id": "negative_abs",
            "question": "Unknown?",
            "answer": "I don't know",
            "retrieval_results": {
                "ranked_items": [
                    {"corpus_id": item, "text": item, "timestamp": "date"}
                    for item in ["a1", "a2"]
                ],
                "metrics": {
                    "session": {"recall_any@5": 0.0, "recall_any@10": 0.0}
                },
            },
        },
    ]
    result.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    expectations = ArtifactExpectations(
        result_sha256=_sha(result),
        result_size=result.stat().st_size,
        result_rows=2,
        dataset_sha256=_sha(dataset),
        dataset_size=dataset.stat().st_size,
        runner_sha256=_sha(source / "benchmarks/longmemeval_bench.py"),
        lock_sha256=_sha(source / "uv.lock"),
        license_sha256=_sha(source / "LICENSE"),
        pyproject_sha256=_sha(source / "pyproject.toml"),
    )
    return source, dataset, result, expectations


def test_audit_recomputes_custom_and_official_metrics_without_promoting_result(
    tmp_path: Path,
) -> None:
    source, dataset, result, expectations = _fixture(tmp_path)
    report = audit_upstream_artifact(
        source_root=source,
        dataset_path=dataset,
        result_path=result,
        expectations=expectations,
    )

    assert report["status"] == "UPSTREAM_ARTIFACT_AUDITED_NOT_REPRODUCED"
    assert report["scientific_result"] is False
    assert report["metrics"]["mempalace_custom_recall_any_at_5"] == 0.5
    assert report["metrics"]["official_non_abstention_count"] == 1
    assert report["metrics"]["official_recall_all_at_5"] == 0.0
    assert report["metrics"]["official_recall_all_at_10"] == 1.0
    assert report["released_artifact"]["quarantine_from_actor_inputs"] is True
    assert len(report["report_sha256"]) == 64


def test_audit_fails_on_stored_metric_or_source_drift(tmp_path: Path) -> None:
    source, dataset, result, expectations = _fixture(tmp_path)
    rows = [json.loads(line) for line in result.read_text(encoding="utf-8").splitlines()]
    rows[0]["retrieval_results"]["metrics"]["session"]["recall_any@5"] = 0.0
    result.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    changed = ArtifactExpectations(
        **{
            **expectations.__dict__,
            "result_sha256": _sha(result),
            "result_size": result.stat().st_size,
        }
    )
    with pytest.raises(ValueError, match="stored custom recall"):
        audit_upstream_artifact(
            source_root=source,
            dataset_path=dataset,
            result_path=result,
            expectations=changed,
        )

    (source / "uv.lock").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        audit_upstream_artifact(
            source_root=source,
            dataset_path=dataset,
            result_path=result,
            expectations=changed,
        )
