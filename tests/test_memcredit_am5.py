"""Tests for AM5 (scripts/memcredit_am5.py, exploratory): the config on top of am3g's, the
evidence ablation and its leakage facts, the judge prompt, the capped rule against AM4's, the
per-pool records and blocks, the original-pool context against AM3's committed results, and
extract, the blind hand-check sample, merge and analyze end to end on toy run directories (no GPU,
no vLLM, no LongMemEval text)."""

from __future__ import annotations

import copy
import gzip
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import memcredit_am3 as am3  # noqa: E402
import memcredit_am3g as g  # noqa: E402
import memcredit_am4 as am4  # noqa: E402
import memcredit_am5 as a5  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

# --------------------------------------------------------------------------- config


def test_config_merges_am3gs_readers_and_steps_unchanged():
    config = a5.load_config()
    base = g.load_config()
    assert config["readers"] == base["readers"]
    assert config["models"] == base["models"]
    assert config["reader_sampling"] == base["reader_sampling"]
    by_id = {s["id"]: s for s in base["steps"]}
    assert [s["id"] for s in config["steps"]] == [
        "rd-qwen3-8b",
        "rd-olmo2",
        "rd-olmo2-default",
        "rd-qwen35-9b-default",
        "judge32",
    ]
    assert all(s == by_id[s["id"]] for s in config["steps"])
    assert (
        config["population"]["question_ids_sha256"]
        == (base["populations"]["development"]["question_ids_sha256"])
    )
    assert (
        config["population"]["dev_artifact_sha256"]
        == (base["populations"]["development"]["artifact_sha256"])
    )
    assert config["analysis"]["caps"] == [8, 70]


def test_the_am3_per_table_pin_is_the_committed_file():
    config = a5.load_config()
    rows = a5.load_am3_records(config)
    assert len(rows) == 3 * 63 * 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(claim_level="confirmatory"),
        lambda c: c.update(steps=["rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default", "judge8"]),
        lambda c: c.update(steps=["rd-qwen3-8b", "rd-olmo2", "judge32"]),
        lambda c: c["population"].update(arms=["retrieved", "gold"]),
        lambda c: c["job"]["step_budgets"].update(judge32=[90, 170]),
        lambda c: c["base"].update(config_sha256="0" * 64),
    ],
)
def test_config_refuses_changes(tmp_path, mutate):
    import yaml

    raw = yaml.safe_load(a5.CONFIG_PATH.read_text())
    mutate(raw)
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(a5.Am5Error):
        a5.load_config(path)


def _worst_case(config: dict, fallback: bool, residual: bool = False) -> dict:
    """Simulate the driver's step starts with every pass at its max_s and the overhead model."""

    job = config["jobs"][a5.POPULATION]
    over = config["budget"]["overhead_model"]
    deadline = job["minutes"] * 60 - 210
    t = over["job"]
    started = {}
    for step in config["steps"]:
        min_start, max_s = a5.step_budget(config, step["id"])
        if step["id"] == "rd-olmo2-default" and not fallback:
            continue
        if deadline - t < min_start:
            started[step["id"]] = False
            continue
        started[step["id"]] = True
        if step["id"] == "rd-olmo2" and fallback and not residual:
            t += over["failed_engine_step"]
            continue
        t += (over["judge32"] if step["kind"] == "judge" else over["reader"]) + max_s
    return {"started": started, "end": t, "deadline": deadline}


def test_the_judge_starts_and_fits_in_the_worst_case():
    config = a5.load_config()
    for fallback in (False, True):
        sim = _worst_case(config, fallback)
        assert sim["started"]["judge32"], sim
        assert sim["end"] <= sim["deadline"], sim
    residual = _worst_case(config, True, residual=True)
    assert not residual["started"]["judge32"]  # disclosed: a capped OLMo-2 pass plus its fallback


def test_the_caps_are_within_the_budget():
    config = a5.load_config()
    hours = (config["budget"]["build_minutes"] + config["jobs"][a5.POPULATION]["minutes"]) / 60
    assert hours <= config["budget"]["cap_gpu_hours"]


def test_the_artifact_pin_is_required_before_any_run(tmp_path):
    config = a5.load_config()
    config["population"]["artifact_sha256"] = "PENDING"
    with pytest.raises(a5.Am5Error, match="not pinned"):
        a5.require_artifact_pin(config)


