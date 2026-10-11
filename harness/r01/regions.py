"""Screen regions for R01 (draft registration v2, sections 5.3 and 7.1).

The clock box is fitted to the **full extent of the clock label**, not to the pixels that a
one-minute change moves (wave 1's defect): over every Stage A1 frame, the bounding rectangle of
the pixels inside the top bar's centre segment that differ from the bar's background colour,
padded by ``pad`` pixels. Hour digits are therefore inside the box whether or not any A1 pair
crossed an hour. A fit stops (``ok = False``) when the label touches the segment's edge (the
segment is too narrow to hold it) or the box exceeds ``max_area_share`` of the screen.

Composites act on raw PNGs, before ``agents.process_image``: ``swap_box`` copies the box's pixels
from one frame into another; ``mask_box`` fills it with the background colour. ``components``
returns the 8-connected pixel-difference components of a pair, and ``census`` classifies them as
inside the box, caret-like (at most 3 px wide, 10-40 px tall) or other.

Pillow and numpy (scipy for the component labels). Deterministic: the same inputs give the same
PNG bytes.
"""

from __future__ import annotations

import io
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

BAND_ROWS = (0, 32)  # the top bar's rows searched for the clock label (GNOME, 1920 x 1080)
CENTRE = (1 / 3, 2 / 3)  # the bar's centre segment, as fractions of the width
PAD_PX = 4
MAX_AREA_SHARE = 0.02
CARET_MAX_W, CARET_H = 3, (10, 40)


def to_array(png: bytes) -> np.ndarray:
    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()


def to_png(array: np.ndarray) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    # compress_level 1: lossless and deterministic; the level never reaches the model, because
    # ``agents.process_image`` decodes and re-encodes every frame
    Image.fromarray(np.asarray(array, dtype=np.uint8), mode="RGB").save(
        buffer, format="PNG", compress_level=1
    )
    return buffer.getvalue()


@dataclass(frozen=True)
class Box:
    """A half-open pixel rectangle ``[x0, x1) x [y0, y1)``."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def area(self) -> int:
        return max(0, self.x1 - self.x0) * max(0, self.y1 - self.y0)

    def as_list(self) -> list[int]:
        return [self.x0, self.y0, self.x1, self.y1]

    @classmethod
    def of(cls, values: Sequence[int]) -> Box:
        x0, y0, x1, y1 = (int(v) for v in values)
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"empty box {values}")
        return cls(x0, y0, x1, y1)


def band_background(array: np.ndarray, band: tuple[int, int] = BAND_ROWS) -> tuple[int, int, int]:
    """The most frequent colour of the top bar band (its background)."""
    rows = array[band[0] : band[1]].reshape(-1, 3)
    counts = Counter(map(tuple, rows.tolist()))
    colour, _ = counts.most_common(1)[0]
    return tuple(int(c) for c in colour)  # type: ignore[return-value]


def label_extent(
    array: np.ndarray,
    background: tuple[int, int, int],
    band: tuple[int, int] = BAND_ROWS,
    centre: tuple[float, float] = CENTRE,
) -> Box | None:
    """The bounding rectangle of non-background pixels in the band's centre segment."""
    height, width, _ = array.shape
    cx0, cx1 = int(round(width * centre[0])), int(round(width * centre[1]))
    seg = array[band[0] : band[1], cx0:cx1]
    mask = np.any(seg != np.asarray(background, dtype=np.uint8), axis=2)
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    return Box(
        cx0 + int(xs.min()),
        band[0] + int(ys.min()),
        cx0 + int(xs.max()) + 1,
        band[0] + int(ys.max()) + 1,
    )


