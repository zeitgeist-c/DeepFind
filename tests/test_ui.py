"""A7 arayuz testleri (offscreen): tema, sihirbaz, arama, onizleme, kilit."""
import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_TD = "C:/Users/user/AppData/Local/hermes/cache/scratch/evrakci-a1/tessdata"
if os.path.isdir(_TD):
    os.environ["EVRAKCI_TESSDATA"] = _TD

from PySide6.QtWidgets import QApplication  # noqa: E402

from evrakci import coordinator, migrate, schema, theme, vault  # noqa: E402
from evrakci.preview import Onizleme  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402
from evrakci.migrate import ensure_v7  # noqa: E402

PW = "arayuz-sifresi-1234"
APP = None


def _app():
    global APP
    if APP is None:
        APP = QApplication.instance() or QApplication([])
    return APP


def _wait_search(pen):
    deadline = time.monotonic() + 10
    while pen._search_thread is not None or pen._pending_search is not None:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline, "arama zaman aşımı"


def _wait_preview(preview):
    deadline = time.monotonic() + 20
    while preview.busy():
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline

def _pdf(kok, ad, metin):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 13)
    c.drawString(72, 750, metin)
    c.save()
    return p


@pytest.fixture()
def pencere(tmp_path):
    _app()
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara arayüz testi 2024 vergi levhası")
    time.sleep(2.5)
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?, ?)",
                (kok, os.path.normpath(kok).lower()))
    con.commit()
    coordinator.run_scan(con, db, kok)
    con.close()
    from evrakci.app import AnaPencere
    pen = AnaPencere(db, PW)
    yield pen
    try:
        if pen.con is not None:
            vault.lock(pen.con, os.path.dirname(db))
    except Exception:
        pass
    pen._exiting = True
    pen.close()
    deadline = time.monotonic() + 20
    while pen._search_thread is not None or pen.isci_thread is not None or pen.onizleme.busy():
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline
    pen.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_tema_uc_mod(pencere):
    _app()
    assert theme.apply(_app(), "acik") == "acik"
    assert theme.apply(_app(), "koyu") == "koyu"
    assert theme.resolve("sistem", True) == "koyu"
    assert theme.resolve("sistem", False) == "acik"
    from evrakci import ai
    pencere.nav.setCurrentRow(6)
    pencere.ai_question.setText("Ankara arayüz testi")
    pencere._ai_prepare()
    assert pencere.ai_preview is not None
    index = pencere.ai_model.findData("gemini-3.1-flash-lite")
    pencere.ai_model.setCurrentIndex(index)
    assert migrate.get_setting(pencere.con, "ai_model") == "gemini-3.1-flash-lite"
    assert pencere.ai_preview is None and ai.endpoint(pencere.ai_model.currentData())


def test_arama_sonuc_ve_onizleme(pencere, tmp_path):
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    idx = pencere.sonuc_model.index(0, 0)
    pencere._sec(idx)
    _wait_preview(pencere.onizleme)
    assert pencere.onizleme.baslik.text() == "belge.pdf"
    assert "Sayfa" in pencere.onizleme.bilgi.text()


def test_bos_sorgu_tum_arsivi_listelemez(pencere):
    pencere.arama_kutu.setText("")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() == 0


