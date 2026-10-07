"""Summarize a control run: raw and saved verdicts, gold fixed point, flips, saves.

Inputs are the files a ``submit_controls.sh`` run writes:
``raw/raw-verdicts-{lock,scout}.jsonl``, ``saved/saved-verdicts-{lock,scout}.jsonl``,
``raw/raw-notes-*.jsonl``, ``saved/saved-notes-*.jsonl`` and
``lo/reachability-*.jsonl``. The summary holds verdicts, hashes and save
events only; no document content.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from harness.q2_mutation.reachability import save_failures, step_may_write
from harness.q2_mutation.schema import read_verdict_rows
from harness.q2_mutation.stats import clopper_pearson

ARMS = ("lock", "scout")


def _rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows = read_verdict_rows(path.read_text(encoding="utf-8").splitlines())
    return {row.mutant_id: row.to_dict() for row in rows}


def _notes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    return {
        note["mutant_id"]: note
        for note in (json.loads(line) for line in path.read_text().splitlines() if line)
    }


def _key(mutant_id: str) -> tuple[str, str, bool]:
    parts = mutant_id.split("__")
    return parts[0], parts[1], parts[-1] == "lo"


def summarize_run(run: Path) -> dict[str, Any]:
    raw = {arm: _rows(run / "raw" / f"raw-verdicts-{arm}.jsonl") for arm in ARMS}
    saved = {arm: _rows(run / "saved" / f"saved-verdicts-{arm}.jsonl") for arm in ARMS}
    notes = {
        arm: {
            **_notes(run / "raw" / f"raw-notes-{arm}.jsonl"),
            **_notes(run / "saved" / f"saved-notes-{arm}.jsonl"),
        }
        for arm in ARMS
    }
    reach: dict[str, dict[str, Any]] = {}
    for path in sorted((run / "lo").glob("reachability-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                reach[row["job_id"]] = row
    tasks: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        for source, rows in (("raw", raw[arm]), ("saved", saved[arm])):
            for mutant_id, row in rows.items():
                task_id, kind, _ = _key(mutant_id)
                entry = tasks.setdefault(task_id, {"checker_funcs": row["checker_funcs"]})
                note = notes[arm].get(mutant_id, {})
                entry[f"{kind}_{source}_{arm}"] = {
                    "verdict": row["verdict"],
                    "score": row["score"],
                    "error": row.get("error"),
                    "nondeterministic": note.get("nondeterministic"),
                    "setup_unemulated": note.get("setup_unemulated"),
                    "postconfig_unemulated": note.get("postconfig_unemulated"),
                    "unemulated_writes": bool(
                        note.get("setup_unemulated_writes")
                        or note.get("postconfig_unemulated_writes")
                    ),
                    "infra_failed": bool(note.get("infra_failed")),
                }
    for job_id, row in reach.items():
        task_id, kind, _ = _key(job_id)
        entry = tasks.setdefault(task_id, {})
        # The placed candidate files: the stage hashes each before replaying.
        placed = {path: "placed" for path, sha in (row.get("before_sha256") or {}).items() if sha}
        unemulated = list((row.get("plan") or {}).get("unemulated", []))
        entry[f"{kind}_save"] = {
            "infra_error": row.get("infra_error"),
            "save_failures": save_failures(placed, row),
            "unemulated_writes": any(step_may_write(str(step)) for step in unemulated),
            "saves": [
                {
                    "reason": s["reason"],
                    "written": s["written"],
                    "changed": s["before_sha256"] != s["after_sha256"],
                    "seconds_to_write": s["seconds_to_write"],
                    "dialogs": s["dialogs"],
                }
                for s in row.get("saves", [])
            ],
            "failures": row.get("failures", []),
            "unemulated": row.get("plan", {}).get("unemulated", []),
            "derived_outputs": sorted(row.get("outputs", {})),
        }
    return {"tasks": dict(sorted(tasks.items())), "aggregate": aggregate(tasks)}


def unemulated_task(t: Mapping[str, Any]) -> bool:
    """A step the harness cannot replay may write a file the checker reads.

    Such a task is excluded from K1 and P1 and listed (preregistration section 8).
    """
    return any(
        isinstance(value, Mapping) and bool(value.get("unemulated_writes")) for value in t.values()
    )


def save_ok(t: Mapping[str, Any], kind: str) -> bool:
    """The kind's GUI-faithful save ran and wrote every office file (no save row: no)."""
    save = t.get(f"{kind}_save")
    return bool(save) and not save.get("infra_error") and not save.get("save_failures")


