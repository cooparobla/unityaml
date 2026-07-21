"""Handler for image files (.png, .jpg, .jpeg, .gif, .bmp, .tga, etc.).

Reads image dimensions and format using Python stdlib + minimal binary parsing
so Pillow is not required.  When Pillow IS installed, it is used for richer
metadata (channels, exact format string).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unityaml.base import AssetType, BaseFileHandler, BaseProperties, FileVersion
from unityaml.versioning import resolve_versions


@dataclass
class ImageProperties(BaseProperties):
    """Properties specific to image files."""

    asset_type: AssetType = field(default=AssetType.IMAGE, init=False)
    width: int = 0
    height: int = 0
    channels: int = 0   # 3=RGB, 4=RGBA
    file_size_bytes: int = 0
    format: str = ""    # "PNG", "JPEG", "GIF", etc.


class ImageFileHandler(BaseFileHandler):
    """Handles image files — reads dimensions, format, size."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp"}

    def load(self, path: Path) -> ImageProperties:
        path = path.resolve()
        stat = path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        versions = resolve_versions(path)

        width, height, channels, fmt = _read_image_info(path)

        return ImageProperties(
            path=path,
            versions=versions,
            projects=[],
            last_modified=last_modified,
            width=width,
            height=height,
            channels=channels,
            file_size_bytes=stat.st_size,
            format=fmt,
        )


# ---------------------------------------------------------------------------
# Image header parsing (no Pillow required)
# ---------------------------------------------------------------------------

def _read_image_info(path: Path) -> tuple[int, int, int, str]:
    """Return (width, height, channels, format_string) for the given image.

    Falls back to Pillow if available for full accuracy.  Otherwise uses
    lightweight binary header parsing for PNG and JPEG.
    """
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as im:
            w, h = im.size
            mode = im.mode
            channels = len(mode) if mode not in ("P", "L", "LA") else (2 if "A" in mode else 1)
            fmt = im.format or path.suffix.lstrip(".").upper()
            return w, h, channels, fmt
    except ImportError:
        pass

    # Fallback: manual header parse
    ext = path.suffix.lower()
    try:
        with open(path, "rb") as f:
            header = f.read(26)
    except OSError:
        return 0, 0, 0, ext.lstrip(".").upper()

    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return _parse_png(header)
    if header[:2] in (b"\xff\xd8",):
        return _parse_jpeg(path)
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return _parse_gif(header)
    if header[:2] == b"BM":
        return _parse_bmp(header)

    return 0, 0, 0, ext.lstrip(".").upper()


def _parse_png(header: bytes) -> tuple[int, int, int, str]:
    # IHDR starts at byte 16: width (4), height (4), bit_depth (1), color_type (1)
    if len(header) < 26:
        return 0, 0, 0, "PNG"
    w = struct.unpack(">I", header[16:20])[0]
    h = struct.unpack(">I", header[20:24])[0]
    color_type = header[25]
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
    return w, h, channels, "PNG"


def _parse_jpeg(path: Path) -> tuple[int, int, int, str]:
    with open(path, "rb") as f:
        data = f.read(65536)
    i = 2
    while i < len(data) - 8:
        marker = data[i:i+2]
        if marker[0] != 0xFF:
            break
        length = struct.unpack(">H", data[i+2:i+4])[0]
        if marker[1] in (0xC0, 0xC2):  # SOF0, SOF2
            h = struct.unpack(">H", data[i+5:i+7])[0]
            w = struct.unpack(">H", data[i+7:i+9])[0]
            c = data[i+9]
            return w, h, c, "JPEG"
        i += 2 + length
    return 0, 0, 3, "JPEG"


def _parse_gif(header: bytes) -> tuple[int, int, int, str]:
    w = struct.unpack("<H", header[6:8])[0]
    h = struct.unpack("<H", header[8:10])[0]
    return w, h, 3, "GIF"


def _parse_bmp(header: bytes) -> tuple[int, int, int, str]:
    if len(header) < 22:
        return 0, 0, 3, "BMP"
    w = struct.unpack("<I", header[18:22])[0]
    h = abs(struct.unpack("<i", header[22:26])[0]) if len(header) >= 26 else 0
    return w, h, 3, "BMP"
