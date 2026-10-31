"""Consume folder: a settled file moves to the target; indexing stays with normal scan.

Design: the move is atomic on the filesystem (os.replace), the DB record does not move —
the old path record is deleted, the target is re-indexed by a scoped mini-scan
(all lanes including OCR run). Unsupported types are left in place."""
from __future__ import annotations

import os
import time

STABLE_NS = 2_000_000_000  # same decision threshold as the coordinator


def _desteklenir(path: str) -> bool:
    from . import scan as scan_mod
    return os.path.splitext(path)[1].lower() in scan_mod.SUPPORTED_EXTS


def _hedef_yol(hedef_dir: str, ad: str) -> str:
    kok, uzanti = os.path.splitext(ad)
    aday = os.path.join(hedef_dir, ad)
    n = 2
    while os.path.exists(aday):
        aday = os.path.join(hedef_dir, f"{kok} ({n}){uzanti}")
        n += 1
    return aday


def tuket(con, path: str, hedef_dir: str) -> str:
    """'moved' | 'unstable' | 'skipped'. Exception when the DB is locked (caller defers)."""
    if not os.path.isfile(path) or not os.path.isdir(hedef_dir):
        return "skipped"
    if not _desteklenir(path):
        return "skipped"
    try:
        con.execute("PRAGMA busy_timeout=5000")
        st = os.stat(path)
        if time.time_ns() - st.st_mtime_ns < STABLE_NS:
            return "unstable"
        varis = _hedef_yol(hedef_dir, os.path.basename(path))
        # Drop the index record first, then move: when the DB is locked the file is moved
        # but no record left behind under its old path (ghost) in the index.
        con.execute("DELETE FROM files WHERE path=?", (os.path.abspath(path),))
        con.execute("DELETE FROM files WHERE path=?", (path,))
        con.commit()
        os.replace(path, varis)
        return "moved"
    except OSError:
        return "skipped"
