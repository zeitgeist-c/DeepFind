"""Şifresiz kasa testleri: kurulum işareti, algılama, şifre ekleme, arayüz."""
import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import backup, bootstrap, migrate, recovery, schema, vault  # noqa: E402

PW = "yeni-sifre-123456789"


def _bos_kasa(tmp_path, sentinel=True, ad="k.db"):
    db = str(tmp_path / ad)
    pw = vault.SIFRESIZ_ANAHTAR if sentinel else PW
    con = vault.open_vault(db, pw)
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    con.close()
    return db


def _bekle(pen, app):
    deadline = time.monotonic() + 20
    while pen._search_thread is not None or pen.isci_thread is not None \
            or pen.onizleme.busy() or pen._jobs:
        app.processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline


def test_pw01_kurulum_sifresiz_isaretler(tmp_path):
    """Bootstrap, iç anahtarla kurulan kasaya şifresiz işaretini yazar."""
    db = str(tmp_path / "Data" / "k.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    isci = bootstrap.Bootstrap(db, vault.SIFRESIZ_ANAHTAR,
                               {"kokler": [], "tema": "sistem",
                                "sirket_kurali": "belirlenemiyor"})
    isci.run()
    con = vault.open_vault(db, vault.SIFRESIZ_ANAHTAR)
    try:
        assert migrate.get_setting(con, "kasa_sifresiz") == "1"
        assert migrate.get_setting(con, "kurulum_tamam") == "1"
    finally:
        con.close()
    assert vault.sifresiz_mi(db) is True


def test_pw02_sifresiz_mi_ayrimi(tmp_path):
    """İşaret yoksa ya da kasa şifreliyse şifresiz sayılmaz."""
    sifresiz = _bos_kasa(tmp_path, sentinel=True)
    assert vault.sifresiz_mi(sifresiz) is False  # iç anahtar açar ama işaret yok
    con = vault.open_vault(sifresiz, vault.SIFRESIZ_ANAHTAR)
    migrate.set_setting(con, "kasa_sifresiz", "1")
    con.close()
    assert vault.sifresiz_mi(sifresiz) is True
    normal = _bos_kasa(tmp_path, sentinel=False, ad="n.db")
    assert vault.sifresiz_mi(normal) is False


def test_pw03_sifre_eklenince_ic_anahtar_gecersiz(tmp_path):
    """Şifre eklenince (rekey) eski iç anahtar açmaz; işaret 0 olur."""
    db = _bos_kasa(tmp_path, sentinel=True)
    con = vault.open_vault(db, vault.SIFRESIZ_ANAHTAR)
    migrate.set_setting(con, "kasa_sifresiz", "1")
    con.close()
    backup.change_password(db, vault.SIFRESIZ_ANAHTAR, PW, str(tmp_path / "Backups"))
    with pytest.raises(Exception):
        vault.open_vault(db, vault.SIFRESIZ_ANAHTAR)
    con = vault.open_vault(db, PW)
    migrate.set_setting(con, "kasa_sifresiz", "0")
    con.close()
    assert vault.sifresiz_mi(db) is False


def test_pw04_sifre_eklenince_kurtarma_anahtari(tmp_path):
    """Şifre eklenen kasada kurtarma anahtarı hazırlanabilir (ensure_exists)."""
    db = _bos_kasa(tmp_path, sentinel=True)
    anahtar = recovery.ensure_exists(db, vault.SIFRESIZ_ANAHTAR)
    assert anahtar.startswith("EVKC-")
    durum = recovery.status(db)
    assert durum.get("var") is True
    assert recovery.load_key(db) == anahtar


def test_pw05_sihirbaz_sifresiz_secenegi():
    """Sihirbazda boş şifre ve 'kullanmayacağım' kutusu kabul edilir."""
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from evrakci.wizard import Sihirbaz
    s = Sihirbaz()
    s.restart()
    s.next()  # şifre sayfası
    assert s.validateCurrentPage() is True  # boş alanlar: şifresiz kabul
    assert s.secim["sifre"] == ""
    s.s1.setText("kisa")
    s.s2.setText("kisa")
    assert s.validateCurrentPage() is False
    s.s1.clear()
    s.s2.clear()
    s.sifresiz_kutu.setChecked(True)
    assert s.s1.isEnabled() is False and s.s2.isEnabled() is False
    assert s.validateCurrentPage() is True
    assert s.secim["sifre"] == ""
    s.sifresiz_kutu.setChecked(False)
    assert s.s1.isEnabled() is True
    s.close()
    s.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_pw06_pencere_kilit_yok_ve_sifre_ekle(tmp_path, monkeypatch):
    """Şifresiz pencerede kilit yok; 'Şifre ekle' akışı rekey + kurtarma yapar."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    db = _bos_kasa(tmp_path, sentinel=True)
    con = vault.open_vault(db, vault.SIFRESIZ_ANAHTAR)
    migrate.set_setting(con, "kasa_sifresiz", "1")
    con.close()
    from evrakci import app as app_mod
    pen = app_mod.AnaPencere(db, vault.SIFRESIZ_ANAHTAR)
    try:
        assert pen.sifresiz is True
        assert all(title != "Kasayı kilitle" for _b, title in pen.rail_actions)
        pen.kilitle()  # şifresiz kasada kilitleme yok sayılır
        assert pen._locked is False and pen.con is not None
        pen._kurtarma_tazele()
        assert "gerekmez" in pen.kurtarma_durum.text()
        assert pen.kurtarma_olustur.isEnabled() is False
        assert pen.sifre_btn.text() == "Şifre ekle"
        _bekle(pen, app)  # açılış işleri (OCR) bitsin; diyalog akışı için gerekli

        class _Sahte:
            """Kabul eden sahte şifre diyaloğu."""

            def __init__(self, *a, **k):
                class _T:
                    def __init__(self, s):
                        self._s = s

                    def text(self):
                        return self._s

                    def clear(self):
                        pass
                self.new = _T(PW)
                self.confirm = _T(PW)

            def exec(self):
                return 1  # QDialog.Accepted

        monkeypatch.setattr(app_mod, "ParolaDialog", _Sahte)
        monkeypatch.setattr(app_mod.QMessageBox, "information", lambda *a, **k: None)
        monkeypatch.setattr(app_mod.QMessageBox, "critical", lambda *a, **k: None)
        pen._sifre_ekle()
        assert pen.sifresiz is False
        assert pen.sifre_btn.text() == "Parolayı değiştir"
        assert pen._sifre == PW
        assert recovery.load_key(db).startswith("EVKC-")
        assert vault.sifresiz_mi(db) is False
        acik = vault.open_vault(db, PW)
        acik.close()
        with pytest.raises(Exception):
            vault.open_vault(db, vault.SIFRESIZ_ANAHTAR)
    finally:
        pen._exiting = True
        pen.close()
        _bekle(pen, app)
        pen.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
