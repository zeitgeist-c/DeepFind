"""Tüketim klasörü: kararlı dosya hedefe taşınır; indeksleme normal taramaya kalır.

Tasarım: taşıma dosya sisteminde atomik (os.replace), DB kaydı taşınmaz —
eski yol kaydı silinir, hedef kapsamlı mini taramada yeniden indekslenir
(OCR dahil tüm hatlar çalışır). Desteklenmeyen türler yerinde bırakılır.
"""
from __future__ import annotations

import os
import time

STABLE_NS = 2_000_000_000  # coordinator ile aynı karar eşiği


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
    """'moved' | 'unstable' | 'skipped'. DB kilitliyse exception (çağıran erteler)."""
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
        os.replace(path, varis)
        # Eski yolun indeks artığı kalmasın; hedef taramada sıfırdan yazılır.
        con.execute("DELETE FROM files WHERE path=?", (os.path.abspath(path),))
        con.execute("DELETE FROM files WHERE path=?", (path,))
        con.commit()
        return "moved"
    except OSError:
        return "skipped"
