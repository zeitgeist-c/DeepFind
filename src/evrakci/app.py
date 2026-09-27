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

EKRANLAR = ["Ara", "Kaynaklar", "Tarama", "Geçmiş", "Yedekler", "Ayarlar"]


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
                for kok in self.kokler:
                    if self._dur.is_set():
                        break
                    st = coordinator.run_scan(con, self.kasa_yolu, kok,
                                              stop=self._dur.is_set)
                    for k, v in st.items():
                        if isinstance(v, (int, float)):
                            toplam[k] = toplam.get(k, 0) + v
                    toplam["result"] = st.get("result", "")
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
        self.setWindowTitle(f"Evrakçı {__version__}")
        self.setMinimumSize(1100, 700)

        self._kasa_ac()
        self._arayuz()
        self._tepsi()
        try:
            self._oturum_filtresi = OturumKilitFiltresi(self.kilitle)
            QApplication.instance().installNativeEventFilter(self._oturum_filtresi)
        except Exception:
            pass
        self._zamanlayici_kontrol(ilk=True)
        self._kisaltmalar()

    # -- kurulum --
    def _kasa_ac(self):
        from . import schema as schema_mod
        from .migrate import ensure_v7
        self.con = vault.open_vault(self.kasa_yolu, self._sifre)
        schema_mod.ensure_schema(self.con)
        ensure_v5(self.con)
        ensure_v7(self.con)

    def _arayuz(self):
        kok = QWidget()
        kok.setObjectName("kok")
        self.setCentralWidget(kok)
        dis = QVBoxLayout(kok)

        ust = QHBoxLayout()
        self.arama_kutu = QLineEdit()
        self.arama_kutu.setPlaceholderText("Belge ara… (ör. Ankara Ayşe 2024 vergi levhası)")
        self.arama_kutu.setClearButtonEnabled(True)
        self.arama_kutu.returnPressed.connect(self._ara_simdi)
        ust.addWidget(self.arama_kutu, 1)
        self.tara_btn = QPushButton("Şimdi tara")
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
        self.nav.addItems(EKRANLAR + ["Kasayı kilitle"])
        self.nav.setFixedWidth(150)
        self.nav.currentRowChanged.connect(self._ekran)
        govde.addWidget(self.nav)

        self.yigin = QStackedWidget()
        self._ekran_ara()
        self._ekran_kaynaklar()
        self._ekran_tarama()
        self._ekran_gecmis()
        self._ekran_yedekler()
        self._ekran_ayarlar()
        govde.addWidget(self.yigin)

        self.onizleme = Onizleme()
        govde.addWidget(self.onizleme)
        govde.setSizes([150, 520, 430])
        dis.addWidget(govde, 1)

        self.durum = QStatusBar()
        self.setStatusBar(self.durum)
        self._durum_yaz()

        menu = self.menuBar().addMenu("Menü")
        for ad, fn in (("Yedek oluştur", self._yedek_al),
                       ("Kasayı kilitle", self.kilitle),
                       ("Hakkında", self._hakkinda),
                       ("Çıkış", self.close)):
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
        if dk > 0 and (dt.datetime.now() - self._son_hareket).seconds > dk * 60:
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
        self.sonuc_liste.clicked.connect(self._sec)
        k.addWidget(self.sonuc_liste, 1)
        self.oneri = QLabel("")
        self.oneri.setProperty("ikincil", True)
        self.oneri.setWordWrap(True)
        k.addWidget(self.oneri)
        self.yigin.addWidget(w)

    def _ara_simdi(self):
        if self.con is None:
            return
        q = self.arama_kutu.text()
        if not q.strip():
            self.sonuc_model.clear()
            self.oneri.setText("Son aramalar Geçmiş ekranında; aramak için yazın.")
            return
        yil = self.yil_filtre.text().strip() or None
        tur = self.tur_filtre.currentText()
        tur = None if tur == "tümü" else tur
        try:
            out = rank.search_ranked(self.con, q, year=yil, ext=tur, limit=50)
        except Exception as e:  # noqa: BLE001
            self.oneri.setText(f"Arama hatası: {type(e).__name__}")
            return
        kokf = self.sirket_filtre.text().strip().lower()
        res = out["results"]
        if kokf:
            res = [r for r in res if kokf in r["path"].lower()]
        self.sonuclar = res
        self.sonuc_model.clear()
        for r in res:
            item = QStandardItem(f"{r['name']}\n{r['label']} • {', '.join(r['why'])}")
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
            hist_mod.save(self.con, q, f"yil={yil or ''};tur={tur or ''}")
        except Exception:
            pass

    def _sec(self, idx):
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
        idx = self.kok_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.kok_model.item(idx.row()).text().split(" (")[0].replace("[kapalı] ", "")
        self.con.execute("DELETE FROM roots WHERE display_path=?", (yol,))
        self.con.commit()
        self._kok_tazele()
        self._durum_yaz()

    def _haric_ekle(self):
        kural = self.haric_kutu.text().strip()
        if not kural:
            return
        n = exclusions.add(self.con, kural)
        c = exclusions.purge_rule(self.con, n)
        QMessageBox.information(self, "Hariç", f"Kural kaydedildi; {c} dosyanın içeriği temizlendi.")
        self.haric_kutu.clear()

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
        self.tarama_bar.hide()
        self.tarama_bilgi.setText(
            f"Sonuç: {st.get('result','')} • bulunan {st.get('found',0)}, "
            f"işlenen {st.get('done',0)}, OCR {st.get('ocr_done',0)}, "
            f"kopya-hash {st.get('hashed',0)}, eksik {st.get('missing',0)}")
        migrate.set_setting(self.con, "son_tarama", dt.datetime.now().isoformat(timespec="seconds"))
        if st.get("planli"):
            migrate.set_setting(self.con, "son_slot", dt.datetime.now().isoformat(timespec="seconds"))
        self._durum_yaz()

    def _tara_hata(self, msg):
        QMessageBox.warning(self, "Tarama", msg)

    def _tara_temizle(self):
        self.isci = None
        self.isci_thread = None
        self.duraklat_btn.setEnabled(False)
        self.iptal_btn.setEnabled(False)
        self.tara_btn.setEnabled(True)

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
            self.gecmis_model.appendRow(item)

    def _gecmis_kullan(self, idx):
        self.arama_kutu.setText(self.gecmis_model.item(idx.row()).text().split("  [")[0])
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
        try:
            y = backup_mod.create_backup(self.con, self.kasa_yolu, self._sifre,
                                         self._yedek_dizin(),
                                         forbid_under=self._kokler())
            QMessageBox.information(self, "Yedek", f"Oluşturuldu ve doğrulandı:\n{y}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Yedek", f"Başarısız: {e}")
        self._yedek_tazele()

    def _geri_yukle(self):
        idx = self.yedek_liste.currentIndex()
        if not idx.isValid():
            return
        yol = self.yedek_model.item(idx.row()).data()
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
                os.path.join(os.path.dirname(self.kasa_yolu), "staging"))
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
        cur = migrate.get_setting(self.con, "kilit_suresi", "0")
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
                sched.autostart_set("Evrakci", QApplication.applicationFilePath())
            else:
                sched.autostart_clear("Evrakci")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Otomatik başlatma", f"Yazılamadı: {e}")
        QMessageBox.information(self, "Ayarlar", "Kaydedildi.")

    def _parola_degistir(self):
        d = QDialog(self)
        d.setWindowTitle("Parolayı değiştir")
        fl = QFormLayout(d)
        e1, e2 = QLineEdit(), QLineEdit()
        e1.setEchoMode(QLineEdit.Password)
        e2.setEchoMode(QLineEdit.Password)
        fl.addRow("Eski parola:", e1)
        fl.addRow("Yeni parola (≥12):", e2)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        fl.addRow(bb)
        if d.exec() != QDialog.Accepted:
            return
        if e1.text() != self._sifre:
            QMessageBox.warning(self, "Parola", "Eski parola hatalı.")
            return
        if len(e2.text()) < 12:
            QMessageBox.warning(self, "Parola", "Yeni parola en az 12 karakter olmalı.")
            return
        self.con.close()
        self.con = None
        try:
            backup_mod.change_password(self.kasa_yolu, self._sifre, e2.text(),
                                       self._yedek_dizin())
            self._sifre = e2.text()
            QMessageBox.information(self, "Parola", "Değiştirildi (önce yedek alındı).")
        except Exception as ex:  # noqa: BLE001
            QMessageBox.critical(self, "Parola", f"Başarısız, eski kasa korunuyor: {ex}")
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
        m = QMenu()
        for ad, fn in (("Aç", self.show), ("Şimdi tara", self._tara_baslat),
                       ("Kasayı kilitle", self.kilitle), ("Çıkış", self.close)):
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
        if self.isci_thread is not None and self.isci:
            self.isci.durdur()
            self.isci_thread.quit()
            self.isci_thread.wait(5000)
            self.isci_thread = None
            self.isci = None
        self.sonuclar = []
        try:
            self.sonuc_model.clear()
        except Exception:
            pass
        try:
            self.onizleme.temizle()
            self._gecmis_tazele()
            self.gecmis_model.clear()
        except Exception:
            pass
        if self.con is not None:
            try:
                vault.lock(self.con, os.path.dirname(os.path.abspath(self.kasa_yolu)))
            except Exception:
                pass
            self.con = None
        self._sifre = "x" * 32
        self.hide()
        from PySide6.QtWidgets import QInputDialog
        pw, ok = QInputDialog.getText(None, "Evrakçı kilitli", "Kasa şifresi:",
                                      QLineEdit.Password)
        if ok and pw:
            try:
                self._sifre = pw
                self._kasa_ac()
                self.show()
                self._durum_yaz()
                self._zamanlayici_kontrol()
            except Exception:
                QMessageBox.warning(None, "Kasa", "Açılamadı (şifre/sürüm).")
                self.close()
        else:
            self.close()

    def closeEvent(self, ev):
        try:
            tepsiye = self.con is not None and \
                migrate.get_setting(self.con, "tepsiye", "1") == "1"
        except Exception:
            tepsiye = False
        if tepsiye and getattr(self, "tepsi", None) is not None:
            ev.ignore()
            self.hide()
            return
        try:
            if self.con is not None:
                vault.lock(self.con, os.path.dirname(os.path.abspath(self.kasa_yolu)))
        except Exception:
            pass
        self.con = None
        super().closeEvent(ev)


def main(kasa_yolu=None, sifre=None):
    import argparse
    ap = argparse.ArgumentParser(prog="evrakci")
    ap.add_argument("--kasa", default=kasa_yolu)
    ap.add_argument("--tray", action="store_true")
    args, _bilinmeyen = ap.parse_known_args()
    app = QApplication.instance() or QApplication([])
    if not args.kasa:
        from PySide6.QtWidgets import QFileDialog as FD
        args.kasa, _f = FD.getOpenFileName(None, "Kasa seç", "", "Kasa (*.db)")
        if not args.kasa:
            return 1
    if sifre is None:
        from PySide6.QtWidgets import QInputDialog as QI
        from PySide6.QtWidgets import QLineEdit as LE
        sifre, ok = QI.getText(None, "Evrakçı", "Kasa şifresi:", LE.Password)
        if not ok or not sifre:
            return 1
    theme.apply(app, "sistem")
    try:
        pen = AnaPencere(args.kasa, sifre)
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(None, "Kasa", f"Açılamadı: {e}")
        return 2
    sifre = "x" * 32
    if not args.tray:
        pen.show()
    return app.exec()
