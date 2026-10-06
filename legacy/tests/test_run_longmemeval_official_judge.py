from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.memory_trials import (
    LongMemEvalJudgeError,
    LongMemEvalTaskSource,
    ReplayableMemoryWorld,
    collect_all_serve,
    prepare_longmemeval_judge_cases,
    seal_official_judge_contract,
    write_judge_packet,
)
from scripts.run_longmemeval_official_judge import (
    load_judge_packet,
    run_official_judge,
)


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _source(tmp_path: Path) -> LongMemEvalTaskSource:
    tmp_path.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "question_id": "official-001",
            "question_type": "single-session-user",
            "question": "What is the code?",
            "answer": "blue",
            "question_date": "2026/01/03 (Sat) 10:00",
            "haystack_session_ids": ["session-1"],
            "haystack_dates": ["2026/01/01 (Thu) 10:00"],
            "haystack_sessions": [[{"role": "user", "content": "The code is blue."}]],
            "answer_session_ids": ["session-1"],
        }
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


class FakeResponse:
    def __init__(self, response_id: str) -> None:
        self.payload = {
            "id": response_id,
            "model": "gpt-4o-2024-08-06",
            "system_fingerprint": "fp-fixture",
            "choices": [{"message": {"role": "assistant", "content": "yes"}}],
            "usage": {"prompt_tokens": 31, "completion_tokens": 1},
        }

    def model_dump_json(self) -> str:
        return json.dumps(self.payload, sort_keys=True, separators=(",", ":"))


class FakeOpenAI:
    def __init__(self, *, returned_model: str = "gpt-4o-2024-08-06") -> None:
        self.models = self
        self.chat = SimpleNamespace(completions=self)
        self.calls = []
        self.returned_model = returned_model

    def list(self):
        return SimpleNamespace(data=[SimpleNamespace(id="gpt-4o-2024-08-06")])

    def create(self, **payload):
        self.calls.append(payload)
        response = FakeResponse(f"chatcmpl-{len(self.calls)}")
        response.payload["model"] = self.returned_model
        return response


def _packet(tmp_path: Path) -> Path:
    source = _source(tmp_path)
    quality = collect_all_serve(
        ReplayableMemoryWorld(source), source.ids(), tmp_path / "quality"
    )
    assert quality.bundle_root is not None
    cases = prepare_longmemeval_judge_cases(source, quality.bundle_root)
    contract = seal_official_judge_contract()
    root = tmp_path / "packet"
    write_judge_packet(
        root,
        source,
        cases,
        contract,
        experiment_sha256="a" * 64,
        preparation_mode="full-benchmark",
    )
    return root


def test_official_judge_runner_seals_exact_request_and_response(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    client = FakeOpenAI()
    result = run_official_judge(packet, tmp_path / "judge", client=client)
    assert result["status"] == "OFFICIAL_PROMPT_SCORE_VALID"
    assert result["case_count"] == 1
    assert client.calls[0]["model"] == "gpt-4o-2024-08-06"
    assert client.calls[0]["temperature"] == 0
    assert client.calls[0]["n"] == 1
    assert client.calls[0]["max_tokens"] == 10
    resumed_client = FakeOpenAI()
    resumed = run_official_judge(
        packet, tmp_path / "judge", client=resumed_client, resume=True
    )
    assert resumed == result
    assert resumed_client.calls == []


def test_packet_and_returned_model_drift_fail_closed(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    cases_path = packet / "judge-cases.jsonl"
    cases_path.write_text(cases_path.read_text() + "{}\n")
    with pytest.raises(LongMemEvalJudgeError, match="hash verification"):
        load_judge_packet(packet)

    clean_packet = _packet(tmp_path / "clean")
    with pytest.raises(LongMemEvalJudgeError, match="different judge model"):
        run_official_judge(
            clean_packet,
            tmp_path / "drifted",
            client=FakeOpenAI(returned_model="gpt-4o"),
        )


def test_official_judge_resume_does_not_repeat_completed_case(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    client = FakeOpenAI()
    output = tmp_path / "judge"
    manifest, cases, contract = load_judge_packet(packet)
    del manifest
    output.mkdir()
    (output / "responses").mkdir()
    run_contract = {
        "schema_version": "1.0",
        "packet_manifest_sha256": _sha((packet / "manifest.json").read_bytes()),
        "case_root_sha256": _sha(
            json.dumps(
                [case.case_sha256 for case in cases],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ),
        "case_count": 1,
        "judge_contract_sha256": contract.contract_sha256,
    }
    (output / "run-contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True) + "\n"
    )
    # A malformed partial journal must fail rather than silently resubmit it.
    (output / "responses" / f"00000001-{cases[0].trial_id}.json").write_text("{}")
    with pytest.raises((LongMemEvalJudgeError, ValueError)):
        run_official_judge(packet, output, client=client, resume=True)
    assert client.calls == []
