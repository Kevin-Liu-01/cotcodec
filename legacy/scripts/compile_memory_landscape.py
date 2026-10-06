#!/usr/bin/env python3
"""Compile the memory-source ledger into a reproducible research matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

if __package__:
    from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate
else:
    from validate_memory_sources import DEFAULT_LEDGER, load_and_validate

LANES = (
    "active-inactive",
    "context-paging",
    "manual-lifecycle",
    "consolidation",
    "active-context",
    "inactive-archive",
    "episodic",
    "semantic-profile",
    "graph",
    "temporal-graph",
    "procedural",
    "latent-state",
    "controller",
    "benchmark",
    "safety",
)
REPRODUCED_GRADES = {"externally-reproduced", "local-reproduced"}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _lanes_for(source: dict[str, Any]) -> list[str]:
    layers = set(source["memory_layers"])
    kind = source["kind"].lower()
    use_as = " ".join(source["use_as"]).lower()
    lanes: list[str] = []
    residency = source.get("residency_transition", "not-reviewed")
    if residency in {"bidirectional-residency", "active-to-inactive", "inactive-to-active"}:
        lanes.append("active-inactive")
    if residency == "chronological-context-paging":
        lanes.append("context-paging")
    if residency == "manual-promotion":
        lanes.append("manual-lifecycle")
    if residency == "one-way-consolidation":
        lanes.append("consolidation")
    layer_lanes = {
        "active_context": "active-context",
        "inactive_archive": "inactive-archive",
        "episodic_log": "episodic",
        "semantic_profile": "semantic-profile",
        "temporal_graph": "graph",
        "procedural_memory": "procedural",
        "latent_state": "latent-state",
        "controller": "controller",
    }
    lanes.extend(
        lane for layer, lane in layer_lanes.items() if layer in layers
    )
    graph_semantics = source.get(
        "graph_semantics", "generic" if "temporal_graph" in layers else "none"
    )
    if graph_semantics == "temporal-validity":
        lanes.append("temporal-graph")
    if "benchmark" in kind:
        lanes.append("benchmark")
    if "safety" in kind or any(
        marker in use_as
        for marker in ("safety", "poison", "authority", "governance")
    ):
        lanes.append("safety")
    return [lane for lane in LANES if lane in lanes]


def _access_class(source: dict[str, Any]) -> str:
    repositories = source.get("repositories", [])
    artifacts = source.get("artifacts", [])
    if not repositories:
        return "pinned-artifact-only" if artifacts else "paper-or-page-only"
    resolved = sum(repo["license"] != "unresolved" for repo in repositories)
    if resolved == len(repositories):
        return "all-repository-licenses-resolved"
    if resolved:
        return "mixed-repository-license-status"
    return "all-repository-licenses-unresolved"


def compile_landscape(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical matrix without inferring scientific reproduction."""

    rows: list[dict[str, Any]] = []
    for source_id, source in sorted(payload["sources"].items()):
        repositories = [
            {
                "license": repository["license"],
                "revision": repository["revision"],
                "role": repository["role"],
                "url": repository["url"],
            }
            for repository in source.get("repositories", [])
        ]
        rows.append(
            {
                "source_id": source_id,
                "title": source["title"],
                "kind": source["kind"],
                "observed_on": source["observed_on"],
                "memory_layers": list(source["memory_layers"]),
                "residency_transition": source.get(
                    "residency_transition", "not-reviewed"
                ),
                "graph_semantics": source.get(
                    "graph_semantics",
                    "generic" if "temporal_graph" in source["memory_layers"] else "none",
                ),
                "lanes": _lanes_for(source),
                "use_as": list(source["use_as"]),
                "evidence_grade": source["evidence_grade"],
                "scientific_result_reproduced": (
                    source["evidence_grade"] in REPRODUCED_GRADES
                ),
                "conformance_result_reproduced": (
                    source["evidence_grade"] == "local-conformance-reproduced"
                ),
                "negative_finding_reproduced": (
                    source["evidence_grade"] == "local-negative-reproduced"
                ),
                "access_class": _access_class(source),
                "repository_count": len(repositories),
                "resolved_license_repository_count": sum(
                    repository["license"] != "unresolved"
                    for repository in repositories
                ),
                "repositories": repositories,
                "artifact_count": len(source.get("artifacts", [])),
                "primary_sources": list(source["primary_sources"]),
            }
        )

    lane_counts = Counter(lane for row in rows for lane in row["lanes"])
    access_counts = Counter(row["access_class"] for row in rows)
    evidence_counts = Counter(row["evidence_grade"] for row in rows)
    matrix_identity = {
        "ledger_schema_version": payload["schema_version"],
        "ledger_verified_at": payload["verified_at"],
        "rows": rows,
    }
    return {
        "schema_version": 1,
        "ledger_schema_version": payload["schema_version"],
        "ledger_verified_at": payload["verified_at"],
        "source_count": len(rows),
        "matrix_sha256": _canonical_sha256(matrix_identity),
        "lane_counts": dict(sorted(lane_counts.items())),
        "access_class_counts": dict(sorted(access_counts.items())),
        "evidence_grade_counts": dict(sorted(evidence_counts.items())),
        "reproduced_source_count": sum(
            row["scientific_result_reproduced"] for row in rows
        ),
        "conformance_reproduced_source_count": sum(
            row["conformance_result_reproduced"] for row in rows
        ),
        "negative_finding_reproduced_source_count": sum(
            row["negative_finding_reproduced"] for row in rows
        ),
        "rows": rows,
    }


def _filter_rows(matrix: dict[str, Any], lanes: list[str]) -> list[dict[str, Any]]:
    if not lanes:
        return matrix["rows"]
    requested = set(lanes)
    return [row for row in matrix["rows"] if requested <= set(row["lanes"])]


def _render_markdown(matrix: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Agent-memory source matrix",
        "",
        f'- Ledger verified: `{matrix["ledger_verified_at"]}`',
        f'- Full matrix SHA-256: `{matrix["matrix_sha256"]}`',
        f'- Full source count: {matrix["source_count"]}',
        f"- Rows in this view: {len(rows)}",
        f'- Sources with reproduced scientific results: {matrix["reproduced_source_count"]}',
        "",
        "| ID | Title | Lanes | Access | Evidence | Reproduced |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        title = row["title"].replace("|", "\\|")
        lanes = ", ".join(row["lanes"])
        reproduced = "yes" if row["scientific_result_reproduced"] else "no"
        lines.append(
            f'| `{row["source_id"]}` | {title} | {lanes} | '
            f'{row["access_class"]} | {row["evidence_grade"]} | {reproduced} |'
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--lane",
        action="append",
        choices=LANES,
        default=[],
        help="require a lane; repeat to require an intersection",
    )
    args = parser.parse_args()
    matrix = compile_landscape(load_and_validate(args.ledger))
    rows = _filter_rows(matrix, args.lane)
    if args.format == "markdown":
        print(_render_markdown(matrix, rows), end="")
    else:
        output = dict(matrix)
        output["rows"] = rows
        output["view_source_count"] = len(rows)
        output["required_lanes"] = args.lane
        print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