def test_feature_code_is_am3gs_closure_plus_this_script():
    assert a5.FEATURE_CODE[: len(g.FEATURE_CODE)] == g.FEATURE_CODE
    assert a5.FEATURE_CODE[-1] == "scripts/memcredit_am5.py"
    assert all((ROOT / p).is_file() for p in a5.FEATURE_CODE)


def test_the_worker_is_this_script_without_a_population():
    config = a5.load_config()
    step = config["steps"][0]
    args = a5.argparse.Namespace(
        config="c.yaml", evidence="/inputs/study-artifact.json", expected_evidence_sha256="e" * 64
    )
    argv = a5.worker_argv(step, args, Path("/outputs/am5"), 123.0)
    assert argv[1] == str(Path(a5.__file__).resolve())
    assert argv[2] == "worker" and "--population" not in argv
    assert argv[argv.index("--step") + 1] == "rd-qwen3-8b"


def test_the_development_path_guard_applies():
    with pytest.raises(g.Am3gError):
        g.check_dev_path("/x/am3-nonabstain-generality-v1/inputs/abstention-artifact.json")


# --------------------------------------------------------------------------- the ablation


def _turn(text: str, role: str = "user", has_answer: bool = False) -> dict:
    t = {"role": role, "content": text}
    if has_answer:
        t["has_answer"] = True
    return t


def _toy_record(qid: str = "q1", leak: bool = False) -> dict:
    sessions, ids, dates = [], [], []
    for s in range(12):
        sid = f"s{s}" if s not in (3, 7) else f"ans{s}"
        turns = [
            _turn(f"session {s} talk about apples {s} and pears"),
            _turn(f"assistant reply {s}", role="assistant"),
        ]
        if s in (3, 7):
            turns.append(
                _turn(f"my favourite colour is blue, said in session {s}", has_answer=True)
            )
        turns.append(_turn(f"more apples {s} weather chat"))
        if leak and s == 5:
            turns.append(_turn("again: my favourite colour is blue", has_answer=True))
        sessions.append(turns)
        ids.append(sid)
        dates.append(f"2023/05/{s + 1:02d} (Mon) 10:00")
    sessions.append(sessions[3])  # a repeated evidence session id
    ids.append("ans3")
    dates.append("2023/05/30 (Tue) 10:00")
    return {
        "question_id": qid,
        "question_type": "single-session-user",
        "question": "What is my favourite colour blue apples?",
        "answer": "blue",
        "question_date": "2023/06/01 (Thu) 10:00",
        "answer_session_ids": ["ans3", "ans7"],
        "haystack_sessions": sessions,
        "haystack_session_ids": ids,
        "haystack_dates": dates,
    }


def test_ablate_removes_every_evidence_session_and_its_copies():
    record = _toy_record()
    ablated, facts = a5.ablate(record)
    assert "ans3" not in ablated["haystack_session_ids"]
    assert "ans7" not in ablated["haystack_session_ids"]
    assert len(ablated["haystack_sessions"]) == len(ablated["haystack_dates"]) == 10
    assert facts["sessions_removed"] == 3 and facts["repeated_evidence_session_ids"] == 1
    assert facts["has_answer_turns_before"] == 3
    assert facts["has_answer_turns_in_evidence_sessions"] == 3
    assert facts["has_answer_turns_after"] == 0
    assert record["haystack_session_ids"][3] == "ans3"  # the input is not modified


def test_ablate_refuses_abstention_and_missing_sessions():
    record = _toy_record("q1_abs")
    with pytest.raises(a5.Am5Error):
        a5.ablate(record)
    record = _toy_record()
    record["answer_session_ids"] = ["nowhere"]
    with pytest.raises(a5.Am5Error):
        a5.ablate(record)


def test_the_ablated_pool_is_am1s_retrieved_arm_of_the_rest_and_the_leakage_is_counted():
    pilot = g.load_pilot_config(g.load_config())
    pool_config = ms.pool_config(pilot)
    record = _toy_record(leak=True)
    ablated, facts = a5.ablate(record)
    pool = g.retrieved_pool(ablated, pool_config)
    assert (
        pool
        == mc.build_pools(
            ablated, {**pool_config, "pools": {**pool_config["pools"], "distractor_seed": 0}}
        )["retrieved"]
    )
    assert all(m["session_id"] not in ("ans3", "ans7") for m in pool)
    leak = a5.pool_facts(record, ablated, pool, pool_config)
    assert facts["has_answer_turns_after"] == 1
    assert leak["pool_has_answer_memories"] == (sum(m["is_gold"] for m in pool))
    assert leak["remaining_user_turns_containing_the_answer"] == 1
    assert leak["original_pool_has_answer_memories"] >= 1


