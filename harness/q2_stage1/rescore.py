"""Offline rescoring with the raw and the corrected checker (G0 items 6 and 8; sections 8, 9).

Runs in the checker-mutation study's metric image (OSWorld's locked environment), GPU-less,
with no network, each scoring in a fresh process with a timeout (as ``offline_eval``).

``capture``: an S1a episode's captured final state (``osworld_live.LiveTask.write_capture``)
is scored by the pinned ``DesktopEnv.evaluate()`` with the stub VM of ``offline_eval``. The VM
root holds exactly what the live checker read: every file ``get_file`` returned, and no file
where it returned nothing; the task cache holds what the live evaluation left in it
(postconfig output included). Postconfig is not replayed (the capture is taken after it).
Four scores per episode: ``raw`` and ``corrected`` (``compare_pptx_files_zinv`` installed in
OSWorld's ``metrics`` namespace), each with the episode's last action in the history (the
registered score, ``FAIL`` rule included) and with none (``*_state``: the checker's verdict on
the state alone). ``merge`` writes ``corrected_score`` (and the live-versus-offline match)
into the episode records the analysis reads (``records.outcome_array(value="corrected")``).

``validate-zinv``: G0 item 8's validation on the stored checker-mutation confirm campaign.
Every evaluable mutant and every gold whose checker is ``compare_pptx_files`` is rescored
with the original and the corrected comparator (``offline_eval``'s own worker, the
correction installed first). The gate: the corrected comparator passes the 29 audit-confirmed
``pptx.eq.zorder_nonoverlap`` mutants, and gives the original's verdict on every other
evaluable mutant and every gold; the 6 unresolved candidates are reported, not used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time
import traceback
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ZORDER = "pptx.eq.zorder_nonoverlap"
FAMILY = "compare_pptx_files"
THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


def _install_correction(osworld: str) -> None:
    if osworld not in sys.path:
        sys.path.insert(0, osworld)
    import desktop_env.evaluators.metrics as metrics

    from harness.q2_stage1 import zinv

    zinv.install(metrics)


def _capture_worker(payload: dict[str, Any], queue: Any) -> None:
    """Score one captured state (spawned; OSWorld is imported here only)."""
    import logging

    logging.disable(logging.CRITICAL)
    out: dict[str, Any] = {"score": None, "error": None}
    try:
        from harness.q2_mutation.offline_eval import (
            StubController,
            StubSetupController,
            make_offline_get,
            vm_to_host,
        )

        osworld = payload["osworld"]
        if payload["corrected"]:
            _install_correction(osworld)
        if osworld not in sys.path:
            sys.path.insert(0, osworld)
        capture = Path(payload["capture_dir"])
        manifest = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
        raw = payload["task"]
        with tempfile.TemporaryDirectory(prefix="s1a-rescore-") as tmp:
            vm_root = Path(tmp) / "vm"
            vm_root.mkdir()
            for path, digest in manifest["vm_files"].items():
                source = capture / "vm" / path.lstrip("/")
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError(f"captured {path} does not match its digest")
                target = vm_to_host(vm_root, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            import requests

            fetched: list[str] = []
            requests.get = make_offline_get(Path(payload["file_cache"]), fetched)
            from desktop_env.desktop_env import DesktopEnv

            env = DesktopEnv.__new__(DesktopEnv)
            env.cache_dir_base = str(Path(tmp) / "cache")
            env.enable_proxy = False
            env.is_environment_used = False
            last = payload.get("last_action")
            env.action_history = [last] if last else []
            env.controller = StubController(vm_root)
            env.setup_controller = StubSetupController()
            env.vm_ip = "127.0.0.1"
            env.server_port = 0
            env._set_task_info(raw)
            cache_dir = Path(env.cache_dir)
            for rel, digest in manifest["cache_files"].items():
                data = (capture / "cache" / rel).read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError(f"captured cache file {rel} does not match its digest")
                target = cache_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            result = env.evaluate()
            out["score"] = None if result is None else float(result)
            out["file_cache_fetches"] = len(fetched)
    except BaseException as exc:  # noqa: BLE001 - every checker exception is reported
        out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        out["traceback_tail"] = traceback.format_exc()[-800:]
    queue.put(out)


def _job_worker(payload: dict[str, Any], queue: Any) -> None:
    """``offline_eval``'s own worker, with the correction installed first when asked."""
    if payload.get("corrected"):
        _install_correction(payload["osworld"])
    from harness.q2_mutation.offline_eval import _score_in_worker

    _score_in_worker(payload, queue)


