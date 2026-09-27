"""Donmus sqlcipher adim probu (repo disi tani, A8)."""
import sys


def log(m):
    print(m, flush=True)


log("0 basladi")
import sqlcipher3  # noqa: E402

log("1 sqlcipher3 import OK")
db = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/user/Temp/evrakci_frozen/probe.db"
log(f"2 connect {db}")
con = sqlcipher3.connect(db, timeout=10)
log("3 connect OK")
con.execute("PRAGMA key='probe-sifre-1234'")
log("4 key OK")
con.execute("SELECT count(*) FROM sqlite_master").fetchone()
log("5 validate OK")
row = con.execute("PRAGMA cipher_version").fetchone()
log(f"6 cipher_version={row}")
con.execute("PRAGMA journal_mode=WAL")
log("7 wal OK")
con.execute("CREATE TABLE IF NOT EXISTS t(a)")
con.commit()
log("8 ddl OK")
con.close()
log("9 bitti")
