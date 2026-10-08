"""The registered rater runner: one call per item, transport-only retries, receipts."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation import audit, rater_runner, raters

ROOT = Path(__file__).resolve().parents[1]
SALT = "c3" * 32


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
    # Registered parameters: no sampling parameter for the Anthropic model; for
    # the open-weight model thinking on with the model card's sampling for
    # thinking on general tasks, seeded, one configuration (decision D34).
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(anth)
    assert anth["max_tokens"] == 16000 and anth["output_config"] == {"effort": "high"}
    assert anth["model"] == raters.RATERS[0]["registry_id"]
    assert {k: oai[k] for k in ("temperature", "top_p", "top_k", "min_p")} == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
    }
    assert (oai["presence_penalty"], oai["repetition_penalty"]) == (1.5, 1.0)
    assert (oai["seed"], oai["max_tokens"]) == (42, 8192)
    assert oai["chat_template_kwargs"] == {"enable_thinking": True}
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


def _call(rater_id: str, item_id: str, answer: str) -> dict:
    """A minimal record in the shared call schema."""
    return {
        "schema": rater_runner.CALL_SCHEMA,
        "rater_id": rater_id,
        "item_id": item_id,
        "answer": answer,
        "status": "ok",
        "outcome": "ok",
    }


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
    def reply(content: str | None, finish: str = "stop") -> rater_runner.Reply:
        body = {
            "model": "q2m-rater",
            "choices": [{"message": {"content": content}, "finish_reason": finish}],
        }
        return rater_runner.openai_reply(
            rater_runner.Attempt(status=200, response_bytes=json.dumps(body).encode())
        )

    # Thinking on (decision D34): the answer is the first word after the last
    # </think>; a reply cut inside its thinking holds no answer.
    thought = reply("The title on slide 3 is gone.\n</think>\n\nReject. Slide 3 lost its title.")
    assert raters.answer_for(thought.outcome, thought.text) == ("reject", "ok")
    assert thought.extra["thinking_finished"] is True
    cut = reply("I should look at slide 3 and then", finish="length")
    assert raters.answer_for(cut.outcome, cut.text) == ("unsure", "thinking_unfinished")
    assert cut.stop_reason == "length" and cut.extra["thinking_finished"] is False
    assert raters.answer_for(reply("").outcome, None) == ("unsure", "thinking_unfinished")
    empty = reply("done</think>\n\n")
    assert raters.answer_for(empty.outcome, empty.text) == ("unsure", "empty")
    # Only the text after the thinking is read: an answer word inside it is not.
    inner = reply("accept? No.</think>\nMaybe it is fine.")
    assert raters.answer_for(inner.outcome, inner.text) == ("unsure", "unparseable")


def test_runner_calls_each_item_once_and_resumes(tmp_path: Path) -> None:
    packets = [_packet(f"i{n}") for n in range(5)]
    sent: list[str] = []

    def send(item_id: str, payload: bytes) -> rater_runner.Attempt:
        sent.append(item_id)
        reply = "ok</think>\n\n" + ("accept" if item_id != "i3" else "maybe")
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
            "target_id": "t1__x",
            "kind": "null",
            "files": {vm: "/ro/build/" + null.name},
        }
    ]
    targets = [
        {
            "task_id": "t1",
            "target_id": "t1__x",
            "family": "config",
            "vm_path": vm,
            "initial": str(start),
            "context_files": {vm: "/gold"},
        }
    ]
    built = audit.build_sample(
        outcomes,
        saved,
        targets,
        initial_of=lambda task: {vm: str(start)},
        salt=SALT,
        path_map=[("/ro/build/", str(tmp_path) + "/")],
    )
    strata = sorted(r["stratum"] for r in built["sample"])
    assert strata == ["sham", "violation", "violation", "violation"]
    assert all("label" not in item and "verdict" not in str(item) for item in built["items"])
    # One saved-baseline job per target: a text target's starting file goes
    # through the save stage as it is (no UNO save).
    assert built["baseline_jobs"] == [
        {
            "job_id": "baseline__t1__x",
            "mutant_id": "baseline__t1__x",
            "task_id": "t1",
            "target_id": "t1__x",
            "kind": "baseline",
            "files": {vm: str(start)},
        }
    ]
    item = next(i for i in built["items"] if i["candidate"][vm] == str(mutant))
    assert item["baseline_job"] == "baseline__t1__x"
    assert item["baseline_source"] == "mutation_save_stage"
    report = audit.resolve_baselines(
        built["items"],
        built["baseline_jobs"],
        [{"job_id": "baseline__t1__x", "outputs": {}, "saves": [], "before_sha256": {}}],
    )
    assert report["saved"] == 1 and item["baseline"] == {vm: str(start)}
    packet = audit.build_packet(item, "Set a to 3.", tmp_path / "work")
    assert packet["schema"] == rater_runner.PACKET_SCHEMA
    assert raters._leaked_keys(packet) == []
    end = packet["candidate"]["files"][0]
    assert end["vm_path"] == vm and end["pages"] == [] and end["diff_vs_initial"]
    assert end["baseline"] == "saved" and end["save_only_changes"] == 0
    assert packet["initial_files"][0]["structure"] == ['{"a": 1}']
    assert packet["fit"]["fits"] and packet["fit"]["cuts"] == []
    parts = rater_runner.packet_parts(packet)
    assert "Set a to 3." in parts[0]["text"]


def _xlsx_world(tmp_path: Path) -> dict[str, Any]:
    """Raw start, a save that only changes a document property, and a mutant edit."""
    from harness.q2_mutation.operators import _synth as synth

    build = tmp_path / "build"
    target_id = "t1__abc"
    name = "book.xlsx"
    start = synth.build_xlsx(tmp_path / "cache" / name)
    uno_saved = build / "prep" / target_id / "initial" / name
    uno_saved.parent.mkdir(parents=True)
    synth.build_xlsx(uno_saved, title="Saved by LibreOffice")
    gui_saved = synth.build_xlsx(tmp_path / "out" / "baseline" / name, title="Saved by LibreOffice")
    mutant = synth.build_xlsx(
        build / "lo" / name, title="Saved by LibreOffice", cells={"Data": {"B8": ("n", 12, 2)}}
    )
    return {
        "build": build,
        "target_id": target_id,
        "start": start,
        "uno_saved": uno_saved,
        "gui_saved": gui_saved,
        "mutant": mutant,
        "vm": f"/home/user/{name}",
    }


def test_packet_difference_is_against_the_saved_starting_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Save-stage changes (here a document property) are not shown as edits."""
    monkeypatch.setattr(audit, "render_pages", lambda *a, **k: [])
    w = _xlsx_world(tmp_path)
    vm = w["vm"]
    outcomes = [
        {
            "mutant_id": "m1",
            "task_id": "t1",
            "target_id": w["target_id"],
            "label": "should_pass_equiv",
            "lock_status": "evaluable",
            "lock_verdict": "pass",
            "probe_touched": False,
        }
    ]
    saved_jobs = [
        {"mutant_id": "m1", "task_id": "t1", "kind": "mutant", "files": {vm: str(w["mutant"])}},
        {
            "mutant_id": "t1__null__abc",
            "task_id": "t1",
            "target_id": w["target_id"],
            "kind": "null",
            "files": {vm: str(w["mutant"])},
        },
    ]
    targets = [
        {
            "task_id": "t1",
            "target_id": w["target_id"],
            "family": "xlsx",
            "vm_path": vm,
            "initial": str(w["start"]),
            "context_files": {vm: "/gold.xlsx"},
        }
    ]
    built = audit.build_sample(
        outcomes,
        saved_jobs,
        targets,
        initial_of=lambda task: {vm: str(w["start"])},
        salt=SALT,
        build_root=str(w["build"]) + "/",
    )
    (job,) = built["baseline_jobs"]
    # The target file enters the save stage as the build saved it (uno_apply).
    assert job["files"] == {vm: str(w["uno_saved"])}
    rows = [
        {
            "job_id": job["job_id"],
            "outputs": {vm: str(w["gui_saved"])},
            "saves": [{"vm_path": vm, "written": True, "reason": "agent_save"}],
            "before_sha256": {vm: "x"},
        }
    ]
    audit.resolve_baselines(built["items"], built["baseline_jobs"], rows)
    item = next(i for i in built["items"] if i["candidate"][vm] == str(w["mutant"]))
    assert item["baseline"] == {vm: str(w["gui_saved"])} and item["baseline_status"] == "saved"
    packet = audit.build_packet(item, "Format B8.", tmp_path / "work")
    end = packet["candidate"]["files"][0]
    diff = "\n".join(end["diff_vs_initial"])
    assert "B8" in diff and "Saved by LibreOffice" not in diff
    assert end["baseline"] == "saved" and end["save_only_changes"] >= 1
    assert any("not edits" in note for note in end["notes"])
    start_entry = packet["initial_files"][0]
    assert start_entry["baseline"] == "saved" and any(
        "Saved by LibreOffice" in line for line in start_entry["structure"]
    )
    text = "".join(p["text"] for p in rater_runner.packet_parts(packet) if p["type"] == "text")
    assert "save alone changes" in text
    # The raw-baseline difference would have shown the save's own change.
    raw = packets_mod().artifacts({vm: str(w["start"])}, {vm: str(w["mutant"])})[vm]
    assert "Saved by LibreOffice" in "\n".join(raw["diff_vs_initial"])
    # A failed baseline save falls back to the raw starting file and says so.
    failed = dict(item, baseline=None, baseline_status=None)
    audit.resolve_baselines([failed], built["baseline_jobs"], [])
    assert failed["baseline_status"] == "save_failed"
    fallback = audit.build_packet(failed, "Format B8.", tmp_path / "work2")
    assert fallback["candidate"]["files"][0]["baseline"] == "raw"
    assert any("raw starting file" in n for n in fallback["candidate"]["files"][0]["notes"])


