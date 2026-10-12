"""Kota/manifest: bolumlu tarama testleri (FAZ 2)."""
import os

from test_scan_resume import database

from evrakci import coordinator as C
from evrakci import queue as q


def test_manifest_counts_total_before_work(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 a")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 b")
    (tmp_path / "yok.rar").write_bytes(b"desteklenmiyor")
    con = database(tmp_path / "kasa.db")
    try:
        _rid, total = C.build_manifest(con, str(tmp_path))
        assert total == 2
        assert con.execute("SELECT count(*) FROM scan_manifest").fetchone()[0] == 2
    finally:
        con.close()


def _xlsx(path, rows=3):
    from openpyxl import Workbook
    wb = Workbook()
    for i in range(rows):
        wb.active.append([f"kayit {i}"])
    wb.save(path)


def test_batch_limit_processes_at_most_n(tmp_path):
    import time as _time
    root = tmp_path / "kaynak"
    root.mkdir()
    for n in range(3):
        _xlsx(root / f"f{n}.xlsx")
    past = _time.time() - 10
    for p in root.iterdir():
        os.utime(p, (past, past))
    con = database(tmp_path / "kasa.db")
    try:
        stats = C.run_scan(con, str(tmp_path / "kasa.db"), str(root), limit=1)
        assert stats["done"] == 1
        assert stats["result"] == "partial"
        assert q.pending_count(con) >= 1
        stats2 = C.run_scan(con, str(tmp_path / "kasa.db"), str(root))
        assert stats2["done"] >= 2
        assert q.pending_count(con) == 0
    finally:
        con.close()


def test_daily_quota_blocks_second_run(tmp_path):
    from evrakci import migrate as M
    from evrakci import sched
    con = database(tmp_path / "kasa.db")
    try:
        assert sched.quota_left(con, "2026-10-12") is None  # ayar yoksa sinirsiz
        M.set_setting(con, "gunluk_kota", "100")
        M.set_setting(con, "kota_tuketilen_2026-10-12", "100")
        assert sched.quota_left(con, "2026-10-12") == 0
        M.set_setting(con, "kota_tuketilen_2026-10-12", "30")
        assert sched.quota_left(con, "2026-10-12") == 70
    finally:
        con.close()


def test_manifest_exports_md(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 a")
    con = database(tmp_path / "kasa.db")
    try:
        from evrakci import manifest_export as me
        rid, total = C.build_manifest(con, str(tmp_path))
        text = me.render_md(con, rid)
        assert total == 1
        assert "toplam 1" in text and "a.pdf" in text
        out = tmp_path / "manifest.md"
        out.write_text(text, encoding="utf-8")
        assert out.read_text(encoding="utf-8") == text
    finally:
        con.close()
