"""Paylaşılan görsel bileşenler: yüzeyler, satırlar, rozetler, boş durumlar.

Tasarım kuralı: tek yüzey + kıl payı ayırıcı. Kutu içinde kutu yok; renkler
her zaman `theme.pal()` üzerinden gelir, sabit renk kullanılmaz.
"""
from PySide6.QtCore import Qt, QSize, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QPen, QPainter, QFontMetrics
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
                               QStyledItemDelegate, QStyle, QSizePolicy)
from . import theme


def label(text, role=None):
    widget = QLabel(text)
    widget.setWordWrap(True)
    if role:
        widget.setProperty(role, True)
    return widget


def card():
    panel = QFrame()
    panel.setObjectName("card")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    return panel, layout


def bolme():
    """Bölümler arası ince yatay çizgi."""
    cizgi = QFrame()
    cizgi.setObjectName("ayrac")
    cizgi.setFrameShape(QFrame.NoFrame)
    return cizgi


def ayrac_d():
    """Sütunlar arası ince dikey çizgi."""
    cizgi = QFrame()
    cizgi.setObjectName("ayracD")
    cizgi.setFrameShape(QFrame.NoFrame)
    return cizgi


def sayfa_basi(baslik, aciklama=""):
    """Sayfa başlığı şeridi: başlık + açıklama; sağa denetim eklenir."""
    bar = QWidget()
    bar.setObjectName("headBar")
    bar.setAttribute(Qt.WA_StyledBackground, True)
    outer = QHBoxLayout(bar)
    outer.setContentsMargins(22, 16, 22, 14)
    outer.setSpacing(16)
    text = QVBoxLayout()
    text.setSpacing(2)
    bar.baslik = QLabel(baslik)
    bar.baslik.setProperty("baslik", True)
    text.addWidget(bar.baslik)
    bar.aciklama = QLabel(aciklama)
    bar.aciklama.setProperty("ikincil", True)
    bar.aciklama.setWordWrap(True)
    bar.aciklama.setVisible(bool(aciklama))
    text.addWidget(bar.aciklama)
    outer.addLayout(text, 1)
    bar.denetim = QHBoxLayout()
    bar.denetim.setSpacing(8)
    outer.addLayout(bar.denetim)
    return bar


def bolum(baslik):
    """Bölüm başlığı (kutu değil, yalnız yazı)."""
    return label(baslik, "eyebrow")


def sayac(text=""):
    """Sayaç rozeti."""
    chip = QLabel(text)
    chip.setProperty("sayac", True)
    chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return chip


def stat_seridi(kalemler):
    """Ölçü şeridi: (başlık, değer, alt yazı) üçlülerinden kutusuz şerit."""
    strip = QWidget()
    strip.setObjectName("statStrip")
    strip.setAttribute(Qt.WA_StyledBackground, True)
    row = QHBoxLayout(strip)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    for index, (key, value, hint) in enumerate(kalemler):
        if index:
            row.addWidget(ayrac_d())
        cell = QWidget()
        inner = QVBoxLayout(cell)
        inner.setContentsMargins(16, 13, 16, 13)
        inner.setSpacing(3)
        inner.addWidget(label(key, "eyebrow"))
        deger = QLabel(value)
        deger.setProperty("subheading", True)
        deger.setStyleSheet("font-size:20px; font-weight:650;")
        inner.addWidget(deger)
        if hint:
            inner.addWidget(label(hint, "ikincil"))
        inner.addStretch(1)
        row.addWidget(cell, 1)
        cell.deger = deger
    return strip


def ayar_satiri(baslik, ipucu, denetim):
    """Ayarlar satırı: solda başlık+ipucu, sağda denetim; altta kıl payı çizgi."""
    satir = QWidget()
    outer = QHBoxLayout(satir)
    outer.setContentsMargins(0, 9, 0, 9)
    outer.setSpacing(18)
    sol = QVBoxLayout()
    sol.setSpacing(1)
    ad = QLabel(baslik)
    ad.setWordWrap(True)
    font = QFont(ad.font())
    font.setWeight(QFont.DemiBold)
    ad.setFont(font)
    sol.addWidget(ad)
    if ipucu:
        sol.addWidget(label(ipucu, "ikincil"))
    outer.addLayout(sol, 1)
    if isinstance(denetim, QWidget):
        outer.addWidget(denetim, 0, Qt.AlignRight | Qt.AlignVCenter)
    else:
        outer.addLayout(denetim)
    cizgi = bolme()
    kutu = QWidget()
    kutu.setLayout(QVBoxLayout(kutu))
    kutu.layout().setContentsMargins(0, 0, 0, 0)
    kutu.layout().setSpacing(0)
    kutu.layout().addWidget(satir)
    kutu.layout().addWidget(cizgi)
    return kutu


