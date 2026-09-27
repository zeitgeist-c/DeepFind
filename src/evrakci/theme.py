"""Tasarim jetonlari: acik/koyu/sistem. Plan bolum 19 baslangic paleti."""
from __future__ import annotations

TOKENS = {
    "acik": {
        "zemin": "#F4F6FA", "panel": "#FFFFFF", "metin": "#17243B", "buton_metin": "#FFFFFF",
        "ikincil": "#65748B", "marka": "#137C70", "sinir": "#E1E7F0",
        "secili": "#E9F6F2", "uyari": "#986A19", "hata": "#BC4253", "basari": "#137C70",
    },
    "koyu": {
        "zemin": "#0D1523", "panel": "#172237", "metin": "#F1F5FC", "buton_metin": "#09251F",
        "ikincil": "#B1BED3", "marka": "#67D9BC", "sinir": "#455570",
        "secili": "#1C3B3B", "uyari": "#E5B969", "hata": "#F18D99", "basari": "#67D9BC",
    },
}

MODES = ("sistem", "acik", "koyu")


def install_turkish(app):
    from PySide6.QtCore import QLocale, QLibraryInfo, QTranslator
    QLocale.setDefault(QLocale(QLocale.Turkish, QLocale.Turkey))
    if app is not None and not hasattr(app, "_evrakci_translation"):
        translator = QTranslator(app)
        if translator.load("qtbase_tr", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)
        app._evrakci_translation = translator


def app_icon():
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#137C70"))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 14, 14)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(QRectF(19, 12, 28, 40), 4, 4)
    painter.setPen(QPen(QColor("#137C70"), 3))
    for y, end in ((25, 40), (33, 40), (41, 35)):
        painter.drawLine(25, y, end, y)
    painter.end()
    return QIcon(pixmap)


def symbol_icon(kind, color="#91A3BF"):
    """Uygulamanın küçük, tutarlı çizgi simgeleri; harici font gerekmez."""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2, 2)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if kind == "search":
        p.drawEllipse(QRectF(4, 3, 13, 13)); p.drawLine(16, 15, 21, 20)
    elif kind == "folder":
        p.drawRoundedRect(QRectF(3, 7, 18, 13), 2, 2); p.drawLine(3, 7, 3, 4)
        p.drawLine(3, 4, 10, 4); p.drawLine(10, 4, 13, 7)
    elif kind == "lock":
        p.drawRoundedRect(QRectF(5, 10, 14, 11), 2, 2)
        p.drawArc(QRectF(8, 2, 8, 14), 0, 180 * 16); p.drawLine(12, 14, 12, 17)
    elif kind == "history":
        p.drawArc(QRectF(3, 3, 18, 18), 30 * 16, 300 * 16)
        p.drawLine(12, 6, 12, 12); p.drawLine(12, 12, 16, 14)
    elif kind == "scan":
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
        p.drawLine(2, 12, 22, 12); p.drawLine(8, 8, 16, 8)
    elif kind == "settings":
        for y, knob in ((5, 9), (12, 16), (19, 7)):
            p.drawLine(3, y, 21, y)
            p.setBrush(QColor(color)); p.drawEllipse(QRectF(knob - 2, y - 2, 4, 4)); p.setBrush(Qt.NoBrush)
    elif kind == "backup":
        p.drawRoundedRect(QRectF(3, 12, 18, 9), 2, 2)
        p.drawLine(12, 3, 12, 15); p.drawLine(8, 7, 12, 3); p.drawLine(12, 3, 16, 7)
    elif kind == "info":
        p.drawEllipse(QRectF(3, 3, 18, 18))
        p.drawPoint(12, 7); p.drawLine(12, 11, 12, 17)
    elif kind == "exit":
        p.drawLine(10, 3, 4, 3); p.drawLine(4, 3, 4, 21); p.drawLine(4, 21, 10, 21)
        p.drawLine(10, 12, 21, 12); p.drawLine(17, 8, 21, 12); p.drawLine(21, 12, 17, 16)
    else:
        p.drawRoundedRect(QRectF(6, 3, 13, 18), 2, 2)
        for y in (9, 13, 17): p.drawLine(9, y, 16, y)
    p.end()
    return QIcon(pixmap)


