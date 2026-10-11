"""The registered items: reference golds and S1a's saved end states, by split.

Runs in the checker-mutation study's metric image (gold items need the OSWorld checkout and
the file cache) or anywhere for the S1a items. Reads task configs and, for S1a, the lane's
episode records and capture manifests; never a checker verdict of this study.

Gold items (``population`` ``gold``): the checker-mutation study's P1 population, rebuilt
from task configs by its own code: every task of the split with a complete gold
(``controls.make_jobs``) whose gold places at least one office file the save stage
rewrites (``reachability.LO_SAVE_EXTENSIONS``), minus tasks with a setup or postconfig step
the harness cannot replay that may write a checker-read file (``unemulated``). On the
splits this gives dev 17, confirm 67 and reserve 25 (the registered 92 are confirm plus
reserve).

S1a items: every scored episode whose capture holds an office file the checker read
(``capture.json`` ``vm_files``), one item per distinct captured state (``state_sha256``).
``s1a_pass``: every episode of the state scored 1 (the registered score, FAIL rule
included); ``s1a_fail``: every episode scored 0; ``s1a_mixed``: anything else (fractional
credit, or duplicates that disagree). Every pass and mixed state is an item; fail states are
a seeded sample of at most ``FAIL_PER_TASK`` per task (``random.Random(f"r04:s1a-fail:42:
{task}")`` over the task's sorted state digests). S1a's A1 tasks are all in the confirm
split; its A0a episodes are on dev tasks.

An item is a save-stage job (``job_id``, ``task_id``, ``files``: VM path -> local path)
plus what the scorer and the analysis need. Item files stay where they are (the file cache,
the lane's captures on the host); the manifest holds paths and digests only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.reachability import LO_SAVE_EXTENSIONS, build_plan, step_may_write

SCHEMA = "r04-items-v1"
FAIL_PER_TASK = 3
FAIL_SEED = "r04:s1a-fail:42"
POPULATIONS = ("gold", "s1a_pass", "s1a_fail", "s1a_mixed")
_S1A = "program/evidence/2026-10-10/q2-stage1-a1"
# S1a's lane runs (the directory name on the host is the VM job id): the committed digest of
# each run's episode records, and the committed per-file digests of its captures.
S1A_RUNS = {
    "1037": ("A0a", "8b2ce375ac444b8fce4a9796b1900d169a9e40da5bbc7e34ea386f03a8f0c724",
             "program/evidence/2026-10-09/q2-stage1-prefreeze/a0a/vm-1037/raw-sha256sums.txt"),
    "1045": ("A1-9B-S1", "a05dbf8473b83afef8522402e776460ff702e0fae2730f99c25f3978a51f7fc1",
             f"{_S1A}/a1-9b-s1/vm-1045/raw-sha256sums.txt"),
    "1048": ("A1-4B-S1", "733d73fdc49b7582aedb4f09e91a8e07c54c83941496e980f18fb668266b17bd",
             f"{_S1A}/a1-4b-s1/vm-1048/raw-sha256sums.txt"),
    "1051": ("A1-9B-S2", "53559050bdcf66ddc4ee28208aa33d60b5e22db52b3aadf0207a3193a5d53f2a",
             f"{_S1A}/a1-9b-s2/vm-1051/raw-sha256sums.txt"),
    "1062": ("A1-4B-S2", "1b33883129f012009e2ff3a5c7ef2d2093d00b8f562cca1f8d309b56978de4c2",
             f"{_S1A}/a1-4b-s2/vm-1062/raw-sha256sums.txt"),
}  # fmt: skip
SPLIT_RUNS = {"dev": ("1037",), "confirm": ("1045", "1048", "1051", "1062")}


class CaptureMismatch(RuntimeError):
    """A capture file differs from the digest S1a's evidence committed for it."""


def read_sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            out[rel.strip()] = digest
    return out


def verify_capture(run_dir: Path, capture: Path, sums: Mapping[str, str]) -> int:
    """Every file of the capture matches its committed digest, and every committed file of
    the capture exists. Returns the number of files checked."""
    prefix = "./" + capture.relative_to(run_dir).as_posix() + "/"
    listed = {rel for rel in sums if rel.startswith(prefix)}
    seen = set()
    for path in sorted(capture.rglob("*")):
        if not path.is_file():
            continue
        rel = "./" + path.relative_to(run_dir).as_posix()
        if sums.get(rel) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise CaptureMismatch(f"{rel} differs from S1a's committed digest")
        seen.add(rel)
    if listed - seen:
        raise CaptureMismatch(f"{sorted(listed - seen)[:3]} missing from {capture}")
    return len(seen)


def is_office(vm_path: str) -> bool:
    return Path(vm_path).suffix.lower() in LO_SAVE_EXTENSIONS


