"""Search-box query syntax: the `alan:değer` parser.

Pattern source (REA): docspell `PowerSearchInput` — parse while typing, show the
position (caret) on bad input, never run the search on an invalid query.

Fields match the UI filter controls and feed them:

- `yil:` (4 digits) — e.g. `yil:2024`
- `tur:` — e.g. `tur:pdf` or `tur:.pdf`
- `etiket:` — e.g. `etiket:"vergi 2024"` (quotes carry spaces)
- `klasor:` — e.g. `klasor:ankara`

Field names survive Turkish letter folding (`yıl` = `yil`). Out-of-field
words enter the search as free text; the parser is a pure function."""
from __future__ import annotations

from typing import NamedTuple
from .theme import t

ALANLAR = ("yil", "tur", "etiket", "klasor")

# Field help shown to the user
YARDIM = "yil:2024  tur:pdf  etiket:\"vergi 2024\"  klasor:ankara"


class Cozum(NamedTuple):
    serbest: str      # free text outside fields
    alanlar: dict     # {alan: değer}
    hata: str         # "" means valid
    imlec: int        # hata konumu (yoksa -1)


def katla(metin: str) -> str:
    """Fold Turkish letters down to plain ASCII (yıl → yil)."""
    for a, b in (("ı", "i"), ("İ", "i"), ("ğ", "g"), ("Ğ", "g"), ("ş", "s"), ("Ş", "s"),
                 ("ç", "c"), ("Ç", "c"), ("ö", "o"), ("Ö", "o"), ("ü", "u"), ("Ü", "u")):
        metin = metin.replace(a, b)
    return metin.lower()


def _alan_karakteri(karakter: str) -> bool:
    return karakter.isalnum() or karakter in "ıİğĞşŞçÇöÖüÜ"


def cozumle(metin: str, turler=()) -> Cozum:
    """Parse the query text into free text + field dict; give a position on error."""
    serbest: list[str] = []
    alanlar: dict[str, str] = {}
    gecerli_turler = {katla("." + tur.lstrip(".")) for tur in turler if tur and tur != t("tümü")}
    i, n = 0, len(metin)
    while i < n:
        if metin[i].isspace():
            i += 1
            continue
        bas = i
        j = i
        while j < n and _alan_karakteri(metin[j]):
            j += 1
        if j < n and metin[j] == ":" and j > i:
            alan = katla(metin[i:j])
            if alan not in ALANLAR:
                return Cozum(" ".join(serbest), alanlar, f"bilinmeyen alan: '{metin[i:j]}'", i)
            i = j + 1
            if i < n and metin[i] == '"':
                son = metin.find('"', i + 1)
                if son < 0:
                    return Cozum(" ".join(serbest), alanlar, t("kapanmayan tırnak"), i)
                deger = metin[i + 1:son]
                i = son + 1
            else:
                k = i
                while k < n and not metin[k].isspace():
                    k += 1
                deger = metin[i:k]
                i = k
            if not deger:
                return Cozum(" ".join(serbest), alanlar, t("'{alan}' alanı değer bekliyor", alan=alan), bas)
            if alan == "yil" and not (len(deger) == 4 and deger.isdigit()):
                return Cozum(" ".join(serbest), alanlar, t("'yil' 4 haneli olmalı (ör. 2024)"), bas)
            if alan == "tur":
                deger = "." + deger.lstrip(".")
                if gecerli_turler and katla(deger) not in gecerli_turler:
                    return Cozum(" ".join(serbest), alanlar, t("bilinmeyen tür: '{deger}'", deger=deger), bas)
            alanlar[alan] = deger
        else:
            k = i
            while k < n and not metin[k].isspace():
                k += 1
            serbest.append(metin[i:k])
            i = k
    return Cozum(" ".join(serbest), alanlar, "", -1)


def imlec_satiri(metin: str, imlec: int) -> str:
    """Caret line marking the error position (docspell pattern)."""
    if imlec < 0:
        return ""
    return " " * max(0, min(imlec, len(metin))) + "^"
