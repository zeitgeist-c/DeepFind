"""Recovery records and selectable model boundaries for the stability release."""
import os
import sys
import time
import uuid
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from evrakci import coordinator, migrate, schema, vault
from evrakci.migrate import ensure_v5


def test_cancelled_scan_keeps_index_and_interrupted_run_is_recovered(tmp_path, monkeypatch):
    from openpyxl import Workbook
    root = tmp_path / "archive"
    root.mkdir()
    for number in range(10):
        path = root / f"{number}.xlsx"
        book = Workbook()
        book.active.append([f"Ankara evrak {number}"])
        book.save(path)
        old = time.time() - 10
        os.utime(path, (old, old))
    db = str(tmp_path / "index.db")
    password = "sentetik-kararlilik-1234"
    con = vault.open_vault(db, password)
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v8(con)
    original = coordinator._process_job
    stopped = False

    def process(*args, **kwargs):
        nonlocal stopped
        result = original(*args, **kwargs)
        stopped = True
        return result

    monkeypatch.setattr(coordinator, "_process_job", process)
    try:
        result = coordinator.run_scan(con, db, str(root), stop=lambda: stopped, require_vectors=False)
        assert result["result"] == "cancelled" and result["done"] > 0
        row = con.execute("SELECT result, done, found FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        assert row[0] == "cancelled" and row[1] == result["done"]
        preserved = con.execute("SELECT count(*) FROM segments").fetchone()[0]
        assert preserved > 0
        con.execute("INSERT INTO scan_runs(root, started_at) VALUES (?, ?)", (str(root), int(time.time())))
        con.commit()
    finally:
        con.close()
    con = vault.open_vault(db, password)
    try:
        assert migrate.recover_scan_runs(con) == 1
        assert con.execute("SELECT result FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()[0] == "interrupted"
        assert con.execute("SELECT count(*) FROM segments").fetchone()[0] == preserved
        monkeypatch.setattr(coordinator, "_process_job", original)
        resumed = coordinator.run_scan(con, db, str(root), require_vectors=False)
        assert resumed["complete"]
        assert con.execute("SELECT count(*) FROM file_revisions WHERE active=1").fetchone()[0] == 10
    finally:
        con.close()






def test_hash_failure_marks_scan_partial(tmp_path, monkeypatch):
    from evrakci import dup
    root = tmp_path / "archive"
    root.mkdir()
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-hash-1234")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v8(con)

    def broken(*_args, **_kwargs):
        raise RuntimeError("sentetik hash hatası")

    monkeypatch.setattr(dup, "verify_pending", broken)
    try:
        result = coordinator.run_scan(con, db, str(root), require_vectors=False)
        assert result["result"] == "partial"
        assert con.execute("SELECT error_code FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()[0] == "HASH_ERROR"
    finally:
        con.close()








def test_second_launch_wakes_hidden_window():
    from concurrent.futures import ThreadPoolExecutor
    from PySide6.QtWidgets import QApplication
    from evrakci.app import _serve_activation, _wake_existing

    app = QApplication.instance() or QApplication([])

    class Window:
        calls = 0

        def _bring_forward(self):
            self.calls += 1

    window = Window()
    app._main_window = window
    server = _serve_activation(app, "Evrakci-Test-" + uuid.uuid4().hex)
    assert server is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_wake_existing, server.serverName())
            deadline = time.monotonic() + 4
            while not future.done() or window.calls == 0:
                app.processEvents()
                time.sleep(.01)
                assert time.monotonic() < deadline
            assert (future.result(), window.calls) == (True, 1)
    finally:
        server.close()
        del app._main_window
