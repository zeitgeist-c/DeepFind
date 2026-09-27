"""Donmus _load+init probu (repo disi tani, A8)."""
import sys


def log(m):
    print(m, flush=True)


log("0 basladi")
sys.path.insert(0, "src")
from evrakci import vault, schema, scan, extract, index, search  # noqa: E402

log("1 grup1 import OK")
from evrakci import coordinator, exclusions, history, rank, vocab  # noqa: E402

log("2 grup2 import OK")
from evrakci.migrate import ensure_v4, ensure_v6, ensure_v7  # noqa: E402

log("3 migrate import OK")
db = "C:/Users/user/Temp/evrakci_frozen/probe3.db"
import os  # noqa: E402

os.makedirs(os.path.dirname(db), exist_ok=True)
for s in ("", "-wal", "-shm"):
    try:
        os.remove(db + s)
    except OSError:
        pass
con = vault.open_vault(db, "probe-sifre-1234")
log("4 open OK")
schema.ensure_schema(con)
ensure_v4(con)
log("5 schema+v4 OK")
vocab.ensure_v5(con)
log("6 v5 OK")
ensure_v6(con)
ensure_v7(con)
log("7 v6+v7 OK")
con.close()
log("8 close OK - bitti")
