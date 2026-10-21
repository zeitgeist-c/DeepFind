"""Güncelleme akışı: sürüm karşılaştırma, yayın çözümleme, indirme güvenliği,
paket açma doğrulaması ve bekçi betiği — ağ yok, Qt yok."""
import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import update  # noqa: E402


GERCEK_YAYIN = {
    "tag_name": "v0.7.0",
    "html_url": "https://github.com/x/y/releases/tag/v0.7.0",
    "assets": [
        {"name": "Evrakci-0.7.0.zip", "size": 169624127,
         "digest": "sha256:" + "a" * 64,
         "browser_download_url": "https://x/zip"},
    ],
}


def _zip_uret(kok: Path, surum: str, *, program="Evrakçı", eksik_internal=False,
              icerik="paket") -> Path:
    """Gerçek kurulum ZIP'i gibi kök klasörlü bir arşiv üret."""
    zip_yolu = kok / f"Evrakci-{surum}.zip"
    with zipfile.ZipFile(zip_yolu, "w") as z:
        z.writestr(f"Evrakçı-{surum}/manifest.json",
                   json.dumps({"program": program, "version": surum}))
        z.writestr(f"Evrakçı-{surum}/Evrakçı-{surum}.exe", b"MZ" + icerik.encode())
        z.writestr(f"Evrakçı-{surum}/Evrakçı-{surum}.bat", b"@echo off")
        if not eksik_internal:
            z.writestr(f"Evrakçı-{surum}/_internal/base.dll", b"dll")
    return zip_yolu


class SurumTestleri(unittest.TestCase):
    def test_cozumleme_ve_karsilastirma(self):
        self.assertEqual(update.parse_version("v0.7.10"), (0, 7, 10))
        self.assertTrue(update.is_newer("v0.7.0", "0.6.4"))
        self.assertTrue(update.is_newer("0.10.0", "0.7.99"))
        self.assertFalse(update.is_newer("v0.6.4", "0.6.4"))
        self.assertFalse(update.is_newer("v0.6.4", "0.7.0"))

    def test_cozulemeyen_surum_hata(self):
        with self.assertRaises(update.UpdateError):
            update.parse_version("latest")


class YayinCozumleme(unittest.TestCase):
    def test_ascii_varlik_adiyla_bulunur(self):
        # GitHub varlık adlarını latinleştirir (Evrakçı -> Evrakci).
        info = update.parse_release(GERCEK_YAYIN)
        self.assertEqual(info.version, "0.7.0")
        self.assertEqual(info.asset_name, "Evrakci-0.7.0.zip")
        self.assertEqual(info.sha256, "a" * 64)
        self.assertEqual(info.size, 169624127)

    def test_unicode_varlik_adiyla_bulunur(self):
        payload = dict(GERCEK_YAYIN, assets=[dict(GERCEK_YAYIN["assets"][0],
                                                  name="Evrakçı-0.7.0.zip")])
        self.assertEqual(update.parse_release(payload).asset_name, "Evrakçı-0.7.0.zip")

    def test_eksik_paket_hata(self):
        payload = dict(GERCEK_YAYIN, assets=[{"name": "baska.zip", "size": 1,
                                              "digest": "", "browser_download_url": "x"}])
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload)

    def test_cozulemeyen_etiket_hata(self):
        with self.assertRaises(update.UpdateError):
            update.parse_release(dict(GERCEK_YAYIN, tag_name="latest"))

    def test_ozetsiz_yayin_reddedilir(self):
        payload = dict(GERCEK_YAYIN, assets=[dict(GERCEK_YAYIN["assets"][0],
                                                  digest=None)])
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload)


