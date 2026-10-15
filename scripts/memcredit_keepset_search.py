#!/usr/bin/env python3
"""am1-keepset-search-v1 (CPU only): keep-set search against memory credit at equal reader calls,
BM25 top 4 against the full pool, and a label-free non-abstention search, on AM1's 256-subset
tables (registration ``program/preregistrations/am1-keepset-search-v1.md``, D115).

Every number comes from data the program already holds: AM1's committed tables (the judged
utility u(S) of all 2^8 subsets of each pool) and, for the label-free rule, the reader pass that
made them. No GPU, no new model call.

* H-A (oracle utility): direct search (read m distinct random 4-subsets, keep the best one read;
  exact expectation by order statistics) against leave-one-out, SNIPW-64, MSR-Banzhaf-64,
  permutation Shapley-16 and greedy backward elimination with BM25 ties, at matched or fewer
  reader calls. Retrieved arm, keep 4 of 8, non-constant tables. Sampled rules average 200 seeds.
* H-B: accuracy of BM25 top 4 against all 8, retrieved arm, every question; exact McNemar test.
* H-C (label-free): ``nonabstain-BM25`` (the best-BM25-ranked 4-subset whose reply does not
  abstain, BM25 top 4 when every 4-subset abstains) against BM25 top 4; exact McNemar test.
* Descriptive: oracle-search ceiling, direct-search curves, abstention rates, reads of the
  BM25-ordered stop rule, per arm and question type.

Subcommands:

* ``extract`` (host CPU; reads a raw reader pass, which holds texts): joins every request to its
  judged label with ``memcredit_analyze.join_rows`` (the join that built AM1's tables), checks
  that the joined labels reproduce every committed table, and writes AM1d's text-free per-request
  features (``memcredit_label_free.build_features``) to a host-only directory.
* ``analyze`` (local or host CPU): the hypotheses and descriptive outputs from the committed
  tables and the features; writes ``results.json``, ``per-table.json.gz`` and ``tables.md``.
* ``selftest`` (development only): reproduces AM1b's and AM1d's committed numbers where they
  overlap with this code.
* ``power`` (development only): operating characteristics from the development analysis.

``--split heldout`` refuses to open any held-out input unless this registration is frozen (a
ledger row for ``am1-keepset-search-v1`` with the registration file's SHA-256) and every code pin
of the registration's section 16 matches the working tree. ``--split development`` refuses any
held-out path.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_cost_curve as cc  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am1-keepset-search-v1"
REGISTRATION = Path("program/preregistrations/am1-keepset-search-v1.md")
LEDGER = Path("program/preregistrations/ledger.jsonl")
#: The registration's section that lists the code of record (parsed for the held-out gate).
CODE_SECTION = "## 16. Code of record"

K = 8
BUDGET = 4
FULL = (1 << K) - 1
FOUR_SETS = lf.FOUR_SETS
N_FOUR = len(FOUR_SETS)  # 70
ARMS = ("retrieved", "gold")
PRIMARY_ARM = "retrieved"

#: Sampled rules: seeds SEED_BASE .. SEED_BASE + N_SEEDS - 1, each drawn with
#: random.Random(f"{seed}:{question_id}:{arm}:{rule}") (AM1's and AM1b's scheme: seeds 42-44
#: are AM1's draws, seeds 42-61 AM1b's).
SEED_BASE = 42
N_SEEDS = 200
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42
#: H-A: family-wise one-sided alpha per direction, Bonferroni over the family's comparisons.
ALPHA_A = 0.05
#: A bound clears 0 only by more than this many Monte Carlo standard errors of its mean.
MC_SE_MARGIN = 3.0
#: H-B and H-C: two-sided alpha of the exact McNemar test.
ALPHA_PAIRED = 0.05
#: Descriptive direct-search points (calls).
CURVE_POINTS = (8, 16, 26, 38, 70)
#: Power simulation (development only).
POWER_SIMULATIONS = 1_000
POWER_RESAMPLES = 1_000
POWER_SEED = 43
POWER_SCALES = (1.0, 0.5, 0.25)

SAMPLED_RULES = ("snipw_64", "msr_banzhaf_64", "perm_shapley_16")
HA_RULES = ("loo", "snipw_64", "msr_banzhaf_64", "perm_shapley_16", "greedy_backward")


@dataclass(frozen=True)
class Comparison:
    """Direct search minus a rule, in keep-set regret: negative when direct search loses less.
    ``calls`` None means direct search at the rule's own calls (per table and seed)."""

    id: str
    rule: str
    calls: int | None
    describe: str


#: H-A's family (registration section 6).
COMPARISONS: tuple[Comparison, ...] = (
    Comparison("A1", "loo", None, "leave-one-out (9 calls) vs direct search at 9 calls"),
    Comparison("A2", "snipw_64", None, "SNIPW-64 vs direct search at the same calls (per draw)"),
    Comparison("A3", "snipw_64", 26, "SNIPW-64 vs direct search at 26 calls (fewer)"),
    Comparison("A4", "msr_banzhaf_64", None, "MSR-Banzhaf-64 vs direct search at 64 calls"),
    Comparison("A5", "msr_banzhaf_64", 26, "MSR-Banzhaf-64 vs direct search at 26 calls (fewer)"),
    Comparison("A6", "perm_shapley_16", 26, "permutation Shapley-16 vs direct search at 26 calls"),
    Comparison(
        "A7", "greedy_backward", None, "greedy backward, BM25 ties (26 calls) vs direct at 26"
    ),
)
COMPARISON_IDS = tuple(c.id for c in COMPARISONS)


class KeepsetError(ValueError):
    """An input, a gate, a validation check or a void rule failed."""


# --------------------------------------------------------------------------- pinned inputs

HELDOUT_DIR = Path("program/evidence/2026-10-16/am1-confirmatory")
SPLITS: dict[str, dict[str, Any]] = {
    "development": {
        "tables": cc.DEV_TABLES,
        "tables_sha256": cc.DEV_TABLES_SHA256,
        "tables_json_sha256": None,
        "questions": 63,
        "question_ids_sha256": None,
        "nonconstant": {"retrieved": 38, "gold": 51},
        "config": ms.CONFIG_PATH,
        "config_id": "memcredit-study-v1",
        "artifact_split": "development",
        "artifact_sha256": lf.ARTIFACT_SHA256,
        "pass": {
            "job": "1411",
            "name": "job 1411, reader-gpu0 (GPU 0, canonical order, compiled batch-invariant "
            "mode); labels: job 1411 judge32-gpu0 (Qwen3-32B); the pass of AM1's development "
            "tables and of AM1d",
            "reader": "reader-gpu0",
            "judge": "judge32-gpu0",
            "sha256": {
                **lf.MAIN_PASS["sha256"],
                "sessions/reader-gpu0/worker-progress.jsonl": (
                    "4b51a5bc01dbc08fc488539ac8fe2e66af24459ef754d737c5dd60bc4da55956"
                ),
            },
        },
        "frozen_required": False,
    },
    "heldout": {
        "tables": HELDOUT_DIR / "analysis" / "tables.json.gz",
        "tables_sha256": "841e79452d7af6441492abfce64d85cadf5b51415cc7e0461df76ce228df0729",
        # analysis/logs/outputs.sha256: the uncompressed tables.json written by AM1's analyze
        "tables_json_sha256": "2d3574be5d3686d73b73dc2d1b36ed3c9b04b23731078bcb6b5f92b83cc3a9cd",
        "questions": 347,
        "question_ids_sha256": "d4f024fbcda5394984a46c421cd938f2b6db6067fef0f21a5c6e72359b27e50a",
        "nonconstant": {"retrieved": 251, "gold": 288},
        "config": ms.REGISTRATION_CONFIG_PATH,
        "config_id": "am1-memory-credit-v1",
        "artifact_split": "heldout",
        "artifact_sha256": "f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7",
        "pass": {
            "job": "1458",
            "name": "job 1458, reader-gpu0 (GPU 0, canonical order, eager batch-invariant mode); "
            "labels: job 1458 judge32-gpu0 (Qwen3-32B); the pass of AM1's held-out tables",
            "reader": "reader-gpu0",
            "judge": "judge32-gpu0",
            "sha256": {
                "sessions/reader-gpu0/all.json": (
                    "c8381bcbe4afe33e436ad101cbe313ef1608c40916dbd8a6e3a4c0191322e189"
                ),
                "sessions/reader-gpu0/all.npz": (
                    "8f985d8a2b40ecbb4fcbed1c2a63323c3d4ce398da83eea5fef8bca137054776"
                ),
                "sessions/reader-gpu0/all.texts.jsonl.gz": (
                    "b05d5d87f9b9c7445cb053d8e4830e2fcf105f04f7c265551773dd9665fcfd39"
                ),
                "sessions/reader-gpu0/worker-progress.jsonl": (
                    "0f280d34fa6ede8f6e0a11e4428e7114a9489595fae17a7a22940cb55c9ec470"
                ),
                "sessions/judge32-gpu0/all.json": (
                    "5a36bbac383c6a5395c148dc837c75906cf806ff64969cc67ef770b417929300"
                ),
                "sessions/judge32-gpu0/all.npz": (
                    "229cefd3fdadc060a89f5d16e6c7ab76d8a20f7f444bc88fd7d48740c6f9f7f6"
                ),
                "sessions/judge32-gpu0/all.texts.jsonl.gz": (
                    "e2166086dfe773a4e52054d2dc6d58372adb7cde8a4e4a060e990a6e66fb53f4"
                ),
                "sessions/judge8-gpu0/all.json": (
                    "33c280bf120a551fe41c9569cd2c350d31eca50da4b791b64867ec62a370883c"
                ),
                "sessions/judge8-gpu0/all.npz": (
                    "9fe7bf7d1ac5a35478d8dc064d88f30e6f5f65631d664a74d5f8720f932d1ba7"
                ),
                "sessions/judge8-gpu0/all.texts.jsonl.gz": (
                    "e31d77ad7f39a56d829b5ccbef033e56b5b99fe90d01725d03d837a82de95cae"
                ),
                "judge-items.json": (
                    "c3eec6515b4e654bb88cccef65dba1d88e210326bbf238c27c6f8dfa1c3a2999"
                ),
            },
        },
        "frozen_required": True,
    },
}
#: Path parts that mark held-out inputs; the development split never opens one.
HELDOUT_PARTS = ("am1-confirmatory", "am1-memory-credit-v1")
#: The code whose SHA-256 the features record and ``analyze`` checks.
FEATURE_CODE = (
    "scripts/memcredit_keepset_search.py",
    "scripts/memcredit_label_free.py",
    "scripts/memcredit_analyze.py",
    "scripts/memcredit_study.py",
    "harness/memcredit.py",
    "harness/memcredit_study.py",
)
#: AM1b's and AM1d's committed development outputs (selftest only).
AM1B_DIR = Path("program/evidence/2026-10-15/am1b-cost-curve")
AM1D_DIR = Path("program/evidence/2026-10-15/am1d-label-free")
AM1D_FEATURES_SHA256 = "cb678e3bdd5b55bd206a10816ac30eb5502530bc3c47e87d4213bb3f767b7fa5"


