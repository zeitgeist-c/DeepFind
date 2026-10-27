"""Single source of truth for every on-disk path the app uses.

Renaming the product must not orphan an existing vault. `data_root()` returns the
DeepFind folder, but if the pre-rename Evrakci folder exists and DeepFind does
not, it moves it once, at first touch, and leaves a marker so a failed move is
never half-applied.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "DeepFind"
LEGACY_DIR_NAMES = ("Evrakci", "Evrakçı")
_MARKER = ".renamed-from-evrakci"


def _base() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"))


def data_root() -> Path:
    """Return the app data folder, migrating a pre-rename folder once."""
    base = _base()
    target = base / APP_DIR_NAME
    if target.is_dir():
        return target

    for legacy_name in LEGACY_DIR_NAMES:
        legacy = base / legacy_name
        if not legacy.is_dir():
            continue
        try:
            shutil.move(str(legacy), str(target))
        except OSError as exc:  # locked file, permissions, cross-device
            print(
                f"Warning: could not move {legacy} to {target}: {exc}. "
                f"The existing vault stays where it is; pass it explicitly.",
                file=sys.stderr,
            )
            return legacy
        marker = target / _MARKER
        try:
            marker.write_text(str(legacy), encoding="utf-8")
        except OSError:
            pass
        return target

    return target


def ensure_dir(*parts: str) -> Path:
    path = data_root().joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def vault_db() -> Path:
    return data_root() / "Data" / "deepfind.db"


def legacy_vault_db() -> Path:
    """The pre-rename vault filename, used by the one-time DB rename."""
    return data_root() / "Data" / "evrakci.db"


def logs_dir() -> Path:
    return ensure_dir("Logs")


def credentials_dir() -> Path:
    return ensure_dir("Credentials")


def updates_dir() -> Path:
    return ensure_dir("Updates")


def engines_dir(engine_id: str) -> Path:
    return ensure_dir("Engines", engine_id)


def thumbs_dir() -> Path:
    return ensure_dir("thumbs")
