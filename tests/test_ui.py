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
    pen.close()


def test_tema_uc_mod(pencere):
    _app()
    assert theme.apply(_app(), "acik") == "acik"
    assert theme.apply(_app(), "koyu") == "koyu"
    assert theme.resolve("sistem", True) == "koyu"
    assert theme.resolve("sistem", False) == "acik"


def test_arama_sonuc_ve_onizleme(pencere, tmp_path):
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    assert pencere.sonuc_model.rowCount() >= 1
    idx = pencere.sonuc_model.index(0, 0)
    pencere._sec(idx)
    assert pencere.onizleme.baslik.text() == "belge.pdf"
    assert "Sayfa" in pencere.onizleme.bilgi.text()


def test_bos_sorgu_tum_arsivi_listelemez(pencere):
    pencere.arama_kutu.setText("")
    pencere._ara_simdi()
    assert pencere.sonuc_model.rowCount() == 0


def test_sihirbaz_sayfa_ve_sifre_kurali():
    _app()
    from evrakci.wizard import Sihirbaz
    s = Sihirbaz()
    assert s.pageIds() and len(s.pageIds()) == 6
    s.restart()
    s.next()  # sifre sayfasi (page 1)
    s.s1.setText("kisa")
    s.s2.setText("kisa")
    assert s.validateCurrentPage() is False
    s.s1.setText("uzun-sifre-1234")
    s.s2.setText("uzun-sifre-1234")
    assert s.validateCurrentPage() is True
    s.close()


def test_kilit_model_temizler(pencere, tmp_path, monkeypatch):
    pencere.arama_kutu.setText("Ankara")
    pencere._ara_simdi()
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
        assert o.goruntu.pixmap() is not None and not o.goruntu.pixmap().isNull()
    finally:
        con.close()
        o.close()


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
