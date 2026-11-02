"""Tema/dil ayrimi: tema uygulamak kullanicinin dil secimini sifirlamaz."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from deepfind import theme  # noqa: E402


def test_tema_uygulamak_dili_sifirlamaz():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    theme.set_language("de")
    try:
        theme.apply(app, "acik")
        assert theme.language() == "de"
        theme.apply(app, "koyu")
        assert theme.language() == "de"
    finally:
        theme.set_language("tr")


def test_kayitli_dil_yoksa_varsayilan_uygulanir():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    kod = theme.restore_saved_language(app)
    try:
        assert kod in {c for c, *_ in theme.LANGUAGES}
        assert theme.language() == kod
    finally:
        theme.set_language("tr")