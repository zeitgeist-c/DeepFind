"""A5 testleri: normalizasyon, sinifli arama, filtre, gecmis, kopya."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import history, normalize, rank, vocab  # noqa: E402
from evrakci import coordinator, dup, schema, search, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402

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
    coordinator.run_scan(con, db, kok)
    vocab.rebuild_vocab(con)
    return con, db, kok


def test_normalize_tr():
    assert normalize.strict("İSTANBUL IĞDIR") == "istanbul ığdır"
    assert normalize.folded("Ayşe ğüşiöç") == "ayse gusioc"
    assert normalize.extract_years("rapor 2024 ve 1999") == ["2024", "1999"]
    assert normalize.NORMALIZER_VERSION == "a5-1"


def test_src01_siralama_ve_aciklama(tmp_path):
    con, _db, _k = _arsiv(tmp_path)
    r = rank.search_ranked(con, "Ankara Ayşe 2024 vergi levhası")
    assert r["results"], r
    top = r["results"][0]
    assert top["name"] == "Ankara Vergi 2024.pdf", top
    assert top["score_class"] == "strict", top
    assert "ad" in top["why"] and "2024" in top["years"], top
    assert "Ankara" in top["snippet"] and "Ayşe" in top["snippet"]
    con.close()


def test_src02_tolerans(tmp_path):
    con, _db, _k = _arsiv(tmp_path)
    r = rank.search_ranked(con, "Ayse vergi levhasi")
    assert r["results"], r
    assert r["results"][0]["name"] == "Ankara Vergi 2024.pdf", r["results"]
    assert r["results"][0]["score_class"] in ("folded", "fuzzy")
    r2 = rank.search_ranked(con, "Istanbul fatura")
    assert r2["results"] and "stanbul" in r2["results"][0]["name"]
    con.close()


def test_src03_yil_filtre_katı(tmp_path):
    con, _db, _k = _arsiv(tmp_path)
    r = rank.search_ranked(con, "fatura", year="2024")
    assert r["results"] == [], "yanlis yil katı elenmeli"
    r2 = rank.search_ranked(con, "fatura", year="2023")
    assert r2["results"] and r2["results"][0]["name"].endswith("2023.pdf")
    r3 = rank.search_ranked(con, "   ")
    assert r3["empty"] and r3["results"] == []
    con.close()


def test_no_result_durust(tmp_path):
    con, _db, _k = _arsiv(tmp_path)
    r = rank.search_ranked(con, "zebra helikopter kuantum")
    assert r["results"] == []
    assert isinstance(r["suggestions"], list)
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
    st = coordinator.run_scan(con, db, kok)
    # hash artik taramanin arka-plan adimi (A6 kablosu); ikinci cagri bosa duser
    assert st["hashed"] == 3, st
    assert dup.verify_pending(con)["verified"] == 0
    g = dup.groups(con)
    assert len(g) == 1, g
    assert len(g[0]["paths"]) == 2, g  # yalniz tam kopyalar
    names = [os.path.basename(p) for p in g[0]["paths"]]
    assert "belge1.pdf" in names and "kopya.pdf" in names
    con.close()


def test_src04_daginik_terimler(tmp_path):
    kok = str(tmp_path / "arsiv")
    alt = os.path.join(kok, "Ankara")
    os.makedirs(alt)
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(alt, "belge.pdf")
    c = canvas.Canvas(p)
    c.setFont("TR", 14)
    c.drawString(72, 750, "Ayşe Yılmaz")
    c.showPage()
    c.setFont("TR", 14)
    c.drawString(72, 750, "vergi levhası ektedir")
    c.save()
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    vocab.rebuild_vocab(con)
    r = rank.search_ranked(con, "Ankara Ayşe vergi levhası")
    assert r["results"], r
    top = r["results"][0]
    assert top["name"] == "belge.pdf", top
    assert top["page"] in (1, 2), top  # konum tek segmente ait, uydurma yok
    con.close()


def test_eski_arama_calismaya_devam(tmp_path):
    con, _db, _k = _arsiv(tmp_path)
    r = search.search(con, "Ankara")
    assert r, "v1 search geriye uyumlu olmali"
    con.close()
