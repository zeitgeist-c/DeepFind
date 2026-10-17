"""OCR testleri (RapidOCR): triyaj/kalite/bellek/temp + kopya-hash kablosu.

Motor gerçekten kuruluysa (rapidocr + modeller) gercek tanima testleri kosar;
aksi halde motorlu testler atlanir, sozlesme testleri (triyaj, bellek, temp,
butce, erteleme) her kosumda dogrulanir.
"""
import os
import sys
import time
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import coordinator, dup, extract, ocr, rank, schema, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402

PW = "test-sifresi-12345"
MOTOR = ocr.engine_ok()[0]
motor_var = pytest.mark.skipif(not MOTOR, reason="RapidOCR zinciri kurulu degil")


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v5(con)
    ensure_v6(con)
    return con, db


def _yaz_pdf(path, satirlar):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    c = canvas.Canvas(path)
    c.setFont("TR", 13)
    for i, ln in enumerate(satirlar):
        c.drawString(72, 750 - i * 30, ln)
    c.save()


def _tara_pdf(path, satirlar, font_px=56):
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_px)
    img = Image.new("RGB", (1600, 300 + 120 * len(satirlar)), "white")
    dr = ImageDraw.Draw(img)
    for i, ln in enumerate(satirlar):
        dr.text((40, 40 + i * 110), ln, fill="black", font=f)
    p = path + ".png"
    img.save(p)
    c = canvas.Canvas(path)
    c.drawImage(ImageReader(p), 72, 300, width=450, height=450 * img.height / img.width)
    c.save()
    os.remove(p)


def _bekle():
    time.sleep(2.5)  # kararlik esigi (STABLE_NS)


