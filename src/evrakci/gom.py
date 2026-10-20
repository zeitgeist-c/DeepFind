"""Geri doldurma: segment -> vektor (embed kuyrugu).

Sahiplik: coordinator embed islerini buraya verir; model bir kez yuklenir,
her dosya tek transaction'da yazilir. Eski surum satirlar bastan yazilir.
"""
from __future__ import annotations

import numpy as np

from . import embed as embed_mod
from . import extract as ex_mod
from . import job_queue as q

TOPLU = 16


def model_yolu() -> str:
    """Uretim model dosyasi."""
    return embed_mod._varsayilan_model_yolu()


def model_var_mi(yol: str | None = None) -> bool:
    """Uretim modeli diskte mi? Yoksa gom kuyrugu kurulmaz (FTS aynen)."""
    import os

    return os.path.isfile(yol or embed_mod._varsayilan_model_yolu())


def _metinler(con, file_id: int) -> list[tuple[int, str]]:
    satirlar = con.execute(
        "SELECT seg_id, label, raw_text FROM segments"
        " WHERE file_id=? AND kind NOT IN ('name_only','context')"
        " ORDER BY seg_id", (file_id,)).fetchall()
    ciftler = []
    for seg_id, etiket, ham in satirlar:
        parc = ex_mod.Segment("para", None, etiket or "", ham or "")
        for dilim, _, _ in ex_mod.chunks(parc, 4000):
            metin = ((dilim.label or "") + "\n" + (dilim.raw_text or "")).strip()
            if metin:
                ciftler.append((seg_id, metin))
    return ciftler


def vektor_yaz(con, ciftler: list[tuple[int, str]], v) -> int:
    """Dagit: chunk vektorlerini segmentte ortala, birimle, yaz. Donus: segment."""
    import numpy as np

    if not ciftler:
        return 0
    v = np.asarray(v, dtype=np.float32)
    ids = sorted({s for s, _ in ciftler})
    con.execute(
        f"DELETE FROM embeddings WHERE seg_id IN ({','.join('?' * len(ids))})", ids)
    toplam = np.zeros((len(ids), v.shape[1]), dtype=np.float64)
    sayac = np.zeros(len(ids), dtype=np.int64)
    sira = {s: i for i, s in enumerate(ids)}
    for (seg_id, _), satir in zip(ciftler, v):
        toplam[sira[seg_id]] += satir
        sayac[sira[seg_id]] += 1
    for seg_id in ids:
        i = sira[seg_id]
        orta = toplam[i] / max(1, sayac[i])
        norm = float(np.linalg.norm(orta)) or 1.0
        birim = (orta / norm).astype(np.float32)
        con.execute(
            "INSERT INTO embeddings(seg_id, model_ver, dim, vec)"
            " VALUES (?,?,?,?)",
            (seg_id, embed_mod.MODEL_VER, embed_mod.DIM, birim.tobytes()))
    con.commit()
    return len(ids)


def isle_dosya(con, file_id: int, kodla) -> int:
    """kodla(metinler) -> (n,256) float32. Donus: vektor yazilan segment."""
    ciftler = _metinler(con, file_id)
    if not ciftler:
        return 0
    return vektor_yaz(con, ciftler, kodla([t for _, t in ciftler]))


def process_embed_job(con, job: dict, kodla=None) -> str:
    """Tek embed isi: 'done' | 'changed' | 'gone'. Model tembel yuklenir."""
    fid = job["file_id"]
    satir = con.execute(
        "SELECT size, mtime_ns FROM files WHERE file_id=?", (fid,)).fetchone()
    if not satir:
        q.complete(con, job["job_id"])
        return "gone"
    if q.signature_of(*satir) != job["signature"]:
        q.enqueue(con, fid, q.signature_of(*satir), kind="embed")
        con.commit()
        q.complete(con, job["job_id"])
        return "changed"
    if kodla is None:
        ot = embed_mod.Oturum()
        kodla = lambda metinler: ot.encode(metinler, gorev="belge", toplu=TOPLU)  # noqa: E731
    try:
        isle_dosya(con, fid, kodla)
    except Exception as error:
        return q.fail(con, job["job_id"], type(error).__name__)
    q.complete(con, job["job_id"])
    return "done"
