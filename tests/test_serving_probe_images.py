from __future__ import annotations

import base64

import numpy as np
import pytest

from harness.serving_probe.images import (
    data_url,
    decode_png_rgb,
    encode_png_rgb,
    make_image,
    png_size,
    random_pixel_jpeg,
    render_screenshot,
    screenshot_png,
)


def test_png_encoder_round_trips_exact_pixels() -> None:
    pixels = np.random.default_rng(0).integers(0, 256, (17, 23, 3), dtype=np.uint8)
    blob = encode_png_rgb(pixels)
    assert png_size(blob) == (23, 17)
    assert np.array_equal(decode_png_rgb(blob), pixels)


def test_png_is_readable_by_pillow() -> None:
    PIL = pytest.importorskip("PIL.Image")
    import io

    blob = screenshot_png(320, 180, (1, 2, 3))
    with PIL.open(io.BytesIO(blob)) as image:
        assert image.size == (320, 180)
        assert image.mode == "RGB"
        assert np.array_equal(np.asarray(image), render_screenshot(320, 180, (1, 2, 3)))


def test_screenshots_are_deterministic_and_unique_per_seed() -> None:
    first = screenshot_png(640, 360, (101, 2, 0, 1))
    assert first == screenshot_png(640, 360, (101, 2, 0, 1))
    assert first != screenshot_png(640, 360, (101, 2, 0, 2))
    assert first != screenshot_png(640, 360, (101, 2, 1, 1))


def test_rendered_screenshot_is_low_entropy_and_random_jpeg_is_worst_case() -> None:
    rendered = screenshot_png(1920, 1080, (42, 2, 0, 0))
    noise = random_pixel_jpeg(1920, 1080, (42, 2, 0, 0))
    assert png_size(rendered) == (1920, 1080)
    assert len(rendered) < 400_000
    assert len(noise) > 4 * len(rendered)
    assert noise.startswith(b"\xff\xd8")


def test_data_urls_carry_the_sniffed_type() -> None:
    png = screenshot_png(32, 32, (0,))
    assert data_url(png).startswith("data:image/png;base64,")
    assert base64.b64decode(data_url(png).split(",", 1)[1]) == png
    jpeg = make_image("jpeg-random", 32, 32, (0,))
    assert data_url(jpeg).startswith("data:image/jpeg;base64,")
    with pytest.raises(ValueError):
        data_url(b"GIF89a")
    with pytest.raises(ValueError):
        make_image("webp", 32, 32, (0,))
