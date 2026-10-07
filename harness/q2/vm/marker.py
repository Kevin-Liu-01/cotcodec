"""Decode the probe's marker block from a guest screenshot (standard library only).

The probe (``guest/probe.py``) draws its marker in the top rows of the screen.
A screenshot is a PNG; this module decompresses only the first
``probe.MARKER_ROWS`` rows (zlib with a length limit), reverses the PNG row
filters for them, samples each marker cell on a 3 x 3 grid and decodes the
cells with ``probe.parse_marker_bits``. A cell whose nine samples disagree
(for example under the cursor image the guest server pastes into
screenshots) makes the marker unreadable, never silently wrong.

Supported PNGs: 8-bit RGB or RGBA, not interlaced (what the OSWorld guest's
``/screenshot`` returns); anything else raises ``MarkerError``.
"""

from __future__ import annotations

import struct
import zlib
from typing import Any

from harness.q2.vm.guest import probe

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SAMPLE_OFFSETS = (4, 8, 11)


class MarkerError(ValueError):
    """The screenshot is not a PNG this decoder supports."""


def _chunks(data: bytes):
    if data[:8] != PNG_MAGIC:
        raise MarkerError("not a PNG")
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        body = data[offset + 8 : offset + 8 + length]
        yield kind, body
        offset += 12 + length
        if kind == b"IEND":
            return


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def unfilter_row(kind: int, row: bytearray, prior: bytearray, bpp: int) -> bytearray:
    """Reverse one PNG scanline filter in place (types 0-4)."""
    n = len(row)
    if kind == 0:
        return row
    if kind == 1:
        for i in range(bpp, n):
            row[i] = (row[i] + row[i - bpp]) & 0xFF
    elif kind == 2:
        for i in range(n):
            row[i] = (row[i] + prior[i]) & 0xFF
    elif kind == 3:
        for i in range(n):
            left = row[i - bpp] if i >= bpp else 0
            row[i] = (row[i] + ((left + prior[i]) >> 1)) & 0xFF
    elif kind == 4:
        for i in range(n):
            left = row[i - bpp] if i >= bpp else 0
            upleft = prior[i - bpp] if i >= bpp else 0
            row[i] = (row[i] + _paeth(left, prior[i], upleft)) & 0xFF
    else:
        raise MarkerError(f"unknown PNG filter type {kind}")
    return row


def decode_rows(data: bytes, rows: int) -> tuple[int, int, int, list[bytearray]]:
    """(width, height, bytes per pixel, the first ``rows`` reconstructed scanlines)."""
    header = None
    idat = bytearray()
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    if header is None:
        raise MarkerError("PNG has no IHDR")
    width, height, depth, color, _, _, interlace = header
    if depth != 8 or color not in (2, 6) or interlace != 0:
        raise MarkerError(
            f"unsupported PNG (depth {depth}, color type {color}, interlace {interlace})"
        )
    bpp = 3 if color == 2 else 4
    stride = width * bpp + 1
    rows = min(rows, height)
    needed = rows * stride
    inflater = zlib.decompressobj()
    raw = inflater.decompress(bytes(idat), needed)
    while len(raw) < needed and inflater.unconsumed_tail:
        raw += inflater.decompress(inflater.unconsumed_tail, needed - len(raw))
    if len(raw) < needed:
        raise MarkerError("PNG data ends before the marker rows")
    out: list[bytearray] = []
    prior = bytearray(width * bpp)
    for index in range(rows):
        start = index * stride
        row = bytearray(raw[start + 1 : start + stride])
        prior = unfilter_row(raw[start], row, prior, bpp)
        out.append(prior)
    return width, height, bpp, out


def read_marker(data: bytes) -> dict[str, Any]:
    """Decode the marker: {"ok", "seq", "crc", "ambiguous_cells", "size"}."""
    width, height, bpp, rows = decode_rows(data, probe.MARKER_ROWS)
    x0, y0 = probe.MARKER_ORIGIN
    bits: list[int] = []
    ambiguous: list[int] = []
    for index in range(probe.MARKER_BITS):
        votes = []
        for dy in SAMPLE_OFFSETS:
            row = rows[y0 + dy]
            for dx in SAMPLE_OFFSETS:
                x = x0 + index * probe.CELL + dx
                pixel = row[x * bpp : x * bpp + 3]
                votes.append(1 if sum(pixel) < 3 * 128 else 0)
        dark = sum(votes)
        if dark not in (0, len(votes)):
            ambiguous.append(index)
        bits.append(1 if dark * 2 > len(votes) else 0)
    parsed = probe.parse_marker_bits(bits) if not ambiguous else None
    return {
        "ok": parsed is not None,
        "seq": parsed[0] if parsed else None,
        "crc": parsed[1] if parsed else None,
        "ambiguous_cells": ambiguous,
        "size": [width, height],
    }


def encode_test_png(
    width: int, height: int, black: list[tuple[int, int, int, int]], filt: int = 4
) -> bytes:
    """A white RGB PNG with black rectangles, each row with filter ``filt`` (tests only)."""
    pixels = [bytearray(b"\xff" * (width * 3)) for _ in range(height)]
    for x, y, w, h in black:
        for yy in range(max(0, y), min(height, y + h)):
            for xx in range(max(0, x), min(width, x + w)):
                pixels[yy][xx * 3 : xx * 3 + 3] = b"\x00\x00\x00"
    raw = bytearray()
    prior = bytearray(width * 3)
    for row in pixels:
        raw.append(filt)
        raw += _filter(filt, row, prior, 3)
        prior = row
    body = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    return (
        PNG_MAGIC
        + chunk(b"IHDR", body)
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )


def _filter(kind: int, row: bytearray, prior: bytearray, bpp: int) -> bytearray:
    out = bytearray(len(row))
    for i in range(len(row)):
        left = row[i - bpp] if i >= bpp else 0
        up = prior[i]
        upleft = prior[i - bpp] if i >= bpp else 0
        predictor = {0: 0, 1: left, 2: up, 3: (left + up) >> 1, 4: _paeth(left, up, upleft)}[kind]
        out[i] = (row[i] - predictor) & 0xFF
    return out
