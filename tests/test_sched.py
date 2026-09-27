"""A7 zamanlama testleri: slot, catch-up, cift-kosma, otomatik baslatma."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import sched  # noqa: E402


def _dt(gun, saat, dk=0):
    return dt.datetime(2026, 9, gun, saat, dk)


def test_slot_gelmeden_kosmaz():
    kos, neden = sched.should_run(_dt(27, 9), _dt(26, 12, 35))
    assert (kos, neden) == (False, "slot-bekliyor")


def test_slot_geldi_kosar():
    kos, neden = sched.should_run(_dt(27, 13), _dt(26, 12, 35))
    assert kos and neden == "catch-up-tek"


def test_ayni_slot_iki_kez_kosmaz():
    kos, _n = sched.should_run(_dt(27, 13), _dt(27, 12, 35))
    assert kos is False


def test_kacirilan_gun_tek_catchup():
    kos, neden = sched.should_run(_dt(27, 9), _dt(24, 12, 35))
    assert not kos and neden == "slot-bekliyor"
    assert sched.should_run(_dt(27, 13), _dt(24, 12, 35))[0]


def test_iptal_edilen_gun_tekrar_baslamaz():
    assert not sched.should_run(_dt(27, 14), None, handled_day="2026-09-27")[0]
    assert not sched.should_run(_dt(28, 9), None, handled_day="2026-09-27")[0]
    assert sched.should_run(_dt(28, 13), None, handled_day="2026-09-27")[0]


def test_cihaz_gecikmesi_deterministik_sinirli():
    a = sched.device_lag_min("PC-1")
    assert a == sched.device_lag_min("PC-1") and 0 <= a <= 10
    b = sched.device_lag_min("PC-2")
    assert 0 <= b <= 10


def test_otomatik_baslatma_yaz_sil():
    ad = "Evrakci-Test-0000"
    sched.autostart_clear(ad)
    assert sched.autostart_get(ad) is None
    sched.autostart_set(ad, "C:\\ornek\\evrakci.exe")
    try:
        assert "evrakci.exe" in (sched.autostart_get(ad) or "")
    finally:
        assert sched.autostart_clear(ad) is True
    assert sched.autostart_get(ad) is None
