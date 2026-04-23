"""Reproduce the 'cannot select text on JPG' issue.

Creates a JPG with text, runs the full UI pipeline (offscreen), and reports
where text selection goes wrong.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def make_jpg(path: Path) -> None:
    img = Image.new("RGB", (900, 260), "white")
    draw = ImageDraw.Draw(img)
    font = None
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSans.ttf"):
        if os.path.exists(p):
            font = ImageFont.truetype(p, 40)
            break
    draw.text((30, 30), "Selectable JPG text example", fill="black", font=font)
    draw.text((30, 110), "Second line of JPG text here", fill="black", font=font)
    img.save(str(path), "JPEG", quality=90)


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="jpg_repro_"))
    jpg = tmpdir / "sample.jpg"
    make_jpg(jpg)
    print(f"[1] made {jpg} ({jpg.stat().st_size} bytes)")

    from PyQt6.QtCore import QThreadPool
    from PyQt6.QtWidgets import QApplication

    from preview_app.core.image_doc import ImageDoc
    from preview_app.ui.document_tab import DocumentTab
    from preview_app.models.document import DocumentRef

    # direct OCR first, to rule in/out the core path
    doc = ImageDoc.open(jpg)
    words = doc.words_for()
    print(f"[2] direct OCR on JPG: {len(words)} words")
    for w in words[:4]:
        print(f"    {w.text!r} @ ({w.x:.0f},{w.y:.0f}) conf={w.conf}")

    # now the UI path
    qapp = QApplication.instance() or QApplication([])
    ref = DocumentRef.from_path(jpg)
    print(f"[3] DocumentRef kind={ref.kind}")
    tab = DocumentTab(ref, cursive_families=[])
    print(f"[4] tab created; mode_label={tab.mode_label.text()!r}")

    # pump events & wait for the worker
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.05)
    QThreadPool.globalInstance().waitForDone(10000)
    qapp.processEvents()
    qapp.processEvents()

    print(f"[5] after OCR done: mode_label={tab.mode_label.text()!r}")
    overlay = tab.scene.overlay
    if overlay is None:
        print("[6] FAIL: no overlay on scene")
        return 1
    n_words = len(overlay.words)
    has_index = overlay._index is not None
    print(f"[6] overlay.words={n_words}, overlay._index set={has_index}")
    if n_words == 0:
        print("    ^ overlay did not receive the OCR results: the bug is in the signal path")
        return 1

    # simulate a word hit
    if overlay._index is not None:
        w0 = overlay.words[0]
        hit = overlay._index.word_at(w0.x + w0.w / 2, w0.y + w0.h / 2)
        print(f"[7] hit-test at first word center -> {hit}")

    # Post real mouse events on the view at screen positions
    # for the first and last word, and verify selection occurs.
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtTest import QTest

    view = tab.view
    # Make sure the scene has a proper viewport first.
    view.resize(1000, 400)
    view.show()
    for _ in range(10):
        qapp.processEvents()

    w0 = overlay.words[0]
    w_last = overlay.words[-1]
    scene_start = QPointF(w0.x + w0.w / 2, w0.y + w0.h / 2)
    scene_end = QPointF(w_last.x + w_last.w / 2, w_last.y + w_last.h / 2)
    view_start = view.mapFromScene(scene_start)
    view_end = view.mapFromScene(scene_end)
    print(f"    scene_start={scene_start.x():.0f},{scene_start.y():.0f} -> view_start={view_start.x()},{view_start.y()}")

    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, view_start)
    QTest.mouseMove(view.viewport(), view_end)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, view_end)
    qapp.processEvents()

    selected = overlay.selected_words()
    print(f"[8] simulated drag-select: anchor={overlay._anchor} active={overlay._active}, {len(selected)} words selected")
    if len(selected) == 0:
        print("    ^ FAIL: drag produced no selection")
        return 1

    from preview_app.core.selection import assemble_text
    text = assemble_text(selected)
    print(f"[9] copied text would be: {text!r}")
    print("[10] UI-side text-selection is OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
