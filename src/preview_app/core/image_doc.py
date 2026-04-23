from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .ocr import Word, ocr_words
from .pdf_doc import PageRender


@dataclass
class ImageDoc:
    path: Path
    _image: Image.Image | None = None
    _words: list[Word] | None = None

    @classmethod
    def open(cls, path: str | Path) -> "ImageDoc":
        p = Path(path)
        img = Image.open(str(p))
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        return cls(path=p, _image=img)

    @property
    def image(self) -> Image.Image:
        assert self._image is not None
        return self._image

    @property
    def page_count(self) -> int:
        return 1

    def render_page(self, page_index: int = 0, dpi: int = 144) -> PageRender:
        assert self._image is not None
        w, h = self._image.size
        return PageRender(image=self._image, dpi=dpi, width_px=w, height_px=h)

    def detect_mode(self, page_index: int = 0) -> str:
        return "ocr"

    def words_for(self, page_index: int = 0, dpi: int = 144) -> list[Word]:
        if self._words is None:
            assert self._image is not None
            self._words = ocr_words(self._image)
        return self._words

    def close(self) -> None:
        if self._image is not None:
            self._image.close()
            self._image = None
