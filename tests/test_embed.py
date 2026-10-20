"""Vektor motoru testleri (FAZ 1). Gercek model yalnız EVRAKCI_GERCEK_MODEL=1 ile."""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_kirpma_birim_kurede():
    from evrakci import embed

    h = np.arange(24, dtype=np.float32).reshape(1, 3, 8)
    m = np.ones((1, 3))
    v = embed.isle(h, m, kirp=4)
    assert v.shape == (1, 4)
    assert abs(float((v * v).sum()) - 1.0) < 1e-5


def test_maske_sifir_satiri_yok_sayar():
    from evrakci import embed

    h = np.ones((1, 4, 6), dtype=np.float32)
    m = np.array([[1, 1, 0, 0]])
    v = embed.isle(h, m, kirp=6)
    assert v.shape == (1, 6)
    assert abs(float((v * v).sum()) - 1.0) < 1e-5


def test_sabitler():
    from evrakci import embed

    assert embed.DIM == 256
    assert embed.MODEL_VER == "eg2-text-256-v1"
    assert embed.SORGU_ONEKI == "task: search result | query: "
    assert embed.BELGE_ONEKI == "title: none | text: "


GERCEK = os.environ.get("EVRAKCI_GERCEK_MODEL") == "1"


def test_gercek_model_dumani():
    if not GERCEK:
        return
    import time

    from evrakci import embed

    ot = embed.Oturum()
    docs = ["elektrik faturasi tutar 1.250 TL", "kira sozlesmesi aylik 40.000 TL"]
    t = time.perf_counter()
    v = ot.encode(docs, gorev="belge")
    ms = (time.perf_counter() - t) * 1000.0
    assert v.shape == (2, 256)
    assert ms < 60_000, ms
