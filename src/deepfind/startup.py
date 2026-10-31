"""Vault preparation owns its connection in a worker; Qt remains responsive."""
import os
import threading
import time

from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from . import backup, diagnostics, migrate, vault
from .theme import t


def prepare_connection(path, password, backup_dir, progress=None):
    diagnostics.record('vault_open_begin')
    con = vault.open_vault(path, password)
    diagnostics.record('vault_open_ready')
    snapshot = None
    try:
        fts = con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
        # Snapshot older vaults before removing their derived keyword objects.
        if fts:
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
            migrate.ensure_current(con, progress=progress)
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
        if progress: progress('ready', 1, 1)
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
        self.setWindowTitle(t('DeepFind • Açılıyor'))
        self.setMinimumWidth(480)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(self)
        self.status = QLabel(t('Şifreli kasa açılıyor…'))
        self.status.setWordWrap(True)
        self.detail = QLabel(t('Büyük arşiv hazırlanırken lütfen bekleyin.'))
        self.detail.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setStyleSheet('QProgressBar { min-height: 24px; max-height: 24px; text-align: center; }')
        self.bar.setTextVisible(True)
        self.bar.setRange(0, 0)
        layout.addWidget(self.status)
        layout.addWidget(self.detail)
        layout.addWidget(self.bar)
        self._baslangic = 0.0
        self._son_oran = None
        self._stage = ''
        self._stage_started = 0.0
        self._saat = QTimer(self)
        self._saat.setInterval(500)
        self._saat.timeout.connect(self._suren_guncelle)
        self.worker = PreparationWorker(path, password, backup_dir, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.complete)

    def update_progress(self, stage, done, total):
        if stage != self._stage:
            self._stage, self._stage_started = stage, time.monotonic()
        texts = {'backup': 'Güncelleme öncesi güvenli yedek alınıyor…',
                 'verify': 'Yedeğin bütünlüğü doğrulanıyor…',
                 'schema': 'Kasa sürümü kontrol ediliyor…',
                 'fts': 'Arama indeksi bir kez dönüştürülüyor…',
                 'compact_schema': 'Eski indeks sütunu kaldırılıyor…',
                 'commit': 'İndeks değişiklikleri diske kaydediliyor…',
                 'ready': 'Kasa hazır.',
                 'restore': 'Önceki kasa geri yükleniyor…'}
        self.status.setText(texts.get(stage, 'Şifreli kasa açılıyor…'))
        if total:
            self.bar.setRange(0, 100)
            oran = max(0, min(100, int(done * 100 / total)))
            self.bar.setFormat(t('Bu aşama: %p%'))
            self.bar.setValue(oran)
            self._son_oran = (done, total)
            self.detail.setText(self._ayrinti())
        else:
            self.bar.setRange(0, 0)
            self._son_oran = None
            self.detail.setText(self._ayrinti())

    def _ayrinti(self) -> str:
        gecen = time.monotonic() - self._baslangic if self._baslangic else 0.0
        saat = self._sure_yaz(gecen)
        if not self._son_oran:
            return (f'Geçen süre: {saat}. Bu aşamanın yüzdesi ölçülemiyor. '
                    'Kaynak evraklar değiştirilmez.')
        done, total = self._son_oran
        oran = int(done * 100 / total) if total else 0
        unit = 'bölüm' if self._stage == 'fts' else ('sayfa' if self._stage == 'backup' else 'adım')
        metin = f'Bu aşama %{oran} • {done}/{total} {unit} • Geçen süre: {saat}'
        stage_elapsed = time.monotonic() - self._stage_started
        if done > 0 and stage_elapsed > 1:
            kalan = stage_elapsed / done * (total - done)
            metin += f' • kalan ~{self._sure_yaz(kalan)}'
        elif done < total:
            metin += ' • kalan süre hesaplanıyor…'
        return metin + '. Kaynak evraklar değiştirilmez.'

    @staticmethod
    def _sure_yaz(saniye: float) -> str:
        saniye = max(0, int(saniye))
        if saniye < 60:
            return f'{saniye} sn'
        return f'{saniye // 60} dk {saniye % 60:02d} sn'

    def _suren_guncelle(self):
        if self.worker.isRunning():
            self.detail.setText(self._ayrinti())

    def reject(self):
        if self.worker.isRunning():
            self.worker.stop.set()
            self.detail.setText(t('Güvenli duruş bekleniyor… Şema değişimi başladıysa önce tamamlanacak.'))
        else:
            super().reject()

    def complete(self):
        self._saat.stop()
        self.done(QDialog.Rejected if self.worker.stop.is_set() or self.worker.error else QDialog.Accepted)

    def prepare(self):
        self._baslangic = time.monotonic()
        self._saat.start()
        self.worker.start()
        result = self.exec()
        self.worker.wait()
        return result
