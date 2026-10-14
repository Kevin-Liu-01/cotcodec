"""Shared helpers for AM1 Step 0 (``memcredit``), EXPLORATORY.

Pure Python plus numpy (no torch, no vLLM), so that the vLLM image, the CPU selftest and the
host analysis can all import it. It holds:

* config loading (``experiments/am1/memcredit-step0-v1.yaml``);
* LongMemEval-S parsing, a deterministic BM25 retriever over user turns, question selection and
  the two pool arms (retriever top-k and gold-augmented);
* the reader prompt for one subset of a pool (bit ``i`` of a mask keeps memory ``i``);
* A/A replay comparison and exact Clopper-Pearson intervals;
* exact set-function analysis on a 2^k table: the uniform-measure Fourier spectrum, Moebius
  dividends, leave-one-out and exact Shapley credit, and keep-set regret against the exact
  optimum;
* a crude answer-containment utility (the full study uses a judge; Step 0 does not).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am1" / "memcredit-step0-v1.yaml"
EXPERIMENT_ID = "memcredit-step0-v1"
DATE_FORMAT = "%Y/%m/%d (%a) %H:%M"


class MemcreditError(ValueError):
    """The Step 0 config, its inputs or its outputs are invalid."""


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT_ID:
        raise MemcreditError(f"not the {EXPERIMENT_ID} config")
    if config.get("claim_level") != "exploratory":
        raise MemcreditError("AM1 Step 0 is exploratory only")
    if config.get("seeds") != [42, 43, 44]:
        raise MemcreditError("seeds must be [42, 43, 44]")
    pool = config["pools"]
    if not 1 <= int(pool["size"]) <= 10:
        raise MemcreditError("pool size must be 1..10 (2^k subsets are enumerated)")
    if set(pool["arms"]) != {"retrieved", "gold"}:
        raise MemcreditError("the two pool arms are retrieved and gold")
    if pool["distractor_seed"] not in config["seeds"]:
        raise MemcreditError("pools.distractor_seed must be a declared seed")
    for key in ("k1", "b"):
        value = config["retriever"][key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MemcreditError(f"retriever.{key} must be a number")
    seeds = set(config["seeds"])
    for name, spec in config["request_sets"].items():
        if spec.get("seed") is not None and spec["seed"] not in seeds:
            raise MemcreditError(f"request set {name}: seed outside the declared seeds")
    if config["sampling"]["sampled"]["seed"] not in seeds:
        raise MemcreditError("the sampled arm's request seed must be a declared seed")
    if config["shuffle_seed"] not in seeds:
        raise MemcreditError("shuffle_seed must be a declared seed")
    session_ids = [s["id"] for s in config["sessions"]]
    if len(set(session_ids)) != len(session_ids):
        raise MemcreditError("session ids must be unique")
    for session in config["sessions"]:
        for item in session["passes"]:
            if item["set"] not in config["request_sets"]:
                raise MemcreditError(f"{session['id']}: unknown request set {item['set']}")
            if item["sampling"] not in config["sampling"]:
                raise MemcreditError(f"{session['id']}: unknown sampling {item['sampling']}")
            if item.get("order", "canonical") not in ("canonical", "shuffled"):
                raise MemcreditError(f"{session['id']}: order must be canonical or shuffled")
    return config


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


# --------------------------------------------------------------------------- LongMemEval


@dataclass(frozen=True)
class Turn:
    session_index: int
    turn_index: int
    session_id: str
    date: str
    role: str
    content: str
    has_answer: bool


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, DATE_FORMAT)


def iter_turns(record: dict[str, Any]) -> list[Turn]:
    sessions = record["haystack_sessions"]
    dates = record["haystack_dates"]
    ids = record["haystack_session_ids"]
    if not len(sessions) == len(dates) == len(ids):
        raise MemcreditError(f"{record['question_id']}: haystack lists differ in length")
    turns = []
    for s_index, (session, date, session_id) in enumerate(zip(sessions, dates, ids, strict=True)):
        for t_index, turn in enumerate(session):
            turns.append(
                Turn(
                    session_index=s_index,
                    turn_index=t_index,
                    session_id=str(session_id),
                    date=str(date),
                    role=str(turn["role"]),
                    content=str(turn["content"]),
                    has_answer=bool(turn.get("has_answer", False)),
                )
            )
    return turns


def is_abstention(record: dict[str, Any]) -> bool:
    return str(record["question_id"]).endswith("_abs")


def eligibility(record: dict[str, Any], selection: dict[str, Any]) -> str | None:
    """None if the question may enter the demo, else the reason it may not."""

    if selection.get("exclude_abstention", True) and is_abstention(record):
        return "abstention"
    if record["question_type"] not in selection["types"]:
        return "type not in the demo strata"
    gold = [t for t in iter_turns(record) if t.has_answer]
    if not gold:
        return "no gold turn"
    allowed_roles = set(selection["gold_roles"])
    if any(t.role not in allowed_roles for t in gold):
        return "a gold turn is not a user turn"
    if len(gold) > int(selection["max_gold_turns"]):
        return "more gold turns than the cap"
    if len(gold) > int(selection["pool_size"]):
        return "more gold turns than the pool"
    return None


def select_questions(records: Sequence[dict[str, Any]], selection: dict[str, Any]) -> list[str]:
    """Question ids: per type in config order, a seeded sample of the eligible ids (sorted)."""

    rng = random.Random(int(selection["seed"]))
    chosen: list[str] = []
    for qtype, quota in selection["types"].items():
        pool = sorted(
            r["question_id"]
            for r in records
            if r["question_type"] == qtype and eligibility(r, selection) is None
        )
        if len(pool) < int(quota):
            raise MemcreditError(f"only {len(pool)} eligible {qtype} questions")
        chosen.extend(sorted(rng.sample(pool, int(quota))))
    return chosen


# --------------------------------------------------------------------------- BM25

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORD_TEXT = """
a about above after again against all am an and any are as at be because been before
being below between both but by can did do does doing down during each few for from
further had has have having he her here hers herself him himself his how i if in into is
it its itself just me more most my myself no nor not now of off on once only or other
our ours ourselves out over own same she should so some such than that the their theirs
them themselves then there these they this those through to too under until up very was
we were what when where which while who whom why will with you your yours yourself
yourselves
"""
STOPWORDS = frozenset(_STOPWORD_TEXT.split())


def bm25_tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    """Okapi BM25 with the non-negative (Lucene) idf, over pre-tokenized documents."""

    def __init__(self, docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = float(k1)
        self.b = float(b)
        self.docs = [list(d) for d in docs]
        self.lengths = [len(d) for d in self.docs]
        self.n = len(self.docs)
        self.avgdl = (sum(self.lengths) / self.n) if self.n else 0.0
        df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for doc in self.docs:
            counts: dict[str, int] = {}
            for token in doc:
                counts[token] = counts.get(token, 0) + 1
            self.tf.append(counts)
            for token in counts:
                df[token] = df.get(token, 0) + 1
        self.idf = {t: math.log(1.0 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: Sequence[str]) -> list[float]:
        terms = list(dict.fromkeys(query))
        out = []
        for counts, length in zip(self.tf, self.lengths, strict=True):
            norm = self.k1 * (1.0 - self.b + self.b * (length / self.avgdl if self.avgdl else 0.0))
            total = 0.0
            for term in terms:
                f = counts.get(term)
                if f:
                    total += self.idf[term] * f * (self.k1 + 1.0) / (f + norm)
            out.append(total)
        return out


def rank_user_turns(record: dict[str, Any], retriever: dict[str, Any]) -> list[tuple[Turn, float]]:
    """User turns ranked by BM25 against the question; ties by session, then turn index."""

    turns = [t for t in iter_turns(record) if t.role == "user"]
    index = BM25([bm25_tokens(t.content) for t in turns], retriever["k1"], retriever["b"])
    scores = index.scores(bm25_tokens(record["question"]))
    order = sorted(
        range(len(turns)), key=lambda i: (-scores[i], turns[i].session_index, turns[i].turn_index)
    )
    return [(turns[i], scores[i]) for i in order]


# --------------------------------------------------------------------------- pools


def memory_entry(turn: Turn, rank: int, score: float, max_chars: int) -> dict[str, Any]:
    text = turn.content.strip()
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars].rstrip() + " [...]"
    return {
        "session_id": turn.session_id,
        "session_index": turn.session_index,
        "turn_index": turn.turn_index,
        "date": turn.date,
        "is_gold": turn.has_answer,
        "bm25_rank": rank,
        "bm25_score": round(score, 6),
        "chars": len(turn.content),
        "truncated": truncated,
        "text": text,
        "text_sha256": sha256_text(text),
    }


def chronological(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        memories,
        key=lambda m: (parse_date(m["date"]), m["session_index"], m["turn_index"]),
    )


def build_pools(record: dict[str, Any], config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Both arms, each in chronological order (memory i is bit i of a subset mask).

    retrieved: the BM25 top-k user turns (the deployable pool). gold: every gold user turn plus
    distractors drawn uniformly from the question's other user turns (CMP-style), with
    ``random.Random(f"{seed}:{question_id}")``, so the arm does not copy the retriever's pool.
    """

    k = int(config["pools"]["size"])
    max_chars = int(config["pools"]["max_memory_chars"])
    ranked = rank_user_turns(record, config["retriever"])
    entries = [memory_entry(t, r, s, max_chars) for r, (t, s) in enumerate(ranked)]
    retrieved = entries[:k]
    gold = [e for e in entries if e["is_gold"]]
    if len(gold) > k:
        raise MemcreditError(f"{record['question_id']}: more gold turns than the pool")
    others = sorted(
        (e for e in entries if not e["is_gold"]),
        key=lambda e: (e["session_index"], e["turn_index"]),
    )
    rng = random.Random(f"{int(config['pools']['distractor_seed'])}:{record['question_id']}")
    fill = rng.sample(others, k - len(gold))
    pools = {"retrieved": chronological(retrieved), "gold": chronological(gold + fill)}
    for arm, pool in pools.items():
        if len(pool) != k:
            raise MemcreditError(f"{record['question_id']}: {arm} pool has {len(pool)} memories")
    return pools


