"""Salt-okunur kaynak gezgini. Kaynaga yazma islemi yok: scandir + open('rb') disi yasak."""
from __future__ import annotations

import os
from dataclasses import dataclass

SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information"}
SUPPORTED_EXTS = {".pdf", ".xlsx", ".xls", ".docx", '.jpg', '.jpeg', '.png', '.tif', '.tiff',
                  ".txt", ".md", ".log", ".csv", ".tsv", ".pptx", ".epub", ".eml", ".zip"}
NAME_ONLY_EXTS = {".doc"}  # A3: DOC ad/yol; icerik adaptoru A4 karariyla


@dataclass
class Entry:
    path: str
    name: str
    ext: str
    size: int | None
    mtime_ns: int | None


def walk_ro(root: str):
    """Lazy dizin gezme; symlink izlenmez, klasor disi cikilmaz."""
    root = os.path.abspath(root)
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
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
