"""Ladder composition and Stage 0 metrics on synthetic journal rows (needs scipy)."""

from __future__ import annotations

import pytest

pytest.importorskip("scipy")

from harness.q1 import analysis  # noqa: E402
from harness.q1.schema import make_verdict_row  # noqa: E402

UNREFEREEABLE = "unref"  # family/channel verdict meaning "no admissible configuration or draw"


def _row(
    kernel: str,
    gate: str,
    verdict: str,
    config: str = "native/seed-42",
    policy: str = "torch-default",
    gpu: float = 1.0,
    item: str | None = None,
    details: dict | None = None,
    seed: int = 42,
) -> dict:
    return make_verdict_row(
        kernel_id=kernel,
        gate=gate,
        config_id=config,
        verdict=verdict,
        tf32_policy=policy,
        gpu_seconds=gpu,
        details={"item_key": f"{kernel}|{item or gate}|seed-{seed}", **(details or {})},
        seed=seed,
    )


def _c_aggregate(kernel: str, family: str, verdict: str) -> dict:
    if verdict == UNREFEREEABLE:
        details = {"configs": 2, "admissible": 0, "reason": "no-admissible-config"}
        verdict = "error"
    else:
        details = {"configs": 2, "admissible": 2}
    return _row(kernel, family, verdict, "aggregate", item="c", gpu=2.0, details=details)


def _audit_aggregate(kernel: str, channel: str, verdict: str, policy: str) -> dict:
    counts = {
        "pass": 0,
        "silent-wrong": 0,
        "crash-after-launch": 0,
        "refusal-before-launch": 0,
        "inadmissible": 0,
    }
    if verdict == UNREFEREEABLE:
        counts["inadmissible"] = 5
        verdict = "error"
    else:
        counts[
            {
                "accept": "pass",
                "reject": "silent-wrong",
                "refuse": "refusal-before-launch",
                "error": "inadmissible",
            }[verdict]
        ] = 5
    return _row(
        kernel, channel, verdict, "aggregate", policy, details={"policy": policy, "counts": counts}
    )


def _kernel(kernel: str, gates: dict[str, str], audit: dict[str, str]) -> list[dict]:
    rows = [_row(kernel, g, gates[g]) for g in ("a", "b1", "b2") if g in gates]
    for family in ("c1", "c2", "c3", "c_1e-2", "c_kbv_raw"):
        rows.append(_c_aggregate(kernel, family, gates.get(family, "accept")))
    for channel in ("A1", "A2", "A3"):
        for policy in analysis.POLICIES:
            rows.append(_audit_aggregate(kernel, channel, audit.get(channel, "accept"), policy))
    rows.append(_row(kernel, "A4", audit.get("A4", "accept"), "in-process", "not-applicable"))
    return rows


def _entry(kind: str, problem: str, **facts) -> dict:
    base = {
        "kind": kind,
        "problem_id": problem,
        "family": None,
        "rule_origin": None,
        "parent_substrate_id": None,
        "weight": None,
        "source_kind": "inductor",
        "source_tier": "S1",
        "kernel_family": f"inductor:{problem}",
        "control_kind": None,
        "expected": {},
        "split": None,
    }
    return {**base, **facts}


GOOD = {"a": "accept", "b1": "accept", "b2": "accept"}


def test_ladder_and_tiers() -> None:
    rows = _kernel(
        "m1", {"a": "accept", "b1": "error", "b2": "accept", "c2": "reject"}, {"A3": "reject"}
    )
    rows += _kernel("m2", dict(GOOD), {"A3": "refuse"})
    rows.append(_row("m3", "a", "timeout", "item/seed-42"))
    composed = analysis.compose(rows)
    m1 = composed["m1"]
    assert m1["ladder"]["b"] == "accept" and m1["b_fail_open"] == ["b1"]
    assert m1["ladder"]["c"] == "reject"
    assert m1["tiers"]["tf32-admissible"]["G"] == "reject"
    m2 = composed["m2"]["tiers"]["tf32-admissible"]
    assert m2["G"] == "accept" and m2["G-strict"] == "reject"
    assert composed["m3"]["ladder"]["a"] == "reject"  # a timeout is a rejection