# --------------------------------------------------------------------------- prompts


def subset(pool: Sequence[dict[str, Any]], mask: int) -> list[dict[str, Any]]:
    if not 0 <= mask < (1 << len(pool)):
        raise MemcreditError(f"mask {mask} outside a pool of {len(pool)}")
    return [m for i, m in enumerate(pool) if mask >> i & 1]


def user_message(
    question: dict[str, Any], memories: Sequence[dict[str, Any]], template: dict[str, Any]
) -> str:
    if memories:
        lines = "\n".join(f"- [{m['date']}] {m['text']}" for m in memories)
    else:
        lines = template["no_memories"]
    return template["user"].format(
        memories=lines, question_date=question["question_date"], question=question["question"]
    )


def request_table(artifact: dict[str, Any], arms: Sequence[str]) -> list[dict[str, Any]]:
    """Every (question, arm, mask) request in canonical order: question, then arm, then mask."""

    table = []
    for q_index, question in enumerate(artifact["questions"]):
        for arm in arms:
            k = len(question["pools"][arm])
            for mask in range(1 << k):
                table.append(
                    {
                        "index": len(table),
                        "question_index": q_index,
                        "question_id": question["question_id"],
                        "arm": arm,
                        "mask": mask,
                    }
                )
    return table


def request_message(
    artifact: dict[str, Any], request: dict[str, Any], template: dict[str, Any]
) -> str:
    question = artifact["questions"][request["question_index"]]
    memories = subset(question["pools"][request["arm"]], request["mask"])
    return user_message(question, memories, template)


