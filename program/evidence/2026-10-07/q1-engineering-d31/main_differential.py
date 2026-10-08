"""Decision D31 evidence: verdict rows of the main branch's code (inline, before the
engineering pass) against this branch's reference-store path, on the CPU doctor's
synthetic corpus. Recorded analysis script; run in a GPU-less container.

    python main_differential.py --main /main --branch /work --out /out/differential

``--main`` and ``--branch`` are checkouts (read-only). The corpus is built by the
branch's doctor (its fixtures are byte-identical on main). Three runs, each through
its own checkout's runner and worker, 16 CPU slots, the doctor's limits:
``main-1`` and ``main-2`` (main, inline, twice) and ``store`` (branch, reference
store). Rows are compared without timing, run identity, process-specific text
and ``code_sha256`` (the code differs by construction).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

VOLATILE_TOP = ("gpu_seconds", "wall_seconds", "run_id", "code_sha256")
VOLATILE_DETAILS = ("item_wall_seconds", "item_started_at", "item_ended_at", "slot", "log_tail")
TEMPFILE = re.compile(r"/tmp/tmp[A-Za-z0-9_]+\.py")
ADDRESS = re.compile(r" at 0x[0-9a-f]+")


def normalized(row: dict) -> str:
    row = {k: v for k, v in row.items() if k not in VOLATILE_TOP}
    row["details"] = {k: v for k, v in row["details"].items() if k not in VOLATILE_DETAILS}
    return ADDRESS.sub(" at <address>", TEMPFILE.sub("<tempfile>", json.dumps(row, sort_keys=True)))


def final_rows(journal: Path) -> list[dict]:
    rows = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    status: dict[str, tuple[int, bool]] = {}
    for row in rows:
        key, attempt = row["details"]["item_key"], int(row.get("attempt", 1))
        best = status.get(key, (0, False))
        if attempt > best[0]:
            best = (attempt, False)
        if attempt == best[0] and row["details"].get("item_final"):
            best = (attempt, True)
        status[key] = best
    return [
        r
        for r in rows
        if status[r["details"]["item_key"]][1]
        and int(r.get("attempt", 1)) == status[r["details"]["item_key"]][0]
    ]


def index(rows: list[dict]) -> dict:
    out: dict = {}
    for row in rows:
        key = (row["kernel_id"], row["gate"], row["config_id"], row["tf32_policy"])
        out.setdefault(key, []).append(normalized(row))
    return {k: sorted(v) for k, v in out.items()}


def compare(left: list[dict], right: list[dict]) -> dict:
    a, b = index(left), index(right)
    keys = sorted(set(a) | set(b))
    differing = [k for k in keys if a.get(k) != b.get(k)]
    return {
        "rows": [len(left), len(right)],
        "keys": len(keys),
        "identical_keys": len(keys) - len(differing),
        "differing_kernels": sorted({k[0] for k in differing}),
        "differing_keys": [list(k) for k in differing],
    }


def run(checkout: Path, items: Path, journal: Path, workdir: Path) -> None:
    workdir.mkdir(parents=True)
    env = {**os.environ, "TRITON_INTERPRET": "1", "PYTHONPATH": str(checkout)}
    timeouts = json.dumps({"compile": 120.0, "correctness": 20.0, "timing": 120.0})
    subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.q1.runner",
            "--items",
            str(items),
            "--journal",
            str(journal),
            "--slots",
            ",".join(["cpu"] * 16),
            "--timeouts",
            timeouts,
            "--workdir",
            str(workdir),
        ],
        cwd=checkout,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--branch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True)
    sys.path.insert(0, str(args.branch))
    from harness.q1 import refschedule
    from scripts import run_q1_gate_doctor as doctor

    problems, kernels, manifest = doctor.build_corpus(args.out / "corpus")
    items = [i for i in doctor.work_items(problems, kernels, manifest) if i.gate != "timing"]
    plain = args.out / "items-inline.jsonl"
    # main's WorkItem has no requires/journal fields
    plain.write_text(
        "".join(
            json.dumps({k: v for k, v in asdict(i).items() if k not in {"requires", "journal"}})
            + "\n"
            for i in items
        )
    )
    store = args.out / "store-root"
    scheduled = refschedule.with_references([asdict(i) for i in items], root=str(store))
    stored = args.out / "items-store.jsonl"
    stored.write_text(
        "".join(
            json.dumps({**e, "journal": str(store / "references.jsonl")} if e.get("journal") else e)
            + "\n"
            for e in scheduled
        )
    )
    run(args.main, plain, args.out / "main-1.jsonl", args.out / "w-main-1")
    run(args.main, plain, args.out / "main-2.jsonl", args.out / "w-main-2")
    run(args.branch, stored, args.out / "store.jsonl", args.out / "w-store")
    main1 = final_rows(args.out / "main-1.jsonl")
    main2 = final_rows(args.out / "main-2.jsonl")
    branch = final_rows(args.out / "store.jsonl")
    uses = [json.loads(p.read_text()) for p in sorted((store / "uses").glob("*.json"))]
    lookups = [lk for u in uses for lk in u["lookups"]]
    report = {
        "items": len(items),
        "reference_items": sum(1 for e in scheduled if e.get("journal")),
        "main_vs_main": compare(main1, main2),
        "main_vs_store": compare(main1, branch),
        "store_lookups": len(lookups),
        "store_lookups_used_every_draw": sum(
            1 for lk in lookups if lk.get("used") and lk.get("inline_from_draw") is None
        ),
    }
    (args.out / "differential.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, dict)}, indent=1))
    for name in ("main_vs_main", "main_vs_store"):
        r = report[name]
        print(name, r["rows"], r["identical_keys"], "/", r["keys"], r["differing_kernels"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
