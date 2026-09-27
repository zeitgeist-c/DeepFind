"""Kasa giriş ve parola yenileme ekranları."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QCheckBox, QFrame, QHBoxLayout)
from .ui import brand as draw_brand, label


class ParolaDialog(QDialog):
    def __init__(self, parent=None, *, change=False, verify=None, allow_remember=True):
        super().__init__(parent)
        from .theme import app_icon
        self.setWindowIcon(app_icon())
        self.change = change
        self.verify = verify
        self.setWindowTitle("Evrakçı • Şifre değiştir" if change else "Evrakçı • Kasa kilitli")
        self.setMinimumWidth(800)
        self.resize(820, 650 if change else 540)
        self.setObjectName("auth")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(14)
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(246)
        side = QVBoxLayout(rail)
        side.setContentsMargins(24, 28, 24, 28)
        draw_brand(side)
        side.addStretch()
        from .theme import symbol_icon
        lock = QLabel()
        lock.setPixmap(symbol_icon("lock", "#70D6BC").pixmap(62, 62))
        side.addWidget(lock)
        side.addWidget(label("Belgeleriniz.\nSize özel.", "baslik"))
        side.addWidget(label("Şifreli çalışma alanınız\nbu bilgisayarda saklanır.", "ikincil"))
        side.addStretch()
        side.addWidget(label("YEREL VE ŞİFRELİ", "eyebrow"))
        outer.addWidget(rail)
        form = QFrame()
        form.setObjectName("card")
        outer.addWidget(form, 1)
        layout = QVBoxLayout(form)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(13)
        layout.addWidget(label("KASA GÜVENLİĞİ" if change else "GÜVENLİ GİRİŞ", "eyebrow"))
        title = QLabel("Yeni bir şifre belirleyin" if change else "Arşivinize\ngüvenle dönün.")
        title.setWordWrap(True)
        title.setProperty("hero", True)
        layout.addWidget(title)
        desc = QLabel("Mevcut şifrenizi doğrulayın ve yeni şifrenizi iki kez girin."
                      if change else "Belgelerinize ulaşmak için yerel kasanızın kilidini açın.")
        desc.setWordWrap(True)
        desc.setProperty("ikincil", True)
        layout.addWidget(desc)
        layout.addSpacing(8)
        self.old = QLineEdit()
        self.old.setPlaceholderText("Mevcut şifre" if change else "Kasa şifresi")
        self.old.setEchoMode(QLineEdit.Password)
        self.old.setAccessibleName(self.old.placeholderText())
        layout.addWidget(self.old)
        self.new = QLineEdit()
        self.confirm = QLineEdit()
        for field, caption in ((self.new, "Yeni şifre • en az 12 karakter"),
                             (self.confirm, "Yeni şifreyi tekrar girin")):
            field.setEchoMode(QLineEdit.Password)
            field.setPlaceholderText(caption)
            field.setAccessibleName(caption)
            if change:
                layout.addWidget(field)
        show = QCheckBox("Şifreyi göster")
        show.toggled.connect(lambda on: [f.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for f in (self.old, self.new, self.confirm)])
        layout.addWidget(show)
        self.remember = QCheckBox("Beni hatırla")
        self.remember.setToolTip("Bu Windows hesabında otomatik giriş yapar ve otomatik kilidi kapatır. Elle kilitleme şifre ister.")
        if not change and allow_remember:
            layout.addWidget(self.remember)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setProperty("hata", True)
        layout.addWidget(self.error)
        submit = QPushButton("Şifreyi değiştir" if change else "Kasayı aç")
        submit.setProperty("birincil", True)
        submit.setDefault(True)
        submit.clicked.connect(self._submit)
        layout.addWidget(submit)
        cancel = QPushButton("Vazgeç" if change else "Çıkış")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)
        note = QLabel("Şifreniz unutulursa şifreli indeks açılamaz. Kaynak belgeleriniz korunur.")
        note.setProperty("ikincil", True)
        note.setWordWrap(True)
        layout.addWidget(note)

    def _submit(self):
        if not self.old.text():
            self.error.setText("Şifrenizi girin.")
            return
        if self.change:
            if len(self.new.text()) < 12:
                self.error.setText("Yeni şifre en az 12 karakter olmalı.")
                return
            if self.new.text() != self.confirm.text():
                self.error.setText("Yeni şifreler eşleşmiyor.")
                return
            if self.new.text() == self.old.text():
                self.error.setText("Yeni şifre mevcut şifreden farklı olmalı.")
                return
        if self.verify:
            try:
                self.verify(self.old.text())
            except Exception:
                self.error.setText("Kasa açılamadı. Şifreyi ve kasa dosyasını kontrol edin.")
                self.old.selectAll()
                self.old.setFocus()
                return
        self.accept()
