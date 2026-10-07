"""Gold and do-nothing controls, and the gold fixed-point test, as scoring jobs.

``make-jobs`` writes one job per (task, kind) for a split:

* ``gold``: every ``vm_file`` result path paired with a ``cloud_file``
  expected file gets that gold file; tasks whose ``vm_file`` results are not
  all paired with a gold file have no gold control (they need a constructed,
  spec-based positive control instead) and are listed as ``no_gold``.
* ``initial``: the do-nothing end state. Result paths that exist in the
  initial state keep their initial bytes (and are passed explicitly so that
  the reachability stage opens and saves them, as the VM's postconfig would).

``merge-lo`` replaces job files with the reachability stage's saved outputs:
the gold fixed-point candidate is LibreOffice-save(gold), the faithful
do-nothing candidate is LibreOffice-save(initial).

The checker-derived fields read here (result/expected getters) never leave
the harness side.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.offline_eval import file_cache_local, load_task
from harness.q2_mutation.tasks import FILE_CACHE_PREFIX, resolve_vm_path

KINDS = ("gold", "initial")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


def _metric_triples(evaluator: Mapping[str, Any]) -> list[tuple[Any, Any]]:
    funcs = _as_list(evaluator.get("func"))
    results = _as_list(evaluator.get("result"))
    expected = evaluator.get("expected")
    if isinstance(expected, list):
        expected_list = list(expected)
    else:
        expected_list = [expected] * len(funcs) if expected else [None] * len(funcs)
    results += [None] * (len(funcs) - len(results))
    expected_list += [None] * (len(funcs) - len(expected_list))
    return list(zip(results, expected_list, strict=False))


def gold_pairs(raw: Mapping[str, Any]) -> tuple[list[tuple[str, str]], bool]:
    """(vm result path, gold URL) pairs, and whether every vm_file result is covered."""
    pairs: list[tuple[str, str]] = []
    complete = True
    saw_vm_file = False
    for result, expected in _metric_triples(raw["evaluator"]):
        if not isinstance(result, Mapping) or result.get("type") != "vm_file":
            continue
        saw_vm_file = True
        if not isinstance(expected, Mapping) or expected.get("type") != "cloud_file":
            complete = False
            continue
        paths = _as_list(result.get("path"))
        urls = _as_list(expected.get("path"))
        if result.get("multi") != expected.get("multi") or len(paths) != len(urls):
            complete = False
            continue
        for path, url in zip(paths, urls, strict=True):
            if str(url).startswith(FILE_CACHE_PREFIX):
                pairs.append((resolve_vm_path(str(path)), str(url)))
            else:
                complete = False
    return pairs, (complete and saw_vm_file and bool(pairs))


def result_paths(raw: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    for result, _ in _metric_triples(raw["evaluator"]):
        if isinstance(result, Mapping) and result.get("type") == "vm_file":
            paths += [resolve_vm_path(str(p)) for p in _as_list(result.get("path"))]
    return sorted(set(paths))


def initial_files(raw: Mapping[str, Any], file_cache: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for step in raw.get("config", []):
        if step.get("type") != "download":
            continue
        for item in step.get("parameters", {}).get("files", []):
            out[resolve_vm_path(str(item["path"]))] = str(
                file_cache_local(file_cache, str(item["url"]))
            )
    return out


def _sha_files(files: Mapping[str, str | None]) -> str:
    digest = hashlib.sha256()
    for vm_path in sorted(files):
        local = files[vm_path]
        digest.update(vm_path.encode())
        digest.update(hashlib.sha256(Path(local).read_bytes()).digest() if local else b"-")
    return digest.hexdigest()


def make_jobs(
    osworld: Path, file_cache: Path, task_ids: Sequence[str], kinds: Sequence[str] = KINDS
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    report: dict[str, Any] = {"no_gold": [], "gold_equals_initial": []}
    for task_id in task_ids:
        raw = load_task(osworld, task_id)
        initial = initial_files(raw, file_cache)
        if "gold" in kinds:
            pairs, complete = gold_pairs(raw)
            if complete:
                files = {vm: str(file_cache_local(file_cache, url)) for vm, url in pairs}
                if all(
                    vm in initial and Path(initial[vm]).read_bytes() == Path(local).read_bytes()
                    for vm, local in files.items()
                ):
                    report["gold_equals_initial"].append(task_id)
                jobs.append(
                    {
                        "job_id": f"{task_id}__gold",
                        "mutant_id": f"{task_id}__gold",
                        "task_id": task_id,
                        "kind": "gold",
                        "files": files,
                        "candidate_sha256": _sha_files(files),
                    }
                )
            else:
                report["no_gold"].append(task_id)
        if "initial" in kinds:
            files = {vm: initial[vm] for vm in result_paths(raw) if vm in initial}
            jobs.append(
                {
                    "job_id": f"{task_id}__initial",
                    "mutant_id": f"{task_id}__initial",
                    "task_id": task_id,
                    "kind": "initial",
                    "files": files,
                    "candidate_sha256": _sha_files(files) if files else None,
                }
            )
    return jobs, report


def merge_lo(
    jobs: Sequence[Mapping[str, Any]], lo_rows: Sequence[Mapping[str, Any]], *, suffix: str = "lo"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Jobs whose files are the reachability stage's outputs; and excluded jobs."""
    by_id = {row["job_id"]: row for row in lo_rows}
    merged: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for job in jobs:
        row = by_id.get(job["job_id"])
        if row is None or row.get("infra_error"):
            excluded.append(
                {"job_id": job["job_id"], "reason": (row or {}).get("infra_error", "no LO row")}
            )
            continue
        files = dict(job["files"])
        files.update(row.get("outputs", {}))
        merged.append(
            {
                **job,
                "job_id": f"{job['job_id']}__{suffix}",
                "mutant_id": f"{job['mutant_id']}__{suffix}",
                "files": files,
                "saved_via": "gui_faithful_lo_save",
                "lo_build": row.get("lo_build"),
            }
        )
    return merged, excluded


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), "utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("make-jobs")
    make.add_argument("--osworld", type=Path, required=True)
    make.add_argument("--file-cache", type=Path, required=True)
    make.add_argument("--splits", type=Path, required=True)
    make.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    make.add_argument("--out", type=Path, required=True)
    merge = sub.add_parser("merge-lo")
    merge.add_argument("--jobs", type=Path, required=True)
    merge.add_argument("--lo-rows", type=Path, nargs="+", required=True)
    merge.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "make-jobs":
        splits = json.loads(args.splits.read_text(encoding="utf-8"))
        jobs, report = make_jobs(args.osworld, args.file_cache, splits[args.split])
        _write_jsonl(args.out, jobs)
        (args.out.parent / f"{args.out.stem}.report.json").write_text(
            json.dumps(report, indent=1, sort_keys=True), "utf-8"
        )
        print(json.dumps({"jobs": len(jobs), **{k: len(v) for k, v in report.items()}}))
    else:
        rows = [row for path in args.lo_rows for row in _read_jsonl(path)]
        merged, excluded = merge_lo(_read_jsonl(args.jobs), rows)
        _write_jsonl(args.out, merged)
        _write_jsonl(args.out.with_suffix(".excluded.jsonl"), excluded)
        print(json.dumps({"merged": len(merged), "excluded": len(excluded)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
