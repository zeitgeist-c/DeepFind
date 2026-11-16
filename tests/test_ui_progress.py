"""Ilerleme cubuklari + kesik yazi regresyonu (offscreen, kucuk veri).

Sozlesme: yuzde metinli/belirsiz cubuklar ortak `ilerleme_cubugu`
bileseninden gecer (>=20px, ortali metin); ince global stil yalniz
metinsiz mesgul gostergelerinde kalir. Gercek indirme/tarama yok.
"""
import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from deepfind import migrate, schema, vault  # noqa: E402
from deepfind.migrate import ensure_v5  # noqa: E402
from deepfind.migrate import ensure_v7  # noqa: E402

PW = "cubuk-sifresi-1234"
APP = None


def _app():
    global APP
    if APP is None:
        APP = QApplication.instance() or QApplication([])
    return APP


def _bar_metin_sigar(bar, genislik=460):
    """Yuzde metni kirpiliyor mu: cubuk yuksekligi yazi yuksekligini tutmali."""
    from PySide6.QtGui import QFontMetrics

    bar.setFixedWidth(genislik)
    bar.show()
    _app().processEvents()
    time.sleep(0.05)
    _app().processEvents()
    yukseklik = bar.height()
    yazi = QFontMetrics(bar.font()).height()
    return yukseklik, yazi


def test_ilerleme_cubugu_sozlesmesi():
    _app()
    from deepfind.ui import ilerleme_cubugu

    bar = ilerleme_cubugu()
    assert bar.isTextVisible()
    assert "text-align: center" in bar.styleSheet()
    yukseklik, yazi = _bar_metin_sigar(bar)
    assert yukseklik >= 20, yukseklik
    assert yukseklik >= yazi, (yukseklik, yazi)
    faz = ilerleme_cubugu(20)
    yukseklik_faz, _ = _bar_metin_sigar(faz)
    assert yukseklik_faz == 20, yukseklik_faz


def test_model_ilerleme_toplam_yoksa_belirsiz():
    _app()
    from PySide6.QtWidgets import QLabel

    from deepfind.model_ui import _ilerleme_uygula
    from deepfind.ui import ilerleme_cubugu

    bar = ilerleme_cubugu()
    durum = QLabel()
    _ilerleme_uygula(bar, durum, 37 * 1024 * 1024, 100 * 1024 * 1024)
    assert (bar.minimum(), bar.maximum()) == (0, 100)
    assert bar.value() == 37
    _ilerleme_uygula(bar, durum, 5 * 1024 * 1024, 0)
    assert (bar.minimum(), bar.maximum()) == (0, 0)
    yukseklik, yazi = _bar_metin_sigar(bar)
    assert yukseklik >= 20 and yukseklik >= yazi


def test_model_indirme_penceresi_cubuk_sigar(tmp_path, monkeypatch):
    _app()
    from PySide6.QtWidgets import QDialog, QProgressBar

    from deepfind.model_ui import indir_penceresi

    olcu: dict = {}

    def sahte_exec(pencere):
        from PySide6.QtWidgets import QApplication as _QA

        bar = pencere.findChild(QProgressBar)
        assert bar is not None
        pencere.show()
        _QA.processEvents()
        olcu["h"] = bar.height()
        olcu["yazi"] = bar.fontMetrics().height()
        # Buyutulmus pencerede cubuk ayni kalir (max-height sabiti).
        pencere.resize(660, 600)
        _QA.processEvents()
        olcu["h_buyuk"] = bar.height()
        return QDialog.Rejected

    monkeypatch.setattr(QDialog, "exec", sahte_exec)
    ebeveyn = QWidget()
    try:
        indir_penceresi(ebeveyn)
    finally:
        ebeveyn.deleteLater()
    assert olcu["h"] >= 20, olcu
    assert olcu["h"] >= olcu["yazi"], olcu
    assert olcu["h_buyuk"] == olcu["h"], olcu


def test_ocr_hazirlik_cubuk_sigar():
    _app()
    from PySide6.QtWidgets import QProgressBar

    from deepfind.ocr_setup_ui import OcrSetupDialog

    pencere = OcrSetupDialog()
    bar = pencere.findChild(QProgressBar)
    assert bar is not None
    pencere.show()
    yukseklik, yazi = _bar_metin_sigar(bar, genislik=520)
    assert yukseklik >= 20, yukseklik
    assert yukseklik >= yazi, (yukseklik, yazi)
    pencere.close()


def test_acilis_cubuk_sigar(tmp_path):
    _app()
    from PySide6.QtWidgets import QProgressBar

    from deepfind.startup import OpeningDialog

    pencere = OpeningDialog(str(tmp_path / "kasa.db"),
                            str(tmp_path / "yedek"))
    bar = pencere.findChild(QProgressBar)
    assert bar is not None
    # Toplam bilinmezken belirsiz animasyon gorunur yukseklikte.
    assert (bar.minimum(), bar.maximum()) == (0, 0)
    pencere.show()
    yukseklik, yazi = _bar_metin_sigar(bar, genislik=480)
    assert yukseklik >= 20, yukseklik
    assert yukseklik >= yazi, (yukseklik, yazi)
    pencere.close()


@pytest.fixture()
def pencere(tmp_path):
    _app()
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.commit()
    con.close()
    from deepfind.app import AnaPencere

    pen = AnaPencere(db, PW)
    pen.show()
    _app().processEvents()
    yield pen
    try:
        pen._thumblari_durdur()
    except Exception:
        pass
    pen._exiting = True
    pen.close()
    pen.deleteLater()


def test_tarama_ve_guncelleme_cubuklari_sigar(pencere):
    from PySide6.QtWidgets import QProgressBar

    for bar, en_az in ((pencere.tarama_bar, 20),
                       (pencere.scan_phase_bar, 18),
                       (pencere.update_bar, 20)):
        assert isinstance(bar, QProgressBar)
        bar.show()
        yukseklik, yazi = _bar_metin_sigar(bar, genislik=760)
        assert yukseklik >= en_az, (bar, yukseklik)
        assert yukseklik >= yazi, (yukseklik, yazi)
    assert pencere.scan_progress_detail.wordWrap()


def test_tarama_ilerleme_yuzde_ve_belirsiz(pencere):
    pencere.scan_dialog.show()
    _app().processEvents()
    pencere._scan_progress({
        "inventory_ready": True, "inventory_complete": True,
        "documents_total": 200, "documents_done": 46,
        "phase_key": "content", "phase_done": 10, "phase_total": 40,
        "found": 200, "done": 40, "pending": 5, "skipped": 0,
        "ocr_done": 0, "failed": 0, "ocr_failed": 0,
        "stage": "İçerik okunuyor", "path": "b.pdf", "item_result": "done",
    })
    _app().processEvents()
    assert pencere.tarama_bar.value() == 23
    assert "%" in pencere.tarama_bar.text()
    assert "46" in pencere.scan_progress_detail.text()
    assert pencere.scan_phase_bar.isVisible()
    # Envanter henuz kesinlesmediyse belirsiz cubuk + aciklama.
    pencere._scan_progress({"inventory_ready": False, "found": 7,
                            "stage": "Klasörler keşfediliyor", "path": "kok"})
    _app().processEvents()
    assert (pencere.tarama_bar.minimum(), pencere.tarama_bar.maximum()) == (0, 0)
    assert "7" in pencere.scan_progress_detail.text()
    assert "kesinleşmedi" in pencere.scan_progress_detail.text()
