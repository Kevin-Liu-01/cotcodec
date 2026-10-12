"""S2 v4 round 4 (D90): the development smoke's manifest and its reading (dev split only).

Not Phase 0 and not imported by any registered job. D90 fixed the round's acceptance criterion
before the smoke: on the 17 dev tasks every masked boot pair E-E2, ER-ER2, AD-AR and E-S is at most
tol6 (so I2, I5 and I6 are 17 of 17), and no Impress boot shows a deviating status-bar field. To
observe about twice as many Impress boots, the smoke runs smoke 1240's 240 slots
(``dev-smoke-v4.json``) plus a second boot of every capture slot of the 7 Impress dev tasks.

``render``: the base manifest's slots in their order, each capture slot of an Impress dev task
followed, in the same block, by its second boot (so the two boots run side by side, as E and E2
do in the census): a cell with one boot per task (S, A, AR, PL, AD, PD) gets rep 2, and E and ER,
which already have reps 1 and 2, get reps 3 and 4 (the second boots of reps 1 and 2). Slurm minutes
are ``vm_lane.check_slurm``'s requirement.

``read`` (the reading fixed with the manifest, before the smoke runs): the counted, probed capture
attempt of each (task, cell, rep) (``oracle_vm.render_index``, the oracle's own reading of the run
directory), and per task the pairs
* registered: E-S, E-E2, ER-ER2, AD-AR (the pairs of I2, I6 and I5, and ER's A/A pair);
* same cell: each further boot of a cell against the cell's first boot (S-S2, E-E3, E-E4, A-A2,
  ER-ER3, ER-ER4, AR-AR2, PL-PL2, AD-AD2, PD-PD2), so every Impress boot is in at least one pair.
Each pair is counted with K0's rule (``oracle_vm.masked_counts``: a channel differing by more than
20, outside the GNOME top bar and both renders' caret masks), on the whole screen and in
LibreOffice's status bar (rows 1060-1079, Phase 1's step-0 mask rows). The criterion: (a) every
registered pair of every dev task is observed and at most ``tol6`` (the oracle route's tolerance on
the same run); (b) no pair of an Impress dev task shows a deviating status-bar field: more than
``FIELD_PX`` differing pixels in the status-bar rows. A changed pointer-field value changes whole
digits: in smoke 1240 three changed digits gave 148 and 142 px, and boot pairs differed by at most
1 px anywhere else on the screen.

Usage:
  python -m harness.s2_locale.dev_smoke render --base dev-smoke-v4.json --pool POOL --out FILE
  python -m harness.s2_locale.dev_smoke read --runs RUN_DIR --pool POOL --tol6 N --out FILE
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-dev-smoke-round4-v1"
IMPRESS = "libreoffice_impress"
STATUS_BAR_ROWS = (1060, 1080)  # rows 1060-1079: LibreOffice's status bar (Phase 1's mask)
FIELD_PX = 10  # more than this many differing status-bar pixels: a deviating field
REGISTERED = {"E_vs_S": (("E", 1), ("S", 1)), "E_vs_E2": (("E", 1), ("E", 2)),
              "ER_vs_ER2": (("ER", 1), ("ER", 2)), "AD_vs_AR": (("AD", 1), ("AR", 1))}


def impress_dev(pool: Mapping[str, Any]) -> list[str]:
    """The Impress dev tasks of the pool (``split`` dev, ``app`` Impress), sorted."""
    return sorted(t["task_id"] for t in pool.get("tasks", [])
                  if t.get("split") == "dev" and t.get("app") == IMPRESS
                  and t.get("exclusion") is None)  # fmt: skip


def second_boots(base: Mapping[str, Any], tasks: Sequence[str], name: str) -> dict[str, Any]:
    """The base manifest with a second boot of every capture slot of ``tasks`` (module
    docstring), named ``name``, with ``check_slurm``'s minutes for the new slot count."""
    from harness.s2_locale import vm_lane as L

    m = json.loads(json.dumps(base))
    wanted = set(tasks)
    reps: dict[tuple[str, str], int] = {}
    for s in m["slots"]:
        if s.get("kind", "capture") == "capture":
            key = (s["task_id"], s["cell"])
            reps[key] = max(reps.get(key, 0), int(s["rep"]))
    slots = []
    for s in m["slots"]:
        slots.append(s)
        if s.get("kind", "capture") == "capture" and s["task_id"] in wanted:
            rep = int(s["rep"]) + reps[(s["task_id"], s["cell"])]
            slots.append({**s, "rep": rep, "slot": L.slot_id(s["task_id"], s["cell"], rep)})
    m["slots"], m["name"] = slots, name
    v = m["vm"]["concurrency"]
    hash_min = math.ceil(L.image_bytes(m) / 1e9 / L.HASH_GB_PER_MIN)
    slot_min = math.ceil(L.SLOT_MARGIN * len(slots) * L.SLOT_MINUTES / v)
    m["slurm"] = {**m["slurm"], "minutes": hash_min + slot_min + 10}
    return m


