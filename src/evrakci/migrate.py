"""Sema v4: kalici is kuyrugu, revizyonlar, tarama kapsami, haricler. Ileriye donuk migration."""
from __future__ import annotations

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
