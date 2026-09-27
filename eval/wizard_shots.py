"""Kurulumun bütün adımları için yalnız sentetik verili görsel kontrol."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from PySide6.QtWidgets import QApplication
from evrakci import theme
from evrakci.wizard import Sihirbaz
from evrakci.version import __version__


def main():
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase, QFont
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/arial.ttf")
    app.setFont(QFont("Segoe UI", 10))
    output = Path(f"build/review-ui-{__version__}")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evrakci-wizard-") as temp:
        folder = Path(temp) / "Örnek belgeler"
        folder.mkdir()
        for mode in ("acik", "koyu"):
            theme.apply(app, mode)
            wizard = Sihirbaz()
            wizard.resize(1080, 700)
            wizard.show()
            for page in range(6):
                app.processEvents()
                app.processEvents()
                wizard.grab().save(str(output / f"kurulum-{page}-{mode}.png"))
                if page == 1:
                    wizard.s1.setText("yalniz-sentetik-1234")
                    wizard.s2.setText("yalniz-sentetik-1234")
                    wizard._ekle_yol(str(folder))
                wizard.next()
            wizard.close()
            wizard.deleteLater()
            from PySide6.QtCore import QCoreApplication, QEvent
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    print(str(output.resolve()))


if __name__ == "__main__":
    main()
