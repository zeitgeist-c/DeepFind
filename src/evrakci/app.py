"""Evrakci masaustu: Varyant A (sol gezinme + sonuc + sag onizleme). Plan bolum 19-20.

Kilitlenmeden calisir: tarama QThread'de, arama debounce'lu, onizleme tembel.
Kilitte: baglantilar kapanir, model/onislem/gecmis temizlenir (SEC-03).
"""
from __future__ import annotations

import datetime as dt
import os
import threading
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, Qt, QAbstractNativeEventFilter, QTime, QEvent, QSettings, QRect
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QLocalServer, QLocalSocket
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel, QColor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListView,
                               QListWidget, QMainWindow, QMessageBox, QPushButton,
                               QSplitter, QStackedWidget, QStatusBar,
                               QSystemTrayIcon, QMenu, QVBoxLayout, QWidget,
                               QProgressBar, QSpinBox, QTimeEdit, QSizePolicy, QGridLayout, QFrame, QPlainTextEdit, QListWidgetItem, QScrollArea, QStyledItemDelegate, QStyle)

from . import backup as backup_mod
from . import coordinator, exclusions, history as hist_mod
from . import ai, migrate, rank, sched, theme, vault, remember, diagnostics, recovery
from .preview import Onizleme
from .version import __version__
from .vocab import rebuild_vocab
from .auth import ParolaDialog, MOD_KURTARMA
from .ui import (ayar_satiri, ayrac_d, bolum, bolme, brand, card, label, sayac,
                 sayfa_basi, stat_seridi, Toast, EmptyState, CardDelegate)
from . import archive_ui

