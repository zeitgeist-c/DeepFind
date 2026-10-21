"""Evrakci masaustu: Varyant A (sol gezinme + sonuc + sag onizleme). Plan bolum 19-20.

Kilitlenmeden calisir: tarama QThread'de, arama debounce'lu, onizleme tembel.
Kilitte: baglantilar kapanir, model/onislem/gecmis temizlenir (SEC-03).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import (QObject, QThread, QTimer, Signal, Slot, Qt, QAbstractNativeEventFilter,
                            QTime, QEvent, QSettings, QRect, QSize, QItemSelection, QItemSelectionModel)
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel, QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QAbstractItemView, QCheckBox, QComboBox, QDialog,
                               QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit, QListView,
                               QListWidget, QMainWindow, QMessageBox, QPushButton,
                               QSplitter, QStackedWidget, QStatusBar,
                               QSystemTrayIcon, QMenu, QVBoxLayout, QWidget,
                               QProgressBar, QTimeEdit, QSizePolicy, QGridLayout, QFrame, QPlainTextEdit, QListWidgetItem, QScrollArea, QStyledItemDelegate, QStyle)

from . import backup as backup_mod
from . import coordinator, exclusions, history as hist_mod
from . import migrate, rank, scheduler as sched, theme, vault, remember, diagnostics, recovery, thumbs, sorgu
from . import update as update_mod
from .preview import Onizleme
from .version import __version__
from .vocab import rebuild_vocab
from .auth import ParolaDialog, MOD_KURTARMA
from .ui import (ayar_satiri, bolum, bolme, brand, card, label, sayac,
                 sayfa_basi, stat_seridi, Toast, EmptyState, CardDelegate, GorselKutusu,
                 Cip, GridDelegate)
from . import archive_ui

EKRANLAR = ["Ara", "Kaynaklar", "Tarama", "Geçmiş", "Taranmış Evraklar", "Ayarlar"]
SAYFA_ACIKLAMA = {
    "Ara": "Anlamıyla, dosya adıyla veya içeriğiyle arayın; belgeler bu bilgisayarda kalır.",
    "Kaynaklar": "Taranacak klasörleri ve kapsam dışında kalan yolları yönetin.",
    "Tarama": "Arşivinizi güncelleyin; güvenli noktada duraklatıp devam edin.",
    "Geçmiş": "Önceki aramalarınıza tek tıkla dönün.",
    "Taranmış Evraklar": "Kayıtlı dosyaları, tam yollarını ve içerik durumlarını inceleyin.",
    "Ayarlar": "Çalışma tercihleri, kasa güvenliği ve yedekler.",
}


class RailDelegate(QStyledItemDelegate):
    """Keep icons centered when the navigation rail has no labels."""

    def __init__(self, rail, parent=None):
        super().__init__(parent)
        self.rail = rail

    def paint(self, painter, option, index):
        if not self.rail._collapsed:
            return super().paint(painter, option, index)
        painter.save()
        if option.state & (QStyle.State_Selected | QStyle.State_MouseOver):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#25435A" if option.state & QStyle.State_Selected else "#1B304C"))
            painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 10, 10)
        icon = index.data(Qt.DecorationRole)
        if icon:
            size = self.rail.nav.iconSize()
            target = option.rect
            x = target.x() + (target.width() - size.width()) // 2
            y = target.y() + (target.height() - size.height()) // 2
            icon.paint(painter, x, y, size.width(), size.height())
        painter.restore()


class AramaIsci(QThread):
    sonuc = Signal(dict)

    def __init__(self, path, password, request, parent=None):
        super().__init__(parent)
        self.path, self.password, self.request = path, password, request
        self.stop = threading.Event()

    def run(self):
        con = None
        try:
            con = vault.open_vault(self.path, self.password)
            con.execute("PRAGMA query_only=ON")
            con.set_progress_handler(lambda: int(self.stop.is_set()), 1000)
            req = self.request
            q, year, ext, folder = req[0], req[1], req[2], req[3]
            tag = req[4] if len(req) > 4 else None
            out = rank.search_hybrid(con, q, year=year, ext=ext, limit=50,
                                     folder=folder or None, offset=getattr(self,"offset",0),
                                     tag=tag or None)
            if not self.stop.is_set():
                self.sonuc.emit({"request": self.request, "offset":getattr(self,'offset',0), "out": out})
        except Exception as error:
            if not self.stop.is_set():
                self.sonuc.emit({"request": self.request, "error": type(error).__name__})
        finally:
            if con is not None:
                con.close()
            self.password = ""


class OturumKilitFiltresi(QAbstractNativeEventFilter):
    """Windows: uyku/oturum kilidinde kasayi kilitle (plan bolum 15).

    PBT_APMSUSPEND kayitsiz gelir; WTS_SESSION_LOCK icin pencere kaydi denenir,
    basarisizsa sessiz gecilir (kilit yine de elle/zamanlayiciyla olur).
    """
    PBT_APMSUSPEND = 0x0004
    WM_POWERBROADCAST = 0x0218
    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_LOGOFF = 0x5

    def __init__(self, kilitle_fn):
        super().__init__()
        self._kilitle = kilitle_fn

    def nativeEventFilter(self, _event_type, message):
        try:
            import ctypes
            from ctypes import wintypes
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == self.WM_POWERBROADCAST and msg.wParam == self.PBT_APMSUSPEND:
                self._kilitle()
                return True, 0
            if msg.message == self.WM_WTSSESSION_CHANGE and \
                    msg.wParam in (self.WTS_SESSION_LOCK, self.WTS_SESSION_LOGOFF):
                self._kilitle()
                return True, 0
        except Exception:
            pass
        return False, 0


class TaramaIsci(QObject):
    bitti = Signal(dict)
    hata = Signal(str)
    ilerleme = Signal(dict)
    duraklama = Signal(bool)

    def __init__(self, kasa_yolu, sifre, kokler):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.kokler = kokler
        self._dur = threading.Event()
        self.paused = threading.Event()
        self._progress_lock = threading.Lock()
        self._latest = {}
        self._last_emit = 0.0
        self._document_total = None
        self._inventory_complete = False
        self._phase_key = None
        self._phase_started = 0.0
        self._paused_seconds = 0.0
        self._phase_pause_base = 0.0
        self._pause_started = None

    def snapshot(self):
        with self._progress_lock:
            if not self._latest: return {}
            data = dict(self._latest)
            current_pause = time.monotonic()-self._pause_started if self._pause_started is not None else 0
            data['phase_elapsed'] = max(0,time.monotonic()-self._phase_started-(self._paused_seconds-self._phase_pause_base)-current_pause)
            return data

    def report_progress(self, data, totals):
        combined = dict(data, **{k: data.get(k, 0) + totals.get(k, 0)
                               for k in ("found", "done", "failed", "ocr_done", "ocr_failed", "skipped", "pending", "documents_done")})
        with self._progress_lock:
            if self._document_total is not None:
                combined['inventory_ready'] = True
                combined['inventory_complete'] = self._inventory_complete
                combined['documents_total'] = self._document_total
                combined['found'] = self._document_total
            if data.get('phase_key') != self._phase_key:
                self._phase_key = data.get('phase_key')
                self._phase_started = time.monotonic()
                self._phase_pause_base = self._paused_seconds
            self._latest = combined
        now = time.monotonic()
        if now - self._last_emit >= 0.2:
            self._last_emit = now
            self.ilerleme.emit(combined)

    def stop_requested(self):
        waiting = self.paused.is_set() and not self._dur.is_set()
        if waiting:
            self._pause_started = time.monotonic()
            self.duraklama.emit(True)
        while self.paused.is_set() and not self._dur.is_set():
            time.sleep(0.1)
        if waiting:
            self._paused_seconds += time.monotonic()-self._pause_started
            self._pause_started = None
            self.duraklama.emit(False)
        return self._dur.is_set()

    def durdur(self):
        self._dur.set()

    def kos(self):
        try:
            from .migrate import ensure_current
            con = vault.open_vault(self.kasa_yolu, self._sifre)
            inventories = []
            try:
                ensure_current(con)
                toplam = {}
                all_complete = True
                with coordinator.ScanLock(self.kasa_yolu):
                    inventory_totals = {}
                    for kok in self.kokler:
                        if self._dur.is_set(): break
                        st = coordinator.run_scan(con,self.kasa_yolu,kok,stop=self.stop_requested,
                            guarded=True,inventory_only=True,fresh_inventory=True,lock_held=True,
                            progress=lambda data:self.report_progress(data,inventory_totals))
                        inventories.append((kok,st))
                        inventory_totals['found'] = inventory_totals.get('found',0)+st['found']
                    if not self._dur.is_set():
                        self._document_total = sum(st['found'] for _,st in inventories)
                        self._inventory_complete = all(st['scope_complete'] for _,st in inventories)
                        for kok, inventory in inventories:
                            if self._dur.is_set(): break
                            st = coordinator.run_scan(con,self.kasa_yolu,kok,stop=self.stop_requested,
                                guarded=True,prepared=inventory,lock_held=True,
                                progress=lambda data:self.report_progress(data,toplam))
                            all_complete = all_complete and bool(st.get('complete'))
                            for key in ('found','done','changed','unstable','failed','missing','ocr_done',
                                        'ocr_deferred','ocr_failed','embed_done','hashed','skipped','pending','documents_done'):
                                toplam[key] = toplam.get(key,0)+st.get(key,0)
                            toplam['result'] = st.get('result','')
                    else:
                        toplam.update(inventory_totals)
                    toplam['documents_total'] = self._document_total or 0
                    toplam['inventory_ready'] = self._document_total is not None
                    toplam['inventory_complete'] = self._inventory_complete
                    toplam["complete"] = all_complete and not self._dur.is_set()
                    if not toplam["complete"] and toplam.get("result") == "complete":
                        toplam["result"] = "partial"
                    if self._dur.is_set():
                        toplam["result"] = "cancelled"
                    if not self._dur.is_set():
                        self.report_progress(dict(self.snapshot(),stage="Arama sözlüğü güncelleniyor",path="",phase_key='dictionary',phase_done=0,phase_total=0),{})
                        try:
                            rebuild_vocab(con, stop=self.stop_requested, progress=lambda done,total:
                                self.report_progress(dict(self.snapshot(),stage="Arama sözlüğü güncelleniyor",phase_key='dictionary',phase_done=done,phase_total=total),{}))
                        except InterruptedError:
                            toplam['complete'] = False
                            toplam['result'] = 'cancelled'
                            con.execute("UPDATE scan_runs SET result='cancelled',error_code='VOCAB_CANCELLED' WHERE run_id=(SELECT max(run_id) FROM scan_runs)")
                            con.commit()
                        except Exception as error:
                            diagnostics.record("vocabulary_error", type(error).__name__)
                            toplam["complete"] = False
                            toplam["result"] = "partial"
                            con.execute(
                                "UPDATE scan_runs SET result='partial', error_code='VOCAB_ERROR' "
                                "WHERE run_id=(SELECT max(run_id) FROM scan_runs)"
                            )
                            con.commit()
                diagnostics.record("scan_finished", toplam.get("result", "unknown"))
                self.bitti.emit(dict(toplam))
            finally:
                try:
                    for _, inventory in inventories:
                        rid = inventory['run_id']
                        con.execute('DELETE FROM scan_manifest WHERE run_id=?', (rid,))
                        con.execute('UPDATE scan_runs SET finished_at=?,result=? WHERE run_id=? AND finished_at IS NULL',
                                    (int(time.time()),'cancelled' if self._dur.is_set() else 'interrupted',rid))
                    con.commit()
                except Exception:
                    diagnostics.record('scan_inventory_cleanup_failed')
                con.close()
        except Exception as e:  # noqa: BLE001 - worker hatasi arayuze tasinir
            diagnostics.record("scan_error", type(e).__name__)
            self.hata.emit(f"{type(e).__name__}: {e}")
        finally:
            self._sifre = "x" * 32


class KokKaldirIsci(QObject):
    """Kök kaldırma: boşaltma + sözlük yenileme GUI'yi kilitlemeden ayrı thread'de."""
    bitti = Signal(int)   # silinen dosya sayısı
    hata = Signal(str)

    def __init__(self, kasa_yolu, sifre, kok):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.kok = kok

    def kos(self):
        con = None
        scan_lock = None
        try:
            from . import vault as v
            from .vocab import rebuild_vocab
            scan_lock = coordinator.ScanLock(self.kasa_yolu)
            scan_lock.__enter__()
            con = v.open_vault(self.kasa_yolu, self._sifre)
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM roots WHERE display_path=?", (self.kok,))
            remaining = [r[0] for r in con.execute(
                "SELECT display_path FROM roots WHERE enabled=1").fetchall()]
            con.execute("CREATE TEMP TABLE IF NOT EXISTS evrakci_remove_files(file_id INTEGER PRIMARY KEY)")
            con.execute("DELETE FROM temp.evrakci_remove_files")
            cursor = con.execute("SELECT file_id,path FROM files")
            while batch := cursor.fetchmany(1000):
                remove_ids = [fid for fid, path in batch
                              if exclusions.is_excluded(path, [self.kok])
                              and not exclusions.is_excluded(path, remaining)]
                con.executemany("INSERT INTO temp.evrakci_remove_files(file_id) VALUES (?)",
                                ((fid,) for fid in remove_ids))
            sil = con.execute("SELECT count(*) FROM temp.evrakci_remove_files").fetchone()[0]
            if sil:
                tables = {row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                    "('scan_selected','scan_manifest')")}
                if "scan_selected" in tables:
                    con.execute("DELETE FROM scan_selected WHERE file_id IN "
                                "(SELECT file_id FROM temp.evrakci_remove_files)")
                if "scan_manifest" in tables:
                    con.execute("DELETE FROM scan_manifest WHERE file_id IN "
                                "(SELECT file_id FROM temp.evrakci_remove_files)")
                con.execute("DELETE FROM files WHERE file_id IN "
                            "(SELECT file_id FROM temp.evrakci_remove_files)")
                rebuild_vocab(con, transactional=True)
            con.commit()
            self.bitti.emit(sil)
        except Exception as e:  # noqa: BLE001
            diagnostics.record("kok_kaldir_error", type(e).__name__)
            if con is not None:
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
            self.hata.emit(type(e).__name__)
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception as error:  # noqa: BLE001
                    diagnostics.record("kok_kaldir_close_error", type(error).__name__)
            if scan_lock is not None and scan_lock.fh is not None:
                try:
                    scan_lock.__exit__(None, None, None)
                except Exception as error:  # noqa: BLE001
                    diagnostics.record("kok_kaldir_unlock_error", type(error).__name__)
            self._sifre = "x" * 32


class HaricIsci(QObject):
    """Hariç kuralını ekle ve içerik temizliğini atomik, arka planda uygula."""
    bitti = Signal(str, int)
    hata = Signal(str)

    def __init__(self, kasa_yolu, sifre, rule):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.rule = rule

    def kos(self):
        con = None
        scan_lock = None
        try:
            scan_lock = coordinator.ScanLock(self.kasa_yolu)
            scan_lock.__enter__()
            con = vault.open_vault(self.kasa_yolu, self._sifre)
            rule, count = exclusions.add_and_purge(con, self.rule)
            self.bitti.emit(rule, count)
        except Exception as error:  # noqa: BLE001
            diagnostics.record("haric_apply_error", type(error).__name__)
            if con is not None:
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
            self.hata.emit(type(error).__name__)
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception as error:  # noqa: BLE001
                    diagnostics.record("haric_apply_close_error", type(error).__name__)
            if scan_lock is not None and scan_lock.fh is not None:
                try:
                    scan_lock.__exit__(None, None, None)
                except Exception as error:  # noqa: BLE001
                    diagnostics.record("haric_apply_unlock_error", type(error).__name__)
            self._sifre = "x" * 32


class GuncellemeIsci(QObject):
    """Arka planda güncelleme denetimi/indirmesi; ağ GUI'yi meşgul etmez.

    Denetim ve indirme ayrı çağrılır; sinyaller ana thread'e kuyruklanır.
    İptal bir threading.Event'tir: indirme döngüsü her parçada yoklar,
    yarım dosya silinir.
    """
    denetlendi = Signal(object)      # UpdateInfo ya da None (güncel)
    ilerleme = Signal(int, int)      # inen bayt, toplam bayt
    hazir = Signal(str, str)         # sürüm, yerleşmeye hazır klasör
    hata = Signal(str)

    def __init__(self, gorev, current="", info=None, parent=None):
        super().__init__(parent)
        self.gorev = gorev
        self.current = current
        self.info = info
        self.iptal = threading.Event()

    def iptal_et(self):
        self.iptal.set()

    def kos(self):
        try:
            if self.gorev == "denetle":
                self.denetlendi.emit(update_mod.check_for_update(self.current))
            else:
                klasor = update_mod.prepare(self.info, progress=self._ilerleme,
                                            cancel=self.iptal)
                self.hazir.emit(self.info.version, str(klasor))
        except update_mod.UpdateError as error:
            if str(error) == "cancelled":
                return
            diagnostics.record("update_error", type(error).__name__)
            self.hata.emit(str(error))
        except Exception as error:  # noqa: BLE001 - beklenmeyen hata kullanıcıya tasinir
            diagnostics.record("update_error", type(error).__name__)
            self.hata.emit("Güncelleme tamamlanamadı.")

    def _ilerleme(self, done, total):
        # Birleştirme: megabayt başına tek sinyal GUI thread'ini serbest tutar.
        if done % (1024 * 1024) < 256 * 1024 or done == total:
            self.ilerleme.emit(done, total)


class AnaPencere(QMainWindow):
    def __init__(self, kasa_yolu, sifre, prepared=False):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.sifresiz = sifre == vault.SIFRESIZ_ANAHTAR
        self.con = None
        self.sonuclar = []
        self._locked = False
        self._exiting = False
        self._search_thread = None
        self._pending_search = None
        self._kaldir_isci = None
        self._kaldir_thread = None
        self._kaldir_lock_pending = False
        self._kaldir_yol = None
        self._haric_isci = None
        self._haric_thread = None
        self._guncelleme_isci = None
        self._guncelleme_thread = None
        self._guncelleme_info = None
        self._guncelleme_sessiz = False
        self._jobs=[]
        self._job_keys={}
        self._job_pending={}
        self._job_generation=0
        self._search_offset=0
        self.setWindowTitle(f"Evrakçı {__version__}")
        self.setWindowIcon(theme.app_icon())
        self.setMinimumSize(1000, 640)
        self._geometry_ready = False
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.timeout.connect(self._save_window_geometry)

        if prepared:
            self.con = vault.open_vault(self.kasa_yolu, self._sifre)
        else:
            self._kasa_ac()
        from . import ocr_setup
        diagnostics.record("ocr_jobs_begin")
        try:
            ocr_setup.engine_backfill(self.con)  # Tesseract→RapidOCR: bir kez
        except Exception:
            pass
        ocr_setup.reopen_deferred(self.con)
        diagnostics.record("ui_begin")
        self._arayuz()
        self._load_window_geometry()
        self._tepsi()
        diagnostics.record("ui_ready")
        try:
            if QApplication.platformName() == "windows":
                self._oturum_filtresi = OturumKilitFiltresi(self._otomatik_kilitle)
                QApplication.instance().installNativeEventFilter(self._oturum_filtresi)
                import ctypes
                from ctypes import wintypes
                register = ctypes.windll.wtsapi32.WTSRegisterSessionNotification
                register.argtypes = [wintypes.HWND, wintypes.DWORD]
                register.restype = wintypes.BOOL
                self._wts_registered = bool(register(int(self.winId()), 0))
        except Exception:
            pass
        self._zamanlayici_kontrol(ilk=True)
        self._kisaltmalar()
        try:
            from . import embed as _embed

            threading.Thread(target=lambda: _embed.isit_oturumu(cancel=lambda: self._locked or self._exiting), daemon=True).start()
        except Exception:
            pass  # model yoksa aramalar FTS yapar
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._zamanlayici_kontrol)
        self._schedule_timer.start(60_000)
        theme.apply(QApplication.instance(), self.tema_sec.currentData())
        self._sayfa_kartlari()
        self._tema_yenile()
        # İlk açılışta kurtarma anahtarı yoksa sessizce üret (kullanıcı şifresini
        # unutursa indeks kurtarılabilsin). Kullanıcıya Ayarlar'da gösterilir.
        try:
            self._kurtarma_ilk_kurulum()
        except Exception as error:  # noqa: BLE001
            diagnostics.record("recovery_setup_failed", type(error).__name__)
        QTimer.singleShot(1500, self._kurtarma_bildirim_goster)
        # Güncelleme artıklarını topla (çalışılan klasör hariç) ve ilk sessiz
        # denetimi 30 sn sonra yap: program açılışı gecikmesin.
        try:
            update_mod.temizle(aktif_klasor=os.path.dirname(os.path.abspath(sys.executable)))
        except Exception:
            pass
        QTimer.singleShot(1200, self._guncelleme_sonuc_bildir)
        QTimer.singleShot(30_000, self._guncelleme_zamanli)
        # Güncelleme yeni klasöre taşındıysa açılış kaydı eski yolu gösteriyor
        # olabilir; kayıt varsa çalışan yola tazele (kapalı kayıt açılmaz).
        if self._guncelleme_yapilabilir():
            try:
                if sched.autostart_guncelle("Evrakci", sys.executable, self.kasa_yolu):
                    diagnostics.record("autostart_refreshed")
            except Exception:
                pass

    def _guncelleme_sonuc_bildir(self):
        """Bekçi betiğin bıraktığı güncelleme sonucunu bir kez duyur."""
        sonuc = update_mod.son_sonuc()
        if sonuc == "ok":
            self._toast_goster(f"Güncelleme tamamlandı: Evrakçı {__version__}.")
            self.durum.showMessage(f"Evrakçı {__version__} güncellendi.", 8000)
        elif sonuc == "fallback":
            self._toast_goster("Güncelleme taşınamadı; geçici klasörden çalışıyorsunuz.")
        elif sonuc == "install_failed":
            self._toast_goster("Güncelleme kurulamadı veya yönetici onayı iptal edildi. Ayarlar → Güncellemeler'den yeniden deneyin.")

    def _kurtarma_ilk_kurulum(self):
        """Kurtarma anahtarı yoksa üret; sonucu tek seferlik bildirime hazırla."""
        if self.con is None or self._locked or not self._sifre or self.sifresiz:
            return
        durum = recovery.status(self.kasa_yolu)
        if durum.get("var") and recovery.load_key(self.kasa_yolu):
            return
        anahtar = recovery.refresh(self.kasa_yolu, self._sifre)
        self._kurtarma_yeni_bildirim = anahtar

    def _kurtarma_bildirim_goster(self):
        """Yeni üretilen kurtarma anahtarını engellemeden duyur (bir kez)."""
        anahtar = getattr(self, "_kurtarma_yeni_bildirim", "")
        self._kurtarma_yeni_bildirim = ""
        if not anahtar:
            return
        self._toast_goster("Kurtarma anahtarı hazır: Ayarlar → Kurtarma anahtarı.")
        self.durum.showMessage(
            "Şifrenizi unutursanız kurtarma anahtarınızla kasayı açabilirsiniz.", 10000)

    # -- güncelleme: herkese açık yayın deposundan, kullanıcı denetimiyle --
    def _guncelleme_yapilabilir(self):
        """Güncelleme akışı gerçek kurulum ister; kaynak koddan çalışmaz."""
        return bool(getattr(sys, "frozen", False))

    def _guncelleme_zamanli(self):
        # İlk sessiz denetim açılıştan 30 sn sonra; sonra günde bir.
        if not self._guncelleme_yapilabilir() or self._locked or self.con is None:
            return
        stamp = migrate.get_setting(self.con, "update_son_kontrol", "")
        if not update_mod.last_check_is_old(stamp):
            return
        self._guncelleme_denetle(sessiz=True)

    def _guncelleme_denetle(self, sessiz=False):
        if self._guncelleme_isci is not None:
            return
        if not self._guncelleme_yapilabilir():
            if not sessiz:
                self._guncelleme_durum_yaz(
                    "Güncellemeler yalnız kurulu programda denetlenir.")
            return
        if not sessiz:
            self._guncelleme_durum_yaz("Güncelleme denetleniyor…")
            self.update_denetle_btn.setEnabled(False)
        self._guncelleme_sessiz = sessiz
        # Ebeveynsiz işçi: QObject ebeveynliyken moveToThread çalışmaz ve ağ
        # işi GUI thread'inde donar. Yaşam süresi _guncelleme_isci referansıyla.
        isci = GuncellemeIsci("denetle", current=__version__)
        isci.denetlendi.connect(self._guncelleme_denetlendi)
        isci.hata.connect(self._guncelleme_denetleme_hatasi)
        self._guncelleme_isci = isci
        self._guncelleme_thread = QThread(self)
        isci.moveToThread(self._guncelleme_thread)
        self._guncelleme_thread.started.connect(isci.kos)
        isci.denetlendi.connect(self._guncelleme_thread.quit)
        isci.hata.connect(self._guncelleme_thread.quit)
        isci.denetlendi.connect(isci.deleteLater)
        isci.hata.connect(isci.deleteLater)
        self._guncelleme_thread.finished.connect(isci.deleteLater)
        self._guncelleme_thread.finished.connect(self._guncelleme_temizle)
        self._guncelleme_thread.start()

    def _guncelleme_temizle(self):
        self._guncelleme_isci = None
        self._guncelleme_thread = None

    def _guncelleme_denetlendi(self, info):
        if self.con is not None:
            try:
                migrate.set_setting(self.con, "update_son_kontrol", update_mod.now_stamp())
            except Exception:
                pass
        self.update_denetle_btn.setEnabled(True)
        if info is None:
            self._guncelleme_info = None
            # Tek geri bildirim: Ayarlar sayfasındaki satır içi durum.
            # Toast aynı metni sayfanın altından perdeleyip çift gösterim
            # üretiyordu; kaldırılandı (sade UI, bilgi tek yerde).
            self._guncelleme_durum_yaz(f"En güncel sürümü kullanıyorsunuz ({__version__}).")
            return
        self._guncelleme_info = info
        boyut = max(1, round(info.size / (1024 * 1024)))
        self._guncelleme_durum_yaz(
            f"Yeni sürüm {info.version} hazır ({boyut} MB). "
            "İndirmek için “İndir ve kur” düğmesini kullanın.")
        self.update_denetle_btn.setVisible(False)
        self.update_indir_btn.setVisible(True)
        self.update_iptal_btn.setVisible(True)
        if getattr(self, "tepsi", None) is not None:
            self.tepsi.showMessage(
                "Evrakçı", f"Yeni sürüm {info.version} hazır: Ayarlar → Güncellemeler.",
                QSystemTrayIcon.MessageIcon.Information, 10000)
        self.durum.showMessage(
            f"Yeni sürüm {info.version} hazır: Ayarlar → Güncellemeler.", 10000)

    def _guncelleme_denetleme_hatasi(self, mesaj):
        self.update_denetle_btn.setEnabled(True)
        if self._guncelleme_sessiz:
            # Sessiz denetim hatası kullanıcıya gösterilmez; bir sonraki
            # açılışta yeniden denenir.
            self._guncelleme_durum_yaz("Sessiz denetim başarısız; sonraki açılışta yeniden denenecek.")
            return
        self._guncelleme_durum_yaz(mesaj)

    def _guncelleme_indir(self):
        info = self._guncelleme_info
        if info is None or self._guncelleme_isci is not None:
            return
        self.update_indir_btn.setVisible(False)
        self.update_iptal_btn.setVisible(True)
        self.update_iptal_btn.setEnabled(True)
        self.update_bar.setVisible(True)
        self.update_bar.setRange(0, 100 if info.size else 0)
        self._guncelleme_durum_yaz("Güncelleme indiriliyor…")
        isci = GuncellemeIsci("indir", info=info)
        isci.ilerleme.connect(self._guncelleme_ilerleme)
        isci.hazir.connect(self._guncelleme_hazir)
        isci.hata.connect(self._guncelleme_indirme_hatasi)
        self._guncelleme_isci = isci
        self._guncelleme_thread = QThread(self)
        isci.moveToThread(self._guncelleme_thread)
        self._guncelleme_thread.started.connect(isci.kos)
        isci.hazir.connect(self._guncelleme_thread.quit)
        isci.hata.connect(self._guncelleme_thread.quit)
        isci.hazir.connect(isci.deleteLater)
        isci.hata.connect(isci.deleteLater)
        self._guncelleme_thread.finished.connect(isci.deleteLater)
        self._guncelleme_thread.finished.connect(self._guncelleme_temizle)
        self._guncelleme_thread.start()

    def _guncelleme_ilerleme(self, done, total):
        if total:
            self.update_bar.setValue(round(done * 100 / total))
        self._guncelleme_durum_yaz(
            f"Güncelleme indiriliyor… {round(done / (1024 * 1024))} / "
            f"{round(total / (1024 * 1024))} MB")

    def _guncelleme_hazir(self, surum, klasor):
        # Bekçi betik önce bu sürecin çıkmasını bekler, sonra yeni EXE'yi açar.
        # Betik kurulamazsa uygulama kapanmamalı: hata göster, indirme geri gel.
        try:
            update_mod.spawn_swap(os.getpid(), Path(klasor), Path(sys.executable),
                                  self.kasa_yolu)
        except OSError as error:
            diagnostics.record("update_spawn_failed", type(error).__name__)
            self.update_indir_btn.setVisible(True)
            self.update_iptal_btn.setVisible(False)
            self.update_bar.setVisible(False)
            self._guncelleme_durum_yaz(
                "Güncelleme kurulamadı; “İndir ve kur” ile yeniden deneyin.")
            return
        self.update_bar.setRange(0, 0)
        self._guncelleme_durum_yaz(f"Sürüm {surum} hazır. Evrakçı yeniden başlatılıyor…")
        diagnostics.record("update_installing", surum)
        QTimer.singleShot(250, self._cikis)

    def _guncelleme_indirme_hatasi(self, mesaj):
        self.update_indir_btn.setVisible(True)
        self.update_iptal_btn.setVisible(False)
        self.update_bar.setVisible(False)
        self._guncelleme_durum_yaz(mesaj)

    def _guncelleme_iptal(self):
        if self._guncelleme_isci is not None:
            self._guncelleme_isci.iptal_et()
            # İndirme döngüsü iptali bir sonraki parçada görür; işçi sinyal
            # göndermeden döner, bu yüzden thread'i burada kapatıyoruz —
            # yoksa temizlik hiç çalışmaz ve düğmeler kalıcı kilitlenir.
            if self._guncelleme_thread is not None:
                self._guncelleme_thread.quit()
        self.update_iptal_btn.setVisible(False)
        self.update_bar.setVisible(False)
        self.update_indir_btn.setVisible(True)
        if self._guncelleme_info is not None:
            boyut = max(1, round(self._guncelleme_info.size / (1024 * 1024)))
            self._guncelleme_durum_yaz(
                f"Yeni sürüm {self._guncelleme_info.version} hazır ({boyut} MB). "
                "İndirmek için “İndir ve kur” düğmesini kullanın.")

    def _guncelleme_durum_yaz(self, metin):
        self.update_durum.setText(metin)

    def _guncelleme_sifirla(self):
        """Kilit/çıkışta güncelleme satırını başlangıç durumuna döndür."""
        self._guncelleme_info = None
        if self._guncelleme_yapilabilir():
            self.update_durum.setText(f"Sürüm {__version__} kurulu.")
            self.update_denetle_btn.setVisible(True)
            self.update_denetle_btn.setEnabled(True)
        self.update_indir_btn.setVisible(False)
        self.update_iptal_btn.setVisible(False)
        self.update_bar.setVisible(False)

    # -- kurulum --
    def _kasa_ac(self):
        from .startup import prepare_connection
        self.con = prepare_connection(self.kasa_yolu, self._sifre, self._yedek_dizin())

    def _arayuz(self):
        kok = QWidget()
        kok.setObjectName("kok")
        self.setCentralWidget(kok)
        dis = QHBoxLayout(kok)
        dis.setContentsMargins(0, 0, 0, 0)
        dis.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("rail")
        self._rail_width = 250
        rail.setFixedWidth(self._rail_width)
        side = QVBoxLayout(rail)
        side.setContentsMargins(12, 16, 12, 14)
        side.setSpacing(2)
        self.rail = rail
        self._collapsed = False
        self.rail_brand = QWidget()
        brand_layout = QVBoxLayout(self.rail_brand)
        brand_layout.setContentsMargins(4, 0, 4, 14)
        brand_layout.setSpacing(0)
        brand(brand_layout, size=30)
        side.addWidget(self.rail_brand)
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.ElideRight)
        self.nav.addItems(EKRANLAR)
        from PySide6.QtCore import QSize
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setItemDelegate(RailDelegate(self, self.nav))
        self._nav_ikonlari()
        self.nav.currentRowChanged.connect(self._ekran)
        side.addWidget(self.nav, 1)
        side.addWidget(bolme())
        self.rail_toggle = QPushButton("Menüyü daralt")
        self.rail_toggle.setIcon(theme.symbol_icon("left"))
        self.rail_toggle.setIconSize(QSize(17, 17))
        self.rail_toggle.clicked.connect(self._nav_toggle)
        side.addWidget(self.rail_toggle)
        self.rail_actions = []
        for text, kind, callback in (("Kasayı kilitle", "lock", self.kilitle),
                                     ("Çıkış", "exit", self._cikis)):
            if self.sifresiz and kind == "lock":
                continue  # Şifresiz kasada kilit ekranı yok.
            button = QPushButton(text)
            button.setIcon(theme.symbol_icon(kind))
            button.setIconSize(QSize(17, 17))
            button.setToolTip(text)
            button.clicked.connect(callback)
            button.setAccessibleName(text)
            button.setMinimumWidth(0)
            side.addWidget(button)
            self.rail_actions.append((button, text))
        dis.addWidget(rail)
        workspace = QVBoxLayout()
        workspace.setSpacing(0)
        workspace.setContentsMargins(0, 0, 0, 0)

        self.yigin = QStackedWidget()
        self._ekran_ara()
        self._ekran_kaynaklar()
        self._ekran_tarama()
        self._ekran_gecmis()
        self._ekran_ayarlar()
        archive_ui.install(self)
        self._sayfa_kartlari()
        self.workspace = workspace
        govde = QSplitter(Qt.Horizontal)
        govde.addWidget(self.yigin)
        govde.setChildrenCollapsible(False)
        workspace.addWidget(govde, 1)
        self._toolbar()
        dis.addLayout(workspace, 1)
        self._toast = Toast(kok)

        self.preview_dialog = QDialog(self)
        self.preview_dialog.setWindowTitle('Evrakçı • Belge ön izlemesi')
        self.preview_dialog.resize(950, 740)
        preview_layout = QVBoxLayout(self.preview_dialog)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)
        self.preview_path = QLabel()
        self.preview_path.setWordWrap(True)
        self.preview_path.setTextFormat(Qt.PlainText)
        self.preview_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview_path.setProperty("ikincil", True)
        preview_layout.addWidget(self.preview_path)
        tools = QHBoxLayout()
        for caption, callback in [('Yolu kopyala', self._copy_path), ('Klasörü aç', self._open_folder),
                                  ('Dosyayı aç', self._open_file)]:
            button = QPushButton(caption)
            button.clicked.connect(callback)
            tools.addWidget(button)
        tools.addStretch(1)
        preview_layout.addLayout(tools)
        gezinme = QHBoxLayout()
        gezinme.setSpacing(8)
        self.preview_once = QPushButton("‹ Önceki belge")
        self.preview_once.setProperty("kucuk", True)
        self.preview_once.setToolTip("Arama sonuçlarındaki önceki belge")
        self.preview_once.clicked.connect(lambda: self._onizleme_komsu(-1))
        self.preview_konum = label("", "ikincil")
        self.preview_konum.setAlignment(Qt.AlignCenter)
        self.preview_sonra = QPushButton("Sonraki belge ›")
        self.preview_sonra.setProperty("kucuk", True)
        self.preview_sonra.setToolTip("Arama sonuçlarındaki sonraki belge")
        self.preview_sonra.clicked.connect(lambda: self._onizleme_komsu(1))
        gezinme.addWidget(self.preview_once)
        gezinme.addWidget(self.preview_konum, 1)
        gezinme.addWidget(self.preview_sonra)
        preview_layout.addLayout(gezinme)
        self.onizleme = Onizleme(self.preview_dialog)
        self.onizleme.setMinimumWidth(320)
        preview_layout.addWidget(self.onizleme, 1)
        self.preview_dialog.finished.connect(lambda _: self.onizleme.temizle())
        self.yigin.setCurrentIndex(0)
        self.nav.setCurrentRow(0)

        self.durum = QStatusBar()
        self.setStatusBar(self.durum)
        self._durum_yaz()
        self._tema_yenile()

    def _toolbar(self):
        """Başlık şeridi: sayfa başlığı + durum rozeti + ortak işlemler."""
        self.head_bar = sayfa_basi("Ara", "Dosya adı, içerik ve klasör bağlamıyla arayın.")
        self.workspace.insertWidget(0, self.head_bar)
        self.tarama_pill = label("Kasa açık", "pill")
        self.head_bar.denetim.addWidget(self.tarama_pill)
        self.tara_btn = QPushButton("Şimdi tara")
        self.tara_btn.setProperty("kucuk", True)
        self.tara_btn.clicked.connect(self._tara_baslat)
        self.head_bar.denetim.addWidget(self.tara_btn)
        self.tema_sec = QComboBox()
        self.tema_sec.setProperty("kucuk", True)
        for caption, value in [("Sistem teması", "sistem"), ("Açık", "acik"), ("Koyu", "koyu")]:
            self.tema_sec.addItem(caption, value)
        self.tema_sec.setCurrentIndex(max(0, self.tema_sec.findData(migrate.get_setting(self.con, "tema", "sistem"))))
        self.tema_sec.currentIndexChanged.connect(lambda _: self._tema_degistir(self.tema_sec.currentData()))
        self.head_bar.denetim.addWidget(self.tema_sec)

    def _nav_ikonlari(self):
        from PySide6.QtCore import QSize
        self.nav.setIconSize(QSize(18, 18))
        for i, kind in enumerate(("search", "folder", "scan", "history", "document", "settings")):
            self.nav.item(i).setIcon(theme.symbol_icon(kind))

    def _tema_yenile(self):
        """Tema değişince kod içinde üretilen simgeleri tazeler."""
        from PySide6.QtCore import QSize
        self._nav_ikonlari()
        self.rail_toggle.setIcon(theme.symbol_icon("right" if self._collapsed else "left"))
        for button, title in self.rail_actions:
            kind = "lock" if title == "Kasayı kilitle" else "exit"
            button.setIcon(theme.symbol_icon(kind))
        if hasattr(self, "onizleme"):
            self.onizleme.yenile()
        if hasattr(self, "csv_btn"):
            self.csv_btn.setIcon(theme.symbol_icon("backup"))

    def _sayfa_basligi(self, index, baslik, aciklama):
        """Sekme başlığını üst şeride yazar; bölüm içi işlem çubuğu sayfada kalır."""
        if index == self.yigin.currentIndex():
            self.head_bar.baslik.setText(baslik)
            self.head_bar.aciklama.setText(aciklama)
            self.head_bar.aciklama.setVisible(bool(aciklama))

    def _toast_goster(self, mesaj):
        if getattr(self, "_toast", None) is not None:
            self._toast.goster(mesaj)

    def _sayfa_kartlari(self):
        """Her sekmenin kök yerleşimini tek yüzeye oturtur (kart içinde kart yok).

        Hem kurulum sırasında hem de `archive_ui.install` sonrasında çağrılır;
        bu yüzden yığındaki her sayfayı gezer.
        """
        for i in range(self.yigin.count()):
            widget = self.yigin.widget(i)
            if widget is None:
                continue
            layout = widget.layout()
            if layout is None:
                continue
            if widget.objectName() not in ("scanBody", "sayfa"):
                widget.setObjectName("sayfa")
                widget.setAttribute(Qt.WA_StyledBackground, True)
            if widget.property("kenar"):
                continue
            widget.setProperty("kenar", True)
            layout.setContentsMargins(22, 18, 22, 20)
            layout.setSpacing(14)

    def _nav_toggle(self):
        self._collapsed = not self._collapsed
        self.rail.setFixedWidth(86 if self._collapsed else self._rail_width)
        self.rail_brand.setVisible(not self._collapsed)
        self.rail_toggle.setText("" if self._collapsed else "Menüyü daralt")
        self.rail_toggle.setIcon(theme.symbol_icon("right" if self._collapsed else "left"))
        self.rail.layout().setContentsMargins(8 if self._collapsed else 18, 24, 8 if self._collapsed else 18, 20)
        self.rail_toggle.setToolTip("Menüyü genişlet" if self._collapsed else "Menüyü daralt")
        for i, title in enumerate(EKRANLAR):
            self.nav.item(i).setText("" if self._collapsed else title)
            self.nav.item(i).setToolTip(title)
        for button, title in self.rail_actions:
            button.setText("" if self._collapsed else title)
        self._scan_state(getattr(self, "_scan_status", "idle"))
        self.nav.viewport().update()

    def _load_window_geometry(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1440, 860)
            self._geometry_ready = True
            return
        area = screen.availableGeometry()
        saved = QSettings("Evrakci", "Appearance").value("main_geometry")
        if isinstance(saved, QRect) and saved.isValid():
            target = QRect(saved)
        else:
            target = QRect(0, 0, min(1440, int(area.width() * .9)),
                           min(860, int(area.height() * .9)))
            target.moveCenter(area.center())
        target.setWidth(min(max(target.width(), self.minimumWidth()), area.width()))
        target.setHeight(min(max(target.height(), self.minimumHeight()), area.height()))
        if not any(target.intersects(s.availableGeometry()) for s in QApplication.screens()):
            target.moveCenter(area.center())
        else:
            current = next((s.availableGeometry() for s in QApplication.screens()
                            if target.intersects(s.availableGeometry())), area)
            target.moveLeft(max(current.left(), min(target.left(), current.right() - target.width() + 1)))
            target.moveTop(max(current.top(), min(target.top(), current.bottom() - target.height() + 1)))
        self.setGeometry(target)
        self._geometry_ready = True

    def _save_window_geometry(self):
        if self._geometry_ready and not self.isMaximized() and not self.isMinimized():
            QSettings("Evrakci", "Appearance").setValue("main_geometry", self.geometry())

    def _otomatik_kilitle(self):
        if not remember.enabled(self.kasa_yolu):
            self.kilitle()

    def _open_preview(self,result):
        if self.con is None or self._locked: return
        self._preview_result = result
        self.preview_path.setText(result['path'])
        self.onizleme.goster(self.con,result,self._sifre)
        self._onizleme_konum()
        self.preview_dialog.show(); self.preview_dialog.raise_()
        self.onizleme.setFocus()

    def _onizleme_satir(self):
        """Önizlenen belgenin arama sonuçlarındaki satırı (yoksa None)."""
        yol = (getattr(self, "_preview_result", None) or {}).get("path")
        if not yol:
            return None
        for satir, sonuc in enumerate(self.sonuclar):
            if sonuc.get("path") == yol:
                return satir
        return None

    def _onizleme_konum(self):
        """Önizleme penceresindeki belge konumunu ve gezinme düğmelerini tazeler."""
        satir = self._onizleme_satir()
        if satir is None:
            self.preview_konum.setText("")
            self.preview_once.setEnabled(False)
            self.preview_sonra.setEnabled(False)
            return
        self.preview_konum.setText(f"{satir + 1} / {len(self.sonuclar)}")
        self.preview_once.setEnabled(satir > 0)
        self.preview_sonra.setEnabled(satir < len(self.sonuclar) - 1)

    def _onizleme_komsu(self, yon):
        satir = self._onizleme_satir()
        if satir is None:
            return
        hedef = satir + yon
        if not 0 <= hedef < len(self.sonuclar):
            return
        idx = self.sonuc_model.index(hedef, 0)
        self.sonuc_liste.setCurrentIndex(idx)
        self.sonuc_izgara.setCurrentIndex(idx)
        self._secim_guncelle()
        self._sec(self.sonuc_model.index(hedef, 0))

    def _copy_path(self):
        QApplication.clipboard().setText(self.preview_path.text())

    def _copy_result_path(self):
        idx=self.sonuc_liste.currentIndex()
        if idx.isValid() and idx.row()<len(self.sonuclar):
            QApplication.clipboard().setText(self.sonuclar[idx.row()]['path'])

    def _open_folder(self):
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.preview_path.text())))

    def _open_file(self):
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.preview_path.text()))

    def _files_refresh(self,reset=False):
        archive_ui.files_refresh(self,reset)

    def _files_page(self,direction):
        archive_ui.files_page(self,direction)

    def _file_open(self,*args):
        archive_ui.file_open(self,*args)

    def _dosya_ayrinti(self, _idx=None):
        idx = self.file_list.currentIndex()
        satir = self.file_rows[idx.row()] if idx.isValid() and idx.row() < len(self.file_rows) else None
        if satir is None:
            self.dosya_ad.setText("Bir kayıt seçin")
            self.dosya_yol.clear()
            self.dosya_bilgi.clear()
            self.dosya_onizle.setEnabled(False)
            return
        _fid, yol, ad, _uz, durum, hata, kaynak = satir
        self.dosya_ad.setText(ad)
        self.dosya_yol.setText(yol)
        parca = [archive_ui.STATUS.get(durum, durum)]
        if hata:
            parca.append(hata)
        parca.append("Kaynak: " + (kaynak or "—"))
        self.dosya_bilgi.setText("  •  ".join(parca))
        self.dosya_onizle.setEnabled(True)

    def _coverage_report(self):
        if self.con is None: return
        dialog=QDialog(self); dialog.setWindowTitle('Evrakçı • İndeks kapsamı'); dialog.resize(850,600)
        layout=QVBoxLayout(dialog); text=QPlainTextEdit(); text.setReadOnly(True); layout.addWidget(text)
        more=QPushButton('Sonraki hatalar'); layout.addWidget(more)
        state={'offset':0,'generation':self._job_generation}
        def load():
            offset=state['offset']; text.appendPlainText('Kapsam raporu yükleniyor…')
            def operation(con):
                return con.execute('SELECT path,error_code FROM scan_errors ORDER BY run_id DESC,path LIMIT 101 OFFSET ?',(offset,)).fetchall(),con.execute('SELECT index_status,count(*) FROM files GROUP BY index_status').fetchall()
            def ready(value):
                if not dialog.isVisible(): return
                rows,counts=value
                if offset==0: text.setPlainText('\n'.join(f'{archive_ui.STATUS.get(s,s)}: {n}' for s,n in counts)+'\n\nErişim hataları:')
                text.appendPlainText('\n'.join(f'{path} • {code}' for path,code in rows[:100]) or 'Kayıtlı erişim hatası yok.')
                state['offset']+=min(100,len(rows)); more.setEnabled(len(rows)>100)
            archive_ui.job(self,'coverage_report',operation,ready)
        more.clicked.connect(load); dialog.show(); load()

    def _search_next(self):
        self._search_offset+=50
        self._ara_simdi(reset=False)





    def _kisaltmalar(self):
        self.hareketsizlik = QTimer(self)
        self.hareketsizlik.timeout.connect(self._hareket_kontrol)
        self.hareketsizlik.start(60_000)
        self._son_hareket = dt.datetime.now()
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, _o, ev):
        from PySide6.QtCore import QEvent
        if ev.type() == QEvent.Resize and _o is getattr(self, "source_split", None):
            try:
                QTimer.singleShot(0, self._source_layout)
            except RuntimeError:
                pass
        if ev.type() in (QEvent.MouseMove, QEvent.KeyPress, QEvent.MouseButtonPress):
            self._son_hareket = dt.datetime.now()
        return super().eventFilter(_o, ev)

    def _hareket_kontrol(self):
        try:
            dk = int(migrate.get_setting(self.con, "kilit_suresi", "0"))
        except Exception:
            return
        if not self._locked and dk > 0 and (dt.datetime.now() - self._son_hareket).total_seconds() > dk * 60:
            self._otomatik_kilitle()

    # -- arama ekrani: tek yuzey uzerinde uc bolme (filtreler | sonuclar | secili evrak) --
    def _ekran_ara(self):
        w = QWidget()
        k = QVBoxLayout(w)
        k.setContentsMargins(22, 18, 22, 20)
        k.setSpacing(14)
        # Küçük resim yükleyicileri: arama başına tazelenir (bkz. _thumblari_baslat).
        self._thumb_loader = None
        self._buyuk_loader = None
        self._dosya_thumb_loader = None
        self._thumb_items = {}
        self._buyuk_path = None
        self._buyuk_pixmap = None
        self._sorgu_alanlari = set()   # sorgunun kurduğu alanlar (M5)

        self.search_bar = QWidget()
        ust = QHBoxLayout(self.search_bar)
        ust.setContentsMargins(0, 0, 0, 0)
        ust.setSpacing(10)
        self.arama_kutu = QLineEdit()
        self.arama_kutu.setObjectName("search")
        self.arama_kutu.setAccessibleName("Belge arama")
        self.arama_kutu.setPlaceholderText("Arşivinizde arayın…   Örneğin: Ankara vergi 2024")
        self.arama_kutu.setToolTip("Alan sözdizimi: " + sorgu.YARDIM
                                   + "\nAlan dışı sözcükler içerik aramasına girer.")
        self.arama_kutu.setClearButtonEnabled(True)
        self.arama_kutu.returnPressed.connect(self._ara_simdi)
        ust.addWidget(self.arama_kutu, 1)
        search = QPushButton("Ara")
        search.setProperty("birincil", True)
        search.clicked.connect(self._ara_simdi)
        ust.addWidget(search)
        k.addWidget(self.search_bar)
        # Satır içi sorgu doğrulaması (docspell deseni): hatalı alanda imleç gösterilir.
        self.sorgu_uyari = QLabel("")
        self.sorgu_uyari.setProperty("hata", True)
        self.sorgu_uyari.setTextFormat(Qt.PlainText)
        self.sorgu_uyari.setWordWrap(True)
        self.sorgu_uyari.setAccessibleName("Sorgu doğrulama uyarısı")
        from PySide6.QtGui import QFont
        self.sorgu_uyari.setFont(QFont("Cascadia Mono", 9))
        self.sorgu_uyari.hide()
        k.addWidget(self.sorgu_uyari)
        self.search_progress = QProgressBar()
        self.search_progress.setRange(0, 0)
        self.search_progress.setTextVisible(False)
        self.search_progress.hide()
        k.addWidget(self.search_progress)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._ara_simdi)
        self.arama_kutu.textChanged.connect(lambda _t: self._debounce.start())

        yuzey = QFrame()
        yuzey.setObjectName("card")
        yuzey_layout = QHBoxLayout(yuzey)
        yuzey_layout.setContentsMargins(0, 0, 0, 0)
        yuzey_layout.setSpacing(0)
        islik = QSplitter(Qt.Horizontal)
        islik.setChildrenCollapsible(False)

        # -- filtre sutunu --
        filtre = QWidget()
        filtre.setObjectName("sideRail")
        filtre.setAttribute(Qt.WA_StyledBackground, True)
        fl = QVBoxLayout(filtre)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(10)
        kaydir = QScrollArea()
        kaydir.setWidgetResizable(True)
        kaydir.setFrameShape(QScrollArea.NoFrame)
        ic = QWidget()
        form = QVBoxLayout(ic)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        fl.addWidget(kaydir, 1)
        kaydir.setWidget(ic)
        form.addWidget(bolum("Filtreler"))
        self.filtre_sayi = sayac("")
        self.filtre_sayi.hide()
        form.addWidget(self.filtre_sayi)
        # Aktif filtreler başlığın hemen altında: kaldırılabilir çipler + sıfırlama.
        self.filtre_cipleri = QVBoxLayout()
        self.filtre_cipleri.setSpacing(5)
        form.addLayout(self.filtre_cipleri)
        self.filtre_sifirla = QPushButton("Filtreleri sıfırla")
        self.filtre_sifirla.setProperty("kucuk", True)
        self.filtre_sifirla.setToolTip("Tüm arama filtrelerini temizler")
        self.filtre_sifirla.clicked.connect(lambda: self._filtre_temizle())
        self.filtre_sifirla.hide()
        form.addWidget(self.filtre_sifirla)
        self.yil_filtre = QLineEdit()
        self.yil_filtre.setPlaceholderText("Yıl (ör. 2024)")
        self.tur_filtre = QComboBox()
        self.tur_filtre.addItems(["tümü", ".pdf", ".xlsx", ".xls", ".docx", ".doc",
                                  ".txt", ".csv", ".pptx", ".epub", ".eml", ".zip"])
        self.sirket_filtre = QLineEdit()
        self.sirket_filtre.setPlaceholderText("Şirket veya klasör")
        self.etiket_filtre = QLineEdit()
        self.etiket_filtre.setPlaceholderText("Etiket")
        for baslik, x in (("Yıl", self.yil_filtre), ("Tür", self.tur_filtre),
                          ("Şirket veya klasör", self.sirket_filtre), ("Etiket", self.etiket_filtre)):
            alan = QVBoxLayout()
            alan.setSpacing(4)
            alan.addWidget(label(baslik, "ikincil"))
            alan.addWidget(x)
            form.addLayout(alan)
        self.yil_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        self.tur_filtre.currentTextChanged.connect(lambda _t: self._ara_simdi())
        self.sirket_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        self.etiket_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        form.addWidget(bolum("Kayıtlı aramalar"))
        self.kayitli_liste = QComboBox()
        self.kayitli_liste.setPlaceholderText("Kayıtlı arama")
        self.kayitli_liste.activated.connect(self._kayitli_calistir)
        form.addWidget(self.kayitli_liste)
        kayit_satir = QHBoxLayout()
        kayit_satir.setSpacing(8)
        self.kaydet_btn = QPushButton("Kaydet")
        self.kaydet_btn.setProperty("kucuk", True)
        self.kaydet_btn.clicked.connect(self._arama_kaydet)
        kayit_satir.addWidget(self.kaydet_btn)
        self.kayit_sil_btn = QPushButton("Sil")
        self.kayit_sil_btn.setProperty("kucuk", True)
        self.kayit_sil_btn.clicked.connect(self._kayitli_sil)
        kayit_satir.addWidget(self.kayit_sil_btn)
        kayit_satir.addStretch(1)
        form.addLayout(kayit_satir)
        form.addWidget(bolum("Etiket"))
        self.etiket_yaz = QLineEdit()
        self.etiket_yaz.setPlaceholderText("Seçili sonuca etiket")
        form.addWidget(self.etiket_yaz)
        etiket_satir = QHBoxLayout()
        etiket_satir.setSpacing(8)
        self.etiket_ekle_btn = QPushButton("Etiketle")
        self.etiket_ekle_btn.setProperty("kucuk", True)
        self.etiket_ekle_btn.clicked.connect(self._etiket_ekle)
        etiket_satir.addWidget(self.etiket_ekle_btn)
        self.etiket_sil_btn = QPushButton("Etiketi kaldır")
        self.etiket_sil_btn.setProperty("kucuk", True)
        self.etiket_sil_btn.clicked.connect(self._etiket_sil)
        etiket_satir.addWidget(self.etiket_sil_btn)
        etiket_satir.addStretch(1)
        form.addLayout(etiket_satir)
        form.addStretch(1)
        islik.addWidget(filtre)

        # -- sonuc sutunu --
        orta = QWidget()
        ok = QVBoxLayout(orta)
        ok.setContentsMargins(16, 14, 16, 14)
        ok.setSpacing(10)
        bas = QHBoxLayout()
        bas.setSpacing(9)
        bas.addWidget(bolum("Sonuçlar"))
        self.sonuc_sayi = sayac("")
        self.sonuc_sayi.hide()
        bas.addWidget(self.sonuc_sayi)
        bas.addStretch(1)
        # Görünüm modu (paperless görünüm anahtarı deseni).
        self.gorunum_btnleri = {}
        for etiket, mod, ikon in (("Kompakt", "kompakt", "compact"),
                                  ("Satırlar", "satir", "rows"),
                                  ("Izgara", "izgara", "grid")):
            dugme = QPushButton()
            dugme.setCheckable(True)
            dugme.setIcon(theme.symbol_icon(ikon))
            dugme.setIconSize(QSize(16, 16))
            dugme.setFixedWidth(34)
            dugme.setProperty("dar", True)
            dugme.setToolTip(f"{etiket} görünüm")
            dugme.setAccessibleName(f"{etiket} görünüm")
            dugme.clicked.connect(lambda _c=False, m=mod: self._gorunum_ayarla(m))
            self.gorunum_btnleri[mod] = dugme
            bas.addWidget(dugme)
        # Gösterilecek alanlar (paperless "Show" menüsü deseni).
        self.goster_btn = QPushButton("Göster")
        self.goster_btn.setProperty("kucuk", True)
        self.goster_btn.setToolTip("Satırlarda hangi bilgiler görünsün")
        self.goster_menu = QMenu(self.goster_btn)
        self.goster_btn.setMenu(self.goster_menu)
        bas.addWidget(self.goster_btn)
        self.csv_btn = QPushButton("CSV indir")
        self.csv_btn.setProperty("ghost", True)
        self.csv_btn.setProperty("kucuk", True)
        self.csv_btn.clicked.connect(self._sonuc_csv)
        bas.addWidget(self.csv_btn)
        ok.addLayout(bas)
        # Toplu işlem çubuğu: seçim denetimleri + toplu etiket/CSV.
        self.toplu_bar = QWidget()
        toplu = QHBoxLayout(self.toplu_bar)
        toplu.setContentsMargins(0, 0, 0, 0)
        toplu.setSpacing(7)
        self.secim_btnleri = []
        for etiket, adet, ipucu in (("Hiçbiri", 0, "Seçimi temizle"),
                                    ("Sayfa", 50, "İlk 50 sonucu seç"),
                                    ("Tümü", -1, "Tüm sonuçları seç")):
            dugme = QPushButton(etiket)
            dugme.setProperty("kucuk", True)
            dugme.setToolTip(ipucu)
            dugme.clicked.connect(lambda _c=False, n=adet: self._secim_ayarla(n))
            toplu.addWidget(dugme)
            self.secim_btnleri.append(dugme)
        self.secim_sayac = sayac("")
        toplu.addWidget(self.secim_sayac)
        toplu.addStretch(1)
        self.toplu_etiket_btn = QPushButton("Etiketle")
        self.toplu_etiket_btn.setProperty("kucuk", True)
        self.toplu_etiket_btn.setToolTip("Seçili belgelere tek işlemde etiket ekle")
        self.toplu_etiket_btn.clicked.connect(lambda: self._toplu_etiket())
        toplu.addWidget(self.toplu_etiket_btn)
        self.toplu_etiket_sil_btn = QPushButton("Etiketi kaldır")
        self.toplu_etiket_sil_btn.setProperty("kucuk", True)
        self.toplu_etiket_sil_btn.setToolTip("Seçili belgelerden etiketi tek işlemde kaldır")
        self.toplu_etiket_sil_btn.clicked.connect(lambda: self._toplu_etiket(kaldir=True))
        toplu.addWidget(self.toplu_etiket_sil_btn)
        self.toplu_csv_btn = QPushButton("Seçimi CSV")
        self.toplu_csv_btn.setProperty("kucuk", True)
        self.toplu_csv_btn.setToolTip("Yalnız seçili sonuçları CSV olarak indir")
        self.toplu_csv_btn.clicked.connect(self._toplu_csv)
        toplu.addWidget(self.toplu_csv_btn)
        self.toplu_bar.hide()
        ok.addWidget(self.toplu_bar)
        self.sonuc_model = QStandardItemModel()
        self.sonuc_liste = QListView()
        self.sonuc_liste.setObjectName("cardList")
        self.sonuc_liste.setItemDelegate(CardDelegate(self.sonuc_liste, thumb=True))
        self.sonuc_liste.setModel(self.sonuc_model)
        self.sonuc_liste.setSpacing(2)
        self.sonuc_liste.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.sonuc_liste.clicked.connect(self._secim_guncelle)
        self.sonuc_liste.doubleClicked.connect(self._sec)
        self.sonuc_izgara = QListView()
        self.sonuc_izgara.setObjectName("gridList")
        self.sonuc_izgara.setViewMode(QListView.IconMode)
        self.sonuc_izgara.setResizeMode(QListView.Adjust)
        self.sonuc_izgara.setWrapping(True)
        self.sonuc_izgara.setMovement(QListView.Static)
        self.sonuc_izgara.setGridSize(QSize(184, 220))
        self.sonuc_izgara.setItemDelegate(GridDelegate(self.sonuc_izgara))
        self.sonuc_izgara.setModel(self.sonuc_model)
        self.sonuc_izgara.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.sonuc_izgara.clicked.connect(self._secim_guncelle)
        self.sonuc_izgara.doubleClicked.connect(self._sec)
        for gorunum in (self.sonuc_liste, self.sonuc_izgara):
            gorunum.selectionModel().selectionChanged.connect(
                lambda *_a: self._secim_guncelle_bulk())
        self.sonuc_panel = QStackedWidget()
        self.sonuc_panel.addWidget(self.sonuc_liste)   # 0: satır/kompakt
        self.sonuc_panel.addWidget(self.sonuc_izgara)  # 1: ızgara
        self.search_empty = EmptyState("Aradığınız belgeye ulaşın", "Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
        self.sonuc_panel.addWidget(self.search_empty)  # 2: boş durum
        self._bos_index = 2
        self.sonuc_panel.setCurrentIndex(self._bos_index)
        ok.addWidget(self.sonuc_panel, 1)
        self.oneri = QLabel("")
        self.oneri.setProperty("ikincil", True)
        self.oneri.setWordWrap(True)
        ok.addWidget(self.oneri)
        self.search_more = QPushButton("Sonraki sonuçlar")
        self.search_more.setProperty("kucuk", True)
        self.search_more.clicked.connect(self._search_next)
        self.search_more.hide()
        ok.addWidget(self.search_more)
        islik.addWidget(orta)

        # -- secili evrak sutunu --
        ayrinti = QWidget()
        al = QVBoxLayout(ayrinti)
        al.setContentsMargins(16, 14, 16, 16)
        al.setSpacing(10)
        al.addWidget(bolum("Seçili evrak"))
        self.secim_gorsel = GorselKutusu()
        al.addWidget(self.secim_gorsel, 1)
        self.secim_ad = label("Henüz seçim yok", "subheading")
        self.secim_ad.setWordWrap(True)
        al.addWidget(self.secim_ad)
        self.secim_yol = label("", "ikincil")
        self.secim_yol.setTextFormat(Qt.PlainText)
        self.secim_yol.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.secim_yol.setWordWrap(True)
        al.addWidget(self.secim_yol)
        al.addWidget(bolme())
        self.secim_tur = label("", "ikincil")
        self.secim_tur.setWordWrap(True)
        al.addWidget(self.secim_tur)
        self.secim_etiket = label("", "ikincil")
        self.secim_etiket.setWordWrap(True)
        al.addWidget(self.secim_etiket)
        self.secim_onizle = QPushButton("Ön izle")
        self.secim_onizle.setProperty("birincil", True)
        self.secim_onizle.clicked.connect(lambda: self._sec(self._aktif_gosterim().currentIndex()))
        al.addWidget(self.secim_onizle)
        self.secim_kopyala = QPushButton("Yol kopyala")
        self.secim_kopyala.clicked.connect(self._copy_result_path)
        al.addWidget(self.secim_kopyala)
        islik.addWidget(ayrinti)
        islik.setStretchFactor(0, 0)
        islik.setStretchFactor(1, 1)
        islik.setStretchFactor(2, 0)
        islik.setSizes([240, 520, 260])
        self.arama_islik = islik
        yuzey_layout.addWidget(islik)
        k.addWidget(yuzey, 1)
        self._secim_guncelle()
        self._gorunum = "satir"
        self._gorunum_uygula()
        self._goster_menu_tazele()
        self._filtre_cipleri()
        self.yigin.addWidget(w)

    def _secim_guncelle(self, _idx=None):
        secili = self._secili_dosya()
        if secili is None or self.con is None:
            self.secim_ad.setText("Henüz seçim yok")
            self.secim_yol.clear()
            self.secim_tur.clear()
            self.secim_etiket.clear()
            self.secim_onizle.setEnabled(False)
            self.secim_kopyala.setEnabled(False)
            self._buyuk_gorsel_yukle(None)
            return
        try:
            etiketler = rank.file_tags(self.con, secili["file_id"])
        except Exception:
            etiketler = []
        self.secim_ad.setText(secili.get("name", ""))
        self.secim_yol.setText(secili.get("path", ""))
        tur = secili.get("ext", "").lstrip(".").upper()
        self.secim_tur.setText(f"Tür: {tur}" + (f" • {secili['label']}" if secili.get("label") else ""))
        self.secim_etiket.setText("Etiket: " + ", ".join(etiketler) if etiketler else "Etiket yok")
        self.secim_onizle.setEnabled(True)
        self.secim_kopyala.setEnabled(True)
        self._buyuk_gorsel_yukle(secili.get("path"))

    # -- çoklu seçim ve toplu işlem --

    def _secim_satirlari(self):
        """Etkin görünümde seçili satır numaraları."""
        secim = self._aktif_gosterim().selectionModel()
        return {i.row() for i in secim.selectedIndexes() if i.isValid()}

    def _secili_idler(self):
        """Seçili sonuçların file_id'leri (satıra göre sıralı)."""
        return [self.sonuclar[s]["file_id"] for s in sorted(self._secim_satirlari())
                if 0 <= s < len(self.sonuclar)]

    def _secim_ayarla(self, adet):
        """Seçim denetimi: 0 temizler, pozitif ilk n sonucu, -1 tümünü seçer."""
        gorunum = self._aktif_gosterim()
        model = self.sonuc_model
        secim = gorunum.selectionModel()
        secim.clearSelection()
        if adet != 0 and model.rowCount() > 0:
            son = model.rowCount() if adet < 0 else min(model.rowCount(), adet)
            blok = QItemSelection(model.index(0, 0), model.index(son - 1, 0))
            secim.select(blok, QItemSelectionModel.ClearAndSelect)
        self._secim_guncelle_bulk()

    def _secim_guncelle_bulk(self):
        """Toplu işlem çubuğunu ve tek belge panelini seçime göre tazeler."""
        adet = len(self._secim_satirlari())
        self.secim_sayac.setText(f"{adet} seçili" if adet else "")
        self.secim_sayac.setVisible(bool(adet))
        for dugme in (self.toplu_etiket_btn, self.toplu_etiket_sil_btn, self.toplu_csv_btn):
            dugme.setEnabled(bool(adet))
        self.toplu_bar.setVisible(bool(self.sonuclar))
        if self.sonuclar:
            self._secim_guncelle()

    def _toplu_etiket(self, kaldir=False):
        """Seçili belgelere tek işlemde etiket ekler/kaldırır (hatada geri alınır)."""
        from PySide6.QtWidgets import QInputDialog
        idler = self._secili_idler()
        if not idler:
            self.durum.showMessage("Önce sonuç seçin.")
            return
        etiket, tamam = QInputDialog.getText(
            self, "Etiketi kaldır" if kaldir else "Etiketle",
            f"{len(idler)} belge için etiket adı:")
        etiket = (etiket or "").strip().lower()
        if not tamam or not etiket:
            return

        def islem(con):
            return rank.tags_many(con, idler, etiket, remove=kaldir)

        def bitti(sayi):
            self._toast_goster(f"{sayi} belge için '{etiket}' etiketi "
                               + ("kaldırıldı." if kaldir else "eklendi."))
            self._ara_simdi()

        def hata(mesaj):
            QMessageBox.warning(self, "Etiket", f"Toplu işlem geri alındı: {mesaj}")

        archive_ui.job(self, "toplu_etiket", islem, bitti, writable=True, failed=hata)

    def _toplu_csv(self):
        """Yalnız seçili sonuçları CSV olarak indirir."""
        secilenler = [self.sonuclar[s] for s in sorted(self._secim_satirlari())
                      if 0 <= s < len(self.sonuclar)]
        if not secilenler:
            QMessageBox.information(self, "CSV", "Önce sonuç seçin.")
            return
        yol, _ = QFileDialog.getSaveFileName(self, "Seçimi indir", "secili-sonuclar.csv",
                                             "CSV (*.csv)")
        if not yol:
            return
        try:
            from pathlib import Path
            Path(yol).write_bytes(rank.results_csv(self.con, secilenler).encode("utf-8-sig"))
        except OSError as e:
            QMessageBox.warning(self, "CSV", f"Yazılamadı: {e}")
            return
        QMessageBox.information(self, "CSV", f"{len(secilenler)} seçili sonuç kaydedildi.")

    # -- küçük resimler --

    def _thumblari_durdur(self):
        """Koşan küçük resim yükleyicilerini durdur (arama/kilit geçişleri)."""
        for ad in ("_thumb_loader", "_buyuk_loader", "_dosya_thumb_loader"):
            yukleyici = getattr(self, ad, None)
            if yukleyici is not None:
                yukleyici.durdur()
                yukleyici.wait(3000)
                setattr(self, ad, None)

    # -- filtre çipleri --

    ALANLAR = ("yol", "tur", "ozet", "etiket")
    GORUNUMLER = ("kompakt", "satir", "izgara")

    def _filtre_degerleri(self):
        """(etiket, değer, temizleme işlevi) üçlüleri — yalnız dolu olanlar çip olur."""
        return (
            ("Yıl", self.yil_filtre.text().strip(), self.yil_filtre.clear),
            ("Tür", "" if self.tur_filtre.currentText() == "tümü" else self.tur_filtre.currentText(),
             lambda: self.tur_filtre.setCurrentIndex(max(0, self.tur_filtre.findText("tümü")))),
            ("Klasör", self.sirket_filtre.text().strip(), self.sirket_filtre.clear),
            ("Etiket", self.etiket_filtre.text().strip(), self.etiket_filtre.clear),
        )

    def _filtre_cipleri(self):
        """Aktif filtreleri kaldırılabilir çip olarak gösterir; sayaç ve sıfırlama."""
        while self.filtre_cipleri.count():
            oge = self.filtre_cipleri.takeAt(0)
            widget = oge.widget()
            if widget is not None:
                # deleteLater tek başına yetmez: widget layout'tan çıksa da
                # görünür kalır; önce gizlenip ebeveyninden ayrılır.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        aktif = 0
        for etiket, deger, temizle in self._filtre_degerleri():
            if not deger:
                continue
            aktif += 1
            cip = Cip(f"{etiket}: {deger}")
            cip.silindi.connect(temizle)
            cip.silindi.connect(self._ara_simdi)
            self.filtre_cipleri.addWidget(cip)
        self.filtre_sayi.setText(str(aktif))
        self.filtre_sayi.setVisible(bool(aktif))
        self.filtre_sifirla.setVisible(bool(aktif))

    def _filtre_temizle(self):
        """Tüm arama filtrelerini temizler ve aramayı yeniler."""
        self.yil_filtre.clear()
        self.tur_filtre.setCurrentIndex(max(0, self.tur_filtre.findText("tümü")))
        self.sirket_filtre.clear()
        self.etiket_filtre.clear()
        self._sorgu_alanlari = set()
        self._ara_simdi()

    # -- görünüm modları ve gösterilecek alanlar --

    def _alanlar(self):
        """Satırlarda gösterilecek alanlar (ayar yoksa tümü; boşsa yalnız ad)."""
        varsayilan = ",".join(self.ALANLAR)
        ham = (migrate.get_setting(self.con, "goster_alanlari", varsayilan)
               if self.con is not None else varsayilan)
        return {a for a in ham.split(",") if a}

    def _goster_menu_tazele(self):
        """Gösterilecek alanlar menüsünü mevcut seçimle kurar."""
        self.goster_menu.clear()
        alanlar = self._alanlar()
        for etiket, anahtar in (("Yol", "yol"), ("Tür ve etiket", "tur"),
                                ("İçerik özeti", "ozet"), ("Etiketler", "etiket")):
            eylem = self.goster_menu.addAction(etiket)
            eylem.setCheckable(True)
            eylem.setChecked(anahtar in alanlar)
            eylem.toggled.connect(lambda acik, a=anahtar: self._alan_degistir(a, acik))

    def _alan_degistir(self, anahtar, acik):
        """Bir alanı aç/kapat; ayarı sakla ve satırları yeniden yaz."""
        alanlar = self._alanlar()
        if acik:
            alanlar.add(anahtar)
        else:
            alanlar.discard(anahtar)
        sira = [a for a in self.ALANLAR if a in alanlar]
        if self.con is not None:
            migrate.set_setting(self.con, "goster_alanlari", ",".join(sira))
        self._goster_menu_tazele()
        self._satirlari_yaz()
        self._thumblari_baslat()

    def _gorunum_yukle(self):
        """Kayıtlı görünüm modunu ve alan seçimini uygular (kasa açılışında)."""
        mod = (migrate.get_setting(self.con, "gorunum_modu", "satir")
               if self.con is not None else "satir")
        if mod not in self.GORUNUMLER:
            mod = "satir"
        self._gorunum = mod
        self._gorunum_uygula()
        self._goster_menu_tazele()

    def _gorunum_ayarla(self, mod):
        if mod not in self.GORUNUMLER:
            return
        self._gorunum = mod
        if self.con is not None:
            migrate.set_setting(self.con, "gorunum_modu", mod)
        self._gorunum_uygula()

    def _gorunum_uygula(self):
        """Görünüm moduna göre delege ve panel seçimi."""
        mod = getattr(self, "_gorunum", "satir")
        self.sonuc_liste.setItemDelegate(
            CardDelegate(self.sonuc_liste, thumb=True, compact=(mod == "kompakt")))
        for anahtar, dugme in self.gorunum_btnleri.items():
            dugme.setChecked(anahtar == mod)
        self.goster_btn.setEnabled(mod != "izgara")
        # Etkin olmayan yüzeyin seçimi temizlenir (iki görünüm ayrı seçim tutar).
        for gorunum in (self.sonuc_liste, self.sonuc_izgara):
            if gorunum is not self._aktif_gosterim():
                gorunum.selectionModel().clearSelection()
        self._secim_guncelle_bulk()
        self._sonuc_gorunumu(bool(self.sonuclar))
        self.sonuc_liste.doItemsLayout()
        self.sonuc_izgara.doItemsLayout()

    def _sonuc_gorunumu(self, dolu):
        """Sonuç yüzeyi: dolu değilse boş durum, doluysa seçili görünüm."""
        if not dolu:
            self.sonuc_panel.setCurrentIndex(self._bos_index)
            return
        self.sonuc_panel.setCurrentIndex(1 if getattr(self, "_gorunum", "satir") == "izgara" else 0)

    # -- satır içeriği --

    @staticmethod
    def _durum_notu(sonuc):
        if sonuc.get('index_status') != 'ok' or not sonuc.get('content_available', True):
            return (archive_ui.STATUS.get(sonuc.get('index_status'), sonuc.get('index_status', ''))
                    + ' • ' + (sonuc.get('error_code') or '')
                    + (' • Yalnız ad/yol eşleşmesi' if not sonuc.get('content_available', True) else ''))
        return ""

    def _satir_metni(self, sonuc, etiketler, ozet):
        """Seçili alanlara göre satır metni (ad her zaman ilk satırdır)."""
        alanlar = self._alanlar()
        tur = sonuc.get("ext", "").lstrip(".").upper()
        durum = self._durum_notu(sonuc)
        satirlar = [sonuc["name"]]
        if "yol" in alanlar:
            satirlar.append(sonuc["path"])
        if "tur" in alanlar:
            satirlar.append(f"{tur}  •  {sonuc.get('label','')}" + (f"  •  {durum}" if durum else ""))
        if "ozet" in alanlar:
            satirlar.append(ozet[:150])
        if "etiket" in alanlar and etiketler:
            satirlar.append("Etiket: " + ", ".join(etiketler))
        if durum and "tur" not in alanlar:
            satirlar.append(durum)
        return "\n".join(satirlar)

    def _satirlari_yaz(self):
        """`sonuclar` listesini gösterilecek alanlara göre modele yeniden yazar."""
        from PySide6.QtGui import QTextDocument
        self.sonuc_model.clear()
        for sonuc in self.sonuclar:
            try:
                etiketler = rank.file_tags(self.con, sonuc["file_id"])
            except Exception:
                etiketler = []
            belge = QTextDocument()
            belge.setHtml(sonuc.get("snippet", ""))
            ozet = belge.toPlainText()
            item = QStandardItem(self._satir_metni(sonuc, etiketler, ozet))
            item.setEditable(False)
            item.setToolTip(sonuc['path'] + '\n' + ozet)
            self.sonuc_model.appendRow(item)
    @staticmethod
    def _gorsel_tur(ext):
        """Küçük resmi üretilebilen uzantılar (PDF + görseller)."""
        ext = (ext or "").lower()
        return ext == ".pdf" or ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")

    def _list_gorselleri(self, model, esleme, slot):
        """Bir QStandardItemModel için küçük resim yükleyicisi kurar.

        `esleme`: {kaynak yol: satır}. Yükleyici `slot` adlı öznitelikte
        tutulur; yenisi kurulmadan önce var olan durdurulur. Sinyaller bağlı
        metoda bağlanır: iş parçacıkları arası kuyruklu bağlantı sayesinde
        QPixmap yalnızca GUI iş parçacığında kurulur.
        """
        onceki = getattr(self, slot, None)
        if onceki is not None:
            onceki.durdur()
            onceki.wait(3000)
            setattr(self, slot, None)
        isler = [(yol, "s") for yol in list(esleme)[:40]
                 if self._gorsel_tur(os.path.splitext(yol)[1])]
        if not isler:
            return
        yukleyici = thumbs.OnbellekYukleyici(isler, self)
        yukleyici.model = model
        yukleyici.esleme = esleme
        yukleyici.tamam.connect(self._thumb_sinyali)
        yukleyici.finished.connect(self._gorsel_yukleyici_bitti)
        setattr(self, slot, yukleyici)
        yukleyici.start()

    def _thumb_sinyali(self, yol, tur, dosya):
        """Küçük resim hazır: satırı günceller (GUI iş parçacığında)."""
        if self.con is None or self._locked:
            return
        yukleyici = self.sender()
        model = getattr(yukleyici, "model", None)
        if model is None:
            return
        self._model_gorsel_guncelle(model, getattr(yukleyici, "esleme", None) or {}, yol, dosya)

    def _model_gorsel_guncelle(self, model, esleme, yol, dosya):
        satir = esleme.get(yol)
        if satir is None or satir >= model.rowCount():
            return
        pixmap = QPixmap(dosya) if dosya else QPixmap()
        if pixmap.isNull():
            return  # üretilemedi: satır simge yer tutucusunda kalır
        model.setData(model.index(satir, 0), pixmap, Qt.DecorationRole)

    def _gorsel_yukleyici_bitti(self):
        yukleyici = self.sender()
        for ad in ("_thumb_loader", "_buyuk_loader", "_dosya_thumb_loader"):
            if getattr(self, ad, None) is yukleyici:
                setattr(self, ad, None)
        yukleyici.deleteLater()
        thumbs.buda()

    def _thumblari_baslat(self):
        """Görüntülenebilir ilk sonuçlar için küçük resimleri sırayla üret."""
        self._thumb_items = {sonuc["path"]: satir for satir, sonuc in enumerate(self.sonuclar[:40])}
        self._list_gorselleri(self.sonuc_model, self._thumb_items, "_thumb_loader")

    def _buyuk_gorsel_yukle(self, path):
        """Seçili evrak panelindeki büyük önizlemeyi hazırla (aynı dosya ise bekle)."""
        if path == getattr(self, "_buyuk_path", None):
            return
        onceki = getattr(self, "_buyuk_loader", None)
        if onceki is not None:
            onceki.durdur()
            self._buyuk_loader = None
        self._buyuk_path = path
        self._buyuk_pixmap = None
        self.secim_gorsel.gorsel_ata(None)
        if not path or self.con is None or self._locked:
            return
        if not self._gorsel_tur(os.path.splitext(path)[1]):
            return
        yukleyici = thumbs.OnbellekYukleyici([(path, "l")], self)
        yukleyici.tamam.connect(self._buyuk_tamam)
        yukleyici.finished.connect(self._gorsel_yukleyici_bitti)
        self._buyuk_loader = yukleyici
        yukleyici.start()

    def _buyuk_tamam(self, path, tur, dosya):
        if tur != "l" or self.con is None or self._locked:
            return
        secili = self._secili_dosya()
        if secili is None or secili.get("path") != path:
            return
        pixmap = QPixmap(dosya) if dosya else QPixmap()
        if pixmap.isNull():
            return
        self._buyuk_pixmap = pixmap
        self.secim_gorsel.gorsel_ata(pixmap)

    # -- sorgu sözdizimi --

    def _tur_secenekleri(self):
        return [self.tur_filtre.itemText(i) for i in range(self.tur_filtre.count())]

    def _sorgu_uyari_goster(self, ham, cozum):
        """Hatalı sorguda imleçli uyarı gösterir; arama çalıştırılmaz."""
        satir = sorgu.imlec_satiri(ham, cozum.imlec)
        self.sorgu_uyari.setText(f"Sorgu hatası: {cozum.hata}\n{ham}\n{satir}")
        self.sorgu_uyari.show()

    def _sorgu_alanlarini_uygula(self, alanlar):
        """Sorgudaki alanları filtre denetimlerine yazar (sinyaller kapatılarak).

        Kural: sorgu **yalnızca kendi kurduğu** alanı temizler. Kullanıcının elle
        girdiği filtre, sorgu metni değişti diye silinmez; sorgudan çıkarılan
        alan (`yil:2024` silindiyse) ise geri alınır.
        """
        onceki = getattr(self, "_sorgu_alanlari", set())
        for anahtar, denetim in (("yil", self.yil_filtre),
                                 ("klasor", self.sirket_filtre),
                                 ("etiket", self.etiket_filtre)):
            deger = alanlar.get(anahtar)
            if deger:
                if denetim.text().strip() != deger:
                    denetim.blockSignals(True)
                    denetim.setText(deger)
                    denetim.blockSignals(False)
            elif anahtar in onceki and denetim.text().strip():
                denetim.blockSignals(True)
                denetim.clear()
                denetim.blockSignals(False)
        tur = alanlar.get("tur")
        if tur:
            sira = self.tur_filtre.findText(tur)
            if sira >= 0 and self.tur_filtre.currentIndex() != sira:
                self.tur_filtre.blockSignals(True)
                self.tur_filtre.setCurrentIndex(sira)
                self.tur_filtre.blockSignals(False)
        elif "tur" in onceki and self.tur_filtre.currentText() != "tümü":
            self.tur_filtre.blockSignals(True)
            self.tur_filtre.setCurrentIndex(max(0, self.tur_filtre.findText("tümü")))
            self.tur_filtre.blockSignals(False)
        self._sorgu_alanlari = set(alanlar)

    def _ara_simdi(self, reset=True):
        if reset: self._search_offset=0
        self._debounce.stop()
        if reset:
            self._thumblari_durdur()
        if self.con is None:
            return
        ham = self.arama_kutu.text()
        cozum = sorgu.cozumle(ham, self._tur_secenekleri())
        if cozum.hata:
            self._sorgu_uyari_goster(ham, cozum)
            return
        self.sorgu_uyari.hide()
        self._sorgu_alanlarini_uygula(cozum.alanlar)
        self._filtre_cipleri()  # filtre durumu arama sonucundan bağımsız görünür
        q = cozum.serbest
        self._sorgu_serbest = q  # sonuç eşleştirmesi ham kutu metniyle değil, çözülen metinle
        self._pending_search = None
        if self._search_thread is not None:
            self._search_thread.stop.set()
        if not q.strip():
            self.sonuclar = []
            self.onizleme.temizle()
            self.sonuc_model.clear()
            self.sonuc_sayi.clear()
            self.sonuc_sayi.hide()
            self._secim_guncelle()
            self._sonuc_gorunumu(False)
            self.toplu_bar.hide()
            self.search_empty.title.setText("Aradığınız belgeye ulaşın")
            self.search_empty.text.setText("Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
            self.oneri.setText("Filtreler ayarlandı; aramak için bir sözcük de yazın."
                               if cozum.alanlar else
                               "Son aramalar Geçmiş ekranında; aramak için yazın.")
            return
        yil = self.yil_filtre.text().strip() or None
        tur = self.tur_filtre.currentText()
        tur = None if tur == "tümü" else tur
        etiket = self.etiket_filtre.text().strip().lower() or None
        request = (q, yil, tur, self.sirket_filtre.text().strip().lower(), etiket)
        self._pending_search = request
        if self._search_thread is None:
            self._arama_baslat()

    def _arama_baslat(self):
        if self._locked or self.con is None or self._pending_search is None:
            return
        request = self._pending_search
        self._pending_search = None
        self.oneri.setText("Belgeler aranıyor…")
        self._search_thread = AramaIsci(self.kasa_yolu, self._sifre, request, self)
        self._search_thread.offset=self._search_offset
        self.search_progress.show()
        self._search_thread.sonuc.connect(self._arama_bitti)
        self._search_thread.finished.connect(self._arama_temizle)
        self._search_thread.start()

    def _arama_temizle(self):
        thread = self._search_thread
        self._search_thread = None
        if thread is not None:
            thread.deleteLater()
        self._arama_baslat()

    def _arama_bitti(self, message):
        if self._locked or self.con is None:
            return
        q, yil, tur, kokf, etiket = message["request"]
        current = (getattr(self, "_sorgu_serbest", self.arama_kutu.text()),
                   self.yil_filtre.text().strip() or None,
                   None if self.tur_filtre.currentText() == "tümü" else self.tur_filtre.currentText(),
                   self.sirket_filtre.text().strip().lower(),
                   self.etiket_filtre.text().strip().lower() or None)
        if message["request"] != current:
            return
        if message.get('offset',0)!=self._search_offset:
            return
        if "error" in message:
            self.search_progress.hide()
            self.oneri.setText(f"Arama tamamlanamadı: {message['error']}")
            return
        self.search_progress.hide()
        out = message["out"]
        self.search_more.setVisible(out.get("has_more",False))
        res = out["results"]
        self.sonuclar = res
        self.sonuc_model.clear()
        self.sonuc_sayi.setText(f"{len(res)} sonuç" if res else "")
        self.sonuc_sayi.setVisible(bool(res))
        self._secim_guncelle()
        self._sonuc_gorunumu(bool(res))
        self.sonuc_liste.selectionModel().clearSelection()
        self.sonuc_izgara.selectionModel().clearSelection()
        if not res:
            self.search_empty.title.setText("Eşleşen belge bulunamadı")
            self.search_empty.text.setText("Farklı bir kelime deneyin veya arama filtrelerini genişletin.")
        self._satirlari_yaz()
        self._secim_guncelle_bulk()
        if not res:
            self.oneri.setText("Sonuç yok." + (f" Yakın: {', '.join(out['suggestions'])}"
                                               if out["suggestions"] else ""))
        else:
            self.oneri.setText(f"{len(res)} sonuç" +
                               (f" • {', '.join(out['suggestions'][:3])}" if out["suggestions"] else ""))
        if out.get('semantic_error'):
            self.oneri.setText(self.oneri.text() + ' • Anlamsal arama kullanılamadı: ' + out['semantic_error'])
        elif out.get('semantic'):
            self.oneri.setText(self.oneri.text() + ' • Anlamsal + tam arama')
        self._filtre_cipleri()
        try:
            import json
            hist_mod.save(self.con, q, json.dumps({"yil": yil or "", "tur": tur or "tümü", "klasor": kokf, "etiket": etiket or ""}, ensure_ascii=False))
        except Exception:
            pass
        self._thumblari_baslat()

    def _aktif_gosterim(self):
        """Etkin sonuç görünümü (ızgara ya da satır listesi)."""
        return (self.sonuc_izgara if getattr(self, "_gorunum", "satir") == "izgara"
                else self.sonuc_liste)

    def _secili_dosya(self):
        idx = self._aktif_gosterim().currentIndex()
        if not idx.isValid() or idx.row() >= len(self.sonuclar):
            return None
        return self.sonuclar[idx.row()]

    def _etiket_ekle(self):
        r = self._secili_dosya()
        tag = self.etiket_yaz.text().strip().lower()
        if r is None or not tag or self.con is None:
            return
        try:
            rank.set_tag(self.con, r["file_id"], tag)
        except ValueError as e:
            QMessageBox.warning(self, "Etiket", str(e))
            return
        self.etiket_yaz.clear()
        self._ara_simdi()

    def _etiket_sil(self):
        r = self._secili_dosya()
        tag = self.etiket_yaz.text().strip().lower()
        if r is None or not tag or self.con is None:
            return
        rank.remove_tag(self.con, r["file_id"], tag)
        self.etiket_yaz.clear()
        self._ara_simdi()

    # -- etiket kuralları --
    def _kural_tazele(self):
        self.kural_liste.clear()
        if self.con is None:
            return
        for r in rank.tag_rules(self.con):
            item = QListWidgetItem(f"#{r['tag']} ← {r['keywords']} [{r['mode']}]")
            item.setData(Qt.UserRole, r["rule_id"])
            self.kural_liste.addItem(item)

    def _kural_ekle(self):
        if self.con is None:
            return
        try:
            rank.add_rule(self.con, self.kural_etiket.text(),
                          self.kural_kelimeler.text(), self.kural_kip.currentText())
        except ValueError as e:
            QMessageBox.warning(self, "Kural", str(e))
            return
        self.kural_etiket.clear()
        self.kural_kelimeler.clear()
        self._kural_tazele()

    def _kural_sil(self):
        item = self.kural_liste.currentItem()
        if item is None or self.con is None:
            return
        rank.delete_rule(self.con, item.data(Qt.UserRole))
        self._kural_tazele()

    def _tuketim_sec(self):
        path = QFileDialog.getExistingDirectory(self, "Tüketim klasörünü seçin")
        if path:
            self.tuketim_klasoru.setText(path)

    def _tuketim_hedef_sec(self):
        path = QFileDialog.getExistingDirectory(self, "Tüketim hedefini seçin")
        if path:
            self.tuketim_hedefi.setText(path)

    def _tuketim_tara(self):
        if (self.con is None or self._locked or self._kaldir_thread is not None
                or self._haric_thread is not None):
            return
        try:
            kaydir = migrate.get_setting(self.con, "tuketim_klasoru", "").strip()
            hedef = migrate.get_setting(self.con, "tuketim_hedefi", "").strip()
        except Exception:
            return
        if not kaydir or not hedef or not os.path.isdir(kaydir) or not os.path.isdir(hedef):
            return
        from . import consume as consume_mod
        try:
            adlar = sorted(os.listdir(kaydir))[:25]
        except OSError:
            return
        for ad in adlar:
            yol = os.path.join(kaydir, ad)
            try:
                if os.path.isfile(yol) and consume_mod.tuket(self.con, yol, hedef) == "moved":
                    with self._izleme_kilit:
                        self._izleme_bekleyen.add(os.path.abspath(hedef))
            except Exception:
                continue  # DB kilitli vb: sonraki tur dener

    def _sec(self, idx):
        if self.con is None or not idx.isValid() or idx.row() >= len(self.sonuclar): return
        self._open_preview(self.sonuclar[idx.row()])

    # -- kayitli aramalar --
    def _kayitli_tazele(self):
        self.kayitli_liste.clear()
        if self.con is None:
            return
        try:
            for s in rank.saved_searches(self.con):
                self.kayitli_liste.addItem(s["name"], s)
        except Exception:
            pass

    def _mevcut_filtreler(self):
        yil = self.yil_filtre.text().strip() or None
        tur = self.tur_filtre.currentText()
        return yil, None if tur == "tümü" else tur, self.sirket_filtre.text().strip().lower() or None

    def _arama_kaydet(self):
        if self.con is None:
            return
        from PySide6.QtWidgets import QInputDialog
        ad, ok = QInputDialog.getText(self, "Aramayı kaydet", "Ad:")
        if not ok or not (ad or "").strip():
            return
        q = self.arama_kutu.text()
        if not q.strip():
            QMessageBox.information(self, "Arama", "Önce bir sorgu yazın.")
            return
        yil, tur, kokf = self._mevcut_filtreler()
        try:
            rank.save_search(self.con, ad.strip(), q, yil, tur, kokf)
        except ValueError as e:
            QMessageBox.warning(self, "Arama", str(e))
            return
        self._kayitli_tazele()

    def _kayitli_calistir(self, idx):
        s = self.kayitli_liste.itemData(idx)
        if not s:
            return
        self.arama_kutu.setText(s["query"])
        self.yil_filtre.setText(s["year"] or "")
        self.tur_filtre.setCurrentText(s["ext"] or "tümü")
        self.sirket_filtre.setText(s["folder"] or "")
        self._ara_simdi()

    def _kayitli_sil(self):
        s = self.kayitli_liste.currentData()
        if not s:
            return
        rank.delete_search(self.con, s["name"])
        self._kayitli_tazele()

    def _sonuc_csv(self):
        if not self.sonuclar:
            QMessageBox.information(self, "CSV", "İndirilecek sonuç yok.")
            return
        yol, _ = QFileDialog.getSaveFileName(self, "Sonuçları indir", "arama-sonuclari.csv",
                                             "CSV (*.csv)")
        if not yol:
            return
        try:
            from pathlib import Path
            Path(yol).write_bytes(rank.results_csv(self.con, self.sonuclar).encode("utf-8-sig"))
        except OSError as e:
            QMessageBox.warning(self, "CSV", f"Yazılamadı: {e}")
            return
        QMessageBox.information(self, "CSV", f"{len(self.sonuclar)} sonuç kaydedildi.")

    def _ekran_kaynaklar(self):
        w = QWidget()
        k = QVBoxLayout(w)
        k.setContentsMargins(22, 18, 22, 20)
        k.setSpacing(14)
        bas = QHBoxLayout()
        bas.setSpacing(9)
        bas.addWidget(bolum("Klasörler"))
        self.kaynak_sayi = sayac("")
        self.kaynak_sayi.hide()
        bas.addWidget(self.kaynak_sayi)
        bas.addStretch(1)
        ekle = QPushButton("Klasör ekle")
        ekle.setProperty("birincil", True)
        ekle.clicked.connect(self._kok_ekle)
        bas.addWidget(ekle)
        k.addLayout(bas)
        yuzey = QFrame()
        yuzey.setObjectName("card")
        yuzey_layout = QHBoxLayout(yuzey)
        yuzey_layout.setContentsMargins(0, 0, 0, 0)
        yuzey_layout.setSpacing(0)
        self.kok_model = QStandardItemModel()
        self.kok_liste = QListView()
        self.kok_liste.setObjectName("cardList")
        self.kok_liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.kok_liste.setMinimumWidth(160)
        self.kok_liste.setItemDelegate(CardDelegate(self.kok_liste, "folder", compact=True))
        self.kok_liste.setModel(self.kok_model)
        self.kok_liste.setSpacing(2)
        self.kok_panel = QStackedWidget()
        self.kok_panel.addWidget(self.kok_liste)
        self.kok_panel.addWidget(EmptyState("İlk klasörünüzü ekleyin", "Aranacak belgelerin bulunduğu klasörleri\n“Klasör ekle” ile seçin.", "folder"))
        self.source_split = QSplitter(Qt.Horizontal)
        self.source_split.installEventFilter(self)
        self.source_split.addWidget(self.kok_panel)
        ayrinti = QWidget()
        dl = QVBoxLayout(ayrinti)
        dl.setContentsMargins(16, 14, 16, 16)
        dl.setSpacing(10)
        kaydir = QScrollArea()
        kaydir.setWidgetResizable(True)
        kaydir.setFrameShape(QScrollArea.NoFrame)
        ic = QWidget()
        form = QVBoxLayout(ic)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        dl.addWidget(kaydir, 1)
        kaydir.setWidget(ic)
        form.addWidget(bolum("Seçili kaynak"))
        self.source_title = label("Bir kaynak seçin", "subheading")
        self.source_path = label("", "ikincil")
        self.source_path.setTextFormat(Qt.PlainText)
        self.source_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.source_status = label("", "pill")
        self.source_status.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        form.addWidget(self.source_title)
        form.addWidget(self.source_path)
        form.addWidget(self.source_status)
        form.addWidget(label("Kaynağı kaldırmak diskteki belgeleri silmez.", "ikincil"))
        form.addWidget(bolme())
        form.addWidget(bolum("Dışlananlar"))
        form.addWidget(label("Hariç kuralı eklemek için klasör yolunu yazıp Dışla'ya basın:", "ikincil"))
        hsatir = QHBoxLayout()
        hsatir.setSpacing(8)
        self.haric_kutu = QLineEdit()
        disla = QPushButton("Dışla")
        disla.setProperty("kucuk", True)
        disla.clicked.connect(self._haric_ekle)
        self.haric_uygula = disla
        hsatir.addWidget(self.haric_kutu, 1)
        hsatir.addWidget(disla)
        form.addLayout(hsatir)
        form.addStretch(1)
        kaldir = QPushButton("Kaldır")
        kaldir.setProperty("tehlike", True)
        kaldir.clicked.connect(self._kok_kaldir)
        self.source_remove = kaldir
        form.addWidget(kaldir)
        details = ayrinti
        details.setMinimumWidth(0)
        self.source_split.addWidget(details)
        self.source_split.setChildrenCollapsible(False)
        self.source_split.setStretchFactor(0, 1)
        self.source_split.setStretchFactor(1, 0)
        self.source_split.setSizes([520, 300])
        yuzey_layout.addWidget(self.source_split)
        k.addWidget(yuzey, 1)
        self.kok_liste.selectionModel().currentChanged.connect(self._source_selected)
        self.haric_bilgi = QLabel("")
        self.haric_bilgi.hide()
        k.addWidget(self.haric_bilgi)
        self.yigin.addWidget(w)
        self._kok_tazele()

    def _kok_tazele(self):
        selected = self.kok_liste.currentIndex().data(Qt.UserRole + 1)
        self.kok_model.clear()
        try:
            rows = self.con.execute(
                "SELECT display_path, company_rule, enabled FROM roots ORDER BY display_path"
            ).fetchall()
        except Exception:
            rows = []
        for yol, kural, akt in rows:
            item = QStandardItem(f"{os.path.basename(yol.rstrip('/\\')) or yol}\n{'Aramaya açık' if akt else 'Arama kapalı'}")
            item.setEditable(False)
            item.setData(yol)
            item.setToolTip(yol)
            item.setData(bool(akt), Qt.UserRole + 2)
            self.kok_model.appendRow(item)
        if hasattr(self, "tarama_root_count"):
            self.tarama_root_count.setText(f"{len(self._kokler())} kaynak klasörü")
        self.kok_panel.setCurrentIndex(0 if self.kok_model.rowCount() else 1)
        self.kaynak_sayi.setText(f"{len(rows)} klasör")
        self.kaynak_sayi.setVisible(bool(rows))
        row = next((i for i in range(self.kok_model.rowCount()) if self.kok_model.item(i).data() == selected), 0)
        self.kok_liste.setCurrentIndex(self.kok_model.index(row, 0))
        self._source_selected(self.kok_liste.currentIndex())
        if hasattr(self, "scope_mode") and self.scope_mode.currentIndex() == 1:
            self._scope_changed()

    def _source_selected(self, index, previous=None):
        path = index.data(Qt.UserRole + 1) or ""
        self.source_title.setText(os.path.basename(path.rstrip('/\\')) or path or "Bir kaynak seçin")
        self.source_path.setText(path)
        self.source_status.setText(("Aramaya açık" if index.data(Qt.UserRole + 2) else "Arama kapalı") if path else "")
        self.source_status.setVisible(bool(path))
        if hasattr(self, "source_remove"):
            self.source_remove.setEnabled(bool(path) and self._kaldir_thread is None and self._haric_thread is None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._source_layout)
        QTimer.singleShot(0,lambda:archive_ui.layout_cards(self))
        if self._geometry_ready and not self.isMaximized():
            self._geometry_timer.start(500)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._geometry_ready and not self.isMaximized():
            self._geometry_timer.start(500)

    def _source_layout(self):
        split = getattr(self, "source_split", None)
        if split is None:
            return
        try:
            orientation = Qt.Vertical if self.width() < 1200 else Qt.Horizontal
            if split.orientation() != orientation:
                split.setOrientation(orientation)
                split.setSizes([220, 440])
        except RuntimeError:
            # Pencere kapanırken zamanlanmış çağrı: nesne silinmiş olabilir.
            pass

    def _kok_ekle(self):
        yol = QFileDialog.getExistingDirectory(self, "Kaynak klasör seç")
        if not yol:
            return
        try:
            self.con.execute(
                "INSERT INTO roots(display_path, canonical_path) VALUES (?, ?)"
                " ON CONFLICT(canonical_path) DO NOTHING",
                (yol, os.path.normpath(yol).lower()))
            self.con.commit()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Kök", f"Eklenemedi: {e}")
        self._kok_tazele()
        self._durum_yaz()

    def _kok_kaldir(self):
        if not self._exclusive_ready():
            return
        idx = self.kok_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.kok_model.item(idx.row()).data()
        if QMessageBox.question(self, "Kaynağı kaldır",
                                "Bu klasörün yerel arama kayıtları kaldırılacak. Kaynak belgeler korunur. Devam edilsin mi?") != QMessageBox.Yes:
            return
        # GUI'yi kilitlemeden arka planda boşaltır; büyük arşivlerde dakikalar alabilir.
        self._debounce.stop()
        self._pending_search = None
        self._kaldir_yol = yol
        self._kaldir_isci = KokKaldirIsci(self.kasa_yolu, self._sifre, yol)
        self._kaldir_thread = QThread(self)
        self._kaldir_isci.moveToThread(self._kaldir_thread)
        self._kaldir_thread.started.connect(self._kaldir_isci.kos)
        self._kaldir_isci.bitti.connect(self._kok_kaldir_bitti)
        self._kaldir_isci.hata.connect(self._kok_kaldir_hata)
        self._kaldir_isci.bitti.connect(self._kaldir_thread.quit)
        self._kaldir_isci.hata.connect(self._kaldir_thread.quit)
        self._kaldir_isci.bitti.connect(self._kaldir_isci.deleteLater)
        self._kaldir_isci.hata.connect(self._kaldir_isci.deleteLater)
        self._kaldir_thread.finished.connect(self._kaldir_temizle)
        self.source_remove.setEnabled(False)
        self.source_remove.setText("Kaldırılıyor…")
        self.durum.showMessage("Kaynak kaldırılıyor… Kaynak belgeler korunur.")
        self.centralWidget().setEnabled(False)
        self._kaldir_thread.start()

    def _kok_kaldir_bitti(self, sil):
        if self._locked:
            return
        self.onizleme.temizle()
        self.sonuclar = []
        self.sonuc_model.clear()
        self._list_cache.clear()
        # Stop old watchers and restart only those for roots still registered.
        self._izleme_baslat()
        with self._izleme_kilit:
            self._izleme_bekleyen = {
                path for path in self._izleme_bekleyen
                if not exclusions.is_excluded(path, [self._kaldir_yol or ""])
            }
        self._kok_tazele()
        self._durum_yaz()
        if sil:
            self.durum.showMessage(f"{sil} dosyanın kaydı kaldırıldı. Kaynak belgeler korunur.", 8000)

    def _kok_kaldir_hata(self, msg):
        if self._locked:
            return
        self.durum.showMessage(f"Kaynak kaldırılamadı; kayıtlar korunuyor ({msg}).", 12000)
        self._kok_tazele()
        self._durum_yaz()

    def _kaldir_temizle(self):
        self._kaldir_isci = None
        self._kaldir_thread = None
        if self.centralWidget() is not None:
            self.centralWidget().setEnabled(True)
        if hasattr(self, "source_remove") and self.source_remove.text() == "Kaldırılıyor…":
            self.source_remove.setText("Kaldır")
            self.source_remove.setEnabled(self.kok_liste.currentIndex().isValid())
        if self._kaldir_lock_pending and not self._exiting:
            self._kaldir_lock_pending = False
            QTimer.singleShot(0, self.kilitle)

    def _haric_ekle(self):
        if not self._exclusive_ready():
            return
        kural = self.haric_kutu.text().strip()
        if not kural:
            return
        self._debounce.stop()
        self._pending_search = None
        self._haric_isci = HaricIsci(self.kasa_yolu, self._sifre, kural)
        self._haric_thread = QThread(self)
        self._haric_isci.moveToThread(self._haric_thread)
        self._haric_thread.started.connect(self._haric_isci.kos)
        self._haric_isci.bitti.connect(self._haric_bitti)
        self._haric_isci.hata.connect(self._haric_hata)
        self._haric_isci.bitti.connect(self._haric_thread.quit)
        self._haric_isci.hata.connect(self._haric_thread.quit)
        self._haric_isci.bitti.connect(self._haric_isci.deleteLater)
        self._haric_isci.hata.connect(self._haric_isci.deleteLater)
        self._haric_thread.finished.connect(self._haric_temizle)
        self.haric_uygula.setEnabled(False)
        self.haric_uygula.setText("Uygulanıyor…")
        self.durum.showMessage("Hariç kuralı uygulanıyor; arayüz kısa süreyle devre dışı.")
        self.centralWidget().setEnabled(False)
        self._haric_thread.start()

    def _haric_bitti(self, rule, count):
        if self._locked:
            return
        self.haric_kutu.clear()
        self.sonuclar = []
        self.sonuc_model.clear()
        self.onizleme.temizle()
        self._list_cache.clear()
        self.durum.showMessage(f"Hariç kuralı kaydedildi; {count} dosyanın içeriği temizlendi.", 8000)

    def _haric_hata(self, error_type):
        if self._locked:
            return
        self.durum.showMessage(f"Hariç kuralı uygulanamadı; değişiklikler geri alındı ({error_type}).", 12000)

    def _haric_temizle(self):
        self._haric_isci = None
        self._haric_thread = None
        if self.centralWidget() is not None:
            self.centralWidget().setEnabled(True)
        self.haric_uygula.setText("Dışla")
        self.haric_uygula.setEnabled(True)
        if self._kaldir_lock_pending and not self._exiting:
            self._kaldir_lock_pending = False
            QTimer.singleShot(0, self.kilitle)

    # -- tarama --
    def _ekran_tarama(self):
        w = QWidget()
        w.setObjectName("scanBody")
        w.setAttribute(Qt.WA_StyledBackground, True)
        k = QVBoxLayout(w)
        hour = migrate.get_setting(self.con, "saat", "12")
        minute = migrate.get_setting(self.con, "dakika", "30")
        try:
            scheduled_time = f"{int(hour):02d}:{int(minute):02d}"
        except (TypeError, ValueError):
            scheduled_time = "—"
        self.tarama_bilgi = QLabel("Henüz tarama yapılmadı.")
        self.tarama_bilgi.setWordWrap(True)
        self.tarama_root_count = label("", "ikincil")
        strip = stat_seridi([
            ("Kapsam", f"{len(self._kokler())}", "kaynak klasör • Kaynaklar bölümünden değişir"),
            ("Günlük düzen", scheduled_time, "Planlı tarama saati • Ayarlar’dan değişir"),
            ("Durum", "Hazır", "Henüz tarama yapılmadı"),
        ])
        self.tarama_time = QLabel(scheduled_time)
        self._stat_durum = strip
        k.addWidget(strip)

        islem = QHBoxLayout()
        islem.setSpacing(8)
        self.scan_start = QPushButton("Taramayı başlat")
        self.scan_start.setProperty("birincil", True)
        self.scan_start.clicked.connect(self._tara_baslat)
        islem.addWidget(self.scan_start)
        self.duraklat_btn = QPushButton("Duraklat")
        self.duraklat_btn.clicked.connect(self._tara_duraklat)
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.clicked.connect(self._tara_iptal)
        self.iptal_btn.setEnabled(False)
        islem.addWidget(self.duraklat_btn)
        islem.addWidget(self.iptal_btn)
        self.retry_scan = QPushButton("Sorunlu dosyaları yeniden dene")
        self.retry_scan.clicked.connect(self._retry_scan)
        self.retry_scan.hide()
        islem.addWidget(self.retry_scan)
        islem.addStretch(1)
        self.details_open = QPushButton("Tarama ayrıntılarını aç")
        self.details_open.setProperty("ghost", True)
        self.details_open.clicked.connect(self._scan_show)
        islem.addWidget(self.details_open)
        k.addLayout(islem)

        self.scan_dialog = QDialog(self)
        self.scan_dialog.setWindowTitle("Evrakçı • Tarama ayrıntıları")
        self.scan_dialog.resize(760, 560)
        popup = QVBoxLayout(self.scan_dialog)
        popup.setContentsMargins(18, 18, 18, 18)
        popup.setSpacing(12)
        popup.addWidget(label("Tarama ayrıntıları", "baslik"))
        self.popup_status = label("Henüz tarama yapılmadı.", "subheading")
        popup.addWidget(self.popup_status)
        self.popup_scope = label("", "ikincil")
        self.popup_scope.setTextFormat(Qt.PlainText)
        self.popup_scope.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.popup_scope.setMinimumWidth(0)
        popup.addWidget(self.popup_scope)
        self.tarama_bar = QProgressBar()
        self.tarama_bar.setStyleSheet('QProgressBar { min-height: 24px; max-height: 24px; text-align: center; }')
        self.tarama_bar.setTextVisible(True)
        self.tarama_bar.setFormat('Belge tamamlanma: %p%')
        self.tarama_bar.setRange(0, 0)
        self.tarama_bar.hide()
        popup.addWidget(self.tarama_bar)
        self.scan_phase_bar = QProgressBar()
        self.scan_phase_bar.setStyleSheet('QProgressBar { min-height: 20px; max-height: 20px; text-align: center; }')
        self.scan_phase_bar.setTextVisible(True)
        self.scan_phase_bar.hide()
        popup.addWidget(self.scan_phase_bar)
        self.scan_progress_detail = label('', 'ikincil')
        self.scan_progress_detail.setWordWrap(True)
        popup.addWidget(self.scan_progress_detail)
        detail_card, detail_layout = card()
        self.scan_current = label("Tarama ayrıntıları burada görünecek.", "subheading")
        self.scan_current.setTextFormat(Qt.PlainText)
        self.scan_current.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.scan_current.setMinimumWidth(0)
        self.scan_counts = label("", "ikincil")
        self.scan_clock = label("", "ikincil")
        detail_layout.addWidget(self.scan_current)
        self.scan_counts.hide()
        counts_grid = QGridLayout()
        counts_grid.setSpacing(0)
        self.scan_metrics = {}
        for i, (key, caption) in enumerate((("found", "Toplam / bulunan"), ('documents_done','Tamamlanan belge'), ('documents_remaining','Kalan belge'), ("done", "İçeriği okunan"), ("pending", "Bekleyen iş"),
                                           ("skipped", "Güncel / atlanan"), ("ocr_done", "OCR tamamlanan"), ("failed", "İşlem hatası"), ("ocr_failed", "OCR hatası"))):
            metric = QWidget()
            ml = QVBoxLayout(metric)
            ml.setContentsMargins(12, 10, 12, 10)
            ml.setSpacing(2)
            ml.addWidget(label(caption, "eyebrow"))
            value = QLabel("0")
            value.setProperty("subheading", True)
            ml.addWidget(value)
            self.scan_metrics[key] = value
            counts_grid.addWidget(metric, i // 3, i % 3)
        detail_layout.addLayout(counts_grid)
        detail_layout.addWidget(self.scan_clock)
        self.scan_details_toggle = QPushButton("Ayrıntıları göster")
        self.scan_details_toggle.setCheckable(True)
        self.scan_log = QPlainTextEdit()
        self.scan_log.setObjectName("log")
        self.scan_log.setReadOnly(True)
        self.scan_log.document().setMaximumBlockCount(200)
        self.scan_log.setMaximumHeight(160)
        self.scan_log.hide()
        self.scan_details_toggle.toggled.connect(self.scan_log.setVisible)
        self.scan_details_toggle.toggled.connect(lambda on: self.scan_details_toggle.setText("Ayrıntıları gizle" if on else "Ayrıntıları göster"))
        detail_layout.addWidget(self.scan_details_toggle)
        detail_layout.addWidget(self.scan_log)
        popup.addWidget(detail_card, 1)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._scan_clock_update)
        self.scan_started = None
        self._scan_stage = ""
        self._last_scan_log = ""
        satir = QHBoxLayout()
        satir.addStretch(1)
        background = QPushButton("Arka planda sürdür")
        background.clicked.connect(self.scan_dialog.hide)
        satir.addWidget(background)
        popup.addLayout(satir)

        self.scope_mode = QComboBox()
        self.scope_mode.addItems(["Tüm kaynaklar", "Seçili kaynaklar", "Bir klasör veya disk"])
        self.scope_sources = QListWidget()
        self.scope_sources.setMaximumHeight(140)
        self.scope_sources.hide()
        self.scope_path = QLineEdit()
        self.scope_path.setPlaceholderText("Bu tarama için klasör veya disk yolu")
        self.scope_path.hide()
        self.scope_browse = QPushButton("Taranacak klasörü seç…")
        self.scope_browse.clicked.connect(self._scope_browse)
        self.scope_browse.hide()
        k.addWidget(ayar_satiri("Kapsam", "Bu taramada hangi klasörlerin taranacağı.", self.scope_mode))
        k.addWidget(self.scope_sources)
        k.addWidget(self.scope_path)
        k.addWidget(self.scope_browse)
        self.scope_mode.currentIndexChanged.connect(self._scope_changed)

        k.addWidget(bolum("Son taramalar"))
        self.scan_history = QListWidget()
        self.scan_history.setObjectName("cardList")
        self.scan_history.setAccessibleName("Son tarama kayıtları")
        k.addWidget(self.scan_history, 1)
        self._scan_history_refresh()
        k.addWidget(self.tarama_bilgi)
        self.yigin.addWidget(w)
        self.isci = None
        self.isci_thread = None
        self._izleyiciler = []
        self._izleme_bekleyen = set()
        self._izleme_kilit = threading.Lock()
        self._izleme_saat = QTimer(self)
        self._izleme_saat.timeout.connect(self._izleme_bosalt)
        self._izleme_saat.start(5000)

    def _kokler(self):
        try:
            return [r[0] for r in self.con.execute(
                "SELECT display_path FROM roots WHERE enabled=1 ORDER BY display_path").fetchall()]
        except Exception:
            return []

    def _scope_changed(self):
        mode = self.scope_mode.currentIndex()
        self.scope_sources.setVisible(mode == 1)
        self.scope_path.setVisible(mode == 2)
        self.scope_browse.setVisible(mode == 2)
        if mode == 1:
            checked = {self.scope_sources.item(i).text() for i in range(self.scope_sources.count())
                       if self.scope_sources.item(i).checkState() == Qt.Checked}
            self.scope_sources.clear()
            for path in self._kokler():
                item = QListWidgetItem(path)
                item.setCheckState(Qt.Checked if path in checked else Qt.Unchecked)
                self.scope_sources.addItem(item)

    def _retry_scan(self):
        if not self._exclusive_ready():
            return
        rows = self.con.execute("SELECT j.job_id,f.path FROM jobs j JOIN files f ON f.file_id=j.file_id"
                                " WHERE j.status IN ('pending','dead')").fetchall()
        for job_id, path in rows:
            if any(self._under(path, root) for root in self._scan_roots):
                self.con.execute("UPDATE jobs SET status='pending',not_before=0,attempts=0 WHERE job_id=?", (job_id,))
        self.con.commit()
        self._tara_baslat(roots=self._scan_roots)

    def _scope_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Taranacak klasörü seçin")
        if path:
            self.scope_path.setText(path)

    def _tara_baslat(self, checked=False, *, automatic=False, roots=None):
        if self._locked or self.con is None or self._kaldir_thread is not None or self._haric_thread is not None:
            return
        if self.isci_thread is not None:
            if not automatic:
                self._scan_show()
            return
        kokler = roots if roots is not None else self._kokler()
        if not automatic and roots is None:
            mode = self.scope_mode.currentIndex()
            if mode == 1:
                kokler = [self.scope_sources.item(i).text() for i in range(self.scope_sources.count())
                          if self.scope_sources.item(i).checkState() == Qt.Checked]
            elif mode == 2:
                path = self.scope_path.text().strip().strip('"')
                kokler = [os.path.abspath(path)] if path else []
                if not kokler or not os.path.isdir(kokler[0]):
                    QMessageBox.information(self, "Tarama", "Ulaşılabilen bir klasör veya disk seçin.")
                    return
        if not kokler:
            QMessageBox.information(self, "Tarama", "Taranacak en az bir klasör seçin.")
            return
        # Aynı kapsamın iç içe kökleri bir kez taranır.
        unique = []
        for path in sorted(set(map(os.path.abspath, kokler)), key=len):
            if not any(self._under(path, parent) for parent in unique):
                unique.append(path)
        kokler = unique
        self._scan_roots = kokler
        self.retry_scan.hide()
        migrate.set_setting(self.con, "tarama_ele_alinan_gun", dt.date.today().isoformat())
        self.isci_thread = QThread(self)
        self.isci = TaramaIsci(self.kasa_yolu, self._sifre, kokler)
        self.isci.moveToThread(self.isci_thread)
        self.isci_thread.started.connect(self.isci.kos)
        self.isci.ilerleme.connect(self._scan_progress)
        self.isci.duraklama.connect(self._scan_paused)
        self.isci.bitti.connect(self._tara_bitti)
        self.isci.hata.connect(self._tara_hata)
        self.isci.bitti.connect(self.isci_thread.quit)
        self.isci.hata.connect(self.isci_thread.quit)
        self.isci.bitti.connect(self.isci.deleteLater)
        self.isci.hata.connect(self.isci.deleteLater)
        self.isci_thread.finished.connect(self._tara_temizle)
        self.scan_started = dt.datetime.now()
        self._scan_elapsed = time.monotonic()
        self._scan_stage = "Hazırlanıyor"
        self.scan_log.clear()
        self.scan_counts.clear()
        self._scan_metrics_update({})
        self._last_scan_log = ""
        self.scan_current.setText("Kapsam: " + " • ".join(kokler))
        self.scan_log.appendPlainText("Kapsam: " + " | ".join(kokler))
        self.scan_timer.start(1000)
        self._scan_clock_update()
        self.isci_thread.start()
        diagnostics.record("scan_started", "automatic" if automatic else "manual")
        self.tarama_bar.show()
        self.tarama_bar.setRange(0,0)
        self.scan_progress_detail.setText('Dosya listesi oluşturuluyor…')
        self.scan_phase_bar.hide()
        self.duraklat_btn.setText("Duraklat")
        self.duraklat_btn.setEnabled(True)
        self.iptal_btn.setEnabled(True)
        self.tara_btn.setEnabled(True)
        self._scan_state("running")
        self.scan_start.setEnabled(False)
        self.scope_mode.setEnabled(False)
        self.scope_sources.setEnabled(False)
        self.scope_path.setEnabled(False)
        self.scope_browse.setEnabled(False)
        self.tarama_bilgi.setText(f"Tarama başladı • {len(kokler)} klasör")
        self.popup_scope.setText(f"{len(kokler)} kaynak • " + " | ".join(kokler))
        if not automatic:
            self._scan_show()

    @staticmethod
    def _under(path, root):
        try:
            return os.path.normcase(os.path.commonpath([path, root])) == os.path.normcase(root)
        except ValueError:
            return False

    def _scan_clock_update(self):
        data = {}
        if self.isci is not None:
            data = self.isci.snapshot()
            if data:
                self._scan_progress(data)
        if self.scan_started:
            seconds = int(time.monotonic() - self._scan_elapsed)
            text = f"Başlangıç {self.scan_started:%H:%M:%S} • Geçen süre {seconds // 60:02d}:{seconds % 60:02d}"
            done,total = data.get('phase_done',0),data.get('phase_total',0)
            elapsed = data.get('phase_elapsed',0)
            if data.get('inventory_ready') and total:
                text += f'\nBu aşama: {done}/{total} iş'
                if done and elapsed > 2 and done < total:
                    remaining = int(elapsed/done*(total-done))
                    text += f' • bu aşamada kalan ~{remaining//60} dk {remaining%60:02d} sn'
                elif done < total:
                    text += ' • kalan süre hesaplanıyor…'
            elif data.get('phase_key') in ('finalize','dictionary'):
                text += '\nSon kontroller sürüyor.'
            self.scan_clock.setText(text)

    def _scan_progress(self, data):
        if self._locked:
            return
        data = dict(data)
        ready = data.get('inventory_ready',False)
        total,done = data.get('documents_total',0),data.get('documents_done',0)
        data['documents_remaining'] = max(0,total-done) if ready else 0
        self._scan_metrics_update(data)
        if ready:
            self.tarama_bar.setRange(0,100)
            percentage = min(100,int(done*100/total)) if total else 0
            self.tarama_bar.setValue(percentage)
            text = f'Tamamlanan {done:,} / {total:,} belge • Kalan {max(0,total-done):,}'
            if not data.get('inventory_complete',True):
                text = 'Envanter eksik • bilinen belgeler: ' + text
                self.tarama_bar.setFormat('Bilinen belgeler: %p%')
            else:
                self.tarama_bar.setFormat('Belge tamamlanma: %p%')
            self.scan_progress_detail.setText(text)
            if getattr(self,'_scan_status','') == 'running':
                self.tarama_bilgi.setText(f'%{percentage} • {text}')
        else:
            self.tarama_bar.setRange(0,0)
            self.scan_progress_detail.setText(f"Dosya listesi oluşturuluyor • {data.get('found',0):,} belge bulundu. Toplam henüz kesinleşmedi.")
        phase_done,phase_total = data.get('phase_done',0),data.get('phase_total',0)
        self.scan_phase_bar.setVisible(bool(ready and phase_total))
        if ready and phase_total:
            caption = {'content':'İçerik okuma','ocr':'OCR','embedding':'Vektör dizini','dictionary':'Arama sözlüğü'}.get(data.get('phase_key'),'Bu aşama')
            self.scan_phase_bar.setRange(0,100)
            self.scan_phase_bar.setFormat(caption + ': %p%')
            self.scan_phase_bar.setValue(min(100,int(phase_done*100/phase_total)))
        self._scan_stage = data.get("stage", "")
        path = data.get("path", "")
        self.scan_current.setText(self._scan_stage + "\n" + path)
        self.popup_status.setText(self._scan_stage)
        self.scan_counts.setText(f"Bulunan {data.get('found', 0):,} • İşlenen {data.get('done', 0):,} • "
                                 f"Bekleyen {data.get('pending', 0):,} • OCR {data.get('ocr_done', 0):,} • "
                                 f"Güncel/atlanan {data.get('skipped', 0):,} • İşlem hatası {data.get('failed', 0):,} • OCR hatası {data.get('ocr_failed', 0):,}")
        outcome = {"done": "İşlendi", "changed": "Dosya değişti", "unstable": "Dosya henüz kararlı değil",
                   "retry": "İşlenemedi, yeniden deneme bekliyor", "dead": "İşlenemedi", "deferred": "Ertelendi"}.get(data.get("item_result"), "")
        line = f"{self._scan_stage}: {path}" + (" • " + outcome if outcome else "")
        if line != self._last_scan_log:
            self.scan_log.appendPlainText(line)
            self._last_scan_log = line

    def _tara_duraklat(self):
        if self.isci:
            paused = self.isci.paused.is_set()
            self.isci.paused.clear() if paused else self.isci.paused.set()
            self.duraklat_btn.setText("Duraklat" if paused else "Devam et")
            self._scan_state("running" if paused else "pausing")
            self.tarama_bilgi.setText("Tarama devam ediyor." if paused else "Duraklatılıyor; güvenli noktada bekleyecek.")

    def _tara_iptal(self):
        if self.isci:
            migrate.set_setting(self.con, "tarama_ele_alinan_gun", dt.date.today().isoformat())
            self.isci.durdur()
            self._scan_state("cancelling")
            self.tarama_bilgi.setText("Tarama iptal ediliyor. Bugün otomatik olarak tekrar başlamayacak.")
            self.duraklat_btn.setEnabled(False)
            self.iptal_btn.setEnabled(False)

    def _tara_bitti(self, st):
        if self.con is None or self._locked:
            return
        self.scan_timer.stop()
        self._scan_clock_update()
        result = {"cancelled": "Tarama iptal edildi", "complete": "Tarama tamamlandı",
                  "partial": "Tarama kısmen tamamlandı"}.get(st.get("result"), "Tarama durdu")
        self._scan_progress(dict(st,stage=result))
        self._scan_metrics_update(st)
        self.tarama_bilgi.setText(result)
        self.popup_status.setText(result)
        self._scan_state("idle")
        self.scan_counts.setText(f"Bulunan {st.get('found',0):,} • İşlenen {st.get('done',0):,} • "
                                 f"Bekleyen {st.get('pending',0):,} • OCR {st.get('ocr_done',0):,} • "
                                 f"Güncel/atlanan {st.get('skipped',0):,} • İşlem hatası {st.get('failed',0):,} • OCR hatası {st.get('ocr_failed',0):,}")
        self.retry_scan.setVisible(bool(st.get('pending') or st.get('failed') or st.get('ocr_failed')))
        self.scan_log.appendPlainText(result)
        if not st.get('done'):
            self.scan_log.appendPlainText("Yeni içerik işlenmedi. Dosyalar güncel olabilir veya bekleyen/erişilemeyen işler bulunabilir; yukarıdaki aşama ve hata kayıtlarını kontrol edin.")
        migrate.set_setting(self.con, "son_tarama", dt.datetime.now().isoformat(timespec="seconds"))
        if st.get("complete"):
            migrate.set_setting(self.con, "son_slot", dt.datetime.now().isoformat(timespec="seconds"))
        self._durum_yaz()
        self._scan_history_refresh()
        self._izleme_bosalt()

    def _tara_hata(self, msg):
        if self._locked:
            return
        self.scan_timer.stop()
        self.tarama_bar.hide()
        self.scan_phase_bar.hide()
        self.tarama_bilgi.setText("Tarama tamamlanamadı. Bugün otomatik tekrar denenmeyecek.")
        self.scan_log.appendPlainText(msg)
        self.popup_status.setText("Tarama tamamlanamadı.")
        self._scan_state("idle")
        if self.con is not None:
            self.con.execute(
                "UPDATE scan_runs SET result='error', finished_at=?, error_code='WORKER_ERROR' "
                "WHERE finished_at IS NULL", (int(time.time()),)
            )
            self.con.commit()
            self._scan_history_refresh()
        QMessageBox.warning(self, "Tarama", msg)

    def _scan_history_refresh(self):
        if not hasattr(self, "scan_history") or self.con is None:
            return
        self.scan_history.clear()
        rows = self.con.execute(
            "SELECT started_at, root, result, found, done, pending, failed, ocr_done, ocr_failed "
            "FROM scan_runs ORDER BY run_id DESC LIMIT 12"
        ).fetchall()
        names = {"complete": "Tamamlandı", "partial": "Kısmi", "cancelled": "İptal edildi",
                 "interrupted": "Kesintiye uğradı", "error": "Hata"}
        for stamp, root, result, found, done, pending, failed, ocr_done, ocr_failed in rows:
            when = dt.datetime.fromtimestamp(stamp).strftime("%d.%m.%Y %H:%M")
            item = QListWidgetItem(
                f"{when}\n{os.path.basename(root) or root}  •  {names.get(result, 'Sürüyor')}"
                f"  •  {done} işlendi / {found} bulundu  •  {pending} bekliyor"
                f"  •  {failed + ocr_failed} hata"
            )
            item.setData(Qt.UserRole, result)
            self.scan_history.addItem(item)

    def _tara_temizle(self):
        thread = self.isci_thread
        self.isci = None
        self.isci_thread = None
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn.setEnabled(False)
        self.tara_btn.setEnabled(True)
        self._scan_state("idle")
        self.scan_start.setEnabled(True)
        self.scope_mode.setEnabled(True)
        self.scope_sources.setEnabled(True)
        self.scope_path.setEnabled(True)
        self.scope_browse.setEnabled(True)
        self.scan_timer.stop()
        if thread is not None:
            thread.deleteLater()

    # -- canli izleme --
    def _izleme_baslat(self):
        from . import watch as watch_mod
        self._izleme_durdur()
        if self.con is None or self._locked:
            return
        try:
            if migrate.get_setting(self.con, "canli_izleme", "1") != "1":
                return
        except Exception:
            return
        for kok in self._kokler():
            try:
                iz = watch_mod.Izleyici(kok, self._izleme_olay)
                iz.start()
                self._izleyiciler.append(iz)
            except Exception:
                diagnostics.record("watch_start_failed")

    def _izleme_olay(self, dirs):
        # Izleyici thread'inden gelir: GUI'ye dokunulmaz, yalnız set güncellenir.
        with self._izleme_kilit:
            self._izleme_bekleyen.update(d for d in dirs if os.path.isdir(d))
        diagnostics.record("watch_event")

    def _izleme_durdur(self):
        izleyiciler, self._izleyiciler = self._izleyiciler, []
        for iz in izleyiciler:
            try:
                iz.durdur()
            except Exception:
                pass
        for iz in izleyiciler:
            try:
                iz.join(timeout=3)
            except Exception:
                pass

    def _izleme_bosalt(self):
        if (self._locked or self.con is None or self.isci_thread is not None
                or self._kaldir_thread is not None or self._haric_thread is not None):
            return
        self._tuketim_tara()
        with self._izleme_kilit:
            bekleyen = sorted(d for d in self._izleme_bekleyen if os.path.isdir(d))
            self._izleme_bekleyen.clear()
        if bekleyen:
            self.scan_log.appendPlainText(
                f"İzleme: {len(bekleyen)} klasörde değişiklik → tarama başlıyor.")
            self._tara_baslat(roots=bekleyen, automatic=True)

    # -- geçmiş: liste + seçili arama ayrıntısı --
    def _ekran_gecmis(self):
        w = QWidget()
        k = QVBoxLayout(w)
        k.setContentsMargins(22, 18, 22, 20)
        k.setSpacing(14)
        bas = QHBoxLayout()
        bas.setSpacing(9)
        bas.addWidget(bolum("Aramalar"))
        self.gecmis_sayi = sayac("")
        bas.addWidget(self.gecmis_sayi)
        bas.addStretch(1)
        self.gecmis_temizle_ust = QPushButton("Temizle")
        self.gecmis_temizle_ust.setToolTip("Tümünü temizle")
        self.gecmis_temizle_ust.setProperty("kucuk", True)
        self.gecmis_temizle_ust.clicked.connect(self._gecmis_temizle)
        bas.addWidget(self.gecmis_temizle_ust)
        k.addLayout(bas)

        yuzey = QFrame()
        yuzey.setObjectName("card")
        yuzey_layout = QHBoxLayout(yuzey)
        yuzey_layout.setContentsMargins(0, 0, 0, 0)
        yuzey_layout.setSpacing(0)
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        self.gecmis_model = QStandardItemModel()
        self.gecmis_liste = QListView()
        self.gecmis_liste.setObjectName("cardList")
        self.gecmis_liste.setItemDelegate(CardDelegate(self.gecmis_liste, "history"))
        self.gecmis_liste.setModel(self.gecmis_model)
        self.gecmis_liste.setSpacing(2)
        self.gecmis_liste.clicked.connect(self._gecmis_ayrinti)
        self.gecmis_liste.doubleClicked.connect(self._gecmis_kullan)
        self.gecmis_panel = QStackedWidget()
        self.gecmis_panel.addWidget(self.gecmis_liste)
        self.gecmis_panel.addWidget(EmptyState("Aramalarınız burada kalır", "Önceki aramalarınıza yeniden ulaşabilir\nve aynı filtrelerle devam edebilirsiniz.", "history"))
        split.addWidget(self.gecmis_panel)
        ayrinti = QWidget()
        al = QVBoxLayout(ayrinti)
        al.setContentsMargins(16, 14, 16, 16)
        al.setSpacing(10)
        al.addWidget(bolum("Seçili arama"))
        self.gecmis_sorgu = label("Bir arama seçin", "subheading")
        self.gecmis_sorgu.setWordWrap(True)
        al.addWidget(self.gecmis_sorgu)
        self.gecmis_filtre = label("", "pill")
        self.gecmis_filtre.setWordWrap(True)
        al.addWidget(self.gecmis_filtre)
        al.addWidget(bolme())
        al.addStretch(1)
        self.gecmis_calistir = QPushButton("Bu aramayı çalıştır")
        self.gecmis_calistir.setProperty("birincil", True)
        self.gecmis_calistir.clicked.connect(self._gecmis_calistir)
        al.addWidget(self.gecmis_calistir)
        self.gecmis_sil_btn = QPushButton("Seçiliyi sil")
        self.gecmis_sil_btn.clicked.connect(self._gecmis_sil)
        al.addWidget(self.gecmis_sil_btn)
        self.gecmis_temizle_btn = QPushButton("Tümünü temizle")
        self.gecmis_temizle_btn.setProperty("tehlike", True)
        self.gecmis_temizle_btn.clicked.connect(self._gecmis_temizle)
        al.addWidget(self.gecmis_temizle_btn)
        split.addWidget(ayrinti)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([560, 300])
        self.gecmis_split = split
        yuzey_layout.addWidget(split)
        k.addWidget(yuzey, 1)
        self.yigin.addWidget(w)
        self._gecmis_ayrinti()

    def _gecmis_veri(self, item):
        import json
        query, filters = item.data(Qt.UserRole + 1)
        try:
            values = json.loads(filters)
        except (ValueError, TypeError):
            values = dict(x.split("=", 1) for x in filters.split(";") if "=" in x)
        return query, values

    def _gecmis_ayrinti(self, _idx=None):
        idx = self.gecmis_liste.currentIndex()
        item = self.gecmis_model.item(idx.row()) if idx.isValid() and idx.row() < self.gecmis_model.rowCount() else None
        if item is None:
            self.gecmis_sorgu.setText("Bir arama seçin")
            self.gecmis_filtre.clear()
            self.gecmis_filtre.hide()
            self.gecmis_calistir.setEnabled(False)
            self.gecmis_sil_btn.setEnabled(False)
            return
        query, values = self._gecmis_veri(item)
        self.gecmis_sorgu.setText(query)
        parca = []
        if values.get("yil"):
            parca.append(f"yıl:{values['yil']}")
        if values.get("tur") and values["tur"] != "tümü":
            parca.append(f"tür:{values['tur']}")
        if values.get("klasor"):
            parca.append(f"klasör:{values['klasor']}")
        if values.get("etiket"):
            parca.append(f"etiket:{values['etiket']}")
        self.gecmis_filtre.setText("  •  ".join(parca) or "Filtresiz arama")
        self.gecmis_filtre.show()
        self.gecmis_calistir.setEnabled(True)
        self.gecmis_sil_btn.setEnabled(True)

    def _gecmis_calistir(self):
        idx = self.gecmis_liste.currentIndex()
        if idx.isValid():
            self._gecmis_kullan(idx)

    def _gecmis_tazele(self):
        archive_ui.refresh_history(self)

    def _gecmis_kullan(self, idx):
        query, values = self._gecmis_veri(self.gecmis_model.item(idx.row()))
        controls = (self.arama_kutu, self.yil_filtre, self.tur_filtre, self.sirket_filtre,
                    self.etiket_filtre)
        for control in controls:
            control.blockSignals(True)
        self.arama_kutu.setText(query)
        self.yil_filtre.setText(values.get("yil", ""))
        self.tur_filtre.setCurrentText(values.get("tur") or "tümü")
        self.sirket_filtre.setText(values.get("klasor", ""))
        self.etiket_filtre.setText(values.get("etiket", ""))
        for control in controls:
            control.blockSignals(False)
        self.nav.setCurrentRow(0)
        self._ara_simdi()

    def _gecmis_sil(self):
        idx = self.gecmis_liste.currentIndex()
        if idx.isValid():
            hist_mod.delete(self.con, self.gecmis_model.item(idx.row()).data())
            self._gecmis_tazele()

    def _gecmis_temizle(self):
        if QMessageBox.question(self, "Geçmiş", "Tüm arama geçmişi silinsin mi?") \
                == QMessageBox.Yes:
            hist_mod.clear(self.con)
            self._gecmis_tazele()

    # -- kurtarma anahtarı: Ayarlar icinde bolum --
    def _kurtarma_bolumu(self, k):
        """Kurtarma anahtarı durumu, oluşturma, yenileme, kaldırma ve belge."""
        k.addWidget(bolum("Kurtarma anahtarı"))
        self.kurtarma_durum = label("", "ikincil")
        self.kurtarma_durum.setWordWrap(True)
        self.kurtarma_olustur = QPushButton("Anahtar oluştur")
        self.kurtarma_olustur.setProperty("kucuk", True)
        self.kurtarma_olustur.clicked.connect(self._kurtarma_olustur_tiklandi)
        self.kurtarma_goster = QPushButton("Anahtarı göster")
        self.kurtarma_goster.setProperty("kucuk", True)
        self.kurtarma_goster.clicked.connect(self._kurtarma_goster)
        self.kurtarma_yazdir = QPushButton("Yazdır / kaydet")
        self.kurtarma_yazdir.setProperty("kucuk", True)
        self.kurtarma_yazdir.clicked.connect(self._kurtarma_yazdir)
        self.kurtarma_kaldir = QPushButton("Kaldır")
        self.kurtarma_kaldir.setProperty("kucuk", True)
        self.kurtarma_kaldir.setProperty("tehlike", True)
        self.kurtarma_kaldir.clicked.connect(self._kurtarma_kaldir)
        self.kurtarma_denetim = QWidget()
        kd = QHBoxLayout(self.kurtarma_denetim)
        kd.setContentsMargins(0, 0, 0, 0)
        kd.setSpacing(8)
        for b in (self.kurtarma_olustur, self.kurtarma_goster, self.kurtarma_yazdir,
                  self.kurtarma_kaldir):
            kd.addWidget(b)
        k.addWidget(ayar_satiri(
            "Şifre unutulursa kurtarma",
            "Anahtar kasa klasöründe saklanır; belgeyle birlikte güvenli bir yerde tutun.",
            self.kurtarma_denetim))

    def _kurtarma_tazele(self):
        if not hasattr(self, "kurtarma_durum"):
            return
        if self.sifresiz:
            self.kurtarma_durum.setText(
                "Şifre kullanmıyorsunuz; kurtarma anahtarı gerekmez. Şifre eklediğinizde "
                "anahtar kendiliğinden oluşturulur.")
            for b in (self.kurtarma_olustur, self.kurtarma_goster,
                      self.kurtarma_yazdir, self.kurtarma_kaldir):
                b.setEnabled(False)
            return
        self.kurtarma_olustur.setEnabled(True)
        durum = recovery.status(self.kasa_yolu)
        if not durum.get("var"):
            self.kurtarma_durum.setText("Henüz kurtarma anahtarı yok.")
            self.kurtarma_goster.setEnabled(False)
            self.kurtarma_yazdir.setEnabled(False)
            self.kurtarma_kaldir.setEnabled(False)
            self.kurtarma_olustur.setText("Anahtar oluştur")
            return
        parcalar = []
        anahtar = recovery.load_key(self.kasa_yolu)
        parcalar.append("Kurtarma anahtarı hazır." if anahtar else
                        "Anahtar dosyası bulunamadı; yeniden oluşturun.")
        if durum.get("kasa_eslesmiyor"):
            parcalar.append("Kasa değişmiş görünüyor; anahtarı yenilemeniz önerilir.")
        self.kurtarma_durum.setText(" ".join(parcalar))
        self.kurtarma_goster.setEnabled(bool(anahtar))
        self.kurtarma_yazdir.setEnabled(bool(anahtar))
        self.kurtarma_kaldir.setEnabled(True)
        self.kurtarma_olustur.setText("Anahtarı yenile")

    def _kurtarma_olustur_tiklandi(self):
        if self.con is None or self._locked:
            return
        var = recovery.status(self.kasa_yolu).get("var")
        if var:
            cevap = QMessageBox.question(
                self, "Kurtarma anahtarı",
                "Yeni bir kurtarma anahtarı üretilecek ve eskisi geçersiz olacak.\n"
                "Devam edilsin mi?")
            if cevap != QMessageBox.Yes:
                return
        try:
            anahtar = recovery.refresh(self.kasa_yolu, self._sifre)
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Kurtarma", f"Anahtar oluşturulamadı: {error}")
            return
        self._kurtarma_tazele()
        self._kurtarma_goster(anahtar)

    def _kurtarma_goster(self, anahtar=None):
        if self.con is None or self._locked:
            return
        if not anahtar:
            anahtar = recovery.load_key(self.kasa_yolu)
        if not anahtar:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Evrakçı • Kurtarma anahtarı")
        dialog.setMinimumWidth(560)
        yerlesim = QVBoxLayout(dialog)
        yerlesim.setContentsMargins(20, 20, 20, 20)
        yerlesim.setSpacing(12)
        yerlesim.addWidget(label("Kurtarma anahtarınız", "baslik"))
        uyari = label("Bu anahtarı şimdi kaydedin. Anahtar şifrenizi açabilir; "
                      "şifrenizi unuttuğunuzda indeksinizi kurtarır.", "uyari")
        yerlesim.addWidget(uyari)
        gosterim = QLineEdit(anahtar)
        gosterim.setReadOnly(True)
        gosterim.setAlignment(Qt.AlignCenter)
        gosterim.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; letter-spacing: 1px;")
        gosterim.setCursorPosition(0)
        yerlesim.addWidget(gosterim)
        satir = QHBoxLayout()
        satir.setSpacing(8)
        kopyala = QPushButton("Kopyala")
        kopyala.clicked.connect(lambda: QApplication.clipboard().setText(anahtar))
        satir.addWidget(kopyala)
        yazdir = QPushButton("Yazdır / kaydet")
        yazdir.clicked.connect(lambda: self._kurtarma_yazdir(anahtar))
        satir.addWidget(yazdir)
        satir.addStretch(1)
        kapat = QPushButton("Kapat")
        kapat.setProperty("birincil", True)
        kapat.clicked.connect(dialog.accept)
        satir.addWidget(kapat)
        yerlesim.addLayout(satir)
        dosya = recovery.key_path(self.kasa_yolu)
        yol_notu = QLabel(f"Anahtar ayrıca şu dosyada durur:\n{dosya}")
        yol_notu.setProperty("ikincil", True)
        yol_notu.setWordWrap(True)
        yol_notu.setTextInteractionFlags(Qt.TextSelectableByMouse)
        yerlesim.addWidget(yol_notu)
        dialog.exec()

    def _kurtarma_yazdir(self, anahtar=None):
        if self.con is None or self._locked:
            return
        if not anahtar:
            anahtar = recovery.load_key(self.kasa_yolu)
        if not anahtar:
            return
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        belge = QTextDocument()
        belge.setPlainText(recovery.document_text(self.kasa_yolu, anahtar, bicimli=True))
        yazici = QPrinter(QPrinter.HighResolution)
        secim = QPrintDialog(yazici, self)
        secim.setWindowTitle("Kurtarma belgesini yazdır")
        var = None
        if secim.exec() == QDialog.Accepted:
            belge.print_(yazici)
        else:
            # Yazdırma iptal edildiyse dosyaya kaydetmeyi öner.
            var = QFileDialog.getSaveFileName(
                self, "Kurtarma belgesini kaydet",
                os.path.join(os.path.dirname(self.kasa_yolu), "evrakci-kurtarma-belgesi.txt"),
                "Metin (*.txt)")[0]
            if var:
                try:
                    from pathlib import Path
                    Path(var).write_text(
                        recovery.document_text(self.kasa_yolu, anahtar, bicimli=True),
                        encoding="utf-8")
                    self._toast_goster("Kurtarma belgesi kaydedildi.")
                except OSError as error:
                    QMessageBox.warning(self, "Kurtarma", f"Kaydedilemedi: {error}")

    def _kurtarma_kaldir(self):
        if self.con is None or self._locked:
            return
        cevap = QMessageBox.question(
            self, "Kurtarma anahtarını kaldır",
            "Kurtarma anahtarı silinecek. Şifrenizi unutursanız indeksinizi kurtaramazsınız.\n"
            "Devam edilsin mi?")
        if cevap != QMessageBox.Yes:
            return
        recovery.remove(self.kasa_yolu)
        self._kurtarma_tazele()
        self._toast_goster("Kurtarma anahtarı kaldırıldı.")

    # -- yedekler: Ayarlar icinde bolum; ayri sekme degil --
    def _yedek_bolumu(self, k):
        """Yedek listesi ve işlemleri; Ayarlar sayfasının sonuna eklenir."""
        bas = QHBoxLayout()
        bas.setSpacing(9)
        bas.addWidget(bolum("Yedekler"))
        bas.addStretch(1)
        yeni = QPushButton("Yedek oluştur")
        yeni.setProperty("birincil", True)
        yeni.clicked.connect(self._yedek_al)
        bas.addWidget(yeni)
        geri = QPushButton("Geri yükle")
        geri.clicked.connect(self._geri_yukle)
        bas.addWidget(geri)
        k.addLayout(bas)
        yuzey = QFrame()
        yuzey.setObjectName("card")
        yuzey_layout = QVBoxLayout(yuzey)
        yuzey_layout.setContentsMargins(6, 6, 6, 6)
        yuzey_layout.setSpacing(0)
        self.yedek_model = QStandardItemModel()
        self.yedek_liste = QListView()
        self.yedek_liste.setObjectName("cardList")
        self.yedek_liste.setItemDelegate(CardDelegate(self.yedek_liste, "backup"))
        self.yedek_liste.setModel(self.yedek_model)
        self.yedek_liste.setSpacing(2)
        self.yedek_panel = QStackedWidget()
        self.yedek_panel.addWidget(self.yedek_liste)
        self.yedek_panel.addWidget(EmptyState("Arama bilgilerinizi koruyun", "Henüz bir yedek yok. “Yedek oluştur” ile\nşifreli bir kopya saklayabilirsiniz.", "backup"))
        yuzey_layout.addWidget(self.yedek_panel, 1)
        k.addWidget(yuzey, 1)
        self.yedek_bilgi = QLabel("Yedekler bu bilgisayarda saklanır. Kaynak belgelerinizi içermez.")
        self.yedek_bilgi.setProperty("ikincil", True)
        self.yedek_bilgi.setWordWrap(True)
        k.addWidget(self.yedek_bilgi)
        self._yedek_tazele()

    def _guncelleme_bolumu(self, k):
        """Güncellemeler: durum satırı + denetle/indir/iptal ve ilerleme."""
        bas = QHBoxLayout()
        bas.setSpacing(9)
        bas.addWidget(bolum("Güncellemeler"))
        k.addLayout(bas)
        self.update_durum = label("", "ikincil")
        self.update_durum.setWordWrap(True)
        self.update_denetle_btn = QPushButton("Güncellemeyi denetle")
        self.update_denetle_btn.clicked.connect(lambda: self._guncelleme_denetle())
        self.update_indir_btn = QPushButton("İndir ve kur")
        self.update_indir_btn.setProperty("birincil", True)
        self.update_indir_btn.clicked.connect(self._guncelleme_indir)
        self.update_iptal_btn = QPushButton("İptal")
        self.update_iptal_btn.clicked.connect(self._guncelleme_iptal)
        if not self._guncelleme_yapilabilir():
            self.update_denetle_btn.setVisible(False)
            self.update_durum.setText(
                "Bu kopya kaynak koddan çalışıyor; güncelleme denetimi kurulu sürümde kullanılabilir.")
        else:
            self.update_durum.setText(f"Sürüm {__version__} kurulu.")
        self.update_indir_btn.setVisible(False)
        self.update_iptal_btn.setVisible(False)
        self.update_bar = QProgressBar()
        self.update_bar.setVisible(False)
        k.addWidget(ayar_satiri(
            "Sürüm", "Yeni sürüm çıktığında buradan indirilir; kurulum kendiliğinden tamamlanır.",
            self._denetim_satiri(self.update_durum, self.update_denetle_btn,
                                 self.update_indir_btn, self.update_iptal_btn)))
        k.addWidget(self.update_bar)

    def _yedek_dizin(self):
        d = os.path.join(os.path.dirname(os.path.abspath(self.kasa_yolu)), "..", "Backups")
        return os.path.abspath(d)

    def _yedek_tazele(self):
        archive_ui.refresh_backups(self)

    def _yedek_al(self):
        if self.con is None: return
        path=self.kasa_yolu; password=self._sifre; directory=self._yedek_dizin(); roots=self._kokler()
        self.durum.showMessage('Yedek oluşturuluyor…')
        def ready(path):
            self.durum.showMessage('Yedek oluşturuldu ve doğrulandı: '+path)
            self._yedek_tazele()
        archive_ui.job(self,'backup_create',lambda con:backup_mod.create_backup(con,path,password,directory,manual=True,forbid_under=roots),ready,writable=True)

    def _yedek_acilir(self, yol, sifre):
        """Yedek verilen şifreyle açılıp doğrulanabiliyor mu (sessiz deneme)."""
        try:
            return backup_mod.verify_backup(yol, sifre)["ok"]
        except Exception:
            return False

    def _geri_yukle(self):
        if not self._exclusive_ready():
            return
        idx = self.yedek_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.yedek_model.item(idx.row()).data()
        if self.sifresiz:
            # Şifresiz kasada yedekler de iç anahtarla korunur; şifre sorulmaz.
            backup_password = vault.SIFRESIZ_ANAHTAR
        else:
            password_dialog = ParolaDialog(self, verify=lambda pw: None)
            password_dialog.setWindowTitle("Yedek şifresini doğrulayın")
            if password_dialog.exec() != QDialog.Accepted:
                return
            backup_password = password_dialog.old.text()
            password_dialog.old.clear()
            # Şifresiz dönemde alınmış yedekler iç anahtarla açılır (kullanıcı bilmez).
            if not self._yedek_acilir(yol, backup_password or self._sifre) \
                    and self._yedek_acilir(yol, vault.SIFRESIZ_ANAHTAR):
                backup_password = vault.SIFRESIZ_ANAHTAR
        if QMessageBox.question(
                self, "Geri yükle",
                "Mevcut kasa rollback'e alınacak ve seçili yedek açılacak.\nDevam edilsin mi?") \
                != QMessageBox.Yes:
            return
        path=self.kasa_yolu; password=self._sifre
        def restore(con):
            con.close()
            return backup_mod.restore_replace(path,password,yol,os.path.join(os.path.dirname(path),'staging'),backup_password=backup_password)
        def reopen(message):
            self.centralWidget().setEnabled(True)
            self._kasa_ac(); self._yedek_tazele(); self._durum_yaz()
            self.durum.showMessage(message)
        self.con.close(); self.con=None
        archive_ui.job(self,'restore',restore,lambda result:reopen(f"Geri yükleme tamamlandı: {result['kasa_counts'].get('files','?')} dosya"),writable=True,failed=lambda error:reopen('Geri yükleme başarısız; mevcut kasa korunuyor: '+error))
        self.centralWidget().setEnabled(False)
        self.durum.showMessage('Yedek doğrulanıyor ve geri yükleniyor…')

    # -- ayarlar: bolum basliklari + kil payi ayiricili satirlar --
    def _ekran_ayarlar(self):
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(22, 18, 22, 20)
        outer.setSpacing(6)
        ic = QWidget()
        ic.setObjectName("ayarGovde")
        ic.setAttribute(Qt.WA_StyledBackground, True)
        k = QVBoxLayout(ic)
        k.setContentsMargins(0, 0, 8, 0)
        k.setSpacing(0)

        def baslik(text):
            return bolum(text)

        from . import ocr_setup
        k.addWidget(baslik("Çalışma"))
        hazir = ocr_setup.ready()[0]
        self.ocr_status = label("Hazır" if hazir else "Eksik", "basari" if hazir else "hata")
        ocr_repair = QPushButton("Doğrula / onar")
        ocr_repair.setProperty("kucuk", True)
        ocr_repair.clicked.connect(self._ocr_repair)
        k.addWidget(ayar_satiri("OCR bileşenleri", "Türkçe metin tanıma durumu", self._denetim_satiri(self.ocr_status, ocr_repair)))
        self.scan_time_edit = QTimeEdit()
        self.scan_time_edit.setDisplayFormat("HH:mm")
        self.scan_time_edit.setAccessibleName("Günlük tarama saati")
        try:
            value = QTime(int(migrate.get_setting(self.con, "saat", "12")), int(migrate.get_setting(self.con, "dakika", "30")))
            self.scan_time_edit.setTime(value if value.isValid() else QTime(12, 30))
        except ValueError:
            self.scan_time_edit.setTime(QTime(12, 30))
        k.addWidget(ayar_satiri("Günlük tarama saati", "Bilgisayar açıksa bu saatte taranır.", self.scan_time_edit))
        self.gecikme = QCheckBox()
        self.gecikme.setChecked(migrate.get_setting(self.con, "gecikme", "0") == "1")
        k.addWidget(ayar_satiri("Ağ yükünü azaltmak için taramayı geciktir", "Cihaz başına küçük rastgele gecikme ekler.", self.gecikme))
        self.otostart = QCheckBox()
        startup_command = sched.autostart_get("Evrakci")
        self.otostart.setChecked(startup_command is not None)
        k.addWidget(ayar_satiri("Windows açılışında başlat", "Oturum açıldığında Evrakçı kendiliğinden başlar.", self.otostart))
        self.canli_izleme = QCheckBox()
        self.canli_izleme.setChecked(migrate.get_setting(self.con, "canli_izleme", "1") == "1")
        k.addWidget(ayar_satiri("Değişen klasörleri canlı izle", "Değişiklik olunca kendiliğinden tarar.", self.canli_izleme))
        self.tepsiye = QCheckBox()
        self.tepsiye.setChecked(migrate.get_setting(self.con, "tepsiye", "1") == "1")
        k.addWidget(ayar_satiri("Kapatınca tepsiye küçült", "Program arka planda çalışmaya devam eder.", self.tepsiye))
        import sys
        self.startup_status = label(
            "Açılış kaydı eski paket yolunu gösteriyor; Kaydet ile güncelleyin."
            if startup_command and getattr(sys, "frozen", False)
            and os.path.normcase(sys.executable) not in os.path.normcase(startup_command)
            else "", "ikincil")
        k.addWidget(self.startup_status)

        k.addWidget(baslik("Tüketim"))
        self.tuketim_klasoru = QLineEdit()
        self.tuketim_klasoru.setPlaceholderText("Boşsa kapalı")
        self.tuketim_klasoru.setText(migrate.get_setting(self.con, "tuketim_klasoru", ""))
        self.tuketim_sec_btn = QPushButton("Seç")
        self.tuketim_sec_btn.setProperty("kucuk", True)
        self.tuketim_sec_btn.clicked.connect(self._tuketim_sec)
        k.addWidget(ayar_satiri("Gelen klasörü", "Yeni evrakın düştüğü izlenen klasör.", self._denetim_satiri(self.tuketim_klasoru, self.tuketim_sec_btn)))
        self.tuketim_hedefi = QLineEdit()
        self.tuketim_hedefi.setPlaceholderText("Taşınacak arşiv klasörü")
        self.tuketim_hedefi.setText(migrate.get_setting(self.con, "tuketim_hedefi", ""))
        self.tuketim_hedef_sec_btn = QPushButton("Seç")
        self.tuketim_hedef_sec_btn.setProperty("kucuk", True)
        self.tuketim_hedef_sec_btn.clicked.connect(self._tuketim_hedef_sec)
        k.addWidget(ayar_satiri("Arşiv hedefi", "Evrakın taşınacağı arşiv klasörü.", self._denetim_satiri(self.tuketim_hedefi, self.tuketim_hedef_sec_btn)))

        k.addWidget(baslik("Etiket kuralları"))
        self.kural_liste = QListWidget()
        self.kural_liste.setObjectName("cardList")
        self.kural_liste.setMaximumHeight(110)
        k.addWidget(self.kural_liste)
        self.kural_etiket = QLineEdit()
        self.kural_etiket.setPlaceholderText("etiket")
        self.kural_etiket.setFixedWidth(110)
        self.kural_kelimeler = QLineEdit()
        self.kural_kelimeler.setPlaceholderText("kelime1, kelime2")
        self.kural_kip = QComboBox()
        self.kural_kip.addItems(["any", "all"])
        self.kural_ekle_btn = QPushButton("Ekle")
        self.kural_ekle_btn.setProperty("kucuk", True)
        self.kural_ekle_btn.clicked.connect(self._kural_ekle)
        self.kural_sil_btn = QPushButton("Sil")
        self.kural_sil_btn.setProperty("kucuk", True)
        self.kural_sil_btn.clicked.connect(self._kural_sil)
        kural_satir = QWidget()
        ks = QHBoxLayout(kural_satir)
        ks.setContentsMargins(0, 0, 0, 0)
        ks.setSpacing(8)
        for x in (self.kural_etiket, self.kural_kelimeler, self.kural_kip,
                  self.kural_ekle_btn, self.kural_sil_btn):
            ks.addWidget(x)
        k.addWidget(ayar_satiri("Yeni kural", "Kelime eşleşince etiket kendiliğinden eklenir.", kural_satir))

        k.addWidget(baslik("Kasa güvenliği"))
        self.kilit_sure = QComboBox()
        self.kilit_sure.addItems(["kapalı", "5", "15", "30"])
        cur = migrate.get_setting(self.con, "kilit_suresi", "15")
        self.kilit_sure.setCurrentText(cur if cur in ("5", "15", "30") else "kapalı")
        k.addWidget(ayar_satiri("Hareketsizlikte kilitle", "“Beni hatırla” açıkken otomatik kilit kapanır.", self.kilit_sure))
        self.sifre_btn = QPushButton("Şifre ekle" if self.sifresiz else "Parolayı değiştir")
        self.sifre_btn.clicked.connect(self._sifre_islemi)
        self.forget_btn = QPushButton("Hatırlanan girişi kaldır")
        self.forget_btn.clicked.connect(self._forget_login)
        self.forget_btn.setVisible(not self.sifresiz)
        k.addWidget(ayar_satiri("Şifre", "Şifresiz kasaya şifre ekleyin; mevcut şifreyi değiştirirken doğrulama istenir.",
                                self._denetim_satiri(self.sifre_btn, self.forget_btn)))
        self._kurtarma_bolumu(k)
        self._yedek_bolumu(k)
        from .model_ui import install
        install(self, k)
        self._guncelleme_bolumu(k)
        alt = "Yerel ve şifreli çalışır" if not self.sifresiz else "Yerel çalışır; şifre eklenebilir"
        self.surum_bilgi = QLabel(f"Evrakçı {__version__} · {alt}")
        self.surum_bilgi.setProperty("ikincil", True)
        k.addWidget(self.surum_bilgi)
        k.addStretch(1)

        kaydir = QScrollArea()
        kaydir.setWidgetResizable(True)
        kaydir.setFrameShape(QScrollArea.NoFrame)
        kaydir.setWidget(ic)
        outer.addWidget(kaydir, 1)
        self.settings_page = w
        self.yigin.addWidget(w)
        self._kural_tazele()

    def _denetim_satiri(self, *widgets):
        kutu = QWidget()
        row = QHBoxLayout(kutu)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for i, widget in enumerate(widgets):
            row.addWidget(widget, 1 if i == 0 and widget.__class__.__name__ in ("QLineEdit",) else 0)
        return kutu














    def _forget_login(self):
        remember.forget(self.kasa_yolu)
        QMessageBox.information(self, "Giriş", "Hatırlanan giriş kaldırıldı. Sonraki açılışta şifre istenecek.")

    def _ayar_kaydet(self):
        migrate.set_setting(self.con, "saat", str(self.scan_time_edit.time().hour()))
        migrate.set_setting(self.con, "dakika", str(self.scan_time_edit.time().minute()))
        self.tarama_time.setText(f"{self.scan_time_edit.time().hour():02d}:{self.scan_time_edit.time().minute():02d}")
        migrate.set_setting(self.con, "gecikme", "1" if self.gecikme.isChecked() else "0")
        onceki_izleme = migrate.get_setting(self.con, "canli_izleme", "1")
        migrate.set_setting(self.con, "canli_izleme", "1" if self.canli_izleme.isChecked() else "0")
        if ("1" if self.canli_izleme.isChecked() else "0") != onceki_izleme:
            if self.canli_izleme.isChecked():
                self._izleme_baslat()
            else:
                self._izleme_durdur()
        migrate.set_setting(self.con, "tepsiye", "1" if self.tepsiye.isChecked() else "0")
        kaydir = self.tuketim_klasoru.text().strip()
        hedef = self.tuketim_hedefi.text().strip()
        if kaydir and not os.path.isdir(kaydir):
            QMessageBox.warning(self, "Tüketim", "Tüketim klasörü bulunamadı.")
            return
        if hedef and not os.path.isdir(hedef):
            QMessageBox.warning(self, "Tüketim", "Tüketim hedefi bulunamadı.")
            return
        if bool(kaydir) != bool(hedef):
            QMessageBox.warning(self, "Tüketim", "Klasör ve hedef birlikte verilmeli (boş = kapalı).")
            return
        migrate.set_setting(self.con, "tuketim_klasoru", kaydir)
        migrate.set_setting(self.con, "tuketim_hedefi", hedef)
        ks = self.kilit_sure.currentText()
        migrate.set_setting(self.con, "kilit_suresi", "0" if ks == "kapalı" else ks)
        try:
            if self.otostart.isChecked():
                import sys
                if not getattr(sys, "frozen", False):
                    raise RuntimeError("Otomatik başlatma paketlenmiş EXE üzerinden etkinleştirilmelidir.")
                sched.autostart_set("Evrakci", sys.executable, self.kasa_yolu)
                self.startup_status.clear()
            else:
                sched.autostart_clear("Evrakci")
                self.startup_status.clear()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Otomatik başlatma", f"Yazılamadı: {e}")
        QMessageBox.information(self, "Ayarlar", "Kaydedildi.")

    def _ocr_repair(self):
        if not self._exclusive_ready():
            return
        from .ocr_setup_ui import prepare_ocr
        from . import ocr_setup
        if prepare_ocr(self):
            count = ocr_setup.reopen_deferred(self.con)
            self.ocr_status.setText("OCR kullanıma hazır")
            QMessageBox.information(self, "OCR", f"Bileşenler hazır. {count} ertelenmiş OCR işi yeniden denenebilir.")
        else:
            self.ocr_status.setText("OCR bileşenleri eksik")

    def _exclusive_ready(self):
        if self.con is None:
            return False
        if (self.isci_thread is not None or self._search_thread is not None
                or self._debounce.isActive() or self._pending_search is not None
                or self.file_debounce.isActive()
                or self.onizleme.busy() or self._jobs or self._kaldir_thread is not None
                or self._haric_thread is not None):
            QMessageBox.information(self, "İşlem sürüyor", "Devam eden tarama, arama, hariç/kök kaldırma veya önizlemenin bitmesini bekleyin. Taramayı iptal edebilirsiniz.")
            return False
        return True

    def _sifre_islemi(self):
        """Şifresiz kasada şifre ekler; şifreli kasada parolayı değiştirir."""
        if self.sifresiz:
            self._sifre_ekle()
        else:
            self._parola_degistir()

    def _sifre_ekle(self):
        """Şifresiz kasaya şifre ekle; kurtarma anahtarı o an hazırlanır."""
        if not self._exclusive_ready():
            return
        d = ParolaDialog(self, mode="ekle")
        sonuc = d.exec()
        yeni = d.new.text()
        d.new.clear()
        d.confirm.clear()
        if sonuc != QDialog.Accepted:
            return
        self.con.close()
        self.con = None
        hata = None
        try:
            backup_mod.change_password(self.kasa_yolu, vault.SIFRESIZ_ANAHTAR, yeni, self._yedek_dizin())
            self._sifre = yeni
            self.sifresiz = False
            remember.forget(self.kasa_yolu)
        except Exception as ex:  # noqa: BLE001
            hata = ex
        try:
            self._kasa_ac()
        except Exception as ex:  # noqa: BLE001
            QMessageBox.critical(self, "Şifre", f"Kasa yeniden açılamadı: {ex}")
            return
        if hata is not None:
            QMessageBox.critical(self, "Şifre", f"Şifre eklenemedi: {hata}")
            return
        try:
            migrate.set_setting(self.con, "kasa_sifresiz", "0")
        except Exception:
            pass
        try:
            recovery.ensure_exists(self.kasa_yolu, self._sifre)
        except Exception as error:  # noqa: BLE001
            diagnostics.record("recovery_setup_failed", type(error).__name__)
        self.sifre_btn.setText("Parolayı değiştir")
        self.forget_btn.setVisible(True)
        self.surum_bilgi.setText(f"Evrakçı {__version__} · Yerel ve şifreli çalışır")
        self._kurtarma_tazele()
        QMessageBox.information(
            self, "Şifre",
            "Şifre eklendi. Sonraki açılışta kasa bu şifreyle açılır. Kurtarma anahtarı "
            "oluşturuldu; Ayarlar bölümündeki “Kurtarma anahtarı” satırından görüntüleyebilirsiniz.")

    def _parola_degistir(self):
        if not self._exclusive_ready():
            return
        def verify(password):
            check = vault.open_vault(self.kasa_yolu, password)
            check.close()
        d = ParolaDialog(self, change=True, verify=verify)
        if d.exec() != QDialog.Accepted:
            return
        old, new = d.old.text(), d.new.text()
        self.con.close()
        self.con = None
        try:
            backup_mod.change_password(self.kasa_yolu, old, new, self._yedek_dizin())
            self._sifre = new
            remember.forget(self.kasa_yolu)
            QMessageBox.information(self, "Şifre", "Şifreniz değiştirildi. Önceki yedekler eski şifreyle açılır.")
        except Exception as ex:
            QMessageBox.critical(self, "Şifre", f"İşlem tamamlanamadı: {ex}")
        finally:
            d.old.clear()
            d.new.clear()
            d.confirm.clear()
            self._kasa_ac()

    # -- ekran/durum/tepsi/kilit --
    def _ekran(self, i):
        started = time.perf_counter()
        if i == len(EKRANLAR):
            self.kilitle()
            return
        if i < 0 or i >= self.yigin.count():
            return
        self.yigin.setCurrentIndex(i)
        name = EKRANLAR[i]
        self.head_bar.baslik.setText(name if i else "Ara")
        self.head_bar.aciklama.setText(SAYFA_ACIKLAMA.get(name, ""))
        self.head_bar.aciklama.setVisible(bool(SAYFA_ACIKLAMA.get(name)))
        if name == 'Tarama' and self.isci_thread is not None:
            self._scan_show()
        if name == 'Geçmiş':
            self._gecmis_tazele()
        elif name == 'Taranmış Evraklar':
            self._files_refresh(reset=True)
        elif name == 'Kaynaklar':
            self._kok_tazele()
        elif name == 'Ayarlar':
            self._yedek_tazele()
            self._kurtarma_tazele()
            from .model_ui import refresh_coverage
            refresh_coverage(self)
        QTimer.singleShot(0, lambda: diagnostics.record('tab_ready_ms', str(round((time.perf_counter() - started) * 1000))))

    def _durum_yaz(self):
        try:
            kok_sayi = len(self._kokler())
        except Exception:
            kok_sayi = 0
        son = migrate.get_setting(self.con, "son_tarama", "—") if self.con else "—"
        self.durum.showMessage(f"Kasa açık • {kok_sayi} kök • Son tarama: {son}")

    def _tema_degistir(self, mode):
        diagnostics.record("theme", mode if mode in ("sistem", "acik", "koyu") else "unknown")
        theme.apply(QApplication.instance(), mode)
        try:
            migrate.set_setting(self.con, "tema", mode)
        except Exception:
            pass
        if getattr(self, "_toast", None) is not None:
            self._toast.goster(f"{self.tema_sec.currentText()} uygulandı.")
        self.durum.showMessage(f"{self.tema_sec.currentText()} uygulandı.")
        QTimer.singleShot(0, self._tema_yenile)
        QTimer.singleShot(0, lambda: self.onizleme.yenile())

    def _tepsi(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tepsi = None
            return
        self.tepsi = QSystemTrayIcon(self)
        self._tray_frames = theme.scan_icons()
        self._tray_frame = 0
        self._tray_timer = QTimer(self)
        self._tray_timer.setInterval(150)
        self._tray_timer.timeout.connect(self._tray_tick)
        self.tepsi.setIcon(theme.app_icon())
        self.tepsi.setToolTip("Evrakçı • Yerel belge arşivi")
        m = QMenu(self)
        self._tray_menu = m
        for ad, fn in (("Aç", self._bring_forward), ("Şimdi tara", self._tara_baslat),
                       ("Kasayı kilitle", self.kilitle), ("Çıkış", self._cikis)):
            if self.sifresiz and ad == "Kasayı kilitle":
                continue  # Şifresiz kasada kilit yok.
            a = QAction(ad, self)
            a.triggered.connect(fn)
            m.addAction(a)
            if ad == "Şimdi tara":
                self._tray_scan_action = a
        self.tepsi.setContextMenu(m)
        self.tepsi.activated.connect(self._tray_activated)
        self.tepsi.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._bring_forward()

    def _bring_forward(self):
        if self._locked:
            if hasattr(self, "_unlock_dialog"):
                self._unlock_dialog.show()
                self._unlock_dialog.raise_()
                self._unlock_dialog.activateWindow()
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _scan_metrics_update(self, data):
        data = dict(data)
        if data.get('inventory_ready'):
            data['documents_remaining'] = max(0,data.get('documents_total',0)-data.get('documents_done',0))
        for key, value in self.scan_metrics.items():
            value.setText('—' if key in ('documents_done','documents_remaining') and not data.get('inventory_ready') else f"{data.get(key, 0):,}")

    def _scan_show(self):
        if self._locked:
            return
        self.scan_dialog.show()
        self.scan_dialog.raise_()
        self.scan_dialog.activateWindow()

    def _scan_paused(self, paused):
        if self._locked or self._scan_status == "cancelling":
            return
        self._scan_state("paused" if paused else "running")
        self.tarama_bilgi.setText("Tarama duraklatıldı." if paused else "Tarama sürüyor…")
        self.popup_status.setText(self.tarama_bilgi.text())

    def _scan_state(self, state):
        self._scan_status = state
        text = {"running": "Tarama sürüyor…", "pausing": "Duraklatılıyor…",
                "paused": "Tarama duraklatıldı", "cancelling": "İptal ediliyor…"}.get(state)
        self.tara_btn.setText(text or "Şimdi tara")
        item = self.nav.item(2)
        item.setText("" if self._collapsed else text or "Tarama")
        item.setToolTip(text or "Tarama")
        if hasattr(self, "_tray_scan_action"):
            self._tray_scan_action.setText(text or "Şimdi tara")
        if getattr(self, "tepsi", None) is not None:
            self.tepsi.setToolTip("Evrakçı • " + ("Kasa kilitli" if self._locked else text or "Yerel belge arşivi"))
            if state in ("running", "pausing", "cancelling"):
                self._tray_timer.start()
            else:
                self._tray_timer.stop()
                self.tepsi.setIcon(theme.scan_icons(paused=True)[0] if state == "paused" else theme.app_icon())

    def _tray_tick(self):
        self._tray_frame = (self._tray_frame + 1) % len(self._tray_frames)
        self.tepsi.setIcon(self._tray_frames[self._tray_frame])

    def _zamanlayici_kontrol(self, ilk=False):
        if (self._locked or self.con is None or self.isci_thread is not None
                or self._kaldir_thread is not None or self._haric_thread is not None):
            return
        if not self._kokler():
            return
        try:
            saat = int(migrate.get_setting(self.con, "saat", "12"))
            dakika = int(migrate.get_setting(self.con, "dakika", "30"))
            lag = sched.device_lag_min(os.environ.get("COMPUTERNAME", "pc")) \
                if migrate.get_setting(self.con, "gecikme", "0") == "1" else 0
            son_txt = migrate.get_setting(self.con, "son_slot", "")
            son = dt.datetime.fromisoformat(son_txt) if son_txt else None
            kos, neden = sched.should_run(dt.datetime.now(), son, saat, dakika, lag, migrate.get_setting(self.con, "tarama_ele_alinan_gun", ""))
        except Exception:
            return
        if kos and not ilk:
            self._tara_baslat(automatic=True)
        elif kos and ilk:
            self.durum.showMessage("Planlı tarama henüz yapılmadı. Başlatmak için “Şimdi tara”ya basın.")

    def kilitle(self):
        if self._locked or self.sifresiz:
            return
        if self._kaldir_thread is not None or self._haric_thread is not None:
            self._kaldir_lock_pending = True
            self.durum.showMessage("Arka plan işlemi bitince kasa kilitlenecek.")
            return
        diagnostics.record("lock")
        self._job_generation+=1
        self._job_pending.clear()
        self._list_cache.clear()
        for worker in self._jobs: worker.stop.set()
        from .vocab import clear_cache
        clear_cache()
        self._thumblari_durdur()
        self._buyuk_gorsel_yukle(None)
        self.preview_dialog.hide()
        self.preview_path.clear(); self.file_rows=[]; self.file_model.clear(); self.file_filter.clear()
        self.file_notice.clear(); self.file_notice.hide(); self.search_progress.hide()
        if getattr(self,'_connection_reply',None): self._connection_reply.abort()

        remember.forget(self.kasa_yolu)
        self._locked = True
        from . import embed
        embed.close()
        self._debounce.stop()
        self._pending_search = None
        if self._search_thread is not None:
            self._search_thread.stop.set()
        self.hide()
        self.sonuclar = []
        self.arama_kutu.clear()
        self.kayitli_liste.clear()
        self.etiket_filtre.clear()
        self.etiket_yaz.clear()
        self.kural_liste.clear()
        self.kural_etiket.clear()
        self.kural_kelimeler.clear()
        self.tuketim_klasoru.clear()
        self.tuketim_hedefi.clear()
        self.sonuc_model.clear()
        self.sonuc_liste.selectionModel().clearSelection()
        self.sonuc_izgara.selectionModel().clearSelection()
        self.toplu_bar.hide()
        self.secim_sayac.clear()
        self.gecmis_model.clear()
        self.gecmis_sayi.clear()
        self.kok_model.clear()
        self.kaynak_sayi.clear()
        self.yedek_model.clear()
        self.onizleme.temizle()
        self.scan_timer.stop()
        self._izleme_durdur()
        with self._izleme_kilit:
            self._izleme_bekleyen.clear()
        self.scan_dialog.hide()
        self.popup_scope.clear()
        self.popup_status.setText("Kasa kilitli.")
        if self._guncelleme_isci is not None:
            self._guncelleme_isci.iptal_et()
            if self._guncelleme_thread is not None:
                self._guncelleme_thread.quit()
        self._guncelleme_sifirla()
        self.source_title.clear()
        self.source_path.clear()
        self.source_status.clear()
        self._scan_state("idle")
        self.scan_log.clear()
        self.scan_history.clear()
        self.scan_current.setText("Kasa kilitli.")
        self.scan_counts.clear()
        for value in self.scan_metrics.values():
            value.clear()
        self.scan_progress_detail.clear()
        self.tarama_bar.hide()
        self.tarama_bar.setValue(0)
        self.scan_phase_bar.hide()
        self.scan_clock.clear()
        self.scope_path.clear()
        self.scope_sources.clear()
        self.retry_scan.hide()
        self.haric_kutu.clear()
        self._filtre_cipleri()  # M3: aktif filtre çipleri ve sayacı temizlenir
        self.oneri.clear()
        self.sonuc_sayi.clear()
        self.secim_ad.setText("Henüz seçim yok")
        self.secim_yol.clear()
        self.secim_tur.clear()
        self.secim_etiket.clear()
        self.secim_onizle.setEnabled(False)
        self.secim_kopyala.setEnabled(False)
        self.gecmis_sorgu.setText("Bir arama seçin")
        self.gecmis_filtre.clear()
        self.gecmis_calistir.setEnabled(False)
        self.gecmis_sil_btn.setEnabled(False)
        self.dosya_ad.setText("Bir kayıt seçin")
        self.dosya_yol.clear()
        self.dosya_bilgi.clear()
        self.dosya_onizle.setEnabled(False)
        if self.isci:
            self.isci.durdur()
        if self.con is not None:
            self.con.close()
            self.con = None
        self._sifre = ""
        self._kilit_ekrani()
        self._lock_poll = QTimer(self)
        self._lock_poll.timeout.connect(self._kilit_hazir)
        self._lock_poll.start(100)
        self._kilit_hazir()

    def _kilit_ekrani(self):
        """Kilit ekranını kur: şifre veya (istenirse) kurtarma anahtarıyla açma."""
        self._unlock_dialog = ParolaDialog(self, verify=self._unlock, allow_remember=False,
                                           kasa_yolu=self.kasa_yolu)
        self._unlock_dialog.accepted.connect(self._unlocked)
        self._unlock_dialog.rejected.connect(self._cikis)
        self._kurtarma_kopru()

    def _kurtarma_kopru(self):
        """'Şifremi unuttum' basılırsa kurtarma ekranına geç (kilit diyaloğunu yeniden kur)."""
        pencere = self._unlock_dialog
        def gecis():
            if pencere.result() != MOD_KURTARMA:
                return
            if not os.path.isfile(recovery.container_path(self.kasa_yolu)):
                QMessageBox.information(
                    self, "Kurtarma",
                    "Bu kasada kurtarma anahtarı yok. Şifrenizi unuttuysanız kasa açılamaz; "
                    "varsa eski yedeklerinizden geri dönebilir veya kaynak belgelerinizi "
                    "yeniden taratabilirsiniz.")
                if not self._locked:
                    return
                pencere.show()
                return
            yeni = ParolaDialog(self, mode="kurtarma", verify=self._kurtarma_yap,
                                kasa_yolu=self.kasa_yolu)
            self._unlock_dialog = yeni
            yeni.finished.connect(self._kurtarma_bitti)
            yeni.show()
        pencere.finished.connect(gecis)

    def _kurtarma_bitti(self, kod):
        """Kurtarma penceresi kapandı: açıldıysa devam, olmadıysa kilit ekranına dön."""
        if self._locked and self.con is None:
            self._kilit_ekrani()
            self._kilit_hazir()

    def _kurtarma_yap(self, paket):
        """('kurtarma', anahtar, yeni_sifre) -> kasayı kurtar ve bağlantıyı aç."""
        _etiket, anahtar, yeni_sifre = paket
        sonuc = recovery.recover(self.kasa_yolu, anahtar, yeni_sifre,
                                 backup_dir=self._yedek_dizin())
        self._sifre = yeni_sifre
        remember.forget(self.kasa_yolu)
        try:
            self.con = vault.open_vault(self.kasa_yolu, yeni_sifre)
        except Exception as error:
            self._sifre = ""
            raise RuntimeError(f"Kurtarma sonrası kasa açılamadı: {error}") from error
        self._kurtarma_sonucu = sonuc
        # Kurtarma penceresi kapanınca _unlocked çalışsın
        QTimer.singleShot(0, self._unlocked)

    def _kilit_hazir(self):
        if self.isci_thread is None and self._search_thread is None and not self.onizleme.busy() and not self._jobs:
            self._lock_poll.stop()
            from .ocr import clean_stale
            clean_stale(os.path.dirname(os.path.abspath(self.kasa_yolu)), max_age_sec=0)
            self._unlock_dialog.show()

    def _unlock(self, password):
        self._sifre = password
        try:
            self._kasa_ac()
        except Exception:
            self._sifre = ""
            raise

    def _unlocked(self):
        diagnostics.record("unlock")
        self._locked = False
        from . import embed
        threading.Thread(target=lambda: embed.isit_oturumu(cancel=lambda: self._locked or self._exiting), daemon=True).start()
        self.centralWidget().setEnabled(True)
        self._unlock_dialog.old.clear()
        self._son_hareket = dt.datetime.now()
        kurtarma_sonucu = getattr(self, "_kurtarma_sonucu", None)
        self._kurtarma_sonucu = None
        self._kok_tazele()
        self._yedek_tazele()
        self._kurtarma_tazele()
        self._kurtarma_bildirim_goster()
        self._kayitli_tazele()
        self._kural_tazele()
        self._scan_history_refresh()
        self._scope_changed()
        self._gorunum_yukle()
        self.show()
        self._durum_yaz()
        self._scan_state("idle")
        self._zamanlayici_kontrol()
        self._izleme_baslat()
        if kurtarma_sonucu:
            yeni = kurtarma_sonucu.get("yeni_anahtar", "")
            self._toast_goster("Kasa yeni şifreyle açıldı; kurtarma anahtarı yenilendi.")
            self.durum.showMessage("Kurtarma tamamlandı. Kaynak belgeleriniz değişmedi.")
            if yeni:
                self._kurtarma_goster(yeni)

    def _cikis(self):
        diagnostics.record("exit")
        self._exiting = True
        self._izleme_durdur()
        if self._guncelleme_isci is not None:
            # Bekleyen güncelleme işi kapanışı geciktirmesin.
            self._guncelleme_isci.iptal_et()
            if self._guncelleme_thread is not None:
                self._guncelleme_thread.quit()
                self._guncelleme_thread.wait(2000)
        self._job_generation+=1
        self._job_pending.clear()
        for worker in self._jobs: worker.stop.set()
        if self._jobs:
            self.hide(); QTimer.singleShot(100,self._cikis); return
        from . import embed
        embed.close()
        if self.isci_thread is not None:
            if self.isci:
                self.isci.durdur()
            self.hide()
            self.isci_thread.finished.connect(self._cikis)
            return
        if self._search_thread is not None:
            self._search_thread.stop.set()
            self._search_thread.finished.connect(self._cikis)
            return
        if self._kaldir_thread is not None:
            self._kaldir_thread.finished.connect(self._cikis)
            return
        if self._haric_thread is not None:
            self._haric_thread.finished.connect(self._cikis)
            return
        if any(getattr(self, ad, None) is not None
               for ad in ("_thumb_loader", "_buyuk_loader", "_dosya_thumb_loader")):
            self._thumblari_durdur()
            QTimer.singleShot(100, self._cikis)
            return
        if self.onizleme.busy():
            self.onizleme.temizle()
            QTimer.singleShot(100, self._cikis)
            return
        self.scan_dialog.hide()
        if hasattr(self, "_tray_timer"):
            self._tray_timer.stop()
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, ev):
        # Küçük resim yükleyicileri hafiftir: kapanışı geciktirmeden burada
        # bitirilirler. Koşan bir QThread nesnesi pencereyle birlikte yok
        # edilirse Qt süreci düşürür (0xC0000409).
        self._thumblari_durdur()
        try:
            tepsiye = self.con is not None and \
                migrate.get_setting(self.con, "tepsiye", "1") == "1"
        except Exception:
            tepsiye = False
        if not self._exiting and tepsiye and getattr(self, "tepsi", None) is not None:
            diagnostics.record("hide_to_tray")
            self._save_window_geometry()
            ev.ignore()
            self.scan_dialog.hide()
            self.hide()
            return
        # Önizleme nesnesi yok edilmeden önce kendi yükleyicileri (sayfa rayı)
        # durdurulur; koşan QThread pencereyle birlikte yok edilirse Qt düşer.
        self.onizleme.temizle()
        if (self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy()
                or self._jobs or self._kaldir_thread is not None or self._haric_thread is not None
                or self._thumb_loader is not None or self._buyuk_loader is not None
                or self._dosya_thumb_loader is not None):
            ev.ignore()
            self._cikis()
            return
        from . import embed
        embed.close()
        self._save_window_geometry()
        try:
            if self.con is not None:
                vault.lock(self.con, os.path.dirname(os.path.abspath(self.kasa_yolu)))
        except Exception:
            pass
        self.con = None
        self._debounce.stop()
        self.scan_dialog.hide()
        if hasattr(self, "_tray_timer"):
            self._tray_timer.stop()
        self.scan_timer.stop()
        self._izleme_durdur()
        self.hareketsizlik.stop()
        self._schedule_timer.stop()
        if hasattr(self, "_lock_poll"):
            self._lock_poll.stop()
        if hasattr(self, "_unlock_dialog"):
            self._unlock_dialog.rejected.disconnect()
            self._unlock_dialog.close()
        if self.tepsi is not None:
            self.tepsi.hide()
        super().closeEvent(ev)
        QApplication.instance().removeEventFilter(self)
        if hasattr(self, "_oturum_filtresi"):
            QApplication.instance().removeNativeEventFilter(self._oturum_filtresi)
        try:
            import ctypes
            if getattr(self, "_wts_registered", False):
                ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification(int(self.winId()))
        except Exception:
            pass
        if not self._exiting:
            QTimer.singleShot(0, QApplication.instance().quit)


def _instance_name(vault_path):
    import hashlib
    normalized = os.path.normcase(os.path.abspath(vault_path)).encode("utf-8")
    return "Evrakci-" + hashlib.sha256(normalized).hexdigest()[:24]


def _wake_existing(name):
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(1500):
        return False
    socket.disconnectFromServer()
    return True


def _serve_activation(app, name):
    QLocalServer.removeServer(name)  # The per-vault lock is already owned here.
    server = QLocalServer(app)
    if not server.listen(name):
        diagnostics.record("activation_server_failed")
        return None

    def incoming():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            target = getattr(app, "_main_window", None)
            if target is not None:
                target._bring_forward()
            else:
                target = (getattr(app, "_login", None) or
                          getattr(app, "_setup", None) or
                          getattr(app, "_startup_dialog", None))
                if target is not None:
                    target.show()
                    target.raise_()
                    target.activateWindow()
            socket.deleteLater()
            diagnostics.record("activation")
    server.newConnection.connect(incoming)
    return server


def main(kasa_yolu=None, sifre=None):
    import argparse
    ap = argparse.ArgumentParser(prog="evrakci")
    ap.add_argument("--kasa", default=kasa_yolu)
    ap.add_argument("--tray", action="store_true")
    args, _bilinmeyen = ap.parse_known_args()
    if "--restarted" in _bilinmeyen:
        # Güncelleme bekçi betiğinden gelen normal açılış: tek seferlik
        # komut yok, taze sürüm sadece açılır.
        diagnostics.install()
        diagnostics.record("update_restarted")
    app = QApplication.instance() or QApplication([])
    diagnostics.install()
    app.setApplicationName("Evrakçı")
    app.setQuitOnLastWindowClosed(False)
    from PySide6.QtCore import QSettings
    theme.apply(app, QSettings("Evrakci", "Appearance").value("theme", "sistem"))
    if not args.kasa:
        from .cli import DEFAULT_VAULT
        args.kasa = DEFAULT_VAULT
    from PySide6.QtCore import QLockFile
    os.makedirs(os.path.dirname(os.path.abspath(args.kasa)), exist_ok=True)
    instance_lock = QLockFile(os.path.abspath(args.kasa) + ".app.lock")
    if not instance_lock.tryLock(0):
        if _wake_existing(_instance_name(args.kasa)):
            return 0
        QMessageBox.warning(None, "Evrakçı yanıt vermiyor",
                            "Evrakçı işlemi açık görünüyor ancak pencereyi gösterme isteğine yanıt vermedi. "
                            "Görev Yöneticisi'nde işlemi kontrol edin; tanı kaydı Evrakci/Logs/lifecycle.log içindedir.")
        return 1
    server = _serve_activation(app, _instance_name(args.kasa))
    app._activation_server = server
    diagnostics.record("instance_ready")
    setup = None
    if not os.path.exists(args.kasa):
        from .wizard import Sihirbaz
        setup = Sihirbaz()
        app._setup = setup
        diagnostics.record("setup_dialog")
        if setup.exec() != QDialog.Accepted:
            diagnostics.record("setup_cancelled")
            return 1
        diagnostics.record("setup_accepted")
        sifre = setup.s1.text()
        os.makedirs(os.path.dirname(os.path.abspath(args.kasa)), exist_ok=True)
        if not sifre:
            # Şifre boş bırakıldı: kasa iç anahtarla açılır, açılışta şifre sorulmaz.
            sifre = vault.SIFRESIZ_ANAHTAR
            diagnostics.record("setup_passwordless")
    if setup is not None:
        from .ocr_setup_ui import prepare_ocr
        diagnostics.record("ocr_prepare")
        if not prepare_ocr():
            diagnostics.record("ocr_unavailable")
            return 1
        diagnostics.record("ocr_ready")
        from .bootstrap import Bootstrap
        selection = dict(setup.secim)
        selection.pop("sifre", None)
        setup.s1.clear()
        setup.s2.clear()
        setup.secim.pop("sifre", None)
        setup.deleteLater()
        class StartupDialog(QDialog):
            @Slot()
            def mark_ready(self):
                app._startup["success"] = True

            @Slot(str)
            def failure(self, message):
                failed(message)

            @Slot()
            def open_main(self):
                if app._startup["success"]:
                    ready()

            def reject(self):
                if retry.isVisible():
                    app.quit()

            def closeEvent(self, event):
                if retry.isVisible():
                    event.accept()
                    app.quit()
                else:
                    event.ignore()

        progress = StartupDialog()
        app._startup_dialog = progress
        progress.setWindowTitle("Evrakçı • Hazırlanıyor")
        progress.setWindowIcon(theme.app_icon())
        progress.setMinimumWidth(480)
        content = QVBoxLayout(progress)
        content.setContentsMargins(28, 28, 28, 28)
        status = label("Çalışma alanınız hazırlanıyor…", "subheading")
        content.addWidget(status)
        content.addWidget(label("Şifreli kasa kuruluyor. Tamamlandığında Evrakçı kendiliğinden açılacak.", "ikincil"))
        bar = QProgressBar()
        bar.setRange(0, 0)
        content.addWidget(bar)
        retry = QPushButton("Yeniden dene")
        retry.hide()
        content.addWidget(retry)
        exit_button = QPushButton("Çıkış")
        exit_button.hide()
        exit_button.clicked.connect(app.quit)
        content.addWidget(exit_button)
        progress.show()
        # Başlangıç nesneleri, tüm sinyaller tamamlanana kadar uygulamaya ait.
        app._startup = {"dialog": progress, "lock": instance_lock}

        def failed(message):
            diagnostics.record("setup_failed")
            status.setText(message)
            bar.hide()
            retry.show()
            exit_button.show()

        def ready():
            try:
                diagnostics.record("setup_ready")
                pen = AnaPencere(args.kasa, sifre)
                app._main_window = pen
                pen._kok_tazele()
                pen.show()
                progress.hide()
                QTimer.singleShot(0, lambda: pen._tara_baslat(automatic=True))
            except Exception as error:
                diagnostics.record("main_window_failed", type(error).__name__)
                failed(f"Çalışma alanı açılamadı: {error}")

        def prepare():
            status.setText("Çalışma alanınız hazırlanıyor…")
            retry.hide()
            exit_button.hide()
            bar.show()
            thread = QThread(app)
            worker = Bootstrap(args.kasa, sifre, selection)
            worker.moveToThread(thread)
            app._startup.update(thread=thread, worker=worker)
            app._startup["success"] = False
            worker.done.connect(progress.mark_ready)
            worker.error.connect(progress.failure)
            worker.done.connect(thread.quit)
            worker.error.connect(thread.quit)
            worker.done.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
            thread.started.connect(worker.run)
            thread.finished.connect(progress.open_main)
            thread.finished.connect(thread.deleteLater)
            thread.start()

        retry.clicked.connect(prepare)
        progress.rejected.connect(lambda: None)  # Hazırlık sırasında Esc süreci kapatmaz.
        QTimer.singleShot(0, prepare)
        try:
            return app.exec()
        finally:
            instance_lock.unlock()
            if server is not None:
                server.close()

    if sifre is None:
        sifre = remember.load(args.kasa)
        if sifre:
            try:
                check = vault.open_vault(args.kasa, sifre)
                check.close()
            except Exception:
                remember.forget(args.kasa)
                sifre = None
    if sifre is None and vault.sifresiz_mi(args.kasa):
        # Şifresiz kasa: iç anahtar açıyorsa kullanıcıya sorulmadan açılır.
        sifre = vault.SIFRESIZ_ANAHTAR
        diagnostics.record("passwordless_open")
    while sifre is None:
        diagnostics.record("login_dialog")
        def verify(password):
            con = vault.open_vault(args.kasa, password)
            con.close()
        login = ParolaDialog(verify=verify, kasa_yolu=args.kasa)
        app._login = login
        sonuc = login.exec()
        if sonuc == MOD_KURTARMA:
            # "Şifremi unuttum": kurtarma anahtarıyla aç, yeni şifre belirle.
            if not os.path.isfile(recovery.container_path(args.kasa)):
                QMessageBox.information(
                    None, "Kurtarma",
                    "Bu kasada kurtarma anahtarı yok. Şifrenizi unuttuysanız kasa açılamaz; "
                    "varsa eski yedeklerinizden geri dönebilir veya kaynak belgelerinizi "
                    "yeniden taratabilirsiniz.")
                diagnostics.record("login_recovery_missing")
                continue
            def kurtar(paket):
                _etiket, anahtar, yeni_sifre = paket
                recovery.recover(args.kasa, anahtar, yeni_sifre,
                                 backup_dir=os.path.abspath(os.path.join(
                                     os.path.dirname(args.kasa), '..', 'Backups')))
            kurtarma = ParolaDialog(mode="kurtarma", verify=kurtar, kasa_yolu=args.kasa)
            app._login = kurtarma
            if kurtarma.exec() != QDialog.Accepted:
                # "Şifremi biliyorum" veya kapatma: giriş ekranına dön.
                diagnostics.record("login_recovery_cancelled")
                continue
            remember.forget(args.kasa)
            sifre = kurtarma.new.text()
            kurtarma.old.clear()
            kurtarma.new.clear()
            kurtarma.confirm.clear()
            diagnostics.record("login_recovered")
        elif sonuc != QDialog.Accepted:
            diagnostics.record("login_cancelled")
            return 1
        else:
            diagnostics.record("login_accepted")
            sifre = login.old.text()
            if login.remember.isChecked():
                try:
                    remember.save(args.kasa, sifre)
                except OSError as error:
                    QMessageBox.warning(login, "Beni hatırla", str(error))
            login.old.clear()
    from .ocr_setup_ui import prepare_ocr
    diagnostics.record("ocr_prepare")
    if not prepare_ocr():
        diagnostics.record("ocr_unavailable")
        return 1
    diagnostics.record("ocr_ready")
    from .startup import OpeningDialog
    opening = OpeningDialog(args.kasa, sifre,
                            os.path.abspath(os.path.join(os.path.dirname(args.kasa), '..', 'Backups')))
    opening.setWindowIcon(theme.app_icon())
    app._startup_dialog = opening
    result = opening.prepare()
    if opening.worker.error and not opening.worker.stop.is_set():
        QMessageBox.critical(None, 'Kasa', f'Açılamadı: {opening.worker.error}')
        return 2
    if result != QDialog.Accepted:
        return 1
    try:
        pen = AnaPencere(args.kasa, sifre, prepared=True)
        app._main_window = pen
    except Exception as error:
        diagnostics.record("main_window_failed", type(error).__name__)
        if opening is not None:
            opening.close()
        QMessageBox.critical(None, "Kasa", f"Açılamadı: {error}")
        return 2
    sifre = ""
    if not args.tray or pen.tepsi is None:
        pen.show()
    if opening is not None:
        opening.close()
    diagnostics.record("main_window_ready")
    try:
        return app.exec()
    finally:
        instance_lock.unlock()
        if server is not None:
            server.close()
