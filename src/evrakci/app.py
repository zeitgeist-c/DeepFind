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
from . import ai, migrate, rank, sched, theme, vault, remember, diagnostics
from .preview import Onizleme
from .version import __version__
from .vocab import rebuild_vocab
from .auth import ParolaDialog
from .ui import brand, card, label, EmptyState, CardDelegate

EKRANLAR = ["Ara", "Kaynaklar", "Tarama", "Geçmiş", "Yedekler", "Ayarlar", "AI Yardımcısı"]


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
            q, year, ext, folder = self.request
            out = rank.search_ranked(con, q, year=year, ext=ext, limit=50,
                                     folder=folder or None)
            if not self.stop.is_set():
                self.sonuc.emit({"request": self.request, "out": out})
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
    def __init__(self, kasa_yolu, sifre):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.con = None
        self.sonuclar = []
        self._locked = False
        self._exiting = False
        self._search_thread = None
        self._pending_search = None
        self.setWindowTitle(f"Evrakçı {__version__}")
        self.setWindowIcon(theme.app_icon())
        self.setMinimumSize(1000, 640)
        self._geometry_ready = False
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.timeout.connect(self._save_window_geometry)

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

    # -- kurulum --
    def _kasa_ac(self):
        from .migrate import ensure_current, recover_scan_runs
        diagnostics.record("vault_open_begin")
        self.con = vault.open_vault(self.kasa_yolu, self._sifre)
        diagnostics.record("vault_open_ready")
        current_fts = self.con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
        if current_fts and "remove_diacritics 0" not in current_fts[0]:
            try:
                backup_mod.create_backup(self.con, self.kasa_yolu, self._sifre,
                                         self._yedek_dizin(), manual=True)
            except Exception:
                self.con.close()
                self.con = None
                raise RuntimeError("Geçiş öncesi indeks yedeği alınamadı; mevcut kasa korunuyor.")
        diagnostics.record("schema_begin")
        ensure_current(self.con)
        diagnostics.record("schema_ready")
        recover_scan_runs(self.con)

    def _arayuz(self):
        kok = QWidget()
        kok.setObjectName("kok")
        self.setCentralWidget(kok)
        dis = QHBoxLayout(kok)
        dis.setContentsMargins(16, 16, 20, 12)
        dis.setSpacing(22)
        rail = QFrame()
        rail.setObjectName("rail")
        self._rail_width = 264
        rail.setFixedWidth(self._rail_width)
        side = QVBoxLayout(rail)
        side.setContentsMargins(18, 24, 18, 20)
        side.setSpacing(24)
        self.rail = rail
        self._collapsed = False
        self.rail_brand = QWidget()
        brand_layout = QVBoxLayout(self.rail_brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(theme.app_icon().pixmap(38, 38))
        header.addWidget(logo, 0, Qt.AlignVCenter)
        heading = QLabel("Evrakçı")
        heading.setStyleSheet("font-size:24px; font-weight:700")
        header.addWidget(heading, 0, Qt.AlignVCenter)
        version = QLabel(__version__)
        version.setStyleSheet("font-size:13px; font-weight:600")
        header.addWidget(version, 0, Qt.AlignVCenter)
        header.addStretch()
        brand_layout.addLayout(header)
        side.addWidget(self.rail_brand)
        self.rail_toggle = QPushButton("Menüyü daralt")
        self.rail_toggle.setIcon(theme.symbol_icon("left"))
        self.rail_toggle.clicked.connect(self._nav_toggle)

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.ElideRight)
        self.nav.addItems(EKRANLAR)
        from PySide6.QtCore import QSize
        self.nav.setIconSize(QSize(19, 19))
        self.nav.setItemDelegate(RailDelegate(self, self.nav))
        for i, kind in enumerate(("search", "folder", "scan", "history", "backup", "settings", "search")):
            self.nav.item(i).setIcon(theme.symbol_icon(kind))
        self.nav.currentRowChanged.connect(self._ekran)
        side.addWidget(self.nav, 1)
        side.addWidget(self.rail_toggle)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        side.addLayout(actions)
        self.rail_actions = []
        for text, kind, callback in (("Kasayı kilitle", "lock", self.kilitle),
                                     ("Çıkış", "exit", self._cikis)):
            button = QPushButton(text)
            button.setIcon(theme.symbol_icon(kind))
            button.setToolTip(text)
            button.clicked.connect(callback)
            button.setAccessibleName(text)
            button.setMinimumWidth(0)
            actions.addWidget(button)
            self.rail_actions.append((button, text))
        self._rail_width = max(self._rail_width, sum(b.sizeHint().width() for b, _ in self.rail_actions) + 42)
        rail.setFixedWidth(self._rail_width)
        dis.addWidget(rail)
        workspace = QVBoxLayout()
        workspace.setSpacing(18)
        top = QHBoxLayout()
        top.addWidget(label("ÇALIŞMA ALANI", "eyebrow"))
        top.addStretch()
        top.addWidget(label("●  Kasa açık", "pill"))
        self.tara_btn = QPushButton("Şimdi tara")
        self.tara_btn.setIcon(theme.symbol_icon("scan", "#137C70"))
        self.tara_btn.clicked.connect(self._tara_baslat)
        top.addWidget(self.tara_btn)
        self.tema_sec = QComboBox()
        for caption, value in [("Sistem teması", "sistem"), ("Açık", "acik"), ("Koyu", "koyu")]:
            self.tema_sec.addItem(caption, value)
        self.tema_sec.setCurrentIndex(max(0, self.tema_sec.findData(migrate.get_setting(self.con, "tema", "sistem"))))
        self.tema_sec.currentIndexChanged.connect(lambda _: self._tema_degistir(self.tema_sec.currentData()))
        top.addWidget(self.tema_sec)
        workspace.addLayout(top)

        self.search_bar = QFrame()
        ust = QHBoxLayout(self.search_bar)
        ust.setContentsMargins(0, 0, 0, 0)
        self.arama_kutu = QLineEdit()
        self.arama_kutu.setObjectName("search")
        self.arama_kutu.setAccessibleName("Belge arama")
        self.arama_kutu.setPlaceholderText("Arşivinizde arayın…   Örneğin: Ankara vergi 2024")
        self.arama_kutu.addAction(theme.symbol_icon("search", "#65748B"), QLineEdit.LeadingPosition)
        self.arama_kutu.setClearButtonEnabled(True)
        self.arama_kutu.returnPressed.connect(self._ara_simdi)
        ust.addWidget(self.arama_kutu, 1)
        search = QPushButton("Ara")
        search.setProperty("birincil", True)
        search.clicked.connect(self._ara_simdi)
        ust.addWidget(search)
        workspace.addWidget(self.search_bar)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._ara_simdi)
        self.arama_kutu.textChanged.connect(lambda _t: self._debounce.start())

        govde = QSplitter(Qt.Horizontal)

        self.yigin = QStackedWidget()
        self._ekran_ara()
        self._ekran_kaynaklar()
        self._ekran_tarama()
        self._ekran_gecmis()
        self._ekran_yedekler()
        self._ekran_ayarlar()
        self._ekran_ai()
        descriptions = ["Ad, içerik ve klasör bağlamıyla belgelerinizi bulun.",
                        "Taranacak klasörleri ve kapsam dışında kalan yolları yönetin.",
                        "Arşivinizi güncelleyin; güvenli noktada duraklatıp devam edin.",
                        "Önceki aramalarınıza tek tıkla dönün.",
                        "Şifreli indeksinizi koruyun ve doğrulanmış yedeklere dönün.",
                        "Çalışma tercihleri ve kasa güvenliği.",
                        "Şifreli kasanızdaki alıntıları inceleyip isteğe bağlı bulut yanıtı alın."]
        for i, name in enumerate(EKRANLAR):
            layout = self.yigin.widget(i).layout()
            self.yigin.widget(i).setObjectName("pageCard")
            layout.setContentsMargins(24, 24, 24, 22)
            layout.setSpacing(16)
            heading = QLabel(name if i else "Belgelerinizi bulun")
            heading.setProperty("baslik", True)
            description = QLabel(descriptions[i])
            description.setProperty("ikincil", True)
            description.setWordWrap(True)
            if isinstance(layout, QFormLayout):
                layout.insertRow(0, description)
                layout.insertRow(0, heading)
            else:
                layout.insertWidget(0, description)
                layout.insertWidget(0, heading)
        govde.addWidget(self.yigin)

        self.onizleme = Onizleme()
        self.onizleme.setMinimumWidth(320)
        govde.addWidget(self.onizleme)
        govde.setChildrenCollapsible(False)
        govde.setSizes([550, 420])
        workspace.addWidget(govde, 1)
        dis.addLayout(workspace, 1)
        self.nav.setCurrentRow(0)

        self.durum = QStatusBar()
        self.setStatusBar(self.durum)
        self._durum_yaz()

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

    def _kisaltmalar(self):
        self.hareketsizlik = QTimer(self)
        self.hareketsizlik.timeout.connect(self._hareket_kontrol)
        self.hareketsizlik.start(60_000)
        self._son_hareket = dt.datetime.now()
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, _o, ev):
        from PySide6.QtCore import QEvent
        if _o is getattr(self, "source_split", None) and ev.type() == QEvent.Resize:
            QTimer.singleShot(0, self._source_layout)
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

    # -- arama ekrani --
    def _ekran_ara(self):
        w = QWidget()
        k = QVBoxLayout(w)
        fil = QHBoxLayout()
        self.yil_filtre = QLineEdit()
        self.yil_filtre.setPlaceholderText("Yıl (ör. 2024)")
        self.yil_filtre.setFixedWidth(120)
        self.tur_filtre = QComboBox()
        self.tur_filtre.addItems(["tümü", ".pdf", ".xlsx", ".xls", ".docx", ".doc"])
        self.sirket_filtre = QLineEdit()
        self.sirket_filtre.setPlaceholderText("Şirket veya klasör")
        for x in (self.yil_filtre, self.tur_filtre, self.sirket_filtre):
            fil.addWidget(x)
        self.yil_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        self.tur_filtre.currentTextChanged.connect(lambda _t: self._ara_simdi())
        self.sirket_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        k.addLayout(fil)
        self.aktif_filtre = QLabel("")
        self.aktif_filtre.setProperty("ikincil", True)
        k.addWidget(self.aktif_filtre)
        self.sonuc_model = QStandardItemModel()
        self.sonuc_liste = QListView()
        self.sonuc_liste.setObjectName("cardList")
        self.sonuc_liste.setItemDelegate(CardDelegate(self.sonuc_liste))
        self.sonuc_liste.setModel(self.sonuc_model)
        self.sonuc_liste.setSpacing(4)
        self.sonuc_liste.clicked.connect(self._sec)
        self.sonuc_panel = QStackedWidget()
        self.sonuc_panel.addWidget(self.sonuc_liste)
        self.search_empty = EmptyState("Aradığınız belgeye ulaşın", "Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
        self.sonuc_panel.addWidget(self.search_empty)
        self.sonuc_panel.setCurrentIndex(1)
        k.addWidget(self.sonuc_panel, 1)
        self.oneri = QLabel("")
        self.oneri.setProperty("ikincil", True)
        self.oneri.setWordWrap(True)
        k.addWidget(self.oneri)
        self.yigin.addWidget(w)

    def _ara_simdi(self):
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
            self.sonuc_panel.setCurrentIndex(1)
            self.search_empty.title.setText("Aradığınız belgeye ulaşın")
            self.search_empty.text.setText("Dosya adı veya içerikte geçen birkaç kelime yazın.\nSonuçlar burada listelenir.")
            self.oneri.setText("Son aramalar Geçmiş ekranında; aramak için yazın.")
            return
        yil = self.yil_filtre.text().strip() or None
        tur = self.tur_filtre.currentText()
        tur = None if tur == "tümü" else tur
        request = (q, yil, tur, self.sirket_filtre.text().strip().lower())
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
        q, yil, tur, kokf = message["request"]
        current = (self.arama_kutu.text(), self.yil_filtre.text().strip() or None,
                   None if self.tur_filtre.currentText() == "tümü" else self.tur_filtre.currentText(),
                   self.sirket_filtre.text().strip().lower())
        if message["request"] != current:
            return
        if "error" in message:
            self.oneri.setText(f"Arama tamamlanamadı: {message['error']}")
            return
        out = message["out"]
        res = out["results"]
        self.sonuclar = res
        self.sonuc_model.clear()
        self.sonuc_panel.setCurrentIndex(0 if res else 1)
        if not res:
            self.search_empty.title.setText("Eşleşen belge bulunamadı")
            self.search_empty.text.setText("Farklı bir kelime deneyin veya arama filtrelerini genişletin.")
        for r in res:
            from PySide6.QtGui import QTextDocument
            snippet = QTextDocument()
            snippet.setHtml(r.get("snippet", ""))
            item = QStandardItem(f"{r['name']}\n{r.get('ext', '').lstrip('.').upper()}  •  {r['label']}\n"
                                 + snippet.toPlainText()[:150])
            item.setEditable(False)
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
                                            f"klasör:{kokf}" if kokf else ""] if x))
        try:
            import json
            hist_mod.save(self.con, q, json.dumps({"yil": yil or "", "tur": tur or "tümü", "klasor": kokf}, ensure_ascii=False))
        except Exception:
            pass

    def _sec(self, idx):
        if self.con is None or not idx.isValid() or idx.row() >= len(self.sonuclar):
            return
        r = self.sonuclar[idx.row()]
        self.onizleme.goster(self.con, r)

    # -- kaynaklar --
    def _ekran_kaynaklar(self):
        w = QWidget()
        k = QVBoxLayout(w)
        self.kok_model = QStandardItemModel()
        self.kok_liste = QListView()
        self.kok_liste.setObjectName("cardList")
        self.kok_liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.kok_liste.setMinimumWidth(160)
        self.kok_liste.setItemDelegate(CardDelegate(self.kok_liste, "folder", compact=True))
        self.kok_liste.setModel(self.kok_model)
        self.kok_panel = QStackedWidget()
        self.kok_panel.addWidget(self.kok_liste)
        self.kok_panel.addWidget(EmptyState("İlk klasörünüzü ekleyin", "Aranacak belgelerin bulunduğu klasörleri\n“Klasör ekle” ile seçin.", "folder"))
        self.source_split = QSplitter(Qt.Horizontal)
        self.source_split.installEventFilter(self)
        self.source_split.addWidget(self.kok_panel)
        details, dl = card()
        dl.addWidget(label("SEÇİLİ KAYNAK", "eyebrow"))
        self.source_title = label("Bir kaynak seçin", "subheading")
        self.source_path = label("", "ikincil")
        self.source_path.setTextFormat(Qt.PlainText)
        self.source_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.source_status = label("", "pill")
        self.source_status.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        dl.addWidget(self.source_title)
        dl.addWidget(self.source_path)
        dl.addWidget(self.source_status)
        dl.addWidget(label("Kaynağı kaldırmak diskteki belgeleri silmez.", "ikincil"))
        dl.addStretch()
        details.setMinimumWidth(0)
        self.source_split.addWidget(details)
        self.source_split.setChildrenCollapsible(False)
        self.source_split.setStretchFactor(0, 1)
        self.source_split.setStretchFactor(1, 2)
        self.source_split.setSizes([300, 600])
        k.addWidget(self.source_split, 1)
        self.kok_liste.selectionModel().currentChanged.connect(self._source_selected)
        satir = QHBoxLayout()
        ekle = QPushButton("Klasör ekle")
        ekle.setProperty("birincil", True)
        ekle.clicked.connect(self._kok_ekle)
        kaldir = QPushButton("Kaldır")
        kaldir.clicked.connect(self._kok_kaldir)
        satir.addWidget(ekle)
        self.source_remove = kaldir
        dl.insertWidget(dl.count()-1, kaldir)
        satir.addStretch(1)
        k.addLayout(satir)
        self.haric_bilgi = QLabel("Hariç kuralı eklemek için klasör yolunu yazıp Dışla'ya basın:")
        self.haric_bilgi.setProperty("ikincil", True)
        self.haric_bilgi.setWordWrap(True)
        k.addWidget(self.haric_bilgi)
        hsatir = QHBoxLayout()
        self.haric_kutu = QLineEdit()
        disla = QPushButton("Dışla")
        disla.clicked.connect(self._haric_ekle)
        hsatir.addWidget(self.haric_kutu, 1)
        hsatir.addWidget(disla)
        k.addLayout(hsatir)
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
        if hasattr(self, "source_remove"):
            self.source_remove.setEnabled(bool(path))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._source_layout)
        if self._geometry_ready and not self.isMaximized():
            self._geometry_timer.start(500)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._geometry_ready and not self.isMaximized():
            self._geometry_timer.start(500)

    def _source_layout(self):
        if hasattr(self, "source_split"):
            orientation = Qt.Vertical if self.width() < 1200 else Qt.Horizontal
            if self.source_split.orientation() != orientation:
                self.source_split.setOrientation(orientation)
                self.source_split.setSizes([220, 440])

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
        overview = QHBoxLayout()
        sources, sources_layout = card()
        sources_layout.addWidget(label("TARAMA KAPSAMI", "eyebrow"))
        self.tarama_root_count = label(f"{len(self._kokler())} kaynak klasörü", "baslik")
        sources_layout.addWidget(self.tarama_root_count)
        sources_layout.addWidget(label("Kaynaklar bölümünden değiştirebilirsiniz.", "ikincil"))
        schedule, schedule_layout = card()
        schedule_layout.addWidget(label("GÜNLÜK DÜZEN", "eyebrow"))
        hour = migrate.get_setting(self.con, "saat", "12")
        minute = migrate.get_setting(self.con, "dakika", "30")
        try:
            scheduled_time = f"{int(hour):02d}:{int(minute):02d}"
        except (TypeError, ValueError):
            scheduled_time = "Saat belirlenmedi"
        self.tarama_time = label(scheduled_time, "baslik")
        schedule_layout.addWidget(self.tarama_time)
        schedule_layout.addWidget(label("Planlanan tarama saati • Ayarlar’dan değişir.", "ikincil"))
        overview.addWidget(sources, 1)
        overview.addWidget(schedule, 1)
        k.addLayout(overview)
        self.scope_mode = QComboBox()
        self.scope_mode.addItems(["Tüm kaynaklar", "Seçili kaynaklar", "Bir klasör veya disk"])
        k.addWidget(self.scope_mode)
        self.scope_sources = QListWidget()
        self.scope_sources.setMaximumHeight(140)
        self.scope_sources.hide()
        k.addWidget(self.scope_sources)
        self.scope_path = QLineEdit()
        self.scope_path.setPlaceholderText("Bu tarama için klasör veya disk yolu")
        self.scope_path.hide()
        k.addWidget(self.scope_path)
        self.scope_browse = QPushButton("Taranacak klasörü seç…")
        self.scope_browse.clicked.connect(self._scope_browse)
        self.scope_browse.hide()
        k.addWidget(self.scope_browse)
        self.scope_mode.currentIndexChanged.connect(self._scope_changed)
        self.tarama_bilgi = QLabel("Henüz tarama yapılmadı.")
        self.tarama_bilgi.setWordWrap(True)
        k.addWidget(self.tarama_bilgi)
        self.scan_dialog = QDialog(self)
        self.scan_dialog.setWindowTitle("Evrakçı • Tarama ayrıntıları")
        self.scan_dialog.resize(760, 560)
        popup = QVBoxLayout(self.scan_dialog)
        popup.addWidget(label("Tarama ayrıntıları", "baslik"))
        self.popup_status = label("Henüz tarama yapılmadı.", "subheading")
        popup.addWidget(self.popup_status)
        self.popup_scope = label("", "ikincil")
        self.popup_scope.setTextFormat(Qt.PlainText)
        self.popup_scope.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.popup_scope.setMinimumWidth(0)
        popup.addWidget(self.popup_scope)
        self.details_open = QPushButton("Tarama ayrıntılarını aç")
        self.details_open.clicked.connect(self._scan_show)
        k.addWidget(self.details_open)
        k.addWidget(label("SON TARAMALAR", "eyebrow"))
        self.scan_history = QListWidget()
        self.scan_history.setMaximumHeight(150)
        self.scan_history.setAccessibleName("Son tarama kayıtları")
        k.addWidget(self.scan_history)
        self._scan_history_refresh()
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
        self.scan_metrics = {}
        for i, (key, caption) in enumerate((("found", "Bulunan"), ("done", "İşlenen"), ("pending", "Bekleyen"),
                                           ("skipped", "Güncel / atlanan"), ("ocr_done", "OCR tamamlanan"), ("failed", "İşlem hatası"), ("ocr_failed", "OCR hatası"))):
            metric, ml = card()
            ml.setContentsMargins(12, 10, 12, 10)
            ml.addWidget(label(caption, "ikincil"))
            value = label("0", "subheading")
            ml.addWidget(value)
            self.scan_metrics[key] = value
            counts_grid.addWidget(metric, i // 3, i % 3)
        detail_layout.addLayout(counts_grid)
        detail_layout.addWidget(self.scan_clock)
        self.scan_details_toggle = QPushButton("Ayrıntıları göster")
        self.scan_details_toggle.setCheckable(True)
        self.scan_log = QPlainTextEdit()
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
        self.scan_start = QPushButton("Taramayı başlat")
        self.scan_start.setProperty("birincil", True)
        self.scan_start.clicked.connect(self._tara_baslat)
        k.addWidget(self.scan_start)
        self.duraklat_btn = QPushButton("Duraklat")
        self.duraklat_btn.clicked.connect(self._tara_duraklat)
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.clicked.connect(self._tara_iptal)
        self.iptal_btn.setEnabled(False)
        satir.addWidget(self.duraklat_btn)
        satir.addWidget(self.iptal_btn)
        self.retry_scan = QPushButton("Sorunlu dosyaları yeniden dene")
        self.retry_scan.clicked.connect(self._retry_scan)
        self.retry_scan.hide()
        satir.addWidget(self.retry_scan)
        satir.addStretch(1)
        background = QPushButton("Arka planda sürdür")
        background.clicked.connect(self.scan_dialog.hide)
        satir.addWidget(background)
        popup.addLayout(satir)
        k.addStretch(1)
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(w)
        outer.addWidget(scroll)
        self.yigin.addWidget(page)
        self.isci = None
        self.isci_thread = None

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
            self.scan_history.addItem(
                f"{when} • {os.path.basename(root) or root} • {names.get(result, 'Sürüyor')} "
                f"• {done} işlendi / {found} bulundu • {pending} bekliyor • "
                f"{failed + ocr_failed} hata"
            )

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

    # -- gecmis --
    def _ekran_gecmis(self):
        w = QWidget()
        k = QVBoxLayout(w)
        self.gecmis_model = QStandardItemModel()
        self.gecmis_liste = QListView()
        self.gecmis_liste.setObjectName("cardList")
        self.gecmis_liste.setItemDelegate(CardDelegate(self.gecmis_liste, "history"))
        self.gecmis_liste.setModel(self.gecmis_model)
        self.gecmis_liste.doubleClicked.connect(self._gecmis_kullan)
        self.gecmis_panel = QStackedWidget()
        self.gecmis_panel.addWidget(self.gecmis_liste)
        self.gecmis_panel.addWidget(EmptyState("Aramalarınız burada kalır", "Önceki aramalarınıza yeniden ulaşabilir\nve aynı filtrelerle devam edebilirsiniz.", "history"))
        k.addWidget(self.gecmis_panel, 1)
        satir = QHBoxLayout()
        sil = QPushButton("Seçiliyi sil")
        sil.clicked.connect(self._gecmis_sil)
        temiz = QPushButton("Tümünü temizle")
        temiz.clicked.connect(self._gecmis_temizle)
        satir.addWidget(sil)
        satir.addWidget(temiz)
        satir.addStretch(1)
        k.addLayout(satir)
        self.yigin.addWidget(w)

    def _gecmis_tazele(self):
        self.gecmis_model.clear()
        try:
            rows = hist_mod.list_all(self.con)
        except Exception:
            rows = []
        for qid, q, f, _p, _t in rows:
            import json
            try:
                values = json.loads(f or "{}")
                parts = [str(values.get("yil") or ""),
                         str(values.get("tur") or "").replace("tümü", ""),
                         str(values.get("klasor") or "")]
                description = " • ".join(part for part in parts if part)
            except (ValueError, TypeError, AttributeError):
                description = "Kayıtlı arama filtreleri"
            item = QStandardItem(f"{q}\n{description or 'Tüm belgelerde arama'}")
            item.setEditable(False)
            item.setData(qid)
            item.setData((q, f), Qt.UserRole + 1)
            self.gecmis_model.appendRow(item)
        self.gecmis_panel.setCurrentIndex(0 if self.gecmis_model.rowCount() else 1)

    def _gecmis_kullan(self, idx):
        import json
        query, filters = self.gecmis_model.item(idx.row()).data(Qt.UserRole + 1)
        try:
            values = json.loads(filters)
        except (ValueError, TypeError):
            values = dict(x.split("=", 1) for x in filters.split(";") if "=" in x)
        controls = (self.arama_kutu, self.yil_filtre, self.tur_filtre, self.sirket_filtre)
        for control in controls:
            control.blockSignals(True)
        self.arama_kutu.setText(query)
        self.yil_filtre.setText(values.get("yil", ""))
        self.tur_filtre.setCurrentText(values.get("tur") or "tümü")
        self.sirket_filtre.setText(values.get("klasor", ""))
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

    # -- yedekler --
    def _ekran_yedekler(self):
        w = QWidget()
        k = QVBoxLayout(w)
        self.yedek_model = QStandardItemModel()
        self.yedek_liste = QListView()
        self.yedek_liste.setObjectName("cardList")
        self.yedek_liste.setItemDelegate(CardDelegate(self.yedek_liste, "backup"))
        self.yedek_liste.setModel(self.yedek_model)
        self.yedek_panel = QStackedWidget()
        self.yedek_panel.addWidget(self.yedek_liste)
        self.yedek_panel.addWidget(EmptyState("Arama bilgilerinizi koruyun", "Henüz bir yedek yok. “Yedek oluştur” ile\nşifreli bir kopya saklayabilirsiniz.", "backup"))
        k.addWidget(self.yedek_panel, 1)
        satir = QHBoxLayout()
        yeni = QPushButton("Yedek oluştur")
        yeni.setProperty("birincil", True)
        yeni.clicked.connect(self._yedek_al)
        geri = QPushButton("Geri yükle")
        geri.clicked.connect(self._geri_yukle)
        satir.addWidget(yeni)
        satir.addWidget(geri)
        satir.addStretch(1)
        k.addLayout(satir)
        self.yedek_bilgi = QLabel("Yedekler bu bilgisayarda saklanır. Kaynak belgelerinizi içermez.")
        self.yedek_bilgi.setProperty("ikincil", True)
        self.yedek_bilgi.setWordWrap(True)
        k.addWidget(self.yedek_bilgi)
        self.yigin.addWidget(w)
        self._yedek_tazele()

    def _yedek_dizin(self):
        d = os.path.join(os.path.dirname(os.path.abspath(self.kasa_yolu)), "..", "Backups")
        return os.path.abspath(d)

    def _yedek_tazele(self):
        self.yedek_model.clear()
        for b in backup_mod.list_backups(self._yedek_dizin()):
            item = QStandardItem(f"{'Manuel yedek' if b['manuel'] else 'Otomatik yedek'}\n"
                                 f"{os.path.basename(b['path'])}\n{b['boyut'] // 1024} KB • Şifreli kasa")
            item.setEditable(False)
            item.setData(b["path"])
            self.yedek_model.appendRow(item)
        self.yedek_panel.setCurrentIndex(0 if self.yedek_model.rowCount() else 1)

    def _yedek_al(self):
        if self.con is None:
            return
        try:
            y = backup_mod.create_backup(self.con, self.kasa_yolu, self._sifre,
                                         self._yedek_dizin(),
                                         manual=True,
                                         forbid_under=self._kokler())
            QMessageBox.information(self, "Yedek", f"Oluşturuldu ve doğrulandı:\n{y}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Yedek", f"Başarısız: {e}")
        self._yedek_tazele()

    def _geri_yukle(self):
        if not self._exclusive_ready():
            return
        idx = self.yedek_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.yedek_model.item(idx.row()).data()
        password_dialog = ParolaDialog(self, verify=lambda pw: backup_mod.verify_backup(yol, pw))
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
        self.con.close()
        self.con = None
        try:
            rap = backup_mod.restore_replace(
                self.kasa_yolu, self._sifre, yol,
                os.path.join(os.path.dirname(self.kasa_yolu), "staging"),
                backup_password=backup_password)
            QMessageBox.information(
                self, "Geri yükle",
                f"Tamam. Dosya: {rap['kasa_counts'].get('files', '?')} • "
                f"Korunan kural: {len(rap.get('korunan_kurallar', []))}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Geri yükle", f"Başarısız, mevcut kasa korunuyor: {e}")
        self._kasa_ac()
        self._yedek_tazele()
        self._durum_yaz()

    # -- ayarlar --
    def _ekran_ayarlar(self):
        w = QWidget()
        outer = QVBoxLayout(w)
        row = QHBoxLayout()
        general, general_layout = card()
        general_layout.addWidget(label("Çalışma düzeni", "subheading"))
        general_layout.addWidget(label("Uygulamanın ne zaman ve nasıl çalışacağını belirleyin.", "ikincil"))
        f = QFormLayout()
        f.setVerticalSpacing(18)
        general_layout.addLayout(f)
        from . import ocr_setup
        self.ocr_status = label("OCR kullanıma hazır" if ocr_setup.ready()[0] else "OCR bileşenleri eksik", "ikincil")
        general_layout.addWidget(self.ocr_status)
        self.ocr_language = QComboBox()
        self.ocr_language.addItem("Türkçe", "tur")
        self.ocr_language.addItem("İngilizce", "eng")
        self.ocr_language.setCurrentIndex(max(0, self.ocr_language.findData(migrate.get_setting(self.con, "ocr_dili", "tur"))))
        f.addRow("OCR dili:", self.ocr_language)
        ocr_repair = QPushButton("OCR bileşenlerini doğrula / onar")
        ocr_repair.clicked.connect(self._ocr_repair)
        general_layout.addWidget(ocr_repair)
        self.scan_time_edit = QTimeEdit()
        self.scan_time_edit.setDisplayFormat("HH:mm")
        self.scan_time_edit.setFixedWidth(120)
        self.scan_time_edit.setAccessibleName("Günlük tarama saati")
        try:
            value = QTime(int(migrate.get_setting(self.con, "saat", "12")), int(migrate.get_setting(self.con, "dakika", "30")))
            self.scan_time_edit.setTime(value if value.isValid() else QTime(12, 30))
        except ValueError:
            self.scan_time_edit.setTime(QTime(12, 30))
        f.addRow("Günlük tarama saati:", self.scan_time_edit)
        self.gecikme = QCheckBox("Ağ yükünü azaltmak için taramayı geciktir")
        self.gecikme.setChecked(migrate.get_setting(self.con, "gecikme", "0") == "1")
        f.addRow(self.gecikme)
        self.otostart = QCheckBox("Windows açılışında başlat")
        startup_command = sched.autostart_get("Evrakci")
        self.otostart.setChecked(startup_command is not None)
        f.addRow(self.otostart)
        import sys
        self.startup_status = label(
            "Açılış kaydı eski paket yolunu gösteriyor; Kaydet ile güncelleyin."
            if startup_command and getattr(sys, "frozen", False)
            and os.path.normcase(sys.executable) not in os.path.normcase(startup_command)
            else "", "ikincil")
        f.addRow(self.startup_status)
        self.tepsiye = QCheckBox("Kapatınca tepsiye küçült")
        self.tepsiye.setChecked(migrate.get_setting(self.con, "tepsiye", "1") == "1")
        f.addRow(self.tepsiye)
        self.kilit_sure = QComboBox()
        self.kilit_sure.addItems(["kapalı", "5", "15", "30"])
        cur = migrate.get_setting(self.con, "kilit_suresi", "15")
        self.kilit_sure.setCurrentText(cur if cur in ("5", "15", "30") else "kapalı")
        security, security_layout = card()
        security_layout.addWidget(label("Kasa güvenliği", "subheading"))
        security_layout.addWidget(label("Şifrenizi ve otomatik kilitlenmeyi yönetin.", "ikincil"))
        security_layout.addWidget(label("Hareketsizlikte kilitle • dakika", "ikincil"))
        security_layout.addWidget(self.kilit_sure)
        kay = QPushButton("Kaydet")
        kay.setProperty("birincil", True)
        kay.clicked.connect(self._ayar_kaydet)
        general_layout.addStretch()
        general_layout.addWidget(kay)
        sif = QPushButton("Parolayı değiştir")
        sif.clicked.connect(self._parola_degistir)
        security_layout.addWidget(sif)
        forget = QPushButton("Hatırlanan girişi kaldır")
        forget.clicked.connect(self._forget_login)
        security_layout.addWidget(forget)
        security_layout.addWidget(label("Beni hatırla açıkken otomatik kilit kapanır. Elle kilitleme her zaman şifre ister.", "ikincil"))
        security_layout.addWidget(label("Şifre değişirken mevcut şifrenizi doğrulamanız gerekir.", "ikincil"))
        security_layout.addStretch()
        self.surum_bilgi = QLabel(f"Evrakçı {__version__}")
        self.surum_bilgi.setProperty("ikincil", True)
        security_layout.addWidget(self.surum_bilgi)
        row.addWidget(general, 1)
        row.addWidget(security, 1)
        outer.addLayout(row)
        outer.addStretch()
        self.yigin.addWidget(w)

    def _ekran_ai(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(label("AI modeli • yalnız açık gönderim", "ikincil"))
        self.ai_model = QComboBox()
        self.ai_model.setAccessibleName("AI modeli")
        for model_id, caption in ai.MODELS.items():
            self.ai_model.addItem(caption, model_id)
        selected = migrate.get_setting(self.con, "ai_model", ai.MODEL)
        self.ai_model.setCurrentIndex(max(0, self.ai_model.findData(selected)))
        layout.addWidget(self.ai_model)
        key_row = QHBoxLayout()
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("API anahtarı kayıtlı" if migrate.get_setting(self.con, "gemini_api_key") else "Gemini API anahtarı")
        self.ai_key_input.setAccessibleName("Gemini API anahtarı")
        key_row.addWidget(self.ai_key_input, 1)
        key_save = QPushButton("Anahtarı kasaya kaydet")
        key_save.clicked.connect(self._ai_save_key)
        key_row.addWidget(key_save)
        key_remove = QPushButton("Kaldır")
        key_remove.clicked.connect(self._ai_remove_key)
        key_row.addWidget(key_remove)
        layout.addLayout(key_row)
        layout.addWidget(label("Anahtar şifreli kasada saklanır. Alıntılar yalnız Gönder'e bastığınızda Google'a iletilir.", "ikincil"))

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
        layout.addLayout(mode_row)
        controls = QHBoxLayout()
        prepare = QPushButton("Alıntıları hazırla")
        prepare.clicked.connect(self._ai_prepare)
        controls.addWidget(prepare)
        self.ai_send = QPushButton("Gösterilen alıntıları gönder")
        self.ai_send.setProperty("birincil", True)
        self.ai_send.setEnabled(False)
        self.ai_send.clicked.connect(self._ai_send)
        controls.addWidget(self.ai_send)
        controls.addStretch()
        layout.addLayout(controls)
        self.ai_status = label("Önce soru sorun veya bir belge seçin; alıntıları kontrol edin.", "ikincil")
        self.ai_status.setWordWrap(True)
        layout.addWidget(self.ai_status)
        self.ai_preview_box = QPlainTextEdit()
        self.ai_preview_box.setReadOnly(True)
        self.ai_preview_box.setPlaceholderText("Buluta gönderilecek metin burada görünecek.")
        layout.addWidget(self.ai_preview_box, 2)
        self.ai_answer = QPlainTextEdit()
        self.ai_answer.setReadOnly(True)
        self.ai_answer.setPlaceholderText("Yanıt burada görünecek.")
        layout.addWidget(self.ai_answer, 1)
        self.ai_answer.hide()
        self.ai_sources = QListWidget()
        self.ai_sources.setMaximumHeight(90)
        self.ai_sources.itemClicked.connect(self._ai_open_source)
        layout.addWidget(self.ai_sources)
        self.ai_sources.hide()
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
        self.yigin.addWidget(w)

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
        if self.con is None:
            return
        documents = ai.list_documents(self.con)
        current = [(self.ai_document.itemData(i), self.ai_document.itemText(i))
                   for i in range(self.ai_document.count())]
        wanted = [(fid, name + " • " + path) for fid, name, path in documents]
        if current == wanted:
            return
        old_id = self.ai_document.currentData()
        self.ai_document.clear()
        for fid, caption in wanted:
            self.ai_document.addItem(caption, fid)
        if old_id is not None:
            self.ai_document.setCurrentIndex(max(0, self.ai_document.findData(old_id)))

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
        try:
            if self.ai_mode.currentData() == "summary":
                file_id = self.ai_document.currentData()
                if file_id is None:
                    raise ValueError("Özetlenecek içerikli belge yok. Önce tarama yapın.")
                preview = ai.prepare_summary(self.con, file_id)
            else:
                preview = ai.prepare_question(self.con, self.ai_question.text())
        except Exception as error:
            self.ai_status.setText(str(error))
            return
        self.ai_preview = preview
        self.ai_preview_box.setPlainText(ai.preview_text(preview))
        self.ai_send.setEnabled(True)
        self.ai_status.setText(f"{len(preview.sources)} alıntı hazır. Göndermeden önce metni inceleyin."
                               + (" Belgenin yalnız gösterilen bölümü özetlenecek." if preview.truncated else ""))

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
            self.nav.setCurrentRow(0)
            self.onizleme.goster(self.con, source)

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
        self.ai_key_input.clear()
        self.ai_document.clear()
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
        migrate.set_setting(self.con, "tepsiye", "1" if self.tepsiye.isChecked() else "0")
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
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy():
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
        if i == len(EKRANLAR):
            self.kilitle()
            self.nav.blockSignals(True)
            self.nav.setCurrentRow(0)
            self.nav.blockSignals(False)
            return
        self.yigin.setCurrentIndex(i)
        if hasattr(self, "search_bar"):
            self.search_bar.setVisible(i == 0)
        if hasattr(self, "onizleme"):
            self.onizleme.setVisible(i == 0)
        if i == 2 and self.isci_thread is not None:
            self._scan_show()
        if i == 3:
            self._gecmis_tazele()
        elif i == 4:
            self._yedek_tazele()
        elif i == 1:
            self._kok_tazele()
        elif i == 6:
            self._ai_refresh_docs()

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
        self.durum.showMessage(f"{self.tema_sec.currentText()} uygulandı.")

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
        self.sonuc_model.clear()
        self.gecmis_model.clear()
        self.kok_model.clear()
        self.yedek_model.clear()
        self.onizleme.temizle()
        self.scan_timer.stop()
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
        if self.isci:
            self.isci.durdur()
        if self.con is not None:
            self.con.close()
            self.con = None
        self._sifre = ""
        self._unlock_dialog = ParolaDialog(self, verify=self._unlock, allow_remember=False)
        self._unlock_dialog.accepted.connect(self._unlocked)
        self._unlock_dialog.rejected.connect(self._cikis)
        self._lock_poll = QTimer(self)
        self._lock_poll.timeout.connect(self._kilit_hazir)
        self._lock_poll.start(100)
        self._kilit_hazir()

    def _kilit_hazir(self):
        if self.isci_thread is None and self._search_thread is None and not self.onizleme.busy():
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
        self._unlock_dialog.old.clear()
        self._son_hareket = dt.datetime.now()
        self._kok_tazele()
        self._yedek_tazele()
        self._scan_history_refresh()
        self._scope_changed()
        self.ai_key_input.setPlaceholderText("API anahtarı kayıtlı" if migrate.get_setting(self.con, "gemini_api_key") else "Gemini API anahtarı")
        self.show()
        self._durum_yaz()
        self._scan_state("idle")
        self._zamanlayici_kontrol()

    def _cikis(self):
        diagnostics.record("exit")
        self._exiting = True
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
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy():
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
        login = ParolaDialog(verify=verify)
        app._login = login
        if login.exec() != QDialog.Accepted:
            diagnostics.record("login_cancelled")
            return 1
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
    opening = None
    if os.path.getsize(args.kasa) > 100_000_000:
        opening = QDialog()
        opening.setWindowTitle("Evrakçı • Açılıyor")
        opening.setWindowIcon(theme.app_icon())
        opening.setMinimumWidth(380)
        opening_layout = QVBoxLayout(opening)
        opening_layout.addWidget(label("Şifreli kasa açılıyor…", "subheading"))
        opening_layout.addWidget(label("Büyük arşiv hazırlanırken lütfen bekleyin.", "ikincil"))
        opening.show()
        app._startup_dialog = opening
        app.processEvents()
    try:
        pen = AnaPencere(args.kasa, sifre)
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
