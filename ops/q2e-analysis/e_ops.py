"""Operator steps for the registered analysis of `q2-stage1-successor-e-v1` (section 18 (iii)).

An operator script, not code of record. It never edits a file of the export; it calls the
registered commands (``harness.q2_stage1e.analysis``, ``harness.q2_stage1.rescore``,
``glmm.R``) from the read-only export of E's freeze commit and records what ran. Every output
is written once: a subcommand refuses to overwrite one.

Subcommands (host, system ``python3 -E -s -B``; each returns within seconds except
``submit-batch``, whose wait is bounded by ``--wait-max``)::

    e_ops.py live-records   # SHA-check each run's records against its DR0 file; concatenate
    e_ops.py submit-batch   # on an empty queue: the GLMM job, then one rescoring job per E job
    e_ops.py merge          # registered `rescore merge` per job, then e.jsonl (registered order)
    e_ops.py coverage       # rescoring coverage, live-score fallbacks, flips split by kind
    e_ops.py step NAME ...  # one cpu-step.sbatch job running `-m harness.q2_stage1e.analysis`
    e_ops.py glmm-collect   # exit code, convergence as glmm.R wrote it, R package lock digest
    e_ops.py provenance     # export, ledger, plan, code-of-record and input digests, versions

Paths come from the environment ``env.sh`` writes (R, X, PLAN, A, INPUTS).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

EXPORT_COMMIT = "f6144d6bf745d944cb016cfc2b9894e1dbf7eb66"
EXPERIMENT_ID = "q2-stage1-successor-e-v1"
REGISTRATION = "program/preregistrations/q2-stage1-successor-e-v1.md"
REGISTRATION_SHA256 = "47e65877aed069fe919d1a2976345b3d5755e4323a71b47f99ece61c6e2ae98b"
PLAN_REL = "program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json"
PLAN_FILE_SHA256 = "12bded251c08755a6b713e8f34f3f327b46e788d55904f2b7118b97675294de8"
PLAN_SHA256 = "4e7298a77670a1e77d1b7c4435722364799f70ea0b6cb093739fa876b25e474d"
S1A_REGISTRATION = "program/preregistrations/q2-stage1-rescoped-v1.md"
S1A_RECORDS = "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
S1A_RECORDS_SHA256 = "4af798f5908e48aaf84d116682c813311b5ae48096e3b7ed2299c1530c08c6c0"
METRIC_IMAGE = "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230"
GLMM_IMAGE = "sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed"
R_LOCK_SHA256 = "abb8871de4549732cd396dc60fc1f2aec78bf1fffad788cb841e8bf61668bfc7"
PY312 = "/home/kevin/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12"
S1A_CPU = "infra/slurm/host-single-node/s1a-cpu.sbatch"
CPU_STEP = "ops/s1a-analysis/cpu-step.sbatch"
RESCORE_TIME = "08:00:00"  # section 18 (iii) step 2
GLMM_TIME = "02:00:00"
GLMM_BOOT, GLMM_SEED = "200", "42"  # S1a's glmm.R call (G0 item 12; G-E5)
GLMM_INPUT = "e-primary.csv"
# The registered job order (section 5.3) and each job's VM (lane) job.
JOBS = (
    ("E-9B-E1", "1219"), ("E-4B-E1", "1222"), ("E-9B-E2", "1251"), ("E-4B-E2", "1254"),
    ("E-9B-E3", "1265"), ("E-4B-E3", "1268"), ("E-9B-E4", "1272"), ("E-4B-E4", "1275"),
)  # fmt: skip
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
INFRA_MARK = "**Infrastructure E runs that neither table above pins.**"


class OpsError(RuntimeError):
    pass


def env(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise OpsError(f"{name} is not set: source the analysis env.sh first")
    return Path(value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def write_new(path: Path, text: str) -> None:
    path = Path(path)
    if path.exists():
        raise OpsError(f"{path} exists; outputs are never overwritten")
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def dumps(value: Any) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def queue() -> list[str]:
    done = subprocess.run(["squeue", "-h", "-o", "%i %j %T %u"], capture_output=True, text=True,
                          timeout=30, check=False)  # fmt: skip
    if done.returncode != 0:
        raise OpsError(f"squeue failed: {done.stderr.strip()}")
    return [line for line in done.stdout.splitlines() if line.strip()]


def check_export(x: Path) -> None:
    if (x / ".git_sha").read_text(encoding="utf-8").strip() != EXPORT_COMMIT:
        raise OpsError(f"{x} is not the export of {EXPORT_COMMIT}")
    if sha256_file(x / REGISTRATION) != REGISTRATION_SHA256:
        raise OpsError("the export's registration is not the frozen file")
    if sha256_file(x / PLAN_REL) != PLAN_FILE_SHA256:
        raise OpsError("the export's plan file is not the registered one")


def run_dirs() -> list[tuple[str, str, Path]]:
    r = env("R")
    out = []
    for job, vm in JOBS:
        run = r / "runs" / vm
        manifest = read_json(run / "manifest.json")
        e = manifest.get("e") or {}
        name = f"E-{e.get('size')}-{e.get('session')}"
        if manifest.get("purpose") != "e" or name != job:
            raise OpsError(f"{run} is not {job}'s run directory")
        if str(read_json(run / "lane-receipt.json").get("job_id")) != vm:
            raise OpsError(f"{run}: the receipt names another job")
        out.append((job, vm, run))
    return out


# --------------------------------------------------------------------------- live records


def live_records(_args: argparse.Namespace) -> int:
    """Each run's records, receipt and manifest checked against the digests its DR0 file
    (the registered `analysis dr0`, re-run into A) read; then the records concatenated in
    the registered job order (the raw, unmerged records: e-live.jsonl)."""
    a = env("A")
    check_export(env("X"))
    checks: dict[str, Any] = {}
    parts: list[bytes] = []
    for job, vm, run in run_dirs():
        dr0 = read_json(a / f"dr0-{vm}.json")
        if dr0.get("job") != job:
            raise OpsError(f"dr0-{vm}.json names {dr0.get('job')}, not {job}")
        files = {name: sha256_file(run / name)
                 for name in ("episodes.jsonl", "lane-receipt.json", "manifest.json")}  # fmt: skip
        if files != dr0.get("files"):
            raise OpsError(f"{job}: the run directory's files differ from dr0-{vm}.json's digests")
        data = (run / "episodes.jsonl").read_bytes()
        parts.append(data if data.endswith(b"\n") or not data else data + b"\n")
        checks[job] = {"vm_job": vm, "files": files, "dr0_fires": dr0.get("fires"),
                       "records": sum(1 for x in data.splitlines() if x.strip())}  # fmt: skip
    out = a / "e-live.jsonl"
    if out.exists():
        raise OpsError(f"{out} exists")
    with out.open("xb") as handle:
        handle.write(b"".join(parts))
    checks["e-live.jsonl"] = sha256_file(out)
    write_new(a / "live-records.json", dumps(checks))
    print(json.dumps({"records": sum(v["records"] for k, v in checks.items() if k != "e-live.jsonl"),
                      "sha256": checks["e-live.jsonl"]}))  # fmt: skip
    return 0


# --------------------------------------------------------------------------- submissions


def argv_hex(argv: list[str]) -> str:
    return json.dumps(argv).encode().hex()


def s1a_cpu_command(name: str, time_limit: str, image: str, argv: list[str], run_dir: Path,
                    inputs: Path, extra_ro: str | None = None) -> list[str]:  # fmt: skip
    x, a = env("X"), env("A")
    parts = ["ALL", "Q2M_MODE=run", f"Q2M_IMAGE_ID={image}", f"Q2M_ARGV_JSON_HEX={argv_hex(argv)}",
             f"Q2M_SOURCE={x}", f"Q2M_RUN_DIR={run_dir}", f"Q2M_INPUTS={inputs}"]  # fmt: skip
    if extra_ro:
        parts.append(f"Q2M_EXTRA_RO={extra_ro}")
    for part in parts[1:]:
        if "," in part:
            raise OpsError(f"an --export value holds a comma: {part}")
    return ["sbatch", "--parsable", f"--time={time_limit}", f"--job-name={name}",
            f"--output={a}/logs/%x-%j.out", "--export=" + ",".join(parts), str(x / S1A_CPU)]  # fmt: skip


def rescore_argv() -> list[str]:
    return ["/opt/venv-lock/bin/python", "-m", "harness.q2_stage1.rescore", "capture",
            "--run-dir", "/ro/run", "--osworld", "/inputs/OSWorld",
            "--file-cache", "/inputs/file_cache_1e112283/files", "--out", "/out/rescored.jsonl"]  # fmt: skip


def glmm_argv() -> list[str]:
    script = (
        "cp /opt/q2/r-packages.json /opt/q2/r-packages.sha256 /out/ || exit 90; "
        f"Rscript /src/harness/q2_stage1/glmm.R /inputs/{GLMM_INPUT} /out/glmm-e-primary.json "
        f"{GLMM_BOOT} {GLMM_SEED} >/out/glmm.log 2>&1; rc=$?; echo $rc >/out/glmm.exit; exit $rc"
    )
    return ["sh", "-c", script]


def batch_commands() -> list[tuple[str, list[str], Path]]:
    a, inputs = env("A"), env("INPUTS")
    out = [("glmm", s1a_cpu_command("q2e-glmm", GLMM_TIME, GLMM_IMAGE, glmm_argv(), a / "glmm-out",
                                    a / "glmm-inputs"), a / "glmm-out")]  # fmt: skip
    for job, vm, run in run_dirs():
        target = a / f"rescore-{vm}"
        out.append((job, s1a_cpu_command(f"q2e-rescore-{vm}", RESCORE_TIME, METRIC_IMAGE,
                                         rescore_argv(), target, inputs, f"{run}:/ro/run"),
                    target))  # fmt: skip
    return out


def submit_batch(args: argparse.Namespace) -> int:
    """On an empty queue (every user's jobs; empty at ``--stable`` consecutive 2-second
    polls), submit the GLMM job, then one rescoring job per E job, and record them."""
    a = env("A")
    check_export(env("X"))
    record, lock = a / "submit-batch.json", a / "submit-batch.lock"
    if record.exists():
        raise OpsError(f"{record} exists: the batch was submitted")
    glmm_input = a / "glmm-inputs" / GLMM_INPUT
    if not glmm_input.is_file():
        raise OpsError(f"{glmm_input} is missing (analysis glmm-input first)")
    commands = batch_commands()
    for _name, _cmd, target in commands:
        if target.exists():
            raise OpsError(f"{target} exists")
    if args.dry_run:
        for name, cmd, _target in commands:
            print(name, " ".join(cmd))
        return 0
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(f"{os.getpid()} {utc()}\n")
    deadline = time.monotonic() + args.wait_max
    empty = 0
    polls = 0
    while True:
        polls += 1
        try:
            busy = queue()
        except (OpsError, subprocess.TimeoutExpired) as err:  # a failed poll counts as busy
            busy = [f"squeue failed: {err}"]
        empty = 0 if busy else empty + 1
        if empty >= args.stable:
            break
        if time.monotonic() > deadline:
            lock.unlink()
            print(f"{utc()} still busy after {polls} polls: {busy}")
            return 4
        time.sleep(2)
    out: dict[str, Any] = {"queue_empty_at": utc(), "polls": polls, "stable_polls": args.stable,
                           "glmm_input_sha256": sha256_file(glmm_input), "jobs": {}}  # fmt: skip
    for name, cmd, target in commands:
        target.mkdir(parents=True)
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False,
                              cwd=str(a))  # fmt: skip
        entry = {"command": cmd, "rc": done.returncode, "submitted_at": utc(),
                 "slurm_job": done.stdout.strip().split(";")[0], "stderr": done.stderr.strip()}  # fmt: skip
        out["jobs"][name] = entry
        print(f"{name}: rc {done.returncode} slurm {entry['slurm_job']}")
    out["queue_after"] = queue()
    write_new(record, dumps(out))
    lock.unlink()
    return 0 if all(v["rc"] == 0 for v in out["jobs"].values()) else 5


def step(args: argparse.Namespace) -> int:
    """One cpu-step.sbatch job (system python3 -E -s -B) running the registered CLI
    ``-m harness.q2_stage1e.analysis <args>`` with the export as its working directory."""
    x, a = env("X"), env("A")
    check_export(x)
    cmd = ["sbatch", "--parsable", f"--job-name=q2e-{args.name}", f"--time={args.time}",
           f"--output={a}/logs/%x-%j.out", str(x / CPU_STEP), "-m", "harness.q2_stage1e.analysis",
           *args.rest]  # fmt: skip
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False, cwd=str(x))
    entry = {"command": cmd, "cwd": str(x), "rc": done.returncode, "submitted_at": utc(),
             "slurm_job": done.stdout.strip().split(";")[0], "stderr": done.stderr.strip(),
             "queue_at_submission": queue()}  # fmt: skip
    write_new(a / f"step-{args.name}.json", dumps(entry))
    print(json.dumps({k: entry[k] for k in ("rc", "slurm_job")}))
    return 0 if done.returncode == 0 else 5


# --------------------------------------------------------------------------- merge, coverage


def merge(_args: argparse.Namespace) -> int:
    """The registered ``rescore merge`` per job (after its rescoring job's receipt exists and
    no rescoring job is in the queue), then e.jsonl: the merged files in the registered order."""
    x, a = env("X"), env("A")
    check_export(x)
    if any(" q2e-rescore-" in f" {line}" for line in queue()):
        raise OpsError("a rescoring job is still in the queue")
    out_all = a / "e.jsonl"
    if out_all.exists():
        raise OpsError(f"{out_all} exists")
    merged = []
    for job, vm, run in run_dirs():
        rdir = a / f"rescore-{vm}"
        if not list(rdir.glob("receipt-*.json")):
            raise OpsError(f"rescoring of {job} has not ended (no receipt in {rdir})")
        out = a / f"merged-{vm}.jsonl"
        if out.exists():
            raise OpsError(f"{out} exists")
        cmd = [sys.executable, "-E", "-s", "-B", "-m", "harness.q2_stage1.rescore", "merge",
               "--episodes", str(run / "episodes.jsonl"), "--rescored", str(rdir / "rescored.jsonl"),
               "--out", str(out)]  # fmt: skip
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False,
                              cwd=str(x))  # fmt: skip
        if done.returncode != 0:
            raise OpsError(f"merge failed for {job}: {done.stderr.strip()}")
        merged.append(out)
    with out_all.open("x", encoding="utf-8") as handle:
        for path in merged:
            handle.write(path.read_text(encoding="utf-8"))
    print(json.dumps({"e.jsonl": sha256_file(out_all),
                      **{p.name: sha256_file(p) for p in merged}}))  # fmt: skip
    return 0


def job_coverage(run: Path, rdir: Path) -> dict[str, Any]:
    """S1a's coverage counts (``ops/s1a-analysis/rescore_jobs.py``), no score read."""
    episodes = read_jsonl(run / "episodes.jsonl")
    scored = [r for r in episodes if r.get("status") == "scored"]
    keys = {(r.get("slot"), r.get("attempt")) for r in scored}

    def ep_dir(r: dict[str, Any]) -> Path:
        return run / "episodes" / f"{str(r['slot']).replace(':', '_')}.a{r['attempt']}"

    rows_path = rdir / "rescored.jsonl"
    rows = read_jsonl(rows_path) if rows_path.is_file() else []
    row_keys = [(r.get("slot"), r.get("attempt")) for r in rows]
    errors: Counter = Counter()
    error_tasks: Counter = Counter()
    for row in rows:
        for key in row:
            if key.endswith("_error"):
                errors[key] += 1
        if any(k.endswith("_error") for k in row):
            error_tasks[str(row.get("task_id"))] += 1
    return {
        "scored_attempts": len(scored),
        "scored_attempts_with_capture": sum(
            1 for r in scored if (ep_dir(r) / "capture" / "capture.json").is_file()),
        "rows": len(rows),
        "rows_matched_to_scored_attempts": sum(1 for k in row_keys if k in keys),
        "rows_unmatched": sum(1 for k in row_keys if k not in keys),
        "duplicate_rows": len(row_keys) - len(set(row_keys)),
        "scored_attempts_without_row": len(keys - set(row_keys)),
        "rows_with_error": sum(1 for row in rows if any(k.endswith("_error") for k in row)),
        "errors_by_field": dict(sorted(errors.items())),
        "rows_with_error_by_task": dict(sorted(error_tasks.items())),
        "rows_raw_null": sum(1 for row in rows if row.get("raw") is None),
        "rows_corrected_null": sum(1 for row in rows if row.get("corrected") is None),
        "corrected_applies": sum(1 for row in rows if row.get("corrected_applies")),
        "live_offline_match": dict(
            sorted(Counter(str(row.get("live_offline_match")) for row in rows).items())),
        "receipts": {p.name: {"exit_status": read_json(p).get("exit_status"),
                              "started_at": read_json(p).get("started_at"),
                              "finished_at": read_json(p).get("finished_at")}
                     for p in sorted(rdir.glob("receipt-*.json"))},
        "rescored_sha256": sha256_file(rows_path) if rows_path.is_file() else None,
    }  # fmt: skip