def test_sihirbaz_sayfa_ve_sifre_kurali():
    _app()
    from evrakci.wizard import Sihirbaz
    s = Sihirbaz()
    assert s.pageIds() and len(s.pageIds()) == 5
    s.restart()
    s.next()  # sifre sayfasi (page 1)
    s.s1.setText("kisa")
    s.s2.setText("kisa")
    assert s.validateCurrentPage() is False
    s.s1.setText("uzun-sifre-1234")
    s.s2.setText("uzun-sifre-1234")
    assert s.validateCurrentPage() is True
    s.close()
    s.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_sihirbaz_ekle_secili_klasor_yenile_ve_kaldir(tmp_path):
    _app()
    from evrakci.wizard import Sihirbaz
    from PySide6.QtWidgets import QWizard
    from PySide6.QtCore import QCoreApplication, QEvent
    s = Sihirbaz()
    root = tmp_path / "Belgeler"
    root.mkdir()
    idx = s.model.index(str(root))
    assert idx.isValid()
    s.agac.setCurrentIndex(idx)
    s.ekle.click()
    assert s.secim["kokler"] == [str(root)]
    assert s.kok_model.rowCount() == 1
    s.unc.setText(str(root) + os.sep)
    s.ekle.click()
    assert s.kok_model.rowCount() == 1
    assert "zaten" in s.kaynak_mesaj.text()
    old_model = s.model
    s.yenile.click()
    assert s.model is not old_model
    assert s.kok_model.rowCount() == 1
    s.kok_liste.setCurrentIndex(s.kok_model.index(0, 0))
    s._kaldir()
    assert s.secim["kokler"] == []
    s.unc.setText(str(tmp_path / "yok"))
    s.ekle.click()
    assert "ulaşılamıyor" in s.kaynak_mesaj.text()
    file = tmp_path / "bir-dosya.txt"
    file.write_text("sentetik")
    s.unc.setText(str(file))
    s.ekle.click()
    assert s.secim["kokler"] == []
    assert s.buttonText(QWizard.NextButton) == "İleri"
    assert s.buttonText(QWizard.BackButton) == "Geri"
    assert not s.windowIcon().isNull()
    assert s.agac.isHeaderHidden()
    assert "Diske/loga" not in s.page(1).subTitle()
    s.close()
    s.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_kilit_model_temizler(pencere, tmp_path, monkeypatch):
    pencere.arama_kutu.setText("Ankara")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    # kilit diyalogunu atla: QInputDialog reddetsin -> pencere kapanir
    from PySide6.QtWidgets import QInputDialog
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    pencere.kilitle()
    assert pencere.con is None
    assert pencere.sonuc_model.rowCount() == 0


def test_pdf_onizleme_sayfa_render(pencere):
    _app()
    o = Onizleme()
    con = vault.open_vault(pencere.kasa_yolu, PW)
    try:
        row = con.execute("SELECT path FROM files").fetchone()
        o.goster(con, {"path": row[0], "name": "belge.pdf", "ext": ".pdf",
                       "label": "Sayfa 1", "page": 1, "snippet": "x", "why": ["ad"]})
        _wait_preview(o)
        assert o.goruntu.pixmap() is not None and not o.goruntu.pixmap().isNull()
    finally:
        con.close()
        o.close()
        o.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_oturum_kilit_filtresi_uykuda_kilitler():
    _app()
    from evrakci.app import OturumKilitFiltresi
    import ctypes
    from ctypes import wintypes
    cagrildi = []
    f = OturumKilitFiltresi(lambda: cagrildi.append(1))
    msg = wintypes.MSG()
    msg.message = OturumKilitFiltresi.WM_POWERBROADCAST
    msg.wParam = OturumKilitFiltresi.PBT_APMSUSPEND
    tuketildi, _kod = f.nativeEventFilter(b"windows_generic",
                                          int(ctypes.addressof(msg)))
    assert tuketildi and cagrildi == [1]
    msg2 = wintypes.MSG()
    msg2.message = 0x0042  # ilgisiz mesaj
    tuketildi2, _k2 = f.nativeEventFilter(b"windows_generic",
                                          int(ctypes.addressof(msg2)))
    assert not tuketildi2 and cagrildi == [1]


def test_tarama_isci_eszamanli_kosar(tmp_path):
    _app()
    from evrakci.app import TaramaIsci
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "is.pdf", "Ankara işçi testi 2024")
    time.sleep(2.5)
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.close()
    isci = TaramaIsci(db, PW, [kok])
    sonuc, hata = [], []
    isci.bitti.connect(sonuc.append)
    isci.hata.connect(hata.append)
    isci.kos()
    assert not hata, hata
    assert sonuc and sonuc[0].get("done", 0) >= 1, sonuc


