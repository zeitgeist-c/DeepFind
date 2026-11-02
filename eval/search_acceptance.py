"""Cok kelimeli arama kabul testi: gercek model, sentetik belgeler.

Olcum:
- "Ahmet Oz vekaletname" sorgusunda kisi + belge turu birlikte degerlendirilmeli.
- Yalniz Ahmet, yalniz Oz veya yalniz vekaletname gecen belgeler sonucu doldurmamali.
- Turkce karakterler, buyuk/kucuk harf, farkli sozcuk sirasi, dogal anlatim.
- Tek kelime sorgu, sonuc bulunmamasi ve sayfalama ayrica kontrol edilir.

Kullanim: PYTHONPATH=src python eval/search_acceptance.py [--cikti build/search-acceptance.json]
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from deepfind import engine, embed, migrate, rank, schema, vault  # noqa: E402

# Paketli surumun gercek motor/model dizini (kaynak agacinda motor yok).
VARLIK_DIZINI = ROOT / "dist" / "DeepFind-0.10.9" / "_internal" / "embedding"
MODEL_GGUF = VARLIK_DIZINI / "embeddinggemma-2-Q8_0.gguf"

# Sentetik belgeler: (anahtar, dosya adi, metin)
BELGELER = [
    ("hedef", "ahmet-oz-vekaletname.txt",
     "VEKÂLETNAME. Ben Ahmet Öz, ... Öz Yapı Ltd. Şti. adına ... her türlü işlemi "
     "yapmak üzere avukat Selin Aydın'ı vekil tayin ettim. Vekâlet veren: Ahmet Öz."),
    ("yanlis_tur", "ahmet-oz-fatura.txt",
     "FATURA. Ahmet Öz adına düzenlenen 2024 yılı hizmet bedeli faturası. "
     "Fatura tutarı 12.500 TL, KDV dahil. Öz Yapı Ltd. Şti."),
    ("yanlis_kisi", "mehmet-kaya-vekaletname.txt",
     "VEKÂLETNAME. Ben Mehmet Kaya, ... Kaya İnşaat adına ... avukat Selin Aydın'ı "
     "vekil tayin ettim. Vekâlet veren: Mehmet Kaya."),
    ("benzer_kisi", "ahmet-demir-vekaletname.txt",
     "VEKÂLETNAME. Ben Ahmet Demir, ... Demir Turizm adına ... avukat Selin Aydın'ı "
     "vekil tayin ettim. Vekâlet veren: Ahmet Demir."),
    ("ilgisiz", "is-guvenligi-denetim.txt",
     "İŞ SAĞLIĞI VE GÜVENLİĞİ DENETİM RAPORU. Şantiyede kişisel koruyucu donanım "
     "kullanımı incelendi; eksiklikler ve öneriler listelenmiştir."),
    ("hedef_varyant", "oz-insaat-vekalet-belgesi.txt",
     "Öz İnşaat adına işlem yapabilmesi için Ahmet Öz tarafından düzenlenmiş vekâlet "
     "belgesi; yetki kapsamı tapu ve banka işlemlerini kapsar."),
]

SORULAR = [
    ("Ahmet Öz vekâletname", {"hedef"}),
    ("vekâletname Ahmet Öz", {"hedef"}),
    ("Ahmet Öz'ün vekâletnamesi", {"hedef"}),
    ("ahmet oz vekaletname", {"hedef"}),          # diakritiksiz / küçük harf
    ("AHMET ÖZ VEKÂLETNAME", {"hedef"}),          # büyük harf
    ("Öz İnşaat vekâlet belgesi", {"hedef_varyant"}),
]


def _kasa(klasor):
    con = vault.open_vault(str(Path(klasor) / "arama.db"), "arama-testi-1234")
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    return con


def _doldur(con, kodla):
    metinler = [metin for _k, _n, metin in BELGELER]
    vektorler = kodla(metinler)
    for i, (anahtar, ad, metin) in enumerate(BELGELER):
        con.execute("INSERT INTO files(path, name, ext, source_status, index_status) VALUES (?,?,?, 'ok','indexed')",
                    (f"C:/sentetik/{ad}", ad, ".txt"))
        fid = con.execute("SELECT file_id FROM files WHERE name=?", (ad,)).fetchone()[0]
        con.execute("INSERT INTO segments(file_id, kind, page, label, raw_text) VALUES (?,?,?,?,?)",
                    (fid, "body", 1, "gövde", metin))
        sid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("INSERT INTO embeddings(seg_id, model_ver, dim, vec) VALUES (?,?,?,?)",
                    (sid, embed.MODEL_VER, embed.DIM,
                     np.asarray(vektorler[i], dtype=np.float32).tobytes()))
    con.commit()


def _ad(con, file_id):
    satir = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()
    ad = satir[0] if satir else "?"
    for anahtar, dosya, _m in BELGELER:
        if dosya == ad:
            return anahtar
    return ad


def kos(kodla, con):
    rapor = []
    for sorgu, beklenen in SORULAR:
        out = rank.search_semantic(con, sorgu, limit=10, kodla=kodla)
        satirlar = [dict(anahtar=_ad(con, r["file_id"]), skor=r["score"],
                         vec=r["vec_skor"]) for r in out["results"]]
        ilk = satirlar[0]["anahtar"] if satirlar else None
        rapor.append(dict(sorgu=sorgu, beklenen=sorted(beklenen), ilk=ilk,
                          dogru=ilk in beklenen, sonuclar=satirlar,
                          dolgu=[s["anahtar"] for s in satirlar[1:]]))
    # Tek kelime, sonuc bulunmama ve sayfalama davranisi
    tek = rank.search_semantic(con, "vekâletname", limit=10, kodla=kodla)
    bos = rank.search_semantic(con, "kuantum bilgisayar kriyojenik soğutucu", limit=10, kodla=kodla)
    sayfa1 = rank.search_semantic(con, "vekâletname", limit=2, offset=0, kodla=kodla)
    sayfa2 = rank.search_semantic(con, "vekâletname", limit=2, offset=2, kodla=kodla)
    ozel = dict(
        tek_kelime=[_ad(con, r["file_id"]) for r in tek["results"]],
        ilgisiz_sorgu=[_ad(con, r["file_id"]) for r in bos["results"]],
        sayfalama=dict(sayfa1=[_ad(con, r["file_id"]) for r in sayfa1["results"]],
                       sayfa2=[_ad(con, r["file_id"]) for r in sayfa2["results"]],
                       has_more1=sayfa1["has_more"]),
    )
    return rapor, ozel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", default=str(ROOT / "build" / "search-acceptance.json"))
    ap.add_argument("--model", default=str(MODEL_GGUF))
    ap.add_argument("--varlik", default=str(VARLIK_DIZINI))
    args = ap.parse_args()
    assert Path(args.model).is_file(), f"gerçek model bulunamadı: {args.model}"
    # Kaynak agacinda llama-server yok: paketin motor dizinini kullan.
    engine.asset_root = lambda: Path(args.varlik)
    oturum = engine.Oturum(args.model, backend="cpu")
    try:
        kodla = lambda texts: oturum.encode(texts, gorev="sorgu")  # noqa: E731
        with tempfile.TemporaryDirectory() as klasor:
            con = _kasa(klasor)
            _doldur(con, kodla)
            rapor, ozel = kos(kodla, con)
            con.close()
    finally:
        oturum.close()
    sonuc = dict(model=str(Path(args.model).name), backend="cpu", sorgular=rapor, ozel=ozel,
                 dogru=sum(1 for r in rapor if r["dogru"]), toplam=len(rapor))
    Path(args.cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(args.cikti).write_text(json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(sonuc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