def packets_mod() -> Any:
    from harness.q2_mutation import packets

    return packets


def test_p1_flips_and_do_nothing_shams_use_the_control_saved_start(tmp_path: Path) -> None:
    vm = "/home/user/a.json"
    raw = tmp_path / "raw.json"
    raw.write_text('{"a": 1}\n', encoding="utf-8")
    saved_start = tmp_path / "saved-start.json"
    saved_start.write_text('{"a": 1}\n', encoding="utf-8")
    saved_gold = tmp_path / "saved-gold.json"
    saved_gold.write_text('{"a": 3}\n', encoding="utf-8")
    outcomes = [
        {
            "mutant_id": f"m{n}",
            "task_id": "t1",
            "target_id": "t1__x",
            "label": "should_pass_equiv",
            "lock_status": "evaluable",
            "lock_verdict": "pass",
            "probe_touched": False,
        }
        for n in range(12)
    ]
    saved = [
        *(
            {"mutant_id": f"m{n}", "task_id": "t1", "kind": "mutant", "files": {vm: str(raw)}}
            for n in range(12)
        ),
        {
            "mutant_id": "t1__null__x",
            "task_id": "t1",
            "target_id": "t1__x",
            "kind": "null",
            "files": {vm: str(raw)},
        },
    ]
    targets = [
        {
            "task_id": "t1",
            "target_id": "t1__x",
            "family": "config",
            "vm_path": vm,
            "initial": str(raw),
            "context_files": {vm: "/g"},
        }
    ]
    controls_saved = [
        {"kind": "gold", "task_id": "t1", "files": {vm: str(saved_gold)}},
        {"kind": "initial", "task_id": "t1", "files": {vm: str(saved_start)}},
    ]
    tasks = {
        "t1": {
            "gold_raw_lock": {"verdict": "pass"},
            "gold_saved_lock": {"verdict": "fail"},
            "gold_save": {"placed_office": ["/home/user/a.docx"], "saves": []},
        }
    }
    built = audit.build_sample(
        outcomes,
        saved,
        targets,
        initial_of=lambda task: {vm: str(raw)},
        salt=SALT,
        controls_tasks=tasks,
        controls_saved=controls_saved,
    )
    by_stratum = {r["stratum"]: r["item_id"] for r in built["sample"]}
    items = {i["item_id"]: i for i in built["items"]}
    flip = items[by_stratum["p1_flip"]]
    assert flip["candidate"] == {vm: str(saved_gold)}
    assert flip["baseline"] == {vm: str(saved_start)}
    assert flip["baseline_source"] == "control_save_stage"
    sham = next(items[r["item_id"]] for r in built["sample"] if r.get("sham") == "do_nothing")
    # The do-nothing end state is the control's saved do-nothing itself.
    assert sham["candidate"] == {vm: str(saved_start)} == sham["baseline"]


