from __future__ import annotations

from scripts.compile_memory_landscape import compile_landscape
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate


def _rows_by_id() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    matrix = compile_landscape(load_and_validate(DEFAULT_LEDGER))
    rows = {row["source_id"]: row for row in matrix["rows"]}
    return matrix, rows


def test_live_landscape_is_complete_and_content_addressed() -> None:
    matrix, rows = _rows_by_id()
    assert matrix["source_count"] == len(rows) == 229
    assert len(matrix["matrix_sha256"]) == 64
    assert matrix["reproduced_source_count"] == 1
    assert matrix["conformance_reproduced_source_count"] == 2
    assert matrix["negative_finding_reproduced_source_count"] == 33
    assert matrix["access_class_counts"]["paper-or-page-only"] == 60


def test_active_inactive_and_graph_lanes_are_structural() -> None:
    _, rows = _rows_by_id()
    assert "active-inactive" in rows["memgpt-letta"]["lanes"]
    assert "temporal-graph" in rows["sodamem"]["lanes"]
    assert "active-inactive" not in rows["sodamem"]["lanes"]
    assert "latent-state" in rows["foresightkv"]["lanes"]
    assert "benchmark" in rows["pm-bench"]["lanes"]
    assert "active-inactive" not in rows["timem"]["lanes"]
    assert "inactive-archive" in rows["timem"]["lanes"]
    assert "graph" in rows["h-mem"]["lanes"]
    assert "temporal-graph" not in rows["h-mem"]["lanes"]
    assert "temporal-graph" in rows["graphiti"]["lanes"]
    assert "temporal-graph" in rows["sodamem"]["lanes"]
    assert "temporal-graph" not in rows["neo4j-agent-memory"]["lanes"]
    assert "context-paging" in rows["magic-context"]["lanes"]
    assert "active-inactive" not in rows["magic-context"]["lanes"]
    assert "manual-lifecycle" in rows["icarus-memory-infra"]["lanes"]
    assert "active-inactive" not in rows["memoria-matrixorigin"]["lanes"]
    assert "temporal-graph" in rows["agent-recall"]["lanes"]
    assert "graph" in rows["memorygraph-typed-coding-memory"]["lanes"]
    assert "active-inactive" not in rows["tokenmizer"]["lanes"]
    assert "graph" in rows["activegraph-event-sourced-runtime"]["lanes"]
    assert "temporal-graph" not in rows["activegraph-event-sourced-runtime"]["lanes"]
    assert "manual-lifecycle" in rows["memforge"]["lanes"]
    assert "active-inactive" not in rows["memforge"]["lanes"]
    assert "active-inactive" not in rows["agenticow"]["lanes"]
    assert "consolidation" in rows["hermes-observational-memory"]["lanes"]


def test_repository_license_status_does_not_imply_reproduction() -> None:
    _, rows = _rows_by_id()
    sodamem = rows["sodamem"]
    foresightkv = rows["foresightkv"]
    assert sodamem["access_class"] == "all-repository-licenses-resolved"
    assert sodamem["scientific_result_reproduced"] is False
    assert rows["fidelis"]["scientific_result_reproduced"] is True
    assert foresightkv["access_class"] == "all-repository-licenses-unresolved"
    assert foresightkv["resolved_license_repository_count"] == 0


def test_negative_and_conformance_evidence_are_not_scientific_results() -> None:
    _, rows = _rows_by_id()
    total_recall = rows["total-recall-oss"]
    hippo = rows["hippo-memory"]
    hermes = rows["hermes-provider-conformance"]
    assert total_recall["negative_finding_reproduced"] is True
    assert total_recall["scientific_result_reproduced"] is False
    assert hippo["negative_finding_reproduced"] is True
    assert hippo["scientific_result_reproduced"] is False
    assert hermes["conformance_result_reproduced"] is True
    assert hermes["scientific_result_reproduced"] is False
