"""Tasarim jetonlari: acik/koyu/sistem. Plan bolum 19 baslangic paleti."""
from __future__ import annotations

TOKENS = {
    "acik": {
        "zemin": "#F5F7FB", "panel": "#FFFFFF", "metin": "#172033",
        "ikincil": "#526176", "marka": "#1D3FAA", "sinir": "#DCE3ED",
        "secili": "#E3EBFA", "uyari": "#8A5A00", "hata": "#A32222", "basari": "#1E6B34",
    },
    "koyu": {
        "zemin": "#111827", "panel": "#1B2434", "metin": "#F3F6FC",
        "ikincil": "#BAC5D6", "marka": "#8FAEFF", "sinir": "#39465C",
        "secili": "#26334D", "uyari": "#D9A441", "hata": "#E07070", "basari": "#6FCF97",
    },
}

MODES = ("sistem", "acik", "koyu")


def resolve(mode: str, system_dark: bool = False) -> str:
    if mode == "koyu" or (mode == "sistem" and system_dark):
        return "koyu"
    return "acik"


def stylesheet(pal: dict) -> str:
    return f"""
QMainWindow, QDialog, QWidget#kok {{ background: {pal['zemin']}; color: {pal['metin']}; }}
QListWidget, QListView, QTreeView, QTableWidget, QTextBrowser, QLineEdit, QComboBox,
QSpinBox, QPlainTextEdit {{
  background: {pal['panel']}; color: {pal['metin']};
  border: 1px solid {pal['sinir']}; border-radius: 8px; padding: 6px;
  selection-background-color: {pal['secili']};
}}
QPushButton {{
  background: {pal['panel']}; color: {pal['metin']};
  border: 1px solid {pal['sinir']}; border-radius: 8px; padding: 7px 14px;
}}
QPushButton:default, QPushButton[birincil="true"] {{
  background: {pal['marka']}; color: #FFFFFF; border: none; font-weight: 600;
}}
QPushButton:disabled {{ color: {pal['ikincil']}; }}
QLabel[ikincil="true"] {{ color: {pal['ikincil']}; }}
QLabel[baslik="true"] {{ font-size: 20px; font-weight: 600; }}
QLabel[uyari="true"] {{ color: {pal['uyari']}; }}
QLabel[hata="true"] {{ color: {pal['hata']}; }}
QLabel[basari="true"] {{ color: {pal['basari']}; }}
QStatusBar {{ background: {pal['panel']}; border-top: 1px solid {pal['sinir']}; }}
QMenuBar, QMenu {{ background: {pal['panel']}; color: {pal['metin']}; }}
QSplitter::handle {{ background: {pal['sinir']}; }}
QToolTip {{ background: {pal['panel']}; color: {pal['metin']};
  border: 1px solid {pal['sinir']}; }}
"""


def apply(app, mode: str) -> str:
    """Temayi uygula, cozulmus adi don (sistem->acik/koyu)."""
    from PySide6.QtGui import QStyleHints
    dark = False
    try:
        hints: QStyleHints = app.styleHints()
        dark = hints.colorScheme() == hints.colorScheme().Dark
    except Exception:
        pass
    name = resolve(mode, dark)
    app.setStyleSheet(stylesheet(TOKENS[name]))
    return name
