"""D59 (iii): offline rescoring, one CPU-only Slurm job per A1 job, and its coverage. An
operator script, not code of record.

``submit`` (host): one ``s1a-cpu.sbatch`` run per A1 run directory, in the metric image, with
``--time=08:00:00`` (``rescore capture`` is serial, about 25 s per scored episode, so about 3 h
per 452-episode job, above the sbatch's 2 h default: bug B4), the run directory mounted
read-only at ``/ro/run`` and the output in ``<analysis>/rescore-<vm job>/rescored.jsonl``.
``sbatch`` returns at once; poll with ``squeue``. ``--dry-run`` prints the commands only::

    python3 -E -s -B rescore_jobs.py submit --export X --analysis-dir A \
        --inputs INPUTS --run-dir RUNS/1045 [--run-dir ...] --out A/rescore-jobs.json

``coverage`` (host): per job, counts only, with no verdict read: the scored attempts, the
scored attempts with a capture, the rows, the rows matched to a scored attempt, the rows with
a ``*_error`` field, the receipt's exit status. With ``--records`` (the merged a1.jsonl) and
``--plan`` (analysis time: this part reads verdicts), it adds the scored final records of
the primary and secondary sets whose verdict fell back to the live score (``corrected_score``
missing or null: ``records.outcome_array`` then reads the live score) and the
corrected-verdict flips split into checker corrections (``corrected_applies``) and
live-versus-offline replay mismatches (no correction applies)::

    python3 -E -s -B rescore_jobs.py coverage --export X --analysis-dir A \
        --run-dir RUNS/1045 [...] [--records A/a1.jsonl --plan PLAN] --out A/rescore-coverage.json
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

TIME_LIMIT = "08:00:00"
SBATCH = "infra/slurm/host-single-node/s1a-cpu.sbatch"
# G0 item 6's command in the metric image (as the dry run's job 1057 ran it on A0a).
OSWORLD = "/inputs/OSWorld"
FILE_CACHE = "/inputs/file_cache_1e112283/files"


def capture_argv() -> list[str]:
    return [
        "/opt/venv-lock/bin/python", "-m", "harness.q2_stage1.rescore", "capture",
        "--run-dir", "/ro/run", "--osworld", OSWORLD, "--file-cache", FILE_CACHE,
        "--out", "/out/rescored.jsonl",
    ]  # fmt: skip


def argv_hex(argv: Sequence[str]) -> str:
    return json.dumps(list(argv)).encode().hex()


def vm_job_id(run_dir: Path) -> str:
    receipt = O.read_json(run_dir / "lane-receipt.json")
    job_id = str(receipt.get("job_id") or run_dir.name)
    if job_id != run_dir.name:
        raise O.OpsError(f"{run_dir}: receipt job_id {job_id} differs from the directory name")
    return job_id


def sbatch_command(export: Path, analysis_dir: Path, inputs: Path, run_dir: Path) -> list[str]:
    vm = vm_job_id(run_dir)
    env = ",".join(
        [
            "ALL",
            "Q2M_MODE=run",
            f"Q2M_IMAGE_ID={O.METRIC_IMAGE_ID}",
            f"Q2M_ARGV_JSON_HEX={argv_hex(capture_argv())}",
            f"Q2M_SOURCE={export}",
            f"Q2M_RUN_DIR={analysis_dir / f'rescore-{vm}'}",
            f"Q2M_INPUTS={inputs}",
            f"Q2M_EXTRA_RO={run_dir}:/ro/run",
        ]
    )
    for part in env.split(",")[1:]:
        if "," in part.split("=", 1)[1]:
            raise O.OpsError(f"an --export value holds a comma: {part}")
    return [
        "sbatch", "--parsable", f"--time={TIME_LIMIT}", f"--job-name=s1a-rescore-{vm}",
        f"--export={env}", str(export / SBATCH),
    ]  # fmt: skip


def submit(args: argparse.Namespace) -> int:
    O.use_export(args.export)
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    runs = O.run_dirs_by_job(args.run_dir)
    out: dict[str, Any] = {"time_limit": TIME_LIMIT, "argv": capture_argv(), "jobs": {}}
    for job, run_dir in runs.items():
        vm = vm_job_id(run_dir)
        target = args.analysis_dir / f"rescore-{vm}"
        if (target / "rescored.jsonl").exists():
            raise O.OpsError(f"{target}/rescored.jsonl exists (capture opens --out with 'w')")
        command = sbatch_command(args.export.resolve(), args.analysis_dir, args.inputs, run_dir)
        entry: dict[str, Any] = {"vm_job": vm, "run_dir": str(run_dir), "command": command}
        if args.dry_run:
            print(shlex.join(command))
        else:
            target.mkdir(parents=True, exist_ok=True)
            done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
            if done.returncode != 0:
                raise O.OpsError(f"sbatch failed for {job}: {done.stderr.strip()}")
            entry["slurm_job"] = done.stdout.strip().split(";")[0]
            print(f"{job} vm {vm}: slurm {entry['slurm_job']}")
        out["jobs"][job] = entry
    if not args.dry_run:
        O.write_new(args.out, O.dumps(out))
    return 0


# --------------------------------------------------------------------------- coverage


def job_coverage(run_dir: Path, rescore_dir: Path) -> dict[str, Any]:
    """Coverage of one job's rescoring (counts only; no score is read)."""
    episodes = O.read_jsonl(run_dir / "episodes.jsonl")
    scored = [r for r in episodes if r.get("status") == "scored"]
    keys = {(r.get("slot"), r.get("attempt")) for r in scored}
    with_capture = sum(
        1 for r in scored if (O.episode_dir(run_dir, r) / "capture" / "capture.json").is_file()
    )
    rows_path = rescore_dir / "rescored.jsonl"
    rows = O.read_jsonl(rows_path) if rows_path.is_file() else []
    row_keys = [(r.get("slot"), r.get("attempt")) for r in rows]
    errors: Counter = Counter()
    for row in rows:
        for key in row:
            if key.endswith("_error"):
                errors[key] += 1
    receipts = sorted(rescore_dir.glob("receipt-*.json"))
    return {
        "scored_attempts": len(scored),
        "scored_attempts_with_capture": with_capture,
        "rows": len(rows),
        "rows_matched_to_scored_attempts": sum(1 for k in row_keys if k in keys),
        "rows_unmatched": sum(1 for k in row_keys if k not in keys),
        "duplicate_rows": len(row_keys) - len(set(row_keys)),
        "scored_attempts_without_row": len(keys - set(row_keys)),
        "rows_with_error": sum(1 for row in rows if any(k.endswith("_error") for k in row)),
        "errors_by_field": dict(sorted(errors.items())),
        "rows_raw_null": sum(1 for row in rows if row.get("raw") is None),
        "rows_corrected_null": sum(1 for row in rows if row.get("corrected") is None),
        "corrected_applies": sum(1 for row in rows if row.get("corrected_applies")),
        "live_offline_match": dict(
            sorted(Counter(str(row.get("live_offline_match")) for row in rows).items())
        ),
        "receipts": {
            path.name: {
                "exit_status": O.read_json(path).get("exit_status"),
                "job_id": O.read_json(path).get("job_id"),
            }
            for path in receipts
        },  # fmt: skip
        "rescored_sha256": O.sha256_file(rows_path) if rows_path.is_file() else None,
    }


