from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.memory_trials import (
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    LONGMEMEVAL_SCREEN32_RAW_TASK_IDS,
    LongMemEvalTaskSource,
    PublicMemorySourceError,
    build_mempalace_session_documents,
    derive_longmemeval_transport_panel,
)
from harness.memory_trials.systems import build_memory_system_request
from scripts.prepare_memory_benchmarks import compile_longmemeval_manifest
from scripts.validate_memory_source_contract import validate_public_longmemeval


def _rows() -> list[dict[str, object]]:
    return [
        {
            "question_id": "public-001",
            "question_type": "knowledge-update",
            "question": "Which city is current?",
            "answer": "Seattle",
            "question_date": "2026/01/03 (Sat) 10:00",
            "haystack_session_ids": ["session-late", "session-early"],
            "haystack_dates": [
                "2026/01/02 (Fri) 10:00",
                "2026/01/01 (Thu) 10:00",
            ],
            "haystack_sessions": [
                [
                    {
                        "role": "user",
                        "content": "I moved to Seattle.",
                        "has_answer": True,
                    },
                    {"role": "assistant", "content": "Noted."},
                ],
                [
                    {
                        "role": "user",
                        "content": "I used to live in Boston.",
                        "has_answer": False,
                    }
                ],
            ],
            "answer_session_ids": ["session-late"],
        },
        {
            "question_id": "public-002_abs",
            "question_type": "single-session-user",
            "question": "What is my favorite constellation?",
            "answer": "I don't know.",
            "question_date": "2026/01/04 (Sun) 10:00",
            "haystack_session_ids": ["session-only"],
            "haystack_dates": ["2026/01/01 (Thu) 10:00"],
            "haystack_sessions": [
                [
                    {"role": "user", "content": "My telescope is blue."},
                    {"role": "assistant", "content": "That sounds nice."},
                ]
            ],
            "answer_session_ids": [],
        },
    ]


def _write_rows(path: Path, rows: list[dict[str, object]]) -> tuple[str, int]:
    encoded = json.dumps(rows, sort_keys=True).encode()
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def _source(path: Path, rows: list[dict[str, object]]) -> LongMemEvalTaskSource:
    digest, size = _write_rows(path, rows)
    return LongMemEvalTaskSource(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
        candidate_seed=42,
    )


def test_public_source_is_content_addressed_and_includes_abstention(tmp_path: Path) -> None:
    source = _source(tmp_path / "longmemeval.json", _rows())
    assert source.ids() == ("longmemeval-public-001", "longmemeval-public-002_abs")
    tasks = tuple(source.load(task_id) for task_id in source.ids())
    assert {task.stratum.value for task in tasks} == {"oracle_context"}
    assert source.provenance["retrieval_evaluation_capable"] is False
    assert source.provenance["graph_claim_enabled"] is False
    assert source.provenance["official_evaluation_implemented"] is True
    assert source.provenance["official_evaluation_executed"] is False
    assert all(sum(event.candidate for event in task.events) == 1 for task in tasks)
    assert all(task.write_step < task.eligibility_step for task in tasks)
    assert source.provenance["candidate_forbidden_inputs"] == [
        "question",
        "answer",
        "has_answer",
        "answer_session_ids",
    ]


