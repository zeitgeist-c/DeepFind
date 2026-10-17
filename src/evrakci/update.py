"""Evrakçı kendi kendini güncelleme: herkese açık Evrakci-Releases deposundan.

Kaynak depo özel kalır; paketler (yalnız kurulum ZIP'i) herkese açık ayrı bir
depoda yayınlanır. Böylece uygulama "en yeni sürüm hangisi?" sorusunu EXE
içine kimlik bilgisi gömmeden sorabilir. GitHub API herkese açık depolarda
kimliksiz yanıt verir (IP başına sınırlı); günde bir denetim tek istek
kullanır ve sınırın çok altında kalır.

Bir yayın kendinden öncekini geçersiz kılar: eski sürüm `releases/latest` ile
doğrudan en yeniye atlar, aradaki adımları indirmez.

Paket bütünlüğü iki katmanlıdır: yayın varlığının SHA-256 özeti (yalnız ağ
yoluyla gelir) indirme sonrası doğrulanır, ardından ZIP açılıp manifest
sürümü denetlenir. Doğrulamayı geçemeyen dosya asla çalıştırılmaz/yerleşmez.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

RELEASE_REPO = "zeitgeist-c/Evrakci-Releases"
API_LATEST = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"
from .version import __version__
USER_AGENT = f"Evrakci/{__version__}"
PROGRAM = "Evrakçı"
log = logging.getLogger("evrakci.update")

# ZIP içindeki kök klasör ve varlık adı bu kalıptan türevlenir. GitHub varlık
# adlarını latinleştirebildiğinden (ç -> c) iki yazım da kabul edilir.
_KLASOR_KALIBI = "Evrakçı-{s}"
_VARLIK_YAZIMLARI = ("Evrakçı-{s}.zip", "Evrakci-{s}.zip")


class UpdateError(Exception):
    """Kullanıcıya aynen gösterilecek hata: ağ, biçim, özet, izin."""


@dataclass
class UpdateInfo:
    version: str
    asset_name: str
    download_url: str
    sha256: str          # beklenen özet; yayın vermiyorsa ""
    size: int
    page_url: str


def parse_version(text: str) -> tuple:
    """'v0.7.10' / '0.7.10-beta' -> (0, 7, 10); sayısal olmayan kuyruk durur."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    if not match:
        raise UpdateError("Sürüm numarası çözümlenemedi.")
    return tuple(int(part) for part in match.groups())


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def parse_release(payload: dict) -> UpdateInfo:
    """`/releases/latest` yanıtından kurulum ZIP varlığını seç."""
    tag = str(payload.get("tag_name") or "")
    version = tag[1:] if tag.startswith("v") else tag
    parse_version(version)  # karşılaştıramayacağımız etiketleri reddet
    adaylar = {y.format(s=version) for y in _VARLIK_YAZIMLARI}
    for asset in payload.get("assets") or []:
        if asset.get("name") not in adaylar:
            continue
        digest = str(asset.get("digest") or "")
        return UpdateInfo(
            version=version,
            asset_name=str(asset.get("name")),
            download_url=str(asset.get("browser_download_url") or ""),
            sha256=digest.split(":", 1)[1] if ":" in digest else digest,
            size=int(asset.get("size") or 0),
            page_url=str(payload.get("html_url") or ""),
        )
    raise UpdateError("En yeni yayında kurulum paketi bulunamadı.")


