"""S2 v3 Phase 0: summary tables of the oracle record (per application and overall)."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def summarize(rec: dict) -> dict:
    tasks = rec["tasks"]
    out: dict = {"tasks": len(tasks), "tolerances": rec["tolerances"]}
    by_app = defaultdict(list)
    for t in tasks:
        by_app[t["app"].replace("libreoffice_", "")].append(t)
    tab = {}
    for app, ts in sorted(by_app.items()) + [("all", tasks)]:
        row = {"tasks": len(ts)}
        for pair in ("E-ER", "A-AR", "E-PL"):
            es = [t["elements"].get(pair, {}) for t in ts if t["elements"].get(pair, {}).get("n")]
            n = sum(e["n"] for e in es)
            row[pair] = {
                "elements": n,
                "share_at_expected": round(sum(e["at_expected"] for e in es) / n, 4) if n else None,
                "share_located": round(sum(e["intact"] for e in es) / n, 4) if n else None,
                "share_unmoved": round(sum(e["unmoved"] for e in es) / n, 4) if n else None,
                "clipped": sum(e["clipped"] for e in es),
                "not_located": sum(e["missing"] for e in es),
                "text_runs": sum(e["text_runs"] for e in es),
                "text_runs_identical": sum(e.get("text_runs_identical", 0) for e in es),
                "median_task_mean_displacement_px": (round(float(np.median([e["mean_displacement_px"] for e in es
                                                     if e.get("mean_displacement_px") is not None])), 1) if es else None),
            }
        o5 = Counter()
        for t in ts:
            for c, v in t["o5"].items():
                o5[(c, v["verdict"])] += 1
        row["o5"] = {f"{c}:{v}": k for (c, v), k in sorted(o5.items())}
        row["admitted_proxy"] = sum(t["admitted"] for t in ts)
        row["leak_tasks"] = {c: sum(1 for t in ts if t["content_leaks"].get(c)) for c in ("A", "AR", "Q")}
        sh = [t["chrome"]["A"]["arabic"] / t["chrome"]["A"]["named"] for t in ts if t.get("chrome", {}).get("A", {}).get("named")]
        row["arabic_chrome_share_median"] = round(float(np.median(sh)), 4) if sh else None
        o8 = [t["elements"].get("E-ER", {}).get("n", 0) - t["elements"].get("E-ER", {}).get("at_expected", 0) for t in ts]
        row["o8_elements_outside_spec_per_task"] = {"median": float(np.median(o8)), "min": int(min(o8)), "max": int(max(o8))}
        tab[app] = row
    out["by_app"] = tab
    return out


if __name__ == "__main__":
    rec = json.loads(Path(sys.argv[1]).read_text())
    s = summarize(rec)
    Path(sys.argv[2]).write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1)[:6000])
