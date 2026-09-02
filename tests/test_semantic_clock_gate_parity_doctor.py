from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from harness.semantic_clock_gate_parity import (
    CommonDoseCell,
    DoseResponseWorld,
    GateContractError,
    LanguageCovariate,
    RecallSimulatorConfig,
    SpanParityConfig,
    attention_window_gradients,
    audit_attention_window,
    build_gate_ledger,
    classify_common_dose_outcome,
    constant_decay_surgery,
    draw_episode_bank,
    duplicate_tokens,
    fit_partial_fertility_slope,
    fit_tracking_slope,
    forgetting_mass,
    gated_delta_scan,
    k1_warp_invariance_kill,
    k2_pooled_kill,
    k7b_floor_hold,
    k9_sign_disagreement,
    k10_language_exclusion,
    k10b_subject_fallback,
    k11_synthetic_fertility_disagreement,
    log_decay_from_preactivation,
    logit_conjunct_sensitivity,
    mask_is_prefix_blind,
    p1_ledger_prediction,
    p3_common_dose_prediction,
    query_only_mask,
    sentence_window_mask,
    simulate_common_dose_cells,
    simulate_recall_exact_match,
    simulate_synthetic_fertility_english,
    span_parity_gradient_error,
    span_parity_loss,
    write_gate_from_preactivation,
    write_surgery,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = PROJECT_ROOT / "scripts" / "run_semantic_clock_gate_parity_doctor.py"

GRID = (
    ("en", 1.0, 40.0),
    ("pol", 1.605, 2.0638),
    ("fin", 1.627, 0.3823),
    ("hun", 1.706, 0.5341),
    ("ukr", 1.792, 0.8371),
    ("hin", 2.073, 0.2144),
    ("ell", 2.119, 0.5490),
    ("ben", 2.164, 0.1084),
    ("tam", 2.744, 0.0449),
    ("kor", 1.284, 0.85),
    ("tha", 1.174, 0.374),
    ("zho-CN", 0.931, 4.3829),
    ("mya", 4.18, 0.0164),
    ("rus", 1.423, 6.9),
    ("tur", 1.429, 1.4),
    ("msa", 1.157, 0.086),
)
FERTILITIES = tuple(sorted({f for _, f, _ in GRID}))


def _episode_ids() -> tuple[np.ndarray, int]:
    facts = [[i] * 3 for i in range(8)]
    distractors = [[8 + i] * 4 for i in range(6)]
    ids = np.array([t for s in facts + distractors for t in s] + [14] * 3)
    return ids, 14


def test_identity_surgery_reproduces_scan_and_r2_moves_it() -> None:
    rng = np.random.default_rng(0)
    a = rng.standard_normal((2, 20))
    b = rng.standard_normal((2, 20))
    g = np.stack([log_decay_from_preactivation(row, 0.0, 0.5) for row in a])
    beta = np.stack([write_gate_from_preactivation(row) for row in b])
    keys = rng.standard_normal((2, 20, 6))
    values = rng.standard_normal((2, 20, 4))
    queries = rng.standard_normal((2, 20, 6))
    base, _ = gated_delta_scan(keys, values, g, beta, queries)
    same, _ = gated_delta_scan(
        keys,
        values,
        np.stack([constant_decay_surgery(r, 1.0) for r in g]),
        np.stack([write_surgery(r, 1.0) for r in beta]),
        queries,
    )
    moved, _ = gated_delta_scan(
        keys, values, np.stack([constant_decay_surgery(r, 2.0) for r in g]), beta, queries
    )
    assert np.max(np.abs(same - base)) <= 1e-9
    assert np.max(np.abs(moved - base)) > 1e-6
    assert np.all(g <= 0.0)
    assert np.all((beta > 0.0) & (beta < 1.0))


def test_token_duplication_scales_forgetting_mass_exactly() -> None:
    g = np.array([[-0.3, -0.1, -0.7, -0.2]])
    base = forgetting_mass(g[0])
    for k in (2, 3, 5):
        dup = duplicate_tokens(g, k)[0]
        assert forgetting_mass(dup) == pytest.approx(k * base, rel=1e-12)
        assert forgetting_mass(constant_decay_surgery(dup, k)) == pytest.approx(base, rel=1e-12)
    with pytest.raises(GateContractError):
        duplicate_tokens(g, 0)


def test_ledger_p1_holds_for_clock_and_k1_fires_for_warp_invariant_gates() -> None:
    fertility = {name: f for name, f, _ in GRID}
    clock_decay = {name: np.full(round(40 * f), -0.02) for name, f, _ in GRID}
    clock_write = {name: np.full(round(40 * f), 0.3) for name, f, _ in GRID}
    ledger = build_gate_ledger(clock_decay, clock_write, fertility)
    assert p1_ledger_prediction(ledger).verdict
    assert not k1_warp_invariance_kill(ledger).verdict
    tam = next(e for e in ledger if e.language == "tam")
    assert tam.forgetting_ratio == pytest.approx(round(40 * 2.744) / 40)
    invariant_decay = {
        name: np.full(round(40 * f), -0.02 * 40 / round(40 * f)) for name, f, _ in GRID
    }
    invariant_write = {
        name: np.full(round(40 * f), 0.3 * 40 / round(40 * f)) for name, f, _ in GRID
    }
    invariant = build_gate_ledger(invariant_decay, invariant_write, fertility)
    assert k1_warp_invariance_kill(invariant).verdict
    assert not p1_ledger_prediction(invariant).verdict
    with pytest.raises(GateContractError, match="reference fertility"):
        build_gate_ledger(clock_decay, clock_write, {**fertility, "en": 1.3})


def test_prefix_blind_window_has_exact_zero_gradient_and_query_mask_does_not_qualify() -> None:
    rng = np.random.default_rng(1)
    ids, query = _episode_ids()
    window = audit_attention_window(rng, sentence_window_mask(ids), ids)
    assert window.prefix_blind
    assert window.max_outside_key_gradient == 0.0
    assert window.max_outside_value_gradient == 0.0
    assert window.perturbation_max_abs_change == 0.0
    assert window.mean_inside_value_gradient > 0.0
    query_mask = query_only_mask(ids, query)
    assert not mask_is_prefix_blind(query_mask, ids)
    audit = audit_attention_window(rng, query_mask, ids)
    assert audit.zero_gradient_outside_window
    assert not audit.prefix_blind


def test_leaky_window_tamper_is_detected() -> None:
    rng = np.random.default_rng(2)
    ids, _ = _episode_ids()
    leaky = sentence_window_mask(ids).copy()
    distractor = int(np.flatnonzero(ids == 9)[0])
    fact = int(np.flatnonzero(ids == 2)[0])
    leaky[distractor, fact] = True
    assert not mask_is_prefix_blind(leaky, ids)
    q, k, v, u = (rng.standard_normal((ids.size, 5)) for _ in range(4))
    key_grad, value_grad = attention_window_gradients(q, k, v, leaky, u)
    assert value_grad[distractor, fact] > 0.0
    clean_key, clean_value = attention_window_gradients(q, k, v, sentence_window_mask(ids), u)
    assert clean_key[distractor, fact] == 0.0
    assert clean_value[distractor, fact] == 0.0


def test_span_parity_gradient_and_rescale_invariance() -> None:
    rng = np.random.default_rng(3)
    g = log_decay_from_preactivation(rng.standard_normal(30), -0.3, 0.1)
    beta = write_gate_from_preactivation(rng.standard_normal(30))
    spans = ((0, 10), (10, 20), (20, 30))
    pairs = ((0, 1), (0, 2))
    config = SpanParityConfig(epsilon=1e-12)
    error = span_parity_gradient_error(
        g, beta, spans, pairs, anchor_span=0, anchor_value=-0.5, config=config
    )
    assert error < 1e-6
    base = span_parity_loss(g, beta, spans, pairs, anchor_span=0, anchor_value=-0.5, config=config)
    scaled = span_parity_loss(
        2.5 * g, beta, spans, pairs, anchor_span=0, anchor_value=-0.5, config=config
    )
    assert scaled.parity_term == pytest.approx(base.parity_term, rel=1e-8)
    assert scaled.anchor_term != base.anchor_term
    with pytest.raises(GateContractError):
        span_parity_loss(g, beta, spans, ((0, 0),), anchor_span=0, anchor_value=-0.5)


def _worlds() -> dict[str, DoseResponseWorld]:
    return {
        "clock": DoseResponseWorld("clock", baseline_logit=1.4, clock_cost=0.7),
        "headroom": DoseResponseWorld(
            "headroom", baseline_logit=1.8, identity_level_slope=1.6, uniform_gain=0.9
        ),
        "identity": DoseResponseWorld(
            "identity",
            baseline_logit=1.4,
            identity_level_slope=0.8,
            identity_gain_slope=0.6,
            uniform_gain=0.2,
        ),
    }


def _bundle(rng: np.random.Generator, world: DoseResponseWorld) -> tuple:
    grid = tuple(LanguageCovariate(n, f, c) for n, f, c in GRID)
    cells = simulate_common_dose_cells(rng, grid, world, episodes=600)
    synthetic = simulate_synthetic_fertility_english(
        rng, FERTILITIES, world, episodes=600, english_cc_share_percent=40.0
    )
    fit_em = fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=200)
    fit_logit = fit_partial_fertility_slope(cells, scale="logit", rng=rng, resamples=200)
    syn_em = fit_partial_fertility_slope(
        synthetic, scale="em", rng=rng, resamples=200, partial=False
    )
    tracking = fit_tracking_slope(cells, synthetic, scale="em", rng=rng, resamples=200)
    return fit_em, fit_logit, syn_em, tracking


