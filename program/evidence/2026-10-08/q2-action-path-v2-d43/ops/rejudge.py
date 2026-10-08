#!/usr/bin/env python3
"""Re-judge extracted development trials with the repository's judge (decision D43).

Reads trial files written by ``extract_trials.py``, rebuilds each trial's judge input with
``harness.q2.vm.suite.observation`` (the campaign's own path) and judges it with
``harness.q2.action_path.verdict`` as it stands in this checkout: the trial verdict, C4
(``rdev_agreement``) and, for L0-raw trials, C2's reading (``acceptance.c2_trial_pass``).
Writes one row per trial with the verdict the runner recorded beside the new one, and a
summary per (job, layer, fault or mutant, cell).

    uv run python <this file> OUT.json TRIALS.json...
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from harness.q2.action_path import acceptance, verdict  # noqa: E402
from harness.q2.vm import suite  # noqa: E402

CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text(encoding="utf-8"))
L0 = {c["id"]: c for c in CELLS["layers"]["L0-fixed"]}


def c2_input(row: dict, judged: dict) -> dict:
    """The fields ``acceptance.c2_trial_pass`` reads, as ``acceptance._trial`` builds them."""
    trial = row["trial"]
    end = (trial.get("post") or {}).get("end") or {}
    compact = [suite._compact_tap(r) for r in row["window"] or []]
    return {
        "pass": judged["pass"],
        "infra": judged["infra"],
        "reasons": judged["reasons"],
        "events": [r[:-1] for r in compact if acceptance._device(r)],
        "probe_events": end.get("events") if end.get("ok") else None,
    }


def rejudge(row: dict) -> dict:
    cell = L0[row["trial"]["cell"]]
    obs = suite.observation(row["trial"], row["window"], row["check"])
    judged = verdict.judge(cell, obs)
    out = {
        "job": row["job"],
        "cycle": row["cycle"],
        "setting": row["setting"],
        "seq": row["trial"]["seq"],
        "cell": cell["id"],
        "layer": row["layer"],
        "variant": row.get("fault") or row.get("mutant"),
        "runner_pass": (row.get("runner_verdict") or {}).get("pass"),
        "runner_reasons": (row.get("runner_verdict") or {}).get("reasons"),
        "pass": judged["pass"],
        "reasons": judged["reasons"],
        "state_not_observed": judged["state_not_observed"],
        "runner_c4": row.get("runner_c4"),
        "c4": verdict.rdev_agreement(cell["expect"], obs["tap_events"] or []),
        "tap_keys": [
            [e["kind"], verdict.keysym_name(e.get("keysym0")), e.get("state")]
            for e in obs["tap_events"] or []
            if e["kind"] in verdict.KEY_KINDS
        ],
        "probe_keys": len([e for e in obs["probe_events"] or [] if e["kind"] in verdict.KEY_KINDS]),
        "probe_focused_after": (
            ((row["trial"].get("post") or {}).get("end") or {}).get("state") or {}
        ).get("focused"),  # fmt: skip
        "guard": {
            "pre": (row["trial"].get("pre") or {}).get("violations"),
            "post": (row["trial"].get("post") or {}).get("violations"),
        },
    }
    if row["layer"] == "L0-raw":
        out["c2_pass"] = acceptance.c2_trial_pass(c2_input(row, judged), cell)
    return out


def main(argv: list[str]) -> int:
    out_path, paths = argv[1], argv[2:]
    rows = []
    for path in paths:
        rows += [rejudge(r) for r in json.loads(Path(path).read_text(encoding="utf-8"))["trials"]]
    groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        key = f"{r['job']} {r['layer']} {r['variant'] or '-'} {r['cell']}"
        g = groups[key]
        g["trials"] += 1
        g["runner_pass"] += bool(r["runner_pass"])
        g["pass"] += bool(r["pass"])
        g["state_not_observed"] += bool(r["state_not_observed"])
        if r["c4"] is not None:
            g["c4_true"] += bool(r["c4"])
        if "c2_pass" in r:
            g["c2_pass"] += bool(r["c2_pass"])
    summary = {k: dict(v) for k, v in sorted(groups.items())}
    Path(out_path).write_text(
        json.dumps({"summary": summary, "trials": rows}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for key, value in summary.items():
        print(key, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
