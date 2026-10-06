from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from harness import icl_rule_distillation as icl
from harness.icl_rule_distillation import (
    PILOT_INTERFACE,
    AttributionInputs,
    AttributionOutcome,
    AttributionThresholds,
    FiniteTaskPrior,
    InterfaceSpec,
    NoiseModel,
    RegimeDoctorConfig,
    RuleContractError,
    RuleFamily,
    attribution_tree,
    build_rule,
    causality_audit,
    clamp_reproduces_gradient_form,
    distillation_loss_and_gradients,
    finite_prior_sampler,
    gaussian_prior_sampler,
    rank_truncation_doctor,
    regime_separation,
    rule_parameter_counts,
    run_regime_distillation,
    sample_finite_prior_episodes,
    simulate_attribution_tree_power,
    state_hash,
    state_statistics_basis,
    tampered_write_pass,
    write_pass,
)
from scripts import run_icl_rule_distillation_doctor as doctor

TINY_SPEC = InterfaceSpec(
    state_dim=4, rank=2, n_demonstrations=3, n_state_statistics=3, theta_hidden=5
)
FAST_CONFIG = RegimeDoctorConfig(
    search_grid=(1e-3, 3e-3),
    search_steps=3,
    steps=12,
    evaluation_episodes=96,
    development_episodes=16,
    batch_size=16,
)


def tiny_setup(seed: int = 0):
    rng = np.random.default_rng(seed)
    prior = FiniteTaskPrior.random(3, TINY_SPEC.state_dim, 0.3, rng)
    episodes = sample_finite_prior_episodes(prior, 3, TINY_SPEC.n_demonstrations, 2, rng)
    basis = state_statistics_basis(TINY_SPEC, 1)
    counts = rule_parameter_counts(TINY_SPEC, tolerance=0.2)
    return rng, prior, episodes, basis, counts


def test_pilot_parameter_counts_match_the_proposal_arithmetic() -> None:
    counts = rule_parameter_counts(PILOT_INTERFACE)
    assert counts.theta == 101_762
    assert (counts.gradient_form_hidden, counts.gradient_form) == (305, 101_631)
    assert (counts.adaptive_hidden, counts.adaptive) == (293, 101_731)
    assert counts.linear == 4_100
    assert counts.within_tolerance()
    assert all(abs(gap) < 0.002 for gap in counts.relative_gaps().values())


def test_iso_parameter_width_fails_closed_outside_tolerance() -> None:
    with pytest.raises(RuleContractError, match="outside"):
        icl.iso_parameter_hidden_width(101_762, 266, 66, 0, tolerance=0.0005)
    with pytest.raises(RuleContractError):
        rule_parameter_counts(PILOT_INTERFACE, tolerance=0.0005)


@pytest.mark.parametrize("family", list(RuleFamily))
def test_analytic_gradients_match_finite_differences(family: RuleFamily) -> None:
    rng, _, episodes, basis, counts = tiny_setup()
    rule = build_rule(family, TINY_SPEC, counts, 5)
    for name in rule.params:
        rule.params[name] += 0.05 * rng.normal(size=rule.params[name].shape)
    _, grads, _ = distillation_loss_and_gradients(rule, episodes, basis)
    step = 1e-6
    for name, values in rule.params.items():
        flat = values.reshape(-1)
        analytic = grads[name].reshape(-1)
        for index in range(min(flat.size, 5)):
            original = flat[index]
            flat[index] = original + step
            plus, _, _ = distillation_loss_and_gradients(rule, episodes, basis)
            flat[index] = original - step
            minus, _, _ = distillation_loss_and_gradients(rule, episodes, basis)
            flat[index] = original
            numeric = (plus - minus) / (2.0 * step)
            assert numeric == pytest.approx(analytic[index], rel=2e-2, abs=1e-7), (name, index)


def test_key_span_ceilings_are_realised_through_the_write_code_path() -> None:
    rng = np.random.default_rng(3)
    prior = FiniteTaskPrior.random(4, 16, 0.25, rng)
    episodes = sample_finite_prior_episodes(prior, 300, 8, 8, rng)
    basis = state_statistics_basis(icl.SYNTHETIC_INTERFACE, 42)
    separation = regime_separation(episodes, basis)
    assert separation.separated()
    assert separation.oracles_realised()
    assert 0.4 < separation.key_span_ceiling_gap < 0.6  # (d - n) / d with d = 16, n = 8
    assert separation.free_write_oracle_gap == pytest.approx(0.0, abs=1e-12)
    gaussian = gaussian_prior_sampler(icl.SYNTHETIC_INTERFACE, 0.25, 8)(rng, 300)
    ridge_regime = regime_separation(gaussian, basis)
    assert not ridge_regime.separated()
    assert ridge_regime.key_span_ceiling_gap == pytest.approx(0.0, abs=1e-12)


