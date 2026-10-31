"""Sorgu sözdizimi çözümleyicisi testleri (docspell `PowerSearchInput` deseni)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import sorgu  # noqa: E402

TURLER = ["tümü", ".pdf", ".xlsx", ".docx"]


def test_serbest_metin_aynen_kalir():
    c = sorgu.cozumle("Ankara vergi 2024", TURLER)
    assert c.serbest == "Ankara vergi 2024"
    assert c.alanlar == {}
    assert not c.hata and c.imlec == -1


def test_alanlar_ayristirilir():
    c = sorgu.cozumle("Ankara yil:2024 tur:pdf etiket:vergi", TURLER)
    assert c.serbest == "Ankara"
    assert c.alanlar == {"yil": "2024", "tur": ".pdf", "etiket": "vergi"}
    assert not c.hata


def test_tirnakli_deger_bosluk_tasir():
    c = sorgu.cozumle('etiket:"vergi 2024" klasor:"C:/Belgeler"', TURLER)
    assert c.alanlar == {"etiket": "vergi 2024", "klasor": "C:/Belgeler"}
    assert not c.hata


def test_turkce_harf_katlamasi():
    assert sorgu.cozumle("yıl:2024", TURLER).alanlar == {"yil": "2024"}
    assert sorgu.cozumle("TÜR:pdf", TURLER).alanlar == {"tur": ".pdf"}


def test_tur_nokta_ile_ya_da_olmadan():
    assert sorgu.cozumle("tur:.pdf", TURLER).alanlar == {"tur": ".pdf"}
    assert sorgu.cozumle("tur:pdf", TURLER).alanlar == {"tur": ".pdf"}


def test_bilinmeyen_alan_konum_bildirir():
    metin = "Ankara turl:pdf"
    c = sorgu.cozumle(metin, TURLER)
    assert "bilinmeyen alan" in c.hata
    assert c.imlec == metin.index("turl")
    assert sorgu.imlec_satiri(metin, c.imlec) == " " * 7 + "^"
    assert c.serbest == "Ankara"  # the correctly resolved part is preserved


def test_gecersiz_yil_ve_tur_reddedilir():
    assert "'yil' 4 haneli" in sorgu.cozumle("yil:24", TURLER).hata
    assert "bilinmeyen tür" in sorgu.cozumle("tur:epub", TURLER).hata
    # Without a kind list only the format is fixed, no verification.
    assert sorgu.cozumle("tur:epub").alanlar == {"tur": ".epub"}


def test_kapanmayan_tirnak_ve_bos_deger():
    assert "kapanmayan tırnak" in sorgu.cozumle('etiket:"vergi', TURLER).hata
    assert "değer bekliyor" in sorgu.cozumle("etiket:", TURLER).hata
    assert "değer bekliyor" in sorgu.cozumle("etiket: tur:pdf", TURLER).hata


def test_bos_ve_yalniz_bosluk():
    for metin in ("", "   ", "\t"):
        c = sorgu.cozumle(metin, TURLER)
        assert c.serbest == "" and c.alanlar == {} and not c.hata
        assert sorgu.imlec_satiri(metin, -1) == ""


def test_imlec_satiri_sinirlari():
    assert sorgu.imlec_satiri("abc", 99) == "   ^"
    assert sorgu.imlec_satiri("abc", -5) == ""