def test_clock_world_claims_and_headroom_world_is_refused() -> None:
    worlds = _worlds()
    rng = np.random.default_rng(42)
    fit_em, fit_logit, syn_em, tracking = _bundle(rng, worlds["clock"])
    assert p3_common_dose_prediction(fit_em, syn_em, tracking).verdict
    assert classify_common_dose_outcome(fit_em, syn_em, tracking).note == "CLAIM"
    assert not k11_synthetic_fertility_disagreement(fit_em, syn_em, tracking).verdict
    fit_em, fit_logit, syn_em, tracking = _bundle(rng, worlds["headroom"])
    # the wave-4 EM-point rule alone would have claimed; the token-count comparator refuses
    assert fit_em.excludes_zero_positively() and fit_em.estimate >= 3.0
    assert k11_synthetic_fertility_disagreement(fit_em, syn_em, tracking).verdict
    assert classify_common_dose_outcome(fit_em, syn_em, tracking).note == "K11_NOT_THE_CLOCK"
    assert not logit_conjunct_sensitivity(fit_em, fit_logit).verdict


def test_identity_world_is_refused_even_though_logit_conjunct_would_claim() -> None:
    rng = np.random.default_rng(42)
    fit_em, fit_logit, syn_em, tracking = _bundle(rng, _worlds()["identity"])
    assert logit_conjunct_sensitivity(fit_em, fit_logit).verdict
    assert classify_common_dose_outcome(fit_em, syn_em, tracking).note == "K11_NOT_THE_CLOCK"


