"""Saatli tarama davranisi (uygulama katmani).

Kurallar:
- Kurulum/ilk acilis/yeniden acilis kendiliginden tarama baslatmaz.
- Saatli tarama kapaliysa otomatik tarama yok.
- Saatinde acik -> tek tarama.
- Tarama surerken saat gelirse ikinci is/kuyruk yok.
- Yalniz tray/arka plan (pencere kapali) saatli tarama izni sayilmaz.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import migrate, vault  # noqa: E402


class _Durum:
    def __init__(self):
        self.mesajlar = []

    def showMessage(self, metin, *_a):
        self.mesajlar.append(metin)


class _Pencere:
    """_zamanlayici_kontrol icin gereken en kucuk pencere yuzeyi."""

    _zamanlayici_kontrol = None  # testte AnaPencere'den baglanir

    def __init__(self, con, kok, gorunur=True, acilis=None):
        self.con = con
        # Uygulama slot anindan once acilmis sayilir (acilis tarama tetiklemez).
        self._acilis = acilis or (dt.datetime.now() - dt.timedelta(hours=1))
        self._kok = kok
        self._locked = False
        self._gorunur = gorunur
        self.isci_thread = None
        self._kaldir_thread = None
        self._haric_thread = None
        self.durum = _Durum()
        self.baslatilan = []

    def isVisible(self):
        return self._gorunur

    def _kokler(self):
        return [self._kok]

    def _tara_baslat(self, checked=False, *, automatic=False, roots=None):
        self.baslatilan.append(("automatic" if automatic else "manual", roots))


def _hazirla(tmp_path, planli="1", saat_ver=None):
    con = vault.open_vault(str(tmp_path / "kasa.db"), "zamanlama-testi-123")
    migrate.ensure_current(con)
    kok = tmp_path / "izole"
    kok.mkdir()
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)",
                (str(kok), os.path.normpath(str(kok)).lower()))
    simdi = saat_ver or dt.datetime.now()
    migrate.set_setting(con, "planli_tarama", planli)
    migrate.set_setting(con, "saat", str(simdi.hour))
    migrate.set_setting(con, "dakika", str(simdi.minute))
    migrate.set_setting(con, "gecikme", "0")
    migrate.set_setting(con, "son_slot", "")
    con.execute("DELETE FROM settings WHERE k='tarama_ele_alinan_gun'")
    con.commit()
    if _Pencere._zamanlayici_kontrol is None:
        from deepfind.app import AnaPencere
        _Pencere._zamanlayici_kontrol = AnaPencere._zamanlayici_kontrol
    return con, str(kok)


def test_ilk_acilis_kendiliginden_tarama_baslatmaz(tmp_path):
    con, kok = _hazirla(tmp_path, planli="1")
    p = _Pencere(con, kok)
    p._zamanlayici_kontrol(ilk=True)
    assert p.baslatilan == []
    con.close()


def test_saatli_tarama_kapaliysa_otomatik_tarama_yok(tmp_path):
    con, kok = _hazirla(tmp_path, planli="0")
    p = _Pencere(con, kok)
    p._zamanlayici_kontrol()
    assert p.baslatilan == []
    con.close()


def test_saatinde_acik_tek_tarama(tmp_path):
    con, kok = _hazirla(tmp_path, planli="1")
    p = _Pencere(con, kok)
    p._zamanlayici_kontrol()
    assert len(p.baslatilan) == 1
    assert p.baslatilan[0][0] == "automatic"
    con.close()


def test_tarama_surerken_ikinci_is_yok(tmp_path):
    con, kok = _hazirla(tmp_path, planli="1")
    p = _Pencere(con, kok)
    p.isci_thread = object()  # bir tarama suruyor
    p._zamanlayici_kontrol()
    assert p.baslatilan == []
    # Sonradan calisacak otomatik kuyruk yok: gun ele alindi olarak isaretlendi.
    assert migrate.get_setting(con, "tarama_ele_alinan_gun", "") == dt.date.today().isoformat()
    p.isci_thread = None
    p._zamanlayici_kontrol()  # ayni gun tekrar denenmez
    assert p.baslatilan == []
    con.close()


def test_slot_anindan_sonra_acilis_tarama_baslatmaz(tmp_path):
    con, kok = _hazirla(tmp_path, planli="1")
    p = _Pencere(con, kok, acilis=dt.datetime.now())  # slot aninda acildi
    p._zamanlayici_kontrol()
    assert p.baslatilan == []
    assert migrate.get_setting(con, "tarama_ele_alinan_gun", "") == dt.date.today().isoformat()
    con.close()


def test_yalniz_tray_arka_plan_saatli_tarama_sayilmaz(tmp_path):
    con, kok = _hazirla(tmp_path, planli="1")
    p = _Pencere(con, kok, gorunur=False)
    p._zamanlayici_kontrol()
    assert p.baslatilan == []
    con.close()
