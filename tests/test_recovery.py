"""Kurtarma anahtari: uretim, konteyner, kurtarma, yenileme, kaldirma.

Kontrat:
- Kurtarma anahtari kasayi acar; yanlis anahtar temiz reddedilir.
- Anahtar diske YALNIZ kasa klasorundeki anahtar dosyasina yazilir (tasarim B).
- Kurtarma sonrasi kasa YENI sifreyle acilir; eski sifre ve kurtarma anahtari gecersiz olur;
  yeni kurtarma anahtari uretilir.
- Sifre degisiminde kurtarma anahtari kendiliginden guncellenir.
- Kurtarma kaynaga (belgelere) dokunmaz.
"""
from semantic_helpers import indexed_content
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import (backup, coordinator, recovery, schema, search, vault)  # noqa: E402
from evrakci.migrate import ensure_current  # noqa: E402

PW = "kurtarma-sifresi-1234"
YENI = "yeni-kurtarma-sifresi-5678"


def _kasa(tmp_path, pw=PW):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, pw)
    schema.ensure_schema(con)
    ensure_current(con)
    return con, db


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


# --- 1. Anahtar uretimi ------------------------------------------------------

def test_anahtar_bicimi_ve_alfabesi():
    k = recovery.new_key()
    assert k.startswith("EVKC-")
    govde = k[5:].replace("-", "")
    assert len(govde) == 32, k
    yasak = set("ILOU01")
    assert not (set(govde) & yasak), f"karistirilabilir harf var: {set(govde) & yasak}"


def test_anahtarlar_tekil():
    kumeler = {recovery.new_key() for _ in range(200)}
    assert len(kumeler) == 200


@pytest.mark.parametrize("girilen", [
    "evkc-nzx27-hw557-bthor-gtaqa-xpvy4-6wnfe-uj",
    "EVKC NZX27 HW557 BTHOR GTAQA XPVY4 6WNFE UJ",
    "  EVKC-NZX27-HW557-BTHOR-GTAQA-XPVY4-6WNFE-UJ  ",
    "NZX27-HW557-BTHOR-GTAQA-XPVY4-6WNFE-UJ",
])
def test_normalize_kullanici_toleransi(girilen):
    assert recovery.normalize(girilen) == "EVKC-NZX27-HW557-BTHOR-GTAQA-XPVY4-6WNFE-UJ"


def test_normalize_bicimsiz_girdi():
    assert recovery.normalize("") == ""
    assert recovery.normalize("!!!") == ""


# --- 2. Konteyner: olustur / dogrula / kurtar --------------------------------

def test_konteyner_olustur_ve_dogrula(tmp_path):
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    yol = recovery.write_container(db, PW, anahtar)
    assert os.path.isfile(yol)
    v = recovery.verify_container(yol, anahtar)
    assert v["ok"] and v["kasa"] == os.path.abspath(db)
    con.close()


def test_yanlis_anahtar_dogrulamada_reddedilir(tmp_path):
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    yol = recovery.write_container(db, PW, anahtar)
    con.close()
    v = recovery.verify_container(yol, recovery.new_key())
    assert v["ok"] is False


def test_konteyner_acik_metin_sizdirmaz(tmp_path):
    con, db = _kasa(tmp_path)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('gizli-yol/belge.pdf','belge.pdf','.pdf')")
    con.commit()
    yol = recovery.write_container(db, PW, recovery.new_key())
    con.close()
    ham = open(yol, "rb").read()
    assert PW.encode() not in ham, "kasa sifresi konteynerde acik"
    assert b"gizli-yol" not in ham, "dosya yolu konteynerde acik"


# --- 3. Kurtarma akisi -------------------------------------------------------