def test_simulator_clock_is_reproduced_by_token_count_but_identity_noise_is_not() -> None:
    rng = np.random.default_rng(42)
    config = RecallSimulatorConfig(per_token_log_decay=-0.005, readout_noise=0.12)
    bank = draw_episode_bank(rng, config, 160)
    outcomes = {
        f: (
            simulate_recall_exact_match(bank, config, fertility=f, decay_ratio=1.0),
            simulate_recall_exact_match(bank, config, fertility=f, decay_ratio=2.0),
        )
        for f in FERTILITIES
    }
    cells = [CommonDoseCell(n, f, c, *outcomes[f]) for n, f, c in GRID]
    synthetic = [CommonDoseCell(f"en-{f}", f, 40.0, *outcomes[f]) for f in FERTILITIES]
    assert (
        cells[0].em_reference.mean()
        > next(c for c in cells if c.language == "tam").em_reference.mean()
    )
    tracking = fit_tracking_slope(cells, synthetic, scale="em", rng=rng, resamples=100)
    assert tracking.estimate == 0.0 and tracking.upper == 0.0
    identity = [
        CommonDoseCell(
            n,
            f,
            c,
            simulate_recall_exact_match(
                bank,
                config,
                fertility=1.0,
                decay_ratio=1.0,
                readout_noise_multiplier=1.0 + 0.6 * max(np.log(f), 0.0),
            ),
            simulate_recall_exact_match(
                bank,
                config,
                fertility=1.0,
                decay_ratio=2.0,
                readout_noise_multiplier=1.0 + 0.6 * max(np.log(f), 0.0),
            ),
        )
        for n, f, c in GRID
    ]
    fit_identity = fit_partial_fertility_slope(identity, scale="em", rng=rng, resamples=100)
    syn_em = fit_partial_fertility_slope(
        synthetic, scale="em", rng=rng, resamples=100, partial=False
    )
    residual = fit_tracking_slope(identity, synthetic, scale="em", rng=rng, resamples=100)
    assert syn_em.excludes_zero_positively()
    # token count fixed at the English count: re-segmented English at f_L gains far more than
    # the identity-noised "language" at f_L, so the residual dose-response is strongly negative
    assert residual.estimate < -3.0
    assert classify_common_dose_outcome(fit_identity, syn_em, residual).note != "CLAIM"


