"""Turkce normalizasyon: strict (harf korur) + folded (tolerans). Surum pinli."""
from __future__ import annotations

import re
import unicodedata
from .theme import t

NORMALIZER_VERSION = "a5-1"

_FOLD = str.maketrans({
    "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "ı": "i",
})


def tr_lower(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("I", "ı").replace("İ", "i")
    return s.lower()


def strict(s: str) -> str:
    return re.sub(r"\s+", " ", tr_lower(s)).strip()


def folded(s: str) -> str:
    return strict(s).translate(_FOLD)


def folded_esit_uzunluk(s: str) -> str:
    """Length-preserving TR lower + diacritic folding.

`folded` shifts positions by collapsing spaces, so this version is used
wherever raw-text offsets must match one-to-one, like snippets.
Rule: every character maps to exactly one character."""
    parcalar = []
    for karakter in s or "":
        kucuk = karakter.replace("I", "ı").replace("İ", "i").lower()
        parcalar.append(kucuk if len(kucuk) == 1 else karakter)
    return "".join(parcalar).translate(_FOLD)


def install(con) -> None:
    """Register the fold() UDF on the connection. Must run on every connection: FTS
triggers write the folded text into the index from inside this SQL (v9).
Idempotent: re-registering when registered may raise SQLITE_MISUSE."""
    try:
        con.execute("SELECT fold('i')").fetchone()
    except Exception:
        con.create_function("fold", 1, folded, deterministic=True)


TOKEN_RE = re.compile(r"[a-zçğıöşü0-9]+", re.IGNORECASE)


def tokens_folded(s: str) -> list:
    return TOKEN_RE.findall(folded(s))


YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def extract_years(*texts: str) -> list:
    out = []
    for t in texts:
        for m in YEAR_RE.findall(t or ""):
            if m not in out:
                out.append(m)
    return out
