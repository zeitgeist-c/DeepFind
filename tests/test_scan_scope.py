"""Tarama kapsami testleri: otomatik tarama kullanicinin sectigi koklerde kalir.

Kurallar:
- Secilmeyen kardes kokler / devre disi kokler taramaya eklenmez.
- Elle taramanin kapsami kaydedilir; otomatik (saatli/izleyici) tarama onu kullanir.
- Kapsam kaydi silme degildir; devre disi kokun kaydi korunur.
- Kapsam daraltmak indeks/belge silmez.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import migrate, vault  # noqa: E402


def _profil(tmp_path):
    con = vault.open_vault(str(tmp_path / "kasa.db"), "sozlesme-testi-123")
    migrate.ensure_current(con)
    return con


class _Tasiyici:
    """Kapsam yardimcilarini GUI kurmadan cagirmak icin minimal tasiyici."""

    def __init__(self, con):
        self.con = con


def _pencere(con):
    from deepfind.app import AnaPencere
    for ad in ("_kokler", "_kapsam_kaydet", "_kayitli_kapsam", "_otomatik_kapsam"):
        setattr(_Tasiyici, ad, getattr(AnaPencere, ad))
    _Tasiyici._under = staticmethod(AnaPencere._under)
    return _Tasiyici(con)


def _cagir(p, ad, *a):
    return getattr(p, ad)(*a)


def test_secili_kok_ve_alt_kok_yalniz_a(tmp_path):
    con = _profil(tmp_path)
    a = tmp_path / "A"
    b = tmp_path / "B"
    (a / "alt").mkdir(parents=True)
    b.mkdir()
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)",
                (str(a), os.path.normpath(str(a)).lower()))
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)",
                (str(b), os.path.normpath(str(b)).lower()))
    con.commit()
    p = _pencere(con)
    # Elle taramada yalniz A secildi -> kapsam kaydedilir.
    _cagir(p, "_kapsam_kaydet", [str(a)])
    kapsam = _cagir(p, "_kayitli_kapsam")
    assert kapsam == [str(a)]
    assert _cagir(p, "_under", str(a / "alt"), str(a)) is True
    assert _cagir(p, "_under", str(b), str(a)) is False
    # Otomatik tarama A ile sinirli; B kendiliginden eklenmez.
    oto = _cagir(p, "_otomatik_kapsam")
    assert oto == [str(a)]
    # Kapsam daraltmasi kok kayitlarini silmez (B hala kayitli).
    kayitli = [r[0] for r in con.execute("SELECT display_path FROM roots").fetchall()]
    assert str(b) in kayitli
    con.close()


def test_devre_disi_kok_otomatik_kapsama_girmez(tmp_path):
    con = _profil(tmp_path)
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()
    con.execute("INSERT INTO roots(display_path, canonical_path, enabled) VALUES (?,?,1)",
                (str(a), os.path.normpath(str(a)).lower()))
    con.execute("INSERT INTO roots(display_path, canonical_path, enabled) VALUES (?,?,0)",
                (str(b), os.path.normpath(str(b)).lower()))
    con.commit()
    p = _pencere(con)
    _cagir(p, "_kapsam_kaydet", [str(a), str(b)])
    # B devre disi -> kayitli kapsamdan dusulur, kayit korunur.
    assert _cagir(p, "_kayitli_kapsam") == [str(a)]
    assert con.execute("SELECT COUNT(*) FROM roots WHERE enabled=0").fetchone()[0] == 1
    con.close()


def test_kaldirilan_kok_kapsamdan_duser(tmp_path):
    con = _profil(tmp_path)
    a = tmp_path / "A"
    a.mkdir()
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)",
                (str(a), os.path.normpath(str(a)).lower()))
    con.commit()
    p = _pencere(con)
    _cagir(p, "_kapsam_kaydet", [str(a)])
    con.execute("DELETE FROM roots WHERE display_path=?", (str(a),))
    con.commit()
    assert _cagir(p, "_kayitli_kapsam") == []
    con.close()


def test_saatli_tarama_yeni_profilde_kapali(tmp_path):
    con = _profil(tmp_path)
    assert migrate.get_setting(con, "planli_tarama", "0") == "0"
    con.close()


def test_saatli_tarama_mevcut_kullanicida_korunur(tmp_path):
    con = _profil(tmp_path)
    # Onceki surumde saatli tarama kullanilmis: son_slot kayitli.
    migrate.set_setting(con, "son_slot", "2026-09-26T12:30:00")
    con.execute("DELETE FROM settings WHERE k='planli_tarama'")
    con.commit()
    assert migrate.ensure_schedule_optin(con) == "1"
    assert migrate.get_setting(con, "planli_tarama", "0") == "1"
    con.close()
