"""Yeni format cikaricilar: txt/csv/md/log, pptx, epub, eml, zip-ici. Saf stdlib kurulum."""
import email.message
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import extract
from evrakci import scan as scan_mod


def _yaz(path, data: bytes):
    path.write_bytes(data)
    return str(path)


def test_desteklenen_uzantilar_genisledi():
    for ext in (".txt", ".md", ".log", ".csv", ".tsv", ".pptx", ".epub", ".eml", ".zip"):
        assert ext in scan_mod.SUPPORTED_EXTS, ext


def test_txt_utf8(tmp_path):
    p = _yaz(tmp_path / "not.txt", "tahsilat makbuzu 54321: 18.750 TL".encode("utf-8"))
    res = extract.extract(p, ".txt", os.path.getsize(p))
    assert res.status == "ok" and "18.750" in res.segments[0].raw_text


def test_txt_windows1254(tmp_path):
    p = _yaz(tmp_path / "eski.txt", "Şişli şubesi ğüşiöç".encode("windows-1254"))
    res = extract.extract(p, ".txt", os.path.getsize(p))
    assert res.status == "ok" and "Şişli" in res.segments[0].raw_text


def test_csv_satirlari(tmp_path):
    p = _yaz(tmp_path / "kasa.csv", "tarih;tutar\na.b;1000\n".encode("utf-8"))
    res = extract.extract(p, ".csv", os.path.getsize(p))
    assert res.status == "ok" and "1000" in res.segments[0].raw_text


def _pptx(path, slaytlar):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>""")
        z.writestr("ppt/presentation.xml", """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>""")
        for i, metin in enumerate(slaytlar, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{metin}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>""")
    return str(path)


def test_pptx_slaytlari(tmp_path):
    p = _pptx(tmp_path / "sunum.pptx", ["Ankara denetim 2024", "gider 8 milyon TL"])
    res = extract.extract(p, ".pptx", os.path.getsize(p))
    assert res.status == "ok"
    metinler = [s.raw_text for s in res.segments]
    assert any("Ankara" in t for t in metinler) and any("8 milyon" in t for t in metinler)
    assert res.segments[0].page == 1


def _epub(path, bolumler):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")
        items = "".join(f'<item id="b{i}" href="b{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(len(bolumler)))
        refs = "".join(f'<itemref idref="b{i}"/>' for i in range(len(bolumler)))
        z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest>{items}</manifest><spine>{refs}</spine></package>""")
        for i, metin in enumerate(bolumler):
            z.writestr(f"OEBPS/b{i}.xhtml", f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{metin}</p></body></html>""")
    return str(path)


def test_epub_bolumleri(tmp_path):
    p = _epub(tmp_path / "kitap.epub", ["tahsilat makbuzu örneği", "ikinci bölüm"])
    res = extract.extract(p, ".epub", os.path.getsize(p))
    assert res.status == "ok"
    assert any("tahsilat" in s.raw_text for s in res.segments)


def test_eml_konu_govde(tmp_path):
    msg = email.message.EmailMessage()
    msg["Subject"] = "2024 kira faturası"
    msg["From"] = "muhasebe@ornek.com"
    msg.set_content("Toplam tutar 52.000 TL.")
    p = _yaz(tmp_path / "posta.eml", msg.as_bytes())
    res = extract.extract(p, ".eml", os.path.getsize(p))
    assert res.status == "ok"
    butun = "\n".join(s.raw_text for s in res.segments)
    assert "kira faturası" in butun and "52.000" in butun


def test_zip_ici_belgeler(tmp_path):
    zp = tmp_path / "arsiv.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ic-not.txt", "zip içi tahsilat 99 TL")
        z.writestr("resim.png", b"sahte-png")
    res = extract.extract(str(zp), ".zip", os.path.getsize(zp))
    assert res.status == "ok"
    assert any("99 TL" in s.raw_text for s in res.segments)
    assert any("ic-not.txt" in s.label for s in res.segments)


def test_zip_bozuk_guarded(tmp_path):
    p = _yaz(tmp_path / "bozuk.zip", b"degil-zip")
    res = extract.extract(p, ".zip", os.path.getsize(p))
    assert res.status in ("corrupt", "partial") and res.error_code in ("CORRUPT_DOCUMENT", "ZIP_LIMIT")


def test_pencere_cursor_yeni_turlerde(tmp_path):
    p = _yaz(tmp_path / "uzun.txt", ("satır veri 123\n" * 30000).encode("utf-8"))
    ilk = extract.extract_window(p, ".txt", os.path.getsize(p))
    assert ilk.next_cursor is not None
    son = extract.extract_window(p, ".txt", os.path.getsize(p), ilk.next_cursor)
    assert son.next_cursor is None
    assert ilk.segments and son.segments
