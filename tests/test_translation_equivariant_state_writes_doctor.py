from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from harness.translation_equivariant_state_writes import (
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
    prefix_carry,
    projection_pooling,
    pure_write,
    retrieval_impossible_control,
    run_gdn_head,
    segment_delta,
    simulate_promotion_rules,
    states_bitwise_identical,
    surface_disjoint,
    value_permutation_control,
    write_norm_falsifier_fires,
    write_norm_shrinkage,
    zero_state_write,
)
from scripts import run_translation_equivariant_state_writes_doctor as doctor


def random_span(rng: np.random.Generator, length: int = 12, dim: int = 8) -> HeadSpan:
    keys = rng.standard_normal((length, dim))
    keys /= np.linalg.norm(keys, axis=1, keepdims=True)
    return HeadSpan(
        keys,
        rng.standard_normal((length, dim)),
        rng.uniform(0.1, 0.9, size=length),
        rng.uniform(0.9, 1.0, size=length),
    )


def test_pure_write_equals_zero_state_run_to_fp64_tolerance() -> None:
    rng = np.random.default_rng(0)
    span = random_span(rng)
    prefix_state = rng.standard_normal(span.state_shape) * 3.0
    report = check_write_identity(prefix_state, span)
    assert report.passed
    assert report.max_abs_residual < 1e-12
    assert report.max_abs_write > 0.1


def test_segment_delta_decomposes_into_write_plus_prefix_carry() -> None:
    rng = np.random.default_rng(1)
    span = random_span(rng)
    prefix_state = rng.standard_normal(span.state_shape)
    delta = segment_delta(prefix_state, span)
    reconstructed = pure_write(prefix_state, span) + prefix_carry(prefix_state, span) - prefix_state
    assert np.allclose(delta, reconstructed, atol=1e-12)


def test_tampered_counterfactual_breaks_the_identity() -> None:
    """Using the wave-2 object D instead of W is caught by the fp64 identity gate."""

    rng = np.random.default_rng(2)
    span = random_span(rng)
    prefix_state = rng.standard_normal(span.state_shape) * 3.0
    tampered_residual = np.max(np.abs(segment_delta(prefix_state, span) - zero_state_write(span)))
    assert tampered_residual > 1e-3
    genuine = check_write_identity(prefix_state, span)
    assert genuine.passed


def test_projection_pooling_matches_single_step_write() -> None:
    rng = np.random.default_rng(3)
    span = random_span(rng, length=1)
    expected = span.beta[0] * np.outer(span.values[0], span.keys[0])
    assert np.allclose(projection_pooling(span), expected)
    assert np.allclose(run_gdn_head(span), expected)


def test_distinctness_gate_fires_in_slow_decay_regime_and_passes_in_fast_decay() -> None:
    rng = np.random.default_rng(4)

    def regime(alpha: float, beta: float) -> list[HeadSpan]:
        spans = []
        for _head in range(4):
            keys = rng.standard_normal((30, 32))
            keys /= np.linalg.norm(keys, axis=1, keepdims=True)
            spans.append(
                HeadSpan(keys, rng.standard_normal((30, 32)), np.full(30, beta), np.full(30, alpha))
            )
        return spans

    slow = distinctness_statistic(regime(0.999, 0.05))
    fast = distinctness_statistic(regime(0.9, 0.8))
    assert slow.mean_cosine > 0.9 and not slow.passed
    assert fast.mean_cosine <= 0.9 and fast.passed


def test_prefix_floor_ledger_requires_two_thirds_of_heads() -> None:
    pair = np.array([[0.9, 0.9], [0.9, 0.9], [0.2, 0.2]])
    floor = np.array([[0.1, 0.1], [0.1, 0.1], [0.19, 0.19]])
    ledger = PrefixFloorLedger("W", pair, floor)
    assert ledger.heads_passing == 2 and ledger.required_heads == 2 and ledger.passed
    failing = PrefixFloorLedger("W", pair, np.full_like(floor, 0.88))
    assert not failing.passed
    with pytest.raises(StateWriteContractError):
        PrefixFloorLedger("W", pair, floor[:2])


