"""En kucuk calisan sema (A3). Tam sozlesme plan bolum 12; buyume migration ile."""
from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS files(
  file_id INTEGER PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  ext TEXT NOT NULL,
  size INTEGER,
  mtime_ns INTEGER,
  source_status TEXT DEFAULT 'ok',
  index_status TEXT DEFAULT 'pending',
  error_code TEXT
);
CREATE TABLE IF NOT EXISTS segments(
  seg_id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  page INTEGER,
  label TEXT NOT NULL,
  raw_text TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  label, raw_text, content='segments', content_rowid='seg_id', tokenize='unicode61 remove_diacritics 0'
);
CREATE TRIGGER IF NOT EXISTS seg_ai AFTER INSERT ON segments BEGIN
  INSERT INTO docs_fts(rowid, label, raw_text) VALUES (new.seg_id, new.label, new.raw_text);
END;
CREATE TRIGGER IF NOT EXISTS seg_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, label, raw_text)
  VALUES ('delete', old.seg_id, old.label, old.raw_text);
END;
"""

SCHEMA_VERSION = "3"


def ensure_schema(con) -> None:
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
        version = con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
        if version and int(version[0]) > 8:
            raise RuntimeError("Kasa daha yeni bir sürümle oluşturulmuş; bu sürümle açılamaz.")
    existing = con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
    rebuild = bool(existing and "remove_diacritics 0" not in existing[0])
    if rebuild:
        con.execute("DROP TRIGGER IF EXISTS seg_ai")
        con.execute("DROP TRIGGER IF EXISTS seg_ad")
        con.execute("DROP TABLE docs_fts")
    con.executescript(SCHEMA_SQL)
    if rebuild:
        con.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (SCHEMA_VERSION,),
    )
    con.commit()


def rebuild_fts(con) -> int:
    con.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
    con.commit()
    return con.execute("SELECT count(*) FROM docs_fts").fetchone()[0]
