"""Sifresiz indeks snapshot: yedek + dogrulama + saklama + geri yukleme.

Sozlesme:
- Yedek = kasa+indeks+gecmis+ayarlarin sifresiz snapshot'i; kaynak belge yok.
- Hedef: yerel Backups (varsayilan) veya kullanicinin sectigi yerel/USB hedef.
  Kaynak kokler ve altlari hedef olamaz. Dogrulanmamis ham dosya kopyasiyla
  kasa cogaltmak yasak (yedekleme yolu kullanilir).
- Gecici isimle yaz, dogrula, atomik finalize et; yarim dosya listeye girmez.
- Saklama: 7 son otomatik; manuel yedekler sessizce silinmez.
- Parola/anahtar diske, loga, manifest'e yazilmaz.
- Yeni yedekler sifresizdir. Eski sifreli yedekler `backup_password` ile
  okunmaya devam eder; sessizce olu sayilmaz.
- `password` parametreleri yalniz eski cagrilarla uyumluluk icin durur ve
  normal yolda yok sayilir.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time

from .theme import t

AUTO_KEEP = 7
AUTO_PREFIX = "deepfind-indeks-"
MANUAL_PREFIX = "deepfind-indeks-manuel-"


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime()) + f"-{time.time_ns() % 1_000_000_000:09d}"


def _manifest(path: str, counts: dict) -> dict:
    return {"yedek": os.path.basename(path), "tarih": _stamp(),
            "sifresiz": True, "counts": counts}


def _counts(con) -> dict:
    out = {}
    for tb in ("files", "segments", "history"):
        try:
            out[tb] = con.execute(f"SELECT count(*) FROM {tb}").fetchone()[0]
        except Exception:
            out[tb] = -1
    try:
        out["embeddings"] = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    except Exception:
        out["embeddings"] = -1
    try:
        out["schema"] = con.execute(
            "SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0]
    except Exception:
        out["schema"] = "?"
    return out


def verify_backup(backup_path: str, password: str | None = None, progress=None) -> dict:
    """Yedegi ayri baglantiyla ac: butunluk + ornek icerik/arama."""
    from . import vault as vault_mod
    if os.path.isfile(backup_path) and vault_mod.is_encrypted(backup_path):
        if not password:
            return {"ok": False, "neden": "sifreli-yedek-parola-gerekli",
                    "counts": {}}
        from . import vault_convert as vc
        return vc.verify_encrypted(backup_path, password)
    try:
        con = sqlite3.connect(backup_path, timeout=10)
    except Exception as exc:
        return {"ok": False, "neden": str(exc), "counts": {}}
    try:
        try:
            rows = con.execute("PRAGMA integrity_check").fetchall()
            ok = len(rows) == 1 and rows[0][0] == "ok"
        except Exception:
            ok = False
        counts = _counts(con)
        try:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            target = 'embeddings' if 'embeddings' in tables else 'docs_fts'
            con.execute('SELECT rowid FROM ' + target + ' LIMIT 1').fetchall()
            index_ok = True
        except Exception:
            index_ok = False
        return {"ok": bool(ok and index_ok), "integrity": rows if ok else [],
                "counts": counts}
    finally:
        try:
            con.close()
        except Exception:
            pass


def create_backup(con, vault_path: str, password: str | None = None, dest_dir: str = "",
                  manual: bool = False, forbid_under: list | None = None,
                  progress=None) -> str:
    """Aktif kasadan sifresiz snapshot. Donus: finalize edilmis yedek yolu."""
    if not dest_dir:
        raise ValueError("yedek hedefi gerekli")
    dest_dir = os.path.abspath(dest_dir)
    forbid = [os.path.normcase(os.path.abspath(pp)) for pp in (forbid_under or [])]
    norm_dest = os.path.normcase(dest_dir)
    if any(norm_dest == pp or norm_dest.startswith(pp.rstrip("/" + chr(92)) + os.sep) for pp in forbid):
        raise ValueError("yedek hedefi kaynak kok/altinda olamaz")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        con.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
    except Exception:
        pass
    prefix = MANUAL_PREFIX if manual else AUTO_PREFIX
    tmp = os.path.join(dest_dir, f".tmp-{prefix}{_stamp()}.db")
    final = None
    try:
        tgt = sqlite3.connect(tmp, timeout=10)
        try:
            tgt.execute('PRAGMA journal_mode=DELETE')
            if progress:
                def copied(status, remaining, total):
                    progress('backup', total - remaining, total)
                con.backup(tgt, pages=256, progress=copied)
            else:
                con.backup(tgt)
            tgt.commit()
        finally:
            tgt.close()
        if progress:
            progress('verify', 0, 0)
        v = verify_backup(tmp)
        if not v["ok"]:
            raise RuntimeError(f"yedek dogrulama basarisiz: {v['counts']}")
        final = os.path.join(dest_dir, f"{prefix}{_stamp()}.db")
        os.replace(tmp, final)
        with open(final + ".json", "w", encoding="utf-8") as f:
            json.dump(_manifest(final, v["counts"]), f, ensure_ascii=False, indent=1)
        if not manual:
            prune(con=None, dest_dir=dest_dir)
        return final
    finally:
        try:
            if final is None and os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def list_backups(dest_dir: str) -> list:
    out = []
    try:
        names = os.listdir(dest_dir)
    except OSError:
        return out
    for n in sorted(names):
        if n.endswith(".db") and (n.startswith(AUTO_PREFIX) or n.startswith(MANUAL_PREFIX)):
            pp = os.path.join(dest_dir, n)
            man = os.path.join(dest_dir, n + ".json")
            meta = {}
            try:
                with open(man, encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                pass
            out.append({"path": pp, "manuel": n.startswith(MANUAL_PREFIX),
                        "boyut": os.path.getsize(pp), "meta": meta})
    return out


def prune(con, dest_dir: str, keep: int = AUTO_KEEP) -> list:
    """Otomatik yedeklerden eskiyi sil (manuel korunur). Donus: silinenler."""
    autos = [b for b in list_backups(dest_dir) if not b["manuel"]]
    doomed = autos[: max(0, len(autos) - keep)]
    gone = []
    for b in doomed:
        try:
            os.remove(b["path"])
            try:
                os.remove(b["path"] + ".json")
            except OSError:
                pass
            gone.append(b["path"])
        except OSError:
            continue
    return gone


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def restore_replace(vault_path: str, password: str | None, backup_path: str,
                    staging_dir: str, backup_password: str | None = None) -> dict:
    """Yedegi staging'de dogrula, mevcut kasayi rollback'e al, atomik degistir.

    Cagiran, con baglantilarini kapatmis olmali (kilit akisi). Donus: rapor.
    Eski sifreli yedek ancak `backup_password` ile acilir.
    """
    from . import exclusions as exc
    from . import vault as vault_mod
    v = verify_backup(backup_path, backup_password)
    if not v["ok"]:
        raise RuntimeError("yedek dogrulanamadi; mevcut kasa korunuyor")
    if vault_mod.is_encrypted(backup_path) and not backup_password:
        raise RuntimeError("sifreli yedek icin yedek parolasi gerekli")
    os.makedirs(staging_dir, exist_ok=True)
    korunan = []
    if os.path.exists(vault_path):
        try:
            keep_con = vault_mod.open_vault(vault_path)
            try:
                korunan = list(exc.list_rules(keep_con))
            finally:
                keep_con.close()
        except Exception:
            raise RuntimeError(t("mevcut hariç kuralları okunamadı; geri yükleme durduruldu"))
    rollback = os.path.join(staging_dir, f"rollback-{_stamp()}.db")
    rollback_alindi = False
    if os.path.exists(vault_path):
        shutil.copyfile(vault_path, rollback)
        rv = verify_backup(rollback)
        if not rv["ok"]:
            raise RuntimeError("rollback snapshot dogrulanamadi; degisim yapilmadi")
        rollback_alindi = True
    import uuid as _uuid
    if vault_mod.is_encrypted(backup_path):
        # Eski sifreli yedekten sifresiz kasaya: donusturucu tek kaynaktir.
        from . import vault_convert as vc
        tmp = vault_path + ".restore-" + _uuid.uuid4().hex + ".db"
        rapor = vc.convert(backup_path, backup_password or "", dest=tmp)
        staged = rapor["kasa"]
    else:
        staged = vault_path + ".restore-" + _uuid.uuid4().hex + ".db"
        shutil.copyfile(backup_path, staged)
    try:
        dst = vault_mod.open_vault(staged)
        try:
            for rule in korunan:
                exc.add_and_purge(dst, rule)
            dst.commit()
        finally:
            dst.close()
    except Exception:
        try:
            os.remove(staged)
        except OSError:
            pass
        raise
    checked = verify_backup(staged)
    if not checked["ok"]:
        try:
            os.remove(staged)
        except OSError:
            pass
        raise RuntimeError(t("staging doğrulanamadı; mevcut kasa korunuyor"))
    os.replace(staged, vault_path)
    return {"kasa": vault_path, "rollback": rollback if rollback_alindi else None,
            "yedek_counts": v["counts"], "kasa_counts": checked["counts"],
            "korunan_kurallar": korunan}
