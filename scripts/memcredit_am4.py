#!/usr/bin/env python3
"""AM4 (D119): a read cap K on the non-abstention stop rule. EXPLORATORY and POST HOC, CPU only.

``am3-nonabstain-generality-v1`` confirmed that keeping the best-BM25-ranked 4-subset whose reply
does not abstain beats BM25 top 4 on AM1's 347 held-out answerable questions, and measured what the
rule costs on LongMemEval-S's 30 abstention questions. The rule reads 4-subsets in BM25 order and
stops at the first reply that does not abstain. With a read cap K it reads at most the first K
4-subsets and keeps BM25 top 4 (always read first) when none of them answers. K = 70 is the
registered rule; K = 1 is BM25 top 4 itself.

This script recomputes the registered run's comparisons at every cap in ``CAPS``, from the
registered run's text-free features, with the registered code: the reading order and the stop rule
are ``memcredit_am3.bm25_order`` and ``memcredit_am3.nonabstain_bm25``, the per-pool records
``memcredit_am3g.table_record``, the paired comparison and the exact McNemar test
``memcredit_keepset_search.paired_reading`` (``mcnemar_exact``), the read summary
``memcredit_keepset_search.reads_summary``, and the natural-mix rate and break-even share
``memcredit_am3g.natural_mix``. Bootstrap settings are the registration's (10,000 resamples, seed
42). Only the cap is new.

The questions are the ones the rule was confirmed on, and K is examined after seeing them, so
nothing here is a finding: the output is the whole K curve, and a chosen K would need new questions.

Subcommands:

* ``analyze --heldout-features F1 --abstention-features F2 --hand-labels L --output-dir O`` (host
  CPU): checks every input against its registered digest, recomputes K = 70 and refuses to write
  anything unless it reproduces the registered analysis (``k70_check``), then writes text-free
  ``results.json`` and ``tables.md``.
* ``crosscheck --results R`` (anywhere, CPU): recomputes the judge-based counts, reads and
  natural-mix point estimates of every cap from the registered run's committed ``per-table.json.gz``
  (text-free), by a separate route, and compares them with ``results.json``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_am3 as am3  # noqa: E402  (the reading order and the stop rule)
import memcredit_am3g as g  # noqa: E402  (records, natural mix, hand plan, config)
import memcredit_keepset_search as ks  # noqa: E402  (paired readings, exact McNemar, reads)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am4-read-caps"
SOURCE = g.EXPERIMENT
CAPS: tuple[int, ...] = (1, 2, 4, 8, 16, 26, 70)
FULL_ORDER = len(g.FOUR_SETS)  # 70: the uncapped (registered) rule
READERS = g.H2_READERS  # qwen3-8b (anchor), OLMo-2, Qwen3.5-9B
JUDGES = g.JUDGES
ARMS = g.ARMS
#: The registered run's inputs (registration section 16 runbook; `logs/analyze-6384f294.log` and
#: `hand-check/` of its evidence directory).
REGISTERED_DIR = PROJECT_ROOT / "program" / "evidence" / "2026-10-15" / SOURCE
FEATURES_SHA256 = {
    "heldout": "ed417538177ba16c439a5ecde4d479f7cb97be9c04f7757ac9c7bb1773132ebe",
    "abstention": "4a18d2cf39b9ee135728bf91819527ce55c488185085b120b7bcf870f9efb464",
}
HAND_LABELS_SHA256 = "2ff9f35371595a24296222d35bec671a56a2f0d2c1f49022c611d970694a4408"
HAND_PLAN_SHA256 = "918468a493f8ae4fe43411fdd20322ffdc7afa75134f908609268e021d4cbfde"
REGISTERED_RESULTS_SHA256 = "d0ff289663e51d2f74736ab2d24b409d2730a9a7ca589c3d00d77b1c9c0028ac"
REGISTERED_PER_TABLE_SHA256 = "921c0ea00342d20b9c014ecfdc4940b9a56bbdaf3dc5f987a4c3930ff3bf6eb7"
#: The registered headline counts K = 70 must give (RESULTS.md): held-out retrieved arm, primary
#: judge, (b, c); abstention questions, primary judge, b2 (the cost).
REGISTERED_HEADLINE = {
    "heldout_b_c": {"qwen3-8b": (39, 0), "olmo-2-1124-7b-instruct": (35, 0), "qwen3.5-9b": (31, 0)},
    "abstention_b2": {"qwen3-8b": 5, "olmo-2-1124-7b-instruct": 8, "qwen3.5-9b": 1},
}
PAIRED_FIELDS = (
    "questions",
    "rule_accuracy",
    "base_accuracy",
    "rule_right_base_wrong",
    "rule_wrong_base_right",
    "discordant",
    "difference",
    "ci95_exact_conditional",
    "ci95_bootstrap",
    "p_exact_mcnemar",
)
COST_FIELDS = (
    "b2_top4_right_rule_wrong",
    "c2_rule_right_top4_wrong",
    "cost_rate",
    "cost_rate_ci95_exact",
    "net_loss_rate",
)
CLAIM = (
    "EXPLORATORY and POST HOC: the held-out and abstention questions are the ones the rule was "
    "confirmed on, and the cap is examined after seeing them. Nothing here is a finding or "
    "licenses a claim; no K is selected; a chosen K would need confirmation on new questions."
)


class Am4Error(ValueError):
    """An input differs from its registered digest, or K = 70 does not reproduce."""


# --------------------------------------------------------------------------- the capped rule


def capped_rule(pool: dict[str, Any], cap: int) -> dict[str, Any]:
    """The stop rule with at most ``cap`` reads: the registered rule's choice
    (``memcredit_am3.nonabstain_bm25``) when its first answering 4-subset is within the first
    ``cap`` of the BM25 order (``memcredit_am3.bm25_order``), else BM25 top 4, the order's first
    element. Reads: the answering position, or ``cap`` when none of the first ``cap`` answers
    (falling back costs no read: top 4's reply is the first read). At cap 70 this is the
    registered rule, choice and reads."""

    if not 1 <= int(cap) <= FULL_ORDER:
        raise Am4Error(f"the cap must be 1-{FULL_ORDER}, not {cap}")
    order = am3.bm25_order(pool["bm25_rank"])
    rule = am3.nonabstain_bm25(pool)
    position = rule["first_answer_position"]
    answered = position is not None and position <= cap
    out = {
        "mask": rule["mask"] if answered else order[0],
        "reads": position if answered else int(cap),
        "answered_within_cap": answered,
        "first_answer_position": position,
    }
    if cap == FULL_ORDER and (out["mask"], out["reads"]) != (rule["mask"], rule["reads"]):
        raise Am4Error("the cap of 70 differs from the registered rule")
    return out


def capped_records(
    pools: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]], cap: int
) -> list[dict[str, Any]]:
    """Per pool, the registered record (``memcredit_am3g.table_record``) with the rule replaced by
    the capped rule: ``u[judge]["nonabstain_bm25"]`` is the judge's label of the capped choice's
    reply, so the registered summaries (``natural_mix``, ``outcomes``) apply unchanged. Order is
    the features' pool order, which the bootstraps depend on."""

    out = []
    for pool, rec in zip(pools, records, strict=True):
        if (pool["question_id"], pool["arm"]) != (rec["question_id"], rec["arm"]):
            raise Am4Error("pools and records are not aligned")
        c = capped_rule(pool, cap)
        u: dict[str, Any] = {}
        for j in JUDGES:
            if rec["u"][j] is None:
                u[j] = None
                continue
            chosen = int(pool["masks"][c["mask"]]["u"][j])
            via_record = (rec["u"][j]["nonabstain_bm25"] if c["mask"] == rec["nonabstain_mask"]
                          else rec["u"][j]["bm25_top4"])  # fmt: skip
            if chosen != via_record or c["mask"] not in (rec["nonabstain_mask"],
                                                         rec["bm25_top4_mask"]):  # fmt: skip
                raise Am4Error("the capped choice is neither the rule's nor BM25 top 4's")
            u[j] = {"bm25_top4": int(rec["u"][j]["bm25_top4"]), "nonabstain_bm25": chosen}
        out.append({
            "question_id": rec["question_id"],
            "question_type": rec["question_type"],
            "arm": rec["arm"],
            "bm25_top4_mask": rec["bm25_top4_mask"],
            "nonabstain_mask": c["mask"],
            "first_answer_position": c["first_answer_position"],
            "reads": c["reads"],
            "cap_reached": not c["answered_within_cap"],
            "u": u,
        })  # fmt: skip
    return out


# --------------------------------------------------------------------------- summaries


def paired(rows: Sequence[dict[str, Any]], judge: str, resamples: int, seed: int) -> dict:
    """The capped rule against BM25 top 4 (``memcredit_keepset_search.paired_reading``: b, c, the
    exact McNemar p, exact conditional and bootstrap intervals), as a description: no label."""

    entry = ks.paired_reading(
        g.outcomes(rows, judge, "nonabstain_bm25"), g.outcomes(rows, judge, "bm25_top4"),
        ("-", "-", "-"), resamples, seed, alpha=g.ALPHA, label_key="label",
    )  # fmt: skip
    entry.pop("label")
    entry.pop("alpha")
    return entry


def population_block(
    rows: Sequence[dict[str, Any]], resamples: int, seed: int, unanswerable: bool
) -> dict[str, Any]:
    """One population and arm at one cap: per judge the paired comparison (and, for the
    unanswerable questions, the cost b2 with its exact interval, as ``h2_block`` reports it); the
    reads (``reads_summary``); how often the cap is reached without an answer; how often the rule
    leaves BM25 top 4."""

    block: dict[str, Any] = {
        "questions": len(rows),
        "reads": ks.reads_summary([r["reads"] for r in rows]),
        "cap_reached_without_answer": sum(r["cap_reached"] for r in rows),
        "rule_switches_from_top4": sum(r["nonabstain_mask"] != r["bm25_top4_mask"] for r in rows),
    }
    for j in JUDGES:
        if any(r["u"][j] is None for r in rows):
            block[j] = {"incomplete": True}
            continue
        e = paired(rows, j, resamples, seed)
        if unanswerable:
            n = e["questions"]
            b2, c2 = e["rule_wrong_base_right"], e["rule_right_base_wrong"]
            e.update({
                "b2_top4_right_rule_wrong": b2,
                "c2_rule_right_top4_wrong": c2,
                "cost_rate": b2 / n,
                "cost_rate_ci95_exact": g.cp_interval(b2, n),
                "net_loss_rate": (b2 - c2) / n,
            })  # fmt: skip
        block[j] = e
    return block


def hand_index(plan: dict[str, Any], labels: Sequence[dict[str, Any]]) -> dict[tuple, int]:
    """(population, reader, question, mask) -> the blind hand label, for every reply the
    registered plan sent to the labeller (``plan["items"][*]["uses"]``). Only ``item_id`` and
    ``label`` are read."""

    by_id = {row["item_id"]: int(row["label"]) for row in labels}
    out: dict[tuple, int] = {}
    for item in plan["items"]:
        for use in item["uses"]:
            key = (use["population"], use["reader"], item["question_id"], int(use["mask"]))
            out[key] = by_id[item["item_id"]]
    return out


def hand_at_cap(
    capped: Sequence[dict[str, Any]], population: str, reader: str, index: dict[tuple, int]
) -> dict[str, Any]:
    """The hand labels where they cover the capped rule's changed cells, retrieved arm:
    over the questions whose capped choice and BM25 top 4 the primary judge labels differently
    (the registration's hand-check definition; every such reply is in the plan, since a cap only
    removes switches), the hand-labelled counts; and over the switched questions the judge calls
    concordant whose two replies were both hand-labelled as distractors, how many the hand labels
    split, and which way."""

    rows = [r for r in capped if r["arm"] == "retrieved"]
    disc = right = wrong = extra = extra_right = extra_wrong = 0
    for r in rows:
        if r["nonabstain_mask"] == r["bm25_top4_mask"]:
            continue
        keys = [(population, reader, r["question_id"], r[m])
                for m in ("nonabstain_mask", "bm25_top4_mask")]  # fmt: skip
        judged = r["u"]["primary"]["nonabstain_bm25"] != r["u"]["primary"]["bm25_top4"]
        if judged and not all(k in index for k in keys):
            raise Am4Error(f"{population}:{reader}: a judge-discordant pair lacks a hand label")
        if not all(k in index for k in keys):
            continue
        h_rule, h_top = index[keys[0]], index[keys[1]]
        if judged:
            disc += 1
            right += int(h_rule == 1 and h_top == 0)
            wrong += int(h_rule == 0 and h_top == 1)
        else:
            extra += 1
            extra_right += int(h_rule == 1 and h_top == 0)
            extra_wrong += int(h_rule == 0 and h_top == 1)
    return {
        "judge_discordant_questions": disc,
        "hand_rule_right_top4_wrong": right,
        "hand_rule_wrong_top4_right": wrong,
        "judge_concordant_switched_pairs_hand_labelled": extra,
        "of_which_hand_rule_right_top4_wrong": extra_right,
        "of_which_hand_rule_wrong_top4_right": extra_wrong,
    }


def k_curve(
    pools_h: dict[str, list[dict[str, Any]]],
    rec_h: dict[str, list[dict[str, Any]]],
    pools_a: dict[str, list[dict[str, Any]]],
    rec_a: dict[str, list[dict[str, Any]]],
    weights: dict[str, int],
    resamples: int,
    seed: int,
    caps: Sequence[int] = CAPS,
    hand: dict[tuple, int] | None = None,
) -> dict[str, Any]:
    """Per reader and cap: the held-out questions (both arms) and the abstention questions, each
    judge; the natural-mix rate and break-even share (``memcredit_am3g.natural_mix``, both
    resampling schemes); and, with ``hand``, the hand labels where they cover the changed cells
    (held-out: the H1 readers; abstention: all three, as the registration labelled them)."""

    curve: dict[str, Any] = {}
    for reader in READERS:
        curve[reader] = {}
        for cap in caps:
            ch = capped_records(pools_h[reader], rec_h[reader], cap)
            ca = capped_records(pools_a[reader], rec_a[reader], cap)
            entry: dict[str, Any] = {
                "heldout": {arm: population_block([r for r in ch if r["arm"] == arm], resamples,
                                                  seed, unanswerable=False)
                            for arm in ARMS},
                "abstention": {"retrieved": population_block(
                    [r for r in ca if r["arm"] == "retrieved"], resamples, seed,
                    unanswerable=True)},
            }  # fmt: skip
            for name, linked in (("natural_mix", False), ("natural_mix_linked_twins", True)):
                entry[name] = {
                    j: g.natural_mix(ch, ca, weights, resamples, seed, judge=j, link_twins=linked)
                    for j in JUDGES
                    if all(x["u"][j] is not None for x in ch + ca)
                }
            if hand is not None:
                entry["hand"] = {}
                if reader in g.H1_READERS:
                    entry["hand"]["heldout"] = hand_at_cap(ch, "heldout", reader, hand)
                entry["hand"]["abstention"] = hand_at_cap(ca, "abstention", reader, hand)
            curve[reader][str(cap)] = entry
    return json.loads(json.dumps(curve))


# --------------------------------------------------------------------------- the K = 70 check


def k70_check(
    curve: dict[str, Any], registered: dict[str, Any], hand_check: dict[str, Any] | None = None
) -> dict[str, Any]:
    """K = 70 must reproduce the registered analysis exactly: the headline counts; per reader,
    judge and arm, every field of the registered rule-against-top-4 comparison and the stop rule's
    read summary; the abstention cost figures under both judges; the natural-mix summaries under
    both judges and both resampling schemes; and, with ``hand_check`` (the registered
    ``memcredit_am3g.hand_check`` recomputed on these inputs), the registered hand check itself and
    the hand-labelled counts at K = 70."""

    top = str(FULL_ORDER)
    d = registered["descriptive"]
    differences: list[str] = []
    compared = 0

    def same(name: str, got: Any, want: Any) -> None:
        nonlocal compared
        compared += 1
        if json.loads(json.dumps(got)) != want:
            differences.append(name)

    for reader in READERS:
        e = curve[reader][top]
        b_c = REGISTERED_HEADLINE["heldout_b_c"][reader]
        got = e["heldout"]["retrieved"]["primary"]
        same(f"headline.{reader}.b_c", (got["rule_right_base_wrong"],
                                        got["rule_wrong_base_right"]), list(b_c))  # fmt: skip
        same(f"headline.{reader}.b2",
             e["abstention"]["retrieved"]["primary"]["b2_top4_right_rule_wrong"],
             REGISTERED_HEADLINE["abstention_b2"][reader])  # fmt: skip
        for arm in ARMS:
            same(f"heldout.{reader}.{arm}.reads", e["heldout"][arm]["reads"],
                 d["cells_heldout"][reader]["primary"][arm]["stop_rule_reads"])  # fmt: skip
        same(
            f"abstention.{reader}.reads",
            e["abstention"]["retrieved"]["reads"],
            d["cells_abstention"][reader]["primary"]["retrieved"]["stop_rule_reads"],
        )
        for j in JUDGES:
            for arm in ARMS:
                want = d["cells_heldout"][reader][j][arm]["paired"]["nonabstain_bm25_vs_bm25_top4"]
                for f in PAIRED_FIELDS:
                    same(f"heldout.{reader}.{j}.{arm}.{f}", e["heldout"][arm][j][f], want[f])
            want = d["cells_abstention"][reader][j]["retrieved"]["paired"][
                "nonabstain_bm25_vs_bm25_top4"
            ]
            for f in PAIRED_FIELDS:
                same(f"abstention.{reader}.{j}.{f}", e["abstention"]["retrieved"][j][f], want[f])
            h2 = registered["h2"] if j == "primary" else d["second_judge_h2"]
            for f in COST_FIELDS:
                same(f"abstention.{reader}.{j}.{f}", e["abstention"]["retrieved"][j][f],
                     h2["readers"][reader][f])  # fmt: skip
            for name in ("natural_mix", "natural_mix_linked_twins"):
                same(f"{name}.{j}.{reader}", e[name][j], d[name][j][reader])
    if hand_check is not None:
        same("hand_check.recomputed", hand_check, registered["h1_hand_check"])
        reg = registered["h1_hand_check"]
        for reader in g.H1_READERS:
            got = curve[reader][top]["hand"]["heldout"]
            want = reg["readers"][reader]
            same(f"hand.heldout.{reader}", [got["judge_discordant_questions"],
                 got["hand_rule_right_top4_wrong"], got["hand_rule_wrong_top4_right"]],
                 [want["discordant_questions"], want["b_hand"], want["c_hand"]])  # fmt: skip
        for reader in READERS:
            got = curve[reader][top]["hand"]["abstention"]
            want = reg["h2_descriptive"]["readers"][reader]
            same(f"hand.abstention.{reader}", [got["judge_discordant_questions"],
                 got["hand_rule_wrong_top4_right"], got["hand_rule_right_top4_wrong"]],
                 [want["discordant_questions"], want["b2_hand"], want["c2_hand"]])  # fmt: skip
    return {"pass": not differences, "compared": compared, "differences": differences}


# --------------------------------------------------------------------------- analyze


def analyze(
    heldout: dict[str, Any],
    abstention: dict[str, Any],
    config: dict[str, Any],
    registered: dict[str, Any],
    labels: Sequence[dict[str, Any]] | None = None,
    labels_sha256: str | None = None,
    hand_plan_sha256: str | None = HAND_PLAN_SHA256,
    caps: Sequence[int] = CAPS,
    check_provenance: bool = True,
) -> dict[str, Any]:
    """The K curve and the K = 70 check. The features' provenance is checked with the registered
    ``check_features`` (pins and code digests); the hand plan is the registered ``hand_plan``,
    whose digest must equal the receipted one; the hand labels join through the registered
    ``hand_check``. Raises unless K = 70 reproduces."""

    if FULL_ORDER not in caps:
        raise Am4Error("the caps must include 70, the registered rule, for the check")
    spec = config["analysis"]
    resamples, seed = int(spec["bootstrap"]["resamples"]), int(spec["bootstrap"]["seed"])
    weights = dict(spec["natural_mix"])
    if check_provenance:
        g.check_features(heldout, config, "heldout")
        g.check_features(abstention, config, "abstention")
    g.int_masks(heldout)
    g.int_masks(abstention)
    rec_h, rec_a = g.records_of(heldout), g.records_of(abstention)
    pools_h = {r: d["pools"] for r, d in heldout["readers"].items()}
    pools_a = {r: d["pools"] for r, d in abstention["readers"].items()}
    index = hand = None
    if labels is not None:
        plan = g.hand_plan(heldout, abstention)
        if hand_plan_sha256 is not None and plan["plan_sha256"] != hand_plan_sha256:
            raise Am4Error("the hand plan these features give differs from the receipted plan")
        hand = g.hand_check(heldout, plan, list(labels), labels_sha256, g.ALPHA)
        if hand["status"] != "joined":
            raise Am4Error(f"the hand labels do not cover the plan: {hand['status']}")
        index = hand_index(plan, labels)
    curve = k_curve(pools_h, rec_h, pools_a, rec_a, weights, resamples, seed, caps, index)
    check = k70_check(curve, registered, hand)
    if not check["pass"]:
        raise Am4Error(f"K = 70 does not reproduce the registered analysis: "
                       f"{check['differences'][:20]}")  # fmt: skip
    return {
        "experiment": EXPERIMENT,
        "claim_level": "exploratory, post hoc",
        "claim": CLAIM,
        "source": {"registration": SOURCE, "freeze_commit": "6384f294", "decision": "D119"},
        "config": {
            "caps": list(caps),
            "rule": "read 4-subsets in BM25 order (memcredit_am3.bm25_order) and keep the first "
            "whose reply does not abstain among the first K; keep BM25 top 4 when none of them "
            "answers; reads: the answering position, or K",
            "bootstrap_resamples": resamples,
            "bootstrap_seed": seed,
            "natural_mix_weights": weights,
            "populations": {"answerable": "AM1's 347 held-out questions",
                            "unanswerable": "LongMemEval-S's 30 abstention questions"},
            "p_values": "exact two-sided McNemar, unadjusted, descriptive",
        },  # fmt: skip
        "k70_check": check,
        "hand_labels": None if hand is None else {
            "labels_sha256": hand["labels_sha256"], "plan_sha256": hand["plan_sha256"],
            "items": hand["items"], "labeller": hand["labeller"],
            "coverage": "held-out: OLMo-2 and Qwen3.5-9B; abstention: all three readers "
            "(the registration did not hand-label the anchor's held-out replies)"},
        "curve": curve,
    }  # fmt: skip


# --------------------------------------------------------------------------- tables


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _p(x: float | None) -> str:
    return g._p(x)


def _ci(ci: Sequence[float | None] | None, signed: bool = False) -> str:
    return g._ci(ci, signed)


def render_markdown(results: dict[str, Any]) -> str:
    curve, caps = results["curve"], results["config"]["caps"]
    w = results["config"]["natural_mix_weights"]
    mix = f"{w['answerable']}:{w['abstention']}"
    lines = [
        "# AM4 read caps: tables (EXPLORATORY, POST HOC)", "",
        "Generated by `scripts/memcredit_am4.py analyze` from the registered features of "
        f"`{SOURCE}`. The questions are the ones the rule was confirmed on, and K is examined "
        "after seeing them: nothing here is a finding, and no K is selected.", "",
        "- K: at most K 4-subsets read in BM25 order; BM25 top 4 kept when none of them answers. "
        "K = 1 is BM25 top 4; K = 70 is the registered rule.",
        "- b: the capped rule right, BM25 top 4 wrong; c: the reverse (347 held-out answerable "
        "questions). b2: BM25 top 4 right (a correct abstention), the capped rule wrong; c2: the "
        "reverse (30 abstention questions). p: exact two-sided McNemar, unadjusted, descriptive.",
        f"- Net rate: at LongMemEval-S's mix of {mix} answerable to unanswerable questions. "
        "Break-even: the unanswerable share above which BM25 top 4 is ahead (1 when the rule "
        "never loses). Intervals: 95% percentile bootstrap, each population resampled "
        "separately (registration section 6.4).",
        f"- K = 70 check: {'pass' if results['k70_check']['pass'] else 'FAIL'}, "
        f"{results['k70_check']['compared']} registered figures reproduced exactly.", "",
    ]  # fmt: skip
    for j, judge in (("primary", "Qwen3-32B"), ("secondary", "Qwen3-8B")):
        lines += [
            f"## Retrieved arm, {judge} judge"
            + (" (primary)" if j == "primary" else " (second judge, descriptive)"),
            "",
        ]
        for reader in READERS:
            lines += [f"### {reader}", "",
                      "| K | b | c | difference [95% bootstrap] | p | b2 | c2 | cost rate [exact "
                      "95%] | mean reads, answerable | mean reads, unanswerable | net rate "
                      f"at {mix} [95%] | break-even share [95%] |",
                      "|---:|---:|---:|---|---:|---:|---:|---|---:|---:|---|---|"]  # fmt: skip
            for cap in caps:
                e = curve[reader][str(cap)]
                h, a = e["heldout"]["retrieved"], e["abstention"]["retrieved"]
                hj, aj = h[j], a[j]
                m = e["natural_mix"].get(j)
                if hj.get("incomplete") or aj.get("incomplete") or m is None:
                    lines.append(f"| {cap} | incomplete |||||||||||")
                    continue
                lines.append(
                    f"| {cap} | {hj['rule_right_base_wrong']} | {hj['rule_wrong_base_right']} | "
                    f"{hj['difference']:+.3f} {_ci(hj['ci95_bootstrap'], True)} | "
                    f"{_p(hj['p_exact_mcnemar'])} | {aj['b2_top4_right_rule_wrong']} | "
                    f"{aj['c2_rule_right_top4_wrong']} | {_f(aj['cost_rate'])} "
                    f"{_ci(aj['cost_rate_ci95_exact'])} | {_f(h['reads']['mean'], 2)} | "
                    f"{_f(a['reads']['mean'], 2)} | {m['mix_rate']:+.3f} "
                    f"{_ci(m['mix_rate_ci95'], True)} | "
                    f"{_f(m['break_even_unanswerable_share'])} {_ci(m['break_even_ci95'])} |"
                )
            lines.append("")
    lines += ["## Reads", "",
              "Reads per pool: the answering position, or K when none of the first K answers "
              "(\"cap reached\"). Retrieved arm.", "",
              "| Reader | K | answerable: mean | median | 90th pct | cap reached (of 347) | "
              "unanswerable: mean | median | cap reached (of 30) |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for reader in READERS:
        for cap in caps:
            e = curve[reader][str(cap)]
            h, a = e["heldout"]["retrieved"], e["abstention"]["retrieved"]
            lines.append(
                f"| {reader} | {cap} | {_f(h['reads']['mean'], 2)} | "
                f"{_f(h['reads']['median'], 0)} | {h['reads']['p90']} | "
                f"{h['cap_reached_without_answer']} | {_f(a['reads']['mean'], 2)} | "
                f"{_f(a['reads']['median'], 0)} | {a['cap_reached_without_answer']} |"
            )
    lines += ["", "## Gold arm, held-out answerable questions (descriptive)", "",
              "| Reader | K | b, c (Qwen3-32B) | p | b, c (Qwen3-8B) | p | mean reads |",
              "|---|---:|---|---:|---|---:|---:|"]  # fmt: skip
    for reader in READERS:
        for cap in caps:
            gold = curve[reader][str(cap)]["heldout"]["gold"]
            cells = []
            for j in JUDGES:
                e = gold[j]
                cells.append("incomplete | " if e.get("incomplete") else
                             f"{e['rule_right_base_wrong']}, {e['rule_wrong_base_right']} | "
                             f"{_p(e['p_exact_mcnemar'])}")  # fmt: skip
            lines.append(f"| {reader} | {cap} | {cells[0]} | {cells[1]} | "
                         f"{_f(gold['reads']['mean'], 2)} |")  # fmt: skip
    if "hand" in curve[READERS[0]][str(caps[0])]:
        lines += ["", "## Blind hand labels where they cover the changed cells (agent labels, D9)",
                  "",
                  "Over the questions the primary judge splits at that K, the hand-labelled "
                  "counts: held-out (rule right, top 4 wrong; reverse) and abstention (b2: top 4 "
                  "right, rule wrong; c2: reverse). Extra: switched questions the judge calls "
                  "concordant whose two replies were both hand-labelled as distractors, and how "
                  "many of them the hand labels split (rule right, top 4 right). The anchor's "
                  "held-out replies were not hand-labelled.", "",
                  "| Population | Reader | K | judge-split questions | hand: rule right, top 4 "
                  "wrong | hand: rule wrong, top 4 right | extra pairs | hand-split extra "
                  "pairs |",
                  "|---|---|---:|---:|---:|---:|---:|---|"]  # fmt: skip
        for population in ("heldout", "abstention"):
            for reader in READERS:
                for cap in caps:
                    hd = curve[reader][str(cap)]["hand"].get(population)
                    if hd is None:
                        continue
                    lines.append(
                        f"| {population} | {reader} | {cap} | {hd['judge_discordant_questions']} "
                        f"| {hd['hand_rule_right_top4_wrong']} | "
                        f"{hd['hand_rule_wrong_top4_right']} | "
                        f"{hd['judge_concordant_switched_pairs_hand_labelled']} | "
                        f"{hd['of_which_hand_rule_right_top4_wrong']}, "
                        f"{hd['of_which_hand_rule_wrong_top4_right']} |"
                    )
    k = results["k70_check"]
    lines += ["", "## K = 70 check", "",
              f"- {k['compared']} registered figures compared (headline counts; every field of the "
              "rule-against-top-4 comparison per reader, judge and arm; read summaries; abstention "
              "cost figures; natural-mix summaries under both judges and both resampling schemes; "
              "the hand check); differences: "
              f"{len(k['differences'])}. Pass: {k['pass']}."]  # fmt: skip
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- crosscheck


def crosscheck(
    per_table: Sequence[dict[str, Any]], results: dict[str, Any], tolerance: float = 1e-12
) -> dict[str, Any]:
    """A second route to the judge-based figures, from the registered per-table records (no
    features, no stop-rule code): at cap K a pool's outcome is the registered rule's when its
    ``first_answer_position`` is at most K, else BM25 top 4's, and its reads are that position or
    K. Compares b, c (both judges, both arms), b2, c2, the cap counts, the mean reads and the
    natural-mix point estimates (rate and break-even share) with ``results``."""

    caps = results["config"]["caps"]
    w = results["config"]["natural_mix_weights"]
    wa = w["answerable"] / (w["answerable"] + w["abstention"])
    differences: list[str] = []
    compared = 0

    def same(name: str, got: Any, want: Any) -> None:
        nonlocal compared
        compared += 1
        ok = (math.isclose(got, want, rel_tol=0.0, abs_tol=tolerance)
              if isinstance(got, float) or isinstance(want, float) else got == want)  # fmt: skip
        if not ok:
            differences.append(name)

    for reader in READERS:
        for cap in caps:
            e = results["curve"][reader][str(cap)]
            nets: dict[str, dict[str, float]] = {j: {} for j in JUDGES}
            for population, arm in (("heldout", "retrieved"), ("heldout", "gold"),
                                    ("abstention", "retrieved")):  # fmt: skip
                rows = [r for r in per_table if r["population"] == population
                        and r["reader"] == reader and r["arm"] == arm]  # fmt: skip
                within = [r["first_answer_position"] is not None
                          and r["first_answer_position"] <= cap for r in rows]  # fmt: skip
                reads = [r["first_answer_position"] if w_ else cap
                         for r, w_ in zip(rows, within, strict=True)]  # fmt: skip
                block = e[population][arm]
                same(
                    f"{reader}.{cap}.{population}.{arm}.cap_reached",
                    sum(not x for x in within),
                    block["cap_reached_without_answer"],
                )
                same(
                    f"{reader}.{cap}.{population}.{arm}.mean_reads",
                    sum(reads) / len(reads),
                    block["reads"]["mean"],
                )
                for j in JUDGES:
                    if block[j].get("incomplete"):
                        continue
                    rule = [r["u"][j]["nonabstain_bm25"] if w_ else r["u"][j]["bm25_top4"]
                            for r, w_ in zip(rows, within, strict=True)]  # fmt: skip
                    top = [r["u"][j]["bm25_top4"] for r in rows]
                    b = sum(1 for x, t in zip(rule, top, strict=True) if x == 1 and t == 0)
                    c = sum(1 for x, t in zip(rule, top, strict=True) if x == 0 and t == 1)
                    same(
                        f"{reader}.{cap}.{population}.{arm}.{j}.b",
                        b,
                        block[j]["rule_right_base_wrong"],
                    )
                    same(
                        f"{reader}.{cap}.{population}.{arm}.{j}.c",
                        c,
                        block[j]["rule_wrong_base_right"],
                    )
                    if arm == "retrieved":
                        nets[j][population] = (b - c) / len(rows)
            for j in JUDGES:
                m = e["natural_mix"].get(j)
                if m is None:
                    continue
                gain, loss = nets[j]["heldout"], -nets[j]["abstention"]
                same(f"{reader}.{cap}.{j}.mix_rate", wa * gain - (1 - wa) * loss, m["mix_rate"])
                be = g.break_even(gain, loss)
                want = m["break_even_unanswerable_share"]
                if be is None or want is None:
                    same(f"{reader}.{cap}.{j}.break_even_defined", be is None, want is None)
                else:
                    same(f"{reader}.{cap}.{j}.break_even", be, want)
    return {"pass": not differences, "compared": compared, "differences": differences[:50]}


# --------------------------------------------------------------------------- CLI


def _digest_checked(path: Path, expected: str, what: str) -> Path:
    actual = g.sha256_file(path)
    if actual != expected:
        raise Am4Error(f"{what} ({path.name}) differs from its registered SHA-256: {actual}")
    return path


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    out = Path(args.output_dir)
    if out.exists():
        raise Am4Error(f"{out} exists: analyze writes a new output directory")
    registered_path = _digest_checked(Path(args.registered_results), REGISTERED_RESULTS_SHA256,
                                      "the registered results")  # fmt: skip
    registered = json.loads(registered_path.read_text(encoding="utf-8"))
    heldout = g.read_gz_json(
        _digest_checked(
            Path(args.heldout_features), FEATURES_SHA256["heldout"], "the held-out features"
        )
    )
    abstention = g.read_gz_json(_digest_checked(Path(args.abstention_features),
                                                FEATURES_SHA256["abstention"],
                                                "the abstention features"))  # fmt: skip
    labels, digest = g.read_hand_labels(Path(args.hand_labels), HAND_LABELS_SHA256)
    config = g.load_config()
    results = analyze(heldout, abstention, config, registered, labels, digest)
    results["inputs"] = {
        "features_sha256": dict(FEATURES_SHA256),
        "hand_labels_sha256": HAND_LABELS_SHA256,
        "hand_plan_sha256": HAND_PLAN_SHA256,
        "registered_results_sha256": REGISTERED_RESULTS_SHA256,
        "code_sha256": {p: g.sha256_file(PROJECT_ROOT / p)
                        for p in ("scripts/memcredit_am4.py", *g.FEATURE_CODE)},
    }  # fmt: skip
    out.mkdir(parents=True)
    lane.write_json(out / "results.json", results)
    (out / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return {"k70_check": results["k70_check"]["pass"],
            **{f: g.sha256_file(out / f) for f in ("results.json", "tables.md")}}  # fmt: skip


def cmd_crosscheck(args: argparse.Namespace) -> dict[str, Any]:
    path = _digest_checked(Path(args.per_table), REGISTERED_PER_TABLE_SHA256,
                           "the registered per-table records")  # fmt: skip
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        per_table = json.load(fh)
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    report = crosscheck(per_table, results)
    if not report["pass"]:
        raise Am4Error(f"the per-table route differs: {report['differences']}")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze", allow_abbrev=False)
    a.add_argument("--heldout-features", required=True)
    a.add_argument("--abstention-features", required=True)
    a.add_argument("--hand-labels", required=True)
    a.add_argument("--registered-results", default=str(REGISTERED_DIR / "results.json"))
    a.add_argument("--output-dir", required=True)
    c = sub.add_parser("crosscheck", allow_abbrev=False)
    c.add_argument("--per-table", default=str(REGISTERED_DIR / "per-table.json.gz"))
    c.add_argument("--results", required=True)
    args = parser.parse_args(argv)
    commands = {"analyze": cmd_analyze, "crosscheck": cmd_crosscheck}
    try:
        print(json.dumps(commands[args.command](args), indent=2, sort_keys=True))
    except (Am4Error, g.Am3gError, am3.Am3Error, ks.KeepsetError, ms.StudyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
