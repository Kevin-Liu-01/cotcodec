"""Trimming rule q1-stage0-trim/2 (harness.q1.trim): seeds, FRR set, frames, schedule, weights.

Pure Python; the regression tests on the committed pilot-exposure file check the
pilot's own record (jobs 474, 518, 548).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.q1 import pilot, trim
from harness.q1.schema import MUTATION_FAMILIES

SMALL = "L2/74_ConvTranspose3d_LeakyReLU_Multiply_LeakyReLU_Max"  # 0.02 GB
MEDIUM = "L1/95_CrossEntropyLoss"  # 0.54 GB
BIG = "L1/3_Batched_matrix_multiplication"  # 1.34 GB
BIGGER = "L1/89_cumsum"  # 4.3 GB


def _sub(kernel_id: str, problem: str, unit: str | None = None) -> trim.KernelRecord:
    return trim.KernelRecord(
        kernel_id=kernel_id,
        kernel_path=f"/c/{kernel_id}/kernel.py",
        problem_id=problem,
        kind="substrate",
        half="evaluation",
        unit=unit or f"u:{kernel_id}",
    )


def _mut(kernel_id: str, parent: str, problem: str, family: str, split: str) -> trim.KernelRecord:
    return trim.KernelRecord(
        kernel_id=kernel_id,
        kernel_path=f"/c/{kernel_id}/kernel.py",
        problem_id=problem,
        kind="mutant",
        half="evaluation",
        parent=parent,
        family=family,
        split=split,
        dedup_hash=hashlib.sha256(kernel_id.encode()).hexdigest(),
        base_weight=2.0,
    )


def test_seeds_are_named_and_order_free() -> None:
    assert trim.seed_of("mutants", "arithmetic", "test") == int.from_bytes(
        hashlib.sha256(b"q1-stage0-trim/2/mutants/arithmetic/test").digest()[:8], "big"
    )
    ids = [f"k{i}" for i in range(50)]
    first = trim.seeded_order(ids, "x")
    assert first == trim.seeded_order(list(reversed(ids)), "x")
    assert sorted(first) == sorted(ids) and first != sorted(ids)
    assert trim.seeded_order(ids, "y") != first
    assert [trim.sample_size(0.15, n) for n in (0, 1, 6, 7, 69)] == [0, 1, 1, 2, 11]


def test_concurrency_classes_follow_native_bytes() -> None:
    assert trim.concurrency_class(SMALL) == "small" and trim.concurrency_units(SMALL) == 1
    assert trim.concurrency_class(MEDIUM) == "small"  # 0.537 GB < 0.6 GB
    assert trim.concurrency_units(BIG) == trim.TRIM_RULE["slot_capacity"]
    assert trim.concurrency_class("L9/1_not_in_the_manifest") == "exclusive"


def test_frr_set_skips_substrates_that_add_no_unit_and_splits_core_and_margin() -> None:
    subs = [_sub(f"s{i}", SMALL) for i in range(3)]
    subs += [
        _sub("x-big-family", BIG, unit="u:s0"),  # same unit as an in-scope substrate
        _sub("y-big", BIG),
        _sub("z-bigger", BIGGER),
        _sub("w-bigger", BIGGER),
    ]
    rule = {**trim.TRIM_RULE, "frr_min_units": 4, "frr_margin_units": 1}
    out = trim.frr_set(subs, rule)
    assert [s.kernel_id for s in out["core"]] == ["y-big"]
    assert out["skipped_no_new_unit"] == ["x-big-family"]
    assert [s.kernel_id for s in out["margin"]] == ["w-bigger"]  # ties by substrate id
    assert out["units_with_core"] == 4 and out["units_with_margin"] == 5


def test_frames_drop_exposed_mutants_by_id_and_by_content() -> None:
    parent = "s0"
    mutants = [_mut(f"s0.m{i}", parent, SMALL, "arithmetic", "test") for i in range(5)]
    exposed = {
        "mutants": [
            {"kernel_id": "s0.m1", "parent": parent, "dedup_hash": "unused"},
            # renamed in a rebuilt corpus, same content
            {"kernel_id": "old-id", "parent": parent, "dedup_hash": mutants[3].dedup_hash},
        ]
    }
    framed = trim.mutant_frames(mutants, {parent}, exposed)
    assert framed["exposed_removed"] == ["s0.m1", "s0.m3"]
    assert sorted(framed["frames"]["arithmetic"]["test"]) == ["s0.m0", "s0.m2", "s0.m4"]
    assert framed["frames"]["arithmetic"]["test"] == trim.seeded_order(
        ["s0.m0", "s0.m2", "s0.m4"], "mutants", "arithmetic", "test"
    )


def test_samples_are_prefixes_and_rank_major_cuts_every_family_evenly() -> None:
    frames = {
        "arithmetic": {"test": [f"a{i}" for i in range(130)], "dev": [f"ad{i}" for i in range(20)]},
        "boundary": {"test": [f"b{i}" for i in range(7)], "dev": []},
    }
    sample = trim.mutant_sample(frames)
    assert sample["arithmetic"]["test_quota"] == frames["arithmetic"]["test"][:60]
    assert sample["arithmetic"]["robustness"] == frames["arithmetic"]["test"][:6]
    assert sample["arithmetic"]["test_extension"] == frames["arithmetic"]["test"][60:120]
    assert sample["arithmetic"]["dev_quota"] == frames["arithmetic"]["dev"][:15]
    assert sample["boundary"]["test_quota"] == frames["boundary"]["test"]
    assert sample["boundary"]["robustness"] == frames["boundary"]["test"][:1]
    order = trim.rank_major({f: v["test_quota"] for f, v in sample.items()})
    first_two = order[:2]
    assert {x[0] for x in first_two} == {"a", "b"}  # rank 0 of both families first
    assert trim.family_order() == trim.seeded_order(MUTATION_FAMILIES, "family-order")


def _control(kernel_id: str, problem: str, kind: str, parent: str | None, hack: str | None):
    return trim.KernelRecord(
        kernel_id=kernel_id,
        kernel_path=f"/c/{kernel_id}/kernel.py",
        problem_id=problem,
        kind="control",
        parent=parent,
        control_kind=kind,
        hack_kind=hack,
    )


def test_control_schedule_samples_every_kind_and_lists_the_rest() -> None:
    subs = [f"s{i}" for i in range(10)]
    controls = [
        _control(f"{s}.hack.decoy", SMALL, "hack-emulating-mutant", s, "decoy") for s in subs
    ]
    controls.append(
        _control(
            "big.hack.kbv-h1-identity-shortcut",
            "L1/19_ReLU",
            "hack-emulating-mutant",
            "big",
            "kbv-h1-identity-shortcut",
        )
    )
    controls.append(_control("ctl-identity-a", SMALL, "reference-identity", None, None))
    controls.append(_control("ctl-identity-b", "L1/19_ReLU", "reference-identity", None, None))
    controls.append(
        _control(
            "ctl-kernelbench-zero-out-L1-1",
            "L1/1_Square_matrix_multiplication_",
            "kernelbench-adversarial",
            None,
            None,
        )
    )
    out = trim.control_schedule(controls, set(subs), {SMALL, "L1/19_ReLU"})
    assert len(out["hack_sample"]["decoy"]) == 2  # ceil(0.15 * 10)
    assert out["kinds_without_in_scope_instance"] == ["kbv-h1-identity-shortcut"]
    assert out["identity"] == ["ctl-identity-a"]
    assert "ctl-identity-b" in out["not_scheduled"]["identity-out-of-scope"]
    assert len(out["not_scheduled"]["decoy:not-sampled"]) == 8
    assert out["adversarial"] == ["ctl-kernelbench-zero-out-L1-1"]


def _corpus() -> list[trim.KernelRecord]:
    records = [_sub("s1-a", SMALL), _sub("s1-b", MEDIUM), _sub("s1-c", BIG), _sub("s2-d", BIGGER)]
    for family in ("arithmetic", "indexing"):
        for i in range(6):
            split = "test" if i % 2 else "dev"
            records.append(_mut(f"s1-a.{family}{i}", "s1-a", SMALL, family, split))
    records.append(_control("s1-a.hack.decoy", SMALL, "hack-emulating-mutant", "s1-a", "decoy"))
    return records


def test_plan_runs_buckets_in_order_with_units_and_limits() -> None:
    exposed = {"mutants": [{"kernel_id": "s1-a.arithmetic1", "parent": "s1-a", "dedup_hash": "x"}]}
    rule = {**trim.TRIM_RULE, "frr_min_units": 3, "frr_margin_units": 1}
    record = trim.plan(_corpus(), rule=rule, exposed=exposed)
    items = record["items"]
    buckets = [i["bucket"] for i in items]
    assert buckets == sorted(buckets)  # bucket order is the run order
    assert record["frr_set"]["core"] == ["s1-c"] and record["frr_set"]["margin"] == ["s2-d"]
    assert "s1-a.arithmetic1" not in {i["kernel_id"] for i in items}
    assert record["mutants_exposed_removed"] == ["s1-a.arithmetic1"]
    by_kernel = {i["kernel_id"]: i for i in items}
    assert by_kernel["s1-c"]["units"] == rule["slot_capacity"] and by_kernel["s1-a"]["units"] == 1
    assert by_kernel["s1-c"]["timeouts"] == pilot.watchdog_limits(BIG)
    p1 = [i for i in items if i["bucket"] == "P1"]
    assert {i["kernel_id"] for i in p1} >= {"s1-a", "s1-b", "s1-c", "s1-a.hack.decoy"}
    assert all(i["seed"] == 42 for i in p1)
    p3 = {(i["kernel_id"], i["seed"]) for i in items if i["bucket"] == "P3"}
    assert p3 == {("s1-a.hack.decoy", 43), ("s1-a.hack.decoy", 44)}
    p5 = {i["kernel_id"] for i in items if i["bucket"] == "P5"}
    assert p5 == {"s1-a", "s1-b"}  # only in-scope substrates get replicates
    # every kernel-replicate carries every scoring gate
    per = {}
    for i in items:
        per.setdefault((i["bucket"], i["kernel_id"], i["seed"]), set()).add(i["gate"])
    assert all(g == set(trim.SCORING_GATES) for g in per.values())
    assert record["plan_sha256"] == trim.plan_digest(record)
    again = trim.plan(list(reversed(_corpus())), rule=rule, exposed=exposed)
    assert again["plan_sha256"] == record["plan_sha256"]


def test_ht_weights_use_frame_size_over_scored_including_cut_items() -> None:
    record = {
        "mutant_frames": {"arithmetic": {"test": ["m1", "m2", "m3", "m4"], "dev": []}},
        "mutant_sample": {
            "arithmetic": {"test_quota": ["m1", "m2", "m3"], "test_extension": [], "dev_quota": []}
        },
    }
    out = trim.ht_weights(record, {"m1", "m2"}, {"m1": 2.0, "m2": None})
    assert out["weights"] == {"m1": 4.0, "m2": 2.0}  # (n/k) x (N/m) = base x 4/2
    factor = out["factors"]["arithmetic/test"]
    assert factor["N"] == 4 and factor["m"] == 2 and factor["sampled_not_scored"] == ["m3"]
    done = trim.scored_kernel_replicates(
        [("k", g, 42) for g in trim.SCORING_GATES] + [("k2", "a", 42)]
    )
    assert done == {("k", 42)}


def test_budget_check_is_the_sum_of_caps() -> None:
    ok = trim.budget_check(spent_gpu_hours=0.9, job_cap_gpu_hours=5.0, reserve_gpu_hours=1.5)
    assert ok["ok"] and ok["headroom_gpu_hours"] == pytest.approx(0.6)
    over = trim.budget_check(spent_gpu_hours=0.9, job_cap_gpu_hours=6.0, reserve_gpu_hours=1.5)
    assert not over["ok"]
    assert not trim.budget_check(spent_gpu_hours=0, job_cap_gpu_hours=0, reserve_gpu_hours=0)["ok"]


def test_pilot_exposure_file_is_hash_bound_and_lists_the_pilot_record(tmp_path: Path) -> None:
    exposed = trim.load_exposed()
    tests = sorted(
        m["kernel_id"].split(".", 1)[1] for m in exposed["mutants"] if m["split"] == "test"
    )
    assert tests == [
        "launch-stride-swap.L158C21",
        "plus2minus.L132C31",
        "program-id-axis-swap.L55C17",
    ]
    assert len(exposed["mutants"]) == 8
    assert sorted(exposed["evaluation_units"]) == [
        "flaggems:src/flag_gems/cumsum.py:cumsum_kernel",
        "inductor:L1/3_Batched_matrix_multiplication",
        "inductor:L2/3_ConvTranspose3d_Sum_LayerNorm_AvgPool_GELU",
        "inductor:L2/74_ConvTranspose3d_LeakyReLU_Multiply_LeakyReLU_Max",
        "liger:src/liger_kernel/ops/cross_entropy.py:liger_cross_entropy_kernel",
        "triton-tutorials:python/tutorials/03-matrix-multiplication.py:matmul_kernel",
    ]
    assert exposed["data_motivated_units"]["tf32-tl-dot-threshold"] == [
        "triton-tutorials:python/tutorials/03-matrix-multiplication.py:matmul_kernel"
    ]
    tampered = tmp_path / "exposed.json"
    tampered.write_text(json.dumps({**exposed, "mutants": []}))
    with pytest.raises(ValueError):
        trim.load_exposed(tampered)
