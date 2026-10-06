from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.causal_memory_trials import TrialOutcome
from harness.memory_trials import (
    LongMemEvalJudgeError,
    LongMemEvalTaskSource,
    ReplayableMemoryWorld,
    collect_all_serve,
    official_answer_check_prompt,
    official_judge_request_payload,
    parse_official_judgment,
    prepare_longmemeval_judge_cases,
    seal_judgment,
    seal_official_judge_contract,
    summarize_longmemeval_judgments,
    write_judge_packet,
)


def _sha(value: str | bytes) -> str:
    data = value.encode() if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _source(tmp_path: Path) -> LongMemEvalTaskSource:
    rows = [
        {
            "question_id": "judge-001",
            "question_type": "temporal-reasoning",
            "question": "How many days later?",
            "answer": "18 days",
            "question_date": "2026/01/03 (Sat) 10:00",
            "haystack_session_ids": ["session-1"],
            "haystack_dates": ["2026/01/01 (Thu) 10:00"],
            "haystack_sessions": [
                [{"role": "user", "content": "The visit was January 1."}]
            ],
            "answer_session_ids": ["session-1"],
        },
        {
            "question_id": "judge-002_abs",
            "question_type": "single-session-user",
            "question": "What is my favorite moon?",
            "answer": "The information is not present.",
            "question_date": "2026/01/03 (Sat) 10:00",
            "haystack_session_ids": ["session-2"],
            "haystack_dates": ["2026/01/01 (Thu) 10:00"],
            "haystack_sessions": [
                [{"role": "assistant", "content": "You own a telescope."}]
            ],
            "answer_session_ids": [],
        },
    ]
    encoded = json.dumps(rows, sort_keys=True).encode()
    path = tmp_path / "longmemeval.json"
    path.write_bytes(encoded)
    return LongMemEvalTaskSource(
        path,
        expected_sha256=_sha(encoded),
        expected_size=len(encoded),
        dataset_revision="1" * 40,
        candidate_seed=42,
    )


def _outcome(answer: str) -> TrialOutcome:
    artifacts = {
        "trace": json.dumps({"event": "completed"}, sort_keys=True),
        "prompt": json.dumps({"messages": []}, sort_keys=True),
        "memory_frame": json.dumps({"evidence": []}, sort_keys=True),
        "model_output": answer,
        "model_receipt": json.dumps({"model": "fixture"}, sort_keys=True),
        "tool_trace": json.dumps(
            {"actual": {"mode": "answer", "answer": answer}}, sort_keys=True
        ),
    }
    return TrialOutcome(
        visibility="serve",
        utility=1.0,
        success=True,
        restored_snapshot_sha256="a" * 64,
        replay_key="b" * 64,
        rng_state_sha256="c" * 64,
        tool_tape_sha256="d" * 64,
        exogenous_trace_sha256="e" * 64,
        candidate_visible=True,
        trace_json=artifacts["trace"],
        trace_sha256=_sha(artifacts["trace"]),
        prompt_json=artifacts["prompt"],
        prompt_sha256=_sha(artifacts["prompt"]),
        memory_frame_json=artifacts["memory_frame"],
        memory_frame_sha256=_sha(artifacts["memory_frame"]),
        model_output_json=artifacts["model_output"],
        model_output_sha256=_sha(artifacts["model_output"]),
        model_receipt_json=artifacts["model_receipt"],
        model_receipt_sha256=_sha(artifacts["model_receipt"]),
        tool_trace_json=artifacts["tool_trace"],
        tool_trace_sha256=_sha(artifacts["tool_trace"]),
    )


