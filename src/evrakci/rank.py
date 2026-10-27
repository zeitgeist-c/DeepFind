"""Semantic document retrieval from encrypted embeddings, with source filters."""
from __future__ import annotations
from . import normalize as nz, snippet as snip

def search_semantic(con, query, year=None, ext=None, limit=50, folder=None,
                    offset=0, tag=None, kodla=None):
    from . import embed as embed_mod
    import numpy as np
    query=(query or '').strip()
    if len(query)>2000:
        raise ValueError('Sorgu çok uzun; en fazla 2000 karakter kullanın.')
    limit=max(1,min(int(limit),200));offset=max(0,int(offset))
    output=dict(results=[],suggestions=[],class_counts={'semantic':0},empty=not query,
                has_more=False,offset=offset,semantic=True)
    if not query:
        return output
    if kodla is None:
        session=embed_mod.hazir_oturum()
        if session is None:
            return dict(output,engine_status=embed_mod.status(),
                        semantic_error='Anlamsal arama modeli hazır değil. Model durumunu kontrol edip yeniden deneyin.')
        kodla=lambda texts:session.encode(texts,gorev='sorgu')
    try:
        qvec=np.asarray(kodla([query]),dtype=np.float32)
        if qvec.shape!=(1,embed_mod.DIM) or not np.isfinite(qvec).all():
            raise ValueError('Geçersiz sorgu vektörü')
        qvec=qvec[0];qnorm=np.linalg.norm(qvec)
        if not np.isfinite(qnorm) or qnorm<1e-12:raise ValueError('Boş sorgu vektörü')
        qvec=qvec/qnorm
    except Exception:
        return dict(output,semantic_error='Arama modeli sorguyu işleyemedi. Model durumunu kontrol edip yeniden deneyin.')
    filters = ["e.model_ver=?", "e.dim=?", "f.index_status NOT IN ('excluded','pending','missing')", "f.source_status='ok'", "s.kind NOT IN ('name_only','context')"]
    args = [embed_mod.MODEL_VER, embed_mod.DIM]
    if year:
        filters.append('EXISTS(SELECT 1 FROM file_years y WHERE y.file_id=f.file_id AND y.year=?)'); args.append(year)
    if ext:
        filters.append('f.ext=?'); args.append(ext)
    if folder:
        filters.append('instr(lower(f.path),lower(?))>0'); args.append(folder)
    if tag:
        filters.append('EXISTS(SELECT 1 FROM file_tags t WHERE t.file_id=f.file_id AND t.tag=?)'); args.append(tag.strip().lower())
    cursor = con.execute("SELECT f.file_id,f.path,f.name,f.ext,f.index_status,f.error_code,"
                         "s.seg_id,s.label,s.page,e.vec FROM embeddings e "
                         "JOIN segments s ON s.seg_id=e.seg_id JOIN files f ON f.file_id=s.file_id "
                         "WHERE " + ' AND '.join(filters), args)
    best = {}
    indexed = 0
    for fid,path,name,fext,state,error,sid,label,page,blob in cursor:
        if len(blob) != embed_mod.DIM * 4: continue
        v = np.frombuffer(blob, dtype=np.float32)
        if not np.isfinite(v).all(): continue
        norm = np.linalg.norm(v)
        if not np.isfinite(norm) or norm < 1e-12: continue
        indexed += 1
        similarity = float(np.clip(np.dot(qvec, v / norm), -1.0, 1.0))
        if similarity <= 0: continue
        if fid in best and best[fid][0] >= similarity: continue
        best[fid] = (similarity, (path,name,fext,state,error,sid,label,page))

    ordered=sorted(best.items(),key=lambda item:(-item[1][0],item[1][1][0],item[0]))
    selected=ordered[offset:offset+limit]
    results=[]
    for fid,(similarity,data) in selected:
        path,name,fext,state,error,sid,label,page=data
        raw=con.execute('SELECT raw_text FROM segments WHERE seg_id=?',(sid,)).fetchone()[0]
        years=[r[0] for r in con.execute('SELECT year FROM file_years WHERE file_id=?',(fid,))]
        results.append(dict(file_id=fid,path=path,name=name,ext=fext,label=label,page=page,
            seg_id=sid,snippet=snip.highlight(raw or '',nz.tokens_folded(query)),
            score=round(similarity*100,1),score_class='semantic',vec_skor=round(similarity,3),
            why=['anlamsal benzerlik'],years=years,index_status=state,error_code=error,
            content_available=True))
    return dict(output,results=results,class_counts={'semantic':len(results)},
                has_more=len(ordered)>offset+limit,indexed_documents=len(best),
                index_message='' if indexed else 'Bu kapsamda aranabilir içerik vektörü yok. Kaynaklarınızı tarayın.')

