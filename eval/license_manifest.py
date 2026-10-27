"""A8: kurulu dagitimdan ucuncu-taraf lisans manifesti uretir (LISANSLAR.md)."""
import importlib.metadata as m
import os
import shutil
import sys

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENV = os.path.join(KOK, ".venv", "Lib", "site-packages")
HEDEF = os.path.join(KOK, "LISANSLAR.md")

ILGILI = ["sqlcipher3", "pypdfium2", "openpyxl", "xlrd", "python-docx",
          "defusedxml", "rapidfuzz", "pillow", "pyside6-essentials", "shiboken6",
          "rapidocr", "onnxruntime-directml", "opencv-python-headless", "numpy"]


def lisans_dosyalari(dist):
    out = []
    for f in (dist.files or []):
        a = str(f).lower()
        if "license" in a or "licence" in a or "copying" in a or "notice" in a:
            out.append(f)
    return out


def main():
    sys.path.insert(0, os.path.join(KOK, "src"))
    from deepfind.version import __version__
    sys.path.insert(0, os.path.join(VENV))
    satir = [f"# DeepFind {__version__} — Üçüncü-taraf lisansları", "",
             "Üretim: kurulu dağıtımdan, dosya-içi METADATA + lisans metni adıyla.",
             ""]
    for ad in ILGILI:
        try:
            d = m.distribution(ad)
        except Exception as e:  # noqa: BLE001
            satir.append(f"- {ad}: BULUNAMADI ({e})")
            continue
        ver = d.version
        lic = d.metadata.get("License-Expression") or d.metadata.get("License") or "?"
        dosyalar = [str(f) for f in lisans_dosyalari(d)]
        satir.append(f"- {d.metadata['Name']}=={ver} — {lic}")
        for f in dosyalar[:4]:
            satir.append(f"  - {f}")
    satir += ["", "- EmbeddingGemma 2 Q8_0: Apache-2.0; embedding/model-LICENSE.txt.",
              "- llama.cpp b11765: MIT; embedding/llama-LICENSE.txt.",
              "- LLVM OpenMP: Apache-2.0 with LLVM exceptions; motor klasörlerinde LICENSE-LLVM-OpenMP.",
              "- İsteğe bağlı CUDA: NVIDIA çalışma zamanı lisansları."]
    satir += ["",
              "PySide6 (LGPLv3): lisans metni pakette `licenses/` altında taşınır; "
              "Qt kaynak teklifi Qt Company kanalıyla (dinamik bağ, değişiklik yok).",
              "RapidOCR (PP-OCR modelleri, Apache-2.0) + ONNX Runtime (MIT) + "
              "OpenCV-python-headless (Apache-2.0) bağımlılıkları licenses/ altında taşınır."]
    with open(HEDEF, "w", encoding="utf-8") as f:
        f.write("\n".join(satir) + "\n")
    print(f"yazildi: {HEDEF}", flush=True)


if __name__ == "__main__":
    main()
