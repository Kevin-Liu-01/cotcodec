"""S2 v4 P0.9 (ii): the gold rows of the passing-side control (one per pool task with a gold).

Registration ``s2-arabic-cua-locale-v4`` P0.9: "the task's gold end state (the checker-mutation
study's reference gold for the task)". The reference gold is the one the study's controls define
(``harness.q2_mutation.controls.gold_pairs``, used unedited): every ``vm_file`` result the
checker reads is paired with a ``cloud_file`` expected file of the pinned file cache, the pairs
form a complete gold only if every metric has one, and a gold whose files are byte-identical to
the task's initial downloads is no answer (``gold_equals_initial``). Tasks without a complete
gold have no passing-side control (K0: ``runnable`` at best).

A row is what ``vm_lane.render_gold`` and ``vm_gold.py`` take: ``task_id``, ``job_id``
(``<task>__gold``), ``files`` {VM path: {rel (path in the file cache), sha256 (the pinned
receipt's)}} and ``candidate_sha256``, the SHA-256 of the first file in VM-path order (the K2
executor checks that one placed file carries it). Standard library only; run where the pinned
OSWorld tree is (the host's read-only copy):

  python3 -m harness.s2_locale.golds --osworld DIR --pool POOL_JSON --out golds.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

POOL = ("program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/"
        "pool-v3.json")  # fmt: skip
RECEIPTS = "program/evidence/q2-mutation/harness/file-cache-receipts.tsv"
SCHEMA = "s2v4-golds-v1"


def pool_tasks(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The registered pool: every pool-v3 task without an exclusion (106)."""
    return [t for t in pool["tasks"] if t.get("exclusion") is None]


def receipts(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and len(parts[2]) == 64:
            out[parts[0]] = parts[2]
    return out


def rel_of(url: str) -> str:
    """The file-cache relative path of a pinned file-cache URL (``main`` or the revision)."""
    from harness.q2_mutation.tasks import FILE_CACHE_PREFIX

    if not url.startswith(FILE_CACHE_PREFIX):
        raise ValueError(f"not a file-cache URL: {url}")
    _, _, rest = url[len(FILE_CACHE_PREFIX):].partition("/")
    return urllib.parse.unquote(rest)


def gold_row(raw: Mapping[str, Any], task_id: str, pins: Mapping[str, str]) -> dict[str, Any]:
    """The task's gold row, or ``{"task_id", "no_gold": reason}``."""
    from harness.q2_mutation.controls import gold_pairs
    from harness.q2_mutation.tasks import resolve_vm_path

    pairs, complete = gold_pairs(raw)
    if not complete:
        return {"task_id": task_id, "no_gold": "incomplete"}
    files = {}
    for vm_path, url in pairs:
        rel = rel_of(url)
        if rel not in pins:
            return {"task_id": task_id, "no_gold": f"{rel} not in the file-cache receipts"}
        files[vm_path] = {"rel": rel, "sha256": pins[rel]}
    initial = {}
    for step in raw.get("config", []):
        if step.get("type") == "download":
            for item in step.get("parameters", {}).get("files", []):
                try:
                    initial[resolve_vm_path(str(item["path"]))] = pins.get(rel_of(str(item["url"])))
                except ValueError:
                    continue
    if all(initial.get(vm) == f["sha256"] for vm, f in files.items()):
        return {"task_id": task_id, "no_gold": "gold_equals_initial"}
    first = sorted(files)[0]
    return {"task_id": task_id, "job_id": f"{task_id}__gold", "files": files,
            "candidate_sha256": files[first]["sha256"]}  # fmt: skip


def rows(osworld: Path, tasks: Iterable[Mapping[str, Any]],
         pins: Mapping[str, str]) -> list[dict[str, Any]]:  # fmt: skip
    from harness.q2_mutation.offline_eval import load_task

    return [gold_row(load_task(osworld, t["task_id"]), t["task_id"], pins) for t in tasks]


def digest(lines: Iterable[Mapping[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in lines)
    return hashlib.sha256(text.encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--pool", type=Path, default=Path(POOL))
    parser.add_argument("--receipts", type=Path, default=Path(RECEIPTS))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    tasks = pool_tasks(json.loads(args.pool.read_text(encoding="utf-8")))
    out = rows(args.osworld, tasks, receipts(args.receipts.read_text(encoding="utf-8")))
    golds = [r for r in out if "no_gold" not in r]
    args.out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in golds))
    missing = {r["task_id"]: r["no_gold"] for r in out if "no_gold" in r}
    print(json.dumps({"tasks": len(out), "golds": len(golds), "no_gold": len(missing),
                      "golds_sha256": digest(golds), "no_gold_by_task": missing}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
