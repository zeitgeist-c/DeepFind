"""Ilk acilis sihirbazi: gizlilik -> kasa sifresi -> kaynak -> sirket kurali -> tema -> ozet.

Yari kapanirsa kasa bozuk sayilmaz; cagiran kaldigi adimi saklar (A7 UI).
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFileSystemModel, QHBoxLayout,
                               QLabel, QLineEdit, QListView, QPushButton, QTreeView,
                               QVBoxLayout, QWizard, QWizardPage, QFrame, QSplitter)
from .theme import LANGUAGES, app_icon, install_language, resolve_language, set_language, t
from .ui import brand, bolme, card, label
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
        self.kutu.addWidget(label(t("İLK KURULUM"), "eyebrow"))
        self.heading = label(baslik, "baslik")
        self.kutu.addWidget(self.heading)
        self.kutu.addWidget(label(alt, "ikincil"))


class Sihirbaz(QWizard):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        from . import identity
        install_language(QApplication.instance(), resolve_language(
            QSettings(identity.APP_IDENTITY, "Appearance").value("language", "en")))
        self.setWindowTitle(t("DeepFind — İlk kurulum"))
        self.setWindowIcon(app_icon())
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setMinimumSize(980, 640)
        self.resize(1060, 690)
        self.setOption(QWizard.NoBackButtonOnStartPage)
        self.setButtonLayout([QWizard.CancelButton, QWizard.CustomButton1, QWizard.Stretch, QWizard.BackButton,
                              QWizard.NextButton, QWizard.FinishButton])
        self.setButtonText(QWizard.BackButton, "Geri")
        self.setButtonText(QWizard.NextButton, t("İleri"))
        self.setButtonText(QWizard.FinishButton, t("Kurulumu tamamla"))
        self.setButtonText(QWizard.CancelButton, t("Vazgeç"))
        self.setButtonText(QWizard.HelpButton, t("Yardım"))
        self.secim = {"kokler": [], "tema": "sistem", "sirket_kurali": "belirlenemiyor"}
        self.tema = QComboBox(self)
        for caption, value in [(t("Sistem teması"), "sistem"), (t("Açık"), "acik"), ("Koyu", "koyu")]:
            self.tema.addItem(caption, value)
        self.setOption(QWizard.HaveCustomButton1)
        from PySide6.QtWidgets import QMenu
        self.tema.hide()
        self.theme_button = QPushButton("Tema: Sistem")
        menu = QMenu(self.theme_button)
        self._theme_menu = menu
        for index, caption in enumerate((t("Sistem teması"), t("Açık"), "Koyu")):
            menu.addAction(caption, lambda checked=False, i=index: self.tema.setCurrentIndex(i))
        self.theme_button.setMenu(menu)
        self.setButton(QWizard.CustomButton1, self.theme_button)
        self.tema.currentIndexChanged.connect(self._tema_degistir)
        saved_theme = QSettings(identity.APP_IDENTITY, "Appearance").value("theme", "sistem")
        self.tema.setCurrentIndex(max(0, self.tema.findData(saved_theme)))
        self.secim["tema"] = self.tema.currentData()
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(258)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(24, 26, 24, 26)
        rail_layout.setSpacing(2)
        brand(rail_layout, size=32)
        rail_layout.addSpacing(18)
        rail_layout.addWidget(label(t("İlk kurulum"), "eyebrow"))
        rail_layout.addSpacing(6)
        self.steps = []
        for i, title in enumerate((t("Hoş geldiniz"), t("Kasa şifresi"), t("Klasörler"), t("Düzen"), "Son kontrol")):
            step = label(f"{i + 1:02d}   {title}")
            step.setObjectName("step")
            rail_layout.addWidget(step)
            self.steps.append(step)
        rail_layout.addStretch()
        rail_layout.addWidget(bolme())
        rail_layout.addSpacing(14)
        rail_layout.addWidget(label(t("Kaynak belgeleriniz korunur.\nArama bilgileri şifreli saklanır."), "ikincil"))
        self._rail = rail
        self.setSideWidget(rail)

        g = _Sayfa("Belgeleriniz.\nTek bir arama.", t("Dağınık klasörlerden aradığınız belgeye.\nDeepFind’yı birkaç kısa adımda kullanıma hazırlayın."))
        g.heading.setProperty("hero", True)
        self._dil_degisti = False
        self.dil_secici = QComboBox()
        for kod, ad, _qt, _yerel in LANGUAGES:
            self.dil_secici.addItem(ad, kod)
        _kayitli = resolve_language(QSettings(identity.APP_IDENTITY, "Appearance").value("language", "en"))
        self.dil_secici.setCurrentIndex(max(0, self.dil_secici.findData(_kayitli)))
        self.dil_secici.currentIndexChanged.connect(self._dil_degistir)
        dil_satiri, dil_icerik = card()
        dil_icerik.addWidget(label(t("Arayüz dili"), "subheading"))
        dil_icerik.addWidget(self.dil_secici)
        g.kutu.addWidget(dil_satiri)
        for title, text in [
            (t("Adıyla ya da içeriğiyle bulun"), t("Bir dosya adı, birkaç kelime veya bir yıl yazmanız yeterli.")),
            (t("Klasörler sizden, düzen DeepFind’dan"), t("Bilgisayarınızdaki ve ağdaki belge klasörlerini seçin.")),
            (t("Size özel bir çalışma alanı"), t("İsterseniz şifre belirleyin; arama bilgileriniz bu bilgisayarda korunur."))]:
            panel, content = card()
            content.addWidget(label(title, "subheading"))
            content.addWidget(label(text, "ikincil"))
            g.kutu.addWidget(panel)
        g.kutu.addStretch()
        self.addPage(g)

        s = _Sayfa(t("Şifrenizi belirleyin"), t("Şifre isteğe bağlıdır. Belirlerseniz en az 12 karakter olmalı ve iki kez girilmeli."))
        password_panel, f = card()
        self.s1 = QLineEdit()
        self.s1.setEchoMode(QLineEdit.Password)
        self.s2 = QLineEdit()
        self.s2.setEchoMode(QLineEdit.Password)
        self.s1.setPlaceholderText("En az 12 karakter")
        self.s2.setPlaceholderText(t("Şifrenizi tekrar girin"))
        self.s1.setAccessibleName(t("Yeni şifre"))
        self.s2.setAccessibleName(t("Şifre tekrarı"))
        self.sifre_hata = QLabel("")
        self.sifre_hata.setProperty("hata", True)
        f.addWidget(label(t("Kasa şifresi"), "subheading"))
        f.addWidget(self.s1)
        f.addWidget(label(t("Şifreyi tekrar girin"), "ikincil"))
        f.addWidget(self.s2)
        s.kutu.addWidget(password_panel)
        s.kutu.addWidget(self.sifre_hata)
        self.sifresiz_kutu = QCheckBox(t("Şifre kullanmayacağım — uygulama açılışta şifre sormaz"))
        self.sifresiz_kutu.toggled.connect(self._sifresiz_degistir)
        s.kutu.addWidget(self.sifresiz_kutu)
        show = QCheckBox(t("Şifreyi göster"))
        show.toggled.connect(lambda on: [field.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for field in (self.s1, self.s2)])
        s.kutu.addWidget(show)
        note = QLabel(t("Bu şifreyi uygulamayı açarken kullanacaksınız; sonradan Ayarlar bölümünden ") +
                      t("ekleyebilir veya değiştirebilirsiniz. Şifre belirlemezseniz uygulama her ") +
                      t("açılışta şifre sormaz; koruma Windows hesabınıza bağlı kalır. Şifrenizi ") +
                      t("unutursanız kurtarma anahtarıyla kasayı açabilirsiniz; asıl belgeleriniz ") +
                      "her durumda korunur.")
        note.setWordWrap(True)
        note.setProperty("ikincil", True)
        s.kutu.addWidget(note)
        s.kutu.addStretch()
        self.addPage(s)

        k = _Sayfa(t("Aranacak klasörleri seçin"), t("Aşağıdan bir klasör seçip Ekle’ye basın veya klasör yolunu yazın."))
        ust = QHBoxLayout()
        self.unc = QLineEdit()
        self.unc.setPlaceholderText(t("Klasör yolu • ör. C:\\Belgeler veya \\\\NAS\\Belgeler"))
        self.unc.setAccessibleName(t("Eklenecek klasörün yolu"))
        self.ekle = QPushButton("Ekle")
        self.ekle.setProperty("birincil", True)
        self.ekle.clicked.connect(self._unc_ekle)
        self.unc.returnPressed.connect(self._unc_ekle)
        ust.addWidget(self.unc, 1)
        ust.addWidget(self.ekle)
        k.kutu.addLayout(ust)
        actions = QHBoxLayout()
        browse = QPushButton(t("Klasör seç…"))
        browse.clicked.connect(self._gozat)
        self.yenile = QPushButton(t("Yenile"))
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
        self.agac.setAccessibleName(t("Bilgisayarınızdaki klasörler"))
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
        self.kok_liste.setAccessibleName(t("Aramaya eklenen klasörler"))
        columns = QSplitter(Qt.Horizontal)
        available, available_layout = card()
        available_layout.addWidget(label(t("Bilgisayar ve ağ"), "subheading"))
        available_layout.addWidget(self.agac, 1)
        selected_panel, selected = card()
        self.kok_baslik = QLabel(t("Eklenen klasörler • 0"))
        self.kok_baslik.setProperty("subheading", True)
        remove = QPushButton(t("Seçilenleri kaldır"))
        remove.clicked.connect(self._kaldir)
        selected.addWidget(self.kok_baslik)
        selected.addWidget(label(t("Yalnız bu klasörlerde arama yapılır."), "ikincil"))
        selected.addWidget(self.kok_liste, 1)
        select_all = QPushButton(t("Tümünü seç"))
        select_all.clicked.connect(self.kok_liste.selectAll)
        selected.addWidget(select_all)
        removal = QHBoxLayout()
        removal.addWidget(remove)
        clear = QPushButton(t("Tümünü kaldır"))
        clear.clicked.connect(self._tumunu_kaldir)
        removal.addWidget(clear)
        selected.addLayout(removal)
        columns.addWidget(available)
        columns.addWidget(selected_panel)
        columns.setChildrenCollapsible(False)
        columns.setSizes([360, 320])
        k.kutu.addWidget(columns, 1)
        self.kaynak_mesaj = QLabel(t("Henüz klasör eklenmedi."))
        self.kaynak_mesaj.setWordWrap(True)
        k.kutu.addWidget(self.kaynak_mesaj)
        self.addPage(k)

        r = _Sayfa(t("Şirket kuralı"), t("Örnek yolların nasıl yorumlanacağını kaydetmeden görürsünüz."))
        self.kural = QComboBox()
        self.kural.addItems(["belirlenemiyor", t("bu kök tek şirket"),
                             t("şirket alt klasör seviyesinde")])
        self.kural.currentTextChanged.connect(lambda t: self.secim.update(sirket_kurali=t))
        self.ornek = QLabel("")
        self.ornek.setProperty("ikincil", True)
        self.ornek.setWordWrap(True)
        r.kutu.addWidget(QLabel(t("Kök başına kural:")))
        r.kutu.addWidget(self.kural)
        r.kutu.addWidget(self.ornek)
        r.kutu.addWidget(label(t("Bu seçim, dosyalarınıza dokunmadan arama sonuçlarının klasör bağlamını belirler."), "ikincil"))
        r.kutu.addStretch()
        self.addPage(r)

        o = _Sayfa(t("Her şey yerli yerinde."), t("“Kurulumu tamamla” ile ilk taramayı başlatın. Belgelerinizin sayısına göre bu biraz zaman alabilir."))
        self.ozet = QLabel("")
        self.ozet.setWordWrap(True)
        summary_panel, summary_layout = card()
        summary_layout.addWidget(label(t("Çalışma alanınız"), "subheading"))
        summary_layout.addWidget(self.ozet)
        o.kutu.addWidget(summary_panel)
        o.kutu.addWidget(label(t("Belgeleriniz taşınmaz veya değiştirilmez. Tarama sürerken uygulamayı kullanabilirsiniz."), "ikincil"))
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
            self._mesaj(t("Önce listeden bir klasör seçin veya klasör yolunu yazın."))
            return
        yol = os.path.abspath(os.path.normpath(yol))
        if not os.path.isdir(yol):
            self._mesaj(t("Bu klasöre ulaşılamıyor. Yolu ve bağlantınızı kontrol edin; bir dosya değil, klasör seçin."))
            return
        keys = {os.path.normcase(os.path.normpath(p)) for p in self.secim["kokler"]}
        if os.path.normcase(yol) in keys:
            self._mesaj(t("Bu klasör zaten eklendi."))
            return
        self.secim["kokler"].append(yol)
        self.unc.clear()
        self._tazele()
        self._mesaj(t("Klasör eklendi. İsterseniz başka klasörler de ekleyebilirsiniz."))

    def _gozat(self):
        yol = QFileDialog.getExistingDirectory(self, t("Aranacak klasörü seçin"))
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
        self._mesaj(t("Klasör listesi yenilendi. Eklediğiniz klasörler korundu."))

    def _tema_degistir(self):
        from . import theme
        from PySide6.QtWidgets import QApplication
        self.secim["tema"] = self.tema.currentData()
        self.theme_button.setText("Tema: " + self.tema.currentText())
        theme.apply(QApplication.instance(), self.tema.currentData())

    def _dil_degistir(self):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from . import identity
        from . import theme
        kod = self.dil_secici.currentData() or 'en'
        QSettings(identity.APP_IDENTITY, 'Appearance').setValue('language', kod)
        theme.set_language(kod)
        install_language(QApplication.instance(), kod)
        self._dil_degisti = True
        self.reject()

    def _tumunu_kaldir(self):
        self.secim["kokler"].clear()
        self._tazele()
        self._mesaj(t("Arama listesi temizlendi. Asıl klasörler korunuyor."))

    def _sifresiz_degistir(self, on):
        """'Şifre kullanmayacağım' işaretlenince alanlar kapanır ve temizlenir."""
        for field in (self.s1, self.s2):
            field.setEnabled(not on)
            if on:
                field.clear()
        if on:
            self.sifre_hata.setText("")

    def _kaldir(self):
        rows = sorted({i.row() for i in self.kok_liste.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.secim["kokler"].pop(row)
        self._tazele()
        self._mesaj(t("Seçilen klasörler arama listesinden kaldırıldı.") if rows else t("Önce kaldırılacak klasörleri seçin."))

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
            if self.sifresiz_kutu.isChecked() or not (self.s1.text() or self.s2.text()):
                sifre_satiri = (t("Şifre: Yok (açılışta sorulmaz)\n")
                                + t("Arama bilgileriniz bu bilgisayarda korunur."))
            else:
                sifre_satiri = (t("Şifre: Belirlendi\n") +
                                t("Arama bilgileriniz şifreli saklanır."))
            self.ozet.setText(f"Kök: {len(self.secim['kokler'])} adet\n"
                              f"Tema: {self.tema.currentText()}\n"
                              f"{sifre_satiri}")

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
            if self.sifresiz_kutu.isChecked() or not (a or b):
                # Şifre isteğe bağlı: boş bırakılırsa kasa şifresiz kurulur.
                self.sifre_hata.setText("")
                self.secim["sifre"] = ""
                return super().validateCurrentPage()
            if len(a) < 12:
                self.sifre_hata.setText(t("Şifre en az 12 karakter olmalı. Şifre kullanmayacaksanız ") +
                                        t("“Şifre kullanmayacağım” seçeneğini işaretleyin."))
                return False
            if a != b:
                self.sifre_hata.setText(t("Şifreler eşleşmiyor."))
                return False
            self.sifre_hata.setText("")
            self.secim["sifre"] = a
        if self.currentPage() is self.page(2) and not self.secim["kokler"]:
            self._mesaj(t("Devam etmek için en az bir klasör ekleyin."))
            return False
        return super().validateCurrentPage()
