"""Tests for AM3 (scripts/memcredit_am3.py): the config and its pins, the 71-request table, the
refusal of held-out paths, stop tokens and worker environments, judge items across readers, the
nonabstain-BM25 rule, the anchor comparisons, and extract plus analyze end to end on a toy run
directory (no GPU, no vLLM)."""

from __future__ import annotations

import copy
import gzip
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import memcredit_am3 as am3  # noqa: E402
import memcredit_cost_curve as cc  # noqa: E402
import memcredit_keepset_search as ks  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit_study as ms  # noqa: E402

# --------------------------------------------------------------------------- config


def test_config_loads_with_its_pins():
    config = am3.load_config()
    pilot = am3.load_pilot_config(config)
    assert config["claim_level"] == "exploratory"
    assert [r["id"] for r in config["readers"]] == [
        "qwen3-8b",
        "olmo-2-1124-7b-instruct",
        "qwen3.5-9b",
    ]
    anchor = next(r for r in config["readers"] if r["role"] == "anchor")
    assert anchor["engine"] == pilot["reader"]["engine"]
    assert config["reader_sampling"] == {"temperature": 0.0, "max_tokens": 64, "logprobs": 0}
    assert config["pilot"]["study_artifact_sha256"] == lf.ARTIFACT_SHA256
    assert config["pilot"]["tables_sha256"] == cc.DEV_TABLES_SHA256
    assert am3.sha256_file(ROOT / config["pilot"]["tables"]) == cc.DEV_TABLES_SHA256
    # The prompt keeps AM1's "I don't know" instruction.
    assert 'say "I don\'t know"' in pilot["prompt"]["user"]
    assert pilot["prompt"]["enable_thinking"] is False


def test_the_registry_pins_the_second_reader():
    registry = yaml.safe_load((ROOT / "models" / "registry.yaml").read_text())
    entry = registry["models"]["olmo-2-1124-7b-instruct"]
    reader = am3.reader_spec(am3.load_config(), "olmo-2-1124-7b-instruct")
    assert entry["revision"] == reader["revision"]
    assert entry["license"] == "apache-2.0" and entry["access"] == "public"
    assert entry["trust_remote_code"] is False


def _write_config(tmp_path: Path, mutate) -> Path:
    config = yaml.safe_load(am3.CONFIG_PATH.read_text())
    mutate(config)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["readers"][0]["engine"].update(max_num_seqs=128),
        lambda c: c["readers"][0].update(role="other"),
        lambda c: c.update(claim_level="confirmatory"),
        lambda c: c["reader_sampling"].update(max_tokens=128),
        lambda c: c["pilot"].update(config_sha256="0" * 64),
        lambda c: c["job"].update(gpus=2),
        lambda c: c["job"]["steps"][0].update(batch_invariant=False),
        lambda c: c["job"]["steps"][2].update(only_if_incomplete="rd-qwen3-8b"),
        lambda c: c["job"]["steps"][5].update(id="judge-x"),
    ],
)
def test_config_refuses_changes(tmp_path, mutate):
    with pytest.raises(am3.Am3Error):
        am3.load_config(_write_config(tmp_path, mutate))


# --------------------------------------------------------------------------- paths


@pytest.mark.parametrize(
    "path",
    [
        "program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz",
        "/home/x/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1",
        "/home/x/cotcodec-runs/stage0/am1-keepset-search-v1/private/features.json.gz",
    ],
)
def test_held_out_paths_are_refused(path):
    with pytest.raises(am3.Am3Error):
        am3.check_path(path)


def test_held_out_symlink_is_refused(tmp_path):
    target = tmp_path / "am1-confirmatory"
    target.mkdir()
    link = tmp_path / "innocent"
    link.symlink_to(target)
    with pytest.raises(am3.Am3Error):
        am3.check_path(link)


# --------------------------------------------------------------------------- toy data


def _memory(i: int, rank: int) -> dict:
    return {"text": f"memory {i}", "date": "2023/05/01", "bm25_rank": rank, "is_gold": i == 0}


def _toy_artifact(questions: int = 4) -> dict:
    qs = []
    for q in range(questions):
        qs.append({
            "question_id": f"q{q}",
            "question_type": "multi-session" if q % 2 else "temporal-reasoning",
            "question": f"question {q}?",
            "question_date": "2023/06/01",
            "answer": f"blue {q}",
            "pools": {
                "retrieved": [_memory(i, (i * 3 + q) % 8) for i in range(8)],
                "gold": [_memory(i, 10 * i + q) for i in range(8)],
            },
            "placebos": {
                arm: {"swaps": [[{"text": f"swap {i}"}] for i in range(8)],
                      "reorders": [list(range(8))[::-1]]}
                for arm in am3.ARMS
            },
        })  # fmt: skip
    return {"experiment_id": ms.EXPERIMENT_ID, "split": "development", "questions": qs}


