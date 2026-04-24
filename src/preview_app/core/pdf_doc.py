from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz
from PIL import Image, ImageDraw

from .ocr import Word, ocr_words


PageMode = Literal["text", "ocr"]


@dataclass
class PageRender:
    image: Image.Image
    dpi: int
    width_px: int
    height_px: int


class PdfDoc:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._doc = fitz.open(str(self.path))
        self._mode_cache: dict[int, PageMode] = {}
        self._words_cache: dict[tuple[int, int], list[Word]] = {}
        self._render_cache: dict[tuple[int, int], PageRender] = {}
        self._baked = False

    def bake(self) -> None:
        # Flatten AcroForm widgets & annotations into page content so they
        # can't render over later signatures and the form becomes frozen.
        if self._baked:
            return
        self._doc.bake(annots=True, widgets=True)
        self._baked = True
        self.invalidate_caches()

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def is_encrypted(self) -> bool:
        return self._doc.is_encrypted

    def authenticate(self, password: str) -> bool:
        return bool(self._doc.authenticate(password))

    def close(self) -> None:
        self._doc.close()

    def render_page(self, page_index: int, dpi: int = 144) -> PageRender:
        key = (page_index, dpi)
        cached = self._render_cache.get(key)
        if cached is not None:
            return cached
        page = self._doc.load_page(page_index)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        _overlay_widget_placeholders(img, page, dpi)
        render = PageRender(image=img, dpi=dpi, width_px=pix.width, height_px=pix.height)
        self._render_cache[key] = render
        return render

    def detect_mode(self, page_index: int) -> PageMode:
        cached = self._mode_cache.get(page_index)
        if cached is not None:
            return cached
        page = self._doc.load_page(page_index)
        words = page.get_text("words")
        mode: PageMode = "text" if len(words) >= 5 else "ocr"
        self._mode_cache[page_index] = mode
        return mode

    def words_for(self, page_index: int, dpi: int = 144) -> list[Word]:
        key = (page_index, dpi)
        cached = self._words_cache.get(key)
        if cached is not None:
            return cached

        mode = self.detect_mode(page_index)
        if mode == "text":
            words = self._text_words(page_index, dpi)
        else:
            render = self.render_page(page_index, dpi)
            words = ocr_words(render.image)

        self._words_cache[key] = words
        return words

    def _text_words(self, page_index: int, dpi: int) -> list[Word]:
        page = self._doc.load_page(page_index)
        scale = dpi / 72.0
        result: list[Word] = []
        raw = page.get_text("words")
        for tup in raw:
            x0, y0, x1, y1, text, block, line, word = tup[:8]
            if not text or not text.strip():
                continue
            result.append(
                Word(
                    text=text,
                    x=x0 * scale,
                    y=y0 * scale,
                    w=(x1 - x0) * scale,
                    h=(y1 - y0) * scale,
                    block=int(block),
                    par=int(block),
                    line=int(line),
                    word=int(word),
                    conf=100.0,
                )
            )
        return result

    def invalidate_caches(self) -> None:
        self._mode_cache.clear()
        self._words_cache.clear()
        self._render_cache.clear()

    def reload(self) -> None:
        self._doc.close()
        self._doc = fitz.open(str(self.path))
        self.invalidate_caches()

    def get_page(self, page_index: int) -> fitz.Page:
        return self._doc.load_page(page_index)

    def save(self, path: str | Path | None = None) -> Path:
        if path is None:
            self._doc.saveIncr()
            self.invalidate_caches()
            return self.path
        target = Path(path)
        self._doc.save(str(target), garbage=4, deflate=True)
        return target


def _overlay_widget_placeholders(img: Image.Image, page: fitz.Page, dpi: int) -> None:
    # PyMuPDF's pixmap does not draw the "please fill me in" highlight that
    # Evince/Firefox/Adobe render for empty AcroForm widgets. Composite a
    # translucent grey box so placement in the app matches what viewers show.
    widgets = list(page.widgets() or [])
    if not widgets:
        return
    scale = dpi / 72.0
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for w in widgets:
        r = w.rect
        box = (
            int(r.x0 * scale),
            int(r.y0 * scale),
            int(r.x1 * scale),
            int(r.y1 * scale),
        )
        draw.rectangle(box, fill=(210, 210, 210, 120), outline=(150, 150, 150, 200), width=1)
    if img.mode != "RGBA":
        rgba = img.convert("RGBA")
        rgba.alpha_composite(overlay)
        img.paste(rgba.convert(img.mode))
    else:
        img.alpha_composite(overlay)
