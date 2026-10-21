"""En kucuk calisan sema (A3). Tam sozlesme plan bolum 12; buyume migration ile.

v9: docs_fts artik KATLANMIS (nz.folded) metin icerir; trigger'lar fold() UDF'i
ile yazar (baglantiya normalize.install ile tanimlanir). segments.folded_text
kolonu ve docs_fts_folded tablosu kaldirildi — her belgede 1 ham kopya + FTS.
"""
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
  INSERT INTO docs_fts(rowid, label, raw_text)
  VALUES (new.seg_id, fold(new.label), fold(new.raw_text));
END;
CREATE TRIGGER IF NOT EXISTS seg_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, label, raw_text)
  VALUES ('delete', old.seg_id, fold(old.label), fold(old.raw_text));
END;
CREATE TABLE IF NOT EXISTS embeddings(
  seg_id INTEGER PRIMARY KEY REFERENCES segments(seg_id) ON DELETE CASCADE,
  model_ver TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vec BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embeddings_ver ON embeddings(model_ver);
"""

SCHEMA_VERSION = "3"

# docs_fts icerigi v9'dan itibaren KATLANMIS; eski (ham indeksli) kasayi ayirt
# etmek icin schema_meta anahtari.
FTS_FOLDED_KEY = "fts_folded"


def needs_folded_rebuild(con) -> bool:
    """Eski (ham icerikli docs_fts) kasada katlanmis indeks henuz kurulmamis mi?"""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
        return False
    marker = con.execute(
        "SELECT v FROM schema_meta WHERE k=?", (FTS_FOLDED_KEY,)).fetchone()
    if marker:
        return False
    # Isaret yoksa ya yeni/bos kasa ya da eski (ham indeksli) kasa.
    return con.execute("SELECT count(*) FROM segments").fetchone()[0] > 0


def mark_folded(con) -> None:
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES (?, '1') "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (FTS_FOLDED_KEY,))


EMBED_VER_KEY = "embed_model_ver"


def mark_embed(con) -> None:
    from . import embed as embed_mod

    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES (?, ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (EMBED_VER_KEY, embed_mod.MODEL_VER),
    )


def _folded_triggers(con) -> None:
    """Trigger'lari fold() yazan v9 surumune degistir (IF NOT EXISTS eski
    govdeyi korudugu icin acik DROP + CREATE)."""
    con.executescript(
        "DROP TRIGGER IF EXISTS seg_ai; DROP TRIGGER IF EXISTS seg_ad;"
        "CREATE TRIGGER seg_ai AFTER INSERT ON segments BEGIN "
        "INSERT INTO docs_fts(rowid, label, raw_text) "
        "VALUES (new.seg_id, fold(new.label), fold(new.raw_text)); END;"
        "CREATE TRIGGER seg_ad AFTER DELETE ON segments BEGIN "
        "INSERT INTO docs_fts(docs_fts, rowid, label, raw_text) "
        "VALUES ('delete', old.seg_id, fold(old.label), fold(old.raw_text)); END;")


def ensure_schema(con) -> None:
    from . import normalize as nz
    nz.install(con)  # trigger calismasi fold() UDF'ine baglidir
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
        version = con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
        if version and int(version[0]) > 9:
            raise RuntimeError("Kasa daha yeni bir sürümle oluşturulmuş; bu sürümle açılamaz.")
    existing = con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
    rebuild = bool(existing and "remove_diacritics 0" not in existing[0])
    if rebuild:
        con.execute("DROP TRIGGER IF EXISTS seg_ai")
        con.execute("DROP TRIGGER IF EXISTS seg_ad")
        con.execute("DROP TABLE docs_fts")
    folded_rebuild = needs_folded_rebuild(con)
    con.executescript(SCHEMA_SQL)
    # Trigger govdesi fold() icermiyorsa (eski kasa) her durumda yenile; bos
    # eski kasada rebuild tetiklenmese de yazma yolu fold'lu olmali.
    trig = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='seg_ai'").fetchone()
    if not trig or "fold(" not in (trig[0] or ""):
        _folded_triggers(con)
    if folded_rebuild:
        # Eski kasa: indeksi katlanmis icerikle bastan kur
        # (rebuild trigger'a girmez; bkz. rebuild_fts).
        rebuild_fts(con)
    elif rebuild:
        rebuild_fts(con)
    if not con.execute("SELECT v FROM schema_meta WHERE k=?", (FTS_FOLDED_KEY,)).fetchone():
        mark_folded(con)
    if not con.execute("SELECT v FROM schema_meta WHERE k=?", (EMBED_VER_KEY,)).fetchone():
        mark_embed(con)
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END",
        (SCHEMA_VERSION,),
    )
    con.commit()


def rebuild_fts(con, progress=None) -> int:
    """Harici-icerik FTS'ini fold() UDF'iyle bastan kurar.

    NOT: FTS5 'rebuild' komutu trigger'lari ATLAR ve icerik tablosundan HAM
    metin okur (v9 kaniti). Bu yuzden delete-all + fold'lu INSERT kullanilir;
    baglanticida fold() tanimli olmali (normalize.install)."""
    from . import normalize as nz
    nz.install(con)
    con.execute('SAVEPOINT rebuild_folded_fts')
    try:
        total = con.execute('SELECT count(*) FROM segments').fetchone()[0]
        if progress: progress('fts', 0, total)
        con.execute("INSERT INTO docs_fts(docs_fts) VALUES('delete-all')")
        last = None
        done = 0
        while True:
            rows = con.execute('SELECT seg_id FROM segments ORDER BY seg_id LIMIT 256').fetchall() if last is None else con.execute(
                'SELECT seg_id FROM segments WHERE seg_id > ? ORDER BY seg_id LIMIT 256', (last,)).fetchall()
            if not rows: break
            end = rows[-1][0]
            if last is None:
                con.execute('INSERT INTO docs_fts(rowid,label,raw_text) SELECT seg_id,fold(label),fold(raw_text) FROM segments WHERE seg_id <= ?', (end,))
            else:
                con.execute('INSERT INTO docs_fts(rowid,label,raw_text) SELECT seg_id,fold(label),fold(raw_text) FROM segments WHERE seg_id > ? AND seg_id <= ?', (last,end))
            last = end
            done += len(rows)
            if progress: progress('fts', done, total)
        if progress: progress('commit', 0, 0)
    except BaseException:
        con.execute('ROLLBACK TO rebuild_folded_fts')
        con.execute('RELEASE rebuild_folded_fts')
        raise
    con.execute('RELEASE rebuild_folded_fts')
    con.commit()
    return done
