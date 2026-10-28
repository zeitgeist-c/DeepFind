"""Belge küçük resimleri: yerel önbellek ve arka planda üretim.

Desen kaynağı (REA): paperless-ngx thumbnail'ı sunucuda dosyaya üretip
`{id}.webp` olarak saklıyor ve uç nokta ETag ile önbellekliyor; papermerge
`NodeThumbnail` ile listelerde gösteriyor. Evrakçı karşılığı: anahtar
(yol, boyut, mtime) değişmedikçe üretim tekrarlanmaz; ağır render `workers`
alt sürecinde koşar, arayüz yalnızca hazır dosyayı yükler.

Kural: küçük resim kaynak dosyanın yerine geçmez; yalnız görsel kolaylıktır.
Üretilemezse sessizce simgeye düşülür (bozuk/erişilemeyen kaynak akışı bozmaz).
"""
from __future__ import annotations

import hashlib
import os
import threading

from PySide6.QtCore import QThread, Signal

from . import workers

KUCUK = 300   # liste satırı küçük resmi (en uzun kenar, px)
BUYUK = 900   # detay paneli önizlemesi
SINIR = 4000  # önbellekte tutulacak en fazla dosya


def onbellek_dizini() -> str:
    taban = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    yol = os.path.join(taban, "Evrakçı", "thumbs")
    os.makedirs(yol, exist_ok=True)
    return yol


_UZANTI: str | None = None


def bicim_uzantisi() -> str:
    """Qt okuyabildiği ve Pillow yazabildiği biçimi seç (webp → jpg).

    PySide6-Essentials her kurulumda WebP eklentisini taşımayabilir; Qt'nin
    gerçekten okuyabildiğini ölçmeden WebP yazmak sessiz boş görsele yol açar.
    """
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
    """Önbelleği en yeni `sinir` dosyaya indir; silinen sayısını döndür."""
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
    """Önbelleği tamamen boşalt."""
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
    """Sırayla küçük resim üretir; önbellekte olanı doğrudan bildirir.

    İşler: (kaynak yol, tür) ikilileri. Sinyal: (kaynak yol, tür, dosya).
    Dosya boş dize ise üretim yapılamadı (arayüz simgeye düşer).
    """

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
                # "pN": kaynağın N. sayfası (sayfa rayı); diğerleri ilk sayfa.
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
