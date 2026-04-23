"""End-to-end smoke test — exercises the real code paths without a GUI."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PREVIEW_APP_SMOKE", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fitz  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from preview_app.core.image_doc import ImageDoc  # noqa: E402
from preview_app.core.pdf_doc import PdfDoc  # noqa: E402
from preview_app.core.selection import WordIndex, assemble_text  # noqa: E402
from preview_app.core.signer import apply_signature  # noqa: E402
from preview_app.models.signature import SignatureStore  # noqa: E402


def _make_sample_image(path: Path) -> None:
    img = Image.new("RGB", (800, 220), "white")
    draw = ImageDraw.Draw(img)
    font = None
    for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/freefont/FreeSans.ttf"):
        if os.path.exists(candidate):
            font = ImageFont.truetype(candidate, 36)
            break
    draw.text((20, 20), "Hello from preview app", fill="black", font=font)
    draw.text((20, 80), "OCR should pick up this text", fill="black", font=font)
    img.save(str(path), "PNG")


def _make_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 100), "Greenfield preview app test document", fontsize=14)
    page.insert_text((72, 130), "This is a born-digital PDF text layer.", fontsize=14)
    page.insert_text((72, 160), "A signature will be placed at the bottom.", fontsize=14)
    doc.save(str(path))
    doc.close()


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="preview_app_smoke_"))
    print(f"work dir: {tmpdir}")

    # 1. Image + OCR
    img_path = tmpdir / "sample.png"
    _make_sample_image(img_path)
    image_doc = ImageDoc.open(img_path)
    words = image_doc.words_for()
    assert words, "no OCR words detected"
    text = assemble_text(words)
    print(f"[image] {len(words)} words, text={text!r}")
    assert "Hello" in text, f"OCR missed 'Hello' in: {text}"

    # 2. WordIndex hit-testing
    idx = WordIndex(words)
    first = words[0]
    hit = idx.word_at(first.x + first.w / 2, first.y + first.h / 2)
    assert hit == 0, f"word_at should hit first word, got {hit}"
    last = idx.nearest_word(1e6, 1e6)
    assert last is not None
    sel = idx.range_between(0, last)
    assert len(sel) == len(words), "range_between(0, last) must cover everything"

    # 3. Text PDF
    pdf_path = tmpdir / "text.pdf"
    _make_sample_pdf(pdf_path)
    pdf = PdfDoc(pdf_path)
    assert pdf.page_count == 1
    mode = pdf.detect_mode(0)
    print(f"[pdf] mode={mode}")
    assert mode == "text", f"expected text mode, got {mode}"
    pdf_words = pdf.words_for(0)
    pdf_text = assemble_text(pdf_words)
    print(f"[pdf] {len(pdf_words)} words, first-line={pdf_text.splitlines()[0]!r}")
    assert "Greenfield" in pdf_text

    # 4. Signature store + drawn PNG
    store = SignatureStore(tmpdir / "sigs")
    # Fake a tiny signature PNG
    sig_png_bytes = b""
    sig_src = tmpdir / "sig_src.png"
    sig_img = Image.new("RGBA", (240, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(sig_img)
    d.line([(10, 60), (100, 20), (170, 50), (230, 30)], fill=(0, 0, 0, 255), width=4)
    sig_img.save(str(sig_src), "PNG")
    sig_png_bytes = sig_src.read_bytes()

    sig = store.add("Test", "drawn", sig_png_bytes, is_default=True)
    assert store.get(sig.id) is not None
    assert store.default().id == sig.id
    print(f"[sig] stored id={sig.id}, path={store.path_for(sig)}")

    # 5. Apply signature to PDF
    signed_dir = tmpdir / "out"
    signed_dir.mkdir()
    signed_path = signed_dir / "signed.pdf"
    apply_signature(
        pdf,
        page_index=0,
        signature_png=store.path_for(sig),
        rect_px=(200, 1300, 600, 1420),  # in 144-dpi pixel coords
        dpi=144,
    )
    pdf.save(signed_path)
    pdf.close()
    assert signed_path.exists() and signed_path.stat().st_size > 0
    # Re-open and confirm at least one image block was added
    verify = fitz.open(str(signed_path))
    imgs = verify.load_page(0).get_images(full=True)
    verify.close()
    print(f"[sign] images on page: {len(imgs)}")
    assert imgs, "signature image was not embedded"

    # 6. Main-window construction (Qt-level)
    from PyQt6.QtCore import QThreadPool
    from PyQt6.QtWidgets import QApplication
    from preview_app.ui.main_window import MainWindow
    qapp = QApplication.instance() or QApplication([])
    win = MainWindow(cursive_families=[])
    win.open_path(str(img_path))
    win.open_path(str(pdf_path))
    assert win.tabs.count() == 2
    qapp.processEvents()
    QThreadPool.globalInstance().waitForDone(10000)
    qapp.processEvents()
    print(f"[ui] opened {win.tabs.count()} tabs successfully")

    print("ALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
