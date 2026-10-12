"""Canlı izleme testleri: saf mantık + Win32 duman (Windows)."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import watch


def test_onemli_mi_gecicileri_eler():
    assert watch.onemli_mi("C:/a/belge.pdf")
    assert not watch.onemli_mi("C:/a/~$belge.docx")
    assert not watch.onemli_mi("C:/a/kilit.lock")
    assert not watch.onemli_mi("C:/a/yedek.tmp")


def test_coalesce_ust_klasore_indirger(tmp_path):
    kok = str(tmp_path)
    a = os.path.join(kok, "a")
    b = os.path.join(kok, "a", "alt")
    c = os.path.join(kok, "diger")
    assert watch.coalesce([a, b, c], [kok]) == sorted([a, c])


def test_coalesce_kok_disini_atar(tmp_path):
    assert watch.coalesce([str(tmp_path / "a"), "C:/baska/yol"], [str(tmp_path)]) == [str(tmp_path / "a")]


def test_coalesce_tasinca_koku_ister(tmp_path):
    kok = str(tmp_path)
    dirs = [os.path.join(kok, f"d{i}") for i in range(watch.COALESCE_LIMIT + 5)]
    assert watch.coalesce(dirs, [kok]) == [kok]


def test_debounce_suresi_dolmadan_bildirmez(tmp_path):
    gelen = []
    iz = watch.Izleyici(str(tmp_path), gelen.append)
    iz.bildir([str(tmp_path / "a.pdf")], simdi=100.0)
    assert iz.bosalt(simdi=100.0 + watch.DEBOUNCE_SEC - 1) == []
    assert gelen == []
    due = iz.bosalt(simdi=100.0 + watch.DEBOUNCE_SEC)
    assert due == [str(tmp_path)]
    assert gelen == [[str(tmp_path)]]


@pytest.mark.skipif(os.name != "nt", reason="Win32 izleme")
def test_win32_olay_gelir(tmp_path):
    iz = watch.Izleyici(str(tmp_path), lambda dirs: None)
    iz.start()
    try:
        # İlk dosya izleme başlamadan düşebilir; birkaç kez dene.
        deadline = time.monotonic() + 15
        n = 0
        while time.monotonic() < deadline:
            n += 1
            (tmp_path / f"yeni{n}.pdf").write_bytes(b"%PDF-1.4 x")
            time.sleep(1.5)
            with iz._kilit:
                if iz._bekleyen:
                    break
        with iz._kilit:
            assert iz._bekleyen, "Win32 olay üretmedi"
    finally:
        iz.durdur()
        iz.join(timeout=10)
        assert not iz.is_alive()


def test_izleme_taramayi_tetikler(tmp_path, monkeypatch):
    """Uçtan uca (arayıssız): olay -> debounce -> kapsamlı tarama -> indeks."""
    import sqlite3
    import time as _time
    from openpyxl import Workbook
    from evrakci import coordinator as C
    from evrakci import migrate, schema
    from evrakci.vocab import ensure_v5
    monkeypatch.setattr(watch, "DEBOUNCE_SEC", 1)
    root = tmp_path / "kaynak"
    root.mkdir()
    con = sqlite3.connect(str(tmp_path / "kasa.db"))
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    try:
        db = str(tmp_path / "kasa.db")

        def tara(dirs):
            c2 = sqlite3.connect(db)
            try:
                C.run_scan(c2, db, dirs[0])
            finally:
                c2.close()

        iz = watch.Izleyici(str(root), tara)
        iz.start()
        try:
            wb = Workbook()
            wb.active.append(["izlenen kayıt"])
            wb.save(root / "a.xlsx")
            past = _time.time() - 10
            import os as _os
            _os.utime(root / "a.xlsx", (past, past))
            deadline = _time.monotonic() + 30
            while _time.monotonic() < deadline:
                time.sleep(1)
                if con.execute("SELECT count(*) FROM segments").fetchone()[0]:
                    break
            assert "izlenen" in con.execute("SELECT raw_text FROM segments").fetchone()[0]
        finally:
            iz.durdur()
            iz.join(timeout=10)
    finally:
        con.close()