def verdict_sources(finals: dict, tasks: list[str], rows: dict) -> dict[str, Any]:
    """S1a's split (``rescore_jobs.verdict_sources``): corrected verdicts from rescoring,
    live-score fallbacks, the merge rule's metric-exception zeros, and the corrected-verdict
    flips by task as checker corrections or live-versus-offline replay mismatches."""
    task_set = set(tasks)
    fallback = offline = metric_zero = unknown = 0
    flips: dict[str, dict[str, int]] = {}
    replay_mismatch_records = 0
    for (_z, _s, t, _h, _r), rec in finals.items():
        if t not in task_set or rec["status"] != "scored":
            continue
        row = rows.get((rec.get("slot"), rec.get("attempt")))
        if row is not None and row.get("live_offline_match") is False:
            replay_mismatch_records += 1
        corrected = rec.get("corrected_score")
        if corrected is None:
            fallback += 1
            continue
        if rec.get("metric_exception"):
            metric_zero += 1
        else:
            offline += 1
        if (float(corrected) == 1.0) == (float(rec["score"]) == 1.0):
            continue
        if row is None:
            kind = "unknown (no rescoring row)"
            unknown += 1
        elif row.get("corrected_applies"):
            kind = "checker_correction"
        else:
            kind = "replay_mismatch"
        per = flips.setdefault(t, {})
        per[kind] = per.get(kind, 0) + 1
        if kind == "checker_correction" and row.get("live_offline_match") is False:
            key = "checker_correction_raw_replay_also_differs"
            per[key] = per.get(key, 0) + 1
    totals: Counter = Counter()
    for per in flips.values():
        totals.update(per)
    return {
        "scored_final_records": fallback + offline + metric_zero,
        "corrected_from_offline_rescoring": offline,
        "metric_exception_scored_0_by_merge_rule": metric_zero,
        "fell_back_to_live_score": fallback,
        "raw_replay_differs_from_live": replay_mismatch_records,
        "flips_by_task": dict(sorted(flips.items())),
        "flips_total": dict(sorted(totals.items())),
        "flips_unknown_kind": unknown,
    }


