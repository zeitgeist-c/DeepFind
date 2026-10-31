"""Design tokens and the app stylesheet (0.5 UI language).

Single surface + hairline divider: no card inside a card. The rail follows the theme
(soft gray on light, neutral dark on dark). No hardcoded colors in code;
wherever a color is needed, call `pal()`."""
from __future__ import annotations

TOKENS = {
    "acik": {
        "zemin": "#F1F3F7", "panel": "#FFFFFF", "yuzey2": "#F6F8FB",
        "metin": "#101828", "ikincil": "#667085", "buton_metin": "#FFFFFF",
        "marka": "#0E7C6B", "marka_tint": "#E7F4F1", "sinir": "#E4E7EC",
        "secili": "#EFF6F4", "uyari": "#B54708", "hata": "#B42318", "basari": "#0E7C6B",
        "ray": "#F6F8FB", "ray_aktif": "#E8EEF3", "ray_metin": "#101828", "ray_ikincil": "#667085",
    },
    "koyu": {
        "zemin": "#0E1116", "panel": "#161B22", "yuzey2": "#1B212A",
        "metin": "#E6EDF3", "ikincil": "#9BA6B4", "buton_metin": "#062B24",
        "marka": "#4FD1B5", "marka_tint": "#15332D", "sinir": "#333B47",
        "secili": "#1E312E", "uyari": "#F0B45C", "hata": "#FF8A8A", "basari": "#4FD1B5",
        "ray": "#12171D", "ray_aktif": "#232A34", "ray_metin": "#E6EDF3", "ray_ikincil": "#9BA6B4",
    },
}

MODES = ("sistem", "acik", "koyu")


# Code, tag under its own name, Qt translation file, QLocale counterpart.
# English first and default; flags are never used as language identity.
LANGUAGES = [
    ("en", "English", None, ("English", "UnitedStates")),
    ("tr", "Türkçe", "qtbase_tr", ("Turkish", "Turkey")),
    ("de", "Deutsch", "qtbase_de", ("German", "Germany")),
    ("es", "Español", "qtbase_es", ("Spanish", "Spain")),
    ("fr", "Français", "qtbase_fr", ("French", "France")),
    ("it", "Italiano", "qtbase_it", ("Italian", "Italy")),
    ("pt-BR", "Português (Brasil)", "qtbase_pt", ("Portuguese", "Brazil")),
    ("ru", "Русский", "qtbase_ru", ("Russian", "Russia")),
    ("pl", "Polski", "qtbase_pl", ("Polish", "Poland")),
    ("nl", "Nederlands", "qtbase_nl", ("Dutch", "Netherlands")),
    ("zh-CN", "简体中文", "qtbase_zh_CN", ("Chinese", "China")),
    ("ja", "日本語", "qtbase_ja", ("Japanese", "Japan")),
    ("ko", "한국어", "qtbase_ko", ("Korean", "SouthKorea")),
]

CODES = {code for code, _, _, _ in LANGUAGES}
DEFAULT_LANGUAGE = "en"


def resolve_language(code):
    """Known code -> itself; English when unregistered/broken."""
    return code if code in CODES else DEFAULT_LANGUAGE


