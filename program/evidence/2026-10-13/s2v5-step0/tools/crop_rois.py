"""Crop the rule's fixed region (canary_targets_v5.ROI) out of every step-0 screenshot, RGB.

Standard library only (runs on the host). Reads the pinned rule module from the export for ROI and
the PNG unfilter; changes nothing in it. For every kept screenshot ``<job>/<NN-cid>/cycles/
shots-BB/canary-SSS-<app|after>-<entry>.png`` it writes ``<out>/<cell>/boot-BB/<name>`` holding
the screen region ``ROI[app]`` (for an ``after`` screenshot, the ROI of the trial's app), and
checks that the rule's luminance of the crop equals its luminance of the region in the full
screenshot. Prints one JSON summary line.

Usage: python3 -B crop_rois.py SOURCE_DIR JOB_DIR OUT_DIR
"""

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

source, job, out = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(source))
from harness.s2_locale import canary_targets_v5 as R  # noqa: E402


def decode_rgb(data, y1):
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
    width, height, depth, color, _, _, interlace = header
    channels = {0: 1, 2: 3, 6: 4}[color]
    assert depth == 8 and interlace == 0
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    rows, prev = [], bytes(stride)
    for y in range(y1):
        off = y * (stride + 1)
        line = R._unfilter(raw[off], raw[off + 1 : off + 1 + stride], prev, channels)
        rows.append(bytes(line))
        prev = bytes(line)
    return width, height, channels, rows


def write_rgb(rows_rgb, width):
    raw = b"".join(b"\x00" + r for r in rows_rgb)

    def chunk(kind, body):
        crc = struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
        return struct.pack(">I", len(body)) + kind + body + crc

    ihdr = struct.pack(">IIBBBBB", width, len(rows_rgb), 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


summary = {"crops": 0, "luminance_equal": 0, "mismatch": [], "skipped": []}
index = []
for sub in sorted(p for p in job.iterdir() if (p / "apdelta.json").is_file()):
    cell = json.loads((sub / "apdelta.json").read_text())["cells"][0]
    for shots in sorted((sub / "cycles").glob("shots-*")):
        boot = shots.name.split("-")[1]
        for shot in sorted(shots.glob("canary-*.png")):
            parts = shot.stem.split("-", 3)  # canary, seq, app|after, entry
            kind, entry = parts[2], parts[3]
            app = kind
            if kind == "after":
                # the trial's app, from the matching before-screenshot of the same seq
                twins = [p for p in shots.glob(f"canary-{parts[1]}-*-{entry}.png") if p != shot]
                if len(twins) != 1:
                    summary["skipped"].append(str(shot.relative_to(job)))
                    continue
                app = twins[0].stem.split("-", 3)[2]
            if app not in R.ROI:
                summary["skipped"].append(str(shot.relative_to(job)))
                continue
            x0, y0, x1, y1 = R.ROI[app]
            data = shot.read_bytes()
            width, height, ch, rows = decode_rgb(data, y1)
            crop = []
            for y in range(y0, y1):
                line = rows[y]
                if ch == 3:
                    crop.append(line[x0 * 3 : x1 * 3])
                else:
                    seg = bytearray()
                    for x in range(x0, x1):
                        seg += line[x * ch : x * ch + 3] if ch == 4 else bytes([line[x]] * 3)
                    crop.append(bytes(seg))
            png = write_rgb(crop, x1 - x0)
            dest = out / cell / f"boot-{boot}" / (shot.stem + f"-roi-{app}.png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(png)
            same = R.read_luminance(png)[2] == R.read_luminance(data, R.ROI[app])[2]
            summary["crops"] += 1
            summary["luminance_equal"] += int(same)
            if not same:
                summary["mismatch"].append(str(dest.relative_to(out)))
            index.append({
                "cell": cell, "boot": int(boot), "screenshot": str(shot.relative_to(job)),
                "screenshot_sha256": hashlib.sha256(data).hexdigest(),
                "screen": [width, height], "roi_app": app, "roi": list(R.ROI[app]),
                "crop": str(dest.relative_to(out)), "crop_sha256": hashlib.sha256(png).hexdigest(),
                "luminance_equal": same,
            })
(out / "crops-index.json").write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in summary.items()}))
