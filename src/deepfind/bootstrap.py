"""Prepare the first vault without stalling the UI; never touch source files."""
import os
from PySide6.QtCore import QObject, Signal
from . import vault, migrate
from .theme import t


class Bootstrap(QObject):
    done = Signal()
    error = Signal(str)

    def __init__(self, path, password, selection):
        super().__init__()
        self.path, self.password, self.selection = path, password, selection

    def run(self):
        con = None
        try:
            con = vault.open_vault(self.path, self.password)
            migrate.ensure_current(con)
            for root in self.selection['kokler']:
                con.execute("INSERT OR IGNORE INTO roots(display_path, canonical_path, company_rule) VALUES (?,?,?)",
                            (root, os.path.normpath(root).lower(), self.selection['sirket_kurali']))
            con.commit()
            migrate.set_setting(con, "tema", self.selection['tema'])
            migrate.set_setting(con, "kurulum_tamam", "1")
            migrate.set_setting(con, "kasa_sifresiz",
                                "1" if self.password == vault.SIFRESIZ_ANAHTAR else "0")
            self.done.emit()
        except Exception as error:
            self.error.emit(t("Kurulum tamamlanamadı: {error}", error=error))
        finally:
            if con is not None:
                con.close()
            self.password = ""