def pairs_for(boots: set[tuple[str, int]]) -> dict[str, tuple[tuple[str, int], tuple[str, int]]]:
    """The registered pairs and the same-cell pairs (each further boot against the first)."""
    out = dict(REGISTERED)
    for cell, rep in sorted(boots):
        if rep >= 2 and (cell, 1) in boots:
            name = f"{cell}_vs_{cell}{rep}"
            out.setdefault(name, ((cell, 1), (cell, rep)))
    return out


def pair_counts(a_dir: Path, b_dir: Path) -> dict[str, Any]:
    """K0's masked counts (``oracle_vm.masked_counts``) and the same count in the status bar."""
    from harness.s2_locale import oracle as O
    from harness.s2_locale import oracle_vm as V

    a, b = V.Render(a_dir), V.Render(b_dir)
    out = V.masked_counts(a, b)
    if out.get("diff_pixels") is None:
        return out
    mask = a.caret() | b.caret()
    mask[:V.SHELL_ROWS, :] = True
    lo, hi = STATUS_BAR_ROWS
    diff = (abs(a.img - b.img).max(axis=2) > O.INK_DIFF // 2) & ~mask
    out["status_bar_pixels"] = int(diff[lo:hi].sum())
    out["status_bar_exact"] = int(((a.img != b.img).any(axis=2) & ~mask)[lo:hi].sum())
    return out


def read(run_dirs: Sequence[Path], pool: Mapping[str, Any], tol6: int) -> dict[str, Any]:
    """The round's criterion on the smoke's run directory (module docstring)."""
    from harness.s2_locale import oracle_vm as V

    index = V.render_index(run_dirs)
    dev = sorted(t["task_id"] for t in pool.get("tasks", []) if t.get("split") == "dev")
    impress = set(impress_dev(pool))
    per_task: dict[str, Any] = {}
    over, deviating, missing = [], [], []
    for task in dev:
        boots = {(c, r) for (t, c, r) in index if t == task}
        rows = {}
        for name, (a, b) in pairs_for(boots).items():
            if a not in boots or b not in boots:
                if name in REGISTERED:
                    missing.append([task[:8], name])
                continue
            rows[name] = pair_counts(index[(task, *a)], index[(task, *b)])
            count = rows[name].get("diff_pixels")
            if name in REGISTERED and (count is None or count > tol6):
                over.append([task[:8], name, count])
            if task in impress and (rows[name].get("status_bar_pixels") or 0) > FIELD_PX:
                deviating.append([task[:8], name, rows[name]["status_bar_pixels"]])
        per_task[task[:8]] = {"impress": task in impress, "boots": len(boots), "pairs": rows}
    impress_boots = sum(1 for (t, _, _) in index if t in impress)
    return {
        "schema": SCHEMA, "development_only": True, "tol6": tol6, "field_px": FIELD_PX,
        "status_bar_rows": list(STATUS_BAR_ROWS), "dev_tasks": len(dev),
        "impress_boots_read": impress_boots,
        "registered_pairs_missing": missing, "registered_pairs_over_tol6": over,
        "impress_status_bar_deviations": deviating,
        "pass": not missing and not over and not deviating,
        "per_task": per_task,
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ren = sub.add_parser("render")
    ren.add_argument("--base", type=Path, required=True)
    ren.add_argument("--pool", type=Path, required=True)
    ren.add_argument("--name", default="s2v4-dev-smoke-v5")
    ren.add_argument("--out", type=Path, required=True)
    rd = sub.add_parser("read")
    rd.add_argument("--runs", type=Path, nargs="+", required=True)
    rd.add_argument("--pool", type=Path, required=True)
    rd.add_argument("--tol6", type=int, required=True, help="the oracle route's tol6 on this run")
    rd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    pool = json.loads(args.pool.read_text(encoding="utf-8"))
    if args.command == "render":
        m = second_boots(json.loads(args.base.read_text(encoding="utf-8")), impress_dev(pool),
                         args.name)  # fmt: skip
        args.out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"slots": len(m["slots"]), "minutes": m["slurm"]["minutes"]}))
        return 0
    out = read(args.runs, pool, args.tol6)
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps({k: out[k] for k in ("pass", "impress_boots_read",
                                          "registered_pairs_over_tol6",
                                          "impress_status_bar_deviations")}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
