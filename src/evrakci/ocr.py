"""Sayfa bazli yerel OCR: triyaj, sinirli render, timeout'lu Tesseract, kalite gecisi.

Plan bolum 11 sozlesmesi:
- Temel motor: CPU Tesseract 5, tur (+olculmus kombinasyon). Cloud/LLM yok.
- Gereksiz OCR yok: yeterli dogal metni olan sayfa atlanir (OCR-01).
- Iyilestirme: yalniz sorunlu sayfa, sinirli deneme; kotulesirse onceki korunur (OCR-02).
- Timeout/RAM/model eksikligi: kontrollu erteleme, klasik arama surer (OCR-03).
- Gecici turevler: kontrollu temp dizini, is/cokme sonrasi temizlik (kabul: kontrollu temp).
"""
from __future__ import annotations

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

# --- pinli adaylar (plan bolum 6/11; A1 kanitli, A8'de paket manifestine tasinir) ---
TESS_VERSION = "5.4.0.20240606"
MODEL_SHA = {
    "tur": "489b9504e80d7184ed1ac9a1976647884ee71149da231ff3c2c1dc15370f2f3d",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
    "osd": "9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff",
}
DEFAULT_LANGS = "tur"  # A6 olcumu (eval/lang_compare, 27.09.2026): ayni 61 kelimelik
# TR sayfada tur=1.000 dogruluk, tur+eng=0.820 (eng TR kelimeleri bozuyor); sure esit.
EXE_CANDIDATES = (
    os.environ.get("EVRAKCI_TESSERACT") or "",
    "C:/Program Files/Tesseract-OCR/tesseract.exe",
)

# --- butceler (plan bolum 8/11/21 adaylari) ---
MIN_TEXT_CHARS = 20       # sayfada bu kadar dogal metin varsa OCR atlanir
RENDER_DPIS = (300, 200, 150, 100)
MAX_RENDER_MP = 12        # sayfa basina megapiksel siniri
BASIC_TIMEOUT = 60        # sayfa render + temel OCR (sn)
IMPROVE_TIMEOUT = 120     # iyilestirme gecisi (sn)
MAX_ATTEMPTS_PAGE = 2     # temel + en fazla 1 iyilestirme
OCR_MAX_PAGES = 200       # belge basina OCR sayfa siniri (ustu partial)
RAM_MIN_AVAIL = int(1.5 * 1024**3)  # altinda OCR ertelenir (histerezis A7'de)
MAX_TEXT_DOC = 10 * 1024 * 1024     # belge basina cikarilmis metin (UTF-8)

GARBLE_RE = re.compile(r"[^A-Za-zÇçĞğIıİiÖöŞşÜü0-9\s.,;:!?()\[\]{}\"'`\-–—/\\+*=<>@#\$%€₺&…°]")
REPEAT_RE = re.compile(r"(.)\1{5,}")


@dataclass
class OcrPage:
    page: int
    text: str = ""
    mean_conf: float = -1.0
    words: int = 0
    garbage: float = 0.0
    method: str = "skip"  # skip | basic | improved | low | unavailable | deferred | timeout
    error_code: str | None = None
    dpi: int = 0
    langs: str = ""
    elapsed_ms: int = 0
    attempts: int = 0


def find_exe() -> str | None:
    for c in EXE_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    w = shutil.which("tesseract")
    return w


def tessdata_dir() -> str | None:
    env = os.environ.get("EVRAKCI_TESSDATA")
    if env and os.path.isdir(env):
        return env
    exe = find_exe()
    if exe:
        d = os.path.join(os.path.dirname(exe), "tessdata")
        if os.path.isdir(d):
            return d
    return None  # sistem varsayilani


def langs_available() -> list:
    exe = find_exe()
    if not exe:
        return []
    env = dict(os.environ)
    td = tessdata_dir()
    if td and os.environ.get("EVRAKCI_TESSDATA"):
        env["TESSDATA_PREFIX"] = td
    try:
        p = subprocess.run([exe, "--list-langs"], capture_output=True, text=True,
                           timeout=30, env=env)
        return [l.strip() for l in p.stdout.splitlines()
                if l.strip() and "available" not in l.lower() and "list of" not in l.lower()]
    except Exception:
        return []


def models_ok(langs: str = DEFAULT_LANGS) -> tuple:
    """(tamam_mi, eksik_liste). Motor + istenen diller + sha pinleri."""
    if not find_exe():
        return False, ["tesseract-exe"]
    td = tessdata_dir()
    if not td:
        return False, ["tessdata-dizini"]
    import hashlib
    missing = []
    for lang in langs.split("+"):
        f = os.path.join(td, f"{lang}.traineddata")
        if not os.path.isfile(f):
            missing.append(lang)
            continue
        if lang in MODEL_SHA:
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for b in iter(lambda: fh.read(1 << 20), b""):
                    h.update(b)
            if h.hexdigest() != MODEL_SHA[lang]:
                missing.append(lang + ":sha-uyusmazligi")
    avail = langs_available()
    for lang in langs.split("+"):
        if lang not in avail and lang not in missing:
            missing.append(lang + ":tesseract-gormuyor")
    return (len(missing) == 0), missing


