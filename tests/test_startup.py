import os
import time

from deepfind import migrate, vault, backup
from deepfind import startup


def test_acilis_yuzde_ve_sayac_gosterir(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    dialog = startup.OpeningDialog(
        str(tmp_path / 'yok.db'), 'sifre', str(tmp_path / 'yedek'))
    dialog._baslangic = time.monotonic() - 10
    dialog.update_progress('backup', 3, 10)
    assert dialog.bar.value() == 30
    assert '%30' in dialog.detail.text()
    assert '3/10' in dialog.detail.text()
    assert 'kalan' in dialog.detail.text()
    dialog.update_progress('schema', 0, 0)
    assert 'Geçen süre' in dialog.detail.text()
    assert dialog._sure_yaz(75) == '1 dk 15 sn'
    dialog._saat.stop()
    dialog.deleteLater()
    app.processEvents()


def test_legacy_preparation_stays_responsive_and_reports_backup(tmp_path, monkeypatch):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog
    app = QApplication.instance() or QApplication([])
    path = str(tmp_path / 'legacy.db')
    password = 'synthetic-startup-1234'
    con = vault.open_vault(path, password)
    migrate.ensure_current(con)
    con.execute("DELETE FROM schema_meta WHERE k='archive_version'")
    con.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(raw_text)")
    con.commit()
    con.close()
    original = backup.create_backup
    def slow(*args, **kwargs):
        kwargs['progress']('backup', 1, 2)
        time.sleep(.25)
        return original(*args, **kwargs)
    monkeypatch.setattr(backup, 'create_backup', slow)
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start(10)
    dialog = startup.OpeningDialog(path, password, str(tmp_path / 'backups'))
    stages = []
    dialog.worker.progress.connect(lambda stage, *_: stages.append(stage))
    assert dialog.prepare() == QDialog.Accepted
    timer.stop()
    assert len(ticks) >= 10
    assert {'backup', 'verify', 'schema'} <= set(stages)
    assert dialog.worker.password == ''
    con = vault.open_vault(path, password)
    assert con.execute("SELECT v FROM schema_meta WHERE k='archive_version'").fetchone()[0] == '034'
    con.close()
    assert len(list((tmp_path / 'backups').glob('deepfind-*.db'))) == 1
    # A successful upgrade is recorded; ordinary subsequent opens never repeat it.
    con = startup.prepare_connection(path, password, str(tmp_path / 'backups'))
    con.close()
    assert len(list((tmp_path / 'backups').glob('deepfind-*.db'))) == 1


def test_cancel_before_migration_preserves_legacy_marker(tmp_path):
    path = str(tmp_path / 'legacy.db')
    password = 'synthetic-startup-1234'
    con = vault.open_vault(path, password)
    migrate.ensure_current(con)
    con.execute("DELETE FROM schema_meta WHERE k='archive_version'")
    con.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(raw_text)")
    con.commit()
    con.close()
    worker = startup.PreparationWorker(path, password, str(tmp_path / 'backups'))
    worker.stop.set()
    worker.run()
    assert worker.error
    con = vault.open_vault(path, password)
    assert not con.execute("SELECT 1 FROM schema_meta WHERE k='archive_version'").fetchone()
    assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    con.close()
