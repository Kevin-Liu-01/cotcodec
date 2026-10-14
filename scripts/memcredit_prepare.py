#!/usr/bin/env python3
"""AM1 Step 0 (EXPLORATORY): build the demo's memory pools from LongMemEval-S (CPU).

Reads the pinned ``longmemeval_s_cleaned.json`` (experiments/am1/memcredit-step0-v1.yaml,
``source``), checks its size and SHA-256, selects the demo questions (seeded, stratified),
ranks each question's user turns with BM25 and builds the two pool arms. Writes:

* ``--artifact``: the study artifact the GPU job reads (questions, answers and pool texts). It
  holds LongMemEval text and stays on the host, outside the repository.
* ``--summary``: a text-free summary for the repository (question ids and types, pool
  coordinates, gold flags, BM25 ranks, text SHA-256, eligibility counts, the artifact digest).
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import memcredit as mc  # noqa: E402


def build_artifact(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    selection = dict(config["selection"])
    by_id = {r["question_id"]: r for r in records}
    if len(by_id) != len(records):
        raise mc.MemcreditError("duplicate question ids in the source")
    chosen = mc.select_questions(records, selection)
    questions = []
    for question_id in chosen:
        record = by_id[question_id]
        gold_total = sum(1 for t in mc.iter_turns(record) if t.has_answer)
        questions.append(
            {
                "question_id": question_id,
                "question_type": record["question_type"],
                "question": record["question"],
                "answer": record["answer"],
                "question_date": record["question_date"],
                "gold_turns_total": gold_total,
                "user_turns_total": sum(1 for t in mc.iter_turns(record) if t.role == "user"),
                "pools": mc.build_pools(record, config),
            }
        )
    reasons = collections.Counter(mc.eligibility(r, selection) or "eligible" for r in records)
    eligible_by_type = collections.Counter(
        r["question_type"] for r in records if mc.eligibility(r, selection) is None
    )
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "source": config["source"],
        "selection": selection,
        "retriever": config["retriever"],
        "pools_config": config["pools"],
        "eligibility": {
            "reasons": dict(sorted(reasons.items())),
            "eligible_by_type": dict(sorted(eligible_by_type.items())),
        },
        "questions": questions,
    }


def public_summary(artifact: dict[str, Any], artifact_sha256: str) -> dict[str, Any]:
    """The artifact without LongMemEval text: coordinates, flags, ranks and digests."""

    questions = []
    for q in artifact["questions"]:
        pools = {}
        for arm, pool in q["pools"].items():
            pools[arm] = [{k: v for k, v in m.items() if k != "text"} for m in pool]
        questions.append(
            {
                "question_id": q["question_id"],
                "question_type": q["question_type"],
                "question_sha256": mc.sha256_text(q["question"]),
                "answer_sha256": mc.sha256_text(str(q["answer"])),
                "gold_turns_total": q["gold_turns_total"],
                "user_turns_total": q["user_turns_total"],
                "gold_in_pool": {
                    arm: sum(m["is_gold"] for m in pool) for arm, pool in q["pools"].items()
                },
                "pools": pools,
            }
        )
    return {
        "experiment_id": artifact["experiment_id"],
        "claim_level": "exploratory",
        "artifact_sha256": artifact_sha256,
        "source": artifact["source"],
        "selection": artifact["selection"],
        "retriever": artifact["retriever"],
        "pools_config": artifact["pools_config"],
        "eligibility": artifact["eligibility"],
        "questions": questions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", required=True, help="longmemeval_s_cleaned.json")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    config = mc.load_config()
    source = Path(args.source)
    raw = source.read_bytes()
    pinned = config["source"]
    if len(raw) != pinned["size_bytes"] or mc.sha256_bytes(raw) != pinned["sha256"]:
        raise mc.MemcreditError("the source file differs from the pinned size or SHA-256")
    records = json.loads(raw)
    artifact = build_artifact(records, config)
    data = mc.canonical_json(artifact)
    for path in (Path(args.artifact), Path(args.summary)):
        if path.exists():
            raise mc.MemcreditError(f"refusing to overwrite {path}")
    Path(args.artifact).write_bytes(data)
    digest = mc.sha256_bytes(data)
    summary = public_summary(artifact, digest)
    Path(args.summary).write_bytes(mc.canonical_json(summary))
    print(
        json.dumps(
            {
                "artifact_sha256": digest,
                "artifact_bytes": len(data),
                "questions": [q["question_id"] for q in artifact["questions"]],
                "gold_in_pool": [s["gold_in_pool"] for s in summary["questions"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
