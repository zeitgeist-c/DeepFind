"""Her PDF'in ilk 3 sayfasindaki dogal metin uzunlugunu sayar,
needs_ocr esigine (20) gore OCR'e gidecek/girmeyecek oranini basar."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import scan as scan_mod
from deepfind.extract import extract_window
from deepfind.ocr import MIN_TEXT_CHARS, needs_ocr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()
    total = ocr = skipped = 0
    for e in scan_mod.walk_ro(a.root):
        if e.ext != ".pdf":
            continue
        try:
            res = extract_window(e.path, ".pdf", e.size, 0)
        except Exception:
            continue
        for s in (res.segments or [])[:3]:
            total += 1
            if needs_ocr(s.raw_text):
                ocr += 1
            else:
                skipped += 1
        if total >= a.limit * 3:
            break
    print(f"sayfa={total} ocr_gidecek={ocr} atlanan={skipped} esik={MIN_TEXT_CHARS}")


if __name__ == "__main__":
    main()
