"""Install pinned OCR models without altering system-wide Tesseract."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
MODELS = {
    "tur": (4550554, "7393381111e1152420fc4092cb44eef4237580d21b92bf30d7d221aad192c6b7"),
    "eng": (4113088, "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"),
    "osd": (10562727, "9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff"),
}
BASE_URL = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{REVISION}"


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "evrakci" / "ocr_runtime"
    return Path(os.environ.get("EVRAKCI_OCR_RUNTIME", "C:/Program Files/Tesseract-OCR"))


def executable() -> Path:
    return runtime_dir() / "tesseract.exe"


def data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Evrakci" / "OCR" / "tessdata"


def _valid(path: Path, lang: str) -> bool:
    if not path.is_file():
        return False
    size, digest = MODELS[lang]
    if path.stat().st_size != size:
        return False
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == digest


def ready() -> tuple[bool, list[str]]:
    missing = []
    if not executable().is_file():
        missing.append("tesseract.exe")
    missing += [lang for lang in MODELS if not _valid(data_dir() / f"{lang}.traineddata", lang)]
    if not missing:
        try:
            _engine_check(data_dir())
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            missing.append("motor doğrulaması")
    return not missing, missing


def _engine_check(directory: Path) -> None:
    env = dict(os.environ, TESSDATA_PREFIX=str(directory))
    completed = subprocess.run([str(executable()), "--list-langs"], capture_output=True,
                               text=True, timeout=30, env=env)
    found = set(completed.stdout.split())
    if completed.returncode or not set(MODELS).issubset(found):
        raise RuntimeError("OCR motoru dil modellerini yükleyemedi: " + completed.stderr[:400])


def ensure(progress=None, offline_dir: str | None = None) -> None:
    """Verify, download/copy missing models, then activate each atomically."""
    if not executable().is_file():
        raise RuntimeError("Paketli Tesseract motoru eksik; uygulama paketini yeniden edinin.")
    target = data_dir()
    target.mkdir(parents=True, exist_ok=True)
    for index, lang in enumerate(MODELS):
        final = target / f"{lang}.traineddata"
        if _valid(final, lang):
            if progress:
                progress(lang, index + 1, len(MODELS), MODELS[lang][0], MODELS[lang][0])
            continue
        part = target / f"{lang}.traineddata.part"
        if offline_dir:
            source = Path(offline_dir) / final.name
            if not _valid(source, lang):
                raise RuntimeError(f"Çevrimdışı pakette {final.name} eksik veya doğrulanamadı.")
            with source.open("rb") as incoming, part.open("wb") as outgoing:
                for chunk in iter(lambda: incoming.read(1 << 20), b""):
                    outgoing.write(chunk)
        else:
            downloaded = part.stat().st_size if part.exists() else 0
            expected = MODELS[lang][0]
            if downloaded >= expected:
                part.unlink()
                downloaded = 0
            request = urllib.request.Request(f"{BASE_URL}/{final.name}",
                                             headers={"Range": f"bytes={downloaded}-"} if downloaded else {})
            with urllib.request.urlopen(request, timeout=30) as response:
                if downloaded and response.status != 206:
                    downloaded = 0
                with part.open("ab" if downloaded else "wb") as fh:
                    while chunk := response.read(1 << 20):
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if progress:
                            progress(lang, index + 1, len(MODELS), downloaded, expected)
        if not _valid(part, lang):
            raise RuntimeError(f"{final.name} bütünlük doğrulaması başarısız; yeniden deneyin.")
        part.replace(final)
    _engine_check(target)
    if progress:
        progress("ready", len(MODELS), len(MODELS), 1, 1)


def reopen_deferred(con) -> int:
    """Retry only OCR jobs previously deferred for missing engine/model."""
    if not ready()[0]:
        return 0
    result = con.execute(
        "UPDATE jobs SET not_before=0 WHERE kind='ocr' AND status='pending'"
        " AND error_code IN ('MODEL_MISSING','ENGINE_UNAVAILABLE')")
    con.commit()
    return result.rowcount
