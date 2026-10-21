import sqlite3
import pytest
from evrakci import migrate, schema, normalize


def populated():
    con = sqlite3.connect(':memory:')
    migrate.ensure_current(con)
    fid = con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/x','x','.txt')").lastrowid
    con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'body','Sayfa','Şırnak sözleşme')", (fid,))
    con.commit()
    return con


def test_current_vault_never_rebuilds_index_on_reopen():
    con = populated()
    trace = []
    con.set_trace_callback(trace.append)
    for _ in range(3):
        migrate.ensure_current(con)
    assert not any("'delete-all'" in sql.lower() for sql in trace)
    assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH 'sirnak'").fetchone()[0] == 1
    con.close()


def test_lowered_marker_is_repaired_without_rebuilding_completed_index():
    con = populated()
    con.execute("UPDATE schema_meta SET v='8' WHERE k='schema_version'")
    con.commit()
    trace = []
    con.set_trace_callback(trace.append)
    migrate.ensure_current(con)
    assert not any("'delete-all'" in sql.lower() for sql in trace)
    assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == '9'
    con.close()


def test_rebuild_progress_counts_real_rows_with_sparse_ids_and_rolls_back_failure():
    con = populated()
    fid = con.execute('SELECT file_id FROM files').fetchone()[0]
    con.executemany("INSERT INTO segments(seg_id,file_id,kind,label,raw_text) VALUES (?,?,'body','Sayfa','İstanbul')",
                    [(1000+i*3,fid) for i in range(600)])
    con.commit()
    reports = []
    assert schema.rebuild_fts(con, lambda *args: reports.append(args)) == 601
    counts = [(done,total) for stage,done,total in reports if stage=='fts']
    assert counts == [(0,601),(256,601),(512,601),(601,601)]
    def fail(stage, done, total):
        if stage == 'fts' and done == 256:
            raise RuntimeError('synthetic interrupt')
    with pytest.raises(RuntimeError, match='synthetic interrupt'):
        schema.rebuild_fts(con, fail)
    assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH 'istanbul'").fetchone()[0] == 600
    con.execute("INSERT INTO docs_fts(docs_fts) VALUES('integrity-check')")
    con.close()


def test_legacy_helpers_cannot_lower_current_schema_version():
    from evrakci.vocab import ensure_v5
    con = populated()
    for helper in [schema.ensure_schema, migrate.ensure_v4, ensure_v5,
                   migrate.ensure_v6, migrate.ensure_v7, migrate.ensure_v8]:
        helper(con)
        assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == '9'
    con.close()


def test_encrypted_vault_migrates_once_then_three_fast_opens(tmp_path, monkeypatch):
    from evrakci import startup, vault
    path = str(tmp_path / 'synthetic.db')
    password = 'synthetic-index-once-1234'
    con = vault.open_vault(path, password)
    migrate.ensure_current(con)
    fid = con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/test','test','.txt')").lastrowid
    con.executemany("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'body','Sayfa','Şırnak sözleşme')", [(fid,)]*601)
    con.execute("DELETE FROM schema_meta WHERE k='fts_folded'")
    con.execute("UPDATE schema_meta SET v='8' WHERE k='schema_version'")
    con.commit(); con.close()
    calls = []
    original = schema.rebuild_fts
    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(schema, 'rebuild_fts', counted)
    events = []
    for _ in range(4):
        con = startup.prepare_connection(path, password, str(tmp_path/'backups'), lambda *args: events.append(args))
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH 'sirnak'").fetchone()[0] == 601
        con.close()
    assert len(calls) == 1
    assert len(list((tmp_path/'backups').glob('evrakci-*.db'))) == 1
    assert [(d,t) for s,d,t in events if s=='fts'] == [(0,601),(256,601),(512,601),(601,601)]


def test_progress_eta_uses_current_phase_and_never_invents_total_percent(tmp_path):
    import os, time
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from evrakci.startup import OpeningDialog
    app = QApplication.instance() or QApplication([])
    dialog = OpeningDialog(str(tmp_path/'test.db'), 'synthetic', str(tmp_path/'backups'))
    dialog._baslangic = time.monotonic() - 300
    dialog.update_progress('fts', 0, 100)
    dialog._stage_started = time.monotonic() - 10
    dialog.update_progress('fts', 50, 100)
    assert dialog.bar.value() == 50
    assert '50/100 bölüm' in dialog.detail.text()
    assert 'kalan ~10 sn' in dialog.detail.text()
    dialog.update_progress('commit', 0, 0)
    assert dialog.bar.maximum() == 0
    assert 'yüzdesi ölçülemiyor' in dialog.detail.text()
    dialog.update_progress('ready', 1, 1)
    assert dialog.bar.value() == 100
    dialog.deleteLater(); app.processEvents()
