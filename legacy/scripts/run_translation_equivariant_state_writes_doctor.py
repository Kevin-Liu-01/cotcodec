#!/usr/bin/env python3
"""Phase-0 CPU doctor for Direction 22 (translation-equivariant state writes).

Runs the registered synthetic cases on a seeded NumPy two-layer GDN and random
projections, prints a JSON receipt and writes it to ``--output``. Every number
in the receipt is a synthetic-case number. A PASS proves that the pre-registered
phase-0 objects and gates are executable and behave as registered on these
inputs; it proves nothing about any model, corpus, or prediction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.translation_equivariant_state_writes import (  # noqa: E402
    HeadSpan,
    PrefixFloorLedger,
    PromotionRuleConfig,
    RecallPrompt,
    StateWriteContractError,
    TinyGDNConfig,
    TinyGDNModel,
    build_recall_manifest,
    check_write_identity,
    distinctness_statistic,
    exact_match,
    fla_cross_check,
    flat_cosine,
    flatten_spans,
    flatten_states,
    lookup_reader,
    manifest_sha256,
    object_cosine_ledger,
    projection_pooling,
    pure_write,
    retrieval_impossible_control,
    segment_delta,
    simulate_promotion_rules,
    states_bitwise_identical,
    surface_disjoint,
    value_permutation_control,
    write_norm_falsifier_fires,
    write_norm_shrinkage,
    zero_state_write,
)

DOCTOR_NAME = "translation-equivariant-state-writes-phase0"
STATUS_PASS = "PHASE0_OBJECT_DOCTOR_PASS"
STATUS_FAIL = "PHASE0_OBJECT_DOCTOR_FAIL"
EVIDENCE_GRADE = (
    "executability-and-gate-semantics-only: every number in this receipt is a synthetic-case "
    "number from a seeded NumPy two-layer GDN with random weights, random projections, integer "
    "stand-in keys and an assumed seed-noise model; no checkpoint, corpus, tokenizer, fla kernel "
    "or GPU was touched; a PASS proves that the pre-registered phase-0 objects (W, D, P), gates "
    "(fp64 identity, bitwise prefix state, prefix floor, G2 distinctness, leakage controls, "
    "write-norm falsifier, promotion rule) and their rejections are executable and behave as "
    "registered on these inputs, and proves nothing about any model, FLORES+, or predictions "
    "P0a-P2"
)
IDENTITY_TOLERANCE = 1e-10
DISTINCTNESS_THRESHOLD = 0.9
PREFIX_LENGTH = 40
SPAN_LENGTH = 12
PAIRS = 24
SHRINKAGE_LADDER = (1.0, 0.1, 0.01)
REGIME_ALPHAS = (0.999, 0.99, 0.95, 0.9)
REGIME_BETAS = (0.05, 0.3, 0.8)
REGIME_SPAN = 30
REGIME_DIM = 64
REGIME_HEADS = 8
RECALL_PROMPTS = 600
RECALL_FACTS = 8
RECALL_KEY_POOL = 500
RULE_DELTAS = (0.0, 3.0, 5.0, 8.0, 10.0)
SURFACE_CASES: tuple[tuple[str, str, bool], ...] = (
    ("The cat sat on the mat", "Die Katze saß auf der Matte", True),
    ("Berlin fell in 1990", "Berlín cayó en 1990", False),
    ("Information is power", "Informationen sind Macht", False),
    ("abc marks the spot", "abc markiert den Ort", False),
    ("an ab", "ab an", True),
    ("ＴＯＫＹＯ station", "tokyo bahnhof", False),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if args.seed < 0:
        parser.error("--seed must be non-negative")
    return args


def _realize_pairs(
    model: TinyGDNModel,
    rng: np.random.Generator,
    prefix_states: np.ndarray,
    *,
    shuffled: bool,
) -> tuple[list[tuple[HeadSpan, ...]], list[tuple[HeadSpan, ...]], list[tuple[HeadSpan, ...]]]:
    """Realize anchor / positive / floor spans behind the shared prefix state.

    Positive spans are the language-B translation of the anchor (``shuffled=False``)
    or the translation of a different pair's anchor (``shuffled=True``); floor spans
    are always a fresh same-prefix language-B non-translation.
    """

    offset = model.config.language_offset
    contents = [rng.integers(0, offset, size=SPAN_LENGTH) for _pair in range(PAIRS)]
    order = np.roll(np.arange(PAIRS), 1) if shuffled else np.arange(PAIRS)
    anchors, positives, floors = [], [], []
    for pair in range(PAIRS):
        anchors.append(flatten_spans(model.forward(contents[pair], prefix_states)))
        positives.append(
            flatten_spans(model.forward(model.translate(contents[order[pair]]), prefix_states))
        )
        floor_content = model.translate(rng.integers(0, offset, size=SPAN_LENGTH))
        floors.append(flatten_spans(model.forward(floor_content, prefix_states)))
    return anchors, positives, floors


def _scaled(spans: list[tuple[HeadSpan, ...]], scale: float) -> list[tuple[HeadSpan, ...]]:
    if scale == 1.0:
        return spans
    return [tuple(span.with_scaled_values(scale) for span in heads) for heads in spans]


def _pooling(_state: np.ndarray, span: HeadSpan) -> np.ndarray:
    return projection_pooling(span)


def run_doctor(seed: int) -> dict[str, Any]:
    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    config = TinyGDNConfig(seed=seed)
    model = TinyGDNModel(config)
    offset = config.language_offset
    cases: dict[str, Any] = {}
    gates: dict[str, bool] = {}

    # --- positive control: fp64 identity W == S_{S0=0}(a) on the 2-layer GDN
    prefix = rng.integers(0, offset, size=PREFIX_LENGTH)
    prefix_states = model.forward(prefix).final_states
    span_tokens = rng.integers(0, offset, size=SPAN_LENGTH)
    span_trace = model.forward(span_tokens, prefix_states)
    spans = flatten_spans(span_trace)
    states = flatten_states(prefix_states)
    identity_reports = [
        check_write_identity(state, span, IDENTITY_TOLERANCE)
        for state, span in zip(states, spans, strict=True)
    ]
    carry_share = []
    for state, span in zip(states, spans, strict=True):
        delta = segment_delta(state, span)
        write = pure_write(state, span)
        carry_share.append(float(np.linalg.norm(delta - write) / np.linalg.norm(delta)))
    cases["write_identity_fp64"] = {
        "description": "W(a|c) = S(c+a) - S_{v=0}(c,a) must equal the zero-initial-state run",
        "layers": config.layers,
        "heads_per_layer": config.heads,
        "prefix_tokens": PREFIX_LENGTH,
        "span_tokens": SPAN_LENGTH,
        "max_abs_residual": max(report.max_abs_residual for report in identity_reports),
        "max_abs_write": max(report.max_abs_write for report in identity_reports),
        "tolerance": IDENTITY_TOLERANCE,
        "prefix_carry_share_of_D": carry_share,
        "passed": all(report.passed for report in identity_reports),
    }
    gates["write_identity_fp64"] = cases["write_identity_fp64"]["passed"]

    # --- positive control + perturbation: S(c) bitwise identical across a pair
    repeated = model.forward(prefix).final_states
    perturbed_prefix = prefix.copy()
    perturbed_prefix[PREFIX_LENGTH // 2] = (perturbed_prefix[PREFIX_LENGTH // 2] + 1) % offset
    perturbed_states = model.forward(perturbed_prefix).final_states
    identical = states_bitwise_identical(prefix_states, repeated)
    detected = not states_bitwise_identical(prefix_states, perturbed_states)
    cases["prefix_state_bitwise_identity"] = {
        "description": "two forward passes of the shared prefix agree bitwise; a one-token "
        "prefix change is detected",
        "repeated_pass_identical": identical,
        "perturbed_prefix_detected": detected,
        "passed": identical and detected,
    }
    gates["prefix_state_bitwise_identity"] = identical and detected

    # --- positive control: prefix-floor ledger on translation pairs (W, D, P)
    anchors, positives, floors = _realize_pairs(model, rng, prefix_states, shuffled=False)
    ledgers = {}
    for name, object_fn in (("W", pure_write), ("D", segment_delta), ("P", _pooling)):
        pair_cos, floor_cos = object_cosine_ledger(object_fn, states, anchors, positives, floors)
        ledgers[name] = PrefixFloorLedger(name, pair_cos, floor_cos)
    cases["prefix_floor_ledger_translation_pairs"] = {
        "description": "translation-pair cosine must exceed the same-prefix non-translation "
        "floor by >= 0.05 in >= 2/3 of heads (registered for W; D and P reported)",
        "pairs": PAIRS,
        "translation_noise": config.translation_noise,
        "ledgers": {name: ledger.summary() for name, ledger in ledgers.items()},
        "passed": ledgers["W"].passed,
    }
    gates["prefix_floor_ledger_translation_pairs"] = ledgers["W"].passed

    # --- negative control: shuffled pairing must fail the W ledger
    shuffled_anchors, shuffled_positives, shuffled_floors = _realize_pairs(
        model, rng, prefix_states, shuffled=True
    )
    pair_cos, floor_cos = object_cosine_ledger(
        pure_write, states, shuffled_anchors, shuffled_positives, shuffled_floors
    )
    shuffled_ledger = PrefixFloorLedger("W-shuffled", pair_cos, floor_cos)
    cases["prefix_floor_ledger_shuffled_pairing"] = {
        "description": "pairing each anchor with another pair's translation must fail the "
        "W prefix-floor gate",
        "ledger": shuffled_ledger.summary(),
        "gate_rejected": not shuffled_ledger.passed,
        "passed": not shuffled_ledger.passed,
    }
    gates["prefix_floor_ledger_shuffled_pairing"] = not shuffled_ledger.passed

    # --- counterfactual: write shrinkage exposes the wave-2 prefix shortcut in D, not W
    ladder = []
    reference_norm = float(
        np.mean([np.linalg.norm(zero_state_write(span)) for heads in anchors for span in heads])
    )
    base_margins = ledgers["W"].head_margins
    for scale in SHRINKAGE_LADDER:
        row: dict[str, Any] = {"value_scale": scale}
        for name, object_fn in (("W", pure_write), ("D", segment_delta)):
            pair_cos, floor_cos = object_cosine_ledger(
                object_fn,
                states,
                _scaled(anchors, scale),
                _scaled(positives, scale),
                _scaled(floors, scale),
            )
            ledger = PrefixFloorLedger(f"{name}-scaled-{scale}", pair_cos, floor_cos)
            row[name] = ledger.summary()
        current_norm = float(
            np.mean(
                [
                    np.linalg.norm(zero_state_write(span))
                    for heads in _scaled(anchors, scale)
                    for span in heads
                ]
            )
        )
        shrinkage = write_norm_shrinkage(reference_norm, current_norm)
        row["mean_write_norm"] = current_norm
        row["write_norm_shrinkage"] = shrinkage
        row["write_norm_falsifier_fires"] = write_norm_falsifier_fires(shrinkage)
        row["W_margin_drift_from_unscaled"] = float(
            np.max(np.abs(np.asarray(row["W"]["head_margins"]) - base_margins))
        )
        row["D_floor_elevation_from_unscaled"] = float(
            row["D"]["mean_floor_cosine"] - ledgers["D"].summary()["mean_floor_cosine"]
        )
        ladder.append(row)
    final = ladder[-1]
    shrinkage_gate = (
        all(row["W"]["passed"] for row in ladder)
        and all(row["W_margin_drift_from_unscaled"] <= 1e-9 for row in ladder)
        and final["D"]["mean_floor_cosine"] >= 0.8
        and final["D_floor_elevation_from_unscaled"] >= 0.3
        and final["write_norm_falsifier_fires"]
        and not ladder[0]["write_norm_falsifier_fires"]
    )
    cases["wave2_shortcut_write_shrinkage"] = {
        "description": "scaling the span values leaves W's cosines unchanged (W is linear in v) "
        "while D's same-prefix non-translation floor rises toward 1 because the shared prefix "
        "carry S_{v=0}(c,a) - S(c) dominates D: a loss on D is reducible by shrinking writes, a "
        "loss on W is not; the mean ||W|| falsifier fires above 30 percent. The erase term "
        "(I - beta k k^T) keeps a content-dependent residue in D, so D's margin need not vanish",
        "ladder": ladder,
        "passed": shrinkage_gate,
    }
    gates["wave2_shortcut_write_shrinkage"] = shrinkage_gate

    # --- causality perturbation: later tokens cannot change W; a span token must
    suffix = rng.integers(0, offset, size=8)
    extended = model.forward(np.concatenate([prefix, span_tokens, suffix]), trajectory=True)
    assert extended.trajectory is not None
    mid_states = extended.trajectory[PREFIX_LENGTH + SPAN_LENGTH]
    direct_states = model.forward(np.concatenate([prefix, span_tokens])).final_states
    later_token_effect = float(np.max(np.abs(mid_states - direct_states)))
    edited_span = span_tokens.copy()
    edited_span[SPAN_LENGTH // 2] = (edited_span[SPAN_LENGTH // 2] + 1) % offset
    edited_spans = flatten_spans(model.forward(edited_span, prefix_states))
    in_span_effect = float(
        min(
            np.max(np.abs(pure_write(state, edited) - pure_write(state, original)))
            for state, edited, original in zip(states, edited_spans, spans, strict=True)
        )
    )
    causal = later_token_effect <= 1e-12 and in_span_effect > 1e-6
    cases["causality_perturbation"] = {
        "description": "appending tokens after the span leaves the span-end state unchanged; "
        "editing one span token changes W in every head",
        "later_token_max_effect": later_token_effect,
        "in_span_edit_min_effect": in_span_effect,
        "passed": causal,
    }
    gates["causality_perturbation"] = causal

    # --- gate G2: distinctness cos(W, P) regime sweep and the tiny model's own value
    sweep = []
    for alpha in REGIME_ALPHAS:
        for beta in REGIME_BETAS:
            regime_spans = []
            for _head in range(REGIME_HEADS):
                keys = rng.standard_normal((REGIME_SPAN, REGIME_DIM))
                keys /= np.linalg.norm(keys, axis=1, keepdims=True)
                regime_spans.append(
                    HeadSpan(
                        keys,
                        rng.standard_normal((REGIME_SPAN, REGIME_DIM)),
                        np.full(REGIME_SPAN, beta),
                        np.full(REGIME_SPAN, alpha),
                    )
                )
            report = distinctness_statistic(regime_spans, DISTINCTNESS_THRESHOLD)
            sweep.append(
                {
                    "alpha": alpha,
                    "beta": beta,
                    "mean_cos_W_P": report.mean_cosine,
                    "contrast_interpretable": report.passed,
                }
            )
    slow = next(r for r in sweep if r["alpha"] == 0.999 and r["beta"] == 0.05)
    fast = next(r for r in sweep if r["alpha"] == 0.9 and r["beta"] == 0.8)
    tiny_report = distinctness_statistic(spans, DISTINCTNESS_THRESHOLD)
    g2_gate = (not slow["contrast_interpretable"]) and fast["contrast_interpretable"]
    cases["distinctness_g2_regime_sweep"] = {
        "description": "mean cos(W, P) over heads on random unit keys and Gaussian values at "
        "sentence length; the gate must fire in the slow-decay small-beta regime and pass in "
        "the fast-decay large-beta regime",
        "span_tokens": REGIME_SPAN,
        "dims": REGIME_DIM,
        "heads": REGIME_HEADS,
        "threshold": DISTINCTNESS_THRESHOLD,
        "sweep": sweep,
        "tiny_model_realized_spans": tiny_report.summary(),
        "passed": g2_gate,
    }
    gates["distinctness_g2_regime_sweep"] = g2_gate

    # --- leakage controls: synthetic TP-MQAR-v2 with an oracle lookup reader
    recall_rng = np.random.default_rng(seed + 1)
    manifest = build_recall_manifest(
        recall_rng,
        prompts=RECALL_PROMPTS,
        facts_per_prompt=RECALL_FACTS,
        key_pool=RECALL_KEY_POOL,
    )
    impossible = [
        retrieval_impossible_control(prompt, recall_rng, key_pool=RECALL_KEY_POOL)
        for prompt in manifest
    ]
    permuted = [value_permutation_control(prompt, recall_rng) for prompt in manifest]
    positive_em = exact_match(manifest, lookup_reader)
    impossible_em = exact_match(impossible, lookup_reader)
    permuted_em = exact_match(permuted, lookup_reader)
    leaked_em = exact_match(permuted, lookup_reader, against="leaked_answer")
    leakage_gate = (
        positive_em == 1.0 and impossible_em <= 0.01 and permuted_em == 1.0 and leaked_em <= 0.01
    )
    cases["tp_mqar_leakage_controls"] = {
        "description": "oracle lookup reader: positive control at 1.0; retrieval-impossible "
        "and value-permutation-leak scores at chance (1e-4 per prompt)",
        "prompts": RECALL_PROMPTS,
        "facts_per_prompt": RECALL_FACTS,
        "key_pool": RECALL_KEY_POOL,
        "chance_em": 1e-4,
        "positive_control_em": positive_em,
        "retrieval_impossible_em": impossible_em,
        "value_permutation_context_em": permuted_em,
        "value_permutation_leaked_em": leaked_em,
        "sealed_manifest_sha256": manifest_sha256(manifest),
        "keys_are": "integer stand-ins for FLORES+ sentence ids; no text, no tokenizer",
        "passed": leakage_gate,
    }
    gates["tp_mqar_leakage_controls"] = leakage_gate

    # --- surface-disjoint filter on fixed string cases
    surface_rows = []
    for left, right, expected in SURFACE_CASES:
        observed = surface_disjoint(left, right)
        surface_rows.append(
            {"left": left, "right": right, "expected": expected, "observed": observed}
        )
    surface_gate = all(row["expected"] == row["observed"] for row in surface_rows)
    cases["surface_disjoint_filter"] = {
        "description": "NFKC + casefold token, digit-string and character-4-gram filter "
        "(tokenizer-free stand-in for the subword clause)",
        "cases": surface_rows,
        "passed": surface_gate,
    }
    gates["surface_disjoint_filter"] = surface_gate

    # --- promotion-rule operating characteristics (Reviewer B, wave 4)
    rule_config = PromotionRuleConfig()
    points = simulate_promotion_rules(rule_config, RULE_DELTAS, np.random.default_rng(seed + 2))
    by_delta = {point.delta: point for point in points}
    monte_carlo_ok = all(
        abs(point.all_pairs_promote - point.all_pairs_analytic) <= 0.005 for point in points
    )
    rule_gate = (
        monte_carlo_ok
        and by_delta[5.0].all_pairs_promote <= 0.15
        and by_delta[5.0].seed_mean_promote >= 0.45
        and by_delta[0.0].seed_mean_promote <= 0.01
        and by_delta[8.0].seed_mean_promote >= 0.9
    )
    cases["promotion_rule_operating_characteristics"] = {
        "description": "Monte-Carlo pass/kill/underpowered probabilities of the wave-4 rule "
        "(every seed pair >= 5) and the wave-5 rule (seed mean >= 5, all pairs positive, "
        "pooled prompt-clustered CI excludes 0; kill on any negative pair or negative mean) "
        "under the assumed seed-paired SD of 3 EM points",
        "assumptions": {
            "minimum_effect_em_points": rule_config.minimum_effect,
            "seed_paired_sd_em_points": rule_config.seed_sd,
            "seeds": rule_config.seeds,
            "prompts_per_seed": rule_config.prompts_per_seed,
            "prompt_paired_sd_em_points": rule_config.prompt_sd_points,
            "pooled_ci_half_width_em_points": rule_config.pooled_half_width,
            "draws": rule_config.draws,
            "noise_model_status": "assumption; seed SD at 57M is unknown (proposal C28)",
        },
        "operating_points": [point.summary() for point in points],
        "monte_carlo_matches_closed_form": monte_carlo_ok,
        "passed": rule_gate,
    }
    gates["promotion_rule_operating_characteristics"] = rule_gate

    # --- degenerate-input rejection
    unit = np.eye(4)[:3]
    valid_keys = unit / np.linalg.norm(unit, axis=1, keepdims=True)
    valid_values = np.ones((3, 2))
    rejections: list[tuple[str, Any]] = [
        ("alpha above one", lambda: HeadSpan(valid_keys, valid_values, [0.5] * 3, [1.0, 1.5, 1.0])),
        ("alpha zero", lambda: HeadSpan(valid_keys, valid_values, [0.5] * 3, [0.0, 0.9, 0.9])),
        ("beta above one", lambda: HeadSpan(valid_keys, valid_values, [1.5, 0.5, 0.5], [0.9] * 3)),
        ("nan key", lambda: HeadSpan(valid_keys * np.nan, valid_values, [0.5] * 3, [0.9] * 3)),
        ("length mismatch", lambda: HeadSpan(valid_keys, valid_values[:2], [0.5] * 3, [0.9] * 3)),
        ("empty span", lambda: HeadSpan(np.zeros((0, 4)), np.zeros((0, 2)), [], [])),
        (
            "state shape mismatch",
            lambda: pure_write(
                np.zeros((4, 2)), HeadSpan(valid_keys, valid_values, [0.5] * 3, [0.9] * 3)
            ),
        ),
        ("zero-norm cosine", lambda: flat_cosine(np.zeros((2, 2)), np.ones((2, 2)))),
        ("token outside vocabulary", lambda: model.forward([config.vocab_size])),
        (
            "retrieval-impossible query present",
            lambda: RecallPrompt(((1, "0001"), (2, "0002")), 1, "0001", "retrieval-impossible"),
        ),
        ("odd vocabulary", lambda: TinyGDNConfig(vocab_size=7)),
        ("non-positive minimum effect", lambda: PromotionRuleConfig(minimum_effect=0.0)),
    ]
    rejection_rows = []
    for label, action in rejections:
        try:
            action()
        except StateWriteContractError as exc:
            rejection_rows.append({"input": label, "rejected": True, "message": str(exc)})
        else:
            rejection_rows.append({"input": label, "rejected": False, "message": ""})
    rejection_gate = all(row["rejected"] for row in rejection_rows)
    cases["degenerate_input_rejection"] = {
        "description": "every degenerate input must raise StateWriteContractError",
        "cases": rejection_rows,
        "passed": rejection_gate,
    }
    gates["degenerate_input_rejection"] = rejection_gate

    # --- informational: fla cross-check (skipped without torch + fla + CUDA)
    informational = {"fla_cross_check": fla_cross_check(spans[0], states[0])}

    status = STATUS_PASS if all(gates.values()) else STATUS_FAIL
    implementation = PROJECT_ROOT / "harness" / "translation_equivariant_state_writes.py"
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "doctor": DOCTOR_NAME,
        "direction": "22-translation-equivariant-state-writes",
        "status": status,
        "evidence_grade": EVIDENCE_GRADE,
        "numbers_are": "synthetic-case numbers; not measurements of any model or corpus",
        "config": {
            "seed": seed,
            "tiny_gdn": {
                "vocab_size": config.vocab_size,
                "hidden": config.hidden,
                "layers": config.layers,
                "heads": config.heads,
                "key_dim": config.key_dim,
                "value_dim": config.value_dim,
                "translation_noise": config.translation_noise,
                "decay_rate": config.decay_rate,
                "beta_bias": config.beta_bias,
            },
            "identity_tolerance": IDENTITY_TOLERANCE,
            "distinctness_threshold": DISTINCTNESS_THRESHOLD,
        },
        "cases": cases,
        "gates": gates,
        "informational": informational,
        "pending_before_phase0_gpu": [
            "W-vs-P and W-vs-D reads on the registered qwen3.5-4b-base recurrent states in the "
            "rebuilt fla image (container smoke not run)",
            "cos(W, P) on the 57M A0 hybrid at initialization: the 57M model definition does "
            "not exist in the repository yet",
            "TP-MQAR-v2 builder over FLORES+ devtest/dev text with the Qwen3.5 and 57M "
            "tokenizers (gated terms not accepted; this doctor uses integer stand-in keys)",
            "fla chunk_gated_delta_rule cross-check on CUDA (skipped here; never executed)",
            "FLORES+ deduplication against the phase-1 streams; per-arm selection ledger format",
        ],
        "provenance": {
            "implementation_sha256": hashlib.sha256(implementation.read_bytes()).hexdigest(),
            "doctor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "numpy_version": np.__version__,
            "python_version": sys.version.split()[0],
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    payload["wall_seconds"] = round(time.perf_counter() - started, 3)
    payload["hash_note"] = "payload_sha256 covers every key except wall_seconds and hash_note"
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_doctor(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == STATUS_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
