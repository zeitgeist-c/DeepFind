"""Cikaricilar: salt-okunur acis, sayfa/bolge konumlu segmentler. Kaynaga yazmaz."""
from __future__ import annotations

from dataclasses import dataclass, field
from .theme import t

SIZE_LIMIT = 200 * 1024 * 1024  # plan bolum 8 adayi
MAX_PDF_PAGES = 1000        # belge basina sayfa; ustu partial + PAGE_LIMIT
MAX_TEXT_DOC = 10 * 1024 * 1024  # belge basina UTF-8 metin; ustu kesilir + partial
MAX_ZIP_ENTRIES = 10_000    # OOXML toplam entry
MAX_ZIP_BYTES = 256 * 1024 * 1024  # OOXML toplam acilim
MAX_ZIP_RATIO = 100         # genisleme orani guvenlik esigi
MAX_CELL_VISITS = 2_000_000  # Excel hucre ziyareti; ustu partial + CELL_LIMIT


@dataclass
class Segment:
    kind: str  # pdf_page | sheet | para | table | name_only
    page: int | None
    label: str
    raw_text: str
    start_offset: int = 0


@dataclass
class ExtractResult:
    segments: list = field(default_factory=list)
    status: str = "ok"  # ok | partial | unsupported_content | corrupt | encrypted | size_limit
    error_code: str | None = None
    next_cursor: int | None = None

