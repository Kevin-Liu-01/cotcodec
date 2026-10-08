"""Dev summary of the D34 rerate with both raters (isolated Claude + thinking-on Qwen).

Exploratory development evidence; nothing here is a result of the
registration, which is not frozen. Inputs (paths on the command line):

``--sample``             ``dev-audit-v4/sample.jsonl`` (labels, strata, shams)
``--spot-check``         ``dev-audit-v4/spot-check.jsonl``
``--open-calls``         ``calls.jsonl`` of lane job 722 (open-weight, thinking on)
``--claude-registered``  ``calls.jsonl`` of the registered ``ingest-isolated``
``--claude-excepted``    ``calls.jsonl`` of ``ingest_relay_excepted.py`` (sensitivity)
``--summary-registered`` ``audit-summary.json`` of ``audit summarize`` on the registered calls
``--summary-excepted``   ``audit-summary.json`` of ``audit summarize`` on the sensitivity calls
``--strict-audit``       ``transcript-audit.json`` of ``audit_transcripts.py``

Output: aggregates only (counts, rates, digests), on stdout as JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ADJUDICATION_MINUTES = (3, 5)  # prereg section 9: assumed minutes per item
KAPPA_MIN = 0.6


def jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kappa(pairs: list[tuple[str, str]]) -> float:
    cats = ("accept", "reject", "unsure")
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = sum(
        (sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats
    )
    return (po - pe) / (1 - pe)


def registered_view(summary: dict) -> dict:
    keep = (
        "kappa",
        "kappa_fires",
        "n_items",
        "n_unresolved",
        "sham_accuracy",
        "label_error",
        "k3",
        "k3_fires",
        "k4_fires",
        "label_error_resolved_only",
        "label_error_unresolved_as_wrong",
        "per_rater",
        "by_label_class",
        "adjudication",
        "answer_status",
    )
    out = {k: summary[k] for k in keep}
    gold = dict(summary["gold_defects"])
    gold.pop("items", None)
    out["gold_defects"] = gold
    out["p1_flip_decisions"] = dict(Counter(summary["p1_flips"].values()))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    for name in (
        "sample",
        "spot-check",
        "open-calls",
        "claude-registered",
        "claude-excepted",
        "summary-registered",
        "summary-excepted",
        "strict-audit",
    ):
        p.add_argument(f"--{name}", type=Path, required=True)
    a = p.parse_args()

    rows = jsonl(a.sample)
    by_item = {r["item_id"]: r for r in rows}
    open_ = {c["item_id"]: c for c in jsonl(a.open_calls)}
    reg = {c["item_id"]: c for c in jsonl(a.claude_registered)}
    exc = {c["item_id"]: c for c in jsonl(a.claude_excepted)}
    assert set(open_) == set(reg) == set(exc) == set(by_item)
    spot = {r["item_id"] for r in jsonl(a.spot_check)}
    strict = json.loads(a.strict_audit.read_text())

    def cls(r: dict) -> str:
        if r["sham"]:
            return f"sham_{r['sham']}"
        return r["label"] or r["stratum"]

    real = [r for r in rows if not r["sham"]]
    out: dict = {
        "label": "exploratory development evidence (D34); not a result of the registration",
        "inputs_sha256": {name: sha(path) for name, path in vars(a).items()},
        "items": len(rows),
        "real_items": len(real),
        "transcript_audit": strict["totals"],
    }
    for name, claude in (("registered", reg), ("relay_excepted", exc)):
        view: dict = {}
        answers = Counter()
        cross = Counter()
        splits = Counter()
        for r in rows:
            c, o = claude[r["item_id"]]["answer"], open_[r["item_id"]]["answer"]
            answers[(cls(r), "claude", c)] += 1
            if not r["sham"]:
                cross[f"claude_{c}/open_{o}"] += 1
                if not (c == o and c in ("accept", "reject")):
                    splits[f"{cls(r)}: claude_{c}/open_{o}"] += 1
        view["claude_outcomes"] = dict(Counter(c["outcome"] for c in claude.values()))
        view["claude_answers_by_class"] = {
            k: dict(sorted((ans, n) for (kk, _, ans), n in answers.items() if kk == k))
            for k in sorted({k for k, _, _ in answers})
        }
        view["real_item_crosstab"] = dict(sorted(cross.items()))
        view["real_item_splits"] = dict(sorted(splits.items()))
        view["raw_agreement_real"] = sum(
            claude[r["item_id"]]["answer"] == open_[r["item_id"]]["answer"] for r in real
        ) / len(real)
        view["kappa_check"] = kappa(
            [(claude[r["item_id"]]["answer"], open_[r["item_id"]]["answer"]) for r in real]
        )
        out[name] = view
    out["open_weight_answers_by_class"] = {
        k: dict(Counter(open_[r["item_id"]]["answer"] for r in rows if cls(r) == k))
        for k in sorted({cls(r) for r in rows})
    }
    out["open_weight_statuses"] = dict(Counter(c["status"] for c in open_.values()))
    sreg = json.loads(a.summary_registered.read_text())
    sexc = json.loads(a.summary_excepted.read_text())
    out["summary_registered"] = registered_view(sreg)
    out["summary_relay_excepted"] = registered_view(sexc)
    for name, s in (("registered", sreg), ("relay_excepted", sexc)):
        pool = s["adjudication"]["pool"]
        out[name]["adjudication_hours"] = [pool * m / 60 for m in ADJUDICATION_MINUTES]
        out[name]["kappa_below_0_6"] = s["kappa"] < KAPPA_MIN
    out["spot_check_items"] = len(spot)
    out["d34_i"] = {
        "rule": (
            "D34 (i): if development kappa is still below 0.6, no other rater is tried; "
            "P2-P5 leave the confirmatory headline before the confirm campaign runs, and the "
            "campaign reports P1 and the checker false-negative candidates descriptively"
        ),
        "kappa_registered": sreg["kappa"],
        "kappa_relay_excepted": sexc["kappa"],
        "fires_registered": sreg["kappa"] < KAPPA_MIN,
        "fires_relay_excepted": sexc["kappa"] < KAPPA_MIN,
    }
    print(json.dumps(out, indent=1, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