def coverage(_args: argparse.Namespace) -> int:
    x, a = env("X"), env("A")
    check_export(x)
    sys.path.insert(0, str(x))
    from harness.q2_stage1e import plan as PE  # noqa: PLC0415
    from harness.q2_stage1e import records as RE  # noqa: PLC0415

    out_path = a / "rescore-coverage.json"
    if out_path.exists():
        raise OpsError(f"{out_path} exists")
    plan = PE.load_plan(env("PLAN"))
    out: dict[str, Any] = {"jobs": {}}
    rows: dict = {}
    for job, vm, run in run_dirs():
        rdir = a / f"rescore-{vm}"
        out["jobs"][job] = {"vm_job": vm, **job_coverage(run, rdir)}
        if (rdir / "rescored.jsonl").is_file():
            for row in read_jsonl(rdir / "rescored.jsonl"):
                rows[(row.get("slot"), row.get("attempt"))] = row
    finals = RE.final_records(RE.read_jsonl(a / "e.jsonl"))
    tasks = list(plan["tasks"])
    d82 = [t for t in tasks if t not in plan["gold_defect_tasks_d82"]]
    report = a / "report.json"
    out["labels"] = read_json(report)["labels"] if report.is_file() else {
        "not_determined": "report.json not yet written"}
    out["note"] = ("records.outcome_array(value='corrected') reads the live score where "
                   "corrected_score is missing or null (registered behaviour); a flip on a task "
                   "without a checker correction (corrected_applies false) is a live-versus-"
                   "offline replay mismatch")  # fmt: skip
    out["verdict_sources"] = {
        "primary_113": verdict_sources(finals, tasks, rows),
        "d82_110": verdict_sources(finals, d82, rows),
        "secondary_s1a_base_32": verdict_sources(finals, list(plan["s1a_base"]), rows),
    }
    write_new(out_path, dumps(out))
    print(json.dumps({job: {k: v for k, v in c.items() if k in (
        "scored_attempts", "rows", "rows_with_error", "scored_attempts_without_row")}
        for job, c in out["jobs"].items()}))  # fmt: skip
    return 0


