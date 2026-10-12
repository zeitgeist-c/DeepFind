"""Resume/idempotency: ayni imza tekrar kuyruga girmez, kapsam kalicidir."""
import os
import sqlite3

from evrakci import coordinator as C
from evrakci import migrate, queue as q
from evrakci import schema
from evrakci.extract import ExtractResult, Segment
from evrakci.scan import Entry
from evrakci.vocab import ensure_v5


def database(path=None):
    con = sqlite3.connect(str(path) if path else ":memory:")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    return con


def _entry(path, size=10, mtime_ns=1000):
    name = os.path.basename(path)
    return Entry(path, name, os.path.splitext(name)[1].lower(), size, mtime_ns)


def test_scan_selected_survives_reconnect(tmp_path):
    db = tmp_path / "kasa.db"
    con = database(db)
    con.execute("INSERT OR IGNORE INTO scan_selected VALUES (7)")
    con.commit()
    con.close()
    con2 = database(db)  # ensure_current tekrar kosar (idempotent olmali)
    try:
        assert con2.execute("SELECT count(*) FROM scan_selected").fetchone()[0] == 1
    finally:
        con2.close()


def test_same_signature_not_requeued(tmp_path):
    con = database(tmp_path / "kasa.db")
    try:
        entry = _entry("C:/arsiv/a.pdf")
        assert C.note_discovered(con, entry) == "queued"
        fid = con.execute("SELECT file_id FROM files WHERE path=?", (entry.path,)).fetchone()[0]
        sig = q.signature_of(entry.size, entry.mtime_ns)
        C.write_revision(con, fid, sig,
                         ExtractResult([Segment("pdf_page", 1, "Sayfa 1", "tahsilat makbuzu")]), "")
        jid = con.execute("SELECT job_id FROM jobs").fetchone()[0]
        q.complete(con, jid)
        assert C.note_discovered(con, entry) == "skipped"
        assert q.pending_count(con) == 0
    finally:
        con.close()


def test_changed_signature_requeued(tmp_path):
    con = database(tmp_path / "kasa.db")
    try:
        entry = _entry("C:/arsiv/a.pdf", size=10, mtime_ns=1000)
        assert C.note_discovered(con, entry) == "queued"
        fid = con.execute("SELECT file_id FROM files WHERE path=?", (entry.path,)).fetchone()[0]
        sig = q.signature_of(entry.size, entry.mtime_ns)
        C.write_revision(con, fid, sig,
                         ExtractResult([Segment("pdf_page", 1, "Sayfa 1", "tahsilat makbuzu")]), "")
        jid = con.execute("SELECT job_id FROM jobs").fetchone()[0]
        q.complete(con, jid)
        changed = _entry("C:/arsiv/a.pdf", size=11, mtime_ns=1000)
        assert C.note_discovered(con, changed) == "queued"
        assert q.pending_count(con) == 1
    finally:
        con.close()