def rows_by_attempt(rescore_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[Any, Any], Mapping]:
    return {(r.get("slot"), r.get("attempt")): r for r in rescore_rows}


def verdict_sources(
    finals: Mapping[Any, Mapping[str, Any]],
    tasks: Sequence[str],
    rows: Mapping[tuple[Any, Any], Mapping[str, Any]],
) -> dict[str, Any]:
    """For the scored final records of ``tasks``: how many corrected verdicts come from the
    offline rescoring and how many fell back to the live score, and the corrected-verdict
    flips split into checker corrections and replay mismatches (by task)."""
    task_set = set(tasks)
    fallback = offline = 0
    flips: dict[str, dict[str, int]] = {}
    unknown = 0
    for (_z, _s, t, _h, _r), rec in finals.items():
        if t not in task_set or rec["status"] != "scored":
            continue
        corrected = rec.get("corrected_score")
        if corrected is None:
            fallback += 1
            continue
        offline += 1
        if (float(corrected) == 1.0) == (float(rec["score"]) == 1.0):
            continue
        row = rows.get((rec.get("slot"), rec.get("attempt")))
        if row is None:
            kind = "unknown (no rescoring row)"
            unknown += 1
        elif row.get("corrected_applies"):
            kind = "checker_correction"
        else:
            kind = "replay_mismatch"
        per = flips.setdefault(t, {})
        per[kind] = per.get(kind, 0) + 1
    totals: Counter = Counter()
    for per in flips.values():
        totals.update(per)
    return {
        "scored_final_records": fallback + offline,
        "corrected_from_offline_rescoring": offline,
        "fell_back_to_live_score": fallback,
        "flips_by_task": dict(sorted(flips.items())),
        "flips_total": dict(sorted(totals.items())),
        "flips_unknown_kind": unknown,
    }


