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
EXTRACTOR_VERSION = "a4-2"
OCR_VERSION = "a6-1"


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
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        ("6",),
    )
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('ocr_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
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
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
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
    if not version or int(version[0]) < 7:
        ensure_v7(con)
    columns = {row[1] for row in con.execute("PRAGMA table_info(scan_runs)")}
    for name, definition in SCAN_RUN_COLUMNS.items():
        if name not in columns:
            con.execute(f"ALTER TABLE scan_runs ADD COLUMN {name} {definition}")
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', '8') "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v"
    )
    con.commit()


def ensure_current(con) -> None:
    """Run the legacy backfill only for vaults that have not completed it."""
    from . import schema
    from . import normalize
    from .vocab import ensure_v5

    version = None
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
        row = con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
        version = int(row[0]) if row else None
    if version is not None and version > 8:
        raise RuntimeError("Kasa daha yeni bir sürümle oluşturulmuş; bu sürümle açılamaz.")
    if version is not None and version < 7:
        # Older startup paths wrote a lower version during their idempotent
        # checks. The completed v5 marker plus v7 tables prove no backfill is
        # needed, even if a previous launch stopped after rewriting the marker.
        marker = con.execute("SELECT v FROM schema_meta WHERE k='normalizer_version'").fetchone()
        tables = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE name IN "
            "('roots','settings','docs_fts_folded','jobs','vocabulary')"
        )}
        if (marker and marker[0] == normalize.NORMALIZER_VERSION and
                {'roots', 'settings', 'docs_fts_folded', 'jobs', 'vocabulary'} <= tables and
                'folded_text' in {row[1] for row in con.execute("PRAGMA table_info(segments)")}):
            con.execute("UPDATE schema_meta SET v='7' WHERE k='schema_version'")
            con.commit()
            version = 7
    if version is None or version < 7:
        schema.ensure_schema(con)
        ensure_v5(con)
    ensure_v8(con)


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
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (SCHEMA_VERSION,),
    )
    con.commit()
