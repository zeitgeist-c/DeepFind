"""Sentetik kalite corpus ureteci (yapay veri; gercek arsiv yok). Deterministik."""
from __future__ import annotations

import os
import random
import shutil

SEHIR = ["Ankara", "İstanbul", "İzmir"]
KISI = ["Ayşe Yılmaz", "Mehmet Demir", "Fatma Kaya", "Mustafa Çelik", "Elif Şahin",
        "Hasan Öztürk", "Zeynep Arslan", "Ali Vural"]
TUR = ["vergi levhası", "fatura", "beyanname", "sözleşme", "rapor", "bordro"]
YIL = ["2021", "2022", "2023", "2024"]


def _pdf(path, lines):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    c = canvas.Canvas(path)
    c.setFont("TR", 13)
    for i, ln in enumerate(lines):
        if i and i % 8 == 0:
            c.showPage()
            c.setFont("TR", 13)
        c.drawString(72, 750 - (i % 8) * 30, ln)
    c.save()


def build(root: str, seed: int = 7) -> list:
    """Donus: [(dosya_adi, beklenen_sorgular...)] degil; sorgu listesi ayri uretilir."""
    rng = random.Random(seed)
    if os.path.exists(root):
        shutil.rmtree(root)
    idx = 0
    for si, sehir in enumerate(SEHIR):
        for yi, yil in enumerate(YIL):
            for ti, tur in enumerate(TUR):
                kisi = KISI[(si + yi + ti) % len(KISI)]
                d = os.path.join(root, sehir, yil)
                os.makedirs(d, exist_ok=True)
                ad = f"{kisi.split()[0]} {tur} {yil}"
                no = f"BV-{1000 + idx}"
                if idx % 3 == 0:
                    p = os.path.join(d, ad + ".pdf")
                    _pdf(p, [f"{sehir} {kisi} {yil} {tur}",
                             f"Belge no {no} duzenlendi",
                             "Sayfa iki detayi burada yer alir ek bilgi"])
                elif idx % 3 == 1:
                    import openpyxl
                    p = os.path.join(d, ad + ".xlsx")
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Belge"
                    ws["A1"] = sehir
                    ws["B2"] = kisi
                    ws["C3"] = f"{tur} {yil} {no}"
                    wb.save(p)
                    wb.close()
                else:
                    from docx import Document
                    p = os.path.join(d, ad + ".docx")
                    doc = Document()
                    doc.add_paragraph(f"{kisi} {sehir} {tur}")
                    doc.add_paragraph(f"{yil} yili {no} numarali rapor")
                    doc.save(p)
                idx += 1
    # capraz sayfa: terimler ayri sayfalarda
    d = os.path.join(root, "Ankara", "2024")
    _pdf(os.path.join(d, "Dağınık Belge 2024.pdf"),
         ["Ayşe Yılmaz burada", "lorem " * 20, "lorem " * 20, "lorem " * 20,
          "lorem " * 20, "lorem " * 20, "lorem " * 20, "lorem " * 20,
          "vergi levhası ektedir son"])
    # kopya cifti (byte-identical)
    import shutil as sh
    sh.copy(os.path.join(d, "Dağınık Belge 2024.pdf"), os.path.join(d, "Dağınık Kopya 2024.pdf"))
    # ilk 70KB ayni, sonu farkli (DUP-01)
    bas = "X" * 70000
    with open(os.path.join(root, "benzer1.pdf"), "wb") as f:
        f.write(b"%PDF " + bas.encode() + b" BITIS-A")
    with open(os.path.join(root, "benzer2.pdf"), "wb") as f:
        f.write(b"%PDF " + bas.encode() + b" BITIS-B")
    # bos + bozuk
    open(os.path.join(root, "bos.pdf"), "wb").close()
    with open(os.path.join(root, "bozuk.pdf"), "wb") as f:
        f.write(b"bozuk icerik \xff\xfe")
    return idx


def queries() -> list:
    """(sorgu, beklenen_dosya_adi | None, grup). Holdout ayracı kosucuda."""
    q = []
    q.append(("Ankara Ayşe 2024 vergi levhası", "Ayşe vergi levhası 2024.pdf", "tam"))
    q.append(("İstanbul Mehmet 2023 fatura", "Mehmet fatura 2023.xlsx", "kisi-sirket"))
    q.append(("Ayse vergi levhasi 2024", "Ayşe vergi levhası 2024.pdf", "diakritik"))
    q.append(("Istanbul fatura", "Mehmet fatura 2023.xlsx", "i-donusumu"))
    q.append(("vergile evha", "Ayşe vergi levhası 2024.pdf", "typo"))
    q.append(("beyaname 2022", None, "typo"))  # grup ici, beklenen asagida duzeltilir
    q.append(("Ankara Ayşe vergi", "Dağınık Belge 2024.pdf", "capraz-sayfa"))
    q.append(("BV-1005", None, "belge-no"))
    q.append(('"vergi levhası"', "Ayşe vergi levhası 2024.pdf", "tirnak"))
    q.append(("zebra helikopter kuantum", None, "no-result"))
    q.append(("1999", None, "no-result"))
    q.append(("", None, "bos"))
    # uretilmis kombinasyonlar
    rng = random.Random(11)
    combos = [("Ankara", "Ayşe", "2021"), ("İzmir", "Fatma", "2022"),
              ("İstanbul", "Elif", "2024"), ("Ankara", "Mustafa", "2023"),
              ("İzmir", "Hasan", "2021"), ("İstanbul", "Zeynep", "2022")]
    for sehir, ad, yil in combos:
        q.append((f"{sehir} {ad} {yil}", None, "uretim"))
    return q
