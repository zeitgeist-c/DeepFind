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
    if version is not None and version > 9:
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
    ensure_archive(con)
    ensure_v9(con)

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


def ensure_v9(con) -> None:
    """v9: tek katlanmis FTS. docs_fts trigger'lari fold() UDF'i ile katlanmis
    metin yazar; `segments.folded_text` kolonu ve `docs_fts_folded` tablosu
    kaldirilir (her belgede 1 ham kopya + tek FTS — ~8-9 GB kazanc).

    Idempotent; startup.open_vault akisi migration oncesi otomatik yedek alir.
    VACUUM burada degil, ayrica (sadece kapanista / CLI) — buyuk kasada dakikalar.
    """
    from . import normalize as nz
    from . import schema as schema_mod
    nz.install(con)  # fold() olmadan trigger/rebuild yanlis ya da hataya duser
    version_row = con.execute(
        "SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
    version = int(version_row[0]) if version_row else 0
    cols = {r[1] for r in con.execute("PRAGMA table_info(segments)")}
    has_folded_col = "folded_text" in cols
    has_folded_fts = bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE name='docs_fts_folded'").fetchone())
    needs_marker = not con.execute(
        "SELECT v FROM schema_meta WHERE k=?", (schema_mod.FTS_FOLDED_KEY,)).fetchone()

    if version >= 9 and not has_folded_col and not has_folded_fts and not needs_marker:
        return  # zaten v9

    # 1) docs_fts_folded yardimci tablo + trigger'larini kaldir (shadow tablolar
    #    FTS5 tarafindan otomatik duser).
    con.execute("DROP TRIGGER IF EXISTS segf_ai")
    con.execute("DROP TRIGGER IF EXISTS segf_ad")
    if has_folded_fts:
        con.execute("DROP TABLE IF EXISTS docs_fts_folded")

    # 2) Trigger'lari fold() yazan v9 govdesine cevir.
    schema_mod._folded_triggers(con)

    # 3) Katlanmis indeksi bastan kur (rebuild trigger'a girmez; bkz. rebuild_fts).
    if needs_marker or version < 9:
        schema_mod.rebuild_fts(con)
    schema_mod.mark_folded(con)

    # 4) folded_text kolonunu dusur (SQLite >= 3.35; sqlcipher3 3.51 destekli).
    if has_folded_col:
        if sqlite_supports_drop_column(con):
            con.execute("ALTER TABLE segments DROP COLUMN folded_text")
        # Desteklenmiyorsa kolon bos/okunmaz kalir; boyut VACUUM'da serbest kalir.

    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', '9') "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v")
    # Eski tamamlanmis taramalarin kapsam kayitlari bos yer kaplar (~0,25 GB);
    # surebilen (finished_at NULL) taramalarin kapsami resume icin kalmali.
    con.execute("DELETE FROM scan_scopes WHERE run_id IN "
                "(SELECT run_id FROM scan_runs WHERE finished_at IS NOT NULL)")
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
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (SCHEMA_VERSION,),
    )
    con.commit()
