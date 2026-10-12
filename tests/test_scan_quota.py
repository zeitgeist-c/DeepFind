"""Kota/manifest: bolumlu tarama testleri (FAZ 2)."""
import os

from test_scan_resume import database

from evrakci import coordinator as C
from evrakci import queue as q


def test_manifest_counts_total_before_work(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 a")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 b")
    (tmp_path / "yok.txt").write_bytes(b"desteklenmiyor")
    con = database(tmp_path / "kasa.db")
    try:
        _rid, total = C.build_manifest(con, str(tmp_path))
        assert total == 2
        assert con.execute("SELECT count(*) FROM scan_manifest").fetchone()[0] == 2
    finally:
        con.close()
