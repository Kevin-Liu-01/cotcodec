"""Pre-freeze design counts for q2-evaluator-mutation-v1 (third draft).

Answers the second review's counting defects from task configs, the probe map
and the committed dev evidence only. Reads no spec, mutant or verdict of a
confirm or reserve task.

Run on the H100 host (system Python 3.10), from a staged tree of the branch:

    python3 recount.py --src <staged tree> --inputs <q2 inputs dir> \
        --jobs-dir <target-counts-v1 run dir> --out counts.json

* targets per split (``campaign.select_targets`` on the target-count run's
  control jobs) with their checker family;
* P3 / P4 populations at the code's cell-level rule (``campaign.is_probe_touched``,
  which also marks the two probe-informed operators): target tasks with at
  least one planned violation (extra-change) operator outside probe-touched
  cells, overall and per checker family (the family floor is 8 tasks);
* the P1 population: complete golds of confirm and reserve, split into golds
  with an office file the save stage rewrites (``LO_SAVE_EXTENSIONS``) and the
  rest, with the scoping probe's headless saves and the setup or postconfig
  steps the harness cannot replay;
* the dev ratios at the same rule from ``dev-mutants-v4`` (committed outcomes).
"""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--jobs-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.src))
    from harness.q2_mutation import campaign
    from harness.q2_mutation.offline_eval import build_initial_vm_root, checker_funcs, load_task
    from harness.q2_mutation.operators import all_operators
    from harness.q2_mutation.reachability import LO_SAVE_EXTENSIONS, build_plan, step_may_write

    label_of = {op.name: op.label_class for op in all_operators()}
    splits = json.loads((args.src / campaign.SPLITS_PATH).read_text())
    probe = json.loads((args.src / campaign.PROBE_TOUCHED).read_text())
    cells = campaign.probe_touched_cells(probe)
    osworld = args.inputs / "OSWorld"
    cache = args.inputs / "file_cache_1e112283" / "files"
    out: dict = {"rule": "campaign.is_probe_touched (probe cells and probe-informed operators)"}

    def untouched(task: str, family: str, has_initial: bool, label: str) -> list[str]:
        return [
            op
            for op in campaign.wanted_operators(family, has_initial)
            if label_of[op] == label and not campaign.is_probe_touched(cells, task, op)
        ]

    for split in ("dev", "confirm", "reserve"):
        task_ids = list(splits[split])
        raw = {t: load_task(osworld, t) for t in task_ids}
        jobs = []
        for line in (args.jobs_dir / f"jobs-{split}.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            job = json.loads(line)
            job["files"] = {
                vm: (local.replace("/inputs/", str(args.inputs) + "/", 1) if local else local)
                for vm, local in job["files"].items()
            }
            jobs.append(job)
        targets, _ = campaign.select_targets(jobs, task_ids, raw)
        by_task: dict[str, list[dict]] = defaultdict(list)
        for target in targets:
            by_task[target["task_id"]].append(target)
        rows = {}
        for task, ts in sorted(by_task.items()):
            fam = campaign.checker_family(checker_funcs(raw[task]))
            viol = sorted(
                {op for t in ts for op in untouched(task, t["family"], bool(t["initial"]),
                                                    "should_fail_violation")}
            )
            extra = sorted(
                {op for t in ts for op in untouched(task, t["family"], bool(t["initial"]),
                                                    "should_fail_extra_change")}
            )
            rows[task] = {
                "doc_families": sorted({t["family"] for t in ts}),
                "checker_family": fam,
                "untouched_violation_ops": viol,
                "untouched_extra_ops": extra,
            }
        def by(key: str, predicate) -> dict:
            return dict(Counter(key_fn for key_fn in (
                "+".join(r[key]) if isinstance(r[key], list) else r[key]
                for r in rows.values() if predicate(r))))
        out[split] = {
            "target_tasks": len(rows),
            "targets": len(targets),
            "targets_by_doc_family": dict(Counter(t["family"] for t in targets)),
            "target_tasks_by_checker_family": by("checker_family", lambda r: True),
            "violation_untouched_tasks": sum(1 for r in rows.values() if r["untouched_violation_ops"]),
            "violation_untouched_by_doc_family": by(
                "doc_families", lambda r: r["untouched_violation_ops"]),
            "violation_untouched_by_checker_family": by(
                "checker_family", lambda r: r["untouched_violation_ops"]),
            "extra_untouched_tasks": sum(1 for r in rows.values() if r["untouched_extra_ops"]),
            "extra_untouched_by_doc_family": by(
                "doc_families", lambda r: r["untouched_extra_ops"]),
            "extra_untouched_by_checker_family": by(
                "checker_family", lambda r: r["untouched_extra_ops"]),
            "tasks": rows,
        }
        if split == "dev":
            continue
        golds = {}
        for job in jobs:
            if job["kind"] != "gold":
                continue
            task = job["task_id"]
            vm_paths = sorted(job["files"])
            office = [p for p in vm_paths if posixpath.splitext(p)[1].lower() in LO_SAVE_EXTENSIONS]
            plan = build_plan(raw[task], vm_paths)
            post = any(step_may_write(str(step)) for step in plan.get("unemulated", []))
            with tempfile.TemporaryDirectory() as tmp:
                setup = build_initial_vm_root(raw[task], cache, Path(tmp)).unemulated_writes
            probes = probe["tasks"].get(task, {}).get("probes", [])
            golds[task] = {
                "suffixes": sorted({posixpath.splitext(p)[1].lower() for p in vm_paths}),
                "exposed": bool(office),
                "unemulated_writes": bool(post or setup),
                "probe_headless_saved": "lo_rt:gold_headless_save(ubuntu .13)" in probes,
            }
        counted = {t: g for t, g in golds.items() if not g["unemulated_writes"]}
        out[split]["p1"] = {
            "complete_golds": len(golds),
            "unemulated": sorted(t for t, g in golds.items() if g["unemulated_writes"]),
            "exposed": sum(1 for g in counted.values() if g["exposed"]),
            "not_exposed": {t: g["suffixes"] for t, g in sorted(counted.items())
                            if not g["exposed"]},
            "exposed_probe_saved": sum(
                1 for g in counted.values() if g["exposed"] and g["probe_headless_saved"]),
            "exposed_not_probe_saved": sorted(
                t for t, g in counted.items() if g["exposed"] and not g["probe_headless_saved"]),
            "not_exposed_probe_saved": sum(
                1 for g in counted.values() if not g["exposed"] and g["probe_headless_saved"]),
        }
    # Dev ratios at the cell-level rule, from the committed dev-mutants-v4 outcomes.
    dev_rows = [
        json.loads(line)
        for line in (args.src / "program/evidence/q2-mutation/integration/dev-mutants-v4/"
                     "outcomes.jsonl").read_text().splitlines()
        if line.strip()
    ]
    evaluable = [
        r for r in dev_rows
        if r["lock_status"] == "evaluable"
        and not campaign.is_probe_touched(cells, r["task_id"], r["operator"])
    ]
    dev = {}
    for label in ("should_pass_equiv", "should_pass_alt_solution", "should_fail_violation",
                  "should_fail_extra_change"):
        rows = [r for r in evaluable if r["label"] == label]
        tasks = sorted({r["task_id"] for r in rows})
        events = [r for r in rows if r["lock_event"] != "ok"]
        dev[label] = {
            "evaluable_tasks": len(tasks),
            "evaluable_mutants": len(rows),
            "mutants_per_task": round(len(rows) / len(tasks), 2) if tasks else None,
            "tasks": tasks,
            "event_tasks": sorted({r["task_id"] for r in events}),
            "events": len(events),
        }
    out["dev_v4_cell_level"] = dev
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    summary = {
        s: {k: v for k, v in out[s].items() if k != "tasks"} for s in ("dev", "confirm", "reserve")
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "tasks"}
                      for k, v in dev.items()}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
