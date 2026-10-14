"""Paylaşılan görsel bileşenler: marka, kartlar ve boş durumlar."""
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QFont, QPen, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
                               QStyledItemDelegate, QStyle)
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
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    return panel, layout


def bolme():
    """Bölümler arası ince çizgi."""
    cizgi = QFrame()
    cizgi.setObjectName("bolme")
    cizgi.setFrameShape(QFrame.HLine)
    return cizgi


def brand(layout, *, size=38):
    row = QHBoxLayout()
    icon = QLabel()
    icon.setPixmap(theme.app_icon().pixmap(size, size))
    icon.setAccessibleName("Evrakçı logosu")
    row.addWidget(icon)
    text = QVBoxLayout()
    text.setSpacing(1)
    from .version import __version__
    title = QHBoxLayout()
    title.addWidget(label("Evrakçı", "baslik"))
    title.addSpacing(6)
    title.addWidget(label(__version__, "eyebrow"))
    text.addLayout(title)
    text.addWidget(label("BELGE ARŞİVİNİZ", "eyebrow"))
    row.addLayout(text)
    row.addStretch()
    layout.addLayout(row)


class EmptyState(QWidget):
    def __init__(self, title, text, kind="search", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()
        icon = QLabel()
        icon.setPixmap(theme.symbol_icon(kind, "#6B9B9B").pixmap(64, 64))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        self.title = label(title, "subheading")
        self.title.setAlignment(Qt.AlignCenter)
        self.text = label(text, "ikincil")
        self.text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addStretch()


class CardDelegate(QStyledItemDelegate):
    def __init__(self, parent, kind="document", *, compact=False):
        super().__init__(parent)
        self.kind = kind
        self.compact = compact
        self.icon = theme.symbol_icon(kind, "#137C70")
        self.dark_icon = theme.symbol_icon(kind, "#67D9BC")

    def sizeHint(self, option, index):
        return QSize(280, 64 if self.compact else (120 if self.kind == "document" else 92))

    def paint(self, painter, option, index):
        from PySide6.QtWidgets import QApplication
        dark = QApplication.instance().property("evrakci_theme") == "koyu"
        pal = theme.TOKENS["koyu" if dark else "acik"]
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect.adjusted(1, 2, -1, -6))
        selected = bool(option.state & QStyle.State_Selected)
        painter.setPen(QPen(QColor(pal["marka"] if selected else pal["sinir"]), 1))
        painter.setBrush(QColor(pal["secili"] if selected else pal["panel"]))
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(pal["secili"]))
        tile = QRectF(rect.left() + 12, rect.top() + 11, 32, 32) if self.compact else QRectF(rect.left() + 14, rect.top() + 17, 40, 40)
        painter.drawRoundedRect(tile, 9, 9)
        (self.dark_icon if dark else self.icon).paint(painter, tile.toRect().adjusted(8, 8, -8, -8))
        lines = str(index.data(Qt.DisplayRole) or "").splitlines()
        left = int(rect.left() + (54 if self.compact else 68))
        width = max(10, int(rect.right() - left - 12))
        font = QFont(option.font)
        font.setPixelSize(14)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(pal["metin"]))
        painter.drawText(left, int(rect.top() + (24 if self.compact else 30)),
                         painter.fontMetrics().elidedText(lines[0] if lines else "", Qt.ElideRight, width))
        font.setPixelSize(12)
        font.setWeight(QFont.Normal)
        painter.setFont(font)
        painter.setPen(QColor(pal["ikincil"]))
        for i, text in enumerate(lines[1:2] if self.compact else lines[1:4]):
            painter.drawText(left, int(rect.top() + (44 if self.compact else 50) + i * 20),
                             painter.fontMetrics().elidedText(text, Qt.ElideRight, width))
        painter.restore()
