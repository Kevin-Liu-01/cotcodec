from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from harness import translation_supervised_indexer as tsi
from harness.translation_supervised_indexer import (
    ConditionRecall,
    IndexerContractError,
    IndexerParameters,
    SyntheticWorldConfig,
    TrainingConfig,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = PROJECT_ROOT / "scripts" / "run_translation_supervised_indexer_doctor.py"


def small_world() -> tsi.SyntheticBilingualWorld:
    config = SyntheticWorldConfig(
        topics=3, concepts_per_topic=4, d_sem=6, d_lang=3, d_form=4, same_language_heads=2
    )
    return tsi.build_synthetic_world(config, seed=5)


def test_top_k_selection_is_causal_deterministic_and_budgeted() -> None:
    rng = np.random.default_rng(0)
    scores = rng.normal(size=(9, 9))
    selection = tsi.top_k_selection(scores, 3)
    assert selection.dtype == np.bool_
    assert not np.any(selection & ~tsi.causal_mask(9))
    assert selection[0].sum() == 1 and selection[1].sum() == 2  # fewer visible keys than k
    assert np.all(selection[2:].sum(axis=1) == 3)
    tied = np.zeros((4, 4))
    assert np.array_equal(tsi.top_k_selection(tied, 2)[3], np.array([True, True, False, False]))


def test_selection_recall_rejects_future_needle_and_non_causal_selection() -> None:
    selection = tsi.top_k_selection(np.zeros((8, 8)), 3)
    assert tsi.selection_recall(selection, np.array([6, 7]), np.array([0, 1, 2])) == pytest.approx(
        1.0
    )
    with pytest.raises(IndexerContractError, match="precede every query"):
        tsi.selection_recall(selection, np.array([6]), np.array([0, 7]))
    tampered = selection.copy()
    tampered[5, 6] = True  # a key after its query
    with pytest.raises(IndexerContractError, match="not causal"):
        tsi.selection_recall(tampered, np.array([6, 7]), np.array([0, 1, 2]))


def test_union_reference_matches_brute_force_and_respects_budgets() -> None:
    world = small_world()
    rng = np.random.default_rng(3)
    family = tsi.make_prompt_family(world, rng, 1, 0, 2, 0.5, haystack_length=20, needle_length=2)
    prompt = family.prompts["CX"]
    probs = tsi.teacher_attention(world.embed(prompt.tokens)[None], world.teacher)
    union = tsi.union_top_k_reference(probs, 4)[0]
    assert np.array_equal(union, tsi.brute_force_union_top_k(probs[0], 4))
    assert union.sum(axis=1).max() <= probs.shape[1] * 4
    budget = tsi.budget_matched_reference(probs, 4)[0]
    assert budget.sum(axis=1).max() <= 4
    with pytest.raises(IndexerContractError, match="one key per head"):
        tsi.budget_matched_reference(probs, 1)


def test_aggregations_are_row_normalised_and_rh_needs_weights() -> None:
    world = small_world()
    hidden = world.embed(np.arange(7))[None]
    probs = tsi.teacher_attention(hidden, world.teacher)
    for aggregation, weights in (
        ("hs", None),
        ("mp", None),
        ("rh", np.array([1.0, 2.0, 0.0, 1.0])),
    ):
        target = tsi.aggregate_target(probs, aggregation, weights)
        assert np.allclose(target.sum(axis=-1), 1.0)
        assert not np.any(target[..., ~tsi.causal_mask(7)])
    with pytest.raises(IndexerContractError, match="retrieval-head weights"):
        tsi.aggregate_target(probs, "rh")
    with pytest.raises(IndexerContractError, match="unknown aggregation"):
        tsi.aggregate_target(probs, "avg")  # type: ignore[arg-type]


def test_t_star_rule_respects_the_mn_band_and_tie_break() -> None:
    table = {
        "hs": ConditionRecall(ml=95, mn=90, cx=60),
        "mp": ConditionRecall(ml=94, mn=89, cx=70),
        "rh": ConditionRecall(ml=99, mn=80, cx=85),
    }
    choice = tsi.select_target_aggregation(table)
    assert choice.selected == "mp"
    assert choice.eligible == ("hs", "mp")
    wide = tsi.select_target_aggregation(table, band=10.0)
    assert wide.selected == "rh"
    tie = tsi.select_target_aggregation(
        {"rh": ConditionRecall(90, 90, 70), "hs": ConditionRecall(90, 90, 70)}
    )
    assert tie.selected == "hs"
    lam = tsi.select_target_aggregation(
        {"0.25": ConditionRecall(90, 90, 70), "0.5": ConditionRecall(90, 89.5, 72)},
        preference=("0.25", "0.5"),
    )
    assert lam.selected == "0.5"


def test_k2a_evaluability_and_recovery_semantics() -> None:
    fires = tsi.k2a_target_aggregation_artifact(90.0, 60.0, 85.0)
    assert fires.evaluable and fires.fired
    holds = tsi.k2a_target_aggregation_artifact(90.0, 60.0, 70.0)
    assert holds.evaluable and not holds.fired
    small = tsi.k2a_target_aggregation_artifact(62.0, 60.0, 61.9)
    assert not small.evaluable and not small.fired
    tampered = tsi.k2a_target_aggregation_artifact(50.0, 60.0, 70.0)  # reference below the indexer
    assert not tampered.evaluable and not tampered.fired


def test_decision_rule_regions_and_withholding() -> None:
    rule = tsi.derive_decision_rule(sigma_hat=2.0, sigma_df=6, se_prompt=1.3, n_seeds=5)
    assert 0.0 < rule.kappa <= 3.0
    assert rule.regions_separated and not rule.phase1_withheld
    assert rule.se_d_upper > np.sqrt(2.0 / 5.0) * 2.0  # the wave-4 seed-only SE
    assert rule.sigma_upper > 2.0
    assert tsi.classify_primary_gain(7.0, rule, True) == "confirm"
    assert tsi.classify_primary_gain(7.0, rule, False) == "inconclusive"
    assert tsi.classify_primary_gain(rule.kappa, rule, True) == "kill"
    assert tsi.classify_primary_gain(rule.kappa + 0.1, rule, True) == "inconclusive"
    noisy = tsi.derive_decision_rule(sigma_hat=4.7, sigma_df=6, se_prompt=1.3, n_seeds=5)
    assert noisy.kappa == 0.0 and noisy.phase1_withheld
    assert tsi.classify_primary_gain(7.0, noisy, True) == "withheld"
    twelve = tsi.derive_decision_rule(sigma_hat=2.0, sigma_df=12, se_prompt=1.3, n_seeds=5)
    assert twelve.sigma_upper < rule.sigma_upper  # claiming 12 df understates the bound


def test_pooled_seed_sd_reports_honest_degrees_of_freedom() -> None:
    pooled = tsi.pooled_seed_sd({"hs": [60, 62, 61], "mp": [58, 59, 63], "rh": [50, 52, 51]})
    assert pooled.degrees_of_freedom == 6
    assert pooled.configurations == 3
    assert pooled.sigma_hat == pytest.approx(np.sqrt((2.0 + 14.0 + 2.0) / 6.0))
    with pytest.raises(IndexerContractError, match="at least two seeds"):
        tsi.pooled_seed_sd({"hs": [60.0]})


def test_paired_cluster_bootstrap_se_tracks_the_analytic_value() -> None:
    rng = np.random.default_rng(1)
    clusters = np.repeat(np.arange(120), 5)
    effect = rng.normal(0.0, 3.0, size=120)[clusters]
    differences = np.stack([effect + rng.normal(0.0, 6.0, size=clusters.size) for _ in range(3)])
    se = tsi.paired_cluster_bootstrap_se(differences, clusters, replicates=400, seed=2)
    analytic = np.sqrt(9.0 / 120 + 36.0 / (3 * clusters.size))
    assert se == pytest.approx(analytic, rel=0.3)


def test_passage_split_is_disjoint_and_reads_fail_closed() -> None:
    ids = [f"p{index}" for index in range(488)]
    split = tsi.split_passage_ids(ids, seed=42)
    assert (len(split.development), len(split.audit), len(split.primary)) == (122, 122, 244)
    assert split.development | split.audit | split.primary == set(ids)
    assert split == tsi.split_passage_ids(ids, seed=42)
    tsi.assert_reads_within(sorted(split.audit)[:3], split, "audit")
    with pytest.raises(IndexerContractError, match="outside the audit partition"):
        tsi.assert_reads_within(sorted(split.primary)[:1], split, "audit")
    with pytest.raises(IndexerContractError, match="outside the primary partition"):
        tsi.assert_reads_within(sorted(split.audit)[:1], split, "primary")
    with pytest.raises(IndexerContractError, match="unique"):
        tsi.split_passage_ids(["a", "a", "b", "c"], seed=1)


def test_alignment_loss_accounts_mass_and_rejects_label_leaks() -> None:
    world = small_world()
    concat = tsi.build_bilingual_concatenation(
        [[world.symbol(1, 0, 0), world.symbol(1, 1, 0)], [world.symbol(1, 4, 1)]],
        [[world.symbol(0, 4, 0)], [world.symbol(0, 0, 1), world.symbol(0, 1, 1)]],
        [(0, 1), (1, 0)],
        world.separator_token,
    )
    params = IndexerParameters.random(world.config.d_model, 4, 2, seed=1)
    forward = tsi.indexer_forward(world.embed(concat.tokens)[None], params)
    result = tsi.alignment_log_mass_loss(
        forward.log_probs, concat.label_mask[None], concat.query_rows[None]
    )
    assert result.query_count == 3
    assert np.all(result.label_mass > 0.0) and np.all(result.label_mass <= 1.0)
    assert result.loss == pytest.approx(float(-np.log(result.label_mass).mean()))
    leak = concat.label_mask.copy()
    leak[3, 5] = True  # key after the query
    with pytest.raises(IndexerContractError, match="causality leak"):
        tsi.alignment_log_mass_loss(forward.log_probs, leak[None], concat.query_rows[None])
    with pytest.raises(IndexerContractError, match="causality leak"):
        tsi.label_mask_from_alignment(
            np.array([2, 2, 1, 0, 0]), np.array([0, 0, -1, 0, 0]), [(0, 0)]
        )


def test_permuted_labels_are_a_derangement_and_half_labels_cover_the_key_half() -> None:
    world = small_world()
    sentences_key = [[world.symbol(1, c, 0)] for c in range(3)]
    sentences_query = [[world.symbol(0, c, 0)] for c in range(3)]
    concat = tsi.build_bilingual_concatenation(
        sentences_key, sentences_query, [(0, 0), (1, 1), (2, 2)], world.separator_token
    )
    permuted = tsi.permuted_label_mask(concat, seed=3)
    assert not np.any(permuted & concat.label_mask)
    assert permuted.sum() == concat.label_mask.sum()
    half = tsi.other_half_label_mask(concat)
    assert np.all(half[concat.query_rows][:, concat.half == 0])
    assert not np.any(half[~concat.query_rows])


def test_analytic_gradient_matches_finite_differences() -> None:
    world = small_world()
    training = TrainingConfig(
        label_mode="true",
        lambda_x=0.5,
        batch_size=2,
        sentences=3,
        sentence_length=2,
        rank=4,
        heads=2,
        bilingual_fraction=1.0,
    )
    batch = tsi.make_training_batch(world, np.random.default_rng(1), training, None, label_seed=3)
    params = IndexerParameters.random(world.config.d_model, 4, 2, seed=9, scale=0.8)
    _, gradient = tsi.loss_and_gradient(params, batch, 0.5)
    vector = params.as_vector()
    numeric = np.zeros_like(vector)
    for index in range(len(vector)):
        bump = np.zeros_like(vector)
        bump[index] = 1e-6
        plus, _ = tsi.loss_and_gradient(params.with_vector(vector + bump), batch, 0.5)
        minus, _ = tsi.loss_and_gradient(params.with_vector(vector - bump), batch, 0.5)
        numeric[index] = (plus.total - minus.total) / 2e-6
    assert np.linalg.norm(gradient - numeric) <= 1e-6 * np.linalg.norm(numeric)


def test_synthetic_world_rejects_a_non_involutive_map() -> None:
    config = SyntheticWorldConfig(topics=3, concepts_per_topic=4, d_sem=6, d_lang=3, d_form=4)
    rotation, _ = np.linalg.qr(np.random.default_rng(0).normal(size=(6, 6)))
    with pytest.raises(IndexerContractError, match="symmetric orthogonal"):
        tsi.build_synthetic_world(config, 1, rotation=rotation)
    assert tsi.build_synthetic_world(config, 1).rotation @ tsi.build_synthetic_world(
        config, 1
    ).rotation == pytest.approx(np.eye(6), abs=1e-9)


def test_gate_helpers_follow_registered_thresholds() -> None:
    assert tsi.adequacy_gate(94.0, 100.0).fired and not tsi.adequacy_gate(95.0, 100.0).fired
    assert tsi.bug_tell(96.0, 95.0).fired and not tsi.bug_tell(95.0, 95.0).fired
    assert tsi.k1_localization_negative({"a": 5.0, "b": 4.0}).fired
    assert not tsi.k1_localization_negative({"a": 5.0, "b": 5.01}).fired
    assert (
        tsi.phase0_localization({"a": 10.0}).fired and not tsi.phase0_localization({"a": 9.9}).fired
    )
    assert tsi.k3_loss_form(10.0, 8.0, 0.0, True).fired
    assert not tsi.k3_loss_form(10.0, 8.0, 0.0, False).evaluable
    assert (
        tsi.k4_semantic_sharpening(10.0, 5.0).fired
        and not tsi.k4_semantic_sharpening(10.0, 4.9).fired
    )
    assert tsi.k8_language_harm({"ja": 2.1}, 0.0).fired
    assert tsi.k8_language_harm({"ja": 0.0}, 0.51).fired
    assert not tsi.k8_language_harm({"ja": 2.0}, 0.5).fired
    assert tsi.inertness_holds(90.0, 91.0) and not tsi.inertness_holds(90.0, 91.01)


def test_doctor_runs_end_to_end_and_refuses_to_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "phase0-doctor.json"
    completed = subprocess.run(
        [sys.executable, str(DOCTOR), "--output", str(output)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(output.read_text())
    assert payload["status"] == "PHASE0_DOCTOR_PASS"
    assert payload["numbers_are_synthetic"] is True
    assert payload["evidence_grade"].startswith("EXECUTABILITY_AND_GATE_SEMANTICS_ONLY")
    assert payload["runtime_seconds"] < 60.0
    assert set(payload["case_status"].values()) == {"PASS"}
    for name in (
        "synthetic_excess_gap_and_repair",
        "shifted_script_negative_control",
        "leakage_and_causality_perturbations",
        "degenerate_input_rejection",
        "decision_rule_from_stated_noise_model",
        "passage_split_and_read_separation",
    ):
        assert name in payload["cases"]
    positive = payload["cases"]["synthetic_excess_gap_and_repair"]["seeds"]
    assert set(positive) == {"42", "43", "44"}
    for seed_entry in positive.values():
        assert seed_entry["statistics_points"]["D"] >= 6.0
        assert seed_entry["registered_gates"]["P1_localization"]["fired"] is True
    again = subprocess.run(
        [sys.executable, str(DOCTOR), "--output", str(output)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert again.returncode != 0
    assert "new versioned attempt" in again.stderr
