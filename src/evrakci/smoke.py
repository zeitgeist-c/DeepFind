"""Paketli ana pencere/arama/önizleme/worker doğrulaması: yalnız sentetik veri."""
import json
import os
from pathlib import Path
import tempfile
import time


def run(report_path):
    def checkpoint(stage):
        nonlocal current_stage
        current_stage = stage
        Path(report_path).write_text(json.dumps({"ok": False, "stage": stage}), encoding="utf-8")
    current_stage = "start"
    checkpoint("imports")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication, QDialog
    from openpyxl import Workbook
    from . import schema, vault, theme
    from .migrate import ensure_v8, get_setting, set_setting
    from .vocab import ensure_v5, rebuild_vocab
    from .index import index_entry
    from .scan import Entry
    from .workers import run_work
    from .app import AnaPencere
    from .version import __version__
    report = {"version": __version__, "ok": False}
    checkpoint("application")
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QIcon
    assert not QIcon(str(Path(__file__).parent / "assets/check-light.svg")).pixmap(16, 16).isNull()
    checkpoint("fixture")
    try:
        with tempfile.TemporaryDirectory(prefix="evrakci-package-smoke-",ignore_cleanup_errors=True) as temp:
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
            ensure_v8(con)
            stat = source.stat()
            index_entry(con, Entry(str(source), source.name, ".xlsx", stat.st_size, stat.st_mtime_ns), result)
            rebuild_vocab(con)
            set_setting(con, "ai_model", "gemini-3.5-flash")
            con.close()
            checkpoint("window")
            pen = AnaPencere(db, password)
            pen.show()
            app.processEvents()
            from .archive_ui import layout_cards
            pen.resize(1500,1000); app.processEvents(); layout_cards(pen); app.processEvents()
            assert [pen.nav.item(i).text() for i in range(pen.nav.count())] == ['Ara','AI ile ara','Kaynaklar','Tarama','Geçmiş','Taranmış Evraklar','Ayarlar']
            assert pen.arama_islik.count()==3 and pen.gecmis_split.count()==2 and pen.dosya_split.count()==2
            assert not pen.secim_onizle.isEnabled() and not pen.dosya_onizle.isEnabled()
            assert pen.ai_page.isAncestorOf(pen.ai_key_input) and pen.ai_page.isAncestorOf(pen.ai_question)
            assert pen.settings_page.isAncestorOf(pen.yedek_liste)
            assert pen.settings_page.isAncestorOf(pen.update_durum)
            assert not pen.update_denetle_btn.isHidden()   # paketli: denetim açık
            assert pen.update_indir_btn.isHidden()
            assert pen.update_bar.isHidden()
            assert [pen.ai_model.itemData(i) for i in range(pen.ai_model.count())] == [
                "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                "gemma-4-26b-a4b-it"]
            assert pen.ai_model.currentData() == "gemini-3.5-flash-lite"
            assert get_setting(pen.con, "ai_model") == "gemini-3.5-flash-lite"
            pen.ai_model.setCurrentIndex(0)
            assert get_setting(pen.con, "ai_model") == "gemini-3.6-flash"
            pen.arama_kutu.setText("Ankara denetim")
            pen._ara_simdi()
            deadline = time.monotonic() + 30
            while pen._search_thread is not None:
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.sonuc_model.rowCount() == 1
            pen.sonuc_liste.setCurrentIndex(pen.sonuc_model.index(0, 0))
            pen._secim_guncelle()
            assert pen.secim_ad.text() == "ornek.xlsx" and pen.secim_onizle.isEnabled()
            checkpoint("preview")
            pen._sec(pen.sonuc_model.index(0, 0))
            while pen.onizleme.busy():
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.onizleme.tablo.rowCount() == 1
            checkpoint("pdf-preview-loading")
            import pypdfium2 as pdfium
            from .preview import Onizleme
            pdf_path = Path(temp) / "sentetik.pdf"
            pdf = pdfium.PdfDocument.new()
            pdf.new_page(width=612, height=792)
            pdf.save(pdf_path)
            pdf.close()

            class NoSegmentQuery:
                def execute(self, sql, args=()):
                    assert "segments" not in sql.lower()
                    return pen.con.execute(sql, args)

            preview = Onizleme()
            preview.show()
            preview.goster(NoSegmentQuery(), {"path": str(pdf_path), "name": pdf_path.name,
                                              "ext": ".pdf", "label": "Sayfa 1", "page": 1,
                                              "snippet": "Sentetik özet"})
            assert preview.yukleme.isVisible()
            deadline = time.monotonic() + 30
            while preview.busy():
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            app.processEvents()
            assert not preview.yukleme.isVisible()
            assert preview.goruntu.pixmap() is not None and not preview.goruntu.pixmap().isNull()
            preview.close()
            preview.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            checkpoint("ai-local-preview")
            pen._ai_show()
            pen.ai_question.setText("Ankara denetim")
            pen._ai_prepare()
            deadline=time.monotonic()+30
            while pen._jobs:
                app.processEvents(); time.sleep(0.01)
                assert time.monotonic()<deadline
            assert pen.ai_preview is not None and pen.ai_reply is None
            assert "Ankara" in pen.ai_preview_box.toPlainText()
            gemma_index = pen.ai_model.findData("gemma-4-26b-a4b-it")
            assert gemma_index >= 0
            pen.ai_model.setCurrentIndex(gemma_index)
            assert pen.ai_preview is None
            pen.ai_mode.setCurrentIndex(1)
            deadline=time.monotonic()+30
            while pen._jobs:
                app.processEvents(); time.sleep(0.01)
                assert time.monotonic()<deadline
            assert pen.ai_document.count() == 1
            pen._ai_prepare()
            while pen._jobs:
                app.processEvents(); time.sleep(0.01)
                assert time.monotonic()<deadline
            assert pen.ai_preview is not None and pen.ai_preview.mode == "summary"
            assert pen.ai_reply is None
            checkpoint("packaged-ocr")
            from . import ocr_setup, ocr
            from PIL import Image, ImageDraw, ImageFont
            assert ocr_setup.ready()[0]
            image = Image.new("RGB", (1100, 220), "white")
            ImageDraw.Draw(image).text((30, 35), "Ankara belge 2024",
                                       fill="black", font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 65))
            ocr_image = str(Path(temp) / "ocr-probe.png")
            image.save(ocr_image)
            os.utime(ocr_image,(time.time()-10,time.time()-10))
            text, conf, words = ocr.recognize_png(ocr_image)
            assert words > 0 and "Ankara" in text
            checkpoint("scan-popup")
            pen.con.execute("INSERT INTO roots(display_path,canonical_path) VALUES (?,?)", (temp, temp.lower()))
            pen.con.commit()
            pen._kok_tazele()
            pen._tara_baslat()
            assert pen.scan_dialog.isVisible()
            worker = pen.isci
            pen.scan_dialog.close()
            pen._tara_baslat()
            assert pen.isci is worker and pen.scan_dialog.isVisible()
            deadline = time.monotonic() + 30
            while pen.isci_thread is not None:
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.tara_btn.text() == "Şimdi tara"
            assert not pen.scan_dialog.isModal()
            assert pen.scan_history.count() > 0
            checkpoint('archive-file-list-image-ocr')
            pen.nav.setCurrentRow(5)
            deadline=time.monotonic()+30
            while pen._jobs:
                app.processEvents(); time.sleep(.01); assert time.monotonic()<deadline
            assert any(row[1]==ocr_image for row in pen.file_rows)
            from .rank import search_ranked
            assert any(row['path']==ocr_image for row in search_ranked(pen.con,'Ankara belge')['results'])
            checkpoint('root-remove-worker')
            # Kök kaldırma: ayrı thread'de çalışır, GUI yanıt verir, temizlik doğru.
            from evrakci.app import KokKaldirIsci
            from PySide6.QtCore import QThread
            # Ana test kökünü çıkar; k2 temp içinde kalsın ve TemporaryDirectory temizlesin.
            pen.con.execute("DELETE FROM roots WHERE display_path=?", (temp,))
            k2 = str(Path(temp) / "ikinci-kok")
            os.makedirs(k2)
            from openpyxl import Workbook
            p2 = os.path.join(k2, "tasinan.xlsx")
            wbp = Workbook(); wbp.active.append(["G koku testi 2026"]); wbp.save(p2)
            pen.con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)", (k2, k2.lower()))
            pen.con.execute("INSERT INTO files(path,name,ext,size,mtime_ns) VALUES (?,?,?,?,?)",
                            (p2, os.path.basename(p2), ".xlsx", 100, 100))
            pen.con.commit()
            pen._kok_tazele()
            isci = KokKaldirIsci(db, password, k2)
            th = QThread()
            isci.moveToThread(th)
            th.started.connect(isci.kos)
            biten = []
            isci.bitti.connect(lambda n: biten.append(n))
            isci.bitti.connect(th.quit)
            isci.hata.connect(lambda m: biten.append(("hata", m)))
            th.start()
            deadline = time.monotonic() + 30
            while th.isRunning() and time.monotonic() < deadline:
                app.processEvents(); time.sleep(0.01)
            th.wait(2000)
            assert biten == [1], biten
            assert pen.con.execute("SELECT count(*) FROM files WHERE path LIKE ?", (k2 + "%",)).fetchone()[0] == 0
            checkpoint('exclusion-worker')
            from evrakci.app import HaricIsci
            k3 = str(Path(temp) / "disla-koku")
            p3 = os.path.join(k3, "gizli.pdf")
            pen.con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)",
                            (p3, "NameSurvives", ".pdf"))
            fid = pen.con.execute("SELECT file_id FROM files WHERE path=?", (p3,)).fetchone()[0]
            pen.con.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) "
                            "VALUES (?,?,?,?,?)", (fid,"text",1,"Sayfa 1","BodyRemoved"))
            pen.con.execute("INSERT INTO vocabulary(term,freq) VALUES ('namesurvives',1),('bodyremoved',1)")
            pen.con.commit()
            worker = HaricIsci(db, password, k3)
            th2 = QThread(); worker.moveToThread(th2); th2.started.connect(worker.kos)
            excluded = []; worker.bitti.connect(lambda rule, count: excluded.append((rule,count)))
            worker.bitti.connect(th2.quit); worker.bitti.connect(worker.deleteLater)
            worker.hata.connect(lambda error: excluded.append(("error",error)))
            th2.start(); deadline = time.monotonic()+30
            while th2.isRunning() and time.monotonic()<deadline:
                app.processEvents(); time.sleep(.01)
            th2.wait(2000)
            assert excluded == [(k3,1)], excluded
            assert pen.con.execute("SELECT index_status FROM files WHERE file_id=?",(fid,)).fetchone()[0]=='excluded'
            assert pen.con.execute("SELECT count(*) FROM segments WHERE file_id=?",(fid,)).fetchone()[0]==0
            assert pen.con.execute("SELECT term FROM vocabulary WHERE term='namesurvives'").fetchone()
            assert pen.con.execute("SELECT term FROM vocabulary WHERE term='bodyremoved'").fetchone() is None
            pen._nav_toggle()
            assert pen.nav.horizontalScrollBar().maximum() == 0
            pen._nav_toggle()
            assert pen.scan_time_edit.displayFormat() == "HH:mm"
            checkpoint("lock")
            assert theme.apply(app, "koyu") == "koyu"
            pen.kilitle()
            assert pen.con is None and pen.sonuc_model.rowCount() == 0
            pen._unlock_dialog.old.setText(password)
            pen._unlock_dialog._submit()
            assert pen.con is not None and not pen._locked
            pen._exiting = True
            pen._cikis()
            while pen._jobs or pen.onizleme.busy():
                app.processEvents(); time.sleep(0.01)
                assert time.monotonic()<deadline
            checkpoint("actual-first-run")
            from .startup_smoke import run as startup_run
            startup_run(temp)
            checkpoint('background-startup-migration')
            from .startup import OpeningDialog
            from .migrate import ensure_current
            old_db = str(Path(temp) / 'startup-legacy.db')
            old_con = vault.open_vault(old_db, password)
            ensure_current(old_con)
            old_con.execute("DELETE FROM schema_meta WHERE k='archive_version'")
            old_con.commit(); old_con.close()
            opening = OpeningDialog(old_db, password, str(Path(temp) / 'startup-backups'))
            phases = []
            opening.worker.progress.connect(lambda phase, *_: phases.append(phase))
            assert opening.prepare() == QDialog.Accepted
            assert {'backup', 'verify', 'schema'} <= set(phases)
            report.update(ok=True, checks=["frozen-spawn-extraction", "vault", "FTS", "async-search",
                                           "excel-preview", "pdf-preview-loading", "dark-theme", "lock-unlock",
                                           "setup-folder-add-refresh", "turkish-buttons-logo", "svg-assets",
                                           "actual-first-run-to-main-and-scan", "scan-popup-background-reopen", "compact-time-and-navigation",
                                           "packaged-turkish-ocr", "ai-local-preview-no-network",
                                           "ai-model-switch", "ai-model-migration", "durable-scan-history",
                                           'search-workbench-ai-tab-settings-backups','paged-archive-files','image-ocr-indexed',
                                           'background-startup-migration', 'root-remove-worker', 'exclusion-worker'])
    except Exception as error:
        import traceback
        report["stage"] = current_stage
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()[-3000:]
        if 'pen' in locals():
            pen._cikis()
            deadline=time.monotonic()+30
            while pen._jobs or pen.onizleme.busy() or pen.isci_thread is not None:
                app.processEvents(); time.sleep(.01)
                if time.monotonic()>deadline: break
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 2