def infra_failed(t: Mapping[str, Any], *keys: str) -> bool:
    return any(bool((t.get(key) or {}).get("infra_failed")) for key in keys)


def aggregate(tasks: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "excluded_unemulated": sorted(k for k, t in tasks.items() if unemulated_task(t)),
    }
    kept = {k: t for k, t in tasks.items() if not unemulated_task(t)}
    for arm in ARMS:
        gold = {k: t for k, t in kept.items() if f"gold_raw_{arm}" in t}
        initial = [t for t in kept.values() if f"initial_raw_{arm}" in t]
        paired = [t for t in gold.values() if f"initial_raw_{arm}" in t]
        both = [t for t in paired if not infra_failed(t, f"gold_raw_{arm}", f"initial_raw_{arm}")]
        k1 = sum(
            t[f"gold_raw_{arm}"]["verdict"] == "pass"
            and t[f"initial_raw_{arm}"]["verdict"] == "fail"
            for t in both
        )
        # P1 counts a gold only if its GUI-faithful save wrote every office file
        # and neither scoring timed out; the others are listed, never counted.
        fixed = {
            k: t
            for k, t in gold.items()
            if f"gold_saved_{arm}" in t
            and save_ok(t, "gold")
            and not infra_failed(t, f"gold_raw_{arm}", f"gold_saved_{arm}")
        }
        flips = [
            t
            for t in fixed.values()
            if t[f"gold_raw_{arm}"]["verdict"] == "pass"
            and t[f"gold_saved_{arm}"]["verdict"] != "pass"
        ]
        dn_saved_pass = [
            t for t in initial if t.get(f"initial_saved_{arm}", {}).get("verdict") == "pass"
        ]
        out[arm] = {
            "tasks_with_gold": len(gold),
            "tasks_with_initial": len(initial),
            "k1_gold_pass_and_do_nothing_fail": f"{k1}/{len(both)}",
            "k1_infra_excluded": len(paired) - len(both),
            "gold_raw_verdicts": dict(
                Counter(t[f"gold_raw_{arm}"]["verdict"] for t in gold.values())
            ),
            "gold_saved_verdicts": dict(
                Counter(t[f"gold_saved_{arm}"]["verdict"] for t in fixed.values())
            ),
            "gold_fixed_point_flips": len(flips),
            "gold_fixed_point_n": len(fixed),
            "gold_fixed_point_flip_clopper_pearson95": (
                list(clopper_pearson(len(flips), len(fixed))) if fixed else None
            ),
            "gold_fixed_point_not_counted": sorted(set(gold) - set(fixed)),
            "gold_save_failed": sorted(
                k for k, t in gold.items() if "gold_save" in t and not save_ok(t, "gold")
            ),
            "do_nothing_saved_passes": len(dn_saved_pass),
        }
    flips = []
    unstable: list[dict[str, str]] = []
    for task_id, t in tasks.items():
        for kind in ("gold", "initial"):
            for source in ("raw", "saved"):
                a = t.get(f"{kind}_{source}_lock")
                b = t.get(f"{kind}_{source}_scout")
                if not (a and b) or (a["verdict"], a["score"]) == (b["verdict"], b["score"]):
                    continue
                if a.get("nondeterministic") or b.get("nondeterministic"):
                    # S1 counts a flip only when each venv is stable on repeat.
                    unstable.append({"task_id": task_id, "candidate": f"{kind}_{source}"})
                else:
                    flips.append(
                        {
                            "task_id": task_id,
                            "candidate": f"{kind}_{source}",
                            "lock": a,
                            "scout": b,
                        }
                    )
    out["dependency_flips"] = flips
    out["venv_differences_from_nondeterministic_checkers"] = unstable
    saves = [
        s
        for t in tasks.values()
        for k in ("gold_save", "initial_save")
        for s in t.get(k, {}).get("saves", [])
    ]
    out["saves"] = {
        "n": len(saves),
        "written": sum(s["written"] for s in saves),
        "changed_bytes": sum(s["changed"] for s in saves),
        "slower_than_0_5s": sum((s["seconds_to_write"] or 0) > 0.5 for s in saves),
        "with_dialog": sum(bool(s["dialogs"]) for s in saves),
    }
    out["save_infra_errors"] = sorted(
        task_id
        for task_id, t in tasks.items()
        for k in ("gold_save", "initial_save")
        if t.get(k, {}).get("infra_error")
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    summary = summarize_run(args.run)
    args.out.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["aggregate"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
