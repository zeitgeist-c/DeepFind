"""Sema v4: kalici is kuyrugu, revizyonlar, tarama kapsami, haricler. Ileriye donuk migration."""
from __future__ import annotations

import time

SCHEMA_V4_SQL = """
CREATE TABLE IF NOT EXISTS file_revisions(
  rev_id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
  signature TEXT NOT NULL,
  extractor TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS jobs(
  job_id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
  signature TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'extract',
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  not_before INTEGER NOT NULL DEFAULT 0,
  lease_until INTEGER NOT NULL DEFAULT 0,
  error_code TEXT,
  UNIQUE(file_id, signature, kind)
);
CREATE TABLE IF NOT EXISTS scan_runs(
  run_id INTEGER PRIMARY KEY,
  root TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  finished_at INTEGER,
  result TEXT
);
CREATE TABLE IF NOT EXISTS scan_scopes(
  run_id INTEGER NOT NULL REFERENCES scan_runs(run_id) ON DELETE CASCADE,
  dir TEXT NOT NULL,
  complete INTEGER NOT NULL DEFAULT 0,
  UNIQUE(run_id, dir)
);
CREATE TABLE IF NOT EXISTS exclusions(
  rule TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL
);
"""

SCHEMA_VERSION = "4"
EXTRACTOR_VERSION = "archive-034"
OCR_VERSION = "rapid-2"  # Entirely blank pages are successful coverage, not NO_TEXT.


SCHEMA_V5_EXTRA = """
CREATE TABLE IF NOT EXISTS file_hashes(
  file_id INTEGER PRIMARY KEY REFERENCES files(file_id) ON DELETE CASCADE,
  signature TEXT NOT NULL,
  sha256 TEXT,
  hash_status TEXT NOT NULL DEFAULT 'pending',
  verified_at INTEGER
);
CREATE TABLE IF NOT EXISTS history(
  query_id INTEGER PRIMARY KEY,
  query TEXT NOT NULL,
  filters TEXT NOT NULL DEFAULT '',
  pinned INTEGER NOT NULL DEFAULT 0,
  used_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS file_years(
  file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
  year TEXT NOT NULL,
  source TEXT NOT NULL,
  evidence TEXT,
  UNIQUE(file_id, year)
);
"""


def ensure_v5(con):
    ensure_v4(con)
    con.executescript(SCHEMA_V5_EXTRA)
    con.commit()


def ensure_v6(con) -> None:
    """OCR metadata: segment duzeyinde yontem + guven (hata/durum degil, yontem bilgisi)."""
    ensure_v4(con)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(segments)").fetchall()]
        if "method" not in cols:
            con.execute("ALTER TABLE segments ADD COLUMN method TEXT DEFAULT ''")
        if "confidence" not in cols:
            con.execute("ALTER TABLE segments ADD COLUMN confidence REAL")
    except Exception:
        pass
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END",
        ("6",),
    )
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('ocr_version', ?) "
        "ON CONFLICT(k) DO NOTHING",
        (OCR_VERSION,),
    )
    con.commit()


SCHEMA_V7_SQL = """
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS roots(
  root_id INTEGER PRIMARY KEY,
  display_path TEXT NOT NULL,
  canonical_path TEXT NOT NULL UNIQUE,
  company_rule TEXT NOT NULL DEFAULT 'belirlenemiyor',
  enabled INTEGER NOT NULL DEFAULT 1
);
"""


def ensure_v7(con) -> None:
    """Ayarlar + kok kayitlari (A7). Idempotent."""
    ensure_v6(con)
    con.executescript(SCHEMA_V7_SQL)
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END",
        ("7",),
    )
    con.commit()


SCAN_RUN_COLUMNS = {
    "updated_at": "INTEGER",
    "stage": "TEXT",
    "found": "INTEGER NOT NULL DEFAULT 0",
    "done": "INTEGER NOT NULL DEFAULT 0",
    "pending": "INTEGER NOT NULL DEFAULT 0",
    "failed": "INTEGER NOT NULL DEFAULT 0",
    "ocr_done": "INTEGER NOT NULL DEFAULT 0",
    "ocr_failed": "INTEGER NOT NULL DEFAULT 0",
    "error_code": "TEXT",
}


def ensure_v8(con) -> None:
    """Add encrypted scan checkpoints without replacing existing file/job records."""
    version = con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
    if version and int(version[0]) >= 8:
        return
    if not version or int(version[0]) < 7:
        ensure_v7(con)
    columns = {row[1] for row in con.execute("PRAGMA table_info(scan_runs)")}
    for name, definition in SCAN_RUN_COLUMNS.items():
        if name not in columns:
            con.execute(f"ALTER TABLE scan_runs ADD COLUMN {name} {definition}")
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', '8') "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END"
    )
    con.commit()


def ensure_current(con, progress=None) -> None:
    """Prepare metadata and migrate directly to vector-only schema v10."""
    from . import schema
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v8(con)
    ensure_archive(con)
    ensure_v10(con, progress=progress)
    con.execute("DELETE FROM settings WHERE k IN ('gemini_api_key','ai_model')")
    con.commit()