# --------------------------------------------------------------------------- GLMM


def glmm_collect(_args: argparse.Namespace) -> int:
    a = env("A")
    gdir = a / "glmm-out"
    out_path = a / "glmm-summary.json"
    if out_path.exists():
        raise OpsError(f"{out_path} exists")
    receipts = sorted(gdir.glob("receipt-*.json"))
    if not receipts:
        raise OpsError("the GLMM job has not ended (no receipt)")
    fit_path = gdir / "glmm-e-primary.json"
    fit = read_json(fit_path) if fit_path.is_file() else None
    lock = gdir / "r-packages.json"
    lock_sha = sha256_file(lock) if lock.is_file() else None
    summary: dict[str, Any] = {
        "input": {"file": GLMM_INPUT, "sha256": sha256_file(a / "glmm-inputs" / GLMM_INPUT)},
        "image": GLMM_IMAGE,
        "argv": glmm_argv(),
        "receipts": {p.name: read_json(p) for p in receipts},
        "exit_code": (gdir / "glmm.exit").read_text().strip() if (gdir / "glmm.exit").is_file() else None,
        "r_packages_sha256": lock_sha,
        "r_packages_registered": R_LOCK_SHA256,
        "r_packages_match": lock_sha == R_LOCK_SHA256,
        "fit_sha256": sha256_file(fit_path) if fit else None,
        "fit": {k: fit.get(k) for k in ("n_episodes", "n_tasks", "seed", "n_boot", "full", "reduced",
                                        "variance_components", "lrt_task_harness",
                                        "glmmTMB_version", "TMB_version", "R_version")}
        if fit else None,
        "note": ("with one Bernoulli episode per (task, harness, session) the "
                 "(1|task:harness:session) term is not identified apart from the Bernoulli "
                 "variance (registration section 11); the fit is reported as glmm.R wrote it"),
    }  # fmt: skip
    report = a / "report.json"
    summary["labels"] = read_json(report)["labels"] if report.is_file() else None
    write_new(out_path, dumps(summary))
    print(json.dumps({"exit_code": summary["exit_code"], "r_packages_match": summary["r_packages_match"],
                      "full": (fit or {}).get("full"), "reduced": (fit or {}).get("reduced")}))  # fmt: skip
    return 0 if summary["r_packages_match"] else 3


