from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models.signature import SignatureStore


class SignatureSidebar(QDockWidget):
    sign_requested = pyqtSignal(str)
    new_requested = pyqtSignal()
    manage_requested = pyqtSignal()

    def __init__(self, store: SignatureStore, parent=None):
        super().__init__("Signatures", parent)
        self.store = store
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable)

        self.list = QListWidget()
        self.list.setIconSize(QSize(180, 72))
        self.list.itemDoubleClicked.connect(self._on_double_clicked)

        self.btn_sign = QPushButton("Sign with selected")
        self.btn_new = QPushButton("New…")
        self.btn_default = QPushButton("Set default")
        self.btn_rename = QPushButton("Rename")
        self.btn_delete = QPushButton("Delete")

        self.btn_sign.clicked.connect(self._on_sign_clicked)
        self.btn_new.clicked.connect(self.new_requested.emit)
        self.btn_default.clicked.connect(self._on_set_default)
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_delete.clicked.connect(self._on_delete)

        row1 = QHBoxLayout()
        row1.addWidget(self.btn_sign)
        row1.addWidget(self.btn_new)
        row2 = QHBoxLayout()
        row2.addWidget(self.btn_default)
        row2.addWidget(self.btn_rename)
        row2.addWidget(self.btn_delete)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.list, stretch=1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        self.setWidget(body)

        self.refresh()

    def focus_list(self) -> None:
        self.list.setFocus()
        if self.list.count() > 0 and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def refresh(self) -> None:
        self.list.clear()
        for sig in self.store.all():
            pixmap = QPixmap(str(self.store.path_for(sig)))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    180, 72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            icon = QIcon(pixmap) if not pixmap.isNull() else QIcon()
            label = sig.name + ("  (default)" if sig.is_default else "")
            item = QListWidgetItem(icon, label)
            item.setData(Qt.ItemDataRole.UserRole, sig.id)
            self.list.addItem(item)

    def _current_sig_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        sig_id = item.data(Qt.ItemDataRole.UserRole)
        if sig_id:
            self.sign_requested.emit(sig_id)

    def _on_sign_clicked(self) -> None:
        sig_id = self._current_sig_id()
        if sig_id is None:
            default = self.store.default()
            if default is not None:
                sig_id = default.id
        if sig_id is None:
            QMessageBox.information(self, "Sign", "No signatures available. Create one first.")
            return
        self.sign_requested.emit(sig_id)

    def _on_set_default(self) -> None:
        sig_id = self._current_sig_id()
        if sig_id is None:
            return
        self.store.set_default(sig_id)
        self.refresh()

    def _on_rename(self) -> None:
        sig_id = self._current_sig_id()
        if sig_id is None:
            return
        sig = self.store.get(sig_id)
        if sig is None:
            return
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=sig.name)
        if ok and new_name.strip():
            self.store.rename(sig_id, new_name.strip())
            self.refresh()

    def _on_delete(self) -> None:
        sig_id = self._current_sig_id()
        if sig_id is None:
            return
        sig = self.store.get(sig_id)
        if sig is None:
            return
        resp = QMessageBox.question(
            self,
            "Delete",
            f"Delete signature '{sig.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.store.delete(sig_id)
            self.refresh()