def test_pooled_kill_sign_disagreement_floor_and_exclusion_semantics() -> None:
    rng = np.random.default_rng(5)
    grid = tuple(LanguageCovariate(n, f, c) for n, f, c in GRID)
    null_cells = simulate_common_dose_cells(rng, grid, DoseResponseWorld("null"), episodes=600)
    fit_a = fit_partial_fertility_slope(null_cells, scale="em", rng=rng, resamples=100)
    fit_b = fit_partial_fertility_slope(
        simulate_common_dose_cells(rng, grid, DoseResponseWorld("null"), episodes=600),
        scale="em",
        rng=rng,
        resamples=100,
    )
    pooled = k2_pooled_kill({"qwen": fit_a, "rwkv7": fit_b})
    assert pooled.statistics["pooled_standard_error"] < fit_a.standard_error
    assert not k9_sign_disagreement(fit_a, fit_b).verdict or (fit_a.lower > 0) != (fit_b.lower > 0)
    assert k7b_floor_hold(59.9).verdict and not k7b_floor_hold(60.0).verdict
    languages = [n for n, _, _ in GRID]
    floors = dict.fromkeys(languages, 70.0)
    for language in ("mya", "tam", "ben", "hin", "ell"):
        floors[language] = 40.0
    exclusion = k10_language_exclusion(dict.fromkeys(languages, 5.0), floors)
    assert exclusion.verdict and exclusion.statistics["remaining"] == 11.0
    assert k10b_subject_fallback(qwen_carries_primary=True, rwkv7_carries_primary=False).startswith(
        "qwen"
    )
    assert k10b_subject_fallback(
        qwen_carries_primary=False, rwkv7_carries_primary=False
    ).startswith("redesign")


def test_degenerate_inputs_fail_closed() -> None:
    rng = np.random.default_rng(6)
    ref = rng.random(40) < 0.5
    dose = rng.random(40) < 0.6
    with pytest.raises(GateContractError):
        constant_decay_surgery(np.full(3, -0.1), -1.0)
    with pytest.raises(GateContractError):
        write_surgery(np.array([0.2, 1.2]), 2.0)
    with pytest.raises(GateContractError):
        CommonDoseCell("x", 1.5, 1.0, ref, dose[:-1])
    with pytest.raises(GateContractError, match="at least four"):
        cells = [CommonDoseCell(n, f, c, ref, dose) for n, f, c in GRID[:3]]
        fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=50)
    with pytest.raises(GateContractError, match="constant"):
        cells = [CommonDoseCell(n, 1.0, c, ref, dose) for n, _, c in GRID[:6]]
        fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=50)
    with pytest.raises(GateContractError):
        sentence_window_mask(np.array([0, 1, 0]))
    with pytest.raises(GateContractError):
        DoseResponseWorld("saturating")


def test_doctor_runs_end_to_end_and_receipt_is_tamper_evident(tmp_path: Path) -> None:
    output = tmp_path / "phase0-doctor.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--output",
            str(output),
            "--tally-seeds",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=PROJECT_ROOT,
    )
    assert completed.returncode == 0, completed.stdout[-4000:] + completed.stderr[-4000:]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "PHASE0_OBJECT_DOCTOR_PASS"
    assert "synthetic" in payload["evidence_grade"].lower()
    assert "not compute evidence" in payload["evidence_grade"]
    assert all(payload["gates"].values())
    expected_cases = {
        "identity_surgery_r1_and_causality",
        "ledger_parity_positive_control",
        "ledger_warp_invariant_negative_control",
        "prefix_blind_window_zero_gradient",
        "query_only_mask_is_not_prefix_blind",
        "leaky_window_tamper_detected",
        "span_parity_loss_gradient_and_invariances",
        "mechanistic_recall_positive_control",
        "mechanistic_identity_negative_control",
        "parametric_clock_world",
        "parametric_headroom_world",
        "parametric_identity_world",
        "parametric_null_world",
        "permuted_fertility_negative_control",
        "kill_hold_and_exclusion_semantics",
        "degenerate_inputs_rejected",
    }
    assert expected_cases <= set(payload["cases"])
    assert payload["cases"]["parametric_headroom_world"]["decision"]["em_scale_alone_would_claim"]
    assert (
        payload["cases"]["parametric_headroom_world"]["decision"]["classification"]
        == "K11_NOT_THE_CLOCK"
    )
    assert payload["provenance"]["elapsed_seconds"] < 60.0
    recorded = payload.pop("payload_sha256")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == recorded
    payload["gates"]["leaky_window_tamper_detected"] = False
    tampered = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(tampered).hexdigest() != recorded
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            [sys.executable, str(DOCTOR), "--output", str(output), "--tally-seeds", "1"],
            capture_output=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
