"""Kasa: normal kullanimda sifresiz SQLite.

Sifreleme kaldirildi. Bu modul `sqlcipher3` ice aktarmaz; normal veri yolu
saf `sqlite3` kullanir. Eski sifreli kasalar icin bk. `vault_convert`.
"""
from __future__ import annotations

import os
import sqlite3

from . import normalize as nz

BUSY_TIMEOUT_MS = 5000

# Geriye uyumluluk: eski cagrilar `vault.SIFRESIZ_ANAHTAR` gecirir; yok sayilir.
SIFRESIZ_ANAHTAR = "DEEPFIND-SIFRESIZ-KASA-v1"

_SQLITE_HEADER = b"SQLite format 3\x00"


class EncryptedVaultError(RuntimeError):
    """Dosya sifreli eski format; `vault_convert` ile donusturulmeli."""


def is_encrypted(path: str) -> bool:
    """Sifreli/bozuk dosyayi baslik + acilis denemesiyle ayirt et."""
    try:
        with open(path, "rb") as fh:
            if fh.read(len(_SQLITE_HEADER)) == _SQLITE_HEADER:
                return False
    except OSError:
        return False
    try:
        con = sqlite3.connect(path, timeout=10)
        try:
            con.execute("SELECT count(*) FROM sqlite_master").fetchone()
            return False
        finally:
            con.close()
    except Exception:
        return True
    return True


def open_vault(path: str, password: str | None = None) -> sqlite3.Connection:
    """Sifresiz kasayi ac. `password` yalniz eski cagrilar icin yok sayilir."""
    if path and os.path.isfile(path) and is_encrypted(path):
        raise EncryptedVaultError(
            "Bu kasa eski sifreli bicimde. Lutfen once 'kasa-donustur' "
            "ile sifresiz bicime donusturun; mevcut parola yalniz donusumde istenir."
        )
    con = sqlite3.connect(path, timeout=10)
    try:
        con.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        con.execute("PRAGMA temp_store=MEMORY")
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("SELECT count(*) FROM sqlite_master").fetchone()
        con.execute("PRAGMA journal_mode=WAL")
        nz.install(con)
        return con
    except Exception:
        con.close()
        raise


def sifresiz_mi(path: str) -> bool:
    """Yeni dunyada: duz SQLite aciliyorsa sifresiz sayilir."""
    try:
        con = open_vault(path)
    except Exception:
        return False
    try:
        return True
    finally:
        con.close()


def lock(con, vault_dir: str) -> bool:
    """Kasayi kilitle: baglantilari kapat, kontrollu temp artiklarini temizle.

    Yeni is baslatilmaz, sonuc/onislem cache'i cagiranda temizlenir (A7 UI).
    Donus: her zaman True (idempotent sayilmaz; kapali con tekrar kapatilmaz).
    """
    from .ocr import clean_stale
    try:
        con.close()
    except Exception:
        pass
    try:
        clean_stale(vault_dir)
    except Exception:
        pass
    return True