def test_rank_truncation_is_inert_inside_the_rank_and_active_beyond_it() -> None:
    receipt = rank_truncation_doctor(PILOT_INTERFACE, np.random.default_rng(0))
    assert receipt.passes()
    assert receipt.rank_before_truncation == 9 and receipt.rank_after_truncation == 8
    with pytest.raises(RuleContractError):
        icl.rank_truncate(np.eye(3), 4)


def test_causality_audit_passes_honest_pass_and_detects_leaked_probe() -> None:
    _, _, episodes, basis, counts = tiny_setup()
    rule = build_rule(RuleFamily.THETA, TINY_SPEC, counts, 9)
    audit = causality_audit(rule, episodes, basis)
    assert audit.passes()
    honest = write_pass(rule, episodes.keys, episodes.values, basis)
    leaked = tampered_write_pass(rule, episodes, basis)
    assert state_hash(honest.state) != state_hash(leaked.state)
    assert honest.ledger.chain_hash != leaked.ledger.chain_hash


def test_write_direction_clamp_reproduces_the_gradient_form_network_exactly() -> None:
    _, _, episodes, basis, counts = tiny_setup()
    theta = build_rule(RuleFamily.THETA, TINY_SPEC, counts, 11)
    assert isinstance(theta, icl.MLPWriteRule)
    assert clamp_reproduces_gradient_form(theta, episodes, basis)
    clamped = write_pass(theta, episodes.keys, episodes.values, basis, clamp_write_direction=True)
    assert icl.readout_in_key_span(clamped.state, episodes.keys) <= 1e-9
    free = write_pass(theta, episodes.keys, episodes.values, basis)
    assert icl.readout_in_key_span(free.state, episodes.keys) > 1e-3


def test_degenerate_inputs_are_rejected() -> None:
    rng, prior, _, basis, _ = tiny_setup()
    with pytest.raises(RuleContractError):
        InterfaceSpec(state_dim=1)
    with pytest.raises(RuleContractError, match="distinct"):
        FiniteTaskPrior(np.vstack([prior.task_vectors, prior.task_vectors[:1]]), 0.3)
    with pytest.raises(RuleContractError, match="noise_sigma"):
        FiniteTaskPrior(prior.task_vectors, 0.0)
    with pytest.raises(RuleContractError, match="variance"):
        icl.teacher_fidelity(np.ones((2, 2)), np.ones((2, 2)))
    with pytest.raises(RuleContractError):
        write_pass(icl.LinearGDRule(TINY_SPEC), np.zeros((1, 2, 4)), np.zeros((1, 2, 3)), basis)
    with pytest.raises(RuleContractError):
        AttributionThresholds(min_class_families=1)
    with pytest.raises(RuleContractError):
        RegimeDoctorConfig(clamp_cost=0.2, primary_gap=0.1)


def _inputs(gaps, mask, **overrides) -> AttributionInputs:
    keywords = {"clamp": 0.08, "sibling": 0.08, "reservoir": 0.3, "audits": True}
    keywords.update(overrides)
    return AttributionInputs(
        np.asarray(gaps),
        np.asarray(mask),
        keywords["clamp"],
        keywords["sibling"],
        keywords["reservoir"],
        keywords["audits"],
    )


def test_attribution_tree_routes_every_bucket() -> None:
    strong = [0.16, 0.14, 0.15, 0.13, 0.17, 0.15, 0.14, 0.16]
    four = [True] * 4 + [False] * 4
    assert attribution_tree(_inputs(strong, four)).outcome is AttributionOutcome.CONFIRMED
    class_miss = attribution_tree(_inputs([0.02, 0.01, 0.03, 0.02, 0.24, 0.26, 0.25, 0.27], four))
    assert class_miss.outcome is AttributionOutcome.CLASS_UNRESOLVED
    unmeasurable = attribution_tree(_inputs(strong, [True] * 3 + [False] * 5))
    assert unmeasurable.outcome is AttributionOutcome.CLASS_UNRESOLVED
    assert "below 4" in unmeasurable.reason
    assert (
        attribution_tree(_inputs(strong, four, clamp=0.02)).outcome
        is AttributionOutcome.UNATTRIBUTED
    )
    inconclusive = attribution_tree(_inputs([0.07, 0.08, 0.06, 0.07, 0.08, 0.07, 0.06, 0.08], four))
    assert inconclusive.outcome is AttributionOutcome.INCONCLUSIVE
    k1 = attribution_tree(_inputs([0.02, 0.01, -0.01, 0.03, 0.02, 0.0, 0.01, 0.02], four))
    assert k1.outcome is AttributionOutcome.K1_GRADIENT_FORM
    assert (
        attribution_tree(_inputs(strong[:6], four[:6])).outcome
        is AttributionOutcome.K2_UNMEASURABLE
    )
    assert (
        attribution_tree(_inputs(strong, four, reservoir=0.5)).outcome
        is AttributionOutcome.K4_AUDIT
    )
    assert (
        attribution_tree(_inputs(strong, four, audits=False)).outcome is AttributionOutcome.K4_AUDIT
    )
    assert (
        attribution_tree(_inputs(strong, four, sibling=0.01)).outcome
        is AttributionOutcome.K6_COLLAPSE
    )
    assert (
        attribution_tree(_inputs(strong, four, sibling=None)).outcome
        is AttributionOutcome.CONFIRMED
    )