def test_fit_packet_shortens_starting_listings_first_and_records_cuts() -> None:
    big = [f"/sheet[0]/cell[{i}] = {i}" for i in range(4000)]
    packet = _packet("i0")
    packet["initial_files"][0]["structure"] = list(big)
    packet["candidate"]["files"][0]["structure"] = list(big)
    packet["candidate"]["files"][0]["diff_vs_initial"] = [f"changed {i}" for i in range(300)]
    before = audit.estimate_tokens(packet)
    budget = before - 20_000
    fit = audit.fit_packet(packet, budget=budget)
    assert fit["estimated_tokens"] == before and fit["fits"]
    assert fit["estimated_tokens_after"] <= budget
    assert fit["cuts"][0]["kind"] == "starting file"
    assert packet["initial_files"][0]["structure"][-1].endswith(audit.FIT_NOTE)
    # The end-state difference is the last thing cut and stayed whole here.
    assert len(packet["candidate"]["files"][0]["diff_vs_initial"]) == 300
    # The registered budget leaves the reply (thinking and answer) and the prompt
    # allowance in the window, and the window is the engine's (decision D34).
    assert audit.PACKET_TOKEN_BUDGET == 139_264 - 8_192 - 2_048 == 129_024
    assert dict(rater_runner.ENGINE_FLAGS)["max_model_len"] == audit.CONTEXT_TOKENS
    assert rater_runner.OPEN_WEIGHT["max_tokens"] == audit.ANSWER_TOKENS
    small = _packet("i1")
    assert audit.fit_packet(small)["cuts"] == [] and small["fit"]["fits"]
    tiny = _packet("i2", pages=3)
    fit = audit.fit_packet(tiny, budget=1)
    assert fit["images_dropped"] == 4 and fit["fits"] is False
    assert any("rendered pages not shown" in n for n in tiny["candidate"]["files"][0]["notes"])


def test_image_tokens_follow_the_registered_cell_rule() -> None:
    import base64
    import struct
    import zlib

    def png(width: int, height: int) -> str:
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        chunk = b"IHDR" + ihdr
        data = struct.pack(">I", len(ihdr)) + chunk + struct.pack(">I", zlib.crc32(chunk))
        return base64.b64encode(b"\x89PNG\r\n\x1a\n" + data).decode()

    assert audit.image_size(png(850, 1100)) == (850, 1100)
    assert audit.image_tokens(png(850, 1100)) == 27 * 35 + 2
    assert audit.image_tokens("AA==") == math.ceil(1700 / 32) * math.ceil(2200 / 32) + 2


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
    rater_of = {"a": "model-rater-anthropic", "b": "model-rater-open-weight"}
    for rater, answer in (("a", "accept"), ("b", "reject")):
        calls = [_call(rater_of[rater], f"i{n}", answer if n else "accept") for n in range(3)]
        # Rater a's items came from two packet shards (one lane job each).
        if rater == "a":
            audit.write_jsonl(tmp_path / "a" / "shard0" / "calls.jsonl", calls[:2])
            audit.write_jsonl(tmp_path / "a" / "shard1" / "calls.jsonl", calls[2:])
        else:
            audit.write_jsonl(tmp_path / rater / "calls.jsonl", calls)
    audit.write_jsonl(tmp_path / "adj.jsonl", [{"item_id": "i1", "answer": "accept"}])
    base = [
        "summarize",
        "--sample",
        str(tmp_path / "sample.jsonl"),
        "--adjudications",
        str(tmp_path / "adj.jsonl"),
        "--n-boot",
        "50",
    ]
    code = audit.main(
        [
            *base,
            "--anthropic-calls",
            str(tmp_path / "a" / "shard0" / "calls.jsonl"),
            str(tmp_path / "a" / "shard1" / "calls.jsonl"),
            "--open-calls",
            str(tmp_path / "b" / "calls.jsonl"),
            "--out",
            str(tmp_path / "out"),
        ]
    )
    assert code == 0
    summary = json.loads((tmp_path / "out" / "audit-summary.json").read_text())
    decisions = {
        r["key"]: r["decision"] for r in audit.read_jsonl(tmp_path / "out" / "decisions.jsonl")
    }
    # m0 agreed; m1 adjudicated; m2 unresolved; m3 never rated by either rater.
    # m2 was rated in rater a's second shard: merged, not "unrated".
    assert decisions == {"m0": "accept", "m1": "accept", "m2": "unresolved", "m3": "unresolved"}
    assert summary["n_adjudicated"] == 1 and summary["human_spot_check"] == "pending"
    assert summary["answer_status"]["model-rater-open-weight"]["unrated"] == 1
    assert summary["answer_status"]["model-rater-anthropic"] == {"ok": 3, "unrated": 1}
    shards = summary["calls_files"]["model-rater-anthropic"]
    assert [s["records"] for s in shards] == [2, 1]
    # The same item in two shards breaks "one call per rater per item".
    audit.write_jsonl(
        tmp_path / "a" / "dup" / "calls.jsonl", [_call("model-rater-anthropic", "i0", "reject")]
    )
    with pytest.raises(SystemExit, match="one call per rater per item"):
        audit.main(
            [
                *base,
                "--anthropic-calls",
                str(tmp_path / "a" / "shard0" / "calls.jsonl"),
                str(tmp_path / "a" / "dup" / "calls.jsonl"),
                "--open-calls",
                str(tmp_path / "b" / "calls.jsonl"),
                "--out",
                str(tmp_path / "out2"),
            ]
        )
    # A calls file of another audit (an item outside the sample) is refused.
    audit.write_jsonl(
        tmp_path / "other" / "calls.jsonl", [_call("model-rater-anthropic", "zz", "accept")]
    )
    with pytest.raises(SystemExit, match="outside the sample"):
        audit.main(
            [
                *base,
                "--anthropic-calls",
                str(tmp_path / "other" / "calls.jsonl"),
                "--open-calls",
                str(tmp_path / "b" / "calls.jsonl"),
                "--out",
                str(tmp_path / "out3"),
            ]
        )
    # A record of the other rater in a rater's file is refused.
    audit.write_jsonl(
        tmp_path / "wrong" / "calls.jsonl", [_call("model-rater-open-weight", "i0", "accept")]
    )
    with pytest.raises(SystemExit, match="not model-rater-anthropic"):
        rater_runner.merge_calls([tmp_path / "wrong" / "calls.jsonl"], "model-rater-anthropic")
    # Inside one file: a second record for an item is refused, not resolved by
    # keeping the last one, and a record without a rater_id is not a call.
    audit.write_jsonl(
        tmp_path / "twice" / "calls.jsonl",
        [
            _call("model-rater-anthropic", "i0", "accept"),
            _call("model-rater-anthropic", "i0", "reject"),
        ],
    )
    with pytest.raises(SystemExit, match="a second record for item i0"):
        rater_runner.merge_calls([tmp_path / "twice" / "calls.jsonl"], "model-rater-anthropic")
    anonymous = _call("model-rater-anthropic", "i0", "accept")
    del anonymous["rater_id"]
    audit.write_jsonl(tmp_path / "anon" / "calls.jsonl", [anonymous])
    for rater_id in ("model-rater-anthropic", None):
        with pytest.raises(SystemExit, match="not a call record"):
            rater_runner.merge_calls([tmp_path / "anon" / "calls.jsonl"], rater_id)


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
    base += ["--audit-id", "dev-smoke", "--gpu-ledger", str(tmp_path / "ledger.jsonl")]
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
                "36",
                "--max-gpu-hours",
                "0.6",
                "--kind",
                "smoke",
                "--out",
                str(tmp_path / "m2.yaml"),
                "--name",
                "q2m-rater-smoke-2",
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
                str(tmp_path / "m3.yaml"),
                "--name",
                "q2m-rater-audit-3",
            ]
        )
    with pytest.raises(SystemExit, match="exists"):
        render_rater_manifest.main(
            [*base, "--minutes", "6", "--max-gpu-hours", "0.1", "--kind", "smoke"]
            + ["--out", str(out)]
        )