def save_search(con, name: str, query: str, year=None, ext=None, folder=None) -> None:
    name = (name or "").strip()
    if not name or not (query or "").strip():
        raise ValueError("ad ve sorgu gerekli")
    con.execute("INSERT INTO saved_searches(name, query, year, ext, folder) VALUES (?,?,?,?,?)"
                " ON CONFLICT(name) DO UPDATE SET query=excluded.query, year=excluded.year,"
                " ext=excluded.ext, folder=excluded.folder",
                (name, query.strip(), year, ext, folder))
    con.commit()


def saved_searches(con) -> list:
    return [dict(name=r[0], query=r[1], year=r[2], ext=r[3], folder=r[4]) for r in
            con.execute("SELECT name, query, year, ext, folder FROM saved_searches ORDER BY name").fetchall()]


def delete_search(con, name: str) -> None:
    con.execute("DELETE FROM saved_searches WHERE name=?", (name,))
    con.commit()


def _csv_hucre(deger):
    """CSV formül enjeksiyonunu etkisizleştir.

    Excel/LibreOffice `=,+,-,@` ile başlayan hücreyi formül olarak çalıştırır;
    dosya adı ve etiketler kullanıcı/kaynak denetiminde olduğundan başına
    tek tırnak konur (hücre metin olarak okunur, görünen değer değişmez).
    """
    metin = "" if deger is None else str(deger)
    tehlikeli = ("=", "+", "-", "@", chr(9), chr(13))
    if metin.startswith(tehlikeli):
        return "'" + metin
    return metin


def results_csv(con, results) -> str:
    """Arama sonuçlarını CSV metni yapar (dosya yazımı çağıranda)."""
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["dosya", "yol", "tur", "sayfa", "yil", "etiketler", "neden"])
    for r in results:
        w.writerow([_csv_hucre(r.get("name", "")), _csv_hucre(r.get("path", "")),
                    _csv_hucre(r.get("ext", "")), _csv_hucre(r.get("page") or ""),
                    _csv_hucre(",".join(r.get("years", []))),
                    _csv_hucre(", ".join(file_tags(con, r.get("file_id")))),
                    _csv_hucre(" + ".join(r.get("why", [])))])
    return buf.getvalue()


def file_tags(con, file_id) -> list:
    try:
        return [r[0] for r in con.execute(
            "SELECT tag FROM file_tags WHERE file_id=? ORDER BY tag", (file_id,)).fetchall()]
    except Exception:
        return []


def set_tag(con, file_id, tag: str, auto: int = 0) -> None:
    tag = (tag or "").strip().lower()
    if not tag:
        raise ValueError("etiket gerekli")
    con.execute("INSERT INTO file_tags(file_id, tag, auto) VALUES (?,?,?)"
                " ON CONFLICT(file_id, tag) DO NOTHING", (file_id, tag, auto))
    con.commit()


def remove_tag(con, file_id, tag: str) -> None:
    con.execute("DELETE FROM file_tags WHERE file_id=? AND tag=?", (file_id, (tag or "").strip().lower()))
    con.commit()


def tags_many(con, file_ids, tag: str, *, auto: int = 0, remove: bool = False) -> int:
    """Birden çok belgeye etiket ekler/kaldırır: tek işlem, hatada tümü geri alınır.

    Yarı uygulanmış toplu işlem bırakmamak için tüm satırlar yazıldıktan sonra
    tek `commit` yapılır; herhangi bir hata `rollback` ile geri alınır.
    """
    tag = (tag or "").strip().lower()
    if not tag:
        raise ValueError("etiket gerekli")
    idler = list(file_ids)
    if not idler:
        return 0
    try:
        if remove:
            con.executemany("DELETE FROM file_tags WHERE file_id=? AND tag=?",
                            ((fid, tag) for fid in idler))
        else:
            con.executemany("INSERT INTO file_tags(file_id, tag, auto) VALUES (?,?,?)"
                            " ON CONFLICT(file_id, tag) DO NOTHING",
                            ((fid, tag, auto) for fid in idler))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return len(idler)


def add_rule(con, tag: str, keywords: str, mode: str = "any") -> int:
    tag = (tag or "").strip().lower()
    keywords = (keywords or "").strip()
    if not tag or not keywords or mode not in ("any", "all"):
        raise ValueError("etiket, anahtar kelimeler ve kip(any/all) gerekli")
    cur = con.execute("INSERT INTO tag_rules(tag, keywords, mode) VALUES (?,?,?)",
                      (tag, keywords, mode))
    con.commit()
    return cur.lastrowid


def tag_rules(con) -> list:
    try:
        return [dict(rule_id=r[0], tag=r[1], keywords=r[2], mode=r[3]) for r in
                con.execute("SELECT rule_id, tag, keywords, mode FROM tag_rules ORDER BY tag").fetchall()]
    except Exception:
        return []


def delete_rule(con, rule_id: int) -> None:
    con.execute("DELETE FROM tag_rules WHERE rule_id=?", (rule_id,))
    con.commit()
