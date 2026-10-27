"""A5 testleri: normalizasyon, sinifli arama, filtre, gecmis, kopya."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import history, normalize, rank  # noqa: E402
from evrakci import coordinator, dup, schema, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.migrate import ensure_v5  # noqa: E402

PW = "test-sifresi-12345"


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v6(con)
    ensure_v5(con)
    return con, db


def _pdf(kok, ad, metin):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 14)
    c.drawString(72, 750, metin)
    c.save()
    return p


def _arsiv(tmp_path, n=3):
    from test_durability import _pdf as _  # noqa
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok, exist_ok=True)
    _pdf(kok, "Ankara Vergi 2024.pdf", "Ankara Ayşe 2024 vergi levhası")
    _pdf(kok, "Istanbul Fatura 2023.pdf", "Mehmet Demir 2023 faturası İstanbul")
    _pdf(kok, "Notlar.docx", "placeholder") if False else None
    from docx import Document
    d = Document()
    d.add_paragraph("Çankırı şemsiye bahçesi raporu")
    d.save(os.path.join(kok, "Rapor Çankırı.docx"))
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    return con, db, kok


def test_normalize_tr():
    assert normalize.strict("İSTANBUL IĞDIR") == "istanbul ığdır"
    assert normalize.folded("Ayşe ğüşiöç") == "ayse gusioc"
    assert normalize.extract_years("rapor 2024 ve 1999") == ["2024", "1999"]
    assert normalize.NORMALIZER_VERSION == "a5-1"


def test_v9_sema_tek_kopya(tmp_path):
    """v9 kasada folded_text kolonu ve docs_fts_folded yok; arama calisir."""
    con, _db = _kasa(tmp_path)
    cols = {r[1] for r in con.execute("PRAGMA table_info(segments)")}
    assert "folded_text" not in cols
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts_folded'").fetchone()
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='segf_ai'").fetchone()
    con.close()










def test_gecmis_limit(tmp_path):
    con, _db = _kasa(tmp_path)
    for i in range(25):
        history.save(con, f"sorgu {i}")
    rows = history.list_all(con)
    assert len([x for x in rows if not x[3]]) == 20
    qid = rows[0][0]
    assert history.pin(con, qid) is True
    assert history.list_all(con)[0][3] == 1
    history.delete(con, qid)
    assert all(x[0] != qid for x in history.list_all(con))
    con.close()


def test_dup01_ilk64k_ayri_grup(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    bas = "A" * 70000
    with open(os.path.join(kok, "belge1.pdf"), "wb") as f:
        f.write(b"%PDF-fake " + bas.encode() + b" SONBIR")
    with open(os.path.join(kok, "belge2.pdf"), "wb") as f:
        f.write(b"%PDF-fake " + bas.encode() + b" SONIKI")
    with open(os.path.join(kok, "kopya.pdf"), "wb") as f:
        f.write(b"%PDF-fake " + bas.encode() + b" SONBIR")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    st = coordinator.run_scan(con, db, kok, require_vectors=False)
    # hash artik taramanin arka-plan adimi (A6 kablosu); ikinci cagri bosa duser
    assert st["hashed"] == 3, st
    assert dup.verify_pending(con)["verified"] == 0
    g = dup.groups(con)
    assert len(g) == 1, g
    assert len(g[0]["paths"]) == 2, g  # yalniz tam kopyalar
    names = [os.path.basename(p) for p in g[0]["paths"]]
    assert "belge1.pdf" in names and "kopya.pdf" in names
    con.close()






def _hafiza():
    import sqlite3
    from evrakci import index, migrate, schema
    from evrakci.extract import ExtractResult, Segment
    from evrakci.scan import Entry
    con = sqlite3.connect(":memory:")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v7(con)
    for path, metin in {
        "C:/a/fatura.pdf": "ABC kira faturası 2023",
        "C:/a/fatura-elektrik.pdf": "XYZ elektrik faturası",
        "C:/a/makbuz.pdf": "tahsilat makbuzu 54321",
        "C:/a/not.pdf": "or use this",
    }.items():
        index.index_entry(con, Entry(path, os.path.basename(path), ".pdf", 10, 1),
                          ExtractResult([Segment("pdf_page", 1, "Sayfa 1", metin)]))
    return con


def _yollar(r):
    return [x["path"] for x in r["results"]]






def test_kayitli_arama_crud():
    from evrakci import migrate
    con = _hafiza()
    try:
        migrate.ensure_archive(con)
        rank.save_search(con, "kiralar", "kira faturası", year="2023")
        assert rank.saved_searches(con) == [
            {"name": "kiralar", "query": "kira faturası", "year": "2023", "ext": None, "folder": None}]
        rank.save_search(con, "kiralar", "kira")
        assert rank.saved_searches(con)[0]["query"] == "kira"
        rank.delete_search(con, "kiralar")
        assert rank.saved_searches(con) == []
        with pytest.raises(ValueError):
            rank.save_search(con, "  ", "kira")
    finally:
        con.close()


def test_csv_satirlari():
    con = _hafiza()
    try:
        out = rank.results_csv(con, [dict(name="fatura.pdf",path="C:/a/fatura.pdf",ext=".pdf",file_id=1)])
        satirlar = out.strip().split("\n")
        assert satirlar[0] == "dosya,yol,tur,sayfa,yil,etiketler,neden"
        assert any("fatura.pdf" in s for s in satirlar[1:])
    finally:
        con.close()