def test_kurulum_tema_ve_toplu_klasor_islemleri(tmp_path):
    from evrakci.wizard import Sihirbaz
    from PySide6.QtCore import QCoreApplication, QEvent
    s = Sihirbaz()
    try:
        for i in range(3):
            folder = tmp_path / str(i)
            folder.mkdir()
            s._ekle_yol(str(folder))
        s.tema.setCurrentIndex(2)
        assert _app().property('evrakci_theme') == 'koyu'
        s.kok_liste.selectAll()
        s._kaldir()
        assert not s.secim['kokler']
        s._ekle_yol(str(tmp_path / '0'))
        s._tumunu_kaldir()
        assert s.kok_model.rowCount() == 0
        assert all((tmp_path / str(i)).is_dir() for i in range(3))
    finally:
        s.close()
        s.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_dar_gezinme_kapsam_ve_hatirlanan_kilit(pencere, tmp_path, monkeypatch):
    from evrakci import remember
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    pencere._nav_toggle()
    assert pencere.rail.width() == 86 and pencere.nav.item(0).text() == ''
    assert pencere.nav.item(0).toolTip() == 'Ara'
    pencere._nav_toggle()
    assert pencere.nav.item(0).text() == 'Ara'
    pencere.scope_mode.setCurrentIndex(1)
    assert pencere.scope_sources.count() == 1
    remember.save(pencere.kasa_yolu, PW)
    pencere._otomatik_kilitle()
    assert not pencere._locked
    pencere.scan_log.appendPlainText('sentetik dosya yolu')
    pencere.kilitle()
    assert pencere._locked and not remember.enabled(pencere.kasa_yolu)
    assert not pencere.scan_log.toPlainText()

def test_015_popup_background_and_automatic(pencere, monkeypatch):
    from evrakci import app as app_module
    from PySide6.QtCore import Slot
    class SlowWorker(app_module.TaramaIsci):
        @Slot()
        def kos(self):
            while not self._dur.is_set():
                time.sleep(0.01)
            self.bitti.emit({'result': 'cancelled'})
    monkeypatch.setattr(app_module, 'TaramaIsci', SlowWorker)
    pencere.nav.setCurrentRow(1)
    pencere._tara_baslat(automatic=True)
    _app().processEvents()
    assert not pencere.scan_dialog.isVisible()
    assert pencere.nav.currentRow() == 1
    worker = pencere.isci
    pencere.tara_btn.click()
    assert pencere.isci is worker and pencere.scan_dialog.isVisible()
    pencere.scan_counts.setText('sentetik sayaç')
    pencere.scan_dialog.close()
    assert pencere.isci is worker and not pencere.scan_dialog.isVisible()
    pencere.tara_btn.click()
    assert pencere.scan_counts.text() == 'sentetik sayaç'
    pencere._tara_iptal()
    deadline = time.monotonic() + 5
    while pencere.isci_thread is not None:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline
    assert pencere.tara_btn.text() == 'Şimdi tara'
    assert pencere.nav.item(2).text() == 'Tarama'


def test_015_time_source_and_layout(pencere, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *a: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: None)
    from evrakci import sched
    monkeypatch.setattr(sched, "autostart_clear", lambda *a: None)
    from PySide6.QtCore import QTime, Qt
    from PySide6.QtWidgets import QPushButton
    for hour, minute in [(0, 0), (23, 59)]:
        pencere.scan_time_edit.setTime(QTime(hour, minute))
        pencere._ayar_kaydet()
        assert migrate.get_setting(pencere.con, 'saat') == str(hour)
        assert migrate.get_setting(pencere.con, 'dakika') == str(minute)
        assert pencere.tarama_time.text() == f'{hour:02}:{minute:02}'
    assert pencere.source_path.text() == pencere.kok_model.item(0).data()
    assert not any(b.text() == 'Hakkında' for b in pencere.findChildren(QPushButton))
    pencere.show()
    _app().processEvents()
    buttons = [b for b, _ in pencere.rail_actions]
    assert buttons[0].y() == buttons[1].y()
    assert pencere.rail_toggle.y() < buttons[0].y()
    assert all(b.width() >= b.fontMetrics().horizontalAdvance(b.text()) + 20 for b in buttons)
    pencere._nav_toggle()
    _app().processEvents()
    assert pencere.nav.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert pencere.nav.horizontalScrollBar().maximum() == 0