def request_set(n_requests: int, spec: dict[str, Any]) -> list[int]:
    """Request indices of a named set: all, or a seeded sample, in index order."""

    size = spec.get("size")
    if size is None or int(size) >= n_requests:
        return list(range(n_requests))
    return sorted(random.Random(int(spec["seed"])).sample(range(n_requests), int(size)))


def pass_order(indices: Sequence[int], order: str, shuffle_seed: int) -> list[int]:
    out = list(indices)
    if order == "shuffled":
        random.Random(shuffle_seed).shuffle(out)
    return out


# --------------------------------------------------------------------------- A/A statistics


def _log_binom_pmf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), summed in log space."""

    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    # Sum the shorter side; the tails used here (alpha / 2) are far from rounding error.
    upper_side = k > n // 2
    terms = range(k + 1, n + 1) if upper_side else range(k + 1)
    logs = [_log_binom_pmf(i, n, p) for i in terms]
    top = max(logs)
    total = 0.0 if top == -math.inf else math.exp(top) * sum(math.exp(v - top) for v in logs)
    return max(0.0, min(1.0, 1.0 - total if upper_side else total))


def _bisect(fn: Any, lo: float, hi: float, iterations: int = 64) -> float:
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        if fn(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1 - alpha) interval for a binomial proportion k / n."""

    if n <= 0 or not 0 <= k <= n:
        raise MemcreditError(f"invalid binomial counts k={k}, n={n}")
    tail = alpha / 2.0
    # lower: the smallest p with P(X >= k | p) >= tail; upper: the largest p with
    # P(X <= k | p) >= tail.
    lower = 0.0 if k == 0 else _bisect(lambda p: 1.0 - binom_cdf(k - 1, n, p) >= tail, 0.0, 1.0)
    upper = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p) < tail, 0.0, 1.0)
    return lower, upper


