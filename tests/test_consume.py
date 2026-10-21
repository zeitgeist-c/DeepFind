"""Tüketim klasörü: kararlı dosya hedefe taşınır, indeks normal taramaya kalır."""
import os
import time

from evrakci import consume


def test_tuket_tasir(tmp_path):
    import sqlite3
    from evrakci import migrate, schema
    from evrakci.migrate import ensure_v5
    gelen = tmp_path / "gelen"
    gelen.mkdir()
    hedef = tmp_path / "arsiv"
    hedef.mkdir()
    dosya = gelen / "fatura.pdf"
    dosya.write_bytes(b"%PDF-1.4 x")
    past = time.time() - 10
    os.utime(dosya, (past, past))
    con = sqlite3.connect(str(tmp_path / "kasa.db"))
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    try:
        assert consume.tuket(con, str(dosya), str(hedef)) == "moved"
        assert not dosya.exists()
        assert (hedef / "fatura.pdf").exists()
    finally:
        con.close()


def test_tuket_cakisansa_numara_verir(tmp_path):
    import sqlite3
    from evrakci import migrate, schema
    from evrakci.migrate import ensure_v5
    gelen = tmp_path / "gelen"
    gelen.mkdir()
    hedef = tmp_path / "arsiv"
    hedef.mkdir()
    (hedef / "fatura.pdf").write_bytes(b"eski")
    dosya = gelen / "fatura.pdf"
    dosya.write_bytes(b"%PDF-1.4 yeni")
    past = time.time() - 10
    os.utime(dosya, (past, past))
    con = sqlite3.connect(str(tmp_path / "kasa.db"))
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    try:
        assert consume.tuket(con, str(dosya), str(hedef)) == "moved"
        assert (hedef / "fatura (2).pdf").exists()
    finally:
        con.close()


def test_tuket_kararsiz_ve_desteksiz_bekler(tmp_path):
    import sqlite3
    from evrakci import migrate, schema
    from evrakci.migrate import ensure_v5
    gelen = tmp_path / "gelen"
    gelen.mkdir()
    hedef = tmp_path / "arsiv"
    hedef.mkdir()
    taze = gelen / "taze.pdf"
    taze.write_bytes(b"%PDF-1.4 x")
    exe = gelen / "kur.exe"
    exe.write_bytes(b"MZ")
    con = sqlite3.connect(str(tmp_path / "kasa.db"))
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    try:
        assert consume.tuket(con, str(taze), str(hedef)) == "unstable"
        assert taze.exists()
        assert consume.tuket(con, str(exe), str(hedef)) == "skipped"
        assert exe.exists()
    finally:
        con.close()
