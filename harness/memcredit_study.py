"""AM1 study helpers (``memcredit-study-v1``): pure Python plus numpy, no torch, no vLLM.

The development-set pilot (EXPLORATORY) and the draft registration ``am1-memory-credit-v1`` share
these definitions:

* config loading (``experiments/am1/memcredit-study-v1.yaml``);
* the usable set and the seeded development / held-out split;
* the two pool arms (``harness.memcredit.build_pools``, Step 0's rules) and AM2's content-placebo
  arms (length- and rank-matched swaps, reorders);
* the request table (subset table, swaps, reorders) and its reader messages;
* LongMemEval's official answer-check prompt and label rule (the judge);
* the credit estimators read off an exact 2^k table (exact Shapley and Banzhaf, leave-one-out,
  leave-one-in, permutation Shapley, SNIPW over random exposures), the structure census and
  keep-set regret against the exact optimum;
* small statistics (Cohen's kappa, AUROC, Spearman, a cluster bootstrap).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from harness import memcredit as mc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am1" / "memcredit-study-v1.yaml"
EXPERIMENT_ID = "memcredit-study-v1"
#: Configs that share this module: the development pilot and its cross-GPU A/A diagnostic.
CONFIG_IDS = (EXPERIMENT_ID, "memcredit-study-v1-aa")
AA_CONFIG_PATH = PROJECT_ROOT / "experiments" / "am1" / "memcredit-study-v1-aa.yaml"
REGISTRATION_ID = "am1-memory-credit-v1"
SPLITS = ("development", "heldout")
REQUEST_KINDS = ("table", "swap", "reorder")


class StudyError(ValueError):
    """The study config, its inputs or its outputs are invalid."""


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") not in CONFIG_IDS:
        raise StudyError(f"not a {EXPERIMENT_ID} config")
    if config.get("claim_level") != "exploratory":
        raise StudyError("the development pilot is exploratory only")
    seeds = config.get("seeds")
    if seeds != [42, 43, 44]:
        raise StudyError("seeds must be [42, 43, 44]")
    declared = set(seeds)
    seeded = [
        ("split.seed", config["split"]["seed"]),
        ("pools.distractor_seed", config["pools"]["distractor_seed"]),
        ("placebo.reorder_seed", config["placebo"]["reorder_seed"]),
        ("judge.validation.derangement_seed", config["judge"]["validation"]["derangement_seed"]),
        ("judge.hand_check.seed", config["judge"]["hand_check"]["seed"]),
        ("internal.xfit_seed", config["internal"]["xfit_seed"]),
        ("analysis.bootstrap.seed", config["analysis"]["bootstrap"]["seed"]),
        ("analysis.power.seed", config["analysis"]["power"]["seed"]),
        ("job.shuffle_seed", config["job"]["shuffle_seed"]),
    ]
    for name, value in seeded:
        if value not in declared:
            raise StudyError(f"{name} must be a declared seed")
    if list(config["analysis"]["estimator_seeds"]) != seeds:
        raise StudyError("analysis.estimator_seeds must be the declared seeds")
    if set(config["pools"]["arms"]) != {"retrieved", "gold"}:
        raise StudyError("the two pool arms are retrieved and gold")
    k = int(config["pools"]["size"])
    if not 1 <= k <= 10:
        raise StudyError("pool size must be 1..10")
    fraction = float(config["split"]["development_fraction"])
    if not 0.0 < fraction < 0.5:
        raise StudyError("the development fraction must be in (0, 0.5)")
    if int(config["placebo"]["swap_variants"]) < 1:
        raise StudyError("at least one swap variant")
    for budget in config["analysis"]["keep_budgets"]:
        if not 1 <= int(budget) < k:
            raise StudyError("keep budgets must be 1..k-1")
    if config["analysis"]["headline_budget"] not in config["analysis"]["keep_budgets"]:
        raise StudyError("the headline budget must be one of the keep budgets")
    worker_ids: list[str] = []
    for phase in config["job"]["phases"]:
        gpus = [w["gpu"] for w in phase["workers"]]
        if len(set(gpus)) != len(gpus):
            raise StudyError(f"phase {phase['id']}: two workers on one GPU")
        for source in phase.get("judge_items_from", []):
            if source not in worker_ids:
                raise StudyError(f"phase {phase['id']}: judge items from an unknown reader")
        for worker in phase["workers"]:
            if worker.get("cache_from") is not None and worker["cache_from"] not in worker_ids:
                raise StudyError(f"{worker['id']}: cache_from names no earlier worker")
            if worker.get("questions") is not None and int(worker["questions"]) < 1:
                raise StudyError(f"{worker['id']}: questions must be positive")
            if not isinstance(worker.get("enforce_eager", False), bool):
                raise StudyError(f"{worker['id']}: enforce_eager must be a boolean")
            worker_ids.append(worker["id"])
            if worker["kind"] not in ("reader", "judge", "attention"):
                raise StudyError(f"{worker['id']}: unknown worker kind")
            if not 0 <= int(worker["gpu"]) < int(config["job"]["gpus"]):
                raise StudyError(f"{worker['id']}: GPU outside the job's allocation")
            if worker["kind"] == "judge" and worker["judge"] not in ("primary", "secondary"):
                raise StudyError(f"{worker['id']}: judge must be primary or secondary")
            if worker.get("order", "canonical") not in ("canonical", "shuffled"):
                raise StudyError(f"{worker['id']}: order must be canonical or shuffled")
    if len(set(worker_ids)) != len(worker_ids):
        raise StudyError("worker ids must be unique")
    return config


def pool_config(config: dict[str, Any]) -> dict[str, Any]:
    """The keys ``harness.memcredit.build_pools`` reads."""

    return {"pools": config["pools"], "retriever": config["retriever"]}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- usable set and split


def usable_reason(record: dict[str, Any], rules: dict[str, Any]) -> str | None:
    """None if the question is usable, else why not (Step 0's census definition)."""

    if rules.get("exclude_abstention", True) and mc.is_abstention(record):
        return "abstention"
    gold = [t for t in mc.iter_turns(record) if t.has_answer]
    if len(gold) < int(rules["min_gold_turns"]):
        return "no gold turn"
    if any(t.role not in set(rules["gold_roles"]) for t in gold):
        return "a gold turn is not a user turn"
    if len(gold) > int(rules["max_gold_turns"]):
        return "more gold turns than the cap"
    if len(gold) > int(rules["pool_size"]):
        return "more gold turns than the pool"
    return None


def round_half_up(value: float) -> int:
    return int(Decimal(repr(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def make_split(records: Sequence[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """The seeded, type-stratified development / held-out split of the usable questions."""

    rules = config["usable"]
    spec = config["split"]
    seed = int(spec["seed"])
    fraction = float(spec["development_fraction"])
    ids = [r["question_id"] for r in records]
    if len(set(ids)) != len(ids):
        raise StudyError("duplicate question ids in the source")
    by_type: dict[str, list[str]] = {}
    reasons: dict[str, int] = {}
    for record in records:
        reason = usable_reason(record, rules)
        reasons[reason or "usable"] = reasons.get(reason or "usable", 0) + 1
        if reason is None:
            by_type.setdefault(record["question_type"], []).append(record["question_id"])
    development: list[str] = []
    heldout: list[str] = []
    per_type: dict[str, dict[str, int]] = {}
    for qtype in sorted(by_type):
        pool = sorted(by_type[qtype])
        random.Random(f"{seed}:{qtype}").shuffle(pool)
        n_dev = round_half_up(fraction * len(pool))
        development.extend(sorted(pool[:n_dev]))
        heldout.extend(sorted(pool[n_dev:]))
        per_type[qtype] = {"usable": len(pool), "development": n_dev, "heldout": len(pool) - n_dev}
    development.sort()
    heldout.sort()
    if set(development) & set(heldout):
        raise StudyError("the split overlaps")
    body = {
        "experiment_id": EXPERIMENT_ID,
        "registration_id": REGISTRATION_ID,
        "source": config["source"],
        "usable_rules": rules,
        "rule": (
            "per question type (sorted ids): random.Random(f'{seed}:{type}').shuffle; the first "
            "round_half_up(fraction * n) are development, the rest held out"
        ),
        "seed": seed,
        "development_fraction": fraction,
        "reasons": dict(sorted(reasons.items())),
        "per_type": per_type,
        "counts": {
            "usable": len(development) + len(heldout),
            "development": len(development),
            "heldout": len(heldout),
            "source_questions": len(records),
        },  # fmt: skip
        "development": development,
        "heldout": heldout,
    }
    body["development_sha256"] = mc.sha256_text("\n".join(development))
    body["heldout_sha256"] = mc.sha256_text("\n".join(heldout))
    return body


def load_split(path: Path, config: dict[str, Any]) -> dict[str, Any]:
    split = json.loads(path.read_text(encoding="utf-8"))
    if split.get("experiment_id") != EXPERIMENT_ID or split.get("source") != config["source"]:
        raise StudyError("the split belongs to another experiment or source")
    for name in SPLITS:
        if mc.sha256_text("\n".join(split[name])) != split[f"{name}_sha256"]:
            raise StudyError(f"the {name} ids differ from their SHA-256")
    if set(split["development"]) & set(split["heldout"]):
        raise StudyError("the split overlaps")
    return split


def registration_frozen(ledger: Path, registration: Path) -> bool:
    """True when the ledger holds a row for the registration id with the file's SHA-256."""

    if not ledger.is_file() or not registration.is_file():
        return False
    digest = sha256_file(registration)
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("experiment_id") == REGISTRATION_ID and row.get("sha256") == digest:
            return True
    return False


# --------------------------------------------------------------------------- placebos


def _turn_entries(record: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    max_chars = int(config["pools"]["max_memory_chars"])
    ranked = mc.rank_user_turns(record, config["retriever"])
    return [mc.memory_entry(t, r, s, max_chars) for r, (t, s) in enumerate(ranked)]


def _key(entry: dict[str, Any]) -> tuple[int, int]:
    return (int(entry["session_index"]), int(entry["turn_index"]))


def match_swaps(
    memory: dict[str, Any],
    candidates: Sequence[dict[str, Any]],
    variants: int,
    tolerances: Sequence[float],
) -> tuple[list[dict[str, Any]], float | None]:
    """``variants`` length- then rank-matched candidates for one memory.

    The first tolerance on |log(len ratio)| that leaves at least ``variants`` candidates is used
    (all candidates when none does); among those, the nearest BM25 rank, then the smaller length
    gap, then session and turn index. Lengths are the prompt text's characters.
    """

    if len(candidates) < variants:
        raise StudyError("fewer placebo candidates than variants")
    length = max(1, len(memory["text"]))

    def gap(c: dict[str, Any]) -> float:
        return abs(math.log(max(1, len(c["text"])) / length))

    chosen_tol: float | None = None
    eligible = list(candidates)
    for tol in tolerances:
        within = [c for c in candidates if gap(c) <= float(tol) + 1e-12]
        if len(within) >= variants:
            eligible, chosen_tol = within, float(tol)
            break
    eligible.sort(
        key=lambda c: (abs(int(c["bm25_rank"]) - int(memory["bm25_rank"])), gap(c), *_key(c))
    )
    return eligible[:variants], chosen_tol


def build_placebos(
    record: dict[str, Any], pools: dict[str, list[dict[str, Any]]], config: dict[str, Any]
) -> dict[str, Any]:
    """Per arm: ``swaps`` (per slot, ``variants`` replacement entries) and ``reorders``."""

    spec = config["placebo"]
    variants = int(spec["swap_variants"])
    tolerances = [float(t) for t in spec["length_log_tolerances"]]
    entries = _turn_entries(record, config)
    in_pools = {_key(m) for pool in pools.values() for m in pool}
    pool_texts = {m["text"] for pool in pools.values() for m in pool}
    candidates = [
        e
        for e in entries
        if not e["is_gold"]
        and _key(e) not in in_pools
        and e["text"] not in pool_texts
        and e["text"].strip()
    ]
    out: dict[str, Any] = {}
    for arm, pool in pools.items():
        swaps = []
        for memory in pool:
            chosen, tol = match_swaps(memory, candidates, variants, tolerances)
            swaps.append(
                [
                    {
                        "session_index": c["session_index"],
                        "turn_index": c["turn_index"],
                        "session_id": c["session_id"],
                        "bm25_rank": c["bm25_rank"],
                        "chars": c["chars"],
                        "truncated": c["truncated"],
                        "text": c["text"],
                        "text_sha256": c["text_sha256"],
                        "length_log_ratio": round(
                            math.log(max(1, len(c["text"])) / max(1, len(memory["text"]))), 6
                        ),
                        "rank_gap": int(c["bm25_rank"]) - int(memory["bm25_rank"]),
                        "tolerance": tol,
                    }
                    for c in chosen
                ]
            )
        k = len(pool)
        shuffled = list(range(k))
        rng = random.Random(f"{int(spec['reorder_seed'])}:{record['question_id']}:{arm}")
        while True:
            rng.shuffle(shuffled)
            if k < 2 or (shuffled != list(range(k)) and shuffled != list(range(k))[::-1]):
                break
        out[arm] = {"swaps": swaps, "reorders": [list(range(k))[::-1], list(shuffled)]}
    return out


# --------------------------------------------------------------------------- requests


def pool_request_specs(k: int, variants: int, reorders: int) -> list[dict[str, Any]]:
    """One pool's requests in canonical order: 2^k masks, then swaps (slot, variant), reorders."""

    specs: list[dict[str, Any]] = [{"kind": "table", "mask": m} for m in range(1 << k)]
    specs += [{"kind": "swap", "slot": i, "variant": v} for i in range(k) for v in range(variants)]
    specs += [{"kind": "reorder", "variant": r} for r in range(reorders)]
    return specs


def request_table(artifact: dict[str, Any], arms: Sequence[str]) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for q_index, question in enumerate(artifact["questions"]):
        for arm in arms:
            k = len(question["pools"][arm])
            placebo = question["placebos"][arm]
            variants = len(placebo["swaps"][0]) if placebo["swaps"] else 0
            for spec in pool_request_specs(k, variants, len(placebo["reorders"])):
                table.append(
                    {"index": len(table), "question_index": q_index,
                     "question_id": question["question_id"], "arm": arm, **spec}
                )  # fmt: skip
    return table


def request_memories(artifact: dict[str, Any], request: dict[str, Any]) -> list[dict[str, Any]]:
    question = artifact["questions"][request["question_index"]]
    pool = question["pools"][request["arm"]]
    kind = request["kind"]
    if kind == "table":
        return mc.subset(pool, int(request["mask"]))
    placebo = question["placebos"][request["arm"]]
    if kind == "swap":
        slot = int(request["slot"])
        replacement = placebo["swaps"][slot][int(request["variant"])]
        memories = [dict(m) for m in pool]
        memories[slot] = {**memories[slot], "text": replacement["text"]}
        return memories
    if kind == "reorder":
        return [pool[j] for j in placebo["reorders"][int(request["variant"])]]
    raise StudyError(f"unknown request kind {kind}")


def request_message(
    artifact: dict[str, Any], request: dict[str, Any], template: dict[str, Any]
) -> str:
    question = artifact["questions"][request["question_index"]]
    return mc.user_message(question, request_memories(artifact, request), template)


def memory_line(memory: dict[str, Any]) -> str:
    """The line ``harness.memcredit.user_message`` writes for one memory."""

    return f"- [{memory['date']}] {memory['text']}"


def shuffled(indices: Sequence[int], seed: int) -> list[int]:
    out = list(indices)
    random.Random(seed).shuffle(out)
    return out


# --------------------------------------------------------------------------- the judge

#: LongMemEval's ``get_anscheck_prompt`` (src/evaluation/evaluate_qa.py, github.com/xiaowu0162/
#: LongMemEval at 9e0b455f4ef0e2ab8f2e582289761153549043fc, MIT), word for word; the abstention
#: template is left out because the study excludes abstention questions.
_COMMON = (
    "I will give you a question, a correct answer, and a response from a "
    "model. Please answer yes if the response contains the correct answer. "
    "Otherwise, answer no. If the response is equivalent to the correct "
    "answer or contains all the intermediate steps to get the correct answer, "
    "you should also answer yes. If the response only contains a subset of the "
    "information required by the answer, answer no. "
)
JUDGE_TEMPLATES = {
    "single-session-user": _COMMON
    + "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response "
    "correct? Answer yes or no only.",
    "temporal-reasoning": _COMMON + "In addition, do not "
    "penalize off-by-one errors for the number of days. If the question asks "
    "for the number of days/weeks/months, etc., and the model makes off-by-one "
    "errors (e.g., predicting 19 days when the answer is 18), the model's "
    "response is still correct. \n\nQuestion: {}\n\nCorrect Answer: "
    "{}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or "
    "no only.",
    "knowledge-update": (
        "I will give you a question, a correct answer, and a response from a "
        "model. Please answer yes if the response contains the correct answer. "
        "Otherwise, answer no. If the response contains some previous information "
        "along with an updated answer, the response should be considered as correct "
        "as long as the updated answer is the required answer.\n\nQuestion: "
        "{}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response "
        "correct? Answer yes or no only."
    ),
    "single-session-preference": (
        "I will give you a question, a rubric for desired personalized response, "
        "and a response from a model. Please answer yes if the response satisfies "
        "the desired response. Otherwise, answer no. The model does not need to "
        "reflect all the points in the rubric. The response is correct as long as "
        "it recalls and utilizes the user's personal information correctly."
        "\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the "
        "model response correct? Answer yes or no only."
    ),
}
JUDGE_TEMPLATES["single-session-assistant"] = JUDGE_TEMPLATES["single-session-user"]
JUDGE_TEMPLATES["multi-session"] = JUDGE_TEMPLATES["single-session-user"]


def judge_prompt(question_type: str, question: str, answer: str, response: str) -> str:
    try:
        template = JUDGE_TEMPLATES[question_type]
    except KeyError as exc:
        raise StudyError(f"no judge template for {question_type}") from exc
    return template.format(question, answer, response)


def parse_judgment(reply: str) -> tuple[int, bool]:
    """The official label ("yes" occurs, case-folded) and a strict well-formedness flag."""

    normalized = reply.strip().casefold().rstrip(".")
    return int("yes" in reply.casefold()), normalized in {"yes", "no"}


def validation_items(artifact: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Per question: the reference answer (expect 1), "I don't know." (expect 0) and another
    same-type question's reference answer (expect 0), by a seeded derangement within each type."""

    questions = artifact["questions"]
    items: list[dict[str, Any]] = []
    by_type: dict[str, list[int]] = {}
    for q_index, q in enumerate(questions):
        by_type.setdefault(q["question_type"], []).append(q_index)
    partner: dict[int, int] = {}
    for qtype in sorted(by_type):
        members = by_type[qtype]
        if len(members) < 2:
            continue
        rng = random.Random(f"{int(spec['derangement_seed'])}:{qtype}")
        while True:
            perm = list(members)
            rng.shuffle(perm)
            if all(a != b for a, b in zip(members, perm, strict=True)):
                break
        for a, b in zip(members, perm, strict=True):
            if str(questions[b]["answer"]).strip() != str(questions[a]["answer"]).strip():
                partner[a] = b
    for q_index, q in enumerate(questions):
        items.append({"question_index": q_index, "response": str(q["answer"]),
                      "source": "validation:reference", "expected": 1})  # fmt: skip
        items.append({"question_index": q_index, "response": str(spec["idk_response"]),
                      "source": "validation:idk", "expected": 0})  # fmt: skip
        if q_index in partner:
            other = questions[partner[q_index]]
            items.append({"question_index": q_index, "response": str(other["answer"]),
                          "source": "validation:other-answer", "expected": 0,
                          "other_question_id": other["question_id"]})  # fmt: skip
    return items


def judge_item_table(
    artifact: dict[str, Any],
    replies: dict[int, str],
    requests: Sequence[dict[str, Any]],
    validation: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply) from the reader, then the validation items, in
    canonical order (question index, then text). ``replies`` maps request index to reply text."""

    seen: dict[tuple[int, str], dict[str, Any]] = {}
    for request in requests:
        text = replies.get(request["index"])
        if text is None:
            continue
        key = (int(request["question_index"]), text.strip())
        if key not in seen:
            seen[key] = {"question_index": key[0], "response": key[1], "source": "reader"}
    items = [seen[k] for k in sorted(seen)]
    for item in validation:
        key = (int(item["question_index"]), item["response"].strip())
        items.append(dict(item, response=key[1]))
    out = []
    for index, item in enumerate(items):
        q = artifact["questions"][item["question_index"]]
        out.append(dict(item, index=index, question_id=q["question_id"],
                        question_type=q["question_type"]))  # fmt: skip
    return out


def judge_message(artifact: dict[str, Any], item: dict[str, Any]) -> str:
    q = artifact["questions"][item["question_index"]]
    return judge_prompt(q["question_type"], q["question"], str(q["answer"]), item["response"])


# --------------------------------------------------------------------------- set functions


def banzhaf(values: Sequence[float]) -> list[float]:
    """Exact Banzhaf values: the mean marginal of i over the 2^(k-1) sets without i."""

    k = mc.check_table(values)
    out = []
    for i in range(k):
        bit = 1 << i
        total = sum(float(values[m | bit]) - float(values[m]) for m in range(1 << k) if not m & bit)
        out.append(total / (1 << (k - 1)))
    return out


def leave_one_in(values: Sequence[float]) -> list[float]:
    k = mc.check_table(values)
    return [float(values[1 << i]) - float(values[0]) for i in range(k)]


def permutation_shapley(
    values: Sequence[float], permutations: int, rng: random.Random
) -> tuple[list[float], int]:
    """Monte Carlo Shapley over ``permutations`` uniform orders; also the distinct subsets read."""

    k = mc.check_table(values)
    phi = [0.0] * k
    seen: set[int] = set()
    items = list(range(k))
    for _ in range(permutations):
        rng.shuffle(items)
        mask = 0
        seen.add(mask)
        for i in items:
            new = mask | 1 << i
            phi[i] += float(values[new]) - float(values[mask])
            mask = new
            seen.add(mask)
    return [p / permutations for p in phi], len(seen)


def snipw(values: Sequence[float], exposures: int, rng: random.Random) -> tuple[list[float], int]:
    """Self-normalized IPW contrast over random exposures (each memory kept with known
    probability 1/2): mean u with i kept minus mean u with i dropped; 0 where a side is empty.
    With equal propensities the self-normalized weights cancel to these means."""

    k = mc.check_table(values)
    masks = [rng.getrandbits(k) for _ in range(exposures)]
    out = []
    for i in range(k):
        bit = 1 << i
        inside = [float(values[m]) for m in masks if m & bit]
        outside = [float(values[m]) for m in masks if not m & bit]
        if not inside or not outside:
            out.append(0.0)
        else:
            out.append(sum(inside) / len(inside) - sum(outside) / len(outside))
    return out, len(set(masks))


def random_regret(values: Sequence[float], budget: int) -> float:
    """Expected regret of a uniformly random size-``budget`` keep set."""

    k = mc.check_table(values)
    masks = [m for m in range(1 << k) if mc.popcount(m) == budget]
    best = max(float(values[m]) for m in masks)
    return best - sum(float(values[m]) for m in masks) / len(masks)


def relevant_items(values: Sequence[float]) -> list[int]:
    k = mc.check_table(values)
    out = []
    for i in range(k):
        bit = 1 << i
        if any(float(values[m | bit]) != float(values[m]) for m in range(1 << k) if not m & bit):
            out.append(i)
    return out


def is_monotone(values: Sequence[float], decreasing: bool = False) -> bool:
    k = mc.check_table(values)
    for m in range(1 << k):
        for i in range(k):
            bit = 1 << i
            if m & bit:
                continue
            step = float(values[m | bit]) - float(values[m])
            if (step > 0) if decreasing else (step < 0):
                return False
    return True


def minimal_true_sets(values: Sequence[float]) -> list[int]:
    """Minimal masks with u = 1 (for a 0/1 table)."""

    k = mc.check_table(values)
    ones = [m for m in range(1 << k) if float(values[m]) >= 0.5]
    return [m for m in ones if not any(o != m and (o & m) == o for o in ones)]


def structure_class(values: Sequence[float]) -> str:
    """Census class of a 0/1 table: constant-0, constant-1, single (u is one memory's
    indicator), and, or, monotone-mixed, negative (u decreasing: memories only hurt) or
    non-monotone (some memory helps on some sets and hurts on others)."""

    if any(float(v) not in (0.0, 1.0) for v in values):
        raise StudyError("structure classes are defined for 0/1 tables")
    if len(set(float(v) for v in values)) == 1:
        return f"constant-{int(float(values[0]))}"
    if is_monotone(values):
        minimal = minimal_true_sets(values)
        if len(minimal) == 1:
            return "single" if mc.popcount(minimal[0]) == 1 else "and"
        if all(mc.popcount(m) == 1 for m in minimal):
            return "or"
        return "monotone-mixed"
    if is_monotone(values, decreasing=True):
        return "negative"
    return "non-monotone"


def table_summary(values: Sequence[float], gold_mask: int) -> dict[str, Any]:
    """Set-function facts of one table: spectrum, AND/OR baseline, Moebius mass by order,
    relevant memories (gold and not), the structure class, the best keep values."""

    k = mc.check_table(values)
    spectrum = mc.fourier_order_shares(values)
    m = mc.popcount(gold_mask)
    dividends = mc.moebius(values)
    mass = [0.0] * (k + 1)
    for t, v in enumerate(dividends):
        mass[mc.popcount(t)] += abs(v)
    relevant = relevant_items(values)
    return {
        "k": k,
        "gold_mask": gold_mask,
        "gold_in_pool": m,
        "mean": sum(float(v) for v in values) / len(values),
        "u_full": float(values[-1]),
        "u_empty": float(values[0]),
        "constant": len(set(float(v) for v in values)) == 1,
        "structure": structure_class(values),
        "relevant": relevant,
        "relevant_gold": [i for i in relevant if gold_mask >> i & 1],
        "relevant_nongold": [i for i in relevant if not gold_mask >> i & 1],
        "fourier_shares": spectrum["shares"],
        "fourier_share_order_2_plus": spectrum["share_order_2_plus"],
        "and_or_baseline": mc.and_or_baseline(m) if m else None,
        "moebius_abs_mass_by_order": mass,
        "best_by_budget": {b: mc.best_keep_sets(values, b)[0] for b in range(1, k)},
    }


# --------------------------------------------------------------------------- statistics


def cohen_kappa(a: Sequence[int], b: Sequence[int]) -> float | None:
    n = len(a)
    if n == 0 or n != len(b):
        return None
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1 - expected)


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """Mann-Whitney AUROC with ties counted one half; None when a class is empty."""

    pos = [s for s, y in zip(scores, labels, strict=True) if y]
    neg = [s for s, y in zip(scores, labels, strict=True) if not y]
    if not pos or not neg:
        return None
    order = sorted(set(scores))
    rank = {}
    position = 1
    counts: dict[float, int] = {}
    for s in scores:
        counts[s] = counts.get(s, 0) + 1
    for s in order:
        c = counts[s]
        rank[s] = position + (c - 1) / 2.0
        position += c
    rank_sum = sum(rank[s] for s in pos)
    n_pos, n_neg = len(pos), len(neg)
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def cluster_bootstrap(
    clusters: dict[str, list[float]], resamples: int, seed: int, alpha: float = 0.05
) -> dict[str, Any]:
    """Mean over units with a percentile interval from resampling clusters with replacement."""

    keys = sorted(k for k, v in clusters.items() if v)
    units = [x for k in keys for x in clusters[k]]
    if not units:
        return {"mean": None, "ci": [None, None], "units": 0, "clusters": 0}
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        total = 0.0
        count = 0
        for _ in keys:
            values = clusters[keys[rng.randrange(len(keys))]]
            total += sum(values)
            count += len(values)
        stats.append(total / count)
    stats.sort()
    lo = stats[int(math.floor(alpha / 2 * (resamples - 1)))]
    hi = stats[int(math.ceil((1 - alpha / 2) * (resamples - 1)))]
    return {"mean": sum(units) / len(units), "ci": [lo, hi], "units": len(units),
            "clusters": len(keys)}  # fmt: skip


def all_budget_sets(k: int, budget: int) -> list[int]:
    return [sum(1 << i for i in combo) for combo in combinations(range(k), budget)]
