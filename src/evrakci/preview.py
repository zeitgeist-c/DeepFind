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
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTextBrowser,
                               QVBoxLayout, QWidget)


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
        self._path = None
        self._zoom = 1.0
        self._sayfa = 1
        self._toplam = 1
        self._orijinal = None  # olceklenmemis sayfa pixmap'i
        self._threads = []
        self._generation = 0
        self._expected = None
        self._fallback = ""
        k = QVBoxLayout(self)
        self.baslik = QLabel("Belge seçilmedi")
        self.baslik.setProperty("baslik", True)
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

        nav = QVBoxLayout()
        satir1 = QHBoxLayout()
        self.once = QPushButton("<")
        self.once.setAccessibleName("Önceki sayfa")
        self.sonra = QPushButton(">")
        self.sonra.setAccessibleName("Sonraki sayfa")
        self.sayfa_no = QSpinBox()
        self.sayfa_no.setMinimum(1)
        satir1.addWidget(self.once)
        satir1.addWidget(self.sayfa_no, 1)
        satir1.addWidget(self.sonra)
        satir2 = QHBoxLayout()
        self.buyut = QPushButton("+")
        self.kucult = QPushButton("−")
        satir2.addWidget(QLabel("Yakınlaştır:"))
        satir2.addWidget(self.kucult)
        satir2.addWidget(self.buyut)
        satir2.addStretch(1)
        nav.addLayout(satir1)
        nav.addLayout(satir2)
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

    # -- dis API --
    def goster(self, con, sonuc: dict):
        """sonuc: rank.search_ranked kaydi (path, name, ext, label, page, snippet, why...)."""
        path = sonuc["path"]
        self.temizle()
        self._path = path
        self._zoom = 1.0
        self.baslik.setText(sonuc["name"])
        neden = ", ".join(sonuc.get("why", []))
        self.bilgi.setText(f"{sonuc.get('label','')} • {neden}")
        self.uyari.hide()
        self._expected = con.execute("SELECT size,mtime_ns FROM files WHERE path=?", (path,)).fetchone()
        rows = con.execute("SELECT label,raw_text FROM segments WHERE file_id="
                           "(SELECT file_id FROM files WHERE path=?) ORDER BY seg_id LIMIT 60", (path,)).fetchall()
        self._fallback = "\n\n".join(f"[{label}]\n{text}" for label, text in rows)
        ext = (sonuc.get("ext") or "").lower()
        if ext == ".pdf":
            self._pdf(path, sonuc.get("page") or 1)
        elif ext in (".xlsx", ".xls"):
            self._start("excel", (path, sonuc.get("label", "")))
        else:
            self._metin_goster(con, path)

    def temizle(self):
        self._generation += 1
        for thread in self._threads:
            thread.stop.set()
        self._fallback = ""
        self._path = None
        self._orijinal = None
        self.goruntu.clear()
        self.tablo.clear()
        self.tablo.setRowCount(0)
        self.tablo.setColumnCount(0)
        self.uyari.clear()
        self.uyari.hide()
        self.pdf_nav.hide()
        self._expected = None
        self.baslik.setText("Belge seçilmedi")
        self.bilgi.setText("")
        self.metin.clear()
        self.goruntu.hide()
        self.canvas.hide()
        self.tablo.hide()

    def busy(self):
        return bool(self._threads)

    def _start(self, kind, args):
        self._generation += 1
        for thread in self._threads:
            thread.stop.set()
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
        if "error" in message:
            self.goruntu.hide()
            self.metin.show()
            self.metin.setPlainText(self._fallback or "İndeks metni bulunamadı.")
            self.uyari.setText("Kaynak önizlemesi açılamadı; son indeks metni gösteriliyor.")
            self.uyari.show()
            return
        if message.get("changed"):
            self.uyari.setText("Kaynak değişti. Önizleme güncel dosyadır; indeks metni önceki sürüme ait olabilir.")
            self.uyari.show()
        self.metin.hide()
        result = message["result"]
        if message["kind"] == "pdf":
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
