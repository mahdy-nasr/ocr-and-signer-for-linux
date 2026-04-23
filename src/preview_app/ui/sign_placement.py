from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent


HANDLE_SIZE = 10
RESIZE_MARGIN = 6


class _Signals(QObject):
    confirmed = pyqtSignal(object)
    cancelled = pyqtSignal(object)
    geometry_changed = pyqtSignal()


class SignPlacementItem(QGraphicsItem):
    def __init__(self, pixmap: QPixmap, signature_path: Path):
        super().__init__()
        self._pixmap = pixmap
        self._width = float(pixmap.width())
        self._height = float(pixmap.height())
        self.signature_path = Path(signature_path)

        self._signals = _Signals()
        self.confirmed = self._signals.confirmed
        self.cancelled = self._signals.cancelled
        self.geometry_changed = self._signals.geometry_changed

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._resizing = False
        self._resize_anchor: Optional[QPointF] = None
        self._aspect = self._width / max(self._height, 1.0)

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE
        return QRectF(-pad, -pad, self._width + pad * 2, self._height + pad * 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(
            QRectF(0, 0, self._width, self._height).toRect(),
            self._pixmap,
        )
        painter.setPen(QPen(QColor(40, 90, 220), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawRect(QRectF(0, 0, self._width, self._height))
        br = self._resize_handle_rect()
        painter.setPen(QPen(QColor(40, 90, 220), 1))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(br)

    def _resize_handle_rect(self) -> QRectF:
        return QRectF(
            self._width - HANDLE_SIZE / 2,
            self._height - HANDLE_SIZE / 2,
            HANDLE_SIZE,
            HANDLE_SIZE,
        )

    def hoverMoveEvent(self, event) -> None:
        if self._resize_handle_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._resize_handle_rect().contains(event.pos()):
            self._resizing = True
            self._resize_anchor = event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._resizing:
            new_w = max(20.0, event.pos().x())
            new_h = max(20.0, new_w / self._aspect)
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                new_h = max(20.0, event.pos().y())
                new_w = new_h * self._aspect
            self.prepareGeometryChange()
            self._width = new_w
            self._height = new_h
            self.update()
            self._signals.geometry_changed.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)
        self._signals.geometry_changed.emit()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._resizing = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._signals.confirmed.emit(self)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._signals.cancelled.emit(self)
            event.accept()
            return
        super().keyPressEvent(event)

    def target_rect_px(self) -> tuple[float, float, float, float]:
        pos = self.pos()
        x0 = pos.x()
        y0 = pos.y()
        return (x0, y0, x0 + self._width, y0 + self._height)

    def confirm(self) -> None:
        self._signals.confirmed.emit(self)

    def cancel(self) -> None:
        self._signals.cancelled.emit(self)
