"""Pilot selection rule and scoring schedule (pure Python)."""

from __future__ import annotations

from harness.q1 import pilot


def _s1(problem_id: str, half: str) -> dict[str, str]:
    return {
        "substrate_id": f"s1-inductor-{problem_id.replace('/', '-')}",
        "problem_id": problem_id,
        "source_kind": "inductor",
        "split_half": half,
    }


def _s2(substrate_id: str, problem_id: str, kind: str) -> dict[str, str]:
    return {
        "substrate_id": substrate_id,
        "problem_id": problem_id,
        "source_kind": kind,
        "split_half": "evaluation",
    }


CANDIDATES = (
    [_s1(f"L1/{n}_Op{n}", "evaluation") for n in (1, 2, 3, 4)]
    + [_s1(pid, "evaluation") for pid in ("L1/19_ReLU", "L1/25_Swish", "L1/26_GELU_")]
    + [_s1(f"L2/{n}_Fused{n}", "evaluation") for n in range(1, 6)]
    + [_s1(f"L1/{n}_Cal{n}", "calibration") for n in range(40, 45)]
    + [_s1(f"L2/{n}_CalFused{n}", "calibration") for n in range(40, 45)]
    + [
        _s2("s2-flaggems-relu-L1-19_ReLU", "L1/19_ReLU", "flaggems"),
        _s2("s2-flaggems-gelu-L1-26_GELU_", "L1/26_GELU_", "flaggems"),
        _s2("s2-liger-rms-norm-L1-36_RMSNorm_", "L1/36_RMSNorm_", "liger"),
        _s2("s2-tutorial-fused-softmax-L1-23_Softmax", "L1/23_Softmax", "triton-tutorial"),
    ]
)


def test_selection_fills_every_stratum_in_key_order() -> None:
    result = pilot.select_pilot(CANDIDATES)
    assert len(result["evaluation"]) == 8 and len(result["calibration"]) == 4
    assert len(set(result["evaluation"])) == 8
    by_name = {row["stratum"]: row for row in result["strata"]}
    for stratum in pilot.STRATA:
        members = [c for c in CANDIDATES if stratum.predicate(c)]
        expected = sorted(members, key=lambda c: pilot.pilot_key(c["substrate_id"]))
        chosen = by_name[stratum.name]["chosen"]
        if stratum.name != "s2-any":
            assert chosen == [c["substrate_id"] for c in expected[: stratum.count]]
    activation = by_name["s1-eval-l1-activation"]["chosen"][0]
    assert activation.split("-", 2)[2].replace("-", "/", 1) in {
        "L1/19_ReLU",
        "L1/25_Swish",
        "L1/26_GELU_",
    }


def test_selection_is_order_independent_and_skips_ineligible() -> None:
    first = pilot.select_pilot(CANDIDATES)
    again = pilot.select_pilot(list(reversed(CANDIDATES)))
    assert first == again
    dropped = first["evaluation"][0]
    replaced = pilot.select_pilot(CANDIDATES, eligible=lambda c: c["substrate_id"] != dropped)
    assert dropped not in replaced["evaluation"]
    row = replaced["strata"][0]
    assert row["replaced_ineligible"] == [dropped] and len(row["chosen"]) == 1


def test_order_mutants_round_robins_families() -> None:
    mutants = [
        {"kernel_id": f"m-{family}-{i}", "family": family}
        for family in ("precision", "arithmetic", "boundary")
        for i in range(3)
    ]
    ordered = pilot.order_mutants(mutants)
    assert [m["family"] for m in ordered[:3]] == ["arithmetic", "boundary", "precision"]
    assert len(ordered) == 9


def test_schedule_tiers_and_kernel_contiguity() -> None:
    subs = [
        {"kernel_id": f"s{i}", "kernel_path": f"/c/s{i}/kernel.py", "problem_id": "L1/1_Op1"}
        for i in range(2)
    ]
    controls = {
        "s0": [{"kernel_id": "s0.hack.a", "kernel_path": "/x", "problem_id": "L1/1_Op1"}],
        "s1": [],
    }
    mutants = {
        "s0": [
            {
                "kernel_id": f"s0.m{i}",
                "kernel_path": "/m",
                "problem_id": "L1/1_Op1",
                "family": "arithmetic",
            }
            for i in range(2)
        ],
        "s1": [],
    }
    plan = pilot.schedule(subs, controls, mutants, gates=("a", "b1"))
    tiers = [item.tier for item in plan]
    assert tiers == sorted(tiers, key=lambda t: int(t[1]))
    assert [i.kernel_id for i in plan if i.tier == "P0"] == ["s0", "s0", "s1", "s1"]
    assert {i.seed for i in plan if i.tier == "P3"} == {43, 44}
    first, second = (m["kernel_id"] for m in pilot.order_mutants(mutants["s0"]))
    assert [i.kernel_id for i in plan if i.tier == "P2"] == [first, first]
    assert [i.kernel_id for i in plan if i.tier == "P4"] == [second, second]
    keys = [(i.kernel_id, i.gate, i.seed) for i in plan]
    assert len(keys) == len(set(keys))
