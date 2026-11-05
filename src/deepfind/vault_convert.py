"""Eski sifreli kasadan sifresiz SQLite'a tek yonlu donusum.

Yalniz bu modul `sqlcipher3` ice aktarir; normal calisma yolu (`vault`,
`backup`, arayuz) saf `sqlite3` kullanir. Parola loga/komut satirina yazilmaz;
yalniz bu donusum sirasinda bellege alinir ve is bitince silinir.
"""
from __future__ import annotations

import os
import sqlite3
import uuid


def _sqlcipher():
    try:
        import sqlcipher3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Eski format donusturucu icin sqlcipher3 gerekli; "
            "normal kurulumda bulunmaz."
        ) from exc
    return sqlcipher3


def _escape(s: str) -> str:
    return s.replace("'", "''")


def is_encrypted(path: str) -> bool:
    from . import vault as v
    return v.is_encrypted(path)


def _counts(con) -> dict:
    out = {}
    for t in ("files", "segments", "embeddings", "settings", "roots"):
        try:
            out[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except Exception:
            out[t] = -1
    try:
        out["schema"] = con.execute(
            "SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0]
    except Exception:
        out["schema"] = "?"
    try:
        rows = con.execute("PRAGMA integrity_check").fetchall()
        out["integrity"] = len(rows) == 1 and rows[0][0] == "ok"
    except Exception:
        out["integrity"] = False
    return out


def convert(src: str, password: str, dest: str | None = None) -> dict:
    """Sifreli kasayi sifresiz kopyaya donustur; kaynaga yazma.

    - `dest` verilmezse kaynak dosyanin yaninda gecici uretilir; donus tamamsa
      atomik `os.replace` ile kaynagin uzerine yazilir (rollback: kaynak baska
      adla yedeklenir).
    - Yanlis parola, bozuk kaynak, disk dolmasi veya kesintide eski kasa korunur.
    """
    sqlcipher3 = _sqlcipher()
    if not os.path.isfile(src):
        raise FileNotFoundError(f"kasa bulunamadi: {src}")
    if not password:
        raise ValueError("donusum icin mevcut parola gerekli")
    hedef = dest or (src + ".donusuyor-" + uuid.uuid4().hex + ".db")
    rollback = None
    try:
        eski = sqlcipher3.connect(src, timeout=10)
    except Exception as exc:
        raise RuntimeError("eski kasa acilamadi; eski kasa korunuyor") from exc
    try:
        try:
            eski.execute(f"PRAGMA key='{_escape(password)}'")
            eski.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except Exception as exc:
            raise ValueError(
                "parola yanlis veya kasa bozuk; eski kasa korunuyor") from exc
        if os.path.exists(hedef):
            os.remove(hedef)
        eski.execute(f"ATTACH DATABASE '{hedef}' AS plaintext KEY ''")
        try:
            eski.execute("SELECT sqlcipher_export('plaintext')")
        finally:
            try:
                eski.execute("DETACH DATABASE plaintext")
            except Exception:
                pass
    finally:
        try:
            eski.close()
        except Exception:
            pass
    # Dogrula: butunluk + icerik sayilari eslesmeli.
    try:
        yeni = sqlite3.connect(hedef, timeout=10)
        try:
            satirlar = yeni.execute("PRAGMA integrity_check").fetchall()
            if not (len(satirlar) == 1 and satirlar[0][0] == "ok"):
                raise RuntimeError(
                    "donusen kasa butunluk denetimini gecemedi; eski kasa korunuyor")
            yeni_sayim = _counts(yeni)
        finally:
            yeni.close()
        # Kaynak sayimlari karsilastir (sifreli baglanti yeniden acilir).
        eski2 = sqlcipher3.connect(src, timeout=10)
        try:
            eski2.execute(f"PRAGMA key='{_escape(password)}'")
            eski_sayim = _counts(eski2)
        finally:
            eski2.close()
        for tablo in ("files", "segments", "embeddings"):
            if eski_sayim.get(tablo, -1) != yeni_sayim.get(tablo, -1):
                raise RuntimeError(
                    f"icerik eslesmedi ({tablo}: {eski_sayim.get(tablo)} -> "
                    f"{yeni_sayim.get(tablo)}); eski kasa korunuyor")
    except Exception:
        try:
            if os.path.exists(hedef):
                os.remove(hedef)
        except OSError:
            pass
        raise
    if dest is None:
        # Atomik gecis: once kaynagi yedekle, sonra yeni dosyayi yerine koy.
        rollback = src + ".sifreli-yedek-" + uuid.uuid4().hex + ".db"
        os.replace(src, rollback)
        try:
            os.replace(hedef, src)
        except Exception:
            try:
                os.replace(rollback, src)
            except Exception:
                pass
            raise RuntimeError(
                "yeni kasa yerine konulamadi; eski kasa yedekte duruyor: " + str(rollback))
        return {"kasa": src, "rollback": rollback, "eski": eski_sayim, "yeni": yeni_sayim}
    return {"kasa": hedef, "rollback": None, "eski": eski_sayim, "yeni": yeni_sayim}


def verify_encrypted(path: str, password: str) -> dict:
    """Eski sifreli yedegi parola ile dogrula (sessizce olume terk etme)."""
    sqlcipher3 = _sqlcipher()
    try:
        con = sqlcipher3.connect(path, timeout=10)
    except Exception as exc:
        return {"ok": False, "neden": f"acilmadi: {exc}"}
    try:
        try:
            con.execute(f"PRAGMA key='{_escape(password)}'")
            con.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except Exception:
            return {"ok": False, "neden": "parola yanlis veya dosya bozuk"}
        return {"ok": True, "counts": _counts(con)}
    finally:
        try:
            con.close()
        except Exception:
            pass