def test_request_table_reads_every_4_subset_and_the_full_pool():
    artifact = _toy_artifact(3)
    table = am3.request_table(artifact)
    assert len(table) == 3 * 2 * 71
    assert [r["index"] for r in table] == list(range(len(table)))
    first_pool = [r["mask"] for r in table[:71]]
    assert first_pool == sorted(lf.FOUR_SETS) + [255]
    assert all(bin(m).count("1") == 4 for m in first_pool[:70])
    for q in artifact["questions"]:
        for arm in am3.ARMS:
            ranks = [m["bm25_rank"] for m in q["pools"][arm]]
            assert lf.bm25_top_mask(ranks) in first_pool
    assert {r["arm"] for r in table[:71]} == {"retrieved"}
    assert {r["arm"] for r in table[71:142]} == {"gold"}


def test_reader_messages_are_the_pilots_messages():
    config = am3.load_config()
    pilot = am3.load_pilot_config(config)
    artifact = _toy_artifact(1)
    messages = am3.reader_messages(pilot, artifact)
    assert len(messages) == 142
    full = am3.request_table(artifact)[70]
    assert full["mask"] == 255
    assert messages[70] == ms.request_message(artifact, full, pilot["prompt"])
    assert "memory 7" in messages[70] and "memory 7" not in messages[0]


class _Tok:
    unk_token_id = 0

    def __init__(self, vocab: dict[str, int]):
        self.vocab = vocab

    def __call__(self, text, add_special_tokens=False):
        if text in self.vocab:
            return {"input_ids": [self.vocab[text]]}
        return {"input_ids": [5, 6]}

    def convert_ids_to_tokens(self, tid):
        return {v: k for k, v in self.vocab.items()}.get(tid, "<unk>")


def test_stop_token_must_be_one_token():
    tok = _Tok({"<|im_end|>": 151645, "<|endoftext|>": 0})
    assert am3.stop_token_id(tok, "<|im_end|>") == 151645
    # OLMo-2's end-of-text is also its unk token; it is still a valid single token.
    assert am3.stop_token_id(tok, "<|endoftext|>") == 0
    with pytest.raises(am3.Am3Error):
        am3.stop_token_id(tok, "</s>")


def test_worker_env_sets_the_mode(tmp_path):
    config = am3.load_config()
    bi = am3.step_spec(config, "rd-olmo2")
    default = am3.step_spec(config, "rd-olmo2-default")
    env = am3.worker_env({"VLLM_BATCH_INVARIANT": "1", "PATH": "/bin"}, tmp_path, default)
    assert "VLLM_BATCH_INVARIANT" not in env and env["CUDA_VISIBLE_DEVICES"] == "0"
    env = am3.worker_env({"PATH": "/bin"}, tmp_path, bi)
    assert env["VLLM_BATCH_INVARIANT"] == "1" and env["HF_HUB_OFFLINE"] == "1"
    assert env["VLLM_CACHE_ROOT"].startswith(str(tmp_path / "cache" / "rd-olmo2"))


def test_engine_kwargs():
    config = am3.load_config()
    pilot = am3.load_pilot_config(config)
    qwen35 = am3.model_spec(config, pilot, am3.step_spec(config, "rd-qwen35-9b"))
    kw = am3.engine_kwargs(qwen35, 42, True)
    assert kw["enforce_eager"] is True and kw["limit_mm_per_prompt"] == {"image": 0, "video": 0}
    assert kw["trust_remote_code"] is False and kw["seed"] == 42
    judge = am3.model_spec(config, pilot, am3.step_spec(config, "judge32"))
    assert judge["model_id"] == "qwen3-32b" and judge["sampling"]["max_tokens"] == 10
    assert "limit_mm_per_prompt" not in am3.engine_kwargs(judge, 42, False)
    assert "enforce_eager" not in am3.engine_kwargs(judge, 42, False)


# --------------------------------------------------------------------------- judge items