def test_build_artifact_takes_the_split_order_and_no_text_reaches_the_summary():
    pilot = g.load_pilot_config(g.load_config())
    records = [_toy_record("q1"), _toy_record("q2", leak=True)]
    split = {"development": ["q2", "q1"]}
    artifact, facts = a5.build_artifact(records, pilot, split)
    assert [q["question_id"] for q in artifact["questions"]] == ["q2", "q1"]
    assert all(not q["abstention"] for q in artifact["questions"])
    digest = a5.sha256_bytes(mc.canonical_json(artifact))
    summary = a5.artifact_summary(artifact, digest, facts, pilot)
    assert summary["leakage"]["has_answer_turns_left_in_the_haystack"] == 1
    assert summary["leakage"]["questions_with_has_answer_turns_left"] == 1
    blob = json.dumps(summary)
    for text in ("favourite colour", "apples", "weather chat"):
        assert text not in blob


def test_judge_message_is_the_answer_check_template():
    artifact = {
        "questions": [
            {
                "question_id": "q1",
                "question_type": "multi-session",
                "question": "How many?",
                "answer": "3",
                "abstention": False,
            }
        ]
    }
    item = {"question_index": 0, "response": "Three."}
    assert a5.judge_message(artifact, item) == ms.judge_prompt(
        "multi-session", "How many?", "3", "Three."
    )
    artifact["questions"][0]["abstention"] = True
    with pytest.raises(a5.Am5Error):
        a5.judge_message(artifact, item)


# --------------------------------------------------------------------------- rule and records


def _pool(seed: int, top4_abstains: bool | None = None) -> dict:
    rng = random.Random(seed)
    ranks = list(range(8))
    rng.shuffle(ranks)
    masks = {}
    for m in g.REQUEST_MASKS:
        abstain = rng.random() < 0.8
        masks[m] = {"abstain": abstain, "u": {"primary": int(not abstain and rng.random() < 0.3),
                                              "secondary": None},
                    "finish": "stop", "pattern": "i_dont_know" if abstain else None,
                    "digest": f"d{seed}-{m}"}  # fmt: skip
    top4 = lf.bm25_top_mask(ranks)
    if top4_abstains is not None:
        masks[top4]["abstain"] = top4_abstains
        if top4_abstains:
            masks[top4]["u"]["primary"] = 0
    return {
        "question_id": f"q{seed}",
        "question_type": "multi-session",
        "arm": "retrieved",
        "bm25_rank": ranks,
        "gold_mask": 0,
        "masks": masks,
    }


def test_capped_rule_is_am4s():
    for seed in range(60):
        pool = _pool(seed)
        for cap in (1, 2, 8, 26, 70):
            assert a5.capped_rule(pool, cap) == {
                k: v for k, v in am4.capped_rule(pool, cap).items()
            }


def test_pool_record_switches_only_from_an_abstaining_top4():
    for seed in range(80):
        pool = _pool(seed)
        rec = a5.pool_record(pool, [8, 70])
        for cap in ("8", "70"):
            if rec["caps"][cap]["switched"]:
                assert rec["bm25_top4_abstains"]
                assert not rec["caps"][cap]["kept_abstains"]
                assert rec["first_answer_position"] <= int(cap)
        if rec["caps"]["8"]["switched"]:
            assert rec["caps"]["70"]["mask"] == rec["caps"]["8"]["mask"]
        assert rec["caps"]["70"]["mask"] == am3.nonabstain_bm25(pool)["mask"]


def test_ablated_block_counts():
    pools = [_pool(s, top4_abstains=s % 3 != 0) for s in range(30)]
    recs = [a5.pool_record(p, [8, 70]) for p in pools]
    block = a5.ablated_block(recs, [8, 70], {})
    n_top_answers = sum(not r["bm25_top4_abstains"] for r in recs)
    assert block["bm25_top4_answers"]["count"] == n_top_answers == 10
    for cap in ("8", "70"):
        c = block["caps"][cap]
        switched = sum(r["caps"][cap]["switched"] for r in recs)
        assert c["switch_rate"]["count"] == switched
        assert c["rule_keeps_an_abstention"]["count"] == 20 - switched
        assert c["cost_judge"]["count"] == switched - c["switched_judged_correct"]
        assert c["switched_hand"]["labelled"] == 0 and c["cost_hand"] is None
    assert block["caps"]["8"]["switch_rate"]["count"] <= block["caps"]["70"]["switch_rate"]["count"]


