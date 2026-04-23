from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..core.ocr import Word
from .rubberband_tool import RubberBandItem
from .selection_overlay import SelectionOverlayItem
from .sign_placement import SignPlacementItem


class PageScene(QGraphicsScene):
    rect_selection_finalized = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.overlay: SelectionOverlayItem | None = None
        self.rubberband: RubberBandItem | None = None
        self.rect_actions_proxy: QGraphicsProxyWidget | None = None
        self._mode = "text"
        self._placements: list[SignPlacementItem] = []
        self._placement_bars: dict[SignPlacementItem, QGraphicsProxyWidget] = {}

    def set_page_pixmap(self, pixmap: QPixmap) -> None:
        self.clear()
        self._placements = []
        self._placement_bars = {}
        self.rect_actions_proxy = None

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.addItem(self.pixmap_item)
        self.setSceneRect(QRectF(pixmap.rect()))

        self.overlay = SelectionOverlayItem(pixmap.width(), pixmap.height())
        self.addItem(self.overlay)
        self.overlay.setZValue(10)

        self.rubberband = RubberBandItem(pixmap.width(), pixmap.height())
        self.rubberband.finalized.connect(self._on_rubberband_finalized)
        self.addItem(self.rubberband)
        self.rubberband.setZValue(20)

        self._apply_mode()

    def set_words(self, words: list[Word]) -> None:
        if self.overlay is not None:
            self.overlay.set_words(words)

    def set_selection_mode(self, mode: str) -> None:
        self._mode = mode
        self._apply_mode()

    def _apply_mode(self) -> None:
        if self.overlay is None or self.rubberband is None:
            return
        if self._mode == "text":
            self.overlay.setEnabled(True)
            self.overlay.setVisible(True)
            self.rubberband.setEnabled(False)
            self.rubberband.setVisible(False)
            self.rubberband.clear()
            self.hide_rect_actions()
        else:
            self.overlay.clear_selection()
            self.overlay.setEnabled(False)
            self.overlay.setVisible(False)
            self.rubberband.setEnabled(True)
            self.rubberband.setVisible(True)
            self.rubberband.clear()

    def page_width_px(self) -> float:
        if self.pixmap_item is None:
            return 0.0
        return float(self.pixmap_item.pixmap().width())

    def page_height_px(self) -> float:
        if self.pixmap_item is None:
            return 0.0
        return float(self.pixmap_item.pixmap().height())

    def selected_words(self) -> list[Word]:
        if self.overlay is None:
            return []
        return self.overlay.selected_words()

    def selected_rect_px(self) -> tuple[float, float, float, float] | None:
        if self.rubberband is None:
            return None
        return self.rubberband.final_rect()

    def _on_rubberband_finalized(self, x0, y0, x1, y1):
        rect = (float(x0), float(y0), float(x1), float(y1))
        self.rect_selection_finalized.emit(rect)

    def show_rect_actions(self, on_copy: Callable[[], None], on_save: Callable[[], None]) -> None:
        self.hide_rect_actions()
        if self.rubberband is None:
            return
        rect = self.rubberband.final_rect()
        if rect is None:
            return

        widget = QWidget()
        widget.setStyleSheet("QWidget { background: #222; border-radius: 6px; }"
                             "QPushButton { color: white; padding: 4px 10px; border: none; }")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        btn_copy = QPushButton("Copy")
        btn_save = QPushButton("Save as PNG…")

        def _run_copy():
            on_copy()
            self.hide_rect_actions()

        def _run_save():
            on_save()
            self.hide_rect_actions()

        # Defer so the click handler returns before the proxy is removed.
        btn_copy.clicked.connect(lambda _=False: QTimer.singleShot(0, _run_copy))
        btn_save.clicked.connect(lambda _=False: QTimer.singleShot(0, _run_save))
        layout.addWidget(btn_copy)
        layout.addWidget(btn_save)

        proxy = self.addWidget(widget)
        proxy.setZValue(30)
        x0, y0, x1, y1 = rect
        widget.adjustSize()
        proxy.setPos(x0, y1 + 8)
        self.rect_actions_proxy = proxy

    def hide_rect_actions(self) -> None:
        if self.rect_actions_proxy is not None:
            self.removeItem(self.rect_actions_proxy)
            self.rect_actions_proxy = None

    def add_placement_item(self, item: SignPlacementItem) -> None:
        self.addItem(item)
        item.setZValue(40)
        self._placements.append(item)
        if self.overlay is not None:
            self.overlay.setEnabled(False)
        if self.rubberband is not None:
            self.rubberband.setEnabled(False)
        item.setSelected(True)
        item.setFocus()
        self._show_placement_bar(item)
        item.geometry_changed.connect(lambda it=item: self._reposition_placement_bar(it))

    def _show_placement_bar(self, item: SignPlacementItem) -> None:
        widget = QWidget()
        widget.setStyleSheet(
            "QWidget { background: #222; border-radius: 6px; }"
            "QLabel { color: white; padding: 2px 6px; }"
            "QPushButton { color: white; padding: 4px 10px; border: none; }"
            "QPushButton:hover { background: #444; }"
        )
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        hint = QLabel("Drag to move, corner handle to resize")
        btn_apply = QPushButton("Apply")
        btn_cancel = QPushButton("Cancel")
        btn_apply.setDefault(True)
        # Defer confirm/cancel so the click handler returns before the proxy
        # (which owns these buttons) is removed from the scene.
        btn_apply.clicked.connect(lambda _=False, it=item: QTimer.singleShot(0, it.confirm))
        btn_cancel.clicked.connect(lambda _=False, it=item: QTimer.singleShot(0, it.cancel))
        layout.addWidget(hint)
        layout.addWidget(btn_apply)
        layout.addWidget(btn_cancel)

        proxy = self.addWidget(widget)
        proxy.setZValue(50)
        self._placement_bars[item] = proxy
        self._reposition_placement_bar(item)

    def _reposition_placement_bar(self, item: SignPlacementItem) -> None:
        proxy = self._placement_bars.get(item)
        if proxy is None:
            return
        widget = proxy.widget()
        if widget is not None:
            widget.adjustSize()
        rect = item.sceneBoundingRect()
        proxy.setPos(rect.left(), rect.bottom() + 6)

    def remove_placement_item(self, item: SignPlacementItem) -> None:
        if item in self._placements:
            self._placements.remove(item)
        proxy = self._placement_bars.pop(item, None)
        if proxy is not None and proxy.scene() is self:
            self.removeItem(proxy)
        if item.scene() is self:
            self.removeItem(item)
        if not self._placements:
            self._apply_mode()

    def pending_placements(self) -> list[SignPlacementItem]:
        return list(self._placements)
