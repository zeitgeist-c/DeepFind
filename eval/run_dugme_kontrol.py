"""Son kurulum ekranindaki 'DeepFind'i baslat' dugmesinin ayri kontrolu.

Sessiz kurulum sonucu bu dugmenin kabulü sayilmaz. Bu betik ayni [Run]
komutunu gercek Setup motoruna isletir: test kurulumu TestRunAlways ile
derlenir (skipifsilent yok), /SILENT kurulur, Setup'un baslattigi surec
calisir-yol (ExecutablePath) ile dogrulanir, yalniz o PID agaciyla
kapatilir, kaldirma yapilir. Uretim AppId/kasa/kisayola dokunulmaz.
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
LOG = ROOT / "build" / "run-dugme-kontrol.log"
EXE_ADI = f"DeepFind-{__version__}.exe"


def _kayit(satir):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(satir + "\n")
    print(satir, flush=True)


def _pid_bul(hedef):
    """Hedef klasorden calisan DeepFind PID'leri (yol dogrulamali)."""
    r = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process -Filter \"Name='{EXE_ADI}'\" | "
         "Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True, timeout=60)
    pidler = [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]
    dogrulanan = []
    norm_hedef = os.path.normcase(str(hedef))
    for pid in pidler:
        q = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').ExecutablePath"],
            capture_output=True, text=True, timeout=60)
        yol = (q.stdout or "").strip()
        if yol and os.path.normcase(yol).startswith(norm_hedef):
            dogrulanan.append(pid)
    return dogrulanan


def _pid_oldumu(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}"],
                       capture_output=True, text=True, timeout=60)
    return str(int(pid)) in (r.stdout or "")


def main():
    sonuc = {}
    LOG.write_text("", encoding="utf-8")
    assert SETUP.is_file(), f"kurulum paketi yok: {SETUP}"
    yedek = SETUP.with_suffix(".exe.kabul-oncesi")
    shutil.copyfile(SETUP, yedek)
    try:
        # 1) Test kurulumu [Run] komutlu derle (uretim .iss'e ifdef disinda dokunulmaz).
        _kayit("derleme basladi (TestInstall + TestRunAlways)")
        subprocess.run([str(ISCC), "/DTestInstall", "/DTestRunAlways",
                        str(ROOT / "packaging/DeepFind.iss")],
                       cwd=str(ROOT / "packaging"), check=True, timeout=600)
        assert windows_file_version(SETUP) == tuple(map(int, __version__.split(".")))
        _kayit("derleme tamam")
        sonuc["derleme"] = True
        # 2) Kayit defteri yedegi.
        reg = ROOT / "build" / f"reg-rundugme-{uuid.uuid4().hex}.reg"
        reg.write_bytes(b"")
        r = subprocess.run(["reg", "export", REG_KEY, str(reg), "/y"], capture_output=True)
        reg_ok = r.returncode == 0 and reg.stat().st_size > 0
        assert reg_ok, "kayit defteri yedegi alinamadi"
        hedef = (ROOT / "build" / ("rundugme-" + uuid.uuid4().hex)).resolve()
        try:
            # 3) Sessiz kur: Setup [Run] girdisini kendi calistirir (dugme komutuyla ayni).
            kur_log = ROOT / "build" / "run-dugme-kurulum.log"
            r = subprocess.run(
                [str(SETUP), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS",
                 f"/DIR={hedef}", f"/LOG={kur_log}"],
                capture_output=True, timeout=900)
            _kayit(f"kurulum cikis={r.returncode}")
            assert r.returncode == 0, r.returncode
            exe = hedef / EXE_ADI
            assert exe.is_file(), exe
            # 4) Setup'un baslattigi sureci yoldan dogrula.
            pidler = []
            bitis = time.monotonic() + 90
            while time.monotonic() < bitis:
                pidler = _pid_bul(hedef)
                if pidler:
                    break
                time.sleep(2)
            assert pidler, "Setup [Run] komutuyla uygulama baslamadi"
            _kayit(f"[Run] baslattigi PID: {pidler}")
            sonuc["run_pid"] = pidler
            metin = kur_log.read_text(encoding="utf-8", errors="replace") if kur_log.is_file() else ""
            assert "run entry" in metin.lower(), "kurulum gunlugunde Run girdisi yok"
            _kayit("kurulum gunlugu: Run girdisi islendi")
            sonuc["run_gunluk"] = True
            # 5) Yalniz dogrulanan PID'leri kapat.
            for pid in pidler:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True, timeout=60)
            bitis = time.monotonic() + 60
            while time.monotonic() < bitis:
                if not any(_pid_oldumu(p) for p in pidler):
                    break
                time.sleep(2)
            assert not any(_pid_oldumu(p) for p in pidler), "surec durmadi"
            _kayit("dogrulanan surecler durdu")
            # 6) Kaldir.
            un = hedef / "unins000.exe"
            k = subprocess.run([str(un), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                               capture_output=True, timeout=900)
            _kayit(f"kaldirma cikis={k.returncode}")
            assert k.returncode == 0, k.returncode
            assert not exe.exists(), "kaldirma dosya birakti"
            sonuc["kaldirma"] = 0
        finally:
            if reg.exists() and reg.stat().st_size:
                subprocess.run(["reg", "import", str(reg)], capture_output=True)
            if hedef.exists():
                shutil.rmtree(hedef, ignore_errors=True)
    finally:
        shutil.copyfile(yedek, SETUP)
        try:
            yedek.unlink()
        except OSError:
            pass
    sonuc["ok"] = True
    (ROOT / "build" / "run-dugme-kontrol.json").write_text(
        json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    _kayit("TAMAM: " + json.dumps(sonuc, ensure_ascii=False))


if __name__ == "__main__":
    main()
