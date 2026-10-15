#!/usr/bin/env python3
"""am5-ablated-cost-v1 (D121): is the non-abstention keep rule's cost on questions whose evidence
is absent below its gain on the same questions with their evidence?

The rule (AM1d's ``nonabstain@70``, H-C of ``am1-keepset-search-v1``, confirmed for three readers
by ``am3-nonabstain-generality-v1``) reads a pool's 70 4-subsets in BM25 order and keeps the first
whose reply does not abstain (AM1d's four patterns, digest ``031bee27...``), within a read cap K
(AM4's definition); otherwise it keeps BM25 top 4. AM4 measured its gain at every K on AM1's 347
held-out questions (post hoc). AM5 measured its cost on the 63 development questions with their
evidence sessions removed (exploratory). This registration measures the cost on the 347 held-out
questions with their evidence removed and compares it, question by question, with the gain the
same questions' original pools gave:

* Population. Each held-out question's evidence sessions (LongMemEval's ``answer_session_ids``)
  are removed from its haystack and the BM25 top-8 user-turn pool is built from the rest with
  AM1's retrieved-arm functions (``prepare-heldout``, host CPU, before the freeze). AM5's 63
  development ablated pools ride along in the same job as a replay control (V3).
* Readers. Qwen3-8B (eager, batch-invariant), OLMo-2-1124-7B-Instruct (batch-invariant) and
  Qwen3.5-9B (default mode), am3g's revisions and engines, AM1's prompt; 71 requests per pool; the
  Qwen3-32B judge with LongMemEval's answer-check prompt on every distinct (question, reply).
* Outcome on an ablated pool. A reply is correct when it abstains (AM1d's patterns) or, when it
  does not, when the judge says it matches the reference answer. The cost indicator of a question
  is 1 when the capped rule's reply is wrong and BM25 top 4's is correct, which happens exactly
  when the rule switches away from an abstaining top 4 to a reply the judge rejects.
* Primary, per reader: the cost rate at K = 8 against the K = 8 gain rate of the same 347
  questions' original pools (``am3-nonabstain-generality-v1``'s committed per-pool records, read as
  AM4 reads them): paired by question, exact McNemar on (cost only, gain only), Holm across the
  three readers at 0.05: COST_BELOW_GAIN, COST_ABOVE_GAIN or NOT_SEPARATED, a directional reading
  standing only if a blind hand check agrees. Secondary: K = 70. The break-even evidence-absent
  share gain / (gain + cost) with a question-cluster bootstrap.

Subcommands (POP is ``development`` or ``heldout``):

* ``prepare-heldout`` (host CPU, before the freeze): the ablated held-out artifact with the replay
  control appended (pool texts; host only) and its text-free summary.
* ``plan --population POP --evidence A``; ``selftest --population POP --evidence A`` (CPU, no
  engine: tokenizers only, no model output).
* ``run --population POP --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the GPU job, one H100. ``worker``: one step.
* ``extract --population POP --run-dir R --evidence A --summary P --private-dir P
  --reference-run-dir REF`` (host; reads replies): text-free features, the replay checks against
  AM5's job 1487.
* ``hand-sample``, ``hand-merge`` (host): the blind hand check, am3g's protocol.
* ``analyze --population POP --features F --hand-labels L --hand-labels-sha256 S
  --hand-plan-sha256 P --output-dir O`` (CPU): text-free ``results.json``, ``per-table.json.gz``,
  ``tables.md``.
* ``dryrun-compare --features F --am5-features A --am5-hand-labels L --output-dir O``: the
  development dry run against AM5's committed outputs.
* ``power --output P``: the operating characteristics (committed inputs only).
* ``rerun-decision --population POP --job-dir J``: am3g's mechanical rerun rule.

The held-out population is refused before the freeze (``gate``) by every command that runs a
model on it or reads its outputs; ``prepare-heldout``, ``plan`` and the tokenizer-only
``selftest`` produce no model output and run before it.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
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

import memcredit_am3 as am3  # noqa: E402  (engine helpers, rule, per-pool helpers)
import memcredit_am3g as g  # noqa: E402  (readers, steps, pools, judge, hand-check protocol)
import memcredit_am5 as a5  # noqa: E402  (ablation, capped rule, per-pool records and blocks)
import memcredit_keepset_search as ks  # noqa: E402  (McNemar, paired readings, ledger, pins)
import memcredit_label_free as lf  # noqa: E402  (abstention patterns, BM25 order)
import memcredit_step0 as s0  # noqa: E402  (engine streaming, pass files, GPU sampler)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am5-ablated-cost-v1"
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am5" / "am5-ablated-cost-v1.yaml"
REGISTRATION = Path("program/preregistrations/am5-ablated-cost-v1.md")
LEDGER = Path("program/preregistrations/ledger.jsonl")
POPULATIONS = ("development", "heldout")
#: Which populations open only after the freeze. A code property, so no config edit can lift it.
GATED = {"development": False, "heldout": True}
ARMS = ("retrieved",)
READERS = g.H2_READERS
ANCHOR = g.ANCHOR
JUDGE = "primary"
JUDGE_STEP = "judge32"
STEP_IDS = ("rd-qwen3-8b", "rd-olmo2", "rd-olmo2-default", "rd-qwen35-9b-default", JUDGE_STEP)
CAPS = (8, 70)
PRIMARY_CAP = 8
SECONDARY_CAP = 70
FULL = g.FULL
FOUR_SETS = g.FOUR_SETS
REQUEST_MASKS = g.REQUEST_MASKS
N_REQUESTS = len(REQUEST_MASKS)
#: The GPU job's output directory inside the lane (``/outputs/am5r``; on the host
#: ``R/runs/POP/JOB/am5r``).
OUTPUT = "am5r"
ALPHA = 0.05
COST_ABOVE, COST_BELOW, NOT_SEPARATED = "COST_ABOVE_GAIN", "COST_BELOW_GAIN", "NOT_SEPARATED"
#: ``ks.paired_reading`` labels (rule := cost indicator, base := gain indicator): its first label
#: is "rule above base".
PAIRED_LABELS = (COST_ABOVE, COST_BELOW, NOT_SEPARATED)
DIRECTIONAL = (COST_ABOVE, COST_BELOW)
SPLITS = {"development": "dev-ablated", "heldout": "heldout-ablated"}
#: Path parts the development dry run never opens (held-out data, its runs and artifacts).
FORBIDDEN_DEV_PARTS = (
    "am1-confirmatory",
    "am1-memory-credit-v1",
    "am1-keepset-search-v1",
    "am3-nonabstain-generality-v1",
    "am5-ablated-cost-v1",
    "heldout-ablated",
)
VOID_DIGEST = g.VOID_DIGEST
VOID_INCOMPLETE = g.VOID_INCOMPLETE
VOID_REPLAY = "VOID (V3, the replay control failed)"
#: The code whose SHA-256 the features record and ``analyze`` checks: AM5's closure (am3g's plus
#: memcredit_am5.py) and this script; a test checks it against a fresh interpreter.
FEATURE_CODE = (*a5.FEATURE_CODE, "scripts/memcredit_am5r.py")
SMOKE_REQUESTS = g.SMOKE_REQUESTS
SMOKE_FAILED_EXIT = g.SMOKE_FAILED_EXIT
PREFERENCE = "single-session-preference"

#: The blind labeller's instructions (registration section 8). Every item is a reply that does not
#: abstain by AM1d's patterns, on a pool that may lack the evidence: it is correct when it gives
#: the reference answer or declines to answer, and wrong when it gives another answer.
HAND_INSTRUCTIONS = """Blind hand check, am5-ablated-cost-v1 (D9: agent labels).

Each line of the sample is one item: a LongMemEval-S question, its question type, the check
"answer-or-decline", the question's reference answer (for single-session-preference, a rubric)
and a reply written by a language model that was given some of the user's past messages. Those
messages may or may not hold the information the question needs. Label every item, independently
of the others.

- 1 if the reply gives the reference answer: it contains the reference answer, or is equivalent
  to it, or contains all the intermediate steps to reach it.
  - temporal-reasoning: do not penalise an off-by-one error in a number of days, weeks or months.
  - knowledge-update: a reply that mentions earlier information along with the updated answer is
    correct as long as the updated answer is the one required.
  - single-session-preference: 1 if the reply satisfies the rubric, recalling and using the
    user's personal information correctly; it need not cover every point.
- 1 also if the reply declines to answer and gives no answer: it says that it does not know, that
  the messages do not say, that the information is missing or not enough, or it asks for the
  missing information. When you give a 1 for this reason, the note must start with "decline:".
- 0 if the reply gives an answer that is not the reference answer: a different answer, a guess,
  only part of the information the answer needs, or alternatives none of which is the reference
  answer. A reply that declines and then still offers an answer is labelled by that answer.

Use only the question, the check, the reference text and the reply. Do not look for, open or
infer any other file, label or result. Write one JSON object per line, in the sample's order:
{"item_id": "...", "label": 1 or 0, "note": "short"}. A note for a 1 given because the reply
declines starts with decline: (for example "decline: says the messages do not say").
"""
HAND_CHECK = "answer-or-decline"
#: The note prefix that marks a 1 given for a decline (registration section 8).
DECLINE_NOTE = "decline:"
#: Item roles of the hand plan (registration section 8).
ROLE_RIGHT = "switched-judged-correct"
ROLE_WRONG_PRIMARY = "switched-judged-wrong-primary"
ROLE_WRONG_SECONDARY = "switched-judged-wrong-secondary"
ROLE_TOP4 = "top4-answers"
ROLE_DISTRACTOR = "distractor"


class Am5rError(ValueError):
    """The config, an input, a gate or a void rule failed."""


sha256_bytes = g.sha256_bytes
sha256_text = g.sha256_text
sha256_file = g.sha256_file
ids_sha256 = g.ids_sha256
write_gz_json = g.write_gz_json
read_gz_json = g.read_gz_json


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and not set(value) - set("0123456789abcdef")


def code_digests(root: Path = PROJECT_ROOT) -> dict[str, str]:
    return {path: sha256_file(root / path) for path in FEATURE_CODE}


def check_dev_path(path: Path | str | None) -> None:
    """The development dry run never opens held-out inputs (symlinks resolved)."""

    if path is None:
        return
    texts = [str(path)]
    with contextlib.suppress(OSError):
        texts.append(str(Path(path).resolve()))
    for text in texts:
        for part in FORBIDDEN_DEV_PARTS:
            if part in text:
                raise Am5rError(f"the development population refuses {path}")


def refuse_inside_repo(path: Path | str) -> None:
    if Path(path).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        raise Am5rError(f"{path} is inside the repository; host-only files stay outside it")


# --------------------------------------------------------------------------- the gate


def gate(
    population: str,
    ledger: Path | None = None,
    registration: Path | None = None,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Run before any held-out output is produced or read: the ledger must hold a row for this
    experiment with the registration file's SHA-256, and every code pin of its section 16 must
    match the working tree. The development population needs neither. Tests pass scratch copies."""

    if population not in POPULATIONS:
        raise Am5rError(f"unknown population {population}")
    if not GATED[population]:
        return {"population": population, "frozen_required": False}
    ledger = ledger or root / LEDGER
    registration = registration or root / REGISTRATION
    if not ks.registration_frozen(ledger, registration, EXPERIMENT):
        raise Am5rError(
            f"the {population} population opens only after the freeze: no ledger row for "
            f"{EXPERIMENT} with this registration file's SHA-256"
        )
    try:
        pins = ks.check_code_pins(registration, root)
    except ks.KeepsetError as exc:
        raise Am5rError(f"{VOID_DIGEST}: {exc}") from exc
    return {"population": population, "frozen_required": True, "registration_frozen": True,
            "code_pins": pins}  # fmt: skip


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """This registration's config merged onto the frozen am3g config (validated by
    ``memcredit_am3g.load_config``): the readers, models, reader sampling, pilot pins and the
    listed steps come from it unchanged."""

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("experiment_id") != EXPERIMENT:
        raise Am5rError(f"not the {EXPERIMENT} config")
    if raw.get("claim_level") != "confirmatory":
        raise Am5rError("the registration's config is confirmatory")
    if raw.get("seeds") != [42, 43, 44]:
        raise Am5rError("seeds must be [42, 43, 44]")
    base_path = PROJECT_ROOT / raw["base"]["config"]
    if sha256_file(base_path) != raw["base"]["config_sha256"]:
        raise Am5rError("the am3g config differs from its pinned SHA-256")
    base = g.load_config(base_path)
    by_id = {s["id"]: s for s in base["steps"]}
    if tuple(raw["steps"]) != STEP_IDS:
        raise Am5rError(f"steps: {list(STEP_IDS)}, am3g's, in order (no second judge)")
    steps = [by_id[i] for i in raw["steps"]]
    pops = raw["populations"]
    if sorted(pops) != sorted(POPULATIONS):
        raise Am5rError("populations: development, heldout")
    for name, spec in pops.items():
        if tuple(spec.get("arms", ())) != ARMS:
            raise Am5rError(f"populations.{name}: the retrieved arm only")
        if spec.get("split") != SPLITS[name]:
            raise Am5rError(f"populations.{name}.split must be {SPLITS[name]}")
        if not _is_digest(spec.get("question_ids_sha256")):
            raise Am5rError(f"populations.{name}.question_ids_sha256 must be a SHA-256")
        if not isinstance(spec.get("questions"), int) or spec["questions"] < 1:
            raise Am5rError(f"populations.{name}.questions must be a positive integer")
        for key in ("artifact_sha256", "summary_sha256"):
            if not _is_digest(spec.get(key)):
                raise Am5rError(f"populations.{name}.{key} must be a SHA-256")
        ref = spec.get("reference") or {}
        if sorted(ref.get("readers", {})) != sorted(READERS) or not ref.get("sha256"):
            raise Am5rError(f"populations.{name}.reference: job 1487's three reader passes")
        if any(not _is_digest(v) for v in ref["sha256"].values()):
            raise Am5rError(f"populations.{name}.reference.sha256: SHA-256 values")
        gain = spec.get("gain") or {}
        if not _is_digest(gain.get("sha256")) or sorted(gain.get("expected", {})) != sorted(
            str(c) for c in CAPS
        ):
            raise Am5rError(f"populations.{name}.gain: a pinned per-table and its counts per cap")
    dev, held = pops["development"], pops["heldout"]
    if held["reference"] != dev["reference"]:
        raise Am5rError("the replay control's reference is the development dry run's (job 1487)")
    control = held.get("control") or {}
    if (control.get("artifact_sha256") != dev["artifact_sha256"]
            or control.get("question_ids_sha256") != dev["question_ids_sha256"]
            or control.get("questions") != dev["questions"]):  # fmt: skip
        raise Am5rError("the replay control is the development population, unchanged")
    if not _is_digest(held.get("source_artifact_sha256")):
        raise Am5rError("the held-out ids and order come from AM1's pinned held-out artifact")
    jobs = raw["jobs"]
    if sorted(jobs) != sorted(POPULATIONS):
        raise Am5rError("one job per population")
    for name, job in jobs.items():
        if int(job["gpus"]) != 1:
            raise Am5rError(f"jobs.{name}: one GPU")
        budgets = job["step_budgets"]
        if sorted(budgets) != sorted(STEP_IDS):
            raise Am5rError(f"jobs.{name}: a budget for every step")
        for sid, (min_start, max_s) in budgets.items():
            if not 0 < int(max_s) < int(min_start) < int(job["minutes"]) * 60:
                raise Am5rError(f"jobs.{name}.{sid}: 0 < max_s < min_start_s < the limit")
    analysis = raw["analysis"]
    if [int(c) for c in analysis["caps"]] != list(CAPS) or int(analysis["primary_cap"]) != 8:
        raise Am5rError("caps [8, 70], primary 8")
    if float(analysis["alpha"]) != ALPHA:
        raise Am5rError("alpha 0.05")
    hand = raw["hand_check"]
    if int(hand["chunk"]) != g.HAND_CHUNK or hand["labeller_model"] != g.HAND_LABELLER_MODEL:
        raise Am5rError("the hand check is am3g's: chunks of 60, the pinned labeller model")
    if int(hand["seed"]) not in raw["seeds"] or not 0 < float(hand["secondary_fraction"]) <= 1:
        raise Am5rError("hand_check: a declared seed and a sampling fraction in (0, 1]")
    return {
        "experiment_id": EXPERIMENT,
        "claim_level": "confirmatory",
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
        "populations": pops,
        "jobs": jobs,
        "budget": raw["budget"],
        "analysis": analysis,
        "hand_check": hand,
    }


