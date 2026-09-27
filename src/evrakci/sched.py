"""Zamanlama: gunluk tarama slotu, cihaz gecikmesi, catch-up, cift-kosma kilidi.

Plan bolum 18 sozlesmesi:
- Varsayilan yerel saat 12:30 + cihaz basina sabit kucuk gecikme (NAS yuk dagilimi).
- Uygulama kapaliyken/kilitliyken is calismaz; kilit acilinca kacirilan gunluk is
  bir kez baslatilabilir. Ayni slot iki kez kosmaz.
- Uyku/saat degisimi sonrasi yeniden degerlendirilir.
- Windows gorev zamanlayicisi/sunucu servisi yok.
"""
from __future__ import annotations

import datetime as dt
import hashlib

DEFAULT_HOUR = 12
DEFAULT_MINUTE = 30
MAX_LAG_MIN = 10  # cihaz gecikmesi ust siniri (dk)


def device_lag_min(device_id: str, max_lag: int = MAX_LAG_MIN) -> int:
    """Cihaz kimliginden deterministik 0..max_lag dakika gecikme."""
    h = hashlib.sha256(device_id.encode("utf-8")).digest()
    return int.from_bytes(h[:2], "big") % (max_lag + 1)


def slot_for(day: dt.date, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE,
             lag_min: int = 0) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hour, minute) + dt.timedelta(minutes=lag_min)


def should_run(now: dt.datetime, last_ok: dt.datetime | None,
               hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE,
               lag_min: int = 0, handled_day: str = "") -> tuple:
    """(calismali_mi, neden). Kilit disi cagrilir; kilitliyse cagiran calistirmaz."""
    today_slot = slot_for(now.date(), hour, minute, lag_min)
    if handled_day >= now.date().isoformat():
        return False, "bugunku-slot-ele-alindi"
    if last_ok is not None and last_ok >= today_slot:
        return False, "bugunku-slot-tamam"
    if now >= today_slot:
        if last_ok is None:
            return True, "ilk-gun-slot-geldi"
        # kacirilan gunler icin tek catch-up (her gecmis gune ayri tarama yok)
        return True, "catch-up-tek"
    return False, "slot-bekliyor"


def mark_done() -> dt.datetime:
    return dt.datetime.now()


def autostart_set(app_name: str, exe_path: str, vault_path: str | None = None) -> None:
    """HKCU Run'a kullanici-duzeyi otomatik baslatma yazar (yonetici yok)."""
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_SET_VALUE)
    try:
        import subprocess
        command = [exe_path, "--tray"]
        if vault_path:
            command.extend(["--kasa", vault_path])
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, subprocess.list2cmdline(command))
    finally:
        winreg.CloseKey(key)


def autostart_clear(app_name: str) -> bool:
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
    except OSError:
        return False
    try:
        winreg.DeleteValue(key, app_name)
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(key)


def autostart_get(app_name: str) -> str | None:
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_QUERY_VALUE)
    except OSError:
        return None
    try:
        val, _t = winreg.QueryValueEx(key, app_name)
        return val
    except OSError:
        return None
    finally:
        winreg.CloseKey(key)
