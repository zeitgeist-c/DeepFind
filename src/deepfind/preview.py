"""Document preview: PDF page image, Excel data region, Word text/table.

M2 (REA pattern): zoom steps — "fit width", "fit page"
and percent steps (paperless `pdf-viewer` zoom steps); page thumbnail rail on the
left, lazily loaded (papermerge `PageList`); keyboard
navigation and -/+ steps (paperless document viewer).

Rules (plan section 20.3): never invent a box without a trusted bbox; never present
old snippets with a new image as if the same version when the source
changed; without access show the last indexed text and say there is no page image."""
from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import Qt, QEvent, QSize, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QProgressBar, QPushButton,
                               QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem,
                               QTextBrowser, QVBoxLayout, QWidget)

from . import thumbs
from .tasks import DatabaseTask, indexed_text
from .ui import EmptyState, label
from .theme import t

# (tag, data) — data is "width"/"page" or a percent multiplier (float)
KADEMELER = ((t("Genişliğe sığdır"), "genislik"), (t("Sayfaya sığdır"), "sayfa"),
             ("%50", 0.5), ("%75", 0.75), ("%100", 1.0),
             ("%125", 1.25), ("%150", 1.5), ("%200", 2.0))
RAY_ADIM = 12  # thumbnails produced per round on the page rail


class PreviewWorker(QThread):
    ready = Signal(dict)

    def __init__(self, kind, args, generation, expected, parent):
        super().__init__(parent)
        self.kind, self.args, self.generation, self.expected = kind, args, generation, expected
        self.stop = threading.Event()

    def run(self):
        from .workers import run_work
        try:
            # source operations including stat and file open stay off the UI.
            st = os.stat(self.args[0])
            changed = bool(self.expected and tuple(self.expected) != (st.st_size, st.st_mtime_ns))
            result = run_work(self.kind, self.args, stop=self.stop.is_set)
            message = {"generation": self.generation, "kind": self.kind,
                       "result": result, "changed": changed}
        except Exception as error:
            message = {"generation": self.generation, "error": type(error).__name__}
        if not self.stop.is_set():
            self.ready.emit(message)