def fit_clock_box(
    frames: Iterable[bytes],
    *,
    band: tuple[int, int] = BAND_ROWS,
    centre: tuple[float, float] = CENTRE,
    pad: int = PAD_PX,
    max_area_share: float = MAX_AREA_SHARE,
) -> dict[str, Any]:
    """Fit the clock box to the union of the label's extent over ``frames`` (section 5.3)."""
    union: list[int] | None = None
    background: tuple[int, int, int] | None = None
    n = 0
    touches = 0
    shape: tuple[int, int] | None = None
    for png in frames:
        array = to_array(png)
        n += 1
        shape = shape or array.shape[:2]
        if array.shape[:2] != shape:
            return {"ok": False, "reason": "frames differ in size", "frames": n}
        bg = band_background(array, band)
        background = background or bg
        if bg != background:
            return {
                "ok": False,
                "reason": f"top bar background differs: {bg} vs {background}",
                "frames": n,
            }
        extent = label_extent(array, background, band, centre)
        if extent is None:
            continue
        cx0, cx1 = int(round(shape[1] * centre[0])), int(round(shape[1] * centre[1]))
        if extent.x0 <= cx0 or extent.x1 >= cx1:
            touches += 1
        union = (
            extent.as_list()
            if union is None
            else [
                min(union[0], extent.x0),
                min(union[1], extent.y0),
                max(union[2], extent.x1),
                max(union[3], extent.y1),
            ]
        )
    if n == 0 or union is None or shape is None or background is None:
        return {"ok": False, "reason": "no frame shows a label in the centre segment", "frames": n}
    height, width = shape
    box = Box(
        max(0, union[0] - pad),
        max(band[0], union[1] - pad),
        min(width, union[2] + pad),
        min(band[1], union[3] + pad),
    )
    out: dict[str, Any] = {
        "ok": True,
        "box": box.as_list(),
        "background": list(background),
        "frames": n,
        "label_union": union,
        "pad_px": pad,
        "band_rows": list(band),
        "centre": list(centre),
        "area_share": round(box.area / (width * height), 6),
        "frames_touching_segment_edge": touches,
    }
    if touches:
        out.update(
            ok=False, reason=f"the label touches the centre segment's edge in {touches} frames"
        )
    elif box.area > max_area_share * width * height:
        out.update(ok=False, reason=f"box area share {out['area_share']} > {max_area_share}")
    return out


def swap_box(dst_png: bytes, src_png: bytes, box: Box) -> bytes:
    """``dst`` with the pixels inside ``box`` copied from ``src`` (same size required)."""
    dst, src = to_array(dst_png), to_array(src_png)
    if dst.shape != src.shape:
        raise ValueError("frames differ in size")
    out = dst.copy()
    out[box.y0 : box.y1, box.x0 : box.x1] = src[box.y0 : box.y1, box.x0 : box.x1]
    return to_png(out)


def mask_box(png: bytes, box: Box, colour: Sequence[int]) -> bytes:
    array = to_array(png)
    array[box.y0 : box.y1, box.x0 : box.x1] = np.asarray(colour, dtype=np.uint8)
    return to_png(array)


def differs(a_png: bytes, b_png: bytes) -> np.ndarray:
    a, b = to_array(a_png), to_array(b_png)
    if a.shape != b.shape:
        raise ValueError("frames differ in size")
    return np.any(a != b, axis=2)


def differs_outside(a_png: bytes, b_png: bytes, box: Box) -> bool:
    mask = differs(a_png, b_png)
    mask[box.y0 : box.y1, box.x0 : box.x1] = False
    return bool(mask.any())


def differs_inside(a_png: bytes, b_png: bytes, box: Box) -> bool:
    return bool(differs(a_png, b_png)[box.y0 : box.y1, box.x0 : box.x1].any())


def components(a_png: bytes, b_png: bytes) -> list[Box]:
    """8-connected components of the pixels that differ between two frames."""
    from scipy import ndimage

    mask = differs(a_png, b_png)
    labels, n = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    out = []
    for sl in ndimage.find_objects(labels):
        if sl is None:
            continue
        ys, xs = sl
        out.append(Box(xs.start, ys.start, xs.stop, ys.stop))
    return sorted(out, key=lambda b: (b.y0, b.x0))


def classify(component: Box, box: Box) -> str:
    inside = (
        component.x0 >= box.x0
        and component.x1 <= box.x1
        and component.y0 >= box.y0
        and component.y1 <= box.y1
    )
    if inside:
        return "clock"
    w, h = component.x1 - component.x0, component.y1 - component.y0
    if w <= CARET_MAX_W and CARET_H[0] <= h <= CARET_H[1]:
        return "caret_like"
    return "other"


def census(a_png: bytes, b_png: bytes, box: Box) -> dict[str, Any]:
    """Region census of one pair: component counts by class and whether any pixel outside the
    box differs (the A1 primary statistic's unit)."""
    comps = components(a_png, b_png)
    counts = Counter(classify(c, box) for c in comps)
    return {
        "identical": not comps,
        "outside_box": differs_outside(a_png, b_png, box),
        "clock": counts.get("clock", 0),
        "caret_like": counts.get("caret_like", 0),
        "other": counts.get("other", 0),
    }