def run_worker(target: Any, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    os.environ.update(THREAD_ENV)
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=target, args=(payload, queue))
    started = time.monotonic()
    process.start()
    try:
        out = queue.get(timeout=timeout)
    except Exception:  # noqa: BLE001 - empty queue at the deadline
        out = None
    process.join(10)
    if process.is_alive():
        process.kill()
        process.join()
    if out is None:
        return {"score": None, "error": f"no result within {timeout} s (exit {process.exitcode})",
                "infra": True, "seconds": round(time.monotonic() - started, 3)}  # fmt: skip
    out["seconds"] = round(time.monotonic() - started, 3)
    return out


def checker_funcs(task: Mapping[str, Any]) -> list[str]:
    func = task["evaluator"]["func"]
    return [str(f) for f in func] if isinstance(func, list) else [str(func)]


# --------------------------------------------------------------------------- capture


def rescore_episode(
    episode_dir: Path, record: Mapping[str, Any], task: Mapping[str, Any], *, osworld: str,
    file_cache: str, timeout: float = 300.0,
) -> dict[str, Any]:  # fmt: skip
    """The four offline scores of one captured episode and their agreement with live."""
    capture = episode_dir / "capture"
    manifest = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
    history = manifest.get("action_history") or []
    last = history[-1] if history else None
    base = {"osworld": osworld, "file_cache": file_cache, "capture_dir": str(capture),
            "task": dict(task)}  # fmt: skip
    corrected_applies = FAMILY in checker_funcs(task)
    out: dict[str, Any] = {
        "slot": record.get("slot"),
        "attempt": record.get("attempt"),
        "task_id": record.get("task_id"),
        "live_score": record.get("score"),
        "state_sha256": manifest.get("state_sha256"),
        "corrected_applies": corrected_applies,
    }
    for name, corrected, history_last in (
        ("raw", False, last), ("raw_state", False, None),
        ("corrected", True, last), ("corrected_state", True, None),
    ):  # fmt: skip
        if corrected and not corrected_applies:
            out[name] = out[name.replace("corrected", "raw")]
            continue
        run = run_worker(
            _capture_worker, {**base, "corrected": corrected, "last_action": history_last}, timeout
        )
        out[name] = run["score"]
        if run.get("error"):
            out[f"{name}_error"] = run["error"]
    live = record.get("score")
    out["live_offline_match"] = None if live is None or out["raw"] is None else (
        float(live) == float(out["raw"]))  # fmt: skip
    return out


def merge(episodes: Iterable[Mapping[str, Any]], rescored: Iterable[Mapping[str, Any]]):
    """Episode records with ``corrected_score`` and the offline agreement filled in."""
    by_key = {(r["slot"], r["attempt"]): r for r in rescored}
    for record in episodes:
        rec = dict(record)
        found = by_key.get((rec.get("slot"), rec.get("attempt")))
        if rec.get("status") == "scored" and found is not None:
            corrected = found.get("corrected")
            if rec.get("metric_exception"):
                corrected = 0.0
            rec["corrected_score"] = corrected
            rec["offline_raw_score"] = found.get("raw")
            rec["offline_state_score"] = found.get("raw_state")
            rec["live_offline_match"] = found.get("live_offline_match")
        yield rec


