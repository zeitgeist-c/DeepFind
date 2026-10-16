"""Document retrieval in SQLite; limit only after intersection and filters."""
from __future__ import annotations
import re
from . import normalize as nz, snippet as snip, vocab as vc

MAX_DOCS = 500  # compatibility; never a per-token cutoff
FUZZY_MIN_RESULTS = 5
RAWTOK_RE = re.compile(r"[A-Za-zÇçĞğIıİiÖöŞşÜü0-9]+")

_OR_SPLIT_RE = re.compile(r"\s+(?:OR|VEYA)\s+", re.IGNORECASE)
_NOT_PHRASE_RE = re.compile(r'-"([^"]+)"')
_NOT_WORD_RE = re.compile(r"(?:^|\s)- ?([A-Za-zÇçĞğIıİiÖöŞşÜü0-9]+)")
_NOT_KW_RE = re.compile(r"\bNOT\s+")  # yalnız büyük harf; küçük 'not' Türkçe kelimedir


def _split_groups(query):
    """OR/VEYA gruplarına böl (tırnak içindeki korunur)."""
    groups, cur = [], []
    for chunk in re.split(r'("[^"]*")', query):
        if chunk.startswith('"'):
            cur.append(chunk)
        else:
            parts = _OR_SPLIT_RE.split(chunk)
            cur.append(parts[0])
            for p in parts[1:]:
                groups.append("".join(cur))
                cur = [p]
    groups.append("".join(cur))
    return [g.strip() for g in groups if g.strip()] or [query]


def _split_excluded(group):
    """(pozitif_metin, [dislanan...]). -terim, -"kalıp", NOT terim."""
    excl = []
    g = _NOT_PHRASE_RE.sub(lambda m: (excl.append(m.group(1)), " ")[1], group)
    g = _NOT_KW_RE.sub("-", g)
    g = _NOT_WORD_RE.sub(lambda m: (excl.append(m.group(1)), " ")[1], g)
    return g, excl


def _quote(t):
    return '"' + t.replace('"', '""') + '"'

def _query(con, query, year, ext, folder, limit, offset, fuzzy=None, tag=None):
    args=[]
    # v9: docs_fts KATLANMIS icerik tasir (fold() UDF trigger'lari). strict =
    # orijinal terimler (diakritigsiz sorguda birebir), folded = nz.folded() ile
    # katlanmis terimler; ikisi de ayni indekste (eski docs_fts_folded kaldirildi).
    def group(tokens, phrases, use_fuzzy=False):
        if use_fuzzy:
            expressions = ['('+' OR '.join('"'+x+'"' for x in [t]+fuzzy.get(t, []))+')' for t in tokens]
            expressions += ['"'+p+'"' for p in phrases]
        else:
            expressions = [_quote(t) for t in tokens]
            expressions += [_quote(p) for p in phrases]
        if not expressions:
            return 'SELECT file_id FROM files WHERE 0', []
        sql = ' INTERSECT '.join(f'SELECT s.file_id FROM docs_fts JOIN segments s ON s.seg_id=docs_fts.rowid WHERE docs_fts MATCH ?' for _ in expressions)
        return sql, expressions
    strict_parts, fold_parts, excl_selects = [], [], []
    strict_args, fold_args, excl_args, hit_tokens = [], [], [], []
    for grp in _split_groups(query):
        pos, excl = _split_excluded(grp)
        raw = RAWTOK_RE.findall(pos)
        folded = nz.tokens_folded(pos)
        quoted = re.findall(r'"([^"]+)"', pos)
        hit_tokens.extend(folded)
        s_sql, s_args = group(raw, quoted)
        strict_parts.append(s_sql)
        strict_args.extend(s_args)
        f_sql, f_args = group(folded, [nz.folded(p) for p in quoted], use_fuzzy=bool(fuzzy))
        fold_parts.append(f_sql)
        fold_args.extend(f_args)
        for e in excl:
            excl_selects.append(f'SELECT s.file_id FROM docs_fts JOIN segments s ON s.seg_id=docs_fts.rowid WHERE docs_fts MATCH ?')
            excl_args.append(_quote(nz.folded(e)))
    strict=' UNION '.join(strict_parts)
    fold=' UNION '.join(fold_parts)
    args.extend(strict_args)
    args.extend(fold_args)
    hit_expr=' + '.join('CASE WHEN instr(fold(s2.raw_text), ?) > 0 THEN 1 ELSE 0 END' for _ in hit_tokens) or '0'
    # Rank/filter before fetching content. Only one segment per output document.
    filters=["f.index_status NOT IN ('excluded','pending')"]
    if year:
        filters.append('EXISTS(SELECT 1 FROM file_years y WHERE y.file_id=f.file_id AND y.year=?)'); args.append(year)
    if ext:
        filters.append('f.ext=?'); args.append(ext)
    if folder:
        filters.append('instr(lower(f.path),lower(?))>0'); args.append(folder)
    if tag:
        filters.append('EXISTS(SELECT 1 FROM file_tags t WHERE t.file_id=f.file_id AND t.tag=?)'); args.append(tag.strip().lower())
    if excl_selects:
        filters.append(f"f.file_id NOT IN ({' UNION '.join(excl_selects)})")
        args.extend(excl_args)
    args.extend([limit,offset])
    args.extend(hit_tokens)  # hit_expr en son alt sorguda (SQL'de LIMIT'ten sonra)
    # Segment secimi (hit_expr -> fold() Python UDF) yalniz LIMIT gecmis satirlar
    # icin kossun: once dokuman sayfasi belirlenir, segment sonra secilir.
    sql=f'''WITH strict AS ({strict}), folded AS ({fold}), candidates AS (
      SELECT file_id,100 base FROM strict UNION ALL SELECT file_id,{30 if fuzzy else 60} FROM folded WHERE file_id NOT IN (SELECT file_id FROM strict)
    ), picked AS (SELECT f.file_id,f.path,f.name,f.ext,f.index_status,f.error_code,c.base
      FROM candidates c JOIN files f ON f.file_id=c.file_id WHERE {' AND '.join(filters)}
      ORDER BY c.base DESC,f.path LIMIT ? OFFSET ?)
      SELECT p.file_id,p.path,p.name,p.ext,p.index_status,p.error_code,p.base,s.seg_id,s.label,s.page,s.raw_text,s.kind
      FROM picked p JOIN segments s ON s.seg_id=(
        SELECT s2.seg_id FROM segments s2 WHERE s2.file_id=p.file_id ORDER BY ({hit_expr}) DESC,
        CASE WHEN s2.kind IN ('name_only','context') THEN 1 ELSE 0 END,s2.seg_id LIMIT 1)'''
    return con.execute(sql,args).fetchall()

