"""DeepFind kendi kendini güncelleme: herkese açık DeepFind deposundan.

Kaynak depo özel kalır; kurulum ve güncelleme paketleri herkese açık ayrı bir
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

RELEASE_REPO = "zeitgeist-c/DeepFind"
API_LATEST = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"
from .version import __version__
from .installer import windows_file_version, spawn_installer
from . import paths
from .theme import t
USER_AGENT = f"DeepFind/{__version__}"
PROGRAM = "DeepFind"
log = logging.getLogger("deepfind.update")

# Legacy ZIP preparation keeps the original root folder convention.
_KLASOR_KALIBI = "DeepFind-{s}"


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
        raise UpdateError(t("Sürüm numarası çözümlenemedi."))
    return tuple(int(part) for part in match.groups())


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def parse_release(payload: dict) -> UpdateInfo:
    """Select a verified installer; ZIP assets are only for older clients."""
    tag = str(payload.get("tag_name") or "")
    version = tag[1:] if tag.startswith("v") else tag
    # Sürüm adı dosya yoluna giriyor (Updates/<ad>-<sürüm>.exe); yalnız
    # rakam+nokta kabul edilir, aksi halde "../" ile hedef dizin dışına yazılır.
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise UpdateError(t("Yayın sürüm etiketi beklenen biçimde değil."))
    parse_version(version)  # karşılaştıramayacağımız etiketleri reddet
    # Modern clients always use the installer, including portable -> installed
    # migration. ZIP remains a release asset for pre-0.10 clients only.
    adaylar = {f'DeepFind-{version}.exe'}
    from .model_indir import paylasilan_hazir
    incremental = paylasilan_hazir()
    if incremental:
        adaylar.update({f'DeepFind-{version}.zip', f'DeepFind-{version}.deepfind'})
    def priority(asset):
        name = str(asset.get('name',''))
        return 0 if name.endswith('.deepfind') else 1 if name.endswith('.exe') else 2
    for asset in sorted(payload.get("assets") or [], key=priority):
        if asset.get("name") not in adaylar:
            continue
        digest = str(asset.get("digest") or "")
        if not re.fullmatch(r'(?:sha256:)?[0-9a-fA-F]{64}', digest):
            raise UpdateError('Yayın SHA-256 doğrulama bilgisi eksik.')
        return UpdateInfo(
            version=version,
            asset_name=str(asset.get("name")),
            download_url=str(asset.get("browser_download_url") or ""),
            sha256=digest.split(":", 1)[1] if ":" in digest else digest,
            size=int(asset.get("size") or 0),
            page_url=str(payload.get("html_url") or ""),
        )
    raise UpdateError(t("En yeni yayında doğrulanabilir kurulum EXE'si bulunamadı."))


def fetch_latest() -> UpdateInfo:
    request = urllib.request.Request(API_LATEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(t("Henüz yayınlanmış bir sürüm yok.")) from exc
        raise UpdateError(t("Güncelleme sunucusuna ulaşılamadı.")) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise UpdateError(t("Güncelleme sunucusuna ulaşılamadı.")) from exc
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
    base = paths.updates_dir()
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
        raise UpdateError(t("Güncelleme indirmesi kesintiye uğradı.")) from exc
    if cancel is not None and cancel.is_set():
        dest.unlink(missing_ok=True)
        raise UpdateError("cancelled")
    if info.size and written != info.size:
        dest.unlink(missing_ok=True)
        raise UpdateError(t("İndirme, dosya tamamlanmadan bitti."))
    if info.sha256:
        actual = _sha256_of(dest)
        if actual.lower() != info.sha256.lower():
            dest.unlink(missing_ok=True)
            raise UpdateError(t("İndirilen dosyanın özeti tutmuyor."))
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
                raise UpdateError(t("Paket beklenmeyen dosya yolları içeriyor."))
            archive.extractall(hedef_ust)
        if not kok.is_dir():
            raise UpdateError(t("Paket yapısı beklenenden farklı."))
        exe = kok / f"{kok.name}.exe"
        if not exe.is_file():
            raise UpdateError(t("Paket içinde uygulama dosyası bulunamadı."))
        if not (kok / "_internal").is_dir():
            raise UpdateError(t("Paket eksik görünüyor."))
        manifest_yolu = kok / "manifest.json"
        try:
            manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateError(t("Paket sürüm bilgisi okunamadı.")) from exc
        if manifest.get("program") != PROGRAM or manifest.get("version") != beklenen_surum:
            raise UpdateError(t("Paket sürüm bilgisi beklenenden farklı."))
        return kok
    except UpdateError:
        shutil.rmtree(kok, ignore_errors=True)
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(kok, ignore_errors=True)
        raise UpdateError(t("Paket açılamadı.")) from exc


def prepare(info: UpdateInfo, progress=None, cancel=None) -> Path:
    """İndir + aç + doğrula; yerleşmeye hazır klasörü döndür.

    Açma/doğrulama başarısızsa indirilen ZIP de silinir: yarıda kalan ya da
    bozuk bir paket diskte artık bırakmaz.
    """
    klasor = updates_dir()
    if info.asset_name.endswith('.deepfind'):
        return prepare_incremental(info, klasor, progress, cancel)
    if info.asset_name.lower().endswith('.exe'):
        target = klasor / f'DeepFind-{info.version}.exe'
        download(info, target, progress=progress, cancel=cancel)
        try:
            if windows_file_version(target) != parse_version(info.version):
                raise UpdateError('Kurulum dosyasının sürümü doğrulanamadı.')
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target
    zip_yolu = klasor / f"{_KLASOR_KALIBI.format(s=info.version)}.zip"
    download(info, zip_yolu, progress=progress, cancel=cancel)
    try:
        return extract_zip(zip_yolu, klasor, info.version)
    except UpdateError:
        zip_yolu.unlink(missing_ok=True)
        raise


def prepare_incremental(info, directory, progress=None, cancel=None):
    """Only two permitted members: versioned installer and strict model manifest."""
    from .model_indir import MODEL_SHA256, paylasilan_hazir
    if not paylasilan_hazir(): raise UpdateError('Model doğrulanamadı; tam kurulum gerekli.')
    archive = directory / f'DeepFind-{info.version}.deepfind'
    download(info, archive, progress=progress, cancel=cancel)
    target = directory / f'DeepFind-{info.version}.exe'
    try:
        with zipfile.ZipFile(archive) as z:
            installer = f'DeepFind-{info.version}.exe'
            if len(z.infolist()) != 2 or set(z.namelist()) != {installer, 'manifest.json'}:
                raise UpdateError('Güncelleme paketi beklenmeyen dosyalar içeriyor.')
            if z.getinfo('manifest.json').file_size > 65536 or z.getinfo(installer).file_size > 2*1024**3:
                raise UpdateError('Güncelleme paketi boyut sınırını aşıyor.')
            meta = json.loads(z.read('manifest.json'))
            if meta != {'program':PROGRAM, 'version':info.version, 'model_sha256':MODEL_SHA256}:
                raise UpdateError('Güncelleme modeli/sürümü uyuşmuyor; tam kurulum gerekli.')
            with z.open(installer) as source, target.open('wb') as out:
                shutil.copyfileobj(source, out, 1024*1024)
        if windows_file_version(target) != parse_version(info.version):
            raise UpdateError('Kurulum sürümü uyuşmuyor.')
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        archive.unlink(missing_ok=True)


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
    if hazir_klasor.is_file() and hazir_klasor.suffix.lower() == '.exe':
        return spawn_installer(old_pid, hazir_klasor, Path(calisan_exe), kasa_yolu)
    calisan_exe = Path(calisan_exe)
    hedef_ust = calisan_exe.resolve().parent
    yeni_exe = hedef_ust / hazir_klasor.name / f"{hazir_klasor.name}.exe"
    gecici_exe = hazir_klasor / f"{hazir_klasor.name}.exe"
    betik = hazir_klasor.parent / "deepfind-guncelleme.bat"
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
