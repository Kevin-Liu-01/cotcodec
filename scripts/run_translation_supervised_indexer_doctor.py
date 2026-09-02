#!/usr/bin/env python3
"""Exercise the Direction-21 Phase-0 objects on synthetic cases before any model training.

Executability and gate-semantics doctor for the translation-supervised sparse
indexer. It proves that the registered objects (indexer, target aggregations,
fixed reference, selection recall, xi / S / D statistics, T* and lambda_x rules,
L_x with its controls, the passage split and the decision rule) run on CPU with
NumPy/SciPy only, and that every registered gate fires in the registered
direction on synthetic positive and negative controls. Every number it prints
is a synthetic-case number; it proves nothing about any language model,
checkpoint or dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import scipy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import translation_supervised_indexer as tsi  # noqa: E402
from harness.translation_supervised_indexer import (  # noqa: E402
    AGGREGATIONS,
    ConditionRecall,
    IndexerContractError,
    IndexerParameters,
    SyntheticWorldConfig,
    TrainingConfig,
)

DOCTOR_NAME = "translation-supervised-sparse-indexer-phase0"
EVIDENCE_GRADE = (
    "EXECUTABILITY_AND_GATE_SEMANTICS_ONLY: every number below is a synthetic-case "
    "number from a NumPy toy (two scripts related by a fixed reflection, an eight-head "
    "softmax teacher, a rank-16 ReLU indexer). A PASS proves that the Phase-0 objects "
    "run on CPU and that the registered gates fire in the registered direction on "
    "positive and negative controls. It proves nothing about any language model, "
    "checkpoint, tokenizer, dataset, GPU budget or the research claim."
)
LAMBDA_CANDIDATES = (0.25, 0.5)
DEVELOPMENT_LANGUAGE = 1
HELD_OUT_LANGUAGE = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--families", type=int, default=8, help="prompt families per direction")
    return parser.parse_args()


def _recall(recall: ConditionRecall) -> dict[str, float | None]:
    return {
        "ML": recall.ml,
        "MN": recall.mn,
        "CX": recall.cx,
        "CS": recall.cs,
        "delta": recall.delta,
        "literalness_gap": recall.literalness_gap,
    }


def _selectors(result: tsi.SelectorRecalls) -> dict[str, Any]:
    return {
        "indexer": _recall(result.indexer),
        "target": _recall(result.target),
        "union_reference_RU": _recall(result.union_reference),
        "budget_matched_Uk": _recall(result.budget_matched_reference),
        "prompt_count": result.prompt_count,
        "achieved_k": result.achieved_k,
    }


def _expect_error(callable_: Any, *args: Any, **kwargs: Any) -> bool:
    try:
        callable_(*args, **kwargs)
    except IndexerContractError:
        return True
    return False


def _reflection(seed: int, dimension: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    basis, _ = np.linalg.qr(rng.normal(size=(dimension, dimension)))
    signs = np.where(np.arange(dimension) < dimension // 2, 1.0, -1.0)
    return (basis * signs) @ basis.T


# --------------------------------------------------------------------------- #
# Case 1: synthetic excess gap and its repair (positive control + label controls)
# --------------------------------------------------------------------------- #


def case_excess_gap_and_repair(
    seeds: list[int], families: int
) -> tuple[dict[str, Any], dict[int, Any]]:
    config = SyntheticWorldConfig()
    per_seed: dict[str, Any] = {}
    trained: dict[int, Any] = {}
    gates: dict[str, bool] = {
        "adequacy_gate_passes_every_seed": True,
        "no_bug_tell_every_seed": True,
        "excess_cross_script_gap_at_least_10_points_every_seed": True,
        "fixed_reference_has_no_cross_script_gap_every_seed": True,
        "alignment_loss_repairs_held_out_cross_script_recall_by_at_least_6_every_seed": True,
        "permuted_labels_recover_under_half_of_D_every_seed": True,
        "other_half_labels_recover_under_half_of_D_every_seed": True,
        "no_held_out_language_harm_over_2_points_every_seed": True,
        "t_star_and_lambda_x_frozen_on_development_prompts_only": True,
    }
    for seed in seeds:
        world = tsi.build_synthetic_world(config, seed)
        development = tsi.evaluation_families(world, seed, DEVELOPMENT_LANGUAGE, None, families)
        held_out = tsi.evaluation_families(
            world, seed, HELD_OUT_LANGUAGE, DEVELOPMENT_LANGUAGE, families
        )
        head_weights = tsi.retrieval_head_weights(world, seed)

        ladder: dict[str, dict[str, Any]] = {}
        for aggregation in AGGREGATIONS:
            run = tsi.train_indexer(
                world, TrainingConfig(aggregation=aggregation), seed, head_weights=head_weights
            )
            ladder[aggregation] = {
                "run": run,
                "development": tsi.evaluate_selectors(
                    world, run.params, aggregation, development, head_weights
                ),
                "held_out": tsi.evaluate_selectors(
                    world, run.params, aggregation, held_out, head_weights
                ),
            }
        t_star = tsi.select_target_aggregation(
            {name: entry["development"].indexer for name, entry in ladder.items()}
        )
        lambda_runs: dict[str, dict[str, Any]] = {}
        for lambda_x in LAMBDA_CANDIDATES:
            run = tsi.train_indexer(
                world,
                TrainingConfig(aggregation=t_star.selected, label_mode="true", lambda_x=lambda_x),
                seed,
                head_weights=head_weights,
            )
            lambda_runs[str(lambda_x)] = {
                "run": run,
                "development": tsi.evaluate_selectors(
                    world, run.params, t_star.selected, development, head_weights
                ),
            }
        lambda_choice = tsi.select_target_aggregation(
            {name: entry["development"].indexer for name, entry in lambda_runs.items()},
            preference=tuple(str(v) for v in LAMBDA_CANDIDATES),
        )
        chosen_lambda = float(lambda_choice.selected)
        treatment = lambda_runs[lambda_choice.selected]["run"]
        controls = {
            mode: tsi.train_indexer(
                world,
                TrainingConfig(
                    aggregation=t_star.selected, label_mode=mode, lambda_x=chosen_lambda
                ),
                seed,
                head_weights=head_weights,
            )
            for mode in ("permuted", "half")
        }
        counterfactual = ladder[t_star.selected]["held_out"]
        held = {
            "b_kl_only_t_star": counterfactual,
            "c_t_star_plus_L_x": tsi.evaluate_selectors(
                world, treatment.params, t_star.selected, held_out, head_weights
            ),
            "d_t_star_plus_L_perm": tsi.evaluate_selectors(
                world, controls["permuted"].params, t_star.selected, held_out, head_weights
            ),
            "e_t_star_plus_L_half": tsi.evaluate_selectors(
                world, controls["half"].params, t_star.selected, held_out, head_weights
            ),
        }
        b = held["b_kl_only_t_star"]
        c = held["c_t_star_plus_L_x"]
        d = held["d_t_star_plus_L_perm"]
        e = held["e_t_star_plus_L_half"]
        xi_by_aggregation = {
            name: tsi.own_target_excess(entry["held_out"].indexer, entry["held_out"].target)
            for name, entry in ladder.items()
        }
        gain = tsi.primary_gain(c.indexer.cx, b.indexer.cx)
        gain_perm = tsi.primary_gain(d.indexer.cx, b.indexer.cx)
        gain_half = tsi.primary_gain(e.indexer.cx, b.indexer.cx)
        hs_held = ladder["hs"]["held_out"]
        adequacy = tsi.adequacy_gate(b.indexer.ml, b.target.ml)
        tell = tsi.bug_tell(b.indexer.ml, b.target.ml, tolerance=1.0)
        localization = tsi.phase0_localization(xi_by_aggregation)
        k1 = tsi.k1_localization_negative(xi_by_aggregation)
        k2a = tsi.k2a_target_aggregation_artifact(
            hs_held.union_reference.cx, hs_held.indexer.cx, counterfactual.indexer.cx
        )
        inert_d = tsi.inertness_holds(d.indexer.mn, b.indexer.mn)
        inert_e = tsi.inertness_holds(e.indexer.mn, b.indexer.mn)
        k3 = tsi.k3_loss_form(gain, gain_perm, gain_half, inert_d and inert_e)
        k8 = tsi.k8_language_harm(
            {
                "held-out-MN": b.indexer.mn - c.indexer.mn,
                "held-out-CS": (b.indexer.cs or 0.0) - (c.indexer.cs or 0.0),
            },
            e3_drop=0.0,
        )
        reference_clean = abs(b.union_reference.delta) <= 5.0 and b.union_reference.cx >= 90.0
        seed_gates = {
            "adequacy": not adequacy.fired,
            "no_bug_tell": not tell.fired,
            "excess_gap": xi_by_aggregation[t_star.selected] >= tsi.LOCALIZATION_CONFIRM_POINTS,
            "reference_clean": reference_clean,
            "repair": gain >= tsi.CONFIRM_THRESHOLD_POINTS,
            "perm_specific": gain_perm <= 0.5 * gain,
            "half_specific": gain_half <= 0.5 * gain,
            "no_harm": not k8.fired,
        }
        gates["adequacy_gate_passes_every_seed"] &= seed_gates["adequacy"]
        gates["no_bug_tell_every_seed"] &= seed_gates["no_bug_tell"]
        gates["excess_cross_script_gap_at_least_10_points_every_seed"] &= seed_gates["excess_gap"]
        gates["fixed_reference_has_no_cross_script_gap_every_seed"] &= seed_gates["reference_clean"]
        gates["alignment_loss_repairs_held_out_cross_script_recall_by_at_least_6_every_seed"] &= (
            seed_gates["repair"]
        )
        gates["permuted_labels_recover_under_half_of_D_every_seed"] &= seed_gates["perm_specific"]
        gates["other_half_labels_recover_under_half_of_D_every_seed"] &= seed_gates["half_specific"]
        gates["no_held_out_language_harm_over_2_points_every_seed"] &= seed_gates["no_harm"]
        trained[seed] = {
            "world": world,
            "b": ladder[t_star.selected]["run"],
            "c": treatment,
            "t_star": t_star.selected,
            "head_weights": head_weights,
            "D": gain,
            "families": families,
        }
        per_seed[str(seed)] = {
            "world_identity": world.identity(),
            "development_language": DEVELOPMENT_LANGUAGE,
            "held_out_language": HELD_OUT_LANGUAGE,
            "retrieval_head_weights": [float(w) for w in head_weights],
            "label_free_ladder_development": {
                name: _recall(entry["development"].indexer) for name, entry in ladder.items()
            },
            "label_free_ladder_held_out": {
                name: _selectors(entry["held_out"]) for name, entry in ladder.items()
            },
            "t_star": asdict(t_star),
            "lambda_x_development_table": {
                name: _recall(entry["development"].indexer) for name, entry in lambda_runs.items()
            },
            "lambda_x_selected": chosen_lambda,
            "held_out_arms": {name: _selectors(result) for name, result in held.items()},
            "statistics_points": {
                "xi_T_by_aggregation": xi_by_aggregation,
                "xi_U_t_star": tsi.reference_excess(b.indexer, b.union_reference),
                "S_hs": tsi.absolute_shortfall(hs_held.union_reference.cx, hs_held.indexer.cx),
                "S_t_star": tsi.absolute_shortfall(b.union_reference.cx, b.indexer.cx),
                "D": gain,
                "D_perm": gain_perm,
                "D_half": gain_half,
                "inertness_perm": inert_d,
                "inertness_half": inert_e,
                "literalness_gap_indexer_b": b.indexer.literalness_gap,
            },
            "registered_gates": {
                "adequacy": asdict(adequacy),
                "bug_tell": asdict(tell),
                "P1_localization": asdict(localization),
                "K1": asdict(k1),
                "K2a": asdict(k2a),
                "K3": asdict(k3),
                "K8": asdict(k8),
            },
            "training_losses": {
                "b_final_kl": ladder[t_star.selected]["run"].final_loss.kl,
                "c_final_kl": treatment.final_loss.kl,
                "c_final_L_x": treatment.final_loss.alignment,
                "d_final_L_perm": controls["permuted"].final_loss.alignment,
                "e_final_L_half": controls["half"].final_loss.alignment,
            },
            "seed_gates": seed_gates,
        }
    return {"gates": gates, "seeds": per_seed, "training_config": asdict(TrainingConfig())}, trained


# --------------------------------------------------------------------------- #
# Case 2: shifted-script negative control
# --------------------------------------------------------------------------- #


def case_shifted_script(trained: dict[int, Any]) -> dict[str, Any]:
    per_seed: dict[str, Any] = {}
    gate = True
    for seed, entry in trained.items():
        world = entry["world"]
        shifted = tsi.build_synthetic_world(
            world.config, seed, rotation=_reflection(seed + 100_000, world.config.d_sem)
        )
        shared = bool(
            np.allclose(
                shifted.embeddings[: world.config.concepts * world.config.forms],
                world.embeddings[: world.config.concepts * world.config.forms],
            )
        )
        families = tsi.evaluation_families(
            shifted, seed, HELD_OUT_LANGUAGE, DEVELOPMENT_LANGUAGE, entry["families"]
        )
        b = tsi.evaluate_selectors(
            shifted, entry["b"].params, entry["t_star"], families, entry["head_weights"]
        )
        c = tsi.evaluate_selectors(
            shifted, entry["c"].params, entry["t_star"], families, entry["head_weights"]
        )
        shifted_gain = tsi.primary_gain(c.indexer.cx, b.indexer.cx)
        ok = shared and shifted_gain <= 0.5 * entry["D"] and b.target.cx >= 90.0
        gate &= ok
        per_seed[str(seed)] = {
            "script_0_vectors_shared_with_original": shared,
            "b_on_shifted": _selectors(b),
            "c_on_shifted": _selectors(c),
            "D_shifted": shifted_gain,
            "D_original": entry["D"],
            "passes": ok,
        }
    return {
        "gates": {"alignment_gain_collapses_under_a_different_script_map_every_seed": gate},
        "seeds": per_seed,
        "note": (
            "the teacher of the shifted world knows its own map (target CX stays high); "
            "the indexers trained on the original map must not"
        ),
    }


# --------------------------------------------------------------------------- #
# Case 3: fixed reference against brute force; chance-level random selection
# --------------------------------------------------------------------------- #


def case_fixed_reference(seed: int) -> dict[str, Any]:
    config = SyntheticWorldConfig()
    world = tsi.build_synthetic_world(config, seed)
    rng = np.random.default_rng([seed, 99])
    families = [
        tsi.make_prompt_family(
            world, rng, HELD_OUT_LANGUAGE, 0, DEVELOPMENT_LANGUAGE, float(rng.uniform(0.1, 0.9))
        )
        for _ in range(5)
    ]
    prompts = [prompt for family in families for prompt in family.prompts.values()][:20]
    matches = 0
    union_budget_ok = True
    budget_ok = True
    random_recalls: list[float] = []
    for prompt in prompts:
        probs = tsi.teacher_attention(world.embed(prompt.tokens)[None], world.teacher)
        k = prompt.ledger.achieved_k
        union = tsi.union_top_k_reference(probs, k)[0]
        brute = tsi.brute_force_union_top_k(probs[0], k)
        matches += int(np.array_equal(union, brute))
        union_budget_ok &= bool(union.sum(axis=1).max() <= probs.shape[1] * k)
        budget = tsi.budget_matched_reference(probs, k)[0]
        budget_ok &= bool(budget.sum(axis=1).max() <= k)
        random_scores = rng.normal(size=(len(prompt.tokens), len(prompt.tokens)))
        random_recalls.append(
            100.0
            * tsi.selection_recall(
                tsi.top_k_selection(random_scores, k),
                prompt.query_positions,
                prompt.needle_positions,
            )
        )
    chance = 100.0 * prompts[0].ledger.achieved_k / (prompts[0].ledger.haystack_tokens + 1)
    mean_random = float(np.mean(random_recalls))
    return {
        "gates": {
            "union_reference_matches_brute_force_on_20_prompts": matches == len(prompts) == 20,
            "union_reference_rows_within_H_times_k": union_budget_ok,
            "budget_matched_rows_within_k": budget_ok,
            "random_selection_sits_at_chance": abs(mean_random - chance) <= 10.0,
        },
        "prompts_checked": len(prompts),
        "exact_matches": matches,
        "random_selection_recall_points": mean_random,
        "chance_level_points": chance,
    }


# --------------------------------------------------------------------------- #
# Case 4: analytic gradient against central finite differences
# --------------------------------------------------------------------------- #


def case_gradient_check() -> dict[str, Any]:
    config = SyntheticWorldConfig(
        topics=3, concepts_per_topic=4, d_sem=6, d_lang=3, d_form=4, same_language_heads=2
    )
    world = tsi.build_synthetic_world(config, 5)
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
    rng = np.random.default_rng(1)
    batch = tsi.make_training_batch(world, rng, training, None, label_seed=3)
    params = IndexerParameters.random(config.d_model, 4, 2, seed=9, scale=0.8)
    loss, gradient = tsi.loss_and_gradient(params, batch, 0.5)
    vector = params.as_vector()
    numeric = np.zeros_like(vector)
    step = 1e-6
    for index in range(len(vector)):
        bump = np.zeros_like(vector)
        bump[index] = step
        plus, _ = tsi.loss_and_gradient(params.with_vector(vector + bump), batch, 0.5)
        minus, _ = tsi.loss_and_gradient(params.with_vector(vector - bump), batch, 0.5)
        numeric[index] = (plus.total - minus.total) / (2.0 * step)
    relative = float(np.linalg.norm(gradient - numeric) / max(np.linalg.norm(numeric), 1e-12))
    return {
        "gates": {"analytic_gradient_matches_finite_differences": relative <= 1e-6},
        "relative_error": relative,
        "parameters": int(len(vector)),
        "loss": asdict(loss),
    }


# --------------------------------------------------------------------------- #
# Case 5: L_x mass accounting and permutation sensitivity
# --------------------------------------------------------------------------- #


def case_alignment_loss(trained: dict[int, Any]) -> dict[str, Any]:
    seed = min(trained)
    entry = trained[seed]
    world = entry["world"]
    rng = np.random.default_rng([seed, 77])
    config = TrainingConfig(label_mode="true", bilingual_fraction=1.0, batch_size=6)
    batch = tsi.make_training_batch(world, rng, config, None, label_seed=seed)
    permuted = tsi.make_training_batch(
        world,
        np.random.default_rng([seed, 77]),
        TrainingConfig(label_mode="permuted", bilingual_fraction=1.0, batch_size=6),
        None,
        label_seed=seed,
    )
    forward = tsi.indexer_forward(batch.hidden, entry["c"].params)
    true_loss = tsi.alignment_log_mass_loss(forward.log_probs, batch.label_mask, batch.query_rows)
    perm_loss = tsi.alignment_log_mass_loss(
        forward.log_probs, permuted.label_mask, permuted.query_rows
    )
    random_params = IndexerParameters.random(world.config.d_model, 16, 4, seed=seed + 1)
    random_forward = tsi.indexer_forward(batch.hidden, random_params)
    random_true = tsi.alignment_log_mass_loss(
        random_forward.log_probs, batch.label_mask, batch.query_rows
    )
    random_perm = tsi.alignment_log_mass_loss(
        random_forward.log_probs, permuted.label_mask, permuted.query_rows
    )
    masses = true_loss.label_mass
    return {
        "gates": {
            "label_mass_per_query_in_unit_interval": bool(
                np.all(masses > 0.0) and np.all(masses <= 1.0)
            ),
            "trained_indexer_true_labels_beat_permuted_labels": true_loss.loss
            <= 0.8 * perm_loss.loss,
            "same_sequences_under_both_label_sets": bool(
                np.array_equal(batch.hidden, permuted.hidden)
            ),
        },
        "trained_L_x_true": true_loss.loss,
        "trained_L_x_permuted": perm_loss.loss,
        "random_indexer_L_x_true": random_true.loss,
        "random_indexer_L_x_permuted": random_perm.loss,
        "query_tokens": true_loss.query_count,
        "label_mass_min": float(masses.min()),
        "label_mass_mean": float(masses.mean()),
    }


# --------------------------------------------------------------------------- #
# Case 6: decision rule from a stated noise model (wave-5 repair)
# --------------------------------------------------------------------------- #


def case_decision_rule() -> dict[str, Any]:
    # Assumed inputs, not measurements: a 2-point seed SD from three block-form
    # configurations on one base at three seeds (df = 6, not 12), and a paired
    # passage-cluster prompt SE of 1.3 points.
    rng = np.random.default_rng(2026)
    per_configuration = {
        name: list(rng.normal(loc=60.0, scale=2.0, size=3)) for name in ("hs", "mp", "rh")
    }
    pooled = tsi.pooled_seed_sd(per_configuration)
    assumed = tsi.derive_decision_rule(sigma_hat=2.0, sigma_df=6, se_prompt=1.3, n_seeds=5)
    twelve_df = tsi.derive_decision_rule(sigma_hat=2.0, sigma_df=12, se_prompt=1.3, n_seeds=5)
    noisy = tsi.derive_decision_rule(sigma_hat=4.7, sigma_df=6, se_prompt=1.3, n_seeds=5)
    seed_only_wave4 = math.sqrt(2.0 / 5.0) * 2.0
    grid = [tsi.derive_decision_rule(s, 6, 1.3, 5).kappa for s in np.linspace(0.5, 6.0, 12)]
    monotone = all(
        later <= earlier + 1e-12 for earlier, later in zip(grid[:-1], grid[1:], strict=True)
    )
    classifications = {
        "D=7_interval_excludes_zero": tsi.classify_primary_gain(7.0, assumed, True),
        "D=7_interval_includes_zero": tsi.classify_primary_gain(7.0, assumed, False),
        "D=1": tsi.classify_primary_gain(1.0, assumed, True),
        "D=4.5": tsi.classify_primary_gain(4.5, assumed, True),
        "D=7_under_withheld_rule": tsi.classify_primary_gain(7.0, noisy, True),
    }
    # Bootstrap check: shared passage-cluster effects across three seeds, 366
    # clusters of 6 prompts, prompt noise SD 10, cluster SD 3 (synthetic).
    clusters = np.repeat(np.arange(366), 6)
    cluster_effect = rng.normal(0.0, 3.0, size=366)[clusters]
    differences = np.stack(
        [cluster_effect + rng.normal(0.0, 10.0, size=clusters.size) for _ in range(3)]
    )
    bootstrap_se = tsi.paired_cluster_bootstrap_se(differences, clusters, replicates=600, seed=7)
    analytic_se = math.sqrt(9.0 / 366 + 100.0 / (3 * clusters.size))
    e2_se = (
        math.sqrt(2.0 * 0.25 / 1500.0) * 100.0
    )  # unpaired Bernoulli p=0.5, 1,500 prompts, points
    e2_mde = tsi.minimum_detectable_effect(math.sqrt(e2_se**2 + 2.0 * 2.0**2 / 3.0))
    return {
        "gates": {
            "pooled_seed_sd_reports_honest_df_6_for_three_configs_x_three_seeds": (
                pooled.degrees_of_freedom == 6
            ),
            "kappa_never_exceeds_3_and_never_below_0": all(0.0 <= k <= 3.0 for k in grid),
            "kappa_non_increasing_in_sigma": monotone,
            "confirm_kill_separation_at_least_two_se_when_phase1_runs": assumed.regions_separated
            and not assumed.phase1_withheld,
            "phase1_withheld_when_kappa_hits_zero": noisy.phase1_withheld and noisy.kappa == 0.0,
            "combined_se_exceeds_wave4_seed_only_se": assumed.se_d_upper > seed_only_wave4,
            "classification_regions_are_as_registered": classifications
            == {
                "D=7_interval_excludes_zero": "confirm",
                "D=7_interval_includes_zero": "inconclusive",
                "D=1": "kill",
                "D=4.5": "inconclusive",
                "D=7_under_withheld_rule": "withheld",
            },
            "cluster_bootstrap_se_within_25_percent_of_analytic": abs(bootstrap_se - analytic_se)
            <= 0.25 * analytic_se,
        },
        "inputs_are_assumed_not_measured": True,
        "pooled_seed_sd_synthetic": asdict(pooled),
        "rule_sigma2_df6_seprompt1.3_seeds5": asdict(assumed),
        "rule_sigma2_df12_for_comparison": asdict(twelve_df),
        "rule_sigma4.7_df6": asdict(noisy),
        "wave4_seed_only_se": seed_only_wave4,
        "kappa_grid_sigma_0.5_to_6": grid,
        "classifications": classifications,
        "bootstrap_se_synthetic": bootstrap_se,
        "analytic_se_synthetic": analytic_se,
        "e2_closed_form": {
            "prompt_se_points_1500_prompts_p0.5_unpaired": e2_se,
            "assumed_seed_sd_points": 2.0,
            "seeds": 3,
            "mde_points_alpha0.01_power0.8": e2_mde,
            "registered_p3_effect_points": 8.0,
        },
    }


# --------------------------------------------------------------------------- #
# Case 7: passage split and read separation
# --------------------------------------------------------------------------- #


def case_passage_split() -> dict[str, Any]:
    ids = [f"belebele-passage-{index:03d}" for index in range(488)]
    split = tsi.split_passage_ids(ids, seed=42)
    again = tsi.split_passage_ids(ids, seed=42)
    other = tsi.split_passage_ids(ids, seed=43)
    sizes = (len(split.development), len(split.audit), len(split.primary))
    complete = split.development | split.audit | split.primary == set(ids)
    audit_ok = _expect_error(tsi.assert_reads_within, sorted(split.primary)[:3], split, "audit")
    primary_ok = _expect_error(tsi.assert_reads_within, sorted(split.audit)[:1], split, "primary")
    return {
        "gates": {
            "split_is_complete_and_disjoint": complete,
            "split_sizes_are_25_25_50_percent": sizes == (122, 122, 244),
            "split_is_deterministic_for_a_seed": split == again,
            "split_changes_with_the_seed": split != other,
            "gate_read_on_primary_passages_fails_closed": audit_ok,
            "primary_read_on_audit_passages_fails_closed": primary_ok,
            "read_inside_declared_partition_is_accepted": tsi.assert_reads_within(
                sorted(split.audit)[:5], split, "audit"
            )
            is None,
        },
        "sizes": {"development": sizes[0], "audit": sizes[1], "primary": sizes[2]},
    }


# --------------------------------------------------------------------------- #
# Case 8: leakage and causality perturbations must be rejected
# --------------------------------------------------------------------------- #


def case_leakage_and_causality(trained: dict[int, Any]) -> dict[str, Any]:
    seed = min(trained)
    world = trained[seed]["world"]
    rng = np.random.default_rng([seed, 5])
    family = tsi.make_prompt_family(world, rng, HELD_OUT_LANGUAGE, 0, None, 0.5)
    prompt = family.prompts["CX"]
    length = len(prompt.tokens)
    forward = tsi.indexer_forward(world.embed(prompt.tokens)[None], trained[seed]["c"].params)
    selection = tsi.top_k_selection(forward.scores[0], prompt.ledger.achieved_k)
    leaked = selection.copy()
    leaked[int(prompt.query_positions[0]), int(prompt.query_positions[-1])] = True  # a future key
    future_needle = np.append(prompt.needle_positions, int(prompt.query_positions[-1]))
    log_probs = forward.log_probs
    label_leak = np.zeros((1, length, length), dtype=bool)
    rows = np.zeros((1, length), dtype=bool)
    q0 = int(prompt.query_positions[0])
    rows[0, q0] = True
    label_leak[0, q0, q0 + 1] = True  # aligned key after the query token
    half = np.array([2] * 4 + [1] + [0] * 4)  # queries placed BEFORE the keys
    sentence_id = np.array([0, 0, 1, 1, -1, 0, 0, 1, 1])
    checks = {
        "selection_with_a_future_key_is_rejected": _expect_error(
            tsi.selection_recall, leaked, prompt.query_positions, prompt.needle_positions
        ),
        "needle_after_query_is_rejected": _expect_error(
            tsi.selection_recall, selection, prompt.query_positions, future_needle
        ),
        "alignment_label_on_a_future_key_is_rejected": _expect_error(
            tsi.alignment_log_mass_loss, log_probs, label_leak, rows
        ),
        "query_half_before_key_half_is_rejected": _expect_error(
            tsi.label_mask_from_alignment, half, sentence_id, [(0, 0), (1, 1)]
        ),
        "non_causal_probabilities_are_rejected": _expect_error(
            tsi.aggregate_target, np.full((1, 2, 3, 3), 1.0 / 3.0), "hs"
        ),
        "top_k_selection_never_selects_a_future_key": not bool(
            np.any(selection & ~tsi.causal_mask(length))
        ),
        "union_reference_never_selects_a_future_key": not bool(
            np.any(
                tsi.union_top_k_reference(
                    tsi.teacher_attention(world.embed(prompt.tokens)[None], world.teacher),
                    prompt.ledger.achieved_k,
                )[0]
                & ~tsi.causal_mask(length)
            )
        ),
        "evaluation_prompts_carry_no_alignment_labels": not hasattr(prompt, "label_mask"),
    }
    return {"gates": checks}


# --------------------------------------------------------------------------- #
# Case 9: degenerate inputs must be rejected
# --------------------------------------------------------------------------- #


def case_degenerate_inputs() -> dict[str, Any]:
    good_probs = tsi.teacher_attention(
        np.random.default_rng(0).normal(size=(1, 6, 5)),
        tsi.TeacherParameters(np.ones((2, 5, 5)) * 0.1, np.ones((2, 5, 5)) * 0.1),
    )
    rule = tsi.derive_decision_rule(2.0, 6, 1.3, 5)
    checks = {
        "empty_needle": _expect_error(
            tsi.selection_recall, np.eye(4, dtype=bool), np.array([3]), np.array([], dtype=int)
        ),
        "k_zero": _expect_error(tsi.top_k_selection, np.zeros((4, 4)), 0),
        "k_above_length": _expect_error(tsi.top_k_selection, np.zeros((4, 4)), 5),
        "nan_scores": _expect_error(tsi.top_k_selection, np.full((4, 4), np.nan), 2),
        "negative_probabilities": _expect_error(tsi.aggregate_target, -good_probs, "hs"),
        "unknown_aggregation": _expect_error(tsi.aggregate_target, good_probs, "xx"),
        "rh_without_weights": _expect_error(tsi.aggregate_target, good_probs, "rh"),
        "budget_matched_k_below_heads": _expect_error(tsi.budget_matched_reference, good_probs, 1),
        "recall_points_above_100": _expect_error(ConditionRecall, 101.0, 50.0, 50.0),
        "t_star_without_candidates": _expect_error(tsi.select_target_aggregation, {}),
        "t_star_negative_band": _expect_error(
            tsi.select_target_aggregation, {"hs": ConditionRecall(1, 1, 1)}, -1.0
        ),
        "pooled_sd_single_seed": _expect_error(tsi.pooled_seed_sd, {"hs": [1.0]}),
        "sigma_df_zero": _expect_error(tsi.sigma_upper_bound, 2.0, 0),
        "negative_prompt_se": _expect_error(tsi.derive_decision_rule, 2.0, 6, -1.0),
        "single_seed_rule": _expect_error(tsi.derive_decision_rule, 2.0, 6, 1.0, 1),
        "kill_ceiling_above_confirm": _expect_error(
            tsi.derive_decision_rule, 2.0, 6, 1.0, 5, 6.0, 7.0
        ),
        "non_finite_gain": _expect_error(tsi.classify_primary_gain, float("nan"), rule, True),
        "duplicate_passage_ids": _expect_error(tsi.split_passage_ids, ["a", "a", "b"], 1),
        "split_fractions_leave_no_primary": _expect_error(
            tsi.split_passage_ids, list("abcdefgh"), 1, 0.5, 0.5
        ),
        "empty_alignment": _expect_error(
            tsi.build_bilingual_concatenation, [[1, 2]], [[3, 4]], [], 0
        ),
        "empty_sentence": _expect_error(
            tsi.build_bilingual_concatenation, [[1, 2], []], [[3, 4]], [(0, 0)], 0
        ),
        "indexer_shape_mismatch": _expect_error(
            IndexerParameters, np.ones((2, 3, 4)), np.ones((3, 5)), np.zeros((3, 2)), np.ones(2)
        ),
        "hidden_width_mismatch": _expect_error(
            tsi.indexer_forward, np.ones((1, 3, 7)), IndexerParameters.random(5, 2, 2, 0)
        ),
        "lambda_zero_with_labels": _expect_error(TrainingConfig, label_mode="true", lambda_x=0.0),
        "world_topic_weight_out_of_range": _expect_error(SyntheticWorldConfig, topic_weight=1.5),
        "world_needs_two_scripts": _expect_error(SyntheticWorldConfig, scripts=(0, 0)),
        "k8_without_languages": _expect_error(tsi.k8_language_harm, {}, 0.0),
        "k1_without_values": _expect_error(tsi.k1_localization_negative, {}),
    }
    return {"gates": {f"rejects_{name}": ok for name, ok in checks.items()}}


# --------------------------------------------------------------------------- #
# Case 10: T*, K1, K2a, K2b, K3, K4, K8, adequacy semantics on hand-made tables
# --------------------------------------------------------------------------- #


def case_gate_semantics() -> dict[str, Any]:
    table = {
        "hs": ConditionRecall(ml=95, mn=90, cx=60),
        "mp": ConditionRecall(ml=94, mn=89, cx=70),
        "rh": ConditionRecall(ml=99, mn=80, cx=85),  # best CX but 10 points below the MN ceiling
    }
    t_star = tsi.select_target_aggregation(table)
    tie = tsi.select_target_aggregation(
        {"mp": ConditionRecall(90, 90, 70), "hs": ConditionRecall(90, 90, 70)}
    )
    rule = tsi.derive_decision_rule(2.0, 6, 1.3, 5)
    k2a_fires = tsi.k2a_target_aggregation_artifact(90.0, 60.0, 85.0)
    k2a_holds = tsi.k2a_target_aggregation_artifact(90.0, 60.0, 70.0)
    k2a_not_evaluable = tsi.k2a_target_aggregation_artifact(62.0, 60.0, 61.9)
    checks = {
        "t_star_excludes_high_cx_candidate_outside_mn_band": t_star.selected == "mp"
        and "rh" not in t_star.eligible,
        "t_star_tie_breaks_to_head_sum": tie.selected == "hs",
        "adequacy_fires_above_5_point_shortfall": tsi.adequacy_gate(94.0, 100.0).fired
        and not tsi.adequacy_gate(95.5, 100.0).fired,
        "bug_tell_fires_when_indexer_beats_own_literal_target": tsi.bug_tell(96.0, 95.0).fired,
        "k1_fires_only_when_every_xi_at_most_5": tsi.k1_localization_negative(
            {"a": 5.0, "b": 2.0}
        ).fired
        and not tsi.k1_localization_negative({"a": 5.0, "b": 5.1}).fired,
        "p1_needs_one_xi_at_least_10": tsi.phase0_localization({"a": 3.0, "b": 10.0}).fired
        and not tsi.phase0_localization({"a": 9.9}).fired,
        "k2a_fires_at_80_percent_recovery": k2a_fires.fired and k2a_fires.evaluable,
        "k2a_holds_below_80_percent_recovery": not k2a_holds.fired and k2a_holds.evaluable,
        "k2a_not_evaluable_when_shortfall_under_3": not k2a_not_evaluable.evaluable
        and not k2a_not_evaluable.fired,
        "k2b_fires_at_or_below_kappa": tsi.k2b_weak_alignment_effect(rule.kappa, rule, True).fired,
        "k2b_inconclusive_between_kappa_and_6": not tsi.k2b_weak_alignment_effect(
            rule.kappa + 0.1, rule, True
        ).fired
        and "inconclusive" in tsi.k2b_weak_alignment_effect(rule.kappa + 0.1, rule, True).note,
        "k3_needs_inertness": not tsi.k3_loss_form(10.0, 9.0, 0.0, False).evaluable
        and tsi.k3_loss_form(10.0, 9.0, 0.0, True).fired
        and not tsi.k3_loss_form(10.0, 7.9, 0.0, True).fired,
        "k4_fires_at_half_of_D": tsi.k4_semantic_sharpening(10.0, 5.0).fired
        and not tsi.k4_semantic_sharpening(10.0, 4.9).fired,
        "k8_fires_on_2_point_language_drop_or_half_point_e3_drop": tsi.k8_language_harm(
            {"ja": 2.1}, 0.0
        ).fired
        and tsi.k8_language_harm({"ja": 0.0}, 0.6).fired
        and not tsi.k8_language_harm({"ja": 2.0}, 0.5).fired,
        "inertness_tolerance_is_one_point": tsi.inertness_holds(90.0, 91.0)
        and not tsi.inertness_holds(90.0, 91.1),
    }
    return {
        "gates": checks,
        "t_star_hand_made": asdict(t_star),
        "kappa_for_assumed_inputs": rule.kappa,
    }


# --------------------------------------------------------------------------- #


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(
            f"{args.output} exists; a material change is a new versioned attempt "
            "with a new output path"
        )
    if len(set(args.seeds)) < 3:
        raise SystemExit("at least three distinct seeds are required")
    started = time.perf_counter()
    cases: dict[str, Any] = {}
    cases["synthetic_excess_gap_and_repair"], trained = case_excess_gap_and_repair(
        args.seeds, args.families
    )
    cases["shifted_script_negative_control"] = case_shifted_script(trained)
    cases["fixed_reference_brute_force_and_chance_level"] = case_fixed_reference(args.seeds[0])
    cases["analytic_gradient_check"] = case_gradient_check()
    cases["alignment_loss_mass_accounting_and_permutation_sensitivity"] = case_alignment_loss(
        trained
    )
    cases["decision_rule_from_stated_noise_model"] = case_decision_rule()
    cases["passage_split_and_read_separation"] = case_passage_split()
    cases["leakage_and_causality_perturbations"] = case_leakage_and_causality(trained)
    cases["degenerate_input_rejection"] = case_degenerate_inputs()
    cases["gate_semantics_on_hand_made_tables"] = case_gate_semantics()
    elapsed = time.perf_counter() - started

    case_status = {
        name: ("PASS" if all(case["gates"].values()) else "FAIL") for name, case in cases.items()
    }
    all_pass = all(status == "PASS" for status in case_status.values())
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "doctor": DOCTOR_NAME,
        "status": "PHASE0_DOCTOR_PASS" if all_pass else "PHASE0_DOCTOR_FAIL",
        "evidence_grade": EVIDENCE_GRADE,
        "numbers_are_synthetic": True,
        "seeds": list(args.seeds),
        "families_per_direction": args.families,
        "case_status": case_status,
        "cases": cases,
        "runtime_seconds": elapsed,
        "provenance": {
            "implementation": "harness/translation_supervised_indexer.py",
            "implementation_sha256": hashlib.sha256(
                (PROJECT_ROOT / "harness" / "translation_supervised_indexer.py").read_bytes()
            ).hexdigest(),
            "doctor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "python_version": sys.version.split()[0],
            "runtime": "numpy-cpu",
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode()
    with args.output.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    summary = {
        "status": payload["status"],
        "case_status": case_status,
        "runtime_seconds": round(elapsed, 2),
        "evidence_grade": EVIDENCE_GRADE,
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
