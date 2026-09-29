"""Small, path-free lifecycle log for diagnosing packaged Windows exits."""
from __future__ import annotations

import faulthandler
import os
import time
from pathlib import Path

_stream = None


def _log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Evrakci" / "Logs"
    base.mkdir(parents=True, exist_ok=True)
    return base / "lifecycle.log"


def install() -> None:
    global _stream
    if _stream is not None:
        return
    path = _log_path()
    if path.exists() and path.stat().st_size > 2_000_000:
        old = path.with_suffix(".previous.log")
        old.unlink(missing_ok=True)
        path.replace(old)
    # This path is fixed under LocalAppData, never under a scanned source root.
    _stream = path.open("at", encoding="utf-8", buffering=1)
    faulthandler.enable(file=_stream, all_threads=True)
    record("start")


def record(stage: str, detail: str = "") -> None:
    if _stream is None:
        return
    # Callers pass fixed state names / exception types, never paths or messages.
    _stream.write(f"{int(time.time())} pid={os.getpid()} {stage} {detail}\n")
