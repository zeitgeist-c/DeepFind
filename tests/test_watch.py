"""Canlı izleme testleri: saf mantık + Win32 duman (Windows)."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import watch


def test_onemli_mi_gecicileri_eler():
    assert watch.onemli_mi("C:/a/belge.pdf")
    assert not watch.onemli_mi("C:/a/~$belge.docx")
    assert not watch.onemli_mi("C:/a/kilit.lock")
    assert not watch.onemli_mi("C:/a/yedek.tmp")


def test_coalesce_ust_klasore_indirger(tmp_path):
    kok = str(tmp_path)
    a = os.path.join(kok, "a")
    b = os.path.join(kok, "a", "alt")
    c = os.path.join(kok, "diger")
    assert watch.coalesce([a, b, c], [kok]) == sorted([a, c])


def test_coalesce_kok_disini_atar(tmp_path):
    assert watch.coalesce([str(tmp_path / "a"), "C:/baska/yol"], [str(tmp_path)]) == [str(tmp_path / "a")]


def test_coalesce_tasinca_koku_ister(tmp_path):
    kok = str(tmp_path)
    dirs = [os.path.join(kok, f"d{i}") for i in range(watch.COALESCE_LIMIT + 5)]
    assert watch.coalesce(dirs, [kok]) == [kok]


def test_debounce_suresi_dolmadan_bildirmez(tmp_path):
    gelen = []
    iz = watch.Izleyici(str(tmp_path), gelen.append)
    iz.bildir([str(tmp_path / "a.pdf")], simdi=100.0)
    assert iz.bosalt(simdi=100.0 + watch.DEBOUNCE_SEC - 1) == []
    assert gelen == []
    due = iz.bosalt(simdi=100.0 + watch.DEBOUNCE_SEC)
    assert due == [str(tmp_path)]
    assert gelen == [[str(tmp_path)]]


@pytest.mark.skipif(os.name != "nt", reason="Win32 izleme")
def test_win32_olay_gelir(tmp_path):
    gelen = []
    iz = watch.Izleyici(str(tmp_path), lambda dirs: gelen.extend(dirs))
    iz.start()
    try:
        (tmp_path / "yeni.pdf").write_bytes(b"%PDF-1.4 x")
        deadline = time.monotonic() + 10
        while not gelen and time.monotonic() < deadline:
            time.sleep(0.2)
            iz.bosalt()
        # Olay kuyruğa girmiş olmalı (debounce bildirimi beklemez).
        with iz._kilit:
            bekleyen = dict(iz._bekleyen)
        assert gelen or bekleyen, "Win32 olay üretmedi"
    finally:
        iz.durdur()
        iz.join(timeout=10)
        assert not iz.is_alive()
