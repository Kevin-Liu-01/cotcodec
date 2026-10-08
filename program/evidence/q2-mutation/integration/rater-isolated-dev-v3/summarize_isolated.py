"""Dev summary of the D27 rerate with both raters (isolated Claude + Qwen3.6-35B-A3B).

Exploratory development evidence; nothing here is a result of the
registration. Inputs (paths on the command line):

``--sample``            the rerate audit's ``sample.jsonl`` (labels, strata)
``--claude-calls``      ``calls.jsonl`` of ``rater_runner ingest-isolated``
``--open-calls``        ``calls.jsonl`` of the open-weight lane job (702)
``--registered``        ``audit-summary.json`` of ``audit summarize`` on the
                        same three files (the registered summary)
``--spot-check``        the audit's ``spot-check.jsonl``
``--transcript-audit``  ``transcript-audit.json`` of ``audit_transcripts.py``
``--v8-release``        ``dev-mutants-v8/mutations.release.jsonl``
``--v2-sample``         ``rater-smoke-dev-v2/audit/sample.jsonl``
``--v4-release``        ``dev-mutants-v4/mutations.release.jsonl``
``--v2-claude``         the earlier shared-directory Claude answers on the
                        second smoke's items (not blind; kept outside the
                        repository, digest recorded)

Matching of the two audits' items (task, operator, site and recipe steps; by
task for shams and P1 flips) is ``summarize_rerate.match_keys`` of the
rerate evidence. Output: aggregates only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from harness.q2_mutation import raters, stats  # noqa: E402
from harness.q2_mutation.rater_runner import answer_records  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "summarize_rerate",
    Path(__file__).resolve().parent.parent / "rater-rerate-dev-v3" / "summarize_rerate.py",
)
assert _spec and _spec.loader
rerate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rerate)

ADJUDICATION_MINUTES = (3, 5)  # prereg section 9: assumed minutes per item


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    for name in (
        "sample",
        "claude-calls",
        "open-calls",
        "registered",
        "spot-check",
        "transcript-audit",
        "v8-release",
        "v2-sample",
        "v4-release",
    ):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--v2-claude", type=Path)
    a = p.parse_args()

    rows = jsonl(a.sample)
    claude = {c["item_id"]: c for c in jsonl(a.claude_calls)}
    open_ = {c["item_id"]: c for c in jsonl(a.open_calls)}
    assert set(claude) == set(open_) == {r["item_id"] for r in rows}
    first = {i: c["answer"] for i, c in claude.items()}
    second = {i: c["answer"] for i, c in open_.items()}
    registered = json.loads(a.registered.read_text())
    audit = json.loads(a.transcript_audit.read_text())

    real = [r for r in rows if not r.get("sham")]
    shams = [r for r in rows if r.get("sham")]
    pairs = [(first[r["item_id"]], second[r["item_id"]]) for r in real]
    confusion = Counter(f"{x}/{y}" for x, y in pairs)
    split = [
        r
        for r in real
        if raters.consensus(first[r["item_id"]], second[r["item_id"]]) == "unresolved"
    ]
    spot = {row["item_id"] for row in jsonl(a.spot_check)}
    split_ids = {r["item_id"] for r in split}

    def by_class(answers: dict[str, str]) -> dict[str, dict[str, int]]:
        out: dict[str, Counter] = {}
        for r in rows:
            out.setdefault(rerate.klass(r), Counter())[answers[r["item_id"]]] += 1
        return {k: dict(v) for k, v in sorted(out.items())}

    def against_labels(answers: dict[str, str]) -> dict[str, object]:
        contradicts = Counter(
            rerate.klass(r)
            for r in real
            if answers[r["item_id"]] != "unsure" and answers[r["item_id"]] != rerate.consistent(r)
        )
        unsure = Counter(rerate.klass(r) for r in real if answers[r["item_id"]] == "unsure")
        consistent = sum(1 for r in real if answers[r["item_id"]] == rerate.consistent(r))
        return {
            "label_consistent": consistent,
            "real_items": len(real),
            "contradicts_label_by_class": dict(contradicts),
            "unsure_by_class": dict(unsure),
            "shams_right": sum(answers[r["item_id"]] == rerate.consistent(r) for r in shams),
            "shams": len(shams),
        }

    violation_ops: dict[str, Counter] = {}
    for r in real:
        if r.get("label") != "should_fail_violation":
            continue
        op = str(r["mutant_id"]).split("__")[1]
        violation_ops.setdefault(op, Counter())[
            f"{first[r['item_id']]}/{second[r['item_id']]}"
        ] += 1

    n_split = len(split)
    out: dict[str, object] = {
        "label": "exploratory development evidence (dev split); not a result of the registration",
        "items": len(rows),
        "real_items": len(real),
        "shams": len(shams),
        "raters": {
            "model-rater-anthropic": (
                "claude-opus-5-5 through the agent harness, one isolated agent per item"
            ),
            "model-rater-open-weight": "Qwen3.6-35B-A3B, lane job 702",
        },
        "transcript_audit": {
            **{
                k: audit["totals"][k]
                for k in ("raters", "strict_void", "tool_totals", "reads_outside")
            },
            "registered_isolation_void": sum(
                c["outcome"] == "isolation_void" for c in claude.values()
            ),
            "answer_source": dict(Counter(c["extra"]["answer_source"] for c in claude.values())),
            "tree_rehash_matches_export": sum(
                c["extra"]["tree_sha256"] == c["extra"]["tree_rehashed_sha256"]
                for c in claude.values()
            ),
            "raters_not_opening_every_page": audit["totals"]["raters_not_opening_every_page"],
        },
        "registered": {
            "kappa": registered["kappa"],
            "kappa_min": raters.KAPPA_MIN,
            "kappa_fires": registered["kappa_fires"],
            "sham_accuracy": registered["sham_accuracy"],
            "label_error": registered["label_error"],
            "k3": registered["k3"],
            "k3_threshold": stats.K3_THRESHOLD,
            "k3_fires": registered["k3_fires"],
            "k4_fires": registered["k4_fires"],
            "label_error_resolved_only": registered["label_error_resolved_only"],
            "per_rater": registered["per_rater"],
            "by_label_class": registered["by_label_class"],
            "p1_flips_decision": sorted(registered["p1_flips"].values()),
            "n_items": registered["n_items"],
            "n_unresolved": registered["n_unresolved"],
            "n_adjudicated": registered["n_adjudicated"],
        },
        "unresolved_share_real_items": n_split / len(real),
        "adjudication_workload": {
            "split_items": n_split,
            "split_by_class": dict(Counter(rerate.klass(r) for r in split)),
            "split_pattern_claude_over_open": dict(
                Counter(f"{first[r['item_id']]}/{second[r['item_id']]}" for r in split)
            ),
            "hours_at_3_to_5_minutes": [n_split * m / 60 for m in ADJUDICATION_MINUTES],
            "spot_check_items": len(spot),
            "spot_check_also_split": len(spot & split_ids),
            "split_or_spot_check_items": len(spot | split_ids),
        },
        "real_item_agreement": {
            "raw_agreement": sum(x == y for x, y in pairs) / len(pairs),
            "kappa": stats.cohens_kappa([x for x, _ in pairs], [y for _, y in pairs]),
            "confusion_claude_over_open": dict(sorted(confusion.items())),
        },
        "answers_by_label_class": {
            "claude_isolated": by_class(first),
            "open_weight": by_class(second),
        },
        "against_labels": {
            "claude_isolated": against_labels(first),
            "open_weight": against_labels(second),
        },
        "violation_operators_claude_over_open": {
            k: dict(v) for k, v in sorted(violation_ops.items())
        },
        "kappa_rule_d27": (
            "kappa below 0.6 with the stronger open-weight rater: under D27 the design goes back "
            "to review; the kappa rule is not changed"
            if registered["kappa_fires"]
            else "kappa at or above 0.6"
        ),
        "inputs_sha256": {
            name: sha(getattr(a, name.replace("-", "_")))
            for name in (
                "sample",
                "claude-calls",
                "open-calls",
                "registered",
                "spot-check",
                "transcript-audit",
                "v8-release",
                "v2-sample",
                "v4-release",
            )
        },
    }

    # The isolated answers against the earlier shared-directory (non-blind) Claude
    # answers on matched items, and the 13 deterministic sham / P1 ids shared
    # with the committed second-smoke sample.
    v2_rows = jsonl(a.v2_sample)
    v3_key = rerate.match_keys(rows, jsonl(a.v8_release))
    v2_key = rerate.match_keys(v2_rows, jsonl(a.v4_release))
    v2_item = {key: item for item, key in v2_key.items()}
    matched = {item: v2_item[key] for item, key in v3_key.items() if key in v2_item}
    real_ids = {r["item_id"] for r in real}
    shared_ids = {r["item_id"] for r in rows} & {r["item_id"] for r in v2_rows}
    by_id = {r["item_id"]: r for r in rows}
    out["ids_shared_with_committed_smoke_v2_sample"] = {
        "items": len(shared_ids),
        "kinds": dict(Counter(rerate.klass(by_id[i]) for i in shared_ids)),
        "claude_label_consistent": sum(first[i] == rerate.consistent(by_id[i]) for i in shared_ids),
    }
    if a.v2_claude:
        earlier = {
            str(r["item_id"]): raters.parse_first_token(str(r.get("answer")))[0]
            for r in answer_records(a.v2_claude.read_bytes())
        }
        both = [
            (earlier[old], first[new])
            for new, old in matched.items()
            if new in real_ids and old in earlier
        ]
        out["isolated_vs_earlier_nonblind_claude_matched_real_items"] = {
            "items": len(both),
            "raw_agreement": sum(x == y for x, y in both) / len(both) if both else None,
            "kappa": stats.cohens_kappa([x for x, _ in both], [y for _, y in both])
            if both
            else None,
            "changes_earlier_to_isolated": dict(Counter(f"{x}->{y}" for x, y in both if x != y)),
            "earlier_answers_sha256": sha(a.v2_claude),
            "note": (
                "the earlier answers came from one agent over all items in a shared "
                "directory (not blind, D27)"
            ),
        }
        opens = [
            (earlier[old], second[new])
            for new, old in matched.items()
            if new in real_ids and old in earlier
        ]
        out["earlier_nonblind_claude_vs_open_weight_matched_real_items"] = {
            "items": len(opens),
            "kappa": stats.cohens_kappa([x for x, _ in opens], [y for _, y in opens])
            if opens
            else None,
        }
    print(json.dumps(out, indent=1, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
