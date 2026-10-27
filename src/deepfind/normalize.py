"""Turkce normalizasyon: strict (harf korur) + folded (tolerans). Surum pinli."""
from __future__ import annotations

import re
import unicodedata

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
    """Uzunluğu değiştirmeyen TR lower + diakritik katlama.

    `folded` boşlukları daralttığı için konum kaydırır; snippet gibi ham
    metin offset'i ile birebir eşleşmesi gereken yerlerde bu sürüm kullanılır.
    Kural: her karakter tek karaktere eşlenir (İ→i, I→ı, ş→s, boşluk→boşluk).
    """
    parcalar = []
    for karakter in s or "":
        kucuk = karakter.replace("I", "ı").replace("İ", "i").lower()
        parcalar.append(kucuk if len(kucuk) == 1 else karakter)
    return "".join(parcalar).translate(_FOLD)


def install(con) -> None:
    """fold() UDF'ini bağlantıya kaydet. Her bağlantıda çağrılmalı: FTS
    trigger'ları indekse katlanmış metni bu SQL içinden yazar (v9).
    Idempotent: kayitliyse yeniden kaydetme SQLITE_MISUSE verebilir."""
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
