"""Container steps of ``q2-zinv-reserve-validation-v1`` (registration section 5).

``select-targets`` (metric image, end of step 1)
    After the parent's ``campaign targets``: keeps the targets of one document family (pptx),
    moving the full list to ``targets-all.jsonl``. It reads only the target rows (no task
    config, checker or verdict). On the reserve split it refuses any selection other than the
    registered eight targets on ``rules.RESERVE_PPTX_TASKS``.
``rescore`` (metric image, step 4)
    Every evaluable mutant and every saved gold and do-nothing state checked by
    ``compare_pptx_files`` alone (``q2_stage1.rescore.validation_set``, with no audit input),
    scored in fresh processes with the original comparator and with ``compare_pptx_files_zinv``
    installed (``q2_stage1.rescore``'s worker, unchanged), with the registered verdict and the
    digest of the scored files kept beside each score.
``judge`` (anywhere)
    ``rules.judge`` over the rescored rows.

    python -m harness.q2_zinv_reserve.run select-targets --prep /out --family pptx --split reserve
    python -m harness.q2_zinv_reserve.run rescore --split reserve --mutant-jobs ... --out rows.json
    python -m harness.q2_zinv_reserve.run judge --rows rows.json --out judgement.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from harness.q2_zinv_reserve import rules

ROWS_SCHEMA = "q2-zinv-reserve-rows-v1"
JUDGEMENT_SCHEMA = "q2-zinv-reserve-judgement-v1"
ZINV_PATH = Path(__file__).resolve().parents[1] / "q2_stage1" / "zinv.py"
RESCORE_PATH = Path(__file__).resolve().parents[1] / "q2_stage1" / "rescore.py"


class RunError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    Path(path).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def write_json(path: Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- select-targets


def select_targets(
    targets: Sequence[Mapping[str, Any]], family: str, split: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The targets of ``family`` and a summary; refuses an unregistered reserve selection."""
    kept = [dict(t) for t in targets if t.get("family") == family]
    tasks = sorted({str(t["task_id"]) for t in kept})
    if split == rules.SPLIT:
        if family != rules.TARGET_FAMILY:
            raise RunError(f"the reserve split registers the {rules.TARGET_FAMILY} family only")
        if tuple(tasks) != rules.RESERVE_PPTX_TASKS or len(kept) != len(tasks):
            raise RunError(
                f"reserve {family} targets {len(kept)} on {tasks} differ from the registered "
                f"{len(rules.RESERVE_PPTX_TASKS)} on rules.RESERVE_PPTX_TASKS"
            )
    dropped: dict[str, int] = {}
    for t in targets:
        if t.get("family") != family:
            dropped[str(t.get("family"))] = dropped.get(str(t.get("family")), 0) + 1
    summary = {
        "split": split,
        "family": family,
        "targets_all": len(targets),
        "targets_kept": len(kept),
        "tasks_kept": tasks,
        "kept_target_ids": sorted(str(t["target_id"]) for t in kept),
        "dropped_by_family": dict(sorted(dropped.items())),
    }
    return kept, summary


def cmd_select_targets(args: argparse.Namespace) -> int:
    prep = Path(args.prep)
    path, all_path = prep / "targets.jsonl", prep / "targets-all.jsonl"
    if all_path.exists():
        raise RunError(f"{all_path} exists: the selection already ran")
    targets = read_jsonl(path)
    kept, summary = select_targets(targets, args.family, args.split)
    path.rename(all_path)
    write_jsonl(path, kept)
    summary["targets_all_sha256"] = sha256_file(all_path)
    summary["targets_sha256"] = sha256_file(path)
    write_json(prep / "targets-selection.json", summary)
    print(json.dumps({k: summary[k] for k in ("split", "family", "targets_all", "targets_kept")}))
    return 0


# --------------------------------------------------------------------------- rescore


