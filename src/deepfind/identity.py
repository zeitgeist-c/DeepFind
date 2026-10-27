"""Identity keys that must survive the rename.

QSettings stores window geometry and the chosen theme under the organisation name.
HKCU\\...\\Run stores the autostart entry under a value name. If either is renamed
blindly, the user loses their window layout, theme and autostart registration and
gets a second stale entry. So the new name is used, and the old one is migrated
once, at startup, before anything reads it.
"""

from __future__ import annotations

import sys

APP_IDENTITY = "DeepFind"
LEGACY_IDENTITY = "Evrakci"
_SETTINGS_APP = "Appearance"


def migrate_qsettings() -> str | None:
    """Copy the pre-rename QSettings file to the new identity, once."""
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        return None

    new = QSettings(APP_IDENTITY, _SETTINGS_APP)
    old = QSettings(LEGACY_IDENTITY, _SETTINGS_APP)

    if new.allKeys():
        return None                      # new identity already in use
    old_keys = old.allKeys()
    if not old_keys:
        return None                      # nothing to migrate

    for key in old_keys:
        new.setValue(key, old.value(key))
    new.sync()
    return f"{len(old_keys)} arayuz ayari {LEGACY_IDENTITY} -> {APP_IDENTITY} tasindi."


def migrate_autostart() -> str | None:
    """Rename the HKCU Run value if the old one is still registered."""
    if sys.platform != "win32":
        return None
    import winreg

    run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0,
                             winreg.KEY_READ | winreg.KEY_SET_VALUE)
    except OSError:
        return None

    try:
        try:
            old_value, value_type = winreg.QueryValueEx(key, LEGACY_IDENTITY)
        except OSError:
            return None                  # no legacy entry
        try:
            winreg.QueryValueEx(key, APP_IDENTITY)
            already = True
        except OSError:
            already = False
        if not already:
            winreg.SetValueEx(key, APP_IDENTITY, 0, value_type, old_value)
        winreg.DeleteValue(key, LEGACY_IDENTITY)
        return "Otomatik baslatma kaydi DeepFind adina tasindi."
    except OSError as exc:
        print(f"Warning: autostart migration failed: {exc}", file=sys.stderr)
        return None
    finally:
        winreg.CloseKey(key)


def migrate_all() -> list[str]:
    """Run every identity migration; returns human-readable notes."""
    notes = []
    for fn in (migrate_qsettings, migrate_autostart):
        try:
            msg = fn()
        except Exception as exc:                      # never block startup
            print(f"Warning: {fn.__name__} failed: {exc}", file=sys.stderr)
            continue
        if msg:
            notes.append(msg)
    return notes
