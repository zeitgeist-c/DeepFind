"""Canlı klasör izleme: Win32 ReadDirectoryChangesW, yeni bağımlılık yok.

Tasarım: izleyici thread yalnız olay toplar + debounce yapar; DB'ye yazmaz.
Değişen dizinler `on_change(dirs)` ile arayüze verilir, tarama mevcut
`_tara_baslat(roots=..., automatic=True)` yolundan koşar. Güç kesintisinde
olaylar kaybolur; zamanlanmış tarama güvenlik ağı olarak kalır.
"""
from __future__ import annotations

import os
import struct
import threading
import time

DEBOUNCE_SEC = 10
COALESCE_LIMIT = 50
BUF_SIZE = 64 * 1024
ATLANAN_SONEKLER = (".tmp", ".temp", ".lock", ".swp")

# FILE_NOTIFY_CHANGE_* (toplu izleme filtresi)
IZLE_FILTRE = 0x1 | 0x2 | 0x8 | 0x10 | 0x40


def onemli_mi(path: str) -> bool:
    """Gecici/kilit dosyalar tarama tetiklemez."""
    base = os.path.basename(path)
    if base.startswith("~$"):
        return False
    return not base.lower().endswith(ATLANAN_SONEKLER)


def _altinda(path: str, root: str) -> bool:
    try:
        return os.path.normcase(os.path.commonpath([path, root])) == os.path.normcase(root)
    except ValueError:
        return False


def coalesce(dirs, roots) -> list:
    """Değişen dizinleri üst köklere indirge. Çoksa köklerin tamamı istenir."""
    temiz = sorted({os.path.abspath(d) for d in dirs if os.path.isabs(d)}, key=len)
    koks = [os.path.abspath(r) for r in roots]
    secili = []
    for d in temiz:
        if not any(_altinda(d, r) for r in koks):
            continue
        if not any(_altinda(d, s) for s in secili):
            secili.append(d)
    if len(secili) > COALESCE_LIMIT:
        return sorted(set(koks))
    return secili


def hazir(bekleyen: dict, simdi: float) -> list:
    """Debounce süresi dolan dizinler."""
    return sorted(d for d, son in bekleyen.items() if simdi - son >= DEBOUNCE_SEC)


class Izleyici(threading.Thread):
    """Kök başına izleyici thread. Windows dışında hemen çıkar."""

    def __init__(self, root: str, on_change):
        super().__init__(daemon=True, name=f"izle-{os.path.basename(root) or root}")
        self.root = os.path.abspath(root)
        self._on_change = on_change
        self._dur = threading.Event()
        self._bekleyen = {}
        self._kilit = threading.Lock()

    def bildir(self, yollar, simdi: float | None = None):
        """Olay girişi (gerçek API + test kancası)."""
        if simdi is None:
            simdi = time.monotonic()
        with self._kilit:
            for yol in yollar:
                if onemli_mi(yol):
                    self._bekleyen[os.path.dirname(os.path.abspath(yol))] = simdi

    def bosalt(self, simdi: float | None = None) -> list:
        """Süresi dolanları al ve bildir. Donus: bildirilen dizinler."""
        if simdi is None:
            simdi = time.monotonic()
        with self._kilit:
            due = hazir(self._bekleyen, simdi)
            for d in due:
                del self._bekleyen[d]
        if due:
            self._on_change(coalesce(due, [self.root]))
        return due

    def durdur(self):
        self._dur.set()

    def run(self):
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        # 64-bit'te HANDLE kesilmesin: prototipler şart (yoksa heap bozulur).
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.HANDLE]
        k32.CreateEventW.restype = wintypes.HANDLE
        k32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL,
                                     wintypes.LPCWSTR]
        k32.ReadDirectoryChangesW.restype = wintypes.BOOL
        k32.ReadDirectoryChangesW.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                              wintypes.BOOL, wintypes.DWORD, wintypes.LPDWORD,
                                              ctypes.c_void_p, wintypes.LPVOID]
        k32.GetOverlappedResult.restype = wintypes.BOOL
        k32.GetOverlappedResult.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                            wintypes.LPDWORD, wintypes.BOOL]
        k32.CancelIoEx.restype = wintypes.BOOL
        k32.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.ResetEvent.restype = wintypes.BOOL
        k32.ResetEvent.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.GetLastError.restype = wintypes.DWORD
        while not self._dur.is_set():
            sap = k32.CreateFileW(self.root, 0x0001, 7, None, 3, 0x02000000 | 0x40000000, None)
            if sap == wintypes.HANDLE(-1).value:
                # Kök yok/çevrimdışı (NAS kopuk): bekle, zamanlanmış tarama devrede.
                self._dur.wait(30)
                continue
            try:
                self._dongu(k32, ctypes, wintypes, sap)
            finally:
                k32.CloseHandle(sap)

    def _dongu(self, k32, ctypes, wintypes, sap):
        class _OV(ctypes.Structure):
            _fields_ = [("Internal", ctypes.c_void_p),
                        ("InternalHigh", ctypes.c_void_p),
                        ("Offset", wintypes.DWORD),
                        ("OffsetHigh", wintypes.DWORD),
                        ("hEvent", wintypes.HANDLE)]

        olay = k32.CreateEventW(None, True, False, None)
        try:
            buf = ctypes.create_string_buffer(BUF_SIZE)
            n = wintypes.DWORD()
            while not self._dur.is_set():
                ov = _OV()
                ov.hEvent = olay
                ok = k32.ReadDirectoryChangesW(sap, buf, BUF_SIZE, True, IZLE_FILTRE,
                                               None, ctypes.byref(ov), None)
                if not ok:
                    return  # sap bozuldu; dış döngü yeniden açar
                rc = k32.WaitForSingleObject(olay, 2000)
                if self._dur.is_set():
                    k32.CancelIoEx(sap, ctypes.byref(ov))
                    k32.GetOverlappedResult(sap, ctypes.byref(ov), ctypes.byref(n), True)
                    return
                if rc != 0:  # timeout: bekleyen okumayı iptal edip yeniden ver
                    k32.CancelIoEx(sap, ctypes.byref(ov))
                    k32.GetOverlappedResult(sap, ctypes.byref(ov), ctypes.byref(n), True)
                    k32.ResetEvent(olay)
                    self.bosalt()
                    continue
                if not k32.GetOverlappedResult(sap, ctypes.byref(ov), ctypes.byref(n), False):
                    if k32.GetLastError() == 1022:  # ERROR_NOTIFY_ENUM_DIR: taşma
                        with self._kilit:
                            self._bekleyen.clear()
                        self._on_change([self.root])
                    k32.ResetEvent(olay)
                    continue
                self._coz(buf, n.value)
                k32.ResetEvent(olay)
                self.bosalt()
        finally:
            k32.CloseHandle(olay)

    def _coz(self, buf, n: int):
        off = 0
        yollar = []
        while off + 12 <= n:
            next_off, _eylem, adlen = struct.unpack_from("<III", buf, off)
            if off + 12 + adlen > n:
                break
            try:
                ad = bytes(buf[off + 12:off + 12 + adlen]).decode("utf-16-le")
            except (UnicodeDecodeError, ValueError):
                ad = ""
            if ad:
                yollar.append(os.path.join(self.root, ad))
            if next_off == 0:
                break
            off += next_off
            if off >= n:
                break
        if yollar:
            self.bildir(yollar)
