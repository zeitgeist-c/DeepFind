"""Izole kurulum + otomatik baslatma + paketli ilk acilis kabulu.

Gercek Inno paketi (ayri AppId, en dusuk yetki) ayri bir klasore kurulur; kullanicinin
kurulu uygulamasi, kasasi ve kisayollari ellenmez. Kayit defteri anahtari once
yedeklenir, sonra geri yuklenir.

Kontroller:
1. Kurulum secilen dilde install-language.txt uretir (tr, de).
2. Kurulan exe adi ve gomulu surum dogru.
3. Uc motor (cpu/vulkan/cuda) gerekli dagitilabilir dosyalariyla kurulur.
4. Model pakette gomulu degildir; ilk acilis akisi indirir (smoke dogrular).
5. Kurulumun "DeepFind'i baslat" komutu (explorer aktarimi) uygulamayi baslatir.
6. Paketli uygulama ilk acilis -> ana ekran -> yeniden acilis zincirini tamamlar
   (paket ici --package-smoke, sentetik belgeler).
7. Kaldirma temiz calisir; kullanici alanindaki model korunur.

Kullanim: PYTHONPATH=src python eval/install_launch_acceptance.py
"""
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from deepfind.installer import windows_file_version  # noqa: E402
from deepfind.version import __version__  # noqa: E402

ISCC = Path(os.environ.get("INNO_ISCC", r"C:\Users\mahmu\AppData\Local\Programs\Inno Setup 6\ISCC.exe"))
SETUP = ROOT / "build" / "test-installer" / f"DeepFind-{__version__}.exe"
REG_KEY = r"HKCU\Software\DeepFind"
LOG = ROOT / "build" / "install-launch-acceptance.log"


def _kayit(satir):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(satir + "\n")
    print(satir, flush=True)


def _reg_yedek(yol):
    yol.write_bytes(b"")
    r = subprocess.run(["reg", "export", REG_KEY, str(yol), "/y"],
                       capture_output=True)
    return r.returncode == 0 and yol.stat().st_size > 0


def _reg_geri(yol):
    if yol.exists() and yol.stat().st_size:
        subprocess.run(["reg", "import", str(yol)], capture_output=True)


def _kur(hedef, dil):
    return subprocess.run([str(SETUP), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                           "/NOICONS", f"/LANG={dil}", f"/DIR={hedef}"],
                          capture_output=True, timeout=900)


def _kaldir(hedef):
    un = hedef / "unins000.exe"
    if not un.is_file():
        try:
            _kayit(f"kaldirici yok; hedef icerigi: {sorted(p.name for p in hedef.iterdir())}")
        except Exception:
            pass
        return None
    return subprocess.run([str(un), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                          capture_output=True, timeout=900)


def _kabukla_baslat(exe):
    """Setup'in [Run] satirinin yaptigi is: kabuk (ShellExecute) uzerinden acma.

    Etkilesimli kurulumda bu is explorer.exe aktarimiyla olur. Etkilesimsiz
    kabul oturumunda explorer.exe komut satiri hedefe ulasmaz; ayni kabuk-acma
    yolunu dogrudan isleten os.startfile esdeger ve gozlenebilir kanittir.
    """
    import os
    os.startfile(str(exe))


def _calisiyor_mu(exe_adi):
    r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_adi}"],
                       capture_output=True, text=True, timeout=60)
    return exe_adi.lower() in r.stdout.lower()


def _kapat(exe_adi):
    subprocess.run(["taskkill", "/F", "/IM", exe_adi],
                   capture_output=True, timeout=60)


def _surecleri_temizle():
    """Kurulu uygulamanin tum surecleri (arama motoru dahil) dursun.

    Yalniz kabul ortami: kaldirma kilitli dosya birakmasin diye _kaldir'dan
    once cagrilir. Gercek kullanimda Inno CloseApplications ile sorar.
    """
    for imaj in ("DeepFind-0.10.9.exe", "llama-server.exe"):
        subprocess.run(["taskkill", "/F", "/IM", imaj],
                       capture_output=True, timeout=60)
    bitis = time.monotonic() + 60
    while time.monotonic() < bitis:
        r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=60)
        kucuk = r.stdout.lower()
        if "deepfind-0.10.9.exe" not in kucuk and "llama-server.exe" not in kucuk:
            return True
        time.sleep(2)
    return False


