#!/usr/bin/env python3
"""AM5 (D120; EXPLORATORY, development split only): what does the non-abstention keep rule cost
when the evidence is absent?

The rule (AM1d's ``nonabstain@70``; H-C of ``am1-keepset-search-v1``; confirmed for three readers
by ``am3-nonabstain-generality-v1``) reads a pool's 70 4-subsets in BM25 order and keeps the first
whose reply does not abstain, up to K reads; otherwise it keeps BM25 top 4. Its cost on
unanswerable questions was measured only on LongMemEval-S's 30 edited abstention questions, with a
judge that failed its check (G-J2). AM5 builds unanswerable pools from the 63 development
questions instead:

* For each question, every haystack session in LongMemEval's ``answer_session_ids`` is removed,
  and the BM25 top-8 user-turn pool is built from the rest exactly as AM1's retrieved arm
  (``memcredit_am3g.retrieved_pool``: ``harness.memcredit`` ``rank_user_turns``,
  ``memory_entry``, ``chronological``). "I don't know" is then the correct reply by construction,
  unless the answer also appears outside the evidence sessions (the leakage check).
* Per pool each reader answers the 70 4-subsets and all 8 (71 requests), with am3g's readers,
  engines and steps unchanged and AM1's prompt; the Qwen3-32B judge scores every distinct
  (question, reply) with LongMemEval's non-abstention answer-check prompt against the reference
  answer.
* Per reader and cap K (8 and 70): (a) the switch rate, the share of pools where BM25 top 4
  abstains and a non-abstaining 4-subset is found within K reads (abstention flags only, no
  judge); (b) the pools where BM25 top 4 does not abstain; (c) the pools whose all-8 reply
  abstains, and those where every 4-subset abstains; (d) how many switched replies and
  non-abstaining top-4 replies the judge calls correct, and a blind agent hand check of all of
  them; (e) the leakage counts. Beside them, the same quantities and the rule's gain on the same
  questions' original pools, from AM3's committed per-pool records.

Subcommands:

* ``prepare --source F --split-file S --dev-artifact D --artifact A --summary P`` (host CPU): the
  ablated artifact (pool texts; host only) and its text-free summary with the leakage facts.
* ``plan --evidence A``; ``selftest --evidence A`` (CPU, no engine).
* ``run --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the GPU job, one H100. ``worker``: one step.
* ``extract --run-dir R --evidence A --summary P --private-dir P`` (host; reads replies): text-free
  features to a host-only directory.
* ``hand-sample --run-dir R --evidence A --features F --hand-dir H`` (host; writes texts to H);
  ``hand-audit`` (on the Mac: the labeller's transcript, text-free); ``hand-merge --hand-dir H``
  (host).
* ``analyze --features F --hand-labels L --hand-labels-sha256 S --hand-plan-sha256 P
  --output-dir O`` (CPU): text-free ``results.json``, ``per-table.json.gz`` and ``tables.md``.

The GPU job's driver and worker are am3g's (``memcredit_am3g.run_main``, ``vllm_worker``,
``run_step``) with the population swapped for this one; am3g's registered file is not changed.
Nothing here opens a held-out or abstention input (``memcredit_am3g.check_dev_path``).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import signal
import subprocess
import sys
import threading
import time
import zipfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_am3 as am3  # noqa: E402  (engine helpers, rule, per-pool record)
import memcredit_am3g as g  # noqa: E402  (readers, steps, pools, prompts, judge, worker pieces)
import memcredit_keepset_search as ks  # noqa: E402  (reads summary)
import memcredit_label_free as lf  # noqa: E402  (abstention patterns)
import memcredit_step0 as s0  # noqa: E402  (engine streaming, pass files, GPU sampler)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am5-evidence-ablated-dev"
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am5" / "am5-evidence-ablated-dev.yaml"
POPULATION = "dev-ablated"
ARMS = ("retrieved",)
K = g.K
FULL = g.FULL
FOUR_SETS = g.FOUR_SETS
REQUEST_MASKS = g.REQUEST_MASKS
FULL_ORDER = len(FOUR_SETS)
JUDGE = "primary"
JUDGE_STEP = "judge32"
READERS = g.H2_READERS
SMOKE_REQUESTS = g.SMOKE_REQUESTS
SMOKE_FAILED_EXIT = g.SMOKE_FAILED_EXIT
#: The code whose SHA-256 the features record: am3g's closure plus this script.
FEATURE_CODE = (*g.FEATURE_CODE, "scripts/memcredit_am5.py")
CLAIM = (
    "EXPLORATORY, development split only (the pilot's 63 questions, with their evidence sessions "
    "removed). Nothing here licenses a claim; a held-out registration follows only if the "
    "development run is clean (D120)."
)
#: The blind labeller's instructions (only the check "answer": every item is a reply that does not
#: abstain, compared with the question's reference answer; am3g's criteria for that check).
HAND_INSTRUCTIONS = """Blind hand check, AM5 (exploratory; D9: agent labels).

Each line of the sample is one item: a LongMemEval-S question, its question type, the check
"answer", the question's reference answer and a reply written by a language model that was given
some of the user's past messages. Label every item, independently of the others.

- 1 if the reply is correct: it contains the reference answer, or is equivalent to it, or
  contains all the intermediate steps to reach it. A reply that gives only part of the
  information the answer needs is 0.
- temporal-reasoning: do not penalise an off-by-one error in a number of days, weeks or months.
- knowledge-update: a reply that mentions earlier information along with the updated answer is
  correct as long as the updated answer is the one required.
- single-session-preference (the reference is a rubric): 1 if the reply satisfies the rubric,
  recalling and using the user's personal information correctly; it need not cover every point.
- A reply that declines to answer ("I don't know", "the memories do not say") is 0.

Use only the question, the reference answer and the reply. Do not look for, open or infer any
other file, label or result. Write one JSON object per line, in the sample's order:
{"item_id": "...", "label": 1 or 0, "note": "optional, short"}.
"""


class Am5Error(ValueError):
    """The config, an input or a check failed."""


sha256_bytes = g.sha256_bytes
sha256_text = g.sha256_text
sha256_file = g.sha256_file


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and not set(value) - set("0123456789abcdef")


def code_digests(root: Path = PROJECT_ROOT) -> dict[str, str]:
    return {path: sha256_file(root / path) for path in FEATURE_CODE}


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """AM5's config merged onto the frozen am3g config (validated by ``memcredit_am3g``): the
    readers, models, reader sampling, pilot pins and the listed steps come from it unchanged."""

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("experiment_id") != EXPERIMENT:
        raise Am5Error(f"not the {EXPERIMENT} config")
    if raw.get("claim_level") != "exploratory":
        raise Am5Error("AM5 is exploratory")
    if raw.get("seeds") != [42, 43, 44]:
        raise Am5Error("seeds must be [42, 43, 44]")
    base_path = PROJECT_ROOT / raw["base"]["config"]
    if sha256_file(base_path) != raw["base"]["config_sha256"]:
        raise Am5Error("the am3g config differs from its pinned SHA-256")
    base = g.load_config(base_path)
    by_id = {s["id"]: s for s in base["steps"]}
    ids = list(raw["steps"])
    if len(set(ids)) != len(ids) or any(i not in by_id for i in ids):
        raise Am5Error("steps: distinct am3g step ids")
    steps = [by_id[i] for i in ids]
    if [s["id"] for s in steps if s["kind"] == "judge"] != [JUDGE_STEP]:
        raise Am5Error("the one judge step is judge32 (Qwen3-32B)")
    if {s.get("reader") for s in steps if s["kind"] == "reader"} != set(READERS):
        raise Am5Error("every reader has a step")
    for s in steps:
        other = s.get("only_if_incomplete")
        if other is not None and other not in ids[: ids.index(s["id"])]:
            raise Am5Error(f"{s['id']}: its only_if_incomplete step is not run before it")
    pop = raw["population"]
    if pop.get("name") != POPULATION or tuple(pop.get("arms", ())) != ARMS:
        raise Am5Error(f"the population is {POPULATION}, retrieved arm only")
    if pop.get("split") != "development" or int(pop.get("questions", 0)) != 63:
        raise Am5Error("the population is the 63 development questions")
    for key in ("question_ids_sha256", "dev_artifact_sha256"):
        if not _is_digest(pop.get(key)):
            raise Am5Error(f"population.{key} must be a SHA-256")
    job = raw["job"]
    if int(job["gpus"]) != 1:
        raise Am5Error("one GPU")
    budgets = job["step_budgets"]
    if sorted(budgets) != sorted(ids):
        raise Am5Error("a budget for every step")
    for sid, (min_start, max_s) in budgets.items():
        if not 0 < int(max_s) < int(min_start) < int(job["minutes"]) * 60:
            raise Am5Error(f"job.{sid}: 0 < max_s < min_start_s < the limit")
    caps = [int(c) for c in raw["analysis"]["caps"]]
    if not caps or any(not 1 <= c <= FULL_ORDER for c in caps):
        raise Am5Error(f"caps must lie in 1-{FULL_ORDER}")
    per_table = raw["analysis"]["am3_per_table"]
    if not _is_digest(per_table.get("sha256")):
        raise Am5Error("analysis.am3_per_table.sha256 must be a SHA-256")
    config = {
        "experiment_id": EXPERIMENT,
        "claim_level": "exploratory",
        "seeds": raw["seeds"],
        "base": raw["base"],
        "pilot": base["pilot"],
        "am3": base["am3"],
        "split_file_sha256": base["split_file_sha256"],
        "requests": base["requests"],
        "reader_sampling": base["reader_sampling"],
        "readers": base["readers"],
        "models": base["models"],
        "steps": steps,
        "jobs": {POPULATION: job},
        "population": pop,
        "budget": raw["budget"],
        "analysis": {"caps": caps, "am3_per_table": per_table},
        "hand_check": raw["hand_check"],
    }
    return config


def require_artifact_pin(config: dict[str, Any]) -> str:
    pin = config["population"].get("artifact_sha256")
    if not _is_digest(pin):
        raise Am5Error("the ablated artifact is not pinned yet (run prepare, then pin it)")
    return pin


def step_budget(config: dict[str, Any], step_id: str) -> tuple[int, int]:
    min_start, max_s = config["jobs"][POPULATION]["step_budgets"][step_id]
    return int(min_start), int(max_s)


# --------------------------------------------------------------------------- the ablated pools


def ablate(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """The record without its evidence sessions: every haystack session whose id is in
    ``answer_session_ids`` is removed (all copies of a repeated id), with its date. Returns the
    ablated record and text-free facts."""

    if mc.is_abstention(record):
        raise Am5Error(f"{record['question_id']}: AM5 takes no abstention question")
    evidence = {str(s) for s in record.get("answer_session_ids") or []}
    if not evidence:
        raise Am5Error(f"{record['question_id']}: no answer_session_ids")
    ids = [str(s) for s in record["haystack_session_ids"]]
    keep = [i for i, sid in enumerate(ids) if sid not in evidence]
    removed = len(ids) - len(keep)
    out = dict(record)
    out["haystack_sessions"] = [record["haystack_sessions"][i] for i in keep]
    out["haystack_session_ids"] = [record["haystack_session_ids"][i] for i in keep]
    out["haystack_dates"] = [record["haystack_dates"][i] for i in keep]
    turns_before = mc.iter_turns(record)
    turns_after = mc.iter_turns(out)
    facts = {
        "evidence_session_ids": len(evidence),
        "evidence_session_ids_in_haystack": len(evidence & set(ids)),
        "sessions_before": len(ids),
        "sessions_removed": removed,
        "sessions_after": len(keep),
        "repeated_evidence_session_ids": removed - len(evidence & set(ids)),
        "user_turns_before": sum(t.role == "user" for t in turns_before),
        "user_turns_after": sum(t.role == "user" for t in turns_after),
        "has_answer_turns_before": sum(t.has_answer for t in turns_before),
        "has_answer_turns_in_evidence_sessions": sum(
            t.has_answer for t in turns_before if t.session_id in evidence
        ),
        "has_answer_turns_after": sum(t.has_answer for t in turns_after),
        "has_answer_user_turns_after": sum(t.has_answer and t.role == "user" for t in turns_after),
    }
    if facts["evidence_session_ids_in_haystack"] != facts["evidence_session_ids"]:
        raise Am5Error(f"{record['question_id']}: an evidence session is not in the haystack")
    if any(t.session_id in evidence for t in turns_after):
        raise Am5Error(f"{record['question_id']}: an evidence turn survived the ablation")
    return out, facts


def _turn_key(m: dict[str, Any]) -> tuple[str, int]:
    return (str(m["session_id"]), int(m["turn_index"]))


def pool_facts(
    record: dict[str, Any], ablated: dict[str, Any], pool: list[dict[str, Any]],
    pool_config: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Text-free leakage facts of one ablated pool: LongMemEval's has_answer flags left in it;
    memories whose text (cut as AM1 cuts it) equals an evidence-session user turn's; memories
    that contain the normalized reference answer (``harness.memcredit.contains_answer``, crude:
    short answers match by chance); the same answer search over every remaining user turn; and how
    many memories the ablated pool shares with the original retrieved pool."""

    evidence = {str(s) for s in record["answer_session_ids"]}
    entries = g.memory_texts(record, pool_config)
    evidence_text = {e["text_sha256"] for e in entries if e["session_id"] in evidence}
    original = g.retrieved_pool(record, pool_config)
    answer = str(record["answer"])
    remaining = [t for t in mc.iter_turns(ablated) if t.role == "user"]
    return {
        "pool_has_answer_memories": sum(bool(m["is_gold"]) for m in pool),
        "pool_memories_equal_to_an_evidence_turn": sum(
            m["text_sha256"] in evidence_text for m in pool
        ),
        "pool_memories_containing_the_answer": sum(
            mc.contains_answer(m["text"], answer) for m in pool
        ),
        "remaining_user_turns_containing_the_answer": sum(
            mc.contains_answer(t.content, answer) for t in remaining
        ),
        "answer_normalized_tokens": len(mc.normalize_answer(answer).split()),
        "original_pool_has_answer_memories": sum(bool(m["is_gold"]) for m in original),
        "memories_shared_with_the_original_pool": len(
            {_turn_key(m) for m in pool} & {_turn_key(m) for m in original}
        ),
    }


