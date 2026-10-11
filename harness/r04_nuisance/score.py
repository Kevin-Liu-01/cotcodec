"""Score every (item, cell): the pinned checker and the corrected comparator, in fresh processes.

Runs in the checker-mutation study's metric image (OSWorld's locked environment, GPU-less,
no network) and reuses the two registered offline scorers unchanged:

* gold items: ``offline_eval``'s worker (the pinned ``DesktopEnv.evaluate()`` with the stub
  VM over the task's initial state, the VM baseline files and the candidate files, one
  non-FAIL action), through ``rescore._job_worker`` so the corrected comparator can be
  installed first;
* S1a items: ``rescore._capture_worker`` over a capture directory (exactly what the live
  checker read, the task cache as the live evaluation left it, the episode's own last
  action). For a saved cell the scorer writes a derived capture: the captured files with
  the save stage's outputs put in place, and the manifest's digests updated.

``raw`` is the item as it is (gold unsaved; S1a as captured). A saved cell's item is merged
from the save stage's row (``controls.merge_lo``: a save that failed is excluded, never
scored on its pre-save bytes). Each checker version is scored ``--repeat`` times (2); a
timeout is retried twice and then is an infrastructure failure; scorings that disagree make
the (item, cell, checker) nondeterministic. ``zinv`` is scored only where a task's checker is
``compare_pptx_files``; elsewhere it equals the pinned verdict.

Output: one JSON row per (item, cell) in ``<out>/scores-<cell>.jsonl``; scores, verdicts,
digests and save events only, no document content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SCHEMA = "r04-scores-v1"
ZINV_FAMILY = "compare_pptx_files"
CHECKERS = ("pinned", "zinv")


def verdict_of(score: float | None, error: str | None) -> str:
    if error is not None or score is None:
        return "error"
    return "pass" if float(score) == 1.0 else "fail"


def remap_path(local: str | None, prefix_map: Mapping[str, str]) -> str | None:
    if local is None:
        return None
    for old, new in prefix_map.items():
        if local.startswith(old):
            return new + local[len(old) :]
    return local


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_cell_rows(cell_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(cell_dir.glob("reachability-*.jsonl")):
        for row in read_jsonl(path):
            if row["job_id"] in rows:
                raise ValueError(f"{cell_dir}: job {row['job_id']} has two save rows")
            rows[row["job_id"]] = row
    return rows


def save_summary(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "infra_error": (row.get("infra_error") or None) and str(row["infra_error"])[:300],
        "failures": row.get("failures", []),
        "saves": [
            {
                "vm_path": s.get("vm_path"),
                "reason": s.get("reason"),
                "written": s.get("written"),
                "changed": s.get("before_sha256") != s.get("after_sha256"),
                "after_sha256": s.get("after_sha256"),
                "seconds_to_write": s.get("seconds_to_write"),
                "dialogs": s.get("dialogs"),
            }
            for s in row.get("saves", [])
        ],
        "outputs": sorted(row.get("outputs", {})),
        "after_sha256": row.get("after_sha256"),
        "unemulated": (row.get("plan") or {}).get("unemulated", []),
        "lo_build": row.get("lo_build"),
        "profile_set": row.get("profile_set"),
        "activations_adapted": row.get("activations_adapted", []),
        "env_set": row.get("env_set"),
        "seconds": row.get("seconds"),
    }


def derived_capture(item: Mapping[str, Any], merged: Mapping[str, str | None], dest: Path) -> Path:
    """A capture directory holding ``merged`` (VM path -> file, None: absent) and the item's
    captured cache, with a manifest whose digests match (``rescore._capture_worker`` checks
    them)."""
    source = Path(item["capture_dir"])
    manifest = json.loads((source / "capture.json").read_text(encoding="utf-8"))
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "vm").mkdir(parents=True)
    vm_files: dict[str, str] = {}
    for vm_path, local in sorted(merged.items()):
        if local is None:
            continue
        data = Path(local).read_bytes()
        target = dest / "vm" / vm_path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        vm_files[vm_path] = hashlib.sha256(data).hexdigest()
    if (source / "cache").is_dir():
        shutil.copytree(source / "cache", dest / "cache")
    manifest["vm_files"] = vm_files
    manifest["state_sha256"] = hashlib.sha256(
        json.dumps(
            {"vm": vm_files, "cache": manifest.get("cache_files", {})}, sort_keys=True
        ).encode()
    ).hexdigest()
    manifest["r04_derived_from"] = item["state_sha256"]
    (dest / "capture.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), "utf-8")
    return dest


def _office_digests(files: Mapping[str, str | None]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for vm_path, local in sorted(files.items()):
        if Path(vm_path).suffix.lower() in (".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"):
            out[vm_path] = hashlib.sha256(Path(local).read_bytes()).hexdigest() if local else None
    return out


def score_checker(
    target: Any, payload: Mapping[str, Any], *, repeat: int, timeout: float
) -> dict[str, Any]:
    from harness.q2_stage1.rescore import run_worker

    runs = []
    infra_timeouts = 0
    for _ in range(max(1, repeat)):
        for _attempt in range(3):
            run = run_worker(target, dict(payload), timeout)
            if not run.get("infra"):
                break
            infra_timeouts += 1
        runs.append(run)
    scores = [r.get("score") for r in runs]
    errors = [r.get("error") for r in runs]
    infra = [
        bool(r.get("infra"))
        or str(r.get("error") or "").startswith(("LiveStateRequired", "OfflineNetworkRefused"))
        for r in runs
    ]
    keys = {(s, e is None) for s, e in zip(scores, errors, strict=True)}
    return {
        "scores": scores,
        "errors": [None if e is None else str(e)[:300] for e in errors],
        "verdict": verdict_of(scores[0], errors[0]),
        "nondeterministic": len(keys) > 1,
        "infra_failed": any(infra),
        "infra_timeouts": infra_timeouts,
        "seconds": round(sum(float(r.get("seconds") or 0) for r in runs), 3),
    }


def score_item(
    item: Mapping[str, Any],
    cell: str,
    save_row: Mapping[str, Any] | None,
    *,
    args: argparse.Namespace,
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    from harness.q2_mutation.controls import merge_lo
    from harness.q2_stage1.rescore import _capture_worker, _job_worker, checker_funcs

    task = tasks[item["task_id"]]
    funcs = checker_funcs(task)
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "item_id": item["item_id"],
        "cell": cell,
        "task_id": item["task_id"],
        "population": item["population"],
        "split": item["split"],
        "checker_funcs": funcs,
        "save": save_summary(save_row),
    }
    if cell == "raw":
        files: dict[str, str | None] = dict(item["files"])
    else:
        merged, excluded = merge_lo([item], [save_row] if save_row else [], suffix=None)
        if excluded:
            out["status"] = excluded[0]["kind"]
            out["reason"] = str(excluded[0]["reason"])[:400]
            return out
        prefix = {args.saves_prefix.rstrip("/") + "/": args.saves_root.rstrip("/") + "/"}
        files = {p: remap_path(v, prefix) for p, v in merged[0]["files"].items()}
    out["office_sha256"] = _office_digests(files)
    if item["population"] == "gold":
        payload_base: dict[str, Any] = {
            "osworld": str(args.osworld),
            "file_cache": str(args.file_cache),
            "job": {
                "mutant_id": item["item_id"],
                "task_id": item["task_id"],
                "files": files,
                "saved_via": "none" if cell == "raw" else cell,
                "lo_build": None,
                "include_initial": True,
                "candidate_sha256": item.get("candidate_sha256"),
            },
            "vm_baseline": str(args.vm_baseline) if args.vm_baseline else None,
        }
        target = _job_worker
    else:
        if cell == "raw":
            capture = Path(item["capture_dir"])
        else:
            safe = item["item_id"].replace(":", "_")
            capture = derived_capture(item, files, args.out / "captures" / cell / safe)
        manifest = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
        history = manifest.get("action_history") or []
        payload_base = {
            "osworld": str(args.osworld),
            "file_cache": str(args.file_cache),
            "capture_dir": str(capture),
            "task": dict(task),
            "last_action": history[-1] if history else None,
        }
        target = _capture_worker
    for checker in CHECKERS:
        if checker == "zinv" and ZINV_FAMILY not in funcs:
            out["zinv"] = {**out["pinned"], "same_as_pinned": True}
            continue
        payload = {**payload_base, "corrected": checker == "zinv"}
        out[checker] = score_checker(target, payload, repeat=args.repeat, timeout=args.timeout)
    pinned = out["pinned"]
    if pinned["infra_failed"]:
        out["status"] = "infra_failed"
    elif pinned["nondeterministic"]:
        out["status"] = "nondeterministic"
    else:
        out["status"] = "scored"
    if cell != "raw" and args.keep_captures is False and item["population"] != "gold":
        shutil.rmtree(capture, ignore_errors=True)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    import os

    os.environ.setdefault("PYTHONHASHSEED", "0")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument(
        "--cell",
        action="append",
        default=[],
        help="CELL=DIR with the save stage's reachability-*.jsonl, or 'raw'",
    )
    parser.add_argument("--saves-root", required=True, help="mounted save-stage output root")
    parser.add_argument("--saves-prefix", default="/out", help="that root inside the LO container")
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--file-cache", type=Path, required=True)
    parser.add_argument("--vm-baseline", type=Path, default=None)
    parser.add_argument("--only", type=Path, default=None, help="file of item ids to score")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--keep-captures", action="store_true")
    args = parser.parse_args(argv)
    from harness.q2_stage1.osworld_live import load_task

    items = read_jsonl(args.items)
    if args.only:
        wanted = set(args.only.read_text(encoding="utf-8").split())
        items = [i for i in items if i["item_id"] in wanted]
    tasks = {t: load_task(str(args.osworld), t) for t in sorted({i["task_id"] for i in items})}
    args.out.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    for spec in args.cell:
        cell, _, cell_dir = spec.partition("=")
        rows = {} if cell == "raw" else load_cell_rows(Path(cell_dir))

        def one(
            item: Mapping[str, Any], cell: str = cell, rows: Mapping[str, Any] = rows
        ) -> dict[str, Any]:
            try:
                return score_item(item, cell, rows.get(item["job_id"]), args=args, tasks=tasks)
            except Exception as exc:  # noqa: BLE001 - recorded as a harness failure
                return {
                    "schema": SCHEMA,
                    "item_id": item["item_id"],
                    "cell": cell,
                    "task_id": item["task_id"],
                    "population": item["population"],
                    "split": item["split"],
                    "status": "harness_error",
                    "reason": f"{type(exc).__name__}: {str(exc)[:300]}",
                }

        path = args.out / f"scores-{cell}.jsonl"
        counts: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool, path.open("w") as handle:
            for row in pool.map(one, items):
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary[cell] = counts
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
