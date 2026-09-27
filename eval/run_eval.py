"""A5 kalite eval: corpus tara, holdout ayir, top1/top3 + sure raporu. Cikis: rapor + exit kodu."""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from corpus import build, make_queries  # noqa: E402
from evrakci import coordinator, rank, schema, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.vocab import ensure_v5, rebuild_vocab  # noqa: E402

PW = "eval-sifresi-12345"
HOLDOUT = 0.20


def main() -> int:
    base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Temp", "evrakci_eval")
    base = os.path.abspath(base)
    kok = os.path.join(base, "corpus")
    db = os.path.join(base, "kasa.db")
    for f in (db, db + "-wal", db + "-shm", db + "-journal"):
        if os.path.exists(f):
            os.remove(f)
    recs = build(kok)
    time.sleep(2.5)
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v6(con)
    ensure_v5(con)
    t0 = time.perf_counter()
    stats = coordinator.run_scan(con, db, kok)
    tara_sn = time.perf_counter() - t0
    rebuild_vocab(con)

    scored = [q for q in make_queries(recs) if q[2] not in ("bos",)]
    rng = random.Random(5)
    idx = list(range(len(scored)))
    rng.shuffle(idx)
    n_hold = max(1, int(len(scored) * HOLDOUT))
    hold = set(idx[:n_hold])
    ayar = [q for i, q in enumerate(scored) if i not in hold]
    hold_q = [q for i, q in enumerate(scored) if i in hold]

    def beklenen_kontrol(sorgu, beklenen, grup, sonuclar):
        adlar = [r["name"] for r in sonuclar]
        if beklenen is None:
            return (None, None)  # no-result: ayri kontrol
        if beklenen.startswith("YILSET:"):
            _, yil, tur = beklenen.split(":")
            ok = any(yil in (r.get("years") or []) and tur in r["name"] for r in sonuclar)
            return ok, ok
        t1 = beklenen in adlar[:1]
        t3 = beklenen in adlar[:3]
        return t1, t3

    def kos(qs):
        det = []
        for sorgu, beklenen, grup in qs:
            a = time.perf_counter()
            out = rank.search_ranked(con, sorgu)
            dt = (time.perf_counter() - a) * 1000
            res = out["results"]
            if beklenen is None:
                ok = (res == [])
                det.append({"q": sorgu, "grup": grup, "no_result_ok": ok, "ms": round(dt, 1)})
            else:
                t1, t3 = beklenen_kontrol(sorgu, beklenen, grup, res)
                det.append({"q": sorgu, "grup": grup, "top1": t1, "top3": t3,
                            "bulunan": res[0]["name"] if res else None,
                            "sinif": res[0]["score_class"] if res else None,
                            "ms": round(dt, 1)})
        return det

    d_ayar, d_hold = kos(ayar), kos(hold_q)
    con.close()

    def ozet(det):
        puanli = [d for d in det if "top1" in d]
        nr = [d for d in det if "no_result_ok" in d]
        ms = [d["ms"] for d in det]
        ms_sorted = sorted(ms)
        p95 = ms_sorted[max(0, int(len(ms_sorted) * 0.95) - 1)] if ms_sorted else 0
        return {
            "n": len(det), "puanli": len(puanli),
            "top1": round(sum(d["top1"] for d in puanli) / max(1, len(puanli)), 3),
            "top3": round(sum(d["top3"] for d in puanli) / max(1, len(puanli)), 3),
            "no_result": [d["q"] for d in nr if not d["no_result_ok"]],
            "p50_ms": round(statistics.median(ms), 1) if ms else 0,
            "p95_ms": round(p95, 1),
        }

    rapor = {"belge": len(recs), "tara_sn": round(tara_sn, 1), "tarama": stats,
             "ayar": ozet(d_ayar), "holdout": ozet(d_hold),
             "ayar_detay": d_ayar, "holdout_detay": d_hold}
    rp = os.path.join(base, "eval_rapor.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(f"belge={len(recs)} tara={tara_sn:.1f}sn", flush=True)
    for k in ("ayar", "holdout"):
        o = rapor[k]
        print(f"{k}: n={o['n']} top1={o['top1']} top3={o['top3']} "
              f"no_result_hatali={o['no_result']} p50={o['p50_ms']}ms p95={o['p95_ms']}ms", flush=True)
    for d in d_ayar + d_hold:
        if "top1" in d and not d["top3"]:
            print(f"  ISKARTA [{d['grup']}] {d['q']!r} -> {d['bulunan']} ({d['sinif']})", flush=True)
    ok = rapor["holdout"]["top3"] >= 0.90 and not rapor["holdout"]["no_result"]
    print("KAPI: " + ("GECTI" if ok else "KALDI"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