def search_ranked(con, query, year=None, ext=None, limit=50, folder=None, offset=0, tag=None):
    nz.install(con)  # hit_expr fold() UDF'ine bagli (v9)
    tokens=nz.tokens_folded(query)
    if len(query)>2000 or len(RAWTOK_RE.findall(query))>32:
        raise ValueError('sorgu çok uzun')
    if not tokens:
        return {'results':[], 'suggestions':[], 'class_counts':{}, 'empty':True}
    limit=max(1,min(int(limit),200)); offset=max(0,int(offset))
    rows=_query(con,query,year,ext,folder,limit+1,offset,tag=tag)
    suggestions=[]
    if len(rows)<FUZZY_MIN_RESULTS and not re.findall(r'"([^"]+)"',query):
        alternatives={t:[c for c,_ in vc.suggest(con,t)] for t in tokens}
        suggestions=list(dict.fromkeys(c for values in alternatives.values() for c in values))[:5]
        if any(alternatives.values()):
            known={r[0] for r in rows}
            rows += [r for r in _query(con,query,year,ext,folder,limit+1,offset,alternatives,tag=tag) if r[0] not in known]
    more=len(rows)>limit
    # v9: tek katlanmis indeks. Sinif karari artik ham metne gore verilir:
    # 'strict' = sorgunun yazim bicimi ham metinde aynen geciyor (tr_lower
    # token kumesi), aksi halde toleransli (folded). FTS tek indeks oldugu
    # icin kapi (base) sinifi tek basina yaniltici olabilir.
    want={nz.tr_lower(t) for t in RAWTOK_RE.findall(query)}
    quoted=bool(re.findall(r'"([^"]+)"', query))
    results=[]; counts={'strict':0,'folded':0,'fuzzy':0}
    for fid,path,name,fext,status,error,base,sid,label,page,raw,kind in rows[:limit]:
        cls={100:'strict',60:'folded',30:'fuzzy'}[base]
        if want and not quoted and cls in ('strict','folded'):
            doc={nz.tr_lower(t) for t in RAWTOK_RE.findall((raw or '')+' '+name)}
            exact=want <= doc
            if cls=='strict' and not exact: cls, base = 'folded', 60
            elif cls=='folded' and exact: cls, base = 'strict', 100
        counts[cls]+=1
        years=[r[0] for r in con.execute('SELECT year FROM file_years WHERE file_id=?',(fid,))]
        name_hit=any(t in nz.folded(name) for t in tokens)
        why=(['ad'] if name_hit else [])+[{'strict':'birebir icerik','folded':'toleransli icerik','fuzzy':'yaklasik icerik'}[cls]]
        if years: why.append('yil:'+','.join(years))
        results.append(dict(file_id=fid,seg_id=sid,path=path,name=name,ext=fext,label=label,page=page,
          snippet=snip.highlight(raw or '',tokens),score_class=cls,score=base,why=why,years=years,
          index_status=status,error_code=error,content_available=kind not in ('name_only','context')))
    return dict(results=results,suggestions=suggestions,class_counts=counts,empty=False,has_more=more,offset=offset)


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


def results_csv(con, results) -> str:
    """Arama sonuçlarını CSV metni yapar (dosya yazımı çağıranda)."""
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["dosya", "yol", "tur", "sayfa", "yil", "etiketler", "neden"])
    for r in results:
        w.writerow([r.get("name", ""), r.get("path", ""), r.get("ext", ""),
                    r.get("page") or "", ",".join(r.get("years", [])),
                    ", ".join(file_tags(con, r.get("file_id"))),
                    " + ".join(r.get("why", []))])
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
