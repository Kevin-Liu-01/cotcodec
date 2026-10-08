"""Summary of the D34 development rerate: Qwen3.6-35B-A3B with thinking on (exploratory).

Inputs (paths on the command line; the label-bearing ones are held on the host
until the isolated Claude answers on the same items are ingested):

``--sample``          the D34 audit's ``sample.jsonl`` (labels, strata; held)
``--open-calls``      the lane job's ``calls.jsonl`` (held)
``--receipts``        the lane job's ``receipt.json``
``--v9-release``      ``mutations.release.jsonl`` of ``dev-mutants-v9`` (held)
``--packets-manifest`` the audit's ``packets-manifest.json`` (estimates, fit)
``--v3-sample``       the D27 audit's ``audit/sample.jsonl`` (committed)
``--v8-release``      ``dev-mutants-v8/mutations.release.jsonl`` (committed)
``--v3-claude-calls`` the isolated Claude calls on the D27 audit (committed)
``--v3-open-calls``   the thinking-off Qwen3.6-35B-A3B calls on the D27 audit (committed)

Items of the two audits are matched by task and, for mutants, by operator, site
and recipe steps (a LibreOffice save is not byte-deterministic, so mutant ids
differ between runs); shams and P1 flips by task and kind. The packets differ
between the audits (D34 added text differences for new files and the save
drift rule), so the comparison with the D27 Claude answers is a projection,
not the registered D34 result, which needs the isolated Claude answers on the
D34 packets. The label-consistent answer is accept for should-pass labels,
gold shams and P1 flips, reject for should-fail labels and do-nothing shams.

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
from harness.q2_mutation.rater_runner import merge_calls  # noqa: E402

PASS = ("should_pass_equiv", "should_pass_alt_solution")
OPEN = "model-rater-open-weight"
CLAUDE = "model-rater-anthropic"


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
        "pairs": dict(Counter(f"{a}/{b}" for a, b in pairs)),
    }


def registered(rows: list[dict], sample_path: Path, first: dict, second: dict) -> dict:
    """The registered summary with ``first`` as the Anthropic rater's answers."""
    sample, labels, item_of = load_sample(sample_path)
    keep = {r["mutant_id"] for r in rows}
    ratings = {
        key: (first.get(item, "unsure"), second.get(item, "unsure"))
        for key, item in item_of.items()
        if key in keep
    }
    part = [s for s in sample if s.mutant_id in keep]
    summary = raters.summarize(part, labels, ratings, n_boot=2000, seed=42)
    return {
        "kappa": summary.kappa,
        "kappa_fires": summary.kappa_fires,
        "real_items": summary.n_items,
        "split_items": summary.n_unresolved,
        "k3_fires": dict(summary.k3_fires),
        "k4_fires": summary.k4_fires,
        "label_error": {g: i.estimate for g, i in summary.label_error.items()},
        "k3_items": {g: (b.n_items if b else 0) for g, b in summary.k3.items()},
        "adjudication": dict(summary.adjudication),
        "gold_defect_tasks": len(summary.gold_defects["tasks"]),
        "gold_defect_equivalence_items": summary.gold_defects["equivalence_items"],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=Path, required=True)
    p.add_argument("--open-calls", type=Path, nargs="+", required=True)
    p.add_argument("--receipts", type=Path, nargs="+", required=True)
    p.add_argument("--v9-release", type=Path, required=True)
    p.add_argument("--packets-manifest", type=Path, required=True)
    p.add_argument("--v3-sample", type=Path, required=True)
    p.add_argument("--v8-release", type=Path, required=True)
    p.add_argument("--v3-claude-calls", type=Path, required=True)
    p.add_argument("--v3-open-calls", type=Path, required=True)
    a = p.parse_args()

    rows = jsonl(a.sample)
    calls = merge_calls(a.open_calls, OPEN)
    answer = {r["item_id"]: calls[r["item_id"]]["answer"] for r in rows if r["item_id"] in calls}
    by_class: dict[str, Counter] = {}
    by_op: dict[str, Counter] = {}
    for row in rows:
        got = answer.get(row["item_id"], "unrated")
        by_class.setdefault(klass(row), Counter())[got] += 1
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
    labels_as_first = {r["item_id"]: consistent(r) for r in rows}
    out: dict = {
        "items": len(rows),
        "real_items": len(real),
        "shams": dict(Counter(str(r["sham"]) for r in shams)),
        "rated": len(answer),
        "unrated": len(rows) - len(answer),
        "outcomes": dict(Counter(c["outcome"] for c in calls.values())),
        "statuses": dict(Counter(c["status"] for c in calls.values())),
        "answers": dict(Counter(answer.values())),
        "answers_by_label_class": {k: dict(v) for k, v in sorted(by_class.items())},
        "answers_by_operator": {k: dict(v) for k, v in sorted(by_op.items())},
        "sham_accuracy": {
            kind: {
                "correct": sum(
                    answer.get(r["item_id"]) == consistent(r) for r in shams if r["sham"] == kind
                ),
                "shams": sum(1 for r in shams if r["sham"] == kind),
            }
            for kind in ("gold", "do_nothing")
        },
        "contradicts_label_by_class": dict(contradicts),
        "unsure_by_class": dict(
            Counter(klass(r) for r in real if answer.get(r["item_id"]) == "unsure")
        ),
        "split_share_if_anthropic_agreed_with_every_label": sum(
            1 for r in real if answer.get(r["item_id"]) != consistent(r)
        )
        / len(real),
        "if_anthropic_agreed_with_every_label": registered(
            rows, a.sample, labels_as_first, answer
        ),
    }

    # Projection with the D27 isolated Claude answers on matched items.
    v3_rows = jsonl(a.v3_sample)
    v4_key = match_keys(rows, jsonl(a.v9_release))
    v3_key = match_keys(v3_rows, jsonl(a.v8_release))
    v3_item = {key: item for item, key in v3_key.items()}
    matched = {item: v3_item[key] for item, key in v4_key.items() if key in v3_item}
    claude = {i: c["answer"] for i, c in merge_calls([a.v3_claude_calls], CLAUDE).items()}
    off = {i: c["answer"] for i, c in merge_calls([a.v3_open_calls], OPEN).items()}
    real_ids = {r["item_id"] for r in real}
    pairs = [
        (claude[old], answer[new])
        for new, old in matched.items()
        if new in real_ids and old in claude and new in answer
    ]
    before = [
        (claude[old], off[old])
        for new, old in matched.items()
        if new in real_ids and old in claude and old in off and new in answer
    ]
    think_vs_off = [
        (off[old], answer[new])
        for new, old in matched.items()
        if new in real_ids and old in off and new in answer
    ]
    first = {new: claude[old] for new, old in matched.items() if old in claude}
    matched_rows = [r for r in rows if r["item_id"] in first]
    out["projection_with_d27_isolated_claude_answers"] = {
        "note": (
            "the D27 Claude answers were given on the D27 packets; the D34 packets add text "
            "differences for new files and count save drift, so this is a projection only"
        ),
        "matched_items": len(matched),
        "matched_real_items": len(set(matched) & real_ids),
        "claude_d27_vs_qwen_thinking_on": agreement(pairs),
        "claude_d27_vs_qwen_thinking_off_same_items": agreement(before),
        "qwen_thinking_off_vs_on": agreement(think_vs_off),
        "registered_summary_on_matched_items": registered(matched_rows, a.sample, first, answer),
    }

    receipts = [json.loads(r.read_text()) for r in a.receipts]
    rating_s = sum(r.get("engine", {}).get("rating_s") or 0.0 for r in receipts)
    usage = [c["usage"] for c in calls.values() if c.get("usage")]
    prompt = [u["prompt_tokens"] for u in usage]
    completion = sorted(u["completion_tokens"] for u in usage)
    seconds = [sum(x["seconds"] for x in c["attempts"]) for c in calls.values()]
    out["throughput"] = {
        "rating_seconds": rating_s,
        "items_per_minute": len(usage) / (rating_s / 60) if rating_s else None,
        "engine_ready_s": [r.get("engine", {}).get("ready_s") for r in receipts],
        "engine_stop_s": [r.get("engine", {}).get("stop_s") for r in receipts],
        "prompt_tokens_total": sum(prompt),
        "prompt_tokens_max": max(prompt) if prompt else None,
        "prompt_tokens_median": statistics.median(prompt) if prompt else None,
        "completion_tokens_total": sum(completion),
        "completion_tokens_median": statistics.median(completion) if completion else None,
        "completion_tokens_p90": (
            completion[int(0.9 * (len(completion) - 1))] if completion else None
        ),
        "completion_tokens_max": max(completion) if completion else None,
        "completion_tokens_per_second": sum(completion) / rating_s if rating_s else None,
        "prompt_tokens_per_second": sum(prompt) / rating_s if rating_s else None,
        "cut_at_max_tokens": sum(1 for c in calls.values() if c.get("stop_reason") == "length"),
        "thinking_unfinished": sum(
            1 for c in calls.values() if c["outcome"] == "thinking_unfinished"
        ),
        "seconds_per_call_median": statistics.median(seconds) if seconds else None,
        "seconds_per_call_max": max(seconds) if seconds else None,
        "retries": sum(max(0, len(c["attempts"]) - 1) for c in calls.values()),
    }
    manifest = json.loads(a.packets_manifest.read_text())
    out["packets"] = {
        "shards": [{k: s[k] for k in ("items", "bytes", "sha256")} for s in manifest["shards"]],
        "fit": manifest["fit"],
        "baselines": {k: manifest["baselines"][k] for k in ("items", "jobs", "saved")},
    }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
