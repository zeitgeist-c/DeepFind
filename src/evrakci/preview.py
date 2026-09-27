"""Belge onizleme: PDF sayfa goruntusu, Excel veri bolgesi, Word metin/tablo.

Kurallar (plan bolum 20.3): guvenilir bbox yoksa kutu uydurulmaz; kaynak
degismisse eski snippet ile yeni goruntu ayni surummus gibi sunulmaz;
erisim yoksa son indeks metni gosterilir, sayfa goruntusu yok denir.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTextBrowser,
                               QVBoxLayout, QWidget)


class Onizleme(QWidget):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        self._path = None
        self._zoom = 1.0
        self._sayfa = 1
        self._toplam = 1
        self._orijinal = None  # olceklenmemis sayfa pixmap'i
        k = QVBoxLayout(self)
        self.baslik = QLabel("Belge seçilmedi")
        self.baslik.setProperty("baslik", True)
        self.baslik.setWordWrap(True)
        k.addWidget(self.baslik)
        self.bilgi = QLabel("")
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
        self.once = QPushButton("◀")
        self.sonra = QPushButton("▶")
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
        k.addWidget(self.goruntu, 1)
        self.tablo = QTableWidget()
        self.tablo.hide()
        k.addWidget(self.tablo, 1)
        self.metin = QTextBrowser()
        k.addWidget(self.metin, 1)

    # -- dis API --
    def goster(self, con, sonuc: dict):
        """sonuc: rank.search_ranked kaydi (path, name, ext, label, page, snippet, why...)."""
        path = sonuc["path"]
        self._path = path
        self._zoom = 1.0
        self.baslik.setText(sonuc["name"])
        neden = ", ".join(sonuc.get("why", []))
        self.bilgi.setText(f"{sonuc.get('label','')} • {neden}")
        self.uyari.hide()
        self._durum_kontrol(con, path)
        ext = (sonuc.get("ext") or "").lower()
        if ext == ".pdf":
            self._pdf(path, sonuc.get("page") or 1)
        elif ext in (".xlsx", ".xls"):
            self._excel(con, path)
        else:
            self._metin_goster(con, path)

    def temizle(self):
        self._path = None
        self.baslik.setText("Belge seçilmedi")
        self.bilgi.setText("")
        self.metin.clear()
        self.goruntu.hide()
        self.tablo.hide()

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
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(path)
            self._toplam = len(doc)
            doc.close()
        except Exception:
            self._toplam = 1
        self.sayfa_no.setMaximum(max(1, self._toplam))
        self._git(max(1, min(sayfa, self._toplam)))

    def _git(self, sayfa):
        self._sayfa = max(1, min(sayfa, self._toplam))
        self.sayfa_no.blockSignals(True)
        self.sayfa_no.setValue(self._sayfa)
        self.sayfa_no.blockSignals(False)
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(self._path)
            try:
                bmp = doc[self._sayfa - 1].render(scale=2.0 * self._zoom).to_pil()
                data = bmp.convert("RGB").tobytes()
                q = QImage(data, bmp.width, bmp.height, bmp.width * 3,
                           QImage.Format_RGB888)
                pm = QPixmap.fromImage(q)
                self._orijinal = pm
                self._yerlestir()
            finally:
                doc.close()
        except Exception as e:
            self.goruntu.setText(f"Sayfa görüntülenemedi: {type(e).__name__}")

    def _yerlestir(self):
        if self._orijinal is None or self._orijinal.isNull():
            return
        hedef = self.goruntu.size()
        if hedef.width() < 50 or hedef.height() < 50:
            genis = self.goruntu.width() or 380
            pm = self._orijinal
            if pm.width() > genis:
                pm = pm.scaledToWidth(genis, Qt.SmoothTransformation)
        else:
            pm = self._orijinal.scaled(hedef, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.goruntu.setPixmap(pm)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._path and self._path.lower().endswith(".pdf") and self._orijinal is not None:
            self._yerlestir()

    def _zoomla(self, f):
        self._zoom = max(0.5, min(3.0, self._zoom * f))
        if self._path and self._path.lower().endswith(".pdf"):
            self._git(self._sayfa)

    def _excel(self, con, path):
        self.goruntu.hide()
        self.pdf_nav.hide()
        self.metin.hide()
        self.tablo.show()
        self.tablo.clear()
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            try:
                ws = wb.worksheets[0]
                self.bilgi.setText(f"{self.bilgi.text()} • Sayfa: {ws.title}")
                rows = list(ws.iter_rows(values_only=True))[:200]
            finally:
                wb.close()
        except Exception:
            rows = [r[0].split(" | ") for r in con.execute(
                "SELECT raw_text FROM segments WHERE file_id="
                "(SELECT file_id FROM files WHERE path=?) LIMIT 200", (path,)).fetchall()
                if r[0]]
        if not rows:
            self.tablo.hide()
            self.metin.show()
            self.metin.setPlainText("Veri bölgesi okunamadı.")
            return
        genis = max(len(r) for r in rows)
        self.tablo.setRowCount(len(rows))
        self.tablo.setColumnCount(genis)
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                self.tablo.setItem(i, j, QTableWidgetItem("" if v is None else str(v)))
        self.tablo.resizeColumnsToContents()

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