def chunks(segment, size=4000):
    """Bounded search units with original text offsets (no content dropped)."""
    raw = segment.raw_text or ''
    if not raw:
        yield segment, segment.start_offset, segment.start_offset
    start=0
    while start<len(raw):
        end=min(len(raw),start+size)
        if end<len(raw):
            boundary=max(raw.rfind('\n',start+size//2,end),raw.rfind(' ',start+size//2,end))
            if boundary>start: end=boundary+1
        yield Segment(segment.kind, segment.page, segment.label, raw[start:end]),segment.start_offset+start,segment.start_offset+end
        start=end

def extract_window(path, ext, size, cursor=0, batch=100):
    """Cursor counts source units; PDF and Excel continue beyond legacy caps."""
    if size is not None and size>SIZE_LIMIT:
        return ExtractResult(status='partial',error_code='SIZE_LIMIT')
    if ext == '.pdf':
        import pypdfium2 as pdfium
        try:
            doc = pdfium.PdfDocument(path)
        except Exception as error:
            return ExtractResult(status='encrypted' if 'password' in str(error).lower() else 'corrupt', error_code='PASSWORD_REQUIRED' if 'password' in str(error).lower() else 'CORRUPT_DOCUMENT')
        try:
            end=min(len(doc),cursor+batch); segments=[]
            for i in range(cursor,end):
                page=doc[i]
                textpage=page.get_textpage()
                try: text=textpage.get_text_range() or ''
                finally: textpage.close(); page.close()
                segments.append(Segment('pdf_page',i+1,f'Sayfa {i+1}',text))
            return ExtractResult(segments,next_cursor=end if end<len(doc) else None)
        finally: doc.close()
    if ext in ('.xlsx','.xls'):
        if ext=='.xlsx':
            code=_zip_guard(path)
            if code: return ExtractResult(status='partial',error_code=code)
            import openpyxl
            try: book=openpyxl.load_workbook(path,read_only=True,data_only=True)
            except Exception: return ExtractResult(status='corrupt',error_code='CORRUPT_DOCUMENT')
            sheets=((s.title,s.iter_rows(values_only=True)) for s in book.worksheets)
        else:
            import xlrd
            try: book=xlrd.open_workbook(path,on_demand=True)
            except Exception: return ExtractResult(status='corrupt',error_code='CORRUPT_DOCUMENT')
            sheets=((s.name,(s.row_values(i) for i in range(s.nrows))) for s in book.sheets())
        segments=[]; position=0; end=cursor+batch*10
        try:
            for title,rows in sheets:
                for rowno,row in enumerate(rows,1):
                    if position>=end: return ExtractResult(segments,next_cursor=position)
                    if position>=cursor:
                        values=[str(v) for v in row if v is not None and str(v).strip()]
                        if values: segments.append(Segment('sheet',None,f'{title} • Satır {rowno}', ' | '.join(values)))
                    position+=1
            return ExtractResult(segments)
        finally:
            if ext=='.xlsx': book.close()
            else: book.release_resources()
    if ext in {'.jpg','.jpeg','.png','.tif','.tiff'}:
        from PIL import Image
        try:
            with Image.open(path) as im: count=getattr(im,'n_frames',1)
            end=min(count,cursor+batch)
            return ExtractResult([Segment('image_page',i+1,f'Resim {i+1}','') for i in range(cursor,end)],next_cursor=end if end<count else None)
        except Exception: return ExtractResult(status='corrupt',error_code='CORRUPT_IMAGE')
    if ext=='.doc':
        from .doc_adapter import extract_doc_guarded
        result=extract_doc_guarded(path) or ExtractResult(status='unsupported_content',error_code='ENGINE_UNAVAILABLE')
        if result.status!='ok': return result
    elif ext=='.docx':
        result=_docx(path,bounded=False)
        if result.status!='ok': return result
    elif ext in _WINDOW_READERS:
        result=_WINDOW_READERS[ext](path,bounded=False)
        if result.status!='ok': return result
    else:
        return extract(path,ext,size)
    from itertools import islice
    def units():
        for segment in result.segments:
            for part,start,end in chunks(segment):
                part.start_offset=start
                yield part
    parts=list(islice(units(),cursor,cursor+batch+1))
    return ExtractResult(parts[:batch],next_cursor=cursor+batch if len(parts)>batch else None)


def _budget_text(parts: list, status: str = "ok",
                 error_code: str | None = None) -> tuple:
    """Metin butcesi: 10 MB ustu kesilir, partial isaretlenir (basari sayilmaz)."""
    total = sum(len(p.encode("utf-8")) for p in parts)
    if total <= MAX_TEXT_DOC:
        return parts, status, error_code
    cut, acc = [], 0
    for p in parts:
        encoded = p.encode("utf-8")
        if acc + len(encoded) > MAX_TEXT_DOC:
            cut.append(encoded[:max(0, MAX_TEXT_DOC - acc)].decode("utf-8", errors="ignore"))
            acc = MAX_TEXT_DOC
            break
        cut.append(p)
        acc += len(encoded)
    return cut, "partial", error_code or "SIZE_LIMIT"


def _zip_guard(path: str) -> str | None:
    """OOXML ZIP guvenlik siniri. Donus: hata kodu | None(temiz)."""
    import zipfile
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return "CORRUPT_DOCUMENT"
    try:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            return "ZIP_LIMIT"
        total = sum(i.file_size for i in infos)
        if total > MAX_ZIP_BYTES:
            return "ZIP_LIMIT"
        comp = sum(i.compress_size for i in infos)
        if comp > 0 and total / comp > MAX_ZIP_RATIO and total > 1024 * 1024:
            return "ZIP_LIMIT"
        return None
    finally:
        zf.close()


def extract(path: str, ext: str, size: int | None) -> ExtractResult:
    if size is not None and size > SIZE_LIMIT:
        return ExtractResult(status="partial", error_code="SIZE_LIMIT")
    if ext == ".pdf":
        return _pdf(path)
    if ext == ".xlsx":
        return _xlsx(path)
    if ext == ".xls":
        return _xls(path)
    if ext == ".docx":
        return _docx(path)
    if ext in (".txt", ".md", ".log", ".csv", ".tsv"):
        return _txt(path)
    if ext == ".pptx":
        return _pptx(path)
    if ext == ".epub":
        return _epub(path)
    if ext == ".eml":
        return _eml(path)
    if ext == ".zip":
        return _zip_inner(path)
    if ext == ".doc":
        return ExtractResult(status="unsupported_content", error_code="UNSUPPORTED_CONTENT")
    return ExtractResult(status="unsupported_content", error_code="UNSUPPORTED_CONTENT")


def _pdf(path: str) -> ExtractResult:
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(path)
    except Exception as e:
        msg = str(e).lower()
        if "password" in msg or "encrypt" in msg:
            # V1: sifre toplanmaz/brute-force yok; ayri listelenir
            return ExtractResult(status="encrypted", error_code="PASSWORD_REQUIRED")
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    try:
        segs = []
        capped = False
        for i, page in enumerate(doc, start=1):
            if i > MAX_PDF_PAGES:
                capped = True
                break
            try:
                txt = page.get_textpage().get_text_range() or ""
            except Exception:
                txt = ""
            segs.append(Segment("pdf_page", i, f"Sayfa {i}", txt))
        texts = [s.raw_text for s in segs]
        cut, status, code = _budget_text(texts)
        for s, t in zip(segs, cut):
            s.raw_text = t
        segs = segs[:len(cut)]
        if capped:
            status, code = "partial", "PAGE_LIMIT"
        return ExtractResult(segs, status, code)
    finally:
        doc.close()


def _xlsx(path: str) -> ExtractResult:
    import openpyxl

    zg = _zip_guard(path)
    if zg:
        code = "CORRUPT_DOCUMENT" if zg == "CORRUPT_DOCUMENT" else zg
        st = "corrupt" if zg == "CORRUPT_DOCUMENT" else "partial"
        return ExtractResult(status=st, error_code=code)
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    try:
        segs = []
        visits = 0
        capped = False
        for ws in wb.worksheets:
            lines = []
            for r, row in enumerate(ws.iter_rows(values_only=True), start=1):
                vals = [str(v) for v in row if v is not None and str(v).strip()]
                visits += len(row)
                if visits > MAX_CELL_VISITS:
                    capped = True
                    break
                if vals:
                    lines.append(f"R{r}: {' | '.join(vals)}")
            segs.append(Segment("sheet", None, ws.title, "\n".join(lines)))
            if capped:
                break
        texts = [s.raw_text for s in segs]
        cut, status, code = _budget_text(texts)
        for s, t in zip(segs, cut):
            s.raw_text = t
        segs = segs[:len(cut)]
        if capped:
            status, code = "partial", "CELL_LIMIT"
        return ExtractResult(segs, status, code)
    finally:
        wb.close()


def _xls(path: str) -> ExtractResult:
    import xlrd

    try:
        bk = xlrd.open_workbook(path)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    segs = []
    visits = 0
    capped = False
    for sh in bk.sheets():
        lines = []
        for r in range(sh.nrows):
            vals = [str(sh.cell_value(r, c)) for c in range(sh.ncols)
                    if str(sh.cell_value(r, c)).strip()]
            visits += sh.ncols
            if visits > MAX_CELL_VISITS:
                capped = True
                break
            if vals:
                lines.append(f"R{r + 1}: {' | '.join(vals)}")
        segs.append(Segment("sheet", None, sh.name, "\n".join(lines)))
        if capped:
            break
    texts = [s.raw_text for s in segs]
    cut, status, code = _budget_text(texts)
    for s, t in zip(segs, cut):
        s.raw_text = t
    segs = segs[:len(cut)]
    if capped:
        status, code = "partial", "CELL_LIMIT"
    return ExtractResult(segs, status, code)


def _docx(path: str, bounded=True) -> ExtractResult:
    from docx import Document

    zg = _zip_guard(path)
    if zg:
        code = "CORRUPT_DOCUMENT" if zg == "CORRUPT_DOCUMENT" else zg
        st = "corrupt" if zg == "CORRUPT_DOCUMENT" else "partial"
        return ExtractResult(status=st, error_code=code)
    try:
        d = Document(path)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    segs = []
    for i, p in enumerate(d.paragraphs):
        if p.text.strip():
            segs.append(Segment("para", None, f"Paragraf {i + 1}", p.text))
    for ti, t in enumerate(d.tables):
        cells = []
        for r, row in enumerate(t.rows):
            vals = [c.text.strip() for c in row.cells if c.text.strip()]
            if vals:
                cells.append(f"R{r + 1}: {' | '.join(vals)}")
        if cells:
            segs.append(Segment("table", None, f"Tablo {ti + 1}", "\n".join(cells)))
    seen_parts = set()
    for section in d.sections:
        for part, label in ((section.header, t("Üstbilgi")), (section.footer, "Altbilgi"),
                            (section.first_page_header, t("İlk sayfa üstbilgi")),
                            (section.first_page_footer, t("İlk sayfa altbilgi"))):
            key = str(part.part.partname)
            if key in seen_parts:
                continue
            seen_parts.add(key)
            text = "\n".join(p.text for p in part.paragraphs if p.text.strip())
            if text:
                segs.append(Segment("para", None, label, text))
    if not bounded:
        return ExtractResult(segs)
    texts = [s.raw_text for s in segs]
    cut, status, code = _budget_text(texts)
    for s, t in zip(segs, cut):
        s.raw_text = t
    segs = segs[:len(cut)]
    return ExtractResult(segs, status, code)


TXT_EXTS = {".txt", ".md", ".log", ".csv", ".tsv"}
ZIP_INNER_MAX_FILES = 25
ZIP_INNER_MAX_BYTES = 10 * 1024 * 1024
ZIP_INNER_TOTAL_BYTES = 50 * 1024 * 1024


def _bounded_result(segs: list, bounded: bool) -> ExtractResult:
    if not bounded:
        return ExtractResult(segs)
    texts = [s.raw_text for s in segs]
    cut, status, code = _budget_text(texts)
    for s, t in zip(segs, cut):
        s.raw_text = t
    return ExtractResult(segs[:len(cut)], status, code)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "windows-1254"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _txt(path: str, bounded: bool = True) -> ExtractResult:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    text = _decode(data)
    segs = [Segment("text", None, "Metin", text)] if text.strip() else []
    return _bounded_result(segs, bounded)


def _pptx(path: str, bounded: bool = True) -> ExtractResult:
    code = _zip_guard(path)
    if code:
        return ExtractResult(status="partial" if code != "CORRUPT_DOCUMENT" else "corrupt",
                             error_code=code)
    import re as _re
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    try:
        names = sorted(
            (n for n in zf.namelist() if _re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(_re.search(r"\d+", n).group()))
        segs = []
        for num, name in enumerate(names, 1):
            try:
                root = ET.fromstring(zf.read(name))
            except Exception:
                continue
            parts = [el.text for el in root.iter()
                     if el.tag.endswith("}t") and (el.text or "").strip()]
            text = " ".join(" ".join(p.split()) for p in parts)
            if text:
                segs.append(Segment("slide", num, f"Slayt {num}", text))
    finally:
        zf.close()
    return _bounded_result(segs, bounded)


def _epub(path: str, bounded: bool = True) -> ExtractResult:
    code = _zip_guard(path)
    if code:
        return ExtractResult(status="partial" if code != "CORRUPT_DOCUMENT" else "corrupt",
                             error_code=code)
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    try:
        try:
            container = ET.fromstring(zf.read("META-INF/container.xml"))
        except Exception:
            return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
        rootfile = None
        for el in container.iter():
            if el.tag == "rootfile" or el.tag.endswith("}rootfile"):
                rootfile = el.get("full-path")
                break
        if not rootfile:
            return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
        base = rootfile.rpartition("/")[0]
        opf = ET.fromstring(zf.read(rootfile))
        hrefs = {}
        for el in opf.iter():
            if el.tag == "item" or el.tag.endswith("}item"):
                if el.get("id") and el.get("href"):
                    hrefs[el.get("id")] = el.get("href")
        order = []
        for el in opf.iter():
            if (el.tag == "itemref" or el.tag.endswith("}itemref")) and el.get("idref") in hrefs:
                order.append(hrefs[el.get("idref")])
        segs = []
        for i, href in enumerate(order, 1):
            full = (base + "/" + href) if base else href
            try:
                xroot = ET.fromstring(zf.read(full))
            except Exception:
                continue
            for parent in xroot.iter():
                for child in list(parent):
                    if child.tag == "script" or child.tag.endswith(("}script", "}style")) \
                            or child.tag == "style":
                        parent.remove(child)
            text = " ".join("".join(xroot.itertext()).split())
            if text:
                segs.append(Segment("chapter", None, t("Bölüm {i}", i=i), text))
    finally:
        zf.close()
    return _bounded_result(segs, bounded)


def _eml(path: str, bounded: bool = True) -> ExtractResult:
    import email
    from email import policy
    try:
        with open(path, "rb") as fh:
            msg = email.message_from_binary_file(fh, policy=policy.default)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    segs = []
    for label, val in (("Konu", msg["subject"]), (t("Gönderen"), msg["from"]),
                       ("Tarih", msg["date"])):
        if val and str(val).strip():
            segs.append(Segment("mail", None, label, str(val).strip()))
    bodies, atts = [], []
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.is_multipart():
                    continue
                if part.get_content_disposition() == "attachment":
                    fn = part.get_filename()
                    if fn:
                        atts.append(str(fn))
                    continue
                if part.get_content_type() == "text/plain":
                    try:
                        bodies.append(str(part.get_content()))
                    except Exception:
                        pass
        elif msg.get_content_type() == "text/plain":
            bodies.append(str(msg.get_content()))
    except Exception:
        pass
    body = "\n".join(b.strip() for b in bodies if b and b.strip())
    if body:
        segs.append(Segment("mail", None, t("Gövde"), body))
    if atts:
        segs.append(Segment("mail", None, "Ekler", "\n".join(atts)))
    return _bounded_result(segs, bounded)


def _zip_inner(path: str, bounded: bool = True) -> ExtractResult:
    code = _zip_guard(path)
    if code:
        return ExtractResult(status="partial" if code != "CORRUPT_DOCUMENT" else "corrupt",
                             error_code=code)
    import os
    import tempfile
    import zipfile
    from pathlib import Path
    try:
        zf = zipfile.ZipFile(path)
        infos = sorted((i for i in zf.infolist() if not i.is_dir()),
                       key=lambda i: i.filename)
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    capped = len(infos) > ZIP_INNER_MAX_FILES
    infos = infos[:ZIP_INNER_MAX_FILES]
    segs, total = [], 0

    def _inner(tmp_file: str, inner_ext: str, inner_name: str) -> list:
        if inner_ext in TXT_EXTS:
            res = _txt(tmp_file, bounded=False)
        elif inner_ext == ".pdf":
            res = _pdf(tmp_file)
        elif inner_ext == ".docx":
            res = _docx(tmp_file, bounded=False)
        elif inner_ext in (".xlsx", ".xls"):
            res = _extract_sheet(tmp_file, inner_ext)
        elif inner_ext == ".pptx":
            res = _pptx(tmp_file, bounded=False)
        elif inner_ext == ".epub":
            res = _epub(tmp_file, bounded=False)
        elif inner_ext == ".eml":
            res = _eml(tmp_file, bounded=False)
        else:
            return [Segment("zip_name", None, inner_name, inner_name)]
        if res.status not in ("ok", "partial") or not res.segments:
            return [Segment("zip_name", None, inner_name, inner_name)]
        return [Segment("zip_" + s.kind, s.page, f"{inner_name} • {s.label}", s.raw_text)
                for s in res.segments]

    try:
        with tempfile.TemporaryDirectory(prefix="zip-") as tmp:
            for n, info in enumerate(infos):
                name = info.filename
                if name.startswith("__MACOSX/"):
                    continue
                inner_ext = os.path.splitext(name)[1].lower()
                if info.file_size > ZIP_INNER_MAX_BYTES or total + info.file_size > ZIP_INNER_TOTAL_BYTES:
                    capped = True
                    segs.append(Segment("zip_name", None, name, name))
                    continue
                try:
                    data = zf.read(info.filename)
                except Exception:
                    continue
                total += len(data)
                tmp_file = os.path.join(tmp, f"i{n}{inner_ext or '.bin'}")
                try:
                    # Kontrollu temp: is sonu dizinle silinir; kaynaga yazilmaz.
                    Path(tmp_file).write_bytes(data)
                except OSError:
                    continue
                segs.extend(_inner(tmp_file, inner_ext, name))
    finally:
        zf.close()
    if capped:
        bounded_segs = _bounded_result(segs, bounded)
        return ExtractResult(bounded_segs.segments, "partial", "ZIP_LIMIT")
    return _bounded_result(segs, bounded)


def _extract_sheet(path: str, ext: str) -> ExtractResult:
    """Zip-ici tablo okuma: _xlsx/_xls mantigi, dosya zaten guvenli temp'te."""
    if ext == ".xlsx":
        return _xlsx(path)
    return _xls(path)


_WINDOW_READERS = {
    ".txt": _txt, ".md": _txt, ".log": _txt, ".csv": _txt, ".tsv": _txt,
    ".pptx": _pptx, ".epub": _epub, ".eml": _eml, ".zip": _zip_inner,
}
