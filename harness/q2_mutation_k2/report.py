"""The K2 report: in-VM verdicts against offline verdicts (registration sections 5-9).

Reads only the K2 job's run records and lane receipts, the frozen K2 sample, the K2-C list,
the offline lock-exact verdict rows and the offline notes summary (whose ``nondeterministic``
list is cause (2)'s offline side). It never reads an audit summary, a decision, the
adjudication pool, an adjudication answer, a spot check or a rater output: every input path is
checked against ``FORBIDDEN_INPUT`` and refused if it names one (section 9).

Outputs (``--out-dir``):

* ``k2-pairs.jsonl``: one row per pair (set, pair, job, checker family, offline verdict, each
  run's reading, the pair's reading and explanation);
* ``k2-summary.json``: counts, the fitness gate, the registered outcome, per-family and
  per-save-path agreement, the K2-C summary (descriptive) and the reported-only timings;
* ``k2-report.json``: the parent analysis's ``--k2-report`` input (``executor_commit``,
  ``pairs``, ``disagreements`` with ``checker_family`` and ``explanation``), written only for
  the registered job (purpose ``k2``), and only when the fitness gate passes (section 6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation_k2 import rules

FORBIDDEN_INPUT = re.compile(
    r"adjudicat|audit-summary|decisions|spot-check|pool|answers|rater|calls\.jsonl|sample\.jsonl$",
    re.IGNORECASE,
)
ALLOWED_SAMPLE = re.compile(r"k2-sample\.jsonl$")
REPORT_SCHEMA = "q2m-k2-report-v1"
# Registered inputs of the k2 job (section 2): the released confirm-campaign files.
REGISTERED_INPUTS = {
    "sample": "1194168019c4aa87fa3f4aa0ad02f9ed53c207a86ebec264e731545afed6525a",
    "verdicts": "e9289a954d5aee21156d0b317267b6f818f630b140ac5337e8fae0cc4c66b021",
    "notes_summary": "de597827720bce5aacffa6e51f649510f425bbd89cf558f52da5fe0f881ee823",
}


class ReportError(ValueError):
    """An input is outside what the report may read, or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_input(path: Path) -> Path:
    """Refuse any input that names an audit, decision, adjudication or rater file."""
    text = str(path)
    if FORBIDDEN_INPUT.search(text) and not ALLOWED_SAMPLE.search(text):
        raise ReportError(f"{path}: the K2 report never reads audit or adjudication files")
    if not path.is_file():
        raise ReportError(f"{path}: missing")
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    check_input(path)
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def checker_family(funcs: Sequence[str]) -> str:
    """``harness.q2_mutation.campaign.checker_family`` (a test keeps the two equal)."""
    return "+".join(sorted(set(funcs)))


def pairs_of(sample: Sequence[Mapping[str, Any]], k2c: Sequence[Mapping[str, Any]]) -> list[dict]:
    out = [{"set": "k2", "pair": i, **_id(r)} for i, r in enumerate(sample)]
    out += [{"set": "k2c", "pair": i, **_id(r)} for i, r in enumerate(k2c)]
    return out


def _id(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("job_id", "mutant_id", "task_id", "kind", "candidate_sha256")
    return {k: row[k] for k in keys}


def group_records(records: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int, int], list]:
    """Attempts per (set, pair, run), in attempt order; a duplicated attempt is refused."""
    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, int, int, int]] = set()
    for record in records:
        key = (str(record["set"]), int(record["pair"]), int(record["run"]))
        attempt = int(record.get("attempt") or 1)
        if (*key, attempt) in seen:
            raise ReportError(f"{record.get('slot')}: attempt {attempt} recorded twice")
        seen.add((*key, attempt))
        groups[key].append(record)
    for rows in groups.values():
        rows.sort(key=lambda r: int(r.get("attempt") or 1))
    return groups


