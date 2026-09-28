"""Blocking first-run OCR component page; download itself runs off the UI thread."""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QFileDialog

from . import ocr_setup


class _Installer(QObject):
    done = Signal()
    failed = Signal(str)
    progress = Signal(str, int, int, int, int)

    def __init__(self, offline_dir=None):
        super().__init__()
        self.offline_dir = offline_dir

    @Slot()
    def run(self):
        try:
            ocr_setup.ensure(lambda *args: self.progress.emit(*args), self.offline_dir)
            self.done.emit()
        except Exception as error:
            self.failed.emit(str(error))


class OcrSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evrakçı • OCR hazırlanıyor")
        self.setMinimumWidth(520)
        self.running = False
        self.completed = False
        self.failure_message = ""
        self.offline_dir = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Gerekli bileşenler"))
        self.status = QLabel("Türkçe OCR hazırlanıyor. Doğrulanınca Evrakçı açılacak.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)
        self.retry = QPushButton("Yeniden dene")
        self.retry.hide()
        self.retry.clicked.connect(self.start)
        layout.addWidget(self.retry)
        self.offline = QPushButton("Çevrimdışı model klasörü seç")
        self.offline.hide()
        self.offline.clicked.connect(self.choose_offline)
        layout.addWidget(self.offline)
        self.exit_button = QPushButton("Çıkış")
        self.exit_button.clicked.connect(self.reject)
        self.exit_button.hide()
        layout.addWidget(self.exit_button)

    @Slot(str, int, int, int, int)
    def update_progress(self, lang, index, total, downloaded, expected):
        if lang == "ready":
            self.status.setText("OCR kullanıma hazır.")
            self.bar.setValue(100)
            return
        self.status.setText(f"{lang.upper()} modeli doğrulanıyor/indiriliyor • {index}/{total} • "
                            f"{downloaded // 1024:,}/{expected // 1024:,} KB")
        self.bar.setValue(int(((index - 1) + min(downloaded, expected) / expected) / total * 100))

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
            self.offline.show()
            self.exit_button.show()

    def choose_offline(self):
        folder = QFileDialog.getExistingDirectory(self, "Doğrulanmış OCR model klasörü")
        if folder:
            self.offline_dir = folder
            self.start()

    def start(self):
        if self.running:
            return
        self.running = True
        self.completed = False
        self.failure_message = ""
        self.retry.hide()
        self.offline.hide()
        self.exit_button.hide()
        self.bar.setValue(0)
        self.thread = QThread(self)
        self.worker = _Installer(self.offline_dir)
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