def test_controls_inputs_map_each_run_to_its_own_save_stage(tmp_path: Path) -> None:
    for name in ("confirm", "reserve"):
        run = tmp_path / name
        audit.write_jsonl(
            run / "saved" / "jobs-saved.jsonl",
            [
                {
                    "kind": "gold",
                    "task_id": f"t-{name}",
                    "mutant_id": f"t-{name}__gold__lo",
                    "files": {"/home/user/a.docx": f"/out/files/t-{name}__gold/home/user/a.docx"},
                }
            ],
        )
    tasks, saved = audit.controls_inputs([str(tmp_path / "confirm"), str(tmp_path / "reserve")])
    assert tasks == {}
    paths = sorted(job["files"]["/home/user/a.docx"] for job in saved)
    assert paths == [
        f"{tmp_path}/confirm/lo/files/t-confirm__gold/home/user/a.docx",
        f"{tmp_path}/reserve/lo/files/t-reserve__gold/home/user/a.docx",
    ]
    assert audit.controls_inputs([]) == (None, [])


def test_malformed_200_bodies_are_saved_hashed_and_unsure(tmp_path: Path) -> None:
    """A proxy error page with HTTP 200 is a recorded call, never a crash or a resend."""
    page = b"<html><body>502 Bad Gateway</body></html>"
    sent: list[str] = []

    def send(item_id: str, payload: bytes) -> rater_runner.Attempt:
        sent.append(item_id)
        bodies = {
            "i0": page,
            "i1": b"[1, 2]",
            "i2": json.dumps({"choices": [{"message": {"content": ["x"]}}]}).encode(),
            "i3": b"\xff\xfe",
        }
        return rater_runner.Attempt(
            status=200, request_bytes=payload, response_bytes=bodies[item_id]
        )

    runner = rater_runner.Runner(
        "model-rater-open-weight", tmp_path, send, rater_runner.openai_reply, workers=2
    )
    result = runner.run([_packet(f"i{n}") for n in range(4)])
    assert result["outcomes"] == {"malformed_response": 4} and not result["stopped"]
    calls = rater_runner.read_calls(tmp_path / "calls.jsonl")
    assert calls["i0"]["answer"] == "unsure" and calls["i0"]["status"] == "malformed_response"
    assert calls["i0"]["response_sha256"] == rater_runner.sha256_bytes(page)
    assert (tmp_path / "responses" / "i0.json").read_bytes() == page
    runner.run([_packet(f"i{n}") for n in range(4)])
    assert sorted(sent) == ["i0", "i1", "i2", "i3"]  # resumed: nothing is sent again
    for parse in (rater_runner.anthropic_reply, rater_runner.openai_reply):
        reply = parse(rater_runner.Attempt(status=200, response_bytes=page))
        assert reply.outcome == "malformed_response"

    def boom(attempt: rater_runner.Attempt) -> rater_runner.Reply:
        raise KeyError("content")

    other = rater_runner.Runner("model-rater-anthropic", tmp_path / "b", send, boom, workers=1)
    assert other.run([_packet("i0")])["outcomes"] == {"malformed_response": 1}


def test_anthropic_receipt_is_written_when_the_run_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packets = tmp_path / "packets.jsonl"
    packets.write_text(json.dumps(_packet("i0")) + "\n", encoding="utf-8")
    monkeypatch.setattr(rater_runner, "_anthropic_client", lambda: object())
    monkeypatch.setattr(
        rater_runner,
        "anthropic_model_record",
        lambda client: {"requested": "claude-opus-5-5", "id": "claude-opus-5-5"},
    )
    monkeypatch.setattr(rater_runner, "anthropic_sender", lambda client: None)

    def crash(self: rater_runner.Runner, packets: Any) -> dict:
        raise RuntimeError("disk full")

    monkeypatch.setattr(rater_runner.Runner, "run", crash)
    monkeypatch.setattr(rater_runner, "_install_stop", lambda runner: None)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="disk full"):
        rater_runner.main(
            [
                "anthropic",
                "--packets",
                str(packets),
                "--expected-packets-sha256",
                rater_runner.sha256_file(packets),
                "--out",
                str(out),
            ]
        )
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["run_error"] == "RuntimeError: disk full" and receipt["result"] == {}


