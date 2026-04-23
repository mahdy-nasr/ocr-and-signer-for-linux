from __future__ import annotations

from pathlib import Path

from PIL import Image


def save_image_region(source: Image.Image, rect_px: tuple[int, int, int, int], out_path: str | Path) -> Path:
    cropped = source.crop(rect_px)
    p = Path(out_path)
    cropped.save(str(p), "PNG")
    return p
