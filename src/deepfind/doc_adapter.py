"""DOC adaptoru (plan bolum 8 kapisi): LibreOffice varsa korumali donusum, yoksa ad/yol."""
from __future__ import annotations

import os
import subprocess
import tempfile

CANDIDATES = [
    "C:/Program Files/LibreOffice/program/soffice.exe",
    "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
]

CONVERT_TIMEOUT = 120


def find_office() -> str | None:
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def convert_doc(path: str, workdir: str) -> str:
    """Kaynaga yazmaz: cikti yalniz workdir'e. Donusum yoksa EngineUnavailable."""
    soffice = find_office()
    if not soffice:
        raise EngineUnavailable("LibreOffice bulunamadi")
    profile = os.path.join(workdir, "lo-profile")
    outdir = os.path.join(workdir, "lo-out")
    os.makedirs(profile, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.basename(path)
    r = subprocess.run(
        [soffice, "--headless", "--nolockcheck", "--norestore",
         f"-env:UserInstallation=file:///{profile}",
         "--convert-to", "txt:Text (encoded):UTF8", "--outdir", outdir, path],
        capture_output=True, text=True, timeout=CONVERT_TIMEOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if r.returncode != 0:
        raise ConvertFailed(f"soffice rc={r.returncode}: {r.stderr[:200]}")
    stem = os.path.splitext(base)[0] + ".txt"
    out = os.path.join(outdir, stem)
    if not os.path.exists(out):
        raise ConvertFailed("cikti uretilemedi")
    with open(out, encoding="utf-8", errors="replace") as f:
        return f.read()


class EngineUnavailable(Exception):
    pass


class ConvertFailed(Exception):
    pass


def extract_doc_guarded(path: str):
    """(metin, uyari) veya None (adaptor yok). Gecici cikti is sonu silinir."""
    from .extract import ExtractResult, Segment
    try:
        with tempfile.TemporaryDirectory(prefix="deepfind-doc-") as wd:
            text = convert_doc(path, wd)
    except EngineUnavailable:
        return None
    except Exception:
        return ExtractResult(status="corrupt", error_code="CORRUPT_DOCUMENT")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    segs = [Segment("para", None, f"Paragraf {i + 1}", ln) for i, ln in enumerate(lines)]
    return ExtractResult(segs or [], "ok" if segs else "partial")