def _corpus(n_mutants: int = 10) -> tuple[list[dict], dict]:
    """One correct parent per problem; mutants of it; c catches every mutant a misses half of."""
    rows, table = [], {}
    for p in range(3):
        parent = f"sub{p}"
        table[parent] = _entry("substrate", f"L1/{p}_P")
        rows += _kernel(parent, dict(GOOD), {})
    for i in range(n_mutants):
        kernel = f"mut{i}"
        table[kernel] = _entry(
            "mutant",
            f"L1/{i % 3}_P",
            family="boundary",
            rule_origin="paper",
            parent_substrate_id=f"sub{i % 3}",
            weight=2.0,
        )
        a = "accept" if i < 4 else "reject"
        rows += _kernel(kernel, {**GOOD, "a": a, "c1": "reject"}, {"A1": "reject"})
    return rows, table


def test_metrics_ms_far_frr() -> None:
    rows, table = _corpus()
    rows += _kernel("sub9", {**GOOD, "c3": "reject"}, {})  # correct substrate gate c rejects
    table["sub9"] = _entry("substrate", "L1/9_P")
    result = analysis.metrics(analysis.compose(rows), table, resamples=200)
    assert result["counts"]["witnessed"] == 10 and result["counts"]["correct_substrates"] == 4
    a, c = result["gates"]["a"], result["gates"]["c"]
    assert a["MS"]["k"] == 6 and a["FAR"] == pytest.approx(0.4)
    assert c["MS"]["rate"] == 1.0 and c["MS_weighted"]["rate"] == 1.0
    assert a["MS_weighted"]["rate"] == pytest.approx(0.6)
    assert c["FRR"]["k"] == 1 and a["FRR"]["k"] == 0
    assert c["FRR_independent"]["k"] == 1 and c["FRR_independent"]["n"] == 4
    assert a["FA_share_uninterpreted"]["rate"] == 1.0
    assert result["MS_by_family"]["boundary"]["a"]["k"] == 6
    assert result["MS_by_origin"]["paper"]["c"]["k"] == 10
    assert result["MS_by_source_tier"]["S1"]["c"]["n"] == 10
    paired = result["paired_differences"]["MS_c-MS_a"]
    assert paired["n"] == 10 and paired["hi_only"] == 4 and paired["lo_only"] == 0
    assert paired["difference"] == pytest.approx(0.4)
    crit = result["criterion_3_FRR_c"]
    assert crit["n"] == 4 and not crit["evaluable"] and not crit["holds"]


def test_parent_filter_drops_mutants_of_a_faulty_parent() -> None:
    """Review finding: a parent's own fault must not make its mutants 'witnessed'."""
    rows, table = [], {}
    # The parent fails the audit at held-out shapes (A3) and gate c sees the same fault (c3).
    faulty = {**GOOD, "c3": "reject"}
    rows += _kernel("parent", faulty, {"A3": "reject"})
    table["parent"] = _entry("substrate", "L1/1_P")
    rows += _kernel("mutant", faulty, {"A3": "reject"})  # a no-op mutation of it
    table["mutant"] = _entry("mutant", "L1/1_P", family="arithmetic", parent_substrate_id="parent")
    result = analysis.metrics(analysis.compose(rows), table, resamples=0)
    assert result["counts"]["mutants_scored"] == 0 and result["counts"]["witnessed"] == 0
    assert result["counts"]["mutants_excluded"] == {"parent-reject": 1}
    assert result["gates"]["c"]["MS"]["n"] == 0 and result["gates"]["a"]["MS"]["n"] == 0


def test_s1_calibration_parents_are_out_of_primary_scope() -> None:
    rows, table = _corpus(6)
    result = analysis.metrics(
        analysis.compose(rows), table, mutant_parents={"sub0", "sub1"}, resamples=0
    )
    assert result["counts"]["mutants_scored"] == 4
    assert result["counts"]["mutants_excluded"] == {"parent-out-of-scope": 2}


