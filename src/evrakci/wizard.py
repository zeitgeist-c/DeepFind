"""Ilk acilis sihirbazi: gizlilik -> kasa sifresi -> kaynak -> sirket kurali -> tema -> ozet.

Yari kapanirsa kasa bozuk sayilmaz; cagiran kaldigi adimi saklar (A7 UI).
"""
from __future__ import annotations

import os

from PySide6.QtCore import QDir, Qt, QStringListModel
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFileSystemModel, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListView, QPushButton, QTreeView,
                               QVBoxLayout, QWizard, QWizardPage)
from .theme import app_icon, install_turkish


class _Sayfa(QWizardPage):
    def __init__(self, baslik, alt=""):
        super().__init__()
        self.setTitle(baslik)
        self.setSubTitle(alt)
        self.kutu = QVBoxLayout(self)
        self.kutu.setSpacing(10)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(36, 36))
        logo.setAccessibleName("Evrakçı logosu")
        brand.addWidget(logo)
        name = QLabel("Evrakçı")
        name.setProperty("baslik", True)
        brand.addWidget(name)
        brand.addStretch()
        self.kutu.addLayout(brand)


class Sihirbaz(QWizard):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        from PySide6.QtWidgets import QApplication
        install_turkish(QApplication.instance())
        self.setWindowTitle("Evrakçı — İlk kurulum")
        self.setWindowIcon(app_icon())
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setMinimumSize(800, 650)
        self.setButtonText(QWizard.BackButton, "Geri")
        self.setButtonText(QWizard.NextButton, "İleri")
        self.setButtonText(QWizard.FinishButton, "Kurulumu tamamla")
        self.setButtonText(QWizard.CancelButton, "Vazgeç")
        self.setButtonText(QWizard.HelpButton, "Yardım")
        self.secim = {"kokler": [], "tema": "sistem", "sirket_kurali": "belirlenemiyor"}

        g = _Sayfa("Belgelerinizi kolayca bulun", "İlk kurulum • 6 kısa adım")
        for title, text in [
            ("1. Bir şifre belirleyin", "Belge arama bilgileri bu bilgisayarda şifreli olarak saklanır."),
            ("2. Klasörlerinizi seçin", "Bilgisayarınızdaki veya ağdaki klasörleri aramaya ekleyin."),
            ("3. Aramaya başlayın", "Dosya adı veya belge içeriğinde geçen kelimelerle belgelerinizi bulun."),
            ("Kaynak belgeleriniz korunur", "Evrakçı belgelerinizi değiştirmez, taşımaz veya silmez.")]:
            heading = QLabel(title)
            heading.setStyleSheet("font-weight: 600;")
            body = QLabel(text)
            body.setWordWrap(True)
            body.setProperty("ikincil", True)
            g.kutu.addWidget(heading)
            g.kutu.addWidget(body)
        g.kutu.addStretch()
        self.addPage(g)

        s = _Sayfa("Şifrenizi belirleyin", "En az 12 karakter kullanın ve aynı şifreyi iki kez girin.")
        f = QFormLayout()
        self.s1 = QLineEdit()
        self.s1.setEchoMode(QLineEdit.Password)
        self.s2 = QLineEdit()
        self.s2.setEchoMode(QLineEdit.Password)
        self.s1.setPlaceholderText("En az 12 karakter")
        self.s2.setPlaceholderText("Şifrenizi tekrar girin")
        self.s1.setAccessibleName("Yeni şifre")
        self.s2.setAccessibleName("Şifre tekrarı")
        self.sifre_hata = QLabel("")
        self.sifre_hata.setProperty("hata", True)
        f.addRow("Şifre:", self.s1)
        f.addRow("Şifre (tekrar):", self.s2)
        s.kutu.addLayout(f)
        s.kutu.addWidget(self.sifre_hata)
        show = QCheckBox("Şifreyi göster")
        show.toggled.connect(lambda on: [field.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for field in (self.s1, self.s2)])
        s.kutu.addWidget(show)
        note = QLabel("Bu şifreyi uygulamayı açarken kullanacaksınız. Daha sonra Ayarlar bölümünden "
                      "değiştirebilirsiniz. Şifrenizi unutursanız arama bilgilerini yeniden oluşturmanız gerekir; "
                      "asıl belgeleriniz bundan etkilenmez.")
        note.setWordWrap(True)
        note.setProperty("ikincil", True)
        s.kutu.addWidget(note)
        s.kutu.addStretch()
        self.addPage(s)

        k = _Sayfa("Aranacak klasörleri seçin", "Aşağıdan bir klasör seçip Ekle’ye basın veya klasör yolunu yazın.")
        ust = QHBoxLayout()
        self.unc = QLineEdit()
        self.unc.setPlaceholderText("Klasör yolu • ör. C:\\Belgeler veya \\\\NAS\\Belgeler")
        self.unc.setAccessibleName("Eklenecek klasörün yolu")
        self.ekle = QPushButton("Ekle")
        self.ekle.setProperty("birincil", True)
        self.ekle.clicked.connect(self._unc_ekle)
        self.unc.returnPressed.connect(self._unc_ekle)
        ust.addWidget(self.unc, 1)
        ust.addWidget(self.ekle)
        k.kutu.addLayout(ust)
        actions = QHBoxLayout()
        browse = QPushButton("Klasör seç…")
        browse.clicked.connect(self._gozat)
        self.yenile = QPushButton("Yenile")
        self.yenile.clicked.connect(self._yenile)
        actions.addWidget(browse)
        actions.addWidget(self.yenile)
        actions.addStretch()
        k.kutu.addLayout(actions)
        self.agac = QTreeView()
        self.model = QFileSystemModel(self)
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        self.agac.setModel(self.model)
        self.agac.setHeaderHidden(True)
        self.agac.setAccessibleName("Bilgisayarınızdaki klasörler")
        self.agac.setMinimumHeight(100)
        self.agac.setColumnHidden(1, True)
        self.agac.setColumnHidden(2, True)
        self.agac.setColumnHidden(3, True)
        self.agac.doubleClicked.connect(self._agac_ekle)
        k.kutu.addWidget(self.agac, 1)
        self.kok_liste = QListView()
        self.kok_model = QStringListModel(self)
        self.kok_liste.setModel(self.kok_model)
        self.kok_liste.setMaximumHeight(85)
        self.kok_liste.setAccessibleName("Aramaya eklenen klasörler")
        selected = QHBoxLayout()
        self.kok_baslik = QLabel("Eklenen klasörler • 0")
        remove = QPushButton("Seçileni kaldır")
        remove.clicked.connect(self._kaldir)
        selected.addWidget(self.kok_baslik)
        selected.addStretch()
        selected.addWidget(remove)
        k.kutu.addLayout(selected)
        k.kutu.addWidget(self.kok_liste)
        self.kaynak_mesaj = QLabel("Henüz klasör eklenmedi.")
        self.kaynak_mesaj.setWordWrap(True)
        k.kutu.addWidget(self.kaynak_mesaj)
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
        for label, value in [("Sistem teması", "sistem"), ("Açık", "acik"), ("Koyu", "koyu")]:
            self.tema.addItem(label, value)
        self.tema.currentIndexChanged.connect(lambda _: self.secim.update(tema=self.tema.currentData()))
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
        if not yol:
            yol = self.model.filePath(self.agac.currentIndex())
        self._ekle_yol(yol)

    def _agac_ekle(self, idx):
        self._ekle_yol(self.model.filePath(idx))

    def _mesaj(self, text):
        self.kaynak_mesaj.setText(text)

    def _ekle_yol(self, yol):
        yol = yol.strip().strip('"')
        if not yol:
            self._mesaj("Önce listeden bir klasör seçin veya klasör yolunu yazın.")
            return
        yol = os.path.abspath(os.path.normpath(yol))
        if not os.path.isdir(yol):
            self._mesaj("Bu klasöre ulaşılamıyor. Yolu ve bağlantınızı kontrol edin; bir dosya değil, klasör seçin.")
            return
        keys = {os.path.normcase(os.path.normpath(p)) for p in self.secim["kokler"]}
        if os.path.normcase(yol) in keys:
            self._mesaj("Bu klasör zaten eklendi.")
            return
        self.secim["kokler"].append(yol)
        self.unc.clear()
        self._tazele()
        self._mesaj("Klasör eklendi. İsterseniz başka klasörler de ekleyebilirsiniz.")

    def _gozat(self):
        yol = QFileDialog.getExistingDirectory(self, "Aranacak klasörü seçin")
        if yol:
            self._ekle_yol(yol)

    def _yenile(self):
        previous = self.model
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        self.model.setRootPath("")
        self.agac.setModel(self.model)
        for column in (1, 2, 3):
            self.agac.setColumnHidden(column, True)
        previous.deleteLater()
        self._mesaj("Klasör listesi yenilendi. Eklediğiniz klasörler korundu.")

    def _kaldir(self):
        idx = self.kok_liste.currentIndex()
        if idx.isValid():
            self.secim["kokler"].pop(idx.row())
            self._tazele()
            self._mesaj("Klasör arama listesinden kaldırıldı. Asıl klasör silinmedi.")
        else:
            self._mesaj("Kaldırmak için eklenen klasörler listesinden bir klasör seçin.")

    def _tazele(self):
        self.kok_model.setStringList(self.secim["kokler"])
        self.kok_baslik.setText(f"Eklenen klasörler • {len(self.secim['kokler'])}")
        if self.secim["kokler"]:
            ilk = self.secim["kokler"][0]
            self.ornek.setText(f"Örnek: {ilk} → kural “{self.secim['sirket_kurali']}”")
            self.ozet.setText(f"Kök: {len(self.secim['kokler'])} adet\n"
                              f"Tema: {self.tema.currentText()}\n"
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
            self._mesaj("Devam etmek için en az bir klasör ekleyin.")
            return False
        return super().validateCurrentPage()