def install_language(app, code):
    """Install the Qt standard translation + locale from the user choice."""
    from PySide6.QtCore import QLocale, QLibraryInfo, QTranslator
    code = resolve_language(code)
    entry = next(e for e in LANGUAGES if e[0] == code)
    _qt_file, (lang, country) = entry[2], entry[3]
    try:
        QLocale.setDefault(QLocale(getattr(QLocale, lang), getattr(QLocale, country)))
    except Exception:
        pass
    if app is not None:
        old = getattr(app, "_deepfind_translation", None)
        if old is not None:
            try:
                app.removeTranslator(old)
            except Exception:
                pass
        if _qt_file:
            translator = QTranslator(app)
            try:
                if translator.load(_qt_file, QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
                    app.installTranslator(translator)
                    app._deepfind_translation = translator
                    return
            except Exception:
                pass
        app._deepfind_translation = None


_LANG = DEFAULT_LANGUAGE
from .i18n_tables import (
    DE1 as _DE1, DE2 as _DE2, DE3 as _DE3, DE4 as _DE4, DE5 as _DE5,
    EN1 as _EN1, EN2 as _EN2, EN3 as _EN3, EN4 as _EN4, EN5 as _EN5,
    ES1 as _ES1, ES2 as _ES2, ES3 as _ES3, ES4 as _ES4, ES5 as _ES5,
    FR1 as _FR1, FR2 as _FR2, FR3 as _FR3, FR4 as _FR4, FR5 as _FR5,
    IT1 as _IT1, IT2 as _IT2, IT3 as _IT3, IT4 as _IT4, IT5 as _IT5,
    JA1 as _JA1, JA2 as _JA2, JA3 as _JA3, JA4 as _JA4, JA5 as _JA5,
    KO1 as _KO1, KO2 as _KO2, KO3 as _KO3, KO4 as _KO4, KO5 as _KO5,
    NL1 as _NL1, NL2 as _NL2, NL3 as _NL3, NL4 as _NL4, NL5 as _NL5,
    PB1 as _PB1, PB2 as _PB2, PB3 as _PB3, PB4 as _PB4, PB5 as _PB5,
    PL1 as _PL1, PL2 as _PL2, PL3 as _PL3, PL4 as _PL4, PL5 as _PL5,
    RU1 as _RU1, RU2 as _RU2, RU3 as _RU3, RU4 as _RU4, RU5 as _RU5,
    ZH1 as _ZH1, ZH2 as _ZH2, ZH3 as _ZH3, ZH4 as _ZH4, ZH5 as _ZH5,
)


def _merge(*parts):
    m = {}
    for p in parts:
        m.update(p or {})
    return m


TABLES = {"en": _merge(_EN1, _EN2, _EN3, _EN4, _EN5), "tr": {}, "de": _merge(_DE1, _DE2, _DE3, _DE4, _DE5), "es": _merge(_ES1, _ES2, _ES3, _ES4, _ES5), "fr": _merge(_FR1, _FR2, _FR3, _FR4, _FR5), "it": _merge(_IT1, _IT2, _IT3, _IT4, _IT5), "pt-BR": _merge(_PB1, _PB2, _PB3, _PB4, _PB5), "ru": _merge(_RU1, _RU2, _RU3, _RU4, _RU5), "pl": _merge(_PL1, _PL2, _PL3, _PL4, _PL5), "nl": _merge(_NL1, _NL2, _NL3, _NL4, _NL5), "zh-CN": _merge(_ZH1, _ZH2, _ZH3, _ZH4, _ZH5), "ja": _merge(_JA1, _JA2, _JA3, _JA4, _JA5), "ko": _merge(_KO1, _KO2, _KO3, _KO4, _KO5)}


def set_language(code):
    global _LANG
    _LANG = resolve_language(code)


def language():
    return _LANG


def t(text, **kwargs):
    out = text if text else ''
    if _LANG == 'en':
        en = TABLES.get('en')
        if en and text in en:
            out = en[text]
    else:
        table = TABLES.get(_LANG)
        if table and text in table:
            out = table[text]
    if kwargs:
        try:
            out = out.format(**kwargs)
        except Exception:
            pass
    return out


def install_turkish(app):
    """Backward compatibility: old calls fall back to the English default."""
    install_language(app, DEFAULT_LANGUAGE)


def app_icon():
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#0E7C6B"))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 14, 14)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(QRectF(19, 12, 28, 40), 4, 4)
    painter.setPen(QPen(QColor("#0E7C6B"), 3))
    for y, end in ((25, 40), (33, 40), (41, 35)):
        painter.drawLine(25, y, end, y)
    painter.end()
    return QIcon(pixmap)


def symbol_icon(kind, color=None):
    """The app's small, consistent line icons; no external font needed."""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    if color is None:
        color = pal()["ikincil"]
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2, 2)
    pen = QPen(QColor(color), 1.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if kind in ("left", "right"):
        x, other = (14, 9) if kind == "left" else (10, 15)
        p.drawLine(x, 6, other, 12); p.drawLine(other, 12, x, 18)
    elif kind == "search":
        p.drawEllipse(QRectF(4, 3, 13, 13)); p.drawLine(16, 15, 21, 20)
    elif kind == "ai":
        p.drawLine(12, 3, 12, 6); p.drawLine(12, 18, 12, 21)
        p.drawLine(5, 5, 7, 7); p.drawLine(17, 17, 19, 19)
        p.drawLine(3, 12, 6, 12); p.drawLine(18, 12, 21, 12)
        p.drawLine(5, 19, 7, 17); p.drawLine(17, 7, 19, 5)
        p.drawEllipse(QRectF(9, 9, 6, 6))
    elif kind == "grid":
        for x, y in ((4, 4), (13, 4), (4, 13), (13, 13)):
            p.drawRoundedRect(QRectF(x, y, 7, 7), 1.5, 1.5)
    elif kind == "rows":
        for y in (7, 12, 17):
            p.drawLine(4, y, 21, y)
    elif kind == "compact":
        for y, end in ((7, 21), (12, 18), (17, 21)):
            p.drawLine(4, y, end, y)
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
    elif kind == "check":
        p.drawLine(4, 12, 10, 18); p.drawLine(10, 18, 20, 6)
    else:
        p.drawRoundedRect(QRectF(6, 3, 13, 18), 2, 2)
        for y in (9, 13, 17): p.drawLine(9, y, 16, y)
    p.end()
    return QIcon(pixmap)


def resolve(mode: str, system_dark: bool = False) -> str:
    if mode == "koyu" or (mode == "sistem" and system_dark):
        return "koyu"
    return "acik"


def pal(**over) -> dict:
    """The active theme's tokens. Use this instead of hardcoded colors in code."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    name = "acik"
    if app is not None:
        name = app.property("deepfind_theme") or "acik"
    values = dict(TOKENS.get(name, TOKENS["acik"]))
    values.update(over)
    return values


def stylesheet(p: dict) -> str:
    from pathlib import Path
    assets = (Path(__file__).parent / "assets").as_posix()
    check = "check-dark.svg" if p.get("zemin") == TOKENS["koyu"]["zemin"] else "check-light.svg"
    return f"""
QWidget {{ color: {p['metin']}; font-family: 'Segoe UI'; font-size: 14px; }}
QMainWindow, QDialog, QWizard, QWidget#kok, QWidget#sayfa {{ background: {p['zemin']}; }}

/* -- yüzeyler: tek katman, kıl payı çerçeve -- */
QFrame#card, QWidget#pageCard, QWidget#preview, QWizardPage#setupPage, QFrame#panel {{
 background: {p['panel']}; border: 1px solid {p['sinir']}; border-radius: 12px; }}
