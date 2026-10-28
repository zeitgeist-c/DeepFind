"""Kasa giriş, parola yenileme ve kurtarma anahtarı ekranları."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QCheckBox, QFrame, QHBoxLayout)
from .ui import brand as draw_brand, label
from .theme import t

# Dialog kapanış kodu: kullanıcı "şifremi unuttum" istedi.
MOD_KURTARMA = 2


class ParolaDialog(QDialog):
    """Kasa girişi, şifre değiştirme ve kurtarma anahtarıyla açma.

    `mode`: "giris" (varsayılan) | "degistir" | "kurtarma".
    Geriye dönük uyumluluk: `change=True` -> mode="degistir".
    """

    def __init__(self, parent=None, *, change=False, verify=None, allow_remember=True,
                 mode=None, kasa_yolu=None):
        super().__init__(parent)
        from .theme import app_icon, t
        self.setWindowIcon(app_icon())
        self.verify = verify
        self.kasa_yolu = kasa_yolu
        self.mode = mode or ("degistir" if change else "giris")
        self.change = self.mode in ("degistir", "ekle")
        pencere, eyebrow, hero, aciklama = {
            "giris": ("DeepFind • Kasa kilitli", t("Güvenli giriş"), t("Arşivinize\ngüvenle dönün."),
                      t("Belgelerinize ulaşmak için yerel kasanızın kilidini açın.")),
            "degistir": (t("DeepFind • Şifre değiştir"), t("Kasa güvenliği"), t("Yeni bir şifre belirleyin"),
                         t("Mevcut şifrenizi doğrulayın ve yeni şifrenizi iki kez girin.")),
            "ekle": (t("DeepFind • Şifre ekle"), t("Kasa güvenliği"), t("Uygulama şifresi ekleyin"),
                     t("Sonraki açılışlarda kasa bu şifreyle açılır. Şifre en az 12 karakter olmalı ") +
                     "ve iki kez girilmeli."),
            "kurtarma": (t("DeepFind • Kurtarma anahtarı"), "Kurtarma", t("Anahtarla kasayı açın"),
                         t("Kasa şifrenizi unuttuysanız kurtarma anahtarınızı yapıştırın; ") +
                         t("ardından yeni bir şifre belirleyeceksiniz.")),
        }[self.mode]
        self.setWindowTitle(pencere)
        self.setMinimumWidth(760)
        self.resize(780, 640 if self.change else 520)
        self.setObjectName("auth")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(250)
        side = QVBoxLayout(rail)
        side.setContentsMargins(26, 30, 26, 30)
        side.setSpacing(10)
        draw_brand(side)
        side.addStretch()
        from .theme import symbol_icon, pal
        simge = QLabel()
        simge.setPixmap(symbol_icon("check" if self.mode == "kurtarma" else "lock",
                                    pal()["marka"]).pixmap(52, 52))
        side.addWidget(simge)
        if self.mode == "kurtarma":
            side.addWidget(label(t("Kurtarma anahtarı\nyalnız sizde."), "baslik"))
            side.addWidget(label(t("Anahtar kasayı açar;\nbelgeleriniz değişmez."), "ikincil"))
        else:
            side.addWidget(label(t("Belgeleriniz.\nSize özel."), "baslik"))
            side.addWidget(label(t("Şifreli çalışma alanınız\nbu bilgisayarda saklanır."), "ikincil"))
        side.addStretch()
        side.addWidget(label(t("Yerel ve şifreli"), "eyebrow"))
        outer.addWidget(rail)
        form = QFrame()
        form.setObjectName("card")
        form.setStyleSheet("QFrame#card { border: none; border-radius: 0px; }")
        outer.addWidget(form, 1)
        layout = QVBoxLayout(form)
        layout.setContentsMargins(38, 34, 38, 34)
        layout.setSpacing(12)
        layout.addWidget(label(eyebrow, "eyebrow"))
        self.baslik = QLabel(hero)
        self.baslik.setWordWrap(True)
        self.baslik.setProperty("hero", True)
        layout.addWidget(self.baslik)
        self.aciklama = QLabel(aciklama)
        self.aciklama.setWordWrap(True)
        self.aciklama.setProperty("ikincil", True)
        layout.addWidget(self.aciklama)
        layout.addSpacing(6)

        self.old = QLineEdit()
        self.old.setEchoMode(QLineEdit.Password)
        self.new = QLineEdit()
        self.confirm = QLineEdit()
        self.submit = QPushButton("")
        self.recovery_btn = None
        self.giris_btn = None
        self._alanlari_kur(layout)
        self.remember = QCheckBox(t("Beni hatırla"))
        self.remember.setToolTip(t("Bu Windows hesabında otomatik giriş yapar ve otomatik kilidi kapatır. Elle kilitleme şifre ister."))
        if self.mode == "giris" and allow_remember:
            layout.addWidget(self.remember)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setProperty("hata", True)
        layout.addWidget(self.error)
        layout.addWidget(self.submit)
        self._alt_dugme(layout)
        cancel = QPushButton(t("Vazgeç") if self.change else t("Çıkış"))
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)
        if self.mode == "kurtarma":
            not_metni = (t("Kurtarma anahtarınız yoksa kasa açılamaz; kaynak belgeleriniz korunur, ") +
                         t("varsa eski yedeklerinizden geri dönebilirsiniz."))
        elif self.mode == "degistir":
            not_metni = (t("Şifreniz unutulursa kurtarma anahtarınızla kasayı açabilirsiniz. ") +
                         t("Şifre değişince kurtarma anahtarı kendiliğinden yenilenir."))
        elif self.mode == "ekle":
            not_metni = (t("Şifre eklendikten sonra sonraki açılışlarda bu şifre sorulur. ") +
                         t("Kurtarma anahtarı kendiliğinden oluşturulur; Ayarlar bölümünden ") +
                         t("görüntüleyebilirsiniz."))
        else:
            not_metni = (t("Şifrenizi unuttuysanız kurtarma anahtarınızla kasayı açabilirsiniz. ") +
                         "Kaynak belgeleriniz her durumda korunur.")
        notu = QLabel(not_metni)
        notu.setProperty("ikincil", True)
        notu.setWordWrap(True)
        layout.addWidget(notu)

    def _alanlari_kur(self, layout):
        if self.mode == "kurtarma":
            self.old.setEchoMode(QLineEdit.Normal)
            self.old.setPlaceholderText(t("EVKC-… kurtarma anahtarı"))
            self.old.setAccessibleName(t("Kurtarma anahtarı"))
            layout.addWidget(self.old)
            for field, caption in ((self.new, t("Yeni şifre • en az 12 karakter")),
                                   (self.confirm, t("Yeni şifreyi tekrar girin"))):
                field.setEchoMode(QLineEdit.Password)
                field.setPlaceholderText(caption)
                field.setAccessibleName(caption)
                layout.addWidget(field)
            self.submit.setText(t("Kurtarma anahtarıyla aç"))
            return
        if self.mode == "ekle":
            # Şifresiz kasaya şifre ekleme: mevcut şifre alanı yok.
            for field, caption in ((self.new, t("Yeni şifre • en az 12 karakter")),
                                   (self.confirm, t("Yeni şifreyi tekrar girin"))):
                field.setEchoMode(QLineEdit.Password)
                field.setPlaceholderText(caption)
                field.setAccessibleName(caption)
                layout.addWidget(field)
            self.submit.setText(t("Şifre ekle"))
            return
        self.old.setPlaceholderText(t("Mevcut şifre") if self.change else t("Kasa şifresi"))
        self.old.setAccessibleName(self.old.placeholderText())
        layout.addWidget(self.old)
        if self.change:
            for field, caption in ((self.new, t("Yeni şifre • en az 12 karakter")),
                                   (self.confirm, t("Yeni şifreyi tekrar girin"))):
                field.setEchoMode(QLineEdit.Password)
                field.setPlaceholderText(caption)
                field.setAccessibleName(caption)
                layout.addWidget(field)
        else:
            show = QCheckBox(t("Şifreyi göster"))
            show.toggled.connect(lambda on: self.old.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password))
            layout.addWidget(show)
        self.submit.setText(t("Şifreyi değiştir") if self.change else t("Kasayı aç"))

    def _alt_dugme(self, layout):
        self.submit.setProperty("birincil", True)
        self.submit.setDefault(True)
        self.submit.clicked.connect(self._submit)
        if self.mode == "giris":
            self.recovery_btn = QPushButton(t("Şifremi unuttum"))
            self.recovery_btn.setProperty("ghost", True)
            self.recovery_btn.setToolTip(t("Kurtarma anahtarınız varsa kasayı açabilirsiniz"))
            self.recovery_btn.clicked.connect(lambda: self.done(MOD_KURTARMA))
            layout.addWidget(self.recovery_btn)
        elif self.mode == "kurtarma":
            self.giris_btn = QPushButton(t("Şifremi biliyorum"))
            self.giris_btn.setProperty("ghost", True)
            self.giris_btn.clicked.connect(self.reject)
            layout.addWidget(self.giris_btn)

    def kurtarma_istendi(self) -> bool:
        return self.result() == MOD_KURTARMA

    def _submit(self):
        if self.mode == "kurtarma":
            if not self.old.text().strip():
                self.error.setText(t("Kurtarma anahtarını girin."))
                return
            if len(self.new.text()) < 12:
                self.error.setText(t("Yeni şifre en az 12 karakter olmalı."))
                return
            if self.new.text() != self.confirm.text():
                self.error.setText(t("Yeni şifreler eşleşmiyor."))
                return
            if self.verify:
                try:
                    self.verify(("kurtarma", self.old.text().strip(), self.new.text()))
                except Exception as error:
                    self.error.setText(str(error) or t("Kurtarma tamamlanamadı."))
                    self.old.selectAll()
                    self.old.setFocus()
                    return
            self.accept()
            return
        if self.mode == "ekle":
            if len(self.new.text()) < 12:
                self.error.setText(t("Yeni şifre en az 12 karakter olmalı."))
                return
            if self.new.text() != self.confirm.text():
                self.error.setText(t("Yeni şifreler eşleşmiyor."))
                return
            if self.verify:
                try:
                    self.verify(self.new.text())
                except Exception as error:
                    self.error.setText(str(error) or t("Şifre eklenemedi."))
                    return
            self.accept()
            return
        if not self.old.text():
            self.error.setText(t("Şifrenizi girin."))
            return
        if self.change:
            if len(self.new.text()) < 12:
                self.error.setText(t("Yeni şifre en az 12 karakter olmalı."))
                return
            if self.new.text() != self.confirm.text():
                self.error.setText(t("Yeni şifreler eşleşmiyor."))
                return
            if self.new.text() == self.old.text():
                self.error.setText(t("Yeni şifre mevcut şifreden farklı olmalı."))
                return
        if self.verify:
            try:
                self.verify(self.old.text())
            except Exception:
                self.error.setText(t("Kasa açılamadı. Şifreyi ve kasa dosyasını kontrol edin."))
                self.old.selectAll()
                self.old.setFocus()
                return
        self.accept()
