"""Evrakci giris: varsayilan arayuz; bilinen CLI komutunda CLI'ye devreder."""
from __future__ import annotations

import sys

CLI_KOMUTLAR = {"init", "tara", "ara", "haric-tut", "yedek-al", "yedek-liste",
                "geri-yukle", "parola-degistir", "tani", "-h", "--help"}
# Deger alan bayraklar: router ilk konumsal parcayi ararken bunlar + degerleri atlanir.
# (Aksi halde `--kasa X` komutundaki X, komut sanilip arayuz dalina dusulur.)
DEGERLI_BAYRAKLAR = {"--kasa", "--sifre", "--hedef", "--staging", "--yedek-sifre",
                     "--kok", "--limit", "--yil", "--tur"}


def _ilk_komut(args):
    atla = False
    for a in args:
        if atla:
            atla = False
            continue
        if a in DEGERLI_BAYRAKLAR:
            atla = True
            continue
        if a.startswith("-"):
            continue
        return a
    return None


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ilk = _ilk_komut(args)
    if ilk in CLI_KOMUTLAR or "-h" in args or "--help" in args:
        from evrakci.cli import main as cli_main
        return cli_main(args)
    from evrakci.app import main as app_main
    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
