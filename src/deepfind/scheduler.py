"""Zamanlama: gunluk tarama slotu, cihaz gecikmesi, cift-kosma kilidi.

Sozlesme (kullanici kurali):
- Saatli tarama istege baglidir; yeni profilde kapalidir.
- Yalnizca uygulama o saatte ACIKSA calisir. Uygulama kapaliysa hicbir sey
  baslatilmaz (gorev zamanlayicisi/servis yok).
- Slot kacirilirsa telafi YOK: uygulama sonradan acildiginda o gunku slot
  atlanmis sayilir, tarama baslamaz.
- Uyku/saat degisimi sonrasi da telafi yok.
- Ayni gunku slot bir kez ele alinir; ayni slot iki kez kosmaz.
- Tarama surerken slot gelirse ikinci is veya sonradan calisacak kuyruk yok.
- Varsayilan yerel saat 12:30 + cihaz basina sabit kucuk gecikme (NAS yuk dagilimi).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os

DEFAULT_HOUR = 12
DEFAULT_MINUTE = 30
MAX_LAG_MIN = 10  # cihaz gecikmesi ust siniri (dk)
GRACE_MIN = 3  # slot + bu pencere icinde acik olan uygulama taramayi baslatir


def device_lag_min(device_id: str, max_lag: int = MAX_LAG_MIN) -> int:
    """Cihaz kimliginden deterministik 0..max_lag dakika gecikme."""
    h = hashlib.sha256(device_id.encode("utf-8")).digest()
    return int.from_bytes(h[:2], "big") % (max_lag + 1)


def slot_for(day: dt.date, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE,
             lag_min: int = 0) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hour, minute) + dt.timedelta(minutes=lag_min)


def should_run(now: dt.datetime, last_ok: dt.datetime | None,
               hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE,
               lag_min: int = 0, handled_day: str = "",
               grace_min: int = GRACE_MIN,
               baslangic: dt.datetime | None = None) -> tuple:
    """(calismali_mi, neden). Kilit disi cagrilir; kilitliyse cagiran calistirmaz.

    Sadece slot aninda (slot..slot+grace) acik olan uygulama icin True doner.
    Kacirilan slot telafi edilmez ("kacirildi-atlandi").
    """
    today_slot = slot_for(now.date(), hour, minute, lag_min)
    if handled_day >= now.date().isoformat():
        return False, "bugunku-slot-ele-alindi"
    if last_ok is not None and last_ok >= today_slot:
        return False, "bugunku-slot-tamam"
    if now < today_slot:
        return False, "slot-bekliyor"
    if now > today_slot + dt.timedelta(minutes=grace_min):
        # Uygulama o saatte acik degildi (veya uyuyordu): telafi yok.
        return False, "kacirildi-atlandi"
    if baslangic is not None and baslangic >= today_slot:
        # Uygulama slot anindan sonra acildi: acilis tarama tetiklemez.
        return False, "kacirildi-atlandi"
    return True, "slot-geldi"


def mark_done() -> dt.datetime:
    return dt.datetime.now()


def quota_left(con, day_iso: str) -> int | None:
    """Gunluk tarama kotasindan kalan. Ayar yoksa/sifirsa None (sinirsiz)."""
    from . import migrate as M
    try:
        kota = int(M.get_setting(con, "gunluk_kota", "0"))
    except ValueError:
        kota = 0
    if kota <= 0:
        return None
    try:
        used = int(M.get_setting(con, f"kota_tuketilen_{day_iso}", "0"))
    except ValueError:
        used = 0
    return max(0, kota - used)


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


def autostart_guncelle(app_name: str, exe_path: str, vault_path: str | None = None) -> bool:
    """Refresh the startup entry to the running EXE path when one exists; otherwise untouched.

Since an update moves the program to a new folder, the old entry points at
the old folder; without a refresh the machine would launch the old version
on next boot. A closed (deleted) entry never reopens itself."""
    mevcut = autostart_get(app_name)
    if mevcut is None:
        return False
    try:
        import subprocess
        command = [exe_path, "--tray"]
        if vault_path:
            command.extend(["--kasa", vault_path])
        beklenen = subprocess.list2cmdline(command)
        if os.path.normcase(mevcut.strip()) == os.path.normcase(beklenen):
            return False
        autostart_set(app_name, exe_path, vault_path)
        return True
    except OSError:
        return False
