#!/usr/bin/env python3
"""am3-nonabstain-generality-v1 (D118): does the non-abstention keep rule hold for other readers on
held-out questions, and what does it cost on questions that have no answer?

``am1-keepset-search-v1`` confirmed H-C for the Qwen3-8B reader under the Qwen3-32B judge: keeping
the best-BM25-ranked 4-subset whose reply does not abstain (AM1d's rule and four abstention
patterns, digest ``031bee27...``; BM25 top 4 when every 4-subset abstains) is more accurate than
BM25 top 4 on AM1's 347 held-out questions (39 gained, 0 lost). AM3 (exploratory, development
split) found the same direction for OLMo-2-1124-7B-Instruct and Qwen3.5-9B, without separation.
This registration runs:

* H1 (confirmatory): the rule against BM25 top 4 on the 347 held-out questions, retrieved arm,
  Qwen3-32B judge, for OLMo-2 and Qwen3.5-9B; exact two-sided McNemar per reader, Holm across the
  two readers. The anchor (Qwen3-8B, AM1's reader and eager batch-invariant engine) runs the same
  requests and must replay job 1458 bit for bit and AM1's committed tables label for label.
* H2 (descriptive, registered estimand): the rule's cost on LongMemEval-S's 30 abstention
  questions (``*_abs``), retrieved arm built as AM1's, judged with LongMemEval's official
  abstention prompt, for all three readers: b2 (BM25 top 4 judged correct, the rule's choice
  judged wrong) with an exact interval.

Per pool every reader answers the 70 4-subsets and the full pool of 8 (71 requests) with AM1's
prompt, greedy, 64 tokens; both judges score every distinct (question, reply). Config:
``experiments/am3/am3-nonabstain-generality-v1.yaml``; registration:
``program/preregistrations/am3-nonabstain-generality-v1.md``.

Subcommands (POP is ``development``, ``heldout`` or ``abstention``):

* ``prepare-abstention --source F --split-file S --artifact A --summary P [--dev-artifact D]``
  (host CPU): the abstention population's study artifact (pool texts; host only) and a text-free
  summary. With ``--dev-artifact`` it also checks that the retrieved-arm builder reproduces the
  development artifact's retrieved pools.
* ``plan --population POP --evidence A``; ``selftest --population POP --evidence A`` (CPU, no
  engine; renders every request with every reader's tokenizer and the judge items with both
  judges').
* ``run --population POP --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the GPU job, one H100, steps in order.
* ``worker``: one step.
* ``extract --population POP --run-dir R --evidence A --private-dir P [--reference-run-dir REF]``
  (host only; reads reply texts): joins replies to labels, flags abstentions and runs the anchor
  checks; writes text-free features to a host-only directory.
* ``analyze --heldout-features F1 (--abstention-features F2 | --abstention-void REASON)
  --output-dir O`` (registered) or ``analyze --development-features F --output-dir O`` (dry run):
  CPU only; text-free ``results.json``, ``per-table.json.gz`` and ``tables.md``.
* ``dryrun-compare --development-features F --output-dir O``: the development dry run against
  AM3's committed outputs.
* ``power --am3-features F --output P``: the operating characteristics of section 9.

The held-out and abstention populations are refused before the freeze (``gate``): the ledger must
hold a row for this experiment with the registration file's SHA-256, and every code pin of the
registration's section 16 must match. ``prepare-abstention`` and the tokenizer-only ``selftest`` of
the abstention population are allowed before it (they produce no model output).
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import math
import os
import random
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_am3 as am3  # noqa: E402  (AM3's engine, worker, rule and per-pool helpers)
import memcredit_cost_curve as cc  # noqa: E402  (committed-table decoding)
import memcredit_keepset_search as ks  # noqa: E402  (McNemar, paired readings, reads, ledger)
import memcredit_label_free as lf  # noqa: E402  (abstention patterns, BM25 order)
import memcredit_step0 as s0  # noqa: E402  (engine streaming, pass files, GPU sampler)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am3-nonabstain-generality-v1"
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am3" / "am3-nonabstain-generality-v1.yaml"
REGISTRATION = Path("program/preregistrations/am3-nonabstain-generality-v1.md")
LEDGER = Path("program/preregistrations/ledger.jsonl")
K = 8
BUDGET = 4
FULL = (1 << K) - 1
FOUR_SETS: tuple[int, ...] = lf.FOUR_SETS
REQUEST_MASKS: tuple[int, ...] = am3.REQUEST_MASKS
ARMS = ("retrieved", "gold")
JUDGES = ("primary", "secondary")
JUDGE_STEP = {"primary": "judge32", "secondary": "judge8"}
POPULATIONS = ("development", "heldout", "abstention")
#: Which populations open only after the freeze. A code property, so no config edit can lift it.
GATED = {"development": False, "heldout": True, "abstention": True}
ANCHOR = "qwen3-8b"
H1_READERS = ("olmo-2-1124-7b-instruct", "qwen3.5-9b")
H2_READERS = ("qwen3-8b", "olmo-2-1124-7b-instruct", "qwen3.5-9b")
H1_LABELS = ("NONABSTAIN_HELPS", "NONABSTAIN_HURTS", "NO_DETECTED_DIFFERENCE")
H2_LABELS = ("NONABSTAIN_COSTS", "NONABSTAIN_SAFE", "NO_DETECTED_DIFFERENCE")
ALPHA = 0.05
#: Path parts the development dry run never opens (held-out data and runs, the abstention
#: population's inputs).
FORBIDDEN_DEV_PARTS = (
    "am1-confirmatory",
    "am1-memory-credit-v1",
    "am1-keepset-search-v1",
    "am3-nonabstain-generality-v1",
    "abstention-artifact",
)
#: LongMemEval's official abstention answer-check prompt (``get_anscheck_prompt`` with
#: ``abstention=True``; src/evaluation/evaluate_qa.py at
#: 9e0b455f4ef0e2ab8f2e582289761153549043fc, MIT), word for word as the program's archived port
#: (``legacy/harness/memory_trials/longmemeval_judge.py``) has it; a test checks the two agree.
ABSTENTION_TEMPLATE = (
    "I will give you an unanswerable question, an explanation, and a response "
    "from a model. Please answer yes if the model correctly identifies the "
    "question as unanswerable. The model could say that the information is "
    "incomplete, or some other information is given but the asked information "
    "is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: "
    "{}\n\nDoes the model correctly identify the question as unanswerable? "
    "Answer yes or no only."
)
ABSTENTION_TEMPLATE_SHA256 = "5c0b365a1e1d06db36377c735432b56e122ca3c428f89faf61d43a0d5a7e050b"
#: SHA-256 of json.dumps(ms.JUDGE_TEMPLATES, sort_keys=True, ensure_ascii=False): AM1's pin.
ANSWER_TEMPLATES_SHA256 = "2e27234d4c7d50a1fd99da3e8d3c97704a1f10cc9d52185924b6d8ece3ef71d4"
#: Void prefixes (registration section 8).
VOID_DIGEST = "VOID (V1, a pinned input differs; nothing read)"
VOID_INCOMPLETE = "VOID (V2, incomplete)"
VOID_REPLAY = "VOID (V3, anchor replay failed)"
#: The code whose SHA-256 the features record and ``analyze`` checks (this script and the
#: repository modules it imports; a test checks the list against a fresh interpreter).
FEATURE_CODE = (
    "scripts/memcredit_am3g.py",
    "scripts/memcredit_am3.py",
    "scripts/memcredit_keepset_search.py",
    "scripts/memcredit_cost_curve.py",
    "scripts/memcredit_label_free.py",
    "scripts/memcredit_step0.py",
    "scripts/memcredit_study.py",
    "scripts/memcredit_analyze.py",
    "harness/__init__.py",
    "harness/g2_pilot.py",
    "harness/memcredit.py",
    "harness/memcredit_study.py",
)
SMOKE_REQUESTS = 16
SMOKE_FAILED_EXIT = 4


class Am3gError(ValueError):
    """The config, an input, a gate or a void rule failed."""


# --------------------------------------------------------------------------- small helpers


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ids_sha256(ids: Sequence[str]) -> str:
    return sha256_text("\n".join(ids))


def write_gz_json(path: Path, payload: Any) -> None:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(gzip.compress(blob, mtime=0))
    os.replace(temporary, path)


def read_gz_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def check_dev_path(path: Path | str | None) -> None:
    """The development dry run never opens held-out or abstention inputs (symlinks resolved)."""

    if path is None:
        return
    texts = [str(path)]
    with contextlib.suppress(OSError):
        texts.append(str(Path(path).resolve()))
    for text in texts:
        for part in FORBIDDEN_DEV_PARTS:
            if part in text:
                raise Am3gError(f"the development population refuses {path}")


def refuse_inside_repo(path: Path | str) -> None:
    """Host-only outputs (features, artifacts) never land in the repository they run from."""

    if Path(path).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        raise Am3gError(f"{path} is inside the repository; host-only files stay outside it")


def abstention_template_sha256() -> str:
    return sha256_text(ABSTENTION_TEMPLATE)


def answer_templates_sha256() -> str:
    blob = json.dumps(ms.JUDGE_TEMPLATES, sort_keys=True, ensure_ascii=False).encode()
    return sha256_bytes(blob)


def code_digests(root: Path = PROJECT_ROOT) -> dict[str, str]:
    return {path: sha256_file(root / path) for path in FEATURE_CODE}


# --------------------------------------------------------------------------- the gate


def gate(
    population: str,
    ledger: Path | None = None,
    registration: Path | None = None,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Run before any held-out or abstention input is opened: the ledger must hold a row for this
    experiment with the registration file's SHA-256, and every code pin of its section 16 must
    match the working tree. The development population needs neither. Tests pass scratch copies
    of the ledger and the registration."""

    if population not in POPULATIONS:
        raise Am3gError(f"unknown population {population}")
    if not GATED[population]:
        return {"population": population, "frozen_required": False}
    ledger = ledger or root / LEDGER
    registration = registration or root / REGISTRATION
    if not ks.registration_frozen(ledger, registration, EXPERIMENT):
        raise Am3gError(
            f"the {population} population opens only after the freeze: no ledger row for "
            f"{EXPERIMENT} with this registration file's SHA-256"
        )
    try:
        pins = ks.check_code_pins(registration, root)
    except ks.KeepsetError as exc:
        raise Am3gError(f"{VOID_DIGEST}: {exc}") from exc
    return {"population": population, "frozen_required": True, "registration_frozen": True,
            "code_pins": pins}  # fmt: skip


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT:
        raise Am3gError(f"not the {EXPERIMENT} config")
    if config.get("claim_level") != "confirmatory":
        raise Am3gError("the registration's config is confirmatory")
    if config.get("seeds") != [42, 43, 44]:
        raise Am3gError("seeds must be [42, 43, 44]")
    req = config["requests"]
    if int(req["pool_size"]) != K or int(req["budget"]) != BUDGET:
        raise Am3gError("4-subsets of pools of 8")
    pilot = load_pilot_config(config)
    am3_config = load_am3_config(config)
    if config["readers"] != am3_config["readers"]:
        raise Am3gError("the readers are AM3's, unchanged (model, revision, engine, template)")
    if config["reader_sampling"] != pilot["reader"]["sampling"]:
        raise Am3gError("reader sampling is the pilot reader's (greedy, 64 tokens)")
    ids = [r["id"] for r in config["readers"]]
    if ids != list(H2_READERS) or not set(H1_READERS) <= set(ids) or ANCHOR not in ids:
        raise Am3gError("the readers are qwen3-8b (anchor), OLMo-2 and Qwen3.5-9B, in order")
    anchor = next(r for r in config["readers"] if r["id"] == ANCHOR)
    if anchor.get("role") != "anchor" or anchor["engine"] != pilot["reader"]["engine"]:
        raise Am3gError("the anchor is AM1's reader in AM1's engine")
    models = config["models"]
    for r in config["readers"]:
        pin = models.get(r["model_id"])
        if not pin or pin["revision"] != r["revision"] or pin["receipt_root"] != r["receipt_root"]:
            raise Am3gError(f"{r['id']}: its model pin differs from the reader block")
    for which in JUDGES:
        j = pilot["judge"][which]
        pin = models.get(j["model_id"])
        if not pin or pin["revision"] != j["revision"] or pin["receipt_root"] != j["receipt_root"]:
            raise Am3gError(f"judge {which}: its model pin differs from the pilot's judge")
    for model_id, pin in models.items():
        for key in ("receipt_sha256", "artifact_root_sha256"):
            if not _is_digest(pin.get(key)):
                raise Am3gError(f"models.{model_id}.{key} must be a SHA-256")
    abs_judge = config["abstention_judge"]
    if abs_judge["template_sha256"] != abstention_template_sha256():
        raise Am3gError("the abstention template differs from its pin")
    if abs_judge["template_sha256"] != ABSTENTION_TEMPLATE_SHA256:
        raise Am3gError("the config's abstention template pin differs from the code's")
    if abs_judge["decoy_seed"] not in config["seeds"]:
        raise Am3gError("abstention_judge.decoy_seed must be a declared seed")
    if answer_templates_sha256() != ANSWER_TEMPLATES_SHA256:
        raise Am3gError("LongMemEval's answer-check templates differ from AM1's pin")
    pops = config["populations"]
    if sorted(pops) != sorted(POPULATIONS):
        raise Am3gError("populations: development, heldout, abstention")
    for name, spec in pops.items():
        arms = tuple(spec["arms"])
        expected_arms = ("retrieved",) if name == "abstention" else ARMS
        if arms != expected_arms:
            raise Am3gError(f"{name}: arms must be {expected_arms}")
        for key in ("artifact_sha256", "question_ids_sha256"):
            if not _is_digest(spec.get(key)):
                raise Am3gError(f"populations.{name}.{key} must be a SHA-256")
        if not isinstance(spec.get("questions"), int) or spec["questions"] < 1:
            raise Am3gError(f"populations.{name}.questions must be a positive integer")
    steps = config["steps"]
    step_ids = [s["id"] for s in steps]
    if len(set(step_ids)) != len(step_ids):
        raise Am3gError("step ids must be unique")
    seen: list[str] = []
    for s in steps:
        if s["kind"] == "reader":
            if s["reader"] not in ids:
                raise Am3gError(f"{s['id']}: unknown reader")
        elif s["kind"] == "judge":
            if s.get("judge") not in JUDGES or s["id"] != JUDGE_STEP[s["judge"]]:
                raise Am3gError(f"{s['id']}: judge steps are judge32 and judge8")
        else:
            raise Am3gError(f"{s['id']}: unknown step kind")
        for key in ("batch_invariant", "enforce_eager"):
            if not isinstance(s.get(key), bool):
                raise Am3gError(f"{s['id']}: {key} must be a boolean")
        if not s["enforce_eager"]:
            raise Am3gError(f"{s['id']}: every engine runs eager")
        if s["kind"] == "judge" and not s["batch_invariant"]:
            raise Am3gError(f"{s['id']}: the judges run batch-invariant")
        other = s.get("only_if_incomplete")
        if other is not None:
            prior = next((p for p in steps if p["id"] == other), None)
            if other not in seen or prior is None or prior.get("reader") != s.get("reader"):
                raise Am3gError(f"{s['id']}: only_if_incomplete names no earlier step")
        seen.append(s["id"])
    for s in steps:
        if s.get("reader") == ANCHOR and not s["batch_invariant"]:
            raise Am3gError("the anchor runs batch-invariant only")
    if {s.get("reader") for s in steps if s["kind"] == "reader"} != set(ids):
        raise Am3gError("every reader has a step")
    jobs = config["jobs"]
    if sorted(jobs) != sorted(POPULATIONS):
        raise Am3gError("one job per population")
    for name, job in jobs.items():
        if int(job["gpus"]) != 1:
            raise Am3gError(f"jobs.{name}: one GPU")
        budgets = job["step_budgets"]
        if sorted(budgets) != sorted(step_ids):
            raise Am3gError(f"jobs.{name}: a budget for every step")
        for sid, (min_start, max_s) in budgets.items():
            if not 0 < int(max_s) < int(min_start) < int(job["minutes"]) * 60:
                raise Am3gError(f"jobs.{name}.{sid}: 0 < max_s < min_start_s < the limit")
    return config


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and not set(value) - set("0123456789abcdef")


