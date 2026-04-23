from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent

from ..core.ocr import Word
from ..core.selection import WordIndex


HIGHLIGHT = QColor(80, 140, 255, 90)


class SelectionOverlayItem(QGraphicsItem):
    def __init__(self, width: int, height: int):
        super().__init__()
        self._width = width
        self._height = height
        self.words: list[Word] = []
        self._index: WordIndex | None = None
        self._anchor: int | None = None
        self._active: int | None = None
        self._is_selecting = False
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def set_words(self, words: list[Word]) -> None:
        self.words = words
        self._index = WordIndex(words) if words else None
        self.clear_selection()
        self.update()

    def selected_words(self) -> list[Word]:
        if self._index is None or self._anchor is None or self._active is None:
            return []
        idxs = self._index.range_between(self._anchor, self._active)
        return [self.words[i] for i in idxs]

    def clear_selection(self) -> None:
        self._anchor = None
        self._active = None
        self._is_selecting = False
        self.update()

    # --- hover / cursor feedback ---
    def hoverMoveEvent(self, event) -> None:
        if self._index is None:
            self.unsetCursor()
            return
        pos = event.pos()
        if self._index.word_at(pos.x(), pos.y()) is not None:
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    # --- selection math ---
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._index is None or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        pos = event.pos()
        hit = self._index.word_at(pos.x(), pos.y())
        if hit is None:
            hit = self._index.nearest_word(pos.x(), pos.y())
        if hit is None:
            self.clear_selection()
            event.accept()
            return
        self._anchor = hit
        self._active = hit
        self._is_selecting = True
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._is_selecting or self._index is None or self._anchor is None:
            super().mouseMoveEvent(event)
            return
        pos = event.pos()
        target = self._index.nearest_word(pos.x(), pos.y(), same_line_as=self._anchor)
        if target is not None:
            self._active = target
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._is_selecting = False
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if self._index is None or self._anchor is None or self._active is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(HIGHLIGHT))
        for idx in self._index.range_between(self._anchor, self._active):
            w = self.words[idx]
            painter.drawRect(QRectF(w.x, w.y, w.w, w.h))
