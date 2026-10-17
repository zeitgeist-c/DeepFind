"""A6 kapı raporu: triyaj, OCR kalite/sure, butce, bellek. Sentetik veri."""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import coordinator, extract, ocr, schema, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402

PW = "a6-rapor-sifresi"


def peak_mb():
    try:
        import ctypes
        from ctypes import wintypes

        class PM(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        psapi = ctypes.WinDLL("psapi.dll")
        get = psapi.GetProcessMemoryInfo
        get.restype = wintypes.BOOL
        get.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        pm = PM()
        pm.cb = ctypes.sizeof(PM)
        h = ctypes.windll.kernel32.GetCurrentProcess()
        if get(h, ctypes.byref(pm), pm.cb):
            return round(pm.PeakWorkingSetSize / 1e6, 1)
    except Exception:
        pass
    return None


def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                        "Temp", "evrakci_a6"))
    kok = os.path.join(base, "arsiv")
    os.makedirs(kok, exist_ok=True)
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    c = canvas.Canvas(os.path.join(kok, "iyi.pdf"))
    c.setFont("TR", 13)
    c.drawString(72, 750, "Ankara Ayşe Yılmaz 2024 vergi levhası metin sayfa")
    c.save()
    # taramali sayfa (metin katmani yok) -> OCR beklenir
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader
    fnt = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52)
    img = Image.new("RGB", (1600, 420), "white")
    dr = ImageDraw.Draw(img)
    dr.text((40, 60), "Ankara Ayşe Yılmaz 2024 vergi levhası", fill="black", font=fnt)
    dr.text((40, 200), "Belge no BV-9001 düzenlendi", fill="black", font=fnt)
    png = os.path.join(base, "t.png")
    img.save(png)
    c2 = canvas.Canvas(os.path.join(kok, "taramali.pdf"))
    c2.drawImage(ImageReader(png), 72, 400, width=450, height=118)
    c2.save()
    os.remove(png)
    sys.path.insert(0, os.path.dirname(__file__))
    db = os.path.join(base, "kasa.db")
    for f in (db,):
        if os.path.exists(f):
            os.remove(f)
    time.sleep(2.5)
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v5(con)
    ensure_v6(con)
    t0 = time.perf_counter()
    st = coordinator.run_scan(con, db, kok)
    dt = time.perf_counter() - t0
    seg = con.execute("SELECT kind, method, confidence FROM segments").fetchall()
    con.close()
    rapor = {
        "tarih": "2026-09-27",
        "tarama_sn": round(dt, 1),
        "tarama": st,
        "segmentler": [{"kind": k, "method": m, "conf": c} for k, m, c in seg],
        "tepe_bellek_mb": peak_mb(),
        "butceler": {"dosya_MB": 200, "sayfa": 1000, "render_MP": 12, "metin_MB": 10,
                     "zip_MB": 256, "zip_entry": 10000, "zip_oran": 100,
                     "hucre": 2000000, "ocr_sayfa": 200},
        "motor": "RapidOCR 3.x (PP-OCRv6 small det/rec + cls, ONNX Runtime)",
    }
    rp = os.path.join(base, "a6_rapor.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(f"sonuc={st['result']} ocr_done={st['ocr_done']} tepe={rapor['tepe_bellek_mb']}MB", flush=True)
    print(f"segmentler={rapor['segmentler']}", flush=True)
    print(f"rapor={rp}", flush=True)
    kinds = {s["kind"] for s in rapor["segmentler"]}
    ocr_ok = [s for s in rapor["segmentler"]
              if s["kind"] == "ocr_page" and (s["conf"] or 0) > 0]
    ok = (st["result"] == "complete" and st["ocr_failed"] == 0
          and "pdf_page" in kinds and len(ocr_ok) == 1)
    print("KAPI: " + ("GECTI" if ok else "KALDI"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
