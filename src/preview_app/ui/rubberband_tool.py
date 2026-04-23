from __future__ import annotations

from PyQt6.QtCore import QObject, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCursor, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent


class _Signals(QObject):
    finalized = pyqtSignal(float, float, float, float)


class RubberBandItem(QGraphicsItem):
    def __init__(self, width: int, height: int):
        super().__init__()
        self._width = width
        self._height = height
        self._signals = _Signals()
        self.finalized = self._signals.finalized
        self._start = None
        self._current = None
        self._final: tuple[float, float, float, float] | None = None
        self._dragging = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def clear(self) -> None:
        self._start = None
        self._current = None
        self._final = None
        self._dragging = False
        self.update()

    def final_rect(self) -> tuple[float, float, float, float] | None:
        return self._final

    def hoverMoveEvent(self, event) -> None:
        if self.isEnabled():
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self.isEnabled() or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._start = event.pos()
        self._current = event.pos()
        self._final = None
        self._dragging = True
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        self._current = event.pos()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._dragging:
            super().mouseReleaseEvent(event)
            return
        self._dragging = False
        if self._start is not None and self._current is not None:
            x0 = min(self._start.x(), self._current.x())
            y0 = min(self._start.y(), self._current.y())
            x1 = max(self._start.x(), self._current.x())
            y1 = max(self._start.y(), self._current.y())
            if x1 - x0 >= 3 and y1 - y0 >= 3:
                self._final = (x0, y0, x1, y1)
                self._signals.finalized.emit(x0, y0, x1, y1)
            else:
                self._final = None
        self.update()
        event.accept()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        rect = self._live_rect()
        if rect is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setBrush(QBrush(QColor(80, 140, 255, 40)))
        pen = QPen(QColor(40, 90, 220))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(rect)

    def _live_rect(self) -> QRectF | None:
        if self._final is not None:
            x0, y0, x1, y1 = self._final
            return QRectF(x0, y0, x1 - x0, y1 - y0)
        if self._start is not None and self._current is not None:
            x0 = min(self._start.x(), self._current.x())
            y0 = min(self._start.y(), self._current.y())
            x1 = max(self._start.x(), self._current.x())
            y1 = max(self._start.y(), self._current.y())
            return QRectF(x0, y0, x1 - x0, y1 - y0)
        return None
