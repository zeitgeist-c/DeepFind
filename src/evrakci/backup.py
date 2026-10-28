"""Sifreli indeks snapshot: yedek + dogrulama + saklama + geri yukleme + parola.

Plan bolum 17 sozlesmesi:
- Yedek = kasa+indeks+gecmis+ayarlarin sifreli snapshot'i; kaynak belge yok.
- Hedef: yerel Backups (varsayilan) veya kullanicinin sectigi yerel/USB hedef.
  Kaynak kokler ve altlari hedef olamaz. Dogrulanmamis ham dosya kopyasiyla
  kasa cogaltmak yasak (sifreli backup/export yolu kullanilir).
- Gecici isimle yaz, dogrula, atomik finalize et; yarim dosya listeye girmez.
- Saklama: 7 son otomatik; manuel yedekler sessizce silinmez.
- Sifre/anahtar diske, loga, manifest'e yazilmaz.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

AUTO_KEEP = 7
AUTO_PREFIX = "evrakci-indeks-"
MANUAL_PREFIX = "evrakci-indeks-manuel-"


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime()) + f"-{time.time_ns() % 1_000_000_000:09d}"


def _manifest(path: str, counts: dict) -> dict:
    return {"yedek": os.path.basename(path), "tarih": _stamp(),
            "counts": counts}


def _counts(con) -> dict:
    out = {}
    for t in ("files", "segments", "history"):
        try:
            out[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except Exception:
            out[t] = -1
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


def _pragma_sifre(pw: str) -> str:
    # PRAGMA bagli parametre kabul etmez; SQL metin-degeri kuraliyla tek tirnak ikile.
    return "'" + pw.replace("'", "''") + "'"


def verify_backup(backup_path: str, password: str, progress=None) -> dict:
    """Yedegi ayri baglantiyla ac: sifre + butunluk + ornek icerik/arama."""
    from . import vault
    con = vault.open_vault(backup_path, password)
    if progress:
        def tick():
            progress('verify', 0, 0)
            return 0
        con.set_progress_handler(tick, 10000)
    try:
        try:
            rows = con.execute("PRAGMA integrity_check").fetchall()
            ok = len(rows) == 1 and rows[0][0] == "ok"
        except Exception:
            ok = False
        counts = _counts(con)
        # Verify a readable index in both current and legacy snapshots.
        try:
            tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            target='embeddings' if 'embeddings' in tables else 'docs_fts'
            con.execute('SELECT rowid FROM '+target+' LIMIT 1').fetchall()
            index_ok = True
        except Exception:
            index_ok = False
        return {"ok": bool(ok and index_ok), "integrity": rows if ok else [],
                "counts": counts}
    finally:
        con.close()


def create_backup(con, vault_path: str, password: str, dest_dir: str,
                  manual: bool = False, forbid_under: list | None = None,
                  progress=None) -> str:
    """Aktif kasadan sifreli snapshot. Donus: finalize edilmis yedek yolu."""
    from . import vault
    dest_dir = os.path.abspath(dest_dir)
    forbid = [os.path.normcase(os.path.abspath(p)) for p in (forbid_under or [])]
    norm_dest = os.path.normcase(dest_dir)
    if any(norm_dest == p or norm_dest.startswith(p.rstrip("\\/") + os.sep) for p in forbid):
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
        tgt = vault.open_vault(tmp, password)
        try:
            # Snapshot has no concurrent readers; avoid a second database-sized WAL.
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
        v = verify_backup(tmp, password, progress=progress) if progress else verify_backup(tmp, password)
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
            p = os.path.join(dest_dir, n)
            man = os.path.join(dest_dir, n + ".json")
            meta = {}
            try:
                with open(man, encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                pass
            out.append({"path": p, "manuel": n.startswith(MANUAL_PREFIX),
                        "boyut": os.path.getsize(p), "meta": meta})
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


def restore_replace(vault_path: str, password: str, backup_path: str,
                    staging_dir: str, backup_password: str | None = None) -> dict:
    """Yedegi staging'de dogrula, mevcut kasayi rollback'e al, atomik degistir.

    Cagiran, con baglantilarini kapatmis olmali (kilit akisi). Donus: rapor.
    Eski yedek sifresi farkli olabilir (backup_password).
    """
    from . import vault
    bpw = backup_password if backup_password is not None else password
    v = verify_backup(backup_path, bpw)
    if not v["ok"]:
        raise RuntimeError("yedek dogrulanamadi; mevcut kasa korunuyor")
    os.makedirs(staging_dir, exist_ok=True)
    # mevcut haric kurallarini koru (eski yedek kapsam disi klasoru geri acamaz)
    from . import exclusions as exc
    korunan = []
    if os.path.exists(vault_path):
        try:
            keep_con = vault.open_vault(vault_path, password)
            try:
                korunan = list(exc.list_rules(keep_con))
            finally:
                keep_con.close()
        except Exception:
            raise RuntimeError("mevcut hariç kuralları okunamadı; geri yükleme durduruldu")
    rollback = os.path.join(staging_dir, f"rollback-{_stamp()}.db")
    rollback_alindi = False
    if os.path.exists(vault_path):
        cur = vault.open_vault(vault_path, password)
        try:
            rb = vault.open_vault(rollback, password)
            try:
                cur.backup(rb)
                rb.commit()
            finally:
                rb.close()
        finally:
            cur.close()
        rv = verify_backup(rollback, password)
        if not rv["ok"]:
            raise RuntimeError("rollback snapshot dogrulanamadi; degisim yapilmadi")
        rollback_alindi = True
    # Yedek üzerinde değil, ayrı şifreli staging snapshot üzerinde çalış.
    import uuid
    tmp = vault_path + ".restore-" + uuid.uuid4().hex + ".db"
    src = vault.open_vault(backup_path, bpw)
    try:
        dst = vault.open_vault(tmp, bpw)
        try:
            src.backup(dst)
            dst.commit()
            for rule in korunan:
                exc.add_and_purge(dst, rule)
            dst.commit()
            if bpw != password:
                dst.execute(f"PRAGMA rekey={_pragma_sifre(password)}")
        finally:
            dst.close()
    finally:
        src.close()
    checked = verify_backup(tmp, password)
    if not checked["ok"]:
        raise RuntimeError("staging doğrulanamadı; mevcut kasa korunuyor")
    os.replace(tmp, vault_path)
    return {"kasa": vault_path, "rollback": rollback if rollback_alindi else None,
            "yedek_counts": v["counts"], "kasa_counts": checked["counts"],
            "korunan_kurallar": korunan, "sifre_farkli": bpw != password}

def change_password(vault_path: str, old_pw: str, new_pw: str,
                    backup_dir: str) -> dict:
    """Parola degistir: once yedek, rekey, iki sifreyle dogrula. Basarisizsa eski korunur."""
    from . import vault
    if len(new_pw) < 12:
        raise ValueError("yeni sifre en az 12 karakter olmali")
    if old_pw == new_pw:
        raise ValueError("yeni şifre mevcut şifreden farklı olmalı")
    # Mevcut dosyaya rekey uygulamak yerine kopyayı hazırla, doğrula, atomik değiştir.
    con = vault.open_vault(vault_path, old_pw)
    import uuid
    tmp = vault_path + ".rekey-" + uuid.uuid4().hex + ".db"
    try:
        yedek = create_backup(con, vault_path, old_pw, backup_dir, manual=True)
        dst = vault.open_vault(tmp, old_pw)
        try:
            con.backup(dst)
            dst.commit()
            dst.execute(f"PRAGMA rekey={_pragma_sifre(new_pw)}")
        finally:
            dst.close()
    finally:
        con.close()
    checked = verify_backup(tmp, new_pw)
    if not checked["ok"]:
        raise RuntimeError("yeni şifreyle doğrulama başarısız; mevcut kasa korunuyor")
    try:
        bad = vault.open_vault(tmp, old_pw)
    except Exception:
        bad = None
    if bad is not None:
        bad.close()
        raise RuntimeError("eski şifre staging kasasını açıyor; değişim yapılmadı")
    os.replace(tmp, vault_path)
    # Şifre değişti: kurtarma anahtarı varsa yeni şifreye göre tazele.
    try:
        from . import recovery
        if os.path.isfile(recovery.container_path(vault_path)):
            recovery.refresh(vault_path, new_pw)
    except Exception:
        pass
    return {"yedek": yedek, "counts": checked["counts"]}