def test_unrefereeable_family_is_vacuous_not_outcome_dependent() -> None:
    """Review finding: with c3 unrefereeable for the problem, c must not be 'error' only
    for the kernels c1 accepts (L1/100 HingeLoss)."""
    rows, table = [], {}
    rows += _kernel("parent", {**GOOD, "c3": UNREFEREEABLE}, {})
    table["parent"] = _entry("substrate", "L1/100_HingeLoss")
    caught = {**GOOD, "a": "accept", "c1": "reject", "c3": UNREFEREEABLE}
    missed = {**GOOD, "a": "accept", "c3": UNREFEREEABLE}
    for name, gates in (("caught", caught), ("missed", missed)):
        rows += _kernel(name, gates, {"A2": "reject"})
        table[name] = _entry(
            "mutant", "L1/100_HingeLoss", family="semantic", parent_substrate_id="parent"
        )
    problem_of = {k: v["problem_id"] for k, v in table.items()}
    composed = analysis.compose(rows, problem_of=problem_of)
    assert composed["missed"]["ladder"]["c"] == "accept"
    assert composed["caught"]["ladder"]["c"] == "reject"
    assert composed["parent"]["ladder"]["c"] == "accept"
    assert composed["missed"]["vacuous"] == {"c": ["c3"]}
    result = analysis.metrics(composed, table, resamples=0)
    assert result["gates"]["c"]["MS"]["k"] == 1 and result["gates"]["c"]["MS"]["n"] == 2
    assert result["gates"]["c"]["FRR"]["n"] == 1


def test_unrefereeable_audit_channel_is_vacuous() -> None:
    rows = _kernel("sub", dict(GOOD), {"A2": UNREFEREEABLE})
    rows += _kernel("bad", dict(GOOD), {"A2": UNREFEREEABLE, "A1": "reject"})
    composed = analysis.compose(rows, problem_of={"sub": "L1/1_P", "bad": "L1/1_P"})
    assert composed["sub"]["tiers"]["tf32-admissible"]["G"] == "accept"
    assert composed["bad"]["tiers"]["tf32-admissible"]["G"] == "reject"
    assert composed["sub"]["vacuous"]["tf32-admissible"] == ["A2"]


def test_refereeability_disagreement_is_listed_and_not_vacuous() -> None:
    rows = _kernel("k1", {**GOOD, "c3": UNREFEREEABLE}, {})
    rows += _kernel("k2", dict(GOOD), {})
    table = {"k1": _entry("substrate", "L1/7_P"), "k2": _entry("substrate", "L1/7_P")}
    composed = analysis.compose(rows, problem_of={"k1": "L1/7_P", "k2": "L1/7_P"})
    assert composed["k1"]["ladder"]["c"] == "error"  # not silently vacuous for k1 alone
    report = analysis.refereeability_report(composed, table)
    assert report["anomalies"][0]["unrefereeable_for"] == ["k1"]


def test_every_gate_uses_the_kernels_a_b_and_c_referee() -> None:
    rows, table = _corpus(4)
    rows = [r for r in rows if not (r["kernel_id"] == "mut0" and r["gate"] == "a")]
    composed = analysis.compose(rows)
    assert composed["mut0"]["ladder"]["a"] == "error"
    result = analysis.metrics(composed, table, resamples=0)
    assert result["counts"]["witnessed"] == 4
    assert result["counts"]["witnessed_refereed_by_a_b_c"] == 3
    assert result["gates"]["c"]["MS"]["n"] == 3 and result["gates"]["a"]["MS"]["n"] == 3


def test_cluster_map_links_problems_of_one_kernel_family() -> None:
    table = {
        "s2-mm-a": _entry("substrate", "L1/1_A", source_kind="flaggems", kernel_family="fg:mm"),
        "s2-mm-b": _entry("substrate", "L1/2_B", source_kind="flaggems", kernel_family="fg:mm"),
        "s1-c": _entry("substrate", "L1/3_C"),
    }
    clusters = analysis.cluster_map(table)
    assert clusters["L1/1_A"] == clusters["L1/2_B"] == "L1/1_A"
    assert clusters["L1/3_C"] == "L1/3_C"


