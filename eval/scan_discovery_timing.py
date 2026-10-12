"""Salt-okunur kesif hizini olcer: dosya sayisi ve sure."""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import scan as scan_mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    a = ap.parse_args()
    t0 = time.perf_counter()
    n = 0
    for _e in scan_mod.walk_ro(a.root):
        n += 1
    dt = time.perf_counter() - t0
    print(f"dosya={n} sure_sn={dt:.1f} hiz_dosya_sn={n / max(dt, 1e-6):.0f}")


if __name__ == "__main__":
    main()
