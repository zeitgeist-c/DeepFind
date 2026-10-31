"""Document thumbnails: local cache and background production.

Pattern source (REA): paperless-ngx produces the thumbnail server-side into a file,
stores it as `{id}.webp` and caches the endpoint with ETag; papermerge
shows it in lists with `NodeThumbnail`. DeepFind's counterpart: production
never repeats while the key (path, size, mtime) is unchanged; heavy render runs
in a `workers` subprocess, the UI only loads the finished file.

Rule: a thumbnail never stands in for the source file; it is visual convenience only.
When unproducible, fall back to an icon quietly (a broken/unreachable source never breaks the flow)."""
from __future__ import annotations

import hashlib
import os
import threading

from PySide6.QtCore import QThread, Signal

from . import paths, workers

KUCUK = 300   # list-row thumbnail (longest edge, px)
BUYUK = 900   # detail panel preview
SINIR = 4000  # max files kept in cache


def onbellek_dizini() -> str:
    return str(paths.thumbs_dir())


_UZANTI: str | None = None


def bicim_uzantisi() -> str:
    """Pick a format Qt can read and Pillow can write (webp → jpg).

PySide6-Essentials may not ship the WebP plugin on every install; writing WebP
without measuring what Qt can really read leads to silently empty images."""
    global _UZANTI
    if _UZANTI is None:
        secim = ".jpg"
        try:
            from PySide6.QtGui import QImageReader
            okunur = {bytes(f).decode("ascii", "ignore").lower()
                      for f in QImageReader.supportedImageFormats()}
            from PIL import Image
            Image.init()
            if "webp" in okunur and "WEBP" in Image.SAVE:
                secim = ".webp"
        except Exception:
            secim = ".jpg"
        _UZANTI = secim
    return _UZANTI


def anahtar(path: str, boyut: int, mtime_ns: int, tur: str = "s") -> str:
    canonical = str(path).upper() if os.name == 'nt' else os.path.normcase(str(path))
    ham = f"{canonical}|{int(boyut)}|{int(mtime_ns)}|{tur}"
    return hashlib.sha1(ham.encode("utf-8", "ignore")).hexdigest()


def hedef_yolu(path: str, boyut: int, mtime_ns: int, tur: str = "s",
               dizin: str | None = None) -> str:
    dizin = dizin or onbellek_dizini()
    return os.path.join(dizin, anahtar(path, boyut, mtime_ns, tur) + bicim_uzantisi())


def hazir_olan(path: str, boyut: int, mtime_ns: int, tur: str = "s",
               dizin: str | None = None) -> str | None:
    yol = hedef_yolu(path, boyut, mtime_ns, tur, dizin)
    return yol if os.path.exists(yol) else None


def _damga(path: str):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


def buda(dizin: str | None = None, sinir: int = SINIR) -> int:
    """Trim the cache down to the newest `sinir` files; return the deleted count."""
    dizin = dizin or onbellek_dizini()
    try:
        kayitlar = [os.path.join(dizin, ad) for ad in os.listdir(dizin)]
    except OSError:
        return 0
    kayitlar = [y for y in kayitlar if os.path.isfile(y)]
    if len(kayitlar) <= sinir:
        return 0
    try:
        kayitlar.sort(key=os.path.getmtime)
    except OSError:
        return 0
    silinen = 0
    for yol in kayitlar[:len(kayitlar) - sinir]:
        try:
            os.remove(yol)
            silinen += 1
        except OSError:
            pass
    return silinen


def temizle(dizin: str | None = None) -> int:
    """Empty the cache completely."""
    dizin = dizin or onbellek_dizini()
    silinen = 0
    try:
        adlar = os.listdir(dizin)
    except OSError:
        return 0
    for ad in adlar:
        yol = os.path.join(dizin, ad)
        try:
            if os.path.isfile(yol):
                os.remove(yol)
                silinen += 1
        except OSError:
            pass
    return silinen


class OnbellekYukleyici(QThread):
    """Produce thumbnails in order; report cached ones directly.

Jobs: (source path, kind) pairs. Signal: (source path, kind, file).
An empty file string means production failed (the UI falls back to an icon)."""

    tamam = Signal(str, str, str)

    def __init__(self, isler, parent=None):
        super().__init__(parent)
        self.isler = list(isler)
        self._dur = threading.Event()

    def durdur(self):
        self._dur.set()

    def run(self):
        olcu = {"s": KUCUK, "l": BUYUK}
        oturum = None
        try:
            for kaynak, tur in self.isler:
                if self._dur.is_set():
                    return
                # "pN": page N of the source (page rail); others are the first page.
                sayfa, piksel = 1, olcu.get(tur, KUCUK)
                if tur.startswith("p") and tur[1:].isdigit():
                    sayfa, piksel = int(tur[1:]), KUCUK
                st = _damga(kaynak)
                if st is None:
                    self.tamam.emit(kaynak, tur, "")
                    continue
                onbellek = hazir_olan(kaynak, st[0], st[1], tur)
                if onbellek:
                    self.tamam.emit(kaynak, tur, onbellek)
                    continue
                hedef = hedef_yolu(kaynak, st[0], st[1], tur)
                try:
                    if oturum is None or not oturum.alive():
                        oturum = workers.WorkerSession()
                    oturum.call("thumb", (kaynak, hedef, piksel, sayfa),
                                timeout=45, stop=self._dur.is_set)
                    self.tamam.emit(kaynak, tur, hedef)
                except Exception:
                    self.tamam.emit(kaynak, tur, "")
        finally:
            if oturum is not None:
                oturum.kill()
