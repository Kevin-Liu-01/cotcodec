#!/usr/bin/env python3
"""S2 factorial render oracle (D68 repair): proves that text direction and layout direction vary separately.

The four cells cross interface text (en, ar) with layout (LTR, RTL). The oracle takes, per
cell and per reference state, a screenshot (PNG) and an element list, as the OSWorld
accessibility tree provides it (each element: a stable path, a role, its name and its screen
box), and checks that each factor reaches the screen only through its own channel:

  O1 structure   the (path, role) list is identical in all four cells;
  O2 text runs   every text-bearing element's ink (its rendered glyph run, cropped to the ink
                 bounding box) is the same image in the two layout levels of the same text
                 level (en vs en-RTL; ar-LTR vs ar-RTL). A bidi leak (a string reordered
                 because the paragraph direction followed the layout) changes the ink image;
  O3 mirror      every layout unit's box in the RTL cell is the horizontal reflection of its
                 LTR box inside the window, within a pixel tolerance (no half-mirrored layout);
  O4 order       siblings keep their visual order when only the text changes (en vs ar-LTR;
                 en-RTL vs ar-RTL): a text swap must not rearrange widgets;
  O5 content     the document-content region (the canvas) is pixel-identical in all four cells
                 (setup reached the same state; content is not part of the treatment).

Element list JSON (one file per cell and state):
  {"window": [x, y, w, h], "content": "<path of the content region or null>",
   "elements": [{"path": "...", "role": "...", "name": "...", "box": [x, y, w, h],
                 "text": true|false, "unit": true|false}, ...]}

Tolerances are inputs; Phase 0 calibrates them by an A/A (same cell rendered twice, and the
same string at two horizontal offsets) before the gate runs, and freezes them.

Usage:
  python oracle.py <cells.json> <out.json>
where cells.json maps {"state": {"en": [png, elements], "arL": [...], "enR": [...], "arR": [...]}}
plus optional "tolerance": {"o2_mismatch": 0.02, "o2_dim_px": 1, "o3_px": 2, "o5_mismatch": 0.0}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CELLS = ("en", "arL", "enR", "arR")
PAIRS_LAYOUT = (("en", "enR"), ("arL", "arR"))  # same text, layout differs
PAIRS_TEXT = (("en", "arL"), ("enR", "arR"))  # same layout, text differs
DEFAULT_TOL = {"o2_mismatch": 0.02, "o2_dim_px": 1, "o3_px": 2, "o5_mismatch": 0.0, "ink_threshold": 60}


def load(png: str, elements: str):
    img = np.asarray(Image.open(png).convert("L"), dtype=np.int16)
    el = json.loads(Path(elements).read_text())
    return img, el


def ink_mask(img, box, thr, inset=-2):
    """Ink of one text-bearing element: its box grown by -inset px (glyph overhang included),
    background = the most frequent grey level, ink = pixels differing from it by more than thr,
    cropped to the ink bounding box."""
    x, y, w, h = box
    x0, y0 = int(np.floor(x)) + inset, int(np.floor(y)) + inset
    x1, y1 = int(np.ceil(x + w)) - inset, int(np.ceil(y + h)) - inset
    crop = img[max(y0, 0) : max(y1, 0), max(x0, 0) : max(x1, 0)]
    if crop.size == 0:
        return None
    bg = np.bincount(crop.ravel().astype(np.int64)).argmax()
    m = np.abs(crop - bg) > thr
    if not m.any():
        return np.zeros((0, 0), dtype=bool)
    ys, xs = np.where(m)
    return m[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def _dilate(m):
    """3x3 binary dilation (one-pixel tolerance for rasterisation at a different subpixel phase)."""
    p = np.pad(m, 1)
    out = np.zeros_like(m)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            out |= p[dy : dy + m.shape[0], dx : dx + m.shape[1]]
    return out


def mask_mismatch(a, b, dim_tol):
    """Share of ink pixels of either run with no ink of the other run within one pixel.

    Both ink masks are placed on a common canvas at every offset the dimension tolerance allows
    and the best placement is kept. A glyph run rendered at another subpixel phase scores near
    0; a reordered run (a moved ellipsis, swapped words) leaves whole glyphs unmatched.
    """
    if a is None or b is None:
        return 1.0, "missing"
    if a.size == 0 and b.size == 0:
        return 0.0, "both-empty"
    if a.size == 0 or b.size == 0:
        return 1.0, "one-empty"
    if abs(a.shape[0] - b.shape[0]) > dim_tol or abs(a.shape[1] - b.shape[1]) > dim_tol:
        return 1.0, f"ink box {a.shape} vs {b.shape}"
    H, W = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    best = 1.0
    for ay in range(H - a.shape[0] + 1):
        for ax in range(W - a.shape[1] + 1):
            for by in range(H - b.shape[0] + 1):
                for bx in range(W - b.shape[1] + 1):
                    A = np.zeros((H, W), dtype=bool)
                    B = np.zeros((H, W), dtype=bool)
                    A[ay : ay + a.shape[0], ax : ax + a.shape[1]] = a
                    B[by : by + b.shape[0], bx : bx + b.shape[1]] = b
                    unmatched = np.logical_and(A, ~_dilate(B)).sum() + np.logical_and(B, ~_dilate(A)).sum()
                    best = min(best, float(unmatched / max(A.sum() + B.sum(), 1)))
    return best, ""


def check_state(state, cells, tol):
    data = {c: load(*cells[c]) for c in CELLS}
    out = {"state": state, "checks": {}}
    # O1
    sig = {c: [(e["path"], e["role"]) for e in data[c][1]["elements"]] for c in CELLS}
    o1_bad = [c for c in CELLS if sig[c] != sig["en"]]
    out["checks"]["O1_structure"] = {"pass": not o1_bad, "cells_differing_from_en": o1_bad, "n_elements": len(sig["en"])}
    idx = {c: {e["path"]: e for e in data[c][1]["elements"]} for c in CELLS}
    # O2
    leaks, checked = [], 0
    for a, b in PAIRS_LAYOUT:
        for p, e in idx[a].items():
            if not e.get("text") or p not in idx[b]:
                continue
            checked += 1
            ma = ink_mask(data[a][0], e["box"], tol["ink_threshold"])
            mb = ink_mask(data[b][0], idx[b][p]["box"], tol["ink_threshold"])
            mis, why = mask_mismatch(ma, mb, tol["o2_dim_px"])
            if mis > tol["o2_mismatch"]:
                leaks.append({"pair": f"{a}|{b}", "path": p, "name": e.get("name", ""), "mismatch": round(mis, 4), "note": why})
    out["checks"]["O2_text_run_identity"] = {"pass": not leaks, "runs_checked": checked, "leaks": leaks}
    # O3
    bad, checked = [], 0
    for a, b in PAIRS_LAYOUT:
        wx, wy, ww, wh = data[a][1]["window"]
        for p, e in idx[a].items():
            if not e.get("unit") or p not in idx[b]:
                continue
            checked += 1
            x, y, w, h = e["box"]
            xr, yr, wr, hr = idx[b][p]["box"]
            want = wx + ww - (x - wx) - w
            dx, dy = abs(xr - want), abs(yr - y)
            if dx > tol["o3_px"] or dy > tol["o3_px"] or abs(wr - w) > tol["o3_px"]:
                bad.append({"pair": f"{a}|{b}", "path": p, "x_ltr": x, "x_rtl": xr, "x_expected": round(want, 1), "dy": dy})
    out["checks"]["O3_mirror_fidelity"] = {"pass": not bad, "units_checked": checked, "violations": bad}
    # O4: a text swap must not rearrange widgets: siblings keep their vertical order, and siblings
    # that share a row (overlapping vertical extents) keep their horizontal order
    bad = []
    for a, b in PAIRS_TEXT:
        groups = {}
        for p, e in idx[a].items():
            if e.get("unit") and "/" in p:
                groups.setdefault(p.rsplit("/", 1)[0], []).append(p)
        for parent, kids in groups.items():
            kids = [k for k in kids if k in idx[b]]
            if len(kids) < 2:
                continue
            ya = sorted(kids, key=lambda k: (round(idx[a][k]["box"][1]), k))
            yb = sorted(kids, key=lambda k: (round(idx[b][k]["box"][1]), k))
            if ya != yb:
                bad.append({"pair": f"{a}|{b}", "parent": parent, "kind": "vertical", "order_a": ya, "order_b": yb})
                continue
            rows = []
            for k in ya:
                y0, h0 = idx[a][k]["box"][1], idx[a][k]["box"][3]
                if rows and y0 < rows[-1]["y1"] - 1:
                    rows[-1]["kids"].append(k)
                    rows[-1]["y1"] = max(rows[-1]["y1"], y0 + h0)
                else:
                    rows.append({"kids": [k], "y1": y0 + h0})
            for row in rows:
                if len(row["kids"]) < 2:
                    continue
                xa = sorted(row["kids"], key=lambda k: idx[a][k]["box"][0])
                xb = sorted(row["kids"], key=lambda k: idx[b][k]["box"][0])
                if xa != xb:
                    bad.append({"pair": f"{a}|{b}", "parent": parent, "kind": "horizontal", "order_a": xa, "order_b": xb})
    out["checks"]["O4_order_under_text_swap"] = {"pass": not bad, "violations": bad}
    # O5
    cp = data["en"][1].get("content")
    if cp:
        ref = None
        diffs = {}
        for c in CELLS:
            x, y, w, h = [int(round(v)) for v in idx[c][cp]["box"]]
            crop = data[c][0][y : y + h, x : x + w]
            if ref is None:
                ref = crop
                continue
            if crop.shape != ref.shape:
                diffs[c] = "shape"
                continue
            frac = float((crop != ref).mean())
            if frac > tol["o5_mismatch"]:
                diffs[c] = round(frac, 5)
        out["checks"]["O5_content_identity"] = {"pass": not diffs, "differing_cells": diffs}
    out["pass"] = all(v["pass"] for v in out["checks"].values())
    return out


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    tol = dict(DEFAULT_TOL)
    tol.update(spec.get("tolerance", {}))
    states = {k: v for k, v in spec.items() if k != "tolerance"}
    res = {"tolerance": tol, "states": [check_state(s, cells, tol) for s, cells in states.items()]}
    res["pass"] = all(s["pass"] for s in res["states"])
    inputs = {}
    for cells in states.values():
        for png, el in cells.values():
            for f in (png, el):
                inputs[Path(f).name] = hashlib.sha256(Path(f).read_bytes()).hexdigest()
    res["inputs_sha256"] = inputs
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"pass": res["pass"], "states": {s["state"]: {k: v["pass"] for k, v in s["checks"].items()} for s in res["states"]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
