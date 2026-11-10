"""Salt-okunur kaynak gezgini. Kaynaga yazma islemi yok: scandir + open('rb') disi yasak."""
from __future__ import annotations

import os
from dataclasses import dataclass

SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information"}
SUPPORTED_EXTS = {".pdf", ".xlsx", ".xls", ".docx", '.jpg', '.jpeg', '.png', '.tif', '.tiff',
                  ".txt", ".md", ".log", ".csv", ".tsv", ".pptx", ".epub", ".eml", ".zip"}
NAME_ONLY_EXTS = {".doc"}  # A3: DOC ad/yol; icerik adaptoru A4 karariyla

# Tarama ekranindaki dosya turu secimi: bugunku kapsam = hepsi isaretli.
# Eski profillerde ayar yoktur ve bugunku kapsamla devam eder (None).
TUM_TURLER = sorted(SUPPORTED_EXTS | NAME_ONLY_EXTS)
TUR_AYARI = "tarama_turleri"


def secili_turler(con) -> set | None:
    """Kullanicinin tarama turu secimi; None = ayar yok, bugunku kapsam."""
    try:
        ham = con.execute("SELECT v FROM settings WHERE k=?", (TUR_AYARI,)).fetchone()
    except Exception:
        return None
    if ham is None:
        return None
    return {p for p in (x.strip().lower() for x in (ham[0] or "").split(",")) if p in TUM_TURLER}


def turleri_kaydet(con, turler: set) -> None:
    """Secimi kalici yaz; yeniden acilista korunur. Bos kumede sinirliyken tarama baslamaz."""
    from . import migrate as _migrate
    _migrate.set_setting(con, TUR_AYARI, ",".join(sorted(set(turler) & set(TUM_TURLER))))


def aktif_turler(con) -> set:
    """Bu taramada isleme alinacak turler (varsayilan: hepsi)."""
    secili = secili_turler(con)
    return set(TUM_TURLER) if secili is None else secili


def baslatma_engeli(con) -> str | None:
    """Hic tur secilmediyse tarama baslamaz; donus: kullaniciya gosterilecek neden."""
    if secili_turler(con) == set():
        return ("Hiç dosya türü seçili değil. Taramayı başlatmak için "
                "Tarama ekranından en az bir türü işaretleyin.")
    return None


@dataclass
class Entry:
    path: str
    name: str
    ext: str
    size: int | None
    mtime_ns: int | None


def _tasma_mi(e) -> bool:
    """Junction/symlink gibi secili kok disina tasiyabilecek baglar."""
    try:
        if e.is_symlink():
            return True
    except OSError:
        return True
    try:
        return bool(e.stat(follow_symlinks=False).st_file_attributes & 0x400)
    except (OSError, AttributeError):
        return False


def walk_ro(root: str):
    """Lazy dizin gezme; symlink/junction izlenmez, klasor disi cikilmaz."""
    root = os.path.abspath(root)
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if _tasma_mi(e):
                            continue  # Secili kok disina sessizce tasma.
                        if e.is_dir(follow_symlinks=False):
                            if e.name in SKIP_DIRS or e.name.startswith("~$"):
                                continue
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            if e.name.startswith("~$"):
                                continue
                            st = e.stat(follow_symlinks=False)
                            ext = os.path.splitext(e.name)[1].lower()
                            yield Entry(e.path, e.name, ext, st.st_size, st.st_mtime_ns)
                    except OSError:
                        continue
        except OSError:
            continue
