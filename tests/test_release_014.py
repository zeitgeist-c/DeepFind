"""0.1.4: gerçek hata tetikleyicileri ve kapsam/iptal sınırları."""
import os
import sys
import time
from pathlib import Path
import threading

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from evrakci import coordinator, vault, schema, migrate, job_queue as queue, remember
from evrakci.vocab import ensure_v5

PW = "sentetik-surum-test-1234"


def database(tmp_path):
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v7(con)
    return con, db


def source(path):
    from openpyxl import Workbook
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.active.append(["Ankara denetim"])
    wb.save(path)
    old = time.time() - 10
    os.utime(path, (old, old))


def test_discovery_processes_before_all_files_found_and_scopes_queue(tmp_path, monkeypatch):
    root = tmp_path / "selected"
    for i in range(40):
        source(root / f"{i}.xlsx")
    other = tmp_path / "other" / "outside.xlsx"
    source(other)
    con, db = database(tmp_path)
    try:
        stat = other.stat()
        fid = coordinator.ensure_file(con, coordinator.scan_mod.Entry(str(other), other.name, '.xlsx', stat.st_size, stat.st_mtime_ns))
        queue.enqueue(con, fid, queue.signature_of(stat.st_size, stat.st_mtime_ns))
        con.commit()
        snapshots = []
        discovered_when_processing = []
        original = coordinator._process_job
        def process(*args, **kwargs):
            discovered_when_processing.append(con.execute("SELECT count(*) FROM scan_selected").fetchone()[0])
            return original(*args, **kwargs)
        monkeypatch.setattr(coordinator, '_process_job', process)
        result = coordinator.run_scan(con, db, str(root), progress=snapshots.append)
        assert result['done'] == 40 and result['complete']
        assert min(discovered_when_processing) < 40
        assert snapshots[-1]['done'] == 40
        assert con.execute("SELECT status FROM jobs WHERE file_id=?", (fid,)).fetchone()[0] == 'pending'
        assert not con.execute("SELECT 1 FROM segments WHERE file_id=?", (fid,)).fetchone()
        assert len(list(root.glob('*.xlsx'))) == 40
    finally:
        con.close()


def test_cancel_preserves_completed_files_and_pending_work(tmp_path, monkeypatch):
    root = tmp_path / 'archive'
    for i in range(40):
        source(root / f'{i}.xlsx')
    con, db = database(tmp_path)
    cancel = threading.Event()
    try:
        original = coordinator._process_job
        def process(*args, **kwargs):
            result = original(*args, **kwargs)
            cancel.set()
            return result
        monkeypatch.setattr(coordinator, '_process_job', process)
        result = coordinator.run_scan(con, db, str(root), stop=cancel.is_set)
        assert result['result'] == 'cancelled' and result['done'] > 0
        assert con.execute('SELECT count(*) FROM segments').fetchone()[0] > 0
        assert result['missing'] == 0
        monkeypatch.setattr(coordinator, '_process_job', original)
        resumed = coordinator.run_scan(con, db, str(root))
        assert resumed['complete']
    finally:
        con.close()


def test_remember_encrypted_revocable(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    db = str(tmp_path / 'sample.db')
    remember.save(db, PW)
    assert PW.encode() not in remember._path(db).read_bytes()
    assert remember.load(db) == PW
    remember.forget(db)
    assert remember.load(db) is None and not remember.enabled(db)


def test_worker_pause_resume_and_cancel():
    from evrakci.app import TaramaIsci
    worker = TaramaIsci('not-opened', PW, [])
    worker.paused.set()
    returned = threading.Event()
    thread = threading.Thread(target=lambda: (worker.stop_requested(), returned.set()))
    thread.start()
    assert not returned.wait(0.2)
    worker.paused.clear()
    assert returned.wait(1)
    thread.join()
    worker.paused.set()
    worker.durdur()
    assert worker.stop_requested()
