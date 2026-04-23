"""End-to-end test of the signing flow through the real UI objects.

Simulates the user flow that was broken:
  begin_signing -> reposition/resize placement item -> click Save
WITHOUT pressing Enter. Verifies the signature ends up in the saved PDF.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fitz  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from PyQt6.QtCore import QPointF, QThreadPool  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from preview_app.models.document import DocumentRef  # noqa: E402
from preview_app.ui.document_tab import DocumentTab  # noqa: E402


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 100), "Document to be signed", fontsize=14)
    doc.save(str(path))
    doc.close()


def make_signature_png(path: Path) -> None:
    img = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(10, 80), (90, 20), (180, 60), (260, 30)], fill=(0, 0, 0, 255), width=4)
    img.save(str(path), "PNG")


def count_images_on_page(path: Path, page_index: int = 0) -> int:
    doc = fitz.open(str(path))
    n = len(doc.load_page(page_index).get_images(full=True))
    doc.close()
    return n


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="sign_flow_"))
    pdf = tmpdir / "doc.pdf"
    sig = tmpdir / "sig.png"
    make_pdf(pdf)
    make_signature_png(sig)
    print(f"[setup] {pdf} and {sig}")

    qapp = QApplication.instance() or QApplication([])
    tab = DocumentTab(DocumentRef.from_path(pdf), cursive_families=[])
    qapp.processEvents()
    QThreadPool.globalInstance().waitForDone(10000)
    qapp.processEvents()

    # Begin signing
    tab.begin_signing(sig)
    qapp.processEvents()
    placements = tab.scene.pending_placements()
    assert len(placements) == 1, "expected one pending placement"
    item = placements[0]
    print(f"[1] placement at {item.pos().x():.0f},{item.pos().y():.0f}")

    # User moves it
    item.setPos(QPointF(120, 800))
    item._signals.geometry_changed.emit()
    qapp.processEvents()
    print(f"[2] moved to {item.pos().x():.0f},{item.pos().y():.0f}")

    # User DOES NOT press Enter. They click Save As.
    signed_path = tmpdir / "signed.pdf"
    tab.save_as(str(signed_path))
    qapp.processEvents()

    assert signed_path.exists(), "save_as did not produce a file"
    n_imgs = count_images_on_page(signed_path)
    print(f"[3] images on page after Save As (no Enter): {n_imgs}")
    assert n_imgs >= 1, "signature was NOT stamped into the PDF"

    # Also test Save (incremental)
    tab2 = DocumentTab(DocumentRef.from_path(pdf), cursive_families=[])
    qapp.processEvents()
    QThreadPool.globalInstance().waitForDone(10000)
    qapp.processEvents()
    tab2.begin_signing(sig)
    qapp.processEvents()
    p2 = tab2.scene.pending_placements()[0]
    p2.setPos(QPointF(200, 700))
    p2._signals.geometry_changed.emit()
    qapp.processEvents()
    tab2.save_in_place()
    qapp.processEvents()
    n_imgs2 = count_images_on_page(pdf)
    print(f"[4] images on page after Save in-place (no Enter): {n_imgs2}")
    assert n_imgs2 >= 1, "Save-in-place did NOT stamp signature"

    # Third case: click the Apply button on the floating toolbar via QTest
    # (the real path that segfaulted earlier).
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QPushButton

    pdf3 = tmpdir / "doc3.pdf"
    make_pdf(pdf3)
    tab3 = DocumentTab(DocumentRef.from_path(pdf3), cursive_families=[])
    qapp.processEvents()
    QThreadPool.globalInstance().waitForDone(10000)
    qapp.processEvents()
    tab3.begin_signing(sig)
    qapp.processEvents()

    item3 = tab3.scene.pending_placements()[0]
    proxy = tab3.scene._placement_bars[item3]
    widget = proxy.widget()
    btn_apply = None
    for child in widget.findChildren(QPushButton):
        if child.text() == "Apply":
            btn_apply = child
            break
    assert btn_apply is not None, "could not locate Apply button"
    QTest.mouseClick(btn_apply, Qt.MouseButton.LeftButton)
    # Allow deferred QTimer.singleShot to fire
    for _ in range(10):
        qapp.processEvents()

    n_imgs3 = count_images_on_page(pdf3)
    print(f"[5] images after QTest-click of Apply + save_in_place:")
    tab3.save_in_place()
    qapp.processEvents()
    n_imgs3_after = count_images_on_page(pdf3)
    print(f"    before save={n_imgs3}, after save={n_imgs3_after}")
    assert n_imgs3_after >= 1, "Apply button click did not stamp signature"

    print("SIGNING FLOW FIX CONFIRMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
