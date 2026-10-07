"""Dev-split smoke test of the document and outside-site operators on real OSWorld files.

Harness validation only. For each development-split task whose gold and
initial end states are one office file at the same VM path (as listed in the
harness's control jobs), it:

1. checks the SHA-256 of both files against the job list;
2. saves gold (the base), initial, and the base once more (the null mutant)
   through ``uno_apply.py`` in the LO-VM image;
3. plans only operators that need no requirement spec (``document`` and
   ``outside`` targets) against an empty, unserialized requirement set;
4. applies the recipes and runs the purity checks against the null mutant.

It reports per operator how many recipes applied and passed purity, and the
snapshot-level drift between base and null mutant. It never runs a checker and
never reports labels: without the blind author's spec the labels mean nothing.
The task ids it touched are listed so the confirmatory analysis can mark them.

Usage (inside the LO-VM image)::

    python3 -m harness.q2_mutation.operators.devsmoke --jobs /ro/devjobs/jobs-dev.jsonl \
        --out /out/devsmoke --profile-template /home/user/.config/libreoffice/4/user
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from harness.q2_mutation.operators import registry
from harness.q2_mutation.operators._diff import diff
from harness.q2_mutation.operators._snapshot import SnapshotError, snapshot
from harness.q2_mutation.operators.pipeline import (
    apply_manifest,
    is_admitted,
    make_context,
    plan_task,
    resave_row,
    verify,
    write_jsonl,
)
from harness.q2_mutation.operators.validate import run_uno
from harness.q2_mutation.schema import RequirementSpec

OFFICE_SUFFIXES = {".xlsx": "xlsx", ".docx": "docx", ".pptx": "pptx"}
NO_SPEC_AUTHOR = "operator-devsmoke-no-requirements"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_pairs(jobs: list[dict]) -> list[dict]:
    by_task: dict[str, dict[str, dict]] = defaultdict(dict)
    for job in jobs:
        by_task[job["task_id"]][job["kind"]] = job
    pairs = []
    for task_id, kinds in sorted(by_task.items()):
        gold, initial = kinds.get("gold"), kinds.get("initial")
        if not gold or not initial or len(gold["files"]) != 1 or len(initial["files"]) != 1:
            continue
        (vm_path, gold_file), = gold["files"].items()
        (vm_initial, initial_file), = initial["files"].items()
        family = OFFICE_SUFFIXES.get(Path(vm_path).suffix.lower())
        if family is None or vm_path != vm_initial:
            continue
        pairs.append({"task_id": task_id, "family": family, "vm_path": vm_path,
                      "gold": gold_file, "gold_sha256": gold["candidate_sha256"],
                      "initial": initial_file, "initial_sha256": initial["candidate_sha256"]})
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--jobs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--soffice", default="/usr/bin/soffice")
    parser.add_argument("--display", default=":99")
    parser.add_argument("--profile-template", default=None)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args(argv)
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    jobs = [json.loads(line) for line in Path(args.jobs).read_text().splitlines() if line.strip()]
    pairs = []
    rejected = []
    for pair in task_pairs(jobs):
        ok = (sha256(Path(pair["gold"])) == pair["gold_sha256"]
              and sha256(Path(pair["initial"])) == pair["initial_sha256"])
        (pairs if ok else rejected).append(pair)
    name_of = {p["task_id"]: Path(p["vm_path"]).name for p in pairs}

    def rel(kind: str, task_id: str) -> str:
        return f"saved/{kind}/{task_id}/{name_of[task_id]}"

    rows = []
    for p in pairs:
        rows.append({"mutant_id": f"{p['task_id']}-base", "family": p["family"],
                     "input": p["gold"],
                     "output": rel("base", p["task_id"]), "steps": []})
        rows.append({"mutant_id": f"{p['task_id']}-initial", "family": p["family"],
                     "input": p["initial"], "output": rel("initial", p["task_id"]), "steps": []})
    saved = run_uno(root, rows, "resave", args)
    null_rows = [
        resave_row(f"{p['task_id']}-null", p["family"], rel("base", p["task_id"]),
                   rel("null", p["task_id"]))
        for p in pairs if saved.get(f"{p['task_id']}-base", {}).get("status") == "ok"
    ]
    nulls = run_uno(root, null_rows, "null", args)

    ops = registry()
    wanted = [name for name, cls in ops.items() if cls.target in {"document", "outside"}]
    summary: dict = {"tasks": [], "rejected_hash": [p["task_id"] for p in rejected],
                     "null_drift": {}, "operators": {}}
    plans = []
    for p in pairs:
        task_id = p["task_id"]
        base = root / rel("base", task_id)
        initial = root / rel("initial", task_id)
        if nulls.get(f"{task_id}-null", {}).get("status") != "ok" or not initial.exists():
            summary["tasks"].append({"task_id": task_id, "status": "save-failed"})
            continue
        try:
            drift = diff(snapshot(base, p["family"]), snapshot(root / rel("null", task_id),
                                                              p["family"]))
            spec = RequirementSpec(task_id, NO_SPEC_AUTHOR, (), ())
            ctx = make_context(task_id, spec, base, initial, p["family"], p["vm_path"])
            records, _skips = plan_task(ctx, operators=wanted)
        except (SnapshotError, ValueError, KeyError) as exc:
            summary["tasks"].append({"task_id": task_id, "status": f"snapshot: {exc}"[:300]})
            continue
        summary["null_drift"][task_id] = Counter(c.kind for c in drift)
        summary["tasks"].append({"task_id": task_id, "family": p["family"], "status": "ok",
                                 "planned": len(records)})
        plans.append((p, base, records))
    office_rows = []
    for p, _base, records in plans:
        office_rows += apply_manifest(records, rel("base", p["task_id"]), "mutants")
    applied = run_uno(root, office_rows, "apply", args) if office_rows else {}

    per_op: dict[str, Counter] = defaultdict(Counter)
    failures: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    results = []
    for p, base, records in plans:
        reference = root / rel("null", p["task_id"])
        for record in records:
            mutant = root / "mutants" / record["mutant_id"] / base.name
            log = applied.get(record["mutant_id"])
            done = verify(record, reference, mutant if mutant.exists() else None, log)
            results.append(done)
            op = record["operator"]
            per_op[op]["planned"] += 1
            per_op[op]["applied"] += int(bool(log and log.get("status") == "ok"))
            per_op[op]["admitted"] += int(is_admitted(done))
            for item in done["purity_checks"]:
                if not item["passed"]:
                    failures[op][item["name"]] += 1
                    examples[op].append(f"{p['task_id'][:8]} {item['name']}: "
                                        f"{item['detail'][:240]}")
    write_jsonl(root / "results.jsonl", results)
    for op in sorted(per_op):
        summary["operators"][op] = {**per_op[op], "failed_checks": dict(failures[op]),
                                    "examples": examples[op][:5]}
    summary["touched_task_ids"] = sorted(p["task_id"] for p, _b, _r in plans)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    for op, info in sorted(summary["operators"].items()):
        print(f"{op:45s} planned={info['planned']} applied={info['applied']} "
              f"admitted={info['admitted']} failed={info['failed_checks']}")
    print(json.dumps({"tasks": len(summary["tasks"]), "rejected": summary["rejected_hash"],
                      "null_drift": summary["null_drift"]}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