def test_kurtarma_kasayi_acar_ve_yeni_sifre_kurar(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara kurtarma testi 2024")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    assert indexed_content(con, "kurtarma")
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    con.close()

    rap = recovery.recover(db, anahtar, YENI, backup_dir=str(tmp_path / "backups"))
    assert rap["ok"] and rap["yeni_anahtar"].startswith("EVKC-")

    # yeni sifre calisir, indeks yerinde
    con2 = vault.open_vault(db, YENI)
    assert indexed_content(con2, "kurtarma"), "kurtarma sonrasi indeks korunmali"
    con2.close()
    # eski sifre artik acmaz
    with pytest.raises(Exception):
        vault.open_vault(db, PW)
    # eski kurtarma anahtari artik gecersiz
    v = recovery.verify_container(recovery.container_path(db), anahtar)
    assert v["ok"] is False
    assert os.path.isfile(recovery.key_path(db))
    assert recovery.load_key(db) == rap["yeni_anahtar"]


def test_kurtarma_anahtari_yoksa_eski_sifre_korunur(tmp_path):
    con, db = _kasa(tmp_path)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('a.pdf','a.pdf','.pdf')")
    con.commit()
    con.close()
    with pytest.raises(Exception):
        recovery.recover(db, recovery.new_key(), YENI)
    con2 = vault.open_vault(db, PW)  # hicbir sey bozulmadi
    assert con2.execute("SELECT count(*) FROM files").fetchone()[0] == 1
    con2.close()


def test_kurtarma_islem_kaynaga_dokunmaz(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara dokunulmazlik")
    time.sleep(2.5)
    once = {}
    for dp, _dn, fn in os.walk(kok):
        for f in fn:
            p = os.path.join(dp, f)
            st = os.stat(p)
            once[p] = (st.st_size, st.st_mtime_ns)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    con.close()
    recovery.recover(db, anahtar, YENI, backup_dir=str(tmp_path / "backups"))
    sonra = {}
    for dp, _dn, fn in os.walk(kok):
        for f in fn:
            p = os.path.join(dp, f)
            st = os.stat(p)
            sonra[p] = (st.st_size, st.st_mtime_ns)
    assert once == sonra, "kurtarma kaynaga yazdi"


# --- 4. Yenile / kaldir / sifre degisimi -------------------------------------

def test_yenile_eskiyi_gecersiz_kilar(tmp_path):
    con, db = _kasa(tmp_path)
    eski = recovery.new_key()
    recovery.write_container(db, PW, eski)
    yeni = recovery.refresh(db, PW)
    assert yeni != eski
    assert recovery.verify_container(recovery.container_path(db), yeni)["ok"]
    assert recovery.verify_container(recovery.container_path(db), eski)["ok"] is False
    con.close()


def test_kaldir_geri_donus_yok(tmp_path):
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    recovery.write_key_file(db, anahtar)
    recovery.remove(db)
    assert not os.path.exists(recovery.container_path(db))
    assert not os.path.exists(recovery.key_path(db))
    assert recovery.load_key(db) == ""
    con.close()


def test_sifre_degisince_anahtar_guncellenir(tmp_path):
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    con.close()
    # urun akisi: change_password -> kurtarma yenilenir
    backup.change_password(db, PW, YENI, str(tmp_path / "backups"))
    anahtar2 = recovery.load_key(db)
    assert anahtar2 and anahtar2 != anahtar
    v = recovery.verify_container(recovery.container_path(db), anahtar2)
    assert v["ok"], "sifre degisince kurtarma anahtari guncellenmeli"


# --- 5. Durum ve kenar durumlar ---------------------------------------------

def test_durum_raporu(tmp_path):
    con, db = _kasa(tmp_path)
    assert recovery.status(db)["var"] is False
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    recovery.write_key_file(db, anahtar)
    durum = recovery.status(db)
    assert durum["var"] is True and durum["kasa_eslesiyor"] is True
    con.close()
    # kasa degisince eslesme duser
    con2 = vault.open_vault(db, PW)
    con2.execute("INSERT INTO files(path,name,ext) VALUES ('x.pdf','x.pdf','.pdf')")
    con2.commit()
    con2.close()
    assert recovery.status(db)["kasa_eslesmiyor"] is True


def test_konteyner_bozuksa_temiz_hata(tmp_path):
    con, db = _kasa(tmp_path)
    con.close()
    yol = recovery.container_path(db)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb") as fh:
        fh.write(os.urandom(4096))
    v = recovery.verify_container(yol, recovery.new_key())
    assert v["ok"] is False
    with pytest.raises(Exception):
        recovery.recover(db, recovery.new_key(), YENI)


def test_belge_metni_anahtari_icerir(tmp_path):
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    metin = recovery.document_text(db, anahtar)
    assert anahtar in metin
    assert "EVKC" in metin
    # Biçimli belgede anahtar okunabilirlik için gruplanır; ama belgeden
    # normalize edilerek aynen geri okunabilmelidir (yazdırılan belge işe yaramalı).
    guzel = recovery.document_text(db, anahtar, bicimli=True)
    assert recovery.normalize(guzel) == anahtar
    con.close()


def test_anahtar_dosyasindan_geri_okunur(tmp_path):
    """Yazdırılan belge kaydedilip geri okunduğunda aynı anahtarı vermeli."""
    con, db = _kasa(tmp_path)
    anahtar = recovery.new_key()
    recovery.write_container(db, PW, anahtar)
    recovery.write_key_file(db, anahtar)
    assert recovery.load_key(db) == anahtar
    # dosyayı başka yere kopyalamak da çalışır (kullanıcı belgeyi saklar)
    kopya = tmp_path / "yazdirilacak.txt"
    kopya.write_text(recovery.document_text(db, anahtar, bicimli=True), encoding="utf-8")
    assert recovery.normalize(kopya.read_text(encoding="utf-8")) == anahtar
    con.close()
