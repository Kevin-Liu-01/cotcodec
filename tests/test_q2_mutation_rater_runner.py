"""The registered rater runner: one call per item, transport-only retries, receipts."""

from __future__ import annotations

import json
import math
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
    # The registered budget leaves the answer and prompt allowance in the window.
    assert audit.PACKET_TOKEN_BUDGET == 131_072 - 256 - 2_048
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
    for rater, answer in (("a", "accept"), ("b", "reject")):
        calls = [
            {"item_id": f"i{n}", "answer": answer if n else "accept", "status": "ok"}
            for n in range(3)
        ]
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
        tmp_path / "a" / "dup" / "calls.jsonl", [{"item_id": "i0", "answer": "reject"}]
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
    audit.write_jsonl(tmp_path / "other" / "calls.jsonl", [{"item_id": "zz", "answer": "accept"}])
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
        tmp_path / "wrong" / "calls.jsonl",
        [{"item_id": "i0", "answer": "accept", "rater_id": "model-rater-open-weight"}],
    )
    with pytest.raises(SystemExit, match="not model-rater-anthropic"):
        rater_runner.merge_calls([tmp_path / "wrong" / "calls.jsonl"], "model-rater-anthropic")


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


def test_rater_manifest_cap_counts_earlier_shards(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "infra" / "q2-mutation" / "run"))
    import render_rater_manifest

    packets = tmp_path / "packets-001.jsonl"
    packets.write_text(json.dumps(_packet("i0")) + "\n", encoding="utf-8")
    base = [
        "--name",
        "q2m-rater-audit-1",
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
        "--out",
        str(tmp_path / "m.yaml"),
    ]
    ok = [*base, "--minutes", "24", "--max-gpu-hours", "0.4", "--prior-gpu-hours", "0.6"]
    assert render_rater_manifest.main(ok) == 0
    over = [*base, "--minutes", "24", "--max-gpu-hours", "0.4", "--prior-gpu-hours", "0.7"]
    with pytest.raises(SystemExit, match="exceed the audit cap"):
        render_rater_manifest.main(over)
