"""Cikaricilar: salt-okunur acis, sayfa/bolge konumlu segmentler. Kaynaga yazmaz."""
from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass
class ExtractResult:
    segments: list = field(default_factory=list)
    status: str = "ok"  # ok | partial | unsupported_content | corrupt | encrypted | size_limit
    error_code: str | None = None


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


def _docx(path: str) -> ExtractResult:
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
        for part, label in ((section.header, "Üstbilgi"), (section.footer, "Altbilgi"),
                            (section.first_page_header, "İlk sayfa üstbilgi"),
                            (section.first_page_footer, "İlk sayfa altbilgi")):
            key = str(part.part.partname)
            if key in seen_parts:
                continue
            seen_parts.add(key)
            text = "\n".join(p.text for p in part.paragraphs if p.text.strip())
            if text:
                segs.append(Segment("para", None, label, text))
    texts = [s.raw_text for s in segs]
    cut, status, code = _budget_text(texts)
    for s, t in zip(segs, cut):
        s.raw_text = t
    segs = segs[:len(cut)]
    return ExtractResult(segs, status, code)
