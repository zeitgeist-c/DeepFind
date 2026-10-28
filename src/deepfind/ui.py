"""Paylaşılan görsel bileşenler: yüzeyler, satırlar, rozetler, boş durumlar.

Tasarım kuralı: tek yüzey + kıl payı ayırıcı. Kutu içinde kutu yok; renkler
her zaman `theme.pal()` üzerinden gelir, sabit renk kullanılmaz.
"""
from PySide6.QtCore import Qt, QSize, QRect, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QFontMetrics, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
                               QStyledItemDelegate, QStyle, QSizePolicy)
from . import theme
from .theme import t


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


class GorselKutusu(QLabel):
    """Küçük resmi kutusuna sığdıran, kutu ölçüsü değişince yeniden ölçekleyen görsel.

    Sabit yükseklik kulllanılmaz: sütun kısaldığında sabit kutu taşar ve
    alttaki metinlerle çakışır. Bu bileşen en-boy oranını korur; kutu minimum
    ölçünün altına inmez, fazla alanı kendisi alır.
    """

    def __init__(self, parent=None, minimum=(180, 200), maximum_height=420):
        super().__init__(parent)
        self.setObjectName("thumbBox")
        self.setAlignment(Qt.AlignCenter)
        self.setAccessibleName(t("Seçili evrak önizlemesi"))
        self.setMinimumSize(*minimum)
        self.setMaximumHeight(maximum_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._kaynak = None

    def gorsel_ata(self, pixmap):
        self._kaynak = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._yerlestir()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._yerlestir()

    def _yerlestir(self):
        if self._kaynak is None:
            self.clear()
            return
        self.setPixmap(self._kaynak.scaled(self.size(), Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation))


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
    icon.setAccessibleName("DeepFind logosu")
    row.addWidget(icon)
    text = QVBoxLayout()
    text.setSpacing(0)
    from .version import __version__
    title = QHBoxLayout()
    title.setSpacing(6)
    ad = QLabel("DeepFind")
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
    alt = QLabel(t("BELGE ARŞİVİNİZ"))
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
    """Düz liste satırı: başlık + ikincil satırlar; seçimde sol vurgu çubuğu.

    `thumb=True` iken satır başında küçük resim kutusu çizilir. Görsel
    `Qt.DecorationRole`'den gelir (QPixmap); yoksa nötr zeminde simge düşer,
    böylece yükleme gecikmesi düzeni zıplatıp yeniden akıtmaz.
    """

    _ONBELLEK = {}

    def __init__(self, parent, kind="document", *, compact=False, thumb=False):
        super().__init__(parent)
        self.kind = kind
        self.compact = compact
        self.thumb = thumb

    def _ikon(self, renk):
        anahtar = (self.kind, renk)
        if anahtar not in CardDelegate._ONBELLEK:
            CardDelegate._ONBELLEK[anahtar] = theme.symbol_icon(self.kind, renk)
        return CardDelegate._ONBELLEK[anahtar]

    def _satir_yuksekligi(self):
        if self.compact:
            return 56
        if self.kind == "document":
            return 104
        return 78

    def sizeHint(self, option, index):
        return QSize(240, self._satir_yuksekligi())

    def _gorsel_ciz(self, painter, index, kutu: QRectF, p):
        """Küçük resim kutusunu çizer; görsel yoksa nötr zeminde simge koyar."""
        pixmap = index.data(Qt.DecorationRole)
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            gorsel = pixmap.scaled(int(kutu.width()), int(kutu.height()),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            kirp = QPainterPath()
            kirp.addRoundedRect(kutu, 7, 7)
            painter.save()
            painter.setClipPath(kirp)
            painter.drawPixmap(int(kutu.left() + (kutu.width() - gorsel.width()) / 2),
                               int(kutu.top() + (kutu.height() - gorsel.height()) / 2),
                               gorsel)
            painter.restore()
            return
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["yuzey2"]))
        painter.drawRoundedRect(kutu, 7, 7)
        ikon = self._ikon(p["ikincil"]).pixmap(20, 20)
        painter.drawPixmap(int(kutu.center().x() - 10), int(kutu.center().y() - 10), ikon)

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
        ust = int(rect.top())
        gorsel_genislik = 0
        if self.thumb:
            kutu = (QRectF(rect.left() + 8, ust + 5, 36, 46) if self.compact
                    else QRectF(rect.left() + 10, ust + 9, 66, 86))
            self._gorsel_ciz(painter, index, kutu, p)
            gorsel_genislik = int(kutu.width()) + 10
        sol = int(rect.left() + 14 + gorsel_genislik)
        genislik = max(20, int(rect.width() - 26 - gorsel_genislik))
        if self.compact:
            satirlar = (13, 11) if self.thumb else (14, 11.5)
            yukseklikler = (28, 20) if self.thumb else (22, 18)
            if not self.thumb:
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


