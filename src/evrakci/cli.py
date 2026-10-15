"""Evrakci A3 CLI: kasa kur, tara, ara. Arayuz A7'de; bu komut dikey akis kanitidir."""
from __future__ import annotations

import argparse
import getpass
import os
import sys

APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
DEFAULT_VAULT = os.path.join(APPDATA, "Evrakci", "Data", "evrakci.db")


def _load():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evrakci import vault, schema, scan, extract, index, search  # noqa: E402
    from evrakci import coordinator, exclusions, history, rank, vocab  # noqa: E402
    from evrakci.migrate import ensure_v4  # noqa: E402
    return vault, schema, scan, extract, index, search, rank, history, vocab, \
        coordinator, exclusions, ensure_v4


def _open_db(args):
    """Kasa ac + sema zincirini uygula (v3 -> v7, idempotent)."""
    vault, schema, _s, _e, _i, _se, _r, _h, _v, _c, _x, _m = _load()
    from evrakci.migrate import ensure_current
    pw = args.sifre
    if not pw:
        # Sifresiz kasa: ic anahtar acar, sormadan devam edilir.
        if os.path.exists(args.kasa) and vault.sifresiz_mi(args.kasa):
            pw = vault.SIFRESIZ_ANAHTAR
        else:
            pw = getpass.getpass("Kasa sifresi: ")
    con = vault.open_vault(args.kasa, pw)
    ensure_current(con)
    return con


def cmd_tani(args) -> int:
    """Tani ciktisi: surumler, sayilar, OCR durumu, yedek durumu (sirsiz)."""
    from evrakci.version import __version__
    from evrakci import ocr as _ocr
    con = _open_db(args)
    try:
        meta = {k: v for k, v in con.execute("SELECT k, v FROM schema_meta").fetchall()}
        n_belge = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        n_seg = con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        try:
            bekleyen = con.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0]
        except Exception:
            bekleyen = -1
        try:
            kokler = con.execute("SELECT COUNT(*) FROM roots WHERE enabled=1").fetchone()[0]
        except Exception:
            kokler = -1
    finally:
        con.close()
    try:
        exe = _ocr.find_exe()
    except Exception:
        exe = None
    try:
        diller = _ocr.langs_available()
    except Exception:
        diller = []
    try:
        ram_mb = _ocr.avail_ram()
    except Exception:
        ram_mb = None
    print(f"Evrakci {__version__}", flush=True)
    print(f"sema={meta.get('schema_version', '?')} "
          f"normalizer={meta.get('normalizer_version', '?')} "
          f"extractor={meta.get('extractor_version', '?')} "
          f"ocr={meta.get('ocr_version', '?')}", flush=True)
    print(f"belge={n_belge} segment={n_seg} bekleyen_is={bekleyen} kok={kokler}",
          flush=True)
    print(f"tesseract={'yok' if not exe else exe} "
          f"diller={','.join(diller or ['-'])}", flush=True)
    print(f"ram_kullanilabilir_mb={ram_mb if ram_mb is not None else '?'}", flush=True)
    return 0


def cmd_init(args) -> int:
    vault, schema, *_ = _load()
    pw = args.sifre or getpass.getpass("Kasa sifresi (en az 12 karakter): ")
    if len(pw) < 12:
        print("HATA: sifre en az 12 karakter olmali.", flush=True)
        return 2
    os.makedirs(os.path.dirname(args.kasa), exist_ok=True)
    args.sifre = pw
    con = _open_db(args)
    con.close()
    print(f"Kasa hazir: {args.kasa}", flush=True)
    return 0


def cmd_tara(args) -> int:
    vault, schema, scan, extract, index, _s6, _r, _h, _v, coordinator, _exc, _m4 = _load()
    try:
        con = _open_db(args)
    except Exception:
        print("HATA: kasa acilmadi (sifre/surum).", flush=True)
        return 3
    try:
        stats = coordinator.run_scan(con, args.kasa, args.kok, limit=getattr(args, "limit", None))
    except coordinator.AlreadyRunning:
        print("HATA: baska bir tarama aktif (tek koordinator).", flush=True)
        return 4
    finally:
        con.close()
    print(f"Tarama: {stats['result']} — {stats['found']} bulundu, {stats['done']} islendi,"
          f" {stats['failed']} basarisiz, {stats['missing']} kayip.", flush=True)
    return 0


def cmd_haric(args) -> int:
    _vault, _schema, _s3, _e4, _i5, _s6, rank, history, _v9, _c10, exclusions, _m4 = _load()
    con = _open_db(args)
    rule = exclusions.add(con, args.kural)
    n = exclusions.purge_rule(con, rule)
    con.close()
    print(f"Haric: {rule} — {n} dosyanin icerigi temizlendi.", flush=True)
    return 0