def test_independent_frr_counts_a_family_once() -> None:
    rows, table = [], {}
    for name, problem, c in (("fa", "L1/1_A", "reject"), ("fb", "L1/2_B", "accept")):
        rows += _kernel(name, {**GOOD, "c2": c}, {})
        table[name] = _entry(
            "substrate", problem, source_kind="flaggems", source_tier="S2", kernel_family="fg:mm"
        )
    result = analysis.metrics(analysis.compose(rows), table, resamples=0)
    assert result["gates"]["c"]["FRR"]["k"] == 1 and result["gates"]["c"]["FRR"]["n"] == 2
    independent = result["gates"]["c"]["FRR_independent"]
    assert independent["k"] == 1 and independent["n"] == 1 and independent["clusters"] == 1


def test_precision_only_class() -> None:
    rows = _kernel("p", dict(GOOD), {"A1": "reject"})
    for row in rows:
        if row["gate"] == "A1":
            row["details"]["silent_wrong_all_within_64T"] = True
    composed = analysis.compose(rows)
    assert composed["p"]["precision_only"] == {"tf32-admissible": True, "strict-fp32": True}


def test_cost_ratio_marginal_and_amortized() -> None:
    rows = _kernel("k", dict(GOOD), {})
    rows.append(_row("k", "c_extra", "accept", "x", gpu=0.0, item="c"))
    retried = _row("k", "a", "error", "item/seed-42", gpu=5.0, details={"reason": "infra_failure"})
    summary = analysis.cost(rows, [*rows, retried])
    assert summary["ladder"]["b_median"] == pytest.approx(3.0)
    assert summary["ladder"]["c_median"] == pytest.approx(13.0)  # five c rows of 2.0 GPU-s
    assert summary["marginal"]["c"]["median"] == pytest.approx(10.0)
    assert summary["amortized"]["a"]["per_kernel"] == pytest.approx(6.0)  # retry included


def test_splits_are_seeded_and_disjoint() -> None:
    problems = [f"L1/{i}_P" for i in range(9)]
    cal, ev = analysis.calibration_split(problems)
    assert len(cal) == 5 and len(ev) == 4 and not set(cal) & set(ev)
    assert analysis.calibration_split(reversed(problems)) == (cal, ev)
    frozen = analysis.s1_split()
    assert analysis.calibration_split() == (frozen["calibration"], frozen["evaluation"])
    assert len(frozen["calibration"]) == 98 and len(frozen["evaluation"]) == 98
    table = {f"m{i}": {"kind": "mutant", "split": "dev" if i % 3 else "test"} for i in range(7)}
    table["s"] = {"kind": "substrate", "split": None}
    dev, test = analysis.mutant_split(table)
    assert len(dev) == 4 and len(test) == 3 and not set(dev) & set(test)


def test_substrate_halves() -> None:
    split = analysis.s1_split()
    cal, ev = split["calibration"][0], split["evaluation"][0]
    table = {
        "s1-cal": _entry("substrate", cal),
        "s1-eval": _entry("substrate", ev),
        "s2": _entry("substrate", cal, source_kind="liger", source_tier="S2"),
    }
    halves = analysis.substrate_halves(table, split)
    assert halves == {"evaluation": {"s1-eval", "s2"}, "calibration": {"s1-cal"}}


