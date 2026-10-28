"""Birebir kopya: tam dosya SHA-256, mevcut surumde dogrulanmis. Arka plan isi."""
from __future__ import annotations

import hashlib
import os
import time

BUF = 1024 * 1024


def file_sha256(path: str, stop=None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            if stop and stop():
                raise InterruptedError()
            b = f.read(BUF)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify_pending(con, limit: int = 50, *, scoped=False, stop=None) -> dict:
    """Aktif imzali dosyalarin hash'ini cikar/dogrula. Donus: sayilar."""
    from . import job_queue as q
    out = {"verified": 0, "skipped": 0}
    scope = " AND f.file_id IN (SELECT file_id FROM scan_selected)" if scoped else ""
    rows = con.execute(
        "SELECT f.file_id, f.path, f.size, f.mtime_ns, r.signature"
        " FROM files f JOIN file_revisions r ON r.file_id=f.file_id AND r.active=1"
        " LEFT JOIN file_hashes h ON h.file_id=f.file_id AND h.signature=r.signature"
        " WHERE h.sha256 IS NULL" + scope + " LIMIT ?", (limit,)).fetchall()
    for fid, path, size, mtime, sig in rows:
        if stop and stop():
            break
        try:
            st = os.stat(path)
        except OSError:
            out["skipped"] += 1
            continue
        if q.signature_of(st.st_size, st.st_mtime_ns) != sig:
            out["skipped"] += 1
            continue
        digest = file_sha256(path, stop)
        after = os.stat(path)
        if q.signature_of(after.st_size, after.st_mtime_ns) != sig:
            out["skipped"] += 1
            continue
        con.execute(
            "INSERT INTO file_hashes(file_id, signature, sha256, hash_status, verified_at)"
            " VALUES (?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET signature=excluded.signature,"
            " sha256=excluded.sha256, hash_status='verified', verified_at=excluded.verified_at",
            (fid, sig, digest, "verified", int(time.time())),
        )
        out["verified"] += 1
    con.commit()
    return out


def groups(con, only_visible_paths: set | None = None) -> list:
    """Ayni sha256 gruplari. Filtre disi yol sayilmaz (A5: grup gorunur yollari sayar)."""
    rows = con.execute(
        "SELECT h.sha256, f.path FROM file_hashes h JOIN files f ON f.file_id=h.file_id"
        " JOIN file_revisions r ON r.file_id=f.file_id AND r.active=1 AND r.signature=h.signature"
        " WHERE h.hash_status='verified' AND f.index_status NOT IN ('missing','excluded')").fetchall()
    by: dict = {}
    for sha, path in rows:
        if only_visible_paths is not None and path not in only_visible_paths:
            continue
        by.setdefault(sha, []).append(path)
    return [{"sha256": s, "paths": sorted(p)} for s, p in by.items() if len(p) > 1]
