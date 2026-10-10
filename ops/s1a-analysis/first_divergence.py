"""D59 (iii): first divergence with the registered functions (section 9 item 11). An operator
script, not code of record.

Usage (host, where the step logs stay under section 16)::

    python3 -E -s -B first_divergence.py --export X --plan plan-a0a.json \
        --records a1.jsonl --run-dir RUNS/1045 [--run-dir ...] --guard A/report/guard.json \
        --out first-divergence.json

The registered CLI never passes step logs to ``analysis.report`` (bug B5), so this step does,
with the choices D59 fixes: base tasks only, scored final records only (``records.final_records``:
the last attempt of each slot), and that final attempt's step log. A slot id is
``<job>:<block>:<index>``, so each record's ``steps.jsonl`` is looked up in its own job's run
directory (``<run>/episodes/<slot with ':' as '_'>.a<attempt>/steps.jsonl``). Pairs are
classified by ``records.first_divergence`` through ``analysis.divergence_summary`` (within and
between sessions), pooled and per size. The output holds counts only, never a step log, and
carries the labels of ``run_report.py``'s ``guard.json`` (incomplete, "not externally
anchored").
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

SET = (
    "base tasks; scored final records (the last attempt of each slot); the final attempt's "
    "steps.jsonl, looked up in its own job's run directory"
)


def step_logs(
    finals: Mapping[Any, Mapping[str, Any]], base: Sequence[str], runs: Mapping[str, Path]
) -> tuple[dict[Any, list[dict[str, Any]]], list[str]]:
    """(slot key -> steps of its final attempt, slots whose log was not found)."""
    base_set = set(base)
    logs: dict[Any, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for key, rec in sorted(finals.items()):
        if rec["status"] != "scored" or key[2] not in base_set:
            continue
        run_dir = runs.get(rec["job"])
        path = O.episode_dir(run_dir, rec) / "steps.jsonl" if run_dir is not None else None
        if path is None or not path.is_file():
            missing.append(f"{rec['slot']}.a{rec['attempt']}")
            continue
        logs[key] = O.read_jsonl(path)
    return logs, missing


def summarise(
    finals: Mapping[Any, Mapping[str, Any]], base: Sequence[str], runs: Mapping[str, Path]
) -> dict[str, Any]:
    A, R = O.frozen("analysis"), O.frozen("records")
    logs, missing = step_logs(finals, base, runs)
    steps: dict[str, Counter] = {"within": Counter(), "between": Counter()}
    groups: dict[tuple[str, str, str], list[tuple[str, list[dict[str, Any]]]]] = {}
    for (z, s, t, h, _r), rows in logs.items():
        groups.setdefault((z, t, h), []).append((s, rows))
    for eps in groups.values():
        for i in range(len(eps)):
            for j in range(i + 1, len(eps)):
                kind = "within" if eps[i][0] == eps[j][0] else "between"
                found = R.first_divergence(eps[i][1], eps[j][1])
                steps[kind][f"{found['kind']}@{found['step']}"] += 1
    return {
        "set": SET,
        "scored_base_final_records": sum(
            1 for k, r in finals.items() if r["status"] == "scored" and k[2] in set(base)
        ),
        "step_logs_read": len(logs),
        "step_logs_missing": len(missing),
        "step_logs_missing_slots": missing[:200],
        "first_divergence": A.divergence_summary(logs),
        "first_divergence_by_size": {
            z: A.divergence_summary({k: v for k, v in logs.items() if k[0] == z}) for z in R.SIZES
        },
        "kind_at_step": {kind: dict(sorted(c.items())) for kind, c in steps.items()},
        "note": (
            "descriptive (section 9 item 11): the guest's top-bar clock is on every screenshot, "
            "so nearly every pair parts at step 1 as 'environment'"
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument(
        "--guard", type=Path, required=True,
        help="run_report.py's guard.json: the labels this output carries",
    )  # fmt: skip
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    O.use_export(args.export)
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    R = O.frozen("records")
    labels = O.labels_from_guard(args.guard)
    plan = O.read_json(args.plan)
    finals = R.final_records(R.read_jsonl(args.records))
    runs = O.run_dirs_by_job(args.run_dir)
    out = {"labels": labels, **summarise(finals, plan["base"], runs)}
    out["inputs"] = {
        "records": O.sha256_file(args.records),
        "plan": O.sha256_file(args.plan),
        "guard": O.sha256_file(args.guard),
        "run_dirs": {job: str(path) for job, path in sorted(runs.items())},
    }
    O.write_new(args.out, O.dumps(out))
    print(json.dumps({"step_logs_read": out["step_logs_read"],
                      "step_logs_missing": out["step_logs_missing"],
                      "label": labels.get("incomplete")}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
