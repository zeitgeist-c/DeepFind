"""Arama kutusu sorgu sözdizimi: `alan:değer` çözümleyicisi.

Desen kaynağı (REA): docspell `PowerSearchInput` — yazarken çözümle, hatalı
girdide konumu (şapka) göster ve geçersiz sorguda aramayı çalıştırma.

Alanlar arayüzdeki filtre denetimleriyle aynıdır ve onları besler:

- `yil:` (4 hane) — ör. `yil:2024`
- `tur:` — ör. `tur:pdf` ya da `tur:.pdf`
- `etiket:` — ör. `etiket:"vergi 2024"` (tırnak boşluk taşır)
- `klasor:` — ör. `klasor:ankara`

Alan adları Türkçe harf katlamasına dayanıklıdır (`yıl` = `yil`). Alan dışı
sözcükler serbest metin olarak aramaya girer; çözümleyici saf işlevdir.
"""
from __future__ import annotations

from typing import NamedTuple
from .theme import t

ALANLAR = ("yil", "tur", "etiket", "klasor")

# Kullanıcıya gösterilecek alan yardımı
YARDIM = "yil:2024  tur:pdf  etiket:\"vergi 2024\"  klasor:ankara"


class Cozum(NamedTuple):
    serbest: str      # alan dışı serbest metin
    alanlar: dict     # {alan: değer}
    hata: str         # "" ise geçerli
    imlec: int        # hata konumu (yoksa -1)


def katla(metin: str) -> str:
    """Türkçe harfleri sade ASCII'ye indirir (yıl → yil)."""
    for a, b in (("ı", "i"), ("İ", "i"), ("ğ", "g"), ("Ğ", "g"), ("ş", "s"), ("Ş", "s"),
                 ("ç", "c"), ("Ç", "c"), ("ö", "o"), ("Ö", "o"), ("ü", "u"), ("Ü", "u")):
        metin = metin.replace(a, b)
    return metin.lower()


def _alan_karakteri(karakter: str) -> bool:
    return karakter.isalnum() or karakter in "ıİğĞşŞçÇöÖüÜ"


def cozumle(metin: str, turler=()) -> Cozum:
    """Sorgu metnini serbest metin + alan sözlüğüne çözer; hata varsa konum verir."""
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
    """Hata konumunu gösteren şapka satırı (docspell deseni)."""
    if imlec < 0:
        return ""
    return " " * max(0, min(imlec, len(metin))) + "^"