# --------------------------------------------------------------------------- gates and digests


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(payload: Any) -> bytes:
    return (json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode()


def check_development_path(path: Path | str) -> None:
    """The development split never opens a held-out path (symlinks resolved)."""

    texts = [str(path)]
    with contextlib.suppress(OSError):
        texts.append(str(Path(path).resolve()))
    for text in texts:
        for part in HELDOUT_PARTS:
            if part in text:
                raise KeepsetError(f"the development split refuses held-out paths: {path}")


def registration_frozen(
    ledger: Path | None = None, registration: Path | None = None, experiment: str = EXPERIMENT
) -> bool:
    """True when the ledger holds a row for ``experiment`` with the registration's SHA-256."""

    ledger = ledger or PROJECT_ROOT / LEDGER
    registration = registration or PROJECT_ROOT / REGISTRATION
    if not ledger.is_file() or not registration.is_file():
        return False
    digest = sha256_file(registration)
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("experiment_id") == experiment and row.get("sha256") == digest:
            return True
    return False


_PIN_ROW = re.compile(r"^\| `([^`]+)` \|.*\| `([0-9a-f]{64})` \|\s*$")


def code_pins(registration: Path | None = None) -> dict[str, str]:
    """The registration's code of record: {path: SHA-256} from section 16's table rows."""

    registration = registration or PROJECT_ROOT / REGISTRATION
    text = registration.read_text(encoding="utf-8")
    if CODE_SECTION not in text:
        raise KeepsetError(f"{registration}: no section '{CODE_SECTION}'")
    section = text.split(CODE_SECTION, 1)[1].split("\n## ", 1)[0]
    pins = {}
    for line in section.splitlines():
        match = _PIN_ROW.match(line.strip())
        if match:
            pins[match.group(1)] = match.group(2)
    if not pins:
        raise KeepsetError("the registration pins no code")
    return pins


def check_code_pins(registration: Path | None = None, root: Path = PROJECT_ROOT) -> dict[str, Any]:
    pins = code_pins(registration)
    mismatched = [
        path for path, digest in sorted(pins.items())
        if not (root / path).is_file() or sha256_file(root / path) != digest
    ]  # fmt: skip
    if mismatched:
        raise KeepsetError(f"code differs from the registration's pins: {mismatched}")
    return {"files": len(pins), "all_match": True}


def gate(split: str) -> dict[str, Any]:
    """Run before any input of the split is opened. Held-out: frozen registration and every code
    pin matching; development: nothing to check here (paths are checked as they are opened)."""

    if split not in SPLITS:
        raise KeepsetError(f"unknown split {split}")
    if not SPLITS[split]["frozen_required"]:
        return {"split": split, "frozen_required": False}
    if not registration_frozen():
        raise KeepsetError(
            "held-out data is opened only after the freeze: no ledger row for "
            f"{EXPERIMENT} with this registration file's SHA-256"
        )
    pins = check_code_pins()
    return {"split": split, "frozen_required": True, "registration_frozen": True, "pins": pins}


def check_digests(run_dir: Path, pinned: dict[str, str]) -> dict[str, str]:
    out = {}
    for relative, expected in sorted(pinned.items()):
        actual = sha256_file(run_dir / relative)
        if actual != expected:
            raise KeepsetError(f"{relative}: SHA-256 {actual} is not the pinned {expected}")
        out[relative] = actual
    return out


def code_digests() -> dict[str, str]:
    return {path: sha256_file(PROJECT_ROOT / path) for path in FEATURE_CODE}


# --------------------------------------------------------------------------- tables


def load_tables(split: str, path: Path | None = None) -> list[dict[str, Any]]:
    """The split's committed tables, after the gate, checked against their pinned digests (the
    gz file and, for held-out, the uncompressed tables.json of AM1's analysis)."""

    spec = SPLITS[split]
    gate(split)
    path = path or PROJECT_ROOT / spec["tables"]
    if split == "development":
        check_development_path(path)
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != spec["tables_sha256"]:
        raise KeepsetError(f"{path}: SHA-256 is not the pinned {spec['tables_sha256']}")
    data = gzip.decompress(raw)
    if spec["tables_json_sha256"] is not None and sha256_bytes(data) != spec["tables_json_sha256"]:
        raise KeepsetError("the uncompressed tables differ from AM1's tables.json")
    tables = json.loads(data)
    for t in tables:
        for key in ("regret", "credits", "credits_seeded", "summary", "placebo"):
            if key in t:
                t[key] = cc._field(t[key])
    return tables


def bm25_ranks(t: dict[str, Any]) -> list[int]:
    credit = [float(x) for x in t["credits"]["retrieval_rank"]]
    ranks = [int(-c) for c in credit]
    if [-float(r) for r in ranks] != credit or len(set(ranks)) != K:
        raise KeepsetError(f"{t['question_id']}:{t['arm']}: BM25 ranks are not distinct integers")
    return ranks


def validate_tables(tables: Sequence[dict[str, Any]], split: str) -> dict[str, Any]:
    """The void checks on the tables: count, completeness, decoding, the question set, the
    non-constant counts AM1 reported, distinct BM25 ranks and BM25 top 4 as AM1's retrieval-rank
    keep set."""

    spec = SPLITS[split]
    failures: list[str] = []
    keys = Counter((t["question_id"], t["arm"]) for t in tables)
    qids = sorted({t["question_id"] for t in tables})
    if len(tables) != 2 * spec["questions"] or len(qids) != spec["questions"]:
        failures.append(f"{len(tables)} tables over {len(qids)} questions")
    if any(n != 1 for n in keys.values()) or {a for _, a in keys} != set(ARMS):
        failures.append("not one table per question and arm")
    nonconstant: Counter[str] = Counter()
    for t in tables:
        tag = f"{t['question_id']}:{t['arm']}"
        if not t.get("complete"):
            failures.append(f"{tag}: incomplete")
            continue
        values = cc.decode_values(t["values_hex"])
        if cc.encode_values(values) != t["values_hex"]:
            failures.append(f"{tag}: re-encoding differs")
        constant = len(set(values)) == 1
        if bool(t["summary"]["constant"]) != constant:
            failures.append(f"{tag}: summary.constant differs")
        nonconstant[t["arm"]] += int(not constant)
        ranks = bm25_ranks(t)
        top = lf.bm25_top_mask(ranks)
        check = mc.keep_set_regret_range(values, [-float(r) for r in ranks], BUDGET)
        opt4 = mc.best_keep_sets(values, BUDGET)[0]
        if check["sets"] != 1 or check["mean"] != opt4 - values[top]:
            failures.append(f"{tag}: BM25 top 4 is not the retrieval-rank keep set")
    if dict(nonconstant) != spec["nonconstant"]:
        failures.append(
            f"non-constant tables {dict(nonconstant)} differ from {spec['nonconstant']}"
        )
    if spec["question_ids_sha256"] is not None:
        config = ms.load_config(spec["config"])
        split_file = ms.load_split(PROJECT_ROOT / config["split"]["path"], config)
        ordered = ms.confirmatory_question_ids(split_file, config)
        if mc.sha256_text("\n".join(ordered)) != spec["question_ids_sha256"]:
            failures.append("the confirmatory ids differ from their pin")
        if sorted(ordered) != qids:
            failures.append("the tables' questions are not the confirmatory set")
    report = {
        "tables": len(tables),
        "questions": len(qids),
        "nonconstant": dict(sorted(nonconstant.items())),
        "failures": failures,
        "passed": not failures,
    }
    if failures:
        raise KeepsetError(f"VOID: the tables fail validation ({len(failures)}): {failures[:10]}")
    return report


# --------------------------------------------------------------------------- H-A per table


def ha_table(
    values: Sequence[float],
    question_id: str,
    arm: str,
    ranks: Sequence[int],
    seeds: Sequence[int],
) -> dict[str, Any]:
    """H-A on one table at B = 4: every rule's regret and calls (per seed for the sampled rules),
    the exact direct-search curve, and each comparison's direct-minus-rule difference per seed."""

    direct = cc.direct_search_curve(values, BUDGET)
    rand = ms.random_regret(values, BUDGET)
    rules = {r.name: r for r in cc.credit_rules()}
    priority = [-float(r) for r in ranks]
    out: dict[str, dict[str, list[float]]] = {}
    table = cc.CountingTable(values)
    credit = mc.loo_credit(table)
    out["loo"] = {
        "regret": [float(mc.keep_set_regret_range(values, credit, BUDGET)["mean"])],
        "calls": [table.calls],
    }
    for name in SAMPLED_RULES:
        regrets, calls = [], []
        for seed in seeds:
            rng = cc.rule_rng(seed, question_id, arm, name)
            table = cc.CountingTable(values)
            credit = rules[name].credit(table, rng)
            regrets.append(float(mc.keep_set_regret_range(values, credit, BUDGET)["mean"]))
            calls.append(table.calls)
        out[name] = {"regret": regrets, "calls": calls}
    table = cc.CountingTable(values)
    mask = cc.greedy_backward(table, BUDGET, priority)
    if table.calls != cc.greedy_calls(K, BUDGET, False):
        raise KeepsetError("greedy backward read a different number of sets")
    out["greedy_backward"] = {
        "regret": [cc.set_regret(values, mask, BUDGET)],
        "calls": [table.calls],
        "mask": mask,
    }
    for name in ("loo", "msr_banzhaf_64", "greedy_backward"):
        expected = {"loo": 9, "msr_banzhaf_64": 64, "greedy_backward": 26}[name]
        if set(out[name]["calls"]) != {expected}:
            raise KeepsetError(f"{name}: calls {sorted(set(out[name]['calls']))} != {expected}")
    for cell in out.values():
        cell["direct_matched"] = [cc.matched_direct(direct, c, rand) for c in cell["calls"]]
    diffs = {}
    for comp in COMPARISONS:
        cell = out[comp.rule]
        if comp.calls is None:
            diffs[comp.id] = [d - r for d, r in zip(cell["direct_matched"], cell["regret"],
                                                     strict=True)]  # fmt: skip
        else:
            diffs[comp.id] = [direct[comp.calls - 1] - r for r in cell["regret"]]
    return {"direct": direct, "random": rand, "rules": out, "diffs": diffs}


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def ha_summary(ha: dict[str, Any]) -> dict[str, Any]:
    """The per-table record written to per-table.json.gz (seed means, no per-seed lists)."""

    rules = {}
    for name, cell in ha["rules"].items():
        entry = {
            "regret": _mean(cell["regret"]),
            "calls_mean": _mean(cell["calls"]),
            "calls_min": min(cell["calls"]),
            "calls_max": max(cell["calls"]),
            "direct_matched": _mean(cell["direct_matched"]),
        }
        if "mask" in cell:
            entry["mask"] = cell["mask"]
        rules[name] = entry
    return {
        "direct_curve": ha["direct"],
        "random_regret": ha["random"],
        "rules": rules,
        "comparisons": {cid: _mean(d) for cid, d in ha["diffs"].items()},
    }


# --------------------------------------------------------------------------- H-B / H-C


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value on the discordant pairs: 2 P(X <= min(b, c)), X ~
    Binomial(b + c, 1/2), capped at 1 (exact rational arithmetic); 1 when there are none."""

    if b < 0 or c < 0:
        raise KeepsetError("negative counts")
    n = b + c
    if n == 0:
        return 1.0
    tail = Fraction(sum(math.comb(n, i) for i in range(min(b, c) + 1)), 2**n)
    return float(min(Fraction(1), 2 * tail))


def paired_reading(
    rule: dict[str, float],
    base: dict[str, float],
    labels: tuple[str, str, str],
    resamples: int,
    seed: int,
    alpha: float = ALPHA_PAIRED,
) -> dict[str, Any]:
    """rule minus base in accuracy, paired by question: discordant counts b (rule right, base
    wrong) and c, the exact McNemar test, the paired difference with its exact conditional 95%
    interval ((b + c) / n times 2 pi - 1, pi's Clopper-Pearson interval for b of b + c; the
    inversion of the same exact test) and a question-cluster bootstrap 95% interval; and the
    reading: labels[0] if p <= alpha and b > c, labels[1] if p <= alpha and b < c, else
    labels[2]."""

    qids = sorted(rule)
    if sorted(base) != qids:
        raise KeepsetError("paired readings need the same questions")
    for q in qids:
        if rule[q] not in (0.0, 1.0) or base[q] not in (0.0, 1.0):
            raise KeepsetError("McNemar needs 0/1 outcomes")
    n = len(qids)
    b = sum(1 for q in qids if rule[q] == 1.0 and base[q] == 0.0)
    c = sum(1 for q in qids if rule[q] == 0.0 and base[q] == 1.0)
    p = mcnemar_exact(b, c)
    nd = b + c
    if nd:
        lo, hi = mc.clopper_pearson(b, nd, 0.05)
        exact = [nd / n * (2 * lo - 1), nd / n * (2 * hi - 1)]
    else:
        exact = [0.0, 0.0]
    boot = ms.cluster_bootstrap({q: [rule[q] - base[q]] for q in qids}, resamples, seed, 0.05)
    if p <= alpha and b > c:
        reading = labels[0]
    elif p <= alpha and b < c:
        reading = labels[1]
    else:
        reading = labels[2]
    return {
        "questions": n,
        "rule_accuracy": sum(rule.values()) / n,
        "base_accuracy": sum(base.values()) / n,
        "rule_right_base_wrong": b,
        "rule_wrong_base_right": c,
        "discordant": nd,
        "difference": (b - c) / n,
        "ci95_exact_conditional": exact,
        "ci95_bootstrap": boot["ci"],
        "p_exact_mcnemar": p,
        "alpha": alpha,
        "reading": reading,
    }


def mcnemar_threshold(nd: int, alpha: float = ALPHA_PAIRED) -> int:
    """The largest k with mcnemar_exact(k, nd - k) <= alpha (-1 if none): the exact test rejects
    exactly when min(b, c) <= k. k < nd / 2 always, since the p-value at min(b, c) >= nd / 2 is
    1."""

    k = -1
    while k + 1 < nd and mcnemar_exact(k + 1, nd - k - 1) <= alpha:
        k += 1
    return k


def _pmf(k: int, n: int, p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return float(k == (n if p >= 1.0 else 0))
    return math.exp(mc._log_binom_pmf(k, n, p))


def mcnemar_power(
    n: int,
    rate: float,
    share: float,
    alpha: float = ALPHA_PAIRED,
    thresholds: dict[int, int] | None = None,
) -> float:
    """P(the exact test rejects) over n questions when each is discordant with probability
    ``rate`` and a discordant pair favours the rule with probability ``share`` (exact sums over
    both binomials)."""

    thresholds = thresholds if thresholds is not None else {}
    total = 0.0
    for nd in range(n + 1):
        w = _pmf(nd, n, rate)
        if w < 1e-15:
            continue
        if nd not in thresholds:
            thresholds[nd] = mcnemar_threshold(nd, alpha)
        k = thresholds[nd]
        if k < 0:
            continue
        reject = sum(_pmf(b, nd, share) for b in range(k + 1))
        reject += sum(_pmf(b, nd, share) for b in range(nd - k, nd + 1))
        total += w * reject
    return min(1.0, total)


def nonabstain_choice(pool: dict[str, Any], values: Sequence[float]) -> dict[str, Any]:
    """H-C's rule on one pool: the BM25-ordered stop rule (read 4-subsets in BM25 rank-sum order,
    ``memcredit_label_free.rank_key``; keep the first whose reply does not abstain; BM25 top 4 if
    none does). Its choice is ``nonabstain@70``'s, which ``bm25_ordered_nonabstain`` checks."""

    ranks = pool["bm25_rank"]
    order = sorted(FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)
    posthoc = lf.bm25_ordered_nonabstain(pool, values)
    position = posthoc["first_answer_position"]
    chosen = order[position - 1] if position else order[0]
    nonabstain = next(u for u in lf.UTILITIES if u.name == "nonabstain")
    if chosen != lf.select(pool, list(FOUR_SETS), nonabstain):
        raise KeepsetError("the stop rule differs from nonabstain@70")
    return {
        "mask": chosen,
        "u": float(values[chosen]),
        "first_answer_position": position,
        "reads": position if position else N_FOUR,
        "capped": {k: v for k, v in posthoc["rows"].items()},
    }


