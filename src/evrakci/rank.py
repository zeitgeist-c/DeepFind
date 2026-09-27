"""Belge duzeyi retrieval + sinifli siralama + aciklama (plan bolum 12-13).

Sorgu kelimelerinin tek segmentte olmasi sart degil: her token icin eslesen
belge kumeleri kesisir; konum/snippet en iyi segmentten (uydurma yok).
"""
from __future__ import annotations

import re

from . import normalize as nz
from . import snippet as snip
from . import vocab as vc

MAX_DOCS = 500
FUZZY_MIN_RESULTS = 5
RAWTOK_RE = re.compile(r"[A-Za-zÇçĞğIıİiÖöŞşÜü0-9]+")


def _files_with(con, table: str, token: str) -> set:
    rows = con.execute(
        f"SELECT DISTINCT s.file_id FROM {table}"
        f" JOIN segments s ON s.seg_id = {table}.rowid"
        f" WHERE {table} MATCH ? LIMIT {MAX_DOCS}",
        (f'"{token}"',)).fetchall()
    return {r[0] for r in rows}


def _intersect(sets: list) -> set:
    if not sets:
        return set()
    out = set(sets[0])
    for s in sets[1:]:
        out &= s
    return out


def _segments_of(con, fids: set) -> dict:
    if not fids:
        return {}
    q = ",".join("?" * len(fids))
    out: dict = {}
    for seg_id, fid, label, page, raw in con.execute(
            f"SELECT seg_id, file_id, label, page, raw_text FROM segments WHERE file_id IN ({q})",
            tuple(fids)).fetchall():
        out.setdefault(fid, []).append({"seg_id": seg_id, "label": label, "page": page,
                                        "raw": raw or "", "fold": nz.folded(raw or "")})
    return out


def _best_segment(segs: list, tokens: list) -> dict:
    def hits(s):
        return sum(1 for t in tokens if t in s["fold"])
    return sorted(segs, key=lambda s: (-hits(s), s["seg_id"]))[0]


def _file_rows(con, fids: set) -> dict:
    if not fids:
        return {}
    q = ",".join("?" * len(fids))
    rows = con.execute(
        f"SELECT file_id, path, name, ext, index_status FROM files WHERE file_id IN ({q})",
        tuple(fids)).fetchall()
    return {r[0]: r for r in rows}


def _file_years(con, fids: set) -> dict:
    if not fids:
        return {}
    q = ",".join("?" * len(fids))
    out: dict = {}
    for fid, y in con.execute(f"SELECT file_id, year FROM file_years WHERE file_id IN ({q})",
                              tuple(fids)).fetchall():
        out.setdefault(fid, []).append(y)
    return out


def search_ranked(con, query: str, year: str | None = None, ext: str | None = None,
                  limit: int = 50) -> dict:
    raw_toks = RAWTOK_RE.findall(query)
    qtokens = nz.tokens_folded(query)
    qyears = nz.extract_years(query)
    if not qtokens and not qyears:
        return {"results": [], "suggestions": [], "class_counts": {}, "empty": True}

    strict_docs = _intersect([_files_with(con, "docs_fts", t) for t in raw_toks]) if raw_toks else set()
    folded_docs = _intersect([_files_with(con, "docs_fts_folded", t) for t in qtokens])
    counts = {"strict": len(strict_docs), "folded": len(folded_docs), "fuzzy": 0}

    suggestions: list = []
    fuzzy_docs: set = set()
    if len(strict_docs | folded_docs) < FUZZY_MIN_RESULTS and qtokens:
        alts = {}
        for t in qtokens:
            alts[t] = [c for c, _s in vc.suggest(con, t)]
            for c in alts[t][:2]:
                if c not in suggestions:
                    suggestions.append(c)
        suggestions = suggestions[:5]
        exprs = []
        for t in qtokens:
            opts = [t] + alts.get(t, [])[:3]
            exprs.append("(" + " OR ".join(f'"{o}"' for o in opts) + ")")
        fuzzy_docs = _intersect([
            {r[0] for r in con.execute(
                "SELECT DISTINCT s.file_id FROM docs_fts_folded"
                " JOIN segments s ON s.seg_id = docs_fts_folded.rowid"
                " WHERE docs_fts_folded MATCH ? LIMIT 500", (e,)).fetchall()}
            for e in exprs])
    counts["fuzzy"] = len(fuzzy_docs - strict_docs - folded_docs)

    ranked_fids = [(fid, 100) for fid in strict_docs] + \
                  [(fid, 60) for fid in folded_docs - strict_docs] + \
                  [(fid, 30) for fid in fuzzy_docs - strict_docs - folded_docs]
    if not ranked_fids:
        return {"results": [], "suggestions": suggestions, "class_counts": counts, "empty": False}

    fids = {f for f, _b in ranked_fids}
    frows = _file_rows(con, fids)
    fyears = _file_years(con, fids)
    segmap = _segments_of(con, fids)

    results = []
    for fid, base in ranked_fids:
        fr = frows.get(fid)
        if not fr:
            continue
        _fid, path, name, fext, ist = fr
        if ist in ("missing", "excluded"):
            continue
        years = fyears.get(fid, [])
        if year and year not in years:
            continue  # acik yil filtresi kati kural
        if ext and fext != ext:
            continue
        segs = segmap.get(fid, [])
        if not segs:
            continue
        best = _best_segment(segs, qtokens)
        allfold = " ".join(s["fold"] for s in segs)
        cover = sum(1 for t in qtokens if t in allfold) / max(1, len(qtokens))
        name_cover = sum(1 for t in qtokens if t in nz.folded(name)) / max(1, len(qtokens))
        score = base + round(name_cover * 40) + round(cover * 20)
        if year and year in years:
            score += 10
        elif qyears and any(y in years for y in qyears):
            score += 10
        cls = "strict" if fid in strict_docs else ("folded" if fid in folded_docs else "fuzzy")
        why = []
        if name_cover > 0:
            why.append("ad")
        why.append({"strict": "birebir icerik", "folded": "toleransli icerik",
                    "fuzzy": "yaklasik icerik"}[cls])
        if years:
            why.append("yil:" + ",".join(years))
        results.append({
            "path": path, "name": name, "ext": fext, "label": best["label"], "page": best["page"],
            "snippet": snip.highlight(best["raw"], qtokens), "score_class": cls,
            "score": score, "why": why, "years": years,
        })
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return {"results": results[:limit], "suggestions": suggestions,
            "class_counts": counts, "empty": False}
