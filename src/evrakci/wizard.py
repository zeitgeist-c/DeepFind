"""Ilk acilis sihirbazi: gizlilik -> kasa sifresi -> kaynak -> sirket kurali -> tema -> ozet.

Yari kapanirsa kasa bozuk sayilmaz; cagiran kaldigi adimi saklar (A7 UI).
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QDir, Qt, QStringListModel
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFileSystemModel, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListView, QPushButton, QTreeView,
                               QVBoxLayout, QWizard, QWizardPage, QFrame, QSplitter)
from .theme import app_icon, install_turkish
from .ui import brand, card, label
from .ui import CardDelegate
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView


class _Sayfa(QWizardPage):
    def __init__(self, baslik, alt=""):
        super().__init__()
        self.setObjectName("setupPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.kutu = QVBoxLayout(self)
        self.kutu.setSpacing(16)
        self.kutu.setContentsMargins(30, 28, 30, 28)
        self.kutu.addWidget(label("İLK KURULUM", "eyebrow"))
        self.heading = label(baslik, "baslik")
        self.kutu.addWidget(self.heading)
        self.kutu.addWidget(label(alt, "ikincil"))


class Sihirbaz(QWizard):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        from PySide6.QtWidgets import QApplication
        install_turkish(QApplication.instance())
        self.setWindowTitle("Evrakçı — İlk kurulum")
        self.setWindowIcon(app_icon())
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setMinimumSize(1000, 660)
        self.resize(1080, 700)
        self.setOption(QWizard.NoBackButtonOnStartPage)
        self.setButtonLayout([QWizard.CancelButton, QWizard.CustomButton1, QWizard.Stretch, QWizard.BackButton,
                              QWizard.NextButton, QWizard.FinishButton])
        self.setButtonText(QWizard.BackButton, "Geri")
        self.setButtonText(QWizard.NextButton, "İleri")
        self.setButtonText(QWizard.FinishButton, "Kurulumu tamamla")
        self.setButtonText(QWizard.CancelButton, "Vazgeç")
        self.setButtonText(QWizard.HelpButton, "Yardım")
        self.secim = {"kokler": [], "tema": "sistem", "sirket_kurali": "belirlenemiyor"}
        self.tema = QComboBox(self)
        for caption, value in [("Sistem teması", "sistem"), ("Açık", "acik"), ("Koyu", "koyu")]:
            self.tema.addItem(caption, value)
        self.setOption(QWizard.HaveCustomButton1)
        from PySide6.QtWidgets import QMenu
        self.tema.hide()
        self.theme_button = QPushButton("Tema: Sistem")
        menu = QMenu(self.theme_button)
        self._theme_menu = menu
        for index, caption in enumerate(("Sistem teması", "Açık", "Koyu")):
            menu.addAction(caption, lambda checked=False, i=index: self.tema.setCurrentIndex(i))
        self.theme_button.setMenu(menu)
        self.setButton(QWizard.CustomButton1, self.theme_button)
        self.tema.currentIndexChanged.connect(self._tema_degistir)
        from PySide6.QtCore import QSettings
        saved_theme = QSettings("Evrakci", "Appearance").value("theme", "sistem")
        self.tema.setCurrentIndex(max(0, self.tema.findData(saved_theme)))
        self.secim["tema"] = self.tema.currentData()
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(242)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(22, 24, 22, 24)
        rail_layout.setSpacing(6)
        brand(rail_layout, size=38)
        rail_layout.addSpacing(12)
        rail_layout.addWidget(label("ÇALIŞMA ALANINIZI KURALIM", "eyebrow"))
        self.steps = []
        for i, title in enumerate(("Hoş geldiniz", "Kasa şifresi", "Klasörler", "Düzen", "Son kontrol")):
            step = label(f"{i + 1:02d}   {title}")
            step.setObjectName("step")
            rail_layout.addWidget(step)
            self.steps.append(step)
        rail_layout.addStretch()
        rail_layout.addWidget(label("Belgeleriniz yerinde.\nAramanız size özel.", "subheading"))
        rail_layout.addWidget(label("Kaynak belgeleriniz korunur.\nArama bilgileri şifreli saklanır.", "ikincil"))
        self._rail = rail
        self.setSideWidget(rail)

        g = _Sayfa("Belgeleriniz.\nTek bir arama.", "Dağınık klasörlerden aradığınız belgeye.\nEvrakçı’yı birkaç kısa adımda kullanıma hazırlayın.")
        g.heading.setProperty("hero", True)
        for title, text in [
            ("Adıyla ya da içeriğiyle bulun", "Bir dosya adı, birkaç kelime veya bir yıl yazmanız yeterli."),
            ("Klasörler sizden, düzen Evrakçı’dan", "Bilgisayarınızdaki ve ağdaki belge klasörlerini seçin."),
            ("Size özel bir çalışma alanı", "Şifreniz, arama bilgilerinizi bu bilgisayarda korur.")]:
            panel, content = card()
            content.addWidget(label(title, "subheading"))
            content.addWidget(label(text, "ikincil"))
            g.kutu.addWidget(panel)
        g.kutu.addStretch()
        self.addPage(g)

        s = _Sayfa("Şifrenizi belirleyin", "En az 12 karakter kullanın ve aynı şifreyi iki kez girin.")
        password_panel, f = card()
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
        f.addWidget(label("Kasa şifresi", "subheading"))
        f.addWidget(self.s1)
        f.addWidget(label("Şifreyi tekrar girin", "ikincil"))
        f.addWidget(self.s2)
        s.kutu.addWidget(password_panel)
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
        self.kok_liste = QListView()
        self.kok_model = QStandardItemModel(self)
        self.kok_liste.setModel(self.kok_model)
        self.kok_liste.setObjectName("cardList")
        self.kok_liste.setItemDelegate(CardDelegate(self.kok_liste, "folder", compact=True))
        self.kok_liste.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.kok_liste.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.kok_liste.setAccessibleName("Aramaya eklenen klasörler")
        columns = QSplitter(Qt.Horizontal)
        available, available_layout = card()
        available_layout.addWidget(label("Bilgisayar ve ağ", "subheading"))
        available_layout.addWidget(self.agac, 1)
        selected_panel, selected = card()
        self.kok_baslik = QLabel("Eklenen klasörler • 0")
        self.kok_baslik.setProperty("subheading", True)
        remove = QPushButton("Seçilenleri kaldır")
        remove.clicked.connect(self._kaldir)
        selected.addWidget(self.kok_baslik)
        selected.addWidget(label("Yalnız bu klasörlerde arama yapılır.", "ikincil"))
        selected.addWidget(self.kok_liste, 1)
        select_all = QPushButton("Tümünü seç")
        select_all.clicked.connect(self.kok_liste.selectAll)
        selected.addWidget(select_all)
        removal = QHBoxLayout()
        removal.addWidget(remove)
        clear = QPushButton("Tümünü kaldır")
        clear.clicked.connect(self._tumunu_kaldir)
        removal.addWidget(clear)
        selected.addLayout(removal)
        columns.addWidget(available)
        columns.addWidget(selected_panel)
        columns.setChildrenCollapsible(False)
        columns.setSizes([360, 320])
        k.kutu.addWidget(columns, 1)
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
        r.kutu.addWidget(label("Bu seçim, dosyalarınıza dokunmadan arama sonuçlarının klasör bağlamını belirler.", "ikincil"))
        r.kutu.addStretch()
        self.addPage(r)

        o = _Sayfa("Her şey yerli yerinde.", "“Kurulumu tamamla” ile ilk taramayı başlatın. Belgelerinizin sayısına göre bu biraz zaman alabilir.")
        self.ozet = QLabel("")
        self.ozet.setWordWrap(True)
        summary_panel, summary_layout = card()
        summary_layout.addWidget(label("Çalışma alanınız", "subheading"))
        summary_layout.addWidget(self.ozet)
        o.kutu.addWidget(summary_panel)
        o.kutu.addWidget(label("Belgeleriniz taşınmaz veya değiştirilmez. Tarama sürerken uygulamayı kullanabilirsiniz.", "ikincil"))
        o.kutu.addStretch()
        self.addPage(o)
        self.currentIdChanged.connect(self._sayfa)
        self._sayfa(0)

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

    def _tema_degistir(self):
        from . import theme
        from PySide6.QtWidgets import QApplication
        self.secim["tema"] = self.tema.currentData()
        self.theme_button.setText("Tema: " + self.tema.currentText())
        theme.apply(QApplication.instance(), self.tema.currentData())

    def _tumunu_kaldir(self):
        self.secim["kokler"].clear()
        self._tazele()
        self._mesaj("Arama listesi temizlendi. Asıl klasörler korunuyor.")

    def _kaldir(self):
        rows = sorted({i.row() for i in self.kok_liste.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.secim["kokler"].pop(row)
        self._tazele()
        self._mesaj("Seçilen klasörler arama listesinden kaldırıldı." if rows else "Önce kaldırılacak klasörleri seçin.")

    def _tazele(self):
        self.kok_model.clear()
        for path in self.secim["kokler"]:
            title = Path(path).name or path
            item = QStandardItem(title + "\n" + path)
            item.setToolTip(path)
            item.setEditable(False)
            self.kok_model.appendRow(item)
        self.kok_baslik.setText(f"Eklenen klasörler • {len(self.secim['kokler'])}")
        if self.secim["kokler"]:
            ilk = self.secim["kokler"][0]
            self.ornek.setText(f"Örnek: {ilk} → kural “{self.secim['sirket_kurali']}”")
            self.ozet.setText(f"Kök: {len(self.secim['kokler'])} adet\n"
                              f"Tema: {self.tema.currentText()}\n"
                              "Belgelerinizin arama bilgileri şifreli saklanır.")

    def _sayfa(self, _i):
        self._tazele()
        for i, step in enumerate(self.steps):
            step.setProperty("active", i == max(0, _i))
            step.setProperty("done", 0 <= i < _i)
            step.style().unpolish(step)
            step.style().polish(step)

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
