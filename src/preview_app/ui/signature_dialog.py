from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models.signature import SignatureStore
from .draw_canvas import DrawCanvas
from .typed_signature_widget import TypedSignatureWidget


class SignatureDialog(QDialog):
    def __init__(
        self,
        store: SignatureStore,
        cursive_families: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("New Signature")
        self.resize(720, 420)
        self.store = store

        self.tabs = QTabWidget()
        self.draw_tab = _DrawTab()
        self.type_tab = TypedSignatureWidget(cursive_families)
        self.tabs.addTab(self.draw_tab, "Draw")
        self.tabs.addTab(self.type_tab, "Type")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Signature name (e.g. 'Main')")
        self.default_checkbox = QCheckBox("Set as default")

        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("Name:"))
        meta_row.addWidget(self.name_edit, stretch=1)
        meta_row.addWidget(self.default_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(self.tabs, stretch=1)
        root.addLayout(meta_row)
        root.addWidget(buttons)

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save", "Please enter a name.")
            return
        is_default = self.default_checkbox.isChecked()

        if self.tabs.currentWidget() is self.draw_tab:
            canvas = self.draw_tab.canvas
            if canvas.is_empty():
                QMessageBox.warning(self, "Save", "Draw something first.")
                return
            try:
                png_bytes = canvas.render_to_png_bytes()
            except ValueError as e:
                QMessageBox.warning(self, "Save", str(e))
                return
            self.store.add(name, "drawn", png_bytes, is_default=is_default)
        else:
            widget = self.type_tab
            if not widget.is_valid():
                QMessageBox.warning(self, "Save", "Enter the text to type.")
                return
            png_bytes = widget.render_to_png_bytes()
            meta = {"font_family": widget.current_family(), "text": widget.current_text()}
            self.store.add(name, "typed", png_bytes, is_default=is_default, meta=meta)

        self.accept()


class _DrawTab(QWidget):
    def __init__(self):
        super().__init__()
        self.canvas = DrawCanvas()

        btn_clear = QPushButton("Clear")
        btn_undo = QPushButton("Undo")
        btn_color_black = QPushButton("Black")
        btn_color_blue = QPushButton("Blue")
        thickness = QDoubleSpinBox()
        thickness.setRange(0.5, 8.0)
        thickness.setSingleStep(0.5)
        thickness.setValue(2.4)

        btn_clear.clicked.connect(self.canvas.clear)
        btn_undo.clicked.connect(self.canvas.undo)
        btn_color_black.clicked.connect(lambda: self.canvas.set_color(QColor(0, 0, 0)))
        btn_color_blue.clicked.connect(lambda: self.canvas.set_color(QColor(20, 60, 180)))
        thickness.valueChanged.connect(self.canvas.set_thickness)

        controls = QHBoxLayout()
        controls.addWidget(btn_clear)
        controls.addWidget(btn_undo)
        controls.addSpacing(12)
        controls.addWidget(QLabel("Color:"))
        controls.addWidget(btn_color_black)
        controls.addWidget(btn_color_blue)
        controls.addSpacing(12)
        controls.addWidget(QLabel("Thickness:"))
        controls.addWidget(thickness)
        controls.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(controls)
        root.addWidget(self.canvas, stretch=1)
