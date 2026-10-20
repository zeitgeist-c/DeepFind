"""Model indirici: surum kilitli URL + sha256 + atomik yazim.

Uretim modeli pakete gomulmez; ilk acilista buradan indirilir.
Adres/surum sabitleri surum notuyla birlikte guncellenir.
"""
from __future__ import annotations

import hashlib
import os
import urllib.request

MODEL_SURUM = "eg2-text-256-v1"
MODEL_DOSYA = "eg2-text.onnx"
# Surumde doldurulur (ornek: releases indirme adresi + sha256).
MODEL_URL = ""
MODEL_SHA256 = ""
MODEL_BOYUT = 1085617477  # bayt; export ciktisi, yaklasik


def hedef_yol(kok: str | None = None) -> str:
    taban = kok or os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(taban, "Evrakçı", "models", MODEL_DOSYA)


def _sha256_yoksa(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for parca in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(parca)
    return h.hexdigest()


def gerekli_mi(yol: str | None = None) -> bool:
    """Indirme gerekli mi: dosya yoksa ya da oet tutmuyorsa True."""
    if not MODEL_SHA256:
        return not os.path.isfile(yol or hedef_yol())
    return _sha256_yoksa(yol or hedef_yol()) != MODEL_SHA256


def indir(url: str | None = None, oet: str | None = None,
          yol: str | None = None, ilerleme=None) -> str:
    """Indir + dogrula + atomik tasi. Donus: dosya yolu."""
    url = url or MODEL_URL
    oet = oet or MODEL_SHA256
    yol = yol or hedef_yol()
    if not url:
        raise RuntimeError("model adresi tanimli degil")
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".indir"
    try:
        with urllib.request.urlopen(url, timeout=60) as yanit, open(gecici, "wb") as f:
            toplam = int(yanit.headers.get("Content-Length", 0) or 0)
            okunan = 0
            while True:
                parca = yanit.read(4 * 1024 * 1024)
                if not parca:
                    break
                f.write(parca)
                okunan += len(parca)
                if ilerleme:
                    ilerleme(okunan, toplam)
        if oet:
            h = hashlib.sha256()
            with open(gecici, "rb") as f:
                for parca in iter(lambda: f.read(4 * 1024 * 1024), b""):
                    h.update(parca)
            if h.hexdigest() != oet:
                raise ValueError("model dosyasi dogrulamasi basarisiz")
        os.replace(gecici, yol)
    finally:
        try:
            if os.path.exists(gecici):
                os.remove(gecici)
        except OSError:
            pass
    return yol