def fetch_latest() -> UpdateInfo:
    request = urllib.request.Request(API_LATEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("Henüz yayınlanmış bir sürüm yok.") from exc
        raise UpdateError("Güncelleme sunucusuna ulaşılamadı.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise UpdateError("Güncelleme sunucusuna ulaşılamadı.") from exc
    return parse_release(payload)


def check_for_update(current: str) -> UpdateInfo | None:
    info = fetch_latest()
    return info if is_newer(info.version, current) else None


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def updates_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Evrakci" / "Updates"
    base.mkdir(parents=True, exist_ok=True)
    return base


def download(info: UpdateInfo, dest: Path, progress=None, cancel=None) -> Path:
    """Varlığı dest'e indir; boyut ve SHA-256 doğrulanmadan dosya tutulmaz.

    Yarım inen ya da kurcalanmış paket asla çalışan program olamaz: doğrulama
    hatasında veya iptalde dosya silinir. `cancel` bir threading.Event'tir;
    ilerleme geri çağrısı onu yoklar.
    """
    class Cancelled(Exception):
        pass

    request = urllib.request.Request(info.download_url,
                                     headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or info.size)
            with dest.open("wb") as out:
                try:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                        written += len(chunk)
                        if progress:
                            progress(written, total)
                        if cancel is not None and cancel.is_set():
                            raise Cancelled()
                except Cancelled:
                    pass
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        dest.unlink(missing_ok=True)
        raise UpdateError("Güncelleme indirmesi kesintiye uğradı.") from exc
    if cancel is not None and cancel.is_set():
        dest.unlink(missing_ok=True)
        raise UpdateError("cancelled")
    if info.size and written != info.size:
        dest.unlink(missing_ok=True)
        raise UpdateError("İndirme, dosya tamamlanmadan bitti.")
    if info.sha256:
        actual = _sha256_of(dest)
        if actual.lower() != info.sha256.lower():
            dest.unlink(missing_ok=True)
            raise UpdateError("İndirilen dosyanın özeti tutmuyor.")
    return dest


def _zip_guvenli_mi(archive: zipfile.ZipFile) -> bool:
    """Zip Slip: hiçbir üye hedef ağacın dışına çıkmamalı."""
    for uye in archive.infolist():
        ad = Path(uye.filename)
        if ad.is_absolute() or ad.drive or ".." in ad.parts:
            return False
    return True


def extract_zip(zip_path: Path, hedef_ust: Path, beklenen_surum: str) -> Path:
    """ZIP'i hedef üst dizine aç; kök klasörü, EXE'yi ve manifest'i doğrula.

    Herhangi bir adım başarısız olursa açılmış yarım klasör de silinir:
    doğrulanmamış paket diskte kalmaz.
    """
    zip_path = Path(zip_path)
    hedef_ust = Path(hedef_ust)
    kok = hedef_ust / _KLASOR_KALIBI.format(s=beklenen_surum)
    if kok.exists():
        shutil.rmtree(kok)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if not _zip_guvenli_mi(archive):
                raise UpdateError("Paket beklenmeyen dosya yolları içeriyor.")
            archive.extractall(hedef_ust)
        if not kok.is_dir():
            raise UpdateError("Paket yapısı beklenenden farklı.")
        exe = kok / f"{kok.name}.exe"
        if not exe.is_file():
            raise UpdateError("Paket içinde uygulama dosyası bulunamadı.")
        if not (kok / "_internal").is_dir():
            raise UpdateError("Paket eksik görünüyor.")
        manifest_yolu = kok / "manifest.json"
        try:
            manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateError("Paket sürüm bilgisi okunamadı.") from exc
        if manifest.get("program") != PROGRAM or manifest.get("version") != beklenen_surum:
            raise UpdateError("Paket sürüm bilgisi beklenenden farklı.")
        return kok
    except UpdateError:
        shutil.rmtree(kok, ignore_errors=True)
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(kok, ignore_errors=True)
        raise UpdateError("Paket açılamadı.") from exc


def prepare(info: UpdateInfo, progress=None, cancel=None) -> Path:
    """İndir + aç + doğrula; yerleşmeye hazır klasörü döndür.

    Açma/doğrulama başarısızsa indirilen ZIP de silinir: yarıda kalan ya da
    bozuk bir paket diskte artık bırakmaz.
    """
    klasor = updates_dir()
    zip_yolu = klasor / f"{_KLASOR_KALIBI.format(s=info.version)}.zip"
    download(info, zip_yolu, progress=progress, cancel=cancel)
    try:
        return extract_zip(zip_yolu, klasor, info.version)
    except UpdateError:
        zip_yolu.unlink(missing_ok=True)
        raise


def spawn_swap(old_pid: int, hazir_klasor: Path, calisan_exe: Path,
               kasa_yolu: str) -> Path:
    """Çalışan sürümü taze kopyayla değiştirecek bekçi betiği kur.

    Windows çalışan bir EXE'nin yerini değiştirmez: betik bu süreç çıkana
    kadar bekler, hazır klasörü çalışan programın yanına taşır, yeni EXE'yi
    kasadan bağımsız normal açılışla başlatır ve kendini siler. Taşıma
    başarısız olursa (salt-okunur klasör) geçici kopyadan başlatır ve bunu
    `son-guncelleme.txt` ile bildirir.
    """
    hazir_klasor = Path(hazir_klasor)
    calisan_exe = Path(calisan_exe)
    hedef_ust = calisan_exe.resolve().parent
    yeni_exe = hedef_ust / hazir_klasor.name / f"{hazir_klasor.name}.exe"
    gecici_exe = hazir_klasor / f"{hazir_klasor.name}.exe"
    betik = hazir_klasor.parent / "evrakci-guncelleme.bat"
    sonuc = hazir_klasor.parent / "son-guncelleme.txt"
    zip_yolu = hazir_klasor.parent / f"{hazir_klasor.name}.zip"
    sistem = "%SystemRoot%\\System32"
    satirlar = [
        "@echo off",
        "chcp 65001 >nul",
        "setlocal",
        f'set "PID={old_pid}"',
        f'set "SRCDIR={hazir_klasor}"',
        f'set "DESTPARENT={hedef_ust}"',
        f'set "NEWEXE={yeni_exe}"',
        f'set "GECICI={gecici_exe}"',
        f'set "KASA={kasa_yolu}"',
        f'set "SONUC={sonuc}"',
        "set /a TRIES=0",
        ":wait",
        f'"{sistem}\\tasklist.exe" /FI "PID eq %PID%" 2>NUL | '
        f'"{sistem}\\find.exe" " %PID% " >NUL',
        "if errorlevel 1 goto gone",
        "set /a TRIES+=1",
        "if %TRIES% GEQ 300 goto gone",
        f'"{sistem}\\ping.exe" -n 2 127.0.0.1 >NUL',
        "goto wait",
        ":gone",
        'if not exist "%NEWEXE%" move "%SRCDIR%" "%DESTPARENT%" >NUL 2>NUL',
        'if exist "%NEWEXE%" (',
        '  echo ok>"%SONUC%"',
        '  start "" "%NEWEXE%" --restarted --kasa "%KASA%"',
        ') else (',
        '  echo fallback>"%SONUC%"',
        '  start "" "%GECICI%" --restarted --kasa "%KASA%"',
        ')',
        f'del "{zip_yolu}" >NUL 2>NUL',
        'del "%~f0"',
        "endlocal",
    ]
    betik.write_text("\r\n".join(satirlar), encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", str(betik)], creationflags=flags,
                     cwd=str(betik.parent), close_fds=True)
    log.info("swap armed: pid=%s yeni=%s", old_pid, yeni_exe)
    return betik


def son_sonuc(temizle: bool = True) -> str:
    """Bekçi betiğin bıraktığı sonuç damgasını oku ("ok"/"fallback"/"").

    Okunduğunda damga silinir; bildirim bir kez gösterilir.
    """
    yol = updates_dir() / "son-guncelleme.txt"
    try:
        metin = yol.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if temizle:
        try:
            yol.unlink(missing_ok=True)
        except OSError:
            pass
    return metin


def temizle(aktif_klasor: Path | None = None, min_yas_sn: float = 6 * 3600) -> None:
    """Updates alanındaki eski artıkları topla.

    İki koruma: içinden çalışılan klasöre dokunulmaz (taşınamamış kopya),
    ve yeni hazırlanmış öğeler korunur — bekleyen bir değişim betiği henüz
    taşımamış olabilir; 6 saatlik eşik o yarışı kapatır.
    """
    import time as _zaman
    try:
        kok = updates_dir()
    except OSError:
        return
    aktif = None
    if aktif_klasor is not None:
        try:
            aktif = Path(aktif_klasor).resolve()
        except OSError:
            aktif = None
    simdi = _zaman.time()
    for oge in kok.iterdir():
        try:
            if aktif is not None and oge.resolve() == aktif:
                continue
            if simdi - oge.stat().st_mtime < min_yas_sn:
                continue
            if oge.is_dir():
                shutil.rmtree(oge, ignore_errors=True)
            else:
                oge.unlink(missing_ok=True)
        except OSError:
            continue


def last_check_is_old(stamp: str, max_age_seconds: float = 24 * 3600) -> bool:
    """Damga eksik ya da pencereden eskiyse True (denetim gerekir)."""
    if not stamp:
        return True
    try:
        import datetime
        when = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return True
    import datetime
    age = (datetime.datetime.now() - when.replace(tzinfo=None)).total_seconds()
    return age > max_age_seconds


def now_stamp() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")