def test_tree_power_controls_the_null_and_never_confirms_with_three_class_families() -> None:
    rng = np.random.default_rng(42)
    null = simulate_attribution_tree_power(NoiseModel(), 0.0, 8, 4, 3, 2000, rng)
    assert null.confirmed <= 0.05
    assert null.k1 >= 0.90
    typical = simulate_attribution_tree_power(NoiseModel(), 0.10, 8, 4, 3, 2000, rng)
    assert typical.class_pass_retiered >= typical.class_pass_wave4_two_sided
    assert typical.confirmed + typical.class_unresolved == pytest.approx(typical.primary_pass)
    three = simulate_attribution_tree_power(NoiseModel(), 0.10, 8, 3, 3, 500, rng)
    assert three.confirmed == 0.0
    with pytest.raises(RuleContractError):
        simulate_attribution_tree_power(NoiseModel(), 0.1, 8, 9, 3, 100, rng)


def test_fast_regime_run_reports_ladder_and_search_receipts() -> None:
    prior = FiniteTaskPrior.random(4, 16, 0.25, np.random.default_rng(42))
    receipt = run_regime_distillation(
        FAST_CONFIG, finite_prior_sampler(prior, FAST_CONFIG.spec, FAST_CONFIG.n_queries)
    )
    assert set(receipt.rules) == {family.value for family in RuleFamily}
    for rule in receipt.rules.values():
        assert len(rule.development_losses) == len(FAST_CONFIG.search_grid)
        assert rule.selected_learning_rate in FAST_CONFIG.search_grid
    assert receipt.counts.within_tolerance()
    assert receipt.separation.separated()
    assert receipt.audit.passes()
    assert receipt.clamp_reproduces_gradient_form


def test_doctor_tamper_disabling_leak_detection_fails_the_causality_case(monkeypatch) -> None:
    monkeypatch.setattr(
        icl,
        "tampered_write_pass",
        lambda rule, episodes, basis: write_pass(rule, episodes.keys, episodes.values, basis),
    )
    payload = doctor.build_payload(FAST_CONFIG, seed=42, draws=200)
    causality = payload["cases"]["two_pass_causality_audit"]
    assert causality["gates"]["tampered_pass_detected"] is False
    assert causality["status"] == "FAIL"
    assert payload["status"] == "PHASE0_DOCTOR_FAIL"


def test_doctor_tamper_raising_primary_gap_threshold_fails_positive_control(monkeypatch) -> None:
    monkeypatch.setattr(
        doctor,
        "positive_control_gates",
        lambda receipt, config: {"impossible_gate": receipt.gap("R_theta", "R_gf") >= 0.99},
    )
    payload = doctor.build_payload(FAST_CONFIG, seed=42, draws=200)
    assert payload["cases"]["dmmse_regime_positive_control"]["status"] == "FAIL"
    assert payload["status"] == "PHASE0_DOCTOR_FAIL"


def test_full_doctor_run_writes_a_passing_receipt(tmp_path) -> None:
    output = tmp_path / "phase0-doctor.json"
    assert doctor.main(["--output", str(output), "--draws", "1000"]) == 0
    payload = json.loads(output.read_text())
    assert payload["status"] == "PHASE0_DOCTOR_PASS"
    assert payload["evidence_grade"].startswith("SYNTHETIC_EXECUTABILITY_AND_GATE_SEMANTICS_ONLY")
    assert "synthetic-case numbers" in payload["numbers_are"]
    assert all(payload["gates"].values())
    assert payload["gate_counts"]["passed"] == payload["gate_counts"]["total"] >= 40
    assert set(payload["registered_cases"]) == {
        "parameter_count_pilot_widths",
        "rank_truncation_algebra",
        "dmmse_regime_positive_control",
        "gaussian_prior_negative_control",
        "permuted_teacher_control",
        "two_pass_causality_audit",
        "attribution_tree_semantics_and_power",
        "degenerate_input_rejection",
    }
    positive = payload["cases"]["dmmse_regime_positive_control"]["receipt"]
    assert positive["ladder_readings"]["D(R_theta, R_gf)"] >= 0.10
    negative = payload["cases"]["gaussian_prior_negative_control"]["receipt"]
    assert negative["separation"]["key_span_ceiling_gap"] <= 1e-6
    assert payload["provenance"]["torch_used"] is False
    assert payload["elapsed_seconds"] < 60.0
    recomputed = dict(payload)
    del recomputed["payload_sha256"]
    canonical = json.dumps(recomputed, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == payload["payload_sha256"]
    with pytest.raises(FileExistsError):
        doctor.main(["--output", str(output)])
