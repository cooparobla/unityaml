"""Tests for unityaml.image — ImageProperties, ImageFileHandler, and header parsers.

All tests use synthetic binary images so Pillow is NOT required (though the
tests still pass when Pillow is installed, because Pillow gives the same answers
for standard formats).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from unityaml.base import AssetType
from unityaml.image import (
    ImageFileHandler,
    ImageProperties,
    _parse_bmp,
    _parse_gif,
    _parse_jpeg,
    _parse_png,
    _read_image_info,
)


# ──────────────────────────────────────────────────────────────────────────────
# Image-writing helpers
# ──────────────────────────────────────────────────────────────────────────────


def _write_png(path: Path, width: int = 4, height: int = 2, color_type: int = 2) -> None:
    """Write a minimal valid PNG (no actual pixel decompression needed for header tests)."""

    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    # color_type: 2=RGB, 6=RGBA, 0=Gray, 4=GrayAlpha
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type, 3)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    # Minimal IDAT: one filter byte per row, bpp bytes per pixel
    raw_rows = (b"\x00" + b"\xff" * (width * bpp)) * height
    idat_data = zlib.compress(raw_rows)
    path.write_bytes(
        signature
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", idat_data)
        + chunk(b"IEND", b"")
    )


def _write_jpeg(path: Path, width: int = 8, height: int = 4) -> None:
    """Write a minimal JPEG with a valid SOF0 marker."""
    # SOI + APP0 + SOF0 + EOI
    soi = b"\xff\xd8"
    # APP0 (JFIF) — length = 16
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    # SOF0 — length = 8 + 3*components, precision=8
    n_comp = 3  # RGB
    sof0_data = struct.pack(">H", 8 + 3 * n_comp) + struct.pack(">BHHB", 8, height, width, n_comp)
    for i in range(n_comp):
        sof0_data += struct.pack("BBB", i + 1, 0x11, 0)
    sof0 = b"\xff\xc0" + sof0_data
    eoi = b"\xff\xd9"
    path.write_bytes(soi + app0 + sof0 + eoi)


def _write_gif(path: Path, width: int = 16, height: int = 8) -> None:
    """Write a minimal GIF89a header."""
    header = b"GIF89a" + struct.pack("<HH", width, height) + b"\x00\x00\x00"
    path.write_bytes(header)


def _write_bmp(path: Path, width: int = 10, height: int = 5) -> None:
    """Write a minimal BMP header."""
    # File header (14 bytes) + DIB header (40 bytes)
    pixel_data_offset = 54
    file_size = pixel_data_offset + width * height * 3
    file_header = b"BM" + struct.pack("<IHH I", file_size, 0, 0, pixel_data_offset)
    dib_header = struct.pack(
        "<IiiHHIIiiII",
        40,          # header size
        width,       # width
        height,      # height (positive = bottom-up)
        1,           # color planes
        24,          # bits per pixel
        0,           # BI_RGB (no compression)
        0,           # image size (can be 0 for BI_RGB)
        2835,        # x pixels per meter
        2835,        # y pixels per meter
        0,           # colours in table
        0,           # important colours
    )
    path.write_bytes(file_header + dib_header)


# ──────────────────────────────────────────────────────────────────────────────
# _parse_png
# ──────────────────────────────────────────────────────────────────────────────


class TestParsePng:
    def test_rgb_dimensions(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p, width=4, height=2, color_type=2)
        with open(p, "rb") as f:
            header = f.read(26)
        w, h, ch, fmt = _parse_png(header)
        assert w == 4
        assert h == 2
        assert ch == 3  # RGB
        assert fmt == "PNG"

    def test_rgba_channels(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p, width=2, height=2, color_type=6)
        with open(p, "rb") as f:
            header = f.read(26)
        _, _, ch, _ = _parse_png(header)
        assert ch == 4  # RGBA

    def test_grayscale_channels(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p, width=2, height=2, color_type=0)
        with open(p, "rb") as f:
            header = f.read(26)
        _, _, ch, _ = _parse_png(header)
        assert ch == 1  # Gray

    def test_grayscale_alpha_channels(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p, width=2, height=2, color_type=4)
        with open(p, "rb") as f:
            header = f.read(26)
        _, _, ch, _ = _parse_png(header)
        assert ch == 2  # Gray+Alpha

    def test_short_header_returns_zeros(self):
        w, h, ch, fmt = _parse_png(b"\x89PNG\r\n\x1a\n")  # only 8 bytes
        assert w == 0
        assert h == 0
        assert fmt == "PNG"


# ──────────────────────────────────────────────────────────────────────────────
# _parse_jpeg
# ──────────────────────────────────────────────────────────────────────────────


class TestParseJpeg:
    def test_dimensions(self, tmp_path):
        p = tmp_path / "img.jpg"
        _write_jpeg(p, width=8, height=4)
        w, h, ch, fmt = _parse_jpeg(p)
        assert w == 8
        assert h == 4
        assert ch == 3
        assert fmt == "JPEG"

    def test_fallback_on_corrupt_jpeg(self, tmp_path):
        p = tmp_path / "bad.jpg"
        p.write_bytes(b"\xff\xd8" + b"\x00" * 10)  # no valid SOF
        w, h, ch, fmt = _parse_jpeg(p)
        # Falls back to (0, 0, 3, "JPEG")
        assert fmt == "JPEG"
        assert ch == 3


# ──────────────────────────────────────────────────────────────────────────────
# _parse_gif
# ──────────────────────────────────────────────────────────────────────────────


class TestParseGif:
    def test_gif89a_dimensions(self, tmp_path):
        p = tmp_path / "anim.gif"
        _write_gif(p, width=16, height=8)
        with open(p, "rb") as f:
            header = f.read(26)
        w, h, ch, fmt = _parse_gif(header)
        assert w == 16
        assert h == 8
        assert ch == 3
        assert fmt == "GIF"


# ──────────────────────────────────────────────────────────────────────────────
# _parse_bmp
# ──────────────────────────────────────────────────────────────────────────────


class TestParseBmp:
    def test_bmp_dimensions(self, tmp_path):
        p = tmp_path / "img.bmp"
        _write_bmp(p, width=10, height=5)
        with open(p, "rb") as f:
            header = f.read(26)
        w, h, ch, fmt = _parse_bmp(header)
        assert w == 10
        assert h == 5
        assert ch == 3
        assert fmt == "BMP"

    def test_short_header_returns_safe_defaults(self):
        w, h, ch, fmt = _parse_bmp(b"BM" + b"\x00" * 10)
        assert w == 0
        assert ch == 3
        assert fmt == "BMP"

    def test_negative_height_abs(self, tmp_path):
        """BMP height can be negative (top-down); result should be positive."""
        p = tmp_path / "img.bmp"
        _write_bmp(p, width=4, height=-4)  # _write_bmp treats height as signed
        # Re-read the raw header
        with open(p, "rb") as f:
            header = f.read(26)
        _, h, _, _ = _parse_bmp(header)
        assert h == 4


# ──────────────────────────────────────────────────────────────────────────────
# _read_image_info dispatch
# ──────────────────────────────────────────────────────────────────────────────


class TestReadImageInfo:
    def test_dispatch_png(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p, width=3, height=7)
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "PNG"
        assert w == 3
        assert h == 7

    def test_dispatch_jpeg(self, tmp_path):
        p = tmp_path / "img.jpg"
        _write_jpeg(p, width=5, height=3)
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "JPEG"
        assert w == 5

    def test_dispatch_gif(self, tmp_path):
        p = tmp_path / "img.gif"
        _write_gif(p, width=12, height=6)
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "GIF"
        assert w == 12

    def test_dispatch_bmp(self, tmp_path):
        p = tmp_path / "img.bmp"
        _write_bmp(p, width=8, height=4)
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "BMP"
        assert w == 8

    def test_unknown_extension_returns_ext_name(self, tmp_path):
        p = tmp_path / "img.tga"
        p.write_bytes(b"\x00" * 30)
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "TGA"

    def test_empty_file_does_not_crash(self, tmp_path):
        p = tmp_path / "empty.png"
        p.write_bytes(b"")
        # Should return zeros gracefully
        w, h, ch, fmt = _read_image_info(p)
        assert fmt == "PNG"


# ──────────────────────────────────────────────────────────────────────────────
# ImageFileHandler
# ──────────────────────────────────────────────────────────────────────────────


class TestImageFileHandler:
    def test_load_png(self, tmp_path):
        p = tmp_path / "photo.png"
        _write_png(p, width=4, height=2)
        handler = ImageFileHandler()
        props = handler.load(p)
        assert props.path == p.resolve()
        assert props.asset_type == AssetType.IMAGE
        assert props.format == "PNG"
        assert props.width == 4
        assert props.height == 2
        assert props.file_size_bytes > 0
        assert props.last_modified is not None

    def test_load_jpeg(self, tmp_path):
        p = tmp_path / "photo.jpg"
        _write_jpeg(p, width=6, height=3)
        props = ImageFileHandler().load(p)
        assert props.format == "JPEG"
        assert props.width == 6

    def test_load_gif(self, tmp_path):
        p = tmp_path / "anim.gif"
        _write_gif(p, width=20, height=10)
        props = ImageFileHandler().load(p)
        assert props.format == "GIF"
        assert props.width == 20

    def test_load_bmp(self, tmp_path):
        p = tmp_path / "canvas.bmp"
        _write_bmp(p, width=12, height=6)
        props = ImageFileHandler().load(p)
        assert props.format == "BMP"
        assert props.width == 12

    def test_load_resolves_path(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p)
        props = ImageFileHandler().load(p)
        assert props.path == p.resolve()

    def test_load_sets_versions(self, tmp_path):
        _write_png(tmp_path / "skin.v1.0.png")
        _write_png(tmp_path / "skin.v2.0.png")
        props = ImageFileHandler().load(tmp_path / "skin.v2.0.png")
        assert len(props.versions) == 2

    def test_load_empty_projects_list(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p)
        props = ImageFileHandler().load(p)
        assert props.projects == []

    def test_supported_extensions_set(self):
        exts = ImageFileHandler.SUPPORTED_EXTENSIONS
        assert ".png" in exts
        assert ".jpg" in exts
        assert ".jpeg" in exts
        assert ".gif" in exts
        assert ".bmp" in exts


# ──────────────────────────────────────────────────────────────────────────────
# ImageProperties defaults
# ──────────────────────────────────────────────────────────────────────────────


class TestImageProperties:
    def test_asset_type_is_image(self, tmp_path):
        p = tmp_path / "img.png"
        _write_png(p)
        props = ImageFileHandler().load(p)
        assert props.asset_type == AssetType.IMAGE

    def test_channels_default_zero(self, tmp_path):
        p = tmp_path / "img.tga"
        p.write_bytes(b"\x00" * 20)
        props = ImageFileHandler().load(p)
        assert props.channels == 0  # unknown for TGA
