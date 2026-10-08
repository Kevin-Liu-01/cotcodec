"""Summary of the D27 development rerate with the Qwen3.6-35B-A3B rater (exploratory).

Inputs (paths given on the command line; the label-bearing ones are held on
the host until the isolated Claude answers of the same items are ingested):

``--sample``           the rerate audit's ``sample.jsonl`` (labels, strata)
``--open-calls``       one ``calls.jsonl`` per lane job (shards and reruns)
``--receipts``         the lane jobs' ``receipt.json`` files (timing)
``--estimates``        ``packet-estimates.json`` of the rerate packets
``--v8-release``       ``mutations.release.jsonl`` of the mutation run sampled
``--v2-sample``        the second smoke's ``audit/sample.jsonl`` (committed)
``--v4-release``       ``dev-mutants-v4/mutations.release.jsonl`` (committed)
``--v2-open-calls``    the second smoke's Qwen3.5-9B calls (committed)
``--v2-claude``        the earlier shared-directory Claude answers on the second
                       smoke's items (the rater workflow's wrapper; not blind,
                       exploratory)

Items of the two audits are matched by task and, for mutants, by operator,
site and recipe steps (mutant ids differ between runs because a LibreOffice
save is not byte-deterministic); shams and P1 flips by task. The
label-consistent answer is accept for should-pass labels, gold shams and P1
flips, reject for should-fail labels and do-nothing shams.

Output: aggregates only (no item id, label or answer per item).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from harness.q2_mutation import raters, stats  # noqa: E402
from harness.q2_mutation.audit import load_sample  # noqa: E402
from harness.q2_mutation.rater_runner import answer_records, merge_calls  # noqa: E402

PASS = ("should_pass_equiv", "should_pass_alt_solution")
OPEN = "model-rater-open-weight"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def klass(row: dict) -> str:
    if row.get("sham"):
        return f"sham_{row['sham']}"
    if row["stratum"] == "p1_flip":
        return "p1_flip"
    return str(row["label"])


def consistent(row: dict) -> str:
    return "accept" if klass(row) in (*PASS, "sham_gold", "p1_flip") else "reject"


def recipe_key(release: dict) -> str:
    params = release["recipe_release"]["params"]
    steps = [
        {k: v for k, v in step.items() if "sha256" not in k and k != "expect"}
        for step in params.get("steps", [])
    ]
    return json.dumps(
        [release["task_id"], release["operator"], params.get("site"), steps], sort_keys=True
    )


def match_keys(sample: list[dict], release: list[dict]) -> dict[str, str]:
    """item id -> run-independent key."""
    by_mutant = {r["mutant_id"]: recipe_key(r) for r in release}
    out = {}
    for row in sample:
        if row.get("sham") or row["stratum"] == "p1_flip":
            out[row["item_id"]] = f"{row['task_id']}::{row['mutant_id'].split('__', 1)[1]}"
        elif row["mutant_id"] in by_mutant:
            out[row["item_id"]] = by_mutant[row["mutant_id"]]
    return out


def agreement(pairs: list[tuple[str, str]]) -> dict:
    if not pairs:
        return {"items": 0}
    return {
        "items": len(pairs),
        "kappa": stats.cohens_kappa([x for x, _ in pairs], [y for _, y in pairs]),
        "raw_agreement": sum(a == b for a, b in pairs) / len(pairs),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=Path, required=True)
    p.add_argument("--open-calls", type=Path, nargs="+", required=True)
    p.add_argument("--receipts", type=Path, nargs="+", required=True)
    p.add_argument("--estimates", type=Path)
    p.add_argument("--v8-release", type=Path, required=True)
    p.add_argument("--v2-sample", type=Path, required=True)
    p.add_argument("--v4-release", type=Path, required=True)
    p.add_argument("--v2-open-calls", type=Path, required=True)
    p.add_argument("--v2-claude", type=Path)
    a = p.parse_args()

    rows = jsonl(a.sample)
    calls = merge_calls(a.open_calls, OPEN)
    answer = {
        row["item_id"]: calls[row["item_id"]]["answer"] for row in rows if row["item_id"] in calls
    }
    by_class: dict[str, Counter] = {}
    by_op: dict[str, Counter] = {}
    for row in rows:
        k = klass(row)
        got = answer.get(row["item_id"], "unrated")
        by_class.setdefault(k, Counter())[got] += 1
        parts = str(row["mutant_id"]).split("__")
        if len(parts) == 3 and not row.get("sham"):
            by_op.setdefault(parts[1], Counter())[got] += 1
    real = [r for r in rows if not r.get("sham")]
    shams = [r for r in rows if r.get("sham")]
    contradicts = Counter(
        klass(r)
        for r in real
        if answer.get(r["item_id"]) not in (None, "unsure")
        and answer[r["item_id"]] != consistent(r)
    )
    unsure = Counter(klass(r) for r in real if answer.get(r["item_id"]) == "unsure")
    sample, labels, item_of = load_sample(a.sample)
    label_of = {row["mutant_id"]: row for row in rows}
    ratings = {
        key: (consistent(label_of[key]), answer.get(item, "unsure"))
        for key, item in item_of.items()
    }
    summary = raters.summarize(sample, labels, ratings, n_boot=2000, seed=42)
    out: dict = {
        "items": len(rows),
        "rated": len(answer),
        "unrated": len(rows) - len(answer),
        "outcomes": dict(Counter(c["outcome"] for c in calls.values())),
        "statuses": dict(Counter(c["status"] for c in calls.values())),
        "answers": dict(Counter(answer.values())),
        "answers_by_label_class": {k: dict(v) for k, v in sorted(by_class.items())},
        "answers_by_operator": {k: dict(v) for k, v in sorted(by_op.items())},
        "sham_accuracy": {
            "correct": sum(answer.get(r["item_id"]) == consistent(r) for r in shams),
            "shams": len(shams),
        },
        "real_items": len(real),
        "contradicts_label_by_class": dict(contradicts),
        "unsure_by_class": dict(unsure),
        "split_share_if_anthropic_agreed_with_every_label": sum(
            1 for r in real if answer.get(r["item_id"]) != consistent(r)
        ) / len(real),
        "if_anthropic_agreed_with_every_label": {
            "kappa": summary.kappa,
            "kappa_fires": summary.kappa_fires,
            "k3_fires": dict(summary.k3_fires),
            "k4_fires": summary.k4_fires,
            "label_error_unresolved_as_wrong": dict(summary.label_error_unresolved_as_wrong),
            "k3_items": {
                g: (b.n_items if b else 0, round(b.kish_n, 1) if b else 0.0)
                for g, b in summary.k3.items()
            },
        },
    }

    # Matched comparison with the second smoke (Qwen3.5-9B) and the earlier,
    # non-blind Claude answers on the same sites.
    v2_rows = jsonl(a.v2_sample)
    v3_key = match_keys(rows, jsonl(a.v8_release))
    v2_key = match_keys(v2_rows, jsonl(a.v4_release))
    v2_item = {key: item for item, key in v2_key.items()}
    v2_open = {c["item_id"]: c["answer"] for c in jsonl(a.v2_open_calls)}
    real_items = {r["item_id"] for r in real}
    matched = {item: v2_item[key] for item, key in v3_key.items() if key in v2_item}
    out["matched_with_smoke_v2"] = {
        "items": len(matched),
        "real_items": len(set(matched) & real_items),
    }
    pairs_9b = [
        (v2_open[old], answer[new])
        for new, old in matched.items()
        if new in real_items and old in v2_open and new in answer
    ]
    out["qwen35_9b_vs_qwen36_35b_on_matched_real_items"] = agreement(pairs_9b)
    if a.v2_claude:
        claude = {
            str(r["item_id"]): raters.parse_first_token(str(r.get("answer")))[0]
            for r in answer_records(a.v2_claude.read_bytes())
        }
        pairs = [
            (claude[old], answer[new])
            for new, old in matched.items()
            if new in real_items and old in claude and new in answer
        ]
        out["kappa_vs_earlier_claude_answers_matched_real_items"] = {
            **agreement(pairs),
            "note": "the Claude answers were given by one agent over all items (not blind, D27)",
        }
        nine = [
            (claude[old], v2_open[old])
            for new, old in matched.items()
            if new in real_items and old in claude and old in v2_open
        ]
        out["kappa_9b_vs_earlier_claude_same_items"] = agreement(nine)

    tokens = [c["usage"]["prompt_tokens"] for c in calls.values() if c.get("usage")]
    receipts = [json.loads(r.read_text()) for r in a.receipts]
    rating_s = sum(r.get("engine", {}).get("rating_s") or 0.0 for r in receipts)
    out["throughput"] = {
        "prompt_tokens_total": sum(tokens),
        "prompt_tokens_max": max(tokens) if tokens else None,
        "prompt_tokens_median": statistics.median(tokens) if tokens else None,
        "rating_seconds": rating_s,
        "items_per_minute": len(tokens) / (rating_s / 60) if rating_s else None,
        "prompt_tokens_per_second": sum(tokens) / rating_s if rating_s else None,
        "engine_ready_s": [r.get("engine", {}).get("ready_s") for r in receipts],
        "seconds_per_call_median": statistics.median(
            sum(x["seconds"] for x in c["attempts"]) for c in calls.values()
        )
        if calls
        else None,
        "completion_cut_at_max_tokens": sum(
            1 for c in calls.values() if c.get("stop_reason") == "length"
        ),
    }
    if a.estimates:
        est = json.loads(a.estimates.read_text())
        ratio = [
            calls[i]["usage"]["prompt_tokens"] / est[i]["estimate"]
            for i in calls
            if calls[i].get("usage") and i in est
        ]
        out["throughput"]["actual_over_registered_estimate_max"] = max(ratio) if ratio else None
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
