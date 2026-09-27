"""Kasa giriş ve parola yenileme ekranları."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QCheckBox)


class ParolaDialog(QDialog):
    def __init__(self, parent=None, *, change=False, verify=None):
        super().__init__(parent)
        from .theme import app_icon
        self.setWindowIcon(app_icon())
        self.change = change
        self.verify = verify
        self.setWindowTitle("Evrakçı • Şifre değiştir" if change else "Evrakçı • Kasa kilitli")
        self.setMinimumWidth(460)
        self.setObjectName("auth")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(16)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(48, 48))
        logo.setAccessibleName("Evrakçı logosu")
        layout.addWidget(logo)
        brand = QLabel("EVRAKÇI  /  GÜVENLİ ARŞİV")
        brand.setProperty("ikincil", True)
        layout.addWidget(brand)
        title = QLabel("Şifrenizi yenileyin" if change else "Arşivinize hoş geldiniz")
        title.setProperty("baslik", True)
        layout.addWidget(title)
        desc = QLabel("Mevcut şifrenizi doğrulayın ve yeni şifrenizi iki kez girin."
                      if change else "Belgelerinize ulaşmak için yerel kasanızın kilidini açın.")
        desc.setWordWrap(True)
        desc.setProperty("ikincil", True)
        layout.addWidget(desc)
        self.old = QLineEdit()
        self.old.setPlaceholderText("Mevcut şifre" if change else "Kasa şifresi")
        self.old.setEchoMode(QLineEdit.Password)
        self.old.setAccessibleName(self.old.placeholderText())
        layout.addWidget(self.old)
        self.new = QLineEdit()
        self.confirm = QLineEdit()
        for field, label in ((self.new, "Yeni şifre • en az 12 karakter"),
                             (self.confirm, "Yeni şifreyi tekrar girin")):
            field.setEchoMode(QLineEdit.Password)
            field.setPlaceholderText(label)
            field.setAccessibleName(label)
            if change:
                layout.addWidget(field)
        show = QCheckBox("Şifreyi göster")
        show.toggled.connect(lambda on: [f.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for f in (self.old, self.new, self.confirm)])
        layout.addWidget(show)
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