def test_tiny_model_translation_pairs_pass_and_shuffled_pairs_fail() -> None:
    config = TinyGDNConfig(seed=7)
    model = TinyGDNModel(config)
    rng = np.random.default_rng(7)
    offset = config.language_offset
    prefix = rng.integers(0, offset, size=24)
    prefix_states = model.forward(prefix).final_states
    assert states_bitwise_identical(prefix_states, model.forward(prefix).final_states)
    states = flatten_states(prefix_states)
    contents = [rng.integers(0, offset, size=10) for _pair in range(8)]
    anchors = [flatten_spans(model.forward(content, prefix_states)) for content in contents]
    translations = [
        flatten_spans(model.forward(model.translate(content), prefix_states))
        for content in contents
    ]
    shuffled = translations[1:] + translations[:1]
    heads, pairs = len(states), len(contents)
    pair_cos = np.empty((heads, pairs))
    floor_cos = np.empty((heads, pairs))
    for head, state in enumerate(states):
        for pair in range(pairs):
            anchor = pure_write(state, anchors[pair][head])
            pair_cos[head, pair] = flat_cosine(anchor, pure_write(state, translations[pair][head]))
            floor_cos[head, pair] = flat_cosine(anchor, pure_write(state, shuffled[pair][head]))
    assert PrefixFloorLedger("W", pair_cos, floor_cos).passed
    assert not PrefixFloorLedger("W-shuffled", floor_cos, floor_cos).passed


def test_write_is_linear_in_values_so_cosines_survive_shrinkage() -> None:
    rng = np.random.default_rng(5)
    span = random_span(rng)
    other = random_span(rng)
    base = flat_cosine(zero_state_write(span), zero_state_write(other))
    shrunk = flat_cosine(
        zero_state_write(span.with_scaled_values(0.01)),
        zero_state_write(other.with_scaled_values(0.01)),
    )
    assert shrunk == pytest.approx(base, abs=1e-12)
    norm = float(np.linalg.norm(zero_state_write(span)))
    shrink = write_norm_shrinkage(
        norm, float(np.linalg.norm(zero_state_write(span.with_scaled_values(0.5))))
    )
    assert shrink == pytest.approx(0.5, abs=1e-12)
    assert write_norm_falsifier_fires(shrink) and not write_norm_falsifier_fires(0.1)


def test_degenerate_inputs_fail_closed() -> None:
    keys = np.eye(3)
    values = np.ones((3, 2))
    with pytest.raises(StateWriteContractError, match="alpha"):
        HeadSpan(keys, values, [0.5] * 3, [1.2, 0.9, 0.9])
    with pytest.raises(StateWriteContractError, match="beta"):
        HeadSpan(keys, values, [-0.1, 0.5, 0.5], [0.9] * 3)
    with pytest.raises(StateWriteContractError, match="finite"):
        HeadSpan(keys * np.nan, values, [0.5] * 3, [0.9] * 3)
    with pytest.raises(StateWriteContractError, match="shape"):
        pure_write(np.zeros((3, 2)), HeadSpan(keys, values, [0.5] * 3, [0.9] * 3))
    with pytest.raises(StateWriteContractError, match="zero-norm"):
        flat_cosine(np.zeros(4), np.ones(4))
    with pytest.raises(StateWriteContractError, match="vocabulary"):
        TinyGDNModel(TinyGDNConfig()).forward([999])
    with pytest.raises(StateWriteContractError, match="even"):
        TinyGDNConfig(vocab_size=9)


