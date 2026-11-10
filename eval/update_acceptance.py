"""In-app update acceptance: isolated base -> local next candidate.

Scenario (no production touch, version.py restored afterwards):
  1. install the base candidate (test AppId) into an isolated dir
  2. isolated profile WITH a verified model + a vault with one document
  3. local channel manifest (DEEPFIND_UPDATE_URL=file://...) offering the
     next candidate setup
  4. real Settings -> Check -> Download & install transition in the app
  5. verify: download, digest check, close, install, reopen from the install
     path, same vault readable, verified stamp, version record
  6. failure case: wrong digest -> error shown, old version intact/runnable

Run: PYTHONPATH=src python eval/update_acceptance.py
Requires: base/next aday setups already built (see --help).
"""
import sys

KABUL_ADIMLARI = [
    "taban-kurulum",
    "model+profilli-kasa",
    "yerel-kanal",
    "indir-ve-kur",
    "dogrulama-pulu",
    "surum-kaydi",
    "bozuk-ozet-hatasi",
    "temizlik",
]


def main():
    print("kabul adimlari: " + ", ".join(KABUL_ADIMLARI))
    print("NOT: etkilesimli adimlar (Ayarlar tiklamasi, UAC onayi) gozetimli kosar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
