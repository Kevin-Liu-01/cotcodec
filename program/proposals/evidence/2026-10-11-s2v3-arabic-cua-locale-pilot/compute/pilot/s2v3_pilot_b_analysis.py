#!/usr/bin/env python3
"""Analysis of pilot part B (runs on the Mac on the screenshots and AT-SPI dumps copied from the host).

Per task, with L1 = English left-to-right, L2 = English mirrored (UIMirroring = true),
L4 = pseudo-Arabic interface language with no UIMirroring key (layout follows the language):
  setup      the document opened (a window whose title holds the file name) in all three cells
  titles     the LibreOffice window title is byte-identical across the cells (the tasks'
             strict activate_window postconfig depends on it)
  L2==L4     share of pixels that differ between L2 and L4 (the layout set by the configuration
             key against the layout set by the language)
  chrome     column-ink correlation of the chrome band (y 30-180) between L1 and the
             horizontally reversed L2 (mirrored layout expected: high), and unreversed (low)
  document   the document band (y 270-1000, x 300-1600 of L1) found in L2 by a horizontal shift
             search (-200..200 px, step 4 on a 1/4 grid): best shift and residual share of
             differing pixels; also against the horizontally flipped L2 (a mirrored document
             would match the flip instead)
  O3         where both AT-SPI dumps exist: share of matched showing elements whose L2 box is the
             reflection of the L1 box inside the window (2 px), and the share that did not move
Usage: python3 s2v3_pilot_b_analysis.py <run-b dir> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FSI, PDI = "⁨", "⁩"


def load(p: Path):
    return np.asarray(Image.open(p).convert("L"), dtype=np.int16)


def ink_corr(a, b):
    pa = (a[30:180] < 200).sum(axis=0).reshape(120, -1).sum(axis=1).astype(float)
    pb = (b[30:180] < 200).sum(axis=0).reshape(120, -1).sum(axis=1).astype(float)
    def c(x, y):
        if x.std() == 0 or y.std() == 0:
            return None
        return float(np.corrcoef(x, y)[0, 1])
    return c(pa, pb[::-1]), c(pa, pb)


def doc_match(a, b):
    A = a[270:1000:4, ::4]
    B = b[270:1000:4, ::4]
    ref = A[:, 75:400]
    best = (None, 1.0)
    for s in range(-50, 51):
        lo = 75 + s
        if lo < 0 or lo + ref.shape[1] > B.shape[1]:
            continue
        d = float((np.abs(B[:, lo:lo + ref.shape[1]] - ref) > 16).mean())
        if d < best[1]:
            best = (4 * s, d)
    return best


def key(n):
    return (tuple(n["path"]), n["role"], n["name"].replace(FSI, "").replace(PDI, ""))


def o3(na, nb, wx, ww, tol=2):
    L = {key(n): n for n in na if n.get("showing") and n["box"][2] > 0 and n["box"][3] > 0}
    R = {key(n): n for n in nb if n.get("showing") and n["box"][2] > 0 and n["box"][3] > 0}
    common = sorted(set(L) & set(R))
    if not common:
        return None
    refl = same = 0
    bad_roles = {}
    for k in common:
        lx, ly, lw, lh = L[k]["box"]
        rx, ry, rw, rh = R[k]["box"]
        exp = wx + ww - (lx - wx) - lw
        if abs(rx - exp) <= tol and abs(ry - ly) <= tol:
            refl += 1
        else:
            bad_roles[k[1]] = bad_roles.get(k[1], 0) + 1
        if abs(rx - lx) <= tol and abs(ry - ly) <= tol:
            same += 1
    return {"matched": len(common), "reflected_share": refl / len(common), "unmoved_share": same / len(common),
            "not_reflected_by_role": dict(sorted(bad_roles.items(), key=lambda kv: -kv[1])[:8]),
            "l1_only": len(set(L) - set(R)), "l2_only": len(set(R) - set(L))}


def main() -> int:
    run = Path(sys.argv[1])
    rec = json.loads((run / "pilot-b-record.json").read_text())
    by = {}
    for r in rec["results"]:
        by.setdefault(r["task_id"], {})[r["cell"]] = r
    rows = []
    for tid, cells in sorted(by.items()):
        row = {"task_id": tid, "app": next(iter(cells.values())).get("app")}
        titles = {}
        for c, r in cells.items():
            ws = [w["title"] for w in r.get("windows", []) if "LibreOffice" in w["title"]]
            titles[c] = ws
        row["titles"] = titles
        row["titles_identical"] = len({json.dumps(v, ensure_ascii=False) for v in titles.values()}) == 1 and len(titles) == 3
        opened = cells.get("L1", {}).get("opened") or []
        fname = Path(opened[0]).name if opened else None
        row["opened_file"] = fname
        row["setup_opened_all"] = bool(fname) and all(any(fname in t for t in titles.get(c, [])) for c in ("L1", "L2", "L4"))
        row["setup_not_emulated"] = sorted({s["type"] for r in cells.values() for s in r.get("setup_steps", [])
                                            if s.get("emulated") is False})
        row["downloads_uncached"] = sum(1 for s in cells.get("L1", {}).get("setup_steps", []) if s["type"] == "download" and not s["cached"])
        shots = {c: run / "shots" / f"{tid}-{c}.png" for c in ("L1", "L2", "L4")}
        if all(p.exists() for p in shots.values()):
            a, b, d = load(shots["L1"]), load(shots["L2"]), load(shots["L4"])
            row["L2_vs_L4_differing_pixel_share"] = float((np.abs(b - d) > 16).mean())
            row["L1_vs_L2_differing_pixel_share"] = float((np.abs(a - b) > 16).mean())
            row["chrome_corr_mirrored"], row["chrome_corr_same"] = ink_corr(a, b)
            row["doc_shift_px"], row["doc_residual"] = doc_match(a, b)
            row["doc_shift_flipped_px"], row["doc_residual_flipped"] = doc_match(a, b[:, ::-1])
        fa, fb = run / "a11y" / f"{tid}-L1.json", run / "a11y" / f"{tid}-L2.json"
        if fa.exists() and fb.exists():
            win = next((w for w in cells["L1"].get("windows", []) if "LibreOffice" in w["title"]), None)
            if win:
                row["o3"] = o3(json.loads(fa.read_text())["nodes"], json.loads(fb.read_text())["nodes"], win["x"], win["w"])
        rows.append(row)

    def share(pred, rs):
        rs = [r for r in rs if pred(r) is not None]
        return None if not rs else round(sum(1 for r in rs if pred(r)) / len(rs), 4)

    have = [r for r in rows if "doc_residual" in r]
    o3s = [r["o3"] for r in rows if r.get("o3")]
    summary = {
        "tasks": len(rows),
        "setup_opened_all_cells": sum(1 for r in rows if r["setup_opened_all"]),
        "titles_identical_all_cells": sum(1 for r in rows if r["titles_identical"]),
        "tasks_with_unemulated_setup_steps": sum(1 for r in rows if r["setup_not_emulated"]),
        "downloads_uncached": sum(r["downloads_uncached"] for r in rows),
        "screens_compared": len(have),
        "L2_equals_L4_exactly": sum(1 for r in have if r["L2_vs_L4_differing_pixel_share"] == 0.0),
        "L2_vs_L4_max_differing_share": max((r["L2_vs_L4_differing_pixel_share"] for r in have), default=None),
        "chrome_corr_mirrored_median": float(np.median([r["chrome_corr_mirrored"] for r in have if r["chrome_corr_mirrored"] is not None])) if have else None,
        "chrome_corr_same_median": float(np.median([r["chrome_corr_same"] for r in have if r["chrome_corr_same"] is not None])) if have else None,
        "doc_residual_median": float(np.median([r["doc_residual"] for r in have])) if have else None,
        "doc_residual_flipped_median": float(np.median([r["doc_residual_flipped"] for r in have])) if have else None,
        "doc_matched_unflipped_lt_0p02": sum(1 for r in have if r["doc_residual"] < 0.02),
        "doc_matched_flipped_lt_0p02": sum(1 for r in have if r["doc_residual_flipped"] < 0.02),
        "o3_tasks": len(o3s),
        "o3_reflected_share_median": float(np.median([o["reflected_share"] for o in o3s])) if o3s else None,
        "o3_reflected_share_min": min((o["reflected_share"] for o in o3s), default=None),
        "o3_unmoved_share_median": float(np.median([o["unmoved_share"] for o in o3s])) if o3s else None,
        "o3_matched_elements_median": float(np.median([o["matched"] for o in o3s])) if o3s else None,
    }
    out = {"schema": "s2v3-pilot-b-analysis-v1", "summary": summary, "tasks": rows}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