def test_agent_harness_export_and_ingest(tmp_path: Path) -> None:
    """D25: blind files per item and an index of ids; answers are hashed into the receipt."""
    packets_path = tmp_path / "packets-000.jsonl"
    items = [_packet(f"i{n}", pages=2) for n in range(4)]
    packets_path.write_text("".join(json.dumps(p) + "\n" for p in items), encoding="utf-8")
    export = tmp_path / "export"
    manifest_path = tmp_path / "export-manifest.json"
    assert (
        rater_runner.main(
            [
                "export-harness",
                "--packets",
                str(packets_path),
                "--out",
                str(export),
                "--manifest-out",
                str(manifest_path),
            ]
        )
        == 0
    )
    names = sorted(p.name for p in export.iterdir())
    assert names == [
        "i0.pages",
        "i0.txt",
        "i1.pages",
        "i1.txt",
        "i2.pages",
        "i2.txt",
        "i3.pages",
        "i3.txt",
        "index.json",
    ]
    index = json.loads((export / "index.json").read_text())
    assert sorted(index) == ["i0", "i1", "i2", "i3"] and all(isinstance(i, str) for i in index)
    assert index == raters.rater_order(["i0", "i1", "i2", "i3"], "model-rater-anthropic")
    text = (export / "i0.txt").read_text()
    assert raters.RATER_PROMPT_V1 in text and "Bold the title." in text
    assert text.rstrip().endswith(rater_runner.ANSWER_LINE)
    assert "(image file: i0.pages/p01.png)" in text and (export / "i0.pages" / "p03.png").is_file()
    # The exported file carries the packet content only: no label, verdict or
    # operator, the same parts the API raters see.
    assert raters._leaked_keys(json.loads(manifest_path.read_text())) == []
    for word in ("should_", "verdict", "operator", "witness"):
        assert word not in text
    with pytest.raises(SystemExit, match="not empty"):
        rater_runner.export_harness(items, export)

    answers = [
        {"item_id": "i0", "answer": "Accept", "reason": "B2 bold.", "model_id": "claude-opus-5-5"},
        {"item_id": "i1", "answer": "reject", "reason": "No.", "model_id": "claude-opus-5-5"},
        {"item_id": "i2", "answer": "I think so", "reason": "", "model_id": "claude-opus-5-5"},
    ]
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    out = tmp_path / "rater"
    base = ["--packets", str(packets_path), "--export-manifest", str(manifest_path)]
    assert (
        rater_runner.main(
            ["ingest-harness", *base, "--answers", str(answers_path), "--out", str(out)]
        )
        == 0
    )
    calls = rater_runner.read_calls(out / "calls.jsonl")
    assert calls["i0"]["answer"] == "accept" and calls["i1"]["answer"] == "reject"
    assert calls["i2"]["answer"] == "unsure" and calls["i2"]["status"] == "unparseable"
    manifest = json.loads(manifest_path.read_text())
    assert calls["i0"]["request_sha256"] == manifest["items"]["i0"]["file_sha256"]
    assert calls["i0"]["request_sha256"] == rater_runner.sha256_file(export / "i0.txt")
    assert calls["i0"]["body_sha256"] == rater_runner.sha256_bytes(
        rater_runner.canonical_bytes(rater_runner.harness_body(items[0]))
    )
    assert calls["i0"]["response_sha256"] == rater_runner.sha256_bytes(
        rater_runner.canonical_bytes(answers[0])
    )
    assert "B2 bold" not in (out / "calls.jsonl").read_text()  # reasons stay private
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["path"] == rater_runner.HARNESS_PATH
    assert receipt["answers_sha256"] == rater_runner.sha256_file(answers_path)
    assert receipt["export_manifest_sha256"] == rater_runner.sha256_file(manifest_path)
    assert receipt["calls_sha256"] == rater_runner.sha256_file(out / "calls.jsonl")
    assert receipt["result"]["unrated"] == ["i3"] and "not fixed" in receipt["sampling"]
    got = rater_runner.answers(out / "calls.jsonl", ["i0", "i3"])
    assert got == {"i0": ("accept", "ok"), "i3": ("unsure", "unrated")}
    with pytest.raises(SystemExit, match="one ingest per export"):
        rater_runner.ingest_harness(items, manifest, answers_path.read_bytes(), out)

    def refused(records: list[dict], match: str) -> None:
        with pytest.raises(SystemExit, match=match):
            rater_runner.ingest_harness(
                items, manifest, json.dumps(records).encode(), tmp_path / "x" / match[:5]
            )

    ok = {"item_id": "i0", "answer": "accept", "reason": "", "model_id": "claude-opus-5-5"}
    refused([ok, ok], "second record")
    refused([dict(ok, item_id="zz")], "was not exported")
    refused([dict(ok, model_id="claude-sonnet-5")], "not 'claude-opus-5-5'")
    refused([dict(ok, label="should_pass_equiv")], "keys must be")
    tampered = json.loads(json.dumps(manifest))
    tampered["items"]["i1"]["body_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="differs from the exported file"):
        rater_runner.ingest_harness(items, tampered, b"[]", tmp_path / "y")


def test_rater_manifest_cap_reads_earlier_shards_from_the_ledger(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "infra" / "q2-mutation" / "run"))
    import render_rater_manifest

    packets = tmp_path / "packets-001.jsonl"
    packets.write_text(json.dumps(_packet("i0")) + "\n", encoding="utf-8")
    ledger = tmp_path / "gpu-ledger.jsonl"

    def render(
        name: str, minutes: int, hours: float, audit_id: str = "confirm-audit", out: str = ""
    ) -> int:
        return render_rater_manifest.main(
            [
                "--name",
                name,
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
                "/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/raters/audit",
                "--kind",
                "audit",
                "--audit-id",
                audit_id,
                "--gpu-ledger",
                str(ledger),
                "--minutes",
                str(minutes),
                "--max-gpu-hours",
                str(hours),
                "--out",
                str(tmp_path / f"{out or name}.yaml"),
            ]
        )

    assert render("shard-0", 36, 0.6) == 0
    rows = render_rater_manifest.read_ledger(ledger)
    assert [(r["name"], r["max_gpu_hours"], r["prior_gpu_hours"]) for r in rows] == [
        ("shard-0", 0.6, 0.0)
    ]
    # The rerun's cap is checked against what the ledger already holds.
    with pytest.raises(SystemExit, match=r"ledger \(0.6000 GPU-h\).*exceed the audit cap"):
        render("rerun-1", 30, 0.5)
    assert render("rerun-1", 24, 0.4) == 0
    with pytest.raises(SystemExit, match="exceed the audit cap"):
        render("rerun-2", 1, 0.02)
    # Another audit has its own total; a name is rendered once.
    assert render("other-0", 24, 0.4, audit_id="other-audit") == 0
    with pytest.raises(SystemExit, match="already has a job named"):
        render("other-0", 1, 0.02, audit_id="other-audit", out="other-0-again")
    assert len(render_rater_manifest.read_ledger(ledger)) == 3


