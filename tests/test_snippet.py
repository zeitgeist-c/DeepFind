"""Snippet: ham metin offset'i + HTML kaçışı.

Regresyon: `nz.folded` boşlukları daralttığı için folded offset ham offset'ten
kayıyordu (yanlış pencere, boşlukların bold'lanması); snippet `setHtml` ile
gösterildiği için belge metnindeki `<...>` etiket gibi yorumlanıp kayboluyordu.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from deepfind import normalize as nz, snippet as snip


def _plain(html):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QTextDocument
    QApplication.instance() or QApplication([])
    doc = QTextDocument()
    doc.setHtml(html)
    return doc.toPlainText()


def test_esit_uzunluk_katlama_uzunlugu_korur():
    for metin in ("İSTANBUL", "IŞIK  ĞÜŞİÖÇ", "a\n\n\nb", "Sozlesme <ek-1> & 2024"):
        assert len(nz.folded_esit_uzunluk(metin)) == len(metin)


def test_vurgu_dogru_konumda():
    raw = "x" * 50 + "\n" * 20 + "ARANAN kelime"
    html = snip.highlight(raw, nz.tokens_folded("aranan"))
    assert "<b>ARANAN</b>" in html
    assert "ARANAN" in _plain(html)


def test_turkce_buyuk_harf_eslesir():
    raw = "SÖZLEŞME ŞARTLARI: İSTANBUL 2024"
    html = snip.highlight(raw, nz.tokens_folded("istanbul"))
    assert "<b>İSTANBUL</b>" in html


def test_belge_metni_html_olarak_yorumlanmaz():
    raw = "Sozlesme <ek-1> maddesi & taraf 2024"
    html = snip.highlight(raw, nz.tokens_folded("taraf"))
    duz = _plain(html)
    assert "<ek-1>" in duz and "&" in duz
    assert "<b>taraf</b>" in html


def test_eslesme_yoksa_bas_ve_uzunluk():
    out = snip.highlight("abc" * 200, nz.tokens_folded("zzz"))
    assert out.endswith("…") and len(out) <= 202