def load_pilot_config(config: dict[str, Any]) -> dict[str, Any]:
    spec = config["pilot"]
    path = PROJECT_ROOT / spec["config"]
    if sha256_file(path) != spec["config_sha256"]:
        raise Am3gError("the pilot config differs from its pinned SHA-256")
    pilot = ms.load_config(path)
    if pilot["experiment_id"] != ms.EXPERIMENT_ID:
        raise Am3gError("the prompt and judges come from the development pilot's config")
    return pilot


def load_am3_config(config: dict[str, Any]) -> dict[str, Any]:
    spec = config["am3"]
    path = PROJECT_ROOT / spec["config"]
    if sha256_file(path) != spec["config_sha256"]:
        raise Am3gError("AM3's config differs from its pinned SHA-256")
    return am3.load_config(path)


def population_spec(config: dict[str, Any], population: str) -> dict[str, Any]:
    if population not in POPULATIONS:
        raise Am3gError(f"unknown population {population}")
    return config["populations"][population]


def population_arms(config: dict[str, Any], population: str) -> tuple[str, ...]:
    return tuple(population_spec(config, population)["arms"])


def reader_spec(config: dict[str, Any], reader_id: str) -> dict[str, Any]:
    for r in config["readers"]:
        if r["id"] == reader_id:
            return r
    raise Am3gError(f"unknown reader {reader_id}")


def step_spec(config: dict[str, Any], step_id: str) -> dict[str, Any]:
    for s in config["steps"]:
        if s["id"] == step_id:
            return s
    raise Am3gError(f"unknown step {step_id}")


def step_budget(config: dict[str, Any], population: str, step_id: str) -> tuple[int, int]:
    min_start, max_s = config["jobs"][population]["step_budgets"][step_id]
    return int(min_start), int(max_s)


def model_spec(config: dict[str, Any], pilot: dict[str, Any], step: dict[str, Any]) -> dict:
    if step["kind"] == "reader":
        r = reader_spec(config, step["reader"])
        return {"model_id": r["model_id"], "revision": r["revision"],
                "receipt_root": r["receipt_root"], "engine": r["engine"],
                "enable_thinking": bool(r["enable_thinking"]), "stop_token": r["stop_token"],
                "sampling": config["reader_sampling"]}  # fmt: skip
    j = pilot["judge"][step["judge"]]
    return {"model_id": j["model_id"], "revision": j["revision"], "receipt_root": j["receipt_root"],
            "engine": j["engine"], "enable_thinking": bool(pilot["judge"]["enable_thinking"]),
            "stop_token": s0.END_OF_TURN, "sampling": pilot["judge"]["sampling"]}  # fmt: skip


# --------------------------------------------------------------------------- study artifacts


def load_artifact(
    config: dict[str, Any], population: str, path: Path | str, expected_sha256: str | None = None
) -> dict[str, Any]:
    """The population's pinned study artifact, after the gate (the caller runs it)."""

    spec = population_spec(config, population)
    if population == "development":
        check_dev_path(path)
    raw = Path(path).read_bytes()
    digest = sha256_bytes(raw)
    if digest != spec["artifact_sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: the {population} artifact {path} is not the pinned one")
    if expected_sha256 is not None and digest != expected_sha256:
        raise Am3gError(f"{VOID_DIGEST}: the {population} artifact differs from the expected SHA")
    artifact = json.loads(raw)
    check_artifact(config, population, artifact)
    return artifact


def check_artifact(config: dict[str, Any], population: str, artifact: dict[str, Any]) -> None:
    spec = population_spec(config, population)
    if (
        artifact.get("experiment_id") != spec["experiment_id"]
        or artifact.get("split") != spec["split"]
    ):
        raise Am3gError(f"{VOID_DIGEST}: not the {population} population's artifact")
    ids = [q["question_id"] for q in artifact["questions"]]
    if len(ids) != spec["questions"] or ids_sha256(ids) != spec["question_ids_sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: the {population} question ids differ from their pin")
    for q in artifact["questions"]:
        is_abs = mc.is_abstention(q)
        if (population == "abstention") != is_abs or bool(q.get("abstention")) != is_abs:
            raise Am3gError(f"{q['question_id']}: abstention questions only in that population")
        for arm in population_arms(config, population):
            if len(q["pools"][arm]) != K:
                raise Am3gError(f"{q['question_id']}:{arm}: not a pool of {K}")


def retrieved_pool(record: dict[str, Any], pool_config: dict[str, Any]) -> list[dict[str, Any]]:
    """AM1's retrieved arm (``harness.memcredit.build_pools``, ``retrieved``): the BM25 top-k user
    turns, memories of at most ``max_memory_chars``, chronological. The gold arm is not built:
    it is not defined for abstention questions."""

    k = int(pool_config["pools"]["size"])
    max_chars = int(pool_config["pools"]["max_memory_chars"])
    ranked = mc.rank_user_turns(record, pool_config["retriever"])
    entries = [mc.memory_entry(t, r, s, max_chars) for r, (t, s) in enumerate(ranked)]
    pool = mc.chronological(entries[:k])
    if len(pool) != k:
        raise Am3gError(f"{record['question_id']}: the retrieved pool has {len(pool)} memories")
    return pool


def read_source(path: Path, pilot: dict[str, Any]) -> list[dict[str, Any]]:
    raw = Path(path).read_bytes()
    pinned = pilot["source"]
    if len(raw) != pinned["size_bytes"] or sha256_bytes(raw) != pinned["sha256"]:
        raise Am3gError("the LongMemEval-S file differs from the pinned size or SHA-256")
    return json.loads(raw)


def twin_membership(twin: str, by_id: dict[str, Any], split: dict[str, Any], excluded: set) -> str:
    if twin not in by_id:
        return "absent"
    if twin in excluded:
        return "step0-demo-excluded"
    if twin in split["development"]:
        return "development"
    if twin in split["heldout"]:
        return "heldout-confirmatory"
    return "not-usable"