def float32_bits(values: Iterable[float]) -> bytes:
    return b"".join(struct.pack("<f", float(v)) for v in values)


def first_difference(a: Sequence[int], b: Sequence[int]) -> int | None:
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


# --------------------------------------------------------------------------- set functions


def check_table(values: Sequence[float]) -> int:
    n = len(values)
    k = n.bit_length() - 1
    if n < 1 or (1 << k) != n:
        raise MemcreditError("a set-function table needs 2^k values")
    return k


def popcount(mask: int) -> int:
    return bin(mask).count("1")


def fourier(values: Sequence[float]) -> list[float]:
    """Coefficients f^(T) under the uniform measure, chi_T(S) = prod_{i in T} (+1 if i in S else
    -1); f(S) = sum_T f^(T) chi_T(S). Walsh-Hadamard transform divided by 2^k."""

    k = check_table(values)
    coeffs = [float(v) for v in values]
    h = 1
    while h < len(coeffs):
        for start in range(0, len(coeffs), 2 * h):
            for j in range(start, start + h):
                a, b = coeffs[j], coeffs[j + h]
                # index j lacks the bit (element absent, chi -1), j + h has it (+1)
                coeffs[j], coeffs[j + h] = a + b, b - a
        h *= 2
    return [c / (1 << k) for c in coeffs]


def fourier_order_shares(values: Sequence[float]) -> dict[str, Any]:
    """Variance share by interaction order (uniform measure); None when f is constant."""

    k = check_table(values)
    coeffs = fourier(values)
    by_order = [0.0] * (k + 1)
    for mask, c in enumerate(coeffs):
        by_order[popcount(mask)] += c * c
    variance = sum(by_order[1:])
    if variance <= 1e-15:
        return {"variance": 0.0, "shares": None, "share_order_2_plus": None}
    shares = [v / variance for v in by_order[1:]]
    return {
        "variance": variance,
        "shares": shares,
        "share_order_2_plus": sum(shares[1:]),
    }


def moebius(values: Sequence[float]) -> list[float]:
    """Dividends a(T) = sum_{U subset of T} (-1)^{|T|-|U|} f(U) (0/1 basis)."""

    check_table(values)
    out = [float(v) for v in values]
    h = 1
    while h < len(out):
        for start in range(0, len(out), 2 * h):
            for j in range(start, start + h):
                out[j + h] -= out[j]
        h *= 2
    return out


