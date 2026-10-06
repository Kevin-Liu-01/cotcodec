from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from harness.memory_trials.gaama_natural import (
    DEV_SAMPLE_IDS,
    TEST_SAMPLE_IDS,
    _edge_degree_signature,
    load_locomo_graphs,
    run_natural_holdout,
)
from scripts.validate_gaama_natural_experiment import (
    DEFAULT_EXPERIMENT,
    GaamaNaturalExperimentError,
    validate_experiment_contract,
)


def _fixture() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sample_index, sample_id in enumerate(DEV_SAMPLE_IDS + TEST_SAMPLE_IDS):
        rows.append(
            {
                "sample_id": sample_id,
                "conversation": {
                    "speaker_a": "A",
                    "speaker_b": "B",
                    "session_1_date_time": "7 May 2023",
                    "session_1": [
                        {
                            "speaker": "A",
                            "dia_id": "D1:1",
                            "text": f"marker {sample_index} alpha",
                        },
                        {
                            "speaker": "B",
                            "dia_id": "D1:2",
                            "text": "unrelated bridge",
                        },
                        {
                            "speaker": "A",
                            "dia_id": "D1:3",
                            "text": "target evidence",
                        },
                    ],
                    "session_2_date_time": "8 May 2023",
                    "session_2": [
                        {
                            "speaker": "B",
                            "dia_id": "D2:1",
                            "text": "second session context",
                        },
                        {
                            "speaker": "A",
                            "dia_id": "D2:2",
                            "text": "second session continuation",
                        },
                    ],
                },
                "qa": [
                    {
                        "question": f"marker {sample_index}",
                        "answer": "unused answer",
                        "evidence": ["D1:3"],
                        "category": 1,
                    },
                    {
                        "question": "excluded adversarial category",
                        "answer": "unused",
                        "evidence": ["D1:1"],
                        "category": 5,
                    },
                ],
            }
        )
    return rows


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_natural_study_uses_exact_split_and_ignores_answers(tmp_path: Path) -> None:
    original = _fixture()
    first = tmp_path / "first.json"
    _write(first, original)
    report = run_natural_holdout(first)
    assert report["dev_sample_ids"] == list(DEV_SAMPLE_IDS)
    assert report["test_sample_ids"] == list(TEST_SAMPLE_IDS)
    assert report["dev_questions"] == 3
    assert report["test_questions"] == 7
    assert report["integrity_gates"]["zero_weight_lexical_a_a_exact"] is True
    assert report["integrity_gates"]["graph_candidate_and_degree_contract"] is True
    assert report["model_calls"] == report["embedding_calls"] == 0

    changed = copy.deepcopy(original)
    for sample in changed:
        sample["qa"][0]["answer"] = "completely different secret answer"
    second = tmp_path / "second.json"
    _write(second, changed)
    changed_report = run_natural_holdout(second)
    excluded = {"dataset_sha256", "report_sha256"}
    comparable = {key: value for key, value in report.items() if key not in excluded}
    changed_comparable = {
        key: value
        for key, value in changed_report.items()
        if key not in {"dataset_sha256", "report_sha256"}
    }
    assert comparable == changed_comparable


def test_natural_loader_rejects_malformed_evidence_without_leaking_it(tmp_path: Path) -> None:
    payload = _fixture()
    payload[0]["qa"][0]["evidence"] = ["not-a-dialogue-id"]
    path = tmp_path / "bad-evidence.json"
    _write(path, payload)
    graphs = load_locomo_graphs(path)
    first = next(graph for graph in graphs if graph.sample_id == DEV_SAMPLE_IDS[0])
    assert first.questions == ()


def test_shuffled_graph_preserves_each_nodes_typed_directed_degree(
    tmp_path: Path,
) -> None:
    path = tmp_path / "degree-control.json"
    _write(path, _fixture())
    for graph in load_locomo_graphs(path):
        true_signature = _edge_degree_signature(graph.true_edges)
        for shuffled in graph.shuffled_edges.values():
            assert _edge_degree_signature(shuffled) == true_signature
            assert set(shuffled) != set(graph.true_edges)


def test_registered_natural_experiment_validates() -> None:
    payload = validate_experiment_contract()
    assert payload["contract"]["expected_test_questions"] == 1146


def test_registered_natural_experiment_rejects_split_drift(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["contract"]["test_sample_ids"].reverse()
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(GaamaNaturalExperimentError, match="retrieval contract drifted"):
        validate_experiment_contract(path)
