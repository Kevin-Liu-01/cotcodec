"""The K1 successor's registered budget formula (pure Python, no torch)."""

from __future__ import annotations

import math

import pytest

from harness import sparse_indexer_k1_budget_v2 as budget


def rates(**overrides: float) -> budget.Rates:
    base = budget.scenario_rates("central").as_dict()
    return budget.Rates(**{**base, **overrides})


def test_registered_layout_is_v1s() -> None:
    pytest.importorskip("torch")
    from harness.sparse_indexer_k1_runtime import Profile

    profile = Profile.registered()
    assert budget.MAIN_STEPS == profile.steps == 610 and budget.BATCH == profile.batch == 4
    assert profile.checkpoint_every == budget.CHECKPOINT_EVERY
    assert budget.EXTENSION_STEPS == 2 * budget.MAIN_STEPS
    assert [list(s) for s in budget.SHARDS] == [list(range(0, 8)), list(range(8, 15)),
                                                list(range(15, 22)), list(range(22, 28))]
    assert budget.PROJECTION_MARGIN == 1.2 and budget.SIGNAL_LEAD_MINUTES == 3.0
    assert budget.MAIN_ALLOWANCE_S == 300.0  # v1's registered start-up allowance


def test_unit_mixes_are_the_bundle_metadata_counts() -> None:
    # program/evidence/2026-10-07/q3-k1/smoke-452/run-root-timestamps.txt
    assert budget.AUDIT_MIX.selection_units == 8710
    assert budget.AUDIT_MIX.select_only + budget.AUDIT_MIX.select_mc + budget.AUDIT_MIX.mc_only \
        == 9010
    assert round(budget.AUDIT_MIX.mean_rows, 1) == 33.2
    assert budget.DEV_MIX.select_only + budget.DEV_MIX.select_mc + budget.DEV_MIX.mc_only == 1000
    assert round(budget.DEV_MIX.mean_rows, 1) == 38.6


def test_checkpoint_save_counts() -> None:
    assert budget.checkpoint_saves(0, 610) == 7  # 100..600 and the final
    assert budget.checkpoint_saves(610, 1830) == 13  # 700..1800 and the final
    assert budget.checkpoint_saves(0, 40, 10) == 4
    assert budget.checkpoint_saves(25, 40, 10) == 2


def test_main_projection_is_the_binding_worker_plus_evaluation() -> None:
    r = rates()
    projection = budget.project_main(r)
    steps = [budget.shard_step_s(r, layers) for layers in budget.SHARDS]
    expected_train = max(610 * s + 7 * len(layers) * r.save_layer_s
                         for s, layers in zip(steps, budget.SHARDS, strict=True))
    assert projection["train_s"] == pytest.approx(expected_train)
    expected_eval = (3650 * r.eval_select_s + 5060 * r.eval_select_mc_s
                     + 300 * r.eval_mc_only_s) / 4
    assert projection["eval_s"] == pytest.approx(expected_eval)
    assert projection["wall_s"] == pytest.approx(
        300 + 2 * r.train_startup_s + r.eval_startup_s + 28 * r.save_layer_s
        + projection["train_s"] + projection["devkl_s"] + expected_eval)


def test_the_evaluation_checkpoint_read_is_priced_apart_from_start_up() -> None:
    # An evaluation worker reads the 28-layer generation before its first unit;
    # the probe loads nothing and the smoke times the read apart, so both price
    # it at the save rate (review finding: it was in the smoke's start-up only).
    r = rates()
    assert budget.eval_load_s(r) == pytest.approx(budget.LAYERS * r.save_layer_s)
    for job in ("main", "extension", "smoke"):
        projection = budget.project(r, job)
        assert projection["eval_load_s"] == pytest.approx(budget.eval_load_s(r))
        heavier = budget.project(rates(save_layer_s=r.save_layer_s * 2), job)
        assert heavier["wall_s"] > projection["wall_s"]
    assert "eval_load_s" not in budget.project(r, "headroom-dev")  # dense only, nothing read


def test_the_gauntlet_total_sums_every_cap_and_every_probe_run(monkeypatch) -> None:
    derived = budget.derive_limits(rates())
    caps = sum(entry["max_gpu_hours"] for entry in derived["jobs"].values())
    assert derived["jobs"]["extension"]["max_gpu_hours"] > 0  # counted at its worst case
    assert derived["total_gpu_hours_with_probe"] == round(caps + budget.PROBE_GPU_HOURS, 2)
    assert derived["probe_runs_gpu_hours"] == {"q3-k1-throughput-probe-v1": 0.15}
    assert "expected use never replaces a cap" in derived["counting_rule"]
    # A second probe run (a rerun under a new id) adds its whole cap.
    monkeypatch.setitem(budget.PROBE_RUNS_GPU_HOURS, "q3-k1-throughput-probe-v2", 0.15)
    again = budget.derive_limits(rates())
    assert again["total_gpu_hours_with_probe"] == round(caps + 0.30, 2)
    assert budget.limits_table(again) == budget.limits_table(derived)


