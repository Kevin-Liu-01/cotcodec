from __future__ import annotations

import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")

from harness import sparse_indexer_k1_runtime as rt  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402


def devkl(means: dict[str, float], layers=(0, 1), seeds=(42, 43, 44)) -> list[dict]:
    kl = {}
    for layer in layers:
        for key, value in means.items():
            for seed in seeds:
                kl[f"L{layer:02d}|{key}|{seed}"] = value
    return [{"kl": kl}]


def test_lr_freeze_prefers_1e3_within_one_percent() -> None:
    payload = devkl({"hs|3e-4": 1.000, "hs|1e-3": 1.009, "hs|3e-3": 1.2,
                     "mp|3e-4": 2.0, "mp|1e-3": 2.5, "mp|3e-3": 1.5})
    freeze = rt.freeze_learning_rates(payload, ("hs", "mp"), rt.LEARNING_RATES, (42, 43, 44))
    assert freeze["selected_lr"] == {"hs": "1e-3", "mp": "3e-3"}


def test_lr_freeze_refuses_incomplete_tables() -> None:
    payload = devkl({"hs|3e-4": 1.0, "hs|1e-3": 1.0}, seeds=(42,))
    with pytest.raises(rt.RuntimeContractError):
        rt.freeze_learning_rates(payload, ("hs",), rt.LEARNING_RATES, (42, 43, 44))


def test_epoch_order_and_batches() -> None:
    assert rt.epoch_order(6, 1).tolist() == list(range(6))
    second, third = rt.epoch_order(6, 2), rt.epoch_order(6, 3)
    assert sorted(second.tolist()) == list(range(6)) and second.tolist() != third.tolist()
    assert rt.batch_indices(1, 2, 6, 3).tolist() == [2, 3]
    assert rt.batch_indices(3, 2, 6, 3).tolist() == second[:2].tolist()


def test_learning_rate_warmup_and_tags() -> None:
    assert rt.learning_rate(0, 1e-3, 20) == pytest.approx(5e-5)
    assert rt.learning_rate(19, 1e-3, 20) == pytest.approx(1e-3)
    assert rt.learning_rate(500, 1e-3, 20) == pytest.approx(1e-3)
    assert [rt.lr_tag(v) for v in rt.LEARNING_RATES] == ["3e-4", "1e-3", "3e-3"]
    assert rt.indexer_key("hs", 1e-3, 42) == "hs|1e-3|42"


def test_plan_units_deduplicates_and_merges_needs() -> None:
    prompts = [
        {"prompt_id": "a", "context_index": 0, "query_index": 0, "role": "main", "condition": "MN"},
        {"prompt_id": "b", "context_index": 0, "query_index": 0, "role": "same-script",
         "condition": "MN"},
        {"prompt_id": "c", "context_index": 1, "query_index": 2, "role": "absent",
         "condition": "CX"},
    ]
    units, mapping = rt.plan_units(prompts, {"main", "same-script"}, {"absent"}, {"CX"})
    assert len(units) == 2 and mapping["a"] == mapping["b"]
    by_id = {u["unit"]: u for u in units}
    assert by_id[mapping["a"]]["select"] and not by_id[mapping["a"]]["mc"]
    assert by_id[mapping["c"]]["mc"] and not by_id[mapping["c"]]["select"]


def _chunk(directory, units, value=1.0) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    n = len(units)
    np.savez(directory / f"chunk-{units[0]}.npz", unit_ids=np.asarray(units),
             recall=np.full((n, 2, 3), value, np.float32), ties=np.zeros((n, 3), np.int32),
             max_selected_tokens=np.zeros(n, np.int32), mc_scores=np.zeros((n, 4), np.float32),
             mc_correct=np.zeros(n, np.int32), selectors=np.asarray(["T:hs", "U", "rand"]))


def test_collect_eval_maps_prompts_and_enforces_the_ledger(tmp_path) -> None:
    stage = tmp_path / "eval" / "s"
    _chunk(stage, ["u1", "u2"])
    merged = rt.collect_eval(tmp_path, "s", {"p1": "u1", "p2": "u1", "p3": "u2"})
    assert merged["units"] == 2 and set(merged["rows"]) == {"p1", "p2", "p3"}
    with pytest.raises(rt.RuntimeContractError, match="missing"):
        rt.collect_eval(tmp_path, "s", {"p4": "u9"})
    _chunk(stage, ["u2"])  # a second chunk named after u2 duplicates it
    with pytest.raises(rt.RuntimeContractError, match="twice"):
        rt.collect_eval(tmp_path, "s", {"p1": "u1"})


