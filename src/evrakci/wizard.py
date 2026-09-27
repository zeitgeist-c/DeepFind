"""Ilk acilis sihirbazi: gizlilik -> kasa sifresi -> kaynak -> sirket kurali -> tema -> ozet.

Yari kapanirsa kasa bozuk sayilmaz; cagiran kaldigi adimi saklar (A7 UI).
"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (QComboBox, QFileSystemModel, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListView, QPushButton, QTreeView,
                               QVBoxLayout, QWizard, QWizardPage)


class _Sayfa(QWizardPage):
    def __init__(self, baslik, alt=""):
        super().__init__()
        self.setTitle(baslik)
        self.setSubTitle(alt)
        self.kutu = QVBoxLayout(self)


class Sihirbaz(QWizard):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        self.setWindowTitle("Evrakçı — İlk kurulum")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(720, 520)
        self.secim = {"kokler": [], "tema": "sistem", "sirket_kurali": "belirlenemiyor"}

        g = _Sayfa("Arşiviniz değişmez",
                   "Evrakçı kaynak dosyaları kopyalamaz, taşımaz, silmez. "
                   "Yalnız bu bilgisayarda şifreli bir arama indeksi kurar.")
        g.kutu.addWidget(QLabel("Taranacak klasörleri siz seçersiniz. İndeks metni "
                                "şifreli kasada durur; şifre unutulursa indeks yeniden kurulur."))
        self.addPage(g)

        s = _Sayfa("Kasa şifresi", "En az 12 karakter. Diske/loga yazılmaz.")
        f = QFormLayout()
        self.s1 = QLineEdit()
        self.s1.setEchoMode(QLineEdit.Password)
        self.s2 = QLineEdit()
        self.s2.setEchoMode(QLineEdit.Password)
        self.sifre_hata = QLabel("")
        self.sifre_hata.setProperty("hata", True)
        f.addRow("Şifre:", self.s1)
        f.addRow("Şifre (tekrar):", self.s2)
        s.kutu.addLayout(f)
        s.kutu.addWidget(self.sifre_hata)
        self.addPage(s)

        k = _Sayfa("Kaynak klasör", "Ağaç yalnız açılan dalları yükler; tüm NAS gezilmez.")
        ust = QHBoxLayout()
        self.unc = QLineEdit()
        self.unc.setPlaceholderText("UNC yolu, ör. \\\\NAS\\Belgeler  (veya ağaçtan seç)")
        ekle = QPushButton("Ekle")
        ekle.clicked.connect(self._unc_ekle)
        ust.addWidget(self.unc, 1)
        ust.addWidget(ekle)
        k.kutu.addLayout(ust)
        self.agac = QTreeView()
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(self.model.filter() | self.model.filter().__class__.Hidden)
        self.agac.setModel(self.model)
        self.agac.setColumnHidden(1, True)
        self.agac.setColumnHidden(2, True)
        self.agac.setColumnHidden(3, True)
        self.agac.doubleClicked.connect(self._agac_ekle)
        k.kutu.addWidget(self.agac, 1)
        self.kok_liste = QListView()
        from PySide6.QtCore import QStringListModel
        self.kok_model = QStringListModel()
        self.kok_liste.setModel(self.kok_model)
        k.kutu.addWidget(QLabel("Seçili kökler (çift tık ağaçtan ekler):"))
        k.kutu.addWidget(self.kok_liste)
        self.addPage(k)

        r = _Sayfa("Şirket kuralı", "Örnek yolların nasıl yorumlanacağını kaydetmeden görürsünüz.")
        self.kural = QComboBox()
        self.kural.addItems(["belirlenemiyor", "bu kök tek şirket",
                             "şirket alt klasör seviyesinde"])
        self.kural.currentTextChanged.connect(lambda t: self.secim.update(sirket_kurali=t))
        self.ornek = QLabel("")
        self.ornek.setProperty("ikincil", True)
        self.ornek.setWordWrap(True)
        r.kutu.addWidget(QLabel("Kök başına kural:"))
        r.kutu.addWidget(self.kural)
        r.kutu.addWidget(self.ornek)
        self.addPage(r)

        t = _Sayfa("Tema", "Sonradan ayarlardan değişir.")
        self.tema = QComboBox()
        self.tema.addItems(["sistem", "acik", "koyu"])
        self.tema.currentTextChanged.connect(lambda m: self.secim.update(tema=m))
        t.kutu.addWidget(self.tema)
        self.addPage(t)

        o = _Sayfa("Özet", "“Bitir” ilk taramayı başlatır; arama hemen kullanılabilir.")
        self.ozet = QLabel("")
        self.ozet.setWordWrap(True)
        o.kutu.addWidget(self.ozet)
        self.addPage(o)
        self.currentIdChanged.connect(self._sayfa)

    def _unc_ekle(self):
        yol = self.unc.text().strip()
        if yol and yol not in self.secim["kokler"] and os.path.exists(yol):
            self.secim["kokler"].append(yol)
            self._tazele()

    def _agac_ekle(self, idx):
        yol = self.model.filePath(idx)
        if yol and os.path.isdir(yol) and yol not in self.secim["kokler"]:
            self.secim["kokler"].append(yol)
            self._tazele()

    def _tazele(self):
        self.kok_model.setStringList(self.secim["kokler"])
        if self.secim["kokler"]:
            ilk = self.secim["kokler"][0]
            self.ornek.setText(f"Örnek: {ilk} → kural “{self.secim['sirket_kurali']}”")
            self.ozet.setText(f"Kök: {len(self.secim['kokler'])} adet\n"
                              f"Tema: {self.secim['tema']}\n"
                              "İçerik limiti: 200 MB, temel OCR açık")

    def _sayfa(self, _i):
        self._tazele()

    def validateCurrentPage(self):
        if self.currentPage() is self.page(1):
            a, b = self.s1.text(), self.s2.text()
            if len(a) < 12:
                self.sifre_hata.setText("Şifre en az 12 karakter olmalı.")
                return False
            if a != b:
                self.sifre_hata.setText("Şifreler eşleşmiyor.")
                return False
            self.sifre_hata.setText("")
            self.secim["sifre"] = a
        if self.currentPage() is self.page(2) and not self.secim["kokler"]:
            return False
        return super().validateCurrentPage()