def build_artifact(
    records: list[dict[str, Any]], pilot: dict[str, Any], split: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The ablated development population, in the split's order: per question its ablated
    retrieved pool and the text-free facts."""

    by_id = {r["question_id"]: r for r in records}
    pool_config = ms.pool_config(pilot)
    questions, facts = [], []
    for qid in split["development"]:
        record = by_id[qid]
        ablated, removal = ablate(record)
        pool = g.retrieved_pool(ablated, pool_config)
        leak = pool_facts(record, ablated, pool, pool_config)
        questions.append({
            "question_id": qid,
            "question_type": record["question_type"],
            "question": record["question"],
            "answer": str(record["answer"]),
            "question_date": record["question_date"],
            "abstention": False,
            "gold_turns_total": removal["has_answer_turns_after"],
            "user_turns_total": removal["user_turns_after"],
            "pools": {"retrieved": pool},
        })  # fmt: skip
        facts.append({"question_id": qid, "question_type": record["question_type"],
                      **removal, **leak})  # fmt: skip
    ids = [q["question_id"] for q in questions]
    artifact = {
        "experiment_id": EXPERIMENT,
        "claim_level": "exploratory",
        "split": POPULATION,
        "source": pilot["source"],
        "retriever": pilot["retriever"],
        "pools_config": pilot["pools"],
        "arms": list(ARMS),
        "ablation": "every haystack session whose id is in answer_session_ids removed; the BM25 "
        "top-8 user turns of the rest, as AM1's retrieved arm",
        "question_ids_sha256": g.ids_sha256(ids),
        "questions": questions,
    }
    return artifact, facts


def leakage_totals(facts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def total(key: str) -> int:
        return sum(int(f[key]) for f in facts)

    def pools_with(key: str) -> int:
        return sum(int(f[key]) > 0 for f in facts)

    return {
        "questions": len(facts),
        "sessions_removed": total("sessions_removed"),
        "evidence_session_ids": total("evidence_session_ids"),
        "questions_with_a_repeated_evidence_session_id": pools_with(
            "repeated_evidence_session_ids"
        ),
        "has_answer_turns_before": total("has_answer_turns_before"),
        "has_answer_turns_in_evidence_sessions": total("has_answer_turns_in_evidence_sessions"),
        "has_answer_turns_left_in_the_haystack": total("has_answer_turns_after"),
        "questions_with_has_answer_turns_left": pools_with("has_answer_turns_after"),
        "has_answer_memories_in_the_ablated_pools": total("pool_has_answer_memories"),
        "pools_with_a_has_answer_memory": pools_with("pool_has_answer_memories"),
        "pool_memories_equal_to_an_evidence_turn": total("pool_memories_equal_to_an_evidence_turn"),
        "pools_with_a_memory_equal_to_an_evidence_turn": pools_with(
            "pool_memories_equal_to_an_evidence_turn"
        ),
        "pools_with_a_memory_containing_the_answer": pools_with(
            "pool_memories_containing_the_answer"
        ),
        "questions_whose_remaining_user_turns_contain_the_answer": pools_with(
            "remaining_user_turns_containing_the_answer"
        ),
        "original_pools_with_a_has_answer_memory": pools_with("original_pool_has_answer_memories"),
        "memories_shared_with_the_original_pools": total("memories_shared_with_the_original_pool"),
        "memories": 8 * len(facts),
    }


def artifact_summary(
    artifact: dict[str, Any], digest: str, facts: list[dict[str, Any]], pilot: dict[str, Any]
) -> dict[str, Any]:
    """The artifact without LongMemEval text: ids, types, digests, pool coordinates, BM25 ranks and
    scores, the leakage facts and each full-pool prompt's length in characters."""

    by_q = {f["question_id"]: f for f in facts}
    questions = []
    for q in artifact["questions"]:
        pool = q["pools"]["retrieved"]
        questions.append({
            "question_id": q["question_id"],
            "question_type": q["question_type"],
            "question_sha256": sha256_text(q["question"]),
            "answer_sha256": sha256_text(q["answer"]),
            "pool": [{k: v for k, v in m.items() if k != "text"} for m in pool],
            "full_pool_prompt_chars": len(mc.user_message(q, pool, pilot["prompt"])),
            "facts": by_q[q["question_id"]],
        })  # fmt: skip
    return {
        "experiment_id": artifact["experiment_id"],
        "split": artifact["split"],
        "artifact_sha256": digest,
        "questions": len(questions),
        "question_ids_sha256": artifact["question_ids_sha256"],
        "by_type": dict(sorted(Counter(q["question_type"] for q in questions).items())),
        "leakage": leakage_totals(facts),
        "max_full_pool_prompt_chars": max(q["full_pool_prompt_chars"] for q in questions),
        "ablation": artifact["ablation"],
        "per_question": questions,
    }


def cmd_prepare(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    for p in (args.artifact, args.summary, args.dev_artifact):
        g.check_dev_path(p)
    for p in (args.artifact, args.summary):
        if Path(p).exists():
            raise Am5Error(f"refusing to overwrite {p}")
    g.refuse_inside_repo(args.artifact)
    split = ms.load_split(Path(args.split_file), pilot)
    if sha256_file(Path(args.split_file)) != config["split_file_sha256"]:
        raise Am5Error("the split file differs from its pin")
    if g.ids_sha256(split["development"]) != config["population"]["question_ids_sha256"]:
        raise Am5Error("the split's development ids differ from their pin")
    dev_raw = Path(args.dev_artifact).read_bytes()
    if sha256_bytes(dev_raw) != config["population"]["dev_artifact_sha256"]:
        raise Am5Error("the development artifact differs from its pin")
    dev = json.loads(dev_raw)
    records = g.read_source(Path(args.source), pilot)
    check = g.check_dev_retrieved_pools(records, pilot, dev)
    if check["questions"] == 0 or check["retrieved_pools_identical"] != check["questions"]:
        raise Am5Error(f"the pool builder does not reproduce the development pools: {check}")
    artifact, facts = build_artifact(records, pilot, split)
    data = mc.canonical_json(artifact)
    digest = sha256_bytes(data)
    summary = artifact_summary(artifact, digest, facts, pilot)
    summary["dev_retrieved_pool_check"] = check
    Path(args.artifact).write_bytes(data)
    Path(args.summary).write_bytes(mc.canonical_json(summary))
    pin = config["population"].get("artifact_sha256")
    return {
        "artifact_sha256": digest,
        "artifact_bytes": len(data),
        "questions": summary["questions"],
        "question_ids_sha256": summary["question_ids_sha256"],
        "by_type": summary["by_type"],
        "leakage": summary["leakage"],
        "max_full_pool_prompt_chars": summary["max_full_pool_prompt_chars"],
        "dev_retrieved_pool_check": check,
        "matches_config_pin": digest == pin,
        "summary_sha256": sha256_file(Path(args.summary)),
    }


def load_artifact(
    config: dict[str, Any], path: Path | str, expected_sha256: str | None = None
) -> dict[str, Any]:
    g.check_dev_path(path)
    raw = Path(path).read_bytes()
    digest = sha256_bytes(raw)
    if digest != require_artifact_pin(config):
        raise Am5Error(f"the ablated artifact {path} is not the pinned one")
    if expected_sha256 is not None and digest != expected_sha256:
        raise Am5Error("the ablated artifact differs from the expected SHA-256")
    artifact = json.loads(raw)
    check_artifact(config, artifact)
    return artifact


def check_artifact(config: dict[str, Any], artifact: dict[str, Any]) -> None:
    pop = config["population"]
    if artifact.get("experiment_id") != EXPERIMENT or artifact.get("split") != POPULATION:
        raise Am5Error("not the ablated development artifact")
    ids = [q["question_id"] for q in artifact["questions"]]
    if len(ids) != int(pop["questions"]) or g.ids_sha256(ids) != pop["question_ids_sha256"]:
        raise Am5Error("the question ids differ from the development split's")
    for q in artifact["questions"]:
        if mc.is_abstention(q) or q.get("abstention"):
            raise Am5Error(f"{q['question_id']}: no abstention question here")
        if len(q["pools"]["retrieved"]) != K:
            raise Am5Error(f"{q['question_id']}: not a pool of {K}")


# --------------------------------------------------------------------------- requests and judge


def validation_items(artifact: dict[str, Any], pilot: dict[str, Any]) -> list[dict[str, Any]]:
    """AM1's validation items on these questions (reference answer yes; "I don't know." no;
    another same-type question's answer no)."""

    return ms.validation_items(artifact, pilot["judge"]["validation"])


def judge_items(
    artifact: dict[str, Any], pilot: dict[str, Any], passes: dict[str, dict[int, str]]
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply) of the reader passes, then the validation items
    (am3g's ``judge_items`` for this population)."""

    requests = g.request_table(artifact, ARMS)
    n = len(requests)
    replies: dict[int, str] = {}
    extended: list[dict[str, Any]] = []
    for k, step_id in enumerate(sorted(passes)):
        for index, text in passes[step_id].items():
            replies[k * n + index] = text
        extended += [dict(r, index=k * n + r["index"]) for r in requests]
    return ms.judge_item_table(artifact, replies, extended, validation_items(artifact, pilot))


def judge_message(artifact: dict[str, Any], item: dict[str, Any]) -> str:
    """LongMemEval's non-abstention answer-check prompt against the reference answer."""

    q = artifact["questions"][item["question_index"]]
    if q.get("abstention") or mc.is_abstention(q) or item.get("template") == "abstention":
        raise Am5Error("AM5 judges with the answer-check template only")
    return g.judge_message(artifact, item)


# --------------------------------------------------------------------------- GPU worker and driver
# Ports of memcredit_am3g.vllm_worker, run_step and run_main for this population (no freeze gate;
# AM5's config, artifact, budgets and judge items); the engine calls are the same.


def vllm_worker(args: argparse.Namespace) -> int:
    import vllm.envs as vllm_envs
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    artifact = load_artifact(config, args.evidence, args.expected_evidence_sha256)
    step = g.step_spec(config, args.step)
    _, max_s = step_budget(config, step["id"])
    out = Path(args.output_dir) / "sessions" / step["id"]
    out.mkdir(parents=True, exist_ok=True)
    flag = s0.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": lane.utc_now(), "event": event, "step": step["id"], **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    def finish(code: int, **record: Any) -> None:
        lane.write_json(out / "session.json", {"step": step, "exit": code, **record})
        lane.write_json(out / "done.json", {"exit": code, "utc": lane.utc_now()})
        sys.stdout.flush()

    spec = g.model_spec(config, pilot, step)
    model_dir = am3.MODEL_ROOT / spec["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    if step["kind"] == "reader":
        messages = g.reader_messages(pilot, artifact, ARMS)
    else:
        items = json.loads((Path(args.output_dir) / "judge-items.json").read_text("utf-8"))
        messages = [judge_message(artifact, item) for item in items]
    prompt_ids = [s0.render_prompt_ids(tokenizer, m, spec["enable_thinking"]) for m in messages]
    prompt_lens = [len(p) for p in prompt_ids]
    stop_id = am3.stop_token_id(tokenizer, spec["stop_token"])
    kwargs = am3.engine_kwargs(spec, int(config["seeds"][0]), bool(step["enforce_eager"]))
    want_bi = bool(step["batch_invariant"])
    log("engine-start", engine_kwargs=kwargs, gpu=am3.gpu_identity(), model_id=spec["model_id"],
        population=POPULATION, env_batch_invariant=os.environ.get("VLLM_BATCH_INVARIANT"),
        vllm_envs_batch_invariant=bool(vllm_envs.VLLM_BATCH_INVARIANT),
        prompt_ids_sha256=s0.prompt_digest(prompt_ids), requests=len(prompt_ids),
        prompt_len_min=min(prompt_lens), prompt_len_max=max(prompt_lens),
        prompt_tokens_total=sum(prompt_lens), stop_token_id=stop_id)  # fmt: skip
    if bool(vllm_envs.VLLM_BATCH_INVARIANT) != want_bi:
        log("mode-mismatch", wanted_batch_invariant=want_bi)
        finish(2, reason="mode mismatch")
        os._exit(2)
    t0 = time.time()
    try:
        llm = LLM(**kwargs)
    except Exception as exc:  # noqa: BLE001 - recorded; the driver may run a fallback step
        log("engine-failed", error=repr(exc)[:2000], init_s=round(time.time() - t0, 1))
        finish(5, reason="engine failed", error=repr(exc)[:2000], engine_kwargs=kwargs)
        os._exit(5)
    init_s = round(time.time() - t0, 1)
    log("engine-ready", init_s=init_s)
    engine = llm.llm_engine
    base = {"n": 1, "temperature": spec["sampling"]["temperature"],
            "max_tokens": spec["sampling"]["max_tokens"],
            "logprobs": spec["sampling"]["logprobs"]}  # fmt: skip
    order = list(range(len(prompt_ids)))
    plan = [("smoke", order[:SMOKE_REQUESTS], True), ("all", order, False)]
    passes: list[dict[str, Any]] = []
    code = 0
    for name, indices, smoke in plan:
        remaining = args.deadline - time.time()
        if flag.event.is_set() or remaining < 30:
            passes.append({"name": name, "status": "skipped",
                           "reason": flag.reason or f"remaining {remaining:.0f} s"})  # fmt: skip
            code = 3
            continue
        reset = bool(llm.reset_prefix_cache())
        ids = [f"{step['id']}/{name}/{i}" for i in indices]
        batch = [
            (ours, TokensPrompt(prompt_token_ids=prompt_ids[i]),
             SamplingParams(**base, stop_token_ids=[stop_id]))
            for ours, i in zip(ids, indices, strict=True)
        ]  # fmt: skip
        log("pass-start", name=name, requests=len(batch), prefix_cache_reset=reset)
        stop_at = min(args.deadline, time.time() + float(max_s))
        state, info = s0.stream_requests(engine, batch, stop_at, flag, None)
        record = {
            "session": step["id"],
            "name": name,
            "population": POPULATION,
            "batch_invariant": want_bi,
            "enforce_eager": bool(step["enforce_eager"]),
            "kind": step["kind"],
            "model_id": spec["model_id"],
            "sampling": "greedy",
            "sampling_kwargs": base,
            "stop_token_id": stop_id,
            "order": "canonical",
            "set": name,
            "requests": len(batch),
            "prefix_cache_reset": reset,
            "info": info,
            "status": "complete" if info["finished"] == len(batch) else "partial",
        }
        record = s0.save_pass(out, name, indices, ids, state, prompt_lens, record)
        passes.append({k: record[k] for k in ("name", "status", "requests")} | {"info": info})
        log("pass-done", name=name, status=record["status"], **info)
        if record["status"] != "complete":
            code = 3
        if smoke:
            ok, why = s0.smoke_ok(record, state)
            log("smoke-check", ok=ok, reason=why)
            if not ok:
                code = SMOKE_FAILED_EXIT
                break
    finish(code, engine_kwargs=kwargs, init_s=init_s, passes=passes,
           prompt_ids_sha256=s0.prompt_digest(prompt_ids), gpu=am3.gpu_identity())  # fmt: skip
    closer = threading.Thread(target=lambda: engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


def worker_argv(step: dict[str, Any], args: argparse.Namespace, out: Path, stop_at: float) -> list:
    return [sys.executable, str(Path(__file__).resolve()), "worker", "--step", step["id"],
            "--config", args.config, "--output-dir", str(out), "--deadline", f"{stop_at:.3f}",
            "--evidence", args.evidence,
            "--expected-evidence-sha256", args.expected_evidence_sha256]  # fmt: skip


def run_step(
    step: dict[str, Any], args: argparse.Namespace, out: Path, stop_at: float,
    state: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Start one worker, wait for it, kill it when hung or late; return its record."""

    argv = worker_argv(step, args, out, stop_at)
    env = am3.worker_env(dict(os.environ), out, step)
    record: dict[str, Any] = {"kind": step["kind"], "argv": argv, "started_at": lane.utc_now(),
                              "batch_invariant": step["batch_invariant"],
                              "enforce_eager": step["enforce_eager"]}  # fmt: skip
    if step["kind"] == "reader":
        record["reader"] = step["reader"]
    t0 = time.time()
    with (out / f"worker-{step['id']}.log").open("w", encoding="utf-8") as handle:
        child = subprocess.Popen(
            argv, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        state["children"] = [child]
        done = out / "sessions" / step["id"] / "done.json"
        done_seen: float | None = None
        while child.poll() is None:
            now = time.time()
            if done_seen is None and done.is_file():
                done_seen = now
            hung = done_seen is not None and now - done_seen > 25
            late = now > stop_at + 90
            after_signal = state["signal_at"] is not None and now - state["signal_at"] > 40
            if hung or late or after_signal:
                record["killed"] = "hung after done" if hung else "late" if late else "signal"
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=30)
            time.sleep(1.0)
        state["children"] = []
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(child.pid, signal.SIGKILL)
    record["exit"] = child.returncode
    record["wall_s"] = round(time.time() - t0, 1)
    saved = json.loads(done.read_text()) if done.is_file() else None
    record["worker_done"] = saved
    outcome = {0: "complete", 3: "partial", SMOKE_FAILED_EXIT: "smoke-failed", 5: "engine-failed"}
    record["status"] = "failed" if saved is None else outcome.get(saved["exit"], "failed")
    release_until = time.time() + 120
    while time.time() < release_until:
        used = s0.gpu_memory_used_mib()
        if not used or max(used) < 1024:
            break
        time.sleep(2.0)
    return record


def run_main(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    if list(args.seeds) != config["seeds"]:
        raise Am5Error("--seeds must equal the config's declared seeds")
    artifact = load_artifact(config, args.evidence, args.expected_evidence_sha256)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = lane.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": EXPERIMENT,
        "population": POPULATION,
        "claim_level": "exploratory",
        "started_at": lane.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "questions": len(artifact["questions"]),
        "arms": list(ARMS),
        "reader_requests_per_reader": len(g.request_table(artifact, ARMS)),
        "gpus": am3.driver_gpu_list(),
        "steps": {},
    }
    lane.write_json(out / "summary.json", summary)
    s0.record_environment(out)
    state: dict[str, Any] = {"children": [], "signal": None, "signal_at": None}

    def on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        state["signal_at"] = time.time()
        for child in state["children"]:
            if child.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(child.pid, signal.SIGTERM)

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    try:
        summary["model_verification"] = g.verify_models(config, pilot)
    except Exception as exc:  # noqa: BLE001 - recorded; nothing runs on an unverified model
        summary["model_verification"] = {"error": repr(exc)[:2000]}
        lane.write_json(out / "summary.json", summary)
        return 2
    lane.write_json(out / "summary.json", summary)
    sampler = s0.start_gpu_sampler(out)
    for step in config["steps"]:
        record: dict[str, Any] = {"kind": step["kind"]}
        summary["steps"][step["id"]] = record
        prior = step.get("only_if_incomplete")
        min_start, _ = step_budget(config, step["id"])
        remaining = stop_at - time.time()
        if prior is not None and summary["steps"].get(prior, {}).get("status") == "complete":
            record.update(status="not-needed", reason=f"{prior} completed")
            continue
        if state["signal"] or remaining < float(min_start):
            why = state["signal"] or f"remaining {remaining:.0f} s"
            record.update(status="skipped", reason=why)
            continue
        if step["kind"] == "judge":
            sources = g.reader_steps_complete(summary)
            if not sources:
                record.update(status="skipped", reason="no reader pass completed")
                continue
            if not (out / "judge-items.json").is_file():
                passes = {
                    sid: am3.completed_replies(g.load_pass(out / "sessions" / sid))
                    for sid in sources
                }
                items = judge_items(artifact, pilot, passes)
                lane.write_json(out / "judge-items.json", items)
                summary["judge_items"] = {
                    "from": sources,
                    "total": len(items),
                    "reader": sum(1 for i in items if i["source"] == "reader"),
                    "validation": sum(1 for i in items if i["source"] != "reader"),
                }
        record.update(run_step(step, args, out, stop_at, state))
        lane.write_json(out / "summary.json", summary)
    if sampler is not None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(sampler.pid, signal.SIGTERM)
    summary["finished_at"] = lane.utc_now()
    summary["signal"] = state["signal"]
    lane.write_json(out / "summary.json", summary)
    if state["signal"]:
        lane.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            f"{EXPERIMENT}: every finished pass saved; no resume (a rerun is a new job)",
        )
    readers_done = {summary["steps"][s].get("reader") for s in g.reader_steps_complete(summary)}
    judged = summary["steps"].get(JUDGE_STEP, {}).get("status") == "complete"
    return 0 if readers_done == set(READERS) and judged else 3


# --------------------------------------------------------------------------- plan and selftest


def build_plan(config: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    job = config["jobs"][POPULATION]
    return {
        "experiment_id": EXPERIMENT,
        "population": POPULATION,
        "questions": len(artifact["questions"]),
        "arms": list(ARMS),
        "pools": len(artifact["questions"]),
        "requests_per_pool": len(REQUEST_MASKS),
        "requests_per_reader": len(g.request_table(artifact, ARMS)),
        "readers": [r["id"] for r in config["readers"]],
        "steps": [s["id"] for s in config["steps"]],
        "job_minutes": job["minutes"],
        "gpus": job["gpus"],
    }


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only, no engine: every request rendered with every reader's tokenizer and chat
    template, and the judge items (one placeholder reply per pool) with the judge's; lengths,
    thinking-off markers, stop tokens and vLLM's architecture resolution (am3g's selftest)."""

    from transformers import AutoTokenizer

    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    artifact = load_artifact(config, args.evidence, args.expected_evidence_sha256)
    root = Path(args.model_root)
    report: dict[str, Any] = {"plan": build_plan(config, artifact), "readers": {}}
    messages = g.reader_messages(pilot, artifact, ARMS)
    limit_tokens = config["reader_sampling"]["max_tokens"]
    ok = True
    for r in config["readers"]:
        tok = AutoTokenizer.from_pretrained(str(root / r["model_id"]))
        ids = [s0.render_prompt_ids(tok, m, bool(r["enable_thinking"])) for m in messages]
        lengths = [len(x) for x in ids]
        probe = tok.decode(s0.render_prompt_ids(tok, "x", bool(r["enable_thinking"])))
        marker = r.get("thinking_marker")
        try:
            stop = am3.stop_token_id(tok, r["stop_token"])
            stop_error = None
        except am3.Am3Error as exc:
            stop, stop_error = None, str(exc)
        model_config = json.loads((root / r["model_id"] / "config.json").read_text("utf-8"))
        entry = {
            "requests": len(ids),
            "len_min": min(lengths),
            "len_max": max(lengths),
            "len_mean": sum(lengths) / len(lengths),
            "tokens_total": sum(lengths),
            "fits": max(lengths) <= r["engine"]["max_model_len"] - limit_tokens,
            "thinking_marker_ok": marker is None or marker in probe,
            "no_think_tag_when_unmarked": marker is not None or "<think>" not in probe,
            "stop_token_id": stop,
            "stop_token_error": stop_error,
            "prompt_ids_sha256": s0.prompt_digest(ids),
            "architectures": model_config.get("architectures"),
        }
        entry["ok"] = bool(
            entry["fits"] and entry["thinking_marker_ok"]
            and entry["no_think_tag_when_unmarked"] and stop is not None
        )  # fmt: skip
        ok &= entry["ok"]
        report["readers"][r["id"]] = entry
    placeholder = {"selftest": {r["index"]: "I don't know." for r in g.request_table(artifact, ARMS)
                                if r["mask"] == FULL}}  # fmt: skip
    items = judge_items(artifact, pilot, placeholder)
    spec = pilot["judge"]["primary"]
    tok = AutoTokenizer.from_pretrained(str(root / spec["model_id"]))
    lengths = [len(s0.render_prompt_ids(tok, judge_message(artifact, i), False)) for i in items]
    fits = (
        max(lengths) <= spec["engine"]["max_model_len"] - pilot["judge"]["sampling"]["max_tokens"]
    )
    report["judge"] = {
        "model_id": spec["model_id"],
        "items": len(items),
        "len_max": max(lengths),
        "fits": fits,
        "answer_templates_sha256": g.answer_templates_sha256(),
    }
    ok &= fits
    try:
        import transformers
        import vllm
        from vllm.model_executor.models import registry as vreg

        report["vllm_version"] = vllm.__version__
        report["transformers_version"] = transformers.__version__
        supported = set(vreg.ModelRegistry.get_supported_archs())
        backend = set(getattr(vreg, "_TRANSFORMERS_SUPPORTED_MODELS", {}))
        archs = {}
        for rid, entry in report["readers"].items():
            for arch in entry["architectures"] or []:
                archs[arch] = {"reader": rid, "supported": arch in supported,
                               "transformers_backend": arch in backend,
                               "in_transformers": hasattr(transformers, arch)}  # fmt: skip
        report["architectures"] = archs
        ok &= all(a["supported"] for a in archs.values())
        ok &= all(a["in_transformers"] for a in archs.values() if a["transformers_backend"])
    except Exception as exc:  # noqa: BLE001 - recorded
        report["vllm_import_error"] = repr(exc)
        ok = False
    report["ok"] = bool(ok)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


# --------------------------------------------------------------------------- extract (host)


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    """Host only (reads replies): per reader and pool, per requested mask the primary judge's
    label, the abstention flag and pattern, the finish reason, the token count and the normalized
    reply's SHA-256 (``memcredit_am3g.pool_records``); the judge's validation counts; the
    artifact summary's leakage facts. Writes text-free features to a host-only directory."""

    for p in (args.run_dir, args.evidence, args.private_dir, args.summary):
        g.check_dev_path(p)
    g.refuse_inside_repo(args.private_dir)
    config = load_config(Path(args.config))
    artifact = load_artifact(config, args.evidence)
    summary_art = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    if summary_art.get("artifact_sha256") != require_artifact_pin(config):
        raise Am5Error("the artifact summary is not the pinned artifact's")
    run_dir = Path(args.run_dir)
    summary = g.read_run_json(run_dir / "summary.json", "the driver's summary")
    if summary.get("population") != POPULATION or summary.get("experiment_id") != EXPERIMENT:
        raise Am5Error("the run directory is not this experiment's run")
    items = g.read_run_json(run_dir / "judge-items.json", "the judge items (judge32 was skipped)")
    judge_dir = run_dir / "sessions" / JUDGE_STEP
    labels = {
        "primary": am3.labels_from_pass(g.load_pass(judge_dir)),
        "secondary": {},
    }
    item_of = am3.item_index(items)
    readers: dict[str, Any] = {}
    for sid in g.reader_steps_complete(summary):
        reader_id = summary["steps"][sid]["reader"]
        if reader_id in readers:
            raise Am5Error(f"two completed passes of {reader_id}")
        passed = g.load_pass(run_dir / "sessions" / sid)
        pools = g.pool_records(artifact, ARMS, passed["rows"], item_of, labels)
        finish = Counter(c["finish"] for p in pools for c in p["masks"].values())
        readers[reader_id] = {
            "step": sid,
            "batch_invariant": summary["steps"][sid]["batch_invariant"],
            "enforce_eager": summary["steps"][sid]["enforce_eager"],
            "pass_sha256": {
                f"sessions/{sid}/{f}": sha256_file(run_dir / "sessions" / sid / f)
                for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
            },
            "requests": len(passed["rows"]),
            "finish": dict(sorted(finish.items(), key=lambda kv: str(kv[0]))),
            "missing_logprobs": passed["meta"].get("missing_logprobs"),
            "pools_complete_primary": sum(g.pool_complete(p, ("primary",)) for p in pools),
            "pools": pools,
        }
    validation = {
        "judge_items": len(items),
        "judge_items_reader": sum(1 for i in items if i["source"] == "reader"),
        "labelled": len(labels["primary"]),
        "judge_validation": g.validation_summary(items, labels)["primary"],
        "judge_pass_sha256": {
            f"sessions/{JUDGE_STEP}/{f}": sha256_file(judge_dir / f)
            for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
        },
        "judge_items_sha256": sha256_file(run_dir / "judge-items.json"),
    }
    if lf.patterns_sha256() != lf.ABSTENTION_PATTERNS_SHA256:
        raise Am5Error("the abstention patterns differ from AM1d's")
    payload = {
        "experiment": EXPERIMENT,
        "population": POPULATION,
        "arms": list(ARMS),
        "artifact_sha256": require_artifact_pin(config),
        "question_ids_sha256": config["population"]["question_ids_sha256"],
        "questions": len(artifact["questions"]),
        "abstention_patterns_sha256": lf.patterns_sha256(),
        "answer_templates_sha256": g.answer_templates_sha256(),
        "code_sha256": code_digests(),
        "artifact_summary_sha256": sha256_file(Path(args.summary)),
        "leakage": summary_art["leakage"],
        "leakage_per_question": [q["facts"] for q in summary_art["per_question"]],
        "dev_retrieved_pool_check": summary_art.get("dev_retrieved_pool_check"),
        "run": {
            "summary_steps": {
                sid: {
                    k: rec.get(k)
                    for k in (
                        "kind",
                        "reader",
                        "status",
                        "batch_invariant",
                        "enforce_eager",
                        "exit",
                        "wall_s",
                    )
                }
                for sid, rec in summary.get("steps", {}).items()
            },
            "judge_items": summary.get("judge_items"),
            "model_verification": {
                k: {
                    f: v.get(f)
                    for f in (
                        "repo_id",
                        "revision",
                        "artifact_root_sha256",
                        "receipt_sha256",
                        "verified_by",
                    )
                }
                for k, v in summary.get("model_verification", {}).items()
                if isinstance(v, dict)
            },
        },  # fmt: skip
        "validation": validation,
        "readers": readers,
    }
    private = Path(args.private_dir)
    private.mkdir(parents=True, exist_ok=True)
    target = private / f"features-{POPULATION}.json.gz"
    g.write_gz_json(target, payload)
    return {
        "population": POPULATION,
        "readers": {r: {k: v for k, v in d.items() if k != "pools"} for r, d in readers.items()},
        "validation": validation,
        "features_sha256": sha256_file(target),
    }


def check_features(features: dict[str, Any], config: dict[str, Any]) -> None:
    expected = {
        "experiment": EXPERIMENT,
        "population": POPULATION,
        "artifact_sha256": require_artifact_pin(config),
        "question_ids_sha256": config["population"]["question_ids_sha256"],
        "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
        "answer_templates_sha256": g.ANSWER_TEMPLATES_SHA256,
    }
    bad = [k for k, v in expected.items() if features.get(k) != v]
    if bad:
        raise Am5Error(f"the features differ from the pins: {bad}")
    if sorted(features["readers"]) != sorted(READERS):
        raise Am5Error("the features lack a reader's complete pass")
    for reader_id, reader in features["readers"].items():
        if len(reader["pools"]) != int(config["population"]["questions"]):
            raise Am5Error(f"{reader_id}: pools differ from the population")


def int_masks(features: dict[str, Any]) -> None:
    for reader in features["readers"].values():
        for pool in reader["pools"]:
            pool["masks"] = {int(m): cell for m, cell in pool["masks"].items()}


# --------------------------------------------------------------------------- the capped rule


def capped_rule(pool: dict[str, Any], cap: int) -> dict[str, Any]:
    """AM4's capped rule (``memcredit_am4.capped_rule``; a test checks equality): the registered
    rule's choice when its first answering 4-subset is within the first ``cap`` of the BM25 order,
    else BM25 top 4; reads are that position, or ``cap``."""

    if not 1 <= int(cap) <= FULL_ORDER:
        raise Am5Error(f"the cap must be 1-{FULL_ORDER}, not {cap}")
    order = am3.bm25_order(pool["bm25_rank"])
    rule = am3.nonabstain_bm25(pool)
    position = rule["first_answer_position"]
    answered = position is not None and position <= cap
    return {"mask": rule["mask"] if answered else order[0],
            "reads": position if answered else int(cap),
            "answered_within_cap": answered, "first_answer_position": position}  # fmt: skip


def pool_record(pool: dict[str, Any], caps: Sequence[int]) -> dict[str, Any]:
    """One ablated pool's text-free record: BM25 top 4 and its abstention, the first answering
    position, all 8's abstention, the number of abstaining 4-subsets, the primary judge's labels
    of top 4, all 8 and every cap's choice, and per cap whether the rule switched."""

    masks = pool["masks"]
    top4 = lf.bm25_top_mask(pool["bm25_rank"])
    rule = am3.nonabstain_bm25(pool)
    record: dict[str, Any] = {
        "question_id": pool["question_id"],
        "question_type": pool["question_type"],
        "bm25_top4_mask": top4,
        "bm25_top4_abstains": bool(masks[top4]["abstain"]),
        "first_answer_position": rule["first_answer_position"],
        "all_8_abstains": bool(masks[FULL]["abstain"]),
        "four_subset_abstain": sum(bool(masks[m]["abstain"]) for m in FOUR_SETS),
        "u": {"bm25_top4": int(masks[top4]["u"][JUDGE]), "all_8": int(masks[FULL]["u"][JUDGE])},
        "digest": {"bm25_top4": masks[top4]["digest"], "all_8": masks[FULL]["digest"]},
        "caps": {},
    }
    for cap in caps:
        c = capped_rule(pool, cap)
        switched = c["mask"] != top4
        if switched and not record["bm25_top4_abstains"]:
            raise Am5Error("the rule left a BM25 top 4 that does not abstain")
        record["caps"][str(cap)] = {
            "mask": c["mask"],
            "reads": c["reads"],
            "switched": switched,
            "kept_abstains": bool(masks[c["mask"]]["abstain"]),
            "u": int(masks[c["mask"]]["u"][JUDGE]),
            "digest": masks[c["mask"]]["digest"],
        }
    return record


def records_of(features: dict[str, Any], caps: Sequence[int]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for reader_id in READERS:
        pools = features["readers"][reader_id]["pools"]
        incomplete = [p for p in pools if not g.pool_complete(p, ("primary",))]
        if incomplete:
            raise Am5Error(f"{reader_id}: {len(incomplete)} pools lack replies or labels")
        out[reader_id] = [pool_record(p, caps) for p in pools]
    return out


# --------------------------------------------------------------------------- the blind hand check


def hand_plan(features: dict[str, Any], caps: Sequence[int], seed: int) -> dict[str, Any]:
    """Every reply on an ablated pool that an answer-giving rule would return: per reader, the
    rule's switched reply at the largest cap (which holds every smaller cap's) and BM25 top 4's
    reply where it does not abstain. Deduplicated by (question, normalized-reply SHA-256), in one
    seeded order (``random.Random(f"{seed}:am5:hand:order")``). Text-free, so ``analyze``
    recomputes it."""

    top = str(max(caps))
    uses: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for reader_id in READERS:
        for pool in features["readers"][reader_id]["pools"]:
            masks = {int(m): c for m, c in pool["masks"].items()}
            rec = pool_record({**pool, "masks": masks}, [int(top)])
            entry = rec["caps"][top]
            if entry["switched"]:
                uses.setdefault((rec["question_id"], entry["digest"]), []).append(
                    {"reader": reader_id, "role": "switched", "mask": entry["mask"],
                     "position": rec["first_answer_position"]})  # fmt: skip
            if not rec["bm25_top4_abstains"]:
                uses.setdefault((rec["question_id"], rec["digest"]["bm25_top4"]), []).append(
                    {"reader": reader_id, "role": "top4-answers", "mask": rec["bm25_top4_mask"]}
                )
    keys = sorted(uses)
    random.Random(f"{seed}:am5:hand:order").shuffle(keys)
    items = [{"item_id": f"a{n:04d}", "question_id": q, "reply_digest": d, "check": "answer",
              "uses": uses[(q, d)]} for n, (q, d) in enumerate(keys)]  # fmt: skip
    plan = {"seed": seed, "cap": int(top), "items": items,
            "labeller_prompt_sha256": g.hand_labeller_prompt_sha256(),
            "instructions_sha256": sha256_text(HAND_INSTRUCTIONS)}  # fmt: skip
    plan["plan_sha256"] = sha256_bytes(json.dumps(items, sort_keys=True).encode())
    return plan


def cmd_hand_sample(args: argparse.Namespace) -> dict[str, Any]:
    """Host only (writes texts to ``--hand-dir``): one JSON line per plan item with its id, the
    question id and type, the check, the question, the reference answer and the reply, and nothing
    else; the instructions; the chunks with am3g's pinned labeller prompt; a text-free manifest."""

    for p in (args.run_dir, args.evidence, args.features, args.hand_dir):
        g.check_dev_path(p)
    hand_dir = Path(args.hand_dir)
    g.refuse_inside_repo(hand_dir)
    if hand_dir.exists() and any(hand_dir.iterdir()):
        raise Am5Error(f"refusing a non-empty hand directory {hand_dir}")
    if Path(args.features).resolve().parent == hand_dir.resolve():
        raise Am5Error("the hand directory must not hold the features")
    config = load_config(Path(args.config))
    features = g.read_gz_json(Path(args.features))
    check_features(features, config)
    artifact = load_artifact(config, args.evidence)
    plan = hand_plan(features, config["analysis"]["caps"], int(config["hand_check"]["seed"]))
    index = {(r["question_id"], r["mask"]): r["index"] for r in g.request_table(artifact, ARMS)}
    questions = {q["question_id"]: q for q in artifact["questions"]}
    rows: dict[str, dict[int, Any]] = {}
    lines = []
    for item in plan["items"]:
        use = item["uses"][0]
        reader = use["reader"]
        if reader not in rows:
            step = features["readers"][reader]["step"]
            rows[reader] = g.load_pass(Path(args.run_dir) / "sessions" / step)["rows"]
        text = rows[reader][index[(item["question_id"], use["mask"])]]["text"]
        if sha256_text(mc.normalize_answer(text.strip())) != item["reply_digest"]:
            raise Am5Error("a reply differs from the features' digest")
        q = questions[item["question_id"]]
        lines.append(json.dumps({"item_id": item["item_id"], "question_id": q["question_id"],
                                 "question_type": q["question_type"], "check": "answer",
                                 "question": q["question"], "reference": str(q["answer"]),
                                 "reply": text.strip()}, ensure_ascii=False))  # fmt: skip
    hand_dir.mkdir(parents=True, exist_ok=True)
    sample = hand_dir / "hand-check-sample.jsonl"
    sample.write_text("\n".join(lines) + "\n", encoding="utf-8")
    instructions = hand_dir / "hand-check-instructions.txt"
    instructions.write_text(HAND_INSTRUCTIONS, encoding="utf-8")
    size = int(config["hand_check"]["chunk"])
    ids = [i["item_id"] for i in plan["items"]]
    chunks = []
    for k in range(0, len(lines), size):
        n = k // size + 1
        chunk, output = f"hand-first-chunk-{n:02d}.jsonl", f"hand-labels-first-{n:02d}.jsonl"
        (hand_dir / chunk).write_text("\n".join(lines[k : k + size]) + "\n", "utf-8")
        chunks.append({"chunk": chunk, "output": output, "items": ids[k : k + size],
                       "chunk_sha256": sha256_file(hand_dir / chunk)})  # fmt: skip
    plan_path = hand_dir / "hand-plan.json"
    plan_path.write_text(json.dumps(plan, indent=1, sort_keys=True), encoding="utf-8")
    manifest = {"plan_sha256": plan["plan_sha256"], "items": ids, "chunk_size": size,
                "first": chunks, "labeller_model": config["hand_check"]["labeller_model"],
                "labeller_prompt_sha256": g.hand_labeller_prompt_sha256(),
                "instructions_sha256": sha256_file(instructions),
                "sample_sha256": sha256_file(sample)}  # fmt: skip
    (hand_dir / "hand-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    roles = Counter(u["role"] for i in plan["items"] for u in i["uses"])
    return {"items": len(lines), "uses_by_role": dict(sorted(roles.items())),
            "plan_sha256": plan["plan_sha256"], "sample_sha256": manifest["sample_sha256"],
            "instructions_sha256": manifest["instructions_sha256"], "chunks": len(chunks),
            "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
            "features_sha256": sha256_file(Path(args.features))}  # fmt: skip


def cmd_hand_audit(args: argparse.Namespace) -> dict[str, Any]:
    """On the operator's Mac: the labeller's transcript audited with am3g's ``audit_transcript``
    (only Read of the two inputs and Write of the output, in the chunk's directory; the model; the
    pinned prompt; the agent id; every line after the launch time). Text-free."""

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    chunk = next(c for c in manifest["first"] if c["chunk"] == args.chunk)
    audit = g.audit_transcript(Path(args.transcript), chunk, launch="subagent",
                               chunk_dir=args.chunk_dir, agent_id=args.agent_id,
                               not_before=float(args.not_before))  # fmt: skip
    return {"chunk": args.chunk, "agent_id": args.agent_id, "launch": "subagent",
            "not_before_epoch": float(args.not_before), "audit": audit}  # fmt: skip


def cmd_hand_merge(args: argparse.Namespace) -> dict[str, Any]:
    """Host: the chunk outputs' valid rows (parse, name an item of the plan once, label 0 or 1;
    am3g's ``_valid_rows``) to the final labels file, once; text-free counts and digests."""

    hand_dir = Path(args.hand_dir)
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text(encoding="utf-8"))
    final = hand_dir / "hand-labels.jsonl"
    if final.exists():
        raise Am5Error("the labels were merged once already")
    allowed = set(manifest["items"])
    rows: dict[str, dict[str, Any]] = {}
    stats = []
    for chunk in manifest["first"]:
        path = hand_dir / chunk["output"]
        raw = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        valid, bad = g._valid_rows(raw, set(chunk["items"]) & allowed)
        rows.update(valid)
        stats.append({"chunk": chunk["chunk"], "output_present": path.is_file(),
                      "output_sha256": sha256_file(path) if path.is_file() else None,
                      "valid_rows": len(valid), **bad})  # fmt: skip
    ordered = [rows[i] for i in manifest["items"] if i in rows]
    tmp = final.with_name(final.name + ".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in ordered), "utf-8")
    os.replace(tmp, final)
    return {
        "items": len(manifest["items"]),
        "labelled": len(ordered),
        "missing": len(manifest["items"]) - len(ordered),
        "ones": sum(r["label"] for r in ordered),
        "chunks": stats,
        "labels_sha256": sha256_file(final),
        "plan_sha256": manifest["plan_sha256"],
    }


def read_hand_labels(path: Path, expected_sha256: str) -> dict[str, int]:
    if sha256_file(path) != expected_sha256:
        raise Am5Error("the hand labels differ from their receipted SHA-256")
    out: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["item_id"] in out or row["label"] not in (0, 1):
                raise Am5Error("a hand label is repeated or not 0 or 1")
            out[row["item_id"]] = int(row["label"])
    return out


# --------------------------------------------------------------------------- analysis


def rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = mc.clopper_pearson(k, n) if n else (None, None)
    return {"count": k, "n": n, "rate": (k / n) if n else None,
            "ci95_exact": [lo, hi] if n else None}  # fmt: skip


def ablated_block(
    records: Sequence[dict[str, Any]], caps: Sequence[int], hand_of: dict[tuple[str, str], int]
) -> dict[str, Any]:
    """One reader's ablated pools: (b) top 4 answers, (c) all 8 abstains and every 4-subset
    abstains, then per cap (a) the switch rate, the abstentions the rule keeps, the reads, and
    (d) the switched replies and non-abstaining top-4 replies judged correct and hand-labelled
    correct. ``hand_of`` maps (question id, reply digest) to the hand label."""

    n = len(records)
    top4_answers = [r for r in records if not r["bm25_top4_abstains"]]
    out: dict[str, Any] = {
        "pools": n,
        "bm25_top4_abstains": rate(n - len(top4_answers), n),
        "bm25_top4_answers": rate(len(top4_answers), n),
        "all_8_abstains": rate(sum(r["all_8_abstains"] for r in records), n),
        "every_4_subset_abstains": rate(
            sum(r["four_subset_abstain"] == FULL_ORDER for r in records), n
        ),  # fmt: skip
        "four_subset_replies_abstaining": rate(
            sum(r["four_subset_abstain"] for r in records), FULL_ORDER * n
        ),  # fmt: skip
        "top4_answers_judged_correct": sum(r["u"]["bm25_top4"] for r in top4_answers),
        "top4_answers_hand": _hand_counts(
            [
                (r["question_id"], r["digest"]["bm25_top4"], r["u"]["bm25_top4"])
                for r in top4_answers
            ],
            hand_of,
        ),  # fmt: skip
        "all_8_answers": sum(not r["all_8_abstains"] for r in records),
        "all_8_answers_judged_correct": sum(
            r["u"]["all_8"] for r in records if not r["all_8_abstains"]
        ),  # fmt: skip
        "caps": {},
    }
    for cap in caps:
        key = str(cap)
        switched = [r for r in records if r["caps"][key]["switched"]]
        kept = [r for r in records if r["bm25_top4_abstains"] and not r["caps"][key]["switched"]]
        hand = _hand_counts([(r["question_id"], r["caps"][key]["digest"], r["caps"][key]["u"])
                             for r in switched], hand_of)  # fmt: skip
        judged = sum(r["caps"][key]["u"] for r in switched)
        wrong_by_hand = (len(switched) - hand["hand_correct"]) if hand["complete"] else None
        out["caps"][key] = {
            "switch_rate": rate(len(switched), n),
            "switches_per_abstaining_top4": rate(len(switched), n - len(top4_answers)),
            "rule_keeps_an_abstention": rate(len(kept), n),
            "rule_answers": rate(len(switched) + len(top4_answers), n),
            "reads": ks.reads_summary([r["caps"][key]["reads"] for r in records]),
            "cap_reached_without_answer": sum(
                r["first_answer_position"] is None or r["first_answer_position"] > cap
                for r in records
            ),  # fmt: skip
            "switched_judged_correct": judged,
            "switched_hand": hand,
            "cost_judge": rate(len(switched) - judged, n),
            "cost_hand": rate(wrong_by_hand, n) if wrong_by_hand is not None else None,
            "switched_by_type": dict(
                sorted(Counter(r["question_type"] for r in switched).items())
            ),  # fmt: skip
        }
    return out


def _hand_counts(
    rows: Sequence[tuple[str, str, int]], hand_of: dict[tuple[str, str], int]
) -> dict[str, Any]:
    """Hand labels of (question, digest, judge label) rows: how many are labelled, judged
    correct, hand-labelled correct, and where the two disagree."""

    labelled = [(q, d, u, hand_of[(q, d)]) for q, d, u in rows if (q, d) in hand_of]
    return {"items": len(rows), "labelled": len(labelled), "complete": len(labelled) == len(rows),
            "hand_correct": sum(h for *_, h in labelled),
            "judge_yes_hand_no": sum(u == 1 and h == 0 for _, _, u, h in labelled),
            "judge_no_hand_yes": sum(u == 0 and h == 1 for _, _, u, h in labelled)}  # fmt: skip


def load_am3_records(config: dict[str, Any], root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    spec = config["analysis"]["am3_per_table"]
    path = root / spec["path"]
    if sha256_file(path) != spec["sha256"]:
        raise Am5Error("AM3's per-table records differ from their pin")
    return g.read_gz_json(path)


def original_block(records: Sequence[dict[str, Any]], caps: Sequence[int]) -> dict[str, Any]:
    """The same questions' original pools (AM3's committed per-pool records, retrieved arm,
    Qwen3-32B): (b) and (c) as above, and per cap (a) the switch rate and the rule's gain over
    BM25 top 4 (b gained, c lost), the capped choice being the rule's when its first answering
    position is at most K (AM4's crosscheck)."""

    n = len(records)
    out: dict[str, Any] = {
        "pools": n,
        "bm25_top4_abstains": rate(sum(r["bm25_top4_abstains"] for r in records), n),
        "bm25_top4_answers": rate(sum(not r["bm25_top4_abstains"] for r in records), n),
        "all_8_abstains": rate(sum(r["all_8_abstains"] for r in records), n),
        "every_4_subset_abstains": rate(
            sum(r["four_subset_abstain"] == FULL_ORDER for r in records), n
        ),  # fmt: skip
        "bm25_top4_correct": rate(sum(r["u"]["primary"]["bm25_top4"] for r in records), n),
        "caps": {},
    }
    for cap in caps:
        b = c = switched = switched_correct = 0
        for r in records:
            pos = r["first_answer_position"]
            moved = pos is not None and pos <= cap and r["nonabstain_mask"] != r["bm25_top4_mask"]
            u_top = int(r["u"]["primary"]["bm25_top4"])
            u_cap = int(r["u"]["primary"]["nonabstain_bm25"]) if moved else u_top
            switched += moved
            switched_correct += moved and u_cap == 1
            b += u_cap == 1 and u_top == 0
            c += u_cap == 0 and u_top == 1
        out["caps"][str(cap)] = {
            "switch_rate": rate(switched, n),
            "switched_judged_correct": switched_correct,
            "gained_b": b,
            "lost_c": c,
            "gain_per_question": (b - c) / n,
            "rule_correct": rate(sum(r["u"]["primary"]["bm25_top4"] for r in records) + b - c, n),
        }
    return out


def break_even(gain: float, loss: float) -> float | None:
    """am3g's break-even unanswerable share (``memcredit_am3g.break_even``)."""

    return g.break_even(gain, loss)


def analyze(
    features: dict[str, Any], config: dict[str, Any], hand_labels: dict[str, int] | None,
    hand_plan_sha256: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:  # fmt: skip
    caps = config["analysis"]["caps"]
    int_masks(features)
    recs = records_of(features, caps)
    plan = hand_plan(features, caps, int(config["hand_check"]["seed"]))
    hand_status = "absent"
    hand_of: dict[tuple[str, str], int] = {}
    if hand_labels is not None:
        if plan["plan_sha256"] != hand_plan_sha256:
            raise Am5Error("the hand plan differs from the receipted plan")
        by_id = {i["item_id"]: i for i in plan["items"]}
        if set(hand_labels) - set(by_id):
            raise Am5Error("a hand label names an item outside the plan")
        hand_status = "complete" if set(hand_labels) == set(by_id) else "incomplete"
        hand_of = {(by_id[i]["question_id"], by_id[i]["reply_digest"]): v
                   for i, v in hand_labels.items()}  # fmt: skip
    am3_rows = load_am3_records(config)
    ids = [q["question_id"] for q in features["readers"][READERS[0]]["pools"]]
    results: dict[str, Any] = {
        "experiment": EXPERIMENT,
        "claim": CLAIM,
        "population": POPULATION,
        "questions": features["questions"],
        "caps": caps,
        "judge": "Qwen3-32B (LongMemEval's non-abstention answer-check prompt)",
        "inputs": {
            "artifact_sha256": features["artifact_sha256"],
            "artifact_summary_sha256": features["artifact_summary_sha256"],
            "question_ids_sha256": features["question_ids_sha256"],
            "abstention_patterns_sha256": features["abstention_patterns_sha256"],
            "answer_templates_sha256": features["answer_templates_sha256"],
            "am3_per_table_sha256": config["analysis"]["am3_per_table"]["sha256"],
            "feature_code_sha256": features["code_sha256"],
        },
        "leakage": features["leakage"],
        "leakage_by_type": _leakage_by_type(features["leakage_per_question"]),
        "dev_retrieved_pool_check": features["dev_retrieved_pool_check"],
        "run": features["run"],
        "judge_validation": features["validation"]["judge_validation"],
        "readers": {},
        "hand_check": {"status": hand_status, "plan_sha256": plan["plan_sha256"],
                       "items": len(plan["items"]),
                       "labelled": len(hand_labels) if hand_labels is not None else 0,
                       "ones": sum(hand_labels.values()) if hand_labels else 0,
                       "uses_by_role": dict(sorted(Counter(
                           u["role"] for i in plan["items"] for u in i["uses"]).items()))},
    }  # fmt: skip
    items, agreement = labelled_items(features, plan, hand_labels)
    results["hand_check"]["agreement_with_the_judge"] = agreement
    results["labelled_items"] = items
    per_table: list[dict[str, Any]] = []
    for reader_id in READERS:
        rows = recs[reader_id]
        if [r["question_id"] for r in rows] != ids:
            raise Am5Error("readers' pools are not aligned")
        original = [r for r in am3_rows if r["reader"] == reader_id and r["arm"] == "retrieved"]
        by_q = {r["question_id"]: r for r in original}
        if sorted(by_q) != sorted(ids) or len(original) != len(ids):
            raise Am5Error(f"{reader_id}: AM3's records are not these questions")
        ablated = ablated_block(rows, caps, hand_of)
        orig = original_block([by_q[q] for q in ids], caps)
        side = {}
        for cap in caps:
            key = str(cap)
            gain = orig["caps"][key]["gain_per_question"]
            loss_j = ablated["caps"][key]["cost_judge"]["rate"]
            cost_h = ablated["caps"][key]["cost_hand"]
            loss_h = cost_h["rate"] if cost_h else None
            side[key] = {"gain_per_question_original": gain,
                         "cost_per_question_ablated_judge": loss_j,
                         "cost_per_question_ablated_hand": loss_h,
                         "break_even_share_judge": break_even(gain, loss_j),
                         "break_even_share_hand": (break_even(gain, loss_h)
                                                   if loss_h is not None else None),
                         "switched_on_both": sum(
                             rows[i]["caps"][key]["switched"]
                             and (by_q[q]["first_answer_position"] or 99) <= cap
                             and by_q[q]["nonabstain_mask"] != by_q[q]["bm25_top4_mask"]
                             for i, q in enumerate(ids))}  # fmt: skip
        reader = features["readers"][reader_id]
        results["readers"][reader_id] = {
            "step": reader["step"],
            "batch_invariant": reader["batch_invariant"],
            "finish": reader["finish"],
            "ablated": ablated,
            "original": orig,
            "side_by_side": side,
            "abstention_patterns": dict(sorted(Counter(
                str(c["pattern"]) for p in reader["pools"] for c in p["masks"].values()
                if c["abstain"]).items())),
        }  # fmt: skip
        for r in rows:
            per_table.append({"reader": reader_id, **{k: v for k, v in r.items()
                                                      if k != "digest"},
                              "caps": {k: {kk: vv for kk, vv in v.items() if kk != "digest"}
                                       for k, v in r["caps"].items()}})  # fmt: skip
    return results, per_table


#: The per-question leakage facts reported beside each labelled reply.
ITEM_FACTS = (
    "pool_memories_containing_the_answer",
    "remaining_user_turns_containing_the_answer",
    "answer_normalized_tokens",
    "memories_shared_with_the_original_pool",
    "original_pool_has_answer_memories",
)


def labelled_items(
    features: dict[str, Any], plan: dict[str, Any], hand_labels: dict[str, int] | None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Per hand-plan item (text-free): its question, uses (reader, role, mask, first answering
    position), the primary judge's label of the reply, the hand label, and the question's leakage
    facts; and hand-against-judge agreement over the labelled items (counts and Cohen's kappa)."""

    facts = {f["question_id"]: f for f in features["leakage_per_question"]}
    pools = {(r, p["question_id"]): p for r in READERS for p in features["readers"][r]["pools"]}
    out, pairs = [], []
    for item in plan["items"]:
        judged = sorted({int(pools[(u["reader"], item["question_id"])]["masks"][int(u["mask"])]
                             ["u"][JUDGE]) for u in item["uses"]})  # fmt: skip
        if len(judged) != 1:
            raise Am5Error(f"{item['item_id']}: one reply digest with two judge labels")
        hand = hand_labels.get(item["item_id"]) if hand_labels is not None else None
        q = facts[item["question_id"]]
        out.append({"item_id": item["item_id"], "question_id": item["question_id"],
                    "question_type": q["question_type"], "uses": item["uses"],
                    "judge": judged[0], "hand": hand,
                    "facts": {k: q[k] for k in ITEM_FACTS}})  # fmt: skip
        if hand is not None:
            pairs.append((judged[0], hand))
    agree = sum(a == b for a, b in pairs)
    agreement = {"items": len(pairs), "agree": agree,
                 "judge_yes_hand_no": sum(a == 1 and b == 0 for a, b in pairs),
                 "judge_no_hand_yes": sum(a == 0 and b == 1 for a, b in pairs),
                 "kappa": ms.cohen_kappa([a for a, _ in pairs], [b for _, b in pairs])
                 if pairs else None}  # fmt: skip
    return out, agreement


def _leakage_by_type(facts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for qtype in sorted({f["question_type"] for f in facts}):
        rows = [f for f in facts if f["question_type"] == qtype]
        out[qtype] = {
            "questions": len(rows),
            "pools_with_a_has_answer_memory": sum(f["pool_has_answer_memories"] > 0 for f in rows),
            "pools_with_a_memory_containing_the_answer": sum(
                f["pool_memories_containing_the_answer"] > 0 for f in rows),
            "questions_whose_remaining_user_turns_contain_the_answer": sum(
                f["remaining_user_turns_containing_the_answer"] > 0 for f in rows),
        }  # fmt: skip
    return out


# --------------------------------------------------------------------------- tables


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _r(cell: dict[str, Any] | None) -> str:
    if not cell or cell["count"] is None:
        return "n/a"
    lo, hi = cell["ci95_exact"]
    return f"{cell['count']}/{cell['n']} ({cell['rate']:.3f} [{lo:.3f}, {hi:.3f}])"


def render_markdown(results: dict[str, Any]) -> str:
    caps = [str(c) for c in results["caps"]]
    lines = [
        "# AM5: the non-abstention rule's cost when the evidence is absent (tables)",
        "",
        f"**{results['claim']}**",
        "",
        "Counts over the 63 development questions per reader. Ablated: evidence sessions removed. "
        "Original: AM3's committed records of the same questions' pools (retrieved arm). Rates "
        "with exact 95% Clopper-Pearson intervals. Judge: Qwen3-32B with LongMemEval's "
        "non-abstention answer-check prompt. Hand: one blind isolated agent (D9: agent labels).",
        "",
        "## Ablated pools: (a) switch rate, (b) top 4 answers, (c) whole pool abstains",
        "",
        "| Reader | K | (a) switch rate | (b) BM25 top 4 does not abstain | (c) all 8 abstains | "
        "every 4-subset abstains | rule keeps an abstention | mean reads |",
        "|---|---:|---|---|---|---|---|---:|",
    ]
    for reader, d in results["readers"].items():
        a = d["ablated"]
        for cap in caps:
            c = a["caps"][cap]
            lines.append(
                f"| {reader} | {cap} | {_r(c['switch_rate'])} | {_r(a['bm25_top4_answers'])} | "
                f"{_r(a['all_8_abstains'])} | {_r(a['every_4_subset_abstains'])} | "
                f"{_r(c['rule_keeps_an_abstention'])} | {_f(c['reads']['mean'], 2)} |"
            )
    lines += [
        "",
        "## Ablated pools: (d) answers correct by chance",
        "",
        "Switched: the rule's reply where BM25 top 4 abstains and a 4-subset answers within K "
        "reads. Top-4 answers: BM25 top 4's reply where it does not abstain. Judged: Qwen3-32B "
        "yes. Hand: the blind agent's 1. Cost: switched replies not correct (judge; hand).",
        "",
        "| Reader | K | switched | judged correct | hand correct (labelled) | judge yes, hand no | "
        "judge no, hand yes | cost, judge | cost, hand |",
        "|---|---:|---:|---:|---|---:|---:|---|---|",
    ]
    for reader, d in results["readers"].items():
        a = d["ablated"]
        for cap in caps:
            c = a["caps"][cap]
            h = c["switched_hand"]
            lines.append(
                f"| {reader} | {cap} | {c['switch_rate']['count']} | "
                f"{c['switched_judged_correct']} | {h['hand_correct']} ({h['labelled']} of "
                f"{h['items']}) | {h['judge_yes_hand_no']} | {h['judge_no_hand_yes']} | "
                f"{_r(c['cost_judge'])} | {_r(c['cost_hand'])} |"
            )
    lines += [
        "",
        "| Reader | top-4 answers | judged correct | hand correct (labelled) | all-8 answers | "
        "all-8 answers judged correct |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for reader, d in results["readers"].items():
        a = d["ablated"]
        h = a["top4_answers_hand"]
        lines.append(
            f"| {reader} | {a['bm25_top4_answers']['count']} | {a['top4_answers_judged_correct']} "
            f"| {h['hand_correct']} ({h['labelled']} of {h['items']}) | {a['all_8_answers']} | "
            f"{a['all_8_answers_judged_correct']} |"
        )
    lines += [
        "",
        "## The same questions' original pools (AM3's committed records, retrieved arm)",
        "",
        "| Reader | K | switch rate | BM25 top 4 does not abstain | all 8 abstains | every "
        "4-subset abstains | gained b | lost c | gain per question | BM25 top 4 correct | rule "
        "correct |",
        "|---|---:|---|---|---|---|---:|---:|---:|---|---|",
    ]
    for reader, d in results["readers"].items():
        o = d["original"]
        for cap in caps:
            c = o["caps"][cap]
            lines.append(
                f"| {reader} | {cap} | {_r(c['switch_rate'])} | {_r(o['bm25_top4_answers'])} | "
                f"{_r(o['all_8_abstains'])} | {_r(o['every_4_subset_abstains'])} | "
                f"{c['gained_b']} | {c['lost_c']} | {c['gain_per_question']:+.3f} | "
                f"{_r(o['bm25_top4_correct'])} | {_r(c['rule_correct'])} |"
            )
    lines += [
        "",
        "## Side by side (descriptive)",
        "",
        "Gain per question on the original pools against the cost per question on the ablated "
        "pools of the same 63 questions; the break-even share is am3g's g/(g + l), the share of "
        "evidence-absent questions above which BM25 top 4 is ahead, if deployment's "
        "unanswerable questions looked like these.",
        "",
        "| Reader | K | gain, original | cost, ablated (judge) | cost, ablated (hand) | "
        "break-even (judge) | break-even (hand) | switched on both |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for reader, d in results["readers"].items():
        for cap in caps:
            s = d["side_by_side"][cap]
            lines.append(
                f"| {reader} | {cap} | {s['gain_per_question_original']:+.3f} | "
                f"{_f(s['cost_per_question_ablated_judge'])} | "
                f"{_f(s['cost_per_question_ablated_hand'])} | {_f(s['break_even_share_judge'], 2)}"
                f" | {_f(s['break_even_share_hand'], 2)} | {s['switched_on_both']} |"
            )
    leak = results["leakage"]
    lines += ["", "## (e) Leakage", "", "| Check | Count |", "|---|---:|"]
    lines += [f"| {k.replace('_', ' ')} | {v} |" for k, v in leak.items()]
    lines += ["", "| Type | questions | pools with a has_answer memory | pools with a memory "
              "containing the answer | questions whose remaining user turns contain the answer |",
              "|---|---:|---:|---:|---:|"]  # fmt: skip
    for qtype, v in results["leakage_by_type"].items():
        lines.append(
            f"| {qtype} | {v['questions']} | {v['pools_with_a_has_answer_memory']} | "
            f"{v['pools_with_a_memory_containing_the_answer']} | "
            f"{v['questions_whose_remaining_user_turns_contain_the_answer']} |"
        )
    v = results["judge_validation"]
    lines += [
        "",
        "## Judge validation (AM1's items on these 63 questions)",
        "",
        "| Item | items | judged yes |",
        "|---|---:|---:|",
    ]
    lines += [f"| {k} | {x['items']} | {x['yes']} |" for k, x in sorted(v.items())]
    hc = results["hand_check"]
    ag = hc["agreement_with_the_judge"]
    kappa = "n/a" if ag["kappa"] is None else f"{ag['kappa']:.2f}"
    lines += ["", "## Hand check", "", f"Status: {hc['status']}; {hc['labelled']} of "
              f"{hc['items']} items labelled, {hc['ones']} labelled correct; plan "
              f"`{hc['plan_sha256'][:16]}...`. Hand against judge: {ag['agree']} of {ag['items']} "
              f"agree (judge yes, hand no {ag['judge_yes_hand_no']}; judge no, hand yes "
              f"{ag['judge_no_hand_yes']}; kappa {kappa}).", "",
              "Replies judged or hand-labelled correct, with their question's leakage facts "
              "(answer in a pool memory; answer in a remaining user turn; answer tokens; memories "
              "shared with the original pool; has_answer memories in the original pool):", "",
              "| Item | question | type | uses | judge | hand | answer in pool | answer in "
              "remaining turns | answer tokens | shared memories | original has_answer |",
              "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for it in results["labelled_items"]:
        if not (it["judge"] or it["hand"]):
            continue
        uses = "; ".join(f"{u['reader']} {u['role']}" for u in it["uses"])
        f = it["facts"]
        lines.append(f"| {it['item_id']} | {it['question_id']} | {it['question_type']} | {uses} | "
                     f"{it['judge']} | {it['hand']} | {f['pool_memories_containing_the_answer']} | "
                     f"{f['remaining_user_turns_containing_the_answer']} | "
                     f"{f['answer_normalized_tokens']} | "
                     f"{f['memories_shared_with_the_original_pool']} | "
                     f"{f['original_pool_has_answer_memories']} |")  # fmt: skip
    lines.append("")
    return "\n".join(lines)


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    features = g.read_gz_json(Path(args.features))
    check_features(features, config)
    labels = None
    if args.hand_labels:
        if not (args.hand_labels_sha256 and args.hand_plan_sha256):
            raise Am5Error("the hand labels need their receipted label and plan digests")
        labels = read_hand_labels(Path(args.hand_labels), args.hand_labels_sha256)
    results, per_table = analyze(features, config, labels, args.hand_plan_sha256)
    results["inputs"]["features_sha256"] = sha256_file(Path(args.features))
    results["inputs"]["hand_labels_sha256"] = args.hand_labels_sha256
    out = Path(args.output_dir)
    if out.exists():
        raise Am5Error(f"{out} exists: analyze writes a new directory")
    out.mkdir(parents=True)
    (out / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    g.write_gz_json(out / "per-table.json.gz", per_table)
    (out / "tables.md").write_text(render_markdown(results) + "\n", encoding="utf-8")
    return {k: sha256_file(out / k) for k in ("results.json", "per-table.json.gz", "tables.md")}


# --------------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", allow_abbrev=False)
    prep.add_argument("--source", required=True)
    prep.add_argument("--split-file", required=True)
    prep.add_argument("--dev-artifact", required=True)
    prep.add_argument("--artifact", required=True)
    prep.add_argument("--summary", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--evidence", required=True)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(am3.MODEL_ROOT))
    selftest.add_argument("--evidence", required=True)
    selftest.add_argument("--expected-evidence-sha256", default=None)
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--evidence", required=True)
    run.add_argument("--expected-evidence-sha256", required=True)
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--step", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--evidence", required=True)
    worker.add_argument("--expected-evidence-sha256", required=True)
    extract = sub.add_parser("extract", allow_abbrev=False)
    extract.add_argument("--run-dir", required=True)
    extract.add_argument("--evidence", required=True)
    extract.add_argument("--summary", required=True)
    extract.add_argument("--private-dir", required=True)
    hand = sub.add_parser("hand-sample", allow_abbrev=False)
    hand.add_argument("--run-dir", required=True)
    hand.add_argument("--evidence", required=True)
    hand.add_argument("--features", required=True)
    hand.add_argument("--hand-dir", required=True)
    audit = sub.add_parser("hand-audit", allow_abbrev=False)
    audit.add_argument("--manifest", required=True)
    audit.add_argument("--chunk", required=True)
    audit.add_argument("--chunk-dir", required=True)
    audit.add_argument("--transcript", required=True)
    audit.add_argument("--agent-id", required=True)
    audit.add_argument("--not-before", required=True)
    merge = sub.add_parser("hand-merge", allow_abbrev=False)
    merge.add_argument("--hand-dir", required=True)
    analyze_p = sub.add_parser("analyze", allow_abbrev=False)
    analyze_p.add_argument("--features", required=True)
    analyze_p.add_argument("--hand-labels", default=None)
    analyze_p.add_argument("--hand-labels-sha256", default=None)
    analyze_p.add_argument("--hand-plan-sha256", default=None)
    analyze_p.add_argument("--output-dir", required=True)
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            config = load_config(Path(args.config))
            artifact = load_artifact(config, args.evidence)
            print(json.dumps(build_plan(config, artifact), indent=2))
            return 0
        if args.command == "selftest":
            return selftest_main(args)
        if args.command == "run":
            return run_main(args)
        if args.command == "worker":
            return vllm_worker(args)
        commands = {
            "prepare": cmd_prepare,
            "extract": cmd_extract,
            "hand-sample": cmd_hand_sample,
            "hand-audit": cmd_hand_audit,
            "hand-merge": cmd_hand_merge,
            "analyze": cmd_analyze,
        }
        print(json.dumps(commands[args.command](args), indent=2, sort_keys=True))
        return 0
    except (Am5Error, g.Am3gError, am3.Am3Error, ms.StudyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as exc:
        if args.command in ("run", "worker"):
            raise
        print(f"error: an input is missing or unreadable: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