QFrame#sideRail, QWidget#sideRail {{ background: {p['yuzey2']}; border: none;
 border-right: 1px solid {p['sinir']}; border-radius: 0px; }}
QFrame#rail {{ background: {p['ray']}; border: none;
 border-right: 1px solid {p['sinir']}; border-radius: 0px; }}
QFrame#rail QLabel {{ background: transparent; }}
QWidget#scanBody {{ background: {p['zemin']}; border: none; }}
QWidget#headBar {{ background: {p['panel']}; border-bottom: 1px solid {p['sinir']}; }}
QFrame#ayrac {{ background: {p['sinir']}; border: none; min-height: 1px; max-height: 1px; }}
QFrame#ayracD {{ background: {p['sinir']}; border: none; min-width: 1px; max-width: 1px; }}
QFrame#bolme {{ background: {p['sinir']}; border: none; min-height: 1px; max-height: 1px; }}
QWidget#statStrip {{ background: {p['panel']}; border: 1px solid {p['sinir']}; border-radius: 12px; }}
QStackedWidget {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollArea#paperCanvas {{ background: {p['zemin']}; border: 1px solid {p['sinir']}; border-radius: 10px; }}
QLabel#thumbBox {{ background: {p['yuzey2']}; border: 1px solid {p['sinir']}; border-radius: 10px; }}
QListWidget#pageRail {{ background: {p['yuzey2']}; border: 1px solid {p['sinir']};
 border-radius: 10px; padding: 6px; }}
QListWidget#pageRail::item {{ border-radius: 7px; padding: 3px; color: {p['ikincil']};
 text-align: center; }}
QListWidget#pageRail::item:hover {{ background: {p['secili']}; }}
QListWidget#pageRail::item:selected {{ background: {p['secili']}; color: {p['metin']};
 border: 1px solid {p['marka']}; }}

/* -- filter chips -- */
QFrame#cip {{ background: {p['marka_tint']}; border: 1px solid {p['sinir']};
 border-radius: 999px; }}
QLabel[cipMetin="true"] {{ color: {p['marka']}; font-size: 12px; font-weight: 600;
 background: transparent; }}
QPushButton#cipKaldir {{ background: transparent; border: none; color: {p['marka']};
 font-size: 13px; font-weight: 700; padding: 0px; }}
QPushButton#cipKaldir:hover {{ background: {p['sinir']}; border-radius: 8px; }}
QListView#gridList {{ border: none; padding: 0; background: transparent; }}
QWidget#ayarGovde {{ background: {p['zemin']}; }}

