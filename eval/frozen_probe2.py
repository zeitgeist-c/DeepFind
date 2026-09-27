"""Donmus sema-zincir probu (repo disi tani, A8)."""
import sys


def log(m):
    print(m, flush=True)


log("0 basladi")
from evrakci import vault  # noqa: E402

log("1 vault import OK")
from evrakci import schema  # noqa: E402

log("2 schema import OK")
db = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/user/Temp/evrakci_frozen/probe2.db"
import os  # noqa: E402

for s in ("", "-wal", "-shm"):
    try:
        os.remove(db + s)
    except OSError:
        pass
con = vault.open_vault(db, "probe-sifre-1234")
log("3 open_vault OK")
schema.ensure_schema(con)
log("4 ensure_schema OK")
from evrakci.vocab import ensure_v5  # noqa: E402

ensure_v5(con)
log("5 ensure_v5 OK")
from evrakci.migrate import ensure_v6, ensure_v7  # noqa: E402

ensure_v6(con)
log("6 ensure_v6 OK")
ensure_v7(con)
log("7 ensure_v7 OK")
con.close()
log("8 bitti")
