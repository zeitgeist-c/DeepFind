"""Guncel kabul gorselleri: sihirbaz + arama + ayarlar (acik/koyu). Offscreen, sentetik veri."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from deepfind import theme, vault, migrate, schema, coordinator
from deepfind.version import __version__

SHOT_LANG = os.environ.get("KABUL_LANG", "tr")
SADECE = os.environ.get("KABUL_SADECE", "")
SONEK = f"-{SHOT_LANG}" if SHOT_LANG != "tr" else ""

def pdf(kok, ad, metin):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 13)
    c.drawString(72, 750, metin)
    c.save()

def main():
    base = tempfile.mkdtemp(prefix="deepfind-kabul-")
    out = ROOT / "build" / f"review-ui-{__version__}-kabul"
    out.mkdir(parents=True, exist_ok=True)
    kok = os.path.join(base, "arsiv")
    os.makedirs(kok, exist_ok=True)
    pdf(kok, "Ankara vergi levhasi 2024.pdf", "Ankara Ayse Yilmaz 2024 vergi levhasi metni")
    pdf(kok, "Istanbul fatura 2023.pdf", "Istanbul Mehmet Demir 2023 fatura bedeli")
    db = os.path.join(base, "kasa.db")
    con = vault.open_vault(db)
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    con.execute("INSERT OR IGNORE INTO roots(display_path, canonical_path) VALUES (?, ?)",
                (kok, os.path.normpath(kok).lower()))
    con.commit()
    coordinator.run_scan(con, db, kok)
    con.close()
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase, QFont
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try: QFontDatabase.addApplicationFont(f)
        except Exception: pass
    app.setFont(QFont("Segoe UI", 10))
    # Sihirbaz sayfalari
    from deepfind.wizard import Sihirbaz
    for mode in ("acik", "koyu"):
        if SADECE and SADECE != "sihirbaz":
            break
        theme.set_language(SHOT_LANG)
        theme.apply(app, mode)
        wiz = Sihirbaz()
        wiz.resize(1080, 700)
        wiz.show()
        for page in range(len(wiz.pageIds())):
            app.processEvents(); app.processEvents()
            wiz.grab().save(str(out / f"sihirbaz-{page}-{mode}{SONEK}.png"))
            if page == 1:
                try: wiz._ekle_yol(kok)
                except Exception: pass
            wiz.next()
        wiz.close(); wiz.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    # Ana pencere: arama + ayarlar, acik/koyu
    theme.set_language(SHOT_LANG)
    con = vault.open_vault(db)
    migrate.ensure_current(con)
    from deepfind.app import AnaPencere
    pen = AnaPencere(db, None, prepared=True)
    pen.resize(1366, 768)
    pen.show()
    pen.arama_kutu.setText("Ankara vergi")
    pen._ara_simdi()
    from PySide6.QtWidgets import QApplication as QA
    import time as _t
    deadline = _t.monotonic() + 60
    while getattr(pen, "_search_thread", None) is not None and _t.monotonic() < deadline:
        app.processEvents(); _t.sleep(0.02)
    if pen.sonuc_model.rowCount():
        pen.sonuc_liste.setCurrentIndex(pen.sonuc_model.index(0, 0))
        try: pen._secim_guncelle()
        except Exception: pass
    app.processEvents()
    for mode in ("acik", "koyu"):
        theme.apply(app, mode)
        if not SADECE or SADECE == "arama":
            pen.nav.setCurrentRow(0)
            app.processEvents()
            pen.grab().save(str(out / f"ana-arama-{mode}{SONEK}.png"))
        if not SADECE or SADECE == "tarama":
            pen.nav.setCurrentRow(2)
            app.processEvents()
            pen.grab().save(str(out / f"ana-tarama-{mode}{SONEK}.png"))
        if not SADECE or SADECE == "ayarlar":
            pen.nav.setCurrentRow(5)
            app.processEvents()
            pen.grab().save(str(out / f"ana-ayarlar-{mode}{SONEK}.png"))
    # Kucuk pencere kaniti
    if not SADECE:
        pen.resize(900, 600)
        pen.nav.setCurrentRow(0)
        app.processEvents()
        pen.grab().save(str(out / "ana-arama-kucuk.png"))
        pen.nav.setCurrentRow(2)
        app.processEvents()
        pen.grab().save(str(out / "ana-tarama-kucuk.png"))
    print(str(out.resolve()))
    for p in sorted(out.glob("*.png")):
        print("GOREL:", p.name)

if __name__ == "__main__":
    main()