def avail_ram() -> int | None:
    """Kullanilabilir fiziki RAM (bayt). Windows: GlobalMemoryStatusEx."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = MS()
        ms.dwLength = ctypes.sizeof(MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return int(ms.ullAvailPhys)
    except Exception:
        pass
    return None


def ram_allows() -> bool:
    a = avail_ram()
    return True if a is None else a >= RAM_MIN_AVAIL


def needs_ocr(text: str | None) -> bool:
    """Yeterli dogal metin varsa False (gereksiz OCR yok)."""
    return len((text or "").strip()) < MIN_TEXT_CHARS


def _rmtree_tmp(path: str) -> None:
    """Yalniz kontrollu temp (ocr-tmp alti) silinir; kaynak silme burada olmaz."""
    import shutil
    base = os.environ.get("EVRAKCI_TEMP") or ""
    try:
        ap = os.path.abspath(path)
        if base and not ap.startswith(os.path.abspath(base) + os.sep):
            return
        if os.sep + "ocr-tmp" + os.sep not in ap and not ap.endswith("ocr-tmp"):
            return
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def temp_dir(vault_dir: str) -> str:
    """Kontrollu temp: kasa disi, Evrakci/Temp altinda ise ozel dizin."""
    base = os.environ.get("EVRAKCI_TEMP") or os.path.join(vault_dir, "ocr-tmp")
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix="ocr-", dir=base)


def clean_stale(vault_dir: str, max_age_sec: int = 86400) -> int:
    """Cokme sonrasi kalan temp dizinlerini temizle. Donus: silinen sayisi."""
    base = os.environ.get("EVRAKCI_TEMP") or os.path.join(vault_dir, "ocr-tmp")
    n = 0
    try:
        names = os.listdir(base)
    except OSError:
        return 0
    now = time.time()
    for nm in names:
        if not nm.startswith("ocr-"):
            continue
        p = os.path.join(base, nm)
        try:
            if now - os.path.getmtime(p) > max_age_sec:
                _rmtree_tmp(p)
                n += 1
        except OSError:
            continue
    return n


def render_page_png(pdf_path: str, pageno_0: int, workdir: str,
                    dpi: int | None = None) -> tuple:
    """(png_yolu, kullanilan_dpi). Megapiksel sinirini asmamak icin DPI duser."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_path)
    try:
        if not (0 <= pageno_0 < len(doc)):
            raise IndexError("sayfa disi")
        page = doc[pageno_0]
        try:
            w_pt, h_pt = page.get_size()
        except Exception:
            w_pt, h_pt = 595.0, 842.0
        for d in (RENDER_DPIS if dpi is None else (dpi,)):
            mp = (w_pt * d / 72.0) * (h_pt * d / 72.0) / 1e6
            if mp <= MAX_RENDER_MP:
                use = d
                break
        else:
            use = RENDER_DPIS[-1]
        scale = use / 72.0
        bitmap = page.render(scale=scale).to_pil().convert("L")
        out = os.path.join(workdir, f"p{pageno_0}.png")
        bitmap.save(out)
        return out, use
    finally:
        doc.close()


def _run_tess(png: str, langs: str, psm: int, timeout: int, workdir: str) -> tuple:
    """(tsv_metin, sure_sn, hata). Timeout'ta surec gercekten oldurulur."""
    exe = find_exe()
    t0 = time.perf_counter()
    try:
        # Not: bu build'de stdout + 'tsv' config dosyasi TSV uretmiyor;
        # dogrulanmis yol -c tessedit_create_tsv=1.
        p = subprocess.run(
            [exe, png, "stdout", "-l", langs, "--psm", str(psm),
             "-c", "tessedit_create_tsv=1"],
            capture_output=True, text=True, timeout=timeout, cwd=workdir,
            env=_tess_env())
        return p.stdout, time.perf_counter() - t0, None
    except subprocess.TimeoutExpired:
        return "", time.perf_counter() - t0, "PROCESS_TIMEOUT"
    except Exception as e:
        return "", time.perf_counter() - t0, f"TESS_HATA:{type(e).__name__}"


def _tess_env() -> dict:
    env = dict(os.environ)
    if os.environ.get("EVRAKCI_TESSDATA"):
        env["TESSDATA_PREFIX"] = os.environ["EVRAKCI_TESSDATA"]
    return env


def parse_tsv(tsv: str) -> tuple:
    """(metin, ortalama_conf, kelime_sayisi). Seviye-5 (kelime) satirlari."""
    words, confs = [], []
    try:
        for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
            if row.get("level") != "5" or not (row.get("text") or "").strip():
                continue
            try:
                c = float(row.get("conf", -1))
            except ValueError:
                c = -1
            words.append(row["text"].strip())
            if c >= 0:
                confs.append(c)
    except Exception:
        pass
    text = " ".join(words)
    mean = sum(confs) / len(confs) if confs else -1.0
    return text, mean, len(words)


