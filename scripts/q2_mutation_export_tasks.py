#!/usr/bin/env python3
"""Export the sanitized Q2 mutation task set and its seeded splits.

Reads a pinned OSWorld checkout and the hash receipts of the pinned HF file
cache, then writes, under ``--out`` (default ``program/evidence/q2-mutation``):

* ``sanitized-tasks/<task_id>.json``: the blind-author view of each in-scope
  task (instruction, apps, initial files with SHA-256, snapshot). No evaluator,
  expected, result, postconfig, metric or option field, at any depth.
* ``sanitized-tasks.manifest.json``: pins, selection rule and per-file SHA-256.
* ``splits.json``: seeded stratified dev / confirm / reserve task ids.
* ``--checker-derived`` (optional path): the per-task classification with
  metric function names. It is checker-derived and must never be shown to the
  blind requirement-spec author, so it is written only when asked for.

The OSWorld checkout must be at ``OSWORLD_COMMIT``; receipts must cover every
initial file. The script never imports OSWorld code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q2_mutation import schema, tasks  # noqa: E402

SPLIT_SEED = 42
DEV_FRACTION = 0.15
CONFIRM_SIZE = 120
DEFAULT_OUT = PROJECT_ROOT / "program" / "evidence" / "q2-mutation"


def read_receipts(path: Path) -> dict[str, str]:
    """``path -> sha256`` from the fetch receipts (verified against HF LFS)."""
    out: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 5:
            raise SystemExit(f"{path}:{number}: expected 5 tab-separated fields")
        rel, _size, sha, lfs, _origin = parts
        if lfs != "-" and lfs != sha:
            raise SystemExit(f"{path}:{number}: sha256 does not match the LFS oid")
        out[rel] = sha
    return out


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export(
    osworld: Path, receipts: Path, out: Path, checker_derived: Path | None
) -> dict[str, object]:
    head = git_head(osworld)
    if head != tasks.OSWORLD_COMMIT:
        raise SystemExit(f"OSWorld checkout is at {head}, expected {tasks.OSWORLD_COMMIT}")
    sha_by_path = read_receipts(receipts)
    records = tasks.scope_records(osworld)
    in_scope = [record for record in records if record.in_scope]
    task_dir = out / "sanitized-tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    stale = {p.name for p in task_dir.glob("*.json")} - {f"{r.task_id}.json" for r in in_scope}
    if stale:
        raise SystemExit(f"{task_dir} holds files outside the scope: {sorted(stale)[:5]}")
    file_hashes: dict[str, str] = {}
    for record in in_scope:
        sanitized = tasks.sanitize_task(record.raw, sha_by_path)
        text = _dump(sanitized.to_dict())
        if schema.find_forbidden_keys(json.loads(text)):
            raise SystemExit(f"{record.task_id}: forbidden key leaked into the export")
        path = task_dir / f"{record.task_id}.json"
        path.write_text(text, encoding="utf-8")
        file_hashes[record.task_id] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    splits = tasks.stratified_split(
        in_scope, seed=SPLIT_SEED, dev_fraction=DEV_FRACTION, confirm_size=CONFIRM_SIZE
    )
    manifest = {
        "schema_version": schema.SCHEMA_VERSION,
        "osworld_repo": tasks.OSWORLD_REPO,
        "osworld_commit": tasks.OSWORLD_COMMIT,
        "osworld_evaluator_commit": tasks.OSWORLD_EVALUATOR_COMMIT,
        "task_list": tasks.VERIFIED_TASK_LIST,
        "file_cache_repo": tasks.FILE_CACHE_REPO,
        "file_cache_revision": tasks.FILE_CACHE_REVISION,
        "licence": {
            "osworld_task_configs": "Apache-2.0 (xlang-ai/OSWorld LICENSE)",
            "file_cache": "apache-2.0 (HF dataset card); documents carry third-party content",
        },
        "selection": (
            "test_nogdrive.json tasks whose every metric reads a file or application "
            "config obtainable offline (classes 1A/1B/1V/1C), minus web-dependent tasks "
            "(config criteria plus manual instruction review)"
        ),
        "manual_web_exclusions": dict(sorted(tasks.MANUAL_WEB_EXCLUSIONS.items())),
        "manual_web_keeps": dict(sorted(tasks.MANUAL_WEB_KEEPS.items())),
        "n_verified_tasks": len(records),
        "n_in_scope": len(in_scope),
        "fields": list(schema.SANITIZED_TASK_KEYS),
        "forbidden_keys": sorted(schema.FORBIDDEN_TASK_KEYS),
        "sanitized_task_sha256": dict(sorted(file_hashes.items())),
    }
    (out / "sanitized-tasks.manifest.json").write_text(_dump(manifest), encoding="utf-8")
    split_doc = {
        "seed": SPLIT_SEED,
        "dev_fraction": DEV_FRACTION,
        "confirm_size": CONFIRM_SIZE,
        "rule": (
            "stratified by domain x checker-derived task class; per-stratum shuffle with "
            "random.Random(f'{seed}:{stratum}'); dev = round(dev_fraction * n), at least 1 "
            "in strata of 3+; confirm allocated proportionally (largest remainder)"
        ),
        "counts": {name: len(ids) for name, ids in splits.items()},
        **splits,
    }
    (out / "splits.json").write_text(_dump(split_doc), encoding="utf-8")
    if checker_derived is not None:
        checker_derived.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "task_id": record.task_id,
                "domain": record.domain,
                "task_class": record.task_class,
                "metric_classes": list(record.metric_classes),
                "funcs": list(record.funcs),
                "web_reason": record.web_reason,
                "in_scope": record.in_scope,
            }
            for record in records
        ]
        doc = {
            "warning": "checker-derived; never show to the blind requirement-spec author",
            "osworld_commit": tasks.OSWORLD_COMMIT,
            "class_counts": tasks.class_counts(records),
            "tasks": rows,
        }
        checker_derived.write_text(_dump(doc), encoding="utf-8")
    return {"in_scope": len(in_scope), "splits": split_doc["counts"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--checker-derived", type=Path, default=None)
    args = parser.parse_args(argv)
    summary = export(args.osworld, args.receipts, args.out, args.checker_derived)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
