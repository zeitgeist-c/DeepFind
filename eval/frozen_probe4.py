"""Donmus gercek-CLI probu (repo disi tani, A8)."""
import sys


def log(m):
    print(m, flush=True)


log("0 basladi")
from evrakci.cli import main  # noqa: E402

log("1 cli import OK")
db = "C:/Users/user/Temp/evrakci_frozen/probe4.db"
import os  # noqa: E402

for s in ("", "-wal", "-shm"):
    try:
        os.remove(db + s)
    except OSError:
        pass
log("2 cagri oncesi")
kod = main(["--kasa", db, "--sifre", "probe-sifre-1234", "init"])
log(f"3 init bitti kod={kod}")
kod = main(["--kasa", db, "--sifre", "probe-sifre-1234", "tani"])
log(f"4 tani bitti kod={kod}")