def test_candidate_selection_does_not_use_future_answer_labels(tmp_path: Path) -> None:
    original_rows = _rows()
    changed_rows = json.loads(json.dumps(original_rows))
    changed_rows[0]["answer_session_ids"] = ["session-early"]
    for session in changed_rows[0]["haystack_sessions"]:
        for turn in session:
            turn["has_answer"] = not bool(turn.get("has_answer", False))
    first = _source(tmp_path / "first.json", original_rows)
    second = _source(tmp_path / "second.json", changed_rows)
    first_task = first.load("longmemeval-public-001")
    second_task = second.load("longmemeval-public-001")
    assert first_task == second_task
    candidate = next(event for event in first_task.events if event.candidate)
    assert "has_answer" not in candidate.model_dump_json()
    request, _expected = build_memory_system_request(
        first_task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert "answer_session" not in request.model_dump_json()
    assert "has_answer" not in request.model_dump_json()


def test_candidate_selection_does_not_use_question_or_answer(tmp_path: Path) -> None:
    original_rows = _rows()
    changed_rows = json.loads(json.dumps(original_rows))
    changed_rows[0]["question"] = "A completely different future question?"
    changed_rows[0]["answer"] = "A completely different future answer."
    first = _source(tmp_path / "first.json", original_rows)
    second = _source(tmp_path / "second.json", changed_rows)
    first_task = first.load("longmemeval-public-001")
    second_task = second.load("longmemeval-public-001")
    assert first_task.candidate_id == second_task.candidate_id
    assert first_task.events[:-1] == second_task.events[:-1]


def test_question_type_does_not_masquerade_as_memory_stratum(tmp_path: Path) -> None:
    temporal_rows = _rows()
    archive_rows = json.loads(json.dumps(temporal_rows))
    archive_rows[0]["question_type"] = "multi-session"
    temporal = _source(tmp_path / "temporal.json", temporal_rows).load(
        "longmemeval-public-001"
    )
    archive = _source(tmp_path / "archive.json", archive_rows).load(
        "longmemeval-public-001"
    )
    assert temporal.stratum == archive.stratum
    assert temporal.stratum.value == "oracle_context"
    assert temporal.events[-1].metadata["question_type"] == "knowledge-update"
    assert archive.events[-1].metadata["question_type"] == "multi-session"
    temporal_request, _ = build_memory_system_request(
        temporal,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    archive_request, _ = build_memory_system_request(
        archive,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert temporal_request == archive_request
    assert "stratum" not in temporal_request.model_dump_json()
    assert "residency" not in temporal_request.model_dump_json()


def test_full_haystack_role_is_the_only_retrieval_capable_adapter(
    tmp_path: Path,
) -> None:
    path = tmp_path / "longmemeval_s_cleaned.json"
    digest, size = _write_rows(path, _rows())
    retrieval = LongMemEvalTaskSource(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
        artifact_role=LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    )
    assert retrieval.provenance["artifact_role"] == "full-haystack-retrieval"
    assert retrieval.provenance["retrieval_evaluation_capable"] is True
    assert {task.stratum.value for task in map(retrieval.load, retrieval.ids())} == {
        "inactive_archive"
    }
    manifest = compile_longmemeval_manifest(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
        artifact_role=LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    )
    assert manifest["artifact_role"] == "full-haystack-retrieval"
    assert manifest["artifact"]["download_url"].endswith(
        "/longmemeval_s_cleaned.json?download=true"
    )

    with pytest.raises(PublicMemorySourceError, match="unsupported.*artifact_role"):
        LongMemEvalTaskSource(
            path,
            expected_sha256=digest,
            expected_size=size,
            artifact_role="ambiguous",
        )


def test_registered_transport_panel_is_derived_and_has_required_coverage(
    tmp_path: Path,
) -> None:
    dataset = (
        tmp_path
        / "longmemeval_s_cleaned.json"
    )
    real_dataset = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "benchmarks"
        / "longmemeval"
        / "98d7416c24c778c2fee6e6f3006e7a073259d48f"
        / "longmemeval_s_cleaned.json"
    )
    if not real_dataset.is_file():
        pytest.skip("pinned full-haystack artifact is not present in this checkout")
    dataset.symlink_to(real_dataset)
    rows = json.loads(dataset.read_text())
    assert derive_longmemeval_transport_panel(rows) == (
        LONGMEMEVAL_SCREEN32_RAW_TASK_IDS
    )


def test_explicit_task_ids_are_ordered_and_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    digest, size = _write_rows(path, _rows())
    source = LongMemEvalTaskSource(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
        task_ids=("public-002_abs", "public-001"),
    )
    assert source.ids() == (
        "longmemeval-public-002_abs",
        "longmemeval-public-001",
    )
    assert source.provenance["task_selection"] == "explicit-raw-question-ids"
    with pytest.raises(PublicMemorySourceError, match="unknown LongMemEval task_ids"):
        LongMemEvalTaskSource(
            path,
            expected_sha256=digest,
            expected_size=size,
            dataset_revision="1" * 40,
            task_ids=("missing",),
        )


def test_public_source_sorts_oracle_sessions_before_sealing(tmp_path: Path) -> None:
    source = _source(tmp_path / "longmemeval.json", _rows())
    task = source.load("longmemeval-public-001")
    values = [event.value for event in task.events[:-1]]
    assert values == [
        "I used to live in Boston.",
        "I moved to Seattle.",
        "Noted.",
    ]


def test_public_source_preserves_repeated_session_occurrences(tmp_path: Path) -> None:
    rows = _rows()
    rows[0]["haystack_session_ids"] = ["session-shared", "session-shared"]
    source = _source(tmp_path / "longmemeval.json", rows)
    task = source.load("longmemeval-public-001")
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    documents = build_mempalace_session_documents(request)

    assert len(documents) == 2
    assert len({document.document_id for document in documents}) == 2
    assert [document.text for document in documents] == [
        "I used to live in Boston.",
        "I moved to Seattle.",
    ]


def test_public_source_verbatim_mode_preserves_upstream_user_bytes(
    tmp_path: Path,
) -> None:
    rows = _rows()
    rows[0]["haystack_sessions"][0][0]["content"] = "  I moved to Seattle.  "
    rows[0]["haystack_sessions"][0].append({"role": "user", "content": ""})
    path = tmp_path / "longmemeval.json"
    digest, size = _write_rows(path, rows)
    source = LongMemEvalTaskSource(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
        session_order="source",
        text_normalization="verbatim",
    )
    task = source.load("longmemeval-public-001")
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    documents = build_mempalace_session_documents(request)

    assert source.provenance["session_order"] == "source"
    assert source.provenance["text_normalization"] == "verbatim"
    assert documents[0].text == "  I moved to Seattle.  \n"
    candidate = next(event for event in task.events if event.candidate)
    assert candidate.value is not None and candidate.value.strip()


def test_public_source_rejects_artifact_tampering(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    digest, size = _write_rows(path, _rows())
    path.write_text(path.read_text() + " ")
    with pytest.raises(PublicMemorySourceError, match="size mismatch"):
        LongMemEvalTaskSource(
            path,
            expected_sha256=digest,
            expected_size=size,
            dataset_revision="1" * 40,
        )


def test_public_manifest_binds_exact_tasks_and_candidate_contract(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    digest, size = _write_rows(path, _rows())
    manifest = compile_longmemeval_manifest(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
    )
    assert manifest["status"] == "VERIFIED_PUBLIC_BENCHMARK"
    assert manifest["task_count"] == 2
    assert manifest["candidate_policy_audit"] == {
        "policy": "uniform-prefix-turn-with-committed-seed",
        "forbidden_inputs": [
            "question",
            "answer",
            "has_answer",
            "answer_session_ids",
        ],
        "exactly_one_candidate_per_task": True,
        "all_candidates_precede_query": True,
    }
    assert len(manifest["task_manifest_sha256"]) == 64
    assert len(manifest["manifest_sha256"]) == 64


def test_public_source_doctor_accepts_verified_fixture(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    digest, size = _write_rows(path, _rows())
    report = validate_public_longmemeval(
        path,
        expected_task_count=2,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
    )
    assert report["task_count"] == 2
    assert report["task_manifest_sha256"] == compile_longmemeval_manifest(
        path,
        expected_sha256=digest,
        expected_size=size,
        dataset_revision="1" * 40,
    )["task_manifest_sha256"]
