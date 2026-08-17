from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from harness.memory_trials.neo4j_flat_parity import (
    build_frozen_cases,
    canonical_tuple_payload,
    create_flat_database,
    flat_bm25_dense_rank,
    flat_sql_join_rank,
    validate_fixture,
)
from scripts.run_neo4j_flat_parity_doctor import (
    DoctorError,
    _canonical,
    _sha,
    _validate_component_report,
)
from scripts.validate_neo4j_flat_parity_experiment import (
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)


def test_frozen_fixture_separates_flat_retrieval_from_exact_join() -> None:
    cases = build_frozen_cases()
    report = validate_fixture(cases)
    assert report == {
        "case_count": 48,
        "tuple_count": 672,
        "tuple_payload_bytes": 254280,
        "tuple_payload_sha256": (
            "7d2f8a690aa754a559cb69165d34b9c866eb5aba9d226519f4ae79475b67496c"
        ),
        "flat_hits": 0,
        "flat_join_hits": 48,
        "top_k": 2,
    }


def test_flat_arms_use_same_immutable_tuple_payload() -> None:
    cases = build_frozen_cases(2)
    first = canonical_tuple_payload(cases)
    assert first == canonical_tuple_payload(build_frozen_cases(2))
    database = create_flat_database(cases)
    try:
        for case in cases:
            flat = flat_bm25_dense_rank(database, case)
            joined = flat_sql_join_rank(database, case)
            assert case.target_tuple_id not in flat
            assert case.target_tuple_id in joined
    finally:
        database.close()


def test_object_shuffle_preserves_object_multiset_and_breaks_true_path() -> None:
    case = build_frozen_cases(1)[0]
    true_objects = sorted(row.object for row in case.tuples)
    shuffled_objects = sorted(object_ for _, object_ in case.shuffled_objects)
    assert shuffled_objects == true_objects
    shuffled = dict(case.shuffled_objects)
    first = next(row for row in case.tuples if row.tuple_id.endswith("tuple-m-first"))
    assert shuffled[first.tuple_id] != first.object


def test_registered_flat_parity_contract_is_exact() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["slurm_h100_count"] == 1
    assert payload["runtime"]["container_gpu_count"] == 0
    assert payload["contract"]["case_count"] == 48
    assert payload["scientific_result"] is False


def test_flat_parity_contract_drift_fails_closed(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["contract"]["logical_retrieval_calls_per_arm_per_case"] = 2
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="component contract drifted"):
        validate_experiment_contract(path)


def test_component_report_validator_binds_rows_gates_and_hash() -> None:
    report = {
        "schema_version": 1,
        "study": "neo4j-identical-tuple-flat-parity-v1",
        "status": "NEO4J_IDENTICAL_TUPLE_TRAVERSAL_COMPONENT_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "source_revision": "231d60eac9401ab156ba194b519d89dd644dadb8",
        "case_count": 48,
        "tuple_count": 672,
        "top_k": 2,
        "max_injected_bytes": 256,
        "hit_counts": {
            "flat_bm25_dense": 0,
            "zero_traversal": 0,
            "flat_sql_join": 48,
            "true_graph": 48,
            "shuffled_graph": 0,
        },
        "model_calls": 0,
        "embedding_model_calls": 0,
        "external_network_calls": 0,
        "gates": {"all": True},
        "rows": [{"case_id": f"case-{index:03d}"} for index in range(48)],
    }
    report["report_sha256"] = _sha(_canonical(report))
    _validate_component_report(report)
    report["rows"][0]["case_id"] = "tampered"
    with pytest.raises(DoctorError, match="contract or hash drifted"):
        _validate_component_report(report)
