"""Geri doldurma: segment -> vektor (embed kuyrugu).

Sahiplik: coordinator embed islerini buraya verir; model bir kez yuklenir,
her dosya tek transaction'da yazilir. Eski surum satirlar bastan yazilir.
"""
from __future__ import annotations


from . import embed as embed_mod
from . import job_queue as q

TOPLU = 16


def model_yolu() -> str:
    """Uretim model dosyasi."""
    return embed_mod._varsayilan_model_yolu()


def model_var_mi(yol: str | None = None) -> bool:
    """Is the production model on disk? Semantic scan stays incomplete without a model."""
    import os

    return os.path.isfile(yol or embed_mod._varsayilan_model_yolu())


def _metinler(con, file_id: int) -> list[tuple[int, str]]:
    satirlar = con.execute(
        "SELECT seg_id, label, raw_text FROM segments"
        " WHERE file_id=? AND kind NOT IN ('name_only','context')"
        " ORDER BY seg_id", (file_id,)).fetchall()
    return [(sid, ((label or '') + '\n' + (raw or '')).strip())
            for sid,label,raw in satirlar if (label or raw)]


def vektor_yaz(con, ciftler: list[tuple[int, str]], v) -> int:
    """Dagit: chunk vektorlerini segmentte ortala, birimle, yaz. Donus: segment."""
    import numpy as np

    if not ciftler:
        return 0
    v = np.asarray(v, dtype=np.float32)
    if v.shape != (len(ciftler), embed_mod.DIM) or not np.isfinite(v).all():
        raise ValueError('Geçersiz belge vektörleri')
    if np.any(np.linalg.norm(v,axis=1)<1e-12):
        raise ValueError('Boş belge vektörü')
    sums, counts = {}, {}
    for (sid,_), vector in zip(ciftler,v):
        sums[sid] = sums.get(sid,np.zeros(embed_mod.DIM,dtype=np.float64)) + vector
        counts[sid] = counts.get(sid,0)+1
    values=[]
    for sid,total in sums.items():
        mean = total/counts[sid]
        norm = float(np.linalg.norm(mean))
        if norm < 1e-12: raise ValueError('Boş segment vektörü')
        values.append((sid,embed_mod.MODEL_VER,embed_mod.DIM,(mean/norm).astype(np.float32).tobytes()))
    ids = list(sums)
    con.execute('SAVEPOINT embedding_file')
    try:
        con.executemany('INSERT INTO embeddings(seg_id,model_ver,dim,vec) VALUES (?,?,?,?) '
                        'ON CONFLICT(seg_id) DO UPDATE SET model_ver=excluded.model_ver,dim=excluded.dim,vec=excluded.vec',values)
        con.execute('RELEASE embedding_file')
        con.commit()
    except Exception:
        con.execute('ROLLBACK TO embedding_file')
        con.execute('RELEASE embedding_file')
        raise
    return len(ids)


def isle_dosya(con, file_id: int, kodla, cancel=None) -> int:
    """kodla(metinler) -> (n,256) float32. Donus: vektor yazilan segment."""
    ciftler = _metinler(con, file_id)
    if not ciftler:
        return 0
    v = kodla([t for _, t in ciftler])
    if cancel is not None:
        try:
            if cancel():
                raise InterruptedError("Gömme iptal edildi")
        except InterruptedError:
            raise
        except Exception:
            pass
    return vektor_yaz(con, ciftler, v)


def process_embed_job(con, job: dict, kodla=None, cancel=None, deneme=False,
                        ayrinti: dict | None = None) -> str:
    """Tek embed isi: 'done' | 'changed' | 'gone' | 'deneme_hatasi'.

    `deneme=True` (toplu deneme): kodla hatasi normal isin yeniden deneme
    hakkini tuketmez; is pending birakilir (attempts aynen korunur) ve
    'deneme_hatasi' doner. Cagiran denemeyi kapatip ayni isi normal ayarla
    yeniden isler. Normal ayar da hata verirse mevcut `q.fail` politikasi
    uygulanir. `ayrinti` verilirse {'parca': yazilan segment, 'hata': tur}
    doldurulur; hiz olcumu bu gercek yazim sayisiyla yapilir.

    Gec yanit iptal edilmis isi tamamlayamaz: kodla donse bile yazmadan ve
    kuyruktan dusmeden once iptal denetlenir; iptalde is pending birakilir
    (cagiran `InterruptedError` uzerinden kuyrugu korur). Yazilmamis isler
    yeniden islenebilir kalir; cift yazma olmaz cunku `vektor_yaz` tek
    transaction + upsert'tir.
    """
    fid = job["file_id"]
    if cancel is not None:
        try:
            if cancel():
                raise InterruptedError("Gömme iptal edildi")
        except InterruptedError:
            raise
        except Exception:
            pass
    satir = con.execute(
        "SELECT size, mtime_ns FROM files WHERE file_id=?", (fid,)).fetchone()
    if not satir:
        if cancel is not None:
            try:
                if cancel():
                    raise InterruptedError("Gömme iptal edildi")
            except InterruptedError:
                raise
            except Exception:
                pass
        q.complete(con, job["job_id"])
        return "gone"
    if q.signature_of(*satir) != job["signature"]:
        q.enqueue(con, fid, q.signature_of(*satir), kind="embed")
        con.commit()
        if cancel is not None:
            try:
                if cancel():
                    raise InterruptedError("Gömme iptal edildi")
            except InterruptedError:
                # Yeni imza kuyrukta; eski is pending birakilir.
                con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?",
                            (job["job_id"],))
                con.commit()
                raise
            except Exception:
                pass
        q.complete(con, job["job_id"])
        return "changed"
    if kodla is None:
        ot = embed_mod.isit_oturumu()
        if ot is None:
            raise RuntimeError(embed_mod.status()["error"])
        kodla = lambda metinler: ot.encode(metinler, gorev="belge", toplu=TOPLU)  # noqa: E731
    try:
        yazilan = isle_dosya(con, fid, kodla, cancel=cancel)
    except InterruptedError:
        raise
    except Exception as error:
        hata_turu = type(error).__name__
        if ayrinti is not None:
            ayrinti["parca"] = 0
            ayrinti["hata"] = hata_turu
        if deneme:
            # Deneysel hata: normal isin hakki tuketilmez; son deneme
            # hakkindaki is bile normal ayarla yeniden islenebilir.
            con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?",
                        (job["job_id"],))
            con.commit()
            return "deneme_hatasi"
        return q.fail(con, job["job_id"], hata_turu)
    if cancel is not None:
        try:
            if cancel():
                raise InterruptedError("Gömme iptal edildi")
        except InterruptedError:
            # Vektor yazildiysa bile tamamlanmis sayilmaz; yeniden isleme
            # upsert ile idempotenttir, cift kayit olusmaz.
            con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?",
                        (job["job_id"],))
            con.commit()
            raise
        except Exception:
            pass
    if ayrinti is not None:
        ayrinti["parca"] = int(yazilan)
        ayrinti["hata"] = None
    q.complete(con, job["job_id"])
    return "done"
