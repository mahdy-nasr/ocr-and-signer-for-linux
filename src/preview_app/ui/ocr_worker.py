from __future__ import annotations

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class _Signals(QObject):
    finished = pyqtSignal(int, int, list)
    failed = pyqtSignal(int, str)


class OcrWorker(QRunnable):
    _counter = 0

    def __init__(self, doc, page_index: int, dpi: int):
        super().__init__()
        self.doc = doc
        self.page_index = page_index
        self.dpi = dpi
        OcrWorker._counter += 1
        self.run_id = OcrWorker._counter
        self.signals = _Signals()

    def run(self) -> None:
        try:
            words = self.doc.words_for(self.page_index, self.dpi)
        except Exception as e:  # noqa: BLE001
            try:
                self.signals.failed.emit(self.page_index, str(e))
            except RuntimeError:
                pass
            return
        try:
            self.signals.finished.emit(self.page_index, self.run_id, words)
        except RuntimeError:
            pass