class IndirmeTestleri(unittest.TestCase):
    def _sunucu(self, tmp, icerik: bytes, bildirilen: int):
        veri = Path(tmp) / "paket.bin"
        veri.write_bytes(icerik)
        return update.UpdateInfo(
            version="9.9.9", asset_name="Evrakci-9.9.9.zip",
            download_url=veri.as_uri(), sha256=update._sha256_of(veri),
            size=bildirilen, page_url="")

    def test_ozet_dogrulanir(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._sunucu(tmp, b"kurulum-icerigi", 15)
            dest = Path(tmp) / "yeni" / "Evrakci-9.9.9.zip"
            update.download(info, dest)
            self.assertEqual(dest.read_bytes(), b"kurulum-icerigi")

    def test_bozuk_ozet_dosyayi_siler(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._sunucu(tmp, b"kurulum-icerigi", 15)
            info.sha256 = "0" * 64
            dest = Path(tmp) / "bozuk.zip"
            with self.assertRaises(update.UpdateError):
                update.download(info, dest)
            self.assertFalse(dest.exists())

    def test_eksik_boyut_dosyayi_siler(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._sunucu(tmp, b"kirpik", 9999)
            dest = Path(tmp) / "kirpik.zip"
            with self.assertRaises(update.UpdateError):
                update.download(info, dest)
            self.assertFalse(dest.exists())

    def test_iptal_durdurur_ve_siler(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._sunucu(tmp, b"x" * 4096, 4096)
            iptal = threading.Event()
            iptal.set()
            dest = Path(tmp) / "yarim.zip"
            with self.assertRaises(update.UpdateError):
                update.download(info, dest, cancel=iptal)
            self.assertFalse(dest.exists())


class AcmaTestleri(unittest.TestCase):
    def test_saglam_paket_acilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = _zip_uret(kok, "9.9.9")
            hedef = kok / "Updates"
            klasor = update.extract_zip(zip_yolu, hedef, "9.9.9")
            self.assertEqual(klasor, hedef / "Evrakçı-9.9.9")
            self.assertTrue((klasor / "Evrakçı-9.9.9.exe").is_file())
            self.assertTrue((klasor / "_internal").is_dir())

    def test_yanlis_surum_manifesti_reddedilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = _zip_uret(kok, "9.9.9", program="Baska")
            with self.assertRaises(update.UpdateError):
                update.extract_zip(zip_yolu, kok / "Updates", "9.9.9")

    def test_eksik_yapi_reddedilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = _zip_uret(kok, "9.9.9", eksik_internal=True)
            with self.assertRaises(update.UpdateError):
                update.extract_zip(zip_yolu, kok / "Updates", "9.9.9")

    def test_zip_slip_reddedilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = kok / "kotu.zip"
            with zipfile.ZipFile(zip_yolu, "w") as z:
                z.writestr("../kacak.txt", b"x")
            with self.assertRaises(update.UpdateError):
                update.extract_zip(zip_yolu, kok / "Updates", "9.9.9")

    def test_eski_kalinti_temizlenir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            hedef = kok / "Updates"
            eski = hedef / "Evrakçı-9.9.9"
            eski.mkdir(parents=True)
            (eski / "eski.txt").write_text("x", encoding="utf-8")
            zip_yolu = _zip_uret(kok, "9.9.9")
            klasor = update.extract_zip(zip_yolu, hedef, "9.9.9")
            self.assertFalse((klasor / "eski.txt").exists())

    def test_basarisiz_acma_kalinti_birakmaz(self):
        """Manifest bozuksa ne yarım klasör ne ZIP diskte kalır."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = _zip_uret(kok, "9.9.9", program="Baska")
            info = update.UpdateInfo(
                version="9.9.9", asset_name="Evrakci-9.9.9.zip",
                download_url=zip_yolu.as_uri(),
                sha256=update._sha256_of(zip_yolu),
                size=zip_yolu.stat().st_size, page_url="")
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(kok / "lad")}):
                hedef = update.updates_dir()
                with self.assertRaises(update.UpdateError):
                    update.prepare(info)
                kalanlar = [p.name for p in hedef.iterdir()]
            self.assertEqual(kalanlar, [])


class HazirlamaTestleri(unittest.TestCase):
    def test_hazirla_indirir_acar_dogrular(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            zip_yolu = _zip_uret(kok, "9.9.9")
            info = update.UpdateInfo(
                version="9.9.9", asset_name="Evrakci-9.9.9.zip",
                download_url=zip_yolu.as_uri(), sha256=update._sha256_of(zip_yolu),
                size=zip_yolu.stat().st_size, page_url="")
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(kok / "lad")}):
                klasor = update.prepare(info)
            self.assertTrue((klasor / "Evrakçı-9.9.9.exe").is_file())
            # ZIP yerleşme hazırlığından sonra da duruyor (bekçi betik siler).
            self.assertTrue((kok / "lad" / "Evrakci" / "Updates" /
                             "Evrakçı-9.9.9.zip").is_file())


class BekciBetikTestleri(unittest.TestCase):
    def test_betik_pid_bekler_yeni_exeyi_baslatir_ve_siler(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            hazir = kok / "Updates" / "Evrakçı-9.9.9"
            hazir.mkdir(parents=True)
            exe = hazir / "Evrakçı-9.9.9.exe"
            exe.write_bytes(b"MZ")
            (hazir / "Evrakçı-9.9.9.zip").write_bytes(b"z")  # temizlik hedefi
            calisan = kok / "kurulu" / "Evrakçı-9.9.8.exe"
            calisan.parent.mkdir()
            calisan.write_bytes(b"MZ")

            with mock.patch("evrakci.update.subprocess.Popen") as popen:
                betik = update.spawn_swap(4242, hazir, calisan,
                                          "C:\\kasa\\evrakci.db")
            govde = betik.read_text(encoding="utf-8")
            self.assertIn("PID=4242", govde)
            self.assertIn('" %PID% "', govde)                 # tasklist beklemesi
            self.assertIn("find.exe", govde)                  # System32 tam yolu
            self.assertIn(str(calisan.parent), govde)         # hedef üst dizin
            self.assertIn("--restarted", govde)
            self.assertIn("--kasa", govde)
            self.assertIn("Evrakçı-9.9.9.exe", govde)
            self.assertIn("del ", govde)                      # kendini siler
            self.assertEqual(popen.call_count, 1)

    def test_son_sonuc_okunur_ve_temizlenir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}):
                kok = update.updates_dir()
                damga = kok / "son-guncelleme.txt"
                damga.write_text("ok\r\n", encoding="utf-8")
                self.assertEqual(update.son_sonuc(), "ok")
                self.assertFalse(damga.exists())  # bir kez okunur
                self.assertEqual(update.son_sonuc(), "")

    def test_temizle_aktif_klasore_dokunmaz_eskileri_siler(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}):
                import time as _z
                kok = update.updates_dir()
                aktif = kok / "Evrakçı-9.9.9"
                aktif.mkdir()
                (aktif / "calisan.txt").write_text("x", encoding="utf-8")
                eski = kok / "Evrakçı-9.9.8"
                eski.mkdir()
                (eski / "eski.txt").write_text("x", encoding="utf-8")
                artik = kok / "artik.zip"
                artik.write_bytes(b"z")
                # Yarış koruması: taze öğeler varsayılan eşikte korunur.
                update.temizle(aktif_klasor=aktif)
                self.assertTrue(eski.exists())
                self.assertTrue(artik.exists())
                # Eskimiş öğeler silinir; aktif klasör yine korunur.
                gecmis = _z.time() - 24 * 3600
                for yol in (eski, artik):
                    os.utime(yol, (gecmis, gecmis))
                os.utime(aktif, (gecmis, gecmis))
                update.temizle(aktif_klasor=aktif)
                self.assertTrue(aktif.is_dir())
                self.assertFalse(eski.exists())
                self.assertFalse(artik.exists())


class DamgaTestleri(unittest.TestCase):
    def test_eksik_ve_eski_damga_denetim_ister(self):
        self.assertTrue(update.last_check_is_old(""))
        self.assertTrue(update.last_check_is_old("bozuk"))
        self.assertTrue(update.last_check_is_old("2020-01-01T00:00:00"))
        self.assertFalse(update.last_check_is_old(update.now_stamp()))


class AkisTestleri(unittest.TestCase):
    """Ana pencere kablolaması: Qt thread/ağ yok, sahte pencere üzerinde."""

    def _pencere(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from evrakci import app as app_module
        pencere = app_module.AnaPencere.__new__(app_module.AnaPencere)
        pencere._guncelleme_isci = None
        pencere._guncelleme_thread = None
        pencere._guncelleme_info = None
        pencere.con = mock.Mock()
        pencere.kasa_yolu = "C:\\sentetik\\kasa.db"
        pencere._locked = False
        from PySide6.QtWidgets import (QApplication, QPushButton, QLabel,
                                       QProgressBar)
        QApplication.instance() or QApplication([])
        pencere.update_denetle_btn = QPushButton()
        pencere.update_indir_btn = QPushButton()
        pencere.update_iptal_btn = QPushButton()
        pencere.update_bar = QProgressBar()
        pencere.update_durum = QLabel()
        pencere._toast_goster = mock.Mock()
        pencere.durum = mock.Mock()
        pencere.tepsi = None
        return app_module, pencere

    def test_kaynak_kopya_denetlemez(self):
        app_module, pencere = self._pencere()
        with mock.patch.object(app_module, "GuncellemeIsci") as isci:
            pencere._guncelleme_yapilabilir = lambda: False
            app_module.AnaPencere._guncelleme_denetle(pencere)
        isci.assert_not_called()
        self.assertIn("kurulu", pencere.update_durum.text())

    def test_denetim_sonucu_dugmelere_yansir(self):
        app_module, pencere = self._pencere()
        pencere._guncelleme_sessiz = False
        info = update.UpdateInfo("9.9.9", "Evrakci-9.9.9.zip", "u", "s",
                                 169624127, "p")
        app_module.AnaPencere._guncelleme_denetlendi(pencere, info)
        self.assertFalse(pencere.update_denetle_btn.isVisible())
        self.assertIn("9.9.9", pencere.update_durum.text())
        self.assertIn("MB", pencere.update_durum.text())

    def test_guncel_sonucu_mesaji(self):
        app_module, pencere = self._pencere()
        pencere._guncelleme_sessiz = False
        app_module.AnaPencere._guncelleme_denetlendi(pencere, None)
        self.assertIn("En güncel", pencere.update_durum.text())

    def test_sessiz_hata_gorunur_mesaj_vermez(self):
        app_module, pencere = self._pencere()
        pencere._guncelleme_sessiz = True
        app_module.AnaPencere._guncelleme_denetleme_hatasi(pencere, "ağ yok")
        self.assertNotIn("ağ yok", pencere.update_durum.text())
        pencere._guncelleme_sessiz = False
        app_module.AnaPencere._guncelleme_denetleme_hatasi(pencere, "ağ yok")
        self.assertIn("ağ yok", pencere.update_durum.text())

    def test_kurulamayan_swap_uygulamayi_kapatmaz(self):
        """Bekçi betik kurulamazsa hata görünür ve düğmeler geri gelir."""
        app_module, pencere = self._pencere()
        pencere._cikis = mock.Mock()
        with mock.patch.object(app_module.update_mod, "spawn_swap",
                               side_effect=OSError("izin yok")):
            app_module.AnaPencere._guncelleme_hazir(pencere, "9.9.9",
                                                    "C:\\hazir\\klasor")
        pencere._cikis.assert_not_called()
        self.assertIn("kurulamadı", pencere.update_durum.text())
        self.assertFalse(pencere.update_indir_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
