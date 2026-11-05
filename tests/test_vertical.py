"""A3 dikey akis testleri: sentetik belge -> tara -> indeksle -> ara -> snippet."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import extract, index, scan, schema, vault  # noqa: E402
from deepfind.migrate import ensure_v6  # noqa: E402
from deepfind.migrate import ensure_v5  # noqa: E402

PW = "test-sifresi-12345"


def _sentetik(kok: str) -> None:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    c = canvas.Canvas(os.path.join(kok, "Ankara Vergi Levhası 2024.pdf"))
    c.setFont("TR", 14)
    c.drawString(72, 750, "Ankara Ayşe 2024 vergi levhası")
    c.showPage()
    c.setFont("TR", 14)
    c.drawString(72, 750, "ikinci sayfada beyanname detayı")
    c.save()

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Vergi"
    ws["B14"] = "Ayşe Yılmaz"
    ws["C14"] = "Ankara"
    wb.save(os.path.join(kok, "liste 2024.xlsx"))

    from docx import Document
    d = Document()
    d.add_paragraph("Mehmet Demir Aralık faturası İstanbul")
    d.save(os.path.join(kok, "not.docx"))

    with open(os.path.join(kok, "eski-arşiv.doc"), "wb") as f:
        f.write(b"\x00\x01sahte-doc")


def test_kasa_eski_sifreli_donusumsuz_acilmaz(tmp_path):
    import sqlcipher3
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v6(con)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('a.pdf','a.pdf','.pdf')")
    con.commit()
    con.close()
    # Eski bicimi taklit et: duz kasayi sifrele.
    sifreli = str(tmp_path / "eski.db")
    ham = sqlcipher3.connect(db)
    try:
        ham.execute("ATTACH DATABASE '" + sifreli.replace("'", "''") + "' AS enc KEY 'dogru-parola-1234'")
        ham.execute("SELECT sqlcipher_export('enc')")
        ham.execute("DETACH DATABASE enc")
    finally:
        ham.close()
    with pytest.raises(vault.EncryptedVaultError):
        vault.open_vault(sifreli)


def test_dikey_akis(tmp_path):
    kok = tmp_path / "arsiv"
    kok.mkdir()
    _sentetik(str(kok))
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v6(con)
    girisler = list(scan.walk_ro(str(kok)))
    assert len(girisler) == 4
    for e in girisler:
        index.index_entry(con, e, extract.extract(e.path, e.ext, e.size))
    assert con.execute('SELECT count(*) FROM files').fetchone()[0] == 4
    assert con.execute("SELECT count(*) FROM segments WHERE kind NOT IN ('name_only','context')").fetchone()[0] >= 4
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts'").fetchone()
    con.close()


def test_surum_esitligi():
    import tomllib
    with open(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"), "rb") as f:
        project = tomllib.load(f)
        assert project["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "deepfind.version.__version__"
        assert "version" in project["project"]["dynamic"]


def test_router_bayrak_degerini_komut_sanmaz():
    from deepfind.__main__ import _ilk_komut, main
    assert _ilk_komut(["--kasa", "C:/x/k.db", "--sifre", "pw", "tani"]) == "tani"
    assert _ilk_komut(["--kasa", "C:/x/k.db"]) is None
    assert _ilk_komut([]) is None
    assert _ilk_komut(["tara", "C:/arsiv"]) == "tara"
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