# --------------------------------------------------------------------------- zinv validation


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def remap(job: dict[str, Any], mapping: Mapping[str, str]) -> dict[str, Any]:
    files = {}
    for vm_path, local in (job.get("files") or {}).items():
        if isinstance(local, str):
            for old, new in mapping.items():
                if local.startswith(old):
                    local = new + local[len(old) :]
        files[vm_path] = local
    return {**job, "files": files}


def validation_set(
    mutant_jobs: list[dict[str, Any]],
    mutant_verdicts: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    gold_jobs: list[dict[str, Any]],
    gold_verdicts: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every evaluable compare_pptx_files mutant and every compare_pptx_files gold, with its
    stored verdict, operator, label and audit reading."""
    verdicts = {v["mutant_id"]: v for v in mutant_verdicts}
    out_by_id = {o["mutant_id"]: o for o in outcomes}
    readings = {c["mutant_id"]: c.get("audit_reading") for c in candidates}
    items = []
    for job in mutant_jobs:
        mid = job["mutant_id"]
        verdict, outcome = verdicts.get(mid), out_by_id.get(mid)
        if verdict is None or outcome is None or verdict.get("checker_funcs") != [FAMILY]:
            continue
        if outcome.get("lock_status") != "evaluable":
            continue
        items.append({"kind": "mutant", "job": job, "stored": verdict.get("score"),
                      "operator": outcome.get("operator"), "label": outcome.get("label"),
                      "reading": readings.get(mid)})  # fmt: skip
    gold_v = {v["mutant_id"]: v for v in gold_verdicts}
    for job in gold_jobs:
        verdict = gold_v.get(job["mutant_id"])
        if verdict is None or verdict.get("checker_funcs") != [FAMILY]:
            continue
        if job.get("kind") not in (None, "gold"):
            continue
        items.append({"kind": "gold", "job": job, "stored": verdict.get("score"),
                      "operator": None, "label": "gold", "reading": None})  # fmt: skip
    return items


def judge_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The G0 item 8 gate over rescored rows (``raw``, ``zinv`` scores per item)."""
    confirmed = [r for r in rows if r["operator"] == ZORDER and r["reading"] == "confirmed"]
    unresolved = [r for r in rows if r["operator"] == ZORDER and r["reading"] == "unresolved"]
    others = [r for r in rows if r not in confirmed and r not in unresolved]
    errors = [r for r in rows if r.get("raw_error") or r.get("zinv_error")]
    gate = {
        "confirmed_zorder": len(confirmed),
        "confirmed_zorder_pass_under_zinv": sum(r["zinv"] == 1.0 for r in confirmed),
        "others": len(others),
        "others_equal_original": sum(r["zinv"] == r["stored"] for r in others),
        "others_differing": [
            {k: r[k] for k in ("id", "kind", "operator", "label", "stored", "raw", "zinv")}
            for r in others
            if r["zinv"] != r["stored"]
        ],  # fmt: skip
        "raw_reproduces_stored": sum(r["raw"] == r["stored"] for r in rows),
        "raw_differs_from_stored": [r["id"] for r in rows if r["raw"] != r["stored"]],
        "unresolved_reported": [
            {"id": r["id"], "raw": r["raw"], "zinv": r["zinv"]} for r in unresolved
        ],
        "scoring_errors": [
            {"id": r["id"], "raw_error": r.get("raw_error"), "zinv_error": r.get("zinv_error")}
            for r in errors
        ],  # fmt: skip
        "golds": sum(r["kind"] == "gold" for r in rows),
        "mutants": sum(r["kind"] == "mutant" for r in rows),
        "by_operator": dict(Counter(str(r["operator"]) for r in rows)),
    }
    gate["pass"] = (
        gate["confirmed_zorder"] == 29
        and gate["confirmed_zorder_pass_under_zinv"] == 29
        and gate["others_equal_original"] == gate["others"]
        and not errors
    )
    return gate


def validate_zinv(args: argparse.Namespace) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor

    mapping = dict(item.split("=", 1) for item in args.path_map or [])
    items = validation_set(
        read_jsonl(args.mutant_jobs), read_jsonl(args.mutant_verdicts), read_jsonl(args.outcomes),
        read_jsonl(args.gold_jobs), read_jsonl(args.gold_verdicts),
        json.loads(args.candidates.read_text())["checker_candidates"]["false_negative"]["events"],
    )  # fmt: skip

    def one(item: dict[str, Any]) -> dict[str, Any]:
        job = remap(item["job"], mapping)
        from harness.q2_mutation.offline_eval import ScoreJob

        score_job = ScoreJob.from_dict(job)
        payload = {"osworld": str(args.osworld), "file_cache": str(args.file_cache),
                   "job": score_job.__dict__,
                   "vm_baseline": str(args.vm_baseline) if args.vm_baseline else None}  # fmt: skip
        row = {"id": job["mutant_id"], "task_id": job["task_id"], "kind": item["kind"],
               "operator": item["operator"], "label": item["label"],
               "reading": item["reading"], "stored": item["stored"]}  # fmt: skip
        for name, corrected in (("raw", False), ("zinv", True)):
            run = run_worker(_job_worker, {**payload, "corrected": corrected}, args.timeout)
            row[name] = run.get("score")
            if run.get("error"):
                row[f"{name}_error"] = run["error"]
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(one, items))
    rows.sort(key=lambda r: (r["kind"], r["id"]))
    summary = {
        "schema": "q2-stage1a-zinv-validation-v1",
        "comparator_sha256": hashlib.sha256(
            Path(__file__).with_name("zinv.py").read_bytes()
        ).hexdigest(),
        "gate": judge_validation(rows),
        "rows": rows,
    }
    args.out.write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    return summary["gate"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="rescore the captured episodes of one lane run")
    cap.add_argument("--run-dir", type=Path, required=True, help="the lane's run directory")
    cap.add_argument("--osworld", required=True)
    cap.add_argument("--file-cache", required=True)
    cap.add_argument("--out", type=Path, required=True)
    cap.add_argument("--timeout", type=float, default=300.0)
    mrg = sub.add_parser("merge", help="write corrected scores into episode records")
    mrg.add_argument("--episodes", type=Path, required=True)
    mrg.add_argument("--rescored", type=Path, required=True)
    mrg.add_argument("--out", type=Path, required=True)
    val = sub.add_parser("validate-zinv", help="G0 item 8 on the stored confirm campaign")
    for name in ("mutant-jobs", "mutant-verdicts", "outcomes", "gold-jobs", "gold-verdicts",
                 "candidates", "osworld", "file-cache", "out"):  # fmt: skip
        val.add_argument(f"--{name}", type=Path, required=True)
    val.add_argument("--vm-baseline", type=Path, default=None)
    val.add_argument("--path-map", action="append", help="OLD_PREFIX=NEW_PREFIX for job files")
    val.add_argument("--workers", type=int, default=8)
    val.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    if args.command == "validate-zinv":
        gate = validate_zinv(args)
        print(json.dumps({k: v for k, v in gate.items() if not isinstance(v, list)}))
        return 0
    if args.command == "merge":
        rows = list(merge(read_jsonl(args.episodes), read_jsonl(args.rescored)))
        args.out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        return 0
    from harness.q2_stage1.osworld_live import load_task

    with args.out.open("w", encoding="utf-8") as handle:
        for record in read_jsonl(args.run_dir / "episodes.jsonl"):
            if record.get("status") != "scored":
                continue
            episode_dir = args.run_dir / "episodes" / (
                f"{str(record['slot']).replace(':', '_')}.a{record['attempt']}")  # fmt: skip
            if not (episode_dir / "capture" / "capture.json").exists():
                continue
            task = load_task(args.osworld, record["task_id"])
            row = rescore_episode(episode_dir, record, task, osworld=args.osworld,
                                  file_cache=args.file_cache, timeout=args.timeout)  # fmt: skip
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    raise SystemExit(main())
