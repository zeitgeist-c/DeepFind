"""Blocking first-run OCR readiness page; verification runs off the UI thread.

RapidOCR modelleri paketle gelir: indirme yok, doğrulama + tek seferlik motor
kurulumu (ısınma) yapılır. Hata olursa kullanıcıya onarım/çıkış seçenekleri kalır.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton

from . import ocr_setup


class _Installer(QObject):
    done = Signal()
    failed = Signal(str)
    progress = Signal(str, int, int, int, int)

    @Slot()
    def run(self):
        try:
            ocr_setup.ensure(lambda *args: self.progress.emit(*args))
            self.done.emit()
        except Exception as error:
            self.failed.emit(str(error))


class OcrSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepFind • OCR hazırlanıyor")
        self.setMinimumWidth(520)
        self.running = False
        self.completed = False
        self.failure_message = ""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Gerekli bileşenler"))
        self.status = QLabel("Türkçe OCR doğrulanıyor. Hazır olunca DeepFind açılacak.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)
        self.retry = QPushButton("Yeniden dene")
        self.retry.hide()
        self.retry.clicked.connect(self.start)
        layout.addWidget(self.retry)
        self.exit_button = QPushButton("Çıkış")
        self.exit_button.clicked.connect(self.reject)
        self.exit_button.hide()
        layout.addWidget(self.exit_button)

    @Slot(str, int, int, int, int)
    def update_progress(self, name, index, total, done_bytes, expected_bytes):
        if name == "ready":
            self.status.setText("OCR kullanıma hazır.")
            self.bar.setValue(100)
            return
        self.status.setText("OCR motoru yükleniyor…")
        self.bar.setValue(int(index / max(1, total) * 90))

    @Slot(str)
    def fail(self, message):
        self.failure_message = message

    @Slot()
    def mark_done(self):
        self.completed = True

    @Slot()
    def finish_run(self):
        self.running = False
        if self.completed:
            self.accept()
        else:
            self.status.setText("OCR hazır değil: " + self.failure_message)
            self.retry.show()
            self.exit_button.show()

    def start(self):
        if self.running:
            return
        self.running = True
        self.completed = False
        self.failure_message = ""
        self.retry.hide()
        self.exit_button.hide()
        self.bar.setValue(0)
        self.thread = QThread(self)
        self.worker = _Installer()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.done.connect(self.mark_done)
        self.worker.failed.connect(self.fail)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.finish_run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def reject(self):
        if not self.running:
            super().reject()

    def closeEvent(self, event):
        if self.running:
            event.ignore()
        else:
            super().closeEvent(event)


def prepare_ocr(parent=None) -> bool:
    ok, _ = ocr_setup.ready()
    if ok:
        return True
    dialog = OcrSetupDialog(parent)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, dialog.start)
    result = dialog.exec() == QDialog.Accepted
    return result and ocr_setup.ready()[0]
