"""Aggregates of the D81 run-2 adjudication of q2-evaluator-mutation-v1 (no decision).

Adjudicated by an isolated model on the owner's instruction (D80); not
human-validated.

Reads only committed files: the run-2 answers and isolation records here, the
released sample, the pre-adjudication audit summary, decisions, pool and
spot-check list (2026-10-08), the K2 rerun analysis (2026-10-11, the
pre-adjudication analysis), and the post-adjudication audit summaries and
analyses here (primary (a) and the two D81 sensitivities). Writes
summary.json: answer counts, the isolation outcome, image coverage, what each
pool answer did, the agreement tables ((a) against (b), (a) and (b) against
each model rater, the spot check against the raters' consensus by stratum)
and the before/after of every reported output. Standard library only; run
from the repository root:

    python program/evidence/2026-10-11/q2-mutation-adjudication-v2/summarize_adjudication_v2.py
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

LABEL = "adjudicated by an isolated model on the owner's instruction (D80); not human-validated"
HERE = Path("program/evidence/2026-10-11/q2-mutation-adjudication-v2")
CONF = Path("program/evidence/2026-10-08/q2-mutation-confirm")
K2 = Path("program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186")
ANSWERS = ("accept", "reject", "unsure")


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def js(path: Path):
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over the answer categories (unweighted)."""
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def table(pairs: list[tuple[str, str]], names: tuple[str, str]) -> dict:
    cells = collections.Counter(f"{names[0]}={a} / {names[1]}={b}" for a, b in pairs)
    both = [(a, b) for a, b in pairs if a in ("accept", "reject") and b in ("accept", "reject")]
    return {
        "items": len(pairs),
        "cells": dict(sorted(cells.items())),
        "agree": sum(a == b for a, b in pairs),
        "agree_share": round(sum(a == b for a, b in pairs) / len(pairs), 4) if pairs else None,
        "both_accept_or_reject": len(both),
        "agree_where_both_accept_or_reject": sum(a == b for a, b in both),
        "cohen_kappa_all_categories": None if kappa(pairs) is None else round(kappa(pairs), 4),
        "cohen_kappa_accept_reject_only": None if kappa(both) is None else round(kappa(both), 4),
    }