def cmd_ara(args) -> int:
    _vault, _schema, _s3, _e4, _i5, _v1search, rank, history, _v9, _c10, _e11, _m4 = _load()
    con = _open_db(args)
    kw = {"year": args.yil, "ext": args.tur} if (args.yil or args.tur) else {}
    out = rank.search_ranked(con, args.sorgu, limit=int(args.limit), **kw)
    filt = f"|yil={args.yil}|tur={args.tur}" if kw else ""
    history.save(con, args.sorgu, filt)
    con.close()
    if out["empty"]:
        print("Bos sorgu: son aramalar (A7).", flush=True)
        return 0
    if not out["results"]:
        print("Sonuc yok.", flush=True)
        if out["suggestions"]:
            print("Yakin oneriler: " + ", ".join(out["suggestions"]), flush=True)
        return 0
    for r in out["results"]:
        yer = r["label"] + (f" (sayfa {r['page']})" if r["page"] else "")
        print(f"- {r['name']} [{r['ext']}] @{yer} <{r['score_class']}> ({', '.join(r['why'])})"
              f"\n  {r['snippet']}\n  {r['path']}", flush=True)
    if out["suggestions"]:
        print("Yakin oneriler: " + ", ".join(out["suggestions"]), flush=True)
    return 0


def cmd_yedek(args) -> int:
    _vault, _schema, *_rest, _m4 = _load()
    from evrakci import backup as _yb
    con = _open_db(args)
    try:
        y = _yb.create_backup(con, args.kasa, args.sifre or "", args.hedef,
                              manual=args.manuel, forbid_under=[args.kok] if args.kok else None)
    except ValueError as e:
        print(f"HATA: {e}", flush=True)
        return 2
    finally:
        con.close()
    print(f"Yedek: {y}", flush=True)
    return 0


def cmd_yedek_liste(args) -> int:
    from evrakci import backup as _yb
    for b in _yb.list_backups(args.hedef):
        print(f"- {os.path.basename(b['path'])} "
              f"({'manuel' if b['manuel'] else 'otomatik'}, {b['boyut'] // 1024} KB)",
              flush=True)
    return 0


def cmd_geri_yukle(args) -> int:
    _vault, _schema, *_rest, _m4 = _load()
    from evrakci import backup as _yb
    con = _open_db(args)  # mevcut sifre dogrulamasi
    con.close()
    rap = _yb.restore_replace(args.kasa, args.sifre or "", args.yedek, args.staging,
                              backup_password=args.yedek_sifre)
    print(f"Geri yuklendi: {rap['kasa_counts']} (korunan kural: "
          f"{len(rap.get('korunan_kurallar', []))})", flush=True)
    return 0


def cmd_parola(args) -> int:
    _vault, _schema, *_rest, _m4 = _load()
    from evrakci import backup as _yb
    try:
        rap = _yb.change_password(args.kasa, args.sifre or "", args.yeni, args.hedef)
    except ValueError as e:
        print(f"HATA: {e}", flush=True)
        return 2
    print(f"Parola degisti. Yedek: {rap['yedek']}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="evrakci")
    ap.add_argument("--kasa", default=DEFAULT_VAULT)
    ap.add_argument("--sifre")
    sub = ap.add_subparsers(dest="komut", required=True)
    sub.add_parser("init", help="Yeni sifreli kasa kur")
    p_t = sub.add_parser("tara", help="Kok dizini tara ve indeksle")
    p_t.add_argument("kok")
    p_t.add_argument("--limit", type=int, default=None,
                     help="Bu calistirmada en fazla kac dosya islenir (kalan sonraki tura kalir)")
    p_a = sub.add_parser("ara", help="Kasada ara")
    p_a.add_argument("sorgu")
    p_a.add_argument("--limit", default="50")
    p_a.add_argument("--yil", default=None)
    p_a.add_argument("--tur", default=None)
    p_h = sub.add_parser("haric-tut", help="Klasoru kapsam disi birak ve icerigini temizle")
    p_h.add_argument("kural")
    p_y = sub.add_parser("yedek-al", help="Sifreli indeks yedegi olustur")
    p_y.add_argument("--hedef", required=True)
    p_y.add_argument("--kok", default=None)
    p_y.add_argument("--manuel", action="store_true")
    p_yl = sub.add_parser("yedek-liste", help="Yedekleri listele")
    p_yl.add_argument("--hedef", required=True)
    p_g = sub.add_parser("geri-yukle", help="Yedekten geri yukle (rollback'li)")
    p_g.add_argument("yedek")
    p_g.add_argument("--staging", required=True)
    p_g.add_argument("--yedek-sifre", default=None)
    p_p = sub.add_parser("parola-degistir", help="Kasa parolasini degistir (once yedek)")
    p_p.add_argument("yeni")
    p_p.add_argument("--hedef", required=True)
    sub.add_parser("tani", help="Tani ciktisi: surumler, sayilar, OCR durumu")
    args = ap.parse_args(argv)
    if args.komut == "init":
        return cmd_init(args)
    if args.komut == "tara":
        return cmd_tara(args)
    if args.komut == "haric-tut":
        return cmd_haric(args)
    if args.komut == "yedek-al":
        return cmd_yedek(args)
    if args.komut == "yedek-liste":
        return cmd_yedek_liste(args)
    if args.komut == "geri-yukle":
        return cmd_geri_yukle(args)
    if args.komut == "parola-degistir":
        return cmd_parola(args)
    if args.komut == "tani":
        return cmd_tani(args)
    return cmd_ara(args)


if __name__ == "__main__":
    raise SystemExit(main())
