"""Lean English docs screenshots for DeepFind (offscreen). Writes docs/screenshots/00-06."""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402

from deepfind import coordinator, migrate, schema, theme, vault, identity  # noqa: E402
from deepfind.migrate import ensure_v7, ensure_v5  # noqa: E402
from deepfind.version import __version__  # noqa: E402

PW = "docs-shots-1234"


def pdf(path, text):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path)
    c.setFont("Helvetica", 13)
    c.drawString(72, 750, text)
    c.save()


def main():
    import tempfile
    base = tempfile.mkdtemp(prefix="deepfind-docs-")
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
    os.makedirs(out, exist_ok=True)
    arch = os.path.join(base, "archive")
    os.makedirs(arch, exist_ok=True)
    pdf(os.path.join(arch, "Ankara tax report 2024.pdf"), "Ankara Ayse Yilmaz 2024 tax report text")
    pdf(os.path.join(arch, "Istanbul invoice 2023.pdf"), "Istanbul Mehmet Demir 2023 invoice amount")
    time.sleep(4)  # stability window: files younger than 2 s stay pending
    db = os.path.join(base, "vault.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?, ?)",
                (arch, os.path.normpath(arch).lower()))
    con.commit()
    coordinator.run_scan(con, db, arch)
    con.close()

    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase, QFont
    for _f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            QFontDatabase.addApplicationFont(_f)
        except Exception:
            pass
    app.setFont(QFont("Segoe UI", 10))
    settings = QSettings(identity.APP_IDENTITY, "Appearance")
    prev_lang = settings.value("language", None)
    settings.setValue("language", "en")

    if os.environ.get("DOCS_NO_WIZARD") != "1":
        from deepfind.wizard import Sihirbaz
        wiz = Sihirbaz()
        wiz.resize(1000, 620)
        wiz.show()
        app.processEvents()
        wiz.grab().save(os.path.join(out, "00-ilk-kurulum.png"))
        print("saved 00", flush=True)
        wiz.close()
        app.processEvents()

    from deepfind.app import AnaPencere
    win = AnaPencere(db, PW)
    win.resize(1366, 768)
    theme.apply(app, "acik")
    win.show()
    app.processEvents()

    shots = [("01-ara", 0), ("02-kaynaklar", 1), ("03-tarama", 2),
             ("04-gecmis", 3), ("05-taranmis-evraklar", 4), ("06-ayarlar", 5)]
    win.nav.setCurrentRow(0)
    win.arama_kutu.setText("Ankara tax")
    win._ara_simdi()
    deadline = time.monotonic() + 60
    while win._search_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    if win.sonuc_model.rowCount():
        deadline = time.monotonic() + 90
        while win._thumb_loader is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        win.sonuc_liste.setCurrentIndex(win.sonuc_model.index(0, 0))
        win._secim_guncelle()
        while win._buyuk_loader is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        win._sec(win.sonuc_model.index(0, 0))
    while win.onizleme.busy():
        app.processEvents()
        time.sleep(0.01)
    deadline = time.monotonic() + 60
    while win.onizleme._ray_loader is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    for name, row in shots:
        win.nav.setCurrentRow(row)
        app.processEvents()
        time.sleep(0.3)
        win.grab().save(os.path.join(out, f"{name}.png"))
        print("saved", name, flush=True)
    win._thumblari_durdur()
    win._exiting = True
    win.close()
    if prev_lang is None:
        settings.remove("language")
    else:
        settings.setValue("language", prev_lang)
    print("done", __version__, flush=True)


if __name__ == "__main__":
    main()
