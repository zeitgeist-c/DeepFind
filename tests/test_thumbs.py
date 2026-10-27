"""Küçük resim hattı testleri: önbellek anahtarı, üretim, budama, yükleyici."""
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from deepfind import thumbs, workers  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _pdf(path, metin="Ankara vergi levhası 2024"):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    c = canvas.Canvas(path)
    c.setFont("TR", 13)
    c.drawString(72, 750, metin)
    c.save()
    return path


def test_anahtar_kaynak_degisince_degisir(tmp_path):
    dosya = tmp_path / "a.pdf"
    dosya.write_bytes(b"%PDF-1.4\n")
    temel = thumbs.anahtar(str(dosya), 10, 100)
    assert temel == thumbs.anahtar(str(dosya), 10, 100)
    assert temel != thumbs.anahtar(str(dosya), 11, 100)          # boyut değişti
    assert temel != thumbs.anahtar(str(dosya), 10, 101)          # mtime değişti
    assert temel != thumbs.anahtar(str(dosya), 10, 100, "l")     # tür değişti
    # Windows'ta yol büyük/küçük harf duyarsızdır: aynı anahtar üretilmeli.
    assert temel == thumbs.anahtar(str(dosya).upper(), 10, 100)


def test_hazir_olan_uretilmeden_none_uretilince_yol(tmp_path):
    dosya = tmp_path / "a.pdf"
    dosya.write_bytes(b"x")
    st = thumbs._damga(str(dosya))
    dizin = str(tmp_path / "onbellek")
    assert thumbs.hazir_olan(str(dosya), st[0], st[1], "s", dizin) is None
    os.makedirs(dizin, exist_ok=True)
    hedef = thumbs.hedef_yolu(str(dosya), st[0], st[1], "s", dizin)
    with open(hedef, "wb") as f:
        f.write(b"gorsel")
    assert thumbs.hazir_olan(str(dosya), st[0], st[1], "s", dizin) == hedef


def test_damga_olmayan_dosya(tmp_path):
    assert thumbs._damga(str(tmp_path / "yok.pdf")) is None


def test_thumb_islemi_pdf_uretir(tmp_path):
    kaynak = _pdf(str(tmp_path / "belge.pdf"))
    hedef = str(tmp_path / ("kucuk" + thumbs.bicim_uzantisi()))
    sonuc = workers.run_work("thumb", (kaynak, hedef, 300))
    assert os.path.exists(hedef) and os.path.getsize(hedef) > 0
    from PIL import Image
    with Image.open(hedef) as im:
        assert 0 < im.width and 0 < im.height
        assert max(im.size) <= 300
    assert sonuc["file"] == hedef


def test_thumb_islemi_eksik_dosyada_hata(tmp_path):
    hedef = str(tmp_path / ("yok" + thumbs.bicim_uzantisi()))
    with pytest.raises(RuntimeError) as hata:
        workers.run_work("thumb", (str(tmp_path / "yok.pdf"), hedef, 200))
    assert "FileNotFoundError" in str(hata.value)
    assert not os.path.exists(hedef)


def test_thumb_islemi_gorsel_girdi(tmp_path):
    from PIL import Image
    kaynak = tmp_path / "gorsel.png"
    Image.new("RGB", (2400, 3200), "white").save(kaynak)
    hedef = str(tmp_path / ("g" + thumbs.bicim_uzantisi()))
    workers.run_work("thumb", (str(kaynak), hedef, 200))
    with Image.open(hedef) as im:
        assert max(im.size) <= 200


def test_onbellek_buda_en_eskiyi_siler(tmp_path):
    dizin = str(tmp_path / "onbellek")
    os.makedirs(dizin)
    for i in range(6):
        yol = os.path.join(dizin, f"d{i}.webp")
        with open(yol, "wb") as f:
            f.write(b"x")
        os.utime(yol, (1000 + i, 1000 + i))
    assert thumbs.buda(dizin, sinir=3) == 3
    assert len(os.listdir(dizin)) == 3
    assert not os.path.exists(os.path.join(dizin, "d0.webp"))
    assert thumbs.buda(dizin, sinir=3) == 0


def test_onbellek_temizle(tmp_path):
    dizin = str(tmp_path / "onbellek")
    os.makedirs(dizin)
    for i in range(3):
        with open(os.path.join(dizin, f"a{i}.webp"), "wb") as f:
            f.write(b"x")
    assert thumbs.temizle(dizin) == 3
    assert os.listdir(dizin) == []
    assert thumbs.temizle(str(tmp_path / "olmayan")) == 0


def test_yukleyici_onbellekten_bildirir(tmp_path, monkeypatch):
    """Önbellekte varsa alt süreç kurmadan doğrudan bildirir."""
    uygulama = _app()
    dizin = str(tmp_path / "onbellek")
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: dizin)
    kaynak = _pdf(str(tmp_path / "b.pdf"))
    st = thumbs._damga(kaynak)
    os.makedirs(dizin, exist_ok=True)
    hedef = thumbs.hedef_yolu(kaynak, st[0], st[1], "s", dizin)
    workers.run_work("thumb", (kaynak, hedef, thumbs.KUCUK))
    kayitlar = []
    yukleyici = thumbs.OnbellekYukleyici([(kaynak, "s")])
    yukleyici.tamam.connect(lambda yol, tur, dosya: kayitlar.append((yol, tur, dosya)))
    yukleyici.start()
    yukleyici.wait(10000)
    uygulama.processEvents()
    assert kayitlar == [(kaynak, "s", hedef)]


def test_yukleyici_eksik_dosyada_bos_bildirir(tmp_path, monkeypatch):
    uygulama = _app()
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: str(tmp_path / "onbellek"))
    kayitlar = []
    yukleyici = thumbs.OnbellekYukleyici([(str(tmp_path / "yok.pdf"), "s")])
    yukleyici.tamam.connect(lambda yol, tur, dosya: kayitlar.append(dosya))
    yukleyici.start()
    yukleyici.wait(10000)
    uygulama.processEvents()
    assert kayitlar == [""]


def test_kucuk_resim_kaynak_dizine_dokunmaz(tmp_path, monkeypatch):
    """Kanıt: küçük resim üretimi ve budama kaynak dizini değiştirmez."""
    kaynak_dizin = tmp_path / "kaynaklar"
    kaynak_dizin.mkdir()
    belge = _pdf(str(kaynak_dizin / "evrak.pdf"))
    onceki = {p.name: (p.stat().st_size, p.stat().st_mtime_ns)
              for p in kaynak_dizin.iterdir()}
    dizin = str(tmp_path / "onbellek")
    os.makedirs(dizin, exist_ok=True)
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: dizin)
    st = thumbs._damga(belge)
    hedef = thumbs.hedef_yolu(belge, st[0], st[1], "s", dizin)
    workers.run_work("thumb", (belge, hedef, thumbs.KUCUK))
    # Önbellek dosyası kaynak dizinin dışında kaldı ve kaynak dokunulmadan durdu.
    assert os.path.exists(hedef)
    assert os.path.dirname(os.path.abspath(hedef)) == os.path.abspath(dizin)
    sonraki = {p.name: (p.stat().st_size, p.stat().st_mtime_ns)
               for p in kaynak_dizin.iterdir()}
    assert sonraki == onceki
    # Budama yalnız önbellek dizinindeki dosyaları siler.
    thumbs.buda(dizin, sinir=0)
    assert list(kaynak_dizin.iterdir()) and not os.listdir(dizin)
    assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns)
            for p in kaynak_dizin.iterdir()} == onceki