def test_ingest_harness_accepts_the_rater_workflow_wrapper(tmp_path: Path) -> None:
    items = [_packet(f"i{n}") for n in range(2)]
    manifest = rater_runner.export_harness(items, tmp_path / "export")
    wrapper = {
        "rater": "claude-agent-harness-blind-rater",
        "model_id": "claude-opus-5-5",
        "items": [
            {"item_id": "i0", "answer": "accept", "reason": "ok"},
            {"item_id": "i1", "answer": "reject", "reason": "no"},
        ],
    }
    result = rater_runner.ingest_harness(
        items, manifest, json.dumps(wrapper).encode(), tmp_path / "out"
    )
    assert result["rated"] == 2 and result["models_returned"] == {"claude-opus-5-5": 2}
    for bad, match in (
        ({**wrapper, "model_id": "claude-sonnet-5"}, "not 'claude-opus-5-5'"),
        (
            {**wrapper, "items": [{**wrapper["items"][0], "model_id": "claude-sonnet-5"}]},
            "differs from the wrapper",
        ),
        ({**wrapper, "extra": 1}, "wrapper"),
        ({"items": []}, "wrapper"),
    ):
        with pytest.raises(SystemExit, match=match):
            rater_runner.ingest_harness(
                items, manifest, json.dumps(bad).encode(), tmp_path / "bad" / match[:6]
            )


def _transcript(*entries: dict) -> bytes:
    return "".join(json.dumps(e) + "\n" for e in entries).encode()


def _turn(*blocks: dict, model: str = "claude-opus-5-5") -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "model": model, "content": list(blocks)},
    }


def _use(name: str, **params: Any) -> dict:
    return {"type": "tool_use", "id": "t", "name": name, "input": params}


def test_isolated_export_holds_one_item_per_directory(tmp_path: Path) -> None:
    items = [_packet(f"i{n}", pages=2) for n in range(3)]
    root = tmp_path / "iso"
    packets = tmp_path / "packets-000.jsonl"
    packets.write_text("".join(json.dumps(p) + "\n" for p in items), encoding="utf-8")
    with pytest.raises(SystemExit, match="outside the isolation root"):
        rater_runner.main(
            [
                "export-isolated",
                "--packets",
                str(packets),
                "--iso-root",
                str(root),
                "--manifest-out",
                str(root / "manifest.json"),
            ]
        )
    manifest_path = tmp_path / "iso-manifest.json"
    args = ["--packets", str(packets), "--iso-root", str(root)]
    assert rater_runner.main(["export-isolated", *args, "--manifest-out", str(manifest_path)]) == 0
    manifest = json.loads(manifest_path.read_text())
    # The root holds the item directories and nothing else: no index, no manifest.
    assert sorted(p.name for p in root.iterdir()) == ["i0", "i1", "i2"]
    for item in ("i0", "i1", "i2"):
        folder = root / item
        files = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
        assert files == ["packet.txt", "pages/p01.png", "pages/p02.png", "pages/p03.png"]
        text = (folder / "packet.txt").read_text()
        assert rater_runner.ISOLATED_NOTE in text and "(image file: pages/p01.png)" in text
        for other in {"i0", "i1", "i2"} - {item}:
            assert f"ITEM {other}" not in text
        entry = manifest["items"][item]
        assert entry["files"] == rater_runner.hash_tree(folder)
        assert entry["tree_sha256"] == rater_runner.tree_digest(entry["files"])
        assert not os.access(folder / "packet.txt", os.W_OK)  # read-only
    assert manifest["order"] == raters.rater_order(["i0", "i1", "i2"], "model-rater-anthropic")
    assert raters._leaked_keys(manifest) == []
    with pytest.raises(SystemExit, match="not empty"):
        rater_runner.export_isolated(items, root)


