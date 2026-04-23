from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import QApplication

from . import config
from .ui.main_window import MainWindow


CURSIVE_FONT_FILES = [
    "DancingScript-Regular.ttf",
    "GreatVibes-Regular.ttf",
    "Caveat-Regular.ttf",
]


def _register_fonts() -> list[str]:
    families: list[str] = []
    for filename in CURSIVE_FONT_FILES:
        path = config.fonts_dir() / filename
        if not path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id == -1:
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            families.append(family)
    return families


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    config.ensure_dirs()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("Preview App")
    app.setOrganizationName("preview_app")

    families = _register_fonts()

    qss_path = config.resources_dir() / "styles" / "app.qss"
    if qss_path.exists():
        try:
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except OSError:
            pass

    window = MainWindow(cursive_families=families)
    window.show()

    for arg in argv[1:]:
        if arg and not arg.startswith("-"):
            window.open_path(arg)

    run_loop = getattr(app, "exec")
    return run_loop()
