"""Encrypted document text, source mappings and embeddings; no keyword index."""
EMBEDDING_TABLE_SQL = """CREATE TABLE IF NOT EXISTS embeddings(
  seg_id INTEGER PRIMARY KEY REFERENCES segments(seg_id) ON DELETE CASCADE,
  model_ver TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vec BLOB NOT NULL
)"""
EMBEDDING_INDEX_SQL = 'CREATE INDEX IF NOT EXISTS idx_embeddings_ver ON embeddings(model_ver)'

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
"""
SCHEMA_SQL += EMBEDDING_TABLE_SQL + ";" + EMBEDDING_INDEX_SQL + ";"

SCHEMA_VERSION = "3"
EMBED_VER_KEY = "embed_model_ver"

def ensure_embeddings(con):
    con.execute(EMBEDDING_TABLE_SQL)
    con.execute(EMBEDDING_INDEX_SQL)

def mark_embed(con):
    from . import embed
    con.execute("INSERT INTO schema_meta(k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (EMBED_VER_KEY,embed.MODEL_VER))

def ensure_schema(con):
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
        row=con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()
        if row and int(row[0])>10:
            raise RuntimeError("Kasa daha yeni bir sürümle oluşturulmuş; bu sürümle açılamaz.")
    con.executescript(SCHEMA_SQL)
    if not con.execute("SELECT 1 FROM schema_meta WHERE k=?",(EMBED_VER_KEY,)).fetchone():
        mark_embed(con)
    con.execute("INSERT INTO schema_meta(k,v) VALUES ('schema_version','3') ON CONFLICT(k) DO NOTHING")
    con.commit()
