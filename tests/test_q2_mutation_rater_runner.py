"""The registered rater runner: one call per item, transport-only retries, receipts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation import audit, rater_runner, raters

ROOT = Path(__file__).resolve().parents[1]


def _packet(item_id: str, pages: int = 1) -> dict[str, Any]:
    page = {"page": 1, "of": pages, "media_type": "image/png", "sha256": "ab", "data_b64": "AA=="}
    return {
        "schema": rater_runner.PACKET_SCHEMA,
        "item_id": item_id,
        "prompt_version": "RATER_PROMPT_V1",
        "instruction": "Bold the title.",
        "initial_files": [
            {"vm_path": "/home/user/a.docx", "structure": ['/body[0] = "Title"'], "pages": [page]}
        ],
        "candidate": {
            "files": [
                {
                    "vm_path": "/home/user/a.docx",
                    "structure": ['/body[0] = "Title"'],
                    "diff_vs_initial": ["changed /body[0]/bold: false -> true"],
                    "pages": [page] * pages,
                    "notes": [],
                }
            ]
        },
    }


def test_both_raters_see_the_same_parts_in_the_same_order() -> None:
    packet = _packet("i1", pages=2)
    parts = rater_runner.packet_parts(packet)
    assert [p["type"] for p in parts] == ["text", "image", "text", "image", "text", "image", "text"]
    assert parts[-1]["text"].endswith(rater_runner.ANSWER_LINE)
    anth = rater_runner.anthropic_body(packet)
    oai = rater_runner.openai_body(packet)
    anth_text = [b["text"] for b in anth["messages"][0]["content"] if b["type"] == "text"]
    oai_text = [b["text"] for b in oai["messages"][1]["content"] if b["type"] == "text"]
    assert anth_text == oai_text
    assert anth["system"] == raters.RATER_PROMPT_V1 == oai["messages"][0]["content"]
    # Registered parameters: no sampling parameter for the Anthropic model,
    # greedy decoding without thinking for the open-weight model.
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(anth)
    assert anth["max_tokens"] == 16000 and anth["output_config"] == {"effort": "high"}
    assert anth["model"] == raters.RATERS[0]["registry_id"]
    assert (oai["temperature"], oai["top_p"], oai["seed"], oai["max_tokens"]) == (0.0, 1.0, 42, 256)
    assert oai["chat_template_kwargs"] == {"enable_thinking": False}
    # The body is a pure function of the packet: its digest is reproducible.
    again = rater_runner.canonical_bytes(rater_runner.request_body("model-rater-anthropic", packet))
    assert again == rater_runner.canonical_bytes(anth)


def test_retries_only_on_transport_errors_and_at_most_three() -> None:
    attempts = iter(
        [
            rater_runner.Attempt(transport_error="ConnectError"),
            rater_runner.Attempt(status=529),
            rater_runner.Attempt(status=200, response_bytes=b"{}"),
        ]
    )
    final, log = rater_runner.call_with_retries(lambda: next(attempts), sleep=lambda _: None)
    assert final.status == 200 and len(log) == 3
    # A rejected request is an answer (unsure), never retried.
    once = rater_runner.call_with_retries(
        lambda: rater_runner.Attempt(status=400, response_bytes=b"{}"), sleep=lambda _: None
    )
    assert len(once[1]) == 1
    calls = []

    def flaky() -> rater_runner.Attempt:
        calls.append(1)
        return rater_runner.Attempt(transport_error="ReadTimeout", timeout=True)

    final, log = rater_runner.call_with_retries(flaky, sleep=lambda _: None)
    assert len(calls) == 1 + rater_runner.MAX_TRANSPORT_RETRIES == 4
    assert rater_runner.anthropic_reply(final).outcome == "timeout"
    with pytest.raises(rater_runner.FatalRunError):
        rater_runner.call_with_retries(
            lambda: rater_runner.Attempt(status=401), sleep=lambda _: None
        )


def _anthropic_response(text: str, stop: str = "end_turn") -> bytes:
    body = {
        "id": "msg_1",
        "model": "claude-opus-5-5",
        "stop_reason": stop,
        "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}],
        "usage": {"input_tokens": 10, "output_tokens": 3},
    }
    return json.dumps(body).encode()


def test_replies_map_to_answers() -> None:
    ok = rater_runner.anthropic_reply(
        rater_runner.Attempt(status=200, response_bytes=_anthropic_response("Reject. B2 differs."))
    )
    assert ok.outcome == "ok" and raters.answer_for(ok.outcome, ok.text) == ("reject", "ok")
    refusal = rater_runner.anthropic_reply(
        rater_runner.Attempt(status=200, response_bytes=_anthropic_response("", "refusal"))
    )
    assert raters.answer_for(refusal.outcome, refusal.text) == ("unsure", "refusal")
    rejected = rater_runner.openai_reply(rater_runner.Attempt(status=400, response_bytes=b"{}"))
    assert raters.answer_for(rejected.outcome, rejected.text) == ("unsure", "request_rejected")
    body = {
        "model": "q2m-rater",
        "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
    }
    empty = rater_runner.openai_reply(
        rater_runner.Attempt(status=200, response_bytes=json.dumps(body).encode())
    )
    assert raters.answer_for(empty.outcome, empty.text) == ("unsure", "empty")


def test_runner_calls_each_item_once_and_resumes(tmp_path: Path) -> None:
    packets = [_packet(f"i{n}") for n in range(5)]
    sent: list[str] = []

    def send(item_id: str, payload: bytes) -> rater_runner.Attempt:
        sent.append(item_id)
        reply = "accept" if item_id != "i3" else "maybe"
        body = {"model": "q2m-rater", "choices": [{"message": {"content": reply}}]}
        return rater_runner.Attempt(
            status=200, request_bytes=payload, response_bytes=json.dumps(body).encode()
        )

    runner = rater_runner.Runner(
        "model-rater-open-weight", tmp_path, send, rater_runner.openai_reply, workers=2
    )
    result = runner.run(packets[:3])
    assert sorted(sent) == ["i0", "i1", "i2"] and result["rated_now"] == 3
    # A resumed run on the same directory never sends a rated item again.
    result = runner.run(packets)
    assert sorted(sent) == ["i0", "i1", "i2", "i3", "i4"] and result["rated_before"] == 3
    calls = rater_runner.read_calls(tmp_path / "calls.jsonl")
    assert calls["i3"]["answer"] == "unsure" and calls["i3"]["status"] == "unparseable"
    row = calls["i0"]
    body = rater_runner.request_body("model-rater-open-weight", packets[0])
    assert row["body_sha256"] == rater_runner.sha256_bytes(rater_runner.canonical_bytes(body))
    assert row["request_sha256"] == row["body_sha256"]  # the open rater sends the canonical bytes
    assert row["response_sha256"] and (tmp_path / "responses" / "i0.json").is_file()
    receipt = rater_runner.write_receipt(tmp_path, {"result": result})
    assert receipt["calls_sha256"] == rater_runner.sha256_file(tmp_path / "calls.jsonl")
    assert set(receipt["code_sha256"]) == {"raters.py", "rater_runner.py"}
    got = rater_runner.answers(tmp_path / "calls.jsonl", ["i0", "i3", "never"])
    assert got == {
        "i0": ("accept", "ok"),
        "i3": ("unsure", "unparseable"),
        "never": ("unsure", "unrated"),
    }


def test_a_fatal_error_stops_the_run(tmp_path: Path) -> None:
    def send(item_id: str, payload: bytes) -> rater_runner.Attempt:
        return rater_runner.Attempt(status=401)

    runner = rater_runner.Runner(
        "model-rater-anthropic", tmp_path, send, rater_runner.anthropic_reply, workers=1
    )
    result = runner.run([_packet("i0"), _packet("i1")])
    assert result["fatal"] and result["stopped"]
    assert result["unrated"] == ["i0", "i1"]


def test_load_packets_checks_digest_and_schema(tmp_path: Path) -> None:
    path = tmp_path / "p.jsonl"
    path.write_text(json.dumps(_packet("i0")) + "\n", encoding="utf-8")
    assert len(rater_runner.load_packets(path, rater_runner.sha256_file(path))) == 1
    with pytest.raises(SystemExit, match="SHA-256"):
        rater_runner.load_packets(path, "0" * 64)
    path.write_text(json.dumps({**_packet("i0"), "schema": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not a"):
        rater_runner.load_packets(path)


def test_engine_argv_is_fixed() -> None:
    argv = rater_runner.engine_argv("/model-cache/cotcodec-models/qwen3.5-9b")
    assert argv[:3] == ["vllm", "serve", "/model-cache/cotcodec-models/qwen3.5-9b"]
    assert "--no-enable-prefix-caching" in argv and argv[argv.index("--seed") + 1] == "42"
    assert argv[argv.index("--host") + 1] == "127.0.0.1"


def test_audit_sample_items_and_text_packets(tmp_path: Path) -> None:
    start = tmp_path / "start.json"
    start.write_text('{"a": 1}\n', encoding="utf-8")
    mutant = tmp_path / "mutant.json"
    mutant.write_text('{"a": 2}\n', encoding="utf-8")
    null = tmp_path / "null.json"
    null.write_text('{"a": 1}\n', encoding="utf-8")
    vm = "/home/user/settings.json"
    outcomes = [
        {
            "mutant_id": f"t1__config.viol.value_change__{n}",
            "task_id": "t1",
            "target_id": "t1__x",
            "label": "should_fail_violation",
            "lock_status": "evaluable",
            "lock_verdict": "fail",
            "probe_touched": False,
        }
        for n in range(3)
    ]
    saved = [
        {
            "mutant_id": o["mutant_id"],
            "task_id": "t1",
            "kind": "mutant",
            "files": {vm: "/ro/build/" + mutant.name},
        }
        for o in outcomes
    ] + [
        {
            "mutant_id": "t1__null__x",
            "task_id": "t1",
            "kind": "null",
            "files": {vm: "/ro/build/" + null.name},
        }
    ]
    targets = [{"task_id": "t1", "vm_path": vm, "context_files": {vm: "/gold"}}]
    built = audit.build_sample(
        outcomes,
        saved,
        targets,
        initial_of=lambda task: {vm: str(start)},
        path_map=[("/ro/build/", str(tmp_path) + "/")],
    )
    strata = sorted(r["stratum"] for r in built["sample"])
    assert strata == ["agreement", "agreement", "agreement", "sham"]
    assert all("label" not in item and "verdict" not in str(item) for item in built["items"])
    item = next(i for i in built["items"] if i["candidate"][vm] == str(mutant))
    packet = audit.build_packet(item, "Set a to 3.", tmp_path / "work")
    assert packet["schema"] == rater_runner.PACKET_SCHEMA
    assert raters._leaked_keys(packet) == []
    end = packet["candidate"]["files"][0]
    assert end["vm_path"] == vm and end["pages"] == [] and end["diff_vs_initial"]
    assert packet["initial_files"][0]["structure"] == ['{"a": 1}']
    parts = rater_runner.packet_parts(packet)
    assert "Set a to 3." in parts[0]["text"]


def test_audit_summarize_end_to_end(tmp_path: Path) -> None:
    rows = []
    for n in range(4):
        rows.append(
            {
                "mutant_id": f"m{n}",
                "task_id": f"t{n}",
                "stratum": "agreement",
                "inclusion_probability": 0.5,
                "sham": None,
                "item_id": f"i{n}",
                "label": "should_pass_equiv",
                "verdict": "pass",
            }
        )
    audit.write_jsonl(tmp_path / "sample.jsonl", rows)
    for rater, answer in (("a", "accept"), ("b", "reject")):
        calls = [
            {"item_id": f"i{n}", "answer": answer if n else "accept", "status": "ok"}
            for n in range(3)
        ]
        audit.write_jsonl(tmp_path / rater / "calls.jsonl", calls)
    audit.write_jsonl(tmp_path / "adj.jsonl", [{"item_id": "i1", "answer": "accept"}])
    code = audit.main(
        [
            "summarize",
            "--sample",
            str(tmp_path / "sample.jsonl"),
            "--calls",
            str(tmp_path / "a" / "calls.jsonl"),
            str(tmp_path / "b" / "calls.jsonl"),
            "--adjudications",
            str(tmp_path / "adj.jsonl"),
            "--out",
            str(tmp_path / "out"),
            "--n-boot",
            "50",
        ]
    )
    assert code == 0
    summary = json.loads((tmp_path / "out" / "audit-summary.json").read_text())
    decisions = {
        r["key"]: r["decision"] for r in audit.read_jsonl(tmp_path / "out" / "decisions.jsonl")
    }
    # m0 agreed; m1 adjudicated; m2 unresolved; m3 never rated by either rater.
    assert decisions == {"m0": "accept", "m1": "accept", "m2": "unresolved", "m3": "unresolved"}
    assert summary["n_adjudicated"] == 1 and summary["human_spot_check"] == "pending"
    assert summary["answer_status"]["model-rater-open-weight"]["unrated"] == 1


def test_render_rater_manifest_passes_the_lane_validator(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "infra" / "q2-mutation" / "run"))
    import render_rater_manifest
    import submit_docker_research_job
    import yaml

    packets = tmp_path / "packets-000.jsonl"
    packets.write_text(json.dumps(_packet("i0")) + "\n", encoding="utf-8")
    base = [
        "--name",
        "q2m-rater-smoke",
        "--image-id",
        "sha256:" + "a" * 64,
        "--git-sha",
        "b" * 40,
        "--source-sha256",
        "c" * 64,
        "--packets",
        str(packets),
        "--packets-revision",
        "d" * 40,
        "--run-root",
        "/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/raters/smoke",
    ]
    out = tmp_path / "m.yaml"
    assert (
        render_rater_manifest.main(
            [
                *base,
                "--minutes",
                "12",
                "--max-gpu-hours",
                "0.2",
                "--kind",
                "smoke",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    manifest = submit_docker_research_job.validate_manifest(
        yaml.safe_load(out.read_text()), verify_claim_files=False
    )
    assert manifest["container_profile"] == "vllm" and manifest["max_gpu_hours"] == 0.2
    assert manifest["model"]["model_id"] == raters.RATERS[1]["registry_id"]
    assert manifest["study_artifact"]["sha256"] == rater_runner.sha256_file(packets)
    with pytest.raises(SystemExit, match="capped"):
        render_rater_manifest.main(
            [
                *base,
                "--minutes",
                "30",
                "--max-gpu-hours",
                "0.5",
                "--kind",
                "smoke",
                "--out",
                str(out),
            ]
        )
    with pytest.raises(SystemExit, match="capped"):
        render_rater_manifest.main(
            [
                *base,
                "--minutes",
                "60",
                "--max-gpu-hours",
                "1.5",
                "--kind",
                "audit",
                "--out",
                str(out),
            ]
        )
