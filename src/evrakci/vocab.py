"""Kelime sozlugu: aktif indeksten terim/frekans; fuzzy adaylar sinirli."""
from __future__ import annotations

from . import normalize as nz

SCHEMA_V5_EXTRA = """
CREATE TABLE IF NOT EXISTS vocabulary(term TEXT PRIMARY KEY, freq INTEGER NOT NULL);
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

SCHEMA_VERSION = "5"


def ensure_v5(con) -> None:
    from .migrate import ensure_v4
    ensure_v4(con)
    con.executescript(SCHEMA_V5_EXTRA)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(segments)").fetchall()]
        if "folded_text" not in cols:
            con.execute("ALTER TABLE segments ADD COLUMN folded_text TEXT DEFAULT ''")
    except Exception:
        pass
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts_folded USING fts5("
        "label, raw_text, content='segments', content_rowid='seg_id')"
    )
    con.execute(
        "CREATE TRIGGER IF NOT EXISTS segf_ai AFTER INSERT ON segments BEGIN "
        "INSERT INTO docs_fts_folded(rowid, label, raw_text) "
        "VALUES (new.seg_id, new.label, new.folded_text); END"
    )
    con.execute(
        "CREATE TRIGGER IF NOT EXISTS segf_ad AFTER DELETE ON segments BEGIN "
        "INSERT INTO docs_fts_folded(docs_fts_folded, rowid, label, raw_text) "
        "VALUES ('delete', old.seg_id, old.label, old.folded_text); END"
    )
    # Eski kasanın ilk geçişinde bile tüm içerikleri belleğe alma.
    last_id = 0
    while batch := con.execute(
            "SELECT seg_id, raw_text FROM segments WHERE seg_id>? "
            "AND (folded_text IS NULL OR folded_text='') ORDER BY seg_id LIMIT 100",
            (last_id,)).fetchall():
        for seg_id, raw in batch:
            f = nz.folded(raw or "")
            con.execute("UPDATE segments SET folded_text=? WHERE seg_id=?", (f, seg_id))
            con.execute("INSERT INTO docs_fts_folded(rowid, label, raw_text)"
                        " SELECT seg_id, label, ? FROM segments WHERE seg_id=?", (f, seg_id))
            last_id = seg_id
        con.commit()
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (SCHEMA_VERSION,),
    )
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('normalizer_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (nz.NORMALIZER_VERSION,),
    )
    con.commit()


def rebuild_vocab(con, min_len: int = 2) -> int:
    from collections import Counter
    # Stage in the encrypted database. A crash leaves the prior vocabulary
    # intact; batches keep Python memory bounded for large archives.
    con.execute("CREATE TABLE IF NOT EXISTS vocabulary_build(term TEXT PRIMARY KEY, freq INTEGER NOT NULL)")
    con.execute("DELETE FROM vocabulary_build")
    con.commit()
    for sql in ("SELECT name FROM files", "SELECT folded_text FROM segments"):
        cursor = con.execute(sql)
        while batch := cursor.fetchmany(200):
            counts: Counter = Counter()
            for (value,) in batch:
                counts.update(t for t in nz.tokens_folded(value or "") if len(t) >= min_len)
            con.executemany(
                "INSERT INTO vocabulary_build(term, freq) VALUES (?, ?) "
                "ON CONFLICT(term) DO UPDATE SET freq=freq+excluded.freq",
                counts.items(),
            )
            con.commit()
    count = con.execute("SELECT count(*) FROM vocabulary_build").fetchone()[0]
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("DELETE FROM vocabulary")
        con.execute("INSERT INTO vocabulary(term, freq) SELECT term, freq FROM vocabulary_build")
        con.execute("DELETE FROM vocabulary_build")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return count


def suggest(con, token: str, limit: int = 3) -> list:
    """Token icin sozluk adaylari. Kisa tokenlarda kati esik."""
    from rapidfuzz import process, fuzz
    tok = nz.folded(token)
    if not tok or len(tok) < 2:
        return []
    cutoff = 85 if len(tok) <= 4 else 75
    terms = [r[0] for r in con.execute("SELECT term FROM vocabulary").fetchall()]
    if not terms:
        return []
    out = []
    for cand, score, _ in process.extract(tok, terms, scorer=fuzz.WRatio, limit=limit * 2):
        if score >= cutoff and cand != tok:
            out.append((cand, round(score)))
        if len(out) >= limit:
            break
    return out
