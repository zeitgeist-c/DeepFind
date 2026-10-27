"""Toplu etiket okuma: N+1 yerine tek sorgu."""
import sqlite3

from deepfind import rank


def _con():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE file_tags(file_id INTEGER, tag TEXT)")
    for fid in range(1, 4):
        con.execute("INSERT INTO file_tags VALUES (?,?)", (fid, f"etiket{fid}"))
        con.execute("INSERT INTO file_tags VALUES (?,?)", (fid, "ortak"))
    con.commit()
    return con


def test_tags_many_map_tek_sorgu_ile_ayni_sonuc():
    con = _con()
    try:
        harita = rank.tags_many_map(con, [1, 2, 3])
        for fid in (1, 2, 3):
            assert harita[fid] == rank.file_tags(con, fid)
    finally:
        con.close()


def test_tags_many_map_tekrarlanan_ve_bos_idler():
    con = _con()
    try:
        assert rank.tags_many_map(con, [1, 1, None]) == {1: ["etiket1", "ortak"]}
        assert rank.tags_many_map(con, []) == {}
        assert rank.tags_many_map(con, [999]) == {}
    finally:
        con.close()


def test_tags_many_map_tablo_yoksa_bos():
    con = sqlite3.connect(":memory:")
    try:
        assert rank.tags_many_map(con, [1, 2]) == {}
    finally:
        con.close()


def test_results_csv_etiketleri_toplu_okur():
    con = _con()
    try:
        out = rank.results_csv(con, [
            dict(name="a.pdf", path="C:/a.pdf", ext=".pdf", file_id=1),
            dict(name="b.pdf", path="C:/b.pdf", ext=".pdf", file_id=2),
        ])
        satirlar = out.strip().splitlines()
        assert "etiket1, ortak" in satirlar[1]
        assert "etiket2, ortak" in satirlar[2]
    finally:
        con.close()
