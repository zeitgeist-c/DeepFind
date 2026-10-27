"""Gom semasi testleri (FAZ 2)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import embed, vault  # noqa: E402
from deepfind import migrate as migrate_mod  # noqa: E402

PW = "test-sifresi-12345"


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    migrate_mod.ensure_current(con)
    con.commit()
    return con


def test_gom_tablosu_var(tmp_path):
    con = _kasa(tmp_path)
    ad = con.execute(
        "SELECT name FROM sqlite_master WHERE name='embeddings'").fetchone()
    assert ad is not None
    con.close()


def test_model_ver_isaretli(tmp_path):
    con = _kasa(tmp_path)
    satir = con.execute(
        "SELECT v FROM schema_meta WHERE k='embed_model_ver'").fetchone()
    assert satir is not None and satir[0] == embed.MODEL_VER
    con.close()


def _dosya(con, ad="belge.txt", metin="elektrik faturasi tutar 1.250 TL"):
    from deepfind import extract as ex_mod
    from deepfind import index as index_mod
    from deepfind import scan as scan_mod

    giris = scan_mod.Entry(ad, ad, ".txt", 10, 20)
    sonuc = ex_mod.ExtractResult(
        segments=[ex_mod.Segment("para", None, "Govde", metin)], status="ok")
    return index_mod.index_entry(con, giris, sonuc)


def _sabit_kodla(n=256):
    import numpy as np

    def kodla(metinler):
        v = np.zeros((len(metinler), n), dtype=np.float32)
        for i, t in enumerate(metinler):
            v[i, abs(hash(t)) % n] = 1.0
        return v

    return kodla


def test_isle_dosya_yazar(tmp_path):
    from deepfind import gom

    con = _kasa(tmp_path)
    fid = _dosya(con)
    yazilan = gom.isle_dosya(con, fid, _sabit_kodla())
    assert yazilan == 1
    satir = con.execute(
        "SELECT model_ver, dim, length(vec) FROM embeddings").fetchone()
    assert satir == (embed.MODEL_VER, 256, 256 * 4)
    con.close()


def test_eski_surum_temizlenir(tmp_path):
    from deepfind import gom

    con = _kasa(tmp_path)
    fid = _dosya(con)
    seg = con.execute("SELECT seg_id FROM segments").fetchone()[0]
    con.execute("INSERT INTO embeddings VALUES (?,?,?,?)",
                (seg, "eski-surum", 256, b"\x00" * 1024))
    con.commit()
    gom.isle_dosya(con, fid, _sabit_kodla())
    satirlar = con.execute("SELECT DISTINCT model_ver FROM embeddings").fetchall()
    assert satirlar == [(embed.MODEL_VER,)]
    con.close()


def test_bos_govde_etiketle_yazilir(tmp_path):
    from deepfind import gom

    con = _kasa(tmp_path)
    fid = _dosya(con, metin="")
    # Govde bos ama "Govde" etiketi var: aranabilir kalsin diye yazilir.
    assert gom.isle_dosya(con, fid, _sabit_kodla()) == 1
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 1
    con.close()


def test_imza_degismis_ise_yeniden_kuyruk(tmp_path):
    from deepfind import gom

    con = _kasa(tmp_path)
    fid = _dosya(con)
    con.execute("UPDATE files SET size=99 WHERE file_id=?", (fid,))
    con.commit()
    isonuc = gom.process_embed_job(
        con, {"job_id": 7, "file_id": fid, "signature": "10:20"},
        kodla=_sabit_kodla())
    assert isonuc == "changed"
    bekleyen = con.execute(
        "SELECT count(*) FROM jobs WHERE kind='embed'").fetchone()[0]
    assert bekleyen == 1
    con.close()


def test_model_kapisi():
    import os

    from deepfind import gom

    assert gom.model_var_mi(__file__) is True
    assert gom.model_var_mi(os.path.join("yok", "boyle-bir-dosya.onnx")) is False


def test_vektor_yaz_dagitir(tmp_path):
    import numpy as np

    from deepfind import gom

    con = _kasa(tmp_path)
    fid = _dosya(con)
    ciftler = gom._metinler(con, fid)
    assert len(ciftler) == 1
    v = np.zeros((1, 256), dtype=np.float32)
    v[0, 5] = 1.0
    assert gom.vektor_yaz(con, ciftler, v) == 1
    satir = con.execute("SELECT dim, length(vec) FROM embeddings").fetchone()
    assert satir == (256, 1024)
    con.close()


def test_alt_surec_gom():
    if not os.environ.get("DEEPFIND_GERCEK_MODEL") == "1":
        return
    from deepfind import embed
    from deepfind.workers import WorkerSession

    sess = WorkerSession()
    try:
        sonuc = sess.call("gom", (embed._varsayilan_model_yolu(),
                                  ["elektrik faturasi", "kira sozlesmesi"]),
                          timeout=600)
        assert len(sonuc["vektorler"]) == 2
        assert len(sonuc["vektorler"][0]) == 256
    finally:
        sess.kill()
