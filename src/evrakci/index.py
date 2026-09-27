"""Indeks yazimi: dosya + segment + FTS tek transaction'da. Tek DB yazicisi."""
from __future__ import annotations

import unicodedata

from . import normalize as nz
from .extract import ExtractResult
from .scan import Entry


def index_entry(con, entry: Entry, res: ExtractResult, context: str = "") -> int:
    cur = con.execute("BEGIN IMMEDIATE")
    try:
        con.execute(
            "INSERT INTO files(path, name, ext, size, mtime_ns, source_status, index_status, error_code)"
            " VALUES (?, ?, ?, ?, ?, 'ok', ?, ?)"
            " ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns,"
            " index_status=excluded.index_status, error_code=excluded.error_code",
            (entry.path, entry.name, entry.ext, entry.size, entry.mtime_ns,
             res.status, res.error_code),
        )
        file_id = con.execute("SELECT file_id FROM files WHERE path=?", (entry.path,)).fetchone()[0]
        con.execute("DELETE FROM segments WHERE file_id=?", (file_id,))
        if res.status in ("ok", "partial") and res.segments:
            rows = []
            for s in res.segments:
                raw = unicodedata.normalize("NFC", s.raw_text or "")
                rows.append((file_id, None, s.kind, s.page, s.label, raw, nz.folded(raw)))
            if context.strip():
                cx = unicodedata.normalize("NFC", context.strip())
                rows.append((file_id, None, "context", None, "Konum", cx, nz.folded(cx)))
            con.executemany(
                "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text, folded_text)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        else:
            # Ad/yol her zaman bulunur: icerik yoksa baslik segmenti
            raw = unicodedata.normalize("NFC", entry.name)
            segs = [(file_id, None, "name_only", None, entry.name, raw, nz.folded(raw))]
            if context.strip():
                cx = unicodedata.normalize("NFC", context.strip())
                segs.append((file_id, None, "context", None, "Konum", cx, nz.folded(cx)))
            con.executemany(
                "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text, folded_text)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                segs,
            )
        for y in nz.extract_years(entry.name, context):
            con.execute(
                "INSERT INTO file_years(file_id, year, source, evidence) VALUES (?,?,?,?)"
                " ON CONFLICT(file_id, year) DO NOTHING",
                (file_id, y, "name", entry.name),
            )
        con.execute("COMMIT")
        return file_id
    except Exception:
        con.execute("ROLLBACK")
        raise