def test_the_original_block_reproduces_am3s_committed_development_results():
    config = a5.load_config()
    rows = a5.load_am3_records(config)
    committed = json.loads(
        (ROOT / "program/evidence/2026-10-16/am3-reader-replication/results.json").read_text()
    )
    for reader in a5.READERS:
        recs = [r for r in rows if r["reader"] == reader and r["arm"] == "retrieved"]
        block = a5.original_block(recs, [8, 70])
        cell = _find_cell(committed, reader)
        assert (block["caps"]["70"]["gained_b"], block["caps"]["70"]["lost_c"]) == cell
        assert block["caps"]["8"]["gained_b"] <= block["caps"]["70"]["gained_b"]
    assert [
        a5.original_block([r for r in rows if r["reader"] == x and r["arm"] == "retrieved"], [70])[
            "caps"
        ]["70"]["gained_b"]
        for x in a5.READERS
    ] == [1, 4, 3]


def _find_cell(results: dict, reader: str) -> tuple[int, int]:
    """b and c of the rule against BM25 top 4, retrieved arm, Qwen3-32B, in AM3's results."""

    def walk(node, path):
        if isinstance(node, dict):
            if "rule_right_base_wrong" in node and "rule_wrong_base_right" in node:
                yield path, node
            for k, v in node.items():
                yield from walk(v, path + (k,))

    for path, node in walk(results, ()):
        if (
            reader in path
            and "retrieved" in path
            and "primary" in path
            and any("bm25_top4" in p for p in path)
            and any("nonabstain" in p for p in path)
        ):
            return node["rule_right_base_wrong"], node["rule_wrong_base_right"]
    raise AssertionError(f"no cell for {reader}")


# --------------------------------------------------------------------------- toy runs end to end


def _toy_artifact(n: int = 6) -> dict:
    qs = []
    for q in range(n):
        pool = [{"session_id": f"s{i}", "session_index": i, "turn_index": 0,
                 "date": f"2023/05/{i + 1:02d} (Mon) 10:00", "is_gold": False,
                 "bm25_rank": (i * 3 + q) % 8, "bm25_score": 1.0, "chars": 10,
                 "truncated": False, "text": f"memory {i} of {q}",
                 "text_sha256": "x"} for i in range(8)]  # fmt: skip
        qs.append({"question_id": f"q{q}", "question_type": "multi-session" if q % 2
                   else "temporal-reasoning", "question": f"question {q}?",
                   "question_date": "2023/06/01", "answer": f"blue {q}", "abstention": False,
                   "pools": {"retrieved": pool}})  # fmt: skip
    return {"experiment_id": a5.EXPERIMENT, "split": a5.POPULATION, "questions": qs}


def _reply(reader: str, q: int, mask: int) -> str:
    if mask == g.FULL:
        return "I don't know."
    if mask % 7 == 0 and reader != "a":
        return f"It is blue {q}."
    if mask % 5 == 0:
        return f"It is green {q} {reader}."
    return "I don't know." if mask % 2 else "The memories do not mention it."


