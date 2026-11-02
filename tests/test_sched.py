"""Zamanlama testleri: yalnizca slot aninda acik uygulama tarama baslatir.

Kurallar (kullanici sozlesmesi):
- Saatinde acik -> tek tarama.
- Saatinde kapali, sonradan acilmis -> tarama yok (telafi yok).
- Uyku/saat degisimi -> telafi yok.
- Ayni gun icin yinelenen tarama yok.
- Tarama surerken slot gelmesi -> ikinci is/kuyruk yok (uygulama katmani).
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import scheduler as sched  # noqa: E402


def _dt(gun, saat, dk=0):
    return dt.datetime(2026, 9, gun, saat, dk)


def test_slot_gelmeden_kosmaz():
    kos, neden = sched.should_run(_dt(27, 9), _dt(26, 12, 35))
    assert (kos, neden) == (False, "slot-bekliyor")


def test_slot_aninda_acik_uygulama_kosar():
    kos, neden = sched.should_run(_dt(27, 12, 30), _dt(26, 12, 35))
    assert (kos, neden) == (True, "slot-geldi")


def test_slot_penceresi_icinde_kosar_sonra_kosmaz():
    # 12:30 slot + 3 dk pencere: 12:32 acik -> calisir, 12:40 -> kacirildi.
    assert sched.should_run(_dt(27, 12, 32), _dt(26, 12, 35))[0] is True
    kos, neden = sched.should_run(_dt(27, 12, 40), _dt(26, 12, 35))
    assert (kos, neden) == (False, "kacirildi-atlandi")


def test_sonradan_acilista_telafi_yok():
    # Uygulama 12:30'da kapaliydi, 15:00'te acildi: tarama baslamaz.
    kos, neden = sched.should_run(_dt(27, 15), None)
    assert (kos, neden) == (False, "kacirildi-atlandi")


def test_uyku_sonrasi_telafi_yok():
    # Cihaz 12:20'de uyudu, 16:00'da uyandi: kacirilan slot telafi edilmez.
    assert sched.should_run(_dt(27, 12, 20), _dt(26, 12, 35))[0] is False
    kos, neden = sched.should_run(_dt(27, 16), _dt(26, 12, 35))
    assert (kos, neden) == (False, "kacirildi-atlandi")


def test_ayni_slot_iki_kez_kosmaz():
    kos, neden = sched.should_run(_dt(27, 13), _dt(27, 12, 35))
    assert (kos, neden) == (False, "bugunku-slot-tamam")


def test_iptal_edilen_gun_tekrar_baslamaz():
    assert not sched.should_run(_dt(27, 12, 31), None, handled_day="2026-09-27")[0]
    assert not sched.should_run(_dt(28, 9), None, handled_day="2026-09-27")[0]
    assert sched.should_run(_dt(28, 12, 31), None, handled_day="2026-09-27")[0]


def test_cihaz_gecikmesi_deterministik_sinirli():
    a = sched.device_lag_min("PC-1")
    assert a == sched.device_lag_min("PC-1") and 0 <= a <= 10
    b = sched.device_lag_min("PC-2")
    assert 0 <= b <= 10


def test_otomatik_baslatma_yaz_sil():
    ad = "DeepFind-Test-0000"
    sched.autostart_clear(ad)
    assert sched.autostart_get(ad) is None
    sched.autostart_set(ad, "C:\\ornek\\deepfind.exe")
    try:
        assert "deepfind.exe" in (sched.autostart_get(ad) or "")
    finally:
        assert sched.autostart_clear(ad) is True
    assert sched.autostart_get(ad) is None


def test_otomatik_baslatma_guncelle_yalniz_kayit_varsa():
    """Güncelleme yeni klasöre taşıyınca kayıt tazelenir; kapalı kayıt açılmaz."""
    ad = "DeepFind-Test-0001"
    sched.autostart_clear(ad)
    # Without a record: untouched, no record created (stays closed).
    assert sched.autostart_guncelle(ad, "C:\\yeni\\deepfind.exe") is False
    assert sched.autostart_get(ad) is None
    # Refreshes when a record points at the old path.
    sched.autostart_set(ad, "C:\\eski\\deepfind.exe")
    try:
        assert sched.autostart_guncelle(ad, "C:\\yeni\\deepfind.exe") is True
        assert "yeni" in (sched.autostart_get(ad) or "")
        # Never written twice while already current.
        assert sched.autostart_guncelle(ad, "C:\\yeni\\deepfind.exe") is False
    finally:
        sched.autostart_clear(ad)
