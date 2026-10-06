from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from harness.memory_trials.gaama_component import (
    FrozenEdge,
    build_frozen_cases,
    edges_from_frozen,
    rank_nodes,
    run_component_doctor,
)
from scripts.validate_gaama_graph_experiment import (
    DEFAULT_EXPERIMENT,
    GaamaExperimentError,
    validate_experiment_contract,
)


def test_component_doctor_passes_matched_falsifiers() -> None:
    report = run_component_doctor()
    assert report["status"] == "GAAMA_COMPONENT_CONTRACT_PASS"
    assert report["ppr_weight_zero_equal_flat"] is True
    assert report["flat_hits"] == 0
    assert report["true_graph_hits"] == 24
    assert report["shuffled_graph_hits"] == 0
    assert report["model_calls"] == report["embedding_calls"] == 0


def test_ppr_weight_zero_is_exact_flat_with_same_candidates() -> None:
    case = build_frozen_cases(1)[0]
    nodes = case["nodes"]
    edges = case["true_edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    assert rank_nodes(nodes, [], ppr_weight=0.0) == rank_nodes(
        nodes, edges, ppr_weight=0.0
    )


def test_hub_dampening_is_cancelled_by_row_normalization() -> None:
    edges = [FrozenEdge("hub", f"leaf-{index:03d}") for index in range(60)]
    assert edges_from_frozen(edges, hub_dampening_threshold=50) == edges_from_frozen(
        edges, hub_dampening_threshold=0
    )


def test_registered_gaama_experiment_validates() -> None:
    payload = validate_experiment_contract()
    assert payload["gates"]["required_status"] == "GAAMA_COMPONENT_CONTRACT_PASS"


def test_gaama_experiment_rejects_graph_arm_drift(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["contract"]["graph_arms"].remove("degree-type-shuffled-graph")
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(GaamaExperimentError, match="component contract drifted"):
        validate_experiment_contract(path)