def test_rows_factor_scales_up_never_down() -> None:
    short = rates(eval_rows=20.0)
    long = rates(eval_rows=60.0)
    assert budget.eval_s(short, budget.AUDIT_MIX) > budget.eval_s(rates(eval_rows=33.3),
                                                                  budget.AUDIT_MIX)
    assert budget.eval_s(long, budget.AUDIT_MIX) == pytest.approx(
        budget.eval_s(rates(eval_rows=33.3), budget.AUDIT_MIX))


def test_extension_projection_trains_six_indexers_for_two_epochs() -> None:
    r = rates()
    projection = budget.project_extension(r)
    expected = max(1220 * budget.shard_step_s(r, layers, extension=True)
                   + 14 * len(layers) * r.save_layer_s for layers in budget.SHARDS)
    assert projection["train_s"] == pytest.approx(expected)
    assert "devkl_s" not in projection  # the extension re-reads, it does not re-freeze


def test_limit_rule_and_caps() -> None:
    assert budget.limit_minutes(0.0) == budget.MIN_LIMIT_MINUTES
    wall = 25.0 * 60
    assert budget.limit_minutes(wall) == math.ceil(1.2 * 1.15 * 25.0 + 3.0)
    assert budget.gpu_hours(4, 39) == 2.6 and budget.gpu_hours(1, 11) == 0.19
    # The registered limit always leaves the smoke the 15 percent headroom.
    for minutes in (3.0, 17.3, 41.1):
        limit = budget.limit_minutes(minutes * 60)
        assert budget.required_minutes(minutes * 60 * 1.15) <= limit + 1e-9


def test_resume_legs_finish_or_hold_before_usr1() -> None:
    r = rates()
    for leg in ("resume-r0", "resume-r1", "resume-r2"):
        projection = budget.project_resume(r, leg)
        limit = budget.limit_minutes(projection["wall_s"])
        assert limit - budget.SIGNAL_LEAD_MINUTES >= 1.2 * projection["wall_s"] / 60
    r0 = budget.project_resume(r, "resume-r0")["train_s"]
    r1 = budget.project_resume(r, "resume-r1")["train_s"]
    assert r0 > r1  # R1 only needs to reach the hold at step 25
    with pytest.raises(budget.BudgetContractError, match="four-workers-per-GPU"):
        budget.project_resume(budget.Rates(**{**r.as_dict(), "concurrent_step_s": None}),
                              "resume-r0")


def test_scenarios_central_fits_and_conservative_needs_the_gauntlet() -> None:
    central = budget.derive_limits(budget.scenario_rates("central"))
    conservative = budget.derive_limits(budget.scenario_rates("conservative"))
    batching = budget.derive_limits(budget.scenario_rates("batching-only"))
    assert not central["gauntlet_required"] and central["total_gpu_hours_with_probe"] < 8.0
    assert conservative["gauntlet_required"] and conservative["total_gpu_hours_with_probe"] > 8.0
    assert batching["total_gpu_hours_with_probe"] > conservative["total_gpu_hours_with_probe"]
    for derived in (central, conservative):
        assert {job for job, _ in budget.JOBS} == set(derived["jobs"])
        for job, gpus in budget.JOBS:
            entry = derived["jobs"][job]
            assert entry["max_gpu_hours"] == budget.gpu_hours(gpus, entry["minutes"])


def test_smoke_gate_checks_main_and_extension() -> None:
    probe = rates()
    limits = budget.limits_table(budget.derive_limits(probe))
    assert budget.smoke_gate(probe, limits)["passed"]
    # A smoke 14 percent slower than the probe still fits; one 30 percent slower does not.
    slower = rates(layer_step_s=probe.layer_step_s * 1.14,
                   layer_step_ext_s=probe.layer_step_ext_s * 1.14,
                   eval_select_s=probe.eval_select_s * 1.14,
                   eval_select_mc_s=probe.eval_select_mc_s * 1.14)
    assert budget.smoke_gate(slower, limits)["passed"]
    much = rates(layer_step_ext_s=probe.layer_step_ext_s * 1.6)
    gate = budget.smoke_gate(much, limits)
    assert not gate["passed"] and gate["main"]["fits"] and not gate["extension"]["fits"]


def test_limits_table_validation() -> None:
    limits = budget.limits_table(budget.derive_limits(rates()))
    assert budget.check_limits(limits) == limits
    broken = {**limits, "main": {"minutes": 39, "max_gpu_hours": 9.0}}
    with pytest.raises(budget.BudgetContractError, match="max_gpu_hours"):
        budget.check_limits(broken)
    with pytest.raises(budget.BudgetContractError, match="no registered limit"):
        budget.check_limits({k: v for k, v in limits.items() if k != "extension"})
    with pytest.raises(budget.BudgetContractError, match="integer"):
        budget.check_limits({**limits, "smoke": {"minutes": 7.5, "max_gpu_hours": 0.13}})


def test_continuation_rule_and_rates_validation() -> None:
    assert budget.continuation_minutes(39, 20) == 19
    assert budget.continuation_minutes(39, 35) is None
    with pytest.raises(budget.BudgetContractError):
        rates(layer_step_s=float("nan"))
    with pytest.raises(budget.BudgetContractError, match="unknown"):
        budget.Rates.from_dict({**rates().as_dict(), "speedup": 2.0})