class Toast(QWidget):
    """Pencere içi onay şeridi: kendiliğinden kaybolur, yerleşimi kaydırmaz."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(13, 9, 13, 9)
        self.row.setSpacing(9)
        self.icon = QLabel()
        self.row.addWidget(self.icon)
        self.text = QLabel("")
        self.text.setProperty("toast", True)
        self.row.addWidget(self.text, 1)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self.hide()

    def goster(self, mesaj, sure=2400):
        pal = theme.pal()
        self.icon.setPixmap(theme.symbol_icon("check", pal["marka"]).pixmap(16, 16))
        self.text.setText(mesaj)
        self.setStyleSheet(
            f"QWidget {{ background: {pal['marka_tint']}; border-radius: 9px; }}"
            f" QLabel {{ background: transparent; color: {pal['marka']}; font-size: 12px; font-weight: 600; }}")
        self.adjustSize()
        self.yerlestir()
        self.show()
        self.raise_()
        self._hide_timer.start(sure)

    def yerlestir(self):
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 22
        self.move(max(margin, parent.width() - self.width() - margin),
                  max(margin, parent.height() - self.height() - 34))


def brand(layout, *, size=34):
    row = QHBoxLayout()
    row.setSpacing(9)
    icon = QLabel()
    icon.setPixmap(theme.app_icon().pixmap(size, size))
    icon.setAccessibleName("Evrakçı logosu")
    row.addWidget(icon)
    text = QVBoxLayout()
    text.setSpacing(0)
    from .version import __version__
    title = QHBoxLayout()
    title.setSpacing(6)
    ad = QLabel("Evrakçı")
    font = QFont(ad.font())
    font.setPixelSize(15)
    font.setWeight(QFont.DemiBold)
    ad.setFont(font)
    title.addWidget(ad)
    surum = QLabel(__version__)
    surum.setProperty("eyebrow", True)
    title.addWidget(surum)
    title.addStretch()
    text.addLayout(title)
    alt = QLabel("BELGE ARŞİVİNİZ")
    alt.setProperty("eyebrow", True)
    text.addWidget(alt)
    row.addLayout(text, 1)
    layout.addLayout(row)


class EmptyState(QWidget):
    def __init__(self, title, text, kind="search", parent=None):
        super().__init__(parent)
        self.kind = kind
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setFixedSize(72, 72)
        self.yenile()
        kutu = QHBoxLayout()
        kutu.addStretch()
        kutu.addWidget(self.icon)
        kutu.addStretch()
        layout.addLayout(kutu)
        self.title = label(title, "subheading")
        self.title.setAlignment(Qt.AlignCenter)
        self.text = label(text, "ikincil")
        self.text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addStretch()

    def sizeHint(self):
        return QSize(340, 220)

    def yenile(self):
        p = theme.pal()
        self.icon.setPixmap(theme.symbol_icon(self.kind, p["ikincil"]).pixmap(36, 36))
        self.icon.setStyleSheet(
            f"QLabel {{ background: {p['yuzey2']}; border: 1px solid {p['sinir']};"
            f" border-radius: 18px; padding: 17px; }}")


class CardDelegate(QStyledItemDelegate):
    """Düz liste satırı: başlık + ikincil satırlar; seçimde sol vurgu çubuğu."""

    _ONBELLEK = {}

    def __init__(self, parent, kind="document", *, compact=False):
        super().__init__(parent)
        self.kind = kind
        self.compact = compact

    def _ikon(self, renk):
        anahtar = (self.kind, renk)
        if anahtar not in CardDelegate._ONBELLEK:
            CardDelegate._ONBELLEK[anahtar] = theme.symbol_icon(self.kind, renk)
        return CardDelegate._ONBELLEK[anahtar]

    def _satir_yuksekligi(self):
        if self.compact:
            return 54
        if self.kind == "document":
            return 104
        return 78

    def sizeHint(self, option, index):
        return QSize(240, self._satir_yuksekligi())

    def paint(self, painter, option, index):
        p = theme.pal()
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect.adjusted(0, 2, 0, -4))
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        if selected or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(p["secili"] if selected else p["yuzey2"]))
            painter.drawRoundedRect(rect, 9, 9)
        if selected:
            painter.setBrush(QColor(p["marka"]))
            painter.drawRoundedRect(QRectF(rect.left(), rect.top() + 7, 3, rect.height() - 14), 2, 2)
        lines = str(index.data(Qt.DisplayRole) or "").splitlines()
        sol = int(rect.left() + 14)
        genislik = max(20, int(rect.width() - 26))
        ust = int(rect.top())
        if self.compact:
            satirlar = (14, 11.5)
            yukseklikler = (22, 18)
            from PySide6.QtCore import QRect
            onbellek = self._ikon(p["marka"] if selected else p["ikincil"])
            onbellek.paint(painter, QRect(int(rect.left() + 12), int(rect.top() + 13), 20, 20))
            sol = int(rect.left() + 44)
            genislik = max(20, int(rect.width() - 56))
        else:
            satirlar = (14, 11.5, 11.5, 12.5, 11.5)
            yukseklikler = (24, 18, 18, 20, 18)
        for i, metin in enumerate(lines[: len(satirlar)]):
            font = QFont(option.font)
            font.setPixelSize(int(round(satirlar[i])))
            if i == 0:
                font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            if i == 0:
                painter.setPen(QColor(p["metin"]))
            elif i == 3 and not self.compact:
                painter.setPen(QColor(p["metin"]))
            else:
                painter.setPen(QColor(p["ikincil"]))
            painter.drawText(sol, ust + yukseklikler[i] * (i + 1) - 4,
                             QFontMetrics(font).elidedText(metin, Qt.ElideRight, genislik))
        painter.restore()