def test_judge_items_are_the_union_of_distinct_replies():
    pilot = am3.load_pilot_config(am3.load_config())
    artifact = _toy_artifact(2)
    passes = {
        "rd-a": {0: "Blue 0.", 1: " Blue 0. ", 71: "I don't know."},
        "rd-b": {0: "Blue 0.", 2: "Red.", 142: "Blue 1."},
    }
    items = am3.judge_items(artifact, pilot, passes)
    reader = [(i["question_index"], i["response"]) for i in items if i["source"] == "reader"]
    assert reader == [(0, "Blue 0."), (0, "I don't know."), (0, "Red."), (1, "Blue 1.")]
    assert [i["index"] for i in items] == list(range(len(items)))
    sources = {i["source"] for i in items if i["source"] != "reader"}
    assert sources == {"validation:reference", "validation:idk"}


# --------------------------------------------------------------------------- the rule


def _pool(abstain: dict[int, bool], u32: dict[int, int], u8=None, ranks=None) -> dict:
    ranks = ranks or [3, 0, 5, 1, 7, 2, 6, 4]
    masks = {}
    for m in am3.REQUEST_MASKS:
        masks[m] = {
            "abstain": abstain.get(m, False),
            "u": {"primary": u32.get(m, 0), "secondary": (u8 or u32).get(m, 0)},
        }
    return {"question_id": "t", "question_type": "x", "arm": "retrieved", "bm25_rank": ranks,
            "masks": masks}  # fmt: skip


def test_nonabstain_bm25_keeps_the_first_answering_set_in_bm25_order():
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order = am3.bm25_order(ranks)
    top4 = lf.bm25_top_mask(ranks)
    assert order[0] == top4
    abstain = {order[0]: True, order[1]: True}
    rule = am3.nonabstain_bm25(_pool(abstain, {}, ranks=ranks))
    assert rule == {"mask": order[2], "first_answer_position": 3, "reads": 3}
    # It is AM1d's nonabstain@70 choice.
    features = {"bm25_rank": ranks, "abstain": [abstain.get(m, False) for m in range(256)]}
    nonabstain = next(u for u in lf.UTILITIES if u.name == "nonabstain")
    assert lf.select(features, list(lf.FOUR_SETS), nonabstain) == order[2]


def test_nonabstain_bm25_falls_back_to_top4_when_every_set_abstains():
    abstain = dict.fromkeys(lf.FOUR_SETS, True)
    rule = am3.nonabstain_bm25(_pool(abstain, {}))
    assert rule["mask"] == lf.bm25_top_mask([3, 0, 5, 1, 7, 2, 6, 4])
    assert rule["first_answer_position"] is None and rule["reads"] == 70


def test_table_record_counts_under_both_judges():
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order = am3.bm25_order(ranks)
    top4 = order[0]
    abstain = {top4: True, 255: True}
    u32 = {order[1]: 1, 255: 0}
    u8 = {top4: 1, order[1]: 1, 255: 1}
    rec = am3.table_record(_pool(abstain, u32, u8, ranks))
    assert rec["nonabstain_mask"] == order[1] and rec["reads"] == 2
    assert rec["u"]["primary"] == {
        "bm25_top4": 0, "nonabstain_bm25": 1, "all_8": 0, "oracle_best4": 1,
        "four_subset_correct": 1, "four_subset_abstain_correct": 0,
        "four_subset_nonabstain_correct": 1, "all_8_abstain_correct": 0,
    }  # fmt: skip
    assert rec["u"]["secondary"]["bm25_top4"] == 1
    assert rec["u"]["secondary"]["four_subset_abstain_correct"] == 1
    assert rec["u"]["secondary"]["all_8_abstain_correct"] == 1
    assert rec["bm25_top4_abstains"] and rec["all_8_abstains"]


