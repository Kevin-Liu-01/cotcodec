"""Frozen-input answer screen for the admitted GAAMA graph component.

This module deliberately owns only study compilation and deterministic analysis.
Model loading, Slurm, and container admission stay outside it.  The H100 runner
consumes one sealed CPU evidence bundle, so it cannot silently recompute or tune
retrieval after seeing model answers.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import random
import re
import string
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.memory_trials.gaama_natural import DialogueNode, load_locomo_graphs

ARM_IDS = (
    "flat",
    "true_graph",
    "shuffled_graph_seed_42",
    "shuffled_graph_seed_43",
    "shuffled_graph_seed_44",
)
SHUFFLED_ARM_IDS = ARM_IDS[2:]
PANEL_SEED = 20260815
PANEL_SIZE = 200
PRIMARY_K = 10
MAX_WORDS_PER_RECORD = 80
BOOTSTRAP_SEED = 20260815
BOOTSTRAP_DRAWS = 10_000
AA_QUESTIONS = 20
EXPECTED_CPU_STUDY = "gaama-natural-heldout-graph-retrieval-v1"
EXPECTED_CPU_STATUS = "GAAMA_NATURAL_GRAPH_PASS"
EXPECTED_DATASET_SHA256 = (
    "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
)
EXPECTED_GAAMA_REVISION = "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
QUESTION_ID_RE = re.compile(r"^(conv-[0-9]+):q([0-9]{4})$")
ARTICLE_RE = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)


@dataclass(frozen=True)
class FrozenGaamaInput:
    """Verified CPU result and its embedded immutable LoCoMo artifact."""

    evidence_sha256: str
    cpu_report_sha256: str
    dataset_sha256: str
    dataset_bytes: bytes
    report: dict[str, Any]
    dataset: list[dict[str, Any]]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_json(value: bytes, owner: str) -> Any:
    def reject(constant: str) -> None:
        raise ValueError(f"{owner} contains non-finite JSON constant {constant}")

    try:
        return json.loads(value, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{owner} is not strict JSON") from exc


def _embedded_file(bundle: dict[str, Any], name: str) -> bytes:
    files = bundle.get("files")
    row = files.get(name) if isinstance(files, dict) else None
    if not isinstance(row, dict) or not isinstance(row.get("sha256"), str):
        raise ValueError(f"GAAMA evidence bundle lacks {name}")
    encoded = row.get("content_gzip_base64")
    if encoded is not None:
        if row.get("encoding") != "gzip" or not isinstance(encoded, str):
            raise ValueError(f"GAAMA evidence file {name} has an invalid encoding")
        try:
            value = gzip.decompress(base64.b64decode(encoded, validate=True))
        except (ValueError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
            raise ValueError(f"GAAMA evidence file {name} cannot be decoded") from exc
    else:
        encoded = row.get("content_base64")
        if not isinstance(encoded, str) or "encoding" in row:
            raise ValueError(f"GAAMA evidence file {name} has an invalid encoding")
        try:
            value = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError(f"GAAMA evidence file {name} cannot be decoded") from exc
    if sha256_bytes(value) != row["sha256"] or row.get("bytes") != len(value):
        raise ValueError(f"GAAMA evidence file {name} digest or size drifted")
    return value


def load_frozen_input(path: Path, *, expected_sha256: str) -> FrozenGaamaInput:
    """Load and revalidate the single sealed CPU evidence bundle."""

    if path.is_symlink() or not path.is_file():
        raise ValueError("GAAMA evidence must be a regular non-symlink file")
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError("GAAMA evidence bundle SHA-256 drifted")
    bundle = _strict_json(raw, "GAAMA evidence bundle")
    if not isinstance(bundle, dict):
        raise ValueError("GAAMA evidence bundle must be an object")
    expected_identity = {
        "schema_version": 1,
        "source_id": "gaama",
        "status": EXPECTED_CPU_STATUS,
        "evidence_kind": "natural-heldout-component-reproduction",
        "run_count": 2,
        "scientific_result": False,
        "publication_ready": False,
    }
    if any(bundle.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("GAAMA evidence identity drifted")
    revisions = bundle.get("source_revisions")
    if revisions != {
        "https://github.com/swarna-kpaul/gaama": EXPECTED_GAAMA_REVISION
    }:
        raise ValueError("GAAMA evidence source revision drifted")
    dataset_identity = bundle.get("dataset")
    if dataset_identity != {
        "license": "CC-BY-NC-4.0",
        "name": "LoCoMo-10",
        "sha256": EXPECTED_DATASET_SHA256,
    }:
        raise ValueError("GAAMA evidence dataset identity drifted")

    cpu_report_bytes = _embedded_file(bundle, "run-1/report.json")
    repeat_report_bytes = _embedded_file(bundle, "run-2/report.json")
    if cpu_report_bytes != repeat_report_bytes:
        raise ValueError("GAAMA clean CPU repetitions differ")
    dataset_bytes = _embedded_file(bundle, "source/locomo10.json")
    if sha256_bytes(dataset_bytes) != EXPECTED_DATASET_SHA256:
        raise ValueError("GAAMA embedded dataset differs from its registered digest")
    report = _strict_json(cpu_report_bytes, "GAAMA CPU report")
    dataset = _strict_json(dataset_bytes, "LoCoMo-10")
    if not isinstance(report, dict) or not isinstance(dataset, list):
        raise ValueError("GAAMA embedded report or dataset has the wrong type")
    if (
        report.get("study") != EXPECTED_CPU_STUDY
        or report.get("status") != EXPECTED_CPU_STATUS
        or report.get("selected_ppr_weight") != 0.5
        or report.get("dataset_sha256") != EXPECTED_DATASET_SHA256
        or report.get("test_questions") != 1146
        or not all(report.get("graph_gates", {}).values())
        or not all(report.get("integrity_gates", {}).values())
    ):
        raise ValueError("GAAMA embedded CPU report is not the admitted result")
    return FrozenGaamaInput(
        evidence_sha256=expected_sha256,
        cpu_report_sha256=sha256_bytes(cpu_report_bytes),
        dataset_sha256=sha256_bytes(dataset_bytes),
        dataset_bytes=dataset_bytes,
        report=report,
        dataset=dataset,
    )


def _qa_by_question_id(dataset: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for sample in dataset:
        if not isinstance(sample, dict) or not isinstance(sample.get("sample_id"), str):
            raise ValueError("LoCoMo sample is malformed")
        sample_id = sample["sample_id"]
        qa_rows = sample.get("qa")
        if not isinstance(qa_rows, list):
            raise ValueError(f"{sample_id}: QA roster is malformed")
        for index, qa in enumerate(qa_rows):
            question_id = f"{sample_id}:q{index:04d}"
            if question_id in result or not isinstance(qa, dict):
                raise ValueError("LoCoMo QA identity is duplicated or malformed")
            result[question_id] = qa
    return result


def compile_panel(
    frozen: FrozenGaamaInput,
    *,
    panel_size: int = PANEL_SIZE,
    panel_seed: int = PANEL_SEED,
) -> dict[str, Any]:
    """Freeze a category-balanced panel and every retrieval arm before inference."""

    if panel_size <= 0 or panel_size % 4:
        raise ValueError("GAAMA actor panel size must be positive and divisible by four")
    rows = frozen.report.get("rows")
    if not isinstance(rows, dict) or set(rows) != {
        *ARM_IDS,
        "ppr_weight_zero",
    }:
        raise ValueError("GAAMA CPU report arm roster drifted")
    arm_maps: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in ARM_IDS:
        arm_rows = rows.get(arm)
        if not isinstance(arm_rows, list) or len(arm_rows) != 1146:
            raise ValueError(f"GAAMA arm {arm} has the wrong question count")
        mapped = {
            row["question_id"]: row
            for row in arm_rows
            if isinstance(row, dict) and isinstance(row.get("question_id"), str)
        }
        if len(mapped) != len(arm_rows):
            raise ValueError(f"GAAMA arm {arm} has duplicate or malformed rows")
        arm_maps[arm] = mapped
    roster = set(arm_maps["flat"])
    if any(set(mapped) != roster for mapped in arm_maps.values()):
        raise ValueError("GAAMA retrieval arms use different question rosters")
    if rows["flat"] != rows["ppr_weight_zero"]:
        raise ValueError("GAAMA ppr-weight-zero A/A control drifted")

    qa_by_id = _qa_by_question_id(frozen.dataset)
    by_category: dict[int, list[str]] = defaultdict(list)
    for question_id, row in arm_maps["flat"].items():
        match = QUESTION_ID_RE.fullmatch(question_id)
        qa = qa_by_id.get(question_id)
        if match is None or qa is None:
            raise ValueError("GAAMA report question is absent from LoCoMo")
        if (
            qa.get("category") != row.get("category")
            or not isinstance(qa.get("question"), str)
            or not isinstance(qa.get("answer"), str)
        ):
            raise ValueError("GAAMA report and LoCoMo QA metadata disagree")
        by_category[int(row["category"])].append(question_id)
    quota = panel_size // 4
    if set(by_category) != {1, 2, 3, 4} or any(
        len(question_ids) < quota for question_ids in by_category.values()
    ):
        raise ValueError("GAAMA report cannot satisfy the balanced panel")

    selected: list[str] = []
    for category in (1, 2, 3, 4):
        ordered = sorted(
            by_category[category],
            key=lambda question_id: (
                hashlib.sha256(f"{panel_seed}:{question_id}".encode()).hexdigest(),
                question_id,
            ),
        )
        selected.extend(ordered[:quota])
    selected.sort()
    items: list[dict[str, Any]] = []
    for question_id in selected:
        qa = qa_by_id[question_id]
        flat = arm_maps["flat"][question_id]
        rankings: dict[str, list[str]] = {}
        for arm in ARM_IDS:
            ranking = arm_maps[arm][question_id].get("top_20")
            if (
                not isinstance(ranking, list)
                or len(ranking) != 20
                or len(set(ranking)) != 20
                or not all(isinstance(node_id, str) for node_id in ranking)
            ):
                raise ValueError(f"GAAMA {arm} ranking is malformed")
            rankings[arm] = ranking[:PRIMARY_K]
        items.append(
            {
                "question_id": question_id,
                "sample_id": flat["sample_id"],
                "category": flat["category"],
                "question": qa["question"],
                "answer": qa["answer"],
                "evidence_ids": flat["evidence_ids"],
                "rankings": rankings,
            }
        )
    panel = {
        "schema_version": 1,
        "study": "gaama-natural-h100-actor-screen-v1",
        "panel_seed": panel_seed,
        "panel_size": panel_size,
        "category_counts": {
            str(category): sum(item["category"] == category for item in items)
            for category in (1, 2, 3, 4)
        },
        "sample_ids": sorted({item["sample_id"] for item in items}),
        "arms": list(ARM_IDS),
        "retrieval_k": PRIMARY_K,
        "max_words_per_record": MAX_WORDS_PER_RECORD,
        "evidence_bundle_sha256": frozen.evidence_sha256,
        "cpu_report_sha256": frozen.cpu_report_sha256,
        "dataset_sha256": frozen.dataset_sha256,
        "items": items,
    }
    panel["panel_sha256"] = sha256_bytes(canonical_bytes(panel))
    return panel


def build_node_map(frozen: FrozenGaamaInput, dataset_path: Path) -> dict[str, DialogueNode]:
    """Use the already-audited loader and prove its input is the embedded dataset."""

    if sha256_bytes(dataset_path.read_bytes()) != frozen.dataset_sha256:
        raise ValueError("materialized GAAMA dataset digest drifted")
    nodes = {
        node.node_id: node
        for graph in load_locomo_graphs(dataset_path)
        for node in graph.nodes
    }
    if len(nodes) != 5882:
        raise ValueError("GAAMA dialogue-node roster drifted")
    return nodes


def render_prompt(
    item: dict[str, Any],
    *,
    arm: str,
    nodes: dict[str, DialogueNode],
) -> str:
    """Render only the selected top-k records; no answer/evidence labels enter."""

    if arm not in ARM_IDS:
        raise ValueError("unknown GAAMA actor arm")
    ranking = item["rankings"][arm]
    lines: list[str] = []
    for index, node_id in enumerate(ranking, 1):
        node = nodes.get(node_id)
        if node is None or node.sample_id != item["sample_id"]:
            raise ValueError("GAAMA ranking refers to an invalid dialogue node")
        words = node.text.split()
        text = " ".join(words[:MAX_WORDS_PER_RECORD])
        lines.append(
            f"[{index}] Date: {node.session_date} | Speaker: {node.speaker} | {text}"
        )
    memory = "\n".join(lines)
    return (
        "Answer the question using only the memory records below. "
        "If the records do not contain the answer, answer UNKNOWN. "
        "Return only the shortest answer; do not explain.\n\n"
        f"Memory records:\n{memory}\n\nQuestion: {item['question']}\nAnswer:"
    )


def normalize_answer(value: str) -> str:
    lowered = value.lower()
    without_punctuation = "".join(
        character for character in lowered if character not in string.punctuation
    )
    without_articles = ARTICLE_RE.sub(" ", without_punctuation)
    return " ".join(without_articles.split())


def answer_scores(prediction: str, answer: str) -> tuple[float, float]:
    predicted = normalize_answer(prediction)
    expected = normalize_answer(answer)
    exact = float(predicted == expected)
    predicted_tokens = predicted.split()
    expected_tokens = expected.split()
    if not predicted_tokens or not expected_tokens:
        return exact, float(predicted_tokens == expected_tokens)
    overlap = sum((Counter(predicted_tokens) & Counter(expected_tokens)).values())
    if overlap == 0:
        return exact, 0.0
    precision = overlap / len(predicted_tokens)
    recall = overlap / len(expected_tokens)
    return exact, 2 * precision * recall / (precision + recall)


def expected_case_keys(panel: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (item["question_id"], arm)
        for item in panel["items"]
        for arm in ARM_IDS
    )


def _cluster_differences(
    rows: list[dict[str, Any]], left: str, controls: tuple[str, ...]
) -> dict[str, list[float]]:
    by_key = {(row["question_id"], row["arm"]): row for row in rows}
    grouped: dict[str, list[float]] = defaultdict(list)
    items = {
        (row["question_id"], row["sample_id"])
        for row in rows
        if row["arm"] == left
    }
    for question_id, sample_id in sorted(items):
        left_score = float(by_key[(question_id, left)]["token_f1"])
        control_score = sum(
            float(by_key[(question_id, arm)]["token_f1"]) for arm in controls
        ) / len(controls)
        grouped[sample_id].append(left_score - control_score)
    return dict(grouped)


def _cluster_mean(grouped: dict[str, list[float]]) -> float:
    means = [sum(values) / len(values) for _, values in sorted(grouped.items())]
    return sum(means) / len(means)


def _clustered_interval(grouped: dict[str, list[float]]) -> list[float]:
    groups = sorted(grouped)
    means = {group: sum(grouped[group]) / len(grouped[group]) for group in groups}
    generator = random.Random(BOOTSTRAP_SEED)
    values = [
        sum(means[generator.choice(groups)] for _ in groups) / len(groups)
        for _ in range(BOOTSTRAP_DRAWS)
    ]
    values.sort()
    return [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]


def analyze_rows(rows: list[dict[str, Any]], *, panel: dict[str, Any]) -> dict[str, Any]:
    """Compute the preregistered kill-screen report from a complete plan prefix."""

    expected = expected_case_keys(panel)
    actual = tuple((row.get("question_id"), row.get("arm")) for row in rows)
    if actual != expected:
        raise ValueError("GAAMA actor rows are not the exact complete plan")
    summaries: dict[str, dict[str, float | int]] = {}
    for arm in ARM_IDS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        summaries[arm] = {
            "questions": len(arm_rows),
            "exact_match": sum(float(row["exact_match"]) for row in arm_rows)
            / len(arm_rows),
            "token_f1": sum(float(row["token_f1"]) for row in arm_rows)
            / len(arm_rows),
            "evidence_recall_all_at_10": sum(
                float(row["evidence_recall_all_at_10"]) for row in arm_rows
            )
            / len(arm_rows),
            "mean_prompt_tokens": sum(int(row["receipt"]["prompt_tokens"]) for row in arm_rows)
            / len(arm_rows),
            "mean_completion_tokens": sum(
                int(row["receipt"]["completion_tokens"]) for row in arm_rows
            )
            / len(arm_rows),
        }
    flat_paired = _cluster_differences(rows, "true_graph", ("flat",))
    shuffled_paired = _cluster_differences(rows, "true_graph", SHUFFLED_ARM_IDS)
    true_minus_each_shuffled = {
        arm: _cluster_mean(_cluster_differences(rows, "true_graph", (arm,)))
        for arm in SHUFFLED_ARM_IDS
    }
    prompt_means = [float(summary["mean_prompt_tokens"]) for summary in summaries.values()]
    aa_rows = [row for row in rows if row.get("aa_checked")]
    gates = {
        "row_roster_exact": len(rows) == panel["panel_size"] * len(ARM_IDS),
        "actor_a_a_exact": len(aa_rows) == AA_QUESTIONS
        and all(row.get("aa_text_exact") is True for row in aa_rows),
        "completion_nonempty": all(bool(str(row.get("prediction", "")).strip()) for row in rows),
        "flat_actor_f1_at_least_0_20": summaries["flat"]["token_f1"] >= 0.20,
        "true_f1_exceeds_flat": _cluster_mean(flat_paired) > 0.0,
        "true_f1_exceeds_mean_shuffled": _cluster_mean(shuffled_paired) > 0.0,
        "true_f1_exceeds_at_least_two_shuffles": sum(
            value > 0 for value in true_minus_each_shuffled.values()
        )
        >= 2,
        "mean_prompt_token_ratio_within_1_10": max(prompt_means) / min(prompt_means)
        <= 1.10,
    }
    passed = all(gates.values())
    return {
        "schema_version": 1,
        "study": panel["study"],
        "status": "GAAMA_H100_ACTOR_PASS" if passed else "GAAMA_H100_ACTOR_KILLED",
        "scientific_result": False,
        "publication_ready": False,
        "discovery_only": True,
        "panel_sha256": panel["panel_sha256"],
        "panel_size": panel["panel_size"],
        "arm_summaries": summaries,
        "primary_comparison": {
            "true_minus_flat_cluster_mean_f1": _cluster_mean(flat_paired),
            "true_minus_flat_clustered_bootstrap_95_ci": _clustered_interval(flat_paired),
            "true_minus_mean_shuffled_cluster_mean_f1": _cluster_mean(shuffled_paired),
            "true_minus_mean_shuffled_clustered_bootstrap_95_ci": _clustered_interval(
                shuffled_paired
            ),
            "true_minus_each_shuffled_cluster_mean_f1": true_minus_each_shuffled,
        },
        "gates": gates,
        "claim_boundary": (
            "Bounded deterministic answer-quality kill screen over frozen LoCoMo retrieval "
            "arms; not official LoCoMo evaluation or publication evidence."
        ),
    }
