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
from .theme import LANGUAGES, app_icon, install_language, resolve_language, t
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
        self.setButtonText(QWizard.BackButton, t("Geri"))
        self.setButtonText(QWizard.NextButton, t("İleri"))
        self.setButtonText(QWizard.FinishButton, t("Kurulumu tamamla"))
        self.setButtonText(QWizard.CancelButton, t("Vazgeç"))
        self.setButtonText(QWizard.HelpButton, t("Yardım"))
        self.secim = {"kokler": [], "tema": "sistem", "sirket_kurali": "belirlenemiyor",
                      "embedding_backend": "auto"}
        self.tema = QComboBox(self)
        for caption, value in [(t("Sistem teması"), "sistem"), (t("Açık tema"), "acik"), (t("Koyu tema"), "koyu")]:
            self.tema.addItem(caption, value)
        self.setOption(QWizard.HaveCustomButton1)
        from PySide6.QtWidgets import QMenu
        self.tema.hide()
        self.theme_button = QPushButton(t("Tema") + ": " + t("Sistem teması"))
        menu = QMenu(self.theme_button)
        self._theme_menu = menu
        for index, caption in enumerate((t("Sistem teması"), t("Açık tema"), t("Koyu tema"))):
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
        for i, title in enumerate((t("Hoş geldiniz"), t("Klasörler"),
                                   t("Çalışma motoru"), t("Son kontrol"))):
            step = label(f"{i + 1:02d}   {title}")
            step.setObjectName("step")
            rail_layout.addWidget(step)
            self.steps.append(step)
        rail_layout.addStretch()
        rail_layout.addWidget(bolme())
        rail_layout.addSpacing(14)
        rail_layout.addWidget(label(t("Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır."), "ikincil"))
        self._rail = rail
        self.setSideWidget(rail)

        g = _Sayfa("Belgeleriniz.\nTek bir arama.", t("Dağınık klasörlerden aradığınız belgeye.\nDeepFind’yı birkaç kısa adımda kullanıma hazırlayın."))
        g.heading.setProperty("hero", True)
        self._dil_degisti = False
        self.dil_secici = QComboBox()
        for kod, ad, _qt, _yerel in LANGUAGES:
            self.dil_secici.addItem(ad, kod)
        # Long names and scaled fonts must not clip the closed combo box.
        _metin = self.dil_secici.fontMetrics()
        _genislik = max(_metin.horizontalAdvance(self.dil_secici.itemText(i))
                        for i in range(self.dil_secici.count()))
        self.dil_secici.setMinimumWidth(_genislik + 64)
        self.dil_secici.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.dil_secici.view().setMinimumWidth(self.dil_secici.minimumWidth())
        self.dil_secici.setAccessibleName(t("Arayüz dili"))
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
            (t("Size özel bir çalışma alanı"), t("Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur."))]:
            panel, content = card()
            content.addWidget(label(title, "subheading"))
            content.addWidget(label(text, "ikincil"))
            g.kutu.addWidget(panel)
        g.kutu.addStretch()
        self.addPage(g)

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
        self.kok_baslik = QLabel(t("Eklenen klasörler • {count}", count=0))
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

        m = _Sayfa(t("Çalışma motoru"),
                   t("Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner."))
        motor_panel, motor_kutu = card()
        motor_kutu.addWidget(label(t("Nasıl çalışsın?"), "subheading"))
        from PySide6.QtWidgets import QButtonGroup, QRadioButton
        from . import engine
        self.motor_grup = QButtonGroup(self)
        self.motor_dugme = {}
        mevcut = {row["key"]: row for row in engine.motor_secenekleri()}
        motor_metinleri = [
            ("auto", t("Önerilen: otomatik (ekran kartı, olmazsa işlemci)"),
             t("Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.")),
            ("cpu", t("Yalnız işlemci (CPU)"),
             t("Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.")),
            ("vulkan", t("Ekran kartı (Vulkan)"),
             t("Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.")),
            ("cuda", t("NVIDIA ekran kartı (CUDA)"),
             t("NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.")),
        ]
        for anahtar, baslik, aciklama in motor_metinleri:
            row = mevcut.get(anahtar, {})
            kurulu = bool(row.get("installed"))
            metin = baslik if kurulu else baslik + " — " + t("kurulu değil")
            secenek = QRadioButton(metin)
            secenek.setEnabled(kurulu or anahtar == "auto")
            if anahtar == "cuda" and not kurulu:
                secenek.setToolTip(t("Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz."))
            self.motor_grup.addButton(secenek)
            self.motor_dugme[anahtar] = secenek
            motor_kutu.addWidget(secenek)
            ipucu = label(aciklama, "ikincil")
            ipucu.setWordWrap(True)
            motor_kutu.addWidget(ipucu)
        motor_kutu.addWidget(label(t("Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz."), "ikincil"))
        m.kutu.addWidget(motor_panel)
        self.motor_durum = QLabel("")
        self.motor_durum.setWordWrap(True)
        m.kutu.addWidget(self.motor_durum)
        m.kutu.addStretch()
        self.addPage(m)
        self.motor_dugme["auto"].setChecked(True)
        for anahtar, secenek in self.motor_dugme.items():
            secenek.toggled.connect(lambda on, k=anahtar: self._motor_sec(k, on))
        self._motor_sec("auto", True)

        o = _Sayfa(t("Her şey yerli yerinde."), t("“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın."))
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
        self.theme_button.setText(t("Tema") + ": " + self.tema.currentText())
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

    def _kaldir(self):
        rows = sorted({i.row() for i in self.kok_liste.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.secim["kokler"].pop(row)
        self._tazele()
        self._mesaj(t("Seçilen klasörler arama listesinden kaldırıldı.") if rows else t("Önce kaldırılacak klasörleri seçin."))

    def _motor_sec(self, anahtar, secili):
        """Record the engine choice and surface any failed-GPU fallback."""
        from . import engine
        if not secili:
            return
        self.secim["embedding_backend"] = anahtar
        satirlar = []
        for row in engine.motor_secenekleri():
            ad = row["key"].upper() if row["key"] != "auto" else t("Otomatik")
            if row["installed"]:
                boyut = f" ({row['size_mb']} MB)" if row["size_mb"] else ""
                satirlar.append(f"{ad}: " + t("kurulu") + boyut)
            else:
                ek = f" — {t('yaklaşık {size} MB, indirilebilir', size=row['size_mb'])}" if row["size_mb"] else ""
                satirlar.append(f"{ad}: " + t("kurulu değil") + ek)
        if anahtar == "auto":
            satirlar.append(t("Ekran kartı denemesi başarısız olursa arama işlemcide sürer; "
                              "hangi birimin kullanıldığı durum alanında yazar."))
        elif anahtar == "cuda" and not self.motor_dugme["cuda"].isEnabled():
            satirlar.append(t("CUDA motoru bu kurulumda bulunamadı; kurulumu onarın."))
        self.motor_durum.setText("\n".join(satirlar))

    def _tazele(self):
        self.kok_model.clear()
        for path in self.secim["kokler"]:
            title = Path(path).name or path
            item = QStandardItem(title + "\n" + path)
            item.setToolTip(path)
            item.setEditable(False)
            self.kok_model.appendRow(item)
        self.kok_baslik.setText(t("Eklenen klasörler • {count}", count=len(self.secim["kokler"])))
        if self.secim["kokler"]:
            motor_ad = (self.motor_dugme[self.secim['embedding_backend']].text()
                        if self.secim['embedding_backend'] in self.motor_dugme
                        else t("Otomatik"))
            self.ozet.setText(t("Kök: {count} adet\n", count=len(self.secim['kokler']))
                              + t("Tema") + f": {self.tema.currentText()}\n"
                              + t("Motor") + f": {motor_ad}\n"
                              + t("Kasa: şifresiz\n")
                              + t("Arama bilgileriniz bu bilgisayarda saklanır."))

    def _sayfa(self, _i):
        self._tazele()
        for i, step in enumerate(self.steps):
            step.setProperty("active", i == max(0, _i))
            step.setProperty("done", 0 <= i < _i)
            step.style().unpolish(step)
            step.style().polish(step)

    def validateCurrentPage(self):
        # Sifre kaldirildi: kasa her zaman sifresiz kurulur.
        self.secim["sifre"] = ""
        if self.currentPage() is self.page(1) and not self.secim["kokler"]:
            self._mesaj(t("Devam etmek için en az bir klasör ekleyin."))
            return False
        return super().validateCurrentPage()
