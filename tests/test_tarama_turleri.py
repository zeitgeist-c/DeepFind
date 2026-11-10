"""Tarama dosya turu secimi: varsayilan kapsam, PDF-yalniz, kapatma korumasi.

Kurallar:
- Ayar yoksa (eski profil) bugunku kapsam aynen taranir.
- Yalniz PDF seciliyken yeni/degismis PDF islenir, guncel PDF atlanir.
- Kapali turdeki onceki belgeler silinmez, kayip sayilmaz, aramada kalir.
- Hic tur secilmediyse tarama baslamaz.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import coordinator as C  # noqa: E402
from deepfind import migrate, rank  # noqa: E402
from deepfind import schema, vault  # noqa: E402
from deepfind import scan as scan_mod  # noqa: E402
from semantic_helpers import FixedSession, indexed_content, seed_vectors  # noqa: E402


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db)
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    return con, db


def _dokun(kok, ad, icerik):
    p = kok / ad
    if isinstance(icerik, bytes):
        p.write_bytes(icerik)
    else:
        p.write_text(icerik, encoding="utf-8")
    eski = time.time() - 10
    os.utime(p, (eski, eski))
    return p


def _pdf(kok, ad, metin):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = str(kok / ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 13)
    c.drawString(72, 750, metin)
    c.save()
    eski = time.time() - 10
    os.utime(p, (eski, eski))
    return p


def _docx(kok, ad, metin):
    from docx import Document
    p = str(kok / ad)
    d = Document()
    d.add_paragraph(metin)
    d.save(p)
    eski = time.time() - 10
    os.utime(p, (eski, eski))
    return p


def _arsiv(tmp_path):
    kok = tmp_path / "arsiv"
    kok.mkdir()
    _dokun(kok, "not.txt", "Ankara vergi notu tahsilat")
    _pdf(kok, "fatura.pdf", "Istanbul Mehmet Demir fatura bedeli")
    _docx(kok, "Rapor Cankiri.docx", "Cankiri semsiye bahcesi raporu")
    _dokun(kok, "kurulum.exe", b"MZ-desteklenmeyen")
    return kok


def _yollar(con):
    return {r[0] for r in con.execute("SELECT path FROM files").fetchall()}


def test_eski_profilde_ayar_yoksa_kapsam_bugunku_gibidir(tmp_path):
    con, _db = _kasa(tmp_path)
    try:
        assert scan_mod.secili_turler(con) is None
        assert scan_mod.aktif_turler(con) == set(scan_mod.TUM_TURLER)
        assert scan_mod.baslatma_engeli(con) is None
    finally:
        con.close()


def test_varsayilan_taramada_tum_turler_islenir(tmp_path):
    kok = _arsiv(tmp_path)
    con, db = _kasa(tmp_path)
    try:
        st = C.run_scan(con, db, str(kok), require_vectors=False)
        yollar = _yollar(con)
        assert any(p.endswith("not.txt") for p in yollar)
        assert any(p.endswith("fatura.pdf") for p in yollar)
        assert any(p.endswith("Rapor Cankiri.docx") for p in yollar)
        assert not any(p.endswith("kurulum.exe") for p in yollar)
        assert st["found"] == 3
    finally:
        con.close()


def test_yalniz_pdf_seciliyken_sadece_pdfler_islenir(tmp_path):
    kok = _arsiv(tmp_path)
    con, db = _kasa(tmp_path)
    try:
        scan_mod.turleri_kaydet(con, {".pdf"})
        rid, toplam = C.build_manifest(con, str(kok))
        assert toplam == 1
        con.execute("DELETE FROM scan_manifest WHERE run_id=?", (rid,))
        con.execute("UPDATE scan_runs SET finished_at=1, result='manifest' WHERE run_id=?", (rid,))
        con.commit()
        st = C.run_scan(con, db, str(kok), require_vectors=False)
        assert st["found"] == 1
        yollar = _yollar(con)
        assert any(p.endswith("fatura.pdf") for p in yollar)
        assert not any(p.endswith("not.txt") for p in yollar)
        assert not any(p.endswith(".docx") for p in yollar)
        # Degisen PDF yeniden islenir, guncel olan atlanir.
        _pdf(kok, "fatura.pdf", "Istanbul Mehmet Demir fatura bedeli guncel")
        st2 = C.run_scan(con, db, str(kok), require_vectors=False)
        assert st2["done"] >= 1
        st3 = C.run_scan(con, db, str(kok), require_vectors=False)
        assert st3["done"] == 0
        assert st3["skipped"] >= 1
    finally:
        con.close()


def test_kapali_turdeki_word_belgesi_aramada_kalir(tmp_path):
    kok = _arsiv(tmp_path)
    con, db = _kasa(tmp_path)
    try:
        C.run_scan(con, db, str(kok), require_vectors=False)
        seed_vectors(con)
        once = rank.search_semantic(con, "semsiye bahcesi", kodla=FixedSession().encode)
        assert any("Rapor Cankiri.docx" in r["name"] for r in once["results"]), once
        scan_mod.turleri_kaydet(con, {".pdf"})
        st = C.run_scan(con, db, str(kok), require_vectors=False)
        assert st["result"] in ("complete", "partial")
        satir = con.execute(
            "SELECT index_status FROM files WHERE path LIKE '%Rapor Cankiri.docx'").fetchone()
        assert satir is not None and satir[0] == "ok"
        assert con.execute(
            "SELECT count(*) FROM segments WHERE file_id=(SELECT file_id FROM files "
            "WHERE path LIKE '%Rapor Cankiri.docx')").fetchone()[0] >= 1
        assert any("Rapor Cankiri.docx" in r["name"] for r in indexed_content(con, "semsiye"))
        sonra = rank.search_semantic(con, "semsiye bahcesi", kodla=FixedSession().encode)
        assert any("Rapor Cankiri.docx" in r["name"] for r in sonra["results"]), sonra
        assert st["missing"] == 0
    finally:
        con.close()


def test_hic_tur_secilmediyse_engel_nedeni_var(tmp_path):
    kok = _arsiv(tmp_path)
    con, db = _kasa(tmp_path)
    try:
        scan_mod.turleri_kaydet(con, set())
        engel = scan_mod.baslatma_engeli(con)
        assert engel, "neden gosterilmeli"
        assert "tür" in engel
        st = C.run_scan(con, db, str(kok), require_vectors=False)
        assert st["found"] == 0
        assert st["missing"] == 0
        assert _yollar(con) == set()
    finally:
        con.close()


def test_secim_yeniden_acilista_korunur(tmp_path):
    con, db = _kasa(tmp_path)
    try:
        scan_mod.turleri_kaydet(con, {".pdf", ".txt"})
        con.commit()
        con.close()
        con = vault.open_vault(db)
        assert scan_mod.secili_turler(con) == {".pdf", ".txt"}
    finally:
        con.close()


def test_yarim_kalan_devamda_kapali_turun_isi_calisamaz(tmp_path):
    """Yarim kalan tur + tur kapatma: Word bekleyen isi calismaz, eski indeks aramada kalir."""
    import time as _t
    from deepfind import job_queue as q
    kok = _arsiv(tmp_path)
    con, db = _kasa(tmp_path)
    try:
        C.run_scan(con, db, str(kok), require_vectors=False)
        seed_vectors(con)
        assert any("Rapor Cankiri.docx" in r["name"]
                   for r in rank.search_semantic(
                       con, "semsiye bahcesi",
                       kodla=FixedSession().encode)["results"])
        # Iki belge degisti; onceki tur yarim kalmis gibi bekleyen isler birakilir:
        _docx(kok, "Rapor Cankiri.docx", "Cankiri semsiye bahcesi YENI icerik")
        _pdf(kok, "fatura.pdf", "Istanbul fatura YENI bedel")
        absroot = os.path.abspath(str(kok))
        con.execute("INSERT INTO scan_runs(root, started_at) VALUES (?, ?)", (absroot, int(_t.time())))
        for ad in ("Rapor Cankiri.docx", "fatura.pdf"):
            fid = con.execute("SELECT file_id FROM files WHERE name=?", (ad,)).fetchone()[0]
            st = os.stat(str(kok / ad))
            con.execute("UPDATE files SET size=?, mtime_ns=? WHERE file_id=?",
                        (st.st_size, st.st_mtime_ns, fid))
            q.enqueue(con, fid, q.signature_of(st.st_size, st.st_mtime_ns))
        con.execute("INSERT OR IGNORE INTO scan_selected SELECT file_id FROM files")
        con.commit()
        # Kullanici Word'u kapatip yalniz PDF ile devam eder:
        scan_mod.turleri_kaydet(con, {".pdf"})
        st = C.run_scan(con, db, str(kok), require_vectors=False)
        satir = con.execute(
            "SELECT status FROM jobs JOIN files USING(file_id) WHERE files.name=?",
            ("Rapor Cankiri.docx",)).fetchone()
        assert satir is not None and satir[0] == "pending"
        assert con.execute("SELECT index_status FROM files WHERE name=?",
                           ("Rapor Cankiri.docx",)).fetchone()[0] == "ok"
        assert any("Rapor Cankiri.docx" in r["name"] for r in indexed_content(con, "semsiye"))
        assert st["missing"] == 0
        pdf_metin = con.execute(
            "SELECT group_concat(raw_text, ' ') FROM segments WHERE file_id=("
            "SELECT file_id FROM files WHERE name='fatura.pdf')").fetchone()[0] or ""
        assert "YENI" in pdf_metin
    finally:
        con.close()
