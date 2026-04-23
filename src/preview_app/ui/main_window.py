from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from .. import config
from ..models.document import DocKind, DocumentRef
from ..models.signature import SignatureStore
from .document_tab import DocumentTab
from .signature_dialog import SignatureDialog
from .signature_sidebar import SignatureSidebar


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
PDF_EXTS = {".pdf"}
ALL_EXTS = IMAGE_EXTS | PDF_EXTS


class MainWindow(QMainWindow):
    def __init__(self, cursive_families: list[str]):
        super().__init__()
        self.setWindowTitle("Preview App")
        self.resize(1200, 820)

        self.cursive_families = cursive_families
        self.signature_store = SignatureStore(config.signatures_dir())

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.signature_sidebar = SignatureSidebar(self.signature_store, self)
        self.signature_sidebar.sign_requested.connect(self._sign_with)
        self.signature_sidebar.new_requested.connect(self._new_signature)
        self.signature_sidebar.manage_requested.connect(self._manage_signatures)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.signature_sidebar)
        self.signature_sidebar.hide()

        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self.act_open = QAction("&Open…", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_dialog)
        file_menu.addAction(self.act_open)

        self.act_save = QAction("&Save", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save)
        file_menu.addAction(self.act_save)

        self.act_save_as = QAction("Save &As…", self)
        self.act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.act_save_as.triggered.connect(self._save_as)
        file_menu.addAction(self.act_save_as)

        file_menu.addSeparator()
        self.act_close = QAction("&Close Tab", self)
        self.act_close.setShortcut(QKeySequence("Ctrl+W"))
        self.act_close.triggered.connect(self._close_current_tab)
        file_menu.addAction(self.act_close)

        self.act_quit = QAction("&Quit", self)
        self.act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_quit.triggered.connect(self.close)
        file_menu.addAction(self.act_quit)

        edit_menu = menubar.addMenu("&Edit")
        self.act_copy = QAction("&Copy", self)
        self.act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.act_copy.triggered.connect(self._copy)
        edit_menu.addAction(self.act_copy)

        view_menu = menubar.addMenu("&View")
        self.act_zoom_in = QAction("Zoom &In", self)
        self.act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        self.act_zoom_in.triggered.connect(lambda: self._active_tab_do("zoom_in"))
        view_menu.addAction(self.act_zoom_in)

        self.act_zoom_out = QAction("Zoom &Out", self)
        self.act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.act_zoom_out.triggered.connect(lambda: self._active_tab_do("zoom_out"))
        view_menu.addAction(self.act_zoom_out)

        self.act_fit = QAction("&Fit Width", self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.triggered.connect(lambda: self._active_tab_do("fit_width"))
        view_menu.addAction(self.act_fit)

        view_menu.addSeparator()
        self.act_text_mode = QAction("&Text Select Mode", self)
        self.act_text_mode.setShortcut(QKeySequence("V"))
        self.act_text_mode.setCheckable(True)
        self.act_text_mode.setChecked(True)
        self.act_text_mode.triggered.connect(lambda: self._set_mode("text"))
        view_menu.addAction(self.act_text_mode)

        self.act_rect_mode = QAction("&Rect Select Mode", self)
        self.act_rect_mode.setShortcut(QKeySequence("R"))
        self.act_rect_mode.setCheckable(True)
        self.act_rect_mode.triggered.connect(lambda: self._set_mode("rect"))
        view_menu.addAction(self.act_rect_mode)

        view_menu.addSeparator()
        self.act_toggle_sigs = QAction("&Signatures Panel", self)
        self.act_toggle_sigs.setCheckable(True)
        self.act_toggle_sigs.triggered.connect(self._toggle_sigs)
        view_menu.addAction(self.act_toggle_sigs)

        tools_menu = menubar.addMenu("&Tools")
        self.act_new_sig = QAction("&New Signature…", self)
        self.act_new_sig.triggered.connect(self._new_signature)
        tools_menu.addAction(self.act_new_sig)

        self.act_manage_sigs = QAction("&Manage Signatures…", self)
        self.act_manage_sigs.triggered.connect(self._manage_signatures)
        tools_menu.addAction(self.act_manage_sigs)

        tools_menu.addSeparator()
        self.act_export_sigs = QAction("&Export Signatures…", self)
        self.act_export_sigs.triggered.connect(self._export_signatures)
        tools_menu.addAction(self.act_export_sigs)

        self.act_import_sigs = QAction("&Import Signatures…", self)
        self.act_import_sigs.triggered.connect(self._import_signatures)
        tools_menu.addAction(self.act_import_sigs)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_text_mode)
        tb.addAction(self.act_rect_mode)
        tb.addSeparator()
        tb.addAction(self.act_zoom_out)
        tb.addAction(self.act_zoom_in)
        tb.addAction(self.act_fit)
        tb.addSeparator()
        tb.addAction(self.act_new_sig)
        tb.addAction(self.act_toggle_sigs)

    def _current_tab(self) -> DocumentTab | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, DocumentTab) else None

    def _active_tab_do(self, method: str) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        fn = getattr(tab, method, None)
        if callable(fn):
            fn()

    def _set_mode(self, mode: str) -> None:
        self.act_text_mode.setChecked(mode == "text")
        self.act_rect_mode.setChecked(mode == "rect")
        tab = self._current_tab()
        if tab is not None:
            tab.set_mode(mode)

    def _copy(self) -> None:
        tab = self._current_tab()
        if tab is not None:
            tab.copy_selection()

    def _toggle_sigs(self) -> None:
        if self.signature_sidebar.isVisible():
            self.signature_sidebar.hide()
            self.act_toggle_sigs.setChecked(False)
        else:
            self.signature_sidebar.show()
            self.act_toggle_sigs.setChecked(True)

    def _open_dialog(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(ALL_EXTS))
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open",
            str(Path.home()),
            f"Images and PDFs ({patterns});;All files (*)",
        )
        if filename:
            self.open_path(filename)

    def open_path(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            QMessageBox.warning(self, "Open", f"File not found:\n{p}")
            return
        if p.suffix.lower() not in ALL_EXTS:
            QMessageBox.warning(self, "Open", f"Unsupported file type: {p.suffix}")
            return
        ref = DocumentRef.from_path(p)
        try:
            tab = DocumentTab(ref, cursive_families=self.cursive_families, parent=self)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Open", f"Failed to open:\n{e}")
            return
        tab.selection_changed.connect(self._on_selection_changed)
        idx = self.tabs.addTab(tab, p.name)
        self.tabs.setCurrentIndex(idx)

    def _close_current_tab(self) -> None:
        idx = self.tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def _close_tab(self, idx: int) -> None:
        w = self.tabs.widget(idx)
        if isinstance(w, DocumentTab):
            w.close_doc()
        self.tabs.removeTab(idx)

    def _on_tab_changed(self, idx: int) -> None:
        tab = self._current_tab()
        is_pdf = isinstance(tab, DocumentTab) and tab.ref.kind == DocKind.PDF
        if is_pdf:
            self.signature_sidebar.show()
            self.act_toggle_sigs.setChecked(True)
        else:
            self.signature_sidebar.hide()
            self.act_toggle_sigs.setChecked(False)

    def _on_selection_changed(self) -> None:
        pass

    def _save(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        try:
            tab.save_in_place()
            self.statusBar().showMessage(f"Saved: {tab.ref.path}", 3000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save", f"Failed to save:\n{e}")

    def _save_as(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        default = str(tab.ref.path.with_stem(tab.ref.path.stem + "-signed"))
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save As", default, "PDF files (*.pdf)"
        )
        if not filename:
            return
        try:
            tab.save_as(filename)
            self.statusBar().showMessage(f"Saved: {filename}", 3000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save As", f"Failed to save:\n{e}")

    def _sign_with(self, sig_id: str) -> None:
        tab = self._current_tab()
        if tab is None or tab.ref.kind != DocKind.PDF:
            QMessageBox.information(self, "Sign", "Open a PDF to sign.")
            return
        sig = self.signature_store.get(sig_id)
        if sig is None:
            return
        png_path = self.signature_store.path_for(sig)
        tab.begin_signing(png_path)

    def _new_signature(self) -> None:
        dialog = SignatureDialog(
            self.signature_store,
            cursive_families=self.cursive_families,
            parent=self,
        )
        if getattr(dialog, "exec")():
            self.signature_sidebar.refresh()

    def _manage_signatures(self) -> None:
        self.signature_sidebar.show()
        self.act_toggle_sigs.setChecked(True)
        self.signature_sidebar.focus_list()

    def _export_signatures(self) -> None:
        if not self.signature_store.all():
            QMessageBox.information(self, "Export", "You have no signatures to export.")
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        default = str(Path.home() / f"signatures-{stamp}.zip")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Signatures", default, "Zip archive (*.zip)"
        )
        if not filename:
            return
        try:
            out = self.signature_store.export_zip(filename)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Export", f"Failed to export:\n{e}")
            return
        self.statusBar().showMessage(f"Exported: {out}", 4000)

    def _import_signatures(self) -> None:
        choice = QMessageBox.question(
            self,
            "Import Signatures",
            "Import from a zip file or from a folder?\n\n"
            "Yes = pick a zip file\nNo = pick a folder",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return
        if choice == QMessageBox.StandardButton.Yes:
            source, _ = QFileDialog.getOpenFileName(
                self, "Import Signatures from Zip", str(Path.home()), "Zip archive (*.zip)"
            )
        else:
            source = QFileDialog.getExistingDirectory(
                self, "Import Signatures from Folder", str(Path.home())
            )
        if not source:
            return
        try:
            count = self.signature_store.import_from(source)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Import", f"Failed to import:\n{e}")
            return
        self.signature_sidebar.refresh()
        if count:
            self.statusBar().showMessage(f"Imported {count} signature(s)", 4000)
            self.signature_sidebar.show()
            self.act_toggle_sigs.setChecked(True)
        else:
            QMessageBox.information(
                self, "Import", "No signatures were found in the selected source."
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        for idx in range(self.tabs.count()):
            w = self.tabs.widget(idx)
            if isinstance(w, DocumentTab):
                w.close_doc()
        QThreadPool.globalInstance().waitForDone(2000)
        super().closeEvent(event)