def build_abstention_artifact(
    records: list[dict[str, Any]],
    pilot: dict[str, Any],
    split: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The abstention population: every LongMemEval-S question whose id ends in ``_abs``, sorted;
    per question its retrieved pool and one validation decoy (the reference answer of a
    development question of the same type, ``random.Random(f"{seed}:{question_id}")``). Returns
    (artifact, text-free twin and pool facts for the summary)."""

    by_id = {r["question_id"]: r for r in records}
    pool_config = ms.pool_config(pilot)
    seed = int(config["abstention_judge"]["decoy_seed"])
    dev_by_type: dict[str, list[str]] = {}
    for qid in split["development"]:
        dev_by_type.setdefault(by_id[qid]["question_type"], []).append(qid)
    excluded = set(load_registration_exclusions())
    questions = []
    facts = []
    for qid in sorted(r["question_id"] for r in records if mc.is_abstention(r)):
        record = by_id[qid]
        turns = mc.iter_turns(record)
        candidates = sorted(dev_by_type.get(record["question_type"], []))
        if not candidates:
            raise Am3gError(f"{qid}: no development question of type {record['question_type']}")
        decoy = random.Random(f"{seed}:{qid}").choice(candidates)
        pool = retrieved_pool(record, pool_config)
        questions.append({
            "question_id": qid,
            "question_type": record["question_type"],
            "question": record["question"],
            "answer": str(record["answer"]),
            "question_date": record["question_date"],
            "abstention": True,
            "gold_turns_total": sum(1 for t in turns if t.has_answer),
            "user_turns_total": sum(1 for t in turns if t.role == "user"),
            "pools": {"retrieved": pool},
            "validation_decoy": {"question_id": decoy, "answer": str(by_id[decoy]["answer"])},
        })  # fmt: skip
        twin = qid[: -len("_abs")]
        twin_sessions = set(by_id[twin]["haystack_session_ids"]) if twin in by_id else set()
        sessions = set(record["haystack_session_ids"])
        facts.append({
            "question_id": qid,
            "twin_question_id": twin,
            "twin_membership": twin_membership(twin, by_id, split, excluded),
            "sessions": len(sessions),
            "twin_sessions": len(twin_sessions),
            "shared_sessions": len(sessions & twin_sessions),
        })  # fmt: skip
    ids = [q["question_id"] for q in questions]
    artifact = {
        "experiment_id": EXPERIMENT,
        "claim_level": "confirmatory",
        "split": "abstention",
        "source": pilot["source"],
        "retriever": pilot["retriever"],
        "pools_config": pilot["pools"],
        "arms": ["retrieved"],
        "decoy_rule": f"random.Random(f'{seed}:{{question_id}}').choice(sorted development ids "
        "of the same question type)",
        "question_ids_sha256": ids_sha256(ids),
        "questions": questions,
    }
    return artifact, {"twins": facts}


def load_registration_exclusions() -> list[str]:
    """Step 0's eight demo questions, which AM1 excluded from its confirmatory set."""

    am1 = yaml.safe_load(ms.REGISTRATION_CONFIG_PATH.read_text(encoding="utf-8"))
    return list(am1["confirmatory_set"]["exclude_question_ids"])


def abstention_summary(
    artifact: dict[str, Any], digest: str, facts: dict[str, Any], pilot: dict[str, Any]
) -> dict[str, Any]:
    """The artifact without LongMemEval text: ids, types, digests of the question, explanation and
    every memory, pool coordinates, BM25 ranks and scores, decoy ids, twin facts and the
    full-pool prompt's length in characters."""

    twins = {f["question_id"]: f for f in facts["twins"]}
    questions = []
    for q in artifact["questions"]:
        pool = q["pools"]["retrieved"]
        full = mc.user_message(q, pool, pilot["prompt"])
        questions.append({
            "question_id": q["question_id"],
            "question_type": q["question_type"],
            "question_sha256": sha256_text(q["question"]),
            "answer_sha256": sha256_text(q["answer"]),
            "gold_turns_total": q["gold_turns_total"],
            "user_turns_total": q["user_turns_total"],
            "gold_in_pool": sum(bool(m["is_gold"]) for m in pool),
            "pool": [{k: v for k, v in m.items() if k != "text"} for m in pool],
            "full_pool_prompt_chars": len(full),
            "validation_decoy_question_id": q["validation_decoy"]["question_id"],
            "twin": twins[q["question_id"]],
        })  # fmt: skip
    by_type = Counter(q["question_type"] for q in artifact["questions"])
    membership = Counter(f["twin_membership"] for f in facts["twins"])
    return {
        "experiment_id": artifact["experiment_id"],
        "split": artifact["split"],
        "artifact_sha256": digest,
        "questions": len(questions),
        "question_ids_sha256": artifact["question_ids_sha256"],
        "question_ids": [q["question_id"] for q in artifact["questions"]],
        "by_type": dict(sorted(by_type.items())),
        "twin_membership": dict(sorted(membership.items())),
        "max_full_pool_prompt_chars": max(q["full_pool_prompt_chars"] for q in questions),
        "source": artifact["source"],
        "retriever": artifact["retriever"],
        "pools_config": artifact["pools_config"],
        "decoy_rule": artifact["decoy_rule"],
        "per_question": questions,
    }


def check_dev_retrieved_pools(
    records: list[dict[str, Any]], pilot: dict[str, Any], dev_artifact: dict[str, Any]
) -> dict[str, Any]:
    """The retrieved-arm builder reproduces the development artifact's retrieved pools (built by
    ``harness.memcredit.build_pools`` through AM1's prepare script), memory for memory."""

    by_id = {r["question_id"]: r for r in records}
    pool_config = ms.pool_config(pilot)
    same = 0
    for q in dev_artifact["questions"]:
        same += retrieved_pool(by_id[q["question_id"]], pool_config) == q["pools"]["retrieved"]
    return {"questions": len(dev_artifact["questions"]), "retrieved_pools_identical": same}


def cmd_prepare_abstention(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    for p in (args.artifact, args.summary):
        if Path(p).exists():
            raise Am3gError(f"refusing to overwrite {p}")
    refuse_inside_repo(args.artifact)
    split = ms.load_split(Path(args.split_file), pilot)
    if sha256_file(Path(args.split_file)) != config["split_file_sha256"]:
        raise Am3gError("the split file differs from its pin")
    records = read_source(Path(args.source), pilot)
    artifact, facts = build_abstention_artifact(records, pilot, split, config)
    data = mc.canonical_json(artifact)
    digest = sha256_bytes(data)
    summary = abstention_summary(artifact, digest, facts, pilot)
    if args.dev_artifact:
        check_dev_path(args.dev_artifact)
        dev = load_artifact(config, "development", args.dev_artifact)
        summary["dev_retrieved_pool_check"] = check_dev_retrieved_pools(records, pilot, dev)
    Path(args.artifact).write_bytes(data)
    Path(args.summary).write_bytes(mc.canonical_json(summary))
    spec = population_spec(config, "abstention")
    return {
        "artifact_sha256": digest,
        "artifact_bytes": len(data),
        "questions": summary["questions"],
        "question_ids_sha256": summary["question_ids_sha256"],
        "by_type": summary["by_type"],
        "twin_membership": summary["twin_membership"],
        "max_full_pool_prompt_chars": summary["max_full_pool_prompt_chars"],
        "matches_config_pins": digest == spec["artifact_sha256"]
        and summary["question_ids_sha256"] == spec["question_ids_sha256"]
        and summary["questions"] == spec["questions"],
        "dev_retrieved_pool_check": summary.get("dev_retrieved_pool_check"),
        "summary_sha256": sha256_file(Path(args.summary)),
    }


# --------------------------------------------------------------------------- requests


def request_table(artifact: dict[str, Any], arms: Sequence[str]) -> list[dict[str, Any]]:
    """Every (question, arm, mask) request in canonical order: question, arm, then the 70 4-subset
    masks ascending and the full pool. For both arms it is AM3's request table."""

    table: list[dict[str, Any]] = []
    for q_index, question in enumerate(artifact["questions"]):
        for arm in arms:
            for mask in REQUEST_MASKS:
                table.append({"index": len(table), "question_index": q_index,
                              "question_id": question["question_id"], "arm": arm,
                              "kind": "table", "mask": mask})  # fmt: skip
    return table


def reader_messages(
    pilot: dict[str, Any], artifact: dict[str, Any], arms: Sequence[str]
) -> list[str]:
    return [ms.request_message(artifact, r, pilot["prompt"]) for r in request_table(artifact, arms)]


# --------------------------------------------------------------------------- judge


def validation_items(
    artifact: dict[str, Any], pilot: dict[str, Any], config: dict[str, Any], population: str
) -> list[dict[str, Any]]:
    """Answerable populations: AM1's validation items (per question the reference answer, "I don't
    know." and another same-type question's answer, by the seeded derangement). The development
    dry run adds two calibration items per question under the abstention template (a generic
    explanation; "I don't know." and the reference answer). Abstention population: per question
    its explanation (expected yes), "I don't know." (expected yes) and the decoy answer (no)."""

    spec = config["abstention_judge"]
    if population == "abstention":
        items: list[dict[str, Any]] = []
        for q_index, q in enumerate(artifact["questions"]):
            items.append({"question_index": q_index, "response": str(q["answer"]),
                          "source": "validation:abs-explanation", "expected": 1})  # fmt: skip
            items.append({"question_index": q_index, "response": str(spec["idk_response"]),
                          "source": "validation:abs-idk", "expected": 1})  # fmt: skip
            decoy = q["validation_decoy"]
            items.append({"question_index": q_index, "response": str(decoy["answer"]),
                          "source": "validation:abs-decoy", "expected": 0,
                          "decoy_question_id": decoy["question_id"]})  # fmt: skip
        return items
    items = ms.validation_items(artifact, pilot["judge"]["validation"])
    if population == "development":
        for q_index, q in enumerate(artifact["questions"]):
            for source, response in (
                ("calibration:abs-template-idk", spec["idk_response"]),
                ("calibration:abs-template-reference", str(q["answer"])),
            ):
                items.append({"question_index": q_index, "response": str(response),
                              "source": source, "template": "abstention",
                              "explanation": spec["calibration_explanation"]})  # fmt: skip
    return items


def judge_items(
    artifact: dict[str, Any],
    pilot: dict[str, Any],
    config: dict[str, Any],
    population: str,
    passes: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply) over the given reader passes (step id -> request
    index -> reply), then the population's validation items, in the pilot's canonical order."""

    requests = request_table(artifact, population_arms(config, population))
    n = len(requests)
    replies: dict[int, str] = {}
    extended: list[dict[str, Any]] = []
    for k, step_id in enumerate(sorted(passes)):
        for index, text in passes[step_id].items():
            replies[k * n + index] = text
        extended += [dict(r, index=k * n + r["index"]) for r in requests]
    validation = validation_items(artifact, pilot, config, population)
    return ms.judge_item_table(artifact, replies, extended, validation)


def judge_message(artifact: dict[str, Any], item: dict[str, Any]) -> str:
    """LongMemEval's official answer-check prompt: the abstention template for an abstention
    question (its explanation in place of the answer), the type's template otherwise (AM1's)."""

    q = artifact["questions"][item["question_index"]]
    if item.get("template") == "abstention":
        return ABSTENTION_TEMPLATE.format(q["question"], item["explanation"], item["response"])
    if q.get("abstention"):
        if not mc.is_abstention(q):
            raise Am3gError(f"{q['question_id']} is flagged abstention without the _abs suffix")
        return ABSTENTION_TEMPLATE.format(q["question"], str(q["answer"]), item["response"])
    if mc.is_abstention(q):
        raise Am3gError(f"{q['question_id']} is an abstention question without the flag")
    return ms.judge_message(artifact, item)


# --------------------------------------------------------------------------- vLLM worker


def vllm_worker(args: argparse.Namespace) -> int:
    import vllm.envs as vllm_envs
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    population = args.population
    gate(population)
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    arms = population_arms(config, population)
    step = step_spec(config, args.step)
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

    spec = model_spec(config, pilot, step)
    model_dir = am3.MODEL_ROOT / spec["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    if step["kind"] == "reader":
        messages = reader_messages(pilot, artifact, arms)
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


# --------------------------------------------------------------------------- driver


def run_step(
    step: dict[str, Any], args: argparse.Namespace, out: Path, stop_at: float,
    state: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Start one worker, wait for it, kill it when hung or late; return its record."""

    argv = [sys.executable, str(Path(__file__).resolve()), "worker", "--population",
            args.population, "--step", step["id"], "--config", args.config, "--output-dir",
            str(out), "--deadline", f"{stop_at:.3f}", "--evidence", args.evidence,
            "--expected-evidence-sha256", args.expected_evidence_sha256]  # fmt: skip
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


def reader_steps_complete(summary: dict[str, Any]) -> list[str]:
    return [
        sid
        for sid, rec in summary.get("steps", {}).items()
        if rec.get("kind") == "reader" and rec.get("status") == "complete"
    ]


def verify_models(config: dict[str, Any], pilot: dict[str, Any]) -> dict[str, Any]:
    """Every model against its receipt (``harness.g2_pilot.verify_model``) and against the
    config's pins: revision, receipt SHA-256 and snapshot root. Raises on any difference."""

    verified: dict[str, Any] = {}
    specs = [model_spec(config, pilot, s) for s in config["steps"]]
    primary = pilot["judge"]["primary"]["model_id"]
    for spec in sorted(specs, key=lambda s: s["model_id"] != primary):
        key = spec["model_id"]
        if key in verified:
            continue
        started = time.time()
        record = lane.verify_model(key, spec["receipt_root"])
        pin = config["models"][key]
        for field in ("revision", "receipt_sha256", "artifact_root_sha256"):
            if record.get(field) != pin[field]:
                raise Am3gError(f"{VOID_DIGEST}: {key} {field} {record.get(field)} != {pin[field]}")
        record["wall_s"] = round(time.time() - started, 1)
        verified[key] = record
    return verified


def run_main(args: argparse.Namespace) -> int:
    population = args.population
    gate(population)
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    if list(args.seeds) != config["seeds"]:
        raise Am3gError("--seeds must equal the config's declared seeds")
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    arms = population_arms(config, population)
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
        "arms": list(arms),
        "reader_requests_per_reader": len(request_table(artifact, arms)),
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
        summary["model_verification"] = verify_models(config, pilot)
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
            sources = reader_steps_complete(summary)
            if not sources:
                record.update(status="skipped", reason="no reader pass completed")
                continue
            if not (out / "judge-items.json").is_file():
                passes = {
                    sid: am3.completed_replies(load_pass(out / "sessions" / sid)) for sid in sources
                }
                items = judge_items(artifact, pilot, config, population, passes)
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
    readers_done = {summary["steps"][s].get("reader") for s in reader_steps_complete(summary)}
    judges_done = all(
        summary["steps"].get(JUDGE_STEP[j], {}).get("status") == "complete" for j in JUDGES
    )
    return 0 if readers_done == set(H2_READERS) and judges_done else 3


def load_pass(session_dir: Path, name: str = "all") -> dict[str, Any]:
    import memcredit_study as driver

    return driver.load_pass(session_dir, name)


# --------------------------------------------------------------------------- plan and selftest


def build_plan(config: dict[str, Any], population: str, artifact: dict[str, Any]) -> dict:
    arms = population_arms(config, population)
    job = config["jobs"][population]
    return {
        "experiment_id": EXPERIMENT,
        "population": population,
        "questions": len(artifact["questions"]),
        "arms": list(arms),
        "pools": len(artifact["questions"]) * len(arms),
        "requests_per_pool": len(REQUEST_MASKS),
        "requests_per_reader": len(request_table(artifact, arms)),
        "readers": [r["id"] for r in config["readers"]],
        "steps": [s["id"] for s in config["steps"]],
        "job_minutes": job["minutes"],
        "gpus": job["gpus"],
    }


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only, no engine: every request rendered with every reader's tokenizer and chat
    template, the judge items (with a placeholder reply per pool) with both judges'; lengths,
    thinking-off markers, stop tokens and vLLM's architecture resolution. The held-out population
    needs the freeze; the abstention population's pools may be checked before it (no model
    output is produced)."""

    from transformers import AutoTokenizer

    population = args.population
    if population == "heldout":
        gate(population)
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    artifact = load_artifact(config, population, args.evidence, args.expected_evidence_sha256)
    arms = population_arms(config, population)
    root = Path(args.model_root)
    report: dict[str, Any] = {"plan": build_plan(config, population, artifact), "readers": {}}
    messages = reader_messages(pilot, artifact, arms)
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
    placeholder = {
        "selftest": {
            r["index"]: str(config["abstention_judge"]["idk_response"])
            for r in request_table(artifact, arms)
            if r["mask"] == FULL
        }
    }
    items = judge_items(artifact, pilot, config, population, placeholder)
    report["judges"] = {}
    for which in JUDGES:
        spec = pilot["judge"][which]
        tok = AutoTokenizer.from_pretrained(str(root / spec["model_id"]))
        lengths = [len(s0.render_prompt_ids(tok, judge_message(artifact, i), False))
                   for i in items]  # fmt: skip
        fits = (
            max(lengths)
            <= spec["engine"]["max_model_len"] - pilot["judge"]["sampling"]["max_tokens"]
        )
        report["judges"][which] = {"model_id": spec["model_id"], "items": len(items),
                                   "len_max": max(lengths), "fits": fits}  # fmt: skip
        ok &= fits
    report["judge_templates"] = {
        "abstention_sha256": abstention_template_sha256(),
        "answer_sha256": answer_templates_sha256(),
        "items_by_template": dict(Counter(
            "abstention" if (i.get("template") == "abstention"
                             or artifact["questions"][i["question_index"]].get("abstention"))
            else "answer" for i in items)),
    }  # fmt: skip
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


def pool_records(
    artifact: dict[str, Any],
    arms: Sequence[str],
    reader_rows: dict[int, dict[str, Any]],
    item_of: dict[tuple[int, str], int],
    labels: dict[str, dict[int, int]],
) -> list[dict[str, Any]]:
    """Per pool of one reader pass: per requested mask the judged labels, the abstention flag and
    pattern, the finish reason, the token count and the normalized reply's SHA-256. No text.
    (AM3's ``pool_records`` for any set of arms.)"""

    pools: dict[tuple[int, str], dict[str, Any]] = {}
    for r in request_table(artifact, arms):
        key = (int(r["question_index"]), r["arm"])
        q = artifact["questions"][key[0]]
        if key not in pools:
            pool = q["pools"][r["arm"]]
            pools[key] = {
                "question_id": q["question_id"],
                "question_type": q["question_type"],
                "arm": r["arm"],
                "bm25_rank": [int(m["bm25_rank"]) for m in pool],
                "gold_mask": sum(1 << i for i, m in enumerate(pool) if m["is_gold"]),
                "masks": {},
            }
        row = reader_rows.get(r["index"])
        text = row["text"] if row and row["finish"] in ("stop", "length") else None
        cell: dict[str, Any] = {"finish": row["finish"] if row else None}
        if text is None:
            cell.update(u={j: None for j in JUDGES}, abstain=None, pattern=None, digest=None)
        else:
            item = item_of.get((key[0], text.strip()))
            cell["u"] = {j: (labels[j].get(item) if item is not None else None) for j in JUDGES}
            cell["abstain"], cell["pattern"] = lf.abstention(text)
            normalized = mc.normalize_answer(text.strip())
            cell["digest"] = sha256_text(normalized)
            cell["n_tokens"] = len(row["tokens"])
        pools[key]["masks"][int(r["mask"])] = cell
    return [pools[k] for k in sorted(pools)]


def validation_summary(
    items: Sequence[dict[str, Any]], labels: dict[str, dict[int, int]]
) -> dict[str, Any]:
    """Per judge and validation source: items, yes, missing. AM1's reference count leaves out
    single-session-preference questions (a rubric, not an answer)."""

    sources = sorted({i["source"] for i in items if i["source"] != "reader"})
    out: dict[str, Any] = {}
    for j in JUDGES:
        cell: dict[str, Any] = {}
        for source in sources:
            chosen = [i for i in items if i["source"] == source]
            if source == "validation:reference":
                chosen = [i for i in chosen if i["question_type"] != "single-session-preference"]
            got = [labels[j].get(i["index"]) for i in chosen]
            cell[source] = {"items": len(chosen), "yes": sum(1 for g in got if g == 1),
                            "missing": sum(1 for g in got if g is None)}  # fmt: skip
        out[j] = cell
    return out


def check_pinned_files(run_dir: Path, pinned: dict[str, str]) -> dict[str, str]:
    out = {}
    for relative, expected in sorted(pinned.items()):
        try:
            actual = sha256_file(run_dir / relative)
        except OSError as exc:
            raise Am3gError(f"{VOID_DIGEST}: {relative} is missing or unreadable: {exc}") from exc
        if actual != expected:
            raise Am3gError(f"{VOID_DIGEST}: {relative}: SHA-256 {actual} is not {expected}")
        out[relative] = actual
    return out


def compare_with_reference(
    artifact: dict[str, Any],
    arms: Sequence[str],
    new_rows: dict[int, dict[str, Any]],
    new_labels: dict[str, dict[int, int]],
    new_item_of: dict[tuple[int, str], int],
    ref_rows: dict[int, dict[str, Any]],
    ref_index: dict[tuple[int, str, int], int],
    ref_labels: dict[str, dict[int, int] | None],
    ref_item_of: dict[tuple[int, str], int],
) -> dict[str, Any]:
    """Request by request at the same (question, arm, mask): identical tokens and finish reason,
    identical log-prob bits, identical text; per judge, label agreement over all compared cells
    and over cells whose replies are identical. Differences are listed by (question, arm, mask)."""

    out: dict[str, Any] = {"cells": 0, "compared": 0, "identical_tokens": 0, "identical_bits": 0,
                           "identical_text": 0, "token_differences": []}  # fmt: skip
    for j in JUDGES:
        out[f"label_same_{j}"] = out[f"label_compared_{j}"] = 0
        out[f"label_same_identical_reply_{j}"] = out[f"label_compared_identical_reply_{j}"] = 0
    done = ("stop", "length")
    for r in request_table(artifact, arms):
        out["cells"] += 1
        a = new_rows.get(r["index"])
        b = ref_rows.get(ref_index[(r["question_index"], r["arm"], r["mask"])])
        if a is None or b is None or a["finish"] not in done or b["finish"] not in done:
            continue
        out["compared"] += 1
        same_tok = a["tokens"] == b["tokens"] and a["finish"] == b["finish"]
        out["identical_tokens"] += same_tok
        out["identical_bits"] += same_tok and a["bits"] == b["bits"]
        if not same_tok:
            out["token_differences"].append(
                {"question_id": r["question_id"], "arm": r["arm"], "mask": r["mask"]}
            )
        same_text = a["text"] == b["text"]
        out["identical_text"] += same_text
        for j in JUDGES:
            if ref_labels.get(j) is None:
                continue
            la = new_labels[j].get(new_item_of.get((r["question_index"], a["text"].strip())))
            lb = ref_labels[j].get(ref_item_of.get((r["question_index"], b["text"].strip())))
            if la is None or lb is None:
                continue
            out[f"label_compared_{j}"] += 1
            out[f"label_same_{j}"] += la == lb
            if same_text:
                out[f"label_compared_identical_reply_{j}"] += 1
                out[f"label_same_identical_reply_{j}"] += la == lb
    return out


def load_heldout_tables(config: dict[str, Any]) -> list[dict[str, Any]]:
    """AM1's committed held-out tables (after the gate), checked against both pinned digests."""

    spec = population_spec(config, "heldout")["tables"]
    raw = (PROJECT_ROOT / spec["path"]).read_bytes()
    if sha256_bytes(raw) != spec["sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: the held-out tables' gz differs from its pin")
    data = gzip.decompress(raw)
    if sha256_bytes(data) != spec["json_sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: the held-out tables differ from AM1's tables.json")
    return json.loads(data)


def labels_vs_tables(pools: Sequence[dict[str, Any]], tables: Sequence[dict[str, Any]]) -> dict:
    """The anchor's primary-judge labels against AM1's committed tables (values_hex; bit m is
    u(mask m)) at the 71 requested masks of every pool."""

    by_key = {(t["question_id"], t["arm"]): cc.decode_values(t["values_hex"]) for t in tables}
    cells = same = 0
    differing: list[dict[str, Any]] = []
    for p in pools:
        values = by_key[(p["question_id"], p["arm"])]
        for mask in REQUEST_MASKS:
            u = p["masks"][mask]["u"]["primary"]
            cells += 1
            if u is not None and float(u) == values[mask]:
                same += 1
            else:
                differing.append({"question_id": p["question_id"], "arm": p["arm"], "mask": mask,
                                  "committed": values[mask], "anchor": u})  # fmt: skip
    return {"pools": len(pools), "cells": cells, "cells_same_label": same,
            "differing_cells": differing}  # fmt: skip


def item_replay(
    items: Sequence[dict[str, Any]],
    labels: dict[str, dict[int, int]],
    ref_items: Sequence[dict[str, Any]],
    ref_labels: dict[str, dict[int, int]],
) -> dict[str, Any]:
    """Per judge: the label of every item whose (question, response, source) the reference
    judged too, against the reference's label (the judge's own replay)."""

    ref_key = {(i["question_index"], i["response"], i["source"]): i["index"] for i in ref_items}
    out: dict[str, Any] = {}
    for j in JUDGES:
        compared = same = 0
        for i in items:
            r = ref_key.get((i["question_index"], i["response"], i["source"]))
            if r is None or ref_labels.get(j) is None:
                continue
            a, b = labels[j].get(i["index"]), ref_labels[j].get(r)
            if a is None or b is None:
                continue
            compared += 1
            same += a == b
        out[j] = {"compared": compared, "same": same}
    return out


def anchor_checks_heldout(
    config: dict[str, Any],
    artifact: dict[str, Any],
    anchor_rows: dict[int, dict[str, Any]],
    anchor_pools: Sequence[dict[str, Any]],
    labels: dict[str, dict[int, int]],
    item_of: dict[tuple[int, str], int],
    items: Sequence[dict[str, Any]],
    reference_dir: Path,
) -> dict[str, Any]:
    """R1: the anchor's replies against job 1458's reader pass (tokens at every requested cell);
    R2: its primary-judge labels against AM1's committed tables at every requested cell; and, as
    descriptions, the judges' item-level replay against job 1458's."""

    ref = population_spec(config, "heldout")["reference"]
    digests = check_pinned_files(reference_dir, ref["sha256"])
    ref_reader = load_pass(reference_dir / "sessions" / ref["reader"])
    ref_items = json.loads((reference_dir / "judge-items.json").read_text(encoding="utf-8"))
    ref_labels = {
        "primary": am3.labels_from_pass(load_pass(reference_dir / "sessions" / ref["judge"])),
        "secondary": am3.labels_from_pass(
            load_pass(reference_dir / "sessions" / ref["second_judge"])
        ),
    }
    ref_index = {
        (r["question_index"], r["arm"], r["mask"]): r["index"]
        for r in ms.request_table(artifact, ARMS)
        if r["kind"] == "table"
    }
    r1 = compare_with_reference(artifact, ARMS, anchor_rows, labels, item_of, ref_reader["rows"],
                                ref_index, ref_labels, am3.item_index(ref_items))  # fmt: skip
    tables = load_heldout_tables(config)
    r2 = labels_vs_tables(anchor_pools, tables)
    r1_pass = r1["compared"] == r1["cells"] == r1["identical_tokens"]
    expected_cells = len(artifact["questions"]) * len(ARMS) * len(REQUEST_MASKS)
    r2_pass = r2["cells"] == r2["cells_same_label"] == expected_cells
    return {
        "reference": ref["name"],
        "reference_sha256": digests,
        "r1_replies": {k: v for k, v in r1.items() if k != "token_differences"}
        | {"token_differences": r1["token_differences"][:200], "pass": r1_pass},
        "r2_labels_vs_tables": {k: v for k, v in r2.items() if k != "differing_cells"}
        | {"differing_cells": r2["differing_cells"][:200], "pass": r2_pass},
        "judge_item_replay": item_replay(items, labels, ref_items, ref_labels),
        "pass": r1_pass and r2_pass,
    }


def reference_checks_development(
    config: dict[str, Any],
    artifact: dict[str, Any],
    rows_of: dict[str, dict[int, dict[str, Any]]],
    labels: dict[str, dict[int, int]],
    item_of: dict[tuple[int, str], int],
    items: Sequence[dict[str, Any]],
    reference_dir: Path,
) -> dict[str, Any]:
    """The dry run against AM3's job 1466: every reader's replies at every cell, and both judges
    at the item level."""

    check_dev_path(reference_dir)
    ref = population_spec(config, "development")["reference"]
    digests = check_pinned_files(reference_dir, ref["sha256"])
    ref_items = json.loads((reference_dir / "judge-items.json").read_text(encoding="utf-8"))
    ref_labels = {j: am3.labels_from_pass(load_pass(reference_dir / "sessions" / JUDGE_STEP[j]))
                  for j in JUDGES}  # fmt: skip
    ref_index = {(r["question_index"], r["arm"], r["mask"]): r["index"]
                 for r in request_table(artifact, ARMS)}  # fmt: skip
    readers = {}
    for reader_id, step in ref["readers"].items():
        if reader_id not in rows_of:
            readers[reader_id] = {"missing": True}
            continue
        ref_rows = load_pass(reference_dir / "sessions" / step)["rows"]
        result = compare_with_reference(artifact, ARMS, rows_of[reader_id], labels, item_of,
                                        ref_rows, ref_index, ref_labels,
                                        am3.item_index(ref_items))  # fmt: skip
        result["token_differences"] = result["token_differences"][:200]
        readers[reader_id] = result
    return {"reference": ref["name"], "reference_sha256": digests, "readers": readers,
            "judge_item_replay": item_replay(items, labels, ref_items, ref_labels)}  # fmt: skip


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    population = args.population
    if population == "development":
        for p in (args.run_dir, args.evidence, args.private_dir, args.reference_run_dir):
            check_dev_path(p)
    gate(population)
    refuse_inside_repo(args.private_dir)
    config = load_config(Path(args.config))
    artifact = load_artifact(config, population, args.evidence)
    arms = population_arms(config, population)
    run_dir = Path(args.run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if summary.get("population") != population or summary.get("experiment_id") != EXPERIMENT:
        raise Am3gError("the run directory is not this population's run")
    items = json.loads((run_dir / "judge-items.json").read_text(encoding="utf-8"))
    labels = {
        j: am3.labels_from_pass(load_pass(run_dir / "sessions" / JUDGE_STEP[j]))
        if (run_dir / "sessions" / JUDGE_STEP[j] / "all.npz").is_file() else {}
        for j in JUDGES
    }  # fmt: skip
    item_of = am3.item_index(items)
    readers: dict[str, Any] = {}
    rows_of: dict[str, dict[int, dict[str, Any]]] = {}
    for sid in reader_steps_complete(summary):
        reader_id = summary["steps"][sid]["reader"]
        if reader_id in readers:
            raise Am3gError(f"two completed passes of {reader_id}")
        passed = load_pass(run_dir / "sessions" / sid)
        rows_of[reader_id] = passed["rows"]
        pools = pool_records(artifact, arms, passed["rows"], item_of, labels)
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
            "pools_complete_primary": sum(pool_complete(p, ("primary",)) for p in pools),
            "pools_complete": sum(pool_complete(p, JUDGES) for p in pools),
            "pools": pools,
        }
    validation = {
        "judge_items": len(items),
        "judge_items_reader": sum(1 for i in items if i["source"] == "reader"),
        "labelled": {j: len(labels[j]) for j in JUDGES},
        "judge_validation": validation_summary(items, labels),
        "judge_pass_sha256": {
            f"sessions/{JUDGE_STEP[j]}/{f}": sha256_file(run_dir / "sessions" / JUDGE_STEP[j] / f)
            for j in JUDGES
            for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
            if (run_dir / "sessions" / JUDGE_STEP[j] / f).is_file()
        },
        "judge_items_sha256": sha256_file(run_dir / "judge-items.json"),
    }
    comparisons: dict[str, Any] = {}
    if population == "heldout":
        if not args.reference_run_dir:
            raise Am3gError("the held-out population needs job 1458's run directory")
        if ANCHOR not in readers:
            comparisons["anchor"] = {"pass": False, "reason": "the anchor's pass is incomplete"}
        else:
            comparisons["anchor"] = anchor_checks_heldout(
                config, artifact, rows_of[ANCHOR], readers[ANCHOR]["pools"], labels, item_of,
                items, Path(args.reference_run_dir),
            )  # fmt: skip
    elif population == "development" and args.reference_run_dir:
        comparisons["am3_job_1466"] = reference_checks_development(
            config, artifact, rows_of, labels, item_of, items, Path(args.reference_run_dir)
        )
    if lf.patterns_sha256() != lf.ABSTENTION_PATTERNS_SHA256:
        raise Am3gError(f"{VOID_DIGEST}: the abstention patterns differ from AM1d's")
    spec = population_spec(config, population)
    payload = {
        "experiment": EXPERIMENT,
        "population": population,
        "arms": list(arms),
        "artifact_sha256": spec["artifact_sha256"],
        "question_ids_sha256": spec["question_ids_sha256"],
        "questions": len(artifact["questions"]),
        "abstention_patterns_sha256": lf.patterns_sha256(),
        "abstention_template_sha256": abstention_template_sha256(),
        "answer_templates_sha256": answer_templates_sha256(),
        "code_sha256": code_digests(),
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
        "comparisons": comparisons,
        "readers": readers,
    }
    private = Path(args.private_dir)
    private.mkdir(parents=True, exist_ok=True)
    target = private / f"features-{population}.json.gz"
    write_gz_json(target, payload)
    brief = {
        "population": population,
        "readers": {r: {k: v for k, v in d.items() if k != "pools"} for r, d in readers.items()},
        "validation": validation,
        "comparisons": _brief_comparisons(comparisons),
        "features_sha256": sha256_file(target),
    }
    return brief


def _brief_comparisons(comparisons: dict[str, Any]) -> dict[str, Any]:
    def strip(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items()
                    if k not in ("token_differences", "differing_cells")}  # fmt: skip
        return value

    return strip(comparisons)


def pool_complete(pool: dict[str, Any], judges: Sequence[str]) -> bool:
    return sorted(pool["masks"]) == sorted(REQUEST_MASKS) and all(
        c["abstain"] is not None and all(c["u"][j] is not None for j in judges)
        for c in pool["masks"].values()
    )


# --------------------------------------------------------------------------- analysis


def table_record(pool: dict[str, Any], judges: Sequence[str] = JUDGES) -> dict[str, Any]:
    """One pool's choices and outcomes (AM3's ``table_record``) under the judges whose labels are
    complete for it; ``u`` of a judge without complete labels is None."""

    complete = [j for j in judges if pool_complete(pool, (j,))]
    if "primary" not in complete:
        raise Am3gError(f"{VOID_INCOMPLETE}: {pool['question_id']}:{pool['arm']} lacks labels")
    if list(complete) == list(JUDGES):
        return am3.table_record(pool)
    masked = {**pool, "masks": {m: {**c, "u": {j: c["u"][j] if j in complete else 0
                                               for j in JUDGES}}
                                for m, c in pool["masks"].items()}}  # fmt: skip
    record = am3.table_record(masked)
    for j in JUDGES:
        if j not in complete:
            record["u"][j] = None
    return record


def int_masks(features: dict[str, Any]) -> None:
    for reader in features["readers"].values():
        for pool in reader["pools"]:
            pool["masks"] = {int(m): cell for m, cell in pool["masks"].items()}


def records_of(features: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Per reader, its per-pool records; every pool must have complete primary labels."""

    out: dict[str, list[dict[str, Any]]] = {}
    for reader_id, reader in features["readers"].items():
        incomplete = [p for p in reader["pools"] if not pool_complete(p, ("primary",))]
        if incomplete:
            raise Am3gError(f"{VOID_INCOMPLETE}: {reader_id}: {len(incomplete)} pools lack "
                            "replies or primary labels")  # fmt: skip
        out[reader_id] = [table_record(p) for p in reader["pools"]]
    return out


def outcomes(records: Sequence[dict[str, Any]], judge: str, rule: str) -> dict[str, float]:
    return {r["question_id"]: float(r["u"][judge][rule]) for r in records}


def holm(pvalues: dict[str, float], alpha: float = ALPHA) -> dict[str, dict[str, Any]]:
    """Holm's step-down adjustment: adjusted p_(i) = max over j <= i of min(1, (m - j + 1)
    p_(j)); a hypothesis is rejected when its adjusted p is at most alpha. Ties are ordered by
    name, which does not change any adjusted value."""

    order = sorted(pvalues, key=lambda k: (pvalues[k], k))
    m = len(order)
    out: dict[str, dict[str, Any]] = {}
    running = 0.0
    for i, key in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvalues[key]))
        out[key] = {"p": pvalues[key], "p_holm": running, "rank": i + 1,
                    "step_threshold": alpha / (m - i), "reject": running <= alpha}  # fmt: skip
    return out


def label_of(reject: bool, favour_rule: int, against_rule: int, labels: Sequence[str]) -> str:
    if reject and favour_rule > against_rule:
        return labels[0]
    if reject and favour_rule < against_rule:
        return labels[1]
    return labels[2]


def cp_interval(k: int, n: int) -> list[float]:
    return list(mc.clopper_pearson(k, n, 0.05)) if n else [0.0, 1.0]


def h1_block(
    records: dict[str, list[dict[str, Any]]], resamples: int, seed: int, alpha: float = ALPHA
) -> dict[str, Any]:
    """H1: nonabstain-BM25 against BM25 top 4, retrieved arm, primary judge, all questions, per H1
    reader; exact two-sided McNemar, Holm across the H1 readers."""

    per: dict[str, Any] = {}
    for reader_id in H1_READERS:
        rows = [r for r in records[reader_id] if r["arm"] == "retrieved"]
        per[reader_id] = ks.paired_reading(
            outcomes(rows, "primary", "nonabstain_bm25"), outcomes(rows, "primary", "bm25_top4"),
            H1_LABELS, resamples, seed, alpha=alpha, label_key="unadjusted_label",
        )  # fmt: skip
    adjusted = holm({r: per[r]["p_exact_mcnemar"] for r in H1_READERS}, alpha)
    for reader_id in H1_READERS:
        e = per[reader_id]
        e["holm"] = adjusted[reader_id]
        e["reading"] = label_of(adjusted[reader_id]["reject"], e["rule_right_base_wrong"],
                                e["rule_wrong_base_right"], H1_LABELS)  # fmt: skip
    return {"family": list(H1_READERS), "alpha": alpha, "correction": "holm",
            "arm": "retrieved", "judge": "primary", "readers": per}  # fmt: skip


def h2_block(
    records: dict[str, list[dict[str, Any]]],
    resamples: int,
    seed: int,
    alpha: float = ALPHA,
    judge: str = "primary",
) -> dict[str, Any]:
    """H2 (descriptive, registered estimand): on the abstention questions, b2 (BM25 top 4 judged
    correct, the rule's choice judged wrong) and c2 (the reverse) per reader; the cost rate b2/N
    with its Clopper-Pearson interval; both accuracies with theirs; the paired difference (rule
    minus BM25 top 4) with its exact conditional and bootstrap intervals; the exact McNemar test
    and Holm across the readers, as description labels that decide nothing."""

    per: dict[str, Any] = {}
    for reader_id in H2_READERS:
        rows = [r for r in records[reader_id] if r["arm"] == "retrieved"]
        if any(r["u"][judge] is None for r in rows):
            per[reader_id] = {"incomplete": True}
            continue
        entry = ks.paired_reading(
            outcomes(rows, judge, "nonabstain_bm25"), outcomes(rows, judge, "bm25_top4"),
            (H2_LABELS[1], H2_LABELS[0], H2_LABELS[2]), resamples, seed, alpha=alpha,
            label_key="unadjusted_description",
        )  # fmt: skip
        n = entry["questions"]
        b2, c2 = entry["rule_wrong_base_right"], entry["rule_right_base_wrong"]
        top4_right = sum(int(r["u"][judge]["bm25_top4"]) for r in rows)
        rule_right = sum(int(r["u"][judge]["nonabstain_bm25"]) for r in rows)
        entry.update({
            "b2_top4_right_rule_wrong": b2,
            "c2_rule_right_top4_wrong": c2,
            "cost_rate": b2 / n,
            "cost_rate_ci95_exact": cp_interval(b2, n),
            "net_loss_rate": (b2 - c2) / n,
            "bm25_top4_correct": top4_right,
            "bm25_top4_accuracy_ci95_exact": cp_interval(top4_right, n),
            "nonabstain_bm25_correct": rule_right,
            "nonabstain_bm25_accuracy_ci95_exact": cp_interval(rule_right, n),
            "rule_switches_from_top4": sum(r["nonabstain_mask"] != r["bm25_top4_mask"]
                                           for r in rows),
            "bm25_top4_abstains": sum(r["bm25_top4_abstains"] for r in rows),
        })  # fmt: skip
        per[reader_id] = entry
    complete = [r for r in H2_READERS if not per[r].get("incomplete")]
    adjusted = holm({r: per[r]["p_exact_mcnemar"] for r in complete}, alpha) if complete else {}
    for reader_id in complete:
        e = per[reader_id]
        e["holm"] = adjusted[reader_id]
        e["description"] = label_of(adjusted[reader_id]["reject"], e["b2_top4_right_rule_wrong"],
                                    e["c2_rule_right_top4_wrong"], H2_LABELS)  # fmt: skip
    return {"family": complete, "alpha": alpha, "correction": "holm", "arm": "retrieved",
            "judge": judge, "decides": False, "readers": per}  # fmt: skip


def by_type(
    records: Sequence[dict[str, Any]], judge: str, arm: str = "retrieved"
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    rows = [r for r in records if r["arm"] == arm and r["u"][judge] is not None]
    for qtype in sorted({r["question_type"] for r in rows}):
        sub = [r for r in rows if r["question_type"] == qtype]
        n = len(sub)
        top = sum(r["u"][judge]["bm25_top4"] for r in sub)
        rule = sum(r["u"][judge]["nonabstain_bm25"] for r in sub)
        full = sum(r["u"][judge]["all_8"] for r in sub)
        b = sum(1 for r in sub if r["u"][judge]["nonabstain_bm25"] > r["u"][judge]["bm25_top4"])
        c = sum(1 for r in sub if r["u"][judge]["nonabstain_bm25"] < r["u"][judge]["bm25_top4"])
        out[qtype] = {"questions": n, "bm25_top4": top / n, "nonabstain_bm25": rule / n,
                      "all_8": full / n, "rule_right_top4_wrong": b,
                      "rule_wrong_top4_right": c}  # fmt: skip
    return out


def break_even(gain: float, loss: float) -> float | None:
    """The unanswerable share at which the rule and BM25 top 4 are equally accurate, given the
    rule's net gain per answerable question and net loss per unanswerable question: 1 when it
    never loses (loss <= 0 <= gain), 0 when it never gains (gain <= 0 <= loss, not both 0),
    gain / (gain + loss) when both are positive, None otherwise."""

    if loss <= 0 <= gain:
        return 1.0
    if gain <= 0 <= loss:
        return 0.0
    if gain > 0 and loss > 0:
        return gain / (gain + loss)
    return None


def natural_mix(
    answerable: Sequence[dict[str, Any]],
    unanswerable: Sequence[dict[str, Any]],
    weights: dict[str, int],
    resamples: int,
    seed: int,
    judge: str = "primary",
) -> dict[str, Any]:
    """The rule minus BM25 top 4, over answerable plus unanswerable questions: the raw count over
    the questions run, the rate at LongMemEval-S's mix (weights: answerable, abstention), and the
    break-even unanswerable share, with percentile intervals from a bootstrap that resamples each
    population's questions separately (numpy default_rng(seed))."""

    import numpy as np

    d1 = np.array([float(r["u"][judge]["nonabstain_bm25"] - r["u"][judge]["bm25_top4"])
                   for r in answerable if r["arm"] == "retrieved"])  # fmt: skip
    d2 = np.array([float(r["u"][judge]["nonabstain_bm25"] - r["u"][judge]["bm25_top4"])
                   for r in unanswerable if r["arm"] == "retrieved"])  # fmt: skip
    total = weights["answerable"] + weights["abstention"]
    wa, wb = weights["answerable"] / total, weights["abstention"] / total
    gain, loss = float(d1.mean()), float(-d2.mean())
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, len(d1), size=(resamples, len(d1)))
    ib = rng.integers(0, len(d2), size=(resamples, len(d2)))
    g = d1[ia].mean(axis=1)
    lo_ = -d2[ib].mean(axis=1)
    mix = np.sort(wa * g - wb * lo_)
    pis = [break_even(float(a), float(b)) for a, b in zip(g, lo_, strict=True)]
    defined = sorted(p for p in pis if p is not None)

    def pct(values: Any, q: float) -> float | None:
        if len(values) == 0:
            return None
        return float(values[int(math.floor(q * (len(values) - 1))) if q < 0.5
                            else int(math.ceil(q * (len(values) - 1)))])  # fmt: skip

    return {
        "questions": {"answerable": len(d1), "unanswerable": len(d2)},
        "net_count": int(d1.sum() + d2.sum()),
        "gain_per_answerable": gain,
        "loss_per_unanswerable": loss,
        "weights": {"answerable": wa, "unanswerable": wb, "source": weights},
        "mix_rate": wa * gain - wb * loss,
        "mix_rate_ci95": [pct(mix, 0.025), pct(mix, 0.975)],
        "break_even_unanswerable_share": break_even(gain, loss),
        "break_even_ci95": [pct(defined, 0.025), pct(defined, 0.975)],
        "break_even_undefined_resamples": len(pis) - len(defined),
        "bootstrap": {"resamples": resamples, "seed": seed},
    }


def cells_of(
    records: dict[str, list[dict[str, Any]]], arms: Sequence[str], resamples: int, seed: int,
    alpha: float,
) -> dict[str, Any]:  # fmt: skip
    """Per reader x judge x arm: AM3's cell summary (accuracies of BM25 top 4, nonabstain-BM25, all
    8 and the oracle best 4; the paired comparisons; abstention; the stop rule's reads)."""

    cells: dict[str, Any] = {}
    for reader_id, rows in records.items():
        cells[reader_id] = {}
        for j in JUDGES:
            cells[reader_id][j] = {}
            for arm in arms:
                arm_rows = [r for r in rows if r["arm"] == arm]
                if any(r["u"][j] is None for r in arm_rows):
                    cells[reader_id][j][arm] = {"incomplete": True}
                    continue
                cells[reader_id][j][arm] = am3.cell_summary(arm_rows, j, resamples, seed, alpha)
    return cells


def check_features(features: dict[str, Any], config: dict[str, Any], population: str) -> None:
    """VOID (V1) when the features' provenance differs from the pins."""

    spec = population_spec(config, population)
    checks = {
        "experiment": (features.get("experiment"), EXPERIMENT),
        "population": (features.get("population"), population),
        "artifact_sha256": (features.get("artifact_sha256"), spec["artifact_sha256"]),
        "question_ids_sha256": (features.get("question_ids_sha256"), spec["question_ids_sha256"]),
        "abstention_patterns_sha256": (features.get("abstention_patterns_sha256"),
                                       lf.ABSTENTION_PATTERNS_SHA256),
        "abstention_template_sha256": (features.get("abstention_template_sha256"),
                                       ABSTENTION_TEMPLATE_SHA256),
        "answer_templates_sha256": (features.get("answer_templates_sha256"),
                                    ANSWER_TEMPLATES_SHA256),
    }  # fmt: skip
    bad = [k for k, (got, want) in checks.items() if got != want]
    if population != "development" and features.get("code_sha256") != code_digests():
        bad.append("code_sha256")
    if bad:
        raise Am3gError(f"{VOID_DIGEST}: the {population} features differ from the pins: {bad}")
    if sorted(features["readers"]) != sorted(H2_READERS):
        raise Am3gError(f"{VOID_INCOMPLETE}: the {population} job lacks a reader's complete pass")
    for reader_id, reader in features["readers"].items():
        if len(reader["pools"]) != spec["questions"] * len(spec["arms"]):
            raise Am3gError(f"{VOID_INCOMPLETE}: {reader_id}: pools differ from the population")


def judge_gate_answerable(validation: dict[str, Any]) -> dict[str, Any]:
    """G-J1 (AM1's G2 rule on its validation items): the primary judge says yes to at least 95%
    of reference answers (preference questions left out) and no to at least 95% of "I don't
    know."."""

    v = validation["judge_validation"]["primary"]
    ref, idk = v["validation:reference"], v["validation:idk"]
    ref_ok = ref["yes"] >= math.ceil(0.95 * ref["items"]) and ref["missing"] == 0
    idk_ok = idk["items"] - idk["yes"] >= math.ceil(0.95 * idk["items"]) and idk["missing"] == 0
    return {"reference_yes": [ref["yes"], ref["items"]], "idk_no": [idk["items"] - idk["yes"],
            idk["items"]], "pass": ref_ok and idk_ok}  # fmt: skip


def judge_gate_abstention(validation: dict[str, Any]) -> dict[str, Any]:
    """G-J2: on the abstention questions the primary judge says yes to "I don't know." on at
    least 95% of them and no to the decoy answer on at least 95%; the explanation's yes rate is
    reported."""

    v = validation["judge_validation"]["primary"]
    idk, decoy, expl = (v["validation:abs-idk"], v["validation:abs-decoy"],
                        v["validation:abs-explanation"])  # fmt: skip
    idk_ok = idk["yes"] >= math.ceil(0.95 * idk["items"]) and idk["missing"] == 0
    decoy_ok = (decoy["items"] - decoy["yes"] >= math.ceil(0.95 * decoy["items"])
                and decoy["missing"] == 0)  # fmt: skip
    return {"idk_yes": [idk["yes"], idk["items"]],
            "decoy_no": [decoy["items"] - decoy["yes"], decoy["items"]],
            "explanation_yes": [expl["yes"], expl["items"]],
            "pass": idk_ok and decoy_ok}  # fmt: skip


def anchor_h1(records: dict[str, list[dict[str, Any]]], resamples: int, seed: int) -> dict:
    """The anchor's own H-C counts on the held-out questions, both arms, primary judge: they must
    equal am1-keepset-search-v1's (retrieved 39 against 0; gold 31 against 0) when R1 and R2
    pass; reported, not tested."""

    out = {}
    for arm in ARMS:
        rows = [r for r in records[ANCHOR] if r["arm"] == arm]
        out[arm] = ks.paired_reading(
            outcomes(rows, "primary", "nonabstain_bm25"), outcomes(rows, "primary", "bm25_top4"),
            H1_LABELS, resamples, seed, label_key="unadjusted_description",
        )  # fmt: skip
    out["equals_am1_keepset_search"] = (
        out["retrieved"]["rule_right_base_wrong"],
        out["retrieved"]["rule_wrong_base_right"],
    ) == (39, 0) and (
        out["gold"]["rule_right_base_wrong"],
        out["gold"]["rule_wrong_base_right"],
    ) == (31, 0)
    return out


def descriptive_paired(
    records: dict[str, list[dict[str, Any]]], arm: str, judge: str, resamples: int, seed: int,
    readers: Sequence[str] = H2_READERS,
) -> dict[str, Any]:  # fmt: skip
    """nonabstain-BM25 against BM25 top 4 per reader at one arm and judge, with Holm across the
    given readers, as descriptions that decide nothing."""

    per = {}
    for reader_id in readers:
        rows = [r for r in records[reader_id] if r["arm"] == arm]
        if not rows or any(r["u"][judge] is None for r in rows):
            per[reader_id] = {"incomplete": True}
            continue
        per[reader_id] = ks.paired_reading(
            outcomes(rows, judge, "nonabstain_bm25"), outcomes(rows, judge, "bm25_top4"),
            H1_LABELS, resamples, seed, label_key="unadjusted_description",
        )  # fmt: skip
    done = [r for r in readers if not per[r].get("incomplete")]
    adjusted = holm({r: per[r]["p_exact_mcnemar"] for r in done}) if done else {}
    for reader_id in done:
        e = per[reader_id]
        e["holm"] = adjusted[reader_id]
        e["description"] = label_of(adjusted[reader_id]["reject"], e["rule_right_base_wrong"],
                                    e["rule_wrong_base_right"], H1_LABELS)  # fmt: skip
    return {"arm": arm, "judge": judge, "decides": False, "readers": per}


def analysis_config(resamples: int, seed: int, alpha: float, weights: dict[str, int]) -> dict:
    return {
        "bootstrap_resamples": resamples,
        "bootstrap_seed": seed,
        "alpha": alpha,
        "h1": "exact two-sided McNemar per reader (b: rule right, BM25 top 4 wrong), Holm across "
        "OLMo-2 and Qwen3.5-9B; NONABSTAIN_HELPS / NONABSTAIN_HURTS when the Holm-adjusted p <= "
        "alpha and b > c / b < c, else NO_DETECTED_DIFFERENCE",
        "h2": "descriptive (registered estimand): b2 (BM25 top 4 right, rule wrong) / N with its "
        "Clopper-Pearson 95% interval per reader; the McNemar test with Holm across the three "
        "readers is a description that decides nothing",
        "natural_mix_weights": weights,
        "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
        "abstention_template_sha256": ABSTENTION_TEMPLATE_SHA256,
        "answer_templates_sha256": ANSWER_TEMPLATES_SHA256,
        "requests_per_pool": len(REQUEST_MASKS),
    }


def analyze_registered(
    heldout: dict[str, Any],
    abstention: dict[str, Any] | None,
    config: dict[str, Any],
    abstention_void: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = config["analysis"]
    resamples, seed = int(spec["bootstrap"]["resamples"]), int(spec["bootstrap"]["seed"])
    alpha = float(spec["alpha"])
    weights = dict(spec["natural_mix"])
    check_features(heldout, config, "heldout")
    int_masks(heldout)
    rec_h = records_of(heldout)
    rec_a: dict[str, list[dict[str, Any]]] | None = None
    if abstention is not None:
        check_features(abstention, config, "abstention")
        int_masks(abstention)
        rec_a = records_of(abstention)
    anchor = heldout["comparisons"].get("anchor", {"pass": False})
    replay_ok = bool(anchor.get("pass"))
    gj1 = judge_gate_answerable(heldout["validation"])
    gj2 = judge_gate_abstention(abstention["validation"]) if abstention is not None else None
    validity = {
        "v1_pins": "pass",
        "v2_complete": {"heldout": "pass",
                        "abstention": "pass" if abstention is not None else abstention_void},
        "v3_anchor_replay": {"pass": replay_ok,
                             "r1": anchor.get("r1_replies", {}).get("pass"),
                             "r2": anchor.get("r2_labels_vs_tables", {}).get("pass")},
        "g_j1_answerable_judge": gj1,
        "g_j2_abstention_judge": gj2,
    }  # fmt: skip
    h1 = h1_block(rec_h, resamples, seed, alpha)
    if not replay_ok:
        h1["status"] = f"{VOID_REPLAY}: H1 is not read"
        for e in h1["readers"].values():
            e["reading"] = "VOID"
    elif not gj1["pass"]:
        h1["status"] = "JUDGE_DEPENDENT: G-J1 failed; no decision follows"
        for e in h1["readers"].values():
            e["reading"] = "JUDGE_DEPENDENT"
    else:
        h1["status"] = "read"
    if rec_a is not None:
        h2 = h2_block(rec_a, resamples, seed, alpha)
        if not replay_ok:
            h2["status"] = f"{VOID_REPLAY}: H2 is reported as a description of a void run"
        elif not gj2["pass"]:
            h2["status"] = (
                "JUDGE_QUALIFIED: G-J2 failed; the cost rests on a judge that failed "
                "its abstention validation"
            )
        else:
            h2["status"] = "reported"
    else:
        h2 = {"status": f"VOID: {abstention_void}", "decides": False}
    descriptive: dict[str, Any] = {
        "anchor_h1": anchor_h1(rec_h, resamples, seed),
        "gold_arm": descriptive_paired(rec_h, "gold", "primary", resamples, seed),
        "second_judge_h1": descriptive_paired(rec_h, "retrieved", "secondary", resamples, seed,
                                              H1_READERS),
        "by_type_heldout": {r: {j: by_type(rec_h[r], j) for j in JUDGES} for r in H2_READERS},
        "cells_heldout": cells_of(rec_h, ARMS, resamples, seed, alpha),
    }  # fmt: skip
    if rec_a is not None:
        descriptive["second_judge_h2"] = h2_block(rec_a, resamples, seed, alpha, judge="secondary")
        descriptive["by_type_abstention"] = {
            r: {j: by_type(rec_a[r], j) for j in JUDGES} for r in H2_READERS
        }
        descriptive["cells_abstention"] = cells_of(rec_a, ("retrieved",), resamples, seed, alpha)
        descriptive["natural_mix"] = {
            j: {r: natural_mix(rec_h[r], rec_a[r], weights, resamples, seed, judge=j)
                for r in H2_READERS
                if all(x["u"][j] is not None for x in rec_h[r] + rec_a[r])}
            for j in JUDGES
        }  # fmt: skip
    per_table = []
    for population, recs in (("heldout", rec_h), ("abstention", rec_a or {})):
        for reader_id, rows in recs.items():
            per_table += [{"population": population, "reader": reader_id} | r for r in rows]
    results = {
        "experiment": EXPERIMENT,
        "claim_level": "confirmatory",
        "config": analysis_config(resamples, seed, alpha, weights),
        "inputs": {
            p: {
                k: f[k]
                for k in (
                    "artifact_sha256",
                    "question_ids_sha256",
                    "questions",
                    "arms",
                    "code_sha256",
                    "run",
                )
            }
            | {
                "readers": {
                    r: {
                        k: d[k]
                        for k in (
                            "step",
                            "batch_invariant",
                            "enforce_eager",
                            "pass_sha256",
                            "requests",
                            "finish",
                            "missing_logprobs",
                            "pools_complete_primary",
                            "pools_complete",
                        )
                    }
                    for r, d in f["readers"].items()
                }
            }
            for p, f in (("heldout", heldout), ("abstention", abstention))
            if f is not None
        },  # fmt: skip
        "validation": {
            "heldout": heldout["validation"],
            "abstention": abstention["validation"] if abstention else None,
        },
        "comparisons": _brief_comparisons(heldout["comparisons"]),
        "validity": validity,
        "h1": h1,
        "h2": h2,
        "descriptive": descriptive,
        "verdicts": {
            "H1": {r: h1["readers"][r]["reading"] for r in H1_READERS} | {"status": h1["status"]},
            "H2": {"status": h2["status"], "decides": False},
        },
    }
    return results, per_table


def analyze_development(features: dict[str, Any], config: dict[str, Any]) -> tuple[dict, list]:
    """The dry run on the development split: every cell as AM3 reported it, plus H1's and H2's
    machinery run on development data (labelled; it decides nothing)."""

    spec = config["analysis"]
    resamples, seed = int(spec["bootstrap"]["resamples"]), int(spec["bootstrap"]["seed"])
    alpha = float(spec["alpha"])
    check_features(features, config, "development")
    int_masks(features)
    records = records_of(features)
    per_table = [{"reader": reader_id} | r for reader_id, rows in records.items() for r in rows]
    results = {
        "experiment": EXPERIMENT,
        "claim_level": "exploratory",
        "population": "development",
        "note": "development dry run: no hypothesis is tested; the H1 and H2 blocks run their "
        "code on development data (answerable questions, answer-check judge), decide nothing, and "
        "the H2 block is not H2's population or judge",
        "config": analysis_config(resamples, seed, alpha, dict(spec["natural_mix"])),
        "validation": features["validation"],
        "comparisons": _brief_comparisons(features["comparisons"]),
        "cells": cells_of(records, ARMS, resamples, seed, alpha),
        "mechanics": {
            "h1_block": h1_block(records, resamples, seed, alpha),
            "h2_block_on_development_retrieved": h2_block(records, resamples, seed, alpha),
            "gold_arm": descriptive_paired(records, "gold", "primary", resamples, seed),
            "by_type": {r: {j: by_type(records[r], j) for j in JUDGES} for r in records},
        },
    }
    return results, per_table


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


def render_markdown(results: dict[str, Any]) -> str:
    names = {"primary": "Qwen3-32B", "secondary": "Qwen3-8B"}
    lines: list[str] = []
    if results.get("population") == "development":
        lines += ["# am3-nonabstain-generality-v1: development dry run (EXPLORATORY)", "",
                  "Generated by `scripts/memcredit_am3g.py analyze --development-features`. Every",
                  "number describes the 63 development questions. Nothing is decided.",
                  ""]  # fmt: skip
        lines += _cells_table(results["cells"], names)
        return "\n".join(lines) + "\n"
    lines += ["# am3-nonabstain-generality-v1: tables", "",
              "Generated by `scripts/memcredit_am3g.py analyze`. b: the rule right, BM25 top 4",
              "wrong; c: the reverse. p: exact two-sided McNemar; p (Holm): Holm-adjusted.",
              ""]  # fmt: skip
    v = results["validity"]
    lines += ["## Validity", "",
              f"- V3 anchor replay: {v['v3_anchor_replay']}",
              f"- G-J1 (answerable judge validation): {v['g_j1_answerable_judge']}",
              f"- G-J2 (abstention judge validation): {v['g_j2_abstention_judge']}",
              f"- V2 completeness: {v['v2_complete']}", ""]  # fmt: skip
    h1 = results["h1"]
    lines += [f"## H1 (confirmatory): held-out, retrieved arm, Qwen3-32B ({h1['status']})", "",
              "| Reader | BM25 top 4 | nonabstain-BM25 | b | c | difference | 95% bootstrap | "
              "p | p (Holm) | Reading |",
              "|---|---:|---:|---:|---:|---:|---|---:|---:|---|"]  # fmt: skip
    for r, e in h1["readers"].items():
        lines.append(f"| {r} | {_f(e['base_accuracy'])} | {_f(e['rule_accuracy'])} | "
                     f"{e['rule_right_base_wrong']} | {e['rule_wrong_base_right']} | "
                     f"{e['difference']:+.3f} | {_ci(e['ci95_bootstrap'], True)} | "
                     f"{_p(e['p_exact_mcnemar'])} | {_p(e['holm']['p_holm'])} | "
                     f"{e['reading']} |")  # fmt: skip
    h2 = results["h2"]
    lines += ["", f"## H2 (descriptive): abstention questions, retrieved arm, Qwen3-32B with the "
              f"abstention prompt ({h2['status']})", ""]  # fmt: skip
    if "readers" in h2:
        lines += ["| Reader | N | BM25 top 4 correct | rule correct | b2 (cost) | c2 | cost rate "
                  "[exact 95%] | p | p (Holm) | Description |",
                  "|---|---:|---:|---:|---:|---:|---|---:|---:|---|"]  # fmt: skip
        for r, e in h2["readers"].items():
            if e.get("incomplete"):
                lines.append(f"| {r} | incomplete | | | | | | | | |")
                continue
            lines.append(f"| {r} | {e['questions']} | {e['bm25_top4_correct']} | "
                         f"{e['nonabstain_bm25_correct']} | {e['b2_top4_right_rule_wrong']} | "
                         f"{e['c2_rule_right_top4_wrong']} | {_f(e['cost_rate'])} "
                         f"{_ci(e['cost_rate_ci95_exact'])} | {_p(e['p_exact_mcnemar'])} | "
                         f"{_p(e['holm']['p_holm'])} | {e['description']} |")  # fmt: skip
    d = results["descriptive"]
    a = d["anchor_h1"]
    lines += ["", "## Anchor (Qwen3-8B) on the held-out questions (descriptive)", "",
              f"- retrieved: {a['retrieved']['rule_right_base_wrong']} against "
              f"{a['retrieved']['rule_wrong_base_right']}; gold: "
              f"{a['gold']['rule_right_base_wrong']}"
              f" against {a['gold']['rule_wrong_base_right']}; equal to am1-keepset-search-v1's: "
              f"{a['equals_am1_keepset_search']}", ""]  # fmt: skip
    if "natural_mix" in d:
        lines += ["## Net effect at LongMemEval-S's mix (descriptive)", "",
                  "| Judge | Reader | net count (377 questions) | gain per answerable | loss per "
                  "unanswerable | rate at 470:30 [95%] | break-even unanswerable share [95%] |",
                  "|---|---|---:|---:|---:|---|---|"]  # fmt: skip
        for j, per in d["natural_mix"].items():
            for r, m in per.items():
                lines.append(f"| {names[j]} | {r} | {m['net_count']} | "
                             f"{m['gain_per_answerable']:+.3f} | {m['loss_per_unanswerable']:+.3f} "
                             f"| {m['mix_rate']:+.3f} {_ci(m['mix_rate_ci95'], True)} | "
                             f"{_f(m['break_even_unanswerable_share'])} "
                             f"{_ci(m['break_even_ci95'])} |")  # fmt: skip
        lines.append("")
    lines += ["## Every cell, held-out (descriptive)", ""]
    lines += _cells_table(d["cells_heldout"], names)
    if "cells_abstention" in d:
        lines += ["", "## Every cell, abstention questions (descriptive)", ""]
        lines += _cells_table(d["cells_abstention"], names)
    return "\n".join(lines) + "\n"


def _cells_table(cells: dict[str, Any], names: dict[str, str]) -> list[str]:
    lines = ["| Reader | Judge | Arm | BM25 top 4 | nonabstain-BM25 | all 8 | oracle best 4 | "
             "vs top 4: b, c, p | vs all 8: b, c, p | 4-subset abstain rate | reads median "
             "(mean) |", "|---|---|---|---:|---:|---:|---:|---|---|---:|---|"]  # fmt: skip
    for reader_id, by_judge in cells.items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                if cell.get("incomplete"):
                    lines.append(f"| {reader_id} | {names[j]} | {arm} | incomplete |||||||| ")
                    continue
                acc, pr = cell["accuracy"], cell["paired"]
                hc, h8 = pr["nonabstain_bm25_vs_bm25_top4"], pr["nonabstain_bm25_vs_all_8"]
                rd = cell["stop_rule_reads"]
                lines.append(
                    f"| {reader_id} | {names[j]} | {arm} | {_f(acc['bm25_top4']['mean'])} | "
                    f"{_f(acc['nonabstain_bm25']['mean'])} | {_f(acc['all_8']['mean'])} | "
                    f"{_f(acc['oracle_best4']['mean'])} | {hc['rule_right_base_wrong']}, "
                    f"{hc['rule_wrong_base_right']}, {_p(hc['p_exact_mcnemar'])} | "
                    f"{h8['rule_right_base_wrong']}, {h8['rule_wrong_base_right']}, "
                    f"{_p(h8['p_exact_mcnemar'])} | "
                    f"{_f(cell['abstention']['four_subset_abstain_rate'])} | "
                    f"{_f(rd['median'], 0)} ({_f(rd['mean'], 2)}) |"
                )
    return lines


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    out = Path(args.output_dir)
    if args.development_features:
        if args.heldout_features or args.abstention_features or args.abstention_void:
            raise Am3gError("the development dry run takes only --development-features")
        for p in (args.development_features, args.output_dir):
            check_dev_path(p)
        gate("development")
        features = read_gz_json(Path(args.development_features))
        results, per_table = analyze_development(features, config)
        results["features_sha256"] = {"development": sha256_file(Path(args.development_features))}
    else:
        if not args.heldout_features:
            raise Am3gError("the registered analysis needs --heldout-features")
        if bool(args.abstention_features) == bool(args.abstention_void):
            raise Am3gError("give exactly one of --abstention-features and --abstention-void")
        gate("heldout")
        gate("abstention")
        heldout = read_gz_json(Path(args.heldout_features))
        abstention = (
            read_gz_json(Path(args.abstention_features)) if args.abstention_features else None
        )
        results, per_table = analyze_registered(heldout, abstention, config, args.abstention_void)
        results["features_sha256"] = {"heldout": sha256_file(Path(args.heldout_features))}
        if args.abstention_features:
            results["features_sha256"]["abstention"] = sha256_file(Path(args.abstention_features))
    out.mkdir(parents=True, exist_ok=True)
    lane.write_json(out / "results.json", results)
    write_gz_json(out / "per-table.json.gz", per_table)
    (out / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return {f: sha256_file(out / f) for f in ("results.json", "per-table.json.gz", "tables.md")}


# --------------------------------------------------------------------------- dry-run comparison


AM3_DIR = Path("program/evidence/2026-10-16/am3-reader-replication")
KEEPSET_DIR = PROJECT_ROOT / "program" / "evidence" / "2026-10-16" / "am1-keepset-search"


def dryrun_compare(
    features: dict[str, Any], results: dict[str, Any], per_table: list[dict[str, Any]],
    am3_results: dict[str, Any], am3_per_table: list[dict[str, Any]],
) -> dict[str, Any]:  # fmt: skip
    """The development dry run against AM3's committed outputs: replies at every cell (job 1466),
    judge labels at the item level, every per-pool record and every headline row."""

    checks: list[dict[str, Any]] = []
    comp = features["comparisons"].get("am3_job_1466", {})
    for reader_id, c in comp.get("readers", {}).items():
        if c.get("missing"):
            checks.append({"check": f"replies {reader_id}", "pass": False, "reason": "missing"})
            continue
        checks.append({"check": f"replies {reader_id} vs job 1466 (tokens)",
                       "compared": c["compared"], "identical": c["identical_tokens"],
                       "identical_bits": c["identical_bits"],
                       "pass": c["compared"] == c["cells"] == c["identical_tokens"]})  # fmt: skip
    for j, c in comp.get("judge_item_replay", {}).items():
        checks.append({"check": f"judge {j} item replay vs job 1466", "compared": c["compared"],
                       "identical": c["same"], "pass": c["compared"] > 0
                       and c["compared"] == c["same"]})  # fmt: skip
    ours = {(r["reader"], r["question_id"], r["arm"]): r for r in per_table}
    theirs = {(r["reader"], r["question_id"], r["arm"]): r for r in am3_per_table}
    for reader_id in sorted({k[0] for k in theirs}):
        keys = [k for k in theirs if k[0] == reader_id]
        same = sum(1 for k in keys if ours.get(k) == theirs[k])
        checks.append({"check": f"per-pool records {reader_id} vs AM3's per-table.json.gz",
                       "compared": len(keys), "identical": same,
                       "pass": same == len(keys)})  # fmt: skip
    cells, am3_cells = results["cells"], am3_results["cells"]
    for reader_id, by_judge in am3_cells.items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                mine = cells.get(reader_id, {}).get(j, {}).get(arm)
                checks.append({"check": f"cell {reader_id} {j} {arm} vs AM3's results.json",
                               "pass": mine == cell})  # fmt: skip
    return {"checks": checks, "passed": sum(c["pass"] for c in checks), "total": len(checks),
            "all_pass": all(c["pass"] for c in checks)}  # fmt: skip


def cmd_dryrun_compare(args: argparse.Namespace) -> dict[str, Any]:
    for p in (args.development_features, args.output_dir):
        check_dev_path(p)
    config = load_config(Path(args.config))
    features = read_gz_json(Path(args.development_features))
    results, per_table = analyze_development(features, config)
    am3_results = json.loads((PROJECT_ROOT / AM3_DIR / "results.json").read_text("utf-8"))
    am3_per_table = read_gz_json(PROJECT_ROOT / AM3_DIR / "per-table.json.gz")
    report = dryrun_compare(
        features, json.loads(json.dumps(results)), json.loads(json.dumps(per_table)),
        am3_results, am3_per_table,
    )  # fmt: skip
    report["am3_inputs_sha256"] = {
        f: sha256_file(PROJECT_ROOT / AM3_DIR / f) for f in ("results.json", "per-table.json.gz")
    }
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    lane.write_json(out / "dryrun-compare.json", report)
    return {"passed": report["passed"], "total": report["total"], "all_pass": report["all_pass"],
            "sha256": sha256_file(out / "dryrun-compare.json")}  # fmt: skip


# --------------------------------------------------------------------------- power


def binom_tail_at_least(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def gold_free_proxy(features: dict[str, Any]) -> dict[str, Any]:
    """H2's development proxy: per reader and arm, treat each pool's 4-subsets that hold no gold
    memory as an unanswerable question's subsets (pools with at most 4 gold memories). Counts:
    pools where the BM25-best gold-free 4-subset abstains, and where another gold-free 4-subset
    then answers (the rule would switch away from an abstention)."""

    out: dict[str, Any] = {}
    for reader_id, reader in features["readers"].items():
        out[reader_id] = {}
        for arm in ARMS:
            pools = [p for p in reader["pools"] if p["arm"] == arm]
            eligible = top_abstains = switches = gf_abstain = gf_total = 0
            for p in pools:
                masks = {int(m): c for m, c in p["masks"].items()}
                free = [s for s in FOUR_SETS if not s & int(p["gold_mask"])]
                gf_total += len(free)
                gf_abstain += sum(bool(masks[s]["abstain"]) for s in free)
                if not free:
                    continue
                eligible += 1
                order = sorted(free, key=lambda s: lf.rank_key(s, p["bm25_rank"]), reverse=True)
                if masks[order[0]]["abstain"]:
                    top_abstains += 1
                    switches += any(not masks[s]["abstain"] for s in order[1:])
            out[reader_id][arm] = {"pools": len(pools), "eligible": eligible,
                                   "top_gold_free_abstains": top_abstains, "switches": switches,
                                   "switch_rate": switches / eligible if eligible else None,
                                   "gold_free_subsets_abstaining": [gf_abstain,
                                                                    gf_total]}  # fmt: skip
    return out


def power_report(am3_results: dict[str, Any], keepset: dict[str, Any], proxy: dict) -> dict:
    """H1's power from AM3's development rates and the anchor's held-out rate; H2's power and
    precision at N = 30 from the development proxy and a grid of cost rates."""

    n1 = 347
    thresholds: dict[int, int] = {}
    h1: dict[str, Any] = {}
    for reader_id in H1_READERS:
        cell = am3_results["cells"][reader_id]["primary"]["retrieved"]["paired"][
            "nonabstain_bm25_vs_bm25_top4"
        ]
        b, c = cell["rule_right_base_wrong"], cell["rule_wrong_base_right"]
        rate = (b + c) / cell["questions"]
        share = b / (b + c) if b + c else 1.0
        rows = {}
        for label, r, s in (("development rate", rate, share),
                            ("half the development rate", rate / 2, share),
                            ("a quarter of it", rate / 4, share),
                            ("development rate, 1 in 10 discordant pairs against", rate, 0.9),
                            ("the anchor's held-out rate (39/347)", 39 / 347, 1.0)):  # fmt: skip
            rows[label] = {
                "rate": r, "share_for_rule": s,
                "power_alpha_0.025": ks.mcnemar_power(n1, r, s, 0.025, {}),
                "power_alpha_0.05": ks.mcnemar_power(n1, r, s, 0.05, thresholds),
            }  # fmt: skip
        h1[reader_id] = {"development_b_c": [b, c], "scenarios": rows}
    n2 = 30
    grid = {}
    for q in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5):
        grid[f"{q:.2f}"] = {
            "power_holm_strictest_alpha_0.0167": binom_tail_at_least(7, n2, q),
            "power_alpha_0.05": binom_tail_at_least(6, n2, q),
        }
    h2_proxy = {}
    for reader_id, arms in proxy.items():
        q = arms["retrieved"]["switch_rate"]
        h2_proxy[reader_id] = {
            "switch_rate_retrieved": q,
            "power_holm_strictest_alpha_0.0167": binom_tail_at_least(7, n2, q),
            "power_alpha_0.05": binom_tail_at_least(6, n2, q),
        }
    anchor_switch = keepset["anchor_switch_rate"]
    precision = {f"{k}/30": cp_interval(k, n2) for k in (0, 1, 3, 6, 9, 15)}
    return {
        "h1": {"questions": n1, "readers": h1,
               "note": "power of the exact two-sided McNemar test per reader; Holm across two "
               "readers rejects a reader at least when p <= 0.025 and at most when p <= 0.05, so "
               "the two columns bound its power"},
        "h2": {
            "questions": n2,
            "rejection_with_c2_0": "Holm's strictest step (0.05/3) needs b2 >= 7; alpha 0.05 "
            "needs b2 >= 6",
            "grid_cost_rate": grid,
            "development_gold_free_proxy": proxy,
            "proxy_power": h2_proxy,
            "anchor_heldout_switch_rate_answerable": anchor_switch,
            "anchor_switch_power_holm_strictest": binom_tail_at_least(7, n2, anchor_switch),
            "anchor_switch_power_alpha_0.05": binom_tail_at_least(6, n2, anchor_switch),
            "clopper_pearson_95_at_30": precision,
        },
    }  # fmt: skip


def cmd_power(args: argparse.Namespace) -> dict[str, Any]:
    check_dev_path(args.am3_features)
    am3_results = json.loads((PROJECT_ROOT / AM3_DIR / "results.json").read_text("utf-8"))
    keepset_path = KEEPSET_DIR / "analysis" / "results.json"
    keepset_results = json.loads(keepset_path.read_text("utf-8"))
    held = keepset_results["descriptive"]["retrieved"]["all"]
    # The rule leaves BM25 top 4 where top 4 abstains and some other 4-subset answers.
    switches = (held["abstention"]["bm25_top4_abstains"]
                - held["abstention"]["pools_where_every_4_subset_abstains"])  # fmt: skip
    questions = held["questions"]
    features = read_gz_json(Path(args.am3_features))
    if sha256_file(Path(args.am3_features)) != args.am3_features_sha256:
        raise Am3gError("AM3's features differ from the expected SHA-256")
    proxy = gold_free_proxy(features)
    report = power_report(am3_results, {"anchor_switch_rate": switches / questions}, proxy)
    report["inputs"] = {
        "am3_results_sha256": sha256_file(PROJECT_ROOT / AM3_DIR / "results.json"),
        "am1_keepset_results_sha256": sha256_file(keepset_path),
        "am3_features_sha256": args.am3_features_sha256,
        "anchor_heldout_switches": [switches, questions],
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return {"sha256": sha256_file(Path(args.output))}


# --------------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare-abstention", allow_abbrev=False)
    prep.add_argument("--source", required=True)
    prep.add_argument("--split-file", required=True)
    prep.add_argument("--artifact", required=True)
    prep.add_argument("--summary", required=True)
    prep.add_argument("--dev-artifact", default=None)
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
    extract.add_argument("--private-dir", required=True)
    extract.add_argument("--reference-run-dir", default=None)
    analyze_p = sub.add_parser("analyze", allow_abbrev=False)
    analyze_p.add_argument("--heldout-features", default=None)
    analyze_p.add_argument("--abstention-features", default=None)
    analyze_p.add_argument("--abstention-void", default=None)
    analyze_p.add_argument("--development-features", default=None)
    analyze_p.add_argument("--output-dir", required=True)
    compare = sub.add_parser("dryrun-compare", allow_abbrev=False)
    compare.add_argument("--development-features", required=True)
    compare.add_argument("--output-dir", required=True)
    power_p = sub.add_parser("power", allow_abbrev=False)
    power_p.add_argument("--am3-features", required=True)
    power_p.add_argument("--am3-features-sha256", required=True)
    power_p.add_argument("--output", required=True)
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-abstention":
            print(json.dumps(cmd_prepare_abstention(args), indent=2, sort_keys=True))
            return 0
        if args.command == "plan":
            if args.population == "heldout":
                gate(args.population)
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
        if args.command == "extract":
            print(json.dumps(cmd_extract(args), indent=2, sort_keys=True))
            return 0
        if args.command == "analyze":
            print(json.dumps(cmd_analyze(args), indent=2, sort_keys=True))
            return 0
        if args.command == "dryrun-compare":
            print(json.dumps(cmd_dryrun_compare(args), indent=2, sort_keys=True))
            return 0
        print(json.dumps(cmd_power(args), indent=2, sort_keys=True))
        return 0
    except (Am3gError, am3.Am3Error, ks.KeepsetError, ms.StudyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