def test_cell_summary_paired_counts_and_exact_p():
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order = am3.bm25_order(ranks)
    records = []
    # 6 questions where top 4 abstains and the next set is right: b = 6 against top 4.
    for q in range(6):
        pool = _pool({order[0]: True}, {order[1]: 1}, ranks=ranks)
        pool["question_id"] = f"g{q}"
        records.append(am3.table_record(pool))
    # 1 question where the switch loses: top 4 abstains but is judged right.
    pool = _pool({order[0]: True}, {order[0]: 1}, ranks=ranks)
    pool["question_id"] = "loss"
    records.append(am3.table_record(pool))
    # 3 questions where top 4 answers right and all 8 is right.
    for q in range(3):
        pool = _pool({}, {order[0]: 1, 255: 1}, ranks=ranks)
        pool["question_id"] = f"same{q}"
        records.append(am3.table_record(pool))
    cell = am3.cell_summary(records, "primary", 500, 42, 0.05)
    hc = cell["paired"]["nonabstain_bm25_vs_bm25_top4"]
    assert (hc["rule_right_base_wrong"], hc["rule_wrong_base_right"]) == (6, 1)
    assert hc["p_exact_mcnemar"] == pytest.approx(ks.mcnemar_exact(6, 1))
    assert hc["description"] == "NOT_SEPARATED"  # p = 0.125
    assert cell["accuracy"]["nonabstain_bm25"]["mean"] == pytest.approx(9 / 10)
    assert cell["accuracy"]["bm25_top4"]["mean"] == pytest.approx(4 / 10)
    assert cell["abstention"]["bm25_top4_abstains"] == 7
    assert cell["abstention"]["four_subset_abstain_judged_correct"] == 1
    assert cell["abstention"]["rule_switches_from_top4"] == 7
    assert cell["stop_rule_reads"]["median"] == 2.0
    h8 = cell["paired"]["nonabstain_bm25_vs_all_8"]
    assert (h8["rule_right_base_wrong"], h8["rule_wrong_base_right"]) == (6, 0)


def test_reading_labels():
    assert am3.reading({"rule_right_base_wrong": 9, "rule_wrong_base_right": 0,
                        "p_exact_mcnemar": 0.004}, 0.05) == "HELPS"  # fmt: skip
    assert am3.reading({"rule_right_base_wrong": 0, "rule_wrong_base_right": 9,
                        "p_exact_mcnemar": 0.004}, 0.05) == "HURTS"  # fmt: skip
    assert am3.reading({"rule_right_base_wrong": 2, "rule_wrong_base_right": 0,
                        "p_exact_mcnemar": 0.5}, 0.05) == "NOT_SEPARATED"  # fmt: skip


# --------------------------------------------------------------------------- toy run end to end


def _reply(reader: str, q: int, arm: str, mask: int) -> str:
    """Deterministic toy replies: right ("blue q") when memories 0 and 1 are kept, otherwise an
    abstention or a wrong answer; the second reader abstains in other words more often."""

    if mask & 0b11 == 0b11:
        return f"It is blue {q}." if mask & 0b100 else f"Blue {q}."
    if reader == "b" and mask % 2:
        return "The memories do not mention it."
    return "I don't know." if mask % 3 else f"It is red {q}."


