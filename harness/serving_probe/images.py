"""Synthetic screenshots for the serving probe.

Two image kinds are used, deliberately different in entropy:

* ``png-rendered``: a deterministic, low-entropy desktop-like scene (wallpaper,
  top bar, dock, windows with title bars and rows of word-like blocks), PNG
  encoded with zlib level 6 like PIL's default. Both harnesses the probe
  imitates send PNG screenshots, so the replay uses this kind.
* ``jpeg-random``: iid uniform pixels saved as JPEG, matching vLLM's
  ``RandomMultiModalDataset`` (worst-case compression). The open-loop brackets
  use it so they remain comparable with ``vllm bench serve`` random-mm runs.

Every image depends only on its seed tuple, so reruns send identical bytes and
distinct episodes or steps never share an image (which would let vLLM's
multimodal caches hide encoder cost).
"""

from __future__ import annotations

import base64
import io
import struct
import zlib
from collections.abc import Sequence

import numpy as np

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def encode_png_rgb(pixels: np.ndarray, *, level: int = 6) -> bytes:
    """Encode an ``(H, W, 3)`` uint8 array as an 8-bit RGB PNG (filter type 0)."""
    if pixels.dtype != np.uint8 or pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError("pixels must be an (H, W, 3) uint8 array")
    height, width, _ = pixels.shape
    rows = np.empty((height, 1 + width * 3), dtype=np.uint8)
    rows[:, 0] = 0
    rows[:, 1:] = pixels.reshape(height, width * 3)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows.tobytes(), level))
        + _chunk(b"IEND", b"")
    )


def png_size(data: bytes) -> tuple[int, int]:
    """Return ``(width, height)`` from a PNG header."""
    if not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def decode_png_rgb(data: bytes) -> np.ndarray:
    """Decode a PNG written by :func:`encode_png_rgb` (filter 0, single IDAT)."""
    width, height = png_size(data)
    offset = len(PNG_SIGNATURE)
    idat = b""
    while offset < len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            idat += payload
        offset += 12 + length
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(height, 1 + width * 3)
    if np.any(raw[:, 0] != 0):
        raise ValueError("only filter type 0 is supported")
    return raw[:, 1:].reshape(height, width, 3).copy()


_PALETTE = np.array(
    [
        [48, 10, 36],
        [233, 84, 32],
        [119, 41, 83],
        [44, 0, 30],
        [242, 242, 242],
        [60, 60, 60],
        [25, 118, 210],
        [56, 142, 60],
        [251, 192, 45],
        [211, 47, 47],
    ],
    dtype=np.uint8,
)


def render_screenshot(width: int, height: int, seed: Sequence[int]) -> np.ndarray:
    """Render a deterministic desktop-like RGB scene for ``seed``."""
    rng = np.random.default_rng(list(seed))
    image = np.empty((height, width, 3), dtype=np.uint8)
    base = _PALETTE[rng.integers(0, 4)].astype(np.int16)
    gradient = np.linspace(0, 24, height, dtype=np.int16)[:, None]
    for channel in range(3):
        image[:, :, channel] = np.clip(base[channel] + gradient, 0, 255).astype(np.uint8)
    top_bar = max(1, height // 40)
    image[:top_bar] = (30, 30, 30)
    dock = max(1, width // 30)
    image[top_bar:, :dock] = (40, 40, 48)
    icon = max(2, dock - 12)
    for index in range(int(rng.integers(6, 11))):
        y0 = top_bar + 8 + index * (icon + 10)
        if y0 + icon >= height:
            break
        image[y0 : y0 + icon, 6 : 6 + icon] = _PALETTE[rng.integers(4, len(_PALETTE))]
    for _window in range(int(rng.integers(1, 4))):
        win_w = int(rng.integers(width // 4, max(width // 4 + 1, (3 * width) // 4)))
        win_h = int(rng.integers(height // 4, max(height // 4 + 1, (3 * height) // 4)))
        x0 = int(rng.integers(dock + 4, max(dock + 5, width - win_w)))
        y0 = int(rng.integers(top_bar + 4, max(top_bar + 5, height - win_h)))
        x1, y1 = min(width, x0 + win_w), min(height, y0 + win_h)
        title = max(1, height // 36)
        image[y0:y1, x0:x1] = (250, 250, 250)
        image[y0 : min(y1, y0 + title), x0:x1] = _PALETTE[rng.integers(4, 7)]
        line_height = max(2, height // 60)
        y = y0 + title + line_height
        while y + line_height < y1 - line_height:
            x = x0 + 12
            limit = x1 - 12
            while x < limit:
                word = int(rng.integers(12, 80))
                end = min(limit, x + word)
                image[y : y + line_height - 2, x:end] = (70, 70, 70)
                x = end + int(rng.integers(6, 14))
            y += line_height + int(rng.integers(2, 8))
    return image


def screenshot_png(width: int, height: int, seed: Sequence[int]) -> bytes:
    """Return PNG bytes of :func:`render_screenshot`."""
    return encode_png_rgb(render_screenshot(width, height, seed))


def random_pixel_jpeg(width: int, height: int, seed: Sequence[int]) -> bytes:
    """Return a JPEG of iid uniform pixels (vLLM random-mm equivalent)."""
    from PIL import Image

    rng = np.random.default_rng(list(seed))
    pixels = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    with io.BytesIO() as buffer:
        Image.fromarray(pixels).save(buffer, format="JPEG")
        return buffer.getvalue()


def data_url(data: bytes) -> str:
    """Return a base64 data URL with the MIME type sniffed from the bytes."""
    if data.startswith(PNG_SIGNATURE):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8"):
        mime = "image/jpeg"
    else:
        raise ValueError("only PNG and JPEG images are produced by the probe")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def make_image(kind: str, width: int, height: int, seed: Sequence[int]) -> bytes:
    """Produce one image of ``kind`` for ``seed``."""
    if kind == "png-rendered":
        return screenshot_png(width, height, seed)
    if kind == "jpeg-random":
        return random_pixel_jpeg(width, height, seed)
    raise ValueError(f"unknown image kind {kind!r}")