def and_or_baseline(m: int) -> float | None:
    """Order >= 2 Fourier share of an m-way AND (or OR): 1 - m / (2^m - 1)."""

    if m < 1:
        return None
    return 1.0 - m / ((1 << m) - 1)


def loo_credit(values: Sequence[float]) -> list[float]:
    k = check_table(values)
    full = (1 << k) - 1
    return [float(values[full]) - float(values[full & ~(1 << i)]) for i in range(k)]


def shapley(values: Sequence[float]) -> list[float]:
    """Exact Shapley values, summed in rational arithmetic so that ties are exact."""

    k = check_table(values)
    exact = [Fraction(float(v)) for v in values]
    weights = [
        Fraction(math.factorial(s) * math.factorial(k - s - 1), math.factorial(k)) for s in range(k)
    ]
    phi = [Fraction(0)] * k
    for mask in range(1 << k):
        size = popcount(mask)
        for i in range(k):
            if not mask >> i & 1:
                phi[i] += weights[size] * (exact[mask | 1 << i] - exact[mask])
    return [float(v) for v in phi]


def best_keep_sets(values: Sequence[float], budget: int) -> tuple[float, list[int]]:
    k = check_table(values)
    masks = [m for m in range(1 << k) if popcount(m) == budget]
    best = max(float(values[m]) for m in masks)
    return best, [m for m in masks if float(values[m]) == best]


def credit_keep_sets(credit: Sequence[float], budget: int) -> list[int]:
    """Every size-``budget`` set a top-B rule on ``credit`` may return: the items above the
    cut-off value, plus any choice among the items tied at it."""

    if not 0 < budget <= len(credit):
        raise MemcreditError("budget must be 1..k")
    ranked = sorted(credit, reverse=True)
    cut = ranked[budget - 1]
    above = [i for i, c in enumerate(credit) if c > cut]
    tied = [i for i, c in enumerate(credit) if c == cut]
    base = sum(1 << i for i in above)
    need = budget - len(above)
    return sorted(base | sum(1 << i for i in combo) for combo in combinations(tied, need))


def keep_set_from_credit(credit: Sequence[float], budget: int) -> int:
    """The top-B set with ties broken by the lower memory index."""

    order = sorted(range(len(credit)), key=lambda i: (-credit[i], i))
    mask = 0
    for i in order[:budget]:
        mask |= 1 << i
    return mask


def keep_set_regret(values: Sequence[float], credit: Sequence[float], budget: int) -> float:
    """Regret of the index-tie-broken top-B set against the exact optimum."""

    best, _ = best_keep_sets(values, budget)
    return best - float(values[keep_set_from_credit(credit, budget)])


def keep_set_regret_range(
    values: Sequence[float], credit: Sequence[float], budget: int
) -> dict[str, float | int]:
    """Regret of a top-B rule over every tie-breaking: min, mean (uniform over the tied
    choices), max, and how many sets the rule may return."""

    best, _ = best_keep_sets(values, budget)
    regrets = [best - float(values[m]) for m in credit_keep_sets(credit, budget)]
    return {
        "min": min(regrets),
        "mean": sum(regrets) / len(regrets),
        "max": max(regrets),
        "sets": len(regrets),
    }


# --------------------------------------------------------------------------- crude utility

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = re.compile(r"[^a-z0-9 ]+")


_NUMBER_WORDS = {
    word: str(value)
    for value, word in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ]
    )
}


def normalize_answer(text: str) -> str:
    """Lowercase, punctuation and articles removed, number words 0-20 as digits."""

    text = text.lower().replace("-", " ")
    text = _PUNCT.sub(" ", text)
    text = _ARTICLES.sub(" ", text)
    return " ".join(_NUMBER_WORDS.get(word, word) for word in text.split())


def contains_answer(reply: str, answer: Any) -> int:
    """1 if the normalized gold answer occurs in the normalized reply (crude; no judge)."""

    gold = normalize_answer(str(answer))
    if not gold:
        return 0
    return int(f" {gold} " in f" {normalize_answer(reply)} ")
