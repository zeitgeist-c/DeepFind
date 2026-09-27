"""Tasarim jetonlari: acik/koyu/sistem. Plan bolum 19 baslangic paleti."""
from __future__ import annotations

TOKENS = {
    "acik": {
        "zemin": "#F3F5F9", "panel": "#FFFFFF", "metin": "#172033", "buton_metin": "#FFFFFF",
        "ikincil": "#526176", "marka": "#1D3FAA", "sinir": "#DCE3ED",
        "secili": "#E3EBFA", "uyari": "#8A5A00", "hata": "#A32222", "basari": "#1E6B34",
    },
    "koyu": {
        "zemin": "#10151F", "panel": "#192230", "metin": "#F3F6FC", "buton_metin": "#10151F",
        "ikincil": "#BAC5D6", "marka": "#8FAEFF", "sinir": "#39465C",
        "secili": "#26334D", "uyari": "#D9A441", "hata": "#E07070", "basari": "#6FCF97",
    },
}

MODES = ("sistem", "acik", "koyu")


def app_icon():
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#1D3FAA"))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 14, 14)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(QRectF(19, 12, 28, 40), 4, 4)
    painter.setPen(QPen(QColor("#1D3FAA"), 3))
    for y, end in ((25, 40), (33, 40), (41, 35)):
        painter.drawLine(25, y, end, y)
    painter.end()
    return QIcon(pixmap)


def resolve(mode: str, system_dark: bool = False) -> str:
    if mode == "koyu" or (mode == "sistem" and system_dark):
        return "koyu"
    return "acik"


def stylesheet(pal: dict) -> str:
    return f"""
QWidget {{ color: {pal['metin']}; font-family: 'Segoe UI'; font-size: 15px; }}
QMainWindow, QDialog, QWizard, QWidget#kok {{ background: {pal['zemin']}; }}
QStackedWidget, QWidget#preview {{ background: {pal['panel']}; border-radius: 16px; }}
QListWidget, QListView, QTreeView, QTableWidget, QTextBrowser, QLineEdit, QComboBox,
QSpinBox, QPlainTextEdit {{ background: {pal['panel']}; color: {pal['metin']};
 border: 1px solid {pal['sinir']}; border-radius: 10px; padding: 9px;
 selection-background-color: {pal['secili']}; selection-color: {pal['metin']}; }}
QLineEdit#search {{ min-height: 32px; padding: 10px 16px; font-size: 15px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {pal['marka']}; }}
QPushButton {{ background: {pal['panel']}; color: {pal['metin']};
 border: 1px solid {pal['sinir']}; border-radius: 9px; padding: 10px 18px; font-weight: 600; }}
QPushButton:hover {{ background: {pal['secili']}; border-color: {pal['marka']}; }}
QPushButton:pressed {{ background: {pal['sinir']}; }}
QPushButton:focus {{ border: 2px solid {pal['marka']}; }}
QPushButton:default, QPushButton[birincil="true"] {{ background: {pal['marka']};
 color: {pal['buton_metin']}; border: none; }}
QPushButton:disabled {{ color: {pal['ikincil']}; background: {pal['zemin']}; }}
QListView::item {{ padding: 12px; border-radius: 8px; }}
QListView::item:hover {{ background: {pal['zemin']}; }}
QListView::item:selected {{ background: {pal['secili']}; color: {pal['metin']}; }}
QListWidget#navigation {{ background: transparent; border: none; padding: 0; }}
QListWidget#navigation::item {{ padding: 15px 14px; margin-bottom: 5px; }}
QListWidget#navigation::item:selected {{ font-weight: 600; color: {pal['marka']}; }}
QLabel[ikincil="true"] {{ color: {pal['ikincil']}; }}
QLabel[baslik="true"] {{ font-size: 24px; font-weight: 700; }}
QLabel[uyari="true"] {{ color: {pal['uyari']}; }}
QLabel[hata="true"] {{ color: {pal['hata']}; }}
QLabel[basari="true"] {{ color: {pal['basari']}; }}
QCheckBox {{ spacing: 10px; padding: 5px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QProgressBar {{ border: none; background: {pal['sinir']}; border-radius: 5px; min-height: 8px; }}
QProgressBar::chunk {{ background: {pal['marka']}; border-radius: 5px; }}
QStatusBar {{ background: {pal['zemin']}; color: {pal['ikincil']}; border: none; }}
QMenuBar, QMenu {{ background: {pal['panel']}; color: {pal['metin']}; }}
QMenu::item:selected {{ background: {pal['secili']}; }}
QSplitter::handle {{ background: {pal['zemin']}; width: 12px; }}
QHeaderView::section {{ background: {pal['secili']}; padding: 10px; border: none; }}
QToolTip {{ background: {pal['panel']}; color: {pal['metin']}; border: 1px solid {pal['sinir']}; }}
"""

def apply(app, mode: str) -> str:
    """Temayi uygula, cozulmus adi don (sistem->acik/koyu)."""
    from PySide6.QtGui import QStyleHints
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    dark = False
    try:
        hints: QStyleHints = app.styleHints()
        dark = hints.colorScheme() == hints.colorScheme().Dark
    except Exception:
        pass
    name = resolve(mode, dark)
    style = stylesheet(TOKENS[name])
    if app.styleSheet() != style:
        app.setStyleSheet(style)
    return name