def test_audit_hole_candidates_and_summary() -> None:
    rows = _kernel("k", {**GOOD, "a": "reject", "c3": "reject"}, {})
    for row in rows:
        if row["gate"] == "a":
            row["details"].update({"failed_trials": [1, 3], "reason": "output-mismatch"})
    rows.append(
        _row("k", "c3", "reject", "c3/U1/n/D1/seed-3042", item="c", details={"admissible": True})
    )
    rows.append(
        _row("k", "c3", "reject", "c3/U2/n/D1/seed-3043", item="c", details={"admissible": False})
    )
    table = {"k": _entry("substrate", "L1/1_P")}
    composed = analysis.compose(rows)
    found = analysis.audit_hole_candidates(rows, composed, table)
    requests = found["k"]["replay"]
    assert {"gate": "c3", "config_id": "c3/U1/n/D1/seed-3042"} in requests
    assert {"gate": "a", "config_id": "native/seed-42", "trials": [1, 3]} in requests
    assert len(requests) == 2  # the inadmissible configuration is not replayed
    replay = [
        _row(
            "k",
            "audit_hole",
            "accept",
            "c3:c3/U1/n/D1/seed-3042",
            "tf32-admissible",
            details={
                "classification": "false-reject-by-gate",
                "rejecting_gate": "c3",
                "rejecting_config": "c3/U1/n/D1/seed-3042",
            },
        ),
    ]
    summary = analysis.audit_hole_summary(replay, found)
    assert summary["requested"] == 2 and summary["adjudicated"] == 1
    assert summary["unadjudicated"] == 1 and not summary["criterion_4_holds"]
    assert summary["by_rejecting_gate"] == {"c3": {"false-reject-by-gate": 1}}


def test_c_lite_greedy_set_cover() -> None:
    rows, table = [], {}
    rows += _kernel("parent", dict(GOOD), {})
    table["parent"] = _entry("substrate", "L1/1_P")
    covers = {"cfgA": {"m0", "m1"}, "cfgB": {"m2"}, "cfgC": {"m0"}}
    for i in range(3):
        kernel = f"m{i}"
        table[kernel] = _entry("mutant", "L1/1_P", family="boundary", parent_substrate_id="parent")
        rows += _kernel(kernel, {**GOOD, "c1": "reject"}, {"A1": "reject"})
        for config, members in covers.items():
            rows.append(
                _row(
                    kernel,
                    "c1",
                    "reject" if kernel in members else "accept",
                    f"c1/{config}/seed-1042",
                    item="c",
                    gpu=1.0 if config != "cfgB" else 4.0,
                    details={"admissible": True},
                )
            )
    result = analysis.c_lite_set_cover(rows, analysis.compose(rows), table, ["m0", "m1", "m2"])
    assert result["universe"] == 3 and result["covered"] == 3
    assert [s["config"] for s in result["selected"]] == ["c1/cfgA", "c1/cfgB"]


def test_c_rejection_causes_include_crashed_items() -> None:
    rows = [
        _row("k", "c", "reject", "item/seed-42", details={"reason": "worker-crashed"}),
        _row(
            "j",
            "c2",
            "reject",
            "c2/S-half/D1/seed-2042",
            item="c",
            details={"admissible": True, "reason": "candidate-raised"},
        ),
    ]
    causes = analysis.c_rejection_causes(rows)
    assert causes == {"j": {"candidate-raised": 1}, "k": {"worker-crashed": 1}}


def test_control_checks_read_every_gate_kind() -> None:
    rows = _kernel(
        "ctl",
        {"a": "accept", "b1": "reject", "b2": "accept", "c1": "reject"},
        {"A2": "reject", "A3": "refuse"},
    )
    composed = analysis.compose(rows)
    table = {
        "ctl": {
            "kind": "control",
            "control_kind": "hack-emulating-mutant",
            "expected": {
                "a": "accept",
                "b1": "reject",
                "b": "reject",
                "c1": "reject",
                "c": "reject",
                "A3": "refuse",
                "A4": "accept",
                "audit_N": "reject",
                "audit_G_strict": "reject",
                "b_native": "accept",
            },
        },
        "lost": {"kind": "control", "control_kind": "synthetic", "expected": {"a": "reject"}},
    }
    result = analysis.control_checks(composed, table)
    failed = {(cell["control_id"], cell["gate"]): cell["got"] for cell in result["failed"]}
    assert failed == {("ctl", "b_native"): "missing", ("lost", "a"): "missing"}
    assert result["cells"] == 11 and result["held"] == 9 and not result["all_hold"]
