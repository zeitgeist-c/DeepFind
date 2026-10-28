"""Ham-metin snippet: folded eslesme konumlari ham metne birebir islenir.

Butun normalizasyon adimlari (NFC, TR lower, diakritik fold) tek-karaktere-tek-karakter
oldugundan folded offset == ham offset. Uydurma bbox yok.
"""
from __future__ import annotations

from . import normalize as nz


def highlight(raw: str, terms_folded: list, width: int = 200) -> str:
    f = nz.folded(raw or "")
    best = -1
    for t in terms_folded:
        i = f.find(t)
        if i >= 0 and (best < 0 or i < best):
            best = i
    if best < 0:
        s = (raw or "")[:width]
        return s + (" …" if len(raw or "") > width else "")
    start = max(0, best - width // 3)
    end = min(len(raw or ""), start + width)
    window = (raw or "")[start:end]
    # terimleri pencerede bold'la (ham karsiliklariyla)
    out = []
    i = 0
    fl = nz.folded(window)
    while i < len(window):
        hit = None
        for t in sorted(terms_folded, key=len, reverse=True):
            if fl.startswith(t, i):
                hit = t
                break
        if hit:
            out.append("<b>" + window[i:i + len(hit)] + "</b>")
            i += len(hit)
        else:
            out.append(window[i])
            i += 1
    pre = "… " if start > 0 else ""
    post = " …" if end < len(raw or "") else ""
    return pre + "".join(out) + post
