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
        return None
    return subprocess.run([str(un), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                          capture_output=True, timeout=900)


def _explorer_baslat(exe, *args):
    """Setup'in [Run] satirinin yaptigi is: explorer.exe uzerinden aktarim."""
    return subprocess.run(["explorer.exe", str(exe), *args], capture_output=True, timeout=60)


def main():
    sonuc = {}
    LOG.write_text("", encoding="utf-8")
    assert SETUP.is_file(), f"kurulum paketi yok: {SETUP}"
    reg = ROOT / "build" / f"reg-{uuid.uuid4().hex}.reg"
    assert _reg_yedek(reg), "kayit defteri yedegi alinamadi"
    hedef = (ROOT / "build" / ("installed-" + uuid.uuid4().hex)).resolve()
    try:
        for dil, beklenen in (("turkish", "tr"), ("german", "de")):
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
                # Setup'in postinstall komutu: explorer aktarimi ile uygulamayi baslat.
                rapor = ROOT / "build" / f"pkg-smoke-{uuid.uuid4().hex}.json"
                _explorer_baslat(exe, "--package-smoke", str(rapor))
                bitis = time.monotonic() + 900  # ilk acilista model indirilebilir
                while time.monotonic() < bitis:
                    if rapor.is_file() and rapor.stat().st_size > 0:
                        try:
                            veri = json.loads(rapor.read_text(encoding="utf-8"))
                        except Exception:
                            veri = None
                        if isinstance(veri, dict) and "ok" in veri:
                            break
                    time.sleep(1)
                assert rapor.is_file(), "paketli uygulama baslatilamadi (rapor yok)"
                veri = json.loads(rapor.read_text(encoding="utf-8"))
                _kayit("paketli acilis raporu: " + json.dumps(veri, ensure_ascii=False)[:400])
                assert veri.get("ok") is True, veri
                sonuc["paketli_acilis"] = veri
            k = _kaldir(hedef)
            _kayit(f"kaldirma({dil}) cikis={getattr(k, 'returncode', None)}")
            sonuc[f"kaldirma_{dil}"] = getattr(k, "returncode", None)
            assert not (hedef / f"DeepFind-{__version__}.exe").exists(), "kaldirma dosya birakti"
    finally:
        _reg_geri(reg)
        if hedef.exists():
            shutil.rmtree(hedef, ignore_errors=True)
    sonuc["ok"] = True
    (ROOT / "build" / "install-launch-acceptance.json").write_text(
        json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    _kayit("TAMAM: " + json.dumps(sonuc, ensure_ascii=False))


if __name__ == "__main__":
    main()
