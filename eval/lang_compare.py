"""Dil kombinasyonu olcumu: tur vs tur+eng, ayni sayfalar. Cikis: karsilastirma + oneri."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import ocr  # noqa: E402

CUMLELER = [
    "Ankara Ayşe Yılmaz 2024 vergi levhası düzenlendi",
    "İstanbul Büyükşehir Belediyesi mali rapor ve beyannamesi",
    "Şirketin çıkarılmış sermayesi üç milyon Türk lirasıdır",
    "Iğdır ili Aralık ilçesi tapu şerhi ve ipotek bilgileri",
    "Gayrimenkul değerleme uzmanı sözleşme örneği ektedir",
    "Fatura No BV-1001 tutar 125.750,50 TL olarak kesildi",
    "Ödeme planı: peşinat yüzde yirmi, kalanı on iki taksit",
    "Çalışan bordrosu ve sigorta gün sayısı kontrol edildi",
]


def build(outdir):
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    os.makedirs(outdir, exist_ok=True)
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52)
    img = Image.new("RGB", (1700, 1100), "white")
    dr = ImageDraw.Draw(img)
    for i, ln in enumerate(CUMLELER):
        dr.text((40, 40 + i * 125), ln, fill="black", font=f)
    p = os.path.join(outdir, "sayfa.png")
    img.save(p)
    pdf = os.path.join(outdir, "sayfa.pdf")
    c = canvas.Canvas(pdf)
    c.drawImage(ImageReader(p), 40, 100, width=520, height=336)
    c.save()
    return pdf


def acc(ocr_text, truth_words):
    got = ocr_text.split()
    hit = sum(1 for w in truth_words if w in ocr_text)
    return hit / max(1, len(truth_words)), len(got)


def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                        "Temp", "evrakci_lang"))
    pdf = build(base)
    truth = [w for ln in CUMLELER for w in ln.split()]
    print(f"sayfa={pdf} gercek_kelime={len(truth)}", flush=True)
    for langs in ("tur", "tur+eng"):
        ok, miss = ocr.models_ok(langs)
        print(f"-- {langs}: modeller={'OK' if ok else miss}", flush=True)
        if not ok:
            continue
        wd = ocr.temp_dir(base)
        try:
            t0 = time.perf_counter()
            r = ocr.ocr_page(pdf, 0, wd, langs=langs)
            dt = time.perf_counter() - t0
            a, n = acc(r.text, truth)
            print(f"  yontem={r.method} kelime={r.words}/{n} conf={r.mean_conf:.1f} "
                  f"dogruluk={a:.3f} sure={dt:.1f}sn dpi={r.dpi}", flush=True)
        finally:
            ocr._rmtree_tmp(wd)
    print("ONERI: dogruluk/sure karsilastirmasina gore DEFAULT_LANGS sec", flush=True)


if __name__ == "__main__":
    main()