def split_of(splits: Mapping[str, Any], task_id: str) -> str | None:
    for name in ("dev", "confirm", "reserve"):
        if task_id in splits.get(name, []):
            return name
    return None


# --- golds ---------------------------------------------------------------------------------


def unemulated_writes(
    raw: Mapping[str, Any], file_cache: Path, files: Mapping[str, str]
) -> list[str]:
    """Setup or postconfig steps the harness cannot replay that may write a checker-read file
    (the checker-mutation study's ``unemulated`` rule: its offline scorer's setup and
    postconfig emulation and its save stage's plan)."""
    from harness.q2_mutation.offline_eval import (
        apply_postconfig_file_steps,
        build_initial_vm_root,
    )

    reasons: list[str] = []
    with tempfile.TemporaryDirectory(prefix="r04-items-") as tmp:
        vm_root = Path(tmp) / "vm"
        cache = Path(tmp) / "cache"
        vm_root.mkdir()
        cache.mkdir()
        report = build_initial_vm_root(raw, file_cache, vm_root)
        if report.unemulated_writes:
            reasons += [f"setup: {s}" for s in report.setup_unemulated]
        writes: list[bool] = []
        post = apply_postconfig_file_steps(raw, file_cache, vm_root, cache, writes)
        reasons += [f"postconfig: {s}" for s, w in zip(post, writes, strict=False) if w]
    plan = build_plan(raw, list(files))
    reasons += [f"save stage: {s}" for s in plan["unemulated"] if step_may_write(str(s))]
    return reasons


