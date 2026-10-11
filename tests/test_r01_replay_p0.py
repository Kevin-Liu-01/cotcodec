"""R01 v2: the request-replay driver and the P0 self-test against the fake engine (CPU)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

from harness.r01 import caps, fake_engine, p0, replay, requests


def frame(shade: int) -> bytes:
    image = Image.new("RGB", (320, 180), (shade, 0, 0))  # small: the drivers do not read pixels
    ImageDraw.Draw(image).rectangle([0, 0, 319, 15], fill=(20, 20, 20))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def corpus(n: int = 6, step2: bool = False) -> list[dict]:
    items = []
    for i in range(n):
        frames = [frame(i + 1)] + ([frame(100 + i)] if step2 else [])
        replies = ["Action: wait."] if step2 else []
        built = requests.rebuild(f"Task {i}.", frames, replies)
        items.append(
            {
                "id": f"t{i:03d}-p1-R",
                "cell": "R",
                "task": f"t{i:03d}",
                "pair": 1,
                "step": built["step"],
                "body": built["body"],
                "body_sha256": built["body_sha256"],
            }
        )
    return items


def test_batch1_is_seeded_resets_the_encoder_and_resumes(tmp_path: Path):
    items = corpus(6)
    out = tmp_path / "r.jsonl"
    with fake_engine.FakeEngine() as eng:
        first = replay.run_batch1(eng.transport, items[:3], label="B0a", seed=42, out=out)
        assert first["sent"] == 3
        resumed = replay.run_batch1(eng.transport, items, label="B0a", seed=42, out=out)
        assert resumed == {"label": "B0a", "sent": 3, "skipped": 3}
        assert [r["path"] for r in eng.resets] == ["/reset_encoder_cache"] * 6
        assert eng.max_inflight == 1
    rows = replay.read_jsonl(out)
    assert len(rows) == 6 and len({r["item"] for r in rows}) == 6
    order = [it["id"] for it in replay.seeded_order(items, 42)]
    assert order == [it["id"] for it in replay.seeded_order(list(reversed(items)), 42)]
    row = rows[0]
    assert row["ir"] and row["ir_sha256"] and row["parse_error"] is None
    assert row["margins"] and all(m > 0 for m in row["margins"])
    assert row["prompt_ids_sha256"] and row["completion_ids_sha256"]


def test_a_torn_last_line_is_ignored_and_the_item_reruns(tmp_path: Path):
    items = corpus(2)
    out = tmp_path / "r.jsonl"
    with fake_engine.FakeEngine() as eng:
        replay.run_batch1(eng.transport, items[:1], label="J1", seed=1, out=out)
        with open(out, "a") as handle:
            handle.write('{"label": "J1", "item": "t001-p1-R", "con')
        summary = replay.run_batch1(eng.transport, items, label="J1", seed=1, out=out)
    assert summary["sent"] == 1


def test_identical_requests_are_bitwise_equal_on_a_deterministic_engine_and_not_under_noise(
    tmp_path: Path,
):
    items = corpus(8)
    with fake_engine.FakeEngine() as eng:
        for label in ("a", "b"):
            replay.run_batch1(eng.transport, items, label=label, seed=7, out=tmp_path / "det.jsonl")
    rows = replay.read_jsonl(tmp_path / "det.jsonl")
    by = {(r["label"], r["item"]): r["content_sha256"] for r in rows}
    assert all(by[("a", it["id"])] == by[("b", it["id"])] for it in items)
    with fake_engine.FakeEngine(seed=3, noise_text_p=1.0) as eng:
        for label in ("a", "b"):
            replay.run_batch1(
                eng.transport, items, label=label, seed=7, out=tmp_path / "noisy.jsonl"
            )
    rows = replay.read_jsonl(tmp_path / "noisy.jsonl")
    by = {(r["label"], r["item"]): r["content_sha256"] for r in rows}
    assert sum(by[("a", it["id"])] != by[("b", it["id"])] for it in items) >= 7


def test_coldwarm_resets_both_caches_per_item(tmp_path: Path):
    items = corpus(3)
    with fake_engine.FakeEngine() as eng:
        replay.run_coldwarm(eng.transport, items, label="B5", seed=42, out=tmp_path / "cw.jsonl")
        paths = [r["path"] for r in eng.resets]
    assert paths == ["/reset_prefix_cache", "/reset_encoder_cache"] * 3
    rows = replay.read_jsonl(tmp_path / "cw.jsonl")
    assert sorted(r["role"] for r in rows) == ["cold"] * 3 + ["warm"] * 3


def test_loaded_schedule_is_seeded_and_covers_every_item_once():
    ids = [f"i{k:03d}" for k in range(45)]
    a = replay.loaded_schedule(ids, seed=43, streams=20, think_mean_s=9.0)
    b = replay.loaded_schedule(list(reversed(ids)), seed=43, streams=20, think_mean_s=9.0)
    assert a == b
    assert sorted(x for lane in a["lanes"] for x in lane) == sorted(ids)
    assert max(len(lane) for lane in a["lanes"]) - min(len(lane) for lane in a["lanes"]) <= 1
    assert replay.loaded_schedule(ids, seed=44, streams=20, think_mean_s=9.0) != a


def test_a_loaded_pass_is_atomic_and_a_partial_pass_reruns_whole(tmp_path: Path):
    items = corpus(10)
    calls = {"n": 0}

    def flaky(transport, body, **kw):
        calls["n"] += 1
        if calls["n"] == 4:
            raise RuntimeError("engine went away")
        return replay.post_stream(transport, body)

    with fake_engine.FakeEngine(latency_s=0.01) as eng:
        first = replay.run_loaded_pass(
            eng.transport,
            items,
            label="B1-p1",
            seed=42,
            out_dir=tmp_path,
            streams=4,
            think_mean_s=0.01,
            post=flaky,
            sample_every_s=0.005,
        )
        assert first["status"].startswith("incomplete")
        assert (tmp_path / "B1-p1.partial.jsonl").exists() and not (
            tmp_path / "B1-p1.jsonl"
        ).exists()
        second = replay.run_loaded_pass(
            eng.transport,
            items,
            label="B1-p1",
            seed=42,
            out_dir=tmp_path,
            streams=4,
            think_mean_s=0.01,
            sample_every_s=0.005,
        )
        assert second["status"] == "complete" and second["voided_previous"]
        assert len(replay.read_jsonl(tmp_path / "B1-p1.jsonl")) == 10
        assert [r["path"] for r in eng.resets[:2]] == [
            "/reset_prefix_cache",
            "/reset_encoder_cache",
        ]
        kept = replay.run_loaded_pass(
            eng.transport,
            items,
            label="B1-p1",
            seed=42,
            out_dir=tmp_path,
            streams=4,
            think_mean_s=0.01,
        )
        assert kept["status"] == "kept"
        assert eng.max_inflight >= 2
    assert list((tmp_path / "void").iterdir())


def test_loaded_pass_sleeps_no_think_after_a_lanes_last_item(tmp_path: Path):
    items = corpus(4)
    slept: list[float] = []
    with fake_engine.FakeEngine() as eng:
        replay.run_loaded_pass(
            eng.transport,
            items,
            label="p",
            seed=1,
            out_dir=tmp_path,
            streams=2,
            think_mean_s=5.0,
            sleep=slept.append,
            sample_every_s=None,
        )
    # 2 start offsets + one think per lane (2 items per lane, no think after the last)
    assert len(slept) == 4


def test_p0_self_test_decides_bitwise_fallback_and_logprobs(tmp_path: Path):
    items = corpus(5) + corpus(3, step2=True)
    for i, it in enumerate(items):
        it["id"] = f"{it['id']}-{i}"
    with fake_engine.FakeEngine(mamba_mode=None) as eng:
        test = p0.run_det(eng.transport, items, tmp_path / "det.jsonl")
        decision = p0.decide(test, {"E-det": eng.engine_log()})
    assert test["replica_comparisons"] == 16 and test["text_differences"] == 0
    assert (
        decision["det_bitwise"] and not decision["run_p0_prime"] and not decision["drop_logprobs"]
    )
    assert decision["mamba_cache_mode"]["E-det"].startswith("not logged")
    with fake_engine.FakeEngine(seed=5, noise_text_p=0.5) as eng:
        noisy = p0.run_det(eng.transport, items, tmp_path / "noisy.jsonl")
    assert p0.decide(noisy)["run_p0_prime"]
    with fake_engine.FakeEngine(logprobs_shift=True, mamba_mode="align") as eng:
        lp = p0.run_det(eng.transport, items, tmp_path / "lp.jsonl")
        d = p0.decide(lp, {"E-s1a": eng.engine_log()})
    assert d["det_bitwise"] and d["drop_logprobs"] and d["mamba_cache_mode"]["E-s1a"] == "align"
    rows = replay.read_jsonl(tmp_path / "det.jsonl")
    prices = p0.measured_prices(rows, {it["id"]: it["step"] for it in items})
    assert set(prices) == {1, 2} and prices[1]["n"] == 20


def test_timing_gate_blocks_a_job_whose_projection_exceeds_its_cap():
    job_b1 = caps.Job("J1", "E-det", "x", batch1={1: 100})
    job_ld = caps.Job("J3", "E-s1a", "y", loaded_counts={1: 40}, loaded_passes=2)
    price = {1: {"mean_s": 2.0, "p95_s": 2.5}}
    lat = {1: [2.0, 2.2, 2.5, 3.0] * 10}
    gate = p0.timing_gate([job_b1, job_ld], {"J1": 20, "J3": 4}, price, lat)
    assert gate["J1"]["submit"]  # ceil(3 + 2 + 100 x 2.55 / 60 x 1.26) = 11 <= 20
    assert gate["J1"]["projected_min"] == 11
    assert not gate["J3"]["submit"]


def test_cli_runs_a_corpus_file(tmp_path: Path, capsys):
    items = corpus(2)
    lines = []
    for it in items:
        path = tmp_path / f"{it['id']}.json"
        path.write_text(json.dumps(it["body"]))
        lines.append(
            json.dumps(
                {k: it[k] for k in ("id", "cell", "task", "pair", "step", "body_sha256")}
                | {"body_path": path.name}
            )
        )
    (tmp_path / "corpus.jsonl").write_text("\n".join(lines) + "\n")
    with fake_engine.FakeEngine() as eng:
        rc = replay.main(
            [
                "--transport",
                eng.transport,
                "--corpus",
                str(tmp_path / "corpus.jsonl"),
                "--protocol",
                "batch1",
                "--label",
                "B0a",
                "--seed",
                "42",
                "--out",
                str(tmp_path / "out.jsonl"),
                "--no-logprobs",
            ]
        )
    assert rc == 0 and json.loads(capsys.readouterr().out)["sent"] == 2
    assert all(r["margins"] is None for r in replay.read_jsonl(tmp_path / "out.jsonl"))
