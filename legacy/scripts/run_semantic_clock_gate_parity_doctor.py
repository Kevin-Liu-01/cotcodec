#!/usr/bin/env python3
"""Exercise the Direction-20 phase-0 objects on registered synthetic cases before any GPU job.

Every number this doctor prints is a synthetic-case number produced by the
NumPy Gated DeltaNet simulator, hand-built gate traces and masks, or a
parametric Bernoulli dose-response generator. Passage proves that the
pre-registered objects execute and that the registered gates fire on the
cases they are registered for. It proves nothing about Qwen3.5-4B-Base,
rwkv7-1.5B-world, Kimi-Linear, NTREX or any real translation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import scipy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.semantic_clock_gate_parity import (  # noqa: E402
    CommonDoseCell,
    DoseResponseWorld,
    GateContractError,
    LanguageCovariate,
    RecallSimulatorConfig,
    SlopeFit,
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
    k3_uniform_effect_kill,
    k4_script_gap_kill,
    k7_ceiling_hold,
    k7b_floor_hold,
    k8_resourcedness_kill,
    k9_sign_disagreement,
    k10_language_exclusion,
    k10b_subject_fallback,
    k11_synthetic_fertility_disagreement,
    log_decay_from_preactivation,
    logit_conjunct_sensitivity,
    mask_is_prefix_blind,
    masked_attention,
    p1_ledger_prediction,
    p3_common_dose_prediction,
    query_only_mask,
    sentence_window_mask,
    simulate_common_dose_cells,
    simulate_recall_exact_match,
    simulate_synthetic_fertility_english,
    span_parity_gradient_error,
    span_parity_loss,
    synthetic_fertility_baseline_cost,
    write_gate_from_preactivation,
    write_surgery,
)

DOCTOR_NAME = "semantic-clock-gate-parity-phase0"
PASS_STATUS = "PHASE0_OBJECT_DOCTOR_PASS"
FAIL_STATUS = "PHASE0_OBJECT_DOCTOR_FAIL"
EVIDENCE_GRADE = (
    "EXECUTABILITY_AND_GATE_SEMANTICS_ONLY: every number in this receipt is a synthetic-case "
    "number from a NumPy Gated DeltaNet simulator, hand-built gate traces and attention masks, "
    "or a parametric Bernoulli dose-response generator; no checkpoint, GPU, tokenizer, corpus "
    "or translation was touched. Passage proves that the phase-0 objects execute and that the "
    "registered gates fire on the cases they are registered for. It proves nothing about "
    "Qwen3.5-4B-Base, rwkv7-1.5B-world, Kimi-Linear or NTREX, and it is not compute evidence."
)

# Planning covariates copied from the proposal's claim registry (CR-05 fertility on the
# Qwen3.5-4B-Base tokenizer, CR-07/CR-08 Common Crawl page shares in percent). They are
# FIRST_PARTY owner and refuter measurements used here only as a design matrix; the EM
# outcomes attached to them below are synthetic. English's Common Crawl share is not in
# the registry, so a labelled synthetic design value is used for it.
ENGLISH_CC_SHARE_DESIGN_VALUE = 40.0
GRID_COVARIATES: tuple[tuple[str, float, float], ...] = (
    ("en", 1.0, ENGLISH_CC_SHARE_DESIGN_VALUE),
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
COVARIATE_PROVENANCE = (
    "fertility values are the proposal's CR-05 planning numbers (owner measurement, "
    "FIRST_PARTY, not yet archived); Common Crawl shares are CR-07/CR-08 (read-once, "
    "FIRST_PARTY); English's share is a synthetic design value of 40.0 percent, not a "
    "measurement; every EM outcome is synthetic."
)
FERTILITY_GRID = tuple(sorted({fertility for _, fertility, _ in GRID_COVARIATES}))
WORLDS = {
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
    "null": DoseResponseWorld("null", baseline_logit=1.0),
}
EXPECTED_WORLD_LABEL = {
    "clock": "CLAIM",
    "headroom": "K11_NOT_THE_CLOCK",
    "identity": "K11_NOT_THE_CLOCK",
    "null": "K2_NO_FERTILITY_SLOPE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--simulator-episodes", type=int, default=320)
    parser.add_argument("--dose-episodes", type=int, default=600)
    parser.add_argument("--resamples", type=int, default=500)
    parser.add_argument("--tally-seeds", type=int, default=5)
    return parser.parse_args()


def _slope_receipt(fit: SlopeFit) -> dict[str, float | int | str]:
    return {
        "scale": fit.scale,
        "estimate": fit.estimate,
        "standard_error": fit.standard_error,
        "lower": fit.lower,
        "upper": fit.upper,
        "ols_lower": fit.ols_lower,
        "ols_upper": fit.ols_upper,
        "bootstrap_lower": fit.bootstrap_lower,
        "bootstrap_upper": fit.bootstrap_upper,
        "marginal_estimate": fit.marginal_estimate,
        "marginal_lower": fit.marginal_lower,
        "marginal_upper": fit.marginal_upper,
        "resource_estimate": fit.resource_estimate,
        "n_languages": fit.n_languages,
        "resamples": fit.resamples,
    }


def _cells_receipt(cells: Sequence[CommonDoseCell]) -> dict[str, dict[str, float]]:
    return {
        cell.language: {
            "fertility": cell.fertility,
            "em_reference_percent": 100.0 * float(cell.em_reference.mean()),
            "em_dose_percent": 100.0 * float(cell.em_dose.mean()),
        }
        for cell in cells
    }


def _grid() -> tuple[LanguageCovariate, ...]:
    return tuple(LanguageCovariate(name, f, cc) for name, f, cc in GRID_COVARIATES)


def _decision_bundle(
    cells: Sequence[CommonDoseCell],
    synthetic: Sequence[CommonDoseCell],
    rng: np.random.Generator,
    resamples: int,
) -> dict[str, Any]:
    fit_em = fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=resamples)
    fit_logit = fit_partial_fertility_slope(cells, scale="logit", rng=rng, resamples=resamples)
    synthetic_em = fit_partial_fertility_slope(
        synthetic, scale="em", rng=rng, resamples=resamples, partial=False
    )
    synthetic_logit = fit_partial_fertility_slope(
        synthetic, scale="logit", rng=rng, resamples=resamples, partial=False
    )
    tracking_em = fit_tracking_slope(cells, synthetic, scale="em", rng=rng, resamples=resamples)
    tracking_logit = fit_tracking_slope(
        cells, synthetic, scale="logit", rng=rng, resamples=resamples
    )
    baseline_cost = synthetic_fertility_baseline_cost(synthetic, rng=rng, resamples=resamples)
    p3 = p3_common_dose_prediction(fit_em, synthetic_em, tracking_em)
    k11 = k11_synthetic_fertility_disagreement(fit_em, synthetic_em, tracking_em)
    label = classify_common_dose_outcome(fit_em, synthetic_em, tracking_em)
    conjunct = logit_conjunct_sensitivity(fit_em, fit_logit)
    k8 = k8_resourcedness_kill(fit_em)
    return {
        "cross_language_em": _slope_receipt(fit_em),
        "cross_language_logit": _slope_receipt(fit_logit),
        "synthetic_english_em": _slope_receipt(synthetic_em),
        "synthetic_english_logit": _slope_receipt(synthetic_logit),
        "tracking_em": _slope_receipt(tracking_em),
        "tracking_logit": _slope_receipt(tracking_logit),
        "synthetic_baseline_cost_logit_per_log_f": {
            "estimate": baseline_cost[0],
            "lower": baseline_cost[1],
            "upper": baseline_cost[2],
        },
        "p3_verdict": p3.verdict,
        "p3_statistics": p3.statistics,
        "k11_fires": k11.verdict,
        "k8_fires": k8.verdict,
        "classification": label.note,
        "em_scale_alone_would_claim": bool(
            conjunct.statistics["em_scale_alone_would_claim"] == 1.0
        ),
        "logit_conjunct_would_claim": conjunct.verdict,
    }


# --------------------------------------------------------------------------- #
# Registered cases
# --------------------------------------------------------------------------- #


def case_identity_surgery(rng: np.random.Generator) -> dict[str, Any]:
    batch, length, key_dim, value_dim = 4, 40, 8, 6
    a = rng.standard_normal((batch, length))
    b = rng.standard_normal((batch, length))
    log_decay = np.stack([log_decay_from_preactivation(row, 0.0, 0.5) for row in a])
    write_gate = np.stack([write_gate_from_preactivation(row) for row in b])
    keys = rng.standard_normal((batch, length, key_dim))
    values = rng.standard_normal((batch, length, value_dim))
    queries = rng.standard_normal((batch, length, key_dim))
    baseline, _ = gated_delta_scan(keys, values, log_decay, write_gate, queries)
    surged_decay = np.stack([constant_decay_surgery(row, 1.0) for row in log_decay])
    surged_write = np.stack([write_surgery(row, 1.0) for row in write_gate])
    surged, _ = gated_delta_scan(keys, values, surged_decay, surged_write, queries)
    identity_gap = float(np.max(np.abs(surged - baseline)))
    halved = np.stack([constant_decay_surgery(row, 2.0) for row in log_decay])
    moved, _ = gated_delta_scan(keys, values, halved, write_gate, queries)
    moved_gap = float(np.max(np.abs(moved - baseline)))
    perturbed_keys = keys.copy()
    perturbed_keys[:, length // 2 :, :] += rng.standard_normal(
        (batch, length - length // 2, key_dim)
    )
    causal, _ = gated_delta_scan(perturbed_keys, values, log_decay, write_gate, queries)
    causal_gap = float(np.max(np.abs(causal[:, : length // 2, :] - baseline[:, : length // 2, :])))
    return {
        "identity_max_abs_output_gap": identity_gap,
        "r2_surgery_max_abs_output_gap": moved_gap,
        "future_perturbation_max_abs_change_on_past_outputs": causal_gap,
        "expected": "r = 1 reproduces the unhooked scan to 1e-9, r = 2 moves it, future tokens "
        "never change past outputs",
        "gate": identity_gap <= 1e-9 and moved_gap > 1e-6 and causal_gap == 0.0,
    }


def case_token_duplication(
    rng: np.random.Generator, config: RecallSimulatorConfig, episodes: int
) -> dict[str, Any]:
    length = 30
    log_decay = np.stack([log_decay_from_preactivation(rng.standard_normal(length), -0.5, 0.2)])
    base_mass = forgetting_mass(log_decay[0])
    ratios: dict[str, float] = {}
    restored: dict[str, float] = {}
    for repeats in (2, 3):
        duplicated = duplicate_tokens(log_decay, repeats)[0]
        ratios[str(repeats)] = forgetting_mass(duplicated) / base_mass
        restored[str(repeats)] = forgetting_mass(constant_decay_surgery(duplicated, repeats))
    bank = draw_episode_bank(rng, config, episodes)
    em_single = float(
        simulate_recall_exact_match(bank, config, fertility=1.0, decay_ratio=1.0).mean()
    )
    em_double = float(
        simulate_recall_exact_match(bank, config, fertility=2.0, decay_ratio=1.0).mean()
    )
    em_double_r2 = float(
        simulate_recall_exact_match(bank, config, fertility=2.0, decay_ratio=2.0).mean()
    )
    exact = all(math.isclose(ratios[k], float(k), rel_tol=1e-9) for k in ratios) and all(
        math.isclose(restored[k], base_mass, rel_tol=1e-9) for k in restored
    )
    return {
        "forgetting_mass_ratio_by_repeats": ratios,
        "forgetting_mass_after_surgery_r_equals_k": restored,
        "baseline_forgetting_mass": base_mass,
        "simulator_em_percent_f1_r1": 100.0 * em_single,
        "simulator_em_percent_f2_r1": 100.0 * em_double,
        "simulator_em_percent_f2_r2": 100.0 * em_double_r2,
        "expected": "F scales exactly with the duplication factor, r = k restores it, and doubling "
        "the token count at fixed content lowers simulator recall which r = 2 partly recovers",
        "gate": exact and em_double < em_single and em_double_r2 > em_double,
    }


def _ledger_traces(self_normalizing: bool) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    english_tokens = 40
    decay: dict[str, np.ndarray] = {}
    write: dict[str, np.ndarray] = {}
    for name, fertility, _ in GRID_COVARIATES:
        tokens = max(1, round(fertility * english_tokens))
        per_token = -0.02 * (english_tokens / tokens) if self_normalizing else -0.02
        decay[name] = np.full(tokens, per_token)
        write[name] = np.full(tokens, 0.3 * (english_tokens / tokens) if self_normalizing else 0.3)
    return decay, write


def case_ledger_positive_control() -> dict[str, Any]:
    decay, write = _ledger_traces(self_normalizing=False)
    fertility = {name: f for name, f, _ in GRID_COVARIATES}
    ledger = build_gate_ledger(decay, write, fertility)
    p1 = p1_ledger_prediction(ledger)
    k1 = k1_warp_invariance_kill(ledger)
    return {
        "forgetting_ratio_by_language": {e.language: e.forgetting_ratio for e in ledger},
        "write_ratio_by_language": {e.language: e.write_ratio for e in ledger},
        "p1_statistics": p1.statistics,
        "k1_statistics": k1.statistics,
        "expected": "a per-token clock makes R_F and R_W track fertility: P1 holds, K1 silent",
        "gate": p1.verdict and not k1.verdict,
    }


def case_ledger_negative_control() -> dict[str, Any]:
    decay, write = _ledger_traces(self_normalizing=True)
    fertility = {name: f for name, f, _ in GRID_COVARIATES}
    ledger = build_gate_ledger(decay, write, fertility)
    p1 = p1_ledger_prediction(ledger)
    k1 = k1_warp_invariance_kill(ledger)
    return {
        "forgetting_ratio_by_language": {e.language: e.forgetting_ratio for e in ledger},
        "p1_statistics": p1.statistics,
        "k1_statistics": k1.statistics,
        "expected": "gates that already realize time-warp invariance give R_F near 1: K1 fires, "
        "P1 fails",
        "gate": k1.verdict and not p1.verdict,
    }


def _episode_sentence_ids() -> tuple[np.ndarray, int]:
    facts = [[index] * 3 for index in range(8)]
    distractors = [[8 + index] * 4 for index in range(6)]
    query_sentence = 14
    ids = np.array(
        [token for sentence in facts + distractors for token in sentence] + [query_sentence] * 3
    )
    return ids, query_sentence


def case_prefix_blind_window(rng: np.random.Generator) -> dict[str, Any]:
    ids, _ = _episode_sentence_ids()
    mask = sentence_window_mask(ids)
    audit = audit_attention_window(rng, mask, ids)
    return {
        "tokens": int(ids.size),
        "permitted_pairs": int(mask.sum()),
        "forbidden_pairs": audit.outside_pairs,
        "max_outside_key_gradient": audit.max_outside_key_gradient,
        "max_outside_value_gradient": audit.max_outside_value_gradient,
        "mean_inside_value_gradient": audit.mean_inside_value_gradient,
        "perturbation_max_abs_change": audit.perturbation_max_abs_change,
        "prefix_blind": audit.prefix_blind,
        "expected": "no permitted pair crosses a sentence boundary; gradients to out-of-window "
        "keys and values are exactly zero and perturbing them leaves outputs bitwise unchanged",
        "gate": audit.prefix_blind
        and audit.zero_gradient_outside_window
        and audit.mean_inside_value_gradient > 0.0,
    }


def case_query_only_mask(rng: np.random.Generator) -> dict[str, Any]:
    ids, query_sentence = _episode_sentence_ids()
    mask = query_only_mask(ids, query_sentence)
    audit = audit_attention_window(rng, mask, ids)
    crosses = (ids[:, None] != ids[None, :]) & mask
    return {
        "cross_sentence_pairs_permitted_in_prefix": int(crosses.sum()),
        "prefix_blind": audit.prefix_blind,
        "zero_gradient_outside_own_window": audit.zero_gradient_outside_window,
        "expected": "the wave-3 query-only mask keeps the query blind but lets prefix tokens "
        "attend across sentences (reviewer 1's rehearsal relay), so it is NOT prefix-blind",
        "gate": (not audit.prefix_blind)
        and crosses.sum() > 0
        and audit.zero_gradient_outside_window,
    }


def case_leaky_window_tamper(rng: np.random.Generator) -> dict[str, Any]:
    ids, _ = _episode_sentence_ids()
    leaky = sentence_window_mask(ids).copy()
    distractor_token = int(np.flatnonzero(ids == 9)[0])
    fact_token = int(np.flatnonzero(ids == 2)[0])
    leaky[distractor_token, fact_token] = True
    q = rng.standard_normal((ids.size, 8))
    k = rng.standard_normal((ids.size, 8))
    v = rng.standard_normal((ids.size, 8))
    u = rng.standard_normal((ids.size, 8))
    key_grad, value_grad = attention_window_gradients(q, k, v, leaky, u)
    leaked = float(
        max(key_grad[distractor_token, fact_token], value_grad[distractor_token, fact_token])
    )
    return {
        "tampered_pair": [distractor_token, fact_token],
        "prefix_blind": mask_is_prefix_blind(leaky, ids),
        "gradient_through_tampered_pair": leaked,
        "expected": "one cross-sentence hop makes the prefix-blind gate fail and carries non-zero "
        "gradient",
        "gate": (not mask_is_prefix_blind(leaky, ids)) and leaked > 0.0,
    }


def case_span_parity_loss(rng: np.random.Generator) -> dict[str, Any]:
    length = 60
    log_decay = log_decay_from_preactivation(rng.standard_normal(length), -0.3, 0.1)
    write_gate = write_gate_from_preactivation(rng.standard_normal(length))
    spans = ((0, 10), (10, 26), (26, 40), (40, 60))
    pairs = ((0, 1), (0, 2), (0, 3))
    anchor = float(log_decay[:10].mean())
    config = SpanParityConfig(epsilon=1e-12)
    gradient_error = span_parity_gradient_error(
        log_decay, write_gate, spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    base = span_parity_loss(
        log_decay, write_gate, spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    scaled = span_parity_loss(
        3.0 * log_decay, write_gate, spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    rescale_gap = abs(scaled.parity_term - base.parity_term) / max(base.parity_term, 1e-300)
    # per-language constant rescale: language spans tile the English span by fertility
    english = log_decay[:10]
    constant_decay = [english]
    ratios = []
    for fertility in (1.6, 2.1, 2.7):
        tokens = round(fertility * 10)
        span = np.resize(english, tokens)
        constant_decay.append(span)
        ratios.append(forgetting_mass(span) / forgetting_mass(english))
    tiled = np.concatenate(constant_decay)
    bounds = np.cumsum([0] + [len(s) for s in constant_decay])
    tiled_spans = tuple((int(bounds[i]), int(bounds[i + 1])) for i in range(4))
    tiled_write = np.full(tiled.size, 0.5)
    before = span_parity_loss(
        tiled, tiled_write, tiled_spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    rescaled = tiled.copy()
    for index, ratio in enumerate(ratios, start=1):
        s, e = tiled_spans[index]
        rescaled[s:e] = constant_decay_surgery(rescaled[s:e], ratio)
    after = span_parity_loss(
        rescaled, tiled_write, tiled_spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    # span-ratio noise (CV 0.2 around each language's constant) leaves a residual the constant
    # cannot remove: the executable form of P5's expectation
    noisy = rescaled.copy()
    for index in range(1, 4):
        s, e = tiled_spans[index]
        noisy[s:e] = noisy[s:e] * (1.0 + 0.2 * rng.standard_normal())
    residual = span_parity_loss(
        noisy, tiled_write, tiled_spans, pairs, anchor_span=0, anchor_value=anchor, config=config
    )
    return {
        "max_relative_gradient_error": gradient_error,
        "global_rescale_relative_parity_change": rescale_gap,
        "anchor_term_moves_under_rescale": scaled.anchor_term != base.anchor_term,
        "parity_term_before_constant_rescale": before.parity_term,
        "parity_term_after_constant_rescale": after.parity_term,
        "parity_term_with_span_ratio_cv_0p2": residual.parity_term,
        "expected": "analytic gradient matches central differences, the log-ratio term is "
        "invariant to a global rescale of g, a per-language constant rescale zeroes it when "
        "span ratios are constant and leaves a residual when they vary",
        "gate": gradient_error < 1e-6
        and rescale_gap < 1e-8
        and before.parity_term > 1e-3
        and after.parity_term < 1e-20
        and residual.parity_term > 1e-4,
    }


def case_mechanistic_positive_control(
    rng: np.random.Generator, config: RecallSimulatorConfig, episodes: int, resamples: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    bank = draw_episode_bank(rng, config, episodes)
    cells = []
    by_fertility: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    for name, fertility, cc in GRID_COVARIATES:
        if fertility not in by_fertility:
            by_fertility[fertility] = (
                simulate_recall_exact_match(bank, config, fertility=fertility, decay_ratio=1.0),
                simulate_recall_exact_match(bank, config, fertility=fertility, decay_ratio=2.0),
            )
        reference, dose = by_fertility[fertility]
        cells.append(CommonDoseCell(name, fertility, cc, reference, dose))
    synthetic = tuple(
        CommonDoseCell(
            f"en-resegmented-{fertility}",
            fertility,
            ENGLISH_CC_SHARE_DESIGN_VALUE,
            by_fertility[fertility][0],
            by_fertility[fertility][1],
        )
        for fertility in FERTILITY_GRID
    )
    bundle = _decision_bundle(cells, synthetic, rng, resamples)
    em_en = 100.0 * float(cells[0].em_reference.mean())
    em_tam = 100.0 * float(next(c for c in cells if c.language == "tam").em_reference.mean())
    k7 = k7_ceiling_hold(em_en)
    k7b = k7b_floor_hold(em_en)
    positive = {
        "cells": _cells_receipt(cells),
        "decision": bundle,
        "k7_ceiling_fires": k7.verdict,
        "k7b_floor_fires": k7b.verdict,
        "em_en_minus_em_tam_points": em_en - em_tam,
        "note": "in the simulator fertility changes token count only, so re-segmented English at "
        "f_L is the same generator as language L and the tracking residual is zero by "
        "construction; the informative mechanistic negative control is the identity-noise "
        "case below",
        "expected": "a per-token clock produces a positive fertility slope of the common-dose gain "
        "that token count reproduces (CLAIM), with English between the K7b floor and K7 ceiling",
        "gate": bundle["classification"] == "CLAIM"
        and not k7.verdict
        and not k7b.verdict
        and em_en > em_tam,
    }
    # identity negative control: token count fixed at the English count, a language-identity
    # readout difficulty that grows with log fertility installs the baseline gap instead
    identity_cells = []
    for name, fertility, cc in GRID_COVARIATES:
        multiplier = 1.0 + 0.6 * math.log(fertility) if fertility > 1.0 else 1.0
        identity_cells.append(
            CommonDoseCell(
                name,
                fertility,
                cc,
                simulate_recall_exact_match(
                    bank,
                    config,
                    fertility=1.0,
                    decay_ratio=1.0,
                    readout_noise_multiplier=multiplier,
                ),
                simulate_recall_exact_match(
                    bank,
                    config,
                    fertility=1.0,
                    decay_ratio=2.0,
                    readout_noise_multiplier=multiplier,
                ),
            )
        )
    identity_bundle = _decision_bundle(identity_cells, synthetic, rng, resamples)
    negative = {
        "cells": _cells_receipt(identity_cells),
        "decision": identity_bundle,
        "expected": "a cross-language EM slope installed by language identity at fixed token count "
        "is refused because re-segmented English at matched token count does not reproduce it "
        "(K11), even though the EM-point slope alone would have claimed",
        "gate": identity_bundle["classification"] == "K11_NOT_THE_CLOCK"
        and identity_bundle["em_scale_alone_would_claim"],
    }
    return positive, negative


def case_parametric_world(
    name: str,
    rng: np.random.Generator,
    episodes: int,
    resamples: int,
    tally_seeds: int,
    seed: int,
) -> dict[str, Any]:
    world = WORLDS[name]
    grid = _grid()
    offsets = rng.normal(0.0, 0.15, len(grid))
    covariates = tuple(
        LanguageCovariate(c.language, c.fertility, c.cc_share_percent, float(o))
        for c, o in zip(grid, offsets, strict=True)
    )
    cells = simulate_common_dose_cells(rng, covariates, world, episodes=episodes)
    synthetic = simulate_synthetic_fertility_english(
        rng,
        FERTILITY_GRID,
        world,
        episodes=episodes,
        english_cc_share_percent=ENGLISH_CC_SHARE_DESIGN_VALUE,
    )
    bundle = _decision_bundle(cells, synthetic, rng, resamples)
    tally: Counter[str] = Counter()
    for offset in range(1, tally_seeds + 1):
        tally_rng = np.random.default_rng(seed + 1000 * offset)
        tally_offsets = tally_rng.normal(0.0, 0.15, len(grid))
        tally_cov = tuple(
            LanguageCovariate(c.language, c.fertility, c.cc_share_percent, float(o))
            for c, o in zip(grid, tally_offsets, strict=True)
        )
        tally_cells = simulate_common_dose_cells(tally_rng, tally_cov, world, episodes=episodes)
        tally_syn = simulate_synthetic_fertility_english(
            tally_rng,
            FERTILITY_GRID,
            world,
            episodes=episodes,
            english_cc_share_percent=ENGLISH_CC_SHARE_DESIGN_VALUE,
        )
        fit_em = fit_partial_fertility_slope(
            tally_cells, scale="em", rng=tally_rng, resamples=max(50, resamples // 4)
        )
        syn_em = fit_partial_fertility_slope(
            tally_syn, scale="em", rng=tally_rng, resamples=max(50, resamples // 4), partial=False
        )
        track = fit_tracking_slope(
            tally_cells, tally_syn, scale="em", rng=tally_rng, resamples=max(50, resamples // 4)
        )
        tally[classify_common_dose_outcome(fit_em, syn_em, track).note] += 1
    expected = EXPECTED_WORLD_LABEL[name]
    gate = bundle["classification"] == expected
    if name in {"headroom", "identity"}:
        gate = gate and bundle["em_scale_alone_would_claim"]
    if name == "clock":
        gate = gate and bundle["synthetic_baseline_cost_logit_per_log_f"]["upper"] < 0.0
    return {
        "world": {
            "kind": world.kind,
            "baseline_logit": world.baseline_logit,
            "clock_cost": world.clock_cost,
            "uniform_gain": world.uniform_gain,
            "identity_level_slope": world.identity_level_slope,
            "identity_gain_slope": world.identity_gain_slope,
            "episode_correlation": world.episode_correlation,
        },
        "cells": _cells_receipt(cells),
        "decision": bundle,
        "classification_tally_over_extra_seeds": dict(tally),
        "expected_classification": expected,
        "expected": f"the {name} world must classify as {expected}"
        + (
            " while the EM-point slope alone would have claimed"
            if name in {"headroom", "identity"}
            else ""
        )
        + (
            " and re-segmented English must show a negative baseline token-count cost"
            if name == "clock"
            else ""
        ),
        "gate": gate,
    }


def case_permuted_fertility(
    rng: np.random.Generator, episodes: int, resamples: int
) -> dict[str, Any]:
    cells = simulate_common_dose_cells(rng, _grid(), WORLDS["clock"], episodes=episodes)
    true_fit = fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=resamples)
    permuted = rng.permutation([cell.fertility for cell in cells])
    while np.array_equal(permuted, [cell.fertility for cell in cells]):
        permuted = rng.permutation([cell.fertility for cell in cells])
    shuffled = fit_partial_fertility_slope(
        cells, scale="em", rng=rng, resamples=resamples, fertility_override=permuted.tolist()
    )
    claims = shuffled.excludes_zero_positively() and shuffled.estimate >= 3.0
    return {
        "true_fertility_fit": _slope_receipt(true_fit),
        "permuted_fertility_fit": _slope_receipt(shuffled),
        "expected": "the clock world's slope vanishes when fertility labels are permuted across "
        "languages; the true labels recover it",
        "gate": (not claims) and true_fit.excludes_zero_positively(),
    }


def _fit(
    estimate: float, se: float, scale: str = "em", marginal_lower: float | None = None
) -> SlopeFit:
    half = 1.96 * se
    return SlopeFit(
        scale=scale,
        estimate=estimate,
        standard_error=se,
        ols_lower=estimate - half,
        ols_upper=estimate + half,
        bootstrap_lower=estimate - half,
        bootstrap_upper=estimate + half,
        lower=estimate - half,
        upper=estimate + half,
        resource_estimate=0.0,
        marginal_estimate=estimate,
        marginal_lower=estimate - half if marginal_lower is None else marginal_lower,
        marginal_upper=estimate + half,
        n_languages=16,
        resamples=100,
    )


def case_kill_and_hold_semantics() -> dict[str, Any]:
    k2_fires = k2_pooled_kill({"qwen": _fit(0.4, 1.0), "rwkv7": _fit(-0.3, 1.2)})
    k2_silent = k2_pooled_kill({"qwen": _fit(6.0, 1.5), "rwkv7": _fit(5.0, 1.5)})
    k9 = k9_sign_disagreement(_fit(5.0, 1.0), _fit(-4.0, 1.0))
    k9_silent = k9_sign_disagreement(_fit(5.0, 1.0), _fit(4.0, 1.0))
    k8 = k8_resourcedness_kill(_fit(1.0, 1.5, marginal_lower=2.0))
    k8_silent = k8_resourcedness_kill(_fit(6.0, 1.0))
    k7 = k7_ceiling_hold(96.5)
    k7_silent = k7_ceiling_hold(88.0)
    k7b = k7b_floor_hold(55.0)
    k7b_silent = k7b_floor_hold(72.0)
    languages = [name for name, _, _ in GRID_COVARIATES]
    redraw = dict.fromkeys(languages, 5.0)
    floors = dict.fromkeys(languages, 70.0)
    for language in ("mya", "tam", "ben", "hin", "ell"):
        floors[language] = 40.0
    k10 = k10_language_exclusion(redraw, floors)
    k10_silent = k10_language_exclusion(redraw, dict.fromkeys(languages, 70.0))
    fallback = {
        "both": k10b_subject_fallback(qwen_carries_primary=True, rwkv7_carries_primary=True),
        "qwen_only": k10b_subject_fallback(qwen_carries_primary=True, rwkv7_carries_primary=False),
        "rwkv7_only": k10b_subject_fallback(qwen_carries_primary=False, rwkv7_carries_primary=True),
        "neither": k10b_subject_fallback(qwen_carries_primary=False, rwkv7_carries_primary=False),
    }
    high = ("pol", "fin", "hun", "ukr", "hin", "ell", "ben", "tam")
    k3 = k3_uniform_effect_kill(dict.fromkeys(high, 1.0), dict.fromkeys(high, 1.5))
    k3_silent = k3_uniform_effect_kill(dict.fromkeys(high, 6.0), dict.fromkeys(high, 1.5))
    gaps = {"tam": 12.0, "ben": 11.0, "tha": 11.5, "kor": 10.0, "zho-CN": 12.5, "msa": 9.5}
    k4 = k4_script_gap_kill(gaps)
    k4_silent = k4_script_gap_kill({**gaps, "tha": 2.0, "kor": 1.0, "zho-CN": 3.0, "msa": 2.5})
    checks = {
        "k2_fires_on_two_null_subjects": k2_fires.verdict,
        "k2_silent_on_two_positive_subjects": not k2_silent.verdict,
        "k9_fires_on_opposite_signs": k9.verdict,
        "k9_silent_on_agreeing_signs": not k9_silent.verdict,
        "k8_fires_when_only_marginal_excludes_zero": k8.verdict,
        "k8_silent_when_partial_excludes_zero": not k8_silent.verdict,
        "k7_fires_at_96p5": k7.verdict,
        "k7_silent_at_88": not k7_silent.verdict,
        "k7b_fires_at_55": k7b.verdict,
        "k7b_silent_at_72": not k7b_silent.verdict,
        "k10_five_exclusions_leave_eleven_cannot_carry": k10.verdict
        and k10.statistics["remaining"] == 11.0,
        "k10_silent_with_all_above_floor": not k10_silent.verdict,
        "k10b_fallback_strings_distinct": len(set(fallback.values())) == 4,
        "k3_fires_on_uniform_effect": k3.verdict,
        "k3_silent_on_interaction": not k3_silent.verdict,
        "k4_fires_when_controls_share_the_gap": k4.verdict,
        "k4_silent_when_controls_differ": not k4_silent.verdict,
    }
    return {
        "checks": checks,
        "k2_statistics": k2_fires.statistics,
        "k10_excluded": k10.note,
        "k10b_fallback": fallback,
        "expected": "every registered kill, hold and exclusion fires on its registered trigger and "
        "stays silent otherwise",
        "gate": all(checks.values()),
    }


def case_degenerate_inputs(rng: np.random.Generator) -> dict[str, Any]:
    good_ref = rng.random(50) < 0.6
    good_dose = rng.random(50) < 0.7
    ids, _ = _episode_sentence_ids()
    bad_mask = sentence_window_mask(ids).copy()
    bad_mask[5, :] = False
    grid = _grid()

    def few_languages() -> None:
        cells = [
            CommonDoseCell(c.language, c.fertility, c.cc_share_percent, good_ref, good_dose)
            for c in grid[:3]
        ]
        fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=50)

    def constant_fertility() -> None:
        cells = [
            CommonDoseCell(c.language, 1.0, c.cc_share_percent, good_ref, good_dose)
            for c in grid[:6]
        ]
        fit_partial_fertility_slope(cells, scale="em", rng=rng, resamples=50)

    attempts: dict[str, Callable[[], object]] = {
        "non_positive_decay_ratio": lambda: constant_decay_surgery(np.full(4, -0.1), 0.0),
        "positive_log_decay_rejected": lambda: constant_decay_surgery(np.array([0.1, -0.1]), 2.0),
        "write_gate_outside_unit_interval": lambda: write_surgery(np.array([0.5, 1.5]), 2.0),
        "nan_gate_rejected": lambda: forgetting_mass(np.array([-0.1, np.nan])),
        "unpaired_em_arrays": lambda: CommonDoseCell("x", 1.5, 1.0, good_ref, good_dose[:-1]),
        "non_positive_cc_share": lambda: CommonDoseCell("x", 1.5, 0.0, good_ref, good_dose),
        "too_few_languages_for_two_regressor_fit": few_languages,
        "constant_fertility_not_identified": constant_fertility,
        "mask_row_without_permitted_key": lambda: masked_attention(
            rng.standard_normal((ids.size, 4)),
            rng.standard_normal((ids.size, 4)),
            rng.standard_normal((ids.size, 4)),
            bad_mask,
        ),
        "decreasing_sentence_ids": lambda: sentence_window_mask(np.array([0, 1, 0])),
        "reference_fertility_not_one": lambda: build_gate_ledger(
            {"en": np.full(3, -0.1), "x": np.full(6, -0.1)},
            {"en": np.full(3, 0.5), "x": np.full(6, 0.5)},
            {"en": 1.2, "x": 2.0},
        ),
        "span_pair_of_identical_spans": lambda: span_parity_loss(
            np.full(6, -0.1),
            np.full(6, 0.5),
            ((0, 3), (3, 6)),
            ((0, 0),),
            anchor_span=0,
            anchor_value=-0.1,
        ),
        "world_kind_unknown": lambda: DoseResponseWorld("saturating"),
    }
    outcomes: dict[str, bool] = {}
    for name, attempt in attempts.items():
        try:
            attempt()
        except GateContractError:
            outcomes[name] = True
        else:
            outcomes[name] = False
    return {
        "rejected": outcomes,
        "expected": "every degenerate input raises GateContractError instead of producing a number",
        "gate": all(outcomes.values()),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def run_doctor(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    rng = np.random.default_rng(args.seed)
    config = RecallSimulatorConfig(per_token_log_decay=-0.005, readout_noise=0.12)
    cases: dict[str, dict[str, Any]] = {}
    cases["identity_surgery_r1_and_causality"] = case_identity_surgery(rng)
    cases["token_duplication_scales_forgetting_mass"] = case_token_duplication(
        rng, config, args.simulator_episodes
    )
    cases["ledger_parity_positive_control"] = case_ledger_positive_control()
    cases["ledger_warp_invariant_negative_control"] = case_ledger_negative_control()
    cases["prefix_blind_window_zero_gradient"] = case_prefix_blind_window(rng)
    cases["query_only_mask_is_not_prefix_blind"] = case_query_only_mask(rng)
    cases["leaky_window_tamper_detected"] = case_leaky_window_tamper(rng)
    cases["span_parity_loss_gradient_and_invariances"] = case_span_parity_loss(rng)
    positive, negative = case_mechanistic_positive_control(
        rng, config, args.simulator_episodes, args.resamples
    )
    cases["mechanistic_recall_positive_control"] = positive
    cases["mechanistic_identity_negative_control"] = negative
    for name in ("clock", "headroom", "identity", "null"):
        cases[f"parametric_{name}_world"] = case_parametric_world(
            name, rng, args.dose_episodes, args.resamples, args.tally_seeds, args.seed
        )
    cases["permuted_fertility_negative_control"] = case_permuted_fertility(
        rng, args.dose_episodes, args.resamples
    )
    cases["kill_hold_and_exclusion_semantics"] = case_kill_and_hold_semantics()
    cases["degenerate_inputs_rejected"] = case_degenerate_inputs(rng)
    gates = {name: bool(case["gate"]) for name, case in cases.items()}
    for case in cases.values():
        case["gate"] = bool(case["gate"])
    elapsed = time.perf_counter() - started
    implementation = PROJECT_ROOT / "harness" / "semantic_clock_gate_parity.py"
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "doctor": DOCTOR_NAME,
        "status": PASS_STATUS if all(gates.values()) else FAIL_STATUS,
        "evidence_grade": EVIDENCE_GRADE,
        "simulator_config": {
            "facts": config.facts,
            "distractor_sentences": config.distractor_sentences,
            "english_tokens_per_sentence": config.english_tokens_per_sentence,
            "key_dim": config.key_dim,
            "value_dim": config.value_dim,
            "per_token_log_decay": config.per_token_log_decay,
            "fact_write_gate": config.fact_write_gate,
            "distractor_write_gate": config.distractor_write_gate,
            "readout_noise": config.readout_noise,
            "episodes": args.simulator_episodes,
        },
        "decision_rule": {
            "minimum_em_points_per_log_fertility": 3.0,
            "logit_minimum_for_reported_sensitivity": 0.15,
            "p3": "cross-language EM-point slope clears AND re-segmented English slope clears AND "
            "|tracking residual slope| below the minimum; K11 fires on a cleared cross-language "
            "slope that token count does not reproduce; residual estimate outside the band with "
            "an interval reaching it is the inconclusive second-episode band",
        },
        "cases": cases,
        "gates": gates,
        "covariate_provenance": COVARIATE_PROVENANCE,
        "provenance": {
            "implementation": "harness/semantic_clock_gate_parity.py",
            "implementation_sha256": hashlib.sha256(implementation.read_bytes()).hexdigest(),
            "doctor_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "seed": args.seed,
            "dose_episodes": args.dose_episodes,
            "resamples": args.resamples,
            "tally_seeds": args.tally_seeds,
            "elapsed_seconds": elapsed,
            "executed_on": "CPU only; not the H100 node, not a container",
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


def main() -> int:
    args = parse_args()
    payload = run_doctor(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
