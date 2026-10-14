#!/usr/bin/env python3
"""AM1 Step 0 (EXPLORATORY): a CPU census of LongMemEval-S for the full study's pool design.

For every question of the pinned ``longmemeval_s_cleaned.json``: its type, whether it is an
abstention question, its gold turns by role, the BM25 rank (among the question's user turns, as
in the demo's retriever) of each gold user turn, and whether a full study with user-turn memories
and k = 8 could take it (no abstention, every gold turn a user turn, at most 6 gold turns). The
summary gives, per type, the required-memory count distribution and the retriever's top-8 recall
of the gold turns, which bounds how often the retrieved arm holds every, some or none of them.
Writes question ids, counts and ranks only, no LongMemEval text.
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


def question_row(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    k = int(config["pools"]["size"])
    turns = mc.iter_turns(record)
    gold = [t for t in turns if t.has_answer]
    roles = collections.Counter(t.role for t in gold)
    ranked = mc.rank_user_turns(record, config["retriever"])
    gold_ranks = [r for r, (t, _) in enumerate(ranked) if t.has_answer]
    full_study = dict(config["selection"], types={record["question_type"]: 1})
    reason = mc.eligibility(record, full_study)
    return {
        "question_id": record["question_id"],
        "question_type": record["question_type"],
        "abstention": mc.is_abstention(record),
        "gold_turns": len(gold),
        "gold_user_turns": roles.get("user", 0),
        "gold_assistant_turns": roles.get("assistant", 0),
        "user_turns": len(ranked),
        "gold_user_ranks": gold_ranks,
        "gold_user_in_top_k": sum(1 for r in gold_ranks if r < k),
        "full_study_eligible": reason is None,
        "ineligible_reason": reason,
    }


def summarize(rows: list[dict[str, Any]], k: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        groups[row["question_type"]].append(row)
        groups["all"].append(row)
    for name, items in sorted(groups.items()):
        eligible = [r for r in items if r["full_study_eligible"]]
        gold_total = sum(r["gold_user_turns"] for r in eligible)
        found = sum(r["gold_user_in_top_k"] for r in eligible)
        out[name] = {
            "questions": len(items),
            "abstention": sum(r["abstention"] for r in items),
            "full_study_eligible": len(eligible),
            "required_count_distribution": dict(
                sorted(collections.Counter(r["gold_user_turns"] for r in eligible).items())
            ),
            f"gold_recall_at_{k}": found / gold_total if gold_total else None,
            f"all_gold_in_top_{k}": sum(
                r["gold_user_in_top_k"] == r["gold_user_turns"] for r in eligible
            ),  # fmt: skip
            f"some_gold_in_top_{k}": sum(
                0 < r["gold_user_in_top_k"] < r["gold_user_turns"] for r in eligible
            ),  # fmt: skip
            f"no_gold_in_top_{k}": sum(r["gold_user_in_top_k"] == 0 for r in eligible),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", required=True, help="longmemeval_s_cleaned.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = mc.load_config()
    raw = Path(args.source).read_bytes()
    pinned = config["source"]
    if len(raw) != pinned["size_bytes"] or mc.sha256_bytes(raw) != pinned["sha256"]:
        raise mc.MemcreditError("the source file differs from the pinned size or SHA-256")
    records = json.loads(raw)
    rows = [question_row(r, config) for r in records]
    k = int(config["pools"]["size"])
    result = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "source": pinned,
        "retriever": config["retriever"],
        "pool_size": k,
        "full_study_rule": "no abstention; every gold turn a user turn; at most "
        f"{config['selection']['max_gold_turns']} gold turns",
        "summary": summarize(rows, k),
        "questions": rows,
    }
    out = Path(args.output)
    if out.exists():
        raise mc.MemcreditError(f"refusing to overwrite {out}")
    out.write_bytes(mc.canonical_json(result))
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
