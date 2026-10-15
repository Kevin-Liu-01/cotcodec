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
import re
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
#: A reply that offers alternatives (descriptive only): on the normalized reply.
HEDGE_PATTERN = r"\b(?:or|either|possibly|perhaps|maybe|might|could be|not sure|unsure)\b"
HEDGE_RE = re.compile(HEDGE_PATTERN)


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
    """Where an abstention question's twin sits. The split comes first: a development twin is
    "development" even when it was also one of Step 0's demo questions (``09ba9854``); a held-out
    twin is "heldout-confirmatory" unless it is one of the demo questions AM1 excluded from its
    347 ("heldout-step0-demo-excluded")."""

    if twin not in by_id:
        return "absent"
    if twin in split["development"]:
        return "development"
    if twin in split["heldout"]:
        return "heldout-step0-demo-excluded" if twin in excluded else "heldout-confirmatory"
    return "not-usable"


def memory_texts(record: dict[str, Any], pool_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Every user turn of a record as AM1's memory entries (BM25 order, the same truncation)."""

    max_chars = int(pool_config["pools"]["max_memory_chars"])
    ranked = mc.rank_user_turns(record, pool_config["retriever"])
    return [mc.memory_entry(t, r, sc, max_chars) for r, (t, sc) in enumerate(ranked)]


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
        # Text-free overlap: the abstention pool's memory texts (by SHA-256) against every user
        # turn of the twin and against the twin's own retrieved pool, both cut as AM1 cuts them.
        twin_entries = memory_texts(by_id[twin], pool_config) if twin in by_id else []
        twin_all = {e["text_sha256"] for e in twin_entries}
        twin_pool = {e["text_sha256"] for e in twin_entries[: len(pool)]}
        facts.append({
            "question_id": qid,
            "twin_question_id": twin,
            "twin_membership": twin_membership(twin, by_id, split, excluded),
            "twin_is_step0_demo": twin in excluded,
            "sessions": len(sessions),
            "twin_sessions": len(twin_sessions),
            "shared_sessions": len(sessions & twin_sessions),
            "pool_memories_in_twin_user_turns": sum(m["text_sha256"] in twin_all for m in pool),
            "pool_memories_in_twin_retrieved_pool": sum(
                m["text_sha256"] in twin_pool for m in pool
            ),
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
    overlap = {
        "pools_with_a_memory_in_twin_user_turns": sum(
            f["pool_memories_in_twin_user_turns"] > 0 for f in facts["twins"]
        ),
        "memories_in_twin_user_turns": sum(
            f["pool_memories_in_twin_user_turns"] for f in facts["twins"]
        ),
        "memories_in_twin_retrieved_pool": sum(
            f["pool_memories_in_twin_retrieved_pool"] for f in facts["twins"]
        ),
        "memories": sum(len(q["pools"]["retrieved"]) for q in artifact["questions"]),
    }
    return {
        "experiment_id": artifact["experiment_id"],
        "split": artifact["split"],
        "artifact_sha256": digest,
        "questions": len(questions),
        "question_ids_sha256": artifact["question_ids_sha256"],
        "question_ids": [q["question_id"] for q in artifact["questions"]],
        "by_type": dict(sorted(by_type.items())),
        "twin_membership": dict(sorted(membership.items())),
        "twins_that_are_step0_demo": sum(f["twin_is_step0_demo"] for f in facts["twins"]),
        "twin_text_overlap": overlap,
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


def cmd_abstention_facts(args: argparse.Namespace) -> dict[str, Any]:
    """Rebuild the abstention artifact in memory, check it is byte for byte the pinned one, and
    write its text-free summary with the twin facts (membership, Step 0, session and memory-text
    overlap). It never writes the artifact."""

    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    if Path(args.output).exists():
        raise Am3gError(f"refusing to overwrite {args.output}")
    split = ms.load_split(Path(args.split_file), pilot)
    if sha256_file(Path(args.split_file)) != config["split_file_sha256"]:
        raise Am3gError("the split file differs from its pin")
    records = read_source(Path(args.source), pilot)
    artifact, facts = build_abstention_artifact(records, pilot, split, config)
    data = mc.canonical_json(artifact)
    spec = population_spec(config, "abstention")
    if sha256_bytes(data) != spec["artifact_sha256"] or Path(args.evidence).read_bytes() != data:
        raise Am3gError(f"{VOID_DIGEST}: the rebuilt abstention artifact is not the pinned one")
    summary = abstention_summary(artifact, sha256_bytes(data), facts, pilot)
    Path(args.output).write_bytes(mc.canonical_json(summary))
    return {k: summary[k] for k in ("artifact_sha256", "questions", "twin_membership",
                                    "twins_that_are_step0_demo", "twin_text_overlap")} | {
        "summary_sha256": sha256_file(Path(args.output))}  # fmt: skip


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
            cell["hedge"] = bool(HEDGE_RE.search(normalized))
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


def load_pinned_tables(spec: dict[str, Any], root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Committed AM1-style tables (``tables.json.gz``), checked against the gz digest and the
    uncompressed digest; every entry must carry ``question_id``, ``arm`` and ``values_hex``."""

    path = root / spec["path"]
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Am3gError(f"{VOID_DIGEST}: {spec['path']} is missing or unreadable: {exc}") from exc
    if sha256_bytes(raw) != spec["sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: {spec['path']}: the gz differs from its pin")
    data = gzip.decompress(raw)
    if sha256_bytes(data) != spec["json_sha256"]:
        raise Am3gError(f"{VOID_DIGEST}: {spec['path']}: the tables differ from their pin")
    tables = json.loads(data)
    if not isinstance(tables, list) or any(
        not isinstance(t, dict) or not {"question_id", "arm", "values_hex"} <= set(t)
        for t in tables
    ):
        raise Am3gError(f"{VOID_DIGEST}: {spec['path']}: not a list of tables")
    return tables


def load_heldout_tables(config: dict[str, Any]) -> list[dict[str, Any]]:
    """AM1's committed held-out tables (after the gate), checked against both pinned digests."""

    return load_pinned_tables(population_spec(config, "heldout")["tables"])


def labels_vs_tables(pools: Sequence[dict[str, Any]], tables: Sequence[dict[str, Any]]) -> dict:
    """The anchor's primary-judge labels against AM1's committed tables (values_hex; bit m is
    u(mask m)) at the 71 requested masks of every pool."""

    by_key = {(t["question_id"], t["arm"]): cc.decode_values(t["values_hex"]) for t in tables}
    missing = [(p["question_id"], p["arm"]) for p in pools
               if (p["question_id"], p["arm"]) not in by_key]  # fmt: skip
    if missing:
        raise Am3gError(f"{VOID_DIGEST}: the committed tables lack {len(missing)} pools, e.g. "
                        f"{missing[:3]}")  # fmt: skip
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
    summary = read_run_json(run_dir / "summary.json", "the driver's summary")
    if summary.get("population") != population or summary.get("experiment_id") != EXPERIMENT:
        raise Am3gError(f"{VOID_DIGEST}: the run directory is not this population's run")
    items = read_run_json(
        run_dir / "judge-items.json", "the judge items (no judge step ran: judge32 was skipped)"
    )
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
        try:
            passed = load_pass(run_dir / "sessions" / sid)
        except (OSError, ValueError, KeyError, EOFError) as exc:
            raise Am3gError(f"{VOID_INCOMPLETE}: {sid}'s pass is missing or unreadable: "
                            f"{exc!r}") from exc  # fmt: skip
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
    if population == "development" and ANCHOR in readers:
        # The R2 code on a real committed tables file: the pilot's development tables come from
        # job 1411's compiled pass, so AM3's 8,913 of 8,946 cells are expected, not all.
        pilot_tables = load_pinned_tables(population_spec(config, "development")["tables"])
        check = labels_vs_tables(readers[ANCHOR]["pools"], pilot_tables)
        comparisons["anchor_vs_pilot_tables"] = {k: v for k, v in check.items()
                                                 if k != "differing_cells"}  # fmt: skip
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


def read_run_json(path: Path, what: str) -> Any:
    """A JSON file of a run directory; a missing or unreadable one is the V2 void."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Am3gError(f"{VOID_INCOMPLETE}: {what} ({path.name}) is missing or unreadable: "
                        f"{exc!r}") from exc  # fmt: skip


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
    strata: dict[str, bool] | None = None,
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
        correct_abstentions = sum(
            1 for r in rows if r["bm25_top4_abstains"] and r["u"][judge]["bm25_top4"] == 1
        )
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
            "bm25_top4_correct_abstentions": correct_abstentions,
            "cost_per_correct_top4_abstention": (b2 / correct_abstentions
                                                 if correct_abstentions else None),
            "cost_per_correct_top4_abstention_ci95_exact": (
                cp_interval(b2, correct_abstentions) if correct_abstentions else None),
        })  # fmt: skip
        if strata is not None:
            entry["by_near_miss_memory"] = {}
            for label, flag in (
                ("pool_holds_a_has_answer_memory", True),
                ("pool_holds_none", False),
            ):
                sub = [r for r in rows if strata.get(r["question_id"]) is flag]
                entry["by_near_miss_memory"][label] = {
                    "questions": len(sub),
                    "b2": sum(1 for r in sub if r["u"][judge]["bm25_top4"] == 1
                              and r["u"][judge]["nonabstain_bm25"] == 0),
                    "c2": sum(1 for r in sub if r["u"][judge]["bm25_top4"] == 0
                              and r["u"][judge]["nonabstain_bm25"] == 1),
                    "bm25_top4_correct": sum(int(r["u"][judge]["bm25_top4"]) for r in sub),
                    "nonabstain_bm25_correct": sum(int(r["u"][judge]["nonabstain_bm25"])
                                                   for r in sub),
                }  # fmt: skip
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
    link_twins: bool = False,
) -> dict[str, Any]:
    """The rule minus BM25 top 4, over answerable plus unanswerable questions: the raw count over
    the questions run, the rate at LongMemEval-S's mix (weights: answerable, abstention), and the
    break-even unanswerable share, with percentile intervals from a bootstrap that resamples each
    population's questions separately (numpy default_rng(seed)). With ``link_twins`` an
    abstention question whose twin (its id without ``_abs``) is among the answerable questions is
    resampled together with it, as one unit; the other questions of each population are resampled
    within their population. The break-even interval uses only the resamples where it is defined
    and reports how many are not. Percentiles: the sorted values at floor(0.025 (n - 1)) and
    ceil(0.975 (n - 1))."""

    import numpy as np

    rows_a = [r for r in answerable if r["arm"] == "retrieved"]
    rows_b = [r for r in unanswerable if r["arm"] == "retrieved"]
    d1 = np.array([float(r["u"][judge]["nonabstain_bm25"] - r["u"][judge]["bm25_top4"])
                   for r in rows_a])  # fmt: skip
    d2 = np.array([float(r["u"][judge]["nonabstain_bm25"] - r["u"][judge]["bm25_top4"])
                   for r in rows_b])  # fmt: skip
    total = weights["answerable"] + weights["abstention"]
    wa, wb = weights["answerable"] / total, weights["abstention"] / total
    gain, loss = float(d1.mean()), float(-d2.mean())
    rng = np.random.default_rng(seed)
    linked = 0
    if not link_twins:
        ia = rng.integers(0, len(d1), size=(resamples, len(d1)))
        ib = rng.integers(0, len(d2), size=(resamples, len(d2)))
        g = d1[ia].mean(axis=1)
        lo_ = -d2[ib].mean(axis=1)
    else:
        position = {r["question_id"]: i for i, r in enumerate(rows_a)}
        pairs = [(position[r["question_id"][: -len("_abs")]], j) for j, r in enumerate(rows_b)
                 if r["question_id"].endswith("_abs")
                 and r["question_id"][: -len("_abs")] in position]  # fmt: skip
        linked = len(pairs)
        pa = np.array([a for a, _ in pairs], dtype=int)
        pb = np.array([b for _, b in pairs], dtype=int)
        ua = np.array(sorted(set(range(len(d1))) - set(pa.tolist())), dtype=int)
        ub = np.array(sorted(set(range(len(d2))) - set(pb.tolist())), dtype=int)
        iu = rng.integers(0, len(ua), size=(resamples, len(ua)))
        ju = rng.integers(0, max(len(ub), 1), size=(resamples, len(ub)))
        ip = rng.integers(0, max(len(pairs), 1), size=(resamples, len(pairs)))
        g = (d1[ua][iu].sum(axis=1) + d1[pa][ip].sum(axis=1)) / len(d1)
        lo_ = -(d2[ub][ju].sum(axis=1) + d2[pb][ip].sum(axis=1)) / len(d2)
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
        "bootstrap": {"resamples": resamples, "seed": seed,
                      "resampling": "linked twins as units" if link_twins else
                      "each population separately", "linked_pairs": linked},
    }  # fmt: skip


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
    """G-J1, a replay of AM1's validation items under AM1's G2 rule (it cannot catch errors the
    judge makes on the new readers' replies; the blind hand check does that): the primary judge
    says yes to at least 95%
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


# --------------------------------------------------------------------------- H1's blind hand check

HAND_SEED = 44
#: Items per labelling chunk; every chunk is labelled by a fresh agent context.
HAND_CHUNK = 60
#: The labeller: an isolated Claude agent (registration section 8).
HAND_LABELLER_MODEL = "claude-opus-5-5"
#: What the isolated labeller is told (written beside the sample; registration section 8).
HAND_INSTRUCTIONS = """Blind hand check, am3-nonabstain-generality-v1 (D9: agent labels).

Each line of the sample is one item: a LongMemEval-S question, its question type, a check
("answer" or "abstention"), a reference text and a reply written by a language model that was
given some of the user's past messages. Label every item, independently of the others.

check "answer" (the reference text is the reference answer; for single-session-preference, a
rubric):
- 1 if the reply is correct: it contains the reference answer, or is equivalent to it, or
  contains all the intermediate steps to reach it. A reply that gives only part of the
  information the answer needs is 0.
- temporal-reasoning: do not penalise an off-by-one error in a number of days, weeks or months.
- knowledge-update: a reply that mentions earlier information along with the updated answer is
  correct as long as the updated answer is the one required.
- single-session-preference: 1 if the reply satisfies the rubric, recalling and using the
  user's personal information correctly; it need not cover every point.
- A reply that declines to answer ("I don't know", "the memories do not say") is 0: every
  question with this check has an answer.

check "abstention" (the question cannot be answered from the user's history; the reference text
explains why):
- 1 if the reply correctly identifies the question as unanswerable: it may say that it does not
  know, that the information is incomplete, or that some other information is given but not the
  information asked for.
- 0 if the reply answers the question as if it could be answered.

Use only the question, the check, the reference text and the reply. Do not look for, open or
infer any other file, label or result. Write one JSON object per line, in the sample's order:
{"item_id": "...", "label": 1 or 0, "note": "optional, short"}.
"""
#: The labeller's launch prompt, one per chunk (``hand_labeller_prompt``); its SHA-256 is in the
#: registration (section 8) and every receipt.
HAND_LABELLER_PROMPT = """You are a blind labeller for a research hand check.
You have exactly two input files: {instructions} and {chunk}.
Read {instructions} first, then {chunk}, which has one JSON object per line.
Label every line of {chunk} as the instructions say, independently of the other
lines and using only what each line holds. Then write the labels, one JSON object
per line in the same order, with exactly the keys item_id, label (the integer 1 or
0) and note (a short reason, or empty), to the new file {output}. Read no other
file, do not search for or list other files, run no command and use no other tool.
When the file is written, reply with the number of lines you wrote and nothing else.
"""


def hand_labeller_prompt(
    chunk: str, output: str, instructions: str = "hand-check-instructions.txt"
) -> str:
    """The pinned prompt for one chunk: file names relative to the chunk's own directory (the
    registered launch, section 8), or absolute paths to the same three files."""

    return HAND_LABELLER_PROMPT.format(instructions=instructions, chunk=chunk, output=output)


def hand_labeller_prompt_sha256() -> str:
    return sha256_text(HAND_LABELLER_PROMPT)


def _norm_masks(pool: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(m): c for m, c in pool["masks"].items()}


def _plan_population(
    features: dict[str, Any],
    population: str,
    readers: Sequence[str],
    uses: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """One population's part of the plan (see ``hand_plan``); adds to ``uses``."""

    per_reader: dict[str, Any] = {}
    for reader in readers:
        pools = sorted((p for p in features["readers"][reader]["pools"]
                        if p["arm"] == "retrieved"), key=lambda p: p["question_id"])  # fmt: skip
        discordant, switched, kept = [], [], []
        for p in pools:
            masks = _norm_masks(p)
            top = lf.bm25_top_mask(p["bm25_rank"])
            rule = am3.nonabstain_bm25({"bm25_rank": p["bm25_rank"], "masks": masks})["mask"]
            entry = (p, masks, top, rule)
            if masks[top]["u"]["primary"] != masks[rule]["u"]["primary"]:
                discordant.append(entry)
            elif rule != top:
                switched.append(entry)
            else:
                kept.append(entry)
        rng = random.Random(f"{HAND_SEED}:hand:{reader}" if population != "abstention"
                            else f"{HAND_SEED}:hand:abstention:{reader}")  # fmt: skip
        need = len(discordant)
        from_switched = rng.sample(switched, min(need, len(switched)))
        from_kept = rng.sample(kept, min(need - len(from_switched), len(kept)))

        def add(
            p: dict[str, Any], masks: dict[int, Any], mask: int, role: str, who: str = reader
        ) -> None:
            key = (p["question_id"], masks[mask]["digest"])
            uses.setdefault(key, []).append(
                {"population": population, "reader": who, "role": role, "mask": mask,
                 "judge_primary": masks[mask]["u"]["primary"]}
            )  # fmt: skip

        for p, masks, top, rule in discordant:
            add(p, masks, rule, "discordant-rule")
            add(p, masks, top, "discordant-top4")
        for p, masks, top, rule in from_switched + from_kept:
            add(p, masks, top, "distractor")
            second = rule if rule != top else None
            if second is None:
                others = [m for m in sorted(FOUR_SETS) if m != top]
                for m in rng.sample(others, len(others)):
                    if masks[m]["digest"] != masks[top]["digest"]:
                        second = m
                        break
            if second is not None and masks[second]["digest"] != masks[top]["digest"]:
                add(p, masks, second, "distractor")
        per_reader[reader] = {
            "discordant_questions": need,
            "distractor_questions": len(from_switched) + len(from_kept),
            "distractors_where_the_rule_switched": len(from_switched),
            "distractors_where_it_kept_top4": len(from_kept),
            "switched_shortfall": max(0, need - len(switched)),
        }
    return per_reader


def hand_plan(features: dict[str, Any], abstention: dict[str, Any] | None = None) -> dict[str, Any]:
    """The blind hand check's items, from text-free features alone (so ``analyze`` recomputes
    them). Held-out (or development) features, per H1 reader, and the abstention features when
    given, per H2 reader (descriptive), retrieved arm, primary judge: every discordant question
    (the rule's choice and BM25 top 4 judged differently) gives both replies; as many concordant
    questions, drawn with ``random.Random(f"44:hand:{reader}")`` (``44:hand:abstention:{reader}``
    for the abstention questions), first from those where the rule left BM25 top 4 and then from
    the others, give BM25 top 4's reply and the rule's (or, where the rule kept top 4, a seeded
    other 4-subset's reply that differs). Items are deduplicated by (question, normalized-reply
    SHA-256) and put in one seeded order across readers and populations
    (``random.Random("44:hand:order")``); item ids follow that order; chunks of ``HAND_CHUNK``
    consecutive items."""

    uses: dict[tuple[str, str], list[dict[str, Any]]] = {}
    population = "development" if features.get("population") == "development" else "heldout"
    readers = {population: _plan_population(features, population, H1_READERS, uses)}
    if abstention is not None:
        readers["abstention"] = _plan_population(abstention, "abstention", H2_READERS, uses)
    keys = sorted(uses)
    random.Random(f"{HAND_SEED}:hand:order").shuffle(keys)
    items = [{"item_id": f"h{n:04d}", "question_id": q, "reply_digest": d,
              "check": "abstention" if q.endswith("_abs") else "answer", "uses": uses[(q, d)]}
             for n, (q, d) in enumerate(keys)]  # fmt: skip
    plan = {"seed": HAND_SEED, "chunk_size": HAND_CHUNK, "readers": readers, "items": items,
            "labeller_model": HAND_LABELLER_MODEL,
            "labeller_prompt_sha256": hand_labeller_prompt_sha256(),
            "instructions_sha256": sha256_text(HAND_INSTRUCTIONS)}  # fmt: skip
    plan["plan_sha256"] = sha256_bytes(json.dumps(items, sort_keys=True).encode())
    return plan


def read_hand_labels(path: Path, expected_sha256: str | None) -> tuple[list[dict[str, Any]], str]:
    """The blind hand labels and their SHA-256, which must equal the digest committed before the
    join."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Am3gError(f"the hand labels {path} are missing or unreadable: {exc}") from exc
    digest = sha256_bytes(raw)
    if expected_sha256 is None or digest != expected_sha256:
        raise Am3gError("the hand labels differ from the SHA-256 committed before the join")
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except ValueError as exc:
        raise Am3gError(f"the hand labels are not JSON lines: {exc}") from exc
    return rows, digest


def _discordant_counts(
    hand_of: dict[tuple[str, str, str, str], int], population: str, reader: str
) -> tuple[int, int, int]:
    qids = sorted({q for (pop, r, role, q) in hand_of
                   if pop == population and r == reader and role == "discordant-rule"})  # fmt: skip
    rule_right = sum(1 for q in qids if hand_of[(population, reader, "discordant-rule", q)] == 1
                     and hand_of[(population, reader, "discordant-top4", q)] == 0)  # fmt: skip
    top_right = sum(1 for q in qids if hand_of[(population, reader, "discordant-rule", q)] == 0
                    and hand_of[(population, reader, "discordant-top4", q)] == 1)  # fmt: skip
    return len(qids), rule_right, top_right


def _agreement(pairs: Sequence[tuple[int, int]]) -> dict[str, Any]:
    judge = [a for a, _ in pairs]
    hand = [b for _, b in pairs]
    return {
        "items": len(pairs),
        "agree": sum(1 for a, b in pairs if a == b),
        "kappa": ms.cohen_kappa(judge, hand) if pairs else None,
        "judge_yes_hand_yes": sum(1 for a, b in pairs if a and b),
        "judge_yes_hand_no": sum(1 for a, b in pairs if a and not b),
        "judge_no_hand_yes": sum(1 for a, b in pairs if not a and b),
        "judge_no_hand_no": sum(1 for a, b in pairs if not a and not b),
        "decides": False,
    }


def hand_check(
    features: dict[str, Any],
    plan: dict[str, Any],
    labels: list[dict[str, Any]] | None,
    labels_sha256: str | None,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Join the blind hand labels to the plan. Status: "joined" when every item has exactly one
    label of 0 or 1 and no other item is labelled; "missing" without labels; "incomplete"
    otherwise. H1 (decides, section 7.1): per H1 reader, over its judge-discordant questions,
    b_hand (the rule's reply hand-labelled 1, top 4's 0), c_hand (the reverse), the exact McNemar
    p and Holm across the two readers. H2 (descriptive): per H2 reader on the abstention
    questions, b2_hand (top 4's reply 1, the rule's 0) and c2_hand, with Holm across the three.
    Hand against judge: agreement and Cohen's kappa, overall and per population (descriptive)."""

    out: dict[str, Any] = {
        "plan_sha256": plan["plan_sha256"],
        "items": len(plan["items"]),
        "readers_plan": plan["readers"],
        "labels_sha256": labels_sha256,
        "labeller": f"an isolated agent ({plan['labeller_model']}), blind (D9: agent labels, "
        "not human)",
        "labeller_prompt_sha256": plan["labeller_prompt_sha256"],
    }
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
    hand_of: dict[tuple[str, str, str, str], int] = {}
    pairs: dict[str, list[tuple[int, int]]] = {}
    for item in plan["items"]:
        h = int(by_id[item["item_id"]])
        first = item["uses"][0]
        pairs.setdefault(first["population"], []).append((int(first["judge_primary"]), h))
        for use in item["uses"]:
            hand_of[(use["population"], use["reader"], use["role"], item["question_id"])] = h
    h1_population = next(p for p in plan["readers"] if p != "abstention")
    per: dict[str, Any] = {}
    for reader in H1_READERS:
        n, b, c = _discordant_counts(hand_of, h1_population, reader)
        per[reader] = {"discordant_questions": n, "b_hand": b, "c_hand": c,
                       "p_exact_mcnemar": ks.mcnemar_exact(b, c)}  # fmt: skip
    adjusted = holm({r: per[r]["p_exact_mcnemar"] for r in H1_READERS}, alpha)
    for reader in H1_READERS:
        e = per[reader]
        e["holm"] = adjusted[reader]
        e["hand_label"] = label_of(adjusted[reader]["reject"], e["b_hand"], e["c_hand"], H1_LABELS)
    out["readers"] = per
    if "abstention" in plan["readers"]:
        h2: dict[str, Any] = {}
        for reader in H2_READERS:
            n, rule_right, top_right = _discordant_counts(hand_of, "abstention", reader)
            h2[reader] = {"discordant_questions": n, "b2_hand": top_right, "c2_hand": rule_right,
                          "p_exact_mcnemar": ks.mcnemar_exact(top_right, rule_right)}  # fmt: skip
        adjusted2 = holm({r: h2[r]["p_exact_mcnemar"] for r in H2_READERS}, alpha)
        for reader in H2_READERS:
            e = h2[reader]
            e["holm"] = adjusted2[reader]
            e["description"] = label_of(adjusted2[reader]["reject"], e["b2_hand"], e["c2_hand"],
                                        H2_LABELS)  # fmt: skip
        out["h2_descriptive"] = {"decides": False, "readers": h2}
    out["agreement"] = _agreement([x for v in pairs.values() for x in v])
    out["agreement_by_population"] = {k: _agreement(v) for k, v in sorted(pairs.items())}
    return out


def confirm_reading(judge_reading: str, hand: dict[str, Any], reader: str) -> str:
    """H1's reading after the hand check (registration section 7.1): NONABSTAIN_HELPS or
    NONABSTAIN_HURTS stands only if the hand-label test, with Holm across the two readers, rejects
    in the same direction; otherwise JUDGE_DEPENDENT. NO_DETECTED_DIFFERENCE stands. Without a
    complete join a directional reading is PENDING_HAND_CHECK (no labels) or JUDGE_DEPENDENT
    (labels that do not cover the sample)."""

    if judge_reading not in H1_LABELS[:2]:
        return judge_reading
    if hand["status"] == "missing":
        return "PENDING_HAND_CHECK"
    if hand["status"] != "joined":
        return "JUDGE_DEPENDENT"
    return (
        judge_reading
        if hand["readers"][reader]["hand_label"] == judge_reading
        else "JUDGE_DEPENDENT"
    )


def _sample_rows(
    plan: dict[str, Any],
    sources: dict[str, tuple[dict[str, Any], dict[str, Any], Path, tuple[str, ...]]],
) -> list[str]:
    """One JSON line per plan item: id, question id and type, check, question, reference text,
    reply; nothing else. ``sources``: population -> (features, artifact, run dir, arms)."""

    lines = []
    cache: dict[tuple[str, str], dict[int, Any]] = {}
    indexes = {pop: {(r["question_id"], r["arm"], r["mask"]): r["index"]
                     for r in request_table(art, arms)}
               for pop, (_, art, _, arms) in sources.items()}  # fmt: skip
    questions = {pop: {q["question_id"]: q for q in art["questions"]}
                 for pop, (_, art, _, _) in sources.items()}  # fmt: skip
    for item in plan["items"]:
        use = item["uses"][0]
        pop = use["population"]
        features, _, run_dir, _ = sources[pop]
        key = (pop, use["reader"])
        if key not in cache:
            step = features["readers"][use["reader"]]["step"]
            cache[key] = load_pass(run_dir / "sessions" / step)["rows"]
        text = cache[key][indexes[pop][(item["question_id"], "retrieved", use["mask"])]]["text"]
        if sha256_text(mc.normalize_answer(text.strip())) != item["reply_digest"]:
            raise Am3gError(f"{VOID_DIGEST}: a reply differs from the features' digest")
        q = questions[pop][item["question_id"]]
        lines.append(json.dumps({"item_id": item["item_id"], "question_id": q["question_id"],
                                 "question_type": q["question_type"], "check": item["check"],
                                 "question": q["question"], "reference": str(q["answer"]),
                                 "reply": text.strip()}, ensure_ascii=False))  # fmt: skip
    return lines


def write_chunks(hand_dir: Path, stage: str, lines: Sequence[str], ids: Sequence[str]) -> list:
    """Chunk files (``hand-{stage}-chunk-NN.jsonl``) of ``HAND_CHUNK`` consecutive lines, each with
    its launch prompt (``hand-{stage}-prompt-NN.txt``); returns the chunk manifest."""

    chunks = []
    for k in range(0, len(lines), HAND_CHUNK):
        n = k // HAND_CHUNK + 1
        chunk = f"hand-{stage}-chunk-{n:02d}.jsonl"
        output = f"hand-labels-{stage}-{n:02d}.jsonl"
        (hand_dir / chunk).write_text("\n".join(lines[k : k + HAND_CHUNK]) + "\n", "utf-8")
        (hand_dir / f"hand-{stage}-prompt-{n:02d}.txt").write_text(
            hand_labeller_prompt(chunk, output), "utf-8"
        )
        chunks.append({"chunk": chunk, "output": output, "items": list(ids[k : k + HAND_CHUNK]),
                       "chunk_sha256": sha256_file(hand_dir / chunk)})  # fmt: skip
    return chunks


def cmd_hand_sample(args: argparse.Namespace) -> dict[str, Any]:
    """Host only (reads reply texts): the blind hand-check sample of the held-out job (and the
    abstention job, mixed in, when its features are given), or of the development job for the dry
    run: one JSON line per plan item with its id, the question id and type, the check, the
    question, the reference text and the reply, and nothing else, in the plan's order; the
    labeller's instructions; the chunks with their launch prompts; and a text-free manifest. All
    in ``--hand-dir``, a directory of its own (never the private directory that holds the judge
    labels). Prints counts and digests only."""

    population = args.population
    if population not in ("development", "heldout"):
        raise Am3gError("the hand check samples the held-out job (or the development dry run)")
    if population == "development":
        for path in (args.run_dir, args.evidence, args.features, args.hand_dir):
            check_dev_path(path)
        if args.abstention_features:
            raise Am3gError("the development dry run has no abstention questions")
    gate(population)
    hand_dir = Path(args.hand_dir)
    refuse_inside_repo(hand_dir)
    if hand_dir.exists() and any(hand_dir.iterdir()):
        raise Am3gError(f"refusing a non-empty hand directory {hand_dir}")
    if Path(args.features).resolve().parent == hand_dir.resolve():
        raise Am3gError("the hand directory must not hold the features")
    config = load_config(Path(args.config))
    features = read_gz_json(Path(args.features))
    check_features(features, config, population)
    artifact = load_artifact(config, population, args.evidence)
    sources = {population: (features, artifact, Path(args.run_dir),
                            population_arms(config, population))}  # fmt: skip
    abstention = None
    if args.abstention_features:
        gate("abstention")
        abstention = read_gz_json(Path(args.abstention_features))
        check_features(abstention, config, "abstention")
        abs_artifact = load_artifact(config, "abstention", args.abstention_evidence)
        sources["abstention"] = (abstention, abs_artifact, Path(args.abstention_run_dir),
                                 ("retrieved",))  # fmt: skip
    plan = hand_plan(features, abstention)
    lines = _sample_rows(plan, sources)
    hand_dir.mkdir(parents=True, exist_ok=True)
    sample = hand_dir / "hand-check-sample.jsonl"
    sample.write_text("\n".join(lines) + "\n", encoding="utf-8")
    instructions = hand_dir / "hand-check-instructions.txt"
    instructions.write_text(HAND_INSTRUCTIONS, encoding="utf-8")
    chunks = write_chunks(hand_dir, "first", lines, [i["item_id"] for i in plan["items"]])
    manifest = {"plan_sha256": plan["plan_sha256"], "items": [i["item_id"] for i in plan["items"]],
                "chunk_size": HAND_CHUNK, "first": chunks,
                "labeller_model": HAND_LABELLER_MODEL,
                "labeller_prompt_sha256": hand_labeller_prompt_sha256(),
                "instructions_sha256": sha256_file(instructions),
                "sample_sha256": sha256_file(sample)}  # fmt: skip
    (hand_dir / "hand-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return {"population": population, "items": len(lines), "readers": plan["readers"],
            "plan_sha256": plan["plan_sha256"], "sample_sha256": manifest["sample_sha256"],
            "instructions_sha256": manifest["instructions_sha256"], "chunks": len(chunks),
            "chunk_size": HAND_CHUNK, "labeller_model": HAND_LABELLER_MODEL,
            "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
            "features_sha256": sha256_file(Path(args.features))}  # fmt: skip


def _valid_rows(raw_lines: Sequence[str], allowed: set[str]) -> tuple[dict[str, dict], dict]:
    """Rows that parse, name an allowed item once, and carry a label of 0 or 1."""

    seen: Counter = Counter()
    parsed: dict[str, dict[str, Any]] = {}
    malformed = 0
    for line in raw_lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        item = row.get("item_id") if isinstance(row, dict) else None
        if item not in allowed or row.get("label") not in (0, 1):
            malformed += 1
            continue
        seen[item] += 1
        parsed[item] = {"item_id": item, "label": row["label"], "note": str(row.get("note", ""))}
    repeated = {i for i, n in seen.items() if n > 1}
    valid = {i: r for i, r in parsed.items() if i not in repeated}
    return valid, {"malformed_rows": malformed, "repeated_items": len(repeated)}


def cmd_hand_merge(args: argparse.Namespace) -> dict[str, Any]:
    """Merge one labelling stage's chunk outputs, whatever they hold (registration section 8).
    first: concatenate the chunk outputs in order (``hand-labels-first-raw.jsonl``), keep the
    rows that are valid, and, if items lack a valid row, write the repair sample and its chunks
    (``hand-repair-*``); otherwise write the final labels. repair: add the repair stage's valid
    rows for exactly those items and write the final labels (``hand-labels.jsonl``, sample order),
    complete or not: there is no third stage."""

    hand_dir = Path(args.hand_dir)
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text(encoding="utf-8"))
    final = hand_dir / "hand-labels.jsonl"
    if final.exists():
        raise Am3gError("the final labels exist: no further labelling stage")
    stage = args.stage
    if stage not in ("first", "repair") or stage not in manifest:
        raise Am3gError(f"no {stage} stage in the hand manifest")
    raw_lines: list[str] = []
    missing_chunks = []
    for chunk in manifest[stage]:
        path = hand_dir / chunk["output"]
        if not path.is_file():
            missing_chunks.append(chunk["output"])
            continue
        raw_lines += path.read_text(encoding="utf-8", errors="replace").splitlines()
    raw = hand_dir / f"hand-labels-{stage}-raw.jsonl"
    if raw.exists():
        raise Am3gError(f"{raw} exists: each stage is merged once")
    raw.write_text("\n".join(raw_lines) + ("\n" if raw_lines else ""), encoding="utf-8")
    allowed = {i for c in manifest[stage] for i in c["items"]}
    valid, problems = _valid_rows(raw_lines, allowed)
    out: dict[str, Any] = {"stage": stage, "raw_sha256": sha256_file(raw),
                           "chunks": len(manifest[stage]), "missing_chunk_outputs": missing_chunks,
                           "valid_rows": len(valid), **problems}  # fmt: skip
    if stage == "first":
        lacking = [i for i in manifest["items"] if i not in valid]
        (hand_dir / "hand-valid-first.json").write_text(json.dumps(valid, sort_keys=True))
        out["items_lacking_a_valid_row"] = len(lacking)
        if lacking:
            sample_text = (hand_dir / "hand-check-sample.jsonl").read_text("utf-8")
            sample = {json.loads(x)["item_id"]: x for x in sample_text.splitlines()}
            lines = [sample[i] for i in lacking]
            (hand_dir / "hand-repair-sample.jsonl").write_text("\n".join(lines) + "\n", "utf-8")
            manifest["repair"] = write_chunks(hand_dir, "repair", lines, lacking)
            (hand_dir / "hand-manifest.json").write_text(json.dumps(manifest, indent=1,
                                                                    sort_keys=True))  # fmt: skip
            out["repair_chunks"] = len(manifest["repair"])
            return out
        merged = valid
    else:
        merged = json.loads((hand_dir / "hand-valid-first.json").read_text(encoding="utf-8"))
        merged.update(valid)
    rows = [merged[i] for i in manifest["items"] if i in merged]
    final.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    out.update(final_rows=len(rows), final_complete=len(rows) == len(manifest["items"]),
               final_sha256=sha256_file(final))  # fmt: skip
    return out


def gains_that_hedge(features: dict[str, Any], readers: Sequence[str]) -> dict[str, Any]:
    """Descriptive: per reader, retrieved arm, primary judge, the rule's gains over BM25 top 4 (its
    reply judged right, top 4's wrong) and how many of those replies offer alternatives
    (``HEDGE_PATTERN``), which can contain the right answer among others."""

    out = {}
    for reader in readers:
        gains = hedges = 0
        for p in features["readers"][reader]["pools"]:
            if p["arm"] != "retrieved":
                continue
            masks = _norm_masks(p)
            top = lf.bm25_top_mask(p["bm25_rank"])
            rule = am3.nonabstain_bm25({"bm25_rank": p["bm25_rank"], "masks": masks})["mask"]
            if masks[rule]["u"]["primary"] == 1 and masks[top]["u"]["primary"] == 0:
                gains += 1
                hedges += bool(masks[rule].get("hedge"))
        out[reader] = {"gains": gains, "gains_whose_reply_hedges": hedges}
    return {"pattern": HEDGE_PATTERN, "decides": False, "readers": out}


def analyze_registered(
    heldout: dict[str, Any],
    abstention: dict[str, Any] | None,
    config: dict[str, Any],
    abstention_void: str | None = None,
    hand_labels: list[dict[str, Any]] | None = None,
    hand_labels_sha256: str | None = None,
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
        "g_j1_replay_of_am1_validation_items": gj1,
        "g_j2_abstention_judge": gj2,
    }  # fmt: skip
    h1 = h1_block(rec_h, resamples, seed, alpha)
    for reader_id, e in h1["readers"].items():
        bi = heldout["readers"][reader_id]["batch_invariant"]
        e["engine_mode"] = "batch-invariant" if bi else "default"
        e["scope"] = ("eager batch-invariant replies" if bi else
                      "vLLM default mode and this registration's batch schedule")  # fmt: skip
        e["judge_reading"] = e["reading"]
    plan = hand_plan(heldout, abstention)
    hand = hand_check(heldout, plan, hand_labels, hand_labels_sha256, alpha)
    # Precedence: VOID (V3) over JUDGE_DEPENDENT (G-J1) over the hand check.
    if not replay_ok:
        h1["status"] = f"{VOID_REPLAY}: H1 is not read"
        for e in h1["readers"].values():
            e["reading"] = "VOID"
    elif not gj1["pass"]:
        h1["status"] = "JUDGE_DEPENDENT: G-J1 (the replay of AM1's validation items) failed"
        for e in h1["readers"].values():
            e["reading"] = "JUDGE_DEPENDENT"
    else:
        h1["status"] = "read" if hand["status"] == "joined" else f"hand check {hand['status']}"
        for reader_id, e in h1["readers"].items():
            e["reading"] = confirm_reading(e["judge_reading"], hand, reader_id)
    strata = None
    if abstention is not None:
        strata = {p["question_id"]: int(p["gold_mask"]) != 0
                  for p in abstention["readers"][ANCHOR]["pools"]}  # fmt: skip
    if rec_a is not None:
        h2 = h2_block(rec_a, resamples, seed, alpha, strata=strata)
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
        "h1_gains_that_hedge": gains_that_hedge(heldout, H2_READERS),
        "cells_heldout": cells_of(rec_h, ARMS, resamples, seed, alpha),
    }  # fmt: skip
    if rec_a is not None:
        descriptive["second_judge_h2"] = h2_block(rec_a, resamples, seed, alpha,
                                                  judge="secondary", strata=strata)  # fmt: skip
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
        descriptive["natural_mix_linked_twins"] = {
            j: {r: natural_mix(rec_h[r], rec_a[r], weights, resamples, seed, judge=j,
                               link_twins=True)
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
        "h1_hand_check": hand,
        "h2": h2,
        "descriptive": descriptive,
        "verdicts": {
            "H1": {r: h1["readers"][r]["reading"] for r in H1_READERS} | {"status": h1["status"]},
            "H2": {"status": h2["status"], "decides": False},
        },
    }
    return results, per_table


def analyze_development(
    features: dict[str, Any],
    config: dict[str, Any],
    hand_labels: list[dict[str, Any]] | None = None,
    hand_labels_sha256: str | None = None,
) -> tuple[dict, list]:
    """The dry run on the development split: every cell as AM3 reported it, plus H1's and H2's
    machinery, and H1's hand check when labels are given, run on development data (labelled; it
    decides nothing)."""

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
    if hand_labels is not None:
        mech = results["mechanics"]
        hand = hand_check(features, hand_plan(features), hand_labels, hand_labels_sha256, alpha)
        mech["h1_hand_check"] = hand
        mech["h1_gains_that_hedge"] = gains_that_hedge(features, H2_READERS)
        mech["h1_readings_after_hand_check"] = {
            r: confirm_reading(e["reading"], hand, r)
            for r, e in mech["h1_block"]["readers"].items()
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
              "- G-J1 (a replay of AM1's validation items; it cannot catch reader-specific "
              f"judge errors): {v['g_j1_replay_of_am1_validation_items']}",
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
    hand = results.get("h1_hand_check", {})
    lines += ["", f"## H1's blind hand check ({hand.get('status')}; agent labels, D9)", ""]
    if hand.get("status") == "joined":
        lines += [
            "| Reader | discordant questions | b (hand) | c (hand) | p | p (Holm) | hand label | "
            "judge reading | reading |",
            "|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for r, e in hand["readers"].items():
            h = results["h1"]["readers"][r]
            lines.append(
                f"| {r} | {e['discordant_questions']} | {e['b_hand']} | {e['c_hand']} | "
                f"{_p(e['p_exact_mcnemar'])} | {_p(e['holm']['p_holm'])} | "
                f"{e['hand_label']} | {h['judge_reading']} | {h['reading']} |"
            )
        a = hand["agreement"]
        lines += ["", f"Hand against judge (descriptive): {a['agree']} of {a['items']} items "
                  f"agree, kappa {_f(a['kappa'])}.", ""]  # fmt: skip
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


def check_hand_plan(hand: dict[str, Any], expected: str | None) -> None:
    """Labels join by item id, so they must belong to the plan the receipt names."""

    if expected is None or hand["plan_sha256"] != expected:
        raise Am3gError(
            "the hand labels' receipted plan differs from the plan these features give "
            f"({hand['plan_sha256']})"
        )


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
        labels, digest = (read_hand_labels(Path(args.hand_labels), args.hand_labels_sha256)
                          if args.hand_labels else (None, None))  # fmt: skip
        results, per_table = analyze_development(features, config, labels, digest)
        if labels is not None:
            check_hand_plan(results["mechanics"]["h1_hand_check"], args.hand_plan_sha256)
        results["features_sha256"] = {"development": sha256_file(Path(args.development_features))}
    else:
        if not args.heldout_features:
            raise Am3gError("the registered analysis needs --heldout-features")
        if bool(args.abstention_features) == bool(args.abstention_void):
            raise Am3gError("give exactly one of --abstention-features and --abstention-void")
        if not (args.hand_labels and args.hand_labels_sha256 and args.hand_plan_sha256):
            raise Am3gError(
                "the registered analysis needs --hand-labels, --hand-labels-sha256 and "
                "--hand-plan-sha256 (the blind hand check's labels, their digest and the plan's, "
                "as receipted and committed before the join)"
            )
        gate("heldout")
        gate("abstention")
        heldout = read_gz_json(Path(args.heldout_features))
        abstention = (
            read_gz_json(Path(args.abstention_features)) if args.abstention_features else None
        )
        labels, digest = read_hand_labels(Path(args.hand_labels), args.hand_labels_sha256)
        results, per_table = analyze_registered(
            heldout, abstention, config, args.abstention_void, labels, digest
        )
        check_hand_plan(results["h1_hand_check"], args.hand_plan_sha256)
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


def combined_power(n: int, rate: float, confirm: float, alpha: float) -> float:
    """H1's power with the hand check (section 7.1), with no pair against the rule: the judge
    counts b ~ Binomial(n, rate) gains and rejects when b >= k (the exact test's threshold at
    ``alpha`` with c = 0); the hand confirms each judge-counted gain with probability ``confirm``,
    b_hand ~ Binomial(b, confirm), and must reject too (b_hand >= k)."""

    k = 1
    while ks.mcnemar_exact(k, 0) > alpha:
        k += 1
    total = 0.0
    for b in range(k, n + 1):
        w = ks._pmf(b, n, rate)
        if w < 1e-15:
            continue
        total += w * binom_tail_at_least(k, b, confirm)
    return min(1.0, total)


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
        combined = {}
        for label, r in (("development rate", rate), ("half the development rate", rate / 2),
                         ("a quarter of it", rate / 4),
                         ("the anchor's held-out rate (39/347)", 39 / 347)):  # fmt: skip
            combined[label] = {
                f"a={a}": {"power_alpha_0.025": combined_power(n1, r, a, 0.025),
                           "power_alpha_0.05": combined_power(n1, r, a, 0.05)}
                for a in (1.0, 0.9, 0.8)
            }  # fmt: skip
        h1[reader_id] = {"development_b_c": [b, c], "scenarios": rows,
                         "with_the_hand_check": combined}  # fmt: skip
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
               "the two columns bound its power. with_the_hand_check: the power of the combined "
               "rule (the judge's test and the hand labels' test both reject), with no pair "
               "against the rule and each judge-counted gain confirmed by the hand with "
               "probability a"},
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


# --------------------------------------------------------------------------- the rerun rule

#: The steps every population needs: a complete pass of each reader (OLMo-2 from either of its
#: steps) and of the primary judge. The second judge is descriptive only.
ESSENTIAL = {
    "qwen3-8b": ("rd-qwen3-8b",),
    "olmo-2-1124-7b-instruct": ("rd-olmo2", "rd-olmo2-default"),
    "qwen3.5-9b": ("rd-qwen35-9b-default",),
    "judge32": ("judge32",),
}
#: Lane termination reasons (infra/slurm/host-single-node/docker-research.sbatch) of a job that
#: never started its workload: always an infrastructure failure.
NEVER_STARTED = ("gpu_prolog_unavailable", "foreign_gpu_process", "hard_stop_before_start")
#: A signal this close to the lane's hard stop is the time limit's, not an outside event.
SIGNAL_AT_LIMIT_S = 300


def read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with contextlib.suppress(OSError):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                out[key.strip()] = value.strip()
    return out


def _utc(value: str | None) -> float | None:
    if not value or value == "none":
        return None
    try:
        return time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None


def rerun_decision(
    summary: dict[str, Any] | None, termination: dict[str, str], is_rerun: bool = False
) -> dict:
    """The registration's rerun rule (section 8), mechanically, from the driver's summary and the
    lane's termination record, before extract reads the job. In order:

    1. "rerun" when the workload never started (``NEVER_STARTED``); with no driver summary,
       "no-rerun" after the lane's hard stop and "rerun" otherwise.
    2. "void" (V1) when the model verification failed or a worker found its engine mode other
       than the pinned one (worker exit 2).
    3. "complete" when every essential step completed (``ESSENTIAL``); extract reads this job.
    4. For an incomplete job: "no-rerun" (VOID, V2, time budget) after the lane's hard stop;
       for a signal (a lane reason starting ``signal_`` or a signal the driver recorded),
       "no-rerun" when the lane finished within ``SIGNAL_AT_LIMIT_S`` of its hard stop (the
       limit's signal) and "rerun" otherwise (a cancellation or a node event).
    5. Per essential unit: "no-rerun" for a step skipped for lack of time, a pass stopped by its
       max_s or the deadline, or a worker killed as late; "rerun" for an engine that failed to
       start (OLMo-2's batch-invariant step excepted, whose fallback decides), a failed smoke
       check or a worker that ended without its done record.

    A "rerun" of a job that is itself the registration's rerun becomes "void" (V2): one rerun per
    population. The signal is dated by the lane's finish time (``finished_at``), the only time the
    lane records."""

    out = _rerun_decision(summary, termination)
    if is_rerun and out["decision"] == "rerun":
        out = out | {"decision": "void", "rule": "V2",
                     "why": f"the rerun is incomplete too ({out['why']}); one rerun per "
                     "population"}  # fmt: skip
    return out | {"is_rerun": is_rerun}


def _rerun_decision(summary: dict[str, Any] | None, termination: dict[str, str]) -> dict:
    reason = termination.get("reason", "")
    if reason in NEVER_STARTED:
        return {"decision": "rerun", "why": f"lane: {reason} (the workload never started)"}
    if summary is None:
        if reason == "hard_stop":
            return {"decision": "no-rerun", "why": "lane hard stop before the driver's summary"}
        return {"decision": "rerun", "why": f"no driver summary (lane reason {reason or 'none'})"}
    verification = summary.get("model_verification")
    if isinstance(verification, dict) and "error" in verification:
        return {"decision": "void", "rule": "V1", "why": "model verification failed"}
    steps = summary.get("steps", {})
    statuses = {sid: rec.get("status") for sid, rec in steps.items()}
    out: dict[str, Any] = {"steps": statuses, "lane_reason": reason}
    for sid, rec in steps.items():
        if (rec.get("worker_done") or {}).get("exit") == 2:
            return out | {"decision": "void", "rule": "V1",
                          "why": f"{sid}: the engine mode differs from the pin"}  # fmt: skip
    incomplete = [
        unit
        for unit, step_ids in ESSENTIAL.items()
        if not any(steps.get(sid, {}).get("status") == "complete" for sid in step_ids)
    ]
    if not incomplete:
        return out | {"decision": "complete", "why": "every essential step completed",
                      "second_judge": statuses.get("judge8")}  # fmt: skip
    out["incomplete"] = incomplete
    if reason == "hard_stop":
        return out | {"decision": "no-rerun", "why": "the lane's hard stop (the job's limit)"}
    hard_stop, finished = (
        _utc(termination.get("hard_stop_at")),
        _utc(termination.get("finished_at")),
    )
    at_limit = (
        hard_stop is not None
        and finished is not None
        and (hard_stop - finished <= SIGNAL_AT_LIMIT_S)
    )
    if reason.startswith("signal_") or summary.get("signal"):
        if at_limit:
            return out | {"decision": "no-rerun", "why": "a signal at the limit (lane finish "
                          f"within {SIGNAL_AT_LIMIT_S} s of its hard stop)"}  # fmt: skip
        return out | {"decision": "rerun", "why": "a signal before the limit (a cancellation or "
                      "a node event)"}  # fmt: skip
    for unit in incomplete:
        for sid in ESSENTIAL[unit]:
            rec = steps.get(sid, {})
            status, why = rec.get("status"), str(rec.get("reason", ""))
            if sid == "rd-olmo2" and status in ("engine-failed", "smoke-failed"):
                continue  # its fallback decides
            if status is None or (status == "skipped" and why.startswith("no reader")):
                continue
            if status == "skipped" and why.startswith("remaining"):
                return out | {"decision": "no-rerun", "why": f"{sid}: skipped for lack of time"}
            if status == "partial" or rec.get("killed") == "late":
                return out | {"decision": "no-rerun", "why": f"{sid}: stopped by a time budget"}
            if status in ("engine-failed", "smoke-failed", "failed"):
                return out | {"decision": "rerun", "why": f"{sid}: {status}"}
        return out | {"decision": "rerun", "why": f"{unit}: no complete pass"}
    return out | {"decision": "rerun", "why": "incomplete"}


def cmd_rerun_decision(args: argparse.Namespace) -> dict[str, Any]:
    job_dir = Path(args.job_dir)
    summary_path = job_dir / "am3g" / "summary.json"
    summary = None
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except ValueError:
            summary = None
    decision = rerun_decision(summary, read_env_file(job_dir / "termination.env"), args.is_rerun)
    return {"population": args.population, "job_dir": job_dir.name} | decision


# --------------------------------------------------------------------------- main


def check_config_binding(args: argparse.Namespace) -> None:
    """The held-out and abstention populations run only with the pinned config: its path (whose
    SHA-256 section 16 pins) and no other."""

    gated = False
    if args.command in ("run", "worker", "extract", "hand-sample"):
        gated = GATED.get(args.population, False)
    elif args.command in ("selftest", "plan"):
        gated = args.population == "heldout"
    elif args.command == "analyze":
        gated = not args.development_features
    if gated and Path(args.config).resolve() != CONFIG_PATH.resolve():
        pinned = CONFIG_PATH.relative_to(PROJECT_ROOT)
        raise Am3gError(f"the {args.command} command runs the held-out and abstention "
                        f"populations only with the pinned config {pinned}")  # fmt: skip


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
    analyze_p.add_argument("--hand-labels", default=None)
    analyze_p.add_argument("--hand-labels-sha256", default=None)
    analyze_p.add_argument("--hand-plan-sha256", default=None)
    analyze_p.add_argument("--output-dir", required=True)
    compare = sub.add_parser("dryrun-compare", allow_abbrev=False)
    compare.add_argument("--development-features", required=True)
    compare.add_argument("--output-dir", required=True)
    power_p = sub.add_parser("power", allow_abbrev=False)
    power_p.add_argument("--am3-features", required=True)
    power_p.add_argument("--am3-features-sha256", required=True)
    power_p.add_argument("--output", required=True)
    facts = sub.add_parser("abstention-facts", allow_abbrev=False)
    facts.add_argument("--source", required=True)
    facts.add_argument("--split-file", required=True)
    facts.add_argument("--evidence", required=True)
    facts.add_argument("--output", required=True)
    hand = sub.add_parser("hand-sample", allow_abbrev=False)
    hand.add_argument("--population", required=True, choices=("development", "heldout"))
    hand.add_argument("--run-dir", required=True)
    hand.add_argument("--evidence", required=True)
    hand.add_argument("--features", required=True)
    hand.add_argument("--abstention-run-dir", default=None)
    hand.add_argument("--abstention-evidence", default=None)
    hand.add_argument("--abstention-features", default=None)
    hand.add_argument("--hand-dir", required=True)
    merge = sub.add_parser("hand-merge", allow_abbrev=False)
    merge.add_argument("--hand-dir", required=True)
    merge.add_argument("--stage", required=True, choices=("first", "repair"))
    rerun = sub.add_parser("rerun-decision", allow_abbrev=False)
    rerun.add_argument("--population", required=True, choices=POPULATIONS)
    rerun.add_argument("--job-dir", required=True)
    rerun.add_argument("--is-rerun", action="store_true")
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args(argv)
    try:
        check_config_binding(args)
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
        commands = {
            "dryrun-compare": cmd_dryrun_compare,
            "power": cmd_power,
            "abstention-facts": cmd_abstention_facts,
            "hand-sample": cmd_hand_sample,
            "hand-merge": cmd_hand_merge,
            "rerun-decision": cmd_rerun_decision,
        }
        print(json.dumps(commands[args.command](args), indent=2, sort_keys=True))
        return 0
    except (Am3gError, am3.Am3Error, ks.KeepsetError, ms.StudyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as exc:
        if args.command in ("run", "worker"):
            raise  # the GPU job's driver and workers record their own failures
        # Section 8: no failure surfaces as a traceback; an input that is missing or unreadable
        # where no named check caught it is reported as the V2 void with its cause.
        print(f"error: {VOID_INCOMPLETE}: an input is missing or unreadable: {exc!r}",
              file=sys.stderr)  # fmt: skip
        return 2


if __name__ == "__main__":
    sys.exit(main())
