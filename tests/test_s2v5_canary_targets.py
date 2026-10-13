"""S2 v5 step 0 (D94): the screenshot-only target rule, its admission tests and its pins.

Synthetic glyph images test the segmentation; the committed regions of q2's own measurement
screenshots (development runs 515 and 501 on the certified disk) re-derive the reference.
"""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

import pytest

from harness.s2_locale import canary_targets_v5 as R

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/s2v5_step0"
Q2 = json.loads((ROOT / R.Q2_TARGETS).read_text())["apps"]
RECORD = ROOT / "program/preregistrations/s2-arabic-cua-locale-v5-step0.md"

# --------------------------------------------------------------------------- PNG reader


def _png(width, height, channels, rows, filters):
    """An 8-bit PNG with the given per-row filter types (filtered here, decoded by the module)."""
    color = {1: 0, 3: 2, 4: 6}[channels]
    stride = width * channels
    raw, prev = b"", bytes(stride)
    for row, ftype in zip(rows, filters, strict=True):
        line = bytes(row)
        out = bytearray()
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            up = prev[i]
            upleft = prev[i - channels] if i >= channels else 0
            pred = [0, left, up, (left + up) >> 1, R._paeth(left, up, upleft)][ftype]
            out.append((line[i] - pred) & 0xFF)
        raw += bytes([ftype]) + bytes(out)
        prev = line

    def chunk(kind, body):
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))  # fmt: skip


def test_png_reader_every_filter_and_box():
    width, height = 7, 5
    rgb = [[(17 * x + 31 * y + c * 50) % 256 for x in range(width) for c in range(3)]
           for y in range(height)]  # fmt: skip
    data = _png(width, height, 3, rgb, [0, 1, 2, 3, 4])
    w, h, rows = R.read_luminance(data)
    assert (w, h) == (width, height)
    for y in range(height):
        for x in range(width):
            r, g, b = rgb[y][3 * x : 3 * x + 3]
            assert rows[y][x] == (299 * r + 587 * g + 114 * b + 500) // 1000
    _, _, part = R.read_luminance(data, (2, 1, 5, 3))
    assert part == [row[2:5] for row in rows[1:3]]
    rgba = [[v for x in range(width) for v in (*rgb[y][3 * x : 3 * x + 3], 255)]
            for y in range(height)]  # fmt: skip
    assert R.read_luminance(_png(width, height, 4, rgba, [4, 3, 2, 1, 0]))[2] == rows
    gray = [[(x * y) % 256 for x in range(width)] for y in range(height)]
    assert R.read_luminance(R.write_png_gray(gray))[2] == gray


def test_png_reader_refusals():
    with pytest.raises(R.PngError, match="not a PNG"):
        R.read_luminance(b"GIF89a")
    data = R.write_png_gray([[0, 1], [2, 3]])
    with pytest.raises(R.PngError, match="outside"):
        R.read_luminance(data, (0, 0, 3, 1))
    assert R.measure_png(b"nope", "writer", "drag_select_word")["ok"] is False


