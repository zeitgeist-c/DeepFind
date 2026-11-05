"""Odaksal daraltma (rank._odakla) mock testleri: gercek model yok.

Sozlesme:
- Daraltma yalnizca anlamsal birinci tum bilgilendirici terimleri karsiliyorsa
  ve havuzda tam-kapsamli belge varsa uygulanir.
- Diger durumda saf anlamsal sira korunur.
- Sayfa/boyut degisince liste degismez (tekrar/kayip yok).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import embed, rank  # noqa: E402
from test_hibrit import _dosya, _kasa  # noqa: E402


def _vektor_ata(con, dosya_adi, v):
    sid = con.execute(
        "SELECT s.seg_id FROM segments s JOIN files f ON f.file_id=s.file_id "
        "WHERE f.name=? AND s.kind NOT IN ('name_only','context')",
        (dosya_adi,)).fetchone()[0]
    vv = np.zeros(embed.DIM, dtype=np.float32)
    vv[:len(v)] = np.asarray(v, dtype=np.float32)
    con.execute("INSERT INTO embeddings(seg_id, model_ver, dim, vec) VALUES (?,?,?,?)",
                (sid, embed.MODEL_VER, embed.DIM, vv.tobytes()))
    con.commit()


def _duzen(con):
    _dosya(con, "hedef.txt", "Ahmet Öz vekaletname noter tasdik")
    _dosya(con, "yanlis.txt", "Ahmet Öz fatura ödeme fiş")
    _dosya(con, "varyant.txt", "Ahmet Öz İnşaat vekalet belgesi tapu")
    _vektor_ata(con, "hedef.txt", [1.0, 0.0, 0.0])
    _vektor_ata(con, "yanlis.txt", [0.9, 0.1, 0.0])
    _vektor_ata(con, "varyant.txt", [0.8, 0.2, 0.0])


def _kodla(v):
    vv = np.zeros(embed.DIM, dtype=np.float32)
    vv[:len(v)] = np.asarray(v, dtype=np.float32)
    return lambda metinler: np.tile(vv, (len(metinler), 1))


def test_tam_kapsamli_birinci_daraltir(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    sonuc = rank.search_semantic(con, "Ahmet Öz vekaletname", limit=10,
                                 kodla=_kodla([1.0, 0.0, 0.0]))
    adlar = [r["name"] for r in sonuc["results"]]
    # hedef ve varyant tum terimleri karsilar; yanlis (vekaletname yok) elenir.
    assert adlar == ["hedef.txt", "varyant.txt"], adlar
    assert sonuc["has_more"] is False
    con.close()


def test_kismi_kapsamli_birinci_daraltmaz(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    # Sorgu vektoru yanlis belgeye yakin: anlamsal birinci kismi kapsamli.
    sonuc = rank.search_semantic(con, "Ahmet Öz vekaletname", limit=10,
                                 kodla=_kodla([0.9, 0.1, 0.0]))
    adlar = [r["name"] for r in sonuc["results"]]
    assert adlar[0] == "yanlis.txt"
    assert set(adlar) == {"hedef.txt", "yanlis.txt", "varyant.txt"}, adlar
    con.close()


def test_daraltmada_sayfalama_tutarli(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    k = _kodla([1.0, 0.0, 0.0])
    s1 = rank.search_semantic(con, "Ahmet Öz vekaletname", limit=1, offset=0, kodla=k)
    s2 = rank.search_semantic(con, "Ahmet Öz vekaletname", limit=1, offset=1, kodla=k)
    tum = rank.search_semantic(con, "Ahmet Öz vekaletname", limit=50, kodla=k)
    assert [r["name"] for r in s1["results"]] + [r["name"] for r in s2["results"]] == \
           [r["name"] for r in tum["results"]]
    assert s1["has_more"] is True and s2["has_more"] is False
    con.close()


def test_tek_terimde_daraltma_yok(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    sonuc = rank.search_semantic(con, "vekaletname", limit=10,
                                 kodla=_kodla([1.0, 0.0, 0.0]))
    assert {r["name"] for r in sonuc["results"]} == {"hedef.txt", "yanlis.txt", "varyant.txt"}
    con.close()
