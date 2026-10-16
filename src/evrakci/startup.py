"""Vault preparation owns its connection in a worker; Qt remains responsive."""
import os
import threading
import time

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from . import backup, diagnostics, migrate, vault


def prepare_connection(path, password, backup_dir, progress=None):
    diagnostics.record('vault_open_begin')
    con = vault.open_vault(path, password)
    diagnostics.record('vault_open_ready')
    snapshot = None
    try:
        fts = con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
        marker = con.execute("SELECT 1 FROM schema_meta WHERE k='archive_version'").fetchone() if fts else None
        v9_pending = bool(fts) and con.execute(
            "SELECT count(*) FROM schema_meta WHERE k='fts_folded'").fetchone()[0] == 0 \
            and con.execute("SELECT count(*) FROM segments").fetchone()[0] > 0
        if fts and ('remove_diacritics 0' not in fts[0] or not marker or v9_pending):
            diagnostics.record('migration_backup_begin')
            try:
                snapshot = backup.create_backup(con, path, password, backup_dir,
                                                manual=True, progress=progress)
            except Exception as error:
                raise RuntimeError('Geçiş öncesi indeks yedeği tamamlanamadı; mevcut kasa korunuyor.') from error
            diagnostics.record('migration_backup_ready')
        if progress:
            progress('schema', 0, 0)
        diagnostics.record('schema_begin')
        try:
            migrate.ensure_current(con)
        except Exception:
            con.close()
            con = None
            if snapshot:
                if progress:
                    progress('restore', 0, 0)
                backup.restore_replace(path, password, snapshot, os.path.join(os.path.dirname(path), 'staging'))
            raise
        diagnostics.record('schema_ready')
        migrate.recover_scan_runs(con)
        return con
    except Exception:
        if con is not None:
            con.close()
        raise


class PreparationWorker(QThread):
    progress = Signal(str, int, int)

    def __init__(self, path, password, backup_dir, parent=None):
        super().__init__(parent)
        self.path, self.password, self.backup_dir = path, password, backup_dir
        self.stop = threading.Event()
        self.error = None
        self._last = 0
        self._stage = ''

    def report(self, stage, done, total):
        if stage in ('backup', 'verify') and self.stop.is_set():
            raise InterruptedError('Açılış iptal edildi')
        now = time.monotonic()
        if stage != self._stage or now - self._last >= .1 or (total and done == total):
            self.progress.emit(stage, done, total)
            self._last, self._stage = now, stage

    def run(self):
        try:
            con = prepare_connection(self.path, self.password, self.backup_dir, self.report)
            con.close()
        except Exception as error:
            self.error = error
            diagnostics.record('vault_preparation_failed', type(error).__name__)
        finally:
            self.password = ''


class OpeningDialog(QDialog):
    def __init__(self, path, password, backup_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Evrakçı • Açılıyor')
        self.setMinimumWidth(480)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(self)
        self.status = QLabel('Şifreli kasa açılıyor…')
        self.status.setWordWrap(True)
        self.detail = QLabel('Büyük arşiv hazırlanırken lütfen bekleyin.')
        self.detail.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        layout.addWidget(self.status)
        layout.addWidget(self.detail)
        layout.addWidget(self.bar)
        self.worker = PreparationWorker(path, password, backup_dir, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.complete)

    def update_progress(self, stage, done, total):
        texts = {'backup': 'Güncelleme öncesi güvenli yedek alınıyor…',
                 'verify': 'Yedeğin bütünlüğü doğrulanıyor…',
                 'schema': 'İndeks yapısı güncelleniyor…',
                 'restore': 'Önceki kasa geri yükleniyor…'}
        self.status.setText(texts.get(stage, 'Şifreli kasa açılıyor…'))
        if total:
            self.bar.setRange(0, 100)
            self.bar.setValue(int(done * 100 / total))
            self.detail.setText('Bu işlem büyük kasalarda birkaç dakika sürebilir. Kaynak evraklar değiştirilmez.')
        else:
            self.bar.setRange(0, 0)
            self.detail.setText('Bu aşamanın süresi kasa büyüklüğüne bağlıdır.')

    def reject(self):
        if self.worker.isRunning():
            self.worker.stop.set()
            self.detail.setText('Güvenli duruş bekleniyor… Şema değişimi başladıysa önce tamamlanacak.')
        else:
            super().reject()

    def complete(self):
        self.done(QDialog.Rejected if self.worker.stop.is_set() or self.worker.error else QDialog.Accepted)

    def prepare(self):
        self.worker.start()
        result = self.exec()
        self.worker.wait()
        return result