def population_spec(config: dict[str, Any], population: str) -> dict[str, Any]:
    if population not in POPULATIONS:
        raise Am5rError(f"unknown population {population}")
    return config["populations"][population]


def artifact_pin(config: dict[str, Any], population: str) -> str:
    pin = population_spec(config, population)["artifact_sha256"]
    if not _is_digest(pin):
        raise Am5rError(f"the {population} artifact is not pinned")
    return pin


def step_budget(config: dict[str, Any], population: str, step_id: str) -> tuple[int, int]:
    min_start, max_s = config["jobs"][population]["step_budgets"][step_id]
    return int(min_start), int(max_s)


# --------------------------------------------------------------------------- artifacts


def parts_of(config: dict[str, Any], population: str) -> dict[str, range]:
    """The question ranges of the population's artifact: the development population is one part;
    the held-out artifact holds the 347 ablated held-out questions, then the 63 control ones."""

    spec = population_spec(config, population)
    n = int(spec["questions"])
    if population == "development":
        return {"main": range(0, n)}
    m = int(spec["control"]["questions"])
    return {"main": range(0, n), "control": range(n, n + m)}


def control_range(config: dict[str, Any], population: str) -> range:
    """The questions replayed against job 1487: the control part, or the whole development
    population (the dry run replays all of AM5's requests)."""

    parts = parts_of(config, population)
    return parts.get("control", parts["main"])


def load_artifact(
    config: dict[str, Any], population: str, path: Path | str, expected_sha256: str | None = None
) -> dict[str, Any]:
    """The population's pinned artifact (the caller runs the gate first where it applies)."""

    if population == "development":
        check_dev_path(path)
    raw = Path(path).read_bytes()
    digest = sha256_bytes(raw)
    if digest != artifact_pin(config, population):
        raise Am5rError(f"{VOID_DIGEST}: the {population} artifact {path} is not the pinned one")
    if expected_sha256 is not None and digest != expected_sha256:
        raise Am5rError(f"{VOID_DIGEST}: the {population} artifact differs from the expected SHA")
    artifact = json.loads(raw)
    check_artifact(config, population, artifact)
    return artifact


def check_artifact(config: dict[str, Any], population: str, artifact: dict[str, Any]) -> None:
    spec = population_spec(config, population)
    wanted = ("am5-evidence-ablated-dev", "dev-ablated") if population == "development" else (
        EXPERIMENT, "heldout-ablated")  # fmt: skip
    if (artifact.get("experiment_id"), artifact.get("split")) != wanted:
        raise Am5rError(f"{VOID_DIGEST}: not the {population} population's artifact")
    parts = parts_of(config, population)
    questions = artifact["questions"]
    if len(questions) != sum(len(r) for r in parts.values()):
        raise Am5rError(f"{VOID_DIGEST}: the {population} artifact has {len(questions)} questions")
    ids = [q["question_id"] for q in questions]
    main = parts["main"]
    if ids_sha256(ids[main.start : main.stop]) != spec["question_ids_sha256"]:
        raise Am5rError(f"{VOID_DIGEST}: the {population} question ids differ from their pin")
    if "control" in parts:
        ctrl = parts["control"]
        if ids_sha256(ids[ctrl.start : ctrl.stop]) != spec["control"]["question_ids_sha256"]:
            raise Am5rError(f"{VOID_DIGEST}: the control question ids differ from their pin")
        if artifact.get("parts") != {k: [r.start, r.stop] for k, r in parts.items()}:
            raise Am5rError(f"{VOID_DIGEST}: the artifact's parts differ from the config's")
    for q in questions:
        if mc.is_abstention(q) or q.get("abstention"):
            raise Am5rError(f"{q['question_id']}: no abstention question here")
        if len(q["pools"]["retrieved"]) != g.K:
            raise Am5rError(f"{q['question_id']}: not a pool of {g.K}")