def test_015_pause_ack_and_tray_reset(pencere):
    from evrakci.app import TaramaIsci
    worker = TaramaIsci(pencere.kasa_yolu, PW, [])
    pencere.isci = worker
    pencere._tara_duraklat()
    assert pencere._scan_status == 'pausing'
    pencere._scan_paused(True)
    assert pencere._scan_status == 'paused'
    assert pencere.tara_btn.text() == 'Tarama duraklatıldı'
    pencere._tara_duraklat()
    assert pencere._scan_status == 'running'
    pencere._tara_iptal()
    pencere._scan_paused(False)
    assert pencere._scan_status == 'cancelling'
    pencere._scan_state('idle')
    if pencere.tepsi is not None:
        assert not pencere._tray_timer.isActive()
    pencere.isci = None
    assert len(theme.scan_icons()) == 8
    assert len({icon.cacheKey() for icon in theme.scan_icons()}) == 8

def test_015_lock_clears_dialog(pencere, monkeypatch):
    pencere._scan_show()
    pencere.popup_scope.setText('sentetik yol')
    pencere.scan_current.setText('sentetik dosya')
    pencere._scan_metrics_update({'found':100})
    pencere.kilitle()
    assert not pencere.scan_dialog.isVisible()
    assert not pencere.popup_scope.text()
    assert all(not v.text() for v in pencere.scan_metrics.values())
    assert not pencere.scan_log.toPlainText()


def test_015_without_tray(pencere):
    tray = pencere.tepsi
    pencere.tepsi = None
    try:
        for state in ('running','pausing','paused','cancelling','idle'):
            pencere._scan_state(state)
        assert pencere.tara_btn.text() == 'Şimdi tara'
        pencere._scan_show()
        assert pencere.scan_dialog.isVisible()
    finally:
        pencere.tepsi = tray


def test_020_ai_requires_explicit_send_and_clears_on_lock(pencere):
    import json
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtNetwork import QNetworkReply

    class FakeReply(QObject):
        finished = Signal()

        def __init__(self, payload):
            super().__init__()
            self.payload = payload
            self.aborted = False

        def error(self):
            return QNetworkReply.NoError

        def readAll(self):
            return self.payload

        def abort(self):
            self.aborted = True

    class FakeNetwork:
        def __init__(self):
            self.calls = []
            self.reply = None

        def post(self, request, body):
            self.calls.append((request, body))
            return self.reply

    fake = FakeNetwork()
    pencere.ai_network = fake
    pencere.nav.setCurrentRow(6)
    pencere.ai_question.setText("Ankara arayüz testi")
    pencere._ai_prepare()
    assert pencere.ai_preview is not None
    assert pencere.ai_send.isEnabled()
    assert pencere.ai_reply is None
    assert "Ankara" in pencere.ai_preview_box.toPlainText()
    assert not fake.calls
    pencere._ai_send()
    assert not fake.calls
    sid = pencere.ai_preview.sources[0]["id"]
    fake.reply = FakeReply(json.dumps({"candidates": [{"content": {"parts": [{"text":
        json.dumps({"answer": "Ankara belgesi bulundu.", "source_ids": [sid]})}]}}]}).encode())
    migrate.set_setting(pencere.con, "gemini_api_key", "synthetic-key")
    from pathlib import Path
    assert b"synthetic-key" not in Path(pencere.kasa_yolu).read_bytes()
    pencere._ai_send()
    assert len(fake.calls) == 1
    assert b"Ankara" in fake.calls[0][1]
    assert b"synthetic-key" not in fake.calls[0][1]
    fake.reply.finished.emit()
    assert "Ankara belgesi" in pencere.ai_answer.toPlainText(), pencere.ai_status.text()
    assert pencere.ai_sources.count() == 1
    fake.reply = FakeReply(b"")
    pencere._ai_send()
    assert pencere.ai_reply is fake.reply
    pencere.ai_question.setText("Değişen soru")
    assert fake.reply.aborted and pencere.ai_reply is None
    pencere.kilitle()
    assert pencere.ai_preview is None
    assert not pencere.ai_preview_box.toPlainText()
    assert not pencere.ai_answer.toPlainText()
    assert not pencere.ai_key_input.text()
