"""Re-pilot rule ``q1-repilot/1`` and the store projection (decision D31). Pure Python."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from harness.q1 import cost_card as cc
from harness.q1 import pilot, refstore, repilot, trim

SIZES = {
    "L2/1_A": 10_000_000,
    "L2/2_B": 20_000_000,
    "L2/3_C": 30_000_000,
    "L2/4_D": 100_000_000,
    "L2/5_E": 150_000_000,
    "L2/6_F": 300_000_000,
    "L2/7_G": 350_000_000,
    "L2/8_H": 500_000_000,
    "L2/9_I": 537_000_000,
    "L2/10_J": 700_000_000,
    "L1/11_K": 20_000_000,
    "L1/12_L": 30_000_000,
}


def test_candidates_exclude_s2_problems_ineligible_and_large() -> None:
    ordered = repilot.candidates(
        list(SIZES),
        s2_problems={"L1/12_L"},
        eligible=set(SIZES) - {"L2/3_C"},
        size_of=SIZES.get,
    )
    members = [p for group in ordered.values() for p in group]
    assert "L1/12_L" not in members and "L2/3_C" not in members and "L2/10_J" not in members
    assert ordered["L1-below-0.6GB"] == ["L1/11_K"]
    assert ordered["L2-0-0.05GB"] == sorted(["L2/1_A", "L2/2_B"], key=repilot.order_key)
    assert set(ordered["L2-0.4-0.6GB"]) == {"L2/8_H", "L2/9_I"}
    assert sum(s[4] for s in repilot.STRATA) == 8


def test_pick_replaces_what_does_not_build_and_lists_it() -> None:
    ordered = {"s": ["p1", "p2", "p3", "p4"]}
    record = repilot.pick(ordered, lambda p: p != "p2", counts={"s": 2})
    assert record["problems"] == ["p1", "p3"]
    assert record["strata"] == [
        {"stratum": "s", "chosen": ["p1", "p3"], "replaced_not_built": ["p2"]}
    ]


def test_items_pair_twins_and_place_references_first() -> None:
    problem = "L2/52_Conv2d_Activation_BatchNorm"
    kernels = [
        {"kernel_id": k, "kernel_path": f"/k/{k}.py", "problem_id": problem}
        for k in ("sub", "ctl", "mut")
    ]
    items = repilot.items(kernels, store_root="/store", journal="/out/references.jsonl")
    refs = [i for i in items if refstore.is_reference_gate(i["gate"])]
    assert Counter(i["gate"] for i in refs) == Counter(list(refstore.REFERENCE_GATES))
    assert all(i["journal"] == "/out/references.jsonl" for i in refs)
    consumers = [i for i in items if not refstore.is_reference_gate(i["gate"])]
    assert len(consumers) == 2 * 3 * len(trim.SCORING_GATES)
    # twins adjacent: inline first, then its store twin
    for left, right in zip(consumers[::2], consumers[1::2], strict=True):
        assert repilot.twin(left["kernel_id"]) == right["kernel_id"]
        assert left["gate"] == right["gate"] and not left["requires"]
        assert (right["gate"] in refstore.CHANNEL_OF) == bool(right["requires"])
    first_ref = items.index(refs[0])
    assert items[first_ref + 1]["kernel_id"] == "sub" and items[0]["gate"] == "ref_a"
    assert all(i["units"] == trim.concurrency_units(problem) for i in items)
    assert consumers[0]["timeouts"] == pilot.watchdog_limits(problem)


def _row(kernel: str, verdict: str, **details: object) -> dict:
    return {
        "kernel_id": kernel,
        "gate": "A1",
        "config_id": "aggregate",
        "tf32_policy": "tf32-admissible",
        "verdict": verdict,
        "seed": 42,
        "gpu_seconds": 1.0,
        "wall_seconds": 1.0,
        "max_abs_err": None,
        "max_rel_err": None,
        "tolerance": None,
        "details": {"item_started_at": 1.0, **details},
    }


def test_compare_twins_ignores_timing_and_names_differences() -> None:
    rows = [
        _row("k", "accept", e=1.0),
        {**_row("k.store", "accept", e=1.0), "gpu_seconds": 3.0},
        _row("m", "accept", e=1.0),
        _row("m.store", "accept", e=2.0),
        _row("solo", "reject"),
    ]
    result = repilot.compare_twins(rows)
    assert result["rows_compared"] == 2 and result["rows_identical"] == 1
    assert result["verdicts_identical"] == 2 and result["only_one_arm"] == 1
    assert result["differing"] == [
        {
            "key": ["m", "A1", "aggregate", "tf32-admissible", 42],
            "verdicts_equal": True,
            "fields": [".details.e"],
        }
    ]


def test_store_model_ratio_and_references() -> None:
    model = cc.StoreModel(
        ratio_fits={
            "c": {"inline": {"alpha": 1.0, "beta": 10.0}, "store": {"alpha": 1.0, "beta": 4.0}}
        },
        reference_fits={
            "ref_c": {"alpha": 2.0, "beta": 20.0},
            "ref_A1": {"alpha": 1.0, "beta": 0.0},
        },
    )
    assert model.ratio("c", 0.5) == pytest.approx(3.0 / 6.0)
    assert model.ratio("b1", 0.5) == 1.0
    assert model.reference_seconds(0.5) == pytest.approx(12.0 + 1.0)


def _pairs_and_refs() -> tuple[list[dict], list[dict]]:
    problems = ("L2/52_Conv2d_Activation_BatchNorm", "L2/59_Matmul_Swish_Scaling")
    pairs, refs = [], []
    for problem in problems:
        gb = cc._gigabytes(problem)
        for gate in trim.SCORING_GATES:
            consumer = gate in cc.STORE_CONSUMER_GATES
            pairs.append(
                {
                    "kernel_id": "k",
                    "gate": gate,
                    "seed": 42,
                    "problem_id": problem,
                    "inline": 1.0 + 10.0 * gb,
                    "store": (1.0 + 4.0 * gb) if consumer else (1.0 + 10.0 * gb),
                    "inline_wall": 1.0,
                    "store_wall": 1.0,
                    "same_verdicts": True,
                }
            )
        for gate in refstore.REFERENCE_GATES:
            refs.append({"gate": gate, "problem_id": problem, "gpu_seconds": 1.0 + 5.0 * gb})
    return pairs, refs


def test_fit_store_model_recovers_linear_costs() -> None:
    pairs, refs = _pairs_and_refs()
    model = cc.fit_store_model(pairs, refs)
    assert set(model.ratio_fits) == set(cc.STORE_CONSUMER_GATES)
    fit = model.ratio_fits["c"]
    assert fit["inline"]["beta"] == pytest.approx(10.0) and fit["store"]["beta"] == pytest.approx(
        4.0
    )
    assert model.reference_fits["ref_c"]["alpha"] == pytest.approx(1.0)
    assert model.reference_seconds(0.0) == pytest.approx(len(refstore.REFERENCE_GATES))


def _counts() -> dict:
    rows = []
    for n, problem in enumerate(
        ["L2/52_Conv2d_Activation_BatchNorm", "L2/59_Matmul_Swish_Scaling", "L1/19_ReLU"]
    ):
        rows.append(
            {
                "substrate_id": f"s1-inductor-{problem.replace('/', '-')}",
                "problem_id": problem,
                "source_kind": "inductor",
                "native_input_bytes": pilot.native_input_bytes(problem),
                "exclusive": pilot.exclusive_problem(problem),
                "hack_controls": 4,
                "cpu_distinct_by_family": {"arithmetic": 20 + n, "boundary": 10},
            }
        )
    identity = [{"problem_id": r["problem_id"], "exclusive": r["exclusive"]} for r in rows[:2]]
    return {
        "evaluation_substrates": rows,
        "identity_controls": identity,
        "adversarial_controls": 3,
        "hack_emulating_mutant_controls": 5,
    }


def test_store_projection_leaves_inline_projection_and_charges_references() -> None:
    fits = {g: {"alpha": 1.0, "beta": 10.0} for g in trim.SCORING_GATES}
    rule = {**trim.TRIM_RULE, "frr_min_units": 1, "frr_margin_units": 0}
    base = cc.project_trimmed(_counts(), fits, survival=1.0, rule=rule)
    assert base["reference_store"] is None
    pairs, refs = _pairs_and_refs()
    model = cc.fit_store_model(pairs, refs)
    per_bucket = cc.project_trimmed(_counts(), fits, survival=1.0, rule=rule, store=model)
    per_job = cc.project_trimmed(
        _counts(), fits, survival=1.0, rule=rule, store=model, store_mode="per-job"
    )
    assert per_bucket["kernels"] == base["kernels"]
    assert per_bucket["reference_store"]["reference_groups"] > 0
    assert per_bucket["gpu_hours_by_role"]["reference-items"] > 0
    # cheaper consumers outweigh the references here, and one job shares them more
    assert per_job["gpu_hours"] <= per_bucket["gpu_hours"] < base["gpu_hours"]
    assert (
        per_job["reference_store"]["reference_groups"]
        <= per_bucket["reference_store"]["reference_groups"]
    )
    # L1/19 (6.4 GB) is out of scope: its FRR substrate stays inline
    assert per_bucket["reference_store"]["kernel_replicates_inline"] >= 1
    with pytest.raises(ValueError):
        cc.project_trimmed(_counts(), fits, survival=1.0, rule=rule, store=model, store_mode="x")


def test_reference_rows_are_loaded_and_charged_with_scoring_rows(tmp_path) -> None:
    q1 = tmp_path / "q1"
    (q1 / "repilot").mkdir(parents=True)
    (q1 / "phases.json").write_text(json.dumps({"phases": []}))

    def row(kernel: str, gate: str, start: float, end: float) -> dict:
        return {
            "kernel_id": kernel,
            "gate": gate,
            "config_id": "x",
            "verdict": "accept",
            "attempt": 1,
            "details": {
                "item_key": f"{kernel}|{gate}|seed-42",
                "item_started_at": start,
                "item_ended_at": end,
                "item_wall_seconds": end - start,
                "item_final": True,
            },
        }

    (q1 / "repilot" / "journal.jsonl").write_text(json.dumps(row("k", "c", 0.0, 10.0)) + "\n")
    (q1 / "repilot" / "references.jsonl").write_text(
        json.dumps(row("reference.L1-19_ReLU", "ref_c", 0.0, 10.0)) + "\n"
    )
    job = cc.load_job(q1)
    charged = {i["gate"]: i["gpu_seconds"] for i in job["items"]}
    assert charged == {"c": 5.0, "ref_c": 5.0}


def test_constant_ratio_and_free_reference_variants() -> None:
    pairs, refs = _pairs_and_refs()
    pairs.append({**pairs[0], "gate": "c", "inline": 100.0, "store": 1.0, "same_mode": False})
    model = cc.fit_store_model(pairs, refs, ratio_mode="constant")
    rows = [p for p in pairs if p["gate"] == "c" and p.get("same_mode", True)]
    expected = sum(p["store"] for p in rows) / sum(p["inline"] for p in rows)
    assert model.ratio("c", 0.1) == pytest.approx(expected) == model.ratio("c", 0.5)
    assert model.ratio("b1", 0.1) == 1.0
    free = cc.fit_store_model(pairs, refs, ratio_mode="constant", free_references=True)
    assert free.reference_seconds(0.3) == 0.0 and model.reference_seconds(0.3) > 0
    with pytest.raises(ValueError):
        cc.fit_store_model(pairs, refs, ratio_mode="other")