def test_png_reader_matches_pillow_on_the_committed_regions():
    Image = pytest.importorskip("PIL.Image")
    for path in sorted(FIXTURES.glob("*.png")):
        im = Image.open(path).convert("RGB")
        _, _, rows = R.read_luminance(path.read_bytes())
        px = im.load()
        for y in (0, im.size[1] // 2, im.size[1] - 1):
            for x in range(0, im.size[0], 7):
                r, g, b = px[x, y]
                assert rows[y][x] == (299 * r + 587 * g + 114 * b + 500) // 1000


# --------------------------------------------------------------------------- synthetic glyphs

ASCENDERS, DESCENDERS = set("kdlthi"), set("p")
SYNTH = {  # app: (line start x, glyph-row top y, glyph width, background, ink)
    "writer": (640, 288, 6, 255, 20),
    "chrome": (102, 140, 11, 255, 0),
    "vscode": (568, 278, 6, 31, 204),
}


def synth(app, entry, dx=0, dy=0, caret=None, extra=()):
    """The ROI of a synthetic screenshot: the fixture line as solid glyph boxes at the app's pitch
    (ascenders to the top row, descenders 3 rows below the baseline), plus optional marks."""
    x0, y0, x1, y1 = R.ROI[app]
    start, top, gw, bg, ink = SYNTH[app]
    rows = [[bg] * (x1 - x0) for _ in range(y1 - y0)]

    def put(x, y, v=ink):
        if x0 <= x < x1 and y0 <= y < y1:
            rows[y - y0][x - x0] = v

    pitch = R.PITCH_PX[app]
    text = R.FIXTURES[entry][0]
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        cx = start + dx + round(i * pitch) + 1
        y_top = top + dy if ch in ASCENDERS else top + dy + 3
        y_bottom = top + dy + 11 if ch in DESCENDERS else top + dy + 8
        for x in range(cx, cx + gw):
            for y in range(y_top, y_bottom + 1):
                put(x, y)
    if caret is not None:
        cx, c_top, c_bottom = caret
        for x in (cx, cx + 1):
            for y in range(c_top, c_bottom + 1):
                put(x, y)
    for x, y, v in extra:
        put(x, y, v)
    return rows


def expected(app, entry, dx=0, dy=0):
    start, top, gw, _, _ = SYNTH[app]
    pitch = R.PITCH_PX[app]
    first, last = (5, 8) if entry == "drag_select_word" else (8, 11)
    left = start + dx + round(first * pitch) + 1
    right = start + dx + round(last * pitch) + 1 + gw - 1
    y = (top + dy + top + dy + 11) // 2
    if entry == "drag_select_word":
        return {"from": [left + 1, y], "to": [right - 1, y], "duration_ms": 500}
    return {"x": (left + right) // 2, "y": y}


@pytest.mark.parametrize("app", R.APPS)
@pytest.mark.parametrize("entry", R.ENTRIES)
def test_synthetic_line_gives_the_rule_targets(app, entry):
    out = R.segment(synth(app, entry), app, entry)
    assert out["ok"], out
    assert out["target"] == expected(app, entry)
    assert len(out["words"]) == 3 and len(out["glyphs"][1]) == 4  # 'word' / 'this': 4 glyphs
    assert out["rows"] == [SYNTH[app][1], SYNTH[app][1] + 11]


@pytest.mark.parametrize("app", R.APPS)
def test_a_shifted_line_shifts_the_targets_by_the_same_amount(app):
    for dx, dy in ((71, 0), (71, 1), (0, 1), (-2, -3), (140, 2)):
        for entry in R.ENTRIES:
            out = R.segment(synth(app, entry, dx, dy), app, entry)
            assert out["ok"] and out["target"] == expected(app, entry, dx, dy)


@pytest.mark.parametrize("app", R.APPS)
def test_the_caret_is_removed_wherever_it_blinks(app):
    start, top, gw, _, _ = SYNTH[app]
    for entry in R.ENTRIES:
        n = len(R.FIXTURES[entry][0])
        end = start + round((n - 1) * R.PITCH_PX[app]) + 1 + gw
        for caret in ((start - 1, top - 3, top + 14), (end + 1, top - 3, top + 14),
                      (start - 2, top, top + 11)):  # fmt: skip
            out = R.segment(synth(app, entry, caret=caret), app, entry)
            assert out["ok"], (caret, out)
            assert out["target"] == expected(app, entry)
            assert out["rows"] == [top, top + 11]


def test_long_lines_and_faint_marks_are_ignored():
    app, entry = "writer", "drag_select_word"
    x0, y0, x1, y1 = R.ROI[app]
    border = [(632, y, 155) for y in range(y0, y1)]  # ER's page border (luminance 155)
    marks = [(x, 285, 221) for x in range(696, 711)] + [(710, y, 211) for y in range(273, 286)]
    out = R.segment(synth(app, entry, dx=71, extra=border + marks), app, entry)
    assert out["ok"] and out["line_columns_removed"] == 1
    assert out["target"] == expected(app, entry, dx=71)


def test_no_line_or_two_lines_is_a_failed_measurement():
    app, entry = "writer", "drag_select_word"
    x0, y0, x1, y1 = R.ROI[app]
    blank = [[255] * (x1 - x0) for _ in range(y1 - y0)]
    assert R.segment(blank, app, entry)["ok"] is False
    one = synth(app, entry)
    two = synth(app, entry, dy=40)
    both = [
        [min(a, b) for a, b in zip(r1, r2, strict=True)] for r1, r2 in zip(one, two, strict=True)
    ]
    out = R.segment(both, app, entry)
    assert out["ok"] is False and "2 fixture lines" in out["error"]
    # the other fixture's line is not this entry's
    assert R.segment(synth(app, "triple_click_line"), app, entry)["ok"] is False
    assert R.segment(blank[:-1], app, entry)["ok"] is False  # wrong region size


# --------------------------------------------------------------------------- q2's screenshots


def _region(name):
    return R.read_luminance((FIXTURES / name).read_bytes())[2]


@pytest.mark.parametrize("key", sorted(R.REFERENCE))
def test_reference_is_this_rule_on_q2s_run_515_screenshots(key):
    app, entry = key
    out = R.segment(_region(f"run515-{app}-{entry}.png"), app, entry)
    ref = R.REFERENCE[key]
    assert out["ok"]
    assert out["target_word"] == ref["target_word"] and out["rows"] == ref["rows"]
    assert out["target"] == ref["target"]
    assert ref["screenshot"].endswith(f"{app}-{entry}.png") and len(ref["sha256"]) == 64


@pytest.mark.parametrize("delta", [48, 64, 80, 96])
def test_the_reference_does_not_depend_on_the_ink_threshold_near_80(delta, monkeypatch):
    monkeypatch.setattr(R, "INK_DELTA", delta)
    for (app, entry), ref in R.REFERENCE.items():
        out = R.segment(_region(f"run515-{app}-{entry}.png"), app, entry)
        assert out["target"] == ref["target"], (delta, app, entry)


def test_run_501_boots_agree_with_run_515_and_a_blank_window_is_not_measured():
    """Another boot of the certified disk: same glyph boxes (Chrome's caret visible in one, not
    in the other); VS Code's window was not drawn yet in run 501 (no fixture line)."""
    for app, entry in (("writer", "drag_select_word"), ("chrome", "triple_click_line")):
        out = R.segment(_region(f"run501-{app}-{entry}.png"), app, entry)
        ref = R.REFERENCE[(app, entry)]
        assert out["target_word"] == ref["target_word"] and out["rows"] == ref["rows"]
    out = R.segment(_region("run515-chrome-triple_click_line.png"), "chrome", "triple_click_line")
    assert any(b["caret_columns"] for b in out["bands"])  # the caret was there, and removed
    assert R.segment(_region("run501-vscode-drag_select_word.png"), "vscode",
                     "drag_select_word")["ok"] is False  # fmt: skip


def test_real_regions_with_and_without_a_caret():
    rows = _region("run515-writer-drag_select_word.png")
    x0, y0, _, _ = R.ROI["writer"]
    for x in (638, 639):  # a Writer caret at the line start, taller than the glyphs
        for y in range(285, 303):
            rows[y - y0][x - x0] = 0
    out = R.segment(rows, "writer", "drag_select_word")
    assert out["target"] == R.REFERENCE[("writer", "drag_select_word")]["target"]
    rows = _region("run515-vscode-drag_select_word.png")
    x0, y0, _, _ = R.ROI["vscode"]
    for x in (566, 567):  # VS Code's cursor erased
        for y in range(272, 300):
            rows[y - y0][x - x0] = 31
    out = R.segment(rows, "vscode", "drag_select_word")
    assert out["target"] == R.REFERENCE[("vscode", "drag_select_word")]["target"]


def test_reference_against_q2s_frozen_targets_is_as_the_record_states():
    """Writer and VS Code reproduce q2's frozen numbers within 1 px; Chrome's drag end is 3 px
    short (q2's 228 is the accessibility cell's edge) and its click 2 px: hence the reference."""
    offsets = {k: R.max_offset(v["target"], Q2[k[0]][k[1]]) for k, v in R.REFERENCE.items()}
    assert offsets == {
        ("writer", "triple_click_line"): 1,
        ("writer", "drag_select_word"): 1,
        ("chrome", "triple_click_line"): 2,
        ("chrome", "drag_select_word"): 3,
        ("vscode", "triple_click_line"): 1,
        ("vscode", "drag_select_word"): 1,
    }


# --------------------------------------------------------------------------- admission tests

SHIFT = {"E": (0, 0), "A": (0, 1), "ER": (71, 0), "AR": (71, 1), "PL": (0, 0)}


def world(shift=None, readback=None, skip=(), tweak=None):
    """Observations of the predicted step 0: Writer's fixture at SHIFT, Chrome and VS Code at the
    reference, the v4 drag failing on ER and AR as job 1264 read back, everything else passing."""
    shift = shift or SHIFT
    out = []
    for cell in R.CELLS:
        for app in R.APPS:
            for entry in R.ENTRIES:
                ref = R.REFERENCE[(app, entry)]
                dx, dy = shift[cell] if app == "writer" else (0, 0)
                for boot in range(R.BOOTS):
                    if (cell, app, entry, boot) in skip:
                        continue
                    m = {"ok": True, "target_word": [ref["target_word"][0] + dx,
                                                     ref["target_word"][1] + dx],
                         "rows": [ref["rows"][0] + dy, ref["rows"][1] + dy]}  # fmt: skip
                    expect = "keep Y keep" if entry == "drag_select_word" else "X"
                    text = expect
                    if app == "writer" and entry == "drag_select_word" and dx:
                        text = R.V4_FAILURE_READBACK
                    if readback and (cell, app, entry) in readback:
                        text = readback[(cell, app, entry)]
                    o = {
                        "cell": cell,
                        "boot": boot,
                        "app": app,
                        "entry": entry,
                        "infra": [],
                        "text": text,
                        "expect": expect,
                        "pass": text == expect,
                        "measurement": m,
                        "atspi": {"ok": True, "target": dict(Q2[app][entry])},
                    }
                    if tweak:
                        tweak(o)
                    out.append(o)
    return out


def test_the_predicted_world_is_reading_a_and_hands_v5_the_shifted_writer_targets():
    out = R.decide(world(), Q2)
    assert out["reading"] == "(a)" and not out["exit_labels"], out["exit_labels"]
    t = out["v5_targets"]
    assert t["ER"]["writer"]["drag_select_word"] == {"from": [751, 293], "to": [779, 293],
                                                     "duration_ms": 500}  # fmt: skip
    assert t["AR"]["writer"]["triple_click_line"] == {"x": 789, "y": 294}
    for cell in ("E", "A", "PL"):
        assert t[cell]["writer"] == Q2["writer"]
    for cell in R.CELLS:
        assert t[cell]["chrome"] == Q2["chrome"] and t[cell]["vscode"] == Q2["vscode"]
    rows = out["tests"]["calibration_A"]["writer_vs_q2"]
    assert max(r["offset"] for r in rows) == 2  # A's y: 294 against q2's 292, at the limit


def test_atspi_extents_have_no_role():
    def wild(o):
        o["atspi"] = {"ok": True, "target": {"x": 1, "y": 1}, "boxes": [[0, 0, 1, 1]]}

    a, b = R.decide(world(), Q2), R.decide(world(tweak=wild), Q2)
    assert a["reading"] == b["reading"] and a["tests"] == b["tests"]


def test_drift_above_one_pixel_is_reading_c():
    def drift(o):
        if (o["cell"], o["app"], o["boot"]) == ("AR", "chrome", 3):
            o["measurement"]["target_word"] = [x + 2 for x in o["measurement"]["target_word"]]

    out = R.decide(world(tweak=drift), Q2)
    assert out["reading"] == "not (a)"
    assert "(c) boot-to-boot drift above 1 px" in out["exit_labels"]

    def one(o):
        if (o["cell"], o["app"], o["boot"]) == ("AR", "chrome", 3):
            o["measurement"]["rows"] = [r + 1 for r in o["measurement"]["rows"]]

    assert R.decide(world(tweak=one), Q2)["reading"] == "(a)"  # 1 px is within


def test_glyphs_under_the_v4_target_without_selection_is_reading_b():
    shift = dict(SHIFT, ER=(0, 0))  # ER's fixture where q2 measured it, and the drag still fails
    out = R.decide(world(shift=shift, readback={("ER", "writer", "drag_select_word"):
                                                R.V4_FAILURE_READBACK}), Q2)  # fmt: skip
    assert "(b) glyphs under the v4 target yet no selection" in out["exit_labels"]
    assert "prediction_shift missed" in out["exit_labels"]
    out = R.decide(world(readback={("E", "chrome", "drag_select_word"): "keep word keepY"}), Q2)
    assert out["exit_labels"] == ["(b) glyphs under the v4 target yet no selection"]


def test_calibration_and_predictions_fail_as_registered():
    out = R.decide(world(shift=dict(SHIFT, A=(0, 2))), Q2)  # A's Writer y 295: 3 px from 292
    assert "failed calibration on A" in out["exit_labels"]
    out = R.decide(world(shift=dict(SHIFT, E=(3, 0), PL=(3, 0))), Q2)
    assert "failed calibration on E" in out["exit_labels"]
    out = R.decide(world(shift=dict(SHIFT, ER=(60, 0))), Q2)
    assert out["exit_labels"] == ["prediction_shift missed"]
    out = R.decide(world(shift=dict(SHIFT, AR=(71, 2))), Q2)
    assert "prediction_shift missed" in out["exit_labels"]
    out = R.decide(world(shift=dict(SHIFT, PL=(0, 3))), Q2)
    assert out["exit_labels"] == ["prediction_PL_writer missed"]
    out = R.decide(world(readback={("AR", "writer", "drag_select_word"): "keep Y keep"}), Q2)
    assert out["exit_labels"] == ["prediction_v4_readback missed"]

    def chrome_moved(o):
        if o["cell"] == "ER" and o["app"] == "chrome":
            o["measurement"]["target_word"] = [x + 3 for x in o["measurement"]["target_word"]]

    assert R.decide(world(tweak=chrome_moved), Q2)["exit_labels"] == [
        "prediction_chrome_vscode missed"
    ]


def test_an_incomplete_step_0_is_not_reading_a():
    out = R.decide(world(skip={("PL", "vscode", "triple_click_line", 4)}), Q2)
    assert out["reading"] == "not (a)" and out["exit_labels"][0] == "incomplete"

    def infra(o):
        if (o["cell"], o["app"], o["entry"], o["boot"]) == ("E", "writer", "drag_select_word", 0):
            o["infra"] = ["readback"]

    assert "incomplete" in R.decide(world(tweak=infra), Q2)["exit_labels"]

    def unmeasured(o):
        if (o["cell"], o["boot"]) == ("A", 2) and o["app"] == "chrome":
            o["measurement"] = {"ok": False, "error": "0 fixture lines found"}

    assert "incomplete" in R.decide(world(tweak=unmeasured), Q2)["exit_labels"]


def test_collect_reads_an_ap_delta_step0_job(tmp_path):
    sub = tmp_path / "00-s2v5-step0-er"
    (sub / "cycles" / "shots-00").mkdir(parents=True)
    (sub / "apdelta.json").write_text(json.dumps({"check": "step0", "cells": ["ER"]}))
    src = (FIXTURES / "run515-writer-drag_select_word.png").read_bytes()
    _, _, rows = R.read_luminance(src)
    x0, y0, x1, y1 = R.ROI["writer"]
    full = [[255] * 1920 for _ in range(y1)]
    for y, row in enumerate(rows):
        full[y0 + y][x0:x1] = row
    (sub / "cycles" / "shots-00" / "canary-003-writer-drag_select_word.png").write_bytes(
        R.write_png_gray(full)
    )
    trial = {
        "seq": 3,
        "cell": "writer:drag_select_word",
        "infra": [],
        "pass": False,
        "text": "Ykeep word keep",
        "expect": "keep Y keep",
        "measured": {"extents": {"ok": True, "target": Q2["writer"]["drag_select_word"]}},
    }
    other = {"seq": 4, "cell": "terminal:type_plain"}
    (sub / "cycles" / "record-00.json").write_text(
        json.dumps({"cycle": 0, "runner_result": {"trials": [trial, other]}})
    )
    (obs,) = R.collect(tmp_path)
    assert obs["cell"] == "ER" and obs["boot"] == 0 and obs["text"] == "Ykeep word keep"
    assert obs["measurement"]["target"] == R.REFERENCE[("writer", "drag_select_word")]["target"]
    assert obs["atspi"]["target"] == Q2["writer"]["drag_select_word"]


# --------------------------------------------------------------------------- pins and record


def test_step0_rule_json_pins_the_tree():
    pin = json.loads((ROOT / R.RULE_PIN).read_text())
    assert (
        pin["schema"] == "s2v5-step0-rule-v1" and pin["experiment_id"] == "s2-arabic-cua-locale-v5"
    )
    for path, sha in pin["files"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    must = {"harness/s2_locale/canary_targets_v5.py", "harness/s2_locale/ap_delta_step0.py",
            "tests/test_s2v5_canary_targets.py", "tests/test_s2v5_step0.py",
            "infra/slurm/host-single-node/s2v5-step0.sbatch",
            "program/preregistrations/s2-arabic-cua-locale-v5-step0.md"}  # fmt: skip
    must |= {str(p.relative_to(ROOT)) for p in FIXTURES.glob("*.png")}
    assert must <= set(pin["files"])
    assert R.check_pins(ROOT) == pin["files"]


def test_record_states_the_rule_and_its_numbers():
    text = RECORD.read_text()
    assert text.startswith("# S2 v5 step 0")
    for needle in ("left edge of `w` plus 1 px", "right edge of `d` minus 1 px",
                   "middle of `this`", "centre of the glyph rows", "+71 ± 2", "0 or +1",
                   "within 2 px", "above 1 px", "no second measurement", "no coordinate search",
                   "AT-SPI", "not a ledger registration", f"INK_DELTA = {R.INK_DELTA}",
                   "(751, 293)", "(779, 293)", "(789, 293)", "(751, 294)", "(789, 294)",
                   "(225, 151)", "(242, 151)", "(639, 284)", "(649, 284)"):  # fmt: skip
        assert needle in text, needle
    for app, (x0, y0, x1, y1) in R.ROI.items():
        assert f"[{x0}, {y0}, {x1}, {y1})" in text, app
