"""Evrakci masaustu: Varyant A (sol gezinme + sonuc + sag onizleme). Plan bolum 19-20.

Kilitlenmeden calisir: tarama QThread'de, arama debounce'lu, onizleme tembel.
Kilitte: baglantilar kapanir, model/onislem/gecmis temizlenir (SEC-03).
"""
from __future__ import annotations

import datetime as dt
import os
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt, QAbstractNativeEventFilter
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListView,
                               QListWidget, QMainWindow, QMessageBox, QPushButton,
                               QSplitter, QStackedWidget, QStatusBar,
                               QSystemTrayIcon, QMenu, QVBoxLayout, QWidget,
                               QProgressBar, QSpinBox)

from . import backup as backup_mod
from . import coordinator, exclusions, history as hist_mod
from . import migrate, rank, sched, theme, vault
from .preview import Onizleme
from .version import __version__
from .vocab import ensure_v5, rebuild_vocab
from .auth import ParolaDialog

EKRANLAR = ["Ara", "Kaynaklar", "Tarama", "Geçmiş", "Yedekler", "Ayarlar"]


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

    def __init__(self, kasa_yolu, sifre, kokler):
        super().__init__()
        self.kasa_yolu = kasa_yolu
        self._sifre = sifre
        self.kokler = kokler
        self._dur = threading.Event()

    def durdur(self):
        self._dur.set()

    def kos(self):
        try:
            from . import schema as schema_mod
            from .migrate import ensure_v7
            con = vault.open_vault(self.kasa_yolu, self._sifre)
            try:
                schema_mod.ensure_schema(con)
                ensure_v5(con)
                ensure_v7(con)
                toplam = {}
                all_complete = True
                for kok in self.kokler:
                    if self._dur.is_set():
                        break
                    st = coordinator.run_scan(con, self.kasa_yolu, kok,
                                              stop=self._dur.is_set, guarded=True)
                    all_complete = all_complete and bool(st.get("complete"))
                    for k, v in st.items():
                        if isinstance(v, (int, float)):
                            toplam[k] = toplam.get(k, 0) + v
                    toplam["result"] = st.get("result", "")
                toplam["complete"] = all_complete and not self._dur.is_set()
                if not toplam["complete"] and toplam.get("result") == "complete":
                    toplam["result"] = "partial"
                rebuild_vocab(con)
                self.bitti.emit(dict(toplam))
            finally:
                con.close()
        except Exception as e:  # noqa: BLE001 - worker hatasi arayuze tasinir
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
        self.setMinimumSize(1100, 700)

        self._kasa_ac()
        self._arayuz()
        self._tepsi()
        try:
            if QApplication.platformName() == "windows":
                self._oturum_filtresi = OturumKilitFiltresi(self.kilitle)
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
        theme.apply(QApplication.instance(), self.tema_sec.currentText())

    # -- kurulum --
    def _kasa_ac(self):
        from . import schema as schema_mod
        from .migrate import ensure_v7
        self.con = vault.open_vault(self.kasa_yolu, self._sifre)
        current_fts = self.con.execute("SELECT sql FROM sqlite_master WHERE name='docs_fts'").fetchone()
        if current_fts and "remove_diacritics 0" not in current_fts[0]:
            try:
                backup_mod.create_backup(self.con, self.kasa_yolu, self._sifre,
                                         self._yedek_dizin(), manual=True)
            except Exception:
                self.con.close()
                self.con = None
                raise RuntimeError("Geçiş öncesi indeks yedeği alınamadı; mevcut kasa korunuyor.")
        schema_mod.ensure_schema(self.con)
        ensure_v5(self.con)
        ensure_v7(self.con)

    def _arayuz(self):
        kok = QWidget()
        kok.setObjectName("kok")
        self.setCentralWidget(kok)
        dis = QVBoxLayout(kok)
        dis.setContentsMargins(24, 20, 24, 16)
        dis.setSpacing(18)

        masthead = QHBoxLayout()
        brand = QLabel("Evrakçı")
        brand.setProperty("baslik", True)
        masthead.addWidget(brand)
        subtitle = QLabel("Yerel, şifreli belge arşiviniz")
        subtitle.setProperty("ikincil", True)
        masthead.addWidget(subtitle)
        masthead.addStretch(1)
        badge = QLabel("●  Bu bilgisayarda güvende")
        badge.setProperty("basari", True)
        masthead.addWidget(badge)
        dis.addLayout(masthead)

        ust = QHBoxLayout()
        self.arama_kutu = QLineEdit()
        self.arama_kutu.setObjectName("search")
        self.arama_kutu.setAccessibleName("Belge arama")
        self.arama_kutu.setPlaceholderText("Belge ara… (ör. Ankara Ayşe 2024 vergi levhası)")
        self.arama_kutu.setClearButtonEnabled(True)
        self.arama_kutu.returnPressed.connect(self._ara_simdi)
        ust.addWidget(self.arama_kutu, 1)
        self.tara_btn = QPushButton("Şimdi tara")
        self.tara_btn.setProperty("birincil", True)
        self.tara_btn.clicked.connect(self._tara_baslat)
        ust.addWidget(self.tara_btn)
        self.tema_sec = QComboBox()
        self.tema_sec.addItems(["sistem", "acik", "koyu"])
        self.tema_sec.setCurrentText(migrate.get_setting(self.con, "tema", "sistem"))
        self.tema_sec.currentTextChanged.connect(self._tema_degistir)
        ust.addWidget(self.tema_sec)
        dis.addLayout(ust)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._ara_simdi)
        self.arama_kutu.textChanged.connect(lambda _t: self._debounce.start())

        govde = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.addItems(EKRANLAR + ["Kasayı kilitle"])
        self.nav.setFixedWidth(190)
        self.nav.currentRowChanged.connect(self._ekran)
        govde.addWidget(self.nav)

        self.yigin = QStackedWidget()
        self._ekran_ara()
        self._ekran_kaynaklar()
        self._ekran_tarama()
        self._ekran_gecmis()
        self._ekran_yedekler()
        self._ekran_ayarlar()
        descriptions = ["Ad, içerik ve klasör bağlamıyla belgelerinizi bulun.",
                        "Taranacak klasörleri ve kapsam dışında kalan yolları yönetin.",
                        "Arşivinizi güncelleyin; güvenli noktada duraklatıp devam edin.",
                        "Önceki aramalarınıza tek tıkla dönün.",
                        "Şifreli indeksinizi koruyun ve doğrulanmış yedeklere dönün.",
                        "Çalışma tercihleri ve kasa güvenliği."]
        for i, name in enumerate(EKRANLAR):
            layout = self.yigin.widget(i).layout()
            layout.setContentsMargins(22, 20, 22, 20)
            layout.setSpacing(14)
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
        self.onizleme.setMinimumWidth(340)
        govde.addWidget(self.onizleme)
        govde.setChildrenCollapsible(False)
        govde.setSizes([150, 520, 430])
        dis.addWidget(govde, 1)
        self.nav.setCurrentRow(0)

        self.durum = QStatusBar()
        self.setStatusBar(self.durum)
        self._durum_yaz()

        menu = self.menuBar().addMenu("Menü")
        for ad, fn in (("Yedek oluştur", self._yedek_al),
                       ("Kasayı kilitle", self.kilitle),
                       ("Hakkında", self._hakkinda),
                       ("Çıkış", self._cikis)):
            a = QAction(ad, self)
            a.triggered.connect(fn)
            menu.addAction(a)

    def _kisaltmalar(self):
        self.hareketsizlik = QTimer(self)
        self.hareketsizlik.timeout.connect(self._hareket_kontrol)
        self.hareketsizlik.start(60_000)
        self._son_hareket = dt.datetime.now()
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, _o, ev):
        from PySide6.QtCore import QEvent
        if ev.type() in (QEvent.MouseMove, QEvent.KeyPress, QEvent.MouseButtonPress):
            self._son_hareket = dt.datetime.now()
        return super().eventFilter(_o, ev)

    def _hareket_kontrol(self):
        try:
            dk = int(migrate.get_setting(self.con, "kilit_suresi", "0"))
        except Exception:
            return
        if not self._locked and dk > 0 and (dt.datetime.now() - self._son_hareket).total_seconds() > dk * 60:
            self.kilitle()

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
        self.sirket_filtre.setPlaceholderText("Klasör içerir (ör. Ankara)")
        for x in (self.yil_filtre, self.tur_filtre, self.sirket_filtre):
            fil.addWidget(x)
        fil.addStretch(1)
        self.yil_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        self.tur_filtre.currentTextChanged.connect(lambda _t: self._ara_simdi())
        self.sirket_filtre.textChanged.connect(lambda _t: self._ara_simdi())
        k.addLayout(fil)
        self.aktif_filtre = QLabel("")
        self.aktif_filtre.setProperty("ikincil", True)
        k.addWidget(self.aktif_filtre)
        self.sonuc_model = QStandardItemModel()
        self.sonuc_liste = QListView()
        self.sonuc_liste.setModel(self.sonuc_model)
        self.sonuc_liste.setSpacing(4)
        self.sonuc_liste.clicked.connect(self._sec)
        k.addWidget(self.sonuc_liste, 1)
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
        for r in res:
            from PySide6.QtGui import QTextDocument
            snippet = QTextDocument()
            snippet.setHtml(r.get("snippet", ""))
            item = QStandardItem(f"{r['name']}\n{r['label']} • {', '.join(r['why'])}\n"
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
        self.kok_liste.setModel(self.kok_model)
        k.addWidget(self.kok_liste, 1)
        satir = QHBoxLayout()
        ekle = QPushButton("Klasör ekle")
        ekle.clicked.connect(self._kok_ekle)
        kaldir = QPushButton("Kaldır")
        kaldir.clicked.connect(self._kok_kaldir)
        satir.addWidget(ekle)
        satir.addWidget(kaldir)
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
        self.kok_model.clear()
        try:
            rows = self.con.execute(
                "SELECT display_path, company_rule, enabled FROM roots ORDER BY display_path"
            ).fetchall()
        except Exception:
            rows = []
        for yol, kural, akt in rows:
            item = QStandardItem(f"{'[kapalı] ' if not akt else ''}{yol} ({kural})")
            item.setEditable(False)
            item.setData(yol)
            self.kok_model.appendRow(item)

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
        k = QVBoxLayout(w)
        self.tarama_bilgi = QLabel("Henüz tarama yapılmadı.")
        self.tarama_bilgi.setWordWrap(True)
        k.addWidget(self.tarama_bilgi)
        self.tarama_bar = QProgressBar()
        self.tarama_bar.setRange(0, 0)
        self.tarama_bar.hide()
        k.addWidget(self.tarama_bar)
        satir = QHBoxLayout()
        self.duraklat_btn = QPushButton("Duraklat")
        self.duraklat_btn.clicked.connect(self._tara_duraklat)
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.clicked.connect(self._tara_iptal)
        self.iptal_btn.setEnabled(False)
        satir.addWidget(self.duraklat_btn)
        satir.addWidget(self.iptal_btn)
        satir.addStretch(1)
        k.addLayout(satir)
        k.addStretch(1)
        self.yigin.addWidget(w)
        self.isci = None
        self.isci_thread = None

    def _kokler(self):
        try:
            return [r[0] for r in self.con.execute(
                "SELECT display_path FROM roots WHERE enabled=1 ORDER BY display_path").fetchall()]
        except Exception:
            return []

    def _tara_baslat(self):
        if self._locked or self.con is None:
            return
        kokler = self._kokler()
        if not kokler:
            QMessageBox.information(self, "Tarama", "Önce Kaynaklar ekranından klasör ekleyin.")
            self.nav.setCurrentRow(1)
            return
        if self.isci_thread is not None:
            self.nav.setCurrentRow(2)
            return
        self.isci_thread = QThread(self)
        self.isci = TaramaIsci(self.kasa_yolu, self._sifre, kokler)
        self.isci.moveToThread(self.isci_thread)
        self.isci_thread.started.connect(self.isci.kos)
        self.isci.bitti.connect(self._tara_bitti)
        self.isci.hata.connect(self._tara_hata)
        self.isci.bitti.connect(self.isci_thread.quit)
        self.isci.hata.connect(self.isci_thread.quit)
        self.isci_thread.finished.connect(self._tara_temizle)
        self.isci_thread.start()
        self.tarama_bar.show()
        self.duraklat_btn.setEnabled(True)
        self.iptal_btn.setEnabled(True)
        self.tara_btn.setEnabled(False)
        self.tarama_bilgi.setText(f"Tarama sürüyor: {len(kokler)} kök…")
        self.nav.setCurrentRow(2)

    def _tara_duraklat(self):
        if self.isci:
            self.isci.durdur()
            self.tarama_bilgi.setText("Duraklatılıyor… güvenli noktada duracak.")

    def _tara_iptal(self):
        self._tara_duraklat()

    def _tara_bitti(self, st):
        if self.con is None or self._locked:
            return
        self.tarama_bar.hide()
        self.tarama_bilgi.setText(
            f"Sonuç: {st.get('result','')} • bulunan {st.get('found',0)}, "
            f"işlenen {st.get('done',0)}, OCR {st.get('ocr_done',0)}, "
            f"kopya-hash {st.get('hashed',0)}, eksik {st.get('missing',0)}")
        migrate.set_setting(self.con, "son_tarama", dt.datetime.now().isoformat(timespec="seconds"))
        if st.get("complete") or st.get("result") == "complete":
            migrate.set_setting(self.con, "son_slot", dt.datetime.now().isoformat(timespec="seconds"))
        self._durum_yaz()

    def _tara_hata(self, msg):
        QMessageBox.warning(self, "Tarama", msg)

    def _tara_temizle(self):
        thread = self.isci_thread
        self.isci = None
        self.isci_thread = None
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn.setEnabled(False)
        self.tara_btn.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    # -- gecmis --
    def _ekran_gecmis(self):
        w = QWidget()
        k = QVBoxLayout(w)
        self.gecmis_model = QStandardItemModel()
        self.gecmis_liste = QListView()
        self.gecmis_liste.setModel(self.gecmis_model)
        self.gecmis_liste.doubleClicked.connect(self._gecmis_kullan)
        k.addWidget(self.gecmis_liste, 1)
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
            item = QStandardItem(f"{q}" + (f"  [{f}]" if f else ""))
            item.setEditable(False)
            item.setData(qid)
            item.setData((q, f), Qt.UserRole + 1)
            self.gecmis_model.appendRow(item)

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
        self.yedek_liste.setModel(self.yedek_model)
        k.addWidget(self.yedek_liste, 1)
        satir = QHBoxLayout()
        yeni = QPushButton("Yedek oluştur")
        yeni.clicked.connect(self._yedek_al)
        geri = QPushButton("Geri yükle")
        geri.clicked.connect(self._geri_yukle)
        satir.addWidget(yeni)
        satir.addWidget(geri)
        satir.addStretch(1)
        k.addLayout(satir)
        self.yedek_bilgi = QLabel("Yedekler yerel Backups klasöründedir; kaynak belge içermez.")
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
            item = QStandardItem(f"{os.path.basename(b['path'])} "
                                 f"({'manuel' if b['manuel'] else 'otomatik'}, "
                                 f"{b['boyut'] // 1024} KB)")
            item.setEditable(False)
            item.setData(b["path"])
            self.yedek_model.appendRow(item)

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
        f = QFormLayout(w)
        self.saat = QSpinBox()
        self.saat.setRange(0, 23)
        self.dakika = QSpinBox()
        self.dakika.setRange(0, 59)
        try:
            self.saat.setValue(int(migrate.get_setting(self.con, "saat", "12")))
            self.dakika.setValue(int(migrate.get_setting(self.con, "dakika", "30")))
        except ValueError:
            pass
        hs = QHBoxLayout()
        hs.addWidget(self.saat)
        hs.addWidget(QLabel(":"))
        hs.addWidget(self.dakika)
        f.addRow("Günlük tarama saati:", hs)
        self.gecikme = QCheckBox("Cihaz gecikmesi (NAS yük dağılımı, ~10 dk)")
        self.gecikme.setChecked(migrate.get_setting(self.con, "gecikme", "1") == "1")
        f.addRow(self.gecikme)
        self.otostart = QCheckBox("Windows açılışında başlat")
        self.otostart.setChecked(sched.autostart_get("Evrakci") is not None)
        f.addRow(self.otostart)
        self.tepsiye = QCheckBox("Kapatınca tepsiye küçült")
        self.tepsiye.setChecked(migrate.get_setting(self.con, "tepsiye", "1") == "1")
        f.addRow(self.tepsiye)
        self.kilit_sure = QComboBox()
        self.kilit_sure.addItems(["kapalı", "5", "15", "30"])
        cur = migrate.get_setting(self.con, "kilit_suresi", "15")
        self.kilit_sure.setCurrentText(cur if cur in ("5", "15", "30") else "kapalı")
        f.addRow("Hareketsizlik kilidi (dk):", self.kilit_sure)
        kay = QPushButton("Kaydet")
        kay.clicked.connect(self._ayar_kaydet)
        f.addRow(kay)
        sif = QPushButton("Parolayı değiştir")
        sif.clicked.connect(self._parola_degistir)
        f.addRow(sif)
        self.surum_bilgi = QLabel(f"Evrakçı {__version__} • şema v7")
        self.surum_bilgi.setProperty("ikincil", True)
        f.addRow(self.surum_bilgi)
        self.yigin.addWidget(w)

    def _ayar_kaydet(self):
        migrate.set_setting(self.con, "saat", str(self.saat.value()))
        migrate.set_setting(self.con, "dakika", str(self.dakika.value()))
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
            else:
                sched.autostart_clear("Evrakci")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Otomatik başlatma", f"Yazılamadı: {e}")
        QMessageBox.information(self, "Ayarlar", "Kaydedildi.")

    def _exclusive_ready(self):
        if self.con is None:
            return False
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy():
            QMessageBox.information(self, "İşlem sürüyor", "Devam eden tarama, arama veya önizlemenin bitmesini bekleyin. Taramayı duraklatabilirsiniz.")
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
        if hasattr(self, "onizleme"):
            self.onizleme.setVisible(i == 0)
        if i == 3:
            self._gecmis_tazele()
        elif i == 4:
            self._yedek_tazele()
        elif i == 1:
            self._kok_tazele()

    def _durum_yaz(self):
        try:
            kok_sayi = len(self._kokler())
        except Exception:
            kok_sayi = 0
        son = migrate.get_setting(self.con, "son_tarama", "—") if self.con else "—"
        self.durum.showMessage(f"Kasa açık • {kok_sayi} kök • Son tarama: {son}")

    def _tema_degistir(self, mode):
        resolved = theme.apply(QApplication.instance(), mode)
        try:
            migrate.set_setting(self.con, "tema", mode)
        except Exception:
            pass
        self.durum.showMessage(f"Tema: {mode} uygulandı ({resolved})")

    def _tepsi(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tepsi = None
            return
        self.tepsi = QSystemTrayIcon(self)
        self.tepsi.setIcon(theme.app_icon())
        self.tepsi.setToolTip("Evrakçı • Yerel belge arşivi")
        m = QMenu(self)
        self._tray_menu = m
        for ad, fn in (("Aç", self.show), ("Şimdi tara", self._tara_baslat),
                       ("Kasayı kilitle", self.kilitle), ("Çıkış", self._cikis)):
            a = QAction(ad, self)
            a.triggered.connect(fn)
            m.addAction(a)
        self.tepsi.setContextMenu(m)
        self.tepsi.show()

    def _hakkinda(self):
        QMessageBox.about(self, "Evrakçı",
                          f"Evrakçı {__version__}\nYerel şifreli belge bulma aracı.\n"
                          "Kaynak dosyalar değişmez; indeks bu bilgisayardadır.")

    def _zamanlayici_kontrol(self, ilk=False):
        if self._locked or self.con is None or self.isci_thread is not None:
            return
        if not self._kokler():
            return
        try:
            saat = int(migrate.get_setting(self.con, "saat", "12"))
            dakika = int(migrate.get_setting(self.con, "dakika", "30"))
            lag = sched.device_lag_min(os.environ.get("COMPUTERNAME", "pc")) \
                if migrate.get_setting(self.con, "gecikme", "1") == "1" else 0
            son_txt = migrate.get_setting(self.con, "son_slot", "")
            son = dt.datetime.fromisoformat(son_txt) if son_txt else None
            kos, neden = sched.should_run(dt.datetime.now(), son, saat, dakika, lag)
        except Exception:
            return
        if kos and not ilk:
            self._tara_baslat()
        elif kos and ilk:
            self.durum.showMessage(f"Planlı tarama kaçmış ({neden}); “Şimdi tara” hazır.")

    def kilitle(self):
        if self._locked:
            return
        self._locked = True
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
        self.haric_kutu.clear()
        self.aktif_filtre.clear()
        self.oneri.clear()
        if self.isci:
            self.isci.durdur()
        if self.con is not None:
            self.con.close()
            self.con = None
        self._sifre = ""
        self._unlock_dialog = ParolaDialog(self, verify=self._unlock)
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
        self._locked = False
        self._unlock_dialog.old.clear()
        self._son_hareket = dt.datetime.now()
        self._kok_tazele()
        self._yedek_tazele()
        self.show()
        self._durum_yaz()
        self._zamanlayici_kontrol()

    def _cikis(self):
        self._exiting = True
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
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, ev):
        try:
            tepsiye = self.con is not None and \
                migrate.get_setting(self.con, "tepsiye", "1") == "1"
        except Exception:
            tepsiye = False
        if not self._exiting and tepsiye and getattr(self, "tepsi", None) is not None:
            ev.ignore()
            self.hide()
            return
        if self.isci_thread is not None or self._search_thread is not None or self.onizleme.busy():
            ev.ignore()
            self._cikis()
            return
        try:
            if self.con is not None:
                vault.lock(self.con, os.path.dirname(os.path.abspath(self.kasa_yolu)))
        except Exception:
            pass
        self.con = None
        self._debounce.stop()
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


def main(kasa_yolu=None, sifre=None):
    import argparse
    ap = argparse.ArgumentParser(prog="evrakci")
    ap.add_argument("--kasa", default=kasa_yolu)
    ap.add_argument("--tray", action="store_true")
    args, _bilinmeyen = ap.parse_known_args()
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Evrakçı")
    app.setQuitOnLastWindowClosed(False)
    theme.apply(app, "sistem")
    if not args.kasa:
        from .cli import DEFAULT_VAULT
        args.kasa = DEFAULT_VAULT
    from PySide6.QtCore import QLockFile
    os.makedirs(os.path.dirname(os.path.abspath(args.kasa)), exist_ok=True)
    instance_lock = QLockFile(os.path.abspath(args.kasa) + ".app.lock")
    if not instance_lock.tryLock(0):
        QMessageBox.information(None, "Evrakçı açık", "Bu kasa başka bir Evrakçı penceresinde açık.")
        return 1
    setup = None
    if not os.path.exists(args.kasa):
        from .wizard import Sihirbaz
        setup = Sihirbaz()
        if setup.exec() != QDialog.Accepted:
            return 1
        sifre = setup.s1.text()
        os.makedirs(os.path.dirname(os.path.abspath(args.kasa)), exist_ok=True)
    if sifre is None:
        def verify(password):
            con = vault.open_vault(args.kasa, password)
            con.close()
        login = ParolaDialog(verify=verify)
        if login.exec() != QDialog.Accepted:
            return 1
        sifre = login.old.text()
        login.old.clear()
    try:
        pen = AnaPencere(args.kasa, sifre)
        if setup is not None:
            for root in setup.secim["kokler"]:
                pen.con.execute("INSERT OR IGNORE INTO roots(display_path, canonical_path, company_rule) VALUES (?,?,?)",
                                (root, os.path.normpath(root).lower(), setup.secim["sirket_kurali"]))
            pen.con.commit()
            pen.tema_sec.setCurrentText(setup.secim["tema"])
            setup.s1.clear()
            setup.s2.clear()
            setup.secim.pop("sifre", None)
            pen._kok_tazele()
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(None, "Kasa", f"Açılamadı: {e}")
        return 2
    sifre = "x" * 32
    if not args.tray:
        pen.show()
    if setup is not None:
        QTimer.singleShot(0, pen._tara_baslat)
    return app.exec()
