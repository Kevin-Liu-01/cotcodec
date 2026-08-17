"""Deterministic compilation and analysis for the Mnemon static-space actor cell."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from harness.memory_trials.gaama_actor import answer_scores

ARM_IDS = ("no_memory", "all_spaces", "lexical_router", "oracle_space")
TASK_COUNT = 32
TOP_K = 4
SLOT_CHARACTERS = 160
AA_TASKS = 8


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_panel(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Mnemon actor panel must be a regular non-symlink file")
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError("Mnemon actor panel SHA-256 drifted")

    def reject(value: str) -> None:
        raise ValueError(f"Mnemon actor panel contains non-finite value {value}")

    value = json.loads(raw, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError("Mnemon actor panel must be one JSON object")
    expected_identity = {
        "schema_version": 1,
        "study": "mnemon-static-space-h100-actor-v1",
        "source_id": "mnemon",
        "source_revisions": {
            "https://github.com/mnemon-dev/mnemon": (
                "88d2981edeb18a5ebe048af472f6f96527615454"
            ),
            "https://github.com/omdsh-dev/dsh-mnemon": (
                "1889c68400e52a391ee9a6eedf15bf44bc39dd06"
            ),
        },
        "active_selection_owner": "dsh-mnemon-plugin",
        "retrieval_owner": "mnemon-core",
        "task_count": TASK_COUNT,
        "group_count": TASK_COUNT,
        "arms": list(ARM_IDS),
        "retrieval_top_k": TOP_K,
        "fixed_slot_characters": SLOT_CHARACTERS,
        "retrieval_calls_per_nonempty_arm": 1,
        "router_inputs": ["question"],
        "answer_labels_available_to_router": False,
        "padding_is_memory_evidence": False,
        "scientific_result": False,
        "publication_ready": False,
    }
    if any(value.get(key) != expected for key, expected in expected_identity.items()):
        raise ValueError("Mnemon actor panel identity drifted")
    items = value.get("items")
    if not isinstance(items, list) or len(items) != TASK_COUNT:
        raise ValueError("Mnemon actor task roster drifted")
    for index, item in enumerate(items):
        expected_id = f"mnemon-static-{index:03d}"
        arms = item.get("arms") if isinstance(item, dict) else None
        if (
            not isinstance(item, dict)
            or item.get("task_id") != expected_id
            or item.get("group_id") != f"entity-{index:02d}"
            or not isinstance(item.get("question"), str)
            or not isinstance(item.get("answer"), str)
            or item.get("routed_space") != item.get("target_space")
            or not isinstance(arms, dict)
            or set(arms) != set(ARM_IDS)
            or arms["no_memory"] != []
            or len(arms["all_spaces"]) != TOP_K
            or len(arms["lexical_router"]) != TOP_K
            or arms["lexical_router"] != arms["oracle_space"]
        ):
            raise ValueError(f"Mnemon actor task drifted: {expected_id}")
        for arm in ARM_IDS[1:]:
            for slot in arms[arm]:
                if (
                    not isinstance(slot, dict)
                    or not isinstance(slot.get("text"), str)
                    or not isinstance(slot.get("is_padding"), bool)
                    or (
                        not slot["is_padding"]
                        and not isinstance(slot.get("source_space"), str)
                    )
                ):
                    raise ValueError(f"Mnemon actor slot drifted: {expected_id}/{arm}")
        if any(
            slot["source_space"] != item["target_space"]
            for slot in arms["lexical_router"]
            if not slot["is_padding"]
        ):
            raise ValueError("Mnemon routed context contains inactive-space evidence")
    return value


def expected_case_keys(panel: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (item["task_id"], arm) for item in panel["items"] for arm in ARM_IDS
    )


def render_prompt(item: dict[str, Any], *, arm: str) -> str:
    if arm not in ARM_IDS:
        raise ValueError(f"unknown Mnemon actor arm: {arm}")
    slots = item["arms"][arm]
    if arm == "no_memory":
        memory = "No memory records are available."
    else:
        rendered = []
        for index, slot in enumerate(slots, 1):
            text = " ".join(slot["text"].split())
            fixed = text[:SLOT_CHARACTERS].ljust(SLOT_CHARACTERS, " ")
            rendered.append(f"[{index}] {fixed}")
        memory = "\n".join(rendered)
    return (
        "Answer the question using only the memory records below. If the records "
        "conflict, use the record from the workspace named in the question. Return "
        "only the access-code, with no explanation.\n\n"
        f"Memory records:\n{memory}\n\nQuestion: {item['question']}\nAccess-code:"
    )


def analyze_rows(rows: list[dict[str, Any]], *, panel: dict[str, Any]) -> dict[str, Any]:
    expected = expected_case_keys(panel)
    actual = tuple((row.get("task_id"), row.get("arm")) for row in rows)
    if actual != expected:
        raise ValueError("Mnemon actor rows do not cover the frozen case plan")
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)
    arm_metrics: dict[str, dict[str, float | int]] = {}
    for arm in ARM_IDS:
        arm_rows = by_arm[arm]
        arm_metrics[arm] = {
            "count": len(arm_rows),
            "exact_match": sum(float(row["exact_match"]) for row in arm_rows)
            / len(arm_rows),
            "token_f1": sum(float(row["token_f1"]) for row in arm_rows)
            / len(arm_rows),
            "mean_prompt_tokens": sum(
                int(row["receipt"]["prompt_tokens"]) for row in arm_rows
            )
            / len(arm_rows),
        }
    aa_rows = [row for row in rows if row.get("aa_checked")]
    lexical = arm_metrics["lexical_router"]
    oracle = arm_metrics["oracle_space"]
    all_spaces = arm_metrics["all_spaces"]
    no_memory = arm_metrics["no_memory"]
    token_ratio = float(lexical["mean_prompt_tokens"]) / max(
        1.0, float(all_spaces["mean_prompt_tokens"])
    )
    gates = {
        "actor_aa_exact": len(aa_rows) == AA_TASKS
        and all(row.get("aa_text_exact") is True for row in aa_rows),
        "completion_nonempty": all(bool(str(row.get("prediction", "")).strip()) for row in rows),
        "lexical_equals_oracle": lexical["exact_match"] == oracle["exact_match"]
        and lexical["token_f1"] == oracle["token_f1"],
        "lexical_exact_minimum": float(lexical["exact_match"]) >= 0.80,
        "lexical_beats_all_spaces": float(lexical["token_f1"])
        >= float(all_spaces["token_f1"]) + 0.03,
        "lexical_beats_no_memory": float(lexical["token_f1"])
        >= float(no_memory["token_f1"]) + 0.20,
        "matched_nonempty_prompt_budget": 0.85 <= token_ratio <= 1.15,
    }
    return {
        "schema_version": 1,
        "study": "mnemon-static-space-h100-actor-v1",
        "status": (
            "MNEMON_STATIC_ROUTING_PASS"
            if all(gates.values())
            else "MNEMON_STATIC_ROUTING_KILLED"
        ),
        "scientific_result": False,
        "publication_ready": False,
        "arm_metrics": arm_metrics,
        "lexical_minus_all_token_f1": float(lexical["token_f1"])
        - float(all_spaces["token_f1"]),
        "lexical_to_all_prompt_token_ratio": token_ratio,
        "gates": gates,
    }


__all__ = [
    "AA_TASKS",
    "ARM_IDS",
    "analyze_rows",
    "answer_scores",
    "canonical_bytes",
    "expected_case_keys",
    "load_panel",
    "render_prompt",
    "sha256_bytes",
]
