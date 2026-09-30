"""Belge onizleme: PDF sayfa goruntusu, Excel veri bolgesi, Word metin/tablo.

Kurallar (plan bolum 20.3): guvenilir bbox yoksa kutu uydurulmaz; kaynak
degismisse eski snippet ile yeni goruntu ayni surummus gibi sunulmaz;
erisim yoksa son indeks metni gosterilir, sayfa goruntusu yok denir.
"""
from __future__ import annotations

import os
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QProgressBar, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTextBrowser,
                               QVBoxLayout, QWidget)
from .tasks import DatabaseTask, indexed_text
from .ui import EmptyState, label


class PreviewWorker(QThread):
    ready = Signal(dict)

    def __init__(self, kind, args, generation, expected, parent):
        super().__init__(parent)
        self.kind, self.args, self.generation, self.expected = kind, args, generation, expected
        self.stop = threading.Event()

    def run(self):
        from .workers import run_work
        try:
            # stat ve dosya açma dahil kaynak işlemleri UI dışında.
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
        self._path = None
        self._index_view = False
        self._zoom = 1.0
        self._sayfa = 1
        self._toplam = 1
        self._orijinal = None  # olceklenmemis sayfa pixmap'i
        self._threads = []
        self._generation = 0
        self._expected = None
        self._fallback = ""
        k = QVBoxLayout(self)
        k.setContentsMargins(22, 22, 22, 20)
        k.setSpacing(10)
        k.addWidget(label("BELGE ÖNİZLEMESİ", "eyebrow"))
        self.baslik = QLabel("Belge seçilmedi")
        self.baslik.setProperty("subheading", True)
        self.baslik.setWordWrap(True)
        k.addWidget(self.baslik)
        self.bilgi = QLabel("Sonuçlardan bir belge seçerek içeriğini burada inceleyin.")
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
        yukleme_duzeni.setContentsMargins(0, 12, 0, 12)
        self.yukleme_yazisi = QLabel("PDF açılıyor…")
        self.yukleme_yazisi.setAccessibleName("Önizleme yükleme durumu")
        self.yukleme_cubugu = QProgressBar()
        self.yukleme_cubugu.setRange(0, 0)
        self.yukleme_cubugu.setTextVisible(False)
        self.yukleme_cubugu.setAccessibleName("PDF önizlemesi hazırlanıyor")
        yukleme_duzeni.addWidget(self.yukleme_yazisi)
        yukleme_duzeni.addWidget(self.yukleme_cubugu)
        self.yukleme.hide()
        k.addWidget(self.yukleme)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        satir1 = QHBoxLayout()
        self.once = QPushButton("<")
        self.once.setAccessibleName("Önceki sayfa")
        self.sonra = QPushButton(">")
        self.sonra.setAccessibleName("Sonraki sayfa")
        self.sayfa_no = QSpinBox()
        self.sayfa_no.setFixedWidth(60)
        self.sayfa_no.setAccessibleName("Sayfa numarası")
        self.sayfa_no.setMinimum(1)
        satir1.addWidget(self.once)
        satir1.addWidget(self.sayfa_no, 1)
        satir1.addWidget(self.sonra)
        satir2 = QHBoxLayout()
        self.buyut = QPushButton("+")
        self.kucult = QPushButton("−")
        satir2.addWidget(self.kucult)
        satir2.addWidget(self.buyut)
        satir2.addStretch(1)
        nav.addLayout(satir1)
        nav.addStretch()
        nav.addLayout(satir2)
        self.buyut.setToolTip("Yakınlaştır")
        self.kucult.setToolTip("Uzaklaştır")
        self.buyut.setAccessibleName("Yakınlaştır")
        self.kucult.setAccessibleName("Uzaklaştır")
        for b in (self.once, self.sonra, self.buyut, self.kucult):
            b.setFixedWidth(40)
            b.setMinimumHeight(28)
            b.setStyleSheet("QPushButton { padding: 4px; }")
        self.sayfa_no.setMinimumHeight(28)
        self.once.clicked.connect(lambda: self._git(self._sayfa - 1))
        self.sonra.clicked.connect(lambda: self._git(self._sayfa + 1))
        self.sayfa_no.valueChanged.connect(lambda v: self._git(v))
        self.buyut.clicked.connect(lambda: self._zoomla(1.25))
        self.kucult.clicked.connect(lambda: self._zoomla(0.8))
        self.pdf_nav = QWidget()
        self.pdf_nav.setLayout(nav)
        k.addWidget(self.pdf_nav)

        self.goruntu = QLabel()
        self.goruntu.setAlignment(Qt.AlignCenter)
        self.goruntu.hide()
        from PySide6.QtWidgets import QScrollArea
        self.canvas = QScrollArea()
        self.canvas.setObjectName("paperCanvas")
        self.canvas.setWidget(self.goruntu)
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setFrameShape(QScrollArea.NoFrame)
        self.canvas.hide()
        k.addWidget(self.canvas, 1)
        self.tablo = QTableWidget()
        from PySide6.QtWidgets import QAbstractItemView
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.hide()
        k.addWidget(self.tablo, 1)
        self.metin = QTextBrowser()
        k.addWidget(self.metin, 1)
        self.empty = EmptyState("İçeriğe yakından bakın", "Bir arama sonucunu seçtiğinizde\nbelgenin önizlemesi burada açılır.", "document")
        k.addWidget(self.empty, 1)
        self.index_button=QPushButton('İndeks metnini göster')
        self.index_button.clicked.connect(self._show_index)
        k.addWidget(self.index_button)
        self.more_button=QPushButton('Sonraki bölümleri yükle')
        self.more_button.clicked.connect(self._load_more)
        k.addWidget(self.more_button)
        self.temizle()

    # -- dis API --
    def goster(self, con, sonuc: dict, password=None):
        """sonuc: rank.search_ranked kaydi (path, name, ext, label, page, snippet, why...)."""
        path = sonuc["path"]
        self.temizle()
        self.empty.hide()
        self._path = path
        self._zoom = 1.0
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
            # Büyük kasada segments sorgusu arayüzü kilitleyebilir. Arama özeti hazırdır.
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
        self._fallback = ""
        self._path = None
        self._password = None
        self._offset = 0
        if hasattr(self,'more_button'): self.more_button.hide()
        self._orijinal = None
        self.goruntu.clear()
        self.tablo.clear()
        self.tablo.setRowCount(0)
        self.tablo.setColumnCount(0)
        self.uyari.clear()
        self.uyari.hide()
        self.yukleme.hide()
        self.pdf_nav.hide()
        self._expected = None
        self.baslik.setText("Önizleme")
        self.bilgi.setText("")
        self.metin.clear()
        self.goruntu.hide()
        self.canvas.hide()
        self.tablo.hide()
        self.metin.hide()
        self.empty.show()

    def busy(self):
        return bool(self._threads)

    def _show_index(self):
        self._index_view=True
        self.canvas.hide(); self.tablo.hide(); self.goruntu.hide(); self.metin.show()
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
            self.uyari.setText('İndeks metni yüklenemedi: '+error); self.uyari.show()

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

    def _start(self, kind, args):
        self._generation += 1
        for thread in self._threads:
            thread.stop.set()
        if kind == "pdf":
            self.canvas.hide()
            self.goruntu.hide()
            self.metin.hide()
            self.yukleme_yazisi.setText("PDF sayfası açılıyor…")
            self.yukleme.show()
        else:
            self.metin.show()
            self.metin.setPlainText("Önizleme hazırlanıyor…")
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
            self.metin.setPlainText(self._fallback or "Önizleme metni bulunamadı.")
            if message.get("kind") == "pdf":
                durum = "arama özeti gösteriliyor" if self._fallback else "arama özeti de bulunamadı"
            else:
                durum = "son indeks metni gösteriliyor" if self._fallback else "indeks metni bulunamadı"
            self.uyari.setText(f"Kaynak önizlemesi açılamadı; {durum}.")
            self.uyari.show()
            return
        if message.get("changed"):
            self.uyari.setText("Kaynak değişti. Önizleme güncel dosyadır; indeks metni önceki sürüme ait olabilir.")
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
            self.goruntu.show()
            self.canvas.show()
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

    # -- ic --
    def _durum_kontrol(self, con, path):
        try:
            st = os.stat(path)
            row = con.execute("SELECT size, mtime_ns FROM files WHERE path=?",
                              (path,)).fetchone()
            if row and (row[0] != st.st_size or row[1] != st.st_mtime_ns):
                self.uyari.setText("Kaynak değişti; yeniden indeksleme bekliyor. "
                                   "Görünen alıntı eski sürüme ait olabilir.")
                self.uyari.show()
        except OSError:
            self.uyari.setText("Kaynak erişilemiyor; son indeks metni gösteriliyor.")
            self.uyari.show()

    def _pdf(self, path, sayfa):
        self.tablo.hide()
        self.metin.hide()
        self.goruntu.show()
        self.pdf_nav.show()
        self._git(max(1, sayfa))

    def _git(self, sayfa):
        if self._path:
            self._start("pdf", (self._path, max(1, sayfa), self._zoom))
    def _yerlestir(self):
        if self._orijinal is None or self._orijinal.isNull():
            return
        hedef = self.canvas.viewport().size()
        hedef.setWidth(max(100, int(hedef.width() * self._zoom)))
        hedef.setHeight(max(100, int(hedef.height() * self._zoom)))
        pm = self._orijinal.scaled(hedef, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.goruntu.setPixmap(pm)
        self.goruntu.resize(pm.size())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._path and self._path.lower().endswith(".pdf") and self._orijinal is not None:
            self._yerlestir()

    def _zoomla(self, f):
        self._zoom = max(0.5, min(3.0, self._zoom * f))
        if self._path and self._path.lower().endswith(".pdf"):
            self._git(self._sayfa)

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