# --------------------------------------------------------------------------- provenance


def table_rows(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def section(text: str, heading: str) -> str:
    return text.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]


def provenance(args: argparse.Namespace) -> int:
    x, a = env("X"), env("A")
    check_export(x)
    out_path = a / f"provenance-{args.stage}.json"
    if out_path.exists():
        raise OpsError(f"{out_path} exists")
    reg = (x / REGISTRATION).read_text(encoding="utf-8")
    own, infra = section(reg, "23. Code of record").split(INFRA_MARK, 1)
    e_rows, infra_rows = table_rows(own), table_rows(infra)
    s1a_rows = table_rows(section((x / S1A_REGISTRATION).read_text(encoding="utf-8"),
                                  "20. Code of record"))  # fmt: skip
    changed = {p: s for table in (e_rows, infra_rows, s1a_rows) for p, s in table.items()
               if sha256_file(x / p) != s}  # fmt: skip
    ledger = {}
    for cmd in (["verify", EXPERIMENT_ID], ["check-chain"]):
        done = subprocess.run([PY312, "-E", "-s", "-B", "scripts/preregister.py", *cmd],
                              capture_output=True, text=True, timeout=120, check=False,
                              cwd=str(x))  # fmt: skip
        ledger[" ".join(cmd)] = {"rc": done.returncode, "stdout": done.stdout.strip()}
    sys.path.insert(0, str(x))
    import numpy  # noqa: PLC0415

    from harness.q2_stage1e import plan as PE  # noqa: PLC0415

    plan = PE.load_plan(env("PLAN"))
    inputs: dict[str, Any] = {}
    for job, vm, run in run_dirs():
        inputs[job] = {name: sha256_file(run / name)
                       for name in ("episodes.jsonl", "lane-receipt.json", "manifest.json")}  # fmt: skip
    for path in sorted(a.glob("*.json")) + sorted(a.glob("*.jsonl")) + sorted(a.glob("*/*.json*")) \
            + sorted(a.glob("glmm-inputs/*.csv")):  # fmt: skip
        if path.name.startswith("provenance-") or path.name.endswith(".lock"):
            continue
        inputs[str(path.relative_to(a))] = sha256_file(path)
    out = {
        "stage": args.stage,
        "at": utc(),
        "export": {"path": str(x), "git_sha": (x / ".git_sha").read_text().strip()},
        "registration": {"path": REGISTRATION, "sha256": sha256_file(x / REGISTRATION),
                         "registered": REGISTRATION_SHA256, "ledger": ledger},  # fmt: skip
        "plan": {"file_sha256": sha256_file(env("PLAN")), "plan_sha256": plan["plan_sha256"],
                 "registered_plan_sha256": PLAN_SHA256,
                 "match": plan["plan_sha256"] == PLAN_SHA256},  # fmt: skip
        "code_of_record": {"e_files": len(e_rows), "infra_files": len(infra_rows),
                           "s1a_section20_files": len(s1a_rows), "changed": changed},  # fmt: skip
        "s1a_records": {"path": S1A_RECORDS, "sha256": sha256_file(x / S1A_RECORDS),
                        "registered": S1A_RECORDS_SHA256},  # fmt: skip
        "inputs_and_outputs": inputs,
        "interpreter": {"python": sys.version, "executable": sys.executable,
                        "numpy": numpy.__version__, "platform": platform.platform(),
                        "flags": "-E -s -B"},  # fmt: skip
        "images": {"metric": METRIC_IMAGE, "glmm": GLMM_IMAGE},
        "ops_script_sha256": sha256_file(Path(__file__)),
    }
    ok = (not changed and all(v["rc"] == 0 for v in ledger.values())
          and out["plan"]["match"] and out["s1a_records"]["sha256"] == S1A_RECORDS_SHA256)  # fmt: skip
    out["pass"] = ok
    write_new(out_path, dumps(out))
    print(json.dumps({"pass": ok, "changed": changed,
                      "ledger": {k: v["rc"] for k, v in ledger.items()}}))  # fmt: skip
    return 0 if ok else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("live-records")
    sb = sub.add_parser("submit-batch")
    sb.add_argument("--wait-max", type=float, default=200.0)
    sb.add_argument("--stable", type=int, default=5)
    sb.add_argument("--dry-run", action="store_true")
    st = sub.add_parser("step")
    st.add_argument("--time", default="02:00:00")
    st.add_argument("name")
    st.add_argument("rest", nargs=argparse.REMAINDER)
    sub.add_parser("merge")
    sub.add_parser("coverage")
    sub.add_parser("glmm-collect")
    pv = sub.add_parser("provenance")
    pv.add_argument("--stage", choices=("pre", "post"), required=True)
    args = parser.parse_args(argv)
    handlers = {"live-records": live_records, "submit-batch": submit_batch, "step": step,
                "merge": merge, "coverage": coverage, "glmm-collect": glmm_collect,
                "provenance": provenance}  # fmt: skip
    try:
        return handlers[args.command](args)
    except OpsError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