def gold_items(
    osworld: Path, file_cache: Path, splits: Mapping[str, Any], split: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from harness.q2_mutation.controls import make_jobs
    from harness.q2_mutation.offline_eval import load_task

    jobs, report = make_jobs(osworld, file_cache, splits[split], kinds=("gold",))
    items: list[dict[str, Any]] = []
    out: dict[str, Any] = {
        "split": split,
        "tasks": len(splits[split]),
        "no_gold": sorted(report["no_gold"]),
        "gold_equals_initial": sorted(report["gold_equals_initial"]),
        "not_exposed": [],
        "unemulated": {},
    }
    for job in jobs:
        task_id = job["task_id"]
        files = job["files"]
        if not any(is_office(p) for p in files):
            out["not_exposed"].append(task_id)
            continue
        raw = load_task(osworld, task_id)
        reasons = unemulated_writes(raw, file_cache, files)
        if reasons:
            out["unemulated"][task_id] = reasons
            continue
        items.append(
            {
                "schema": SCHEMA,
                "item_id": f"g:{task_id}",
                "job_id": f"g:{task_id}",
                "mutant_id": f"g:{task_id}",
                "task_id": task_id,
                "population": "gold",
                "split": split,
                "files": dict(files),
                "candidate_sha256": job["candidate_sha256"],
                "office_files": sorted(p for p in files if is_office(p)),
            }
        )
    out["items"] = len(items)
    out["not_exposed"] = sorted(out["not_exposed"])
    return items, out


# --- S1a end states -------------------------------------------------------------------------


def episode_dir(run_dir: Path, record: Mapping[str, Any]) -> Path:
    slot = str(record["slot"]).replace(":", "_")
    return run_dir / "episodes" / f"{slot}.a{record['attempt']}"


def population_of(scores: Iterable[Any]) -> str:
    values = [None if s is None else float(s) for s in scores]
    if values and all(v == 1.0 for v in values):
        return "s1a_pass"
    if values and all(v == 0.0 for v in values):
        return "s1a_fail"
    return "s1a_mixed"


def sample_fail_states(
    states: Sequence[Mapping[str, Any]], per_task: int = FAIL_PER_TASK
) -> list[str]:
    """The registered sample of fail states: at most ``per_task`` per task, seeded."""
    by_task: dict[str, list[str]] = defaultdict(list)
    for state in states:
        by_task[str(state["task_id"])].append(str(state["state_sha256"]))
    chosen: list[str] = []
    for task in sorted(by_task):
        digests = sorted(by_task[task])
        random.Random(f"{FAIL_SEED}:{task}").shuffle(digests)
        chosen += digests[:per_task]
    return sorted(chosen)


def s1a_states(
    runs: Mapping[str, Path],
    splits: Mapping[str, Any],
    sums: Mapping[str, Mapping[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Every distinct office-exposed captured state of the given lane runs (label -> dir).

    With ``sums`` (label -> committed per-file digests), every capture an item uses is
    checked file by file against S1a's evidence before it becomes an item."""
    states: dict[str, dict[str, Any]] = {}
    for label in sorted(runs):
        run_dir = runs[label]
        run_sums = (sums or {}).get(label)
        records = [
            json.loads(x)
            for x in (run_dir / "episodes.jsonl").read_text().splitlines()
            if x.strip()
        ]
        for record in sorted(records, key=lambda r: (str(r["slot"]), int(r["attempt"]))):
            if record.get("status") != "scored":
                continue
            capture = episode_dir(run_dir, record) / "capture"
            manifest_path = capture / "capture.json"
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            vm_files: dict[str, str] = manifest.get("vm_files") or {}
            if not any(is_office(p) for p in vm_files):
                continue
            digest = str(manifest["state_sha256"])
            if run_sums is not None:
                verify_capture(run_dir, capture, run_sums)
            episode = {
                "run": label,
                "job": record.get("job"),
                "slot": record["slot"],
                "attempt": record["attempt"],
                "score": record.get("score"),
                "harness": record.get("harness"),
                "size": record.get("size"),
            }
            if digest in states:
                states[digest]["episodes"].append(episode)
                continue
            task_id = str(record["task_id"])
            states[digest] = {
                "task_id": task_id,
                "state_sha256": digest,
                "split": split_of(splits, task_id),
                "capture_dir": str(capture),
                "files": {p: str(capture / "vm" / p.lstrip("/")) for p in sorted(vm_files)},
                "vm_files_sha256": dict(sorted(vm_files.items())),
                "office_files": sorted(p for p in vm_files if is_office(p)),
                "episodes": [episode],
            }
    out = []
    for digest in sorted(states):
        state = states[digest]
        state["population"] = population_of(e["score"] for e in state["episodes"])
        out.append(state)
    return out


def s1a_items(states: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fails = [s for s in states if s["population"] == "s1a_fail"]
    keep_fail = set(sample_fail_states(fails))
    items = []
    for state in states:
        if state["population"] == "s1a_fail" and state["state_sha256"] not in keep_fail:
            continue
        item_id = f"s:{state['task_id'][:8]}:{state['state_sha256'][:16]}"
        items.append(
            {"schema": SCHEMA, "item_id": item_id, "job_id": item_id, "mutant_id": item_id, **state}
        )
    report = {
        "states": len(states),
        "states_by_population": dict(Counter(s["population"] for s in states)),
        "tasks_by_population": {
            pop: len({s["task_id"] for s in states if s["population"] == pop})
            for pop in ("s1a_pass", "s1a_fail", "s1a_mixed")
        },
        "items": len(items),
        "items_by_population": dict(Counter(i["population"] for i in items)),
        "fail_states_sampled": len(keep_fail),
        "fail_per_task": FAIL_PER_TASK,
    }
    return items, report


def manifest_digest(items: Sequence[Mapping[str, Any]]) -> str:
    lines = sorted(json.dumps(i, sort_keys=True) for i in items)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    parser.add_argument("--osworld", type=Path)
    parser.add_argument("--file-cache", type=Path)
    parser.add_argument("--golds", action="store_true")
    parser.add_argument("--s1a-run", action="append", default=[], help="LABEL=RUN_DIR")
    parser.add_argument("--src", type=Path, default=Path("."), help="repository root")
    parser.add_argument("--out", type=Path, required=True, help="items JSONL")
    args = parser.parse_args(argv)
    splits = json.loads(args.splits.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    report: dict[str, Any] = {"schema": SCHEMA, "split": args.split}
    if args.golds:
        if args.osworld is None or args.file_cache is None:
            parser.error("--golds needs --osworld and --file-cache")
        golds, report["golds"] = gold_items(args.osworld, args.file_cache, splits, args.split)
        items += golds
    if args.s1a_run:
        runs = {k: Path(v) for k, v in (item.split("=", 1) for item in args.s1a_run)}
        sums = {}
        for label, run_dir in runs.items():
            if label not in S1A_RUNS:
                raise SystemExit(f"S1a run {label} is not registered")
            if label not in SPLIT_RUNS.get(args.split, ()):
                raise SystemExit(f"S1a run {label} is not a {args.split} run")
            job, episodes_sha, sums_path = S1A_RUNS[label]
            got = hashlib.sha256((run_dir / "episodes.jsonl").read_bytes()).hexdigest()
            if got != episodes_sha:
                raise SystemExit(f"S1a run {label} ({job}): episode records differ from evidence")
            sums[label] = read_sums(args.src / sums_path)
        states = s1a_states(runs, splits, sums)
        wrong = sorted({s["task_id"] for s in states if s["split"] != args.split})
        if wrong:
            raise SystemExit(f"S1a states outside split {args.split}: {wrong[:5]}")
        s1a, report["s1a"] = s1a_items(states)
        report["s1a"]["runs"] = {k: S1A_RUNS[k][0] for k in sorted(runs)}
        report["s1a"]["captures_verified"] = True
        items += s1a
    report["items"] = len(items)
    report["manifest_sha256"] = manifest_digest(items)
    _write_jsonl(args.out, items)
    args.out.with_suffix(".report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "golds"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
