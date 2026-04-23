from __future__ import annotations

from pathlib import Path

import fitz

from .pdf_doc import PdfDoc


def apply_signature(
    doc: PdfDoc,
    page_index: int,
    signature_png: str | Path,
    rect_px: tuple[float, float, float, float],
    dpi: int,
) -> None:
    """Insert a signature PNG onto a page. rect_px is in rendered-pixel coords."""
    page = doc.get_page(page_index)
    scale = 72.0 / dpi
    x0, y0, x1, y1 = rect_px
    rect_pt = fitz.Rect(x0 * scale, y0 * scale, x1 * scale, y1 * scale)
    page.insert_image(
        rect_pt,
        filename=str(signature_png),
        keep_proportion=False,
        overlay=True,
    )


def save_incremental(doc: PdfDoc) -> Path:
    return doc.save(None)


def save_as(doc: PdfDoc, path: str | Path) -> Path:
    return doc.save(path)