# --------------------------------------------------------------------------- analysis


def check_features(features: dict[str, Any], split: str, check_code: bool = True) -> None:
    spec = SPLITS[split]
    if features.get("experiment") != EXPERIMENT or features.get("split") != split:
        raise KeepsetError("the features belong to another experiment or split")
    if features["pass"]["sha256"] != spec["pass"]["sha256"]:
        raise KeepsetError("the features come from another pass")
    if features["pass"]["study_artifact_sha256"] != spec["artifact_sha256"]:
        raise KeepsetError("the features come from another study artifact")
    if features.get("abstention_patterns_sha256") != lf.ABSTENTION_PATTERNS_SHA256:
        raise KeepsetError("the features used another abstention pattern list")
    if check_code and features.get("code_sha256") != code_digests():
        raise KeepsetError("the features were extracted by other code")


def table_record(
    t: dict[str, Any], pool: dict[str, Any] | None, seeds: Sequence[int]
) -> tuple[dict[str, Any], dict[str, list[float]] | None]:
    values = cc.decode_values(t["values_hex"])
    ranks = bm25_ranks(t)
    top = lf.bm25_top_mask(ranks)
    nonconstant = len(set(values)) > 1
    opt4 = mc.best_keep_sets(values, BUDGET)[0]
    rec: dict[str, Any] = {
        "question_id": t["question_id"],
        "question_type": t["question_type"],
        "arm": t["arm"],
        "nonconstant": nonconstant,
        "opt4": opt4,
        "u_all_8": float(values[FULL]),
        "u_bm25_top4": float(values[top]),
        "bm25_top4_mask": top,
    }
    diffs = None
    if nonconstant:
        ha = ha_table(values, t["question_id"], t["arm"], ranks, seeds)
        rec["ha"] = ha_summary(ha)
        diffs = ha["diffs"]
    if pool is not None:
        if [float(v) for v in pool["u"]] != [float(v) for v in values]:
            raise KeepsetError(f"{t['question_id']}:{t['arm']}: features differ from the table")
        if list(pool["bm25_rank"]) != ranks or pool["question_type"] != t["question_type"]:
            raise KeepsetError(f"{t['question_id']}:{t['arm']}: features' ranks or type differ")
        choice = nonabstain_choice(pool, values)
        abstain4 = [bool(pool["abstain"][m]) for m in FOUR_SETS]
        rec["hc"] = {
            "mask": choice["mask"],
            "u": choice["u"],
            "first_answer_position": choice["first_answer_position"],
            "reads": choice["reads"],
            "capped": choice["capped"],
            "four_subset_abstain": sum(abstain4),
            "four_subset_abstain_correct": sum(
                int(pool["u"][m]) for m in FOUR_SETS if pool["abstain"][m]
            ),
            "bm25_top4_abstains": bool(pool["abstain"][top]),
            "all_8_abstains": bool(pool["abstain"][FULL]),
        }
    return rec, diffs