def ensure_archive(con):
    """Additive archive capabilities; existing index and version remain readable."""
    for table, definitions in {
        'segments': {'start_offset': 'INTEGER NOT NULL DEFAULT 0', 'end_offset': 'INTEGER NOT NULL DEFAULT 0'},
        'jobs': {'cursor': 'INTEGER NOT NULL DEFAULT 0'},
        'files': {'coverage': "TEXT NOT NULL DEFAULT ''"},
    }.items():
        cols = {r[1] for r in con.execute(f'PRAGMA table_info({table})')}
        for col, definition in definitions.items():
            if col not in cols:
                con.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')
    con.executescript('''CREATE TABLE IF NOT EXISTS extraction_stage(
        file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE, signature TEXT,
        position INTEGER, kind TEXT, page INTEGER, label TEXT, raw_text TEXT,
        PRIMARY KEY(file_id,signature,position));
        CREATE TABLE IF NOT EXISTS scan_selected(file_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS saved_searches(
        name TEXT PRIMARY KEY, query TEXT NOT NULL, year TEXT, ext TEXT, folder TEXT);
        CREATE TABLE IF NOT EXISTS file_tags(
        file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
        tag TEXT NOT NULL, auto INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(file_id, tag));
        CREATE TABLE IF NOT EXISTS tag_rules(
        rule_id INTEGER PRIMARY KEY, tag TEXT NOT NULL, keywords TEXT NOT NULL,
        mode TEXT NOT NULL DEFAULT 'any');
        CREATE TABLE IF NOT EXISTS scan_manifest(
        run_id INTEGER NOT NULL REFERENCES scan_runs(run_id) ON DELETE CASCADE,
        file_id INTEGER NOT NULL, size INTEGER, mtime_ns INTEGER,
        PRIMARY KEY(run_id, file_id));
        CREATE TABLE IF NOT EXISTS scan_errors(
        run_id INTEGER REFERENCES scan_runs(run_id) ON DELETE CASCADE,
        path TEXT, error_code TEXT, PRIMARY KEY(run_id,path));
        CREATE TABLE IF NOT EXISTS ocr_coverage(
        file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE, rev_id INTEGER,
        page INTEGER, outcome TEXT, error_code TEXT, PRIMARY KEY(file_id,rev_id,page));
        CREATE INDEX IF NOT EXISTS segments_file ON segments(file_id,seg_id);
        CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(status,kind,not_before);
        CREATE INDEX IF NOT EXISTS files_path_status ON files(index_status,path);''')
    con.execute("INSERT INTO schema_meta(k,v) VALUES('archive_version','034') ON CONFLICT(k) DO UPDATE SET v=excluded.v")
    if 'start_offset' not in {r[1] for r in con.execute('PRAGMA table_info(extraction_stage)')}:
        con.execute('ALTER TABLE extraction_stage ADD COLUMN start_offset INTEGER NOT NULL DEFAULT 0')
    con.commit()


def sqlite_supports_drop_column(con) -> bool:
    ver = tuple(int(p) for p in con.execute("SELECT sqlite_version()").fetchone()[0].split(".")[:2])
    return ver >= (3, 35)


def ensure_v10(con, progress=None):
    """Remove derived lexical objects without re-tokenizing document text.

    Startup never runs VACUUM: freed pages are reused by future vectors.
    """
    row=con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
    obsolete = con.execute("SELECT 1 FROM sqlite_master WHERE name IN "
        "('docs_fts','docs_fts_folded','vocabulary','vocabulary_build') "
        "OR (type='trigger' AND (name IN ('seg_ai','seg_ad','segf_ai','segf_ad') OR name GLOB 'vocab_*')) LIMIT 1").fetchone()
    if row and int(row[0]) >= 10 and not obsolete:
        return
    con.execute('SAVEPOINT semantic_only')
    try:
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
            if name in ('seg_ai','seg_ad','segf_ai','segf_ad') or name.startswith('vocab_'):
                con.execute('DROP TRIGGER "'+name.replace('"','""')+'"')
        for name in ('docs_fts','docs_fts_folded','vocabulary','vocabulary_build'):
            con.execute('DROP TABLE IF EXISTS '+name)
        cols={r[1] for r in con.execute('PRAGMA table_info(segments)')}
        if 'folded_text' in cols:
            con.execute('ALTER TABLE segments DROP COLUMN folded_text')
        con.execute("DELETE FROM schema_meta WHERE k='fts_folded' OR k LIKE 'vocabulary_%'")
        con.execute("INSERT INTO schema_meta(k,v) VALUES ('schema_version','10') ON CONFLICT(k) DO UPDATE SET v=excluded.v")
    except BaseException:
        con.execute('ROLLBACK TO semantic_only');con.execute('RELEASE semantic_only')
        raise
    con.execute('RELEASE semantic_only')
    con.commit()


def recover_scan_runs(con) -> int:
    """Mark a previous unclosed run as interrupted on next application start."""
    cur = con.execute(
        "UPDATE scan_runs SET result='interrupted', finished_at=?, "
        "error_code='UNEXPECTED_EXIT' WHERE finished_at IS NULL",
        (int(time.time()),),
    )
    con.commit()
    return cur.rowcount


def get_setting(con, k: str, default: str = "") -> str:
    r = con.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return r[0] if r else default


def set_setting(con, k: str, v: str) -> None:
    con.execute("INSERT INTO settings(k, v) VALUES (?, ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    con.commit()


def ensure_v4(con) -> None:
    con.executescript(SCHEMA_V4_SQL)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(segments)").fetchall()]
        if "rev_id" not in cols:
            con.execute("ALTER TABLE segments ADD COLUMN rev_id INTEGER")
    except Exception:
        pass
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END",
        (SCHEMA_VERSION,),
    )
    con.commit()
