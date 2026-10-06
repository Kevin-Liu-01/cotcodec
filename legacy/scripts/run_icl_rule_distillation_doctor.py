#!/usr/bin/env python3
"""Execute the Direction-19 phase-0 doctor before any pretrained model is touched.

Every number this doctor prints is a synthetic-case number from a 16-d finite-task
prior regression proxy. The receipt proves that the Stage-A code paths execute on a
CPU with NumPy/SciPy only and that the registered gates have the intended semantics
(positive control, shifted negative control, leakage tamper, degenerate-input
rejection, attribution-tree routing and power). It measures nothing about any
pretrained base and carries no novelty or architecture claim.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import scipy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import icl_rule_distillation as icl  # noqa: E402
from harness.icl_rule_distillation import (  # noqa: E402
    PILOT_INTERFACE,
    AttributionInputs,
    AttributionOutcome,
    AttributionThresholds,
    DistillationConfig,
    FiniteTaskPrior,
    InterfaceSpec,
    NoiseModel,
    RegimeDoctorConfig,
    RuleContractError,
    RuleFamily,
    attribution_tree,
    finite_prior_sampler,
    gaussian_prior_sampler,
    negative_control_gates,
    positive_control_gates,
    rank_truncation_doctor,
    rule_parameter_counts,
    run_regime_distillation,
    simulate_attribution_tree_power,
)

DOCTOR_NAME = "icl-rule-distillation-phase0"
DIRECTION = "icl-rule-distillation-port"
EVIDENCE_GRADE = (
    "SYNTHETIC_EXECUTABILITY_AND_GATE_SEMANTICS_ONLY: every number in this receipt is a "
    "synthetic-case number from a 16-d finite-task-prior regression proxy (Raventos et al. "
    "2023 regime); the receipt proves that the Stage-A code paths execute on CPU with "
    "NumPy/SciPy only and that the registered gates have the intended semantics. It is not a "
    "measurement of any pretrained model, does not evaluate the pilot's held-out-family "
    "teacher-fidelity endpoint, and carries no novelty, portability or architecture claim."
)
NUMBERS_ARE = (
    "synthetic-case numbers (16-d state, 4-task prior, 8 demonstrations, hand-written NumPy "
    "rules); they are labelled as such wherever they are quoted"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--draws", type=int, default=4000, help="tree power Monte-Carlo draws")
    args = parser.parse_args(argv)
    if args.draws < 100:
        parser.error("--draws must be at least 100")
    return args


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
            if field.repr
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, InterfaceSpec):
        return dataclasses.asdict(value)
    return value


def _case(description: str, receipt: Any, gates: dict[str, bool]) -> dict[str, Any]:
    return {
        "description": description,
        "receipt": _jsonable(receipt),
        "gates": {name: bool(flag) for name, flag in gates.items()},
        "status": "PASS" if all(gates.values()) else "FAIL",
    }


def case_parameter_counts() -> dict[str, Any]:
    counts = rule_parameter_counts(PILOT_INTERFACE)
    gates = {
        "theta_count_is_101762": counts.theta == 101_762,
        "gradient_form_hidden_is_305": counts.gradient_form_hidden == 305,
        "adaptive_hidden_is_293": counts.adaptive_hidden == 293,
        "linear_count_is_4100": counts.linear == 4_100,
        "gradient_form_and_adaptive_within_one_percent": counts.within_tolerance(),
    }
    receipt = {
        "counts": counts,
        "relative_gaps": counts.relative_gaps(),
        "interface": PILOT_INTERFACE,
    }
    return _case(
        "Parameter-count doctor at the pilot interface (266 inputs, hidden 256, 130 outputs).",
        receipt,
        gates,
    )


def case_rank_truncation(seed: int) -> dict[str, Any]:
    receipt = rank_truncation_doctor(PILOT_INTERFACE, np.random.default_rng(seed))
    gates = {
        "pi_8_inert_for_eight_rank_one_writes_from_zero": receipt.inert_max_abs_change <= 1e-9,
        "pi_8_truncates_the_ninth_write_to_rank_8": (
            receipt.rank_before_truncation == 9 and receipt.rank_after_truncation == 8
        ),
    }
    return _case(
        "Rank/algebra doctor: Pi_8 is a no-op inside an 8-shot episode and acts on a ninth write.",
        receipt,
        gates,
    )


def case_positive_control(config: RegimeDoctorConfig) -> tuple[dict[str, Any], Any]:
    prior = FiniteTaskPrior.random(
        config.n_tasks,
        config.spec.state_dim,
        config.noise_sigma,
        np.random.default_rng(config.seed),
    )
    receipt = run_regime_distillation(
        config, finite_prior_sampler(prior, config.spec, config.n_queries)
    )
    gates = positive_control_gates(receipt, config)
    payload = {
        "config": config,
        "separation": receipt.separation,
        "rules": receipt.rules,
        "ladder_readings": {
            "D(R_theta, R_gf)": receipt.gap(RuleFamily.THETA, RuleFamily.GRADIENT_FORM),
            "D(R_gf, R_lin)": receipt.gap(RuleFamily.GRADIENT_FORM, RuleFamily.LINEAR),
            "D(R_gf, R_adapt)": receipt.gap(RuleFamily.GRADIENT_FORM, RuleFamily.ADAPTIVE),
        },
        "clamp_ablation": receipt.clamp,
        "write_direction_clamp_cost": receipt.clamp.write_direction_cost(),
        "clamp_reproduces_gradient_form": receipt.clamp_reproduces_gradient_form,
        "causality_audit": receipt.audit,
        "parameter_counts": receipt.counts,
    }
    return (
        _case(
            "dMMSE-regime positive control: distil R_theta, R_gf, R_adapt and R_lin to the "
            "discrete Bayes teacher at equal budget; R_theta must track dMMSE while key-directed "
            "rungs stay under the exact key-span ceiling and track ridge; the w-clamp must cost "
            "fidelity.",
            payload,
            gates,
        ),
        receipt,
    )


def case_negative_control(config: RegimeDoctorConfig, positive: Any) -> dict[str, Any]:
    overrides = {
        family: positive.rules[family.value].selected_learning_rate
        for family in (RuleFamily.THETA, RuleFamily.GRADIENT_FORM)
    }
    receipt = run_regime_distillation(
        config,
        gaussian_prior_sampler(config.spec, config.noise_sigma, config.n_queries),
        (RuleFamily.THETA, RuleFamily.GRADIENT_FORM),
        overrides,
    )
    gates = negative_control_gates(receipt, config)
    theta = receipt.rules[RuleFamily.THETA.value]
    gf = receipt.rules[RuleFamily.GRADIENT_FORM.value]
    payload = {
        "separation": receipt.separation,
        "rules": receipt.rules,
        "optimisation_only_gap_reported_not_attributed": (
            theta.fidelity_to_teacher - gf.fidelity_to_teacher
        ),
        "learning_rates_carried_from_positive_control_without_research": _jsonable(overrides),
    }
    return _case(
        "Gaussian-prior negative control (infinite-task limit; teacher = ridge, inside the key "
        "span, so the gradient-form null is true by construction): the regime statistic must "
        "refuse to separate the classes and any trained gap is reported as optimisation-only.",
        payload,
        gates,
    )


def case_permuted_teacher(positive: Any) -> dict[str, Any]:
    receipt = {name: rule.fidelity_to_permuted_teacher for name, rule in positive.rules.items()}
    gates = {
        "every_rule_fidelity_to_permuted_teacher_at_most_0.05": all(
            value <= 0.05 for value in receipt.values()
        ),
        "tree_cannot_confirm_on_permuted_gap": (
            receipt[RuleFamily.THETA.value] - receipt[RuleFamily.GRADIENT_FORM.value] < 0.10
            or receipt[RuleFamily.THETA.value] <= 0.05
        ),
    }
    return _case(
        "Shifted/permuted control: the teacher's predictions are permuted across probes within "
        "each episode, destroying the query-content link; fidelity must collapse for every rule.",
        receipt,
        gates,
    )


def case_causality(positive: Any) -> dict[str, Any]:
    audit = positive.audit
    gates = {
        "probe_absence_identical": audit.probe_absence_identical,
        "prefix_invariant": audit.prefix_invariant,
        "zero_state_read_is_zero": audit.zero_state_read_is_zero,
        "reset_restores_fresh_state": audit.reset_restores_fresh_state,
        "tampered_pass_detected": audit.tampered_pass_detected,
    }
    return _case(
        "Two-pass causality audit on the trained R_theta: probes never enter Pass W, probes do not "
        "interact in Pass R, M = 0 reads exactly zero, reset restores the fresh state; the tamper "
        "case leaks one probe into Pass W as a ninth demonstration and must be detected.",
        audit,
        gates,
    )


def _inputs(
    gaps: list[float],
    class_mask: list[bool],
    *,
    clamp: float = 0.08,
    sibling: float | None = 0.08,
    reservoir: float = 0.3,
    audits: bool = True,
) -> AttributionInputs:
    return AttributionInputs(
        np.asarray(gaps), np.asarray(class_mask), clamp, sibling, reservoir, audits
    )


def case_attribution_tree(seed: int, draws: int) -> dict[str, Any]:
    strong = [0.16, 0.14, 0.15, 0.13, 0.17, 0.15, 0.14, 0.16]
    four_class = [True, True, True, True, False, False, False, False]
    three_class = [True, True, True, False, False, False, False, False]
    class_miss = [0.02, 0.01, 0.03, 0.02, 0.24, 0.26, 0.25, 0.27]
    scenarios: dict[str, tuple[AttributionInputs, AttributionOutcome]] = {
        "confirmed": (_inputs(strong, four_class), AttributionOutcome.CONFIRMED),
        "class_miss_is_class_unresolved_not_k1": (
            _inputs(class_miss, four_class),
            AttributionOutcome.CLASS_UNRESOLVED,
        ),
        "fewer_than_four_class_families_is_unmeasurable": (
            _inputs(strong, three_class),
            AttributionOutcome.CLASS_UNRESOLVED,
        ),
        "clamp_below_0.05_is_unattributed": (
            _inputs(strong, four_class, clamp=0.02),
            AttributionOutcome.UNATTRIBUTED,
        ),
        "gap_between_0.05_and_0.10_is_inconclusive": (
            _inputs([0.07, 0.08, 0.06, 0.07, 0.08, 0.07, 0.06, 0.08], four_class),
            AttributionOutcome.INCONCLUSIVE,
        ),
        "primary_leaf_failure_is_k1": (
            _inputs([0.02, 0.01, -0.01, 0.03, 0.02, 0.0, 0.01, 0.02], four_class),
            AttributionOutcome.K1_GRADIENT_FORM,
        ),
        "fewer_than_eight_families_is_k2": (
            _inputs(strong[:6], four_class[:6]),
            AttributionOutcome.K2_UNMEASURABLE,
        ),
        "reservoir_at_half_is_k4": (
            _inputs(strong, four_class, reservoir=0.5),
            AttributionOutcome.K4_AUDIT,
        ),
        "audit_failure_is_k4": (
            _inputs(strong, four_class, audits=False),
            AttributionOutcome.K4_AUDIT,
        ),
        "sibling_tie_is_k6": (
            _inputs(strong, four_class, sibling=0.01),
            AttributionOutcome.K6_COLLAPSE,
        ),
        "uninformative_sibling_does_not_block_confirmation": (
            _inputs(strong, four_class, sibling=None),
            AttributionOutcome.CONFIRMED,
        ),
    }
    decisions = {name: attribution_tree(inputs) for name, (inputs, _) in scenarios.items()}
    gates = {
        f"routes_{name}": decisions[name].outcome is expected
        for name, (_, expected) in scenarios.items()
    }
    noise = NoiseModel()
    rng = np.random.default_rng(seed)
    power = {
        f"effect_{effect:.2f}_families_8_class_{n_class}": simulate_attribution_tree_power(
            noise, effect, 8, n_class, 3, draws, rng
        )
        for effect in (0.0, 0.10, 0.15)
        for n_class in (3, 4, 5)
    }
    null = power["effect_0.00_families_8_class_4"]
    typical = power["effect_0.10_families_8_class_4"]
    gates.update(
        {
            "null_false_confirm_at_most_0.05": null.confirmed <= 0.05,
            "null_routes_to_k1_at_least_0.90": null.k1 >= 0.90,
            "retiered_class_condition_no_weaker_than_wave4_two_sided": (
                typical.class_pass_retiered >= typical.class_pass_wave4_two_sided
            ),
            "three_class_families_never_confirm": (
                power["effect_0.10_families_8_class_3"].confirmed == 0.0
            ),
            "k1_rate_independent_of_class_count": (
                abs(
                    power["effect_0.10_families_8_class_4"].k1
                    - power["effect_0.10_families_8_class_5"].k1
                )
                <= 0.02
            ),
        }
    )
    receipt = {
        "thresholds": AttributionThresholds(),
        "decisions": decisions,
        "noise_model_assumed_not_measured": noise,
        "power_by_scenario": power,
        "power_numbers_are": (
            "Monte-Carlo frequencies under the ASSUMED noise SDs (0.08 family, 0.06 seed, 0.035 "
            "query) with clamp, sibling and audit gates assumed to pass; not measurements"
        ),
    }
    return _case(
        "Pre-registered attribution tree (wave-5 re-tiering): routing of every bucket on crafted "
        "inputs, and the joint CONFIRMED / CLASS_UNRESOLVED / K1 frequencies under the assumed "
        "noise model; a class-level miss must never route to K1.",
        receipt,
        gates,
    )


def case_degenerate_inputs() -> dict[str, Any]:
    rng = np.random.default_rng(0)
    good_prior = FiniteTaskPrior.random(3, 4, 0.3, rng)
    duplicate = np.vstack([good_prior.task_vectors, good_prior.task_vectors[:1]])
    small_spec = InterfaceSpec(state_dim=4, rank=2, n_demonstrations=3, n_state_statistics=3)
    basis = icl.state_statistics_basis(small_spec, 0)
    rule = icl.LinearGDRule(small_spec)
    checks: dict[str, Callable[[], object]] = {
        "interface_state_dim_below_two": lambda: InterfaceSpec(state_dim=1),
        "interface_rank_above_state_dim": lambda: InterfaceSpec(state_dim=8, rank=9),
        "prior_with_one_task": lambda: FiniteTaskPrior(good_prior.task_vectors[:1], 0.3),
        "prior_with_duplicate_tasks": lambda: FiniteTaskPrior(duplicate, 0.3),
        "prior_with_zero_noise": lambda: FiniteTaskPrior(good_prior.task_vectors, 0.0),
        "prior_with_nan_vector": lambda: FiniteTaskPrior(
            np.where(np.eye(3, 4) > 0, np.nan, good_prior.task_vectors), 0.3
        ),
        "rank_truncate_above_state_dim": lambda: icl.rank_truncate(np.eye(4), 5),
        "fidelity_against_constant_teacher": lambda: icl.teacher_fidelity(
            np.ones((3, 2)), np.ones((3, 2))
        ),
        "iso_width_outside_tolerance": lambda: icl.iso_parameter_hidden_width(
            10, 266, 66, 0, 0.001
        ),
        "thresholds_with_single_class_family_minimum": lambda: AttributionThresholds(
            min_class_families=1
        ),
        "tree_inputs_with_nan_gap": lambda: AttributionInputs(
            np.array([0.1, np.nan]), np.array([True, False]), 0.1, 0.1, 0.1, True
        ),
        "write_pass_with_mismatched_shapes": lambda: icl.write_pass(
            rule, np.zeros((2, 3, 4)), np.zeros((2, 3, 5)), basis
        ),
        "write_pass_with_non_finite_keys": lambda: icl.write_pass(
            rule, np.full((2, 3, 4), np.inf), np.zeros((2, 3, 4)), basis
        ),
        "distillation_config_with_zero_steps": lambda: DistillationConfig(0, 8, 1e-3, 0),
        "regime_config_with_one_task": lambda: RegimeDoctorConfig(n_tasks=1),
        "t_interval_on_single_family": lambda: icl.family_t_interval(np.array([0.1])),
        "power_with_more_class_than_families": lambda: simulate_attribution_tree_power(
            NoiseModel(), 0.1, 8, 9, 3, 100, rng
        ),
        "search_grid_with_one_rate": lambda: icl.written_search(
            lambda: icl.LinearGDRule(small_spec),
            lambda generator, n: icl.sample_finite_prior_episodes(good_prior, n, 3, 2, generator),
            icl.sample_finite_prior_episodes(good_prior, 4, 3, 2, rng),
            (1e-3,),
            1,
            2,
            0,
            basis,
        ),
    }
    outcomes: dict[str, bool] = {}
    for name, check in checks.items():
        try:
            check()
        except RuleContractError:
            outcomes[name] = True
        else:
            outcomes[name] = False
    return _case(
        "Degenerate-input rejection: every contract violation must raise RuleContractError "
        "rather than produce a number.",
        {"rejected": outcomes},
        {f"rejects_{name}": flag for name, flag in outcomes.items()},
    )


def build_payload(config: RegimeDoctorConfig, seed: int, draws: int) -> dict[str, Any]:
    started = time.perf_counter()
    cases: dict[str, dict[str, Any]] = {}
    cases["parameter_count_pilot_widths"] = case_parameter_counts()
    cases["rank_truncation_algebra"] = case_rank_truncation(seed)
    positive_case, positive = case_positive_control(config)
    cases["dmmse_regime_positive_control"] = positive_case
    cases["gaussian_prior_negative_control"] = case_negative_control(config, positive)
    cases["permuted_teacher_control"] = case_permuted_teacher(positive)
    cases["two_pass_causality_audit"] = case_causality(positive)
    cases["attribution_tree_semantics_and_power"] = case_attribution_tree(seed, draws)
    cases["degenerate_input_rejection"] = case_degenerate_inputs()
    gates = {
        f"{case_name}.{gate_name}": flag
        for case_name, case in cases.items()
        for gate_name, flag in case["gates"].items()
    }
    implementation = PROJECT_ROOT / "harness" / "icl_rule_distillation.py"
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "doctor": DOCTOR_NAME,
        "direction": DIRECTION,
        "status": "PHASE0_DOCTOR_PASS" if all(gates.values()) else "PHASE0_DOCTOR_FAIL",
        "evidence_grade": EVIDENCE_GRADE,
        "numbers_are": NUMBERS_ARE,
        "registered_cases": list(cases),
        "cases": cases,
        "gates": gates,
        "gate_counts": {
            "passed": int(sum(gates.values())),
            "total": len(gates),
        },
        "config": _jsonable(config),
        "provenance": {
            "implementation": "harness/icl_rule_distillation.py",
            "implementation_sha256": hashlib.sha256(implementation.read_bytes()).hexdigest(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "python_version": platform.python_version(),
            "seed": seed,
            "tree_power_draws": draws,
            "runtime": "numpy-cpu",
            "torch_used": False,
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = RegimeDoctorConfig(seed=args.seed)
    payload = build_payload(config, args.seed, args.draws)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PHASE0_DOCTOR_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