def _bundle(tmp_path: Path, source: LongMemEvalTaskSource) -> Path:
    root = tmp_path / "bundle"
    root.mkdir()
    answers = ("19 days", "I do not have that information.")
    rows = [
        {
            "trial_id": trial_id,
            "outcome": _outcome(answer).model_dump(mode="json"),
        }
        for trial_id, answer in zip(source.ids(), answers, strict=True)
    ]
    observed = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    (root / "observed_trials.jsonl").write_text(observed)
    provenance = {
        **source.provenance,
        "world": "replayable-memory-world-v1",
        "actor": "fixture-actor-v1",
        "snapshot_owner": "harness.memory_trials.engine",
        "tool_tape_owner": "harness.memory_trials.engine",
        "memory_system": "fixture-memory-v1",
        "memory_treatment_mode": "storage_and_service",
    }
    manifest = {
        "schema_version": "1.0",
        "status": "COMPLETE",
        "world_provenance": provenance,
        "plan": {"assignment_seed": 42, "trial_ids": list(source.ids())},
        "files": {"observed_trials.jsonl": _sha(observed)},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return root


def _judgments(cases: tuple, contract) -> tuple:
    responses = ("yes", "no")
    judgments = []
    for sequence, (case, response) in enumerate(
        zip(cases, responses, strict=True), start=1
    ):
        provider_response = json.dumps(
            {
                "id": f"chatcmpl-{sequence}",
                "model": contract.requested_model,
                "choices": [{"message": {"role": "assistant", "content": response}}],
                "usage": {"prompt_tokens": 20 + sequence, "completion_tokens": 1},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        request = official_judge_request_payload(case, contract)
        judgments.append(
            seal_judgment(
                {
                "schema_version": "1.0",
                "sequence": sequence,
                "case_sha256": case.case_sha256,
                "judge_contract_sha256": contract.contract_sha256,
                "judge_model_id": contract.requested_model,
                "openai_sdk_version": contract.sdk_version,
                "request_sha256": _sha(
                    json.dumps(request, sort_keys=True, separators=(",", ":"))
                ),
                "provider_response_json": provider_response,
                "provider_response_id": f"chatcmpl-{sequence}",
                "raw_response": response,
                "input_tokens": 20 + sequence,
                "output_tokens": 1,
            }
        )
        )
    return tuple(judgments)


def test_prompt_port_dispatches_temporal_and_abstention_contracts() -> None:
    temporal = official_answer_check_prompt(
        "temporal-reasoning", "When?", "18 days", "19 days", abstention=False
    )
    assert "do not penalize off-by-one errors" in temporal
    abstention = official_answer_check_prompt(
        "single-session-user", "Unknown?", "Absent", "I do not know", abstention=True
    )
    assert "unanswerable question" in abstention
    assert "Does the model correctly identify" in abstention
    assert parse_official_judgment("yes") == (True, True)
    assert parse_official_judgment("No.") == (False, True)
    assert parse_official_judgment("yesterday") == (True, False)


def test_judge_cases_bind_complete_source_and_bundle_provenance(tmp_path: Path) -> None:
    source = _source(tmp_path)
    bundle = _bundle(tmp_path, source)
    cases = prepare_longmemeval_judge_cases(source, bundle)
    assert len(cases) == 2
    assert [case.abstention for case in cases] == [False, True]
    assert cases[0].hypothesis == "19 days"
    contract = seal_official_judge_contract("2.53.0")
    packet = write_judge_packet(
        tmp_path / "packet",
        source,
        cases,
        contract,
        experiment_sha256="a" * 64,
        preparation_mode="transport-panel",
    )
    assert packet["case_count"] == 2
    assert packet["question_type_counts"] == {
        "single-session-user": 1,
        "temporal-reasoning": 1,
    }
    assert packet["judge_contract_sha256"] == contract.contract_sha256
    assert packet["task_manifest_sha256"] == cases[0].source_task_manifest_sha256
    assert packet["source_world_provenance_sha256"] == (
        cases[0].source_world_provenance_sha256
    )

    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["world_provenance"]["adapter_version"] = "drifted-adapter"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(LongMemEvalJudgeError, match="benchmark adapter differ"):
        prepare_longmemeval_judge_cases(source, bundle)


def test_judgment_summary_fails_closed_on_order_and_receipt_drift(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    cases = prepare_longmemeval_judge_cases(source, _bundle(tmp_path, source))
    contract = seal_official_judge_contract("2.53.0")
    judgments = _judgments(cases, contract)
    report = summarize_longmemeval_judgments(cases, judgments, contract)
    assert report["accuracy"] == 0.5
    assert report["well_formed_response_rate"] == 1.0
    assert report["evaluation_mode"] == "randomized-causal"
    with pytest.raises(LongMemEvalJudgeError, match="sequence|ordered judge cases"):
        summarize_longmemeval_judgments(cases, tuple(reversed(judgments)), contract)

    drifted = judgments[1].model_copy(update={"openai_sdk_version": "9.9.9"})
    with pytest.raises(LongMemEvalJudgeError, match="immutable judge contract"):
        summarize_longmemeval_judgments(cases, (judgments[0], drifted), contract)

    wrong_request = judgments[1].model_copy(update={"request_sha256": "0" * 64})
    with pytest.raises(LongMemEvalJudgeError, match="does not bind the case prompt"):
        summarize_longmemeval_judgments(
            cases, (judgments[0], wrong_request), contract
        )


def test_judge_packet_accepts_complete_all_serve_quality_bundle(tmp_path: Path) -> None:
    source = _source(tmp_path)
    result = collect_all_serve(
        ReplayableMemoryWorld(source), source.ids(), tmp_path / "all-serve"
    )
    assert result.bundle_root is not None
    cases = prepare_longmemeval_judge_cases(source, result.bundle_root)
    assert len(cases) == len(source.ids())
    assert {case.evaluation_mode for case in cases} == {
        "all-serve-system-quality"
    }
    assert {case.assignment_seed for case in cases} == {None}
    assert {case.visibility for case in cases} == {"serve"}
    with pytest.raises(LongMemEvalJudgeError, match="mode differs"):
        write_judge_packet(
            tmp_path / "mislabelled",
            source,
            cases,
            seal_official_judge_contract("2.53.0"),
            experiment_sha256="a" * 64,
            preparation_mode="transport-panel",
        )


def test_all_serve_judge_rejects_a_holdout_outcome(tmp_path: Path) -> None:
    source = _source(tmp_path)
    result = collect_all_serve(
        ReplayableMemoryWorld(source), source.ids(), tmp_path / "all-serve"
    )
    assert result.bundle_root is not None
    observed_path = result.bundle_root / "observed_trials.jsonl"
    rows = [json.loads(line) for line in observed_path.read_text().splitlines()]
    rows[0]["outcome"]["visibility"] = "holdout"
    rows[0]["outcome"]["candidate_visible"] = False
    observed = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    observed_path.write_text(observed)
    manifest_path = result.bundle_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["observed_trials.jsonl"] = _sha(observed)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(LongMemEvalJudgeError, match="holdout|hidden-candidate"):
        prepare_longmemeval_judge_cases(source, result.bundle_root)


def test_judge_packet_rejects_empty_and_mixed_contracts(tmp_path: Path) -> None:
    source = _source(tmp_path)
    with pytest.raises(LongMemEvalJudgeError, match="at least one case"):
        write_judge_packet(
            tmp_path / "empty",
            source,
            (),
            seal_official_judge_contract("2.53.0"),
            experiment_sha256="a" * 64,
            preparation_mode="transport-panel",
        )

    cases = prepare_longmemeval_judge_cases(source, _bundle(tmp_path, source))
    mixed = cases[1].model_copy(update={"assignment_seed": 43})
    with pytest.raises(LongMemEvalJudgeError, match="mixes evaluation contracts"):
        write_judge_packet(
            tmp_path / "mixed",
            source,
            (cases[0], mixed),
            seal_official_judge_contract("2.53.0"),
            experiment_sha256="a" * 64,
            preparation_mode="transport-panel",
        )