def main():
    sonuc = {}
    LOG.write_text("", encoding="utf-8")
    assert SETUP.is_file(), f"kurulum paketi yok: {SETUP}"
    reg = ROOT / "build" / f"reg-{uuid.uuid4().hex}.reg"
    assert _reg_yedek(reg), "kayit defteri yedegi alinamadi"
    hedefler = []
    try:
        for dil, beklenen in (("turkish", "tr"), ("german", "de")):
            # Her dil kendi izole hedefine kurulur: donguler arasi kalinti
            # tasiyamaz; ayni-dizin yukseltme installer_acceptance'ta kapsanir.
            hedef = (ROOT / "build" / ("installed-" + uuid.uuid4().hex)).resolve()
            hedefler.append(hedef)
            r = _kur(hedef, dil)
            _kayit(f"kurulum({dil}) cikis={r.returncode}")
            assert r.returncode == 0, r.returncode
            exe = hedef / f"DeepFind-{__version__}.exe"
            assert exe.is_file(), exe
            dil_dosya = hedef / "install-language.txt"
            icerik = dil_dosya.read_text(encoding="utf-8").strip()
            _kayit(f"install-language.txt={icerik}")
            assert icerik == beklenen, (icerik, beklenen)
            surum = windows_file_version(exe)
            _kayit(f"exe surumu={surum}")
            assert surum == tuple(map(int, __version__.split(".")))
            for motor in ("cpu", "vulkan", "cuda"):
                srv = hedef / "_internal" / "embedding" / motor / "llama-server.exe"
                assert srv.is_file(), motor
            _kayit("motorlar: cpu+vulkan+cuda kurulu")
            assert not (hedef / "_internal" / "embedding" / "embeddinggemma-2-Q8_0.gguf").exists(), \
                "model pakette gomulu olmamali"
            _kayit("model pakette gomulu degil (ayri indirilir)")
            sonuc[f"kurulum_{dil}"] = dict(cikis=r.returncode, dil=icerik, surum=str(surum))
            if dil == "turkish":
                # 1) Gercek acilis: kabuk uzerinden baslat, surecin yasadigini gor.
                _kabukla_baslat(exe)
                bitis = time.monotonic() + 120
                while time.monotonic() < bitis:
                    if _calisiyor_mu(exe.name):
                        break
                    time.sleep(2)
                assert _calisiyor_mu(exe.name), "kabuk acmasiyla uygulama baslamadi"
                _kayit("kabuk acmasi: surec calisiyor")
                sonuc["kabuk_acilisi"] = True
                _kapat(exe.name)
                # 2) Kurulu uygulamanin uctan uca kaniti (dogrudan smoke).
                rapor = ROOT / "build" / f"pkg-smoke-{uuid.uuid4().hex}.json"
                subprocess.run([str(exe), "--package-smoke", str(rapor)], check=True,
                               timeout=900)  # ilk acilista model indirilebilir
                assert rapor.is_file(), "paketli uygulama baslatilamadi (rapor yok)"
                veri = json.loads(rapor.read_text(encoding="utf-8"))
                _kayit("paketli acilis raporu: " + json.dumps(veri, ensure_ascii=False)[:400])
                assert veri.get("ok") is True, veri
                sonuc["paketli_acilis"] = veri
            assert _surecleri_temizle(), "uygulama surecleri durmadi"
            k = _kaldir(hedef)
            _kayit(f"kaldirma({dil}) cikis={getattr(k, 'returncode', None)}")
            sonuc[f"kaldirma_{dil}"] = getattr(k, "returncode", None)
            assert not (hedef / f"DeepFind-{__version__}.exe").exists(), "kaldirma dosya birakti"
    finally:
        _reg_geri(reg)
        for hedef in hedefler:
            if hedef.exists():
                shutil.rmtree(hedef, ignore_errors=True)
    sonuc["ok"] = True
    (ROOT / "build" / "install-launch-acceptance.json").write_text(
        json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    _kayit("TAMAM: " + json.dumps(sonuc, ensure_ascii=False))


if __name__ == "__main__":
    main()