@motor_var
def test_triyaj_metinli_sayfada_ocr_yok(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _yaz_pdf(os.path.join(kok, "metin.pdf"),
             ["Ankara Ayşe Yılmaz 2024 vergi levhası", "Belge no BV-1001"])
    _bekle()
    con, db = _kasa(tmp_path)
    st = coordinator.run_scan(con, db, kok)
    assert st["result"] == "complete", st
    n = con.execute("SELECT count(*) FROM segments WHERE kind='ocr_page'").fetchone()[0]
    assert n == 0
    assert con.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
    con.close()


@motor_var
def test_ocr01_taramali_sayfa_okunur(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _tara_pdf(os.path.join(kok, "tarama.pdf"),
              ["Ankara Ayşe Yılmaz 2024 vergi levhası", "Belge no BV-1001"])
    _bekle()
    con, db = _kasa(tmp_path)
    st = coordinator.run_scan(con, db, kok)
    assert st["result"] == "complete", st
    assert st["ocr_done"] == 1, st
    rows = con.execute(
        "SELECT raw_text, method, confidence FROM segments WHERE kind='ocr_page'").fetchall()
    assert len(rows) == 1
    txt, method, conf = rows[0]
    assert "Ankara" in txt and "Ayşe" in txt, txt
    assert method == "basic", method
    assert (conf or 0) > 0
    out = rank.search_ranked(con, "Ankara Ayşe vergi levhası")
    assert out["results"] and out["results"][0]["name"] == "tarama.pdf", out
    con.close()


def test_motor_eksikse_klasik_akis_surer(tmp_path, monkeypatch):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _yaz_pdf(os.path.join(kok, "duz.pdf"), ["Ankara Ayşe 2024 rapor"])
    _bekle()
    monkeypatch.setattr(ocr, "engine_ok", lambda: (False, ["rapidocr-zinciri"]))
    con, db = _kasa(tmp_path)
    st = coordinator.run_scan(con, db, kok)
    assert st["result"] == "complete", st
    n = con.execute("SELECT count(*) FROM segments WHERE kind='ocr_page'").fetchone()[0]
    assert n == 0
    out = rank.search_ranked(con, "Ankara Ayşe rapor")
    assert out["results"], out
    con.close()


def test_motor_eksik_ocr_isi_ertelenir(tmp_path, monkeypatch):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _tara_pdf(os.path.join(kok, "tarama.pdf"), ["Ankara test sayfası"])
    _bekle()
    monkeypatch.setattr(ocr, "engine_ok", lambda: (False, ["rapidocr-zinciri"]))
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    row = con.execute("SELECT index_status, error_code FROM files").fetchone()
    # dosya govde aramada kalir; OCR isi kuyrukta bekler
    assert row[0] in ("partial", "pending"), row
    n = con.execute("SELECT count(*) FROM jobs WHERE kind='ocr'").fetchone()[0]
    assert n >= 1
    con.close()


def test_ram_kapisi_ocr_erteler(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr, "avail_ram", lambda: 1 * 1024**3)
    assert not ocr.ram_allows()
    out, _wd = ocr.ocr_document("yok.pdf", [0], str(tmp_path))
    assert out[0].method == "deferred" and out[0].error_code == "MEMORY_LIMIT"


def test_bozuk_pdf_dosyayi_oldurmez(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr, "engine_ok", lambda: (True, []))
    wd = ocr.temp_dir(str(tmp_path))
    try:
        r = ocr.ocr_page(str(tmp_path / "bozuk.pdf"), 0, wd)
    finally:
        import shutil
        shutil.rmtree(wd, ignore_errors=True)
    assert r.method == "low" and r.error_code == "CORRUPT_DOCUMENT"


def test_temp_cokme_artigi_temizlenir(tmp_path):
    base = os.path.join(str(tmp_path), "ocr-tmp")
    os.makedirs(base)
    eski = os.path.join(base, "ocr-eski")
    os.makedirs(eski)
    import time as _t
    eski_zaman = _t.time() - 90000
    os.utime(eski, (eski_zaman, eski_zaman))
    assert ocr.clean_stale(str(tmp_path)) == 1
    assert not os.path.exists(eski)


def test_butce_metin_kesilir():
    parcalar = ["a" * (6 * 1024 * 1024), "b" * (6 * 1024 * 1024)]
    cut, status, code = extract._budget_text(parcalar)
    assert status == "partial" and sum(len(p) for p in cut) == extract.MAX_TEXT_DOC


def test_butce_zip_entry_siniri(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "MAX_ZIP_ENTRIES", 3)
    zp = str(tmp_path / "siskin.zip")
    with zipfile.ZipFile(zp, "w") as z:
        for i in range(5):
            z.writestr(f"f{i}.txt", "x")
    assert extract._zip_guard(zp) == "ZIP_LIMIT"


def test_butce_pdf_sayfa_siniri(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "MAX_PDF_PAGES", 1)
    from reportlab.pdfgen import canvas
    p = str(tmp_path / "uzun.pdf")
    c = canvas.Canvas(p)
    c.drawString(72, 750, "sayfa bir")
    c.showPage()
    c.drawString(72, 750, "sayfa iki")
    c.save()
    res = extract.extract(p, ".pdf", os.path.getsize(p))
    assert res.status == "partial" and res.error_code == "PAGE_LIMIT", res
    assert len(res.segments) == 1


@motor_var
def test_kopya_hash_taramada_kablolu(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _yaz_pdf(os.path.join(kok, "a.pdf"), ["Ankara kopya testi 2024"])
    import shutil
    shutil.copy(os.path.join(kok, "a.pdf"), os.path.join(kok, "b.pdf"))
    _bekle()
    con, db = _kasa(tmp_path)
    st = coordinator.run_scan(con, db, kok)
    assert st["hashed"] == 2, st
    g = dup.groups(con)
    assert len(g) == 1 and len(g[0]["paths"]) == 2, g
    con.close()


@motor_var
def test_rapid_kucuk_punto_turkce_tanimada(tmp_path):
    """Kalite kapisi (WordArc kaniti): kucuk punto TR metin dogru okunur."""
    from PIL import Image, ImageDraw, ImageFont
    satirlar = ["T.C. Gelir Idaresi Baskanligi", "Vergi Kimlik No: 1234567890",
                "Isyeri adresi: Cankaya/ANKARA, Istiklal Cad. No:4"]
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    img = Image.new("RGB", (900, 40 * len(satirlar) + 40), "white")
    dr = ImageDraw.Draw(img)
    for i, ln in enumerate(satirlar):
        dr.text((20, 20 + i * 40), ln, fill="black", font=f)
    png = str(tmp_path / "kucuk.png")
    img.save(png)
    text, mean, words = ocr.recognize_png(png)
    assert words >= 3
    assert "Gelir" in text and "Vergi" in text, text
    assert mean > 50, mean
