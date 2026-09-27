"""Paketli ana pencere/arama/önizleme/worker doğrulaması: yalnız sentetik veri."""
import json
import os
from pathlib import Path
import tempfile
import time


def run(report_path):
    def checkpoint(stage):
        Path(report_path).write_text(json.dumps({"ok": False, "stage": stage}), encoding="utf-8")
    checkpoint("imports")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from openpyxl import Workbook
    from . import schema, vault, theme
    from .migrate import ensure_v7
    from .vocab import ensure_v5, rebuild_vocab
    from .index import index_entry
    from .scan import Entry
    from .workers import run_work
    from .app import AnaPencere
    from .auth import ParolaDialog
    from .version import __version__
    report = {"version": __version__, "ok": False}
    checkpoint("application")
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QIcon
    assert not QIcon(str(Path(__file__).parent / "assets/check-light.svg")).pixmap(16, 16).isNull()
    checkpoint("fixture")
    try:
        with tempfile.TemporaryDirectory(prefix="evrakci-package-smoke-") as temp:
            from .wizard import Sihirbaz
            from PySide6.QtWidgets import QWizard
            from PySide6.QtCore import QCoreApplication, QEvent
            theme.apply(app, "koyu")
            wizard = Sihirbaz()
            wizard.show()
            app.processEvents()
            assert wizard.buttonText(QWizard.NextButton) == "İleri"
            assert not wizard.windowIcon().isNull()
            wizard.next()
            wizard.s1.setText("yalniz-sentetik-smoke-1234")
            wizard.s2.setText(wizard.s1.text())
            assert wizard.validateCurrentPage()
            wizard.next()
            wizard.agac.setCurrentIndex(wizard.model.index(temp))
            wizard.ekle.click()
            assert wizard.secim["kokler"] == [temp]
            wizard.yenile.click()
            assert wizard.kok_model.rowCount() == 1
            wizard.close()
            wizard.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            source = Path(temp) / "ornek.xlsx"
            wb = Workbook()
            wb.active.append(["Ankara paket denetim 2024"])
            wb.save(source)
            checkpoint("worker")
            result = run_work("extract", (str(source), ".xlsx", source.stat().st_size))
            assert result.status == "ok" and "Ankara" in result.segments[0].raw_text
            db = str(Path(temp) / "kasa.db")
            password = "yalniz-sentetik-smoke-1234"
            con = vault.open_vault(db, password)
            schema.ensure_schema(con)
            ensure_v5(con)
            ensure_v7(con)
            stat = source.stat()
            index_entry(con, Entry(str(source), source.name, ".xlsx", stat.st_size, stat.st_mtime_ns), result)
            rebuild_vocab(con)
            con.close()
            checkpoint("window")
            pen = AnaPencere(db, password)
            pen.show()
            pen.arama_kutu.setText("Ankara denetim")
            pen._ara_simdi()
            deadline = time.monotonic() + 30
            while pen._search_thread is not None:
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.sonuc_model.rowCount() == 1
            checkpoint("preview")
            pen._sec(pen.sonuc_model.index(0, 0))
            while pen.onizleme.busy():
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.onizleme.tablo.rowCount() == 1
            checkpoint("lock")
            assert theme.apply(app, "koyu") == "koyu"
            pen.kilitle()
            assert pen.con is None and pen.sonuc_model.rowCount() == 0
            pen._unlock_dialog.old.setText(password)
            pen._unlock_dialog._submit()
            assert pen.con is not None and not pen._locked
            pen._exiting = True
            pen.close()
            report.update(ok=True, checks=["frozen-spawn-extraction", "vault", "FTS", "async-search",
                                           "excel-preview", "dark-theme", "lock-unlock",
                                           "setup-folder-add-refresh", "turkish-buttons-logo", "svg-assets"])
    except Exception as error:
        report["error"] = repr(error)
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 2
