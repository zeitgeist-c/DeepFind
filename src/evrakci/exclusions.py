"""Hariç kuralları: yeni iş engelle + bekleyen iptal + aktif içerik/FTS/cache temizle."""
from __future__ import annotations

import os
import time

from . import queue as q


def normalize_rule(rule: str) -> str:
    return os.path.normpath(rule.strip())


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def add(con, rule: str) -> str:
    rule = normalize_rule(rule)
    con.execute(
        "INSERT INTO exclusions(rule, created_at) VALUES (?, ?) ON CONFLICT(rule) DO NOTHING",
        (rule, int(time.time())),
    )
    con.commit()
    return rule


def list_rules(con) -> list:
    return [r[0] for r in con.execute("SELECT rule FROM exclusions ORDER BY rule").fetchall()]


def is_excluded(path: str, rules: list) -> bool:
    pl = os.path.normpath(path).lower()
    for r in rules:
        rl = os.path.normpath(r).lower()
        # Kök zaten ayraçla bitiyorsa (C:\, klasör kökü) çift ayraç arama:
        # yalnızca rl + ayraç ile eşleştir.
        if rl.endswith("\\") or rl.endswith("/"):
            if pl == rl or pl.startswith(rl):
                return True
            continue
        if pl == rl or pl.startswith(rl + "\\") or pl.startswith(rl + "/"):
            return True
    return False


def purge_rule(con, rule: str) -> int:
    """Kural kapsamındaki dosyaların aktif içeriğini + bekleyen işlerini sil. Silinen dosya sayısı."""
    rule = normalize_rule(rule)
    esc = _like_escape(rule)
    rows = con.execute(
        "SELECT file_id, path FROM files WHERE lower(path)=lower(?)"
        " OR lower(path) LIKE lower(?) ESCAPE '\\'",
        (rule, esc + "\\\\%"),
    ).fetchall()
    # unix ayraclı varyant da dene
    rows += con.execute(
        "SELECT file_id, path FROM files WHERE lower(path) LIKE lower(?) ESCAPE '\\'",
        (_like_escape(rule) + "/%",),
    ).fetchall()
    seen = set()
    for fid, _p in rows:
        if fid in seen:
            continue
        seen.add(fid)
        con.execute("DELETE FROM segments WHERE file_id=?", (fid,))
        con.execute("DELETE FROM jobs WHERE file_id=?", (fid,))
        con.execute(
            "UPDATE files SET index_status='excluded' WHERE file_id=?", (fid,)
        )
    con.commit()
    q.recover_running(con)
    return len(seen)