def coverage(args: argparse.Namespace) -> int:
    O.use_export(args.export)
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    runs = O.run_dirs_by_job(args.run_dir)
    out: dict[str, Any] = {"jobs": {}}
    all_rows: list[dict[str, Any]] = []
    for job, run_dir in runs.items():
        vm = vm_job_id(run_dir)
        rescore_dir = args.analysis_dir / f"rescore-{vm}"
        out["jobs"][job] = {"vm_job": vm, **job_coverage(run_dir, rescore_dir)}
        rows_path = rescore_dir / "rescored.jsonl"
        if rows_path.is_file():
            all_rows += O.read_jsonl(rows_path)
    if args.records:
        if not args.plan:
            raise O.OpsError("--records needs --plan")
        out["verdict_sources"] = sets_verdict_sources(args.records, args.plan, all_rows)
    O.write_new(args.out, O.dumps(out))
    print(json.dumps({job: {k: v for k, v in c.items() if k in ("scored_attempts", "rows",
                     "rows_with_error", "scored_attempts_without_row")}
                     for job, c in out["jobs"].items()}))  # fmt: skip
    return 0


def sets_verdict_sources(records: Path, plan_path: Path, rows: Sequence[Mapping]) -> dict:
    R = O.frozen("records")
    recs = R.read_jsonl(records)
    plan = O.read_json(plan_path)
    finals = R.final_records(recs)
    base = list(plan["base"])
    blocks = {int(k): v for k, v in plan.get("extension_blocks", {}).items()}
    done = R.completed_extension_blocks(recs, blocks)
    secondary = base + [t for b in done for t in blocks[b]]
    by_attempt = rows_by_attempt(rows)
    return {
        "note": (
            "records.outcome_array(value='corrected') reads the live score where corrected_score "
            "is missing or null (registered behaviour); a flip on a task without a checker "
            "correction (corrected_applies false) is a live-versus-offline replay mismatch"
        ),
        "primary": verdict_sources(finals, base, by_attempt),
        "secondary": {"blocks": done, **verdict_sources(finals, secondary, by_attempt)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub_submit = sub.add_parser("submit", help="one s1a-cpu.sbatch rescoring job per A1 job")
    sub_cover = sub.add_parser("coverage", help="rescoring coverage and live-score fallbacks")
    for cmd in (sub_submit, sub_cover):
        cmd.add_argument("--export", type=Path, required=True)
        cmd.add_argument("--analysis-dir", type=Path, required=True)
        cmd.add_argument("--run-dir", type=Path, action="append", required=True)
        cmd.add_argument("--out", type=Path, required=True)
    sub_submit.add_argument(
        "--inputs",
        type=Path,
        required=True,
        help="the checker-mutation study's inputs (OSWorld, file cache)",
    )
    sub_submit.add_argument("--dry-run", action="store_true")
    sub_cover.add_argument("--records", type=Path, help="merged A1 records (a1.jsonl)")
    sub_cover.add_argument("--plan", type=Path)
    args = parser.parse_args(argv)
    return submit(args) if args.command == "submit" else coverage(args)


if __name__ == "__main__":
    raise SystemExit(main())
