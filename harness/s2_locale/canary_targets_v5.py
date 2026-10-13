"""S2 v5 step 0 (decision D94): the screenshot-only target rule for A6's two pointer composites.

``canary.yaml``'s targeting clause says the targets of ``triple_click_line`` and
``drag_select_word`` are "measured during development on the frozen app configuration". v4 never
measured them on its cell images, and on the mirrored images (ER, AR) Writer draws its document
71 px to the right of where q2 measured it on the certified disk (D93, D94). This module is the
rule D94 fixes before step 0 measures anything:

* Targets come from screenshots only: the glyph boxes of the canary fixture line. The drag runs
  from the left edge of ``w`` plus 1 px to the right edge of ``d`` minus 1 px (the ink box of the
  word ``word`` in ``keep word keep``), the triple-click hits the middle of ``this`` (the ink box of
  ``this`` in ``replace this line``), and y is the centre of the line's glyph rows. Integer
  midpoints round down (``(a + b) // 2``), as q2's own Writer triple-click target did (718 for
  ``this`` at 703-734). AT-SPI extents are copied into the step-0 report for disclosure only: no
  function here reads them for a decision (``decide`` ignores them; a test alters them).
* The segmentation and every threshold are constants below, fixed before step 0:
  1. a fixed region of the screen per application (``ROI``), generous around the line q2 measured
     (Writer's spans the shifted document area as well);
  2. luminance ``(299 R + 587 G + 114 B + 500) // 1000``; background = the median luminance of
     the region; ink = pixels at least ``INK_DELTA`` from the background (either polarity, since
     VS Code draws light text on a dark editor);
  3. straight lines removed: a column (row) whose ink covers at least ``LINE_COVERAGE`` of the
     region's rows (columns) is cleared (Writer's page border, Chrome's frame);
  4. text bands: maximal runs of rows that hold ink;
  5. the text caret removed: in a band, a column whose longest vertical ink run is at least
     ``CARET_RUN`` of the band's height is cleared (no letter of the two fixtures spans both
     ascender and descender rows in one column; the caret spans the whole line);
  6. glyph runs: maximal runs of columns that hold ink in the band; words: glyph runs closer than
     ``WORD_GAP_PX`` merged (about 0.75 of the app's character pitch);
  7. the fixture line: the one triple of consecutive words, in exactly one band, whose ink widths
     fit the fixture's word lengths at the app's pitch (``n p - WIDTH_LOW p`` to
     ``n p + WIDTH_HIGH p``) and whose two gaps are single spaces (at most ``SPACE_GAP_MAX p``);
     none, or more than one, is a failed measurement;
  8. glyph rows: the first and last ink rows within the triple's columns.

``decide`` applies step 0's admission tests and stop rule (the record
``program/preregistrations/s2-arabic-cua-locale-v5-step0.md``): only reading (a) proceeds; every
other outcome is an honest exit for S2, with no second measurement and no coordinate search.

Standard library only (the PNG reader is ``zlib``-based), so it runs on the host as it is.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "s2v5-step0-targets-v1"
APPS = ("writer", "chrome", "vscode")
ENTRIES = ("triple_click_line", "drag_select_word")
CELLS = ("E", "A", "ER", "AR", "PL")
BOOTS = 5
# The fixture of each entry (canary.yaml) and the index of the target word in it.
FIXTURES = {
    "triple_click_line": ("replace this line", 1),
    "drag_select_word": ("keep word keep", 1),
}
# Screen regions [x0, y0, x1, y1) searched for the fixture line, per application.
ROI = {
    "writer": (400, 230, 1600, 360),
    "chrome": (99, 136, 960, 230),
    "vscode": (548, 271, 1350, 330),
}
# Character pitch per application, from canary_targets.json's measured notes (development runs
# 501, 506 and 515): Liberation Mono 10 pt 7.94 px, Chrome 24 px monospace 14.4 px, VS Code 14 px
# 8.43 px. Fonts do not depend on the cell image.
PITCH_PX = {"writer": 7.94, "chrome": 14.4, "vscode": 8.43}
WORD_GAP_PX = {"writer": 6, "chrome": 11, "vscode": 6}
INK_DELTA = 80
LINE_COVERAGE = 0.5
CARET_RUN = 0.9
WIDTH_LOW = 0.75
WIDTH_HIGH = 0.5
SPACE_GAP_MAX = 2.0
DRAG_DURATION_MS = 500

# Step 0's tolerances (the record, section "Admission tests").
TOL_Q2_PX = 2  # a target reproduces another within 2 px, in x and in y
DRIFT_MAX_PX = 1  # glyph boxes agree within 1 px across the boots of one image
SHIFT_DX = (69, 73)  # ER and AR: the fixture at +71 +/- 2 px in x against E
SHIFT_DY = (0, 1)  # and 0 or +1 px in y
UNDER_MARGIN_PX = 3  # a drag end within 3 px of the word's ink box is "on the glyphs"
MIRRORED = ("ER", "AR")
V4_FAILURE_READBACK = "Ykeep word keep"  # job 1264, writer:drag_select_word, 5 of 5 (D93)


class PngError(ValueError):
    """Not a PNG this reader handles (8-bit grey, RGB or RGBA, not interlaced)."""


# --------------------------------------------------------------------------- PNG and luminance


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(ftype: int, line: bytes, prev: bytes, bpp: int) -> bytearray:
    out = bytearray(line)
    n = len(out)
    if ftype == 0:
        return out
    if ftype == 1:
        for i in range(bpp, n):
            out[i] = (out[i] + out[i - bpp]) & 0xFF
    elif ftype == 2:
        for i in range(n):
            out[i] = (out[i] + prev[i]) & 0xFF
    elif ftype == 3:
        for i in range(n):
            left = out[i - bpp] if i >= bpp else 0
            out[i] = (out[i] + ((left + prev[i]) >> 1)) & 0xFF
    elif ftype == 4:
        for i in range(n):
            left = out[i - bpp] if i >= bpp else 0
            upleft = prev[i - bpp] if i >= bpp else 0
            out[i] = (out[i] + _paeth(left, prev[i], upleft)) & 0xFF
    else:
        raise PngError(f"unknown filter type {ftype}")
    return out


def read_luminance(
    data: bytes, box: Sequence[int] | None = None
) -> tuple[int, int, list[list[int]]]:
    """(width, height, rows): the luminance of ``box`` = [x0, y0, x1, y1) of a PNG (the whole
    image when None). Rows below the box are not decoded."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError("not a PNG")
    pos, idat, header = 8, [], None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if header is None:
        raise PngError("no IHDR")
    width, height, depth, color, _, _, interlace = header
    channels = {0: 1, 2: 3, 6: 4}.get(color)
    if depth != 8 or channels is None or interlace != 0:
        raise PngError(
            f"unsupported PNG (depth {depth}, colour type {color}, interlace {interlace})"
        )
    x0, y0, x1, y1 = box if box is not None else (0, 0, width, height)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise PngError(f"box {list(box or [])} is outside the {width}x{height} image")
    raw = zlib.decompressobj()
    stride = width * channels
    buffer, prev, rows, y = b"", bytes(stride), [], 0
    for chunk in idat:
        buffer += raw.decompress(chunk)
        while len(buffer) >= stride + 1 and y < y1:
            line = _unfilter(buffer[0], buffer[1 : stride + 1], prev, channels)
            buffer = buffer[stride + 1 :]
            if y >= y0:
                if channels == 1:
                    rows.append(list(line[x0:x1]))
                else:
                    rows.append(
                        [
                            (299 * line[i] + 587 * line[i + 1] + 114 * line[i + 2] + 500) // 1000
                            for i in range(x0 * channels, x1 * channels, channels)
                        ]
                    )
            prev, y = bytes(line), y + 1
        if y >= y1:
            break
    if len(rows) != y1 - y0:
        raise PngError("truncated image data")
    return width, height, rows