def ablated_question(
    record: dict[str, Any], pool_config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One question with its evidence sessions removed (``memcredit_am5.ablate``) and the BM25
    top 8 of the rest (AM1's retrieved arm), in AM5's artifact form; and its text-free facts."""

    ablated, removal = a5.ablate(record)
    pool = g.retrieved_pool(ablated, pool_config)
    leak = a5.pool_facts(record, ablated, pool, pool_config)
    question = {
        "question_id": record["question_id"],
        "question_type": record["question_type"],
        "question": record["question"],
        "answer": str(record["answer"]),
        "question_date": record["question_date"],
        "abstention": False,
        "gold_turns_total": removal["has_answer_turns_after"],
        "user_turns_total": removal["user_turns_after"],
        "pools": {"retrieved": pool},
    }
    facts = {"question_id": record["question_id"], "question_type": record["question_type"],
             **removal, **leak}  # fmt: skip
    return question, facts


def build_heldout_artifact(
    records: list[dict[str, Any]],
    pilot: dict[str, Any],
    heldout_ids: Sequence[str],
    control: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The held-out population: per held-out question (AM1's order) its ablated pool, then the
    replay control's questions exactly as AM5's artifact holds them."""

    by_id = {r["question_id"]: r for r in records}
    pool_config = ms.pool_config(pilot)
    questions, facts = [], []
    for qid in heldout_ids:
        question, fact = ablated_question(by_id[qid], pool_config)
        questions.append(question)
        facts.append(fact)
    n, m = len(questions), len(control["questions"])
    artifact = {
        "experiment_id": EXPERIMENT,
        "claim_level": "confirmatory",
        "split": "heldout-ablated",
        "source": pilot["source"],
        "retriever": pilot["retriever"],
        "pools_config": pilot["pools"],
        "arms": list(ARMS),
        "ablation": "every haystack session whose id is in answer_session_ids removed; the BM25 "
        "top-8 user turns of the rest, as AM1's retrieved arm",
        "question_ids_sha256": ids_sha256(list(heldout_ids)),
        "parts": {"main": [0, n], "control": [n, n + m]},
        "control": {
            "experiment_id": control["experiment_id"],
            "split": control["split"],
            "question_ids_sha256": control["question_ids_sha256"],
            "questions": m,
        },  # fmt: skip
        "questions": questions + list(control["questions"]),
    }
    return artifact, facts


def heldout_summary(
    artifact: dict[str, Any], digest: str, facts: list[dict[str, Any]], pilot: dict[str, Any]
) -> dict[str, Any]:
    """The held-out artifact without LongMemEval text (``memcredit_am5.artifact_summary`` of the
    held-out part): ids, types, digests, pool coordinates, BM25 ranks and scores, the leakage
    facts and each full-pool prompt's length in characters."""

    n = artifact["parts"]["main"][1]
    view = {**artifact, "questions": artifact["questions"][:n]}
    summary = a5.artifact_summary(view, digest, facts, pilot)
    summary["parts"] = artifact["parts"]
    summary["control"] = artifact["control"]
    summary["max_full_pool_prompt_chars_with_control"] = max(
        len(mc.user_message(q, q["pools"]["retrieved"], pilot["prompt"]))
        for q in artifact["questions"]
    )
    return summary


def cmd_prepare_heldout(args: argparse.Namespace) -> dict[str, Any]:
    """Host CPU, before the freeze: the ablated held-out artifact and its text-free summary. It
    checks the inputs' pins, that the retrieved-arm builder reproduces AM1's held-out retrieved
    pools (347 of 347), and that it rebuilds AM5's 63 ablated development pools exactly, which
    ride along as the replay control. No model sees the artifact."""

    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    spec = population_spec(config, "heldout")
    for p in (args.artifact, args.summary):
        if Path(p).exists():
            raise Am5rError(f"refusing to overwrite {p}")
    refuse_inside_repo(args.artifact)
    split = ms.load_split(Path(args.split_file), pilot)
    if sha256_file(Path(args.split_file)) != config["split_file_sha256"]:
        raise Am5rError("the split file differs from its pin")
    source_raw = Path(args.heldout_source_artifact).read_bytes()
    if sha256_bytes(source_raw) != spec["source_artifact_sha256"]:
        raise Am5rError("AM1's held-out artifact differs from its pin")
    source = json.loads(source_raw)
    heldout_ids = [q["question_id"] for q in source["questions"]]
    if (
        len(heldout_ids) != spec["questions"]
        or ids_sha256(heldout_ids) != spec["question_ids_sha256"]
    ):
        raise Am5rError("AM1's held-out ids differ from their pin")
    control_raw = Path(args.control_artifact).read_bytes()
    if sha256_bytes(control_raw) != spec["control"]["artifact_sha256"]:
        raise Am5rError("AM5's ablated development artifact differs from its pin")
    control = json.loads(control_raw)
    records = g.read_source(Path(args.source), pilot)
    by_id = {r["question_id"]: r for r in records}
    pool_config = ms.pool_config(pilot)
    same = sum(
        g.retrieved_pool(by_id[q["question_id"]], pool_config) == q["pools"]["retrieved"]
        for q in source["questions"]
    )
    builder = {"questions": len(heldout_ids), "retrieved_pools_identical": same}
    if same != len(heldout_ids):
        raise Am5rError(f"the pool builder does not reproduce AM1's held-out pools: {builder}")
    rebuilt, _ = a5.build_artifact(records, pilot, split)
    control_same = sum(
        a == b for a, b in zip(rebuilt["questions"], control["questions"], strict=True)
    )
    control_check = {"questions": len(control["questions"]), "rebuilt_identical": control_same}
    if control_same != len(control["questions"]):
        raise Am5rError(f"the ablation does not rebuild AM5's development pools: {control_check}")
    artifact, facts = build_heldout_artifact(records, pilot, heldout_ids, control)
    data = mc.canonical_json(artifact)
    digest = sha256_bytes(data)
    summary = heldout_summary(artifact, digest, facts, pilot)
    summary["heldout_retrieved_pool_check"] = builder
    summary["control_rebuild_check"] = control_check
    summary["inputs"] = {"heldout_source_artifact_sha256": spec["source_artifact_sha256"],
                         "control_artifact_sha256": spec["control"]["artifact_sha256"],
                         "dataset_sha256": pilot["source"]["sha256"],
                         "split_file_sha256": config["split_file_sha256"]}  # fmt: skip
    Path(args.artifact).write_bytes(data)
    Path(args.summary).write_bytes(mc.canonical_json(summary))
    return {
        "artifact_sha256": digest,
        "artifact_bytes": len(data),
        "questions": summary["questions"],
        "question_ids_sha256": summary["question_ids_sha256"],
        "by_type": summary["by_type"],
        "leakage": summary["leakage"],
        "max_full_pool_prompt_chars": summary["max_full_pool_prompt_chars"],
        "max_full_pool_prompt_chars_with_control": summary[
            "max_full_pool_prompt_chars_with_control"
        ],
        "heldout_retrieved_pool_check": builder,
        "control_rebuild_check": control_check,
        "matches_config_pin": digest == spec["artifact_sha256"],
        "summary_sha256": sha256_file(Path(args.summary)),
    }


# --------------------------------------------------------------------------- requests and judge


def request_table(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Every (question, mask) request in canonical order, the control questions last."""

    return g.request_table(artifact, ARMS)


def validation_items(
    config: dict[str, Any], population: str, artifact: dict[str, Any], pilot: dict[str, Any]
) -> list[dict[str, Any]]:
    """AM1's validation items per part (reference answer yes; "I don't know." no; another
    same-type question's answer no, by AM1's seeded derangement within the part): on the held-out
    part they are AM1's held-out items, on the control part AM5's."""

    spec = pilot["judge"]["validation"]
    out: list[dict[str, Any]] = []
    for part in parts_of(config, population).values():
        view = {"questions": artifact["questions"][part.start : part.stop]}
        for item in ms.validation_items(view, spec):
            out.append(dict(item, question_index=int(item["question_index"]) + part.start))
    return out


def judge_items(
    config: dict[str, Any],
    population: str,
    artifact: dict[str, Any],
    pilot: dict[str, Any],
    passes: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply) of the reader passes, then the validation items
    (``memcredit_am5.judge_items`` for the development population, unchanged)."""

    requests = request_table(artifact)
    n = len(requests)
    replies: dict[int, str] = {}
    extended: list[dict[str, Any]] = []
    for k, step_id in enumerate(sorted(passes)):
        for index, text in passes[step_id].items():
            replies[k * n + index] = text
        extended += [dict(r, index=k * n + r["index"]) for r in requests]
    validation = validation_items(config, population, artifact, pilot)
    return ms.judge_item_table(artifact, replies, extended, validation)


def judge_message(artifact: dict[str, Any], item: dict[str, Any]) -> str:
    """LongMemEval's non-abstention answer-check prompt against the reference answer."""

    q = artifact["questions"][item["question_index"]]
    if q.get("abstention") or mc.is_abstention(q) or item.get("template") == "abstention":
        raise Am5rError("this registration judges with the answer-check template only")
    return ms.judge_message(artifact, item)


# --------------------------------------------------------------------------- GPU worker and driver
# Ports of memcredit_am5's worker and driver (themselves am3g's) with the population and the gate.


def vllm_worker(args: argparse.Namespace) -> int:
    import vllm.envs as vllm_envs
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    population = args.population
    gate(population)
    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    step = g.step_spec(config, args.step)
    _, max_s = step_budget(config, population, step["id"])
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
        population=population, env_batch_invariant=os.environ.get("VLLM_BATCH_INVARIANT"),
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
            "population": population,
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
    return [sys.executable, str(Path(__file__).resolve()), "worker", "--population",
            args.population, "--step", step["id"], "--config", args.config, "--output-dir",
            str(out), "--deadline", f"{stop_at:.3f}", "--evidence", args.evidence,
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
    population = args.population
    gate(population)
    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    if list(args.seeds) != config["seeds"]:
        raise Am5rError("--seeds must equal the config's declared seeds")
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = lane.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": EXPERIMENT,
        "population": population,
        "claim_level": "exploratory" if population == "development" else "confirmatory",
        "started_at": lane.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "questions": len(artifact["questions"]),
        "parts": {k: [r.start, r.stop] for k, r in parts_of(config, population).items()},
        "arms": list(ARMS),
        "reader_requests_per_reader": len(request_table(artifact)),
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
        min_start, _ = step_budget(config, population, step["id"])
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
                items = judge_items(config, population, artifact, pilot, passes)
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


def build_plan(config: dict[str, Any], population: str, artifact: dict[str, Any]) -> dict:
    job = config["jobs"][population]
    return {
        "experiment_id": EXPERIMENT,
        "population": population,
        "questions": len(artifact["questions"]),
        "parts": {k: [r.start, r.stop] for k, r in parts_of(config, population).items()},
        "arms": list(ARMS),
        "requests_per_pool": N_REQUESTS,
        "requests_per_reader": len(request_table(artifact)),
        "readers": [r["id"] for r in config["readers"]],
        "steps": [s["id"] for s in config["steps"]],
        "job_minutes": job["minutes"],
        "gpus": job["gpus"],
    }


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only, no engine and no model output: every request rendered with every reader's
    tokenizer and chat template, and the judge items (one placeholder reply per pool) with the
    judge's; lengths, thinking-off markers, stop tokens and vLLM's architecture resolution.
    Allowed for the held-out population before the freeze: it records lengths only."""

    from transformers import AutoTokenizer

    population = args.population
    config = load_config(Path(args.config))
    pilot = g.load_pilot_config(config)
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    root = Path(args.model_root)
    report: dict[str, Any] = {"plan": build_plan(config, population, artifact), "readers": {}}
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
    placeholder = {"selftest": {r["index"]: "I don't know." for r in request_table(artifact)
                                if r["mask"] == FULL}}  # fmt: skip
    items = judge_items(config, population, artifact, pilot, placeholder)
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


def replay_checks(
    config: dict[str, Any],
    population: str,
    artifact: dict[str, Any],
    rows_of: dict[str, dict[int, dict[str, Any]]],
    labels: dict[str, dict[int, int]],
    item_of: dict[tuple[int, str], int],
    items: Sequence[dict[str, Any]],
    reference_dir: Path,
) -> dict[str, Any]:
    """The replay control against AM5's job 1487: per reader, its replies at every control cell
    against job 1487's at the same (question, mask) (tokens and finish reasons; log-prob bits
    reported), and the primary judge's labels there; the judge's item-level replay. On the
    held-out job the anchor's R1 (tokens) and R2 (labels) are the V3 gate."""

    spec = population_spec(config, population)
    ref = spec["reference"]
    digests = g.check_pinned_files(reference_dir, ref["sha256"])
    ref_items = g.read_run_json(reference_dir / "judge-items.json", "job 1487's judge items")
    ref_labels: dict[str, Any] = {
        "primary": am3.labels_from_pass(g.load_pass(reference_dir / "sessions" / JUDGE_STEP)),
        "secondary": None,
    }
    ctrl = control_range(config, population)
    view = {"questions": artifact["questions"][ctrl.start : ctrl.stop]}
    offset = ctrl.start * N_REQUESTS
    ref_index = {(r["question_index"], r["arm"], r["mask"]): r["index"]
                 for r in g.request_table(view, ARMS)}  # fmt: skip
    shifted_items = {(qi - ctrl.start, text): idx for (qi, text), idx in item_of.items()
                     if ctrl.start <= qi < ctrl.stop}  # fmt: skip
    cells = len(ctrl) * N_REQUESTS
    readers: dict[str, Any] = {}
    for reader_id, step in sorted(ref["readers"].items()):
        if reader_id not in rows_of:
            readers[reader_id] = {"missing": True, "r1": False, "r2": False}
            continue
        rows = {i - offset: row for i, row in rows_of[reader_id].items()
                if offset <= i < offset + cells}  # fmt: skip
        ref_rows = g.load_pass(reference_dir / "sessions" / step)["rows"]
        result = g.compare_with_reference(view, ARMS, rows, labels, shifted_items, ref_rows,
                                          ref_index, ref_labels,
                                          am3.item_index(ref_items))  # fmt: skip
        result["token_differences"] = result["token_differences"][:200]
        result["r1"] = result["compared"] == result["cells"] == result["identical_tokens"] == cells
        result["r2"] = result["label_compared_primary"] == result["label_same_primary"] == cells
        readers[reader_id] = result
    ctrl_items = [dict(i, question_index=int(i["question_index"]) - ctrl.start) for i in items
                  if ctrl.start <= int(i["question_index"]) < ctrl.stop]  # fmt: skip
    replay = g.item_replay(ctrl_items, labels, ref_items, ref_labels)
    anchor = readers.get(ANCHOR, {})
    return {"reference": ref["name"], "reference_sha256": digests, "control_questions": len(ctrl),
            "control_cells": cells, "readers": readers,
            "judge_item_replay": {"primary": replay["primary"]},
            "anchor_r1": bool(anchor.get("r1")), "anchor_r2": bool(anchor.get("r2")),
            "pass": bool(anchor.get("r1") and anchor.get("r2"))}  # fmt: skip


def job_id_of(run_dir: Path) -> str:
    """The job id of a run directory, ``R/runs/POP/JOB/am5r``: its parent's name."""

    return Path(run_dir).parent.name


def check_rerun_decision(run_dir: Path, decision_path: Path, population: str) -> str:
    """The job extract may read: the rerun rule's record for it (``am5r-rerun-decision.sh``) must
    say "complete" and name this job directory and population (registration section 8). Returns
    the job id."""

    job_id = job_id_of(run_dir)
    record = g.read_run_json(decision_path, "the rerun rule's record of the job")
    if not isinstance(record, dict) or record.get("decision") != "complete":
        why = record.get("decision") if isinstance(record, dict) else record
        raise Am5rError(f"the rerun rule's record does not say complete ({why}): not extracted")
    if record.get("job_dir") != job_id or record.get("population") != population:
        raise Am5rError(
            f"the rerun rule's record names job {record.get('job_dir')} of "
            f"{record.get('population')}, not job {job_id} of {population}"
        )
    return job_id


def part_validation(
    items: Sequence[dict[str, Any]], labels: dict[str, dict[int, int]], part: range
) -> dict[str, Any]:
    chosen = [i for i in items if int(i["question_index"]) in part]
    return g.validation_summary(chosen, labels)["primary"]


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    """Host only (reads replies): per reader and pool, per requested mask the primary judge's
    label, the abstention flag and pattern, the finish reason, the token count and the normalized
    reply's SHA-256 (``memcredit_am3g.pool_records``); the main part's pools and, apart, the
    control part's; the replay checks against job 1487; the judge's validation counts per part;
    the prepare summary's leakage facts. Writes text-free features to a host-only directory."""

    population = args.population
    if population == "development":
        for p in (args.run_dir, args.evidence, args.private_dir, args.summary,
                  args.reference_run_dir, args.rerun_decision):  # fmt: skip
            check_dev_path(p)
    gate(population)
    refuse_inside_repo(args.private_dir)
    target = Path(args.private_dir) / f"features-{population}.json.gz"
    if target.exists():
        raise Am5rError(f"{target} exists: extract reads one job, once")
    job_id = check_rerun_decision(Path(args.run_dir), Path(args.rerun_decision), population)
    config = load_config(Path(args.config))
    artifact = load_artifact(config, population, args.evidence)
    pin = artifact_pin(config, population)
    summary_art = g.read_run_json(Path(args.summary), "the artifact's text-free summary")
    summary_pin = population_spec(config, population)["summary_sha256"]
    if sha256_file(Path(args.summary)) != summary_pin or summary_art.get("artifact_sha256") != pin:
        raise Am5rError(f"{VOID_DIGEST}: the artifact summary is not the pinned artifact's")
    run_dir = Path(args.run_dir)
    summary = g.read_run_json(run_dir / "summary.json", "the driver's summary")
    if not isinstance(summary, dict) or (
        summary.get("population"),
        summary.get("experiment_id"),
    ) != (population, EXPERIMENT):
        raise Am5rError(f"{VOID_DIGEST}: the run directory is not this population's run")
    items = g.read_run_json(
        run_dir / "judge-items.json", "the judge items (no judge step ran: judge32 was skipped)"
    )
    try:
        judged = g.load_pass(run_dir / "sessions" / JUDGE_STEP)
    except (OSError, ValueError, KeyError, EOFError) as exc:
        raise Am5rError(f"{VOID_INCOMPLETE}: judge32's pass is missing or unreadable: "
                        f"{exc!r}") from exc  # fmt: skip
    labels = {"primary": am3.labels_from_pass(judged), "secondary": {}}
    item_of = am3.item_index(items)
    parts = parts_of(config, population)
    main = parts["main"]
    readers: dict[str, Any] = {}
    rows_of: dict[str, dict[int, dict[str, Any]]] = {}
    for sid in g.reader_steps_complete(summary):
        reader_id = summary["steps"][sid]["reader"]
        if reader_id in readers:
            raise Am5rError(f"two completed passes of {reader_id}")
        try:
            passed = g.load_pass(run_dir / "sessions" / sid)
        except (OSError, ValueError, KeyError, EOFError) as exc:
            raise Am5rError(f"{VOID_INCOMPLETE}: {sid}'s pass is missing or unreadable: "
                            f"{exc!r}") from exc  # fmt: skip
        rows_of[reader_id] = passed["rows"]
        pools = g.pool_records(artifact, ARMS, passed["rows"], item_of, labels)
        finish = Counter(c["finish"] for p in pools for c in p["masks"].values())
        entry = {
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
            "pools": pools[main.start : main.stop],
        }
        if "control" in parts:
            ctrl = parts["control"]
            entry["control_pools"] = pools[ctrl.start : ctrl.stop]
        readers[reader_id] = entry
    validation = {
        "judge_items": len(items),
        "judge_items_reader": sum(1 for i in items if i["source"] == "reader"),
        "labelled": len(labels["primary"]),
        "judge_validation": part_validation(items, labels, main),
        "judge_pass_sha256": {
            f"sessions/{JUDGE_STEP}/{f}": sha256_file(run_dir / "sessions" / JUDGE_STEP / f)
            for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
        },
        "judge_items_sha256": sha256_file(run_dir / "judge-items.json"),
    }
    if "control" in parts:
        validation["judge_validation_control"] = part_validation(items, labels, parts["control"])
    if not args.reference_run_dir:
        raise Am5rError("the replay checks need job 1487's run directory (--reference-run-dir)")
    replay = replay_checks(config, population, artifact, rows_of, labels, item_of, items,
                           Path(args.reference_run_dir))  # fmt: skip
    if population == "development":
        ref_items = population_spec(config, population)["reference"]["sha256"]["judge-items.json"]
        replay["judge_items_identical_to_1487"] = validation["judge_items_sha256"] == ref_items
    if lf.patterns_sha256() != lf.ABSTENTION_PATTERNS_SHA256:
        raise Am5rError(f"{VOID_DIGEST}: the abstention patterns differ from AM1d's")
    spec = population_spec(config, population)
    payload = {
        "experiment": EXPERIMENT,
        "population": population,
        "job_id": job_id,
        "rerun_decision_sha256": sha256_file(Path(args.rerun_decision)),
        "arms": list(ARMS),
        "artifact_sha256": pin,
        "question_ids_sha256": spec["question_ids_sha256"],
        "questions": len(main),
        "parts": {k: [r.start, r.stop] for k, r in parts.items()},
        "abstention_patterns_sha256": lf.patterns_sha256(),
        "answer_templates_sha256": g.answer_templates_sha256(),
        "code_sha256": code_digests(),
        "artifact_summary_sha256": sha256_file(Path(args.summary)),
        "leakage": summary_art["leakage"],
        "leakage_per_question": [q["facts"] for q in summary_art["per_question"]],
        "pool_builder_checks": {
            k: summary_art.get(k)
            for k in (
                "dev_retrieved_pool_check",
                "heldout_retrieved_pool_check",
                "control_rebuild_check",
            )
            if summary_art.get(k) is not None
        },  # fmt: skip
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
                        "killed",
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
        "replay": replay,
        "readers": readers,
    }
    Path(args.private_dir).mkdir(parents=True, exist_ok=True)
    write_gz_json(target, payload)
    brief_replay = {k: v for k, v in replay.items() if k != "readers"} | {
        "readers": {r: {k: v for k, v in d.items() if k != "token_differences"}
                    for r, d in replay["readers"].items()}}  # fmt: skip
    return {
        "population": population,
        "job_id": job_id,
        "readers": {
            r: {k: v for k, v in d.items() if k not in ("pools", "control_pools")}
            for r, d in readers.items()
        },  # fmt: skip
        "validation": validation,
        "replay": brief_replay,
        "features_sha256": sha256_file(target),
    }


def check_features(features: dict[str, Any], config: dict[str, Any], population: str) -> None:
    """VOID (V1) when the features' provenance differs from the pins; VOID (V2) when a reader's
    complete pass is missing."""

    spec = population_spec(config, population)
    checks = {
        "experiment": (features.get("experiment"), EXPERIMENT),
        "population": (features.get("population"), population),
        "artifact_sha256": (features.get("artifact_sha256"), artifact_pin(config, population)),
        "question_ids_sha256": (features.get("question_ids_sha256"), spec["question_ids_sha256"]),
        "abstention_patterns_sha256": (features.get("abstention_patterns_sha256"),
                                       lf.ABSTENTION_PATTERNS_SHA256),
        "answer_templates_sha256": (features.get("answer_templates_sha256"),
                                    g.ANSWER_TEMPLATES_SHA256),
    }  # fmt: skip
    bad = [k for k, (got, want) in checks.items() if got != want]
    if population != "development" and features.get("code_sha256") != code_digests():
        bad.append("code_sha256")
    if bad:
        raise Am5rError(f"{VOID_DIGEST}: the {population} features differ from the pins: {bad}")
    if sorted(features["readers"]) != sorted(READERS):
        raise Am5rError(f"{VOID_INCOMPLETE}: the {population} job lacks a reader's complete pass")
    for reader_id, reader in features["readers"].items():
        if len(reader["pools"]) != int(spec["questions"]):
            raise Am5rError(f"{VOID_INCOMPLETE}: {reader_id}: pools differ from the population")


def int_masks(features: dict[str, Any]) -> None:
    for reader in features["readers"].values():
        for key in ("pools", "control_pools"):
            for pool in reader.get(key, []):
                pool["masks"] = {int(m): cell for m, cell in pool["masks"].items()}


# --------------------------------------------------------------------------- cost and gain


def cost_records(features: dict[str, Any], key: str = "pools") -> dict[str, list[dict[str, Any]]]:
    """Per reader, AM5's per-pool record of every ablated pool (``memcredit_am5.pool_record``) at
    both caps; every pool must have its replies and primary labels."""

    out: dict[str, list[dict[str, Any]]] = {}
    for reader_id in READERS:
        pools = features["readers"][reader_id].get(key, [])
        incomplete = [p for p in pools if not g.pool_complete(p, ("primary",))]
        if incomplete:
            raise Am5rError(f"{VOID_INCOMPLETE}: {reader_id}: {len(incomplete)} pools lack "
                            "replies or primary labels")  # fmt: skip
        out[reader_id] = [a5.pool_record(p, CAPS) for p in pools]
    return out


def cost_indicator(record: dict[str, Any], cap: int) -> int:
    """1 when BM25 top 4's reply is correct (it abstains) and the capped rule's is wrong (it does
    not abstain and the judge rejects it); 0 otherwise. The rule leaves top 4 only when top 4
    abstains, so this is "switched and judged wrong". The reverse (rule correct, top 4 wrong)
    cannot occur: a top 4 that does not abstain is kept."""

    entry = record["caps"][str(cap)]
    if not entry["switched"]:
        return 0
    if not record["bm25_top4_abstains"] or entry["kept_abstains"]:
        raise Am5rError(f"{record['question_id']}: a switch from a top 4 that answers")
    return 1 - int(entry["u"])


def costs_of(records: Sequence[dict[str, Any]], cap: int) -> dict[str, int]:
    return {r["question_id"]: cost_indicator(r, cap) for r in records}


def load_gain_rows(config: dict[str, Any], population: str) -> list[dict[str, Any]]:
    """The gain side's committed per-pool records (pinned): am3g's registered held-out records,
    or AM3's development records for the dry run."""

    spec = population_spec(config, population)["gain"]
    path = PROJECT_ROOT / spec["path"]
    if population == "development":
        check_dev_path(path)
    try:
        digest = sha256_file(path)
    except OSError as exc:
        raise Am5rError(f"{VOID_DIGEST}: {spec['path']} is missing or unreadable: {exc}") from exc
    if digest != spec["sha256"]:
        raise Am5rError(f"{VOID_DIGEST}: {spec['path']} differs from its pin")
    rows = read_gz_json(path)
    want = spec.get("population_field")
    return [
        r for r in rows if r["arm"] == "retrieved" and (want is None or r.get("population") == want)
    ]


def gain_of(row: dict[str, Any], cap: int) -> tuple[int, int]:
    """(gain, loss) of the capped rule over BM25 top 4 on one original pool, primary judge, read
    as AM4 reads the committed records: the rule's choice when its first answering position is at
    most the cap and differs from top 4, else top 4."""

    pos = row["first_answer_position"]
    moved = pos is not None and pos <= cap and row["nonabstain_mask"] != row["bm25_top4_mask"]
    u_top = int(row["u"]["primary"]["bm25_top4"])
    u_cap = int(row["u"]["primary"]["nonabstain_bm25"]) if moved else u_top
    return int(u_cap == 1 and u_top == 0), int(u_cap == 0 and u_top == 1)


def gains_of(
    config: dict[str, Any], population: str, ids: Sequence[str]
) -> dict[str, dict[str, dict[str, int]]]:
    """Per reader and cap, the gain indicator of every question on its original pool. The loss
    (the reverse) is 0 for every question at both caps, and the gain counts equal the pinned ones
    (AM4's for the held-out questions); otherwise the gain side is not the one this registration
    compares with (V1)."""

    spec = population_spec(config, population)["gain"]
    rows = load_gain_rows(config, population)
    out: dict[str, dict[str, dict[str, int]]] = {}
    for reader_id in READERS:
        mine = {r["question_id"]: r for r in rows if r["reader"] == reader_id}
        if sorted(mine) != sorted(ids):
            raise Am5rError(f"{VOID_DIGEST}: {reader_id}: the gain records are not these questions")
        out[reader_id] = {}
        for cap in CAPS:
            pairs = {q: gain_of(mine[q], cap) for q in ids}
            if any(loss for _, loss in pairs.values()):
                raise Am5rError(f"{VOID_DIGEST}: {reader_id}: a loss on an original pool at K = "
                                f"{cap}; the gain side is not the registered one")  # fmt: skip
            gains = {q: gain for q, (gain, _) in pairs.items()}
            expected = int(spec["expected"][str(cap)][reader_id])
            if sum(gains.values()) != expected:
                raise Am5rError(f"{VOID_DIGEST}: {reader_id}: {sum(gains.values())} gains at K = "
                                f"{cap}, not the pinned {expected}")  # fmt: skip
            out[reader_id][str(cap)] = gains
    return out


def paired(
    cost: dict[str, int], gain: dict[str, int], resamples: int, seed: int, alpha: float = ALPHA
) -> dict[str, Any]:
    """Cost minus gain, paired by question (``memcredit_keepset_search.paired_reading`` with the
    cost indicator as "rule" and the gain indicator as "base"): cost only (n10), gain only (n01),
    the difference with its exact conditional 95% interval (whose ends are the one-sided 97.5%
    bounds) and its question-cluster bootstrap interval, and the exact two-sided McNemar p."""

    e = ks.paired_reading({q: float(v) for q, v in cost.items()},
                          {q: float(v) for q, v in gain.items()}, PAIRED_LABELS, resamples, seed,
                          alpha=alpha, label_key="unadjusted_label")  # fmt: skip
    n = e["questions"]
    both = sum(1 for q in cost if cost[q] and gain[q])
    lo, hi = e["ci95_exact_conditional"]
    return {
        "questions": n,
        "cost": sum(cost.values()),
        "gain": sum(gain.values()),
        "cost_rate": e["rule_accuracy"],
        "gain_rate": e["base_accuracy"],
        "cost_only": e["rule_right_base_wrong"],
        "gain_only": e["rule_wrong_base_right"],
        "both": both,
        "difference": e["difference"],
        "ci95_exact_conditional": e["ci95_exact_conditional"],
        "one_sided_97_5": {"lower": lo, "upper": hi},
        "ci95_bootstrap": e["ci95_bootstrap"],
        "p_exact_mcnemar": e["p_exact_mcnemar"],
        "unadjusted_label": e["unadjusted_label"],
        "cost_rate_ci95_exact": g.cp_interval(sum(cost.values()), n),
        "gain_rate_ci95_exact": g.cp_interval(sum(gain.values()), n),
    }


def family_readings(
    costs: dict[str, dict[str, int]],
    gains: dict[str, dict[str, int]],
    resamples: int,
    seed: int,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Per reader the paired comparison, then Holm across the three readers: COST_ABOVE_GAIN when
    rejected with cost only > gain only, COST_BELOW_GAIN when rejected with gain only > cost only,
    NOT_SEPARATED otherwise."""

    per = {r: paired(costs[r], gains[r], resamples, seed, alpha) for r in READERS}
    adjusted = g.holm({r: per[r]["p_exact_mcnemar"] for r in READERS}, alpha)
    for r in READERS:
        e = per[r]
        e["holm"] = adjusted[r]
        e["label"] = g.label_of(adjusted[r]["reject"], e["cost_only"], e["gain_only"],
                                PAIRED_LABELS)  # fmt: skip
        nd = e["cost_only"] + e["gain_only"]
        level = adjusted[r]["step_threshold"]
        if nd:
            plo, phi = mc.clopper_pearson(e["cost_only"], nd, level)
            e["holm_step_interval"] = {
                "level": 1 - level,
                "interval": [
                    nd / e["questions"] * (2 * plo - 1),
                    nd / e["questions"] * (2 * phi - 1),
                ],
            }
        else:
            e["holm_step_interval"] = {"level": 1 - level, "interval": [0.0, 0.0]}
    return {"readers": per, "family": list(READERS), "alpha": alpha, "correction": "holm"}


def break_even_share(
    cost: dict[str, int], gain: dict[str, int], resamples: int, seed: int
) -> dict[str, Any]:
    """The evidence-absent share at which the rule and BM25 top 4 tie, gain / (gain + cost) with
    gain and cost per question (``memcredit_am3g.break_even``: 1 with no cost, 0 with no gain and
    some cost), with a question-cluster percentile bootstrap: each resample draws questions with
    their (gain, cost) pair (numpy default_rng(seed)); the sorted values at floor(0.025 (n - 1))
    and ceil(0.975 (n - 1))."""

    import numpy as np

    qids = sorted(cost)
    c = np.array([float(cost[q]) for q in qids])
    gg = np.array([float(gain[q]) for q in qids])
    point = g.break_even(float(gg.mean()), float(c.mean()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(qids), size=(resamples, len(qids)))
    shares = [g.break_even(float(a), float(b))
              for a, b in zip(gg[idx].mean(axis=1), c[idx].mean(axis=1), strict=True)]  # fmt: skip
    defined = sorted(s for s in shares if s is not None)

    def pct(q: float) -> float | None:
        if not defined:
            return None
        k = math.floor(q * (len(defined) - 1)) if q < 0.5 else math.ceil(q * (len(defined) - 1))
        return float(defined[k])

    return {"gain_per_question": float(gg.mean()), "cost_per_question": float(c.mean()),
            "break_even_share": point, "ci95": [pct(0.025), pct(0.975)],
            "undefined_resamples": len(shares) - len(defined),
            "bootstrap": {"resamples": resamples, "seed": seed,
                          "resampling": "questions, each with its (gain, cost) pair"}}  # fmt: skip


# --------------------------------------------------------------------------- the blind hand check


def hand_labeller_prompt_sha256() -> str:
    return g.hand_labeller_prompt_sha256()


def hand_plan(features: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """The blind hand check's items, from text-free features alone (so ``analyze`` recomputes
    them). Per reader, on the main part's ablated pools:

    * every switched reply at K = 70 the judge calls correct (which holds K = 8's);
    * every switched reply at K = 8 the judge calls wrong (the primary's cost cells);
    * a seeded sample of the switched replies the judge calls wrong that switch only beyond
      K = 8 (positions 9-70): ``ceil(fraction x n)`` of them, ``random.Random(f"{seed}:am5r:
      hand:wrong:{reader}")``;
    * every BM25 top-4 reply that does not abstain;
    * as distractors, as many other replies that do not abstain (any other requested mask of the
      reader's pools), ``random.Random(f"{seed}:am5r:hand:distractor:{reader}")``, none of them a
      target of any reader.

    Items are deduplicated by (question, normalized-reply SHA-256), keep every use, and are put in
    one seeded order (``random.Random(f"{seed}:am5r:hand:order")``); chunks of 60 items."""

    seed = int(config["hand_check"]["seed"])
    fraction = float(config["hand_check"]["secondary_fraction"])
    uses: dict[tuple[str, str], list[dict[str, Any]]] = {}
    per_reader: dict[str, Any] = {}
    targets_of: dict[str, set[tuple[str, str]]] = {}
    pools_of: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}

    def add(key: tuple[str, str], use: dict[str, Any]) -> None:
        uses.setdefault(key, []).append(use)

    for reader in READERS:
        pools = []
        for pool in features["readers"][reader]["pools"]:
            masks = {int(m): c for m, c in pool["masks"].items()}
            pools.append((pool, masks))
        pools_of[reader] = pools
        right, wrong_primary, wrong_beyond, top4 = [], [], [], []
        for pool, masks in pools:
            rec = a5.pool_record({**pool, "masks": masks}, CAPS)
            entry = rec["caps"][str(SECONDARY_CAP)]
            if entry["switched"]:
                key = (rec["question_id"], entry["digest"])
                within = rec["caps"][str(PRIMARY_CAP)]["switched"]
                use = {"reader": reader, "mask": entry["mask"], "judge_primary": int(entry["u"]),
                       "position": rec["first_answer_position"],
                       "within_primary_cap": within}  # fmt: skip
                if entry["u"] == 1:
                    right.append((key, use | {"role": ROLE_RIGHT}))
                elif within:
                    wrong_primary.append((key, use | {"role": ROLE_WRONG_PRIMARY}))
                else:
                    wrong_beyond.append((key, use | {"role": ROLE_WRONG_SECONDARY}))
            if not rec["bm25_top4_abstains"]:
                top4.append(((rec["question_id"], rec["digest"]["bm25_top4"]),
                             {"reader": reader, "role": ROLE_TOP4, "mask": rec["bm25_top4_mask"],
                              "judge_primary": int(rec["u"]["bm25_top4"])}))  # fmt: skip
        rng = random.Random(f"{seed}:am5r:hand:wrong:{reader}")
        wrong_beyond.sort(key=lambda kv: kv[0])
        k = math.ceil(fraction * len(wrong_beyond))
        sampled = rng.sample(wrong_beyond, k)
        chosen = right + wrong_primary + sampled + top4
        for key, use in chosen:
            add(key, use)
        targets_of[reader] = {key for key, _ in chosen}
        per_reader[reader] = {
            "switched_judged_correct": len(right),
            "switched_judged_wrong_within_primary_cap": len(wrong_primary),
            "switched_judged_wrong_beyond_primary_cap": len(wrong_beyond),
            "switched_judged_wrong_beyond_sampled": len(sampled),
            "top4_answers": len(top4),
        }
    all_targets = set().union(*targets_of.values())
    for reader in READERS:
        candidates: dict[tuple[str, str], dict[str, Any]] = {}
        for pool, masks in pools_of[reader]:
            for mask in REQUEST_MASKS:
                cell = masks[mask]
                if cell["abstain"] or cell.get("digest") is None:
                    continue
                key = (pool["question_id"], cell["digest"])
                if key in all_targets or key in candidates:
                    continue
                judged = cell["u"][JUDGE]
                candidates[key] = {
                    "reader": reader,
                    "role": ROLE_DISTRACTOR,
                    "mask": mask,
                    "judge_primary": None if judged is None else int(judged),
                }
        keys = sorted(candidates)
        want = len(targets_of[reader])
        rng = random.Random(f"{seed}:am5r:hand:distractor:{reader}")
        drawn = rng.sample(keys, min(want, len(keys)))
        for key in drawn:
            add(key, candidates[key])
        per_reader[reader].update(target_items=want, distractor_items=len(drawn),
                                  distractor_shortfall=want - len(drawn))  # fmt: skip
    keys = sorted(uses)
    random.Random(f"{seed}:am5r:hand:order").shuffle(keys)
    items = [{"item_id": f"r{n:04d}", "question_id": q, "reply_digest": d, "check": HAND_CHECK,
              "uses": uses[(q, d)]} for n, (q, d) in enumerate(keys)]  # fmt: skip
    plan = {"seed": seed, "secondary_fraction": fraction, "chunk_size": g.HAND_CHUNK,
            "readers": per_reader, "items": items, "labeller_model": g.HAND_LABELLER_MODEL,
            "labeller_prompt_sha256": hand_labeller_prompt_sha256(),
            "instructions_sha256": sha256_text(HAND_INSTRUCTIONS)}  # fmt: skip
    plan["plan_sha256"] = sha256_bytes(json.dumps(items, sort_keys=True).encode())
    return plan


def _sample_rows(
    plan: dict[str, Any], features: dict[str, Any], artifact: dict[str, Any], run_dir: Path
) -> list[str]:
    """One JSON line per plan item: id, question id and type, check, question, reference text,
    reply; nothing else."""

    lines = []
    cache: dict[str, dict[int, Any]] = {}
    index = {(r["question_id"], r["mask"]): r["index"] for r in request_table(artifact)}
    questions = {q["question_id"]: q for q in artifact["questions"]}
    for item in plan["items"]:
        use = item["uses"][0]
        reader = use["reader"]
        if reader not in cache:
            step = features["readers"][reader]["step"]
            cache[reader] = g.load_pass(run_dir / "sessions" / step)["rows"]
        text = cache[reader][index[(item["question_id"], int(use["mask"]))]]["text"]
        if sha256_text(mc.normalize_answer(text.strip())) != item["reply_digest"]:
            raise Am5rError(f"{VOID_DIGEST}: a reply differs from the features' digest")
        q = questions[item["question_id"]]
        lines.append(json.dumps({"item_id": item["item_id"], "question_id": q["question_id"],
                                 "question_type": q["question_type"], "check": item["check"],
                                 "question": q["question"], "reference": str(q["answer"]),
                                 "reply": text.strip()}, ensure_ascii=False))  # fmt: skip
    return lines


def cmd_hand_sample(args: argparse.Namespace) -> dict[str, Any]:
    """Host only (reads reply texts): the blind sample, one JSON line per plan item, the
    instructions, the chunks with am3g's pinned launch prompt (``memcredit_am3g.write_chunks``),
    the plan (text-free) and a text-free manifest, in ``--hand-dir``, a directory of its own.
    Prints counts and digests only."""

    population = args.population
    if population == "development":
        for path in (args.run_dir, args.evidence, args.features, args.hand_dir):
            check_dev_path(path)
    gate(population)
    hand_dir = Path(args.hand_dir)
    refuse_inside_repo(hand_dir)
    if hand_dir.exists() and any(hand_dir.iterdir()):
        raise Am5rError(f"refusing a non-empty hand directory {hand_dir}")
    if Path(args.features).resolve().parent == hand_dir.resolve():
        raise Am5rError("the hand directory must not hold the features")
    config = load_config(Path(args.config))
    features = read_gz_json(Path(args.features))
    check_features(features, config, population)
    if features.get("job_id") != job_id_of(Path(args.run_dir)):
        raise Am5rError(
            f"{VOID_DIGEST}: the features are job {features.get('job_id')}'s, the "
            f"run directory is job {job_id_of(Path(args.run_dir))}'s"
        )
    artifact = load_artifact(config, population, args.evidence)
    plan = hand_plan(features, config)
    lines = _sample_rows(plan, features, artifact, Path(args.run_dir))
    hand_dir.mkdir(parents=True, exist_ok=True)
    sample = hand_dir / "hand-check-sample.jsonl"
    sample.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    instructions = hand_dir / "hand-check-instructions.txt"
    instructions.write_text(HAND_INSTRUCTIONS, encoding="utf-8")
    ids = [i["item_id"] for i in plan["items"]]
    chunks = g.write_chunks(hand_dir, "first", lines, ids)
    (hand_dir / "hand-plan.json").write_text(json.dumps(plan, indent=1, sort_keys=True))
    manifest = {"plan_sha256": plan["plan_sha256"], "items": ids, "chunk_size": g.HAND_CHUNK,
                "first": chunks, "labeller_model": g.HAND_LABELLER_MODEL,
                "labeller_prompt_sha256": hand_labeller_prompt_sha256(),
                "instructions_sha256": sha256_file(instructions),
                "sample_sha256": sha256_file(sample)}  # fmt: skip
    (hand_dir / "hand-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    roles = Counter(u["role"] for i in plan["items"] for u in i["uses"])
    return {"population": population, "items": len(lines), "readers": plan["readers"],
            "uses_by_role": dict(sorted(roles.items())), "plan_sha256": plan["plan_sha256"],
            "sample_sha256": manifest["sample_sha256"],
            "instructions_sha256": manifest["instructions_sha256"], "chunks": len(chunks),
            "chunk_size": g.HAND_CHUNK, "labeller_model": g.HAND_LABELLER_MODEL,
            "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
            "features_sha256": sha256_file(Path(args.features))}  # fmt: skip


def hand_join(
    plan: dict[str, Any], labels: list[dict[str, Any]] | None, labels_sha256: str | None
) -> dict[str, Any]:
    """Join the labels to the plan: "joined" when every item has exactly one label of 0 or 1 and
    no other item is labelled; "missing" without labels; "incomplete" otherwise. Returns the
    status, the (question, digest) -> label map when joined, and hand-against-judge agreement per
    role (descriptive)."""

    out: dict[str, Any] = {
        "plan_sha256": plan["plan_sha256"],
        "items": len(plan["items"]),
        "readers_plan": plan["readers"],
        "labels_sha256": labels_sha256,
        "labeller": f"an isolated agent ({plan['labeller_model']}), blind (D9: agent labels, "
        "not human)",
        "labeller_prompt_sha256": plan["labeller_prompt_sha256"],
        "instructions_sha256": plan["instructions_sha256"],
        "uses_by_role": dict(sorted(Counter(u["role"] for i in plan["items"]
                                            for u in i["uses"]).items())),
    }  # fmt: skip
    if labels is None:
        out["status"] = "missing"
        return out
    by_id: dict[str, Any] = {}
    bad = []
    for row in labels:
        item_id, label = row.get("item_id"), row.get("label")
        if item_id in by_id or label not in (0, 1):
            bad.append(item_id)
        by_id[item_id] = label
    wanted = {i["item_id"] for i in plan["items"]}
    missing, extra = sorted(wanted - set(by_id)), sorted(set(by_id) - wanted)
    if bad or missing or extra:
        out.update(status="incomplete", missing=missing[:50], extra=extra[:50],
                   invalid_or_repeated=[b for b in bad if b is not None][:50])  # fmt: skip
        return out
    out["status"] = "joined"
    hand_of = {(i["question_id"], i["reply_digest"]): int(by_id[i["item_id"]])
               for i in plan["items"]}  # fmt: skip
    out["hand_of"] = hand_of
    notes = {str(row.get("item_id")): str(row.get("note") or "").strip().lower()
             for row in labels}  # fmt: skip
    decline = {i["item_id"]: by_id[i["item_id"]] == 1 and notes.get(i["item_id"], "").startswith(
        DECLINE_NOTE) for i in plan["items"]}  # fmt: skip
    out["decline_of"] = {(i["question_id"], i["reply_digest"]): decline[i["item_id"]]
                         for i in plan["items"]}  # fmt: skip
    out["decline_items"] = sorted(k for k, v in decline.items() if v)
    by_role_decl: Counter = Counter()
    for i in plan["items"]:
        if decline[i["item_id"]]:
            for role in sorted({u["role"] for u in i["uses"]}):
                by_role_decl[role] += 1
    out["decline_notes"] = {
        "rule": f'a label 1 whose note starts with "{DECLINE_NOTE}" (case-folded): the reply '
        "declines to answer; counts only, no text",
        "items": sum(decline.values()),
        "by_role": dict(sorted(by_role_decl.items())),
        "label_0_with_decline_note": sum(1 for i in plan["items"] if by_id[i["item_id"]] == 0
                                         and notes.get(i["item_id"], "").startswith(DECLINE_NOTE)),
    }  # fmt: skip
    pairs = [(int(i["uses"][0]["judge_primary"]), hand_of[(i["question_id"], i["reply_digest"])])
             for i in plan["items"]]  # fmt: skip
    out["agreement"] = g._agreement(pairs)
    by_role: dict[str, list[tuple[int, int]]] = {}
    for i in plan["items"]:
        h = hand_of[(i["question_id"], i["reply_digest"])]
        for role in sorted({u["role"] for u in i["uses"]}):
            judged = next(int(u["judge_primary"]) for u in i["uses"] if u["role"] == role)
            by_role.setdefault(role, []).append((judged, h))
    out["agreement_by_role"] = {k: g._agreement(v) for k, v in sorted(by_role.items())}
    return out


def hand_costs(
    records: Sequence[dict[str, Any]], cap: int, hand_of: dict[tuple[str, str], int],
    unlabelled: str,
) -> tuple[dict[str, int], dict[str, int]]:  # fmt: skip
    """The hand-based cost indicator: 1 when the capped rule switched and the switched reply's
    hand label is 0. A switched reply without a label (only possible beyond K = 8, where the
    judged-wrong replies are sampled) counts as a cost (``unlabelled="cost"``) or not
    (``"no-cost"``): the assignment least favourable to the reading under confirmation."""

    if unlabelled not in ("cost", "no-cost"):
        raise Am5rError("unlabelled is cost or no-cost")
    out, counts = {}, Counter()
    for r in records:
        entry = r["caps"][str(cap)]
        if not entry["switched"]:
            out[r["question_id"]] = 0
            continue
        key = (r["question_id"], entry["digest"])
        if key in hand_of:
            out[r["question_id"]] = 1 - hand_of[key]
            counts["labelled"] += 1
            counts["judge_yes_hand_no"] += int(entry["u"] == 1 and hand_of[key] == 0)
            counts["judge_no_hand_yes"] += int(entry["u"] == 0 and hand_of[key] == 1)
        else:
            out[r["question_id"]] = 1 if unlabelled == "cost" else 0
            counts["unlabelled"] += 1
            counts["unlabelled_judged_correct"] += int(entry["u"] == 1)
    counts["switched"] = counts["labelled"] + counts["unlabelled"]
    return out, {k: int(counts[k]) for k in ("switched", "labelled", "unlabelled",
                                             "unlabelled_judged_correct", "judge_yes_hand_no",
                                             "judge_no_hand_yes")}  # fmt: skip


def confirm_reading(judge_reading: str, status: str, hand_label: str | None) -> str:
    """A directional judge-based reading stands only if the hand-based label (the same test, with
    Holm across the readers) is the same; otherwise JUDGE_DEPENDENT. NOT_SEPARATED stands whatever
    the hand labels say. Without labels a directional reading is PENDING_HAND_CHECK; with labels
    that do not cover the plan exactly, JUDGE_DEPENDENT."""

    if judge_reading not in DIRECTIONAL:
        return judge_reading
    if status == "missing":
        return "PENDING_HAND_CHECK"
    if status != "joined":
        return "JUDGE_DEPENDENT"
    return judge_reading if hand_label == judge_reading else "JUDGE_DEPENDENT"


# --------------------------------------------------------------------------- analysis


def g_j1(validation: dict[str, Any]) -> dict[str, Any]:
    """G-J1, a replay of AM1's validation items (am3g's rule): the primary judge says yes to at
    least 95% of reference answers (preference questions left out) and no to at least 95% of
    "I don't know."; the other-answer decoys' yes count is reported (a judge accepting wrong
    answers would hide costs; the hand check of every judged-correct switched reply covers that)."""

    v = validation["judge_validation"]
    ref, idk = v["validation:reference"], v["validation:idk"]
    other = v.get("validation:other-answer", {"items": 0, "yes": 0, "missing": 0})
    ref_ok = ref["yes"] >= math.ceil(0.95 * ref["items"]) and ref["missing"] == 0
    idk_ok = idk["items"] - idk["yes"] >= math.ceil(0.95 * idk["items"]) and idk["missing"] == 0
    return {
        "reference_yes": [ref["yes"], ref["items"]],
        "idk_no": [idk["items"] - idk["yes"], idk["items"]],
        "other_answer_yes": [other["yes"], other["items"]],
        "pass": ref_ok and idk_ok,
    }


def by_type(records: Sequence[dict[str, Any]], gains: dict[str, dict[str, int]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for qtype in sorted({r["question_type"] for r in records}):
        sub = [r for r in records if r["question_type"] == qtype]
        row: dict[str, Any] = {"questions": len(sub)}
        for cap in CAPS:
            row[str(cap)] = {
                "switched": sum(r["caps"][str(cap)]["switched"] for r in sub),
                "cost": sum(cost_indicator(r, cap) for r in sub),
                "gain": sum(gains[str(cap)][r["question_id"]] for r in sub),
            }
        out[qtype] = row
    return out


#: The two crude leak flags of the prepare summary (``memcredit_am5.pool_facts``).
LEAK_FLAGS = {
    "answer_in_a_pool_memory": "pool_memories_containing_the_answer",
    "answer_in_a_remaining_user_turn": "remaining_user_turns_containing_the_answer",
}


def leak_breakdown(
    records: Sequence[dict[str, Any]], facts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Descriptive: per crude leak flag (the normalized reference answer as words in a pool memory,
    or in a remaining user turn) and its value, the questions, and at K = 8 and 70 the switches,
    the switched replies judged correct and the costs."""

    out: dict[str, Any] = {}
    for name, key in LEAK_FLAGS.items():
        out[name] = {}
        for value in (True, False):
            sub = [r for r in records if (int(facts[r["question_id"]][key]) > 0) is value]
            row: dict[str, Any] = {"questions": len(sub)}
            for cap in CAPS:
                switched = [r for r in sub if r["caps"][str(cap)]["switched"]]
                row[str(cap)] = {"switched": len(switched),
                                 "switched_judged_correct": sum(int(r["caps"][str(cap)]["u"])
                                                                for r in switched),
                                 "cost": sum(cost_indicator(r, cap) for r in sub)}  # fmt: skip
            out[name]["flag" if value else "no_flag"] = row
    return out


def analysis_config(config: dict[str, Any]) -> dict[str, Any]:
    spec = config["analysis"]
    return {
        "caps": list(CAPS),
        "primary_cap": PRIMARY_CAP,
        "alpha": float(spec["alpha"]),
        "bootstrap": spec["bootstrap"],
        "outcome": "on an ablated pool a reply is correct when it abstains (AM1d's patterns) or, "
        "when it does not, when Qwen3-32B's answer check against the reference says yes",
        "cost_indicator": "BM25 top 4 correct and the capped rule wrong: the rule switched (top 4 "
        "abstained, a 4-subset within K reads answered) and the judge rejects the switched reply",
        "gain_indicator": "on the same question's original pool (am3g's committed records), the "
        "capped rule's reply judged correct and BM25 top 4's wrong (AM4's reading)",
        "test": "exact two-sided McNemar on (cost only, gain only) per reader; Holm across the "
        "three readers at alpha; COST_ABOVE_GAIN / COST_BELOW_GAIN when rejected and cost only > / "
        "< gain only, else NOT_SEPARATED; the decision at K = 8 (primary), K = 70 secondary",
        "break_even": "gain / (gain + cost), question-cluster percentile bootstrap",
        "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
        "answer_templates_sha256": g.ANSWER_TEMPLATES_SHA256,
        "requests_per_pool": N_REQUESTS,
        "hand_instructions_sha256": sha256_text(HAND_INSTRUCTIONS),
    }


def readings_block(
    recs: dict[str, list[dict[str, Any]]],
    gains: dict[str, dict[str, dict[str, int]]],
    cap: int,
    hand: dict[str, Any],
    resamples: int,
    seed: int,
    alpha: float,
    keep: set[str] | None = None,
) -> dict[str, Any]:
    """One cap: the judge-based family readings, the hand-based ones (both assignments of
    unlabelled replies), the readings after the hand check, and the break-even share (judge and
    hand). ``keep`` restricts the questions (the sensitivity analysis)."""

    def sub(d: dict[str, int]) -> dict[str, int]:
        return {q: v for q, v in d.items() if keep is None or q in keep}

    costs = {r: sub(costs_of(recs[r], cap)) for r in READERS}
    gain = {r: sub(gains[r][str(cap)]) for r in READERS}
    judged = family_readings(costs, gain, resamples, seed, alpha)
    block: dict[str, Any] = {"cap": cap, "judge": judged, "readers": {}}
    hand_based: dict[str, Any] = {}
    if hand["status"] == "joined":
        for variant in ("cost", "no-cost"):
            hc, counts = {}, {}
            for r in READERS:
                ind, cnt = hand_costs(recs[r], cap, hand["hand_of"], variant)
                hc[r], counts[r] = sub(ind), cnt
            fam = family_readings(hc, gain, resamples, seed, alpha)
            for r in READERS:
                fam["readers"][r]["switched_replies"] = counts[r]
            hand_based[f"unlabelled_{variant.replace('-', '_')}"] = fam
        block["hand"] = hand_based
    for r in READERS:
        jr = judged["readers"][r]["label"]
        if hand["status"] == "joined":
            variant = "unlabelled_cost" if jr == COST_BELOW else "unlabelled_no_cost"
            hl = hand_based[variant]["readers"][r]["label"]
        else:
            hl = None
        entry = {
            "judge_reading": jr,
            "hand_label": hl,
            "reading": confirm_reading(jr, hand["status"], hl),
            "break_even_judge": break_even_share(costs[r], gain[r], resamples, seed),
        }
        if hand["status"] == "joined":
            exact = hand_based["unlabelled_cost"]["readers"][r]["switched_replies"]
            if cap == PRIMARY_CAP and exact["unlabelled"]:
                raise Am5rError(f"{r}: a switched reply at K = {cap} has no hand label")
            if exact["unlabelled"] == 0:
                hc, _ = hand_costs(recs[r], cap, hand["hand_of"], "cost")
                entry["break_even_hand"] = break_even_share(sub(hc), gain[r], resamples, seed)
        block["readers"][r] = entry
    return block


def analyze_population(
    features: dict[str, Any],
    config: dict[str, Any],
    population: str,
    hand_labels: list[dict[str, Any]] | None,
    hand_labels_sha256: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The registered analysis (held-out) or its mechanics on the development dry run (which
    decide nothing)."""

    spec = config["analysis"]
    resamples, seed = int(spec["bootstrap"]["resamples"]), int(spec["bootstrap"]["seed"])
    alpha = float(spec["alpha"])
    check_features(features, config, population)
    int_masks(features)
    recs = cost_records(features)
    ids = [r["question_id"] for r in recs[READERS[0]]]
    for r in READERS:
        if [x["question_id"] for x in recs[r]] != ids:
            raise Am5rError("readers' pools are not aligned")
    gains = gains_of(config, population, ids)
    plan = hand_plan(features, config)
    hand = hand_join(plan, hand_labels, hand_labels_sha256)
    replay = features["replay"]
    replay_ok = bool(replay.get("pass"))
    gj1 = g_j1(features["validation"])
    validity = {
        "v1_pins": "pass",
        "v2_complete": "pass",
        "v3_replay_control": {"pass": replay_ok, "anchor_r1": replay.get("anchor_r1"),
                              "anchor_r2": replay.get("anchor_r2")},
        "g_j1_replay_of_am1_validation_items": gj1,
    }  # fmt: skip
    primary = readings_block(recs, gains, PRIMARY_CAP, hand, resamples, seed, alpha)
    secondary = readings_block(recs, gains, SECONDARY_CAP, hand, resamples, seed, alpha)
    # Precedence: VOID (V3) over JUDGE_DEPENDENT (G-J1) over the hand check.
    for block in (primary, secondary):
        if not replay_ok:
            block["status"] = f"{VOID_REPLAY}: not read"
            for e in block["readers"].values():
                e["reading"] = "VOID"
        elif not gj1["pass"]:
            block["status"] = "JUDGE_DEPENDENT: G-J1 (the replay of AM1's validation items) failed"
            for e in block["readers"].values():
                e["reading"] = "JUDGE_DEPENDENT" if e["judge_reading"] in DIRECTIONAL else (
                    e["judge_reading"])  # fmt: skip
        else:
            block["status"] = (
                "read" if hand["status"] == "joined" else f"hand check {hand['status']}"
            )
    secondary["decides"] = False
    non_preference = {
        r["question_id"] for r in recs[READERS[0]] if r["question_type"] != PREFERENCE
    }
    sensitivity: dict[str, Any] = {"excluded_type": PREFERENCE, "questions": len(non_preference),
                                   "decides": False}  # fmt: skip
    for cap in CAPS:
        sensitivity[str(cap)] = readings_block(recs, gains, cap, hand, resamples, seed, alpha,
                                               non_preference)  # fmt: skip
    hand_public = {k: v for k, v in hand.items() if k not in ("hand_of", "decline_of")}
    labels_by_id = ({row["item_id"]: int(row["label"]) for row in hand_labels or []}
                    if hand["status"] == "joined" else None)  # fmt: skip
    items, item_agreement = a5.labelled_items(features, plan, labels_by_id)
    declined = set(hand.get("decline_items", []))
    for item in items:
        item["decline"] = item["item_id"] in declined if labels_by_id is not None else None
    facts = {f["question_id"]: f for f in features["leakage_per_question"]}
    descriptive: dict[str, Any] = {"readers": {}}
    hand_of = hand.get("hand_of", {})
    for r in READERS:
        block = a5.ablated_block(recs[r], CAPS, hand_of)
        decline_of = hand.get("decline_of", {})
        switched_declines = {
            str(c): sum(1 for rec in recs[r] if rec["caps"][str(c)]["switched"] and decline_of.get(
                (rec["question_id"], rec["caps"][str(c)]["digest"]))) for c in CAPS
        } if hand["status"] == "joined" else None  # fmt: skip
        descriptive["readers"][r] = {
            "by_leak_flag": leak_breakdown(recs[r], facts),
            "switched_replies_hand_labelled_declines": switched_declines,
            "step": features["readers"][r]["step"],
            "batch_invariant": features["readers"][r]["batch_invariant"],
            "finish": features["readers"][r]["finish"],
            "ablated": block,
            "by_type": by_type(recs[r], gains[r]),
            "gain_counts": {str(c): sum(gains[r][str(c)].values()) for c in CAPS},
            "abstention_patterns": dict(sorted(Counter(
                str(c["pattern"]) for p in features["readers"][r]["pools"]
                for c in p["masks"].values() if c["abstain"]).items())),
        }  # fmt: skip
        if features["readers"][r].get("control_pools"):
            control = cost_records(features, "control_pools")[r]
            descriptive["readers"][r]["control_ablated"] = a5.ablated_block(control, CAPS, {})
    per_table = []
    for r in READERS:
        for rec in recs[r]:
            row = {"reader": r, **{k: v for k, v in rec.items() if k != "digest"},
                   "caps": {k: {kk: vv for kk, vv in v.items() if kk != "digest"}
                            for k, v in rec["caps"].items()}}  # fmt: skip
            row["cost"] = {str(c): cost_indicator(rec, c) for c in CAPS}
            row["gain"] = {str(c): gains[r][str(c)][rec["question_id"]] for c in CAPS}
            per_table.append(row)
    results = {
        "experiment": EXPERIMENT,
        "population": population,
        "claim_level": "confirmatory" if population == "heldout" else "exploratory",
        "note": None if population == "heldout" else (
            "development dry run: the registered machinery on AM5's 63 development ablated pools "
            "against AM3's development gains; nothing is decided"),
        "config": analysis_config(config),
        "inputs": {
            "artifact_sha256": features["artifact_sha256"],
            "question_ids_sha256": features["question_ids_sha256"],
            "artifact_summary_sha256": features["artifact_summary_sha256"],
            "code_sha256": features["code_sha256"],
            "gain_per_table_sha256": population_spec(config, population)["gain"]["sha256"],
            "run": features["run"],
            "readers": {r: {k: features["readers"][r][k] for k in (
                "step", "batch_invariant", "enforce_eager", "pass_sha256", "requests", "finish",
                "missing_logprobs", "pools_complete_primary")} for r in READERS},
        },  # fmt: skip
        "leakage": features["leakage"],
        "pool_builder_checks": features["pool_builder_checks"],
        "validation": features["validation"],
        "replay_control": {k: v for k, v in replay.items() if k != "readers"} | {
            "readers": {r: {k: v for k, v in d.items() if k != "token_differences"}
                        for r, d in replay["readers"].items()}},  # fmt: skip
        "validity": validity,
        "primary": primary,
        "secondary": secondary,
        "sensitivity_without_preference": sensitivity,
        "hand_check": hand_public | {"agreement_items": item_agreement},
        "labelled_items": items,
        "descriptive": descriptive,
        "verdicts": {"primary_k8": {r: primary["readers"][r]["reading"] for r in READERS}
                     | {"status": primary["status"]},
                     "secondary_k70": {r: secondary["readers"][r]["reading"] for r in READERS}
                     | {"status": secondary["status"], "decides": False}},
    }  # fmt: skip
    return results, per_table


def read_hand_labels(path: Path, expected: str | None) -> tuple[list[dict[str, Any]], str]:
    try:
        return g.read_hand_labels(path, expected)
    except g.Am3gError as exc:
        raise Am5rError(str(exc)) from exc


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    population = args.population
    if population == "development":
        for p in (args.features, args.output_dir):
            check_dev_path(p)
    gate(population)
    config = load_config(Path(args.config))
    out = Path(args.output_dir)
    if out.exists():
        raise Am5rError(f"{out} exists: analyze writes a new directory")
    if population == "heldout" and not (args.hand_labels and args.hand_labels_sha256
                                        and args.hand_plan_sha256):  # fmt: skip
        raise Am5rError("the registered analysis needs --hand-labels, --hand-labels-sha256 and "
                        "--hand-plan-sha256 (the blind hand check's labels, their digest and the "
                        "plan's, as receipted and committed before the join)")  # fmt: skip
    features = read_gz_json(Path(args.features))
    labels, digest = (read_hand_labels(Path(args.hand_labels), args.hand_labels_sha256)
                      if args.hand_labels else (None, None))  # fmt: skip
    results, per_table = analyze_population(features, config, population, labels, digest)
    if labels is not None and results["hand_check"]["plan_sha256"] != args.hand_plan_sha256:
        raise Am5rError("the hand labels' receipted plan differs from the plan these features give "
                        f"({results['hand_check']['plan_sha256']})")  # fmt: skip
    results["inputs"]["features_sha256"] = sha256_file(Path(args.features))
    out.mkdir(parents=True)
    lane.write_json(out / "results.json", results)
    write_gz_json(out / "per-table.json.gz", per_table)
    (out / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return {f: sha256_file(out / f) for f in ("results.json", "per-table.json.gz", "tables.md")}


# --------------------------------------------------------------------------- tables


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _p(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:.2g}" if x < 0.001 else f"{x:.3f}"


def _ci(ci: Sequence[float | None] | None, signed: bool = False) -> str:
    if not ci or ci[0] is None:
        return "n/a"
    fmt = "{:+.3f}" if signed else "{:.3f}"
    return f"[{fmt.format(ci[0])}, {fmt.format(ci[1])}]"


def _reading_rows(block: dict[str, Any]) -> list[str]:
    lines = ["| Reader | cost | gain | cost only | gain only | cost - gain [exact 95%] | "
             "bootstrap 95% | p | p (Holm) | judge reading | hand label | reading | "
             "break-even share [95%] |",
             "|---|---:|---:|---:|---:|---|---|---:|---:|---|---|---|---|"]  # fmt: skip
    for r in READERS:
        e = block["judge"]["readers"][r]
        x = block["readers"][r]
        be = x["break_even_judge"]
        lines.append(
            f"| {r} | {e['cost']} | {e['gain']} | {e['cost_only']} | {e['gain_only']} | "
            f"{e['difference']:+.3f} {_ci(e['ci95_exact_conditional'], True)} | "
            f"{_ci(e['ci95_bootstrap'], True)} | {_p(e['p_exact_mcnemar'])} | "
            f"{_p(e['holm']['p_holm'])} | {x['judge_reading']} | {x['hand_label'] or 'n/a'} | "
            f"{x['reading']} | {_f(be['break_even_share'], 2)} {_ci(be['ci95'])} |"
        )
    return lines


def render_markdown(results: dict[str, Any]) -> str:
    dev = results["population"] == "development"
    title = ("am5-ablated-cost-v1: development dry run (EXPLORATORY; nothing is decided)" if dev
             else "am5-ablated-cost-v1: tables")  # fmt: skip
    lines = [f"# {title}", "",
             "Generated by `scripts/memcredit_am5r.py analyze`. Cost: on the question's ablated "
             "pool the capped rule switched and Qwen3-32B rejects the switched reply. Gain: on the "
             "same question's original pool the capped rule's reply judged correct and BM25 top "
             "4's wrong. p: exact two-sided McNemar on (cost only, gain only); p (Holm): across "
             "the three readers.", ""]  # fmt: skip
    v = results["validity"]
    lines += ["## Validity", "",
              f"- V3 replay control: {v['v3_replay_control']}",
              f"- G-J1: {v['g_j1_replay_of_am1_validation_items']}", ""]  # fmt: skip
    for key, name in (("primary", "Primary, K = 8"), ("secondary", "Secondary, K = 70")):
        block = results[key]
        lines += [f"## {name} ({block['status']})", ""] + _reading_rows(block) + [""]
    sens = results["sensitivity_without_preference"]
    for cap in CAPS:
        lines += [f"## Sensitivity without {PREFERENCE} questions, K = {cap} "
                  f"({sens['questions']} questions; descriptive)", ""]  # fmt: skip
        lines += _reading_rows(sens[str(cap)]) + [""]
    hc = results["hand_check"]
    lines += [f"## Blind hand check ({hc['status']}; agent labels, D9)", "",
              f"Plan `{hc['plan_sha256'][:16]}...`, {hc['items']} items; uses by role: "
              f"{hc['uses_by_role']}.", ""]  # fmt: skip
    if hc["status"] == "joined":
        a = hc["agreement"]
        lines += [f"Hand against judge (descriptive): {a['agree']} of {a['items']} agree "
                  f"(judge yes, hand no {a['judge_yes_hand_no']}; judge no, hand yes "
                  f"{a['judge_no_hand_yes']}; kappa {_f(a['kappa'], 2)}).", ""]  # fmt: skip
    if hc["status"] == "joined":
        dn = hc["decline_notes"]
        lines += [f"Hand labels of 1 given for a decline (note starting \"{DECLINE_NOTE}\"): "
                  f"{dn['items']} items, by role {dn['by_role']}; label 0 with such a note: "
                  f"{dn['label_0_with_decline_note']}.", ""]  # fmt: skip
    lines += ["## Switches and costs by the crude leak flags (descriptive)", "",
              "| Reader | flag | value | questions | K = 8: switched, judged correct, cost | "
              "K = 70: switched, judged correct, cost |", "|---|---|---|---:|---|---|"]  # fmt: skip
    for r, d in results["descriptive"]["readers"].items():
        for name, by_value in d["by_leak_flag"].items():
            for value, row in by_value.items():
                cells = " | ".join(
                    ", ".join(str(row[str(c)][f]) for f in ("switched", "switched_judged_correct",
                                                            "cost"))
                    for c in CAPS)  # fmt: skip
                lines.append(f"| {r} | {name} | {value} | {row['questions']} | {cells} |")
    lines.append("")
    lines += ["## Ablated pools (descriptive)", "",
              "| Reader | K | switch rate | cost (judge) | switched judged correct | top 4 does "
              "not abstain | all 8 abstains | every 4-subset abstains | mean reads |",
              "|---|---:|---|---|---:|---|---|---|---:|"]  # fmt: skip
    for r, d in results["descriptive"]["readers"].items():
        a = d["ablated"]
        for cap in CAPS:
            c = a["caps"][str(cap)]
            lines.append(
                f"| {r} | {cap} | {a5._r(c['switch_rate'])} | {a5._r(c['cost_judge'])} | "
                f"{c['switched_judged_correct']} | {a5._r(a['bm25_top4_answers'])} | "
                f"{a5._r(a['all_8_abstains'])} | {a5._r(a['every_4_subset_abstains'])} | "
                f"{_f(c['reads']['mean'], 2)} |"
            )
    lines += [
        "",
        "## Leakage (the prepare summary's counts)",
        "",
        "| Check | Count |",
        "|---|---:|",
    ]
    lines += [f"| {k.replace('_', ' ')} | {val} |" for k, val in results["leakage"].items()]
    rc = results["replay_control"]
    lines += ["", f"## Replay control against job 1487 ({rc['control_questions']} questions, "
              f"{rc['control_cells']} cells per reader)", "",
              "| Reader | identical tokens | identical bits | labels equal | R1 | R2 |",
              "|---|---:|---:|---:|---|---|"]  # fmt: skip
    for r, d in rc["readers"].items():
        if d.get("missing"):
            lines.append(f"| {r} | missing | | | False | False |")
            continue
        lines.append(f"| {r} | {d['identical_tokens']} | {d['identical_bits']} | "
                     f"{d['label_same_primary']} | {d['r1']} | {d['r2']} |")  # fmt: skip
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- dry-run comparison

AM5_DIR = Path("program/evidence/2026-10-16/am5-evidence-ablated")


def am5_view(features: dict[str, Any]) -> dict[str, Any]:
    """The development features in AM5's form (its header fields), so that AM5's own analysis
    (``memcredit_am5.analyze``) reads them unchanged."""

    a5_config = a5.load_config()
    view = json.loads(json.dumps(features))
    view.update(experiment=a5.EXPERIMENT, population=a5.POPULATION,
                artifact_sha256=a5_config["population"]["artifact_sha256"],
                question_ids_sha256=a5_config["population"]["question_ids_sha256"],
                dev_retrieved_pool_check=features["pool_builder_checks"].get(
                    "dev_retrieved_pool_check"))  # fmt: skip
    for reader in view["readers"].values():
        reader.pop("control_pools", None)
    return view


def dryrun_compare(
    features: dict[str, Any],
    am5_features: dict[str, Any],
    am5_labels: dict[str, int],
    results: dict[str, Any],
    am5_plan_sha256: str,
) -> dict[str, Any]:
    """The development dry run against AM5: replies and judge labels against job 1487, the
    features' per-pool cells against AM5's features, AM5's own analysis on these features (with
    AM5's receipted hand labels) against AM5's committed outputs (byte for byte for its per-pool
    table), and this registration's descriptive blocks against AM5's committed figures."""

    checks: list[dict[str, Any]] = []
    replay = features["replay"]
    for r, c in sorted(replay["readers"].items()):
        checks.append(
            {
                "check": f"replies {r} vs job 1487 (tokens and finish)",
                "compared": c.get("compared"),
                "identical": c.get("identical_tokens"),
                "identical_bits": c.get("identical_bits"),
                "pass": bool(c.get("r1")),
            }
        )
        checks.append({"check": f"primary labels {r} vs job 1487 at every cell",
                       "pass": bool(c.get("r2"))})  # fmt: skip
    j = replay["judge_item_replay"]["primary"]
    checks.append({"check": "judge item replay vs job 1487 (validation items included)",
                   "compared": j["compared"], "identical": j["same"],
                   "pass": j["compared"] > 0 and j["compared"] == j["same"]})  # fmt: skip
    checks.append(
        {
            "check": "judge-items.json byte-identical to job 1487's",
            "pass": bool(replay.get("judge_items_identical_to_1487")),
        }
    )
    for r in READERS:
        mine = features["readers"][r]["pools"]
        theirs = am5_features["readers"][r]["pools"]
        same = sum(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
                   for a, b in zip(mine, theirs, strict=True))  # fmt: skip
        checks.append(
            {
                "check": f"feature pools {r} vs AM5's features",
                "compared": len(theirs),
                "identical": same,
                "pass": same == len(theirs) == len(mine),
            }
        )
    a5_config = a5.load_config()
    # AM5's own analysis recomputes AM5's hand plan from these features and refuses a plan other
    # than the one AM5 receipted.
    a5_results, a5_per_table = a5.analyze(am5_view(features), a5_config, am5_labels,
                                          am5_plan_sha256)  # fmt: skip
    committed = json.loads((PROJECT_ROOT / AM5_DIR / "results.json").read_text("utf-8"))
    import gzip

    blob = gzip.compress(json.dumps(a5_per_table, sort_keys=True, separators=(",", ":")).encode(),
                         mtime=0)  # fmt: skip
    committed_pt = PROJECT_ROOT / AM5_DIR / "per-table.json.gz"
    checks.append({"check": "AM5's analysis on these features: per-table.json.gz byte-identical "
                   "to AM5's committed file", "sha256": sha256_bytes(blob),
                   "pass": sha256_bytes(blob) == sha256_file(committed_pt)})  # fmt: skip
    for key in ("readers", "leakage", "leakage_by_type", "judge_validation", "labelled_items"):
        mine = json.loads(json.dumps(a5_results[key]))
        checks.append(
            {
                "check": f"AM5's analysis on these features: results.json '{key}' equal "
                "to AM5's committed results",
                "pass": mine == committed[key],
            }
        )
    hc = {k: v for k, v in a5_results["hand_check"].items()}
    checks.append({"check": "AM5's analysis on these features with AM5's receipted labels: the "
                   "hand check equal to AM5's committed one",
                   "pass": json.loads(json.dumps(hc)) == committed["hand_check"]})  # fmt: skip
    judge_fields = ("switch_rate", "switches_per_abstaining_top4", "rule_keeps_an_abstention",
                    "rule_answers", "reads", "cap_reached_without_answer",
                    "switched_judged_correct", "cost_judge", "switched_by_type")  # fmt: skip
    for r in READERS:
        mine = results["descriptive"]["readers"][r]["ablated"]
        theirs = committed["readers"][r]["ablated"]
        same = all(json.loads(json.dumps(mine["caps"][str(c)][f])) == theirs["caps"][str(c)][f]
                   for c in CAPS for f in judge_fields)  # fmt: skip
        same &= all(
            json.loads(json.dumps(mine[f])) == theirs[f]
            for f in (
                "pools",
                "bm25_top4_abstains",
                "bm25_top4_answers",
                "all_8_abstains",
                "every_4_subset_abstains",
                "four_subset_replies_abstaining",
                "top4_answers_judged_correct",
                "all_8_answers",
                "all_8_answers_judged_correct",
            )
        )
        checks.append(
            {
                "check": f"this registration's ablated block {r} (judge-based fields) "
                "equal to AM5's committed results",
                "pass": same,
            }
        )
        gains = results["descriptive"]["readers"][r]["gain_counts"]
        orig = committed["readers"][r]["original"]["caps"]
        checks.append(
            {
                "check": f"gain counts {r} equal to AM5's original-pool gains (AM3)",
                "pass": all(gains[str(c)] == orig[str(c)]["gained_b"] for c in CAPS),
            }
        )
    return {"checks": checks, "passed": sum(bool(c["pass"]) for c in checks),
            "total": len(checks), "all_pass": all(c["pass"] for c in checks)}  # fmt: skip


def cmd_dryrun_compare(args: argparse.Namespace) -> dict[str, Any]:
    for p in (args.features, args.am5_features, args.am5_hand_labels, args.output_dir):
        check_dev_path(p)
    config = load_config(Path(args.config))
    am5 = population_spec(config, "development")["am5"]
    if sha256_file(Path(args.am5_features)) != am5["features_sha256"]:
        raise Am5rError(f"{VOID_DIGEST}: AM5's features differ from their pin")
    if sha256_file(Path(args.am5_hand_labels)) != am5["hand_labels_sha256"]:
        raise Am5rError(f"{VOID_DIGEST}: AM5's receipted hand labels differ from their pin")
    labels = a5.read_hand_labels(Path(args.am5_hand_labels), am5["hand_labels_sha256"])
    features = read_gz_json(Path(args.features))
    am5_features = read_gz_json(Path(args.am5_features))
    a5.int_masks(am5_features)
    results, _ = analyze_population(json.loads(json.dumps(features)), config, "development",
                                    None, None)  # fmt: skip
    int_masks(features)
    report = dryrun_compare(features, am5_features, labels, results, am5["hand_plan_sha256"])
    report["inputs"] = {"am5_results_sha256": sha256_file(PROJECT_ROOT / AM5_DIR / "results.json"),
                        "am5_per_table_sha256": sha256_file(
                            PROJECT_ROOT / AM5_DIR / "per-table.json.gz"),
                        "am5_features_sha256": am5["features_sha256"],
                        "am5_hand_labels_sha256": am5["hand_labels_sha256"],
                        "features_sha256": sha256_file(Path(args.features))}  # fmt: skip
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    lane.write_json(out / "dryrun-compare.json", report)
    return {"passed": report["passed"], "total": report["total"], "all_pass": report["all_pass"],
            "sha256": sha256_file(out / "dryrun-compare.json")}  # fmt: skip


# --------------------------------------------------------------------------- power


def mcnemar_threshold(nd: int, alpha: float) -> int:
    """``memcredit_keepset_search.mcnemar_threshold`` (the largest k with
    ``mcnemar_exact(k, nd - k) <= alpha``, -1 if none: the exact test rejects exactly when
    min(b, c) <= k), computed with one running sum of exact binomial coefficients; a test checks
    the two agree."""

    from fractions import Fraction

    total, k = 0, -1
    while k + 1 < nd:
        total += math.comb(nd, k + 1)
        if float(min(Fraction(1), Fraction(2 * total, 2**nd))) > alpha:
            break
        k += 1
    return k


def rejection_directions(max_b: int, max_c: int, alpha: float) -> Any:
    """D[b, c]: +1 when the exact two-sided McNemar test at ``alpha`` rejects with b > c, -1 when
    it rejects with b < c, 0 otherwise."""

    import numpy as np

    thresholds: dict[int, int] = {}
    d = np.zeros((max_b + 1, max_c + 1), dtype=np.int8)
    for b in range(max_b + 1):
        for c in range(max_c + 1):
            nd = b + c
            if nd not in thresholds:
                thresholds[nd] = mcnemar_threshold(nd, alpha)
            if b != c and min(b, c) <= thresholds[nd]:
                d[b, c] = 1 if b > c else -1
    return d


def _pmf_vector(n: int, p: float) -> Any:
    import numpy as np

    return np.array([ks._pmf(k, n, p) for k in range(n + 1)])


def power_cost_gain(
    n: int, gains: int, q: float, alpha: float, confirm: float = 1.0, directions: Any = None
) -> dict[str, float]:
    """The probability that the exact McNemar test at ``alpha`` reads COST_BELOW_GAIN or
    COST_ABOVE_GAIN, with the gain indicators fixed at their known values (``gains`` of ``n``) and
    each question's cost indicator Bernoulli(q), independently of its gain: cost only ~
    Binomial(n - gains, q), and the gain-only count is gains minus Binomial(gains, q). With
    ``confirm`` < 1 each judge-counted cost is a hand-confirmed cost with that probability (the
    others are replies the hand labels call correct or declining) and a reading counts only when
    the hand-based test reads the same way (registration section 7)."""

    import numpy as np

    d = directions if directions is not None else rejection_directions(n - gains, gains, alpha)
    w1, w2 = _pmf_vector(n - gains, q), _pmf_vector(gains, q)
    rows, cols = np.nonzero(w1 > 1e-13)[0], np.nonzero(w2 > 1e-13)[0]
    hand = {int(n10): _pmf_vector(int(n10), confirm) for n10 in rows} if confirm < 1.0 else {}
    up, down = (d == 1).astype(float), (d == -1).astype(float)
    below = above = 0.0
    for nb in cols:
        if confirm < 1.0:
            hb = _pmf_vector(int(nb), confirm)
            idx = gains - np.arange(nb + 1)
            m_up, m_down = up[:, idx] @ hb, down[:, idx] @ hb
        for n10 in rows:
            direction = int(d[n10, gains - nb])
            if direction == 0:
                continue
            weight = float(w1[n10] * w2[nb])
            if confirm < 1.0:
                m = m_up if direction > 0 else m_down
                weight *= float(hand[int(n10)] @ m[: n10 + 1])
            if direction > 0:
                above += weight
            else:
                below += weight
    return {"below": min(1.0, below), "above": min(1.0, above)}


def predictive_power(
    n: int, gains: int, k: int, m: int, alpha: float, directions: Any, grid: int = 200
) -> dict[str, float]:
    """The power averaged over the development uncertainty of the cost rate: q ~ Beta(k + 1/2,
    m - k + 1/2) (Jeffreys' prior and k costs of m development pools), truncated to [0, 0.5],
    integrated on q = t^2 / 2 with t at ``grid`` midpoints (the substitution removes the density's
    singularity at 0 when k = 0)."""

    import numpy as np

    t = (np.arange(grid) + 0.5) / grid
    qs = 0.5 * t * t
    log_w = (k - 0.5) * np.log(qs) + (m - k - 0.5) * np.log1p(-qs) + np.log(t)
    w = np.exp(log_w - log_w.max())
    w /= w.sum()
    below = above = 0.0
    for q, weight in zip(qs, w, strict=True):
        if weight < 1e-10:
            continue
        p = power_cost_gain(n, gains, float(q), alpha, directions=directions)
        below += float(weight) * p["below"]
        above += float(weight) * p["above"]
    return {"below": below, "above": above, "any": below + above}


def power_report(config: dict[str, Any], am5_results: dict[str, Any]) -> dict[str, Any]:
    """The test's power per reader, the gain side fixed at the known held-out counts, at AM5's
    development cost rates (and their exact upper bounds) and on a grid; Holm rejects a reader at
    least at 0.05/3 and at most at 0.05, so the two columns bound its power."""

    n = int(population_spec(config, "heldout")["questions"])
    expected = population_spec(config, "heldout")["gain"]["expected"]
    out: dict[str, Any] = {"questions": n, "readers": {},
                           "model": "gain indicators fixed at the known held-out values; each "
                           "question's cost Bernoulli(q), independent of its gain; exact McNemar "
                           "on (cost only, gain only)"}  # fmt: skip
    grid = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20)
    for r in READERS:
        dev = {}
        for cap in CAPS:
            c = am5_results["readers"][r]["ablated"]["caps"][str(cap)]["cost_judge"]
            dev[str(cap)] = {"count": c["count"], "n": c["n"], "rate": c["rate"],
                             "ci95_exact": c["ci95_exact"]}  # fmt: skip
        entry: dict[str, Any] = {"dev_cost": dev, "caps": {}}
        for cap in CAPS:
            gains = int(expected[str(cap)][r])
            rows: dict[str, Any] = {}
            scenarios = [
                ("AM5 development rate", dev[str(cap)]["rate"]),
                ("AM5 development upper 95% bound", dev[str(cap)]["ci95_exact"][1]),
            ]
            scenarios += [(f"q={q:.2f}", q) for q in grid]
            d_lo = rejection_directions(n - gains, gains, ALPHA / 3)
            d_hi = rejection_directions(n - gains, gains, ALPHA)
            for label, q in scenarios:
                lo = power_cost_gain(n, gains, q, ALPHA / 3, directions=d_lo)
                hi = power_cost_gain(n, gains, q, ALPHA, directions=d_hi)
                rows[label] = {"q": q, "below_alpha_0.0167": lo["below"],
                               "below_alpha_0.05": hi["below"], "above_alpha_0.0167": lo["above"],
                               "above_alpha_0.05": hi["above"]}  # fmt: skip
            hand = {}
            for label, q in (
                ("AM5 development rate", dev[str(cap)]["rate"]),
                ("q=0.12", 0.12),
                ("q=0.15", 0.15),
                ("q=0.20", 0.20),
            ):
                hand[label] = {f"a={a}": {
                    "above_alpha_0.0167": power_cost_gain(n, gains, q, ALPHA / 3, a,
                                                          d_lo)["above"],
                    "above_alpha_0.05": power_cost_gain(n, gains, q, ALPHA, a, d_hi)["above"]}
                    for a in (1.0, 0.9, 0.8)}  # fmt: skip
            k, m = int(dev[str(cap)]["count"]), int(dev[str(cap)]["n"])
            lo = predictive_power(n, gains, k, m, ALPHA / 3, d_lo)
            hi = predictive_power(n, gains, k, m, ALPHA, d_hi)
            averaged = {"prior": f"q ~ Beta({k} + 1/2, {m - k} + 1/2) on [0, 0.5]",
                        **{f"{key}_alpha_0.0167": lo[key] for key in lo},
                        **{f"{key}_alpha_0.05": hi[key] for key in hi}}  # fmt: skip
            entry["caps"][str(cap)] = {
                "gains": gains,
                "gain_rate": gains / n,
                "scenarios": rows,
                "averaged_over_development_uncertainty": averaged,
                "with_the_hand_check": hand,
            }
        out["readers"][r] = entry
    return out


def cmd_power(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    path = PROJECT_ROOT / AM5_DIR / "results.json"
    am5 = population_spec(config, "development")["am5"]
    if sha256_file(path) != am5["results_sha256"]:
        raise Am5rError("AM5's committed results differ from their pin")
    report = power_report(config, json.loads(path.read_text("utf-8")))
    report["inputs"] = {
        "am5_results_sha256": am5["results_sha256"],
        "gain_expected": population_spec(config, "heldout")["gain"]["expected"],
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return {"sha256": sha256_file(Path(args.output))}


# --------------------------------------------------------------------------- the rerun rule


def cmd_rerun_decision(args: argparse.Namespace) -> dict[str, Any]:
    """am3g's mechanical rerun rule (``memcredit_am3g.rerun_decision``; its essential steps are
    this registration's: the three readers and judge32) on the driver's summary.json and the
    lane's termination.env."""

    job_dir = Path(args.job_dir)
    summary_path = job_dir / OUTPUT / "summary.json"
    summary = None
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except ValueError:
            summary = None
        if summary is not None and not isinstance(summary, dict):
            raise Am5rError(f"{VOID_INCOMPLETE}: the driver's summary.json is not a JSON object")
    decision = g.rerun_decision(summary, g.read_env_file(job_dir / "termination.env"),
                                args.is_rerun)  # fmt: skip
    return {"population": args.population, "job_dir": job_dir.name} | decision


# --------------------------------------------------------------------------- main


def check_config_binding(args: argparse.Namespace) -> None:
    """The held-out population runs only with the pinned config: its path (whose SHA-256 section
    16 pins) and no other."""

    population = getattr(args, "population", None)
    if population == "heldout" and Path(args.config).resolve() != CONFIG_PATH.resolve():
        pinned = CONFIG_PATH.relative_to(PROJECT_ROOT)
        raise Am5rError(f"the {args.command} command runs the held-out population only with the "
                        f"pinned config {pinned}")  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare-heldout", allow_abbrev=False)
    prep.add_argument("--source", required=True)
    prep.add_argument("--split-file", required=True)
    prep.add_argument("--heldout-source-artifact", required=True)
    prep.add_argument("--control-artifact", required=True)
    prep.add_argument("--artifact", required=True)
    prep.add_argument("--summary", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--population", required=True, choices=POPULATIONS)
    plan.add_argument("--evidence", required=True)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--population", required=True, choices=POPULATIONS)
    selftest.add_argument("--model-root", default=str(am3.MODEL_ROOT))
    selftest.add_argument("--evidence", required=True)
    selftest.add_argument("--expected-evidence-sha256", default=None)
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--population", required=True, choices=POPULATIONS)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--evidence", required=True)
    run.add_argument("--expected-evidence-sha256", required=True)
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--population", required=True, choices=POPULATIONS)
    worker.add_argument("--step", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--evidence", required=True)
    worker.add_argument("--expected-evidence-sha256", required=True)
    extract = sub.add_parser("extract", allow_abbrev=False)
    extract.add_argument("--population", required=True, choices=POPULATIONS)
    extract.add_argument("--run-dir", required=True)
    extract.add_argument("--evidence", required=True)
    extract.add_argument("--summary", required=True)
    extract.add_argument("--private-dir", required=True)
    extract.add_argument("--reference-run-dir", default=None)
    extract.add_argument("--rerun-decision", required=True)
    hand = sub.add_parser("hand-sample", allow_abbrev=False)
    hand.add_argument("--population", required=True, choices=POPULATIONS)
    hand.add_argument("--run-dir", required=True)
    hand.add_argument("--evidence", required=True)
    hand.add_argument("--features", required=True)
    hand.add_argument("--hand-dir", required=True)
    merge = sub.add_parser("hand-merge", allow_abbrev=False)
    merge.add_argument("--hand-dir", required=True)
    merge.add_argument("--stage", required=True, choices=("first", "repair"))
    analyze_p = sub.add_parser("analyze", allow_abbrev=False)
    analyze_p.add_argument("--population", required=True, choices=POPULATIONS)
    analyze_p.add_argument("--features", required=True)
    analyze_p.add_argument("--hand-labels", default=None)
    analyze_p.add_argument("--hand-labels-sha256", default=None)
    analyze_p.add_argument("--hand-plan-sha256", default=None)
    analyze_p.add_argument("--output-dir", required=True)
    compare = sub.add_parser("dryrun-compare", allow_abbrev=False)
    compare.add_argument("--features", required=True)
    compare.add_argument("--am5-features", required=True)
    compare.add_argument("--am5-hand-labels", required=True)
    compare.add_argument("--output-dir", required=True)
    power_p = sub.add_parser("power", allow_abbrev=False)
    power_p.add_argument("--output", required=True)
    rerun = sub.add_parser("rerun-decision", allow_abbrev=False)
    rerun.add_argument("--population", required=True, choices=POPULATIONS)
    rerun.add_argument("--job-dir", required=True)
    rerun.add_argument("--is-rerun", action="store_true")
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args(argv)
    try:
        check_config_binding(args)
        if args.command == "plan":
            config = load_config(Path(args.config))
            artifact = load_artifact(config, args.population, args.evidence)
            print(json.dumps(build_plan(config, args.population, artifact), indent=2))
            return 0
        if args.command == "selftest":
            return selftest_main(args)
        if args.command == "run":
            return run_main(args)
        if args.command == "worker":
            return vllm_worker(args)
        commands = {
            "prepare-heldout": cmd_prepare_heldout,
            "extract": cmd_extract,
            "hand-sample": cmd_hand_sample,
            "hand-merge": g.cmd_hand_merge,
            "analyze": cmd_analyze,
            "dryrun-compare": cmd_dryrun_compare,
            "power": cmd_power,
            "rerun-decision": cmd_rerun_decision,
        }
        print(json.dumps(commands[args.command](args), indent=2, sort_keys=True))
        return 0
    except (Am5rError, a5.Am5Error, g.Am3gError, am3.Am3Error, ks.KeepsetError,
            ms.StudyError) as exc:  # fmt: skip
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as exc:
        if args.command in ("run", "worker"):
            raise  # the GPU job's driver and workers record their own failures
        print(f"error: {VOID_INCOMPLETE}: an input is missing or unreadable: {exc!r}",
              file=sys.stderr)  # fmt: skip
        return 2


if __name__ == "__main__":
    sys.exit(main())