/* -- tipografi -- */
QLabel[eyebrow="true"] {{ color: {p['ikincil']}; font-size: 11px; font-weight: 700; }}
QLabel[subheading="true"] {{ font-size: 15px; font-weight: 600; }}
QLabel[hero="true"] {{ font-size: 28px; font-weight: 700; }}
QLabel[baslik="true"][hero="true"] {{ font-size: 30px; }}
QLabel[baslik="true"] {{ font-size: 19px; font-weight: 700; }}
QLabel[ikincil="true"] {{ color: {p['ikincil']}; }}
QLabel[uyari="true"] {{ color: {p['uyari']}; }}
QLabel[hata="true"] {{ color: {p['hata']}; }}
QLabel[basari="true"] {{ color: {p['basari']}; }}
QLabel#step {{ color: {p['ray_ikincil']}; padding: 9px 10px; border-radius: 8px; }}
QLabel#step[active="true"] {{ color: {p['metin']}; background: {p['ray_aktif']}; font-weight: 600; }}
QLabel#step[done="true"] {{ color: {p['marka']}; }}
QLabel#numb {{ background: {p['marka']}; color: {p['buton_metin']};
 border-radius: 9px; font-weight: 700; font-size: 12px; padding: 2px 7px; }}

/* -- rozetler -- */
QLabel[pill="true"] {{ color: {p['marka']}; background: {p['marka_tint']};
 padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
QLabel[sayac="true"] {{ color: {p['ikincil']}; background: {p['yuzey2']};
 border: 1px solid {p['sinir']}; padding: 2px 9px; border-radius: 999px; font-size: 12px; }}

/* -- girdiler -- */
QListWidget, QListView, QTreeView, QTableWidget, QTextBrowser, QLineEdit, QComboBox,
QSpinBox, QTimeEdit, QPlainTextEdit {{ background: {p['panel']}; color: {p['metin']};
 border: 1px solid {p['sinir']}; border-radius: 8px; padding: 7px 10px;
 selection-background-color: {p['secili']}; selection-color: {p['metin']}; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QSpinBox:focus, QPlainTextEdit:focus,
QTextBrowser:focus {{ border: 1px solid {p['marka']}; }}
QLineEdit#search {{ min-height: 34px; padding: 9px 14px; font-size: 15px; border-radius: 10px; }}
QComboBox {{ padding-right: 26px; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 11px; height: 7px; }}
QTimeEdit, QSpinBox {{ padding-right: 26px; }}
QTimeEdit::up-button, QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; border: none; width: 22px; }}
QTimeEdit::down-button, QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; border: none; width: 22px; }}
QTimeEdit::up-arrow, QSpinBox::up-arrow {{ image: url("{assets}/chevron-up.svg"); width: 10px; height: 6px; }}
QTimeEdit::down-arrow, QSpinBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 10px; height: 6px; }}
QComboBox QAbstractItemView {{ background: {p['panel']}; color: {p['metin']};
 border: 1px solid {p['sinir']}; padding: 4px; selection-background-color: {p['secili']}; }}

/* -- butonlar: üç çeşit -- */
QPushButton {{ background: {p['panel']}; color: {p['metin']};
 border: 1px solid {p['sinir']}; border-radius: 8px; padding: 7px 13px; font-weight: 600; }}
QPushButton:hover {{ background: {p['secili']}; border-color: {p['marka']}; }}
QPushButton:pressed {{ background: {p['sinir']}; }}
QPushButton:default, QPushButton[birincil="true"] {{ background: {p['marka']};
 color: {p['buton_metin']}; border: 1px solid transparent; }}
QPushButton:default:hover, QPushButton[birincil="true"]:hover {{ border-color: {p['metin']}; }}
QPushButton[ghost="true"] {{ background: transparent; border: none; color: {p['marka']}; font-weight: 600; }}
QPushButton[ghost="true"]:hover {{ background: {p['marka_tint']}; border: none; }}
QPushButton[tehlike="true"] {{ background: transparent; color: {p['hata']}; border: 1px solid {p['sinir']}; }}
QPushButton[tehlike="true"]:hover {{ border-color: {p['hata']}; background: transparent; }}
QPushButton[kucuk="true"] {{ padding: 4px 10px; font-size: 12px; border-radius: 7px; }}
QPushButton[dar="true"] {{ padding: 5px 8px; }}
QPushButton:disabled {{ color: {p['ikincil']}; background: {p['panel']}; border-color: {p['sinir']}; }}
QPushButton[birincil="true"]:disabled {{ background: {p['sinir']}; color: {p['ikincil']}; }}

