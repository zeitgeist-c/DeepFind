"""Document retrieval in SQLite; limit only after intersection and filters."""
from __future__ import annotations
import re
from . import normalize as nz, snippet as snip, vocab as vc

MAX_DOCS = 500  # compatibility; never a per-token cutoff
FUZZY_MIN_RESULTS = 5
RAWTOK_RE = re.compile(r"[A-Za-zÇçĞğIıİiÖöŞşÜü0-9]+")

def _files_with(con, table, token):
    if table not in ('docs_fts', 'docs_fts_folded'):
        raise ValueError('Invalid index')
    return {r[0] for r in con.execute(f'SELECT DISTINCT s.file_id FROM {table} JOIN segments s ON s.seg_id={table}.rowid WHERE {table} MATCH ?', ('"'+token.replace('"','""')+'"',))}

def _intersect(sets):
    return set.intersection(*sets) if sets else set()

def _query(con, query, year, ext, folder, limit, offset, fuzzy=None):
    raw = RAWTOK_RE.findall(query)
    folded = nz.tokens_folded(query)
    quoted = re.findall(r'"([^"]+)"', query)
    args=[]
    def group(table, tokens, phrases):
        expressions = ['"'+t.replace('"','""')+'"' for t in tokens]
        expressions += ['"'+p.replace('"','""')+'"' for p in phrases]
        if fuzzy and table=='docs_fts_folded':
            expressions = ['('+' OR '.join('"'+x+'"' for x in [t]+fuzzy.get(t, []))+')' for t in tokens]
            expressions += ['"'+p+'"' for p in phrases]
        if not expressions:
            return 'SELECT file_id FROM files WHERE 0'
        args.extend(expressions)
        return ' INTERSECT '.join(f'SELECT s.file_id FROM {table} JOIN segments s ON s.seg_id={table}.rowid WHERE {table} MATCH ?' for _ in expressions)
    strict=group('docs_fts',raw,quoted)
    fold=group('docs_fts_folded',folded,[nz.folded(p) for p in quoted])
    hit_expr=' + '.join('CASE WHEN instr(s.folded_text, ?) > 0 THEN 1 ELSE 0 END' for _ in folded) or '0'
    args.extend(folded)
    # Rank/filter before fetching content. Only one segment per output document.
    filters=["f.index_status NOT IN ('excluded','pending')"]
    if year:
        filters.append('EXISTS(SELECT 1 FROM file_years y WHERE y.file_id=f.file_id AND y.year=?)'); args.append(year)
    if ext:
        filters.append('f.ext=?'); args.append(ext)
    if folder:
        filters.append('instr(lower(f.path),lower(?))>0'); args.append(folder)
    args.extend([limit,offset])
    sql=f'''WITH strict AS ({strict}), folded AS ({fold}), candidates AS (
      SELECT file_id,100 base FROM strict UNION ALL SELECT file_id,{30 if fuzzy else 60} FROM folded WHERE file_id NOT IN (SELECT file_id FROM strict)
    ), chosen AS (SELECT f.file_id,f.path,f.name,f.ext,f.index_status,f.error_code,c.base,
      (SELECT s.seg_id FROM segments s WHERE s.file_id=f.file_id ORDER BY ({hit_expr}) DESC,
        CASE WHEN s.kind IN ('name_only','context') THEN 1 ELSE 0 END,s.seg_id LIMIT 1) seg_id
      FROM candidates c JOIN files f ON f.file_id=c.file_id WHERE {' AND '.join(filters)}
      ORDER BY c.base DESC,f.path LIMIT ? OFFSET ?)
      SELECT c.*,s.label,s.page,s.raw_text,s.kind FROM chosen c JOIN segments s ON s.seg_id=c.seg_id'''
    return con.execute(sql,args).fetchall()

def search_ranked(con, query, year=None, ext=None, limit=50, folder=None, offset=0):
    tokens=nz.tokens_folded(query)
    if len(query)>2000 or len(RAWTOK_RE.findall(query))>32:
        raise ValueError('sorgu çok uzun')
    if not tokens:
        return {'results':[], 'suggestions':[], 'class_counts':{}, 'empty':True}
    limit=max(1,min(int(limit),200)); offset=max(0,int(offset))
    rows=_query(con,query,year,ext,folder,limit+1,offset)
    suggestions=[]
    if len(rows)<FUZZY_MIN_RESULTS and not re.findall(r'"([^"]+)"',query):
        alternatives={t:[c for c,_ in vc.suggest(con,t)] for t in tokens}
        suggestions=list(dict.fromkeys(c for values in alternatives.values() for c in values))[:5]
        if any(alternatives.values()):
            known={r[0] for r in rows}
            rows += [r for r in _query(con,query,year,ext,folder,limit+1,offset,alternatives) if r[0] not in known]
    more=len(rows)>limit
    results=[]; counts={'strict':0,'folded':0,'fuzzy':0}
    for fid,path,name,fext,status,error,base,sid,label,page,raw,kind in rows[:limit]:
        cls={100:'strict',60:'folded',30:'fuzzy'}[base]; counts[cls]+=1
        years=[r[0] for r in con.execute('SELECT year FROM file_years WHERE file_id=?',(fid,))]
        name_hit=any(t in nz.folded(name) for t in tokens)
        why=(['ad'] if name_hit else [])+[{'strict':'birebir icerik','folded':'toleransli icerik','fuzzy':'yaklasik icerik'}[cls]]
        if years: why.append('yil:'+','.join(years))
        results.append(dict(file_id=fid,seg_id=sid,path=path,name=name,ext=fext,label=label,page=page,
          snippet=snip.highlight(raw or '',tokens),score_class=cls,score=base,why=why,years=years,
          index_status=status,error_code=error,content_available=kind not in ('name_only','context')))
    return dict(results=results,suggestions=suggestions,class_counts=counts,empty=False,has_more=more,offset=offset)
