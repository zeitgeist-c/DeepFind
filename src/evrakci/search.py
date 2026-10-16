"""Guvenli FTS sorgusu: kullanici metni SQL/FTS dili olarak calismaz.

v9: docs_fts katlanmis icerik tasidigi icin v1 arama terimleri de katlanir."""
from __future__ import annotations

import re

from . import normalize as nz


def build_match(query: str) -> str | None:
    toks = re.findall(r'"[^"]+"|\S+', query.strip())
    parts = []
    for t in toks:
        if t.startswith('"') and t.endswith('"') and len(t) >= 2:
            inner = t[1:-1].replace('"', '""')
            if inner.strip():
                parts.append(f'"{nz.folded(inner)}"')
        else:
            clean = t.replace('"', "")
            if clean:
                parts.append(f'"{nz.folded(clean)}"')
    return " ".join(parts) if parts else None


def search(con, query: str, limit: int = 50):
    match = build_match(query)
    if not match:
        return []
    rows = con.execute(
        "SELECT f.path, f.name, f.ext, s.label, s.page,"
        " snippet(docs_fts, 1, '<b>', '</b>', ' … ', 24) AS snip"
        " FROM docs_fts"
        " JOIN segments s ON s.seg_id = docs_fts.rowid"
        " JOIN files f ON f.file_id = s.file_id"
        " WHERE docs_fts MATCH ? AND f.index_status NOT IN ('missing','excluded','pending') LIMIT ?",
        (match, limit),
    ).fetchall()
    return [
        {"path": r[0], "name": r[1], "ext": r[2], "label": r[3], "page": r[4], "snippet": r[5]}
        for r in rows
    ]
