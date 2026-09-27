"""Kalıcı iş kuyruğu: claim/lease, artan retry, çöküş kurtarma, duraklat/iptal bayrakları."""
from __future__ import annotations

import time

RETRY_DELAYS = [60, 300, 1800]  # 1, 5, 30 dk (plan bolum 9 adayi)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1
LEASE_SEC = 600


def now() -> int:
    return int(time.time())


def signature_of(size, mtime_ns) -> str:
    return f"{size}:{mtime_ns}"


def enqueue(con, file_id: int, sig: str, kind: str = "extract") -> None:
    con.execute(
        "INSERT INTO jobs(file_id, signature, kind, status) VALUES (?, ?, ?, 'pending')"
        " ON CONFLICT(file_id, signature, kind) DO NOTHING",
        (file_id, sig, kind),
    )


def claim(con, kinds=("extract",), *, scoped=False) -> dict | None:
    """Süresi dolmuş lease dahil tek iş al. Tek DB yazıcısı varsayımıyla."""
    t = now()
    marks = ",".join("?" * len(kinds))
    scope = " AND file_id IN (SELECT file_id FROM scan_selected)" if scoped else ""
    row = con.execute(
        "SELECT job_id, file_id, signature, kind, attempts FROM jobs"
        f" WHERE kind IN ({marks}) AND (status='pending' AND not_before<=?"
        " OR status='running' AND lease_until<?)" + scope + " ORDER BY job_id LIMIT 1",
        (*kinds, t, t),
    ).fetchone()
    if not row:
        return None
    jid, fid, sig, kind, att = row
    con.execute(
        "UPDATE jobs SET status='running', lease_until=?, attempts=? WHERE job_id=?",
        (t + LEASE_SEC, att, jid),
    )
    con.commit()
    return {"job_id": jid, "file_id": fid, "signature": sig, "kind": kind, "attempts": att}


def complete(con, job_id: int) -> None:
    con.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
    con.commit()


def fail(con, job_id: int, error_code: str) -> str:
    """Hata: retry veya kalıcı basarisiz. Donus: 'retry' | 'dead'."""
    t = now()
    row = con.execute("SELECT attempts FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    att = (row[0] if row else 0) + 1
    if att >= MAX_ATTEMPTS:
        con.execute(
            "UPDATE jobs SET status='dead', attempts=?, error_code=? WHERE job_id=?",
            (att, error_code, job_id),
        )
        con.commit()
        return "dead"
    delay = RETRY_DELAYS[min(att - 1, len(RETRY_DELAYS) - 1)]
    con.execute(
        "UPDATE jobs SET status='pending', attempts=?, not_before=?, error_code=? WHERE job_id=?",
        (att, t + delay, error_code, job_id),
    )
    con.commit()
    return "retry"


def recover_running(con) -> int:
    """Açılışta yarım işleri pending yap (güç kesintisi)."""
    cur = con.execute("UPDATE jobs SET status='pending', lease_until=0 WHERE status='running'")
    con.commit()
    return cur.rowcount


def pending_count(con) -> int:
    return con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0]
