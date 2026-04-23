from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pytesseract
from pytesseract import Output


DEBUG = os.environ.get("PREVIEW_APP_DEBUG", "") not in ("", "0", "false")


@dataclass(frozen=True)
class Word:
    text: str
    x: float
    y: float
    w: float
    h: float
    block: int
    par: int
    line: int
    word: int
    conf: float = 0.0

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @property
    def key(self) -> tuple[int, int, int, int]:
        return (self.block, self.par, self.line, self.word)


def _ocr_pass(pil_image, lang: str, psm: int) -> list[Word]:
    data = pytesseract.image_to_data(
        pil_image,
        lang=lang,
        config=f"--psm {psm}",
        output_type=Output.DICT,
    )
    n = len(data["text"])
    words: list[Word] = []
    for i in range(n):
        if int(data["level"][i]) != 5:
            continue
        text = data["text"][i]
        if not text or not text.strip():
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue
        words.append(
            Word(
                text=text,
                x=float(data["left"][i]),
                y=float(data["top"][i]),
                w=float(data["width"][i]),
                h=float(data["height"][i]),
                block=int(data["block_num"][i]),
                par=int(data["par_num"][i]),
                line=int(data["line_num"][i]),
                word=int(data["word_num"][i]),
                conf=conf,
            )
        )
    return words


def ocr_words(pil_image, lang: str = "eng") -> list[Word]:
    """Run tesseract with layout fallbacks so varied image layouts work."""
    # psm 6 = uniform text block (best for document-style scans)
    # psm 3 = fully automatic (best for mixed / unknown layouts)
    # psm 11 = sparse text (best for posters / UI screenshots)
    # psm 7 = single text line (last-resort for single-line headers)
    tried: list[tuple[int, int]] = []
    for psm in (6, 3, 11, 7):
        try:
            words = _ocr_pass(pil_image, lang, psm)
        except Exception as e:  # noqa: BLE001
            if DEBUG:
                print(f"[ocr] psm={psm} failed: {e}", file=sys.stderr)
            continue
        tried.append((psm, len(words)))
        if words:
            if DEBUG:
                print(f"[ocr] psm={psm} -> {len(words)} words (tried={tried})", file=sys.stderr)
            return words
    if DEBUG:
        print(f"[ocr] no words detected, tried={tried}", file=sys.stderr)
    return []
