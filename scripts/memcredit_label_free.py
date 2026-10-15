#!/usr/bin/env python3
"""AM1d (exploratory, CPU only, development data only): can a label-free utility choose which 4
of 8 memories to keep by search? (D113, next step 1.)

AM1b found that search over keep sets beats every per-memory credit rule when the judged utility
u(S) can be queried. Judging needs the reference answer, so that search cannot run in deployment.
AM1d replaces u(S) by utilities computed only from the reader's own outputs under each memory
subset S, read from the AM1 development pilot's raw reader pass (job 1411, ``reader-gpu0``, the
pass whose judged labels made the committed tables):

* ``conf_mean`` / ``conf_sum``: the reply's mean and summed sampled-token log-prob (every recorded
  generated token, the end-of-turn token included when it was generated);
* ``nonabstain``: 1 unless the reply matches the fixed abstention pattern list below;
* ``agree_full``: 1 when ``normalize_answer(reply(S)) == normalize_answer(reply(all 8))`` (one
  extra call, the full pool);
* ``vote``: the number of queried subsets whose normalized reply equals reply(S), then confidence;
* ``nonabstain_conf_mean``, ``nonabstain_conf_sum``, ``nonabstain_vote``: non-abstention first.

Search: read m distinct uniformly random 4-subsets (m = 8, 16, 26, 38, 70; 70 is every 4-subset),
keep the one with the best label-free score; ties go to the lower BM25 rank sum, then to the
lexicographically smaller sorted BM25 ranks (BM25 ranks are distinct within a pool, so this is a
total order). Every choice is scored with the oracle table: regret = best 4-subset utility minus
u(chosen) (AM1b's convention) and accuracy u(chosen), against BM25 top 4, the full pool of 8 and a
uniformly random 4-subset.

Subcommands:

* ``extract`` (host only; reads raw reader and judge passes, which hold texts): joins every
  request to its judged label with ``memcredit_analyze.join_rows`` (the join that built the
  committed tables), checks that the joined labels reproduce ``values_hex`` of all 126 committed
  tables and stops otherwise, then writes per-request features (numbers, masks, reply-class ids
  and SHA-256 digests of normalized replies; no text) to a host-only private directory. With
  ``--eager-run-dir`` it also reads the eager replay (job 1441, first 16 questions) for a
  sensitivity check.
* ``analyze``: the search, the baselines, question-cluster bootstrap intervals and the text-free
  outputs ``results.json``, ``per-table.json.gz`` and ``tables.md``.

The script refuses any path that names held-out (confirmatory) data.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import gzip
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_cost_curve as cc  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am1d-label-free"
K = 8
BUDGET = 4
FULL = (1 << K) - 1
SEARCH_CALLS = (8, 16, 26, 38, 70)
ARMS = ("retrieved", "gold")
HEADLINE_ARM = "retrieved"
SEED_BASE = 42
N_SEEDS = 50
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42
CROSSFIT_SPLITS = 200
CROSSFIT_SEED = 42
#: Path parts that mark held-out evidence or runs; AM1d never opens a path containing one.
FORBIDDEN_PARTS = ("am1-confirmatory", "am1-memory-credit-v1")

# --------------------------------------------------------------------------- pinned inputs

#: The pilot's study artifact (development split) and its raw passes, as committed in
#: program/evidence/2026-10-15/am1-dev-pilot (README, jobs/*/raw-sha256.txt, all.json.gz).
ARTIFACT_SHA256 = "15567cf14a0c38c1f9edec1f47feceb2a6fccf116338e5957182d03f1d996ebc"
PILOT_CONFIG_ID = "memcredit-study-v1"
MAIN_PASS = {
    "name": "job 1411, reader-gpu0 (GPU 0, canonical order, compiled batch-invariant mode); "
    "labels: job 1411 judge32-gpu0 (Qwen3-32B)",
    "reader": "reader-gpu0",
    "judge": "judge32-gpu0",
    "sha256": {
        "sessions/reader-gpu0/all.json": (
            "967898423e9078656fa0beb3410eed9b4324b8fc850f0e631ac6e982912553c7"
        ),
        "sessions/reader-gpu0/all.npz": (
            "1916a8b17057b8816d0c84b22732ed88b19f7bf7357dbe592c5fa3c60583e261"
        ),
        "sessions/reader-gpu0/all.texts.jsonl.gz": (
            "ef6b575079fe31afa37c7600db8a653b7d513b4a5adf0bbe81d4d6a25c25a34f"
        ),
        "sessions/judge32-gpu0/all.json": (
            "68773539d7dc205a05ceb09cff2f935389baccef6a2286067bcbbbf9713ae6ed"
        ),
        "sessions/judge32-gpu0/all.npz": (
            "ba7e7127bae031dda413b14135b79439fbf3e9e24b0ec366d07b5d5894771536"
        ),
        "sessions/judge32-gpu0/all.texts.jsonl.gz": (
            "d3f24f78e8a2b86eeab77a6d23e8f68fbf2ead545cc4604a3ee8f485640e89b7"
        ),
        "judge-items.json": "f1df06f9a502224b69a4945ffa2f4b70a05d0cdddd5c9e2d724e8dcabacd3c60",
    },
}
EAGER_PASS = {
    "name": "job 1441, rd-eager-gpu0 (GPU 0, canonical order, eager mode, first 16 questions); "
    "labels: job 1441 judge32-gpu0 (Qwen3-32B, eager)",
    "reader": "rd-eager-gpu0",
    "judge": "judge32-gpu0",
    "questions": 16,
    "sha256": {
        "sessions/rd-eager-gpu0/all.json": (
            "4e4bd64f8520afc2257f764973d4baec82348dcd52f394cf9818528db9c71dbd"
        ),
        "sessions/rd-eager-gpu0/all.npz": (
            "2aac51fa25b9c1c41a918ac076fd3a201d0ac09cae526bbaea57ea079d089375"
        ),
        "sessions/rd-eager-gpu0/all.texts.jsonl.gz": (
            "18ed14815105cf42d7de38cf895792a8082bb2a938e3736606ac1d90d3ab366d"
        ),
        "sessions/judge32-gpu0/all.json": (
            "b96ed38d92f95cd09e47565e607cd381d0f7ac3b06aa81f97fb25b6cdbc389f4"
        ),
        "sessions/judge32-gpu0/all.npz": (
            "5298c2d96f6c175732c73e14a9f3604c194c93c78493d361d5a692a9c114f05f"
        ),
        "sessions/judge32-gpu0/all.texts.jsonl.gz": (
            "b02afa506fb5b5f5e5e5c838ebdf757f748f4fbf164a4d74f89f86ba297117b3"
        ),
        "judge-items.json": "8381e0f080b021cfb05c2d7c22007602d0ad8a70f1144000624bda912afa1f16",
    },
}

# --------------------------------------------------------------------------- abstention

#: The abstention pattern list, fixed and committed before any AM1d result was computed. Each
#: pattern is a regular expression searched in ``harness.memcredit.normalize_answer(reply)``
#: (lowercase, punctuation to spaces, articles removed, number words as digits), so "don't"
#: reads "don t". The reader's prompt asks it to say "I don't know" when the memories do not
#: contain the answer. An empty normalized reply also counts as abstaining ("empty").
ABSTENTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("i_dont_know", r"\bi (?:don t|do not|dont) know\b"),
    (
        "cannot_answer",
        r"\b(?:cannot|can t|can not|unable to|not able to) "
        r"(?:answer|determine|tell|say|know|find|recall|be determined)\b",
    ),
    ("no_information", r"\b(?:no|not enough|insufficient) (?:information|info|details|data)\b"),
    (
        "not_in_memories",
        r"\b(?:not (?:mentioned|provided|specified|stated)|"
        r"(?:do|does|did) not (?:contain|mention|include|specify)|"
        r"(?:don t|doesn t|didn t) (?:contain|mention|include|specify))\b",
    ),
)
#: SHA-256 of the canonical JSON of ABSTENTION_PATTERNS; a test pins it so the list cannot drift.
ABSTENTION_PATTERNS_SHA256 = "031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f"
_ABSTENTION_RE = tuple((name, re.compile(rx)) for name, rx in ABSTENTION_PATTERNS)


class LabelFreeError(ValueError):
    """An input, the join or a validation check failed."""


def patterns_sha256() -> str:
    return hashlib.sha256(
        json.dumps(ABSTENTION_PATTERNS, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def abstention(text: str | None) -> tuple[bool, str | None]:
    """(abstains, the first matching pattern's name) for one reply."""

    normalized = mc.normalize_answer(text or "")
    if not normalized:
        return True, "empty"
    for name, pattern in _ABSTENTION_RE:
        if pattern.search(normalized):
            return True, name
    return False, None


# --------------------------------------------------------------------------- paths and digests


def check_path(path: Path | str) -> None:
    """Refuse held-out evidence or runs before anything is opened."""

    texts = [str(path)]
    with contextlib.suppress(OSError):
        texts.append(str(Path(path).resolve()))
    for text in texts:
        for part in FORBIDDEN_PARTS:
            if part in text:
                raise LabelFreeError(f"AM1d reads development data only; refusing {path}")


def sha256_file(path: Path) -> str:
    check_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_digests(run_dir: Path, pinned: dict[str, str]) -> dict[str, str]:
    out = {}
    for relative, expected in sorted(pinned.items()):
        actual = sha256_file(run_dir / relative)
        if actual != expected:
            raise LabelFreeError(f"{relative}: SHA-256 {actual} is not the committed {expected}")
        out[relative] = actual
    return out


def canonical(payload: Any) -> bytes:
    return (json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode()


def write_gz_json(path: Path, payload: Any) -> None:
    check_path(path)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(blob, mtime=0))


def read_gz_json(path: Path) -> Any:
    check_path(path)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- join


def join_requests(
    requests: Sequence[dict[str, Any]],
    reader_rows: dict[int, dict[str, Any]],
    items: Sequence[dict[str, Any]],
    labels: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """``memcredit_analyze.join_rows``'s join for any reader pass, keeping tokens and log-prob
    bits: a request's reply (finish stop or length) is looked up as (question index, stripped
    reply) among the judge's reader items, and the item's primary label is its utility."""

    key_to_item = {
        (i["question_index"], i["response"]): i["index"] for i in items if i["source"] == "reader"
    }
    rows = []
    for request in requests:
        row = reader_rows.get(request["index"])
        text = row["text"] if row and row["finish"] in ("stop", "length") else None
        entry = dict(request, reply=text, finish=row["finish"] if row else None)
        entry["tokens"] = row["tokens"] if row else None
        entry["bits"] = row["bits"] if row else None
        if text is not None:
            item = key_to_item.get((request["question_index"], text.strip()))
            entry["item"] = item
            entry["u"] = labels.get(item, {}).get("label") if item is not None else None
        else:
            entry.update(item=None, u=None)
        rows.append(entry)
    return rows


def validate_tables(
    views: dict[tuple[int, str], dict[str, Any]],
    tables: Sequence[dict[str, Any]],
    question_index: dict[str, int],
) -> dict[str, Any]:
    """Every committed table must be reproduced by the joined labels: the same 256 values (the
    hex encoding of ``memcredit_analyze.analyze``) and the same count of distinct replies.
    Raises LabelFreeError on any difference."""

    failures = []
    reproduced = distinct_ok = 0
    for t in tables:
        tag = f"{t['question_id']}:{t['arm']}"
        key = (question_index[t["question_id"]], t["arm"])
        view = views.get(key)
        if view is None or not view["complete"]:
            failures.append(f"{tag}: the joined table is incomplete")
            continue
        if cc.encode_values(view["values"]) != t["values_hex"]:
            failures.append(f"{tag}: the joined labels do not reproduce values_hex")
            continue
        reproduced += 1
        distinct = len({r for r in view["replies"].values() if r})
        if "distinct_replies" in t and int(t["distinct_replies"]) != distinct:
            failures.append(f"{tag}: distinct replies {distinct} != {t['distinct_replies']}")
            continue
        distinct_ok += 1
    if len(views) != len(tables):
        failures.append(f"{len(views)} joined pools against {len(tables)} committed tables")
    report = {
        "tables": len(tables),
        "values_hex_reproduced": reproduced,
        "distinct_replies_reproduced": distinct_ok,
        "failures": failures,
        "passed": not failures,
    }
    if failures:
        raise LabelFreeError(f"join validation failed ({len(failures)}): {failures[:10]}")
    return report


# --------------------------------------------------------------------------- features


def logprob_summary(tokens: Sequence[int], bits: bytes) -> tuple[int, float, float]:
    """(tokens, summed log-prob, mean log-prob) over every recorded generated token."""

    import numpy as np

    values = np.frombuffer(bits, dtype="<f4")
    n = len(tokens)
    if n == 0 or len(values) != n:
        raise LabelFreeError("a reply without tokens or with mismatched log-probs")
    if not np.all(np.isfinite(values)):
        raise LabelFreeError("a reply with a missing (NaN) log-prob")
    total = math.fsum(float(v) for v in values)
    return n, total, total / n


def pool_features(
    masks: dict[int, dict[str, Any]], question: dict[str, Any], arm: str, eot_id: int
) -> dict[str, Any]:
    """Per mask of one pool: u, token count, summed and mean log-prob, finish, whether the
    end-of-turn token was generated, abstention and its pattern, the reply class (index of the
    normalized reply in order of first appearance by ascending mask) and the normalized reply's
    SHA-256. No text."""

    pool = question["pools"][arm]
    if len(pool) != K or sorted(masks) != list(range(1 << K)):
        raise LabelFreeError(f"{question['question_id']}:{arm}: not a complete 2^{K} table")
    classes: dict[str, int] = {}
    out: dict[str, Any] = {
        "question_id": question["question_id"],
        "question_type": question["question_type"],
        "arm": arm,
        "bm25_rank": [int(m["bm25_rank"]) for m in pool],
        "gold_mask": sum(1 << i for i, m in enumerate(pool) if m["is_gold"]),
    }
    fields: dict[str, list[Any]] = defaultdict(list)
    for mask in range(1 << K):
        r = masks[mask]
        if r["reply"] is None or r["u"] is None:
            raise LabelFreeError(f"{question['question_id']}:{arm}: mask {mask} has no label")
        normalized = mc.normalize_answer(r["reply"].strip())
        cls = classes.setdefault(normalized, len(classes))
        n, total, mean = logprob_summary(r["tokens"], r["bits"])
        abstains, pattern = abstention(r["reply"])
        fields["u"].append(int(r["u"]))
        fields["n_tokens"].append(n)
        fields["sum_lp"].append(total)
        fields["mean_lp"].append(mean)
        fields["finish"].append(r["finish"])
        fields["eot"].append(int(r["tokens"][-1]) == eot_id)
        fields["abstain"].append(abstains)
        fields["pattern"].append(pattern)
        fields["cls"].append(cls)
        fields["digest"].append(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    out.update(fields)
    out["classes"] = len(classes)
    return out


def build_features(
    rows: Sequence[dict[str, Any]],
    artifact: dict[str, Any],
    eot_id: int,
    question_limit: int | None = None,
) -> list[dict[str, Any]]:
    by_pool: dict[tuple[int, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        if r["kind"] != "table":
            continue
        if question_limit is not None and r["question_index"] >= question_limit:
            continue
        by_pool[(int(r["question_index"]), r["arm"])][int(r["mask"])] = r
    out = []
    for (q_index, arm), masks in sorted(by_pool.items()):
        out.append(pool_features(masks, artifact["questions"][q_index], arm, eot_id))
    return out


def end_of_turn_id(run_dir: Path, worker: str) -> int:
    path = run_dir / "sessions" / worker / "worker-progress.jsonl"
    check_path(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("event") == "engine-start":
            return int(record["end_of_turn_id"])
    raise LabelFreeError(f"{path}: no engine-start event")


def reply_stats(features: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Text-free counts over the 4-subset and full-pool replies, per arm."""

    out: dict[str, Any] = {}
    sets4 = ms.all_budget_sets(K, BUDGET)
    for arm in ARMS:
        pools = [p for p in features if p["arm"] == arm]
        if not pools:
            continue
        n = len(pools) * len(sets4)
        flagged = [(p, m) for p in pools for m in sets4 if p["abstain"][m]]
        out[arm] = {
            "pools": len(pools),
            "four_subset_replies": n,
            "abstain": len(flagged),
            "abstain_judged_correct": sum(p["u"][m] for p, m in flagged),
            "nonabstain_judged_correct": sum(
                p["u"][m] for p in pools for m in sets4 if not p["abstain"][m]
            ),
            "abstain_by_pattern": dict(
                sorted(Counter(p["pattern"][m] for p, m in flagged).items())
            ),
            "length_capped": sum(p["finish"][m] == "length" for p in pools for m in sets4),
            "end_of_turn_generated": sum(p["eot"][m] for p in pools for m in sets4),
            "mean_tokens": sum(p["n_tokens"][m] for p in pools for m in sets4) / n,
            "mean_classes_among_4_subsets": sum(len({p["cls"][m] for m in sets4}) for p in pools)
            / len(pools),
            "full_pool_abstain": sum(p["abstain"][FULL] for p in pools),
            "full_pool_abstain_judged_correct": sum(
                p["u"][FULL] for p in pools if p["abstain"][FULL]
            ),
            "agree_with_full": sum(p["cls"][m] == p["cls"][FULL] for p in pools for m in sets4),
        }
    return out


# --------------------------------------------------------------------------- search


FOUR_SETS: tuple[int, ...] = tuple(ms.all_budget_sets(K, BUDGET))


def rank_key(mask: int, ranks: Sequence[int]) -> tuple[Any, ...]:
    """Tie-break key (larger is preferred): lower BM25 rank sum, then lexicographically smaller
    sorted ranks. BM25 ranks are distinct within a pool, so no two sets tie on this key."""

    return _rank_key(mask, tuple(ranks))


@functools.lru_cache(maxsize=1 << 16)
def _rank_key(mask: int, ranks: tuple[int, ...]) -> tuple[Any, ...]:
    chosen = sorted(ranks[i] for i in range(len(ranks)) if mask >> i & 1)
    return (-sum(chosen), tuple(-r for r in chosen))


ScoreFn = Callable[[dict[str, Any], Sequence[int]], Callable[[int], tuple[Any, ...]]]


def _static(fields: tuple[str, ...], nonabstain_first: bool = False) -> ScoreFn:
    def make(pool: dict[str, Any], queried: Sequence[int]) -> Callable[[int], tuple[Any, ...]]:
        def score(m: int) -> tuple[Any, ...]:
            head = (0 if pool["abstain"][m] else 1,) if nonabstain_first else ()
            return head + tuple(pool[f][m] for f in fields)

        return score

    return make


def _nonabstain(pool: dict[str, Any], queried: Sequence[int]) -> Callable[[int], tuple[Any, ...]]:
    return lambda m: (0 if pool["abstain"][m] else 1,)


def _agree_full(pool: dict[str, Any], queried: Sequence[int]) -> Callable[[int], tuple[Any, ...]]:
    full = pool["cls"][FULL]
    return lambda m: (1 if pool["cls"][m] == full else 0,)


def _vote(nonabstain_first: bool) -> ScoreFn:
    def make(pool: dict[str, Any], queried: Sequence[int]) -> Callable[[int], tuple[Any, ...]]:
        counts = Counter(pool["cls"][q] for q in queried)

        def score(m: int) -> tuple[Any, ...]:
            head = (0 if pool["abstain"][m] else 1,) if nonabstain_first else ()
            return head + (counts[pool["cls"][m]], pool["mean_lp"][m])

        return score

    return make


@dataclass(frozen=True)
class Utility:
    name: str
    describe: str
    extra_calls: int
    make: ScoreFn


#: The label-free utilities, declared before any result. Order is the report order and the
#: order in which equal in-sample means are resolved.
UTILITIES: tuple[Utility, ...] = (
    Utility("conf_mean", "mean sampled-token log-prob of reply(S)", 0, _static(("mean_lp",))),
    Utility("conf_sum", "summed sampled-token log-prob of reply(S)", 0, _static(("sum_lp",))),
    Utility("nonabstain", "1 unless reply(S) matches the abstention list", 0, _nonabstain),
    Utility(
        "agree_full",
        "1 when normalize_answer(reply(S)) == normalize_answer(reply(all 8)); +1 call",
        1,
        _agree_full,
    ),
    Utility(
        "vote",
        "count of queried subsets with the same normalized reply, then mean log-prob",
        0,
        _vote(False),
    ),
    Utility(
        "nonabstain_conf_mean",
        "non-abstention, then mean log-prob",
        0,
        _static(("mean_lp",), nonabstain_first=True),
    ),
    Utility(
        "nonabstain_conf_sum",
        "non-abstention, then summed log-prob",
        0,
        _static(("sum_lp",), nonabstain_first=True),
    ),
    Utility(
        "nonabstain_vote",
        "non-abstention, then the vote count, then mean log-prob",
        0,
        _vote(True),
    ),
)
UTILITY_NAMES = tuple(u.name for u in UTILITIES)


def select(pool: dict[str, Any], queried: Sequence[int], utility: Utility) -> int:
    """The queried 4-subset with the best label-free score; ties by ``rank_key``."""

    if not queried:
        raise LabelFreeError("search needs at least one queried subset")
    score = utility.make(pool, queried)
    ranks = pool["bm25_rank"]
    return max(queried, key=lambda m: (score(m), rank_key(m, ranks)))


def draw_order(question_id: str, arm: str, seed: int) -> list[int]:
    """A uniformly random order of the 70 4-subsets; the first m are the m queried subsets (m
    distinct draws without replacement, nested across m, shared by every utility)."""

    rng = random.Random(f"{seed}:{question_id}:{arm}:am1d-search")
    return rng.sample(list(FOUR_SETS), len(FOUR_SETS))


def bm25_top_mask(ranks: Sequence[int], budget: int = BUDGET) -> int:
    order = sorted(range(len(ranks)), key=lambda i: ranks[i])
    return sum(1 << i for i in order[:budget])


def row_names() -> list[str]:
    names = ["bm25_top4", "all_8", "random_4"]
    names += [f"oracle_search@{m}" for m in SEARCH_CALLS]
    names += [f"{u.name}@{m}" for u in UTILITIES for m in SEARCH_CALLS]
    return names


def row_calls(name: str) -> int:
    if name == "bm25_top4" or name == "random_4":
        return 0
    if name == "all_8":
        return 1
    base, m = name.split("@")
    extra = 0 if base == "oracle_search" else {u.name: u.extra_calls for u in UTILITIES}[base]
    return int(m) + extra


def table_results(
    pool: dict[str, Any], values: Sequence[float], seed_list: Sequence[int]
) -> dict[str, Any]:
    """Every rule's accuracy and regret on one table: per seed for the searches (mean over
    seeds), exact expectations for the random set and the oracle search."""

    if [float(v) for v in pool["u"]] != [float(v) for v in values]:
        raise LabelFreeError(f"{pool['question_id']}:{pool['arm']}: features differ from table")
    opt = mc.best_keep_sets(values, BUDGET)[0]
    ranks = pool["bm25_rank"]
    bm25 = bm25_top_mask(ranks)
    rank_credit = [-float(r) for r in ranks]
    check = mc.keep_set_regret_range(values, rank_credit, BUDGET)
    if check["sets"] != 1 or check["mean"] != opt - float(values[bm25]):
        raise LabelFreeError("BM25 top 4 differs from AM1b's retrieval_rank keep set")
    u_random = sum(float(values[s]) for s in FOUR_SETS) / len(FOUR_SETS)
    direct = cc.direct_search_curve(values, BUDGET)
    rows: dict[str, dict[str, Any]] = {
        "bm25_top4": {"u": float(values[bm25]), "mask": bm25},
        "all_8": {"u": float(values[FULL]), "mask": FULL},
        "random_4": {"u": u_random},
    }
    for m in SEARCH_CALLS:
        rows[f"oracle_search@{m}"] = {"u": opt - direct[m - 1]}
    per_seed: dict[str, list[int]] = defaultdict(list)
    for seed in seed_list:
        order = draw_order(pool["question_id"], pool["arm"], seed)
        for m in SEARCH_CALLS:
            queried = order[:m]
            for utility in UTILITIES:
                mask = select(pool, queried, utility)
                per_seed[f"{utility.name}@{m}"].append(int(values[mask]))
                if m == len(FOUR_SETS) and seed == seed_list[0]:
                    rows[f"{utility.name}@{m}"] = {"mask": mask}
    for name, us in per_seed.items():
        cell = rows.setdefault(name, {})
        cell["u"] = sum(us) / len(us)
        cell["u_by_seed"] = "".join(str(x) for x in us)
    for cell in rows.values():
        cell["regret"] = opt - cell["u"]
    for utility in UTILITIES:  # m = 70 reads every 4-subset: one choice, scored by the harness
        cell = rows[f"{utility.name}@{len(FOUR_SETS)}"]
        if len(set(cell["u_by_seed"])) != 1:
            raise LabelFreeError("the exhaustive search differs across seeds")
        if cc.set_regret(values, cell["mask"], BUDGET) != cell["regret"]:
            raise LabelFreeError("regret differs from the harness's keep-set regret")
    return {
        "question_id": pool["question_id"],
        "question_type": pool["question_type"],
        "arm": pool["arm"],
        "nonconstant": len(set(values)) > 1,
        "opt4": opt,
        "rows": rows,
    }


def within_table_auroc(pool: dict[str, Any]) -> dict[str, float] | None:
    """AUROC of each label-free score (all 70 4-subsets read) for u among the 4-subsets of one
    table; None when the 4-subsets do not have both labels."""

    labels = [pool["u"][m] for m in FOUR_SETS]
    if len(set(labels)) < 2:
        return None
    out = {}
    for utility in UTILITIES:
        score = utility.make(pool, FOUR_SETS)
        value = ms.auroc([score(m) for m in FOUR_SETS], labels)
        if value is not None:
            out[utility.name] = value
    return out


# --------------------------------------------------------------------------- aggregation


def _boot(clusters: dict[str, list[float]], resamples: int, seed: int) -> dict[str, Any]:
    r = ms.cluster_bootstrap(clusters, resamples, seed, 0.05)
    return {"mean": r["mean"], "ci95": r["ci"], "units": r["units"]}


def aggregate(
    per_table: Sequence[dict[str, Any]], resamples: int, seed: int, n_seeds: int
) -> dict[str, Any]:
    """Per arm and table set (non-constant, all): every rule's mean regret (non-constant only),
    mean accuracy, and paired accuracy differences against BM25 top 4 and all 8, with
    question-cluster bootstrap 95% intervals; Monte Carlo standard errors over seeds."""

    out: dict[str, Any] = {}
    for arm in ARMS:
        out[arm] = {}
        for subset in ("nonconstant", "all"):
            rows = [
                p for p in per_table if p["arm"] == arm and (subset == "all" or p["nonconstant"])
            ]
            cells = {}
            for name in row_names():
                u: dict[str, list[float]] = defaultdict(list)
                reg: dict[str, list[float]] = defaultdict(list)
                d_bm25: dict[str, list[float]] = defaultdict(list)
                d_full: dict[str, list[float]] = defaultdict(list)
                for p in rows:
                    cell = p["rows"][name]
                    q = p["question_id"]
                    u[q].append(cell["u"])
                    reg[q].append(cell["regret"])
                    d_bm25[q].append(cell["u"] - p["rows"]["bm25_top4"]["u"])
                    d_full[q].append(cell["u"] - p["rows"]["all_8"]["u"])
                entry = {
                    "calls": row_calls(name),
                    "tables": len(rows),
                    "accuracy": _boot(u, resamples, seed),
                    "minus_bm25_top4": _boot(d_bm25, resamples, seed),
                    "minus_all_8": _boot(d_full, resamples, seed),
                }
                if subset == "nonconstant":
                    entry["regret"] = _boot(reg, resamples, seed)
                by_seed = [p["rows"][name].get("u_by_seed") for p in rows]
                if rows and all(by_seed):
                    seed_means = [
                        sum(int(s[j]) for s in by_seed) / len(rows) for j in range(n_seeds)
                    ]
                    centre = sum(seed_means) / n_seeds
                    var = sum((x - centre) ** 2 for x in seed_means) / (n_seeds - 1)
                    entry["seed_mc_se"] = math.sqrt(var / n_seeds)
                cells[name] = entry
            out[arm][subset] = cells
    return out


def crossfit_selection(
    per_table: Sequence[dict[str, Any]],
    arm: str,
    candidates: Sequence[str],
    splits: int,
    seed: int,
) -> dict[str, Any]:
    """Selection-adjusted accuracy gain over BM25 top 4 on the arm's non-constant tables: split
    the questions in half at random, pick the candidate with the highest mean gain on one half
    (ties to the earlier candidate), score it on the other half; both directions, ``splits``
    times. The mean of the held-out gains is not optimistic about the choice itself."""

    rows = sorted(
        (p for p in per_table if p["arm"] == arm and p["nonconstant"]),
        key=lambda p: p["question_id"],
    )
    gain = {
        c: {p["question_id"]: p["rows"][c]["u"] - p["rows"]["bm25_top4"]["u"] for p in rows}
        for c in candidates
    }
    qids = [p["question_id"] for p in rows]
    rng = random.Random(f"{seed}:{arm}:am1d-crossfit")
    held_out = []
    chosen: Counter[str] = Counter()
    for _ in range(splits):
        perm = list(qids)
        rng.shuffle(perm)
        half = len(perm) // 2
        for train, test in ((perm[:half], perm[half:]), (perm[half:], perm[:half])):
            best = max(
                candidates,
                key=lambda c: (
                    sum(gain[c][q] for q in train) / len(train),
                    -list(candidates).index(c),
                ),
            )
            chosen[best] += 1
            held_out.append(sum(gain[best][q] for q in test) / len(test))
    held_out.sort()
    n = len(held_out)
    return {
        "arm": arm,
        "tables": len(rows),
        "candidates": list(candidates),
        "splits": splits,
        "held_out_gain_mean": sum(held_out) / n,
        "held_out_gain_share_positive": sum(x > 0 for x in held_out) / n,
        "held_out_gain_p05_p95": [held_out[int(0.05 * (n - 1))], held_out[int(0.95 * (n - 1))]],
        "chosen": dict(sorted(chosen.items())),
    }


def answers(agg: dict[str, Any], crossfit: dict[str, Any]) -> dict[str, Any]:
    """The headline questions on the retrieved arm's non-constant tables at B = 4."""

    cells = agg[HEADLINE_ARM]["nonconstant"]
    label_free = [f"{u}@{m}" for u in UTILITY_NAMES for m in SEARCH_CALLS]

    def brief(name: str) -> dict[str, Any]:
        c = cells[name]
        return {
            "rule": name,
            "calls": c["calls"],
            "regret": c["regret"]["mean"],
            "accuracy": c["accuracy"]["mean"],
            "minus_bm25_top4": {k: c["minus_bm25_top4"][k] for k in ("mean", "ci95")},
            "minus_all_8": {k: c["minus_all_8"][k] for k in ("mean", "ci95")},
        }

    best = max(label_free, key=lambda n: (cells[n]["accuracy"]["mean"], -label_free.index(n)))
    per_budget = {}
    for m in SEARCH_CALLS:
        names = [f"{u}@{m}" for u in UTILITY_NAMES]
        top = max(names, key=lambda n: (cells[n]["accuracy"]["mean"], -names.index(n)))
        per_budget[str(m)] = brief(top)
    return {
        "cell": {"arm": HEADLINE_ARM, "budget": BUDGET, "tables": cells["bm25_top4"]["tables"]},
        "bm25_top4": brief("bm25_top4"),
        "all_8": brief("all_8"),
        "random_4": brief("random_4"),
        "best_label_free_in_sample": brief(best),
        "best_label_free_beats_bm25_top4_point": cells[best]["minus_bm25_top4"]["mean"] > 0,
        "best_label_free_beats_bm25_top4_ci95": cells[best]["minus_bm25_top4"]["ci95"][0] > 0,
        "best_label_free_per_budget": per_budget,
        "label_free_rules_with_ci95_above_bm25_top4": [
            n for n in label_free if cells[n]["minus_bm25_top4"]["ci95"][0] > 0
        ],
        "label_free_rules_with_ci95_below_bm25_top4": [
            n for n in label_free if cells[n]["minus_bm25_top4"]["ci95"][1] < 0
        ],
        "label_free_rules_with_ci95_above_all_8": [
            n for n in label_free if cells[n]["minus_all_8"]["ci95"][0] > 0
        ],
        "label_free_rules_with_ci95_below_all_8": [
            n for n in label_free if cells[n]["minus_all_8"]["ci95"][1] < 0
        ],
        "crossfit": crossfit,
    }


def eager_sensitivity(
    compiled: Sequence[dict[str, Any]], eager: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    """On the pools the eager replay covers: every rule's mean accuracy and gain over BM25 top 4
    under the compiled pass (tables of job 1411) and under the eager pass (its own judged tables
    and replies). Point estimates only (16 questions)."""

    keyed = {(p["question_id"], p["arm"]): p for p in compiled}
    out: dict[str, Any] = {}
    for arm in ARMS:
        e_rows = [p for p in eager if p["arm"] == arm]
        c_rows = [keyed[(p["question_id"], p["arm"])] for p in e_rows]
        if not e_rows:
            continue
        arm_out: dict[str, Any] = {
            "questions": len(e_rows),
            "nonconstant_compiled": sum(p["nonconstant"] for p in c_rows),
            "nonconstant_eager": sum(p["nonconstant"] for p in e_rows),
            "rows": {},
        }
        for name in row_names():
            entry = {}
            for label, rows in (("compiled", c_rows), ("eager", e_rows)):
                n = len(rows)
                entry[label] = {
                    "accuracy": sum(p["rows"][name]["u"] for p in rows) / n,
                    "minus_bm25_top4": sum(
                        p["rows"][name]["u"] - p["rows"]["bm25_top4"]["u"] for p in rows
                    )
                    / n,
                    "minus_all_8": sum(p["rows"][name]["u"] - p["rows"]["all_8"]["u"] for p in rows)
                    / n,
                }
            arm_out["rows"][name] = entry
        out[arm] = arm_out
    return out


# --------------------------------------------------------------------------- analyze


def analyze(
    features: dict[str, Any],
    tables: Sequence[dict[str, Any]],
    eager: dict[str, Any] | None,
    n_seeds: int,
    seed_base: int,
    resamples: int,
    bootstrap_seed: int,
    crossfit_splits: int = CROSSFIT_SPLITS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seed_list = [seed_base + j for j in range(n_seeds)]
    pools = {(p["question_id"], p["arm"]): p for p in features["pools"]}
    if len(pools) != len(tables):
        raise LabelFreeError(f"{len(pools)} feature pools against {len(tables)} tables")
    per_table = []
    for t in sorted(tables, key=lambda t: (t["arm"], t["question_id"])):
        values = cc.decode_values(t["values_hex"])
        pool = pools[(t["question_id"], t["arm"])]
        result = table_results(pool, values, seed_list)
        if result["nonconstant"] != (not t["summary"]["constant"]):
            raise LabelFreeError("the non-constant set differs from AM1's summary")
        per_table.append(result)
    agg = aggregate(per_table, resamples, bootstrap_seed, n_seeds)
    crossfit = {}
    for arm in ARMS:
        crossfit[arm] = {
            str(m): crossfit_selection(
                per_table,
                arm,
                [f"{u}@{m}" for u in UTILITY_NAMES],
                crossfit_splits,
                CROSSFIT_SEED,
            )
            for m in SEARCH_CALLS
        }
        crossfit[arm]["all"] = crossfit_selection(
            per_table,
            arm,
            [f"{u}@{m}" for u in UTILITY_NAMES for m in SEARCH_CALLS],
            crossfit_splits,
            CROSSFIT_SEED,
        )
    auroc: dict[str, Any] = {}
    for arm in ARMS:
        per = [within_table_auroc(p) for p in features["pools"] if p["arm"] == arm]
        per = [x for x in per if x is not None]
        auroc[arm] = {
            "tables_with_both_labels_among_4_subsets": len(per),
            "mean_auroc": {
                name: sum(x[name] for x in per if name in x) / max(1, sum(name in x for x in per))
                for name in UTILITY_NAMES
            },
        }
    eager_out = None
    if eager is not None:
        e_tables = []
        for pool in eager["pools"]:
            values = [float(v) for v in pool["u"]]
            e_tables.append(table_results(pool, values, seed_list))
        e_tables.sort(key=lambda p: (p["arm"], p["question_id"]))
        eager_out = {
            "pass": eager["pass"],
            "comparison_with_compiled": eager["comparison"],
            "reply_stats": reply_stats(eager["pools"]),
            "rules": eager_sensitivity(per_table, e_tables),
        }
    results = {
        "experiment": EXPERIMENT,
        "status": "EXPLORATORY",
        "data": "development split only (63 questions x 2 arms); no confirmatory data opened",
        "decision": "D113 (next step 1)",
        "inputs": {
            "tables": {
                "path": str(cc.DEV_TABLES),
                "sha256": cc.DEV_TABLES_SHA256,
                "tables": len(tables),
            },
            "pass": features["pass"],
            "features_sha256": features.get("_sha256"),
            "confirmatory_data_opened": False,
        },
        "config": {
            "k": K,
            "budget": BUDGET,
            "search_calls": list(SEARCH_CALLS),
            "arms": list(ARMS),
            "headline": {"arm": HEADLINE_ARM, "budget": BUDGET},
            "seeds": {
                "base": seed_base,
                "count": n_seeds,
                "rng": "random.Random(f'{seed}:{question_id}:{arm}:am1d-search').sample(the 70 "
                "4-subsets, 70); the first m are read; shared by every utility",
            },
            "tie_break": "lower BM25 rank sum, then lexicographically smaller sorted BM25 ranks",
            "regret": "max u over 4-subsets minus u(chosen) (AM1b's convention; for a 4-subset "
            "equal to harness.memcredit.keep_set_regret_range on its indicator)",
            "all_8_regret": "max u over 4-subsets minus u(all 8); negative when the full pool is "
            "right and no 4-subset is",
            "random_4": "expectation over the 70 4-subsets (exact)",
            "oracle_search": "AM1b's direct search on the judged utility (needs labels; "
            "exact expectation), a reference only",
            "nonconstant_rule": "AM1's summary.constant is False (AM1b's set)",
            "bootstrap": {
                "resamples": resamples,
                "seed": bootstrap_seed,
                "code": "harness.memcredit_study.cluster_bootstrap",
                "level": 0.95,
                "unit": "question (one table per question per arm)",
            },
            "crossfit": {"splits": crossfit_splits, "seed": CROSSFIT_SEED},
            "abstention_patterns": [list(p) for p in ABSTENTION_PATTERNS],
            "abstention_patterns_sha256": patterns_sha256(),
            "abstention_text": "harness.memcredit.normalize_answer(reply); empty counts",
            "confidence": "math.fsum of the float32 sampled-token log-probs of every recorded "
            "generated token (end-of-turn included when generated); mean = sum / tokens",
            "normalization_for_agreement_and_vote": "harness.memcredit.normalize_answer of the "
            "stripped reply",
        },
        "utilities": {
            u.name: {"describe": u.describe, "extra_calls": u.extra_calls} for u in UTILITIES
        },
        "validation": features["validation"],
        "reply_stats": reply_stats(features["pools"]),
        "within_table_auroc": auroc,
        "aggregate": agg,
        "answers": answers(agg, crossfit[HEADLINE_ARM]),
        "crossfit": crossfit,
        "eager_sensitivity": eager_out,
    }
    return results, per_table


# --------------------------------------------------------------------------- markdown


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _d(x: float) -> str:
    return f"{x:+.3f}"


def _ci(ci: Sequence[float | None], signed: bool = False) -> str:
    if signed:
        return f"[{_d(ci[0])}, {_d(ci[1])}]"  # type: ignore[arg-type]
    return f"[{_f(ci[0])}, {_f(ci[1])}]"


def render_markdown(results: dict[str, Any]) -> str:
    agg = results["aggregate"]
    lines = [
        "# AM1d label-free search: generated tables",
        "",
        "Generated by `scripts/memcredit_label_free.py analyze`. EXPLORATORY, development data "
        "only. Keep 4 of 8 memories. Accuracy is the judged utility u of the chosen set; regret "
        "is the best 4-subset's u minus u(chosen), on non-constant tables only. Differences are "
        "paired by question (positive: the rule is more accurate). Intervals: 95%, "
        f"question-cluster bootstrap, {results['config']['bootstrap']['resamples']:,} "
        f"resamples, seed {results['config']['bootstrap']['seed']}. Searches: mean over "
        f"{results['config']['seeds']['count']} seeds of m random 4-subsets; ties to the lower "
        "BM25 rank sum. se: Monte Carlo standard error over seeds. `oracle_search` reads the "
        "judged utility (needs labels) and is a reference, not deployable.",
        "",
    ]
    for arm in ARMS:
        for subset in ("nonconstant", "all"):
            cells = agg[arm][subset]
            n = cells["bm25_top4"]["tables"]
            title = "non-constant tables" if subset == "nonconstant" else "all questions"
            primary = " (primary cell)" if arm == HEADLINE_ARM and subset == "nonconstant" else ""
            lines += [f"## {arm} arm, {title} ({n}){primary}", ""]
            if subset == "nonconstant":
                lines += [
                    "| Rule | Calls | Regret [95% CI] | Accuracy [95% CI] | minus BM25 top 4 "
                    "[95% CI] | minus all 8 [95% CI] |",
                    "|---|---:|---|---|---|---|",
                ]
            else:
                lines += [
                    "| Rule | Calls | Accuracy [95% CI] | minus BM25 top 4 [95% CI] | minus all 8 "
                    "[95% CI] |",
                    "|---|---:|---|---|---|",
                ]
            for name in row_names():
                c = cells[name]
                se = c.get("seed_mc_se")
                acc = f"{_f(c['accuracy']['mean'])} {_ci(c['accuracy']['ci95'])}"
                if se is not None and se > 0:
                    acc += f" (se {se:.3f})"
                db = c["minus_bm25_top4"]
                df = c["minus_all_8"]
                parts = [name, str(c["calls"])]
                if subset == "nonconstant":
                    r = c["regret"]
                    parts.append(f"{_d(r['mean'])} {_ci(r['ci95'], True)}")
                parts += [
                    acc,
                    f"{_d(db['mean'])} {_ci(db['ci95'], True)}",
                    f"{_d(df['mean'])} {_ci(df['ci95'], True)}",
                ]
                lines.append("| " + " | ".join(parts) + " |")
            lines.append("")
    lines += [
        "## Selection-adjusted gain over BM25 top 4 (non-constant tables)",
        "",
        "Pick the utility with the highest mean gain on a random half of the questions, score it "
        f"on the other half ({results['config']['crossfit']['splits']} splits, both directions).",
        "",
        "| Arm | Candidates | Held-out gain, mean | Share of halves > 0 | 5th-95th percentile | "
        "Most chosen |",
        "|---|---|---:|---:|---|---|",
    ]
    for arm in ARMS:
        for key, cf in results["crossfit"][arm].items():
            label = "every utility and m" if key == "all" else f"every utility at m = {key}"
            top = max(cf["chosen"].items(), key=lambda kv: (kv[1], kv[0]))
            lines.append(
                f"| {arm} | {label} | {_d(cf['held_out_gain_mean'])} | "
                f"{cf['held_out_gain_share_positive']:.2f} | "
                f"{_ci(cf['held_out_gain_p05_p95'], True)} | {top[0]} ({top[1]}) |"
            )
    lines += [
        "",
        "## Within-table AUROC of each score for u (all 70 4-subsets read)",
        "",
        "| Arm | Tables | " + " | ".join(UTILITY_NAMES) + " |",
        "|---|---:|" + "---:|" * len(UTILITY_NAMES),
    ]
    for arm in ARMS:
        a = results["within_table_auroc"][arm]
        lines.append(
            f"| {arm} | {a['tables_with_both_labels_among_4_subsets']} | "
            + " | ".join(f"{a['mean_auroc'][n]:.3f}" for n in UTILITY_NAMES)
            + " |"
        )
    lines += ["", "## Replies (4-subsets of every pool; counts, no text)", ""]
    keys = list(next(iter(results["reply_stats"].values())))
    lines += ["| Statistic | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    for key in keys:
        vals = []
        for arm in ARMS:
            v = results["reply_stats"][arm][key]
            vals.append(f"{v:.3f}" if isinstance(v, float) else json.dumps(v, sort_keys=True))
        lines.append(f"| {key} | " + " | ".join(vals) + " |")
    eager = results.get("eager_sensitivity")
    if eager:
        lines += [
            "",
            "## Eager replay sensitivity (job 1441, first 16 questions; point estimates)",
            "",
            "Accuracy and gain over BM25 top 4 on the pools the eager replay covers, under the "
            "compiled pass (job 1411's replies and tables) and under the eager pass (its own "
            "replies and judged tables).",
            "",
        ]
        for arm in ARMS:
            e = eager["rules"].get(arm)
            if not e:
                continue
            lines += [
                f"### {arm} arm: {e['questions']} questions (non-constant: compiled "
                f"{e['nonconstant_compiled']}, eager {e['nonconstant_eager']})",
                "",
                "| Rule | Accuracy, compiled | Accuracy, eager | minus BM25, compiled | "
                "minus BM25, eager |",
                "|---|---:|---:|---:|---:|",
            ]
            for name in row_names():
                c, g = e["rows"][name]["compiled"], e["rows"][name]["eager"]
                lines.append(
                    f"| {name} | {c['accuracy']:.3f} | {g['accuracy']:.3f} | "
                    f"{_d(c['minus_bm25_top4'])} | {_d(g['minus_bm25_top4'])} |"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- commands


def load_dev_tables(path: Path) -> list[dict[str, Any]]:
    check_path(path)
    return cc.load_tables(path, cc.DEV_TABLES_SHA256)


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    import memcredit_analyze as ma
    import memcredit_study as driver

    run_dir = Path(args.run_dir)
    for p in (args.run_dir, args.evidence, args.tables, args.private_dir, args.eager_run_dir):
        if p is not None:
            check_path(p)
    config = ms.load_config()
    if config["experiment_id"] != PILOT_CONFIG_ID or config["claim_level"] != "exploratory":
        raise LabelFreeError("AM1d runs under the development pilot's config only")
    if sha256_file(Path(args.evidence)) != ARTIFACT_SHA256:
        raise LabelFreeError("the study artifact is not the development pilot's")
    digests = check_digests(run_dir, MAIN_PASS["sha256"])
    artifact = ma.load_artifact(Path(args.evidence), config, ARTIFACT_SHA256)
    if artifact.get("split") != "development":
        raise LabelFreeError("AM1d reads the development split only")
    tables = load_dev_tables(Path(args.tables))
    question_index = {q["question_id"]: i for i, q in enumerate(artifact["questions"])}
    # The join that built the committed tables, unchanged.
    rows_ma, items, primary, _ = ma.join_rows(run_dir, config, artifact)
    views_ma = ma.pool_views(rows_ma, artifact)
    validation = validate_tables(views_ma, tables, question_index)
    # The same join, keeping tokens and log-probs; it must agree with the harness's request by
    # request.
    requests = ms.request_table(artifact, config["pools"]["arms"])
    reader = ma.load_pass(run_dir, MAIN_PASS["reader"])
    if reader is None:
        raise LabelFreeError("the reader pass is missing")
    if reader["meta"].get("missing_logprobs"):
        raise LabelFreeError("the reader pass has missing log-probs")
    rows = join_requests(requests, reader["rows"], items, primary)
    if len(rows) != len(rows_ma):
        raise LabelFreeError("the two joins differ in length")
    mismatched = sum(
        1
        for a, b in zip(rows, rows_ma, strict=True)
        if a["index"] != b["index"] or a["reply"] != b["reply"] or a["u"] != b["u"]
    )
    if mismatched:
        raise LabelFreeError(f"{mismatched} requests differ between the two joins")
    table_requests = [r for r in rows if r["kind"] == "table"]
    validation.update(
        requests=len(rows),
        table_requests=len(table_requests),
        table_requests_labelled=sum(r["u"] is not None for r in table_requests),
        joins_agree_requests=len(rows) - mismatched,
        judge_items=len(items),
        reader_finish=dict(sorted(Counter(r["finish"] for r in table_requests).items())),
    )
    eot = end_of_turn_id(run_dir, MAIN_PASS["reader"])
    features = build_features(rows, artifact, eot)
    out_private = Path(args.private_dir)
    out_private.mkdir(parents=True, exist_ok=True)
    main_payload = {
        "experiment": EXPERIMENT,
        "pass": {
            "name": MAIN_PASS["name"],
            "run": "~/cotcodec-runs/stage0/am1-study/runs/main/1411/am1",
            "sha256": digests,
            "study_artifact_sha256": ARTIFACT_SHA256,
            "end_of_turn_id": eot,
        },
        "validation": validation,
        "pools": features,
    }
    write_gz_json(out_private / "features-1411.json.gz", main_payload)
    summary = {"main": {"pools": len(features), "validation": validation}}
    if args.eager_run_dir:
        e_dir = Path(args.eager_run_dir)
        e_digests = check_digests(e_dir, EAGER_PASS["sha256"])
        e_reader = driver.load_pass(e_dir / "sessions" / EAGER_PASS["reader"], "all")
        if e_reader["meta"].get("missing_logprobs"):
            raise LabelFreeError("the eager reader pass has missing log-probs")
        e_items_path = e_dir / "judge-items.json"
        check_path(e_items_path)
        e_items = json.loads(e_items_path.read_text(encoding="utf-8"))
        e_primary = ma.labels_from_pass(ma.load_pass(e_dir, EAGER_PASS["judge"]))
        e_rows = join_requests(requests, e_reader["rows"], e_items, e_primary)
        limit = int(EAGER_PASS["questions"])
        e_views = ma.pool_views(e_rows, artifact)
        complete = sorted(key for key, v in e_views.items() if v["complete"])
        expected = sorted((q, a) for q in range(limit) for a in config["pools"]["arms"])
        if complete != expected:
            raise LabelFreeError("the eager pass does not cover exactly the first 16 questions")
        e_eot = end_of_turn_id(e_dir, EAGER_PASS["reader"])
        e_features = build_features(e_rows, artifact, e_eot, question_limit=limit)
        by_index = {r["index"]: r for r in rows}
        same_reply = same_u = cells = 0
        tables_differ = 0
        for key in expected:
            differ = False
            view_c, view_e = views_ma[key], e_views[key]
            for m in range(1 << K):
                cells += 1
                same_u += int(view_c["values"][m] == view_e["values"][m])
                differ |= view_c["values"][m] != view_e["values"][m]
            tables_differ += int(differ)
        for r in e_rows:
            if r["kind"] == "table" and r["question_index"] < limit:
                same_reply += int(r["reply"] == by_index[r["index"]]["reply"])
        comparison = {
            "pools": len(expected),
            "table_cells": cells,
            "table_cells_same_u": same_u,
            "tables_with_any_difference": tables_differ,
            "identical_replies": same_reply,
        }
        eager_payload = {
            "experiment": EXPERIMENT,
            "pass": {
                "name": EAGER_PASS["name"],
                "run": "~/cotcodec-runs/stage0/am1-study/runs/eager/1441/am1",
                "sha256": e_digests,
                "end_of_turn_id": e_eot,
            },
            "comparison": comparison,
            "pools": e_features,
        }
        write_gz_json(out_private / "features-1441.json.gz", eager_payload)
        summary["eager"] = {"pools": len(e_features), "comparison": comparison}
    return summary


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    for p in (args.features, args.eager_features, args.tables, args.output_dir):
        if p is not None:
            check_path(p)
    features = read_gz_json(Path(args.features))
    features["_sha256"] = sha256_file(Path(args.features))
    eager = read_gz_json(Path(args.eager_features)) if args.eager_features else None
    if eager is not None:
        eager["pass"]["features_sha256"] = sha256_file(Path(args.eager_features))
    tables = load_dev_tables(Path(args.tables))
    results, per_table = analyze(
        features,
        tables,
        eager,
        args.seeds,
        args.seed_base,
        args.resamples,
        args.bootstrap_seed,
    )
    import numpy as np

    results["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__}
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_bytes(canonical(results))
    write_gz_json(out_dir / "per-table.json.gz", per_table)
    (out_dir / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return results["answers"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("extract", help="host only: join, validate, write private features")
    ex.add_argument("--run-dir", required=True, help="job 1411's am1 directory")
    ex.add_argument("--evidence", required=True, help="the pilot's study artifact")
    ex.add_argument("--tables", default=str(cc.DEV_TABLES))
    ex.add_argument("--private-dir", required=True, help="host-only output directory")
    ex.add_argument("--eager-run-dir", default=None, help="job 1441's am1 directory")
    an = sub.add_parser("analyze", help="search, baselines, intervals, text-free outputs")
    an.add_argument("--features", required=True)
    an.add_argument("--eager-features", default=None)
    an.add_argument("--tables", default=str(cc.DEV_TABLES))
    an.add_argument("--output-dir", required=True)
    an.add_argument("--seeds", type=int, default=N_SEEDS)
    an.add_argument("--seed-base", type=int, default=SEED_BASE)
    an.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    an.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    args = parser.parse_args(argv)
    if patterns_sha256() != ABSTENTION_PATTERNS_SHA256:
        print("error: the abstention pattern list differs from the committed one", file=sys.stderr)
        return 1
    try:
        result = cmd_extract(args) if args.command == "extract" else cmd_analyze(args)
    except LabelFreeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