class Cip(QFrame):
    """Kaldırılabilir filtre çipi: etiket + × düğmesi (paperless filtre rozeti deseni)."""

    silindi = Signal()

    def __init__(self, metin, parent=None):
        super().__init__(parent)
        self.setObjectName("cip")
        row = QHBoxLayout(self)
        row.setContentsMargins(9, 3, 5, 3)
        row.setSpacing(6)
        self.etiket = QLabel(metin)
        self.etiket.setProperty("cipMetin", True)
        row.addWidget(self.etiket)
        self.kaldir = QPushButton("×")
        self.kaldir.setObjectName("cipKaldir")
        self.kaldir.setFixedSize(17, 17)
        self.kaldir.setCursor(Qt.PointingHandCursor)
        self.kaldir.setToolTip(t("Bu filtreyi kaldır"))
        self.kaldir.setAccessibleName(t("{metin} filtresini kaldır", metin=metin))
        self.kaldir.clicked.connect(self.silindi.emit)
        row.addWidget(self.kaldir)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


class GridDelegate(QStyledItemDelegate):
    """Izgara görünümü: üstte küçük resim, altta ad ve tek satır bilgi."""

    def __init__(self, parent, hucre=(176, 212)):
        super().__init__(parent)
        self.hucre = hucre

    def sizeHint(self, option, index):
        return QSize(*self.hucre)

    def paint(self, painter, option, index):
        p = theme.pal()
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect.adjusted(5, 5, -5, -5))
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["secili"] if selected else
                                (p["yuzey2"] if hovered else p["panel"])))
        painter.drawRoundedRect(rect, 10, 10)
        if selected:
            painter.setPen(QPen(QColor(p["marka"]), 1.4))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 10, 10)
        kutu = QRectF(rect.left() + 9, rect.top() + 9, rect.width() - 18, rect.height() - 66)
        pixmap = index.data(Qt.DecorationRole)
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            gorsel = pixmap.scaled(int(kutu.width()), int(kutu.height()),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            kirp = QPainterPath()
            kirp.addRoundedRect(kutu, 7, 7)
            painter.save()
            painter.setClipPath(kirp)
            painter.drawPixmap(int(kutu.left() + (kutu.width() - gorsel.width()) / 2),
                               int(kutu.top() + (kutu.height() - gorsel.height()) / 2),
                               gorsel)
            painter.restore()
        else:
            painter.setBrush(QColor(p["yuzey2"]))
            painter.drawRoundedRect(kutu, 7, 7)
            ikon = theme.symbol_icon("document", p["ikincil"]).pixmap(24, 24)
            painter.drawPixmap(int(kutu.center().x() - 12), int(kutu.center().y() - 12), ikon)
        lines = str(index.data(Qt.DisplayRole) or "").splitlines()
        ad = QFont(option.font)
        ad.setPixelSize(12)
        ad.setWeight(QFont.DemiBold)
        painter.setFont(ad)
        painter.setPen(QColor(p["metin"]))
        genislik = int(rect.width() - 18)
        painter.drawText(int(rect.left() + 9), int(kutu.bottom() + 20),
                         QFontMetrics(ad).elidedText(lines[0] if lines else "", Qt.ElideMiddle, genislik))
        if len(lines) > 1:
            alt = QFont(option.font)
            alt.setPixelSize(10)
            painter.setFont(alt)
            painter.setPen(QColor(p["ikincil"]))
            painter.drawText(int(rect.left() + 9), int(kutu.bottom() + 36),
                             QFontMetrics(alt).elidedText(" • ".join(lines[1:3]),
                                                          Qt.ElideRight, genislik))
        painter.restore()
