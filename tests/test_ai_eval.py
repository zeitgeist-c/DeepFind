"""AI arama degerlendirme seti: soru -> beklenen belge. Ag cagrisi yok.
Yeni retrieval degisikligi bu sette olculur; gerileme yasaktir."""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import ai, index, migrate, schema
from evrakci.extract import ExtractResult, Segment
from evrakci.scan import Entry
from evrakci.vocab import ensure_v5


@pytest.fixture()
def arsiv():
    con = sqlite3.connect(":memory:")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v7(con)

    def ekle(path, *sayfalar, baglam=""):
        entry = Entry(path, os.path.basename(path),
                      os.path.splitext(path)[1].lower(), 100, 1)
        segs = [Segment("pdf_page", i + 1, f"Sayfa {i + 1}", metin)
                for i, metin in enumerate(sayfalar)]
        index.index_entry(con, entry, ExtractResult(segs), baglam)

    ekle("C:/arsiv/2023-kira-faturasi.pdf",
         "ABC Ltd kira faturası. Toplam tutar 45.000 TL. Ödeme dekontu ektedir.")
    ekle("C:/arsiv/2024-kira-faturasi.pdf",
         "ABC Ltd kira faturası. Toplam tutar 52.000 TL.")
    ekle("C:/arsiv/tahsilat-54321.pdf",
         "54321 numaralı tahsilat makbuzu ile 18.750 TL tahsil edildi.")
    ekle("C:/arsiv/denetim-ankara.pdf",
         "Ankara bölge denetim planı hazırlandı.",
         "Denetim ekibi saha çalışmasını tamamladı.",
         "Denetim sonucunda gider 8 milyon TL, gelir 12 milyon TL olarak kesinleşti.")
    ekle("C:/arsiv/kira-sozlesmesi-2022.pdf",
         "2022 kira sözleşmesi. Aylık kira 20.000 TL, depozito 30.000 TL.")
    ekle("C:/arsiv/elektrik-faturasi-2023.pdf",
         "2023 elektrik faturası 1.250 TL.")
    ekle("C:/arsiv/personel-maas-2024.xlsx",
         "2024 personel maaş bordrosu toplam 900.000 TL.")
    ekle("C:/arsiv/toplanti-notu.pdf",
         "Haftalık toplantı notları. Gündem: temizlik planı.")
    ekle("C:/arsiv/2023/fatura-abc.pdf",
         "ABC Ltd faturası. Toplam tutar 10.000 TL.", baglam="2023")
    ekle("C:/arsiv/2024/fatura-abc.pdf",
         "ABC Ltd faturası. Toplam tutar 11.000 TL.", baglam="2024")
    yield con
    con.close()


SORULAR = [
    # (soru, beklenen yol parcasi)
    ("2023 kira faturası tutarı ne?", "2023-kira-faturasi.pdf"),
    ("2024 kira faturası tutarı ne?", "2024-kira-faturasi.pdf"),
    ("54321 numaralı tahsilat makbuzu tutarı?", "tahsilat-54321.pdf"),
    ("Ankara denetim gideri ne kadar?", "denetim-ankara.pdf"),
    ("Depozito ne kadar?", "kira-sozlesmesi-2022.pdf"),
    ("2023 elektrik faturası tutarı?", "elektrik-faturasi-2023.pdf"),
    ("Personel maaş bordrosu toplamı?", "personel-maas-2024.xlsx"),
]


@pytest.mark.parametrize("soru,beklenen", SORULAR)
def test_eval_sorusu_beklenen_belgeyi_bulur(arsiv, soru, beklenen):
    preview = ai.prepare_question(arsiv, soru)
    yollar = [s["path"] for s in preview.sources]
    assert any(beklenen in y for y in yollar), f"{soru!r} -> {yollar}"


def test_eval_abc_faturalari_iki_belgeyi_bulur(arsiv):
    preview = ai.prepare_question(arsiv, "ABC Ltd faturaları")
    yollar = [s["path"] for s in preview.sources]
    assert any("2023-kira-faturasi.pdf" in y for y in yollar)
    assert any("2024-kira-faturasi.pdf" in y for y in yollar)


def test_eval_gider_cumlesi_tam_alintida(arsiv):
    preview = ai.prepare_question(arsiv, "Ankara denetim gideri ne kadar?")
    metinler = [s["text"] for s in preview.sources]
    assert any("gider 8 milyon TL" in t for t in metinler)


def test_eval_yil_filtresi_yanlis_yili_eler(arsiv):
    preview = ai.prepare_question(arsiv, "2024 ABC faturası tutarı ne?")
    yollar = [s["path"] for s in preview.sources]
    assert any("2024/fatura-abc.pdf" in y for y in yollar)
    assert not any("2023/fatura-abc.pdf" in y for y in yollar)
    preview23 = ai.prepare_question(arsiv, "2023 ABC faturası tutarı ne?")
    yollar23 = [s["path"] for s in preview23.sources]
    assert any("2023/fatura-abc.pdf" in y for y in yollar23)
    assert not any("2024/fatura-abc.pdf" in y for y in yollar23)