def resolve(mode: str, system_dark: bool = False) -> str:
    if mode == "koyu" or (mode == "sistem" and system_dark):
        return "koyu"
    return "acik"


def stylesheet(pal: dict) -> str:
    from pathlib import Path
    assets = (Path(__file__).parent / "assets").as_posix()
    check = "check-dark.svg" if pal is TOKENS["koyu"] else "check-light.svg"
    return f"""
QWidget {{ color: {pal['metin']}; font-family: 'Segoe UI'; font-size: 14px; }}
QMainWindow, QDialog, QWizard, QWidget#kok {{ background: {pal['zemin']}; }}
QFrame#card, QWidget#pageCard, QWidget#preview, QWizardPage#setupPage {{
 background: {pal['panel']}; border: 1px solid {pal['sinir']}; border-radius: 16px; }}
QStackedWidget {{ background: transparent; }}
QWidget#scanBody {{ background: {pal['panel']}; border: none; }}
QFrame#rail {{ background: #112039; border-radius: 16px; }}
QFrame#rail QLabel {{ color: #F3F7FF; background: transparent; }}
QFrame#rail QLabel[ikincil="true"] {{ color: #98A9C3; }}
QFrame#rail QLabel[eyebrow="true"] {{ color: #8195B5; }}
QLabel[eyebrow="true"] {{ color: {pal['ikincil']}; font-size: 11px; font-weight: 600; }}
QLabel[subheading="true"] {{ font-size: 17px; font-weight: 600; }}
QLabel[hero="true"] {{ font-size: 29px; font-weight: 700; }}
QLabel[baslik="true"][hero="true"] {{ font-size: 32px; }}
QLabel[pill="true"] {{ color: {pal['marka']}; background: {pal['secili']};
 padding: 6px 11px; border-radius: 12px; font-size: 12px; }}
QLabel#step {{ color: #91A5C3; padding: 9px 10px; border-radius: 10px; }}
QLabel#step[active="true"] {{ color: #FFFFFF; background: #243E57; font-weight: 600; }}
QLabel#step[done="true"] {{ color: #70D6BC; }}
QListWidget, QListView, QTreeView, QTableWidget, QTextBrowser, QLineEdit, QComboBox,
QSpinBox, QPlainTextEdit {{ background: {pal['panel']}; color: {pal['metin']};
 border: 1px solid {pal['sinir']}; border-radius: 9px; padding: 8px;
 selection-background-color: {pal['secili']}; selection-color: {pal['metin']}; }}
QLineEdit#search {{ min-height: 34px; padding: 10px 16px; font-size: 15px;
 background: {pal['panel']}; border-radius: 12px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {pal['marka']}; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 12px; height: 8px; }}
QSpinBox {{ padding-right: 28px; }}
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; border: none; width: 24px; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; border: none; width: 24px; }}
QSpinBox::up-arrow {{ image: url("{assets}/chevron-up.svg"); width: 10px; height: 6px; }}
QSpinBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 10px; height: 6px; }}
QPushButton {{ background: {pal['panel']}; color: {pal['metin']};
 border: 1px solid {pal['sinir']}; border-radius: 9px; padding: 10px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {pal['secili']}; border-color: {pal['marka']}; }}
QPushButton:pressed {{ background: {pal['sinir']}; }}
QPushButton:focus {{ border: 2px solid {pal['marka']}; }}
QPushButton:default, QPushButton[birincil="true"] {{ background: {pal['marka']};
 color: {pal['buton_metin']}; border: none; }}
QPushButton:disabled {{ color: {pal['ikincil']}; background: {pal['zemin']}; }}
QListView::item {{ padding: 12px; border-radius: 8px; }}
QListView::item:hover {{ background: {pal['zemin']}; }}
QListView::item:selected {{ background: {pal['secili']}; color: {pal['metin']}; }}
QListView#cardList {{ border: none; padding: 0; background: transparent; }}
QTreeView {{ background: {pal['zemin']}; alternate-background-color: {pal['panel']}; }}
QTreeView::item {{ min-height: 28px; }}
QTreeView::item:selected {{ background: {pal['secili']}; color: {pal['metin']}; border: 1px solid {pal['marka']}; }}
QComboBox QAbstractItemView {{ background: {pal['panel']}; color: {pal['metin']}; selection-background-color: {pal['secili']}; }}
QFrame#rail QPushButton {{ background: #1B304C; color: #D9E4F5; border-color: #344963; padding: 8px 5px; }}
QFrame#rail QPushButton:hover {{ background: #25435A; border-color: #70D6BC; }}
QListWidget#navigation {{ background: transparent; color: #A9B9D1; border: none; padding: 0; }}
QListWidget#navigation::item {{ padding: 13px 14px; margin: 3px 0; border-radius: 10px; }}
QListWidget#navigation::item:hover {{ background: #1B304C; }}
QListWidget#navigation::item:selected {{ background: #25435A; font-weight: 600; color: #FFFFFF; }}
QLabel[ikincil="true"] {{ color: {pal['ikincil']}; }}
QLabel[baslik="true"] {{ font-size: 23px; font-weight: 700; }}
QLabel[uyari="true"] {{ color: {pal['uyari']}; }}
QLabel[hata="true"] {{ color: {pal['hata']}; }}
QLabel[basari="true"] {{ color: {pal['basari']}; }}
QCheckBox {{ spacing: 10px; padding: 5px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QProgressBar {{ border: none; background: {pal['sinir']}; border-radius: 5px; min-height: 8px; }}
QProgressBar::chunk {{ background: {pal['marka']}; border-radius: 5px; }}
QStatusBar {{ background: {pal['zemin']}; color: {pal['ikincil']}; border: none; font-size: 12px; }}
QStatusBar::item {{ border: none; }}
QMenuBar, QMenu {{ background: {pal['panel']}; color: {pal['metin']}; }}
QMenu::item:selected {{ background: {pal['secili']}; }}
QSplitter::handle {{ background: {pal['zemin']}; width: 12px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea#paperCanvas {{ background: {pal['zemin']}; border-radius: 10px; }}
QScrollBar:vertical {{ background: transparent; width: 7px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {pal['sinir']}; border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QCheckBox::indicator {{ border: 1px solid {pal['sinir']}; border-radius: 4px; background: {pal['panel']}; }}
QCheckBox::indicator:checked {{ background: {pal['marka']}; border-color: {pal['marka']}; image: url("{assets}/{check}"); }}
QHeaderView::section {{ background: {pal['secili']}; padding: 10px; border: none; }}
QToolTip {{ background: {pal['panel']}; color: {pal['metin']}; border: 1px solid {pal['sinir']}; }}
"""

def apply(app, mode: str) -> str:
    """Temayi uygula, cozulmus adi don (sistem->acik/koyu)."""
    from PySide6.QtGui import QStyleHints
    install_turkish(app)
    from PySide6.QtCore import QSettings
    QSettings("Evrakci", "Appearance").setValue("theme", mode)
    app.setProperty("evrakci_theme_mode", mode)
    if not getattr(app, "_evrakci_scheme_connected", False):
        app.styleHints().colorSchemeChanged.connect(
            lambda _: apply(app, "sistem") if app.property("evrakci_theme_mode") == "sistem" else None)
        app._evrakci_scheme_connected = True
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    dark = False
    try:
        hints: QStyleHints = app.styleHints()
        dark = hints.colorScheme() == hints.colorScheme().Dark
    except Exception:
        pass
    name = resolve(mode, dark)
    app.setProperty("evrakci_theme", name)
    style = stylesheet(TOKENS[name])
    if app.styleSheet() != style:
        app.setStyleSheet(style)
    return name
