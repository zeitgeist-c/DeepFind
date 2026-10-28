"""Sentetik kasayla gerçek ilk kurulum girişini paket içinde denetler."""
import os
import time
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWizard
from .wizard import Sihirbaz
from .app import main


def run(directory):
    app = QApplication.instance()
    source = Path(directory) / "startup-source"
    source.mkdir()
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["İlk kurulum gerçek akış testi"])
    document = source / "belge.xlsx"
    wb.save(document)
    old = time.time() - 10
    os.utime(document, (old, old))
    state = {"setup": False, "scan_started": False, "ok": False, "error": ""}
    deadline = time.monotonic() + 40
    timer = QTimer(app)

    def tick():
        try:
            if time.monotonic() > deadline:
                raise AssertionError("Gerçek kurulum geçişi zaman aşımı")
            if not state["setup"]:
                for widget in app.topLevelWidgets():
                    if isinstance(widget, Sihirbaz) and widget.isVisible():
                        widget.s1.setText("sentetik-startup-123456")
                        widget.s2.setText(widget.s1.text())
                        widget._ekle_yol(str(source))
                        widget.tema.setCurrentIndex(2)
                        for _ in range(4):
                            widget.next()
                        state["setup"] = True
                        widget.button(QWizard.FinishButton).click()
                        break
                return
            pen = getattr(app, '_main_window', None)
            if pen is None or not pen.isVisible():
                return
            if pen.isci_thread is not None:
                state['scan_started'] = True
            if state['scan_started'] and pen.isci_thread is None:
                assert pen.con.execute('SELECT count(*) FROM segments').fetchone()[0] > 0
                assert 'tamamlandı' in pen.tarama_bilgi.text()
                state['ok'] = True
                timer.stop()
                pen._cikis()
        except Exception as error:
            state['error'] = repr(error)
            timer.stop()
            pen = getattr(app, '_main_window', None)
            if pen is not None:
                pen._cikis()
            else:
                app.quit()

    timer.timeout.connect(tick)
    timer.start(100)
    result = main(kasa_yolu=str(Path(directory) / 'first-run.db'))
    timer.stop()
    if not state['ok'] or result:
        raise AssertionError(state['error'] or 'Gerçek ilk kurulum/tarama tamamlanmadı')
    app._startup = None
    return True