EKRANLAR = ["Ara", "AI ile ara", "Kaynaklar", "Tarama", "Geçmiş", "Taranmış Evraklar", "Ayarlar"]
SAYFA_ACIKLAMA = {
    "Ara": "Dosya adı, içerik ve klasör bağlamıyla arayın.",
    "AI ile ara": "Alıntılarla arşivinize soru sorun; göndermeden önce inceleyin.",
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
            out = rank.search_ranked(con, q, year=year, ext=ext, limit=50,
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

    def snapshot(self):
        with self._progress_lock:
            return dict(self._latest)

    def report_progress(self, data, totals):
        combined = dict(data, **{k: data.get(k, 0) + totals.get(k, 0)
                               for k in ("found", "done", "failed", "ocr_done", "ocr_failed", "skipped", "pending")})
        with self._progress_lock:
            self._latest = combined
        now = time.monotonic()
        if now - self._last_emit >= 0.2:
            self._last_emit = now
            self.ilerleme.emit(combined)

    def stop_requested(self):
        waiting = self.paused.is_set() and not self._dur.is_set()
        if waiting:
            self.duraklama.emit(True)
        while self.paused.is_set() and not self._dur.is_set():
            time.sleep(0.1)
        if waiting:
            self.duraklama.emit(False)
        return self._dur.is_set()

    def durdur(self):
        self._dur.set()

    def kos(self):
        try:
            from .migrate import ensure_current
            con = vault.open_vault(self.kasa_yolu, self._sifre)
            try:
                ensure_current(con)
                toplam = {}
                all_complete = True
                for kok in self.kokler:
                    if self._dur.is_set():
                        break
                    st = coordinator.run_scan(con, self.kasa_yolu, kok,
                                              stop=self.stop_requested, guarded=True,
                                              progress=lambda data: self.report_progress(data, toplam))
                    all_complete = all_complete and bool(st.get("complete"))
                    for k, v in st.items():
                        if isinstance(v, (int, float)):
                            toplam[k] = toplam.get(k, 0) + v
                    toplam["result"] = st.get("result", "")
                toplam["complete"] = all_complete and not self._dur.is_set()
                if not toplam["complete"] and toplam.get("result") == "complete":
                    toplam["result"] = "partial"
                if self._dur.is_set():
                    toplam["result"] = "cancelled"
                if not self._dur.is_set():
                    self.ilerleme.emit(dict(self.snapshot(), stage="Arama sözlüğü güncelleniyor", path=""))
                    try:
                        rebuild_vocab(con)
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
                con.close()
        except Exception as e:  # noqa: BLE001 - worker hatasi arayuze tasinir
            diagnostics.record("scan_error", type(e).__name__)
            self.hata.emit(f"{type(e).__name__}: {e}")
        finally:
            self._sifre = "x" * 32


class AnaPencere(QMainWindow):
    def __init__(self, kasa_yolu, sifre, prepared=False):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.con = None
        self.sonuclar = []
        self._locked = False
        self._exiting = False
        self._search_thread = None
        self._pending_search = None
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

    def _kurtarma_ilk_kurulum(self):
        """Kurtarma anahtarı yoksa üret; sonucu tek seferlik bildirime hazırla."""
        if self.con is None or self._locked or not self._sifre:
            return
        durum = recovery.status(self.kasa_yolu)
        if durum.get("var") and recovery.load_key(self.kasa_yolu):
            return
        anahtar = recovery.refresh(self.kasa_yolu, self._sifre)
        self._kurtarma_yeni_bildirim = anahtar

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
        self._ekran_ai()
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
        for i, kind in enumerate(("search", "ai", "folder", "scan", "history", "document", "settings")):
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
        self.preview_path.setText(result['path'])
        self.onizleme.goster(self.con,result,self._sifre)
        self.preview_dialog.show(); self.preview_dialog.raise_()

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

    def _ai_show(self):
        self.nav.setCurrentRow(EKRANLAR.index('AI ile ara'))
        self._ai_refresh_docs()

    def _ai_doc_page(self,direction):
        self.ai_doc_offset=max(0,self.ai_doc_offset+direction*100) if direction else 0
        self._ai_refresh_docs()

    def _ai_test(self):
        if self.con is None: return
        key=migrate.get_setting(self.con,'gemini_api_key','')
        if not key:
            self.ai_connection.setText('Önce anahtarı kaydedin.'); return
        request=QNetworkRequest(QUrl(ai.endpoint(self.ai_model.currentData())))
        request.setHeader(QNetworkRequest.ContentTypeHeader,'application/json')
        request.setRawHeader(b'x-goog-api-key',key.encode())
        request.setTransferTimeout(15000)
        import json
        reply=self.ai_network.post(request,json.dumps({'contents':[{'parts':[{'text':'Reply OK'}]}],'generationConfig':{'maxOutputTokens':8}}).encode())
        self._connection_reply=reply
        self.ai_connection.setText('Bağlantı sınanıyor…')
        def ready():
            if self._locked: return
            code=reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            self.ai_connection.setText('Bağlantı doğrulandı.' if code==200 else {400:'İstek veya model geçersiz.',401:'Anahtar geçersiz.',403:'Anahtar veya model erişimi reddedildi.',404:'Model bulunamadı.',429:'Kota sınırına ulaşıldı.'}.get(code,'Ağ bağlantısı kurulamadı.'))
            reply.deleteLater(); self._connection_reply=None
        reply.finished.connect(ready)

    def _ai_suggest(self):
        if self.con is None or self.ai_reply is not None: return
        key=migrate.get_setting(self.con,'gemini_api_key','')
        if not key:
            self.ai_status.setText('Önce anahtarı kaydedin.'); return
        question=self.ai_question.text().strip()
        if not 3<=len(question)<=1000:
            self.ai_status.setText('Soruyu 3–1000 karakter arasında yazın.'); return
        import json
        request=QNetworkRequest(QUrl(ai.endpoint(self.ai_model.currentData())))
        request.setHeader(QNetworkRequest.ContentTypeHeader,'application/json')
        request.setRawHeader(b'x-goog-api-key',key.encode()); request.setTransferTimeout(20000)
        body={'contents':[{'parts':[{'text':'Bu sorudan belge aramak için en fazla 8 anahtar sözcük çıkar. Tarih, tutar ve evrak numarasını koru. Yalnız JSON nesnesi döndür: {"query":"sözcükler"}. Soru: '+question}]}]}
        reply=self.ai_network.post(request,json.dumps(body,ensure_ascii=False).encode())
        self._suggestion_reply=reply; self.ai_status.setText('Yalnız soru gönderildi; arama sözcükleri hazırlanıyor…')
        def ready():
            if self._locked or self.ai_question.text().strip()!=question:
                reply.deleteLater(); self._suggestion_reply=None; return
            try:
                payload=bytes(reply.readAll())
                if len(payload)>10000: raise ValueError()
                envelope=json.loads(payload)
                raw=''.join(p.get('text','') for p in envelope['candidates'][0]['content']['parts'])
                query=json.loads(raw)['query']
                if not isinstance(query,str) or not 1<=len(query)<=300 or len(query.split())>16: raise ValueError()
                self.ai_retrieval.setText(query); self.ai_status.setText('Önerilen sözcükleri inceleyin, ardından Alıntıları hazırla’ya basın.')
            except (ValueError,KeyError,IndexError,TypeError):
                self.ai_status.setText('Sorgu önerisi alınamadı; arama sözcüklerini kendiniz yazabilirsiniz.')
            reply.deleteLater(); self._suggestion_reply=None
        reply.finished.connect(ready)

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

        self.search_bar = QWidget()
        ust = QHBoxLayout(self.search_bar)
        ust.setContentsMargins(0, 0, 0, 0)
        ust.setSpacing(10)
        self.arama_kutu = QLineEdit()
        self.arama_kutu.setObjectName("search")
        self.arama_kutu.setAccessibleName("Belge arama")
        self.arama_kutu.setPlaceholderText("Arşivinizde arayın…   Örneğin: Ankara vergi 2024")
        self.arama_kutu.setClearButtonEnabled(True)
        self.arama_kutu.returnPressed.connect(self._ara_simdi)
        ust.addWidget(self.arama_kutu, 1)
        search = QPushButton("Ara")
        search.setProperty("birincil", True)
        search.clicked.connect(self._ara_simdi)
        ust.addWidget(search)
        k.addWidget(self.search_bar)
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
        self.aktif_filtre = QLabel("")
        self.aktif_filtre.setProperty("ikincil", True)
        self.aktif_filtre.setWordWrap(True)
        form.addWidget(self.aktif_filtre)
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
        self.csv_btn = QPushButton("CSV indir")
        self.csv_btn.setProperty("ghost", True)
        self.csv_btn.setProperty("kucuk", True)
        self.csv_btn.clicked.connect(self._sonuc_csv)
        bas.addWidget(self.csv_btn)
        ok.addLayout(bas)
        self.sonuc_model = QStandardItemModel()
        self.sonuc_liste = QListView()
        self.sonuc_liste.setObjectName("cardList")
        self.sonuc_liste.setItemDelegate(CardDelegate(self.sonuc_liste))
        self.sonuc_liste.setModel(self.sonuc_model)
        self.sonuc_liste.setSpacing(2)
        self.sonuc_liste.clicked.connect(self._secim_guncelle)
        self.sonuc_liste.doubleClicked.connect(self._sec)
        self.sonuc_panel = QStackedWidget()
        self.sonuc_panel.addWidget(self.sonuc_liste)
        self.search_empty = EmptyState("Aradığınız belgeye ulaşın", "Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
        self.sonuc_panel.addWidget(self.search_empty)
        self.sonuc_panel.setCurrentIndex(1)
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
        al.addStretch(1)
        self.secim_onizle = QPushButton("Ön izle")
        self.secim_onizle.setProperty("birincil", True)
        self.secim_onizle.clicked.connect(lambda: self._sec(self.sonuc_liste.currentIndex()))
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

    def _ara_simdi(self, reset=True):
        if reset: self._search_offset=0
        self._debounce.stop()
        if self.con is None:
            return
        q = self.arama_kutu.text()
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
            self.sonuc_panel.setCurrentIndex(1)
            self.search_empty.title.setText("Aradığınız belgeye ulaşın")
            self.search_empty.text.setText("Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
            self.oneri.setText("Son aramalar Geçmiş ekranında; aramak için yazın.")
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
        current = (self.arama_kutu.text(), self.yil_filtre.text().strip() or None,
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
        self.sonuc_panel.setCurrentIndex(0 if res else 1)
        if not res:
            self.search_empty.title.setText("Eşleşen belge bulunamadı")
            self.search_empty.text.setText("Farklı bir kelime deneyin veya arama filtrelerini genişletin.")
        for r in res:
            from PySide6.QtGui import QTextDocument
            snippet = QTextDocument()
            snippet.setHtml(r.get("snippet", ""))
            try:
                etiketler = rank.file_tags(self.con, r["file_id"])
            except Exception:
                etiketler = []
            item = QStandardItem(f"{r['name']}\n{r['path']}\n{r.get('ext', '').lstrip('.').upper()}  •  {r['label']}\n"
                                 + snippet.toPlainText()[:150]
                                 + (f"\nEtiket: {', '.join(etiketler)}" if etiketler else ""))
            if r.get('index_status')!='ok' or not r.get('content_available',True):
                lines=item.text().splitlines()
                lines[2]+=' • '+archive_ui.STATUS.get(r.get('index_status'),r.get('index_status',''))+' • '+(r.get('error_code') or '')+(' • Yalnız ad/yol eşleşmesi' if not r.get('content_available',True) else '')
                item.setText('\n'.join(lines))
            item.setEditable(False)
            item.setToolTip(r['path']+'\n'+snippet.toPlainText())
            self.sonuc_model.appendRow(item)
        if not res:
            self.oneri.setText("Sonuç yok." + (f" Yakın: {', '.join(out['suggestions'])}"
                                               if out["suggestions"] else ""))
        else:
            self.oneri.setText(f"{len(res)} sonuç" +
                               (f" • {', '.join(out['suggestions'][:3])}" if out["suggestions"] else ""))
        self.aktif_filtre.setText(" ".join(x for x in
                                           [f"yıl:{yil}" if yil else "",
                                            f"tür:{tur}" if tur else "",
                                            f"klasör:{kokf}" if kokf else "",
                                            f"etiket:{etiket}" if etiket else ""] if x))
        try:
            import json
            hist_mod.save(self.con, q, json.dumps({"yil": yil or "", "tur": tur or "tümü", "klasor": kokf, "etiket": etiket or ""}, ensure_ascii=False))
        except Exception:
            pass

    def _secili_dosya(self):
        idx = self.sonuc_liste.currentIndex()
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
        if self.con is None or self._locked:
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
            self.source_remove.setEnabled(bool(path))

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
        self.con.execute("DELETE FROM roots WHERE display_path=?", (yol,))
        remaining = self._kokler()
        for fid, path in self.con.execute("SELECT file_id,path FROM files").fetchall():
            if exclusions.is_excluded(path, [yol]) and not exclusions.is_excluded(path, remaining):
                self.con.execute("DELETE FROM files WHERE file_id=?", (fid,))
        self.con.commit()
        rebuild_vocab(self.con)
        self.onizleme.temizle()
        self.sonuclar = []
        self.sonuc_model.clear()
        self._kok_tazele()
        self._durum_yaz()

    def _haric_ekle(self):
        if not self._exclusive_ready():
            return
        kural = self.haric_kutu.text().strip()
        if not kural:
            return
        n = exclusions.add(self.con, kural)
        c = exclusions.purge_rule(self.con, n)
        QMessageBox.information(self, "Hariç", f"Kural kaydedildi; {c} dosyanın içeriği temizlendi.")
        self.haric_kutu.clear()
        self.sonuc_model.clear()
        self.sonuclar = []
        self.onizleme.temizle()

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
        self.tarama_bar.setRange(0, 0)
        self.tarama_bar.hide()
        popup.addWidget(self.tarama_bar)
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
        for i, (key, caption) in enumerate((("found", "Bulunan"), ("done", "İşlenen"), ("pending", "Bekleyen"),
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
        if self._locked or self.con is None:
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
        if self.isci is not None:
            data = self.isci.snapshot()
            if data:
                self._scan_progress(data)
        if self.scan_started:
            seconds = int(time.monotonic() - self._scan_elapsed)
            self.scan_clock.setText(f"Başlangıç {self.scan_started:%H:%M:%S} • Geçen süre {seconds // 60:02d}:{seconds % 60:02d}")

    def _scan_progress(self, data):
        if self._locked:
            return
        self._scan_metrics_update(data)
        self._scan_stage = data.get("stage", "")
        path = data.get("path", "")
        self.scan_current.setText(self._scan_stage + "\n" + path)
        self.popup_status.setText(self.tarama_bilgi.text())
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
        self.tarama_bar.hide()
        self.scan_timer.stop()
        self._scan_clock_update()
        result = {"cancelled": "Tarama iptal edildi", "complete": "Tarama tamamlandı",
                  "partial": "Tarama kısmen tamamlandı"}.get(st.get("result"), "Tarama durdu")
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
        self._tuketim_tara()
        if self._locked or self.con is None or self.isci_thread is not None:
            return
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

    def _geri_yukle(self):
        if not self._exclusive_ready():
            return
        idx = self.yedek_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.yedek_model.item(idx.row()).data()
        password_dialog = ParolaDialog(self, verify=lambda pw: None)
        password_dialog.setWindowTitle("Yedek şifresini doğrulayın")
        if password_dialog.exec() != QDialog.Accepted:
            return
        backup_password = password_dialog.old.text()
        password_dialog.old.clear()
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
        self.ocr_language = QComboBox()
        self.ocr_language.addItem("Türkçe", "tur")
        self.ocr_language.addItem("İngilizce", "eng")
        self.ocr_language.setCurrentIndex(max(0, self.ocr_language.findData(migrate.get_setting(self.con, "ocr_dili", "tur"))))
        k.addWidget(ayar_satiri("OCR dili", "Tanıma sırasında kullanılacak alfabe", self.ocr_language))
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
        sif = QPushButton("Parolayı değiştir")
        sif.clicked.connect(self._parola_degistir)
        forget = QPushButton("Hatırlanan girişi kaldır")
        forget.clicked.connect(self._forget_login)
        k.addWidget(ayar_satiri("Şifre", "Şifre değişirken mevcut şifreniz doğrulanır.", self._denetim_satiri(sif, forget)))
        self._kurtarma_bolumu(k)
        self._yedek_bolumu(k)
        self.surum_bilgi = QLabel(f"Evrakçı {__version__} · Yerel ve şifreli çalışır")
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

    def _ekran_ai(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self.ai_kurulum = QWidget()
        kl = QVBoxLayout(self.ai_kurulum)
        kl.setContentsMargins(0, 0, 0, 0)
        kl.addWidget(label("AI modeli • yalnız açık gönderim", "ikincil"))
        self.ai_model = QComboBox()
        self.ai_model.setAccessibleName("AI modeli")
        for model_id, caption in ai.MODELS.items():
            self.ai_model.addItem(caption, model_id)
        saved = migrate.get_setting(self.con, "ai_model", ai.MODEL)
        selected = ai.selected_model(saved)
        self.ai_model.setCurrentIndex(self.ai_model.findData(selected))
        if selected != saved:
            migrate.set_setting(self.con, "ai_model", selected)
        kl.addWidget(self.ai_model)
        key_row = QHBoxLayout()
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("API anahtarı kayıtlı" if migrate.get_setting(self.con, "gemini_api_key") else "Gemini API anahtarı")
        self.ai_key_input.setAccessibleName("Gemini API anahtarı")
        kl.addWidget(self.ai_key_input)
        key_satir = QHBoxLayout()
        key_save = QPushButton("Kasaya kaydet")
        key_save.setToolTip("Anahtarı kasaya kaydet")
        key_save.clicked.connect(self._ai_save_key)
        key_satir.addWidget(key_save)
        key_remove = QPushButton("Kaldır")
        key_remove.clicked.connect(self._ai_remove_key)
        key_satir.addWidget(key_remove)
        kl.addLayout(key_satir)
        test = QPushButton("Bağlantıyı test et")
        test.setProperty("ghost", True)
        test.clicked.connect(self._ai_test)
        kl.addWidget(test)
        self.ai_connection = label("Anahtar şifreli kasada saklanır.", "ikincil")
        self.ai_connection.setWordWrap(True)
        kl.addWidget(self.ai_connection)
        kl.addWidget(label("Word/Excel içine gömülü resimler OCR kapsamına dahil değildir.", "ikincil"))
        kl.addStretch(1)
        layout.addWidget(self.ai_kurulum)
        self.ai_soru = QWidget()
        sl = QVBoxLayout(self.ai_soru)
        sl.setContentsMargins(0, 0, 0, 0)
        mode_row = QHBoxLayout()
        self.ai_mode = QComboBox()
        self.ai_mode.addItem("Arşive soru sor", "question")
        self.ai_mode.addItem("Belgeyi özetle", "summary")
        self.ai_mode.currentIndexChanged.connect(self._ai_mode_changed)
        mode_row.addWidget(self.ai_mode)
        self.ai_question = QLineEdit()
        self.ai_question.setPlaceholderText("Örneğin: 2024 denetim raporunda hangi sonuçlar var?")
        self.ai_question.setAccessibleName("Arşive sorulacak soru")
        self.ai_question.returnPressed.connect(self._ai_prepare)
        mode_row.addWidget(self.ai_question, 1)
        self.ai_document = QComboBox()
        self.ai_document.setAccessibleName("Özetlenecek belge")
        self.ai_document.hide()
        mode_row.addWidget(self.ai_document, 1)
        sl.addLayout(mode_row)
        self.ai_retrieval = QLineEdit()
        self.ai_retrieval.setPlaceholderText("İsteğe bağlı arama sözcükleri; asıl soru korunur")
        sl.addWidget(self.ai_retrieval)
        self.ai_retrieval.textChanged.connect(self._ai_clear_preview)
        self.ai_doc_query = QLineEdit()
        self.ai_doc_query.setPlaceholderText("Özetlenecek belgede ad veya yol ara")
        sl.addWidget(self.ai_doc_query)
        self.ai_doc_offset = 0
        doc_nav = QHBoxLayout()
        for caption, direction in [("Önceki belgeler", -1), ("Sonraki belgeler", 1)]:
            button = QPushButton(caption)
            button.clicked.connect(lambda _, d=direction: self._ai_doc_page(d))
            doc_nav.addWidget(button)
        sl.addLayout(doc_nav)
        suggestions = QPushButton("Sorgu önerisi üret")
        suggestions.setToolTip("Gemini ile sorgu önerileri üret (yalnız soru gönderilir)")
        suggestions.clicked.connect(self._ai_suggest)
        sl.addWidget(suggestions)
        layout.addWidget(self.ai_soru)
        self.ai_alinti = QWidget()
        al = QVBoxLayout(self.ai_alinti)
        al.setContentsMargins(0, 0, 0, 0)
        prepare = QPushButton("Alıntıları hazırla")
        prepare.clicked.connect(self._ai_prepare)
        al.addWidget(prepare)
        self.ai_preview_box = QPlainTextEdit()
        self.ai_preview_box.setReadOnly(True)
        self.ai_preview_box.setPlaceholderText("Buluta gönderilecek metin burada görünecek.")
        self.ai_preview_box.setMinimumHeight(120)
        al.addWidget(self.ai_preview_box, 1)
        layout.addWidget(self.ai_alinti)
        self.ai_yanit = QWidget()
        yl = QVBoxLayout(self.ai_yanit)
        yl.setContentsMargins(0, 0, 0, 0)
        self.ai_send = QPushButton("Alıntıları gönder")
        self.ai_send.setToolTip("Gösterilen alıntıları gönder")
        self.ai_send.setProperty("birincil", True)
        self.ai_send.setEnabled(False)
        self.ai_send.clicked.connect(self._ai_send)
        yl.addWidget(self.ai_send)
        self.ai_status = label("Önce soru sorun veya bir belge seçin; alıntıları kontrol edin.", "ikincil")
        self.ai_status.setWordWrap(True)
        yl.addWidget(self.ai_status)
        self.ai_answer = QPlainTextEdit()
        self.ai_answer.setReadOnly(True)
        self.ai_answer.setPlaceholderText("Yanıt burada görünecek.")
        yl.addWidget(self.ai_answer, 1)
        self.ai_answer.hide()
        self.ai_sources = QListWidget()
        self.ai_sources.setMaximumHeight(90)
        self.ai_sources.itemClicked.connect(self._ai_open_source)
        yl.addWidget(self.ai_sources)
        self.ai_sources.hide()
        layout.addWidget(self.ai_yanit)
        self.ai_preview = None
        self.ai_reply = None
        self._ai_timed_out = False
        self.ai_network = QNetworkAccessManager(self)
        self.ai_timeout = QTimer(self)
        self.ai_timeout.setSingleShot(True)
        self.ai_timeout.timeout.connect(self._ai_abort_timeout)
        self.ai_question.textChanged.connect(self._ai_clear_preview)
        self.ai_document.currentIndexChanged.connect(self._ai_clear_preview)
        self.ai_model.currentIndexChanged.connect(self._ai_model_changed)
        self.ai_doc_timer = QTimer(w)
        self.ai_doc_timer.setSingleShot(True)
        self.ai_doc_timer.setInterval(300)
        self.ai_doc_timer.timeout.connect(lambda: self._ai_doc_page(0))
        self.ai_doc_query.textChanged.connect(lambda: self.ai_doc_timer.start())
        self._ai_ham = w

    def _ai_model_changed(self):
        if self.con is not None:
            migrate.set_setting(self.con, "ai_model", self.ai_model.currentData())
        self._ai_clear_preview()

    def _ai_mode_changed(self):
        summary = self.ai_mode.currentData() == "summary"
        self.ai_question.setVisible(not summary)
        self.ai_document.setVisible(summary)
        self._ai_clear_preview()
        if summary:
            self._ai_refresh_docs()

    def _ai_refresh_docs(self):
        archive_ui.refresh_docs(self)

    def _ai_save_key(self):
        key = self.ai_key_input.text().strip()
        if not key:
            self.ai_status.setText("Kaydedilecek anahtar yazılmadı.")
            return
        migrate.set_setting(self.con, "gemini_api_key", key)
        self.ai_key_input.clear()
        self.ai_key_input.setPlaceholderText("API anahtarı kayıtlı")
        self.ai_status.setText("API anahtarı şifreli kasaya kaydedildi.")

    def _ai_remove_key(self):
        migrate.set_setting(self.con, "gemini_api_key", "")
        self.ai_key_input.clear()
        self.ai_key_input.setPlaceholderText("Gemini API anahtarı")
        self.ai_status.setText("API anahtarı kasadan kaldırıldı.")

    def _ai_clear_preview(self):
        if self.ai_reply is not None:
            self.ai_timeout.stop()
            reply, self.ai_reply = self.ai_reply, None
            reply.abort()
            reply.deleteLater()
            self.ai_status.setText("İstek iptal edildi. Yeni alıntılar hazırlayın.")
        self.ai_preview = None
        self.ai_send.setEnabled(False)
        self.ai_preview_box.clear()
        self.ai_answer.clear()
        self.ai_answer.hide()
        self.ai_sources.clear()
        self.ai_sources.hide()

    def _ai_prepare(self):
        if self.con is None or self.ai_reply is not None:
            return
        self._ai_clear_preview()
        question=self.ai_question.text()
        retrieval=self.ai_retrieval.text().strip()
        mode=self.ai_mode.currentData()
        file_id=self.ai_document.currentData()
        self.ai_status.setText('İlgili indeks bölümleri hazırlanıyor…')
        def prepare(con):
            if mode=='summary':
                if file_id is None: raise ValueError('Önce bir belge seçin.')
                return ai.prepare_summary(con,file_id)
            return ai.prepare_question(con,question,retrieval or None)
        def ready(preview):
            if self.ai_question.text()!=question or self.ai_mode.currentData()!=mode or self.ai_retrieval.text().strip()!=retrieval: return
            self.ai_preview=preview
            self.ai_preview_box.setPlainText(ai.preview_text(preview))
            self.ai_send.setEnabled(True)
            self.ai_status.setText(f'{len(preview.sources)} alıntı hazır. Göndermeden önce inceleyin.' + (' Yalnız seçili kesitler gönderilecek.' if preview.truncated else ''))
        archive_ui.job(self,'ai_prepare',prepare,ready,failed=lambda error:self.ai_status.setText(error))

    def _ai_send(self):
        preview = self.ai_preview
        if self.con is None or preview is None or self.ai_reply is not None:
            return
        if not ai.still_current(self.con, preview):
            self._ai_clear_preview()
            self.ai_status.setText("İndeks değişti. Alıntıları yeniden hazırlayın.")
            return
        key = migrate.get_setting(self.con, "gemini_api_key", "")
        if not key:
            self.ai_status.setText("Önce Gemini API anahtarını kasaya kaydedin.")
            return
        model = self.ai_model.currentData()
        request = QNetworkRequest(QUrl(ai.endpoint(model)))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"x-goog-api-key", key.encode("utf-8"))
        reply = self.ai_network.post(request, ai.request_body(preview, model))
        self.ai_reply = reply
        self._ai_timed_out = False
        self.ai_send.setEnabled(False)
        self.ai_status.setText("Yanıt bekleniyor…")
        reply.finished.connect(lambda: self._ai_finished(reply))
        self.ai_timeout.start(30_000)

    def _ai_finished(self, reply):
        if reply is not self.ai_reply:
            reply.deleteLater()
            return
        self.ai_timeout.stop()
        self.ai_reply = None
        if self.con is None or self.ai_preview is None:
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NoError:
            status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if self._ai_timed_out:
                message = "AI isteği zaman aşımına uğradı."
            elif status_code in (401, 403):
                message = "API anahtarı veya erişim izni doğrulanamadı."
            elif status_code == 429:
                message = "Gemini kota sınırına ulaşıldı; daha sonra yeniden deneyin."
            else:
                message = "AI isteği tamamlanamadı. Bağlantıyı kontrol edin."
            self.ai_status.setText(message)
        else:
            try:
                answer, sources = ai.parse_response(bytes(reply.readAll()), self.ai_preview)
                if not ai.still_current(self.con, self.ai_preview):
                    raise ValueError("İndeks değişti; yanıtın kaynakları artık güncel değil.")
                self.ai_answer.setPlainText(answer)
                self.ai_answer.show()
                self.ai_sources.clear()
                for source in sources:
                    item = QListWidgetItem(f"[{source['id']}] {source['name']} • {source['label']}")
                    item.setData(Qt.UserRole, source)
                    self.ai_sources.addItem(item)
                self.ai_sources.show()
                self.ai_status.setText("Yanıtı ve aşağıdaki kaynakları kontrol edin.")
            except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
                self.ai_status.setText("AI yanıtı doğrulanamadı. Kanıt veya biçim hatalı.")
        self.ai_send.setEnabled(self.ai_preview is not None)
        reply.deleteLater()

    def _ai_open_source(self, item):
        if self.con is None:
            return
        source = item.data(Qt.UserRole)
        if source:
            if self.ai_preview is None or not ai.still_current(self.con, self.ai_preview):
                self.ai_status.setText("Kaynak indeksi değişti. Alıntıları yeniden hazırlayın.")
                return
            self._open_preview(source)

    def _ai_abort_timeout(self):
        if self.ai_reply is not None:
            self._ai_timed_out = True
            self.ai_reply.abort()

    def _ai_abort(self):
        self.ai_timeout.stop()
        reply, self.ai_reply = self.ai_reply, None
        if reply is not None:
            reply.abort()
            reply.deleteLater()
        self._ai_clear_preview()
        self.ai_question.clear()
        if hasattr(self,'ai_retrieval'): self.ai_retrieval.clear()
        self.ai_key_input.clear()
        self.ai_document.clear()
        if hasattr(self,'ai_doc_query'): self.ai_doc_query.clear()
        for attr in ('_suggestion_reply','_connection_reply'):
            reply=getattr(self,attr,None)
            if reply is not None:
                reply.abort(); reply.deleteLater(); setattr(self,attr,None)
        self.ai_status.setText("Kasa kilitli.")

    def _forget_login(self):
        remember.forget(self.kasa_yolu)
        QMessageBox.information(self, "Giriş", "Hatırlanan giriş kaldırıldı. Sonraki açılışta şifre istenecek.")

    def _ayar_kaydet(self):
        migrate.set_setting(self.con, "ocr_dili", self.ocr_language.currentData())
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
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy() or self._jobs:
            QMessageBox.information(self, "İşlem sürüyor", "Devam eden tarama, arama veya önizlemenin bitmesini bekleyin. Taramayı iptal edebilirsiniz.")
            return False
        return True

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
        elif name == 'AI ile ara':
            self._ai_refresh_docs()
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
        for key, value in self.scan_metrics.items():
            value.setText(f"{data.get(key, 0):,}")

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
        if self._locked or self.con is None or self.isci_thread is not None:
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
        if self._locked:
            return
        diagnostics.record("lock")
        self._job_generation+=1
        self._job_pending.clear()
        self._list_cache.clear()
        for worker in self._jobs: worker.stop.set()
        from .vocab import clear_cache
        clear_cache()
        self.preview_dialog.hide()
        self.preview_path.clear(); self.file_rows=[]; self.file_model.clear(); self.file_filter.clear()
        self.file_notice.clear(); self.file_notice.hide(); self.search_progress.hide()
        if getattr(self,'_connection_reply',None): self._connection_reply.abort()

        remember.forget(self.kasa_yolu)
        self._locked = True
        self._ai_abort()
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
        self.scan_clock.clear()
        self.scope_path.clear()
        self.scope_sources.clear()
        self.retry_scan.hide()
        self.haric_kutu.clear()
        self.aktif_filtre.clear()
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
        self.centralWidget().setEnabled(True)
        self._unlock_dialog.old.clear()
        self._son_hareket = dt.datetime.now()
        kurtarma_sonucu = getattr(self, "_kurtarma_sonucu", None)
        self._kurtarma_sonucu = None
        self._kok_tazele()
        self._yedek_tazele()
        self._kurtarma_tazele()
        self._kayitli_tazele()
        self._kural_tazele()
        self._scan_history_refresh()
        self._scope_changed()
        self.ai_key_input.setPlaceholderText("API anahtarı kayıtlı" if migrate.get_setting(self.con, "gemini_api_key") else "Gemini API anahtarı")
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
        self._job_generation+=1
        self._job_pending.clear()
        for worker in self._jobs: worker.stop.set()
        if self._jobs:
            self.hide(); QTimer.singleShot(100,self._cikis); return
        self._ai_abort()
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
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy() or self._jobs:
            ev.ignore()
            self._cikis()
            return
        self._ai_abort()
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
    if sifre is None:
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
                return 1
            def kurtar(paket):
                _etiket, anahtar, yeni_sifre = paket
                recovery.recover(args.kasa, anahtar, yeni_sifre,
                                 backup_dir=os.path.abspath(os.path.join(
                                     os.path.dirname(args.kasa), '..', 'Backups')))
            kurtarma = ParolaDialog(mode="kurtarma", verify=kurtar, kasa_yolu=args.kasa)
            app._login = kurtarma
            if kurtarma.exec() != QDialog.Accepted:
                diagnostics.record("login_recovery_cancelled")
                return 1
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