def test_checkpoint_store_keeps_two_generations_and_skips_corrupt(tmp_path) -> None:
    store = rt.CheckpointStore(tmp_path / "w0")
    for step in (10, 20, 30):
        store.save(step, {"x": torch.full((3,), float(step))}, {"config_digest": "c"})
    assert store.generations() == [20, 30]
    (store.path(30) / "state.safetensors").write_bytes(b"corrupt")
    step, tensors, meta = store.load_latest()
    assert step == 20 and float(tensors["x"][0]) == 20.0 and meta["step"] == 20


def test_load_step_never_falls_back_to_an_older_generation(tmp_path) -> None:
    store = rt.CheckpointStore(tmp_path / "worker-0")
    for step in (4, 6):
        store.save(step, {"x": torch.full((3,), float(step))}, {"config_digest": "c"})
    tensors, meta = store.load_step(6)
    assert float(tensors["x"][0]) == 6.0 and meta["step"] == 6
    data = bytearray((store.path(6) / "state.safetensors").read_bytes())
    data[-1] ^= 0xFF
    (store.path(6) / "state.safetensors").write_bytes(bytes(data))
    with pytest.raises(rt.RuntimeContractError, match="fails its digest check"):
        store.load_step(6)
    with pytest.raises(rt.RuntimeContractError):
        store.load_step(8)
    assert store.load_latest()[0] == 4  # training resumes may still fall back


def test_completed_generation_must_match_its_record(tmp_path) -> None:
    ckpt = tmp_path / "checkpoints"
    store = rt.CheckpointStore(ckpt / "worker-1")
    digest = store.save(6, {"x": torch.ones(2)}, {"config_digest": "c"})
    assert not rt.training_completed(ckpt, 2, 6)
    with pytest.raises(rt.RuntimeContractError, match="no completion record"):
        rt.load_completed_generation(ckpt, 1, 6)
    rt.write_completion_record(ckpt, 1, 6, digest, "c", "final")
    tensors, _ = rt.load_completed_generation(ckpt, 1, 6)
    assert float(tensors["x"][0]) == 1.0
    rt.write_completion_record(ckpt, 1, 6, "0" * 64, "c", "final")
    with pytest.raises(rt.RuntimeContractError, match="differs from its completion record"):
        rt.load_completed_generation(ckpt, 1, 6)
    rt.write_completion_record(ckpt, 0, 6, digest, "c", "final")
    assert rt.training_completed(ckpt, 2, 6) and not rt.training_completed(ckpt, 2, 18)


def test_indexer_bank_round_trip_is_bitwise(tmp_path) -> None:
    spec = sit.IndexerSpec(d_model=16, heads=2, dim=8, rope_dims=8)
    keys = ["hs|1e-3|42", "mp|3e-3|43"]
    bank = rt.IndexerBank(spec, [0], keys, torch.device("cpu"))
    hidden = torch.randn(16, 16)
    rows = torch.arange(16)
    target = sit.block_targets(torch.softmax(torch.randn(2, 16, 16).masked_fill(
        torch.triu(torch.ones(16, 16, dtype=bool), 1), float("-inf")), -1), rows)
    for key in keys:
        scores, valid = bank.indexers[(0, key)](hidden, rows)
        sit.kl_block_loss(target[key.split("|")[0]], scores, valid)[0].backward()
        bank.optimisers[(0, key)].step()
    store = rt.CheckpointStore(tmp_path / "w")
    digest = store.save(1, bank.state_tensors(), {})
    fresh = rt.IndexerBank(spec, [0], keys, torch.device("cpu"))
    fresh.load_state(store.load_latest()[1])
    assert sit.state_digest(fresh.state_tensors()) == digest
    assert fresh.param_digest() == bank.param_digest()


def test_atomic_json_returns_the_file_digest(tmp_path) -> None:
    digest = rt.atomic_write_json(tmp_path / "a.json", {"b": 1})
    assert digest == rt.sha256_file(tmp_path / "a.json")
    assert json.loads((tmp_path / "a.json").read_text()) == {"b": 1}


def test_profiles() -> None:
    registered = rt.Profile.registered()
    assert (registered.batch, registered.steps, registered.k_blocks) == (4, 610, 256)
    assert registered.union_k == 1024 and registered.union_budget_k == 64
