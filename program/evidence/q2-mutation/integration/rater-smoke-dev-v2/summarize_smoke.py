"""Summary of the second open-weight rater smoke on dev packets (exploratory).

Inputs (all committed beside this script, or in rater-smoke-dev-v1/):
``audit/sample.jsonl`` (labels, strata), ``open-weight/calls.jsonl`` of this
smoke, ``../rater-smoke-dev-v1/open-weight/calls.jsonl`` (the first smoke, raw
baseline, the same 133 items), ``packet-estimates.json`` (registered token
estimate and baseline status per packet).

The label-consistent answer of an item is accept for should-pass labels, gold
shams and P1 flips, reject for should-fail labels and do-nothing shams. The
hypothetical "Anthropic rater agrees with every label" pairs that answer with
the open-weight rater's and goes through the registered ``raters.summarize``
(kappa, K3, K4), as the third draft's re-audit did for the first smoke.

Usage (repository root): python program/evidence/q2-mutation/integration/
rater-smoke-dev-v2/summarize_smoke.py > summary.json
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4]))

from harness.q2_mutation import raters  # noqa: E402
from harness.q2_mutation.audit import load_sample  # noqa: E402

PASS = ("should_pass_equiv", "should_pass_alt_solution")


def calls(path: Path) -> dict[str, dict]:
    return {
        row["item_id"]: row
        for row in (json.loads(line) for line in path.read_text().splitlines() if line)
    }


def klass(row: dict) -> str:
    if row.get("sham"):
        return f"sham_{row['sham']}"
    if row["stratum"] == "p1_flip":
        return "p1_flip"
    return str(row["label"])


def consistent(row: dict) -> str:
    k = klass(row)
    return "accept" if k in (*PASS, "sham_gold", "p1_flip") else "reject"


def operator(row: dict) -> str | None:
    parts = str(row["mutant_id"]).split("__")
    return parts[1] if len(parts) == 3 and not row.get("sham") else None


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "audit" / "sample.jsonl").read_text().splitlines()]
    v2 = calls(HERE / "open-weight" / "calls.jsonl")
    v1 = calls(HERE.parent / "rater-smoke-dev-v1" / "open-weight" / "calls.jsonl")
    estimates = json.loads((HERE / "packet-estimates.json").read_text())
    by_class: dict[str, Counter] = {}
    by_class_v1: dict[str, Counter] = {}
    by_op: dict[str, Counter] = {}
    transitions: dict[str, Counter] = {}
    for row in rows:
        item = row["item_id"]
        k = klass(row)
        a2 = v2[item]["answer"] if item in v2 else "unrated"
        a1 = v1[item]["answer"] if item in v1 else "unrated"
        by_class.setdefault(k, Counter())[a2] += 1
        by_class_v1.setdefault(k, Counter())[a1] += 1
        transitions.setdefault(k, Counter())[f"{a1}->{a2}"] += 1
        op = operator(row)
        if op:
            by_op.setdefault(op, Counter())[a2] += 1
    sample, labels, item_of = load_sample(HERE / "audit" / "sample.jsonl")
    label_of = {row["mutant_id"]: row for row in rows}
    out: dict = {
        "items": len(rows),
        "rated": len(v2),
        "outcomes": dict(Counter(c["outcome"] for c in v2.values())),
        "statuses": dict(Counter(c["status"] for c in v2.values())),
        "answers": dict(Counter(c["answer"] for c in v2.values())),
        "answers_by_label_class": {k: dict(v) for k, v in sorted(by_class.items())},
        "answers_by_label_class_smoke_v1_raw_baseline": {
            k: dict(v) for k, v in sorted(by_class_v1.items())
        },
        "answer_changes_v1_to_v2_by_label_class": {
            k: dict(v) for k, v in sorted(transitions.items())
        },
        "answers_by_operator": {k: dict(v) for k, v in sorted(by_op.items())},
    }
    rated = {row["item_id"] for row in rows if row["item_id"] in v2}
    for name, data, subset in (
        ("v2", v2, None),
        ("v1", v1, None),
        ("v2_on_items_rated_in_v2", v2, rated),
        ("v1_on_items_rated_in_v2", v1, rated),
    ):
        keep = [row for row in rows if subset is None or row["item_id"] in subset]
        split = sum(
            1 for row in keep if data.get(row["item_id"], {}).get("answer") != consistent(row)
        )
        keys = {row["mutant_id"] for row in keep}
        ratings = {
            key: (consistent(label_of[key]), data[item]["answer"] if item in data else "unsure")
            for key, item in item_of.items()
            if key in keys
        }
        part = [s for s in sample if s.mutant_id in keys]
        summary = raters.summarize(part, labels, ratings, n_boot=2000, seed=42)
        out[f"if_anthropic_agreed_with_every_label_{name}"] = {
            "items": len(keep),
            "split_items": split,
            "split_share": split / len(keep),
            "kappa": summary.kappa,
            "kappa_fires": summary.kappa_fires,
            "k3_fires": dict(summary.k3_fires),
            "k4_fires": summary.k4_fires,
            "label_error_unresolved_as_wrong": dict(summary.label_error_unresolved_as_wrong),
            "k3_items": {
                g: (b.n_items if b else 0, round(b.kish_n, 1) if b else 0.0)
                for g, b in summary.k3.items()
            },
        }
    tokens = [c["usage"]["prompt_tokens"] for c in v2.values() if c.get("usage")]
    ratio = [
        v2[i]["usage"]["prompt_tokens"] / estimates[i]["estimate"]
        for i in v2
        if v2[i].get("usage") and i in estimates
    ]
    out["prompt_tokens"] = {
        "max": max(tokens),
        "median": statistics.median(tokens),
        "smoke_v1_max": max(c["usage"]["prompt_tokens"] for c in v1.values()),
        "smoke_v1_median": statistics.median(c["usage"]["prompt_tokens"] for c in v1.values()),
        "actual_over_registered_estimate_max": max(ratio),
        "registered_estimate_max": max(e["estimate"] for e in estimates.values()),
    }
    out["seconds_per_call_median"] = statistics.median(
        sum(a["seconds"] for a in c["attempts"]) for c in v2.values()
    )
    out["completion_cut_at_max_tokens"] = sum(
        1 for c in v2.values() if c.get("stop_reason") == "length"
    )
    soc = [n for e in estimates.values() for n in e["save_only_changes"] if n is not None]
    out["packets"] = {
        "baseline_status": dict(Counter(e["baseline_status"] for e in estimates.values())),
        "end_state_files_by_baseline": dict(
            Counter(str(b) for e in estimates.values() for b in e["end_baselines"])
        ),
        "save_only_changes_median": statistics.median(soc),
        "save_only_changes_max": max(soc),
        "diff_lines_total": sum(e["diff_lines"] for e in estimates.values()),
        "shortened_by_the_budget": sum(
            1 for e in estimates.values() if e["fit"]["cuts"] or e["fit"]["images_dropped"]
        ),
    }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
