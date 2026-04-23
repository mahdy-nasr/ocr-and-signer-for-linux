from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.image_doc import ImageDoc
from ..core.pdf_doc import PdfDoc
from ..core.selection import assemble_text
from ..core.signer import apply_signature, save_as as _save_as, save_incremental
from ..models.document import DocKind, DocumentRef
from ..util.image_utils import pil_to_qpixmap
from .ocr_worker import OcrWorker
from .page_scene import PageScene
from .page_view import PageView
from .sign_placement import SignPlacementItem


DEFAULT_DPI = 144


class DocumentTab(QWidget):
    selection_changed = pyqtSignal()

    def __init__(self, ref: DocumentRef, cursive_families: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.ref = ref
        self.cursive_families = cursive_families
        self.dpi = DEFAULT_DPI
        self.page_index = 0
        self.mode: str = "text"

        self._thread_pool = QThreadPool.globalInstance()
        self._pending_placement: Path | None = None

        if ref.kind == DocKind.PDF:
            self.doc = PdfDoc(ref.path)
            if self.doc.is_encrypted():
                QMessageBox.warning(self, "Encrypted PDF", "Password-protected PDFs are not supported yet.")
                raise RuntimeError("encrypted pdf")
        else:
            self.doc = ImageDoc.open(ref.path)

        self.scene = PageScene()
        self.scene.rect_selection_finalized.connect(self._on_rect_selection)
        self.view = PageView(self.scene)

        self.mode_label = QLabel()
        self.mode_label.setStyleSheet(
            "QLabel { padding: 2px 8px; border-radius: 8px; background: #eef; color: #224; }"
        )
        self.page_label = QLabel("Page 1 / 1")
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.btn_prev.setFixedWidth(36)
        self.btn_next.setFixedWidth(36)
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.btn_prev)
        top_bar.addWidget(self.page_label)
        top_bar.addWidget(self.btn_next)
        top_bar.addStretch(1)
        top_bar.addWidget(self.mode_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.addLayout(top_bar)
        root.addWidget(self.view, stretch=1)

        self._load_page()

    # ---- page management ----
    def _load_page(self) -> None:
        render = self.doc.render_page(self.page_index, self.dpi)
        pixmap = pil_to_qpixmap(render.image)
        self.scene.set_page_pixmap(pixmap)
        self._pil_image = render.image
        self.view.fit_width()

        self.page_label.setText(f"Page {self.page_index + 1} / {self.doc.page_count}")
        self.btn_prev.setEnabled(self.page_index > 0)
        self.btn_next.setEnabled(self.page_index < self.doc.page_count - 1)

        mode = self.doc.detect_mode(self.page_index)
        self.mode_label.setText("Text layer" if mode == "text" else "OCR…")

        worker = OcrWorker(self.doc, self.page_index, self.dpi)
        worker.signals.finished.connect(self._on_words_ready)
        self._thread_pool.start(worker)

    def _on_words_ready(self, page_index: int, words_id: int, words: list) -> None:
        if page_index != self.page_index:
            return
        self.scene.set_words(words)
        mode = self.doc.detect_mode(page_index)
        if mode == "text":
            self.mode_label.setText("Text layer")
        elif words:
            self.mode_label.setText(f"OCR ({len(words)} words)")
        else:
            self.mode_label.setText("OCR — no text found")

    def _prev_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self._load_page()

    def _next_page(self) -> None:
        if self.page_index < self.doc.page_count - 1:
            self.page_index += 1
            self._load_page()

    # ---- mode / zoom ----
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.scene.set_selection_mode(mode)

    def zoom_in(self) -> None:
        self.view.zoom_by(1.25)

    def zoom_out(self) -> None:
        self.view.zoom_by(1 / 1.25)

    def fit_width(self) -> None:
        self.view.fit_width()

    # ---- copy ----
    def copy_selection(self) -> None:
        words = self.scene.selected_words()
        clipboard = QApplication.clipboard()
        if words:
            clipboard.setText(assemble_text(words))
            return
        rect = self.scene.selected_rect_px()
        if rect is not None:
            x0, y0, x1, y1 = rect
            cropped = self._pil_image.crop((int(x0), int(y0), int(x1), int(y1)))
            qimg = _pil_to_qimage(cropped)
            clipboard.setImage(qimg)

    # ---- rect selection ----
    def _on_rect_selection(self, rect: tuple[float, float, float, float]) -> None:
        self.scene.show_rect_actions(
            on_copy=lambda: self._copy_rect(rect),
            on_save=lambda: self._save_rect(rect),
        )

    def _copy_rect(self, rect: tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = (int(v) for v in rect)
        cropped = self._pil_image.crop((x0, y0, x1, y1))
        qimg = _pil_to_qimage(cropped)
        QApplication.clipboard().setImage(qimg)

    def _save_rect(self, rect: tuple[float, float, float, float]) -> None:
        from PyQt6.QtWidgets import QFileDialog

        x0, y0, x1, y1 = (int(v) for v in rect)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save region as PNG",
            str(self.ref.path.parent / "region.png"),
            "PNG (*.png)",
        )
        if not filename:
            return
        cropped = self._pil_image.crop((x0, y0, x1, y1))
        cropped.save(filename, "PNG")

    # ---- signing ----
    def begin_signing(self, signature_png: Path) -> None:
        if self.ref.kind != DocKind.PDF:
            return
        pixmap = QPixmap(str(signature_png))
        if pixmap.isNull():
            QMessageBox.warning(self, "Sign", "Could not load signature image.")
            return
        target_h = int(self.scene.page_height_px() * 0.12)
        scaled = pixmap.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)
        item = SignPlacementItem(scaled, signature_png)
        initial_x = self.scene.page_width_px() * 0.5 - scaled.width() / 2
        initial_y = self.scene.page_height_px() * 0.75
        item.setPos(initial_x, initial_y)
        item.confirmed.connect(self._confirm_placement)
        item.cancelled.connect(self._cancel_placement)
        self.scene.add_placement_item(item)
        self._pending_placement = signature_png

    def _confirm_placement(self, item: SignPlacementItem) -> None:
        rect = item.target_rect_px()
        signature_png = item.signature_path
        try:
            apply_signature(self.doc, self.page_index, signature_png, rect, self.dpi)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Sign", f"Failed to stamp signature:\n{e}")
            return
        self.scene.remove_placement_item(item)
        self._pending_placement = None
        self._reload_current_page()

    def _cancel_placement(self, item: SignPlacementItem) -> None:
        self.scene.remove_placement_item(item)
        self._pending_placement = None

    def _reload_current_page(self) -> None:
        if isinstance(self.doc, PdfDoc):
            self.doc.invalidate_caches()
        self._load_page()

    # ---- save ----
    def _commit_pending_placements(self) -> None:
        for item in self.scene.pending_placements():
            self._confirm_placement(item)

    def save_in_place(self) -> None:
        if self.ref.kind != DocKind.PDF:
            return
        self._commit_pending_placements()
        save_incremental(self.doc)  # type: ignore[arg-type]

    def save_as(self, path: str) -> None:
        if self.ref.kind != DocKind.PDF:
            return
        self._commit_pending_placements()
        new_path = _save_as(self.doc, path)  # type: ignore[arg-type]
        if isinstance(self.doc, PdfDoc):
            self.doc.close()
            self.doc = PdfDoc(new_path)
            self.ref = DocumentRef(path=Path(new_path), kind=DocKind.PDF)
            self._load_page()

    def close_doc(self) -> None:
        try:
            self.doc.close()
        except Exception:  # noqa: BLE001
            pass


def _pil_to_qimage(pil_image):
    pil_image = pil_image.convert("RGBA") if pil_image.mode != "RGBA" else pil_image
    data = pil_image.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
    return qimg.copy()