def get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def main() -> int:
    sample = {r["item_id"]: r for r in jl(CONF / "audit/released/confirm-audit-v1/sample.jsonl")}
    pre_dec = {r["key"]: r for r in jl(CONF / "audit/audit-summary/decisions.jsonl")}
    pool = [r["item_id"] for r in jl(CONF / "audit/audit-summary/adjudication-pool.jsonl")]
    spot = [r["item_id"] for r in jl(CONF / "audit/released/confirm-audit-v1/spot-check.jsonl")]
    items = sorted(set(pool) | set(spot))

    # Answers. (a): the registered ingest (calls.jsonl; a void would be unsure).
    calls_a = {r["item_id"]: r for r in jl(HERE / "isolation/a/calls.jsonl")}
    a = {i: calls_a[i]["answer"] for i in items}
    run_b = js(HERE / "isolation/b/audit_runs.json")
    run_c = js(HERE / "isolation/c/audit_runs.json")
    b_given = {r["item_id"]: r["answer_given"] for r in run_b["items"]}
    b_strict = {r["item_id"]: r["answer"] for r in run_b["items"]}
    c_ans = {r["item_id"]: r["answer"] for r in run_c["items"]}
    adj = {r["item_id"]: r["answer"] for r in jl(HERE / "adjudications.jsonl")}
    spot_ans = {r["item_id"]: r["answer"] for r in jl(HERE / "spot-check-answers.jsonl")}
    assert set(calls_a) == set(items) and set(b_given) == set(items)
    assert list(adj) == [i for i in pool if a[i] in ("accept", "reject")], "pool order"
    assert list(spot_ans) == [i for i in spot if a[i] in ("accept", "reject")], "spot order"
    assert all(adj[i] == a[i] for i in adj) and all(spot_ans[i] == a[i] for i in spot_ans)

    def stratum(i: str) -> str:
        s = sample[i]
        return f"sham_{s['sham']}" if s["sham"] else s["stratum"]

    def raters(i: str) -> tuple[str, str, str]:
        d = pre_dec[sample[i]["mutant_id"]]
        return d["first"], d["second"], d["decision"]

    def reason(i: str) -> str:
        if raters(i)[2] == "unresolved":
            return "gold_sham_split" if sample[i]["sham"] == "gold" else "split"
        return "concordant_contradicts_label"

    # Pool: what each answer did, by pool reason and stratum, for (a) and (b).
    def pool_effect(ans: dict) -> dict:
        out = collections.defaultdict(collections.Counter)
        for i in pool:
            first, second, decision = raters(i)
            key = f"{reason(i)} / {stratum(i)} / raters anthropic={first}, open_weight={second}"
            x = ans[i]
            if x not in ("accept", "reject"):
                out[key][f"{x}: left out, stays {'unresolved' if decision == 'unresolved' else 'the consensus'}"] += 1
            elif decision != "unresolved":
                out[key]["upholds the consensus" if x == decision else "overturns the consensus"] += 1
            else:
                sides = [n for n, r in (("anthropic", first), ("open_weight", second)) if r == x]
                out[key][f"{x} (sides with {'+'.join(sides) or 'neither'})"] += 1
        return {k: dict(v) for k, v in sorted(out.items())}

    splits28 = [i for i in pool if reason(i) != "concordant_contradicts_label"]
    assert len(splits28) == 28

    # Agreement tables.
    agreement = {
        "a_vs_b_all_52": table([(a[i], b_given[i]) for i in items], ("a", "b")),
        "a_vs_b_28_pool_splits": table([(a[i], b_given[i]) for i in splits28], ("a", "b")),
        "a_vs_b_6_concordant_contradictions": table(
            [(a[i], b_given[i]) for i in pool if reason(i) == "concordant_contradicts_label"], ("a", "b")),
        "a_vs_b_25_spot_check": table([(a[i], b_given[i]) for i in spot], ("a", "b")),
        "a_vs_anthropic_rater_all_52": table([(a[i], raters(i)[0]) for i in items], ("a", "anthropic")),
        "a_vs_open_weight_rater_all_52": table([(a[i], raters(i)[1]) for i in items], ("a", "open_weight")),
        "b_vs_anthropic_rater_all_52": table([(b_given[i], raters(i)[0]) for i in items], ("b", "anthropic")),
        "b_vs_open_weight_rater_all_52": table([(b_given[i], raters(i)[1]) for i in items], ("b", "open_weight")),
        "a_vs_anthropic_rater_28_pool_splits": table([(a[i], raters(i)[0]) for i in splits28], ("a", "anthropic")),
        "a_vs_open_weight_rater_28_pool_splits": table([(a[i], raters(i)[1]) for i in splits28], ("a", "open_weight")),
        "b_vs_anthropic_rater_28_pool_splits": table([(b_given[i], raters(i)[0]) for i in splits28], ("b", "anthropic")),
        "b_vs_open_weight_rater_28_pool_splits": table([(b_given[i], raters(i)[1]) for i in splits28], ("b", "open_weight")),
        "anthropic_vs_open_weight_rater_all_52": table([(raters(i)[0], raters(i)[1]) for i in items],
                                                      ("anthropic", "open_weight")),
        "a_vs_c_12_marker_items": table([(a[i], c_ans[i]) for i in sorted(c_ans)], ("a", "c")),
        "a_vs_b_disagreements": [
            {"item_id": i, "stratum": stratum(i), "in_pool": i in pool, "pool_reason": reason(i) if i in pool else None,
             "in_spot_check": i in spot, "raters": {"anthropic": raters(i)[0], "open_weight": raters(i)[1]},
             "a": a[i], "b": b_given[i]}
            for i in items if a[i] != b_given[i]
        ],
    }

    # Spot check: the adjudicator against the model raters' consensus by stratum.
    expected = {"should_pass_equiv": "accept", "should_pass_alt_solution": "accept",
                "should_fail_violation": "reject", "should_fail_extra_change": "reject"}

    def spot_table(ans: dict) -> dict:
        rows = {}
        for st in ("alt_gate", "fn_equiv", "fp_violation", "sham_gold", "sham_do_nothing"):
            ids = [i for i in spot if stratum(i) == st]
            r = collections.Counter()
            for i in ids:
                first, second, decision = raters(i)
                x = ans[i]
                truth = {"sham_gold": "accept", "sham_do_nothing": "reject"}.get(st) or expected[sample[i]["label"]]
                r["items"] += 1
                r[f"answer_{x}"] += 1
                r["agrees_with_label_or_sham_truth"] += x == truth
                if decision == "unresolved":
                    r["raters_split"] += 1
                else:
                    r["raters_concordant"] += 1
                    r["agrees_with_concordant_raters"] += x == decision
                r["agrees_with_anthropic_rater"] += x == first
                r["agrees_with_open_weight_rater"] += x == second
            rows[st] = dict(sorted(r.items()))
        total = collections.Counter()
        for v in rows.values():
            total.update(v)
        rows["all_25"] = dict(sorted(total.items()))
        return rows

    def spot_disagreements(ans: dict) -> list[dict]:
        return [
            {"item_id": i, "stratum": stratum(i), "raters_consensus": raters(i)[2], "adjudicator": ans[i]}
            for i in spot if raters(i)[2] != "unresolved" and ans[i] != raters(i)[2]
        ]

    # Before (the K2 rerun, pre-adjudication) and after.
    pre_an = js(K2 / "analysis-with-k2/analysis.json")
    post_an = js(HERE / "analysis/analysis.json")
    pre_sum = js(CONF / "audit/audit-summary/audit-summary.json")
    post_sum = js(HERE / "audit-summary/audit-summary.json")
    sens = {v: {"analysis": js(HERE / f"sensitivity/{v}/analysis/analysis.json"),
                "summary": js(HERE / f"sensitivity/{v}/audit-summary/audit-summary.json")}
            for v in ("b-fable", "c-notation")}

    def fn(an):
        c = an["checker_candidates"]["false_negative"]
        return {"by_audit_reading": c["counts"]["by_audit_reading"],
                "on_gold_defect_tasks": c["counts"].get("gold_defect_tasks"),
                "audit_by_family": c["counts"]["audit"]["by_family"],
                "confirmed_share_pooled": c["confirmed_share"]["pooled"],
                "confirmed_share_compare_pptx_files": c["confirmed_share"]["by_family"]["compare_pptx_files"],
                "confirmed_share_zorder_nonoverlap": c["confirmed_share"]["by_operator"]["pptx.eq.zorder_nonoverlap"],
                "candidate_share_pooled": c["candidate_share"]["pooled"]}

    def fp(an):
        c = an["checker_candidates"]["false_positive"]
        return {"by_audit_reading": c["counts"]["by_audit_reading"],
                "events": [{k: e.get(k) for k in ("mutant_id", "family", "audit_decision", "audit_reading",
                                                   "gold_defect_task")} for e in c["events"]],
                "confirmed_share_pooled": c["confirmed_share"]["pooled"],
                "candidate_share_pooled": c["candidate_share"]["pooled"]}

    def p2(an):
        return {"pooled": an["P2"]["pooled"],
                "compare_pptx_files": an["P2"]["by_family"]["compare_pptx_files"],
                "compare_table": an["P2"]["by_family"]["compare_table"],
                "alt_gate": an["audit_gate"]["P2_alt_decisions"],
                "gold_defect_tasks": an["gold_defects"]["tasks"],
                "without_gold_defect_equivalence": None if an["gold_defects"].get(
                    "P2_without_their_equivalence_mutants") is None else {
                    "pooled": an["gold_defects"]["P2_without_their_equivalence_mutants"]["pooled"],
                    "compare_pptx_files": an["gold_defects"]["P2_without_their_equivalence_mutants"]["by_family"][
                        "compare_pptx_files"],
                    "compare_table": an["gold_defects"]["P2_without_their_equivalence_mutants"]["by_family"][
                        "compare_table"]}}

    def audit_stats(s):
        return {"kappa": s["kappa"], "kappa_fires": s["kappa_fires"],
                "k3": {g: {k: v[k] for k in ("estimate", "upper", "n_items", "n_tasks", "sufficient")}
                       for g, v in s["k3"].items()},
                "k3_fires": s["k3_fires"], "k4_fires": s["k4_fires"],
                "label_error": {g: {k: v[k] for k in ("estimate", "low", "high", "n_units", "n_clusters")}
                                for g, v in s["label_error"].items()},
                "label_error_resolved_only": {g: v["estimate"] for g, v in s["label_error_resolved_only"].items()},
                "label_error_unresolved_as_wrong": s["label_error_unresolved_as_wrong"],
                "by_label_class": s["by_label_class"], "adjudication": s["adjudication"],
                "gold_defect_tasks": s["gold_defects"]["tasks"],
                "gold_shams": {k: v for k, v in s["sham_decisions"].items() if k.endswith("__sham_gold")
                               and v != "accept"},
                "p1_flips": s["p1_flips"], "sham_accuracy": s["sham_accuracy"],
                "n_unresolved_rater_splits": s["n_unresolved"],
                "human_spot_check_field_as_the_frozen_tool_writes_it": s["human_spot_check"]}

    def outputs(an, s):
        return {"false_negative": fn(an), "false_positive": fp(an), "P2": p2(an), "audit": audit_stats(s),
                "K4_fires": an["K4"]["fires"], "metrics_leaving_headline": an["exclusions"]["metrics_leaving_headline"],
                "K6b": an["K6b"]["families"], "K7": an["K7"]["families"]}

    unchanged_keys = ("P1", "P3", "P4", "P5", "K1", "K5", "K6", "K9", "population", "primary_dep_set",
                      "metrics_role", "protocol", "descriptive_outputs")
    unchanged = {k: pre_an.get(k) == post_an.get(k) for k in unchanged_keys}
    unchanged["false_negative_candidate_share"] = (
        pre_an["checker_candidates"]["false_negative"]["candidate_share"]
        == post_an["checker_candidates"]["false_negative"]["candidate_share"])
    unchanged["false_positive_all"] = (pre_an["checker_candidates"]["false_positive"]
                                       == post_an["checker_candidates"]["false_positive"])
    unchanged["P2_rate_and_events_pooled"] = (
        {k: pre_an["P2"]["pooled"][k] for k in ("rate", "low", "high", "tasks")}
        == {k: post_an["P2"]["pooled"][k] for k in ("rate", "low", "high", "tasks")})
    unchanged["kappa"] = pre_sum["kappa"] == post_sum["kappa"]
    unchanged["p1_flip_decisions"] = pre_sum["p1_flips"] == post_sum["p1_flips"]
    unchanged["violation_k3_group"] = pre_sum["k3"]["should_fail_violation"] == post_sum["k3"]["should_fail_violation"]

    isolation = {
        "a_registered_ingest": {k: js(HERE / "isolation/a/ingest-stdout.json")[k] for k in (
            "outcomes", "answers", "models_returned", "void", "void_reasons", "relay_frames",
            "transcripts", "transcripts_answering", "attachment_types", "rated")},
        "a_collector": {k: js(HERE / "isolation/a/collect-stdout.json")[k] for k in (
            "transcripts", "answered", "items")},
        "b_equivalent_audit": {k: run_b[k] for k in ("outcomes", "models", "tool_calls", "refusals",
                                                    "unregistered_attachment_types", "relay_frames")},
        "b_void_reasons_other_than_the_unregistered_attachment": sorted({
            r for it in run_b["items"] for r in it["void_reasons"]
            if not r.startswith("attachment 'batching_reminder_sent'")}),
        "c_equivalent_audit": {k: run_c[k] for k in ("outcomes", "models", "tool_calls", "refusals",
                                                    "unregistered_attachment_types", "relay_frames")},
    }
    run_a_eq = js(HERE / "isolation/a/audit_runs-equivalence-check.json")
    reg = js(HERE / "isolation/validation/audit_runs-on-2026-10-08-rating.json")
    reg_52 = [r for r in reg["items"] if r["item_id"] in set(items)]
    image_coverage = {
        "registered_rating_all_178": {"page_images": reg["page_images"], "opened": reg["page_images_opened"],
                                      "items_opening_every_page_image": reg["items_opening_every_page_image"]},
        "registered_rating_on_the_52": {
            "page_images": sum(r["page_images"] for r in reg_52),
            "opened": sum(r["page_images_opened"] for r in reg_52),
            "items_opening_every_page_image": sum(r["page_images_opened"] == r["page_images"] for r in reg_52),
            "short": {r["item_id"]: [r["page_images_opened"], r["page_images"]] for r in reg_52
                      if r["page_images_opened"] != r["page_images"]}},
    }
    for tag, run in (("a", run_a_eq), ("b", run_b), ("c", run_c)):
        image_coverage[f"run_{tag}"] = {
            "items": len(run["items"]), "page_images": run["page_images"], "opened": run["page_images_opened"],
            "items_opening_every_page_image": run["items_opening_every_page_image"],
            "short": {r["item_id"]: [r["page_images_opened"], r["page_images"]] for r in run["items"]
                      if r["page_images_opened"] != r["page_images"]}}

    out = {
        "schema": "q2m-d81-adjudication-summary-v1",
        "label": LABEL,
        "deviation": ("D80 (ii), D81: the 34-item adjudication pool and the 25-item spot check (52 distinct items) "
                      "were answered by fresh isolated model adjudicators (run (a), claude-opus-5-5, one per item, "
                      "the registered template), not by Kevin; D9's spot check was meant as a human validation of "
                      "the model raters and is not human here (it stays pending as a human validation)."),
        "inputs_sha256": {str(p): digest(p) for p in (
            HERE / "adjudications.jsonl", HERE / "spot-check-answers.jsonl",
            HERE / "sensitivity/b-fable/adjudications.jsonl", HERE / "sensitivity/c-notation/adjudications.jsonl",
            HERE / "isolation/a/calls.jsonl", HERE / "isolation/b/audit_runs.json",
            HERE / "isolation/c/audit_runs.json", HERE / "isolation/a/audit_runs-equivalence-check.json",
            HERE / "isolation/validation/audit_runs-on-2026-10-08-rating.json",
            HERE / "audit-summary/audit-summary.json", HERE / "audit-summary/decisions.jsonl",
            HERE / "analysis/analysis.json",
            HERE / "sensitivity/b-fable/analysis/analysis.json", HERE / "sensitivity/c-notation/analysis/analysis.json",
            CONF / "audit/audit-summary/audit-summary.json", CONF / "audit/audit-summary/decisions.jsonl",
            CONF / "audit/audit-summary/adjudication-pool.jsonl",
            CONF / "audit/released/confirm-audit-v1/spot-check.jsonl",
            CONF / "audit/released/confirm-audit-v1/sample.jsonl", K2 / "analysis-with-k2/analysis.json")},
        "answers": {
            "distinct_items": len(items), "pool": len(pool), "spot_check": len(spot),
            "overlap": len(set(pool) & set(spot)),
            "a": dict(collections.Counter(a.values())),
            "a_pool": dict(collections.Counter(a[i] for i in pool)),
            "a_spot_check": dict(collections.Counter(a[i] for i in spot)),
            "b_given": dict(collections.Counter(b_given.values())),
            "b_strict_registered_audit": dict(collections.Counter(b_strict.values())),
            "c": dict(collections.Counter(c_ans.values())),
            "a_left_out_of_adjudications": [i for i in pool if a[i] not in ("accept", "reject")],
            "b_left_out_of_adjudications": [i for i in pool if b_given[i] not in ("accept", "reject")],
        },
        "isolation": isolation,
        "image_coverage": image_coverage,
        "pool_effect_by_reason_and_stratum": {"a": pool_effect(a), "b": pool_effect(b_given)},
        "agreement": agreement,
        "spot_check": {
            "a": {"by_stratum": spot_table(a), "disagreements_with_concordant_raters": spot_disagreements(a)},
            "b": {"by_stratum": spot_table(b_given), "disagreements_with_concordant_raters": spot_disagreements(b_given)},
        },
        "before_after": {
            "before": outputs(pre_an, pre_sum),
            "after_a": outputs(post_an, post_sum),
            "sensitivity_b_fable": outputs(sens["b-fable"]["analysis"], sens["b-fable"]["summary"]),
            "sensitivity_c_notation_identical_to_a": (sens["c-notation"]["analysis"] == post_an
                                                      and sens["c-notation"]["summary"] == post_sum),
        },
        "unchanged_by_adjudication": unchanged,
    }
    (HERE / "summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"items": len(items), "pool": len(pool), "spot": len(spot),
                      "unchanged_all": all(unchanged.values()),
                      "unchanged_false": sorted(k for k, v in unchanged.items() if not v)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
