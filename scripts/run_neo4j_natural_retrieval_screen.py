#!/usr/bin/env python3
"""Run the frozen natural-session topology falsifier without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.neo4j_natural_parity import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
    PANEL_SEED,
    PANEL_TYPES,
    QUESTIONS_PER_TYPE,
    SHUFFLE_SEEDS,
    TOP_K,
    canonical_case_payload,
    chronological_edges,
    freeze_case_rankings,
    load_natural_panel,
    recall_all,
    shuffled_edges,
)

BOOTSTRAP_SEED = 20260815
BOOTSTRAP_DRAWS = 10_000
STATUS_PASS = "NATURAL_SESSION_TOPOLOGY_RETRIEVAL_PASS"
STATUS_KILLED = "NATURAL_SESSION_TOPOLOGY_RETRIEVAL_KILLED"


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_once(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(value)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _stratified_bootstrap(
    rows: list[dict[str, Any]],
    left: str,
    right: str,
) -> tuple[float, float]:
    grouped = {
        question_type: [row for row in rows if row["question_type"] == question_type]
        for question_type in PANEL_TYPES
    }
    rng = random.Random(BOOTSTRAP_SEED)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_DRAWS):
        sample = [
            rng.choice(grouped[question_type])
            for question_type in PANEL_TYPES
            for _ in grouped[question_type]
        ]
        draws.append(
            sum(float(row["hits"][left]) - float(row["hits"][right]) for row in sample)
            / len(sample)
        )
    draws.sort()
    return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]


def _exact_sign_pvalue(rows: list[dict[str, Any]], left: str, right: str) -> float:
    wins = sum(row["hits"][left] and not row["hits"][right] for row in rows)
    losses = sum(row["hits"][right] and not row["hits"][left] for row in rows)
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    probability = sum(
        math.comb(discordant, value) for value in range(wins, discordant + 1)
    ) / (2**discordant)
    return min(1.0, probability)


def _degrees(edges: tuple[tuple[str, str], ...]) -> Counter[str]:
    return Counter(value for edge in edges for value in edge)


def run_screen(dataset: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite output directory: {output_dir}")
    cases = load_natural_panel(dataset)
    case_payload = canonical_case_payload(cases)
    rows: list[dict[str, Any]] = []
    for case in cases:
        rankings = freeze_case_rankings(case)
        degree_match = all(
            _degrees(chronological_edges(case)) == _degrees(shuffled_edges(case, seed))
            for seed in SHUFFLE_SEEDS
        )
        rows.append(
            {
                "question_id": case.question_id,
                "question_type": case.question_type,
                "answer_session_count": len(case.answer_session_ids),
                "session_count": len(case.sessions),
                "rankings": {key: list(value) for key, value in rankings.items()},
                "hits": {key: recall_all(case, value) for key, value in rankings.items()},
                "degree_match": degree_match,
            }
        )
    arms = tuple(rows[0]["rankings"])
    hit_rates = {
        arm: sum(row["hits"][arm] for row in rows) / len(rows) for arm in arms
    }
    shuffle_arms = tuple(f"shuffled_topology_seed_{seed}" for seed in SHUFFLE_SEEDS)
    mean_shuffle = sum(hit_rates[arm] for arm in shuffle_arms) / len(shuffle_arms)
    true_flat_delta = hit_rates["true_topology"] - hit_rates["flat_bm25_dense"]
    true_shuffle_delta = hit_rates["true_topology"] - mean_shuffle
    true_flat_ci = _stratified_bootstrap(rows, "true_topology", "flat_bm25_dense")
    shuffle_cis = {
        arm: _stratified_bootstrap(rows, "true_topology", arm)
        for arm in shuffle_arms
    }
    gates = {
        "exact_registered_dataset": dataset.stat().st_size == LONGMEMEVAL_S_SIZE
        and _sha256(dataset.read_bytes()) == LONGMEMEVAL_S_SHA256,
        "balanced_frozen_panel": len(cases) == QUESTIONS_PER_TYPE * len(PANEL_TYPES)
        and Counter(case.question_type for case in cases)
        == Counter({question_type: QUESTIONS_PER_TYPE for question_type in PANEL_TYPES}),
        "top_k_unique_roster": all(
            len(ranking) == len(set(ranking)) == TOP_K
            for row in rows
            for ranking in row["rankings"].values()
        ),
        "node_degree_preserved_in_shuffles": all(row["degree_match"] for row in rows),
        "true_lift_over_flat_at_least_3_points": true_flat_delta >= 0.03,
        "true_flat_bootstrap_lower_bound_above_zero": true_flat_ci[0] > 0.0,
        "true_lift_over_mean_shuffle_at_least_3_points": true_shuffle_delta >= 0.03,
        "true_beats_each_shuffle_lower_bound_above_zero": all(
            interval[0] > 0.0 for interval in shuffle_cis.values()
        ),
    }
    integrity = {
        key: value
        for key, value in gates.items()
        if key
        in {
            "exact_registered_dataset",
            "balanced_frozen_panel",
            "top_k_unique_roster",
            "node_degree_preserved_in_shuffles",
        }
    }
    if not all(integrity.values()):
        raise RuntimeError(f"natural topology integrity gate failed: {integrity}")
    claim_gates = {key: value for key, value in gates.items() if key not in integrity}
    status = STATUS_PASS if all(claim_gates.values()) else STATUS_KILLED
    report = {
        "schema_version": 1,
        "study": "longmemeval-natural-session-topology-retrieval-v1",
        "status": status,
        "source": {
            "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
            "dataset_sha256": LONGMEMEVAL_S_SHA256,
            "dataset_size": LONGMEMEVAL_S_SIZE,
            "panel_seed": PANEL_SEED,
            "case_payload_sha256": _sha256(case_payload),
        },
        "panel": {
            "questions": len(cases),
            "questions_per_type": QUESTIONS_PER_TYPE,
            "question_types": list(PANEL_TYPES),
            "top_k": TOP_K,
            "shuffle_seeds": list(SHUFFLE_SEEDS),
        },
        "metrics": {
            "recall_all_at_4": hit_rates,
            "true_minus_flat": true_flat_delta,
            "true_minus_flat_bootstrap_95_ci": list(true_flat_ci),
            "true_minus_mean_shuffle": true_shuffle_delta,
            "true_minus_shuffle_bootstrap_95_ci": {
                key: list(value) for key, value in shuffle_cis.items()
            },
            "true_vs_flat_one_sided_sign_p": _exact_sign_pvalue(
                rows, "true_topology", "flat_bm25_dense"
            ),
            "true_vs_shuffle_one_sided_sign_p": {
                arm: _exact_sign_pvalue(rows, "true_topology", arm)
                for arm in shuffle_arms
            },
        },
        "gates": gates,
        "rows": rows,
        "model_calls": 0,
        "embedding_model_calls": 0,
        "scientific_result": False,
        "publication_ready": False,
        "interpretation": (
            "A bounded natural-session topology falsifier only. It does not test "
            "Neo4j storage quality, learned extraction, answer quality, or an agent."
        ),
    }
    panel = {
        "schema_version": 1,
        "source_sha256": LONGMEMEVAL_S_SHA256,
        "case_payload_sha256": _sha256(case_payload),
        "cases": [
            {
                "question_id": case.question_id,
                "question_type": case.question_type,
                "question": case.question,
                "answer": case.answer,
                "answer_session_ids": list(case.answer_session_ids),
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "position": session.position,
                        "date": session.date,
                        "text": session.text,
                    }
                    for session in case.sessions
                ],
            }
            for case in cases
        ],
    }
    output_dir.mkdir(parents=True)
    report_bytes = _canonical(report)
    panel_bytes = _canonical(panel)
    _write_once(output_dir / "report.json", report_bytes)
    _write_once(output_dir / "panel.json", panel_bytes)
    manifest = {
        "schema_version": 1,
        "status": status,
        "files": {
            "panel.json": {"sha256": _sha256(panel_bytes), "bytes": len(panel_bytes)},
            "report.json": {"sha256": _sha256(report_bytes), "bytes": len(report_bytes)},
        },
    }
    _write_once(output_dir / "manifest.json", _canonical(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_screen(args.dataset, args.output_dir)
    print(_canonical({"status": report["status"], "metrics": report["metrics"]}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
