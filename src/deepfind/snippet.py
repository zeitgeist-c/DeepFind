"""Ham-metin snippet: folded eslesme konumlari ham metne birebir islenir.

Konum eslemesi uzunlugu koruyan katlama (`folded_esit_uzunluk`) ile yapilir;
`folded` bosluklari daralttigi icin offset kaydirirdi. Cikti HTML olarak
`QTextDocument.setHtml` ile gosterildigi icin metin parcalari kacirilir:
belge icerigi etiket gibi yorumlanmaz, `<b>` yalniz vurgu icin uretilir.
Uydurma bbox yok.
"""
from __future__ import annotations

from html import escape

from . import normalize as nz


def _katla(metin: str) -> str:
    """Uzunlugu koruyan katlama: len(sonuc) == len(metin)."""
    return nz.folded_esit_uzunluk(metin)


def highlight(raw: str, terms_folded: list, width: int = 200) -> str:
    raw = raw or ""
    f = _katla(raw)
    best = -1
    for t in terms_folded:
        if not t:
            continue
        i = f.find(t)
        if i >= 0 and (best < 0 or i < best):
            best = i
    if best < 0:
        s = raw[:width]
        return escape(s) + (" …" if len(raw) > width else "")
    start = max(0, best - width // 3)
    end = min(len(raw), start + width)
    window = raw[start:end]
    # terimleri pencerede bold'la (ham karsiliklariyla)
    out = []
    i = 0
    fl = _katla(window)
    sirali = sorted({t for t in terms_folded if t}, key=len, reverse=True)
    while i < len(window):
        hit = None
        for t in sirali:
            if fl.startswith(t, i):
                hit = t
                break
        if hit:
            out.append("<b>" + escape(window[i:i + len(hit)]) + "</b>")
            i += len(hit)
        else:
            out.append(escape(window[i]))
            i += 1
    pre = "… " if start > 0 else ""
    post = " …" if end < len(raw) else ""
    return pre + "".join(out) + post

