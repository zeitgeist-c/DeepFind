"""Donmus import-bisect: her modulu sirayla dener, dosya logu (A8 tani)."""
import os
import sys
import traceback

LOG = "C:/Users/user/Temp/evrakci_frozen/bisect.log"

MODS = ["evrakci.scan", "evrakci.extract", "evrakci.index", "evrakci.search",
        "evrakci.coordinator", "evrakci.exclusions", "evrakci.history",
        "evrakci.rank", "evrakci.vocab", "evrakci.migrate", "evrakci.ocr",
        "evrakci.backup", "evrakci.doc_adapter", "evrakci.queue",
        "evrakci.schema", "evrakci.snippet", "evrakci.normalize",
        "evrakci.dup", "evrakci.sched", "evrakci.theme", "evrakci.wizard",
        "evrakci.preview", "evrakci.cli"]


def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(m, flush=True)


def main():
    if os.path.exists(LOG):
        os.remove(LOG)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    sys.path.insert(0, "src")
    log("B0 basladi")
    for m in MODS:
        if only and m != only:
            continue
        try:
            __import__(m)
            log(f"B-OK {m}")
        except Exception:
            log(f"B-FAIL {m}")
            log(traceback.format_exc()[-600:])
    log("B9 bitti")


if __name__ == "__main__":
    main()