def write_png_gray(rows: Sequence[Sequence[int]]) -> bytes:
    """A minimal 8-bit greyscale PNG (filter 0); for tests and synthetic fixtures."""
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


# --------------------------------------------------------------------------- segmentation


def _runs(flags: Sequence[bool]) -> list[tuple[int, int]]:
    out, start = [], None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def _median_low(rows: Sequence[Sequence[int]]) -> int:
    hist = [0] * 256
    for r in rows:
        for v in r:
            hist[v] += 1
    half, seen = (sum(hist) - 1) // 2, 0
    for value, count in enumerate(hist):
        seen += count
        if seen > half:
            return value
    raise ValueError("empty region")


def _longest_run(column: Sequence[bool]) -> int:
    best = cur = 0
    for v in column:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def segment(rows: Sequence[Sequence[int]], app: str, entry: str) -> dict[str, Any]:
    """The fixture line in ``rows``, the luminance of ``ROI[app]`` (screen coordinates out)."""
    x0, y0, x1, y1 = ROI[app]
    h, w = len(rows), len(rows[0]) if rows else 0
    if (w, h) != (x1 - x0, y1 - y0):
        return {"ok": False, "error": f"region is {w}x{h}, not {x1 - x0}x{y1 - y0}"}
    background = _median_low(rows)
    ink = [[abs(v - background) >= INK_DELTA for v in r] for r in rows]
    lines_cols = [c for c in range(w) if sum(ink[y][c] for y in range(h)) >= LINE_COVERAGE * h]
    for c in lines_cols:
        for y in range(h):
            ink[y][c] = False
    lines_rows = [y for y in range(h) if sum(ink[y]) >= LINE_COVERAGE * w]
    for y in lines_rows:
        ink[y] = [False] * w
    pitch, gap = PITCH_PX[app], WORD_GAP_PX[app]
    fixture, target = FIXTURES[entry]
    lengths = [len(word) for word in fixture.split(" ")]
    matches, bands = [], []
    for top, bottom in _runs([any(r) for r in ink]):
        band = [list(ink[y]) for y in range(top, bottom + 1)]
        height = bottom - top + 1
        caret = [
            c
            for c in range(w)
            if _longest_run([band[y][c] for y in range(height)]) >= CARET_RUN * height
        ]
        for c in caret:
            for y in range(height):
                band[y][c] = False
        glyphs = _runs([any(band[y][c] for y in range(height)) for c in range(w)])
        words: list[list[tuple[int, int]]] = []
        for run in glyphs:
            if words and run[0] - words[-1][-1][1] - 1 < gap:
                words[-1].append(run)
            else:
                words.append([run])
        boxes = [(ws[0][0], ws[-1][1]) for ws in words]
        bands.append(
            {
                "rows": [top + y0, bottom + y0],
                "caret_columns": [c + x0 for c in caret],
                "words": [[a + x0, b + x0] for a, b in boxes],
            }
        )
        for i in range(len(boxes) - len(lengths) + 1):
            triple = boxes[i : i + len(lengths)]
            fits = all(
                n * pitch - WIDTH_LOW * pitch <= b - a + 1 <= n * pitch + WIDTH_HIGH * pitch
                for n, (a, b) in zip(lengths, triple, strict=True)
            )
            spaces = all(
                0 < triple[k + 1][0] - triple[k][1] - 1 <= SPACE_GAP_MAX * pitch
                for k in range(len(triple) - 1)
            )
            if fits and spaces:
                matches.append((top, band, words[i : i + len(lengths)], triple))
    out: dict[str, Any] = {
        "app": app,
        "entry": entry,
        "background": background,
        "line_columns_removed": len(lines_cols),
        "line_rows_removed": len(lines_rows),
        "bands": bands,
    }
    if len(matches) != 1:
        out.update(ok=False, error=f"{len(matches)} fixture lines found (exactly one needed)")
        return out
    top, band, words, triple = matches[0]
    span = range(triple[0][0], triple[-1][1] + 1)
    ink_rows = [y for y in range(len(band)) if any(band[y][c] for c in span)]
    g_top, g_bottom = ink_rows[0] + top + y0, ink_rows[-1] + top + y0

    def glyph_box(a: int, b: int) -> list[int]:
        ys = [y for y in range(len(band)) if any(band[y][c] for c in range(a, b + 1))]
        return [a + x0, b + x0, ys[0] + top + y0, ys[-1] + top + y0]

    out.update(
        ok=True,
        rows=[g_top, g_bottom],
        words=[[a + x0, b + x0] for a, b in triple],
        glyphs=[[glyph_box(a, b) for a, b in word] for word in words],
        target_word=[triple[target][0] + x0, triple[target][1] + x0],
    )
    out["target"] = targets(out, entry)
    return out


