"""Kelime sozlugu: aktif indeksten terim/frekans; fuzzy adaylar sinirli."""
from __future__ import annotations

from . import normalize as nz
from threading import RLock
_cache = {}
_cache_lock = RLock()

def clear_cache():
    with _cache_lock:
        _cache.clear()

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
    # v9: folded_text kolonu ve docs_fts_folded artik yok — docs_fts trigger
    # uzerinden fold() UDF'i ile katlanmis icerik tasiyor (migrate.ensure_v9).
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('schema_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=CASE WHEN CAST(schema_meta.v AS INTEGER) < CAST(excluded.v AS INTEGER) THEN excluded.v ELSE schema_meta.v END",
        (SCHEMA_VERSION,),
    )
    con.execute(
        "INSERT INTO schema_meta(k, v) VALUES ('normalizer_version', ?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (nz.NORMALIZER_VERSION,),
    )
    con.commit()


def rebuild_vocab(con, min_len: int = 2, *, transactional: bool = False) -> int:
    from collections import Counter
    if transactional and not con.in_transaction:
        raise RuntimeError("transactional vocabulary rebuild requires an active transaction")
    # Stage in the encrypted database. A crash leaves the prior vocabulary
    # intact; batches keep Python memory bounded for large archives.
    con.execute("CREATE TABLE IF NOT EXISTS vocabulary_build(term TEXT PRIMARY KEY, freq INTEGER NOT NULL)")
    con.execute("DELETE FROM vocabulary_build")
    if not transactional:
        con.commit()
    for sql in ("SELECT name FROM files", "SELECT raw_text FROM segments"):
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
            if not transactional:
                con.commit()
    count = con.execute("SELECT count(*) FROM vocabulary_build").fetchone()[0]
    if not transactional:
        con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("DELETE FROM vocabulary")
        con.execute("INSERT INTO vocabulary(term, freq) SELECT term, freq FROM vocabulary_build")
        con.execute("DELETE FROM vocabulary_build")
        con.execute("INSERT INTO schema_meta(k,v) VALUES ('vocabulary_generation','1') ON CONFLICT(k) DO UPDATE SET v=CAST(v AS INTEGER)+1")
        if not transactional:
            con.execute("COMMIT")
    except Exception:
        if not transactional:
            con.execute("ROLLBACK")
        raise
    return count


def remove_files_from_vocab(con, file_ids, *, include_names: bool = True, min_len: int = 2) -> int:
    """Remove indexed term frequencies for files being deleted or content-excluded.

    Caller owns transaction; this helper never commits.
    """
    from collections import Counter
    ids = list(dict.fromkeys(file_ids))
    if not ids:
        return 0
    con.execute("CREATE TEMP TABLE IF NOT EXISTS evrakci_vocab_remove(file_id INTEGER PRIMARY KEY)")
    con.execute("DELETE FROM temp.evrakci_vocab_remove")
    for start in range(0, len(ids), 500):
        con.executemany("INSERT INTO temp.evrakci_vocab_remove(file_id) VALUES (?)",
                        ((fid,) for fid in ids[start:start + 500]))
    counts: Counter = Counter()
    queries = []
    if include_names:
        queries.append("SELECT f.name FROM files f JOIN temp.evrakci_vocab_remove r USING(file_id)")
    queries.append("SELECT s.raw_text FROM segments s JOIN temp.evrakci_vocab_remove r USING(file_id)")
    for sql in queries:
        cursor = con.execute(sql)
        while batch := cursor.fetchmany(200):
            for (value,) in batch:
                counts.update(t for t in nz.tokens_folded(value or "") if len(t) >= min_len)
    con.executemany("UPDATE vocabulary SET freq=freq-? WHERE term=?",
                    ((freq, term) for term, freq in counts.items()))
    con.execute("DELETE FROM vocabulary WHERE freq<=0")
    con.execute(
        "INSERT INTO schema_meta(k,v) VALUES ('vocabulary_generation','1') "
        "ON CONFLICT(k) DO UPDATE SET v=CAST(v AS INTEGER)+1"
    )
    return len(ids)


def suggest(con, token: str, limit: int = 3) -> list:
    """Token icin sozluk adaylari. Kisa tokenlarda kati esik."""
    from rapidfuzz import process, fuzz
    tok = nz.folded(token)
    if not tok or len(tok) < 2:
        return []
    cutoff = 85 if len(tok) <= 4 else 75
    path = con.execute('PRAGMA database_list').fetchone()[2]
    generation = con.execute("SELECT v FROM schema_meta WHERE k='vocabulary_generation'").fetchone()
    key = (path or id(con), generation[0] if generation else '0')
    with _cache_lock:
        terms = _cache.get(key)
    if terms is None:
        terms = tuple(r[0] for r in con.execute('SELECT term FROM vocabulary'))
        with _cache_lock:
            if len(_cache) >= 4:
                _cache.clear()
            _cache[key] = terms
    if not terms:
        return []
    out = []
    for cand, score, _ in process.extract(tok, terms, scorer=fuzz.WRatio, limit=limit * 2):
        if score >= cutoff and cand != tok:
            out.append((cand, round(score)))
        if len(out) >= limit:
            break
    return out
