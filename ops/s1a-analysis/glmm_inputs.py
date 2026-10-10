"""D59 (iii): the GLMM (secondary model, section 10.1) on the A1 records. An operator script,
not code of record.

``write``: one CSV per set with the registered writer, ``glmm.rows_from_records`` over
``records.final_records`` and ``glmm.write_csv`` (bug B7: ``glmm.py`` offers only
``synthetic``). ``primary.csv`` is the base set, the registered reading (section 11: every
rule reads the primary set unless it says otherwise; ``glmm.py``: "the analysis set");
``secondary.csv`` is base plus the completed extension blocks, reported beside it::

    python3 -E -s -B glmm_inputs.py write --export X --plan PLAN --records A/a1.jsonl \
        --guard A/report/guard.json --out-dir A/glmm-inputs

``submit``: one CPU-only ``s1a-cpu.sbatch`` job in the registered image (G0 item 12) that fits
both sets in parallel with ``glmm.R`` (200 refits, seed 42), writes each fit's exit code to
``<set>.exit`` (a backgrounded ``Rscript``'s failure would otherwise not reach the job's
exit status) and copies the image's package lock. ``--dry-run`` prints the command::

    python3 -E -s -B glmm_inputs.py submit --export X --inputs-dir A/glmm-inputs \
        --out-dir A/glmm-out --guard A/report/guard.json --out A/glmm-job.json

``collect``: each fit's exit code, convergence exactly as ``glmm.R`` writes it (``full``,
``reduced``, ``lrt_task_harness``, the bootstrap counts), a note when the bootstrap intervals
come from a full fit that did not converge or include refits that did not converge, the
package lock's SHA-256 against the registered ``abb8871d...`` (exit 3, after writing the
summary, when it differs) and the labels of ``run_report.py``'s ``guard.json``. It refuses,
writing nothing, until the job's receipt (``receipt-<slurm>.json``, which ``s1a-cpu.sbatch``
writes when the job ends, after both ``.exit`` files) is in the output directory, so it
cannot run before the fits end::

    python3 -E -s -B glmm_inputs.py collect --out-dir A/glmm-out --guard A/report/guard.json \
        --out A/glmm-summary.json

``inputs.json``, ``glmm-job.json`` and ``glmm-summary.json`` carry the labels of
``guard.json`` (D61: every output of an incomplete case is labelled).
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

SETS = ("primary", "secondary")
N_BOOT = 200
SEED = 42
TIME_LIMIT = "02:00:00"
SBATCH = "infra/slurm/host-single-node/s1a-cpu.sbatch"
REGISTERED_READING = (
    "primary (the base set): section 11's default analysis set and glmm.py's 'the analysis "
    "set'; the secondary fit (base plus completed extension blocks) is reported beside it"
)


def container_script(n_boot: int = N_BOOT, seed: int = SEED) -> str:
    fits = " ".join(SETS)
    return (
        "cp /opt/q2/r-packages.json /opt/q2/r-packages.sha256 /out/ || exit 90; "
        f"for f in {fits}; do "
        f"( Rscript /src/harness/q2_stage1/glmm.R /inputs/$f.csv /out/glmm-$f.json {n_boot} {seed} "
        ">/out/$f.log 2>&1; echo $? >/out/$f.exit ) & "
        "done; wait; "
        f'for f in {fits}; do test "$(cat /out/$f.exit)" = 0 || exit 91; done'
    )


def container_argv() -> list[str]:
    return ["sh", "-c", container_script()]


def write(args: argparse.Namespace) -> int:
    O.use_export(args.export)
    labels = O.labels_from_guard(args.guard)
    R, G = O.frozen("records"), O.frozen("glmm")
    targets = [args.out_dir / f"{name}.csv" for name in SETS] + [args.out_dir / "inputs.json"]
    for path in targets:
        if path.exists():
            raise O.OpsError(f"{path} exists; operator outputs are never overwritten")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    recs = R.read_jsonl(args.records)
    plan = O.read_json(args.plan)
    finals = R.final_records(recs)
    base = list(plan["base"])
    blocks = {int(k): v for k, v in plan.get("extension_blocks", {}).items()}
    done = R.completed_extension_blocks(recs, blocks)
    tasks = {"primary": base, "secondary": base + [t for b in done for t in blocks[b]]}
    meta: dict[str, Any] = {
        "labels": labels,
        "registered_reading": REGISTERED_READING,
        "writer": "glmm.rows_from_records(records.final_records(records), tasks) + glmm.write_csv",
        "records": O.sha256_file(args.records),
        "plan": O.sha256_file(args.plan),
        "guard": O.sha256_file(args.guard),
        "completed_extension_blocks": done,
        "sets": {},
    }
    for name in SETS:
        rows = G.rows_from_records(finals, tasks[name])
        path = args.out_dir / f"{name}.csv"
        G.write_csv(rows, path)
        meta["sets"][name] = {
            "tasks": len(tasks[name]),
            "rows": len(rows),
            "sizes": sorted({r["size"] for r in rows}),
            "sessions": sorted({r["session"] for r in rows}),
            "sha256": O.sha256_file(path),
        }
    O.write_new(args.out_dir / "inputs.json", O.dumps(meta))
    print(json.dumps({name: meta["sets"][name]["rows"] for name in SETS}))
    return 0


def sbatch_command(export: Path, inputs_dir: Path, out_dir: Path) -> list[str]:
    hex_argv = json.dumps(container_argv()).encode().hex()
    env = ",".join(
        [
            "ALL", "Q2M_MODE=run", f"Q2M_IMAGE_ID={O.GLMM_IMAGE_ID}",
            f"Q2M_ARGV_JSON_HEX={hex_argv}", f"Q2M_SOURCE={export}",
            f"Q2M_RUN_DIR={out_dir}", f"Q2M_INPUTS={inputs_dir}",
        ]
    )  # fmt: skip
    return [
        "sbatch", "--parsable", f"--time={TIME_LIMIT}", "--job-name=s1a-glmm",
        f"--export={env}", str(export / SBATCH),
    ]  # fmt: skip


def submit(args: argparse.Namespace) -> int:
    O.use_export(args.export)
    labels = O.labels_from_guard(args.guard)
    for name in SETS:
        if not (args.inputs_dir / f"{name}.csv").is_file():
            raise O.OpsError(f"{args.inputs_dir}/{name}.csv is missing (run 'write' first)")
    if any((args.out_dir / f"glmm-{name}.json").exists() for name in SETS):
        raise O.OpsError(f"{args.out_dir} already holds GLMM output")
    command = sbatch_command(args.export.resolve(), args.inputs_dir, args.out_dir)
    if args.dry_run:
        print(shlex.join(command))
        return 0
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if done.returncode != 0:
        raise O.OpsError(f"sbatch failed: {done.stderr.strip()}")
    job = done.stdout.strip().split(";")[0]
    record = {"labels": labels, "slurm_job": job, "command": command, "argv": container_argv()}
    O.write_new(args.out, O.dumps(record))
    print(f"slurm {job}")
    return 0


def _exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def fit_summary(out_dir: Path, name: str) -> dict[str, Any]:
    path = out_dir / f"glmm-{name}.json"
    out: dict[str, Any] = {
        "exit_code": _exit_code(out_dir / f"{name}.exit"),
        "json_present": path.is_file(),
    }
    if not path.is_file():
        return out
    fit = O.read_json(path)
    out["sha256"] = O.sha256_file(path)
    for key in ("n_episodes", "n_tasks", "n_boot", "seed", "glmmTMB_version", "TMB_version",
                "R_version", "full", "reduced", "lrt_task_harness"):  # fmt: skip
        if key in fit:
            out[key] = fit[key]
    boot = fit.get("bootstrap")
    if isinstance(boot, Mapping):
        out["bootstrap"] = {
            k: boot.get(k) for k in ("refits_failed", "refits_not_converged", "refits_used")
        }
    notes = []
    full = fit.get("full") or {}
    if full.get("ok") is not True:
        notes.append("the full fit did not converge (glmm.R's own status above)")
        if isinstance(boot, Mapping):
            notes.append(
                "its bootstrap share intervals come from that non-converged fit and include "
                f"{boot.get('refits_not_converged')} non-converged refits; glmm.R drops only "
                "failed refits"
            )
    elif isinstance(boot, Mapping) and boot.get("refits_not_converged"):
        notes.append(
            f"the share intervals include {boot.get('refits_not_converged')} refits that did not "
            "converge (glmm.R drops only failed refits)"
        )
    lrt = fit.get("lrt_task_harness")
    if isinstance(lrt, Mapping) and lrt.get("both_converged") is not True:
        notes.append("the task:harness likelihood-ratio test compares fits not both converged")
    out["notes"] = notes
    return out


def collect_summary(out_dir: Path) -> dict[str, Any]:
    lock = out_dir / "r-packages.json"
    lock_sha = O.sha256_file(lock) if lock.is_file() else None
    image_file = out_dir / "r-packages.sha256"
    image_sha = image_file.read_text(encoding="utf-8").split()[0] if image_file.is_file() else None
    receipts = sorted(out_dir.glob("receipt-*.json"))
    return {
        "registered_reading": REGISTERED_READING,
        "image_id": O.GLMM_IMAGE_ID,
        "r_packages": {
            "sha256": lock_sha,
            "registered_sha256": O.R_PACKAGES_SHA256,
            "matches_registered": lock_sha == O.R_PACKAGES_SHA256,
            "image_sha256_file": image_sha,
            "matches_image_file": lock_sha is not None and lock_sha == image_sha,
        },
        "fits": {name: fit_summary(out_dir, name) for name in SETS},
        "receipts": {
            p.name: {k: O.read_json(p).get(k) for k in ("job_id", "image_id", "exit_status")}
            for p in receipts
        },
    }


def collect(args: argparse.Namespace) -> int:
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    labels = O.labels_from_guard(args.guard)
    receipts = sorted(args.out_dir.glob("receipt-*.json"))
    if not receipts:
        raise O.OpsError(
            f"no receipt-*.json in {args.out_dir}: the GLMM job has not ended (s1a-cpu.sbatch "
            "writes its receipt last); wait until squeue shows none-running"
        )
    missing = [name for name in SETS if not (args.out_dir / f"{name}.exit").is_file()]
    if missing and all(O.read_json(p).get("exit_status") == 0 for p in receipts):
        raise O.OpsError(f"{args.out_dir}: no {', '.join(missing)}.exit beside a receipt of exit 0")
    out = {"labels": labels, **collect_summary(args.out_dir)}
    out["inputs"] = {"guard": O.sha256_file(args.guard)}
    O.write_new(args.out, O.dumps(out))
    match = out["r_packages"]["matches_registered"]
    print(json.dumps({"r_packages_match": match, "label": labels.get("incomplete"),
                      **{n: f.get("exit_code") for n, f in out["fits"].items()}}))  # fmt: skip
    if not match:
        print(
            "stop: the copied /opt/q2/r-packages.json does not hash to the registered "
            f"{O.R_PACKAGES_SHA256} (G0 item 12); record the cause",
            file=sys.stderr,
        )
        return 3
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write", help="primary.csv and secondary.csv with glmm.rows_from_records")
    w.add_argument("--export", type=Path, required=True)
    w.add_argument("--plan", type=Path, required=True)
    w.add_argument("--records", type=Path, required=True)
    w.add_argument("--guard", type=Path, required=True, help="run_report.py's guard.json (labels)")
    w.add_argument("--out-dir", type=Path, required=True)
    s = sub.add_parser("submit", help="fit both sets in the registered image (s1a-cpu.sbatch)")
    s.add_argument("--export", type=Path, required=True)
    s.add_argument("--inputs-dir", type=Path, required=True)
    s.add_argument("--out-dir", type=Path, required=True)
    s.add_argument("--guard", type=Path, required=True, help="run_report.py's guard.json (labels)")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("collect", help="exit codes, convergence and the package digest")
    c.add_argument("--out-dir", type=Path, required=True)
    c.add_argument(
        "--guard", type=Path, required=True,
        help="run_report.py's guard.json: the labels this output carries",
    )  # fmt: skip
    c.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return {"write": write, "submit": submit, "collect": collect}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
