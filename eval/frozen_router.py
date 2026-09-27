"""Donmus router-calismasi: tembel import + init adimlari dosya loglu (A8)."""
import os
import sys

LOG = "C:/Users/user/Temp/evrakci_frozen/router.log"


def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(m, flush=True)


def main():
    if os.path.exists(LOG):
        os.remove(LOG)
    log("R0 basladi")
    args = list(sys.argv[1:])
    log(f"R1 argv={len(args)}")
    ilk = next((a for a in args if not a.startswith("-")), None)
    log(f"R2 ilk={ilk}")
    from evrakci.cli import main as cli_main  # noqa: E402
    log("R3 cli import OK")
    kod = cli_main(args)
    log(f"R4 bitti kod={kod}")
    return kod


if __name__ == "__main__":
    raise SystemExit(main())