def quality_of(text: str) -> tuple:
    """(garbage_orani, tekrar_var_mi). Uzun cikti otomatik iyi degildir."""
    if not text:
        return 1.0, False
    g = len(GARBLE_RE.findall(text)) / max(1, len(text))
    return g, bool(REPEAT_RE.search(text))


def score_of(mean_conf: float, words: int, garbage: float, repeat: bool) -> float:
    if words == 0:
        return -100.0
    base = mean_conf if mean_conf >= 0 else 0.0
    return base - 40.0 * garbage - (15.0 if repeat else 0.0)


def ocr_page(pdf_path: str, pageno_0: int, workdir: str, langs: str = DEFAULT_LANGS,
             timeout_basic: int = BASIC_TIMEOUT, timeout_improve: int = IMPROVE_TIMEOUT,
             allow_rotate: bool = True) -> OcrPage:
    """Tek sayfa: temel gecis + (gerekirse) tek iyilestirme. Kotu cikti korunmaz."""
    res = OcrPage(page=pageno_0 + 1, langs=langs)
    ok, missing = models_ok(langs)
    if not ok:
        res.method = "unavailable"
        res.error_code = "MODEL_MISSING" if missing != ["tesseract-exe"] else "ENGINE_UNAVAILABLE"
        return res
    t0 = time.perf_counter()
    try:
        png, dpi = render_page_png(pdf_path, pageno_0, workdir)
    except Exception:
        res.method = "low"
        res.error_code = "CORRUPT_DOCUMENT"
        return res
    res.dpi = dpi
    tsv, dt, err = _run_tess(png, langs, 3, timeout_basic, workdir)
    res.attempts = 1
    if err == "PROCESS_TIMEOUT":
        res.method = "timeout"
        res.error_code = "PROCESS_TIMEOUT"
        res.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return res
    text, mean, words = parse_tsv(tsv)
    garbage, repeat = quality_of(text)
    best = (score_of(mean, words, garbage, repeat), text, mean, words, garbage, dpi, 3)
    needs_fix = (words == 0 or mean < 60 or garbage > 0.25)
    if needs_fix and res.attempts < MAX_ATTEMPTS_PAGE:
        # Iyilestirme: farkli segmentasyon + yuksek DPI (sinir icinde) + gerekirse dondurme
        import pypdfium2 as pdfium  # noqa: F401 (render icin)
        from PIL import Image
        res.attempts = 2
        hi = RENDER_DPIS[0] if dpi < RENDER_DPIS[0] else dpi
        png2 = os.path.join(workdir, f"p{pageno_0}_b.png")
        try:
            img = Image.open(png)
            # kontrollu on-isleme: yalniz yuksek DPI yeniden render etkisi icin kopya
            img.save(png2)
            rots = [None, 90, 180, 270] if (words == 0 and allow_rotate) else [None]
            for rot in rots:
                pj = png2 if rot is None else os.path.join(workdir, f"p{pageno_0}_r{rot}.png")
                if rot is not None:
                    img.rotate(rot, expand=True).save(pj)
                tsv2, _dt2, err2 = _run_tess(pj, langs, 6, timeout_improve, workdir)
                if err2 == "PROCESS_TIMEOUT":
                    continue
                t2, m2, w2 = parse_tsv(tsv2)
                g2, r2 = quality_of(t2)
                s2 = score_of(m2, w2, g2, r2)
                if s2 > best[0]:
                    best = (s2, t2, m2, w2, g2, hi, 6)
                if w2 > 0 and m2 >= 60:
                    break
        except Exception:
            pass
    _s, text, mean, words, garbage, _d, _p = best
    res.text, res.mean_conf, res.words, res.garbage = text, mean, words, garbage
    res.elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if words == 0:
        res.method = "low"
        res.error_code = "NO_TEXT"
    else:
        res.method = "improved" if res.attempts > 1 else "basic"
    return res


def ocr_document(pdf_path: str, pages_0: list, vault_dir: str, langs: str = DEFAULT_LANGS,
                 timeout_basic: int = BASIC_TIMEOUT,
                 timeout_improve: int = IMPROVE_TIMEOUT) -> tuple:
    """Belge duzeyi: RAM kapisi + kontrollu temp + sayfa siniri. (sonuclar, workdir-not)."""
    if not ram_allows():
        return [OcrPage(page=p + 1, method="deferred", error_code="MEMORY_LIMIT") for p in pages_0], None
    ok, missing = models_ok(langs)
    if not ok:
        code = "MODEL_MISSING" if missing != ["tesseract-exe"] else "ENGINE_UNAVAILABLE"
        return [OcrPage(page=p + 1, method="unavailable", error_code=code) for p in pages_0], None
    wd = temp_dir(vault_dir)
    try:
        out = []
        for i, p in enumerate(pages_0):
            if i >= OCR_MAX_PAGES:
                out.append(OcrPage(page=p + 1, method="deferred", error_code="PAGE_LIMIT"))
                continue
            out.append(ocr_page(pdf_path, p, wd, langs, timeout_basic, timeout_improve))
        return out, wd
    finally:
        _rmtree_tmp(wd)
