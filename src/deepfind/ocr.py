"""Sayfa bazli yerel OCR: triyaj, sinirli render, RapidOCR (ONNX), bellek kapisi.

Sozlesme:
- Temel motor: RapidOCR (PP-OCR modelleri, ONNX Runtime). Cloud/LLM yok, ek dil
  indirme yok — modeller rapidocr paketinin icinde gelir ve Turkceyi okur.
- Gereksiz OCR yok: yeterli dogal metni olan sayfa atlanir (OCR-01).
- Motor/model eksikligi ve bellek: kontrollu erteleme; içerik eksikliği görünür.
- Gecici turevler: kontrollu temp dizini, is/cokme sonrasi temizlik.
- OCR isleri spawn isci sürecinde kosar (workers.run_work); ana arayuz modeli
  yuklemez, bekci thread siniri asan sureci oldurur.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass

from . import rapid

# --- butceler ---
MIN_TEXT_CHARS = 20       # sayfada bu kadar dogal metin varsa OCR atlanir
RENDER_DPIS = (300, 200, 150, 100)
MAX_RENDER_MP = 12        # sayfa basina megapiksel siniri
OCR_MAX_PAGES = 200       # belge basina OCR sayfa siniri (ustu partial)
RAM_MIN_AVAIL = int(1.5 * 1024**3)  # altinda OCR ertelenir
MAX_TEXT_DOC = 10 * 1024 * 1024     # belge basina cikarilmis metin (UTF-8)


@dataclass
class OcrPage:
    page: int
    text: str = ""
    mean_conf: float = -1.0  # 0-100
    words: int = 0
    method: str = "skip"  # skip | basic | low | unavailable | deferred
    error_code: str | None = None
    elapsed_ms: int = 0


def engine_ok() -> tuple:
    """(tamam_mi, eksik_liste): RapidOCR zinciri + paket ici modeller."""
    missing = []
    if not rapid.stack_present():
        missing.append("rapidocr-zinciri")
    if not rapid.models_present():
        missing.append("ocr-modelleri")
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
    base = os.environ.get("DEEPFIND_TEMP") or ""
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
    """Kontrollu temp: kasa disi, DeepFind/Temp altinda ise ozel dizin."""
    base = os.environ.get("DEEPFIND_TEMP") or os.path.join(vault_dir, "ocr-tmp")
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix="ocr-", dir=base)


def clean_stale(vault_dir: str, max_age_sec: int = 86400) -> int:
    """Cokme sonrasi kalan temp dizinlerini temizle. Donus: silinen sayisi."""
    base = os.environ.get("DEEPFIND_TEMP") or os.path.join(vault_dir, "ocr-tmp")
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
        bitmap = page.render(scale=scale).to_pil().convert("RGB")
        out = os.path.join(workdir, f"p{pageno_0}.png")
        bitmap.save(out)
        return out, use
    finally:
        doc.close()


def _crop_content(img):
    """Bosluklari at: PP-OCR detektoru dev sayfada kucuk metni olceklerken
    kaciriyor; icerik sinir kutusu hizli ve isabetli. Yogun sayfada no-op."""
    import numpy as np
    a = np.asarray(img.convert("L"))
    ys, xs = np.where(a < 200)
    if len(ys) == 0:
        return img
    pad = 24
    top = max(0, int(ys.min()) - pad)
    bottom = min(a.shape[0], int(ys.max()) + pad + 1)
    left = max(0, int(xs.min()) - pad)
    right = min(a.shape[1], int(xs.max()) + pad + 1)
    if (bottom - top) >= a.shape[0] - 2 and (right - left) >= a.shape[1] - 2:
        return img  # icerik butun sayfayi kapliyor
    return img.crop((left, top, right, bottom))


def recognize_png(png_path: str) -> tuple:
    """PNG -> (metin, ort_conf_0_100, satir_sayisi). Motor hatasi RuntimeError."""
    import numpy as np
    from PIL import Image
    img = _crop_content(Image.open(png_path).convert("RGB"))
    arr = np.asarray(img)[:, :, ::-1]  # RGB->BGR
    result = rapid.run(arr)
    txts = [str(t).strip() for t in (getattr(result, "txts", None) or ()) if str(t).strip()]
    scores = [float(s) for s in (getattr(result, "scores", None) or ())]
    text = "\n".join(txts)
    mean = round(100.0 * (sum(scores) / len(scores)), 1) if scores else -1.0
    return text, mean, len(txts)


def ocr_page(pdf_path: str, pageno_0: int, workdir: str) -> OcrPage:
    """Tek sayfa: render + RapidOCR. Motor/model hatasinda kontrollu sonuc."""
    res = OcrPage(page=pageno_0 + 1)
    ok, missing = engine_ok()
    if not ok:
        res.method = "unavailable"
        res.error_code = "ENGINE_UNAVAILABLE" if missing == ["rapidocr-zinciri"] else "MODEL_MISSING"
        return res
    t0 = time.perf_counter()
    try:
        png, _dpi = render_page_png(pdf_path, pageno_0, workdir)
    except Exception:
        res.method = "low"
        res.error_code = "CORRUPT_DOCUMENT"
        res.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return res
    try:
        from PIL import Image
        import numpy as np
        with Image.open(png) as image:
            pixels = np.asarray(image.convert('L'))
        # Only an entirely white page is blank. A single sparse line or
        # faint printed content must still go through OCR.
        if np.count_nonzero(pixels < 255) == 0:
            res.method = 'blank'
            res.elapsed_ms = int((time.perf_counter()-t0)*1000)
            return res
        text, mean, words = recognize_png(png)
    except RuntimeError as exc:
        import logging
        logging.getLogger("deepfind.ocr").warning("OCR sayfa motor hatasi: %s", exc)
        res.method = "unavailable"
        res.error_code = "ENGINE_UNAVAILABLE"
    except Exception:
        res.method = "low"
        res.error_code = "OCR_FAILED"
    else:
        res.text, res.mean_conf, res.words = text, mean, words
        if words == 0 or not text.strip():
            res.method = "low"
            res.error_code = "NO_TEXT"
        else:
            res.method = "basic"
    res.elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return res


def ocr_document(pdf_path: str, pages_0: list, vault_dir: str) -> tuple:
    """Belge duzeyi: RAM kapisi + motor kontrolu + kontrollu temp + sayfa siniri."""
    if not ram_allows():
        return [OcrPage(page=p + 1, method="deferred", error_code="MEMORY_LIMIT") for p in pages_0], None
    ok, missing = engine_ok()
    if not ok:
        code = "ENGINE_UNAVAILABLE" if missing == ["rapidocr-zinciri"] else "MODEL_MISSING"
        return [OcrPage(page=p + 1, method="unavailable", error_code=code) for p in pages_0], None
    wd = temp_dir(vault_dir)
    try:
        out = []
        for i, p in enumerate(pages_0):
            if i >= OCR_MAX_PAGES:
                out.append(OcrPage(page=p + 1, method="deferred", error_code="PAGE_LIMIT"))
                continue
            out.append(ocr_page(pdf_path, p, wd))
        return out, wd
    finally:
        _rmtree_tmp(wd)