def _write_pass(directory: Path, rows: dict[int, tuple[list[int], list[float], str, str]]) -> None:
    import numpy as np

    directory.mkdir(parents=True, exist_ok=True)
    indices = sorted(rows)
    offsets, tokens, logps, finishes = [0], [], [], []
    for i in indices:
        t, lp, finish, _ = rows[i]
        tokens += t
        logps += lp
        offsets.append(len(tokens))
        finishes.append(finish)
    np.savez_compressed(
        directory / "all.npz",
        request_index=np.asarray(indices, dtype=np.int32),
        offsets=np.asarray(offsets, dtype=np.int64),
        token_ids=np.asarray(tokens, dtype=np.int32),
        logprobs=np.asarray(logps, dtype=np.float32),
        num_cached=np.zeros(len(indices), dtype=np.int32),
    )
    (directory / "all.json").write_text(json.dumps({"finish_reasons": finishes}))
    with gzip.open(directory / "all.texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for i in indices:
            handle.write(json.dumps({"request_index": i, "text": rows[i][3]}) + "\n")


def _reader_rows(artifact: dict, reader: str) -> dict:
    rows = {}
    for r in am3.request_table(artifact):
        text = _reply(reader, r["question_index"], r["arm"], r["mask"])
        rows[r["index"]] = ([100 + len(text) % 7, 151645], [-0.1, -0.01], "stop", text)
    return rows


def _toy_run(tmp_path: Path) -> tuple[Path, dict]:
    pilot = am3.load_pilot_config(am3.load_config())
    artifact = _toy_artifact(4)
    run = tmp_path / "run" / "am3"
    steps = {
        "rd-qwen3-8b": {"kind": "reader", "reader": "qwen3-8b", "status": "complete",
                        "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2": {"kind": "reader", "reader": "olmo-2-1124-7b-instruct", "status": "failed",
                     "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2-default": {"kind": "reader", "reader": "olmo-2-1124-7b-instruct",
                             "status": "complete", "batch_invariant": False,
                             "enforce_eager": True},
        "judge32": {"kind": "judge", "status": "complete"},
        "judge8": {"kind": "judge", "status": "complete"},
    }  # fmt: skip
    (run).mkdir(parents=True)
    (run / "summary.json").write_text(json.dumps({"steps": steps}))
    passes = {}
    for sid, reader in (("rd-qwen3-8b", "a"), ("rd-olmo2-default", "b")):
        rows = _reader_rows(artifact, reader)
        _write_pass(run / "sessions" / sid, rows)
        passes[sid] = {i: row[3] for i, row in rows.items()}
    items = am3.judge_items(artifact, pilot, passes)
    (run / "judge-items.json").write_text(json.dumps(items))
    for step, idk_yes in (("judge32", False), ("judge8", True)):
        rows = {}
        for item in items:
            q = artifact["questions"][item["question_index"]]
            right = q["answer"] in item["response"].lower()
            yes = right or (idk_yes and "don't know" in item["response"])
            rows[item["index"]] = ([7], [-0.01], "stop", "yes" if yes else "no")
        _write_pass(run / "sessions" / step, rows)
    return run, artifact


def _toy_tables(artifact: dict, flip: tuple[str, str, int] | None = None) -> list[dict]:
    tables = []
    for q, question in enumerate(artifact["questions"]):
        for arm in am3.ARMS:
            values = [
                1.0 if f"blue {q}" in _reply("a", q, arm, m).lower() else 0.0 for m in range(256)
            ]
            if flip and flip[:2] == (question["question_id"], arm):
                values[flip[2]] = 1.0 - values[flip[2]]
            tables.append({"question_id": question["question_id"], "arm": arm,
                           "values_hex": cc.encode_values(values)})  # fmt: skip
    return tables


def test_extract_and_analyze_end_to_end(tmp_path, monkeypatch):
    run, artifact = _toy_run(tmp_path)
    flip = ("q1", "gold", sorted(lf.FOUR_SETS)[5])
    monkeypatch.setattr(am3, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(am3.cc, "load_tables", lambda *a, **k: _toy_tables(artifact, flip))
    private = tmp_path / "private"
    args = am3.argparse.Namespace(
        config=str(am3.CONFIG_PATH), run_dir=str(run), evidence=str(tmp_path / "artifact.json"),
        private_dir=str(private), pilot_run_dir=None, pilot_eager_run_dir=None,
    )  # fmt: skip
    brief = am3.cmd_extract(args)
    assert set(brief["readers"]) == {"qwen3-8b", "olmo-2-1124-7b-instruct"}
    assert brief["readers"]["olmo-2-1124-7b-instruct"]["batch_invariant"] is False
    assert brief["readers"]["qwen3-8b"]["pools_complete"] == 8
    tables = brief["anchor_comparisons"]["tables"]
    assert (tables["cells"], tables["cells_same_label"]) == (8 * 71, 8 * 71 - 1)
    assert tables["tables_with_any_difference"] == 1
    v = brief["validation"]["judge_validation"]
    assert v["primary"]["validation:idk"]["yes"] == 0
    assert v["secondary"]["validation:idk"]["yes"] == 4
    assert v["primary"]["validation:reference"]["yes"] == 4
    out_a, out_b = tmp_path / "out-a", tmp_path / "out-b"
    digests = []
    for out in (out_a, out_b):
        digests.append(am3.cmd_analyze(am3.argparse.Namespace(
            config=str(am3.CONFIG_PATH), features=str(private / "features.json.gz"),
            output_dir=str(out))))  # fmt: skip
    assert digests[0] == digests[1]
    results = json.loads((out_a / "results.json").read_text())
    cells = results["cells"]
    # Reader a (anchor): every abstaining set is judged wrong by the primary judge, so the rule
    # never loses against top 4 under it.
    for arm in am3.ARMS:
        hc = cells["qwen3-8b"]["primary"][arm]["paired"]["nonabstain_bm25_vs_bm25_top4"]
        assert hc["rule_wrong_base_right"] == 0
    # The toy second judge calls "I don't know." correct; the primary never does.
    for arm in am3.ARMS:
        assert (
            cells["qwen3-8b"]["primary"][arm]["abstention"]["four_subset_abstain_judged_correct"]
            == 0
        )
        assert (
            cells["qwen3-8b"]["secondary"][arm]["abstention"]["four_subset_abstain_judged_correct"]
            > 0
        )
    # Reader b's other abstention phrase is matched by AM1d's not_in_memories pattern.
    b = cells["olmo-2-1124-7b-instruct"]["primary"]["retrieved"]["abstention"]
    a = cells["qwen3-8b"]["primary"]["retrieved"]["abstention"]
    assert b["four_subset_abstain"] > a["four_subset_abstain"]
    # No reply text reaches the outputs.
    blob = (out_a / "results.json").read_text() + (out_a / "tables.md").read_text()
    blob += gzip.decompress((out_a / "per-table.json.gz").read_bytes()).decode()
    for text in ("blue 0", "blue 3", "red 1", "it is", "do not mention", "don't know."):
        assert text not in blob.lower().replace('"i don\'t know.", yes', "")
    assert len(json.loads(gzip.decompress((out_a / "per-table.json.gz").read_bytes()))) == 16


def test_analyze_refuses_incomplete_pools(tmp_path, monkeypatch):
    run, artifact = _toy_run(tmp_path)
    monkeypatch.setattr(am3, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(am3.cc, "load_tables", lambda *a, **k: _toy_tables(artifact))
    args = am3.argparse.Namespace(
        config=str(am3.CONFIG_PATH), run_dir=str(run), evidence="x",
        private_dir=str(tmp_path / "p"), pilot_run_dir=None, pilot_eager_run_dir=None,
    )  # fmt: skip
    am3.cmd_extract(args)
    features = lf.read_gz_json(tmp_path / "p" / "features.json.gz")
    broken = copy.deepcopy(features)
    pool = broken["readers"]["qwen3-8b"]["pools"][0]
    pool["masks"][str(sorted(lf.FOUR_SETS)[0])]["u"]["secondary"] = None
    with pytest.raises(am3.Am3Error):
        am3.analyze(broken, 100, 42, 0.05)
    other = copy.deepcopy(features)
    other["abstention_patterns_sha256"] = "0" * 64
    with pytest.raises(am3.Am3Error):
        am3.analyze(other, 100, 42, 0.05)


def test_anchor_vs_pass_counts_identity_and_labels():
    artifact = _toy_artifact(2)
    requests = am3.request_table(artifact)
    pilot_requests = [r for r in ms.request_table(artifact, list(am3.ARMS)) if r["kind"] == "table"]
    texts = {r["index"]: _reply("a", r["question_index"], r["arm"], r["mask"]) for r in requests}

    def row(text, tokens, bits=b"\x00\x00\x80\xbf"):
        return {"tokens": tuple(tokens), "bits": bits, "finish": "stop", "text": text}

    anchor_rows = {i: row(t, [1, 2]) for i, t in texts.items()}
    pilot_rows = {}
    by_key = {(r["question_index"], r["arm"], r["mask"]): r["index"] for r in requests}
    for r in pilot_requests:
        i = by_key.get((r["question_index"], r["arm"], r["mask"]))
        if i is None:
            pilot_rows[r["index"]] = row("unused", [9])
            continue
        pilot_rows[r["index"]] = row(texts[i], [1, 2])
    # One pilot reply differs in text and one only in its log-prob bits.
    changed = by_key[(0, "retrieved", 255)]
    pilot_index = {(r["question_index"], r["arm"], r["mask"]): r["index"] for r in pilot_requests}
    pilot_rows[pilot_index[(0, "retrieved", 255)]] = row("Something else.", [1, 3])
    pilot_rows[pilot_index[(1, "gold", 255)]] = row(texts[by_key[(1, "gold", 255)]], [1, 2],
                                                    b"\x00\x00\x00\x00")  # fmt: skip
    a_items = {(r["question_index"], texts[r["index"]].strip()): n for n, r in enumerate(requests)}
    p_items = dict(a_items)
    p_items[(0, "Something else.")] = 10_000
    a_labels = {j: {n: 1 for n in a_items.values()} for j in am3.JUDGES}
    p_labels = {"primary": {n: 1 for n in p_items.values()}, "secondary": None}
    p_labels["primary"][10_000] = 0
    out = am3.anchor_vs_pass(artifact, anchor_rows, a_labels, a_items, pilot_rows, p_labels,
                             p_items)  # fmt: skip
    n = len(requests)
    assert out["compared"] == n
    assert out["identical_tokens"] == n - 1 and out["identical_bits"] == n - 2
    assert out["identical_text"] == n - 1
    assert out["label_compared_primary"] == n and out["label_same_primary"] == n - 1
    assert out["label_same_identical_reply_primary"] == n - 1
    assert out["label_compared_secondary"] == 0
    assert changed in anchor_rows
    limited = am3.anchor_vs_pass(artifact, anchor_rows, a_labels, a_items, pilot_rows,
                                 p_labels, p_items, question_limit=1)  # fmt: skip
    assert limited["compared"] == n // 2
