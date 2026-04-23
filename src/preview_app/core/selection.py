from __future__ import annotations

from dataclasses import dataclass, field

from .ocr import Word


@dataclass
class WordIndex:
    """Spatial + reading-order index over words on a single page/image."""

    words: list[Word]
    cell_size: int = 64
    _grid: dict[tuple[int, int], list[int]] = field(default_factory=dict, init=False)
    _ordered: list[int] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._ordered = sorted(range(len(self.words)), key=lambda i: self.words[i].key)
        for i, word in enumerate(self.words):
            x0 = int(word.x // self.cell_size)
            y0 = int(word.y // self.cell_size)
            x1 = int(word.x2 // self.cell_size)
            y1 = int(word.y2 // self.cell_size)
            for cx in range(x0, x1 + 1):
                for cy in range(y0, y1 + 1):
                    self._grid.setdefault((cx, cy), []).append(i)

    def word_at(self, x: float, y: float) -> int | None:
        cx = int(x // self.cell_size)
        cy = int(y // self.cell_size)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for i in self._grid.get((cx + ox, cy + oy), ()):
                    w = self.words[i]
                    if w.x <= x <= w.x2 and w.y <= y <= w.y2:
                        return i
        return None

    def nearest_word(self, x: float, y: float, same_line_as: int | None = None) -> int | None:
        if not self.words:
            return None

        if same_line_as is not None:
            line_key = self.words[same_line_as].key[:3]
            candidates = [i for i, w in enumerate(self.words) if w.key[:3] == line_key]
            if candidates:
                return min(candidates, key=lambda i: self._dist(self.words[i], x, y))

        hit = self.word_at(x, y)
        if hit is not None:
            return hit

        return min(range(len(self.words)), key=lambda i: self._dist(self.words[i], x, y))

    @staticmethod
    def _dist(w: Word, x: float, y: float) -> float:
        cx = w.x + w.w / 2
        cy = w.y + w.h / 2
        return (cx - x) * (cx - x) + (cy - y) * (cy - y)

    def range_between(self, anchor: int, active: int) -> list[int]:
        if not self.words:
            return []
        a_key = self.words[anchor].key
        b_key = self.words[active].key
        lo, hi = (a_key, b_key) if a_key <= b_key else (b_key, a_key)
        return [i for i in self._ordered if lo <= self.words[i].key <= hi]


def assemble_text(words: list[Word]) -> str:
    if not words:
        return ""
    ordered = sorted(words, key=lambda w: w.key)

    paragraphs: list[list[list[str]]] = []
    prev_par: tuple[int, int] | None = None
    prev_line: tuple[int, int, int] | None = None

    for w in ordered:
        par_key = (w.block, w.par)
        line_key = (w.block, w.par, w.line)
        if par_key != prev_par:
            paragraphs.append([[w.text]])
            prev_par = par_key
            prev_line = line_key
        elif line_key != prev_line:
            paragraphs[-1].append([w.text])
            prev_line = line_key
        else:
            paragraphs[-1][-1].append(w.text)

    return "\n\n".join(
        "\n".join(" ".join(line) for line in para) for para in paragraphs
    )