def _prompt_entry(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _wrapped(text: str) -> str:
    """The task text as the workflow harness hands it to the agent."""
    return rater_runner.WORKFLOW_PREAMBLE + "\n".join(
        rater_runner.WORKFLOW_INDENT + line for line in text.split("\n")
    )


def test_transcript_audit_voids_shell_outside_paths_and_other_tools(tmp_path: Path) -> None:
    folder = tmp_path / "iso" / "i0"
    (folder / "pages").mkdir(parents=True)
    (folder / "packet.txt").write_text("x")
    inside = str(folder / "packet.txt")
    page = str(folder / "pages" / "p01.png")

    def audit(*blocks: dict) -> dict:
        return rater_runner.audit_transcript(
            _transcript(
                {"type": "user", "message": {"role": "user", "content": "rate it"}},
                _turn(*blocks),
                _turn(
                    {"type": "text", "text": "accept"}, _use("StructuredOutput", answer="accept")
                ),
            ),
            folder,
        )

    clean = audit(_use("Read", file_path=inside), _use("Read", file_path=page))
    assert clean["void_reasons"] == [] and clean["models"] == {"claude-opus-5-5": 2}
    assert clean["tool_calls"] == {"Read": 2, "StructuredOutput": 1}
    assert clean["packet_read"] is True
    for blocks, reason in (
        ((_use("Bash", command="ls"),), "shell call"),
        ((_use("Read", file_path=str(tmp_path / "iso" / "i1" / "packet.txt")),), "not inside"),
        ((_use("Read", file_path=str(folder / ".." / "i1" / "packet.txt")),), "not inside"),
        ((_use("Read", file_path="packet.txt"),), "not inside"),  # relative: cwd unknown
        # The registered prompt forbids Glob and Grep, inside the directory too (D34).
        ((_use("Glob", path=str(folder), pattern="pages/*.png"),), "not a read-only tool"),
        ((_use("Grep", path=str(folder), pattern="accept"),), "not a read-only tool"),
        ((_use("Write", file_path=inside, content="x"),), "not a read-only tool"),
        ((_use("WebFetch", url="https://example.org"),), "not a read-only tool"),
        ((_use("Task", prompt="rate"),), "not a read-only tool"),
    ):
        reasons = audit(*blocks)["void_reasons"]
        assert reasons and reason in reasons[0], (blocks, reasons)
    nameless = rater_runner.audit_transcript(_transcript({"type": "user"}), folder)
    assert "the transcript names no model" in nameless["void_reasons"]


def test_the_registered_prompt_template_is_committed_and_rendered_per_item() -> None:
    data = rater_runner.ISOLATED_PROMPT_TEMPLATE.read_bytes()
    assert rater_runner.sha256_bytes(data) == rater_runner.ISOLATED_PROMPT_TEMPLATE_SHA256
    text = data.decode()
    for needed in (
        "overrides any CLAUDE.md, AGENTS.md or memory instruction",
        "voids your rating",
        "only with the Read tool",
        "Do not use Bash, Grep, Glob or any other tool, and do not search",
        "{ITEM_DIR}/packet.txt",
        "{ITEM_DIR}/pages/",
        "every page image",
        "Follow the rater instructions in the packet",
        "accept, reject or unsure with a one-sentence reason",
        "structured output, with item_id {ITEM_ID}",
    ):
        assert needed in text, needed
    rendered = rater_runner.render_isolated_prompt("/r/iso/ab12", "ab12")
    assert "{" not in rendered and "/r/iso/ab12/packet.txt" in rendered
    assert rendered.endswith("with item_id ab12.\n")
    with pytest.raises(ValueError, match="absolute"):
        rater_runner.render_isolated_prompt("/r/iso/ab12/", "ab12")
    # The workflow harness's wrapper is accepted; any other text is not.
    assert rater_runner.prompt_matches(rendered, rendered)
    assert rater_runner.prompt_matches(_wrapped(rendered), rendered)
    assert rater_runner.prompt_matches("\n" + rendered + "\n\n", rendered)
    other = rater_runner.render_isolated_prompt("/r/iso/cd34", "cd34")
    assert not rater_runner.prompt_matches(_wrapped(other), rendered)
    assert not rater_runner.prompt_matches(_wrapped(rendered + "\nThe label is accept."), rendered)
    assert not rater_runner.prompt_matches(rater_runner.WORKFLOW_PREAMBLE + rendered, rendered)


def test_transcript_audit_ties_each_transcript_to_its_item(tmp_path: Path) -> None:
    """Review 4: a transcript holding only a StructuredOutput call passed the audit."""
    folder = tmp_path / "iso" / "ab12"
    (folder / "pages").mkdir(parents=True)
    (folder / "packet.txt").write_text("x")
    prompt = rater_runner.render_isolated_prompt(str(folder), "ab12")
    read = _use("Read", file_path=str(folder / "packet.txt"))

    def audit(*entries: dict) -> list[str]:
        return rater_runner.audit_transcript(
            _transcript(*entries), folder, item_id="ab12", expected_prompt=prompt
        )["void_reasons"]

    answer = _use("StructuredOutput", item_id="ab12", answer="reject", reason="r")
    assert audit(_prompt_entry(_wrapped(prompt)), _turn(read), _turn(answer)) == []
    # Only an answer: no prompt, no packet read.
    reasons = audit(_turn(answer))
    assert any("not the registered template" in r for r in reasons)
    assert any("never read packet.txt" in r for r in reasons)
    # Another item's prompt, or an answer for another item.
    other = rater_runner.render_isolated_prompt(str(tmp_path / "iso" / "cd34"), "cd34")
    assert any(
        "not the registered template" in r
        for r in audit(_prompt_entry(other), _turn(read), _turn(answer))
    )
    wrong = _use("StructuredOutput", item_id="cd34", answer="reject")
    assert any(
        "names item(s) ['cd34']" in r
        for r in audit(_prompt_entry(prompt), _turn(read), _turn(wrong))
    )
    # Reading a page but never the packet.
    page = _use("Read", file_path=str(folder / "pages" / "p01.png"))
    assert audit(_prompt_entry(prompt), _turn(page), _turn(answer)) == [
        "the agent never read packet.txt"
    ]
    # A tool result is not a prompt; a later harness message does not replace the first.
    later = {"type": "user", "message": {"role": "user", "content": "please answer now"}}
    result = {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]},
    }
    assert audit(_prompt_entry(prompt), _turn(read), result, later, _turn(answer)) == []


@pytest.mark.parametrize(
    ("final_text", "record", "source"),
    [
        ("reject", "reject", "final_text"),
        ("Answer: Reject. The title is gone.", "reject", "final_text"),
        ("I cannot accept this; reject.", "accept", "not_found"),
        ("I cannot accept this; reject.", "reject", "not_found"),
        ("unacceptable result", "accept", "not_found"),
        ("accepted", "accept", "not_found"),
        ("unsure", "unsure", "final_text"),
        ("", "accept", "not_found"),
    ],
)
def test_final_text_fallback_needs_one_exact_answer_word(
    final_text: str, record: str, source: str
) -> None:
    audit_result = {"structured_answers": [], "final_text": final_text}
    assert rater_runner._answer_source(record, audit_result) == source