def _toy_run(tmp_path: Path, artifact: dict) -> Path:
    from test_memcredit_am3 import _write_pass

    config = a5.load_config()
    pilot = g.load_pilot_config(config)
    run = tmp_path / "run" / "am5"
    steps = {
        "rd-qwen3-8b": {"kind": "reader", "reader": "qwen3-8b", "status": "complete",
                        "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2": {"kind": "reader", "reader": "olmo-2-1124-7b-instruct",
                     "status": "complete", "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2-default": {"kind": "reader", "status": "not-needed"},
        "rd-qwen35-9b-default": {"kind": "reader", "reader": "qwen3.5-9b", "status": "complete",
                                 "batch_invariant": False, "enforce_eager": True},
        "judge32": {"kind": "judge", "status": "complete"},
    }  # fmt: skip
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        json.dumps({"experiment_id": a5.EXPERIMENT, "population": a5.POPULATION, "steps": steps})
    )
    passes = {}
    for sid, reader in (("rd-qwen3-8b", "a"), ("rd-olmo2", "b"), ("rd-qwen35-9b-default", "c")):
        rows = {}
        for r in g.request_table(artifact, a5.ARMS):
            text = _reply(reader, r["question_index"], r["mask"])
            rows[r["index"]] = ([100 + len(text) % 7, 151645], [-0.1, -0.01], "stop", text)
        _write_pass(run / "sessions" / sid, rows)
        passes[sid] = {i: row[3] for i, row in rows.items()}
    items = a5.judge_items(artifact, pilot, passes)
    (run / "judge-items.json").write_text(json.dumps(items))
    rows = {}
    for item in items:
        q = artifact["questions"][item["question_index"]]
        yes = q["answer"] in item["response"].lower()
        rows[item["index"]] = ([7], [-0.01], "stop", "yes" if yes else "no")
    _write_pass(run / "sessions" / "judge32", rows)
    return run


def _pipeline(tmp_path, monkeypatch):
    artifact = _toy_artifact(6)
    config = a5.load_config()
    config["population"]["questions"] = 6
    config["population"]["artifact_sha256"] = "a" * 64
    monkeypatch.setattr(a5, "load_config", lambda *a, **k: copy.deepcopy(config))
    monkeypatch.setattr(a5, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(a5, "load_am3_records", lambda c: _toy_am3_rows(artifact))
    run = _toy_run(tmp_path, artifact)
    summary = tmp_path / "summary.json"
    zero = {
        "pool_has_answer_memories": 0,
        "pool_memories_containing_the_answer": 0,
        "remaining_user_turns_containing_the_answer": 0,
    }
    facts = [
        {"facts": {"question_id": q["question_id"], "question_type": q["question_type"], **zero}}
        for q in artifact["questions"]
    ]
    summary.write_text(
        json.dumps(
            {
                "artifact_sha256": "a" * 64,
                "leakage": {"questions": 6},
                "per_question": facts,
                "dev_retrieved_pool_check": None,
            }
        )
    )
    private = tmp_path / "private"
    args = a5.argparse.Namespace(config="x", run_dir=str(run), evidence="x",
                                 summary=str(summary), private_dir=str(private))  # fmt: skip
    brief = a5.cmd_extract(args)
    features_path = private / f"features-{a5.POPULATION}.json.gz"
    assert brief["features_sha256"] == a5.sha256_file(features_path)
    return artifact, config, run, features_path


def _toy_am3_rows(artifact: dict) -> list[dict]:
    rows = []
    for reader in a5.READERS:
        for i, q in enumerate(artifact["questions"]):
            rows.append({"reader": reader, "arm": "retrieved", "question_id": q["question_id"],
                         "question_type": q["question_type"], "bm25_top4_abstains": i % 2 == 0,
                         "bm25_top4_mask": 15, "nonabstain_mask": 23 if i % 2 == 0 else 15,
                         "first_answer_position": 3 if i % 2 == 0 else 1, "all_8_abstains": False,
                         "four_subset_abstain": 10,
                         "u": {"primary": {"bm25_top4": 0 if i % 2 == 0 else 1,
                                           "nonabstain_bm25": 1}}})  # fmt: skip
    return rows


def test_extract_hand_check_and_analyze_end_to_end_and_text_free(tmp_path, monkeypatch):
    artifact, config, run, features_path = _pipeline(tmp_path, monkeypatch)
    features = g.read_gz_json(features_path)
    a5.check_features(features, config)
    hand = tmp_path / "hand"
    out = a5.cmd_hand_sample(
        a5.argparse.Namespace(
            config="x",
            run_dir=str(run),
            evidence="x",
            features=str(features_path),
            hand_dir=str(hand),
        )
    )
    manifest = json.loads((hand / "hand-manifest.json").read_text())
    lines = (hand / "hand-check-sample.jsonl").read_text().splitlines()
    assert out["items"] == len(lines) == len(manifest["items"]) > 0
    for line in lines:
        row = json.loads(line)
        assert set(row) == {
            "item_id",
            "question_id",
            "question_type",
            "check",
            "question",
            "reference",
            "reply",
        }
        assert row["check"] == "answer"
        assert lf.abstention(row["reply"])[0] is False
    # The labeller: 1 when the reference occurs in the reply.
    chunk = manifest["first"][0]
    rows = [json.loads(x) for x in lines]
    labels = [
        json.dumps({"item_id": r["item_id"], "label": int(r["reference"] in r["reply"].lower())})
        for r in rows
    ]
    (hand / chunk["output"]).write_text("\n".join(labels) + "\n")
    merged = a5.cmd_hand_merge(a5.argparse.Namespace(hand_dir=str(hand)))
    assert merged["labelled"] == merged["items"] and merged["missing"] == 0
    with pytest.raises(a5.Am5Error):
        a5.cmd_hand_merge(a5.argparse.Namespace(hand_dir=str(hand)))
    labels_sha = merged["labels_sha256"]
    outdir = tmp_path / "out"
    a5.cmd_analyze(
        a5.argparse.Namespace(
            config="x",
            features=str(features_path),
            hand_labels=str(hand / "hand-labels.jsonl"),
            hand_labels_sha256=labels_sha,
            hand_plan_sha256=manifest["plan_sha256"],
            output_dir=str(outdir),
        )
    )
    results = json.loads((outdir / "results.json").read_text())
    assert results["hand_check"]["status"] == "complete"
    for d in results["readers"].values():
        for cap in ("8", "70"):
            c = d["ablated"]["caps"][cap]
            h = c["switched_hand"]
            assert h["complete"] and h["judge_yes_hand_no"] == h["judge_no_hand_yes"] == 0
            assert h["hand_correct"] == c["switched_judged_correct"]
        assert d["original"]["caps"]["70"]["gained_b"] == 3
    # Byte-identical on a rerun.
    outdir2 = tmp_path / "out2"
    a5.cmd_analyze(
        a5.argparse.Namespace(
            config="x",
            features=str(features_path),
            hand_labels=str(hand / "hand-labels.jsonl"),
            hand_labels_sha256=labels_sha,
            hand_plan_sha256=manifest["plan_sha256"],
            output_dir=str(outdir2),
        )
    )
    for f in ("results.json", "per-table.json.gz", "tables.md"):
        assert (outdir / f).read_bytes() == (outdir2 / f).read_bytes()
    blob = (
        (outdir / "results.json").read_text()
        + (outdir / "tables.md").read_text()
        + gzip.decompress((outdir / "per-table.json.gz").read_bytes()).decode()
    )
    for text in ("blue 1", "green 2", "It is", "do not mention", "memory 3", "question 4?"):
        assert text not in blob
    with pytest.raises(a5.Am5Error):
        a5.cmd_analyze(
            a5.argparse.Namespace(
                config="x",
                features=str(features_path),
                hand_labels=str(hand / "hand-labels.jsonl"),
                hand_labels_sha256=labels_sha,
                hand_plan_sha256="0" * 64,
                output_dir=str(tmp_path / "out3"),
            )
        )


def test_the_hand_plan_covers_switched_and_answering_top4_replies(tmp_path, monkeypatch):
    _, config, _, features_path = _pipeline(tmp_path, monkeypatch)
    features = g.read_gz_json(features_path)
    plan = a5.hand_plan(features, [8, 70], 44)
    again = a5.hand_plan(copy.deepcopy(features), [8, 70], 44)
    assert plan == again
    keys = {(i["question_id"], i["reply_digest"]) for i in plan["items"]}
    assert len(keys) == len(plan["items"])
    expected = set()
    a5.int_masks(features)
    for reader in a5.READERS:
        for pool in features["readers"][reader]["pools"]:
            rec = a5.pool_record(pool, [70])
            if rec["caps"]["70"]["switched"]:
                expected.add((rec["question_id"], rec["caps"]["70"]["digest"]))
            if not rec["bm25_top4_abstains"]:
                expected.add((rec["question_id"], rec["digest"]["bm25_top4"]))
    assert keys == expected
    assert plan["labeller_prompt_sha256"] == g.hand_labeller_prompt_sha256()


def test_extract_refuses_another_experiments_run(tmp_path, monkeypatch):
    artifact, config, run, _ = _pipeline(tmp_path, monkeypatch)
    summary = json.loads((run / "summary.json").read_text())
    summary["experiment_id"] = g.EXPERIMENT
    (run / "summary.json").write_text(json.dumps(summary))
    args = a5.argparse.Namespace(config="x", run_dir=str(run), evidence="x",
                                 summary=str(tmp_path / "summary.json"),
                                 private_dir=str(tmp_path / "private2"))  # fmt: skip
    with pytest.raises(a5.Am5Error):
        a5.cmd_extract(args)


def test_private_outputs_stay_outside_the_repository(tmp_path):
    args = a5.argparse.Namespace(config=str(a5.CONFIG_PATH), run_dir=str(tmp_path),
                                 evidence="x", summary="x",
                                 private_dir=str(ROOT / "private-test"))  # fmt: skip
    with pytest.raises(g.Am3gError):
        a5.cmd_extract(args)
