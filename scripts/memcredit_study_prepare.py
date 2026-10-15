#!/usr/bin/env python3
"""AM1 study (CPU): the development / held-out split and the study artifact.

Subcommands, each reading the pinned ``longmemeval_s_cleaned.json`` (size and SHA-256 checked):

* ``split --source F --output O [--census C]``: the seeded, type-stratified split of the usable
  questions (``experiments/am1/memcredit-study-v1.yaml``, ``usable`` and ``split``). Writes
  question ids, counts and digests only. With ``--census``, checks that the usable ids equal
  Step 0's census ``full_study_eligible`` ids.
* ``artifact --source F --split-file S --split development --artifact A --summary P``: the two
  pool arms and AM2's placebo arms for every question of one split. The artifact holds
  LongMemEval text and stays on the host; the summary has no text (ids, coordinates, gold flags,
  BM25 ranks, length ratios, SHA-256). The held-out split is refused unless the registration
  ``am1-memory-credit-v1`` is frozen in the ledger with this checkout's file.
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
from harness import memcredit_study as ms  # noqa: E402

LEDGER = PROJECT_ROOT / "program" / "preregistrations" / "ledger.jsonl"
REGISTRATION = PROJECT_ROOT / "program" / "preregistrations" / f"{ms.REGISTRATION_ID}.md"


def read_source(path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    pinned = config["source"]
    if len(raw) != pinned["size_bytes"] or mc.sha256_bytes(raw) != pinned["sha256"]:
        raise ms.StudyError("the source file differs from the pinned size or SHA-256")
    return json.loads(raw)


def build_artifact(
    records: list[dict[str, Any]], config: dict[str, Any], split: dict[str, Any], name: str
) -> dict[str, Any]:
    by_id = {r["question_id"]: r for r in records}
    questions = []
    for question_id in split[name]:
        record = by_id[question_id]
        if ms.usable_reason(record, config["usable"]) is not None:
            raise ms.StudyError(f"{question_id} is in the split but not usable")
        pools = mc.build_pools(record, ms.pool_config(config))
        turns = mc.iter_turns(record)
        questions.append(
            {
                "question_id": question_id,
                "question_type": record["question_type"],
                "question": record["question"],
                "answer": record["answer"],
                "question_date": record["question_date"],
                "gold_turns_total": sum(1 for t in turns if t.has_answer),
                "user_turns_total": sum(1 for t in turns if t.role == "user"),
                "pools": pools,
                "placebos": ms.build_placebos(record, pools, config),
            }
        )
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "split": name,
        "split_ids_sha256": split[f"{name}_sha256"],
        "source": config["source"],
        "retriever": config["retriever"],
        "pools_config": config["pools"],
        "placebo_config": config["placebo"],
        "questions": questions,
    }


def public_summary(artifact: dict[str, Any], artifact_sha256: str) -> dict[str, Any]:
    """The artifact without LongMemEval text."""

    questions = []
    for q in artifact["questions"]:
        pools = {
            arm: [{k: v for k, v in m.items() if k != "text"} for m in pool]
            for arm, pool in q["pools"].items()
        }
        placebos = {
            arm: {
                "swaps": [[{k: v for k, v in s.items() if k != "text"} for s in slot]
                          for slot in p["swaps"]],
                "reorders": p["reorders"],
            }
            for arm, p in q["placebos"].items()
        }  # fmt: skip
        questions.append(
            {
                "question_id": q["question_id"],
                "question_type": q["question_type"],
                "question_sha256": mc.sha256_text(q["question"]),
                "answer_sha256": mc.sha256_text(str(q["answer"])),
                "gold_turns_total": q["gold_turns_total"],
                "user_turns_total": q["user_turns_total"],
                "gold_in_pool": {a: sum(m["is_gold"] for m in p) for a, p in q["pools"].items()},
                "pools": pools,
                "placebos": placebos,
            }
        )
    tolerances = collections.Counter(
        str(s["tolerance"])
        for q in artifact["questions"]
        for p in q["placebos"].values()
        for slot in p["swaps"]
        for s in slot
    )
    return {
        "experiment_id": artifact["experiment_id"],
        "claim_level": "exploratory",
        "artifact_sha256": artifact_sha256,
        "split": artifact["split"],
        "split_ids_sha256": artifact["split_ids_sha256"],
        "source": artifact["source"],
        "retriever": artifact["retriever"],
        "pools_config": artifact["pools_config"],
        "placebo_config": artifact["placebo_config"],
        "swap_tolerance_counts": dict(sorted(tolerances.items())),
        "questions": questions,
    }


def refuse_existing(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            raise ms.StudyError(f"refusing to overwrite {path}")


def split_main(args: argparse.Namespace) -> int:
    config = ms.load_config()
    records = read_source(Path(args.source), config)
    split = ms.make_split(records, config)
    if args.census:
        census = json.loads(Path(args.census).read_text(encoding="utf-8"))
        eligible = sorted(q["question_id"] for q in census["questions"] if q["full_study_eligible"])
        if eligible != sorted(split["development"] + split["heldout"]):
            raise ms.StudyError("the usable ids differ from Step 0's census")
        split["census_check"] = {"census_sha256": ms.sha256_file(Path(args.census)),
                                 "usable_equals_census_eligible": True}  # fmt: skip
    out = Path(args.output)
    refuse_existing(out)
    out.write_bytes(mc.canonical_json(split))
    print(json.dumps({k: split[k] for k in ("counts", "per_type", "development_sha256",
                                            "heldout_sha256")}, indent=2))  # fmt: skip
    return 0


def artifact_main(args: argparse.Namespace) -> int:
    config = ms.load_config()
    split = ms.load_split(Path(args.split_file), config)
    if args.split == "heldout" and not ms.registration_frozen(LEDGER, REGISTRATION):
        raise ms.StudyError(
            f"the held-out split opens only under a frozen {ms.REGISTRATION_ID} registration"
        )
    records = read_source(Path(args.source), config)
    artifact = build_artifact(records, config, split, args.split)
    data = mc.canonical_json(artifact)
    refuse_existing(Path(args.artifact), Path(args.summary))
    Path(args.artifact).write_bytes(data)
    digest = mc.sha256_bytes(data)
    Path(args.summary).write_bytes(mc.canonical_json(public_summary(artifact, digest)))
    print(json.dumps({"artifact_sha256": digest, "artifact_bytes": len(data),
                      "questions": len(artifact["questions"])}, indent=2))  # fmt: skip
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split", allow_abbrev=False)
    split.add_argument("--source", required=True)
    split.add_argument("--output", required=True)
    split.add_argument("--census", default=None)
    artifact = sub.add_parser("artifact", allow_abbrev=False)
    artifact.add_argument("--source", required=True)
    artifact.add_argument("--split-file", required=True)
    artifact.add_argument("--split", required=True, choices=ms.SPLITS)
    artifact.add_argument("--artifact", required=True)
    artifact.add_argument("--summary", required=True)
    args = parser.parse_args()
    if args.command == "split":
        return split_main(args)
    return artifact_main(args)


if __name__ == "__main__":
    sys.exit(main())
