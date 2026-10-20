"""Hibrit arama testleri (FAZ 3)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import embed, rank, vault  # noqa: E402
from evrakci import migrate as migrate_mod  # noqa: E402

PW = "test-sifresi-12345"


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    migrate_mod.ensure_current(con)
    con.commit()
    return con


def _dosya(con, ad, metin):
    from evrakci import extract as ex_mod
    from evrakci import index as index_mod
    from evrakci import scan as scan_mod

    giris = scan_mod.Entry(ad, ad, ".txt", 10, 20)
    sonuc = ex_mod.ExtractResult(
        segments=[ex_mod.Segment("para", None, "Govde", metin)], status="ok")
    return index_mod.index_entry(con, giris, sonuc)


def _vektor(con, metin_parcasi, deger):
    import numpy as np

    seg = con.execute(
        "SELECT seg_id FROM segments WHERE raw_text LIKE ?"
        " AND kind NOT IN ('name_only','context')",
        ("%" + metin_parcasi + "%",)).fetchone()[0]
    v = np.zeros(256, dtype=np.float32)
    v[deger] = 1.0
    con.execute("INSERT INTO embeddings VALUES (?,?,?,?)",
                (seg, embed.MODEL_VER, 256, v.tobytes()))
    con.commit()


def _duzen(con):
    _dosya(con, "a_belge.txt", "kedi mamasi ve su kabı")
    _dosya(con, "b_belge.txt", "kedi tasması ve oyuncak")
    _vektor(con, "mamasi", 0)
    _vektor(con, "tasması", 1)


def _kodla_b(metinler):
    import numpy as np

    v = np.zeros((len(metinler), 256), dtype=np.float32)
    v[:, 1] = 1.0
    return v


def test_hibrit_vektorle_yeniden_siralar(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    sonuc = rank.search_hybrid(con, "kedi", kodla=_kodla_b)
    assert sonuc["results"]
    assert sonuc["results"][0]["name"] == "b_belge.txt"
    con.close()


def test_hibrit_vektor_yoksa_fts_doner(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    con.execute("DELETE FROM embeddings")
    con.commit()
    hibrit = rank.search_hybrid(con, "kedi", kodla=_kodla_b)
    duz = rank.search_ranked(con, "kedi")
    assert [r["name"] for r in hibrit["results"]] == [r["name"] for r in duz["results"]]
    con.close()


def test_hibrit_bicim_sozlesmesi(tmp_path):
    con = _kasa(tmp_path)
    _duzen(con)
    sonuc = rank.search_hybrid(con, "kedi", kodla=_kodla_b)
    assert set(sonuc) >= {"results", "suggestions", "class_counts", "empty", "has_more", "offset"}
    ilk = sonuc["results"][0]
    assert set(ilk) >= {"file_id", "path", "name", "score", "score_class", "snippet", "why"}
    con.close()
