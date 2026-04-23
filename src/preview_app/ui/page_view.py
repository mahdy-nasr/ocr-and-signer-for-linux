from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QWheelEvent
from PyQt6.QtWidgets import QGraphicsView


class PageView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.2 if delta > 0 else 1 / 1.2
            self.zoom_by(factor)
            event.accept()
            return
        super().wheelEvent(event)

    def zoom_by(self, factor: float) -> None:
        new_zoom = self._zoom * factor
        new_zoom = max(0.1, min(new_zoom, 8.0))
        factor = new_zoom / self._zoom
        self._zoom = new_zoom
        self.scale(factor, factor)

    def fit_width(self) -> None:
        rect = self.scene().itemsBoundingRect() if self.scene() else None
        if rect is None or rect.isEmpty():
            return
        viewport_w = self.viewport().width()
        if viewport_w < 50:
            QTimer.singleShot(0, self.fit_width)
            return
        self.resetTransform()
        self._zoom = 1.0
        if rect.width() > 0:
            factor = (viewport_w - 24) / rect.width()
            self.scale(factor, factor)
            self._zoom = factor
        self.centerOn(rect.center().x(), rect.top() + self.viewport().height() / (2 * self._zoom))
