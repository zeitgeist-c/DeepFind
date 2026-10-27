"""Kasa: SQLCipher baglantisi. Anahtar diske/loga yazilmaz, burada tutulmaz."""
from __future__ import annotations

import sqlcipher3

from . import normalize as nz

BUSY_TIMEOUT_MS = 5000

# Sifresiz kasa ic anahtari: kullanici sifre belirlemezse kasa bununla acilir.
# Kullaniciya gosterilmez/sorulmaz; koruma Windows hesabi ve disk sifrelemesine
# dayanir. SQLCipher bos anahtar kabul etmedigi icin sabit bir ic anahtar gerekir.
SIFRESIZ_ANAHTAR = "DEEPFIND-SIFRESIZ-KASA-v1"


def _escape_key(password: str) -> str:
    return password.replace("'", "''")


def open_vault(path: str, password: str) -> sqlcipher3.Connection:
    con = sqlcipher3.connect(path, timeout=10)
    try:
        con.execute(f"PRAGMA key='{_escape_key(password)}'")
        con.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        con.execute("PRAGMA temp_store=MEMORY")
        con.execute("PRAGMA foreign_keys=ON")
        # Anahtar dogrulama: yanlis anahtarda DatabaseError verir.
        con.execute("SELECT count(*) FROM sqlite_master").fetchone()
        row = con.execute("PRAGMA cipher_version").fetchone()
        if not row or not str(row[0]).startswith("4."):
            raise RuntimeError(f"beklenmeyen cipher_version: {row}")
        con.execute("PRAGMA journal_mode=WAL")
        # Legacy snapshots may still contain fold() triggers before migration.
        nz.install(con)
        return con
    except Exception:
        con.close()
        raise


def sifresiz_mi(path: str) -> bool:
    """Kasa sifresiz modda mi: ic anahtar aciyor ve kasa isareti '1' mi.

    Isaret `settings.kasa_sifresiz`; kurulumda sifre bos birakildiysa 1 olur.
    Boylece kullanicinin sifresi tesadufen ic anahtarla ayni olsa bile
    sifresiz sayilmaz (isaret yoksa sifreli kasa varsayilir).
    """
    try:
        con = open_vault(path, SIFRESIZ_ANAHTAR)
    except Exception:
        return False
    try:
        row = con.execute("SELECT v FROM settings WHERE k='kasa_sifresiz'").fetchone()
        return bool(row) and row[0] == "1"
    except Exception:
        return False
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