/* -- listeler -- */
QListView::item {{ padding: 10px; border-radius: 8px; }}
QListView::item:hover {{ background: {p['yuzey2']}; }}
QListView::item:selected {{ background: {p['secili']}; color: {p['metin']}; }}
QListView#cardList {{ border: none; padding: 0; background: transparent; }}
QTreeView {{ background: {p['panel']}; alternate-background-color: {p['yuzey2']}; }}
QTreeView::item {{ min-height: 26px; }}
QTreeView::item:selected {{ background: {p['secili']}; color: {p['metin']}; }}
QHeaderView::section {{ background: {p['yuzey2']}; padding: 9px; border: none;
 border-bottom: 1px solid {p['sinir']}; }}

/* -- ray -- */
QListWidget#navigation {{ background: transparent; color: {p['ray_metin']};
 border: none; padding: 0; }}
QListWidget#navigation::item {{ padding: 8px 10px; margin: 1px 0; border-radius: 8px; }}
QListWidget#navigation::item:hover {{ background: {p['ray_aktif']}; }}
QListWidget#navigation::item:selected {{ background: {p['ray_aktif']}; font-weight: 600; color: {p['metin']}; }}
QFrame#rail QPushButton {{ background: transparent; color: {p['ray_metin']};
 border: 1px solid {p['sinir']}; padding: 7px 8px; text-align: left; }}
QFrame#rail QPushButton:hover {{ background: {p['ray_aktif']}; border-color: {p['marka']}; }}

/* -- diğer -- */
QCheckBox {{ spacing: 9px; padding: 4px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {p['sinir']};
 border-radius: 4px; background: {p['panel']}; }}
QCheckBox::indicator:checked {{ background: {p['marka']}; border-color: {p['marka']};
 image: url("{assets}/{check}"); }}
QProgressBar {{ border: none; background: {p['sinir']}; border-radius: 4px; min-height: 6px; max-height: 6px; }}
QProgressBar::chunk {{ background: {p['marka']}; border-radius: 4px; }}
QStatusBar {{ background: {p['yuzey2']}; color: {p['ikincil']};
 border-top: 1px solid {p['sinir']}; font-size: 12px; }}
QStatusBar::item {{ border: none; }}
QMenuBar, QMenu {{ background: {p['panel']}; color: {p['metin']}; }}
QMenu::item:selected {{ background: {p['secili']}; }}
QSplitter::handle {{ background: {p['sinir']}; width: 1px; height: 1px; }}
QSplitter::handle:hover {{ background: {p['marka']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['sinir']}; border-radius: 4px; min-height: 26px; }}
QScrollBar::handle:vertical:hover {{ background: {p['ikincil']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['sinir']}; border-radius: 4px; min-width: 26px; }}
QScrollBar::handle:horizontal:hover {{ background: {p['ikincil']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
QToolTip {{ background: {p['panel']}; color: {p['metin']}; border: 1px solid {p['sinir']}; }}
QPlainTextEdit#log {{ font-family: 'Cascadia Mono', 'Consolas'; font-size: 12px; }}
"""


def apply(app, mode: str) -> str:
    """Apply the theme, return the resolved name (system->light/dark)."""
    from PySide6.QtGui import QStyleHints
    from PySide6.QtCore import QSettings
    from . import identity
    install_language(app, resolve_language(
        QSettings(identity.APP_IDENTITY, "Appearance").value("language", DEFAULT_LANGUAGE)))
    QSettings(identity.APP_IDENTITY, "Appearance").setValue("theme", mode)
    app.setProperty("deepfind_theme_mode", mode)
    if not getattr(app, "_deepfind_scheme_connected", False):
        app.styleHints().colorSchemeChanged.connect(
            lambda _: apply(app, "sistem") if app.property("deepfind_theme_mode") == "sistem" else None)
        app._deepfind_scheme_connected = True
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    dark = False
    try:
        hints: QStyleHints = app.styleHints()
        dark = hints.colorScheme() == hints.colorScheme().Dark
    except Exception:
        pass
    name = resolve(mode, dark)
    app.setProperty("deepfind_theme", name)
    style = stylesheet(TOKENS[name])
    if app.styleSheet() != style:
        app.setStyleSheet(style)
    return name


def scan_icons(paused=False):
    """Pre-rendered tray frames; the document itself stays stationary."""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
    result = []
    for frame in range(1 if paused else 8):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(10, 10, app_icon().pixmap(44, 44))
        painter.setPen(QPen(QColor("#4FD1B5"), 5))
        if paused:
            painter.drawLine(24, 54, 24, 63)
            painter.drawLine(36, 54, 36, 63)
        else:
            painter.drawArc(QRectF(3, 3, 58, 58), frame * 45 * 16, 110 * 16)
        painter.end()
        result.append(QIcon(pixmap))
    return result
