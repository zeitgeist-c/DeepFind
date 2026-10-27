"""One-time rename of the pre-rename vault file to deepfind.db.

The vault is a SQLCipher database. Renaming the file is safe: the encryption key
derives from the user password and the salt stored inside the file, not from the
filename. Still, this refuses to overwrite and reports what it did.
"""

from __future__ import annotations

import sys

from . import paths


def migrate_vault_filename() -> str | None:
    """Rename evrakci.db -> deepfind.db if the old name is still in use.

    Returns the message to show the user, or None when there was nothing to do.
    """
    new = paths.vault_db()
    old = paths.legacy_vault_db()

    if new.exists():
        return None
    if not old.exists():
        return None

    try:
        old.rename(new)
    except OSError as exc:
        print(
            f"Warning: could not rename {old.name} to {new.name}: {exc}. "
            f"The vault is still readable under its old name.",
            file=sys.stderr,
        )
        return None
    return f"Kasa dosyasi {old.name} -> {new.name} olarak yeniden adlandirildi."