def targets(seg: Mapping[str, Any], entry: str) -> dict[str, Any]:
    """q2's target format (canary_targets.json) from a segmentation."""
    left, right = seg["target_word"]
    y = (seg["rows"][0] + seg["rows"][1]) // 2
    if entry == "drag_select_word":
        return {"from": [left + 1, y], "to": [right - 1, y], "duration_ms": DRAG_DURATION_MS}
    return {"x": (left + right) // 2, "y": y}


def measure_png(data: bytes, app: str, entry: str) -> dict[str, Any]:
    try:
        _, _, rows = read_luminance(data, ROI[app])
    except PngError as exc:
        return {"ok": False, "error": str(exc)}
    out = segment(rows, app, entry)
    out["sha256"] = hashlib.sha256(data).hexdigest()
    return out


# --------------------------------------------------------------------------- the reference

# This rule applied to q2's own measurement screenshots: development run 515 on the certified disk
# S (2026-10-07), which canary_targets.json cites for its targets ("run 515 (these targets): ...
# both composites passed"). The screenshots stay on the host; their SHA-256 are pinned here, and
# their ``ROI`` regions are committed as test fixtures (tests/fixtures/s2v5_step0/), from which
# tests/test_s2v5_canary_targets.py re-derives every value. Chrome's and VS Code's step-0 targets
# are compared with these (q2's frozen Chrome drag end, 228, is the accessibility character cell's
# edge, 3 px beyond the ink of "d" at 24 px, so the frozen number is not reachable by an ink rule;
# the record, section "The Chrome reference", gives the comparison).
REFERENCE_RUN = 515
REFERENCE: dict[tuple[str, str], dict[str, Any]] = {
    ("writer", "triple_click_line"): {
        "screenshot": "canary-040-writer-triple_click_line.png",
        "sha256": "eeb061cf5aa1dfcb6d4c3b67be40fe258c4fa42f5f531c834209037059411905",
        "target_word": [704, 733],
        "rows": [288, 299],
        "target": {"x": 718, "y": 293},
    },
    ("writer", "drag_select_word"): {
        "screenshot": "canary-053-writer-drag_select_word.png",
        "sha256": "b7b66b8c912901b8322addc0e9de580049d25a72704316b1bedf21d9feeedbd2",
        "target_word": [679, 709],
        "rows": [288, 299],
        "target": {"from": [680, 293], "to": [708, 293], "duration_ms": 500},
    },
    ("chrome", "triple_click_line"): {
        "screenshot": "canary-020-chrome-triple_click_line.png",
        "sha256": "cca49959e27d1923832281f3f6548efd1bb2ef1e2268d96bdf3853a87ccbc095",
        "target_word": [216, 269],
        "rows": [140, 163],
        "target": {"x": 242, "y": 151},
    },
    ("chrome", "drag_select_word"): {
        "screenshot": "canary-014-chrome-drag_select_word.png",
        "sha256": "3bf9d63591f23bf4a0458cff0a9623e63ef90fa1ff8fff01a9d94ac63c8b4835",
        "target_word": [171, 226],
        "rows": [140, 163],
        "target": {"from": [172, 151], "to": [225, 151], "duration_ms": 500},
    },
    ("vscode", "triple_click_line"): {
        "screenshot": "canary-013-vscode-triple_click_line.png",
        "sha256": "9d5cf93985a94eac3923e1527eabd2f1f280a4787b1b9321272772267478def5",
        "target_word": [634, 665],
        "rows": [278, 291],
        "target": {"x": 649, "y": 284},
    },
    ("vscode", "drag_select_word"): {
        "screenshot": "canary-041-vscode-drag_select_word.png",
        "sha256": "d36664d5656922b0f34a508ae90c09dc5433cfcf44e8b860cbd2b8fbe45a75fe",
        "target_word": [608, 640],
        "rows": [278, 291],
        "target": {"from": [609, 284], "to": [639, 284], "duration_ms": 500},
    },
}


def _pairs(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[tuple[int, int]]:
    if "from" in a:
        return list(zip([*a["from"], *a["to"]], [*b["from"], *b["to"]], strict=True))
    return [(a["x"], b["x"]), (a["y"], b["y"])]


def max_offset(a: Mapping[str, Any], b: Mapping[str, Any]) -> int:
    """The largest coordinate difference between two targets of one entry (x and y)."""
    return max(abs(p - q) for p, q in _pairs(a, b))


def on_glyphs(target: Mapping[str, Any], seg: Mapping[str, Any]) -> bool:
    """Whether a (q2) target lies on the measured glyphs: the click inside the word's ink box and
    the glyph rows; the drag's two ends within ``UNDER_MARGIN_PX`` of the word's ink box."""
    (left, right), (top, bottom) = seg["target_word"], seg["rows"]
    if "from" in target:
        ends = [target["from"], target["to"]]
        return all(
            left - UNDER_MARGIN_PX <= x <= right + UNDER_MARGIN_PX and top <= y <= bottom
            for x, y in ends
        )
    return left <= target["x"] <= right and top <= target["y"] <= bottom


# --------------------------------------------------------------------------- step 0's job records


def collect(job_dir: Path) -> list[dict[str, Any]]:
    """Every pointer-composite trial of a step-0 job (``ap_delta_step0`` run directories), with
    this rule's measurement of its screenshot taken before the action. The AT-SPI extents q2's
    measure mode records are copied for disclosure (``atspi``); nothing reads them."""
    out = []
    for sub in sorted(Path(job_dir).iterdir()):
        meta = sub / "apdelta.json"
        if not meta.is_file():
            continue
        cells = json.loads(meta.read_text(encoding="utf-8"))["cells"]
        for path in sorted((sub / "cycles").glob("record-*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            boot = int(record["cycle"])
            for trial in ((record.get("runner_result") or {}).get("trials")) or []:
                app, entry = str(trial.get("cell", ":")).split(":", 1)
                if app not in APPS or entry not in ENTRIES:
                    continue
                name = f"canary-{int(trial['seq']):03d}-{app}-{entry}.png"
                shot = sub / "cycles" / f"shots-{boot:02d}" / name
                seg = (
                    measure_png(shot.read_bytes(), app, entry)
                    if shot.is_file()
                    else {"ok": False, "error": "no screenshot"}
                )
                out.append(
                    {
                        "cell": cells[0],
                        "boot": boot,
                        "app": app,
                        "entry": entry,
                        "seq": trial.get("seq"),
                        "screenshot": str(shot.relative_to(job_dir)),
                        "infra": trial.get("infra") or [],
                        "text": trial.get("text"),
                        "expect": trial.get("expect"),
                        "pass": trial.get("pass"),
                        "measurement": {k: v for k, v in seg.items() if k != "bands"},
                        "atspi": ((trial.get("measured") or {}).get("extents")),
                    }
                )
    return out


# --------------------------------------------------------------------------- admission tests


def _median(values: Sequence[int]) -> int:
    return sorted(values)[len(values) // 2]


def decide(
    observations: Sequence[Mapping[str, Any]], q2_targets: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Step 0's admission tests and stop rule (the record, sections "Admission tests" and "Stop
    rule"). ``q2_targets``: canary_targets.json's ``apps``. Only reading (a) proceeds."""
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for o in observations:
        groups.setdefault((o["cell"], o["app"], o["entry"]), []).append(o)
    missing, per = [], {}
    for key in [(c, a, e) for c in CELLS for a in APPS for e in ENTRIES]:
        rows = groups.get(key, [])
        good = [o for o in rows if not o["infra"] and (o["measurement"] or {}).get("ok")]
        boots = sorted({o["boot"] for o in good})
        if len(good) != BOOTS or len(boots) != BOOTS:
            missing.append(
                {
                    "cell": key[0],
                    "app": key[1],
                    "entry": key[2],
                    "measured": len(good),
                    "trials": len(rows),
                }
            )
        if not good:
            continue
        ms = [o["measurement"] for o in good]
        q = {
            "x0": [m["target_word"][0] for m in ms],
            "x1": [m["target_word"][1] for m in ms],
            "top": [m["rows"][0] for m in ms],
            "bottom": [m["rows"][1] for m in ms],
        }
        consensus = {
            "target_word": [_median(q["x0"]), _median(q["x1"])],
            "rows": [_median(q["top"]), _median(q["bottom"])],
        }
        consensus["target"] = targets(consensus, key[2])
        per[key] = {
            "boots": len(good),
            "consensus": consensus,
            "drift": {k: max(v) - min(v) for k, v in q.items()},
        }
    complete = not missing
    tests: dict[str, Any] = {"complete": {"pass": complete, "missing": missing}}
    drift = [
        {"cell": k[0], "app": k[1], "entry": k[2], **v["drift"]}
        for k, v in per.items()
        if max(v["drift"].values()) > DRIFT_MAX_PX
    ]
    tests["c_stable"] = {"pass": complete and not drift, "drift_over_1px": drift}

    def against(cells: Sequence[str], apps: Sequence[str], reference: str) -> dict[str, Any]:
        rows = []
        for c in cells:
            for a in apps:
                for e in ENTRIES:
                    if (c, a, e) not in per:
                        rows.append({"cell": c, "app": a, "entry": e, "offset": None})
                        continue
                    ref = q2_targets[a][e] if reference == "q2" else REFERENCE[(a, e)]["target"]
                    rows.append(
                        {
                            "cell": c,
                            "app": a,
                            "entry": e,
                            "offset": max_offset(per[(c, a, e)]["consensus"]["target"], ref),
                        }
                    )
        ok = complete and all(r["offset"] is not None and r["offset"] <= TOL_Q2_PX for r in rows)
        return {"pass": ok, "rows": rows}

    for cell in ("E", "A"):
        writer = against([cell], ["writer"], "q2")
        others = against([cell], ["chrome", "vscode"], "reference")
        tests[f"calibration_{cell}"] = {
            "pass": writer["pass"] and others["pass"],
            "writer_vs_q2": writer["rows"],
            "chrome_vscode_vs_reference": others["rows"],
        }
    tests["prediction_PL_writer"] = against(["PL"], ["writer"], "q2")
    tests["prediction_chrome_vscode"] = against(
        ["ER", "AR", "PL"], ["chrome", "vscode"], "reference"
    )
    shifts = []
    for c in MIRRORED:
        for e in ENTRIES:
            if (c, "writer", e) not in per or ("E", "writer", e) not in per:
                shifts.append({"cell": c, "entry": e, "dx": None, "dy": None})
                continue
            m, ref = per[(c, "writer", e)]["consensus"], per[("E", "writer", e)]["consensus"]
            shifts.append(
                {
                    "cell": c,
                    "entry": e,
                    "dx": [m["target_word"][i] - ref["target_word"][i] for i in (0, 1)],
                    "dy": [m["rows"][i] - ref["rows"][i] for i in (0, 1)],
                }
            )
    tests["prediction_shift"] = {
        "pass": complete
        and all(
            s["dx"] is not None
            and all(SHIFT_DX[0] <= d <= SHIFT_DX[1] for d in s["dx"])
            and all(d in SHIFT_DY for d in s["dy"])
            for s in shifts
        ),
        "rows": shifts,
    }
    readback = [
        {"cell": c, "boot": o["boot"], "text": o["text"]}
        for c in MIRRORED
        for o in groups.get((c, "writer", "drag_select_word"), [])
    ]
    tests["prediction_v4_readback"] = {
        "pass": complete
        and len(readback) == BOOTS * len(MIRRORED)
        and all(r["text"] == V4_FAILURE_READBACK for r in readback),
        "rows": readback,
    }
    b_rows = [
        {
            "cell": o["cell"],
            "app": o["app"],
            "entry": o["entry"],
            "boot": o["boot"],
            "text": o["text"],
        }
        for o in observations
        if not o["infra"]
        and (o["measurement"] or {}).get("ok")
        and o["pass"] is not True
        and on_glyphs(q2_targets[o["app"]][o["entry"]], o["measurement"])
    ]
    tests["b_pointer"] = {"pass": not b_rows, "glyphs_under_q2_target_without_selection": b_rows}
    labels = []
    if not complete:
        labels.append("incomplete")
    if drift:
        labels.append("(c) boot-to-boot drift above 1 px")
    if b_rows:
        labels.append("(b) glyphs under the v4 target yet no selection")
    for cell in ("E", "A"):
        if not tests[f"calibration_{cell}"]["pass"]:
            labels.append(f"failed calibration on {cell}")
    for name in (
        "prediction_PL_writer",
        "prediction_chrome_vscode",
        "prediction_shift",
        "prediction_v4_readback",
    ):
        if not tests[name]["pass"]:
            labels.append(f"{name} missed")
    proceed = not labels and all(t["pass"] for t in tests.values())
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "reading": "(a)" if proceed else "not (a)",
        "decision": "PROCEED to the v5 draft (D94)" if proceed else "HONEST EXIT for S2 (D94)",
        "exit_labels": labels,
        "tests": tests,
        "per_image": {f"{c}/{a}/{e}": v for (c, a, e), v in sorted(per.items())},
    }
    if proceed:
        # What (a) hands to v5: q2's targets wherever they hold, the measured ones on Writer in
        # ER and AR (the only (image, app) pairs whose fixture moved).
        out["v5_targets"] = {
            c: {
                a: {
                    e: (
                        per[(c, a, e)]["consensus"]["target"]
                        if a == "writer" and c in MIRRORED
                        else q2_targets[a][e]
                    )
                    for e in ENTRIES
                }
                for a in APPS
            }
            for c in CELLS
        }
    out["disclosure"] = {
        "atspi_extents": [
            {
                "cell": o["cell"],
                "app": o["app"],
                "entry": o["entry"],
                "boot": o["boot"],
                "target": (o.get("atspi") or {}).get("target"),
            }
            for o in observations
            if o.get("atspi")
        ],
        "chrome_vscode_vs_q2_frozen": [
            {
                "cell": c,
                "app": a,
                "entry": e,
                "offset": max_offset(per[(c, a, e)]["consensus"]["target"], q2_targets[a][e]),
            }
            for c in CELLS
            for a in ("chrome", "vscode")
            for e in ENTRIES
            if (c, a, e) in per
        ],
    }
    return out


# --------------------------------------------------------------------------- CLI

RULE_PIN = "experiments/manifests/s2v5/step0-rule.json"
Q2_TARGETS = "harness/q2/action_path/canary_targets.json"


def check_pins(source_dir: Path) -> dict[str, str]:
    """Every file ``step0-rule.json`` pins is byte-identical in ``source_dir`` (raises)."""
    pin = json.loads((source_dir / RULE_PIN).read_text(encoding="utf-8"))
    actual = {}
    for path, sha in sorted(pin["files"].items()):
        actual[path] = hashlib.sha256((source_dir / path).read_bytes()).hexdigest()
        if actual[path] != sha:
            raise SystemExit(f"{path} is not the file step0-rule.json pins")
    return actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure", help="one screenshot")
    m.add_argument("png", type=Path)
    m.add_argument("--app", choices=APPS, required=True)
    m.add_argument("--entry", choices=ENTRIES, required=True)
    a = sub.add_parser("analyze", help="step 0's verdict from its job directory")
    a.add_argument("job_dir", type=Path)
    a.add_argument("--source-dir", type=Path, default=Path("."))
    a.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "measure":
        print(json.dumps(measure_png(args.png.read_bytes(), args.app, args.entry), sort_keys=True))
        return 0
    pins = check_pins(args.source_dir)
    q2 = json.loads((args.source_dir / Q2_TARGETS).read_text(encoding="utf-8"))["apps"]
    observations = collect(args.job_dir)
    out = decide(observations, q2)
    out["rule_files"] = pins
    out["observations"] = observations
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "reading": out["reading"],
                "decision": out["decision"],
                "exit_labels": out["exit_labels"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
