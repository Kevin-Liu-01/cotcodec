"""S2 v3 Phase 0: the factorial render oracle (registration v3.1, P0.7), on pixel-located boxes.

Reads one capture directory written by ``harness/s2_locale/capture.py`` (screenshots, accessibility
dumps, records and saved result files) and returns per-task, per-check records. Runs on the
development Mac (numpy, scipy, Pillow); it never touches the host.

Element boxes. AT-SPI extents are used only in left-to-right cells, where they are valid; in a
mirrored cell a median 53% of LibreOffice 7.3.7.2's accessibles keep their unmirrored extents
(wave-1 pilot job 1100), so every right-to-left box is located by ink: the element's ink in the
left-to-right screenshot (inside its accessible box, against the box's own background) is
template-matched in the other cell's screenshot.

Checks (pairs are LTR -> other cell of the same text level unless stated):

* O1 structure: the (path, role) list of showing accessibles. Text pairs (E-A, ER-AR) must be
  identical (instrument); layout pairs (E-ER, A-AR) differences are O8 structure defects.
* O2 text runs: each single-run text element's whole ink run, located in the other layout level
  and re-cut there by its own ink box, is the same image as in the left-to-right level (same size
  within 1 px, at most 2% of pixels differing); a failure is a coupling leak candidate (a run whose
  characters bidi reordered keeps its width and changes its image).
* O3 mirror fidelity: the element's ink sits at the reflection of its LTR box inside the window
  (|dy| <= 2 px and |dx| <= tol3 at mismatch <= tol2). The mirror specification frozen on the dev
  tasks is tol3, the 95th percentile of |dx| among dev-task elements found intact within 24 px of
  their reflection: this build mirrors toolbars and the menubar by reversing their packing, not by
  an exact geometric reflection, so a fixed 2 px line would mark the build itself as defective.
* O4 order under text swap: sibling left-to-right order equal in E and A (accessible boxes) and in
  ER and AR (ink-located boxes).
* O5 content identity: the document region of E, aligned by translation in the other cell, differs
  in at most tol5 pixels; the horizontally flipped region is compared too (a mirrored document
  matches the flip); flip-symmetric content is reported as uninformative.
* O6 invisibility: the E screenshot equals the stock S screenshot up to tol6 pixels.
* O7 window title: byte-identical in every cell and equal to the task's postconfig target.
* O8 RTL-defect inventory: elements misplaced outside the specification, clipped (ink found but
  narrower than 0.8 of the LTR ink), or missing (no intact match, or absent from the mirrored
  accessibility tree); per task; descriptive, never an exclusion.

Tolerances come from the A/A replicates (E-E2, ER-ER2) on the 17 dev tasks, as registered, with
one addition for elements that move: tol2 = max(0.02, 2 x the worst identity A/A element mismatch,
the 95th percentile mismatch of dev-task toolbar elements found intact at a new position in the
same row of the shuffled-toolbar placebo, capped at 0.10); tol5 and tol6 = max(50 px, 2 x the worst
A/A pixel count). Positive controls: planted in the application (PCL/PCR coupled string, PD
document change) and synthetic plants on every task's mirrored screenshot (a shifted widget for
O3, a reordered text run for O2, an altered document block for O5).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.signal import fftconvolve

ARABIC = re.compile(r"[؀-ۿ]")
LETTER = re.compile(r"[A-Za-zÀ-ɏ؀-ۿ]")
TAGGED = "‖"
CHROME_ROLES = {"push button", "toggle button", "menu", "menu item", "check menu item", "radio menu item",
                "label", "page tab", "combo box", "text", "spin button", "check box", "radio button",
                "list item", "tool bar", "status bar", "menu bar", "heading", "icon", "split button",
                "push button menu", "panel"}
LEAF_ROLES = {"push button", "toggle button", "menu", "menu item", "check menu item", "radio menu item",
              "label", "page tab", "combo box", "text", "spin button", "check box", "radio button",
              "list item", "split button", "push button menu", "icon", "heading"}
TEXT_ROLES = {"label", "menu", "page tab", "heading", "list item"}
DOC_ROLES = ("document spreadsheet", "document text", "document presentation", "document frame")
INK_DIFF = 40
LOCAL_R = 24
SEED = 42


def load_png(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------
# elements and ink


def showing_nodes(dump: dict) -> list[dict]:
    return [n for n in dump.get("nodes", []) if n.get("showing")]


def frame_box(nodes: list[dict]) -> tuple[int, int, int, int] | None:
    frames = [n for n in nodes if n["role"] == "frame" and n["box"][2] > 1000]
    if not frames:
        return None
    x, y, w, h = max(frames, key=lambda n: n["box"][2] * n["box"][3])["box"]
    return x, y, w, h


def border_ink(img: np.ndarray, box) -> float:
    """Non-uniformity of a box's one-pixel border: the share of border pixels that differ (by more
    than INK_DIFF / 2) from the border's own modal colour. A box that frames a whole widget has a
    uniform border (background, or the widget's own frame line); a box shifted onto other content
    cuts through it."""
    x, y, w, h = box
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 1.0
    crop = img[y0:y1, x0:x1]
    sides = [crop[0], crop[-1], crop[:, 0], crop[:, -1]]
    worst = 0.0
    for side in sides:
        px = side.astype(np.int64)
        packed = (px[:, 0] << 16) | (px[:, 1] << 8) | px[:, 2]
        vals, counts = np.unique(packed, return_counts=True)
        v = int(vals[np.argmax(counts)])
        mode = np.array([(v >> 16) & 255, (v >> 8) & 255, v & 255])
        worst = max(worst, float((np.abs(px - mode).max(axis=1) > INK_DIFF // 2).mean()))
    return worst


def _judged(n) -> bool:
    w, h = n["box"][2], n["box"][3]
    return ((n["role"] in LEAF_ROLES and w <= 640 and h <= 120) or n["role"] in DOC_ROLES
            or n["role"] in ("tool bar", "status bar")) and w >= 6 and h >= 6


def estimate_dy(img: np.ndarray, nodes: list[dict], max_dy: int = 48) -> int:
    """The VCL widgets' vertical offset: the shift in 0..max_dy px that best frames the judged
    accessibles (lowest mean border ink, each node scored at min(shift 0, shift d) so the native
    GTK widgets, correct at 0, do not pull the estimate)."""
    judged = [n for n in nodes if _judged(n)]
    if not judged:
        return 0
    b0 = np.array([border_ink(img, n["box"]) for n in judged])
    best, best_d = None, 0
    for d in range(0, max_dy + 1):
        bd = np.array([border_ink(img, (n["box"][0], n["box"][1] + d, n["box"][2], n["box"][3])) for n in judged])
        sc = float(np.minimum(b0, bd).mean())
        if best is None or sc < best - 1e-9:
            best, best_d = sc, d
    return best_d


def place_nodes(img: np.ndarray, nodes: list[dict], dy_vcl: int) -> list[dict]:
    """Screen boxes for accessibles in a left-to-right cell.

    Under the container's window manager, LibreOffice's native GTK widgets (the menubar, welded
    entries) report screen coordinates while its VCL-drawn widgets (toolbars, status bar, sheet
    tabs, document) report coordinates ``dy_vcl`` px too high (the window's frame offset, estimated
    per screenshot by ``estimate_dy``; smoke 1124). Each node takes the offset, 0 or ``dy_vcl``,
    whose box frames its content more cleanly (less ink on the box border); nodes too thin to judge
    keep their parent's choice.
    """
    out = []
    choice: dict[tuple, int] = {}
    menubars = [tuple(n["path"]) for n in nodes if n["role"] == "menu bar"]
    statusbars = [tuple(n["path"]) for n in nodes if n["role"] == "status bar"]
    for n in sorted(nodes, key=lambda n: len(n["path"])):
        x, y, w, h = n["box"]
        path = tuple(n["path"])
        if any(path[:len(m)] == m for m in menubars):
            off = 0  # the native GTK menubar and its menus
        elif any(path[:len(m)] == m for m in statusbars):
            off = dy_vcl  # VCL's status bar (a strip whose border ink cannot decide)
        elif _judged(n):
            b0 = border_ink(img, (x, y, w, h))
            b1 = border_ink(img, (x, y + dy_vcl, w, h))
            parent = choice.get(path[:-1])
            off = dy_vcl if b1 + 0.02 < b0 else (0 if b0 + 0.02 < b1 else (parent if parent is not None else dy_vcl))
        else:
            parent = choice.get(path[:-1])
            off = parent if parent is not None else dy_vcl
        choice[tuple(n["path"])] = off
        m = dict(n)
        m["box"] = [x, y + off, w, h]
        m["dy"] = off
        out.append(m)
    return out


def leaf_elements(nodes: list[dict], screen=(1920, 1080)) -> list[dict]:
    out, seen = [], set()
    for n in nodes:
        x, y, w, h = n["box"]
        if n["role"] not in LEAF_ROLES or w < 4 or h < 4 or w > 640 or h > 120:
            continue
        # clip to the screen: in the container the window's bottom edge sits a few pixels below
        # the screen, so the status bar's boxes overhang it by 3-4 px
        x0, y0, x1, y1 = max(0, x), max(0, y), min(screen[0], x + w), min(screen[1], y + h)
        if x1 - x0 < 4 or y1 - y0 < 4 or (x1 - x0) * (y1 - y0) < 0.6 * w * h:
            continue
        x, y, w, h = x0, y0, x1 - x0, y1 - y0
        n = {**n, "box": [x, y, w, h]}
        key = (x, y, w, h)
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def ink_template(img: np.ndarray, box) -> dict | None:
    x, y, w, h = box
    crop = img[y:y + h, x:x + w]
    if crop.size == 0:
        return None
    border = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    vals, counts = np.unique(border.reshape(-1, 3), axis=0, return_counts=True)
    bg = vals[np.argmax(counts)]
    mask = np.abs(crop - bg).max(axis=2) > INK_DIFF
    if mask.sum() < 8:
        return None
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cols = mask[y0:y1, x0:x1].any(axis=0)
    gaps, run = [], 0
    for c in cols:
        if not c:
            run += 1
        else:
            if run:
                gaps.append(run)
            run = 0
    return {"box": (x + x0, y + y0, x1 - x0, y1 - y0), "tpl": crop[y0:y1, x0:x1].copy(),
            "mask": mask[y0:y1, x0:x1].copy(), "max_gap": max(gaps) if gaps else 0, "ink": int(mask.sum())}


def mismatch_at(img: np.ndarray, tpl: np.ndarray, x: int, y: int) -> float:
    h, w = tpl.shape[:2]
    if x < 0 or y < 0 or y + h > img.shape[0] or x + w > img.shape[1]:
        return 1.0
    diff = np.abs(img[y:y + h, x:x + w] - tpl).max(axis=2)
    return float((diff > INK_DIFF).mean())


def local_search(img, tpl, ex, ey, rx=LOCAL_R, ry=3):
    best = (1.0, 0, 0)
    h, w = tpl.shape[:2]
    H, W = img.shape[:2]
    x0, x1 = max(0, ex - rx), min(W - w, ex + rx)
    y0, y1 = max(0, ey - ry), min(H - h, ey + ry)
    if x1 < x0 or y1 < y0:
        return best
    region = img[y0:y1 + h, x0:x1 + w]
    win = np.lib.stride_tricks.sliding_window_view(region, (h, w, 3))[:, :, 0]
    diff = (np.abs(win - tpl).max(axis=-1) > INK_DIFF).mean(axis=(-1, -2))
    iy, ix = np.unravel_index(np.argmin(diff), diff.shape)
    return float(diff[iy, ix]), int(x0 + ix - ex), int(y0 + iy - ey)


def band_search(img, tpl, ey, x_lo=0, x_hi=None, ry=6):
    """Best position of tpl in the horizontal band around row ey (grey SSD by FFT, refined in RGB)."""
    h, w = tpl.shape[:2]
    H, W = img.shape[:2]
    x_hi = W if x_hi is None else x_hi
    y0, y1 = max(0, ey - ry), min(H, ey + h + ry)
    band = img[y0:y1, x_lo:x_hi].mean(axis=2)
    t = tpl.mean(axis=2)
    if band.shape[0] < h or band.shape[1] < w:
        return 1.0, None, None
    ones = np.ones_like(t)
    s_ii = fftconvolve(band ** 2, ones[::-1, ::-1], mode="valid")
    s_it = fftconvolve(band, t[::-1, ::-1], mode="valid")
    ssd = s_ii - 2 * s_it + (t ** 2).sum()
    flat = np.argsort(ssd, axis=None)[:5]
    best = (1.0, None, None)
    for f in flat:
        iy, ix = np.unravel_index(f, ssd.shape)
        mm = mismatch_at(img, tpl, x_lo + ix, y0 + iy)
        if mm < best[0]:
            best = (mm, x_lo + int(ix), y0 + int(iy))
    return best


def column_search(img, tpl, ex, rx=6):
    h, w = tpl.shape[:2]
    H, W = img.shape[:2]
    x0, x1 = max(0, ex - rx), min(W, ex + w + rx)
    col = img[:, x0:x1].mean(axis=2)
    t = tpl.mean(axis=2)
    if col.shape[1] < w:
        return 1.0, None, None
    ones = np.ones_like(t)
    ssd = fftconvolve(col ** 2, ones[::-1, ::-1], mode="valid") - 2 * fftconvolve(col, t[::-1, ::-1], mode="valid") + (t ** 2).sum()
    best = (1.0, None, None)
    for f in np.argsort(ssd, axis=None)[:5]:
        iy, ix = np.unravel_index(f, ssd.shape)
        mm = mismatch_at(img, tpl, x0 + ix, iy)
        if mm < best[0]:
            best = (mm, x0 + int(ix), int(iy))
    return best


def recut_run(img: np.ndarray, x: int, y: int, w: int, h: int, gap: int, margin: int = 8):
    """The ink run around box (x, y, w, h): the box widened by margin, ink columns joined across
    gaps up to ``gap`` px, cut by its own ink box. Returns the RGB cut or None."""
    H, W = img.shape[:2]
    x0, x1 = max(0, x - margin), min(W, x + w + margin)
    y0, y1 = max(0, y - 1), min(H, y + h + 1)
    win = img[y0:y1, x0:x1]
    if win.size == 0:
        return None
    border = np.concatenate([win[0], win[-1], win[:, 0], win[:, -1]])
    vals, counts = np.unique(border.reshape(-1, 3), axis=0, return_counts=True)
    bg = vals[np.argmax(counts)]
    mask = np.abs(win - bg).max(axis=2) > INK_DIFF
    cols = mask.any(axis=0)
    if not cols.any():
        return None
    c = min(max(x - x0 + w // 2, 0), len(cols) - 1)
    if not cols[c]:
        near = np.nonzero(cols)[0]
        c = int(near[np.argmin(np.abs(near - c))])
    lo = hi = c
    while lo > 0 and cols[max(0, lo - 1 - gap):lo].any():
        lo -= 1
    while hi < len(cols) - 1 and cols[hi + 1:hi + 2 + gap].any():
        hi += 1
    sub = mask[:, lo:hi + 1]
    ys = np.nonzero(sub.any(axis=1))[0]
    xs = np.nonzero(sub.any(axis=0))[0]
    return win[ys.min():ys.max() + 1, lo + xs.min():lo + xs.max() + 1]


def run_identity(ltr_img: np.ndarray, ink: dict, oth_img: np.ndarray, fx: int, fy: int, tol2: float = 0.02) -> dict:
    """O2 for a text run: the run re-cut around its located position in the other cell equals the
    run re-cut the same way around its box in the left-to-right cell.

    Both cuts use one rule (the box widened by 8 px, ink columns joined across gaps up to the
    run's own largest gap, cut by the joined ink box), so nested or adjacent accessibles cut the
    same in both cells; a run whose characters bidi reordered (a trailing colon moved to the
    front) keeps its width and changes its image, and fails. Template alignment alone matches the
    unmoved part and misses that.
    """
    x, y, w, h = ink["box"]
    gap = max(3, ink["max_gap"])
    a = recut_run(ltr_img, x, y, w, h, gap)
    b = recut_run(oth_img, fx, fy, w, h, gap)
    if a is None or b is None:
        return {"identical": False, "reason": "no ink"}
    if abs(a.shape[1] - b.shape[1]) > 1 or abs(a.shape[0] - b.shape[0]) > 1:
        return {"identical": False, "reason": "size", "w": [int(a.shape[1]), int(b.shape[1])]}
    hh, ww = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    mm = float((np.abs(a[:hh, :ww] - b[:hh, :ww]).max(axis=2) > INK_DIFF).mean())
    return {"identical": mm <= tol2, "mismatch": round(mm, 4)}


# ------------------------------------------------------------------------------------------
# pairwise element analysis


TOL_LOCATE = 0.10


def element_pass(ltr_img, oth_img, ltr_nodes, frame, mode: str, tol2: float, oth_paths=None, tol3: int = 2) -> list[dict]:
    """mode: 'reflect' (LTR -> mirrored), 'identity' (A/A; placebo: in-row moves), 'column' (vertical moves).

    Locating uses a fixed tolerance (TOL_LOCATE = 0.10 of template pixels): the question is where
    the widget is, and a mirrored toolbar redraws its icons with one-pixel offsets (2-4% of pixels).
    at_expected: located within tol3 px of the expected position; intact: located anywhere in its
    row band. O2's pixel identity of text runs uses tol2 (registered) through run_identity.
    """
    fx, fy, fw, fh = frame
    out = []
    for n in leaf_elements(ltr_nodes):
        ink = ink_template(ltr_img, n["box"])
        if ink is None:
            continue
        ix, iy, iw, ih = ink["box"]
        if mode == "reflect":
            ex = fx + fx + fw - (ix + iw)
        else:
            ex = ix
        ey = iy
        lm, ldx, ldy = local_search(oth_img, ink["tpl"], ex, ey)
        rec = {"path": n["path"], "role": n["role"], "name": n["name"], "ltr_box": list(n["box"]),
               "ink_box": list(ink["box"]), "max_gap": ink["max_gap"], "ink": ink["ink"],
               "local_mismatch": round(lm, 4), "dx": ldx, "dy": ldy}
        rec["at_expected"] = lm <= TOL_LOCATE and abs(ldx) <= tol3 and abs(ldy) <= 2
        rec["near_expected"] = lm <= TOL_LOCATE
        if rec["at_expected"]:
            rec["found_mismatch"], rec["found_x"], rec["found_y"] = rec["local_mismatch"], ex + ldx, ey + ldy
        else:
            if mode == "column":
                bm, bx, by = column_search(oth_img, ink["tpl"], ix)
            else:
                bm, bx, by = band_search(oth_img, ink["tpl"], ey)
            if lm < bm:
                bm, bx, by = lm, ex + ldx, ey + ldy
            rec["found_mismatch"], rec["found_x"], rec["found_y"] = round(bm, 4), bx, by
        rec["intact"] = rec["found_mismatch"] <= TOL_LOCATE
        if rec["intact"] and rec["found_x"] is not None:
            rec["disp_x"] = int(rec["found_x"] - ix)
            rec["disp_y"] = int(rec["found_y"] - iy)
            rec["unmoved"] = abs(rec["found_x"] - ix) <= 2 and abs(rec["found_y"] - iy) <= 2
        else:
            rec["unmoved"] = False
        # clipping: the left or right part of the ink found at the expected place, the rest not
        if not rec["intact"] and mode == "reflect" and iw >= 16:
            half = iw // 2
            lm1, _, _ = local_search(oth_img, ink["tpl"][:, :half], ex, ey, rx=6, ry=2)
            lm2, _, _ = local_search(oth_img, ink["tpl"][:, half:], ex + half, ey, rx=6, ry=2)
            rec["clipped"] = (min(lm1, lm2) <= TOL_LOCATE) and (max(lm1, lm2) > TOL_LOCATE)
        else:
            rec["clipped"] = False
        rec["text_run"] = n["role"] in TEXT_ROLES and ink["max_gap"] <= 12
        if rec["text_run"]:
            if rec["intact"] and rec["found_x"] is not None:
                rec["run"] = run_identity(ltr_img, ink, oth_img, rec["found_x"], rec["found_y"], tol2)
            else:
                rec["run"] = {"identical": False, "reason": "not located"}
        if oth_paths is not None:
            rec["in_other_tree"] = (tuple(n["path"]), n["role"]) in oth_paths
        out.append(rec)
    return out


def structure(nodes: list[dict]) -> list[tuple]:
    return sorted((tuple(n["path"]), n["role"]) for n in nodes)


def structure_diff(a: list[dict], b: list[dict]) -> dict:
    sa, sb = Counter(structure(a)), Counter(structure(b))
    only_a = sum((sa - sb).values())
    only_b = sum((sb - sa).values())
    return {"n_a": sum(sa.values()), "n_b": sum(sb.values()), "only_a": only_a, "only_b": only_b,
            "identical": only_a == 0 and only_b == 0,
            "only_a_roles": dict(Counter(r for (_, r) in (sa - sb).elements()).most_common(8)),
            "only_b_roles": dict(Counter(r for (_, r) in (sb - sa).elements()).most_common(8))}


def sibling_order(boxes: dict[tuple, int]) -> dict[tuple, list]:
    by_parent = defaultdict(list)
    for path, x in boxes.items():
        by_parent[path[:-1]].append((x, path[-1]))
    return {p: [i for _, i in sorted(v)] for p, v in by_parent.items() if len(v) > 1}


def order_agreement(o1: dict, o2: dict) -> dict:
    common = set(o1) & set(o2)
    same = 0
    for p in common:
        a = [i for i in o1[p] if i in set(o2[p])]
        b = [i for i in o2[p] if i in set(o1[p])]
        same += int(a == b)
    return {"parents": len(common), "same_order": same, "share": round(same / len(common), 4) if common else None}


# ------------------------------------------------------------------------------------------
# whole-screen and document checks


def pixel_diff(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(a - b).max(axis=2) > INK_DIFF // 2
    n = int(d.sum())
    rec = {"diff_pixels": n}
    if n:
        ys, xs = np.nonzero(d)
        rec["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        # coarse location histogram: 8 x 6 grid
        H, W = d.shape
        grid = np.zeros((6, 8), dtype=int)
        np.add.at(grid, (np.minimum(ys * 6 // H, 5), np.minimum(xs * 8 // W, 7)), 1)
        rec["grid_6x8"] = grid.tolist()
    return rec


def doc_region(nodes: list[dict]) -> list[int] | None:
    docs = [n for n in nodes if n["role"] in DOC_ROLES and n["box"][2] > 200 and n["box"][3] > 150]
    if not docs:
        return None
    x, y, w, h = max(docs, key=lambda n: n["box"][2] * n["box"][3])["box"]
    x0, y0 = max(0, x + 4), max(0, y + 4)
    x1, y1 = min(1920, x + w - 4), min(1080, y + h - 4)
    return [x0, y0, x1 - x0, y1 - y0]


def align_count(ref: np.ndarray, img: np.ndarray, box, max_dy=60, flip=False) -> dict:
    """Best translation of the reference document crop in img; mismatching pixels on the overlap.

    Coarse: grey SSD by FFT on 4x-downsampled images over the full width and +/- max_dy rows.
    Fine: +/-3 px around the best coarse offset on every second pixel; the count at the chosen
    offset is then taken at full resolution.
    """
    x, y, w, h = box
    crop = ref[y:y + h, x:x + w]
    if flip:
        crop = crop[:, ::-1]
    g = crop.mean(axis=2)
    gi = img.mean(axis=2)

    def ds(a):
        H, W = a.shape[0] // 4 * 4, a.shape[1] // 4 * 4
        return a[:H, :W].reshape(H // 4, 4, W // 4, 4).mean(axis=(1, 3))

    cg = ds(g)
    y_lo, y_hi = max(0, y - max_dy), min(img.shape[0], y + h + max_dy)
    band = ds(gi[y_lo:y_hi])
    if band.shape[0] < cg.shape[0] or band.shape[1] < cg.shape[1]:
        return {"ok": False}
    ones = np.ones_like(cg)
    ssd = (fftconvolve(band ** 2, ones[::-1, ::-1], mode="valid") - 2 * fftconvolve(band, cg[::-1, ::-1], mode="valid"))
    cy, cx = np.unravel_index(np.argmin(ssd), ssd.shape)
    y0, x0 = y_lo + cy * 4, cx * 4
    sub = crop[::2, ::2]
    best = None
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            yy, xx = y0 + dy, x0 + dx
            if yy < 0 or xx < 0 or yy + h > img.shape[0] or xx + w > img.shape[1]:
                continue
            d = int((np.abs(img[yy:yy + h:2, xx:xx + w:2] - sub).max(axis=2) > INK_DIFF // 2).sum())
            if best is None or d < best[0]:
                best = (d, yy, xx)
    if best is None:
        return {"ok": False}
    _, yy, xx = best
    n = int((np.abs(img[yy:yy + h, xx:xx + w] - crop).max(axis=2) > INK_DIFF // 2).sum())
    return {"ok": True, "diff_pixels": n, "dx": int(xx - x), "dy": int(yy - y),
            "ink_pixels_ref": int((np.abs(crop - np.median(crop.reshape(-1, 3), axis=0)).max(axis=2) > INK_DIFF).sum())}


def o5(ref_img, oth_img, box, tol5, max_dy=60) -> dict:
    un = align_count(ref_img, oth_img, box, max_dy=max_dy)
    fl = align_count(ref_img, oth_img, box, max_dy=max_dy, flip=True)
    rec = {"unflipped": un, "flipped": fl}
    if not un.get("ok"):
        rec["verdict"] = "no_alignment"
        return rec
    u = un["diff_pixels"]
    f = fl["diff_pixels"] if fl.get("ok") else 10 ** 9
    if u <= tol5 and f <= tol5:
        rec["verdict"] = "uninformative_symmetric"
    elif u <= tol5:
        rec["verdict"] = "pass"
    elif f <= tol5:
        rec["verdict"] = "fail_mirrored"
    else:
        rec["verdict"] = "fail_changed"
    return rec


# ------------------------------------------------------------------------------------------
# saved files


RSID = re.compile(rb'\s(?:w:rsid\w*|officeooo:(?:paragraph-)?rsid)="[^"]*"')
RSIDS_BLOCK = re.compile(rb"<w:rsids>.*?</w:rsids>", re.S)
VOLATILE_PARTS = {"docProps/core.xml", "docProps/app.xml", "meta.xml", "Thumbnails/thumbnail.png",
                  "docProps/thumbnail.jpeg"}


def canonical_parts(path: Path) -> dict[str, str] | None:
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError):
        return None
    out = {}
    for n in sorted(z.namelist()):
        if n in VOLATILE_PARTS:
            continue
        b = z.read(n)
        b = RSID.sub(b"", b)
        b = RSIDS_BLOCK.sub(b"", b)
        out[n] = hashlib.sha256(b).hexdigest()
    return out


def scan_text(path: Path) -> dict:
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError):
        try:
            t = path.read_text(errors="replace")
        except Exception:  # noqa: BLE001
            return {"readable": False}
        return {"readable": True, "arabic": len(ARABIC.findall(t)), "tag": t.count(TAGGED)}
    ar = tg = 0
    where = []
    for n in z.namelist():
        if not (n.endswith(".xml") or n.endswith(".rels")):
            continue
        t = z.read(n).decode("utf-8", errors="replace")
        a, g = len(ARABIC.findall(t)), t.count(TAGGED)
        ar += a
        tg += g
        if a or g:
            where.append(n)
    return {"readable": True, "arabic": ar, "tag": tg, "parts": where[:10]}
