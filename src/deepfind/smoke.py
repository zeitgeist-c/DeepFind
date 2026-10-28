"""Paketli ana pencere/arama/önizleme/worker doğrulaması: yalnız sentetik veri."""
import json
import os
from pathlib import Path
import tempfile
import time
from .theme import t


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
    from .migrate import ensure_v8
    from .migrate import ensure_v5
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
        with tempfile.TemporaryDirectory(prefix="deepfind-package-smoke-",ignore_cleanup_errors=True) as temp:
            from .wizard import Sihirbaz
            from PySide6.QtWidgets import QWizard
            from PySide6.QtCore import QCoreApplication, QEvent
            theme.apply(app, "koyu")
            wizard = Sihirbaz()
            wizard.show()
            app.processEvents()
            assert wizard.buttonText(QWizard.NextButton) == t("İleri")
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
            from . import embed as model, gom as embedding_jobs
            session=model.isit_oturumu()
            assert session is not None,model.status()
            fid=con.execute('SELECT file_id FROM files').fetchone()[0]
            embedding_jobs.isle_dosya(con,fid,lambda texts:session.encode(texts,gorev='belge'))
            con.close()
            checkpoint("window")
            pen = AnaPencere(db, password)
            pen.show()
            app.processEvents()
            from .archive_ui import layout_cards
            pen.resize(1500,1000); app.processEvents(); layout_cards(pen); app.processEvents()
            gercek = [pen.nav.item(i).text() for i in range(pen.nav.count())]
            beklenen = [t("Ara"),t("Kaynaklar"),t("Tarama"),t("Geçmiş"),t("Taranmış Evraklar"),t("Ayarlar")]
            assert gercek == beklenen, (gercek, beklenen)
            assert pen.arama_islik.count()==3 and pen.gecmis_split.count()==2 and pen.dosya_split.count()==2
            assert not pen.secim_onizle.isEnabled() and not pen.dosya_onizle.isEnabled()
            assert pen.settings_page.isAncestorOf(pen.yedek_liste)
            assert pen.settings_page.isAncestorOf(pen.update_durum)
            assert not pen.update_denetle_btn.isHidden()   # paketli: denetim açık
            assert pen.update_indir_btn.isHidden()
            assert pen.update_bar.isHidden()
            pen.arama_kutu.setText("Ankara denetim")
            pen._ara_simdi()
            deadline = time.monotonic() + 30
            while pen._search_thread is not None or getattr(pen, '_waiting_for_model', False):
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
                                              "snippet": t("Sentetik özet")})
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
            assert not hasattr(pen, 'ai_network')
            assert pen.settings_page.isAncestorOf(pen.model_status)
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
            # Representative old vault: current marker and working FTS, but
            # the optional vector table was never created by an earlier app.
            pen.con.execute('DROP TABLE embeddings')
            pen.con.commit()
            pen._tara_baslat()
            assert pen.scan_dialog.isVisible()
            worker = pen.isci
            pen._tara_duraklat()
            pause_deadline = time.monotonic() + 15
            while pen._scan_status != 'paused':
                app.processEvents();time.sleep(.01)
                assert time.monotonic() < pause_deadline
            pen._tara_duraklat()
            pen.scan_dialog.close()
            pen._tara_baslat()
            assert pen.isci is worker and pen.scan_dialog.isVisible()
            deadline = time.monotonic() + 30
            while pen.isci_thread is not None:
                app.processEvents()
                time.sleep(0.01)
                assert time.monotonic() < deadline
            assert pen.tara_btn.text() == t("Şimdi tara")
            assert not pen.scan_dialog.isModal()
            assert pen.scan_history.count() > 0
            snapshot = worker.snapshot()
            assert snapshot['inventory_ready'] and snapshot['documents_total'] > 0
            assert 0 <= snapshot['documents_done'] <= snapshot['documents_total']
            assert pen.scan_metrics['documents_remaining'].text() == f"{snapshot['documents_total']-snapshot['documents_done']:,}"
            assert pen.tarama_bar.value() == int(snapshot['documents_done']*100/snapshot['documents_total'])
            from .embed import MODEL_VER, DIM
            assert pen.con.execute('SELECT count(*) FROM embeddings WHERE model_ver=? AND dim=?', (MODEL_VER,DIM)).fetchone()[0] > 0
            assert not pen.con.execute("SELECT 1 FROM sqlite_master WHERE name IN ('docs_fts','vocabulary')").fetchone()
            checkpoint('archive-file-list-image-ocr')
            from .app import EKRANLAR
            pen.nav.setCurrentRow(EKRANLAR.index(t("Taranmış Evraklar")))
            deadline=time.monotonic()+30
            while pen._jobs:
                app.processEvents(); time.sleep(.01); assert time.monotonic()<deadline
            pen._files_refresh(reset=True)
            app.processEvents(); time.sleep(0.6); app.processEvents()
            assert any(row[1]==ocr_image for row in pen.file_rows)
            from .rank import search_semantic
            assert any(row['path']==ocr_image for row in search_semantic(pen.con,'Ankara belge')['results'])
            checkpoint('root-remove-worker')
            # Kök kaldırma: ayrı thread'de çalışır, GUI yanıt verir, temizlik doğru.
            from deepfind.app import KokKaldirIsci
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
            from deepfind.app import HaricIsci
            k3 = str(Path(temp) / "disla-koku")
            p3 = os.path.join(k3, "gizli.pdf")
            pen.con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)",
                            (p3, "NameSurvives", ".pdf"))
            fid = pen.con.execute("SELECT file_id FROM files WHERE path=?", (p3,)).fetchone()[0]
            pen.con.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) "
                            "VALUES (?,?,?,?,?)", (fid,"text",1,"Sayfa 1","BodyRemoved"))
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
            pen._nav_toggle()
            assert pen.nav.horizontalScrollBar().maximum() == 0
            pen._nav_toggle()
            assert pen.scan_time_edit.displayFormat() == "HH:mm"
            checkpoint("lock")
            checkpoint('real-semantic-search')
            from . import embed as model, gom as embedding_jobs
            session = model.isit_oturumu()
            assert session is not None, model.status()
            # Index synthetic content with the actual packaged model, not test vectors.
            pen.con.execute("INSERT INTO files(path,name,ext,index_status) VALUES ('synthetic-rental.txt','rental.txt','.txt','ok')")
            synthetic_id = pen.con.execute("SELECT file_id FROM files WHERE path='synthetic-rental.txt'").fetchone()[0]
            pen.con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Belge','kira sözleşmesi aylık ödeme')", (synthetic_id,))
            pen.con.commit()
            embedding_jobs.isle_dosya(pen.con,synthetic_id,lambda texts:session.encode(texts,gorev='belge'))
            from .rank import search_semantic
            result = search_semantic(pen.con,'ev kiralama anlaşması')
            assert any(r['file_id']==synthetic_id and r['score_class']=='semantic' for r in result['results']), result
            report['embedding_backend'] = model.status()
            model_process = session.proc
            assert theme.apply(app, "koyu") == "koyu"
            pen.kilitle()
            assert model_process.poll() is not None
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
            old_fid = old_con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/synthetic/startup.txt','startup.txt','.txt')").lastrowid
            old_con.executemany("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'body','Sayfa','Şırnak sözleşme')", [(old_fid,)] * 601)
            old_con.execute("DELETE FROM schema_meta WHERE k='archive_version'")
            old_con.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(raw_text)")
            old_con.execute("INSERT INTO docs_fts(raw_text) VALUES ('legacy synthetic')")
            old_con.execute("UPDATE schema_meta SET v='8' WHERE k='schema_version'")
            old_con.commit(); old_con.close()
            opening = OpeningDialog(old_db, password, str(Path(temp) / 'startup-backups'))
            phases = []
            counts = []
            opening.worker.progress.connect(lambda phase, *_: phases.append(phase))
            opening.worker.progress.connect(lambda phase, done, total: counts.append((phase, done, total)))
            assert opening.prepare() == QDialog.Accepted
            assert {'backup', 'verify', 'schema'} <= set(phases)
            assert 'fts' not in phases
            checkpoint('startup-index-once')
            for _ in range(3):
                repeated = OpeningDialog(old_db, password, str(Path(temp) / 'startup-backups'))
                repeated_phases = []
                repeated.worker.progress.connect(lambda phase, *_: repeated_phases.append(phase))
                assert repeated.prepare() == QDialog.Accepted
                assert not {'fts', 'backup', 'verify'} & set(repeated_phases)
            verified = vault.open_vault(old_db, password)
            assert verified.execute("SELECT count(*) FROM segments").fetchone()[0] == 601
            assert not verified.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts'").fetchone()
            verified.close()
            from . import gom as _gom
            report["vektor_model"] = bool(_gom.model_var_mi())
            checkpoint('vektor-model-durumu')
            report.update(ok=True, checks=["frozen-spawn-extraction", "vault", "semantic-only-schema", "async-search",
                                           "excel-preview", "pdf-preview-loading", "dark-theme", "lock-unlock",
                                           "setup-folder-add-refresh", "turkish-buttons-logo", "svg-assets",
                                           "actual-first-run-to-main-and-scan", "scan-popup-background-reopen", "compact-time-and-navigation",
                                           "packaged-turkish-ocr", "durable-scan-history",
                                           'search-workbench-local-model-settings-backups','paged-archive-files','image-ocr-indexed',
                                           'background-startup-migration', 'root-remove-worker', 'exclusion-worker',
                                           'vektor-model-durumu', 'real-semantic-search', 'model-process-closed-on-lock',
                                           'startup-index-once', 'startup-counted-progress',
                                           'scan-inventory-and-percentages', 'scan-pause-resume',
                                           'legacy-embedding-schema-repair', 'no-dictionary-maintenance'])
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
