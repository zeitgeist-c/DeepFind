"""Arama gecmisi: 20 sabitlenmemis + 50 sabitli. Kasa kilitliyken erisilmez (A7)."""
from __future__ import annotations

import time

MAX_UNPINNED = 20
MAX_PINNED = 50


def save(con, query: str, filters: str = "") -> None:
    t = int(time.time())
    row = con.execute("SELECT query_id FROM history WHERE query=? AND filters=? AND pinned=0",
                      (query, filters)).fetchone()
    if row:
        con.execute("UPDATE history SET used_at=? WHERE query_id=?", (t, row[0]))
    else:
        con.execute("INSERT INTO history(query, filters, pinned, used_at) VALUES (?,?,0,?)",
                    (query, filters, t))
    # budama: en eski unpinned'ler
    ids = [r[0] for r in con.execute(
        "SELECT query_id FROM history WHERE pinned=0 ORDER BY used_at DESC").fetchall()]
    for old in ids[MAX_UNPINNED:]:
        con.execute("DELETE FROM history WHERE query_id=?", (old,))
    con.commit()


def pin(con, query_id: int) -> bool:
    n = con.execute("SELECT count(*) FROM history WHERE pinned=1").fetchone()[0]
    if n >= MAX_PINNED:
        return False
    con.execute("UPDATE history SET pinned=1 WHERE query_id=?", (query_id,))
    con.commit()
    return True


def list_all(con) -> list:
    return con.execute(
        "SELECT query_id, query, filters, pinned, used_at FROM history"
        " ORDER BY pinned DESC, used_at DESC").fetchall()


def delete(con, query_id: int) -> None:
    con.execute("DELETE FROM history WHERE query_id=?", (query_id,))
    con.commit()


def clear(con, pinned_too: bool = False) -> int:
    cur = con.execute("DELETE FROM history" if pinned_too else "DELETE FROM history WHERE pinned=0")
    con.commit()
    return cur.rowcount
