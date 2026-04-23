from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


DEFAULT_FALLBACK = "Serif"


class TypedSignatureWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, cursive_families: list[str], parent=None):
        super().__init__(parent)
        self.cursive_families = cursive_families or [DEFAULT_FALLBACK]

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Type your signature")
        self.font_combo = QComboBox()
        for family in self.cursive_families:
            self.font_combo.addItem(family)

        self.preview = _TypedPreview(self.cursive_families[0])
        self.preview.setMinimumHeight(180)
        self.preview.setStyleSheet("background: white; border: 1px solid #bbb;")

        top = QHBoxLayout()
        top.addWidget(QLabel("Text:"))
        top.addWidget(self.text_edit, stretch=1)
        top.addWidget(QLabel("Font:"))
        top.addWidget(self.font_combo)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.preview, stretch=1)

        self.text_edit.textChanged.connect(self._on_changed)
        self.font_combo.currentTextChanged.connect(self._on_changed)
        self._on_changed()

    def _on_changed(self) -> None:
        self.preview.set_text(self.text_edit.text())
        self.preview.set_family(self.font_combo.currentText())
        self.changed.emit()

    def is_valid(self) -> bool:
        return bool(self.text_edit.text().strip())

    def current_family(self) -> str:
        return self.font_combo.currentText() or DEFAULT_FALLBACK

    def current_text(self) -> str:
        return self.text_edit.text().strip()

    def render_to_png_bytes(self, target_height_px: int = 220) -> bytes:
        text = self.current_text()
        family = self.current_family()
        if not text:
            raise ValueError("No text to render")

        font = QFont(family)
        font.setPointSizeF(72.0)
        metrics = QFontMetricsF(font)
        ratio = target_height_px / max(metrics.height(), 1.0)
        font.setPointSizeF(72.0 * ratio)
        metrics = QFontMetricsF(font)
        bbox = metrics.tightBoundingRect(text)

        pad = 16
        w = max(1, int(bbox.width() + pad * 2))
        h = max(1, int(metrics.height() + pad * 2))
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        baseline = pad + metrics.ascent()
        painter.drawText(int(pad - bbox.left()), int(baseline), text)
        painter.end()

        from ..util.image_utils import qimage_to_png_bytes
        return qimage_to_png_bytes(img)


class _TypedPreview(QWidget):
    def __init__(self, family: str):
        super().__init__()
        self._text = ""
        self._family = family

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def set_family(self, family: str) -> None:
        self._family = family or DEFAULT_FALLBACK
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        if not self._text:
            return
        font = QFont(self._family)
        font.setPointSizeF(48.0)
        metrics = QFontMetricsF(font)
        ratio = (self.height() - 20) / max(metrics.height(), 1.0)
        font.setPointSizeF(max(12.0, 48.0 * ratio))
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self._text)