def test_recall_controls_score_at_chance_for_the_oracle_reader() -> None:
    rng = np.random.default_rng(11)
    manifest = build_recall_manifest(rng, prompts=200, facts_per_prompt=8, key_pool=100)
    impossible = [retrieval_impossible_control(p, rng, key_pool=100) for p in manifest]
    permuted = [value_permutation_control(p, rng) for p in manifest]
    assert exact_match(manifest, lookup_reader) == 1.0
    assert exact_match(impossible, lookup_reader) <= 0.01
    assert exact_match(permuted, lookup_reader) == 1.0
    assert exact_match(permuted, lookup_reader, against="leaked_answer") == 0.0
    with pytest.raises(StateWriteContractError, match="absent"):
        RecallPrompt(((1, "0001"), (2, "0002")), 1, "0001", "retrieval-impossible")
    with pytest.raises(StateWriteContractError, match="four ASCII digits"):
        RecallPrompt(((1, "001"),), 1, "001", "positive-control")


def test_surface_disjoint_filter_cases() -> None:
    assert surface_disjoint("The cat sat", "Die Katze saß")
    assert not surface_disjoint("Berlin 1990", "Berlín 1990")
    assert not surface_disjoint("Information", "Informationen")
    assert not surface_disjoint("abc here", "abc there")
    assert surface_disjoint("ab", "ab")


def test_promotion_rule_simulation_reproduces_closed_form() -> None:
    points = simulate_promotion_rules(
        PromotionRuleConfig(draws=100_000), (0.0, 5.0, 8.0), np.random.default_rng(3)
    )
    by_delta = {point.delta: point for point in points}
    assert by_delta[5.0].all_pairs_analytic == pytest.approx(0.125)
    assert by_delta[5.0].all_pairs_promote == pytest.approx(0.125, abs=0.01)
    assert by_delta[5.0].seed_mean_promote == pytest.approx(0.49, abs=0.02)
    assert by_delta[8.0].seed_mean_promote > 0.9
    assert by_delta[0.0].seed_mean_promote < 0.01
    for point in points:
        total = point.seed_mean_promote + point.seed_mean_kill + point.seed_mean_underpowered
        assert total == pytest.approx(1.0)


def test_fla_cross_check_is_skipped_without_torch_and_fla() -> None:
    pytest.importorskip("numpy")
    try:
        import fla  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        result = fla_cross_check(random_span(np.random.default_rng(0)))
        assert result["status"] == "skipped"
    else:  # pragma: no cover - only where fla is installed
        result = fla_cross_check(random_span(np.random.default_rng(0)))
        assert result["status"] in {"skipped", "executed"}


def test_full_doctor_run_writes_passing_receipt(tmp_path: Path) -> None:
    output = tmp_path / "phase0-doctor.json"
    assert doctor.main(["--output", str(output)]) == 0
    receipt = json.loads(output.read_text())
    assert receipt["status"] == doctor.STATUS_PASS
    assert all(receipt["gates"].values())
    assert receipt["evidence_grade"].startswith("executability-and-gate-semantics-only")
    assert "synthetic" in receipt["numbers_are"]
    assert receipt["cases"]["write_identity_fp64"]["max_abs_residual"] <= 1e-10
    assert receipt["cases"]["prefix_floor_ledger_shuffled_pairing"]["gate_rejected"]
    assert receipt["informational"]["fla_cross_check"]["status"] in {"skipped", "executed"}
    assert receipt["wall_seconds"] < 60
    with pytest.raises(FileExistsError):
        doctor.main(["--output", str(output)])


def test_doctor_is_deterministic_across_runs(tmp_path: Path) -> None:
    first = doctor.run_doctor(42)
    second = doctor.run_doctor(42)
    assert first["payload_sha256"] == second["payload_sha256"]
    assert doctor.run_doctor(43)["payload_sha256"] != first["payload_sha256"]


def test_doctor_rejects_negative_seed() -> None:
    with pytest.raises(SystemExit):
        doctor.parse_args(["--output", "x.json", "--seed", "-1"])