def items_for(
    mutant_jobs: list[dict[str, Any]],
    mutant_verdicts: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    gold_jobs: list[dict[str, Any]],
    gold_verdicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The validation set of ``q2_stage1.rescore`` (no audit reading), each item with the
    registered verdict row's scored-file digest and the outcome's probe flag and target."""
    from harness.q2_stage1 import rescore

    items = rescore.validation_set(
        mutant_jobs, mutant_verdicts, outcomes, gold_jobs, gold_verdicts, []
    )
    mutant_rows = {v["mutant_id"]: v for v in mutant_verdicts}
    gold_rows = {v["mutant_id"]: v for v in gold_verdicts}
    by_id = {o["mutant_id"]: o for o in outcomes}
    for item in items:
        mid = item["job"]["mutant_id"]
        source = mutant_rows if item["kind"] == "mutant" else gold_rows
        item["stored_scored_sha256"] = source[mid].get("scored_sha256")
        outcome = by_id.get(mid, {}) if item["kind"] == "mutant" else {}
        item["probe_touched"] = outcome.get("probe_touched")
        item["target_id"] = outcome.get("target_id")
    return items


def score_item(
    item: Mapping[str, Any],
    *,
    osworld: str,
    file_cache: str,
    vm_baseline: str | None,
    timeout: float,
    run: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One item scored twice in fresh processes: the original, then zinv installed."""
    from harness.q2_mutation.offline_eval import ScoreJob
    from harness.q2_stage1 import rescore

    run = run or (lambda payload, limit: rescore.run_worker(rescore._job_worker, payload, limit))
    job = dict(item["job"])
    payload = {"osworld": osworld, "file_cache": file_cache,
               "job": ScoreJob.from_dict(job).__dict__, "vm_baseline": vm_baseline}  # fmt: skip
    row: dict[str, Any] = {
        "id": job["mutant_id"],
        "task_id": job["task_id"],
        "kind": item["kind"],
        "operator": item.get("operator"),
        "label": item.get("label"),
        "target_id": item.get("target_id"),
        "probe_touched": item.get("probe_touched"),
        "stored": item.get("stored"),
        "stored_scored_sha256": item.get("stored_scored_sha256"),
    }
    for name, corrected in (("raw", False), ("zinv", True)):
        result = run({**payload, "corrected": corrected}, timeout)
        row[name] = result.get("score")
        row[f"{name}_error"] = result.get("error")
        row[f"{name}_infra"] = bool(result.get("infra"))
        row[f"{name}_scored_sha256"] = result.get("scored_sha256")
        row[f"{name}_seconds"] = result.get("seconds")
    return row


def check_registered_inputs(args: argparse.Namespace) -> None:
    """On the reserve split: the reused code and the parent's control files at their pins."""
    if sha256_file(ZINV_PATH) != rules.ZINV_SHA256:
        raise RunError("harness/q2_stage1/zinv.py differs from its pin")
    if sha256_file(RESCORE_PATH) != rules.RESCORE_SHA256:
        raise RunError("harness/q2_stage1/rescore.py differs from its pin")
    if args.split != rules.SPLIT:
        return
    for path, name in ((args.gold_jobs, "jobs-saved-mounted.jsonl"),
                       (args.gold_verdicts, "saved-verdicts-lock.jsonl")):  # fmt: skip
        if sha256_file(path) != rules.RESERVE_CONTROLS[name]:
            raise RunError(f"{path} is not the registered {rules.RESERVE_CONTROLS_RUN} {name}")


def cmd_rescore(args: argparse.Namespace) -> int:
    check_registered_inputs(args)
    items = items_for(
        read_jsonl(args.mutant_jobs), read_jsonl(args.mutant_verdicts), read_jsonl(args.outcomes),
        read_jsonl(args.gold_jobs), read_jsonl(args.gold_verdicts),
    )  # fmt: skip
    if args.split == rules.SPLIT:
        stray = sorted({i["job"]["task_id"] for i in items if i["kind"] == "mutant"}
                       - set(rules.RESERVE_PPTX_TASKS))  # fmt: skip
        if stray:
            raise RunError(f"mutants outside the registered reserve pptx tasks: {stray}")

    def one(item: dict[str, Any]) -> dict[str, Any]:
        return score_item(item, osworld=str(args.osworld), file_cache=str(args.file_cache),
                          vm_baseline=str(args.vm_baseline) if args.vm_baseline else None,
                          timeout=args.timeout)  # fmt: skip

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(one, items))
    rows.sort(key=lambda r: (r["kind"], r["id"]))
    inputs = {
        name: sha256_file(getattr(args, name))
        for name in ("mutant_jobs", "mutant_verdicts", "outcomes", "gold_jobs", "gold_verdicts")
    }
    out = {
        "schema": ROWS_SCHEMA,
        "experiment_id": rules.EXPERIMENT_ID,
        "split": args.split,
        "comparator_sha256": sha256_file(ZINV_PATH),
        "rescore_sha256": sha256_file(RESCORE_PATH),
        "inputs_sha256": inputs,
        "timeout_s": args.timeout,
        "rows": rows,
    }
    write_json(args.out, out)
    print(json.dumps({"split": args.split, "rows": len(rows),
                      "zorder": sum(rules.in_z(r) for r in rows),
                      "violation": sum(rules.in_v(r) for r in rows)}))  # fmt: skip
    return 0


# --------------------------------------------------------------------------- judge


def cmd_judge(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    if data.get("schema") != ROWS_SCHEMA:
        raise RunError(f"{args.rows} is not a {ROWS_SCHEMA} file")
    if data.get("split") == rules.SPLIT and data.get("comparator_sha256") != rules.ZINV_SHA256:
        raise RunError("the rows were scored with another comparator")
    judgement = rules.judge(data["rows"])
    out = {
        "schema": JUDGEMENT_SCHEMA,
        "split": data.get("split"),
        "rows_sha256": sha256_file(args.rows),
        "comparator_sha256": data.get("comparator_sha256"),
        **judgement,
    }
    write_json(args.out, out)
    headline = {k: out[k] for k in ("split", "outcome", "status")}
    headline["z"] = out["condition_a"]
    headline["v_new_accepts"] = out["condition_b"]["new_accepts"]
    print(json.dumps(headline))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sel = sub.add_parser("select-targets", help="keep one family's targets (end of step 1)")
    sel.add_argument("--prep", type=Path, required=True)
    sel.add_argument("--family", required=True)
    sel.add_argument("--split", required=True)
    res = sub.add_parser("rescore", help="original and zinv scores of every item (step 4)")
    res.add_argument("--split", required=True)
    for name in ("mutant-jobs", "mutant-verdicts", "outcomes", "gold-jobs", "gold-verdicts",
                 "osworld", "file-cache", "out"):  # fmt: skip
        res.add_argument(f"--{name}", type=Path, required=True)
    res.add_argument("--vm-baseline", type=Path, default=None)
    res.add_argument("--workers", type=int, default=7)
    res.add_argument("--timeout", type=float, default=300.0)
    jdg = sub.add_parser("judge", help="the registered rule over the rescored rows")
    jdg.add_argument("--rows", type=Path, required=True)
    jdg.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    commands = {"select-targets": cmd_select_targets, "rescore": cmd_rescore, "judge": cmd_judge}
    try:
        return commands[args.command](args)
    except RunError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    import os

    os.environ.setdefault("PYTHONHASHSEED", "0")  # as q2_stage1.rescore's entry point
    raise SystemExit(main())
