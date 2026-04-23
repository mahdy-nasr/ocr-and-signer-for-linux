from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget


class DrawCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 220)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self._paths: list[QPainterPath] = []
        self._current: QPainterPath | None = None
        self._last_point: QPointF | None = None
        self._thickness: float = 2.4
        self._color: QColor = QColor(0, 0, 0)

    def set_thickness(self, thickness: float) -> None:
        self._thickness = float(thickness)
        self.update()

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def clear(self) -> None:
        self._paths = []
        self._current = None
        self._last_point = None
        self.update()

    def undo(self) -> None:
        if self._paths:
            self._paths.pop()
            self.update()

    def is_empty(self) -> bool:
        return not self._paths and self._current is None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position()
        self._current = QPainterPath()
        self._current.moveTo(point)
        self._last_point = point
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._current is None or self._last_point is None:
            return
        point = event.position()
        mid = QPointF((self._last_point.x() + point.x()) / 2, (self._last_point.y() + point.y()) / 2)
        self._current.quadTo(self._last_point, mid)
        self._last_point = point
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._current is None:
            return
        if self._last_point is not None:
            self._current.lineTo(event.position())
        self._paths.append(self._current)
        self._current = None
        self._last_point = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        pen = QPen(self._color, self._thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for path in self._paths:
            painter.drawPath(path)
        if self._current is not None:
            painter.drawPath(self._current)

    def render_to_png_bytes(self) -> bytes:
        bounds = QRectF()
        for path in self._paths:
            b = path.boundingRect()
            bounds = b if bounds.isEmpty() else bounds.united(b)
        if bounds.isEmpty():
            raise ValueError("Canvas is empty")

        pad = 12
        bounds = bounds.adjusted(-pad, -pad, pad, pad)
        w = max(1, int(bounds.width()))
        h = max(1, int(bounds.height()))
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(-bounds.left(), -bounds.top())
        pen = QPen(self._color, self._thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for path in self._paths:
            painter.drawPath(path)
        painter.end()

        from ..util.image_utils import qimage_to_png_bytes
        return qimage_to_png_bytes(img)
