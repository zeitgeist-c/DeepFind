"""A7 gorsel kanit: ana pencere acik/koyu tema ekran goruntusu (offscreen)."""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_TD = "C:/Users/user/AppData/Local/hermes/cache/scratch/evrakci-a1/tessdata"
if os.path.isdir(_TD):
    os.environ["EVRAKCI_TESSDATA"] = _TD

from PySide6.QtWidgets import QApplication  # noqa: E402

from evrakci import coordinator, migrate, schema, theme, vault  # noqa: E402
from evrakci.migrate import ensure_v7  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402
from evrakci.version import __version__

PW = "gorsel-sifre-1234"


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
    import tempfile
    base = tempfile.mkdtemp(prefix="evrakci-review-")
    output = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build", f"review-ui-{__version__}" + os.environ.get("EVRAKCI_REVIEW_SUFFIX", "")))
    os.makedirs(output, exist_ok=True)
    kok = os.path.join(base, "arsiv")
    os.makedirs(kok, exist_ok=True)
    pdf(kok, "Ankara vergi levhasi 2024.pdf", "Ankara Ayşe Yılmaz 2024 vergi levhası metni")
    pdf(kok, "Istanbul fatura 2023.pdf", "İstanbul Mehmet Demir 2023 fatura bedeli")
    time.sleep(2.5)
    db = os.path.join(base, "kasa.db")
    if os.path.exists(db):
        os.remove(db)
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?, ?)",
                (kok, os.path.normpath(kok).lower()))
    con.commit()
    coordinator.run_scan(con, db, kok)
    con.close()

    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase, QFont
    for _f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            QFontDatabase.addApplicationFont(_f)
        except Exception:
            pass
    app.setFont(QFont("Segoe UI", 10))
    from evrakci.app import AnaPencere
    pen = AnaPencere(db, PW)
    pen.resize(1366, 768)
    pen.show()
    pen.arama_kutu.setText("Ankara Ayşe vergi")
    pen._ara_simdi()
    while pen._search_thread is not None:
        app.processEvents()
        time.sleep(0.01)
    if pen.sonuc_model.rowCount():
        pen._sec(pen.sonuc_model.index(0, 0))
    while pen.onizleme.busy():
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    for mod in ("acik", "koyu"):
        theme.apply(app, mod)
        pen.nav.setCurrentRow(0)
        app.processEvents()
        pen.grab().save(os.path.join(output, f"ana-{mod}.png"))
        print(f"kaydedildi: ana-{mod}.png", flush=True)
        pen.nav.setCurrentRow(6)
        pen.ai_question.setText("Ankara vergi")
        pen._ai_prepare()
        app.processEvents()
        pen.grab().save(os.path.join(output, f"ai-{mod}.png"))
        print(f"kaydedildi: ai-{mod}.png", flush=True)
        from evrakci.auth import ParolaDialog
        login = ParolaDialog()
        login.show()
        app.processEvents()
        login.grab().save(os.path.join(output, f"kilit-{mod}.png"))
        login.close()
        change = ParolaDialog(change=True)
        change.show()
        app.processEvents()
        change.grab().save(os.path.join(output, f"sifre-degistir-{mod}.png"))
        change.close()
        for index, name in enumerate(("ara", "kaynaklar", "tarama", "gecmis", "yedekler", "ayarlar")):
            pen.nav.setCurrentRow(index)
            app.processEvents()
            pen.grab().save(os.path.join(output, f"{name}-{mod}.png"))
    pen._exiting = True
    pen.close()


if __name__ == "__main__":
    main()