def test_isolated_ingest_takes_the_model_from_the_transcript_and_voids_breaches(
    tmp_path: Path,
) -> None:
    items = [_packet(f"i{n}") for n in range(5)]
    root = tmp_path / "iso"
    manifest = rater_runner.export_isolated(items, root)
    assert manifest["prompt_template_sha256"] == rater_runner.ISOLATED_PROMPT_TEMPLATE_SHA256
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()

    def write(item: str, *blocks: dict, model: str = "claude-opus-5-5", prompt: str = "") -> None:
        text = prompt or rater_runner.render_isolated_prompt(str(root / item), item)
        read = _use("Read", file_path=str(root / item / "packet.txt"))
        (transcripts / f"{item}.jsonl").write_bytes(
            _transcript(_prompt_entry(_wrapped(text)), _turn(read, *blocks, model=model))
        )

    write("i0", _use("StructuredOutput", item_id="i0", answer="accept", reason="fine"))
    write(
        "i1",
        _use("Bash", command="cat ../i0/packet.txt"),
        _use("StructuredOutput", item_id="i1", answer="reject"),
    )
    write("i2", _use("StructuredOutput", item_id="i2", answer="reject"))  # the record says accept
    # i3 answers without a transcript; i4 is not answered at all.
    answers = tmp_path / "answers"
    answers.mkdir()
    for item, answer in (("i0", "accept"), ("i1", "reject"), ("i2", "accept"), ("i3", "accept")):
        record = {"item_id": item, "answer": answer, "reason": "r"}
        (answers / f"{item}.json").write_text(json.dumps(record), encoding="utf-8")
    manifest_path = tmp_path / "iso-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    packets = tmp_path / "packets-000.jsonl"
    packets.write_text("".join(json.dumps(p) + "\n" for p in items), encoding="utf-8")
    out = tmp_path / "rater"
    argv = [
        "ingest-isolated",
        "--packets",
        str(packets),
        "--manifest",
        str(manifest_path),
        "--iso-root",
        str(root),
        "--answers",
        str(answers),
        "--transcripts",
        str(transcripts),
        "--out",
        str(out),
    ]
    assert rater_runner.main(argv) == 0
    calls = rater_runner.read_calls(out / "calls.jsonl")
    assert calls["i0"]["answer"] == "accept" and calls["i0"]["outcome"] == "ok"
    assert calls["i0"]["model_returned"] == "claude-opus-5-5"
    assert calls["i0"]["extra"]["transcript_sha256"] == rater_runner.sha256_file(
        transcripts / "i0.jsonl"
    )
    assert calls["i0"]["extra"]["answer_source"] == "structured_output"
    assert calls["i0"]["extra"]["prompt_matches_template"] is True
    assert calls["i0"]["extra"]["packet_read"] is True
    assert calls["i0"]["extra"]["prompt_sha256"] == manifest["items"]["i0"]["prompt_sha256"]
    for item in ("i1", "i2", "i3"):
        assert (calls[item]["answer"], calls[item]["status"]) == ("unsure", "isolation_void")
    assert "shell call Bash" in calls["i1"]["extra"]["void_reasons"]
    assert calls["i2"]["extra"]["void_reasons"] == [
        "the answer is not the one the transcript returned"
    ]
    assert calls["i3"]["extra"]["void_reasons"] == ["no harness transcript for this item"]
    assert "i4" not in calls
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["result"]["unrated"] == ["i4"] and receipt["result"]["void"] == 3
    assert set(receipt["answers_files_sha256"]) == {"i0.json", "i1.json", "i2.json", "i3.json"}
    assert receipt["isolation"]["prompt_template_sha256"] == (
        rater_runner.ISOLATED_PROMPT_TEMPLATE_SHA256
    )
    assert "r" not in {c["extra"].get("reason") for c in calls.values()}
    summary = rater_runner.merged_answers([out / "calls.jsonl"], [f"i{n}" for n in range(5)])
    assert summary["i1"] == ("unsure", "isolation_void") and summary["i4"] == ("unsure", "unrated")

    # Another model in a transcript refuses the whole ingest; so does a second answer.
    records = [{"item_id": "i0", "answer": "accept"}]
    write("i0", _use("StructuredOutput", item_id="i0", answer="accept"), model="claude-sonnet-5")
    with pytest.raises(SystemExit, match="names model"):
        rater_runner.ingest_isolated(items, manifest, root, records, transcripts, tmp_path / "x")
    write("i0", _use("StructuredOutput", item_id="i0", answer="accept"))
    with pytest.raises(SystemExit, match="second answer"):
        rater_runner.ingest_isolated(
            items, manifest, root, records * 2, transcripts, tmp_path / "y"
        )
    # The transcript of another item's agent, filed under i0, is void.
    other = rater_runner.render_isolated_prompt(str(root / "i1"), "i1")
    write("i0", _use("StructuredOutput", item_id="i0", answer="accept"), prompt=other)
    result = rater_runner.ingest_isolated(
        items, manifest, root, records, transcripts, tmp_path / "w"
    )
    row = rater_runner.read_calls(tmp_path / "w" / "calls.jsonl")["i0"]
    assert result["void"] == 1 and row["extra"]["prompt_matches_template"] is False
    write("i0", _use("StructuredOutput", item_id="i0", answer="accept"))
    # A changed item directory voids that item.
    (root / "i0").chmod(0o755)
    (root / "i0" / "note.txt").write_text("label: should_pass_equiv")
    result = rater_runner.ingest_isolated(
        items, manifest, root, records, transcripts, tmp_path / "z"
    )
    assert result["void"] == 1
    row = rater_runner.read_calls(tmp_path / "z" / "calls.jsonl")["i0"]
    assert "the item directory differs from its export" in row["extra"]["void_reasons"]


def test_a_stop_signal_ends_the_run_inside_its_grace(tmp_path: Path) -> None:
    import threading

    packets = [_packet(f"i{n}") for n in range(6)]
    release = threading.Event()
    sent: list[str] = []

    def send(item_id: str, payload: bytes) -> rater_runner.Attempt:
        sent.append(item_id)
        if len(sent) == 1:
            runner.signal_stop()  # the lane's USR1 arrives during the first call
            release.wait(5)  # the engine stops: the request in flight fails
            return rater_runner.Attempt(transport_error="ConnectError", request_bytes=payload)
        body = {"choices": [{"message": {"content": "x</think>\naccept"}}]}
        return rater_runner.Attempt(
            status=200, request_bytes=payload, response_bytes=json.dumps(body).encode()
        )

    runner = rater_runner.Runner(
        "model-rater-open-weight",
        tmp_path,
        send,
        rater_runner.openai_reply,
        workers=1,
        sleep=lambda s: None,
        grace_s=0.2,
    )
    timer = threading.Timer(0.5, release.set)
    timer.start()
    result = runner.run(packets)
    timer.join()
    # One request was in flight; nothing more was sent; the interrupted item has
    # no record (it stays unrated for the rerun), and no retry was made.
    assert len(sent) == 1 and result["stopped"]
    assert sorted(result["unrated"]) == [f"i{n}" for n in range(6)]
    assert (
        not (tmp_path / "calls.jsonl").exists()
        or rater_runner.read_calls(tmp_path / "calls.jsonl") == {}
    )
    # A second signal ends the grace at once.
    hurry = rater_runner.Runner(
        "model-rater-open-weight", tmp_path / "b", send, rater_runner.openai_reply, workers=1
    )
    hurry.signal_stop()
    hurry.signal_stop()
    assert hurry.hurry.is_set()


def test_args_doctor_adds_the_image_input_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rater_runner, "args_doctor", lambda: {"problems": [], "pass": True})
    monkeypatch.setattr(
        rater_runner,
        "image_input_doctor",
        lambda d: {"pass": False, "problems": ["one page gave image placeholders []"]},
    )
    out = tmp_path / "doctor.json"
    code = rater_runner.main(["args-doctor", "--out", str(out), "--model-dir", str(tmp_path)])
    report = json.loads(out.read_text())
    assert code == 1 and report["pass"] is False
    assert report["problems"] == ["image input: one page gave image placeholders []"]
    assert rater_runner.main(["args-doctor", "--out", str(out)]) == 0
