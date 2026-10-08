#!/usr/bin/env python3
"""Summaries for the v2 development record (decision D40) from ``chord_timing.py``'s scan.

    python3 summarize.py SCAN.json OUT_DIR

Writes, into OUT_DIR:

* ``v2-development-runs.json``: one row per v2 development job (784-787);
* ``chord-trials-v2-and-c2.json``: every chord trial of jobs 768 (v1's C2, read only) and
  784-787, as the scan gives it;
* ``chord-super-d-by-condition.json``: every ``chord_super_d`` trial of v1's development
  runs, v1's C2 and v2's development, counted by executor path (L0-raw; L0-fixed directly or
  under H-OSW-fixed or H-GA; the QEMU monitor), keyboard warm-up, and whether it was the
  session's first key event, with the offset and core state of the second key event and
  what the shell did (probe events, probe focus after the entry, marker on screen); mutant
  runs and trials with an infrastructure failure are counted apart;
* ``shell-chords-by-executor.json``: the four shell-grabbed chords and the nine others, per
  executor, with the core state of every key event after the first, from the same trials.

It reads the scan only; every verdict in it is the runner's.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

V2_JOBS = {"784", "785", "786", "787"}
C2_JOB = "768"
SHELL = ("chord_super_d", "chord_alt_f4", "chord_alt_tab", "chord_ctrl_alt_shift_r")
L0_FIXED_PATH = ("L0-fixed", "H-OSW-fixed", "H-GA")


def upper95(n: int) -> float | None:
    """One-sided 95% upper bound on a failure rate after 0 failures in n trials."""
    return round(1 - 0.05 ** (1 / n), 4) if n else None


def path_of(layer: str) -> str:
    if layer in L0_FIXED_PATH:
        return "L0-fixed"
    return {"HMP": "QEMU monitor"}.get(layer, layer)


def group(trials: list[dict]) -> dict:
    second = [t["keys"][1] for t in trials if len(t["keys"]) > 1]
    return {
        "trials": len(trials),
        "pass": sum(1 for t in trials if t["pass"]),
        "second_key_event_offset_ms": dict(
            sorted(collections.Counter(str(k[4]) for k in second).items(), key=lambda x: int(x[0]))
        ),
        "second_key_event_state": dict(collections.Counter(str(k[2]) for k in second)),
        "shell_response": {
            f"probe_events={a} probe_focused_after={b} marker_on_screen={c}": n
            for (a, b, c), n in sorted(
                collections.Counter(
                    (t["probe_events"], t["probe_focused_after"], t["marker_on_screen"])
                    for t in trials
                ).items(),
                key=str,
            )
        },
        "jobs": sorted({int(t["job"]) for t in trials}),
        "upper95_failure_rate_if_none_failed": upper95(len(trials))
        if trials and all(t["pass"] for t in trials)
        else None,
    }


def main(argv: list[str]) -> int:
    scan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    out = Path(argv[2])
    runs = [r for r in scan["runs"] if r["job"] in V2_JOBS]
    (out / "v2-development-runs.json").write_text(json.dumps(runs, indent=1) + "\n")
    picked = [t for t in scan["chord_trials"] if t["job"] in V2_JOBS | {C2_JOB}]
    (out / "chord-trials-v2-and-c2.json").write_text(json.dumps(picked, indent=1) + "\n")

    superd = [t for t in scan["chord_trials"] if t["cell"] == "chord_super_d"]
    excluded = [t for t in superd if t["mutant"] or t["infra"]]
    clean = [t for t in superd if not (t["mutant"] or t["infra"])]
    table = {}
    for t in clean:
        key = (
            path_of(t["layer"]),
            "warm-up" if t["session_warmup"] else "no warm-up",
            "first key of the session"
            if t["key_events_earlier_in_session"] == 0
            else "not the first key",
        )
        table.setdefault(" | ".join(key), []).append(t)
    summary = {
        "source": "chord_timing.py over v1's development runs (482-708), v1's C2 (768) and "
        "v2's development runs (784-787)",
        "runs_scanned": len(scan["runs"]),
        "excluded": [
            {"job": t["job"], "cycle": t["cycle"], "mutant": t["mutant"], "infra": t["infra"]}
            for t in excluded
        ],
        "groups": {k: group(v) for k, v in sorted(table.items())},
        "l0_fixed_path_with_warmup": group(
            [t for t in clean if t["layer"] in L0_FIXED_PATH and t["session_warmup"]]
        ),
        "l0_fixed_path_with_warmup_not_first_key": group(
            [
                t
                for t in clean
                if t["layer"] in L0_FIXED_PATH
                and t["session_warmup"]
                and t["key_events_earlier_in_session"] > 0
            ]
        ),
    }
    (out / "chord-super-d-by-condition.json").write_text(json.dumps(summary, indent=1) + "\n")

    chords = {}
    for t in [t for t in picked if not t["infra"]]:
        executor = path_of(t["layer"])
        entry = chords.setdefault(t["cell"], {}).setdefault(
            executor, {"trials": 0, "pass": 0, "state_after_first_key": collections.Counter()}
        )
        entry["trials"] += 1
        entry["pass"] += bool(t["pass"])
        entry["state_after_first_key"][" ".join(f"{k[0][3]}{k[2]}" for k in t["keys"][1:])] += 1
    for cell in chords.values():
        for entry in cell.values():
            entry["state_after_first_key"] = dict(entry["state_after_first_key"])
    shell = {
        "shell_grabbed": {c: chords.get(c) for c in SHELL},
        "other_chords": {c: v for c, v in sorted(chords.items()) if c not in SHELL},
        "note": "P/R = key press/release; the number is its core state (16 = Mod2, NumLock; "
        "20 = Control+Mod2; 24 = Mod1+Mod2; 80 = Mod4+Mod2; 0 = no bit at all)",
    }
    (out / "shell-chords-by-executor.json").write_text(json.dumps(shell, indent=1) + "\n")
    print(json.dumps({k: (v["trials"], v["pass"]) for k, v in summary["groups"].items()}, indent=1))
    print("L0-fixed path with warm-up:", summary["l0_fixed_path_with_warmup"]["trials"],
          summary["l0_fixed_path_with_warmup"]["upper95_failure_rate_if_none_failed"])  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
