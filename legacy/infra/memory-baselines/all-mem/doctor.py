#!/usr/bin/env python3
"""Contained falsifier for All-Mem archived-source recoverability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import deque
from pathlib import Path
from typing import Any

from all_mem.core import AllMemNode, AllMemSystem, HashEmbeddingModel

STATE_PATH = Path("/state/graph.pkl")
RECOVERY_EDGE_TYPES = {"sibling_split", "sibling", "version", "revision"}
FORBIDDEN_SECRETS = {
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ARK_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    if isinstance(value, set):
        return sorted(canonical(item) for item in value)
    return value


def digest(value: Any) -> str:
    data = json.dumps(canonical(value), separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


class DeterministicController:
    """Closed local controller; never calls a model or network service."""

    def __init__(self) -> None:
        self.stub_calls = 0
        self.split_source_index_prompt_observed = False

    def complete_json(self, prompt: str, *_: Any, **__: Any) -> dict[str, Any]:
        self.stub_calls += 1
        if "Split this All-Mem node" in prompt:
            return {
                "segments": [
                    "The user drinks cedar coffee every morning.",
                    "The user climbs quartz routes every weekend.",
                ]
            }
        if "merged memory block" in prompt:
            return {
                "summary": "The user has a cobalt appointment on Friday.",
                "keywords": ["cobalt", "appointment", "Friday"],
            }
        if "indexing component of All-Mem" in prompt:
            marker = "cedar coffee"
            if marker in prompt:
                self.split_source_index_prompt_observed = True
            raw = prompt.split("Raw content:\n", 1)[-1].split("\n", 1)[0].strip()
            return {"summary": raw[:200], "keywords": raw.lower().split()[:5]}
        if "graph curator" in prompt:
            return {"split_tasks": [], "merge_tasks": [], "update_tasks": []}
        fail("unexpected deterministic-controller prompt")


def node_label(node: AllMemNode) -> str:
    sources = ",".join(sorted(str(value) for value in node.source_ids)) or "none"
    content_hash = hashlib.sha256(node.first_content().encode()).hexdigest()[:12]
    return f"{sources}:{content_hash}"


def source_node_id(system: AllMemSystem, source_id: str) -> str:
    matches = [
        node_id
        for node_id, data in system.graph.graph.nodes(data=True)
        if source_id in {str(value) for value in data["data"].source_ids}
        and data["data"].source_id == source_id
    ]
    if len(matches) != 1:
        fail(f"expected one original node for {source_id}, found {len(matches)}")
    return matches[0]


def derived_node_ids(system: AllMemSystem, source_ids: set[str]) -> list[str]:
    matches = []
    for node_id, data in system.graph.graph.nodes(data=True):
        node = data["data"]
        if {str(value) for value in node.source_ids} == source_ids and node.source_id is None:
            matches.append(node_id)
    return matches


def has_recovery_path(system: AllMemSystem, start: str, target: str) -> bool:
    queue: deque[str] = deque([start])
    seen = {start}
    while queue:
        current = queue.popleft()
        if current == target:
            return True
        for left, right, data in system.graph.graph.out_edges(current, data=True):
            if left != current or data.get("type") not in RECOVERY_EDGE_TYPES:
                continue
            if right not in seen:
                seen.add(right)
                queue.append(right)
        for left, right, data in system.graph.graph.in_edges(current, data=True):
            if right != current or data.get("type") not in RECOVERY_EDGE_TYPES:
                continue
            if left not in seen:
                seen.add(left)
                queue.append(left)
    return False


def build_projection(system: AllMemSystem) -> dict[str, Any]:
    graph = system.graph.graph
    labels = {node_id: node_label(data["data"]) for node_id, data in graph.nodes(data=True)}
    rows = []
    for node_id, data in graph.nodes(data=True):
        node = data["data"]
        rows.append(
            {
                "label": labels[node_id],
                "source_id": node.source_id,
                "source_ids": sorted(str(value) for value in node.source_ids),
                "status": node.status,
                "content_sha256": hashlib.sha256(node.first_content().encode()).hexdigest(),
            }
        )
    edges = sorted(
        {
            (labels[left], labels[right], str(data.get("type", "")))
            for left, right, data in graph.edges(data=True)
        }
    )

    update_old = source_node_id(system, "update-old")
    update_new = source_node_id(system, "update-new")
    split_old = source_node_id(system, "split-original")
    merge_a = source_node_id(system, "merge-a")
    merge_b = source_node_id(system, "merge-b")
    split_derived = derived_node_ids(system, {"split-original"})
    merge_derived = derived_node_ids(system, {"merge-a", "merge-b"})
    if len(split_derived) != 2 or len(merge_derived) != 1:
        fail("derived split or merge node roster drifted")

    _, ranked_source_ids, _ = system.get_context_for_query(
        "project status changed from amber to blue",
        anchor_k=20,
        final_k=20,
        max_candidates=50,
    )
    recovery = {
        "update": has_recovery_path(system, update_new, update_old),
        "split": all(has_recovery_path(system, child, split_old) for child in split_derived),
        "merge_a": has_recovery_path(system, merge_derived[0], merge_a),
        "merge_b": has_recovery_path(system, merge_derived[0], merge_b),
    }
    projection = {
        "nodes": sorted(rows, key=lambda row: (row["label"], row["status"])),
        "edges": edges,
        "active_count": sum(row["status"] == "Active" for row in rows),
        "archived_count": sum(row["status"] == "Archived" for row in rows),
        "recovery": recovery,
        "query": {
            "ranked_source_ids": ranked_source_ids,
            "update_old_recovered": "update-old" in ranked_source_ids,
            "update_new_recovered": "update-new" in ranked_source_ids,
        },
        "derived_source_labels_without_raw_path": (
            not recovery["split"] and not recovery["merge_a"] and not recovery["merge_b"]
        ),
        "native_scoped_purge": hasattr(system, "purge"),
        "persistence_format": "pickle",
    }
    projection["sha256"] = digest(projection)
    return projection


def prepare() -> dict[str, Any]:
    if (
        not STATE_PATH.is_file()
        or STATE_PATH.is_symlink()
        or STATE_PATH.stat().st_size != 0
    ):
        fail("prepare requires a fresh empty regular state file")
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    controller = DeterministicController()
    system = AllMemSystem(controller, diagnosis_workers=1)
    if not isinstance(system.graph.embedding_model, HashEmbeddingModel):
        fail("doctor requires the deterministic hash embedding fallback")

    update_old = system.wake_process(
        "The project status is amber.", "2026-08-01T00:00:00Z", "update-old"
    )
    update_new = system.wake_process(
        "The project status is blue.", "2026-08-02T00:00:00Z", "update-new"
    )
    merge_a = system.wake_process(
        "The user has a cobalt appointment on Friday.",
        "2026-08-03T00:00:00Z",
        "merge-a",
    )
    merge_b = system.wake_process(
        "The user has a cobalt appointment on Friday.",
        "2026-08-03T00:01:00Z",
        "merge-b",
    )
    split_original = system.wake_process(
        "The user drinks cedar coffee and climbs quartz routes.",
        "2026-08-04T00:00:00Z",
        "split-original",
    )

    system._op_update(update_old, update_new, "new project status supersedes old")
    system._op_merge([merge_a, merge_b], "duplicate appointment facts")
    system._op_split(split_original, "unrelated coffee and climbing topics")
    system.graph.rebuild_index()
    projection = build_projection(system)
    if projection["recovery"] != {
        "update": True,
        "split": False,
        "merge_a": False,
        "merge_b": False,
    }:
        fail(f"recovery falsifier drifted: {projection['recovery']}")
    if not projection["query"]["update_old_recovered"]:
        fail("query failed to expand the archived UPDATE predecessor")
    if not controller.split_source_index_prompt_observed:
        fail("split source never reached the native indexing path")
    system.save_graph(STATE_PATH)
    return {
        "phase": "prepare",
        "status": "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY",
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "deterministic_stub_calls": controller.stub_calls,
        "split_source_index_prompt_observed": True,
        "projection": projection,
    }


def verify() -> dict[str, Any]:
    if not STATE_PATH.is_file() or STATE_PATH.is_symlink():
        fail("verify requires a regular saved graph")
    controller = DeterministicController()
    system = AllMemSystem(controller, diagnosis_workers=1)
    system.load_graph(STATE_PATH)
    projection = build_projection(system)
    return {
        "phase": "verify",
        "status": "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY",
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "deterministic_stub_calls": controller.stub_calls,
        "projection": projection,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "verify"), required=True)
    args = parser.parse_args()
    present = sorted(name for name in FORBIDDEN_SECRETS if os.getenv(name))
    if present:
        fail(f"provider secrets are forbidden: {present}")
    result = prepare() if args.phase == "prepare" else verify()
    print(json.dumps(canonical(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