class Onizleme(QWidget):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        self.setObjectName("preview")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._path = None
        self._index_view = False
        self._sayfa = 1
        self._toplam = 1
        self._orijinal = None  # olceklenmemis sayfa pixmap'i
        self._son_kind = None
        self._threads = []
        self._generation = 0
        self._expected = None
        self._fallback = ""
        # page rail state
        self._ray_loader = None
        self._ray_yuklenen = 0
        self._ray_toplam = 0
        self._ray_pixmaps = {}
        self._son_fit_kutusu = None
        k = QVBoxLayout(self)
        k.setContentsMargins(18, 18, 18, 16)
        k.setSpacing(9)
        k.addWidget(label(t("Belge ön izlemesi"), "eyebrow"))
        self.baslik = QLabel(t("Belge seçilmedi"))
        self.baslik.setProperty("subheading", True)
        self.baslik.setWordWrap(True)
        k.addWidget(self.baslik)
        self.bilgi = QLabel(t("Sonuçlardan bir belge seçerek içeriğini burada inceleyin."))
        self.bilgi.setProperty("ikincil", True)
        self.bilgi.setWordWrap(True)
        k.addWidget(self.bilgi)
        self.uyari = QLabel("")
        self.uyari.setProperty("uyari", True)
        self.uyari.setWordWrap(True)
        self.uyari.hide()
        k.addWidget(self.uyari)

        self.yukleme = QWidget()
        yukleme_duzeni = QVBoxLayout(self.yukleme)
        yukleme_duzeni.setContentsMargins(0, 10, 0, 10)
        yukleme_duzeni.setSpacing(8)
        self.yukleme_yazisi = QLabel(t("PDF açılıyor…"))
        self.yukleme_yazisi.setAccessibleName(t("Önizleme yükleme durumu"))
        self.yukleme_cubugu = QProgressBar()
        self.yukleme_cubugu.setRange(0, 0)
        self.yukleme_cubugu.setTextVisible(False)
        self.yukleme_cubugu.setAccessibleName(t("PDF önizlemesi hazırlanıyor"))
        yukleme_duzeni.addWidget(self.yukleme_yazisi)
        yukleme_duzeni.addWidget(self.yukleme_cubugu)
        self.yukleme.hide()
        k.addWidget(self.yukleme)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(8)
        self.once = QPushButton("<")
        self.once.setAccessibleName(t("Önceki sayfa"))
        self.once.setToolTip(t("Önceki sayfa (Sol ok)"))
        self.sonra = QPushButton(">")
        self.sonra.setAccessibleName("Sonraki sayfa")
        self.sonra.setToolTip(t("Sonraki sayfa (Sağ ok)"))
        self.sayfa_no = QSpinBox()
        self.sayfa_no.setFixedWidth(66)
        self.sayfa_no.setAccessibleName(t("Sayfa numarası"))
        self.sayfa_no.setMinimum(1)
        nav.addWidget(self.once)
        nav.addWidget(self.sayfa_no)
        nav.addWidget(self.sonra)
        nav.addStretch(1)
        self.kucult = QPushButton("−")
        self.kucult.setToolTip(t("Uzaklaştır (−)"))
        self.kucult.setAccessibleName(t("Uzaklaştır"))
        self.zoom_sec = QComboBox()
        self.zoom_sec.setAccessibleName(t("Yakınlaştırma"))
        self.zoom_sec.setToolTip(t("Yakınlaştırma kademesi"))
        for etiket, veri in KADEMELER:
            self.zoom_sec.addItem(etiket, veri)
        self.zoom_sec.setCurrentIndex(self.zoom_sec.findData("genislik"))
        self.zoom_sec.currentIndexChanged.connect(lambda _i: self._zoom_uygula())
        self.buyut = QPushButton("+")
        self.buyut.setToolTip(t("Yakınlaştır (+)"))
        self.buyut.setAccessibleName(t("Yakınlaştır"))
        nav.addWidget(self.kucult)
        nav.addWidget(self.zoom_sec)
        nav.addWidget(self.buyut)
        for b in (self.once, self.sonra, self.buyut, self.kucult):
            b.setProperty("dar", True)
            b.setFixedWidth(36)
        self.once.clicked.connect(lambda: self._git(self._sayfa - 1))
        self.sonra.clicked.connect(lambda: self._git(self._sayfa + 1))
        self.sayfa_no.valueChanged.connect(lambda v: self._git(v))
        self.buyut.clicked.connect(lambda: self._zoom_adim(1))
        self.kucult.clicked.connect(lambda: self._zoom_adim(-1))
        self.pdf_nav = QWidget()
        self.pdf_nav.setLayout(nav)
        k.addWidget(self.pdf_nav)

        self.goruntu = QLabel()
        self.goruntu.setAlignment(Qt.AlignCenter)
        self.goruntu.hide()
        self.canvas = QScrollArea()
        self.canvas.setObjectName("paperCanvas")
        self.canvas.setWidget(self.goruntu)
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setFrameShape(QScrollArea.NoFrame)
        self.canvas.hide()
        self.canvas.viewport().installEventFilter(self)  # fit refresh

        # Page rail + page canvas side by side (rail visible only for PDFs).
        self.ray = QListWidget()
        self.ray.setObjectName("pageRail")
        self.ray.setFixedWidth(96)
        self.ray.setIconSize(QSize(58, 74))
        self.ray.setSpacing(2)
        self.ray.setUniformItemSizes(True)
        self.ray.setAccessibleName(t("Sayfa küçük resimleri"))
        self.ray.setToolTip(t("Sayfaya gitmek için küçük resme tıklayın"))
        self.ray.hide()
        self.ray.itemClicked.connect(self._ray_secildi)
        self.ray.verticalScrollBar().valueChanged.connect(self._ray_kaydirma)
        self.govde = QWidget()
        govde_duzeni = QHBoxLayout(self.govde)
        govde_duzeni.setContentsMargins(0, 0, 0, 0)
        govde_duzeni.setSpacing(10)
        govde_duzeni.addWidget(self.ray)
        govde_duzeni.addWidget(self.canvas, 1)
        k.addWidget(self.govde, 1)

        self.tablo = QTableWidget()
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.hide()
        k.addWidget(self.tablo, 1)
        self.metin = QTextBrowser()
        k.addWidget(self.metin, 1)
        self.empty = EmptyState(t("İçeriğe yakından bakın"), t("Bir arama sonucunu seçtiğinizde\nbelgenin önizlemesi burada açılır."), "document")
        k.addWidget(self.empty, 1)
        self.index_button = QPushButton(t('İndeks metnini göster'))
        self.index_button.setProperty("kucuk", True)
        self.index_button.setToolTip(t("Sayfa görüntüsü ile OCR/indeks metni arasında geçiş yapın"))
        self.index_button.clicked.connect(self._show_index)
        k.addWidget(self.index_button)
        self.more_button = QPushButton(t('Sonraki bölümleri yükle'))
        self.more_button.setProperty("kucuk", True)
        self.more_button.clicked.connect(self._load_more)
        k.addWidget(self.more_button)

        # Single re-render when the window size changes in fit modes.
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(160)
        self._fit_timer.timeout.connect(lambda: self._git(self._sayfa))
        self.temizle()

    def yenile(self):
        """Refresh the empty-state icon on theme change."""
        if hasattr(self, "empty"):
            self.empty.yenile()

    # -- dis API --
    def goster(self, con, sonuc: dict, password=None):
        """sonuc: rank.search_semantic kaydi (path, name, ext, label, page, snippet, why...)."""
        path = sonuc["path"]
        self.temizle()
        self.empty.hide()
        self._path = path
        self.baslik.setText(sonuc["name"])
        self.bilgi.setText(f"{sonuc.get('ext', '').lstrip('.').upper()} • {sonuc.get('label','')}")
        self.uyari.hide()
        self._dbpath = con.execute('PRAGMA database_list').fetchone()[2]
        self._password = password
        self._offset=0
        self._result=sonuc
        if password is not None:
            self.metin.setPlainText('İndeks içeriği yükleniyor…'); self.metin.show()
            self._load_more()
            return
        self._expected = con.execute("SELECT size,mtime_ns FROM files WHERE path=?", (path,)).fetchone()
        ext = (sonuc.get("ext") or "").lower()
        if ext == ".pdf":
            # On a large vault the segments query can lock the UI. A search summary is ready.
            self._fallback = sonuc.get("snippet") or ""
            self._pdf(path, sonuc.get("page") or 1)
        elif ext in (".xlsx", ".xls"):
            rows = con.execute("SELECT label,raw_text FROM segments WHERE file_id="
                               "(SELECT file_id FROM files WHERE path=?) ORDER BY seg_id LIMIT 60", (path,)).fetchall()
            self._fallback = "\n\n".join(f"[{label}]\n{text}" for label, text in rows)
            self._start("excel", (path, sonuc.get("label", "")))
        else:
            self._metin_goster(con, path)

    def temizle(self):
        self._generation += 1
        self._index_view = False
        for thread in self._threads:
            thread.stop.set()
        self._ray_durdur()
        self._fallback = ""
        self._path = None
        self._password = None
        self._offset = 0
        if hasattr(self,'more_button'): self.more_button.hide()
        self._orijinal = None
        self._son_kind = None
        self._ray_yuklenen = 0
        self._ray_toplam = 0
        self._ray_pixmaps = {}
        self._son_fit_kutusu = None
        if hasattr(self, "ray"):
            self.ray.clear()
            self.ray.hide()
        if hasattr(self, "_fit_timer"):
            self._fit_timer.stop()
        self.goruntu.clear()
        self.tablo.clear()
        self.tablo.setRowCount(0)
        self.tablo.setColumnCount(0)
        self.uyari.clear()
        self.uyari.hide()
        self.yukleme.hide()
        self.pdf_nav.hide()
        self._expected = None
        self.baslik.setText(t("Önizleme"))
        self.bilgi.setText("")
        self.metin.clear()
        self.goruntu.hide()
        self.canvas.hide()
        self.tablo.hide()
        self.metin.hide()
        self.empty.show()

    def busy(self):
        return bool(self._threads)

    def closeEvent(self, ev):
        """Finish the running render worker threads as the window closes.

Qt kills the process when a running QThread object is destroyed; this guard
is required when the viewer is used standalone (e.g. test/tool)."""
        self.temizle()
        deadline = time.monotonic() + 3
        for thread in list(self._threads):
            kalan = max(0.0, deadline - time.monotonic())
            thread.wait(int(kalan * 1000))
        super().closeEvent(ev)

    # -- klavye --
    def keyPressEvent(self, ev):
        if self._path and self._path.lower().endswith(".pdf"):
            tus = ev.key()
            if tus in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown):
                self._git(self._sayfa + 1); ev.accept(); return
            if tus in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp):
                self._git(self._sayfa - 1); ev.accept(); return
            if tus in (Qt.Key_Plus, Qt.Key_Equal):
                self._zoom_adim(1); ev.accept(); return
            if tus == Qt.Key_Minus:
                self._zoom_adim(-1); ev.accept(); return
            if tus == Qt.Key_0:
                self._zoom_ayarla(1.0); ev.accept(); return
        super().keyPressEvent(ev)

    # -- zoom --
    def _zoom_verisi(self):
        return self.zoom_sec.currentData()

    def _zoom_uygula(self):
        self._yerlestir()
        if self._path and self._path.lower().endswith(".pdf"):
            self._git(self._sayfa)

    def _zoom_ayarla(self, veri):
        i = self.zoom_sec.findData(veri)
        if i >= 0:
            self.zoom_sec.setCurrentIndex(i)  # applies the change signal
        else:
            self._zoom_uygula()

    def _zoom_adim(self, yon):
        veri = self._zoom_verisi()
        yuzdeler = [d for _e, d in KADEMELER if isinstance(d, float)]
        if veri not in yuzdeler:
            self._zoom_ayarla(1.0)
            return
        i = max(0, min(len(yuzdeler) - 1, yuzdeler.index(veri) + yon))
        self._zoom_ayarla(yuzdeler[i])

    def _fit_kutusu(self):
        """(max width, max height) px for fit modes."""
        veri = self._zoom_verisi()
        if veri not in ("genislik", "sayfa"):
            return None
        ölçü = self.canvas.viewport().size()
        genislik = max(120, (ölçü.width() - 18) if ölçü.width() >= 240 else 720)
        yukseklik = None
        if veri == "sayfa":
            yukseklik = max(120, (ölçü.height() - 18) if ölçü.height() >= 240 else 900)
        return (genislik, yukseklik)

    # -- inner --
    def _durum_kontrol(self, con, path):
        try:
            st = os.stat(path)
            row = con.execute("SELECT size, mtime_ns FROM files WHERE path=?",
                              (path,)).fetchone()
            if row and (row[0] != st.st_size or row[1] != st.st_mtime_ns):
                self.uyari.setText(t("Kaynak değişti; yeniden indeksleme bekliyor. ") +
                                   t("Görünen alıntı eski sürüme ait olabilir."))
                self.uyari.show()
        except OSError:
            self.uyari.setText(t("Kaynak erişilemiyor; son indeks metni gösteriliyor."))
            self.uyari.show()

    def _pdf(self, path, sayfa):
        self.tablo.hide()
        self.metin.hide()
        self.goruntu.show()
        self.pdf_nav.show()
        self._git(max(1, sayfa))

    def _git(self, sayfa):
        if not self._path:
            return
        veri = self._zoom_verisi()
        zoom = float(veri) if isinstance(veri, float) else 1.0
        kutu = self._fit_kutusu()
        self._son_fit_kutusu = kutu
        self._start("pdf", (self._path, max(1, sayfa), zoom, kutu))

    def _fit_yenile(self):
        """Schedule a re-render only when the fit box really changed.

No render fires when the box is unchanged: a naive "render on every
size change" would loop, because render hides then shows the canvas."""
        if not (self._path and self._path.lower().endswith(".pdf") and self._orijinal is not None):
            return
        if self._zoom_verisi() not in ("genislik", "sayfa"):
            return
        if self._fit_kutusu() != self._son_fit_kutusu:
            self._fit_timer.start()

    def eventFilter(self, nesne, ev):
        if nesne is self.canvas.viewport() and ev.type() == QEvent.Resize:
            self._fit_yenile()
        return super().eventFilter(nesne, ev)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._son_kind == "image" and self._zoom_verisi() in ("genislik", "sayfa"):
            self._yerlestir()
        else:
            self._fit_yenile()

    def _yerlestir(self):
        if self._orijinal is None or self._orijinal.isNull():
            return
        if self._son_kind == "pdf":
            pm = self._orijinal  # the worker rendered at the requested density
        else:
            pm = self._olcekle(self._orijinal)
        self.goruntu.setPixmap(pm)
        self.goruntu.resize(pm.size())

    def _olcekle(self, pixmap):
        """Apply the zoom step client-side for non-PDF images."""
        veri = self._zoom_verisi()
        ölçü = self.canvas.viewport().size()
        if veri == "genislik":
            hedef = QSize(max(120, ölçü.width() - 18), 100000)
        elif veri == "sayfa":
            hedef = QSize(max(120, ölçü.width() - 18), max(120, ölçü.height() - 18))
        else:
            return pixmap.scaled(int(pixmap.width() * veri), int(pixmap.height() * veri),
                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap.scaled(hedef, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _start(self, kind, args):
        self._generation += 1
        for thread in self._threads:
            thread.stop.set()
        if kind == "pdf":
            self.canvas.hide()
            self.goruntu.hide()
            self.metin.hide()
            self.yukleme_yazisi.setText(t("PDF sayfası açılıyor…"))
            self.yukleme.show()
        else:
            self.metin.show()
            self.metin.setPlainText(t("Önizleme hazırlanıyor…"))
        worker = PreviewWorker(kind, args, self._generation, self._expected, self)
        self._threads.append(worker)
        worker.ready.connect(self._ready)
        worker.finished.connect(lambda: self._finished(worker))
        worker.start()

    def _finished(self, worker):
        if worker in self._threads:
            self._threads.remove(worker)
        worker.deleteLater()

    def _ready(self, message):
        if message["generation"] != self._generation or self._path is None:
            return
        self.yukleme.hide()
        if self._index_view: return
        if "error" in message:
            self.goruntu.hide()
            self.metin.show()
            self.metin.setPlainText(self._fallback or t("Önizleme metni bulunamadı."))
            if message.get("kind") == "pdf":
                durum = t("arama özeti gösteriliyor") if self._fallback else t("arama özeti de bulunamadı")
            else:
                durum = t("son indeks metni gösteriliyor") if self._fallback else t("indeks metni bulunamadı")
            self.uyari.setText(t("Kaynak önizlemesi açılamadı; {durum}.", durum=durum))
            self.uyari.show()
            return
        if message.get("changed"):
            self.uyari.setText(t("Kaynak değişti. Önizleme güncel dosyadır; indeks metni önceki sürüme ait olabilir."))
            self.uyari.show()
        self.metin.hide()
        result = message["result"]
        if message["kind"] in ('pdf','image'):
            self._sayfa, self._toplam = result["number"], result["total"]
            self.sayfa_no.blockSignals(True)
            self.sayfa_no.setMaximum(self._toplam)
            self.sayfa_no.setValue(self._sayfa)
            self.sayfa_no.blockSignals(False)
            q = QImage(result["data"], result["width"], result["height"],
                       result["width"] * 3, QImage.Format_RGB888).copy()
            self._orijinal = QPixmap.fromImage(q)
            self._son_kind = message["kind"]
            self.goruntu.show()
            self.canvas.show()
            if message["kind"] == "pdf":
                if self._ray_toplam != self._toplam or self.ray.count() == 0:
                    self._ray_kur(self._toplam)
                self._ray_guncelle()
            self._yerlestir()
        else:
            self.tablo.show()
            self.tablo.clear()
            rows = result["rows"]
            self.tablo.setRowCount(len(rows))
            self.tablo.setColumnCount(max((len(r) for r in rows), default=0))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.tablo.setItem(i, j, QTableWidgetItem("" if value is None else str(value)))
            self.bilgi.setText(self.bilgi.text() + f" • Sayfa: {result['sheet']}")
            self.tablo.resizeColumnsToContents()

    # -- page rail (papermerge PageList pattern; lazy loading) --

    def _ray_durdur(self):
        yukleyici = getattr(self, "_ray_loader", None)
        if yukleyici is not None:
            yukleyici.durdur()
            yukleyici.wait(3000)
            self._ray_loader = None

    def _ray_kur(self, toplam):
        """Append the first pages to the rail; the rest is produced while scrolling."""
        self._ray_durdur()
        self.ray.clear()
        self._ray_pixmaps = {}
        self._ray_yuklenen = 0
        self._ray_toplam = int(toplam or 0)
        if self._ray_toplam <= 0:
            self.ray.hide()
            return
        self.ray.show()
        self._ray_baslat()

    def _ray_baslat(self):
        self._ray_durdur()
        kalan = self._ray_toplam - self._ray_yuklenen
        if kalan <= 0 or not self._path:
            return
        adet = min(RAY_ADIM, kalan)
        isler = []
        for sira in range(self._ray_yuklenen + 1, self._ray_yuklenen + adet + 1):
            item = QListWidgetItem(str(sira))
            item.setSizeHint(QSize(62, 80))
            item.setToolTip(f"Sayfa {sira}")
            item.setData(Qt.UserRole, sira)
            self.ray.addItem(item)
            isler.append((self._path, f"p{sira}"))
        self._ray_yuklenen += adet
        yukleyici = thumbs.OnbellekYukleyici(isler, self)
        yukleyici.tamam.connect(self._ray_tamam)
        yukleyici.finished.connect(self._ray_bitti)
        self._ray_loader = yukleyici
        yukleyici.start()

    def _ray_bitti(self):
        yukleyici = self.sender()
        if self._ray_loader is yukleyici:
            self._ray_loader = None
        yukleyici.deleteLater()

    def _ray_tamam(self, path, tur, dosya):
        if self.sender() is not self._ray_loader or self._path != path:
            return
        if not (tur.startswith("p") and tur[1:].isdigit()):
            return
        sayfa = int(tur[1:])
        pixmap = QPixmap(dosya) if dosya else QPixmap()
        if pixmap.isNull():
            return
        self._ray_pixmaps[sayfa] = pixmap
        item = self.ray.item(sayfa - 1)
        if item is not None:
            item.setIcon(QIcon(pixmap))

    def _ray_guncelle(self):
        if not self.ray.isVisible() or self._sayfa > self.ray.count():
            return
        self.ray.blockSignals(True)
        self.ray.setCurrentRow(self._sayfa - 1)
        self.ray.blockSignals(False)
        item = self.ray.item(self._sayfa - 1)
        if item is not None:
            self.ray.scrollToItem(item, QListWidget.PositionAtCenter)

    def _ray_secildi(self, item):
        sayfa = item.data(Qt.UserRole) if item is not None else None
        if sayfa and sayfa != self._sayfa:
            self._git(int(sayfa))

    def _ray_kaydirma(self, deger):
        bar = self.ray.verticalScrollBar()
        if bar.maximum() > 0 and deger >= bar.maximum() and self._ray_yuklenen < self._ray_toplam:
            self._ray_baslat()

    # -- OCR/index text view --

    def _show_index(self):
        if self._index_view:
            # The same button goes back: return to the page view.
            self._index_view = False
            self.metin.hide()
            self.index_button.setText(t('İndeks metnini göster'))
            if self._path and self._path.lower().endswith(".pdf") and self._orijinal is not None:
                self.goruntu.show()
                self.canvas.show()
            return
        self._index_view = True
        self.canvas.hide(); self.tablo.hide(); self.goruntu.hide(); self.metin.show()
        self.index_button.setText(t('Sayfa görüntüsüne dön'))
        self.metin.setPlainText(self._fallback or 'İndeks metni bulunamadı.')

    def _load_more(self):
        if not self._path or self._password is None: return
        self.more_button.setEnabled(False)
        path=self._path; generation=self._generation; offset=self._offset
        def load(con):
            rows=indexed_text(con,path,offset)
            expected=con.execute('SELECT size,mtime_ns,index_status,error_code FROM files WHERE path=?',(path,)).fetchone()
            try:
                stat=os.stat(path); changed=expected and tuple(expected[:2])!=(stat.st_size,stat.st_mtime_ns); offline=False
            except OSError: changed=False; offline=True
            return rows,expected,changed,offline
        worker=DatabaseTask(self._dbpath,self._password,load,self)
        self._threads.append(worker)
        worker.ready.connect(lambda value:self._index_ready(generation,offset,value))
        worker.failed.connect(lambda error:self._index_error(generation,error))
        worker.finished.connect(lambda:self._finished(worker)); worker.start()

    def _index_error(self,generation,error):
        if generation==self._generation:
            self.uyari.setText(t('İndeks metni yüklenemedi: ')+error); self.uyari.show()

    def _index_ready(self,generation,offset,value):
        if generation!=self._generation or not self._path: return
        self.more_button.setEnabled(True)
        rows,expected,changed,offline=value
        self._expected=expected[:2] if expected else None
        self._offset+=min(20,len(rows))
        self.more_button.setVisible(len(rows)>20)
        text='\n\n'.join(f'[{label}]\n{raw}' for _,label,raw,_ in rows[:20])
        self._fallback=(self._fallback+'\n\n'+text).strip() if offset else text
        self.metin.setPlainText(self._fallback or 'İndeks metni bulunamadı.')
        if offline or changed or (expected and expected[2]!='ok'):
            self.uyari.setText('Kaynak erişilemiyor; son indeks metni gösteriliyor.' if offline else
                'Kaynak değişti; indeks önceki sürüme ait olabilir.' if changed else f'İçerik kısmi: {expected[3] or expected[2]}')
            self.uyari.show()
        if offset or offline or self._index_view: return
        ext=self._result.get('ext','').lower()
        if ext=='.pdf': self._pdf(self._path,self._result.get('page') or 1)
        elif ext in ('.xlsx','.xls'): self._start('excel',(self._path,self._result.get('label','').split(' • ')[0]))
        elif ext in ('.jpg','.jpeg','.png','.tif','.tiff'): self._start('image',(self._path,self._result.get('page') or 1))

    def _metin_goster(self, con, path):
        self.goruntu.hide()
        self.tablo.hide()
        self.pdf_nav.hide()
        self.metin.show()
        rows = con.execute(
            "SELECT label, raw_text FROM segments WHERE file_id="
            "(SELECT file_id FROM files WHERE path=?) ORDER BY seg_id LIMIT 60",
            (path,)).fetchall()
        if not rows:
            self.metin.setPlainText("Metin yok.")
            return
        self.metin.setPlainText("\n\n".join(f"[{l}]\n{t}" for l, t in rows))
