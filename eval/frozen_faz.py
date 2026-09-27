"""Donmus faz probu: dosya-loglu, PySide6 x SQLCipher etkilesimi (A8 tani)."""
import os
import sys
import traceback

LOG = "C:/Users/user/Temp/evrakci_frozen/faz.log"


def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(m, flush=True)


def main():
    if os.path.exists(LOG):
        os.remove(LOG)
    log("A0 basladi")
    sys.path.insert(0, "src")
    from evrakci import vault  # noqa: E402
    log("A1 vault import OK")
    try:
        c = vault.open_vault("C:/Users/user/Temp/evrakci_frozen/k.db", "donmus-sifre-1234")
        n = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        c.close()
        log(f"A2 dev-db frozen-acis OK belge={n}")
    except Exception:
        log("A2 dev-db frozen-acis FAIL")
        log(traceback.format_exc()[-800:])
    try:
        import evrakci.app  # noqa: E402
        log("A3 app/PySide6 import OK")
    except Exception:
        log("A3 app import FAIL")
        log(traceback.format_exc()[-800:])
    try:
        c = vault.open_vault("C:/Users/user/Temp/evrakci_frozen/k.db", "donmus-sifre-1234")
        n = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        c.close()
        log(f"A4 pyside-sonrasi-acis OK belge={n}")
    except Exception:
        log("A4 pyside-sonrasi-acis FAIL")
        log(traceback.format_exc()[-800:])
    log("A5 bitti")


if __name__ == "__main__":
    main()