def build(
    *,
    records: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    sample: Sequence[Mapping[str, Any]],
    k2c: Sequence[Mapping[str, Any]],
    verdicts: Sequence[Mapping[str, Any]],
    nondeterministic: Sequence[str],
    runs_per_pair: int = rules.RUNS_PER_PAIR,
    only: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Every pair's reading, the gate, the outcome and the analysis report (if written).

    ``only`` (``set:pair`` ids, e.g. ``k2:004``) restricts a development report to the pairs
    a development job ran; the registered job's report reads every pair."""
    purposes = {str(r.get("purpose")) for r in records} | {str(r.get("purpose")) for r in receipts}
    if len(purposes) != 1:
        raise ReportError(f"records and receipts must share one purpose, got {sorted(purposes)}")
    purpose = purposes.pop()
    offline = {str(v["mutant_id"]): v for v in verdicts}
    unstable = set(nondeterministic)
    groups = group_records(records)
    pairs = pairs_of(sample, k2c)
    if only:
        if purpose == "k2":
            raise ReportError("the k2 job's report reads every registered pair")
        wanted = set(only)
        pairs = [p for p in pairs if f"{p['set']}:{int(p['pair']):03d}" in wanted]
        if len(pairs) != len(wanted):
            raise ReportError(f"--only names pairs outside the sample and list: {sorted(wanted)}")
    known = {(p["set"], int(p["pair"])) for p in pairs}
    stray = sorted({(s, p) for s, p, _ in groups} - known)
    if stray:
        raise ReportError(f"records of pairs outside the sample and list: {stray[:5]}")
    rows = []
    for pair in pairs:
        verdict_row = offline.get(str(pair["job_id"]))
        if verdict_row is None:
            raise ReportError(f"{pair['job_id']}: no offline verdict row")
        if verdict_row.get("candidate_sha256") != pair["candidate_sha256"]:
            raise ReportError(f"{pair['job_id']}: the offline row scored another candidate")
        run_rows = []
        for run in range(1, runs_per_pair + 1):
            attempts = groups.get((pair["set"], int(pair["pair"]), run), [])
            for attempt in attempts:
                if attempt.get("candidate_sha256") != pair["candidate_sha256"]:
                    raise ReportError(f"{attempt.get('slot')}: candidate differs from the sample")
            reading = rules.run_reading(attempts)
            run_rows.append({"run": run, **reading})
        reading = rules.classify_pair(
            run_rows, str(verdict_row["verdict"]), str(pair["job_id"]) in unstable
        )
        rows.append(
            {
                **pair,
                "checker_family": checker_family(verdict_row.get("checker_funcs") or []),
                "offline_nondeterministic": str(pair["job_id"]) in unstable,
                "runs": run_rows,
                **reading,
            }
        )
    registered = [r for r in rows if r["set"] == "k2"]
    n = len(registered)
    gate = rules.gate(registered, n) if n else None
    if gate is not None and purpose != "k2":
        # Development: the same rule at 10% of the pairs present (never an analysis input).
        gate["max_excluded"] = n // 10
        gate["passes"] = gate["excluded"] <= gate["max_excluded"]
    if purpose == "k2" and n != rules.REGISTERED_PAIRS:
        raise ReportError(f"the k2 job's sample has {n} pairs, not {rules.REGISTERED_PAIRS}")
    result = rules.outcome(gate, registered) if gate else None
    out: dict[str, Any] = {
        "purpose": purpose,
        "pairs": rows,
        "gate": gate,
        "outcome": result,
        "summary": summarize(rows, records, receipts, purpose, gate, result),
    }
    if purpose == "k2" and result and result["write_analysis_report"]:
        out["analysis_report"] = analysis_report(rows, receipts, gate, result)
    return out


def identity_of(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identities = [dict(r.get("identity") or {}) for r in receipts]
    if not identities:
        raise ReportError("no lane receipt")
    first = identities[0]
    if any(i != first for i in identities[1:]):
        raise ReportError("the lane receipts name different executors")
    if not first.get("executor_commit") or not first.get("vm_image_id"):
        raise ReportError("the lane receipt lacks the executor commit or the VM image")
    return first


def analysis_report(
    rows: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    gate: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """The parent analysis's ``--k2-report`` (``analysis.headline_exclusions`` reads
    ``executor_commit``, ``pairs`` and each disagreement's ``checker_family`` and
    ``explanation``)."""
    ident = identity_of(receipts)
    registered = [r for r in rows if r["set"] == "k2"]
    return {
        "schema": REPORT_SCHEMA,
        "experiment_id": rules.EXPERIMENT_ID,
        "parent": rules.PARENT_ID,
        **ident,
        "pairs": len(registered),
        "compared": sum(1 for r in registered if r["state"] != "excluded"),
        "agree": sum(1 for r in registered if r["state"] == "agree"),
        "excluded": [_brief(r) for r in registered if r["state"] == "excluded"],
        "disagreements": [_brief(r) for r in registered if r["state"] == "differ"],
        "gate": dict(gate),
        "outcome": result["outcome"],
        "families_dropped": result["families_dropped"],
        "label": result["label"],
    }


def _brief(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "job_id",
        "mutant_id",
        "task_id",
        "kind",
        "checker_family",
        "offline_verdict",
        "vm_verdicts",
        "explanation",
    )
    return {k: row.get(k) for k in keys}


def summarize(
    rows: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    purpose: str,
    gate: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None,
) -> dict:
    def counts(subset: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "pairs": len(subset),
            "agree": sum(1 for r in subset if r["state"] == "agree"),
            "differ": sum(1 for r in subset if r["state"] == "differ"),
            "excluded": sum(1 for r in subset if r["state"] == "excluded"),
            "explanations": dict(Counter(r["explanation"] for r in subset if r["explanation"])),
        }

    out: dict[str, Any] = {"purpose": purpose, "gate": gate, "outcome": result}
    for set_name in rules_sets(rows):
        subset = [r for r in rows if r["set"] == set_name]
        by_family = defaultdict(list)
        for r in subset:
            by_family[r["checker_family"]].append(r)
        out[set_name] = {
            **counts(subset),
            "single_run_pairs": sum(1 for r in subset if r["runs_scored"] == 1),
            "by_family": {f: counts(v) for f, v in sorted(by_family.items())},
            "by_offline_verdict": {
                v: counts([r for r in subset if r["offline_verdict"] == v])
                for v in sorted({r["offline_verdict"] for r in subset})
            },
        }
    out["runs"] = run_stats(records)
    out["receipts"] = [
        {k: r.get(k) for k in ("job_id", "name", "statuses", "records", "stopped", "error")}
        for r in receipts
    ]
    return out


def rules_sets(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return [s for s in ("k2", "k2c") if any(r["set"] == s for r in rows)]


def run_stats(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reported only: attempt statuses, exclusion types, save paths, unsaved-at-read counts,
    the save-latency and run-time distributions."""
    latencies = [v for r in records for v in (r.get("save_latency") or {}).values()]
    run_s = [float(r["timings"]["run_s"]) for r in records if (r.get("timings") or {}).get("run_s")]

    def dist(values: Sequence[float]) -> dict[str, Any] | None:
        if not values:
            return None
        ordered = sorted(values)
        return {
            "n": len(ordered),
            "median": round(statistics.median(ordered), 3),
            "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 3),
            "max": round(ordered[-1], 3),
            "over_0_5s": sum(1 for v in ordered if v > 0.5),
        }

    return {
        "attempts": len(records),
        "statuses": dict(Counter(str(r.get("status")) for r in records)),
        "infrastructure_types": dict(
            Counter(
                str(r.get("infrastructure_type")) for r in records if r.get("status") != "scored"
            )
        ),
        "save_paths": dict(
            Counter(how for r in records for how in (r.get("save_paths") or {}).values())
        ),
        "unsaved_at_read_runs": sum(1 for r in records if r.get("unsaved_at_read")),
        "late_writes": sum(
            1 for r in records for v in (r.get("late_write") or {}).values() if v.get("changed")
        ),
        "metric_errors": sum(1 for r in records if r.get("metric_error")),
        "postconfig_failures": sum(int(r.get("postconfig_failures") or 0) for r in records),
        "save_latency_s": dist(latencies),
        "run_s": dist(run_s),
    }


def load_inputs(args: argparse.Namespace) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for run_dir in args.run_dir:
        records += read_jsonl(check_input(run_dir / "k2-runs.jsonl"))
        receipts.append(json.loads(check_input(run_dir / "lane-receipt.json").read_text()))
    sample = read_jsonl(check_input(args.sample))
    k2c = read_jsonl(check_input(args.k2c)) if args.k2c else []
    verdicts = read_jsonl(check_input(args.verdicts))
    notes = json.loads(check_input(args.notes_summary).read_text(encoding="utf-8"))
    digests = {
        "sample": sha256_file(args.sample),
        "verdicts": sha256_file(args.verdicts),
        "notes_summary": sha256_file(args.notes_summary),
        "k2c": sha256_file(args.k2c) if args.k2c else None,
    }
    return {
        "records": records,
        "receipts": receipts,
        "sample": sample,
        "k2c": k2c,
        "verdicts": verdicts,
        "nondeterministic": list((notes.get("lock") or {}).get("nondeterministic") or []),
        "digests": digests,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        required=True,
        help="a K2 lane run directory (k2-runs.jsonl, lane-receipt.json)",
    )
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--k2c", type=Path, default=None)
    parser.add_argument("--verdicts", type=Path, required=True, help="offline verdicts (lock)")
    parser.add_argument("--notes-summary", type=Path, required=True)
    parser.add_argument("--k2c-sha256", default=None, help="the registered K2-C list digest")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--only", default=None, help="set:pair ids (development reports)")
    args = parser.parse_args(argv)
    inputs = load_inputs(args)
    digests = inputs.pop("digests")
    purposes = {str(r.get("purpose")) for r in inputs["receipts"]}
    if purposes == {"k2"}:
        for key, expected in REGISTERED_INPUTS.items():
            if digests[key] != expected:
                raise ReportError(f"{key} is not the registered input ({digests[key]})")
        if not args.k2c or digests["k2c"] != args.k2c_sha256:
            raise ReportError("the k2 job's report reads the registered K2-C list")
    result = build(**inputs, only=args.only.split(",") if args.only else None)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "k2-pairs.jsonl").open("w", encoding="utf-8") as handle:
        for row in result["pairs"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {"schema": "q2m-k2-summary-v1", "inputs": digests, **result["summary"]}
    (args.out_dir / "k2-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    if "analysis_report" in result:
        report = {**result["analysis_report"], "inputs": digests}
        (args.out_dir / "k2-report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(
        json.dumps(
            {"purpose": result["purpose"], "gate": result["gate"], "outcome": result["outcome"]},
            sort_keys=True,
        )
    )
    return 0 if (result["outcome"] or {}).get("outcome") != "INCOMPLETE" else 4


if __name__ == "__main__":
    raise SystemExit(main())
