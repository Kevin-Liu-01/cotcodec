#!/usr/bin/env python3
"""Per-cell summary of a run's save-stage rows (host, standard library only).

    summarize_saves.py RUN/OUT/saves > saves-summary.json

Reads both layouts: one directory per save job (``saves/GROUP/CELL``, keyed ``GROUP/CELL``,
attempts included as their own groups) and the earlier flat one (``saves/CELL``).

Counts only, no document content: rows, infrastructure errors (reason prefixes), save
failures, adapted window activations, saves unwritten or with a dialog, the store_as client's
outcomes, the build identity and locale data each worker recorded, and job seconds.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def cell_dirs(saves: Path) -> list[tuple[str, Path]]:
    out = []
    for path in sorted(p for p in saves.iterdir() if p.is_dir() and p.name != "logs"):
        if any(path.glob("reachability-*.jsonl")) or any(path.glob("cell-*.json")):
            out.append((path.name, path))
            continue
        for sub in sorted(q for q in path.iterdir() if q.is_dir() and q.name != "logs"):
            out.append((f"{path.name}/{sub.name}", sub))
    return out


def summarize(saves: Path) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, cell_dir in cell_dirs(saves):
        rows = [
            json.loads(line)
            for path in sorted(cell_dir.glob("reachability-*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        infos = [
            json.loads(p.read_text(encoding="utf-8")) for p in sorted(cell_dir.glob("cell-*.json"))
        ]
        store = Counter()
        for row in rows:
            for event in row.get("events", []):
                if event.get("event") == "store_as":
                    store[(bool(event.get("ok")), str(event.get("error") or "")[:80])] += 1
        seconds = [float(r["seconds"]) for r in rows if r.get("seconds") is not None]
        out[key] = {
            "rows": len(rows),
            "infra_errors": dict(
                Counter(str(r["infra_error"])[:80] for r in rows if r.get("infra_error"))
            ),
            "with_failures": sum(bool(r.get("failures")) for r in rows),
            "failure_kinds": dict(
                Counter(str(f).split(":")[0] for r in rows for f in r.get("failures", []))
            ),
            "with_adapted_activation": sum(bool(r.get("activations_adapted")) for r in rows),
            "saves": sum(len(r.get("saves", [])) for r in rows),
            "saves_unwritten": sum(not s.get("written") for r in rows for s in r.get("saves", [])),
            "saves_with_dialog": sum(
                bool(s.get("dialogs")) for r in rows for s in r.get("saves", [])
            ),
            "store_as_client": [
                {"ok": ok, "error": err, "n": n} for (ok, err), n in sorted(store.items())
            ],
            "job_seconds": {
                "sum": round(sum(seconds), 3),
                "median": statistics.median(seconds) if seconds else None,
                "max": max(seconds) if seconds else None,
            },
            "build_identity": sorted(
                {json.dumps(i.get("build_identity"), sort_keys=True) for i in infos}
            ),
            "locale_data": sorted(
                {
                    json.dumps(i.get("locale_data"), sort_keys=True)
                    for i in infos
                    if "locale_data" in i
                }
            ),
            "cell_errors": sorted({i["cell_error"] for i in infos if "cell_error" in i}),
            "profile_set": sorted({json.dumps(r.get("profile_set")) for r in rows}),
        }
    return out


if __name__ == "__main__":
    print(json.dumps(summarize(Path(sys.argv[1])), indent=1, sort_keys=True))