def _bounds(clusters: dict[str, list[float]], resamples: int, seed: int, alpha_one: float) -> dict:
    """Mean, two-sided 95% interval, and one-sided (1 - alpha_one) lower and upper bounds (the
    ends of ``cluster_bootstrap``'s two-sided 1 - 2 alpha_one interval: the upper bound is the
    ceil((1 - alpha_one)(R - 1))-th order statistic of R resampled means)."""

    ci95 = ms.cluster_bootstrap(clusters, resamples, seed, 0.05)
    decision = ms.cluster_bootstrap(clusters, resamples, seed, 2 * alpha_one)
    return {
        "mean": ci95["mean"],
        "ci95": ci95["ci"],
        "lower": decision["ci"][0],
        "upper": decision["ci"][1],
        "level_one_sided": 1 - alpha_one,
        "tables": ci95["units"],
    }


def ha_aggregate(
    records: Sequence[dict[str, Any]],
    per_seed: dict[tuple[str, str], dict[str, list[float]]],
    arm: str,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    """H-A on one arm: every comparison's mean difference, 95% interval, decision bounds and
    Monte Carlo error; every rule's regret; direct search at the curve points; the verdict."""

    rows = [r for r in records if r["arm"] == arm and r["nonconstant"]]
    alpha_one = ALPHA_A / len(COMPARISONS)
    comps = {}
    for comp in COMPARISONS:
        clusters = {r["question_id"]: [r["ha"]["comparisons"][comp.id]] for r in rows}
        entry = _bounds(clusters, resamples, seed, alpha_one)
        seeds_by_table = [per_seed[(r["question_id"], arm)][comp.id] for r in rows]
        n_seeds = len(seeds_by_table[0])
        if n_seeds > 1:
            seed_means = [_mean([s[j] for s in seeds_by_table]) for j in range(n_seeds)]
            entry["mc_se"] = statistics.stdev(seed_means) / math.sqrt(n_seeds)
        else:
            entry["mc_se"] = 0.0
        entry["seeds"] = n_seeds
        entry["rule"] = comp.rule
        entry["direct_calls"] = "matched" if comp.calls is None else comp.calls
        entry["rule_calls_mean"] = _mean([r["ha"]["rules"][comp.rule]["calls_mean"] for r in rows])
        entry["describe"] = comp.describe
        entry["classification"] = classify(entry)
        comps[comp.id] = entry
    rules = {}
    for name in HA_RULES:
        clusters = {r["question_id"]: [r["ha"]["rules"][name]["regret"]] for r in rows}
        entry = _bounds(clusters, resamples, seed, alpha_one)
        entry["calls_mean"] = _mean([r["ha"]["rules"][name]["calls_mean"] for r in rows])
        entry["calls_min"] = min(r["ha"]["rules"][name]["calls_min"] for r in rows)
        entry["calls_max"] = max(r["ha"]["rules"][name]["calls_max"] for r in rows)
        rules[name] = entry
    direct = {}
    for m in sorted(set(CURVE_POINTS) | {9, 26, 64}):
        clusters = {r["question_id"]: [r["ha"]["direct_curve"][m - 1]] for r in rows}
        direct[str(m)] = _bounds(clusters, resamples, seed, alpha_one)
    return {
        "tables": len(rows),
        "alpha_family": ALPHA_A,
        "alpha_one_sided_per_comparison": alpha_one,
        "comparisons": comps,
        "rules": rules,
        "direct_search": direct,
        "verdict": ha_verdict(comps),
    }


def classify(entry: dict[str, Any]) -> str:
    """One comparison: SEARCH_BETTER if the upper bound clears 0 (below it by more than
    MC_SE_MARGIN Monte Carlo standard errors), RULE_BETTER if the lower bound clears 0 above,
    NOT_SEPARATED otherwise."""

    margin = MC_SE_MARGIN * float(entry.get("mc_se") or 0.0)
    if entry["upper"] < -margin:
        return "SEARCH_BETTER"
    if entry["lower"] > margin:
        return "RULE_BETTER"
    return "NOT_SEPARATED"


def ha_verdict(comps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """H-A's rule: SEARCH_DOMINATES if every comparison is SEARCH_BETTER; RULE_BEATS_SEARCH if
    any comparison is RULE_BETTER (naming them); INCONCLUSIVE otherwise."""

    classes = {cid: comps[cid]["classification"] for cid in COMPARISON_IDS}
    near = [
        cid for cid in COMPARISON_IDS
        if comps[cid].get("mc_se") and min(abs(comps[cid]["upper"]), abs(comps[cid]["lower"]))
        <= MC_SE_MARGIN * comps[cid]["mc_se"]
    ]  # fmt: skip
    if all(c == "SEARCH_BETTER" for c in classes.values()):
        verdict = "SEARCH_DOMINATES"
    elif any(c == "RULE_BETTER" for c in classes.values()):
        verdict = "RULE_BEATS_SEARCH"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "verdict": verdict,
        "classifications": classes,
        "rule_better": [cid for cid, c in classes.items() if c == "RULE_BETTER"],
        "not_separated": [cid for cid, c in classes.items() if c == "NOT_SEPARATED"],
        "bounds_within_mc_margin": near,
    }


def _boot(clusters: dict[str, list[float]], resamples: int, seed: int) -> dict[str, Any]:
    r = ms.cluster_bootstrap(clusters, resamples, seed, 0.05)
    return {"mean": r["mean"], "ci95": r["ci"], "units": r["units"]}


def descriptive(
    records: Sequence[dict[str, Any]], resamples: int, seed: int, with_features: bool
) -> dict[str, Any]:
    """Per arm and question type (and all types): accuracy of BM25 top 4, all 8, nonabstain-BM25
    and the oracle ceiling (best 4-subset) over every question; direct search's regret on the
    non-constant tables and its accuracy at the curve points; abstention rates and reads."""

    out: dict[str, Any] = {}
    for arm in ARMS:
        out[arm] = {}
        arm_rows = [r for r in records if r["arm"] == arm]
        types = ["all"] + sorted({r["question_type"] for r in arm_rows})
        for qtype in types:
            rows = [r for r in arm_rows if qtype == "all" or r["question_type"] == qtype]
            nc = [r for r in rows if r["nonconstant"]]
            cell: dict[str, Any] = {"questions": len(rows), "nonconstant": len(nc)}

            def acc(fn: Any, subset: Sequence[dict[str, Any]] = rows) -> dict[str, Any]:
                return _boot({r["question_id"]: [fn(r)] for r in subset}, resamples, seed)

            cell["accuracy"] = {
                "bm25_top4": acc(lambda r: r["u_bm25_top4"]),
                "all_8": acc(lambda r: r["u_all_8"]),
                "oracle_ceiling": acc(lambda r: r["opt4"]),
            }
            curve: dict[str, Any] = {}
            for m in CURVE_POINTS:

                def regret_at(r: dict[str, Any], m: int = m) -> float:
                    return r["ha"]["direct_curve"][m - 1] if r["nonconstant"] else 0.0

                curve[str(m)] = {
                    "regret_nonconstant": acc(regret_at, nc) if nc else None,
                    "accuracy_all": acc(lambda r, f=regret_at: r["opt4"] - f(r)),
                }
            cell["direct_search"] = curve
            if with_features:
                cell["accuracy"]["nonabstain_bm25"] = acc(lambda r: r["hc"]["u"])
                n4 = sum(r["hc"]["four_subset_abstain"] for r in rows)
                reads = [r["hc"]["reads"] for r in rows]
                cell["abstention"] = {
                    "four_subset_replies": N_FOUR * len(rows),
                    "four_subset_abstain": n4,
                    "four_subset_abstain_rate": n4 / (N_FOUR * len(rows)),
                    "four_subset_abstain_judged_correct": sum(
                        r["hc"]["four_subset_abstain_correct"] for r in rows
                    ),
                    "bm25_top4_abstains": sum(r["hc"]["bm25_top4_abstains"] for r in rows),
                    "all_8_abstains": sum(r["hc"]["all_8_abstains"] for r in rows),
                    "pools_where_every_4_subset_abstains": sum(
                        r["hc"]["first_answer_position"] is None for r in rows
                    ),
                }
                cell["stop_rule_reads"] = reads_summary(reads)
            out[arm][qtype] = cell
    return out


def reads_summary(reads: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(reads)
    return {
        "pools": len(reads),
        "mean": _mean(reads),
        "median": statistics.median(reads),
        "max": max(reads),
        "at_1": sum(x == 1 for x in reads),
        "at_most_8": sum(x <= 8 for x in reads),
        "at_most_16": sum(x <= 16 for x in reads),
        "p90": ordered[int(math.ceil(0.9 * len(ordered))) - 1],
        "distribution": {str(x): n for x, n in sorted(Counter(reads).items())},
    }


def analyze(
    tables: Sequence[dict[str, Any]],
    features: dict[str, Any] | None,
    split: str,
    n_seeds: int = N_SEEDS,
    seed_base: int = SEED_BASE,
    resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    check_counts: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seeds = [seed_base + j for j in range(n_seeds)]
    validation = validate_tables(tables, split) if check_counts else {"skipped": True}
    pools = None
    if features is not None:
        pools = {(p["question_id"], p["arm"]): p for p in features["pools"]}
        if len(pools) != len(tables):
            raise KeepsetError(f"{len(pools)} feature pools against {len(tables)} tables")
    records, per_seed = [], {}
    for t in sorted(tables, key=lambda t: (t["arm"], t["question_id"])):
        pool = pools[(t["question_id"], t["arm"])] if pools is not None else None
        rec, diffs = table_record(t, pool, seeds)
        records.append(rec)
        if diffs is not None:
            per_seed[(t["question_id"], t["arm"])] = diffs
    h_a = {arm: ha_aggregate(records, per_seed, arm, resamples, bootstrap_seed) for arm in ARMS}
    h_b, h_c = {}, {}
    for arm in ARMS:
        rows = [r for r in records if r["arm"] == arm]
        top = {r["question_id"]: r["u_bm25_top4"] for r in rows}
        full = {r["question_id"]: r["u_all_8"] for r in rows}
        h_b[arm] = paired_reading(
            top, full, ("PRUNING_HELPS", "PRUNING_HURTS", "NO_DETECTED_DIFFERENCE"),
            resamples, bootstrap_seed,
        )  # fmt: skip
        if pools is not None:
            rule = {r["question_id"]: r["hc"]["u"] for r in rows}
            h_c[arm] = paired_reading(
                rule, top, ("NONABSTAIN_HELPS", "NONABSTAIN_HURTS", "NO_DETECTED_DIFFERENCE"),
                resamples, bootstrap_seed,
            )  # fmt: skip
            h_c[arm]["reads"] = {
                "all_questions": reads_summary([r["hc"]["reads"] for r in rows]),
                "nonconstant": reads_summary([r["hc"]["reads"] for r in rows if r["nonconstant"]]),
            }
            h_c[arm]["nonabstain_minus_all_8"] = paired_reading(
                rule, full, ("RULE_AHEAD", "RULE_BEHIND", "NO_DETECTED_DIFFERENCE"),
                resamples, bootstrap_seed,
            )  # fmt: skip
    verdicts = {
        "H-A": {
            "arm": PRIMARY_ARM,
            **h_a[PRIMARY_ARM]["verdict"],
            "gold_arm_same_rule_descriptive": h_a["gold"]["verdict"]["verdict"],
        },
        "H-B": {
            "arm": PRIMARY_ARM,
            "reading": h_b[PRIMARY_ARM]["reading"],
            "gold_arm_descriptive": h_b["gold"]["reading"],
        },  # fmt: skip
        "H-C": (
            {
                "arm": PRIMARY_ARM,
                "reading": h_c[PRIMARY_ARM]["reading"],
                "gold_arm_descriptive": h_c["gold"]["reading"],
            }  # fmt: skip
            if h_c
            else None
        ),
    }
    results = {
        "experiment": EXPERIMENT,
        "split": split,
        "status": (
            "REGISTERED ANALYSIS (am1-keepset-search-v1, held-out tables)"
            if split == "heldout"
            else "DEVELOPMENT DRY RUN: development tables only; not a result of the registration"
        ),
        "validation": validation,
        "features": None
        if features is None
        else {
            "pass": features["pass"],
            "validation": features["validation"],
            "features_sha256": features.get("_sha256"),
            "code_sha256": features.get("code_sha256"),
        },  # fmt: skip
        "config": config_record(n_seeds, seed_base, resamples, bootstrap_seed),
        "h_a": h_a,
        "h_b": h_b,
        "h_c": h_c or None,
        "reply_stats": lf.reply_stats(features["pools"]) if features is not None else None,
        "descriptive": descriptive(records, resamples, bootstrap_seed, features is not None),
        "verdicts": verdicts,
    }
    return results, records


def config_record(n_seeds: int, seed_base: int, resamples: int, bootstrap_seed: int) -> dict:
    return {
        "k": K,
        "budget": BUDGET,
        "arms": list(ARMS),
        "primary_arm": PRIMARY_ARM,
        "comparisons": {
            c.id: {
                "rule": c.rule,
                "direct_calls": "matched" if c.calls is None else c.calls,
                "describe": c.describe,
            }  # fmt: skip
            for c in COMPARISONS
        },
        "seeds": {
            "base": seed_base,
            "count": n_seeds,
            "rng": "random.Random(f'{seed}:{question_id}:{arm}:{rule}')",
        },
        "bootstrap": {
            "resamples": resamples,
            "seed": bootstrap_seed,
            "code": "harness.memcredit_study.cluster_bootstrap",
            "unit": "question (one table per question per arm)",
        },
        "alpha_h_a": {
            "family_wise_one_sided": ALPHA_A,
            "per_comparison": ALPHA_A / len(COMPARISONS),
            "correction": f"Bonferroni over {len(COMPARISONS)} comparisons",
            "mc_se_margin": MC_SE_MARGIN,
        },
        "alpha_paired": ALPHA_PAIRED,
        "regret": "harness.memcredit.keep_set_regret_range mean over tie sets (AM1); a search "
        "rule's set through cc.set_regret",
        "direct_search": "memcredit_cost_curve.direct_search_curve (exact order statistics)",
        "calls": "distinct subsets read per pool (memoized), empty and full sets counted when read",
        "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
        "stop_rule_order": "4-subsets by ascending BM25 rank sum, then lexicographically smaller "
        "sorted BM25 ranks (memcredit_label_free.rank_key, descending)",
    }


# --------------------------------------------------------------------------- markdown


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _s(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.3f}"


def _ci(ci: Sequence[float | None], signed: bool = False) -> str:
    fmt = _s if signed else _f
    return f"[{fmt(ci[0])}, {fmt(ci[1])}]"


def render_markdown(results: dict[str, Any]) -> str:
    cfg = results["config"]
    lines = [
        f"# {EXPERIMENT}: generated tables ({results['split']})",
        "",
        f"Status: {results['status']}. Generated by `scripts/memcredit_keepset_search.py "
        "analyze`. Keep 4 of 8. Intervals are question-cluster bootstraps "
        f"({cfg['bootstrap']['resamples']:,} resamples, seed {cfg['bootstrap']['seed']}). "
        f"Sampled rules: mean over {cfg['seeds']['count']} seeds.",
        "",
        "## Verdicts",
        "",
        "```",
        json.dumps(results["verdicts"], indent=1, sort_keys=True),
        "```",
        "",
    ]
    for arm in ARMS:
        ha = results["h_a"][arm]
        lines += [
            f"## H-A, {arm} arm ({ha['tables']} non-constant tables)"
            + (" (primary)" if arm == PRIMARY_ARM else " (secondary, descriptive)"),
            "",
            "Difference = direct search's regret minus the rule's (negative: search loses less). "
            f"Decision bounds are one-sided at {1 - ha['alpha_one_sided_per_comparison']:.5f} "
            f"(family-wise {ha['alpha_family']}, Bonferroni over {len(COMPARISONS)}).",
            "",
            "| Id | Comparison | Rule calls | Difference | 95% CI | Lower | Upper | MC se | "
            "Class |",
            "|---|---|---:|---:|---|---:|---:|---:|---|",
        ]
        for cid in COMPARISON_IDS:
            c = ha["comparisons"][cid]
            lines.append(
                f"| {cid} | {c['describe']} | {c['rule_calls_mean']:.1f} | {_s(c['mean'])} | "
                f"{_ci(c['ci95'], True)} | {_s(c['lower'])} | {_s(c['upper'])} | "
                f"{c['mc_se']:.4f} | {c['classification']} |"
            )
        lines += [
            "",
            f"Verdict: **{ha['verdict']['verdict']}**",
            "",
            "| Rule | Calls (mean, range) | Regret | 95% CI |",
            "|---|---|---:|---|",
        ]
        for name in HA_RULES:
            r = ha["rules"][name]
            lines.append(
                f"| {name} | {r['calls_mean']:.1f} ({r['calls_min']}-{r['calls_max']}) | "
                f"{_f(r['mean'])} | {_ci(r['ci95'])} |"
            )
        lines += ["", "| Direct search, calls | Regret | 95% CI |", "|---:|---:|---|"]
        for m, d in sorted(ha["direct_search"].items(), key=lambda kv: int(kv[0])):
            lines.append(f"| {m} | {_f(d['mean'])} | {_ci(d['ci95'])} |")
        lines.append("")
    for name, key in (("H-B: BM25 top 4 minus all 8", "h_b"), ("H-C: nonabstain-BM25 minus "
                                                              "BM25 top 4", "h_c")):  # fmt: skip
        block = results.get(key)
        if not block:
            continue
        lines += [
            f"## {name}",
            "",
            "| Arm | Questions | Rule acc. | Base acc. | b | c | Difference | 95% exact cond. | "
            "95% bootstrap | p (exact McNemar) | Reading |",
            "|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|",
        ]
        for arm in ARMS:
            r = block[arm]
            lines.append(
                f"| {arm} | {r['questions']} | {_f(r['rule_accuracy'])} | "
                f"{_f(r['base_accuracy'])} | {r['rule_right_base_wrong']} | "
                f"{r['rule_wrong_base_right']} | {_s(r['difference'])} | "
                f"{_ci(r['ci95_exact_conditional'], True)} | {_ci(r['ci95_bootstrap'], True)} | "
                f"{r['p_exact_mcnemar']:.4g} | {r['reading']} |"
            )
        lines.append("")
    if results.get("h_c"):
        lines += [
            "## H-C: reads of the BM25-ordered stop rule (the answering call included)",
            "",
            "| Arm | Tables | Mean | Median | 90th pct | Max | At 1 | At most 8 | At most 16 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for arm in ARMS:
            for subset in ("all_questions", "nonconstant"):
                r = results["h_c"][arm]["reads"][subset]
                lines.append(
                    f"| {arm} | {r['pools']} {subset} | {r['mean']:.2f} | {r['median']} | "
                    f"{r['p90']} | {r['max']} | {r['at_1']} | {r['at_most_8']} | "
                    f"{r['at_most_16']} |"
                )
        lines.append("")
    lines += [
        "## Descriptive: per arm and question type",
        "",
        "Accuracy over every question; direct-search regret over the non-constant tables.",
        "",
        "| Arm | Type | Questions | Non-const. | Oracle ceiling | All 8 | BM25 top 4 | "
        "nonabstain-BM25 | Direct regret @8 / 16 / 26 / 38 / 70 | 4-subset abstain rate | "
        "Mean reads |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for arm in ARMS:
        for qtype, cell in results["descriptive"][arm].items():
            a = cell["accuracy"]
            curve = " / ".join(
                _f((cell["direct_search"][str(m)]["regret_nonconstant"] or {}).get("mean"))
                for m in CURVE_POINTS
            )
            abst = cell.get("abstention")
            reads = cell.get("stop_rule_reads")
            lines.append(
                f"| {arm} | {qtype} | {cell['questions']} | {cell['nonconstant']} | "
                f"{_f(a['oracle_ceiling']['mean'])} | {_f(a['all_8']['mean'])} | "
                f"{_f(a['bm25_top4']['mean'])} | "
                f"{_f(a['nonabstain_bm25']['mean']) if 'nonabstain_bm25' in a else 'n/a'} | "
                f"{curve} | {_f(abst['four_subset_abstain_rate']) if abst else 'n/a'} | "
                f"{_f(reads['mean'], 2) if reads else 'n/a'} |"
            )
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- commands


def write_gz_json(path: Path, payload: Any) -> None:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(blob, mtime=0))


def read_gz_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def end_of_turn_id(path: Path) -> int:
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("event") == "engine-start":
            return int(record["end_of_turn_id"])
    raise KeepsetError(f"{path}: no engine-start event")


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    import memcredit_analyze as ma

    split = args.split
    spec = SPLITS[split]
    gate_record = gate(split)
    run_dir, evidence, private = Path(args.run_dir), Path(args.evidence), Path(args.private_dir)
    if private.resolve().is_relative_to(PROJECT_ROOT.resolve()):
        raise KeepsetError("the features stay on the host: --private-dir must be outside the repo")
    if split == "development":
        for p in (run_dir, evidence, private):
            check_development_path(p)
    config = ms.load_config(spec["config"])
    if config["experiment_id"] != spec["config_id"]:
        raise KeepsetError("the config is not the split's")
    digests = check_digests(run_dir, spec["pass"]["sha256"])
    if sha256_file(evidence) != spec["artifact_sha256"]:
        raise KeepsetError("the study artifact is not the pinned one")
    artifact = ma.load_artifact(evidence, config, spec["artifact_sha256"])
    if artifact.get("split") != spec["artifact_split"]:
        raise KeepsetError("the study artifact belongs to another split")
    tables = load_tables(split)
    validate_tables(tables, split)
    question_index = {q["question_id"]: i for i, q in enumerate(artifact["questions"])}
    # The join that built AM1's tables, unchanged; then AM1d's join keeping tokens and log-probs.
    rows_ma, items, primary, _ = ma.join_rows(run_dir, config, artifact)
    views = ma.pool_views(rows_ma, artifact)
    try:
        validation = lf.validate_tables(views, tables, question_index)
    except lf.LabelFreeError as exc:
        raise KeepsetError(f"VOID (H-C): {exc}") from exc
    requests = ms.request_table(artifact, config["pools"]["arms"])
    reader = ma.load_pass(run_dir, spec["pass"]["reader"])
    if reader is None or reader["meta"].get("missing_logprobs"):
        raise KeepsetError("the reader pass is missing or lacks log-probs")
    rows = lf.join_requests(requests, reader["rows"], items, primary)
    mismatched = sum(
        1 for a, b in zip(rows, rows_ma, strict=True)
        if a["index"] != b["index"] or a["reply"] != b["reply"] or a["u"] != b["u"]
    )  # fmt: skip
    if mismatched or len(rows) != len(rows_ma):
        raise KeepsetError(f"VOID (H-C): {mismatched} requests differ between the two joins")
    table_requests = [r for r in rows if r["kind"] == "table"]
    validation.update(
        requests=len(rows),
        table_requests=len(table_requests),
        table_requests_labelled=sum(r["u"] is not None for r in table_requests),
        joins_agree_requests=len(rows) - mismatched,
        judge_items=len(items),
        reader_finish=dict(sorted(Counter(r["finish"] for r in table_requests).items())),
    )
    if validation["table_requests_labelled"] != validation["table_requests"]:
        raise KeepsetError("VOID (H-C): a table request has no reply or no label")
    eot = end_of_turn_id(run_dir / "sessions" / spec["pass"]["reader"] / "worker-progress.jsonl")
    try:
        features = lf.build_features(rows, artifact, eot)
    except lf.LabelFreeError as exc:
        raise KeepsetError(f"VOID (H-C): {exc}") from exc
    private.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": EXPERIMENT,
        "split": split,
        "gate": gate_record,
        "pass": {
            "name": spec["pass"]["name"],
            "job": spec["pass"]["job"],
            "sha256": digests,
            "study_artifact_sha256": spec["artifact_sha256"],
            "end_of_turn_id": eot,
        },
        "abstention_patterns_sha256": lf.patterns_sha256(),
        "code_sha256": code_digests(),
        "validation": validation,
        "pools": features,
    }
    out = private / f"features-{split}-{spec['pass']['job']}.json.gz"
    write_gz_json(out, payload)
    return {"features": str(out), "sha256": sha256_file(out), "pools": len(features),
            "validation": validation}  # fmt: skip


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    split = args.split
    gate(split)
    if split == "heldout" and not args.features:
        raise KeepsetError("the registered analysis needs the extracted features")
    if split == "development":
        for p in (args.features, args.output_dir):
            if p is not None:
                check_development_path(p)
    tables = load_tables(split)
    features = None
    if args.features:
        features = read_gz_json(Path(args.features))
        features["_sha256"] = sha256_file(Path(args.features))
        check_features(features, split)
    results, records = analyze(
        tables, features, split, args.seeds, args.seed_base, args.resamples, args.bootstrap_seed
    )
    import numpy as np

    results["inputs"] = {
        "tables": {
            "path": str(SPLITS[split]["tables"]),
            "sha256": SPLITS[split]["tables_sha256"],
            "json_sha256": SPLITS[split]["tables_json_sha256"],
        },  # fmt: skip
        "features_sha256": features["_sha256"] if features else None,
        "code_sha256": code_digests(),
    }
    results["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_bytes(canonical(results))
    write_gz_json(out / "per-table.json.gz", records)
    (out / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return results["verdicts"]


# --------------------------------------------------------------------------- selftest (dev only)


def _check(checks: list[dict[str, Any]], name: str, compared: int, identical: int, **extra) -> None:
    checks.append({"check": name, "compared": compared, "identical": identical,
                   "passed": compared > 0 and compared == identical, **extra})  # fmt: skip


def selftest(
    tables: Sequence[dict[str, Any]],
    analysis_dir: Path,
    am1d_features: Path | None,
    our_features: Path | None,
) -> dict[str, Any]:
    """Development only. Reproduce AM1b's and AM1d's committed numbers where this code overlaps
    them: AM1b's per-table and aggregate rows for leave-one-out, SNIPW-64, MSR-Banzhaf-64,
    permutation Shapley-16 (seeds 42-61, AM1b's 20), greedy backward, the random set, retrieval
    rank and direct search; AM1d's features, per-table choices and aggregate accuracies, reply
    statistics and stop-rule positions; and the exact sign tests AM1d's README quotes."""

    checks: list[dict[str, Any]] = []
    root = PROJECT_ROOT
    am1b_rows = json.loads(gzip.decompress((root / AM1B_DIR / "per-table.json.gz").read_bytes()))
    am1b = json.loads((root / AM1B_DIR / "results.json").read_text(encoding="utf-8"))
    am1d_rows = json.loads(gzip.decompress((root / AM1D_DIR / "per-table.json.gz").read_bytes()))
    am1d = json.loads((root / AM1D_DIR / "results.json").read_text(encoding="utf-8"))
    ours = json.loads((analysis_dir / "results.json").read_text(encoding="utf-8"))
    our_rows = read_gz_json(analysis_dir / "per-table.json.gz")
    by_key = {(t["question_id"], t["arm"]): t for t in tables}
    b_key = {(p["question_id"], p["arm"]): p for p in am1b_rows}
    am1b_seeds = list(range(SEED_BASE, SEED_BASE + int(am1b["config"]["seeds"]["count"])))
    # ---- AM1b, per table, B = 4, at AM1b's 20 seeds
    per_rule: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    curves = [0, 0]
    am1b_clusters: dict[str, dict[str, dict[str, dict[str, list[float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    for key, p in sorted(b_key.items()):
        t = by_key[key]
        values = cc.decode_values(t["values_hex"])
        ha = ha_table(values, key[0], key[1], bm25_ranks(t), am1b_seeds)
        curves[0] += 1
        curves[1] += int(ha["direct"] == p["direct_search"]["4"])
        for name in HA_RULES:
            cell = p["rules"][name]["4"]
            mine = ha["rules"][name]
            ok = (
                _mean(mine["regret"]) == cell["regret"]
                and _mean(mine["direct_matched"]) == cell["direct_matched"]
                and _mean(mine["calls"]) == cell["calls"]
                and min(mine["calls"]) == cell["calls_min"]
                and max(mine["calls"]) == cell["calls_max"]
                and (len(mine["regret"]) == 1 or mine["regret"] == cell["regret_by_seed"])
            )
            per_rule[name][0] += 1
            per_rule[name][1] += int(ok)
            am1b_clusters[key[1]][name]["regret"][key[0]] = [_mean(mine["regret"])]
            am1b_clusters[key[1]][name]["minus"][key[0]] = [
                _mean(mine["regret"]) - _mean(mine["direct_matched"])
            ]
        for name, value in (("random_keep_set", ha["random"]),):
            per_rule[name][0] += 1
            per_rule[name][1] += int(p["rules"][name]["4"]["regret"] == value)
        rank_regret = mc.keep_set_regret_range(values, [-float(r) for r in bm25_ranks(t)], 4)
        per_rule["retrieval_rank"][0] += 1
        per_rule["retrieval_rank"][1] += int(
            p["rules"]["retrieval_rank"]["4"]["regret"] == rank_regret["mean"]
        )
    _check(checks, "AM1b per-table direct-search curve, B = 4 (70 points each)", *curves)
    for name, (c, i) in sorted(per_rule.items()):
        _check(checks, f"AM1b per-table {name}, B = 4 (regret, calls, matched direct; seeds "
               "42-61 per seed)", c, i)  # fmt: skip
    # ---- AM1b aggregates (AM1b's convention: rule minus direct; 10,000 resamples, seed 42)
    agg_n = agg_same = 0
    mismatches = []
    resamples, seed = (
        int(am1b["config"]["bootstrap"]["resamples"]),
        int(am1b["config"]["bootstrap"]["seed"]),
    )
    for arm in ARMS:
        for name in HA_RULES:
            theirs = am1b["curve"][arm]["4"][name]
            reg = am1b_clusters[arm][name]["regret"]
            minus = am1b_clusters[arm][name]["minus"]
            r95 = ms.cluster_bootstrap(reg, resamples, seed, 0.05)
            r99 = ms.cluster_bootstrap(reg, resamples, seed, 0.01)
            d95 = ms.cluster_bootstrap(minus, resamples, seed, 0.05)
            ok = (
                r95["mean"] == theirs["mean_regret"] and r95["ci"] == theirs["ci95"]
                and r99["ci"] == theirs["ci99"]
                and d95["mean"] == theirs["minus_direct_matched"]["mean"]
                and d95["ci"] == theirs["minus_direct_matched"]["ci95"]
            )  # fmt: skip
            agg_n += 1
            agg_same += int(ok)
            if not ok:
                mismatches.append(f"{arm}:{name}")
        for m in (8, 9, 16, 26, 38, 64, 70):
            point = am1b["direct_search"][arm]["4"][m - 1]
            row = ours["h_a"][arm]["direct_search"].get(str(m))
            clusters = {
                p["question_id"]: [p["ha"]["direct_curve"][m - 1]]
                for p in our_rows if p["arm"] == arm and p["nonconstant"]
            }  # fmt: skip
            r95 = ms.cluster_bootstrap(clusters, resamples, seed, 0.05)
            r99 = ms.cluster_bootstrap(clusters, resamples, seed, 0.01)
            ok = (
                point["calls"] == m and r95["mean"] == point["mean_regret"]
                and r95["ci"] == point["ci95"] and r99["ci"] == point["ci99"]
                and (row is None or row["mean"] == point["mean_regret"])
            )  # fmt: skip
            agg_n += 1
            agg_same += int(ok)
            if not ok:
                mismatches.append(f"{arm}:direct@{m}")
    _check(checks, "AM1b results.json rows at B = 4 (mean, 95% and 99% intervals, rule minus "
           "direct at matched calls; direct search at 8, 9, 16, 26, 38, 64, 70 calls)",
           agg_n, agg_same, mismatches=mismatches)  # fmt: skip
    # ---- our registered dry run's deterministic per-table values equal AM1b's
    det_n = det_same = 0
    for p in our_rows:
        key = (p["question_id"], p["arm"])
        if not p["nonconstant"]:
            continue
        theirs = b_key[key]
        for name in ("loo", "greedy_backward"):
            det_n += 1
            mine_regret = p["ha"]["rules"][name]["regret"]
            det_same += int(mine_regret == theirs["rules"][name]["4"]["regret"])
        det_n += 1
        det_same += int(p["ha"]["direct_curve"] == theirs["direct_search"]["4"])
    _check(checks, "dry run (200 seeds): per-table leave-one-out, greedy backward and direct "
           "curve equal AM1b's", det_n, det_same)  # fmt: skip
    # ---- AM1d
    d_key = {(p["question_id"], p["arm"]): p for p in am1d_rows}
    if am1d_features is not None and our_features is not None:
        theirs_f = read_gz_json(am1d_features)
        ok_digest = sha256_file(am1d_features) == AM1D_FEATURES_SHA256
        mine_f = read_gz_json(our_features)
        a = {(p["question_id"], p["arm"]): p for p in theirs_f["pools"]}
        b = {(p["question_id"], p["arm"]): p for p in mine_f["pools"]}
        equal = sum(int(canonical(a[k]) == canonical(b.get(k))) for k in a)
        _check(checks, "AM1d features-1411 pools (pinned digest) equal this extract's pools",
               len(a) if ok_digest else 0, equal,
               am1d_features_sha256_pinned=ok_digest)  # fmt: skip
        same_validation = all(
            mine_f["validation"].get(k) == v for k, v in theirs_f["validation"].items()
        )
        _check(checks, "AM1d extract validation record equals this extract's", 1,
               int(same_validation))  # fmt: skip
    pt_n = pt_same = 0
    for p in our_rows:
        key = (p["question_id"], p["arm"])
        theirs = d_key[key]
        ok = (
            p["u_bm25_top4"] == theirs["rows"]["bm25_top4"]["u"]
            and p["bm25_top4_mask"] == theirs["rows"]["bm25_top4"]["mask"]
            and p["u_all_8"] == theirs["rows"]["all_8"]["u"]
            and p["opt4"] == theirs["opt4"]
            and p["nonconstant"] == theirs["nonconstant"]
        )
        if "hc" in p:
            ok = ok and (
                p["hc"]["mask"] == theirs["rows"]["nonabstain@70"]["mask"]
                and p["hc"]["u"] == theirs["rows"]["nonabstain@70"]["u"]
                and p["hc"]["first_answer_position"] == theirs["posthoc"]["first_answer_position"]
                and p["hc"]["capped"] == theirs["posthoc"]["rows"]
            )
        for m in lf.SEARCH_CALLS:
            regret = p["ha"]["direct_curve"][m - 1] if p["nonconstant"] else 0.0
            ok = ok and theirs["rows"][f"oracle_search@{m}"]["u"] == p["opt4"] - regret
        pt_n += 1
        pt_same += int(ok)
    _check(
        checks,
        "AM1d per-table: BM25 top 4, all 8, best 4-subset, oracle search at 8-70 "
        "calls, nonabstain@70 mask and u, stop-rule position and capped rows",
        pt_n,
        pt_same,
    )
    # AM1d aggregate accuracies (10,000 resamples, seed 42, 95%)
    ag_n = ag_same = 0
    mism = []
    for arm in ARMS:
        for subset in ("nonconstant", "all"):
            rows = [
                p for p in our_rows if p["arm"] == arm and (subset == "all" or p["nonconstant"])
            ]
            cells = am1d["aggregate"][arm][subset]
            series = {
                "bm25_top4": {p["question_id"]: [p["u_bm25_top4"]] for p in rows},
                "all_8": {p["question_id"]: [p["u_all_8"]] for p in rows},
            }
            for m in lf.SEARCH_CALLS:
                series[f"oracle_search@{m}"] = {
                    p["question_id"]: [p["opt4"] - (p["ha"]["direct_curve"][m - 1]
                                                    if p["nonconstant"] else 0.0)]
                    for p in rows
                }  # fmt: skip
            if rows and "hc" in rows[0]:
                series["nonabstain@70"] = {p["question_id"]: [p["hc"]["u"]] for p in rows}
            for name, clusters in series.items():
                r = ms.cluster_bootstrap(clusters, 10_000, 42, 0.05)
                ok = r["mean"] == cells[name]["accuracy"]["mean"] and r["ci"] == cells[name][
                    "accuracy"]["ci95"]  # fmt: skip
                ag_n += 1
                ag_same += int(ok)
                if not ok:
                    mism.append(f"{arm}:{subset}:{name}")
            if "nonabstain@70" in series:
                d = {q: [series["nonabstain@70"][q][0] - series["bm25_top4"][q][0]]
                     for q in series["bm25_top4"]}  # fmt: skip
                r = ms.cluster_bootstrap(d, 10_000, 42, 0.05)
                theirs = cells["nonabstain@70"]["minus_bm25_top4"]
                ok = r["mean"] == theirs["mean"] and r["ci"] == theirs["ci95"]
                ag_n += 1
                ag_same += int(ok)
                if not ok:
                    mism.append(f"{arm}:{subset}:nonabstain-minus-top4")
    _check(checks, "AM1d results.json accuracies and the nonabstain@70 - BM25 top 4 difference "
           "(mean and 95% interval; both arms; non-constant and all)", ag_n, ag_same,
           mismatches=mism)  # fmt: skip
    if ours.get("reply_stats"):
        keys = ("pools", "four_subset_replies", "abstain", "abstain_judged_correct",
                "nonabstain_judged_correct", "abstain_by_pattern", "full_pool_abstain",
                "agree_with_full")  # fmt: skip
        rs_n = rs_same = 0
        for arm in ARMS:
            for k in keys:
                rs_n += 1
                rs_same += int(ours["reply_stats"][arm][k] == am1d["reply_stats"][arm][k])
        _check(checks, "AM1d reply statistics (abstention counts, full-pool abstentions)", rs_n,
               rs_same)  # fmt: skip
        st_n = st_same = 0
        for arm in ARMS:
            for subset, mine_key in (("nonconstant", "nonconstant"), ("all", "all_questions")):
                theirs = am1d["posthoc"]["bm25_ordered_nonabstain"][arm][subset]
                mine = ours["h_c"][arm]["reads"][mine_key]
                f = theirs["first_answer_position"]
                ok = (
                    mine["mean"] == theirs["bm25_ordered_nonabstain@70"]["calls_mean"]
                    and mine["max"] == theirs["bm25_ordered_nonabstain@70"]["calls_max"]
                    and mine["at_1"] == f["at_1"]
                )
                st_n += 1
                st_same += int(ok)
        _check(checks, "AM1d stop-rule reads (mean and max uncapped reads, first answers at "
               "position 1)", st_n, st_same)  # fmt: skip
        hb = ours["h_b"]["retrieved"]
        hc = ours["h_c"]["retrieved"]
        quoted = [
            ("BM25 top 4 vs all 8, retrieved: 4 vs 0, exact p = 0.125",
             (hb["rule_right_base_wrong"], hb["rule_wrong_base_right"], hb["p_exact_mcnemar"]),
             (4, 0, 0.125)),
            ("nonabstain@70 vs all 8, retrieved: 5 vs 0, exact p = 0.0625",
             (hc["nonabstain_minus_all_8"]["rule_right_base_wrong"],
              hc["nonabstain_minus_all_8"]["rule_wrong_base_right"],
              hc["nonabstain_minus_all_8"]["p_exact_mcnemar"]), (5, 0, 0.0625)),
            ("nonabstain@70 vs BM25 top 4, retrieved: 1 table vs 0",
             (hc["rule_right_base_wrong"], hc["rule_wrong_base_right"], hc["p_exact_mcnemar"]),
             (1, 0, 1.0)),
        ]  # fmt: skip
        for label, mine, theirs in quoted:
            _check(checks, f"AM1d README: {label}", 1, int(tuple(mine) == tuple(theirs)),
                   ours=list(mine), quoted=list(theirs))  # fmt: skip
    passed = all(c["passed"] for c in checks)
    inputs = {
        "am1b": {
            "per_table_sha256": sha256_file(root / AM1B_DIR / "per-table.json.gz"),
            "results_sha256": sha256_file(root / AM1B_DIR / "results.json"),
        },
        "am1d": {
            "per_table_sha256": sha256_file(root / AM1D_DIR / "per-table.json.gz"),
            "results_sha256": sha256_file(root / AM1D_DIR / "results.json"),
            "features_1411_sha256": AM1D_FEATURES_SHA256 if am1d_features is not None else None,
        },
        "analysis_results_sha256": sha256_file(analysis_dir / "results.json"),
        "features_sha256": sha256_file(our_features) if our_features is not None else None,
    }
    return {"experiment": EXPERIMENT, "split": "development", "checks": checks, "passed": passed,
            "inputs": inputs}  # fmt: skip


def cmd_selftest(args: argparse.Namespace) -> dict[str, Any]:
    for p in (args.analysis_dir, args.am1d_features, args.features, args.output):
        if p is not None:
            check_development_path(p)
    tables = load_tables("development")
    out = selftest(
        tables,
        Path(args.analysis_dir),
        Path(args.am1d_features) if args.am1d_features else None,
        Path(args.features) if args.features else None,
    )
    Path(args.output).write_bytes(canonical(out))
    if not out["passed"]:
        raise KeepsetError("selftest failed: " + ", ".join(
            c["check"] for c in out["checks"] if not c["passed"]))  # fmt: skip
    return {"passed": True, "checks": len(out["checks"])}


# --------------------------------------------------------------------------- power (dev only)


def power(
    analysis_dir: Path,
    n_tables: int,
    n_questions: int,
    simulations: int = POWER_SIMULATIONS,
    resamples: int = POWER_RESAMPLES,
    seed: int = POWER_SEED,
) -> dict[str, Any]:
    """Operating characteristics from the development dry run. H-A: draw ``n_tables`` tables with
    replacement from the development retrieved non-constant tables (their direct-minus-rule
    differences, all comparisons together), thin the effect (each drawn table keeps its
    differences with probability ``scale``, else all are 0), bootstrap ``resamples`` times and
    apply H-A's rule. H-B and H-C: the exact power of the exact McNemar test over ``n_questions``
    at the development discordance rate and shares of discordant pairs favouring the rule."""

    import numpy as np

    rows = read_gz_json(analysis_dir / "per-table.json.gz")
    dev = json.loads((analysis_dir / "results.json").read_text(encoding="utf-8"))
    rows = [r for r in rows if r["arm"] == PRIMARY_ARM and r["nonconstant"]]
    d = np.array([[r["ha"]["comparisons"][c] for c in COMPARISON_IDS] for r in rows])
    rng = np.random.default_rng(seed)
    alpha_one = ALPHA_A / len(COMPARISONS)
    lo_i = int(math.floor(alpha_one * (resamples - 1)))
    hi_i = int(math.ceil((1 - alpha_one) * (resamples - 1)))
    out: dict[str, Any] = {
        "source": "development dry run (38 retrieved non-constant tables)",
        "n_tables": n_tables,
        "n_questions": n_questions,
        "simulations": simulations,
        "inner_resamples": resamples,
        "seed": seed,
        "development_means": {c: float(d[:, j].mean()) for j, c in enumerate(COMPARISON_IDS)},
        "h_a": {},
    }
    for scale in POWER_SCALES:
        verdicts: Counter[str] = Counter()
        search_better = np.zeros(len(COMPARISON_IDS))
        rule_better = np.zeros(len(COMPARISON_IDS))
        for _ in range(simulations):
            idx = rng.integers(0, len(rows), size=n_tables)
            sample = d[idx]
            if scale < 1.0:
                keep = rng.random(n_tables) < scale
                sample = sample * keep[:, None]
            draws = rng.integers(0, n_tables, size=(resamples, n_tables))
            means = np.sort(sample[draws].mean(axis=1), axis=0)
            lower, upper = means[lo_i], means[hi_i]
            sb = upper < 0
            rb = lower > 0
            search_better += sb
            rule_better += rb
            if sb.all():
                verdicts["SEARCH_DOMINATES"] += 1
            elif rb.any():
                verdicts["RULE_BEATS_SEARCH"] += 1
            else:
                verdicts["INCONCLUSIVE"] += 1
        out["h_a"][str(scale)] = {
            "verdict_probability": {k: v / simulations for k, v in sorted(verdicts.items())},
            "search_better_probability": {
                c: float(search_better[j] / simulations) for j, c in enumerate(COMPARISON_IDS)
            },
            "rule_better_probability": {
                c: float(rule_better[j] / simulations) for j, c in enumerate(COMPARISON_IDS)
            },
        }
    paired = {}
    for key, name, src in (("h_b", "BM25 top 4 vs all 8", dev["h_b"]["retrieved"]),
                           ("h_c", "nonabstain-BM25 vs BM25 top 4",
                            (dev.get("h_c") or {}).get("retrieved"))):  # fmt: skip
        if not src:
            continue
        nd = src["discordant"]
        rate = nd / src["questions"]
        grid = {}
        thresholds: dict[int, int] = {}
        for r in sorted({rate, 0.02, 0.04, 0.0635, 0.1, 0.15}):
            grid[f"{r:.4f}"] = {
                f"{s:.2f}": mcnemar_power(n_questions, r, s, thresholds=thresholds)
                for s in (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0)
            }
        paired[key] = {
            "comparison": name,
            "development": {
                "b": src["rule_right_base_wrong"],
                "c": src["rule_wrong_base_right"],
                "questions": src["questions"],
                "discordance_rate": rate,
            },  # fmt: skip
            "power_by_rate_and_share": grid,
        }
    out["paired"] = paired
    return out


def cmd_power(args: argparse.Namespace) -> dict[str, Any]:
    check_development_path(args.analysis_dir)
    check_development_path(args.output)
    out = power(Path(args.analysis_dir), args.tables, args.questions, args.simulations,
                args.resamples, args.seed)  # fmt: skip
    Path(args.output).write_bytes(canonical(out))
    return {k: out["h_a"][k]["verdict_probability"] for k in out["h_a"]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("extract", help="host only: join, validate, write private features")
    ex.add_argument("--split", choices=sorted(SPLITS), required=True)
    ex.add_argument("--run-dir", required=True, help="the job's am1 directory")
    ex.add_argument("--evidence", required=True, help="the study artifact")
    ex.add_argument("--private-dir", required=True, help="host-only output directory")
    an = sub.add_parser("analyze", help="hypotheses and descriptive outputs")
    an.add_argument("--split", choices=sorted(SPLITS), required=True)
    an.add_argument("--features", default=None)
    an.add_argument("--output-dir", required=True)
    an.add_argument("--seeds", type=int, default=N_SEEDS)
    an.add_argument("--seed-base", type=int, default=SEED_BASE)
    an.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    an.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    st = sub.add_parser("selftest", help="development only: reproduce AM1b and AM1d")
    st.add_argument("--analysis-dir", required=True, help="the development dry run's output")
    st.add_argument("--features", default=None, help="this script's development features")
    st.add_argument("--am1d-features", default=None, help="AM1d's features-1411.json.gz")
    st.add_argument("--output", required=True)
    pw = sub.add_parser("power", help="development only: operating characteristics")
    pw.add_argument("--analysis-dir", required=True)
    pw.add_argument("--output", required=True)
    pw.add_argument("--tables", type=int, default=251)
    pw.add_argument("--questions", type=int, default=347)
    pw.add_argument("--simulations", type=int, default=POWER_SIMULATIONS)
    pw.add_argument("--resamples", type=int, default=POWER_RESAMPLES)
    pw.add_argument("--seed", type=int, default=POWER_SEED)
    args = parser.parse_args(argv)
    if lf.patterns_sha256() != lf.ABSTENTION_PATTERNS_SHA256:
        print("error: the abstention pattern list differs from AM1d's", file=sys.stderr)
        return 1
    commands = {"extract": cmd_extract, "analyze": cmd_analyze, "selftest": cmd_selftest,
                "power": cmd_power}  # fmt: skip
    try:
        result = commands[args.command](args)
    except (KeepsetError, lf.LabelFreeError, ms.StudyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
