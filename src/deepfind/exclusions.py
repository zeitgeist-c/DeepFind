"""Exclusion rules: block new jobs; purge pending jobs, texts and vectors."""
from __future__ import annotations

import os
import time

from . import job_queue as q


def normalize_rule(rule: str) -> str:
    return os.path.normpath(rule.strip())


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def add(con, rule: str, *, commit=True) -> str:
    rule = normalize_rule(rule)
    con.execute(
        "INSERT INTO exclusions(rule, created_at) VALUES (?, ?) ON CONFLICT(rule) DO NOTHING",
        (rule, int(time.time())),
    )
    if commit:
        con.commit()
    return rule


def list_rules(con) -> list:
    return [r[0] for r in con.execute("SELECT rule FROM exclusions ORDER BY rule").fetchall()]


def is_excluded(path: str, rules: list) -> bool:
    pl = os.path.normpath(path).lower()
    for r in rules:
        rl = os.path.normpath(r).lower()
        # When the root already ends with a separator (C:\, folder root), double-separator search:
        # match with rl + separator only.
        if rl.endswith("\\") or rl.endswith("/"):
            if pl == rl or pl.startswith(rl):
                return True
            continue
        if pl == rl or pl.startswith(rl + "\\") or pl.startswith(rl + "/"):
            return True
    return False


def purge_rule(con, rule: str, *, commit=True) -> int:
    """Delete the active content + pending jobs of files in the rule's scope. Deleted file count."""
    rule = normalize_rule(rule)
    # SQL LIKE narrows candidates. Strip trailing separators before appending
    # both separator variants; otherwise C:\ becomes a double-separator pattern.
    base = rule.rstrip("\\/")
    prefixes = (base + "\\", base + "/")
    if not base:
        prefixes = ("\\", "/")
    conditions = ["lower(path)=lower(?)"]
    params = [rule]
    for prefix in prefixes:
        conditions.append("lower(path) LIKE lower(?) ESCAPE '\\'")
        params.append(_like_escape(prefix) + "%")
    # SQLite lower() is ASCII-only. Use Python's Unicode-aware path comparison
    # when rule contains non-ASCII characters, so differently-cased paths aren't missed.
    if rule.isascii():
        sql = "SELECT file_id, path FROM files WHERE " + " OR ".join(conditions)
        cursor = con.execute(sql, params)
    else:
        cursor = con.execute("SELECT file_id, path FROM files")
    ids = []
    while batch := cursor.fetchmany(1000):
        for fid, path in batch:
            if is_excluded(path, [rule]):
                ids.append(fid)
    if ids:
        for fid in ids:
            con.execute("DELETE FROM segments WHERE file_id=?", (fid,))
            con.execute("DELETE FROM jobs WHERE file_id=?", (fid,))
            con.execute("UPDATE files SET index_status='excluded' WHERE file_id=?", (fid,))
    if commit:
        con.commit()
    q.recover_running(con, commit=commit)
    return len(ids)


def add_and_purge(con, rule: str) -> tuple[str, int]:
    """Persist exclusion rule and purge indexed content atomically."""
    con.execute("BEGIN IMMEDIATE")
    try:
        normalized = add(con, rule, commit=False)
        count = purge_rule(con, normalized, commit=False)
        con.commit()
        return normalized, count
    except Exception:
        con.rollback()
        raise
