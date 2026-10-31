"""Recovery key: the second way in, so the index survives a forgotten password.

Design B (user decision, 2026-10-15):
- The key lives in the vault folder + is handed over as a printable document.
- The key is randomly generated (user never picks it); confusable letters are absent.

Contract:
- The container is a separate encrypted SQLCipher file carrying the vault path and unlock secret.
- The vault fingerprint is written into the container; a changed vault warns "mismatch".
- After recovery the vault opens with the NEW password; the old password and old key die.
- No secret is ever written to log/log files."""
from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid
from pathlib import Path
from .theme import t

# No confusable characters: I, L, O, U and digits 0, 1 are absent from the alphabet.
ALFABE = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
PREFIX = "EVKC-"
ON_EK = "deepfind-kurtarma"
CONTAINER_SUFFIX = ".kurtarma.db"
KEY_SUFFIX = ".anahtar"
SURUM = "1"
# Belgede anahtar satirini isaretleyen etiket (normalize bunu arar).
ETIKET = "KURTARMA ANAHTARI:"


# --- helpers -------------------------------------------------------------

def _dir(vault_path: str) -> Path:
    return Path(os.path.abspath(vault_path)).parent


def container_path(vault_path: str) -> str:
    return str(_dir(vault_path) / (ON_EK + CONTAINER_SUFFIX))


def key_path(vault_path: str) -> str:
    return str(_dir(vault_path) / (ON_EK + KEY_SUFFIX))


def _pragma(deger: str) -> str:
    return "'" + deger.replace("'", "''") + "'"


def _con(path: str, anahtar: str):
    import sqlcipher3
    con = sqlcipher3.connect(path, timeout=10)
    con.execute(f"PRAGMA key={_pragma(anahtar)}")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("SELECT count(*) FROM sqlite_master").fetchone()
    return con


def kasa_parmak_izi(vault_path: str) -> str:
    """The vault file's identity: size + head + tail chunk digest."""
    h = hashlib.sha256()
    st = os.stat(vault_path)
    h.update(str(st.st_size).encode())
    parca = 64 * 1024
    with open(vault_path, "rb") as fh:
        h.update(fh.read(parca))
        if st.st_size > parca * 2:
            fh.seek(-parca, os.SEEK_END)
            h.update(fh.read(parca))
    return h.hexdigest()[:32]


# --- anahtar -----------------------------------------------------------------

def new_key() -> str:
    """Random recovery key (160 bit)."""
    ham = base64.b32encode(os.urandom(20)).decode().rstrip("=")
    govde = "".join(ch if ch in ALFABE else ALFABE[ord(ch) % len(ALFABE)] for ch in ham)
    return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))


def normalize(girilen: str) -> str:
    """Recognize the key even when the user types it spaced/lowercase/prefixless.

Priority order:
1) The `KURTARMA ANAHTARI:` line in the document,
2) any line containing `EVKC` (pasted key),
3) the alphanumeric run of the whole text (key pasted alone).
The key body is 32 characters; extras are ignored."""
    if not girilen:
        return ""
    satirlar = girilen.splitlines() or [girilen]

    def _govde(metin: str) -> str:
        """Extract the key body from text: EVKC prefix and separators dropped."""
        buyuk = metin.upper()
        if "EVKC" in buyuk:
            buyuk = buyuk[buyuk.index("EVKC") + len("EVKC"):]
        return "".join(ch for ch in buyuk if ch.isalnum())[:32]

    # 1) Tagged row in the document
    for satir in satirlar:
        if ETIKET in satir:
            govde = _govde(satir.split(ETIKET, 1)[1])
            if len(govde) >= 20:
                return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))
    # 2) Row passing EVKC (pasted key)
    for satir in satirlar:
        if "EVKC" in satir.upper():
            govde = _govde(satir)
            if len(govde) >= 20:
                return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))
    # 3) Only the key was pasted
    govde = _govde(girilen)
    if not govde:
        return ""
    return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))


def _dogrula_bicim(anahtar: str) -> str:
    n = normalize(anahtar)
    govde = n[len(PREFIX):].replace("-", "")
    if len(govde) != 32:
        raise ValueError(t("Kurtarma anahtarı eksik veya bozuk görünüyor."))
    return n


# --- konteyner ---------------------------------------------------------------

def write_container(vault_path: str, password: str, anahtar: str) -> str:
    """Write the recovery container (atomic). Returns: container path."""
    anahtar = _dogrula_bicim(anahtar)
    yol = container_path(vault_path)
    gecici = yol + ".tmp-" + uuid.uuid4().hex
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    con = _con(gecici, anahtar)
    try:
        con.execute("CREATE TABLE recovery(k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        con.executemany("INSERT INTO recovery(k,v) VALUES(?,?)", [
            ("surum", SURUM),
            ("olusturma", str(int(time.time()))),
            ("kasa", os.path.abspath(vault_path)),
            ("parmak_izi", kasa_parmak_izi(vault_path)),
            ("acilis", password),
        ])
        con.commit()
    finally:
        con.close()
    # does the written container really open (proof before atomic finalize)
    kontrol = _con(gecici, anahtar)
    try:
        if kontrol.execute("SELECT v FROM recovery WHERE k='acilis'").fetchone() is None:
            raise RuntimeError(t("kurtarma konteyneri doğrulanamadı"))
    finally:
        kontrol.close()
    os.replace(gecici, yol)
    try:
        os.chmod(yol, 0o600)
    except OSError:
        pass
    return yol


def verify_container(yol: str, anahtar: str) -> dict:
    """Does the container open; does the vault match."""
    if not os.path.isfile(yol):
        return {"ok": False, "neden": "konteyner yok"}
    try:
        con = _con(yol, anahtar)
    except Exception:
        return {"ok": False, "neden": t("anahtar geçersiz")}
    try:
        satirlar = dict(con.execute("SELECT k,v FROM recovery").fetchall())
    except Exception:
        con.close()
        return {"ok": False, "neden": t("konteyner okunamadı")}
    con.close()
    kasa = satirlar.get("kasa", "")
    sonuc = {"ok": True, "kasa": kasa, "parmak_izi": satirlar.get("parmak_izi", ""),
             "surum": satirlar.get("surum", ""), "olusturma": satirlar.get("olusturma", "")}
    if kasa and os.path.isfile(kasa):
        try:
            sonuc["kasa_eslesiyor"] = kasa_parmak_izi(kasa) == satirlar.get("parmak_izi")
        except OSError:
            sonuc["kasa_eslesiyor"] = False
    return sonuc


def read_container(yol: str, anahtar: str) -> dict:
    """Read the container content (used during recovery)."""
    con = _con(yol, anahtar)
    try:
        return dict(con.execute("SELECT k,v FROM recovery").fetchall())
    finally:
        con.close()


# --- key file ---------------------------------------------------------

def write_key_file(vault_path: str, anahtar: str) -> str:
    """Key file for the user to keep (design B)."""
    yol = key_path(vault_path)
    gecici = yol + ".tmp"
    metin = document_text(vault_path, anahtar, bicimli=True)
    Path(gecici).write_text(metin, encoding="utf-8")
    os.replace(gecici, yol)
    try:
        os.chmod(yol, 0o600)
    except OSError:
        pass
    return yol


def load_key(vault_path: str) -> str:
    """Read the key from the key file (document headers skipped)."""
    yol = key_path(vault_path)
    try:
        for satir in Path(yol).read_text(encoding="utf-8").splitlines():
            s = satir.strip().strip("•").strip()
            if "EVKC" in s.upper():
                aday = normalize(s.split(":")[-1] if ":" in s else s)
                if aday:
                    return aday
    except OSError:
        return ""
    return ""


def document_text(vault_path: str, anahtar: str, bicimli: bool = False) -> str:
    """Printable recovery document."""
    anahtar = _dogrula_bicim(anahtar)
    kasa = os.path.abspath(vault_path)
    if not bicimli:
        return (t("EVRAKÇI KURTARMA ANAHTARI\n")
                + f"Anahtar : {anahtar}\n"
                + f"Kasa    : {kasa}\n")
    gruplu = " ".join(anahtar[i:i + 5] for i in range(0, len(anahtar), 5))
    return (
        "==================================================\n"
        + t("        EVRAKÇI — KURTARMA ANAHTARI\n")
        + "==================================================\n\n"
        + t("Bu anahtar, kasa şifrenizi unuttuğunuzda arşiv\n")
        + t("indeksinizi kurtarır. Güvenli bir yerde saklayın.\n\n")
        + f"  {ETIKET}  {gruplu}\n\n"
        + f"  Kasa    :  {kasa}\n\n"
        + t("Nasıl kullanılır:\n")
        + t("  1) DeepFind'yı açın, şifre ekranında\n")
        + t("     \"Şifremi unuttum\" seçeneğine basın.\n")
        + t("  2) Yukarıdaki anahtarı yapıştırın (boşluk ve\n")
        + t("     büyük/küçük harf farkı önemli değildir).\n")
        + t("  3) Kasa açılır; yeni bir şifre belirlersiniz.\n\n")
        + t("Anahtar yalnız bu belgede ve kasa klasöründeki\n")
        + t("aynı adlı dosyada bulunur. Kaynak belgeleriniz\n")
        + t("bu işlemden etkilenmez.\n")
        + "==================================================\n"
    )


# --- kurtarma ----------------------------------------------------------------

def recover(vault_path: str, anahtar: str, yeni_sifre: str,
            backup_dir: str | None = None) -> dict:
    """Open the vault with the key, set a new password, generate a new recovery key.

On failure the current vault and current recovery key are preserved."""
    from . import backup, vault
    if len(yeni_sifre) < 12:
        raise ValueError(t("Yeni şifre en az 12 karakter olmalı."))
    yol = container_path(vault_path)
    if not os.path.isfile(yol):
        raise FileNotFoundError(t("Kurtarma konteyneri bulunamadı."))
    try:
        veri = read_container(yol, anahtar)
    except Exception as error:
        raise ValueError(t("Kurtarma anahtarı geçersiz veya konteyner bozuk.")) from error
    eski_sifre = veri.get("acilis", "")
    hedef = veri.get("kasa") or os.path.abspath(vault_path)
    if not os.path.isfile(hedef):
        raise FileNotFoundError(t("Kasa dosyası bulunamadı; kurtarma yapılamıyor."))
    if os.path.abspath(hedef) != os.path.abspath(vault_path):
        # Vault moved: at least make sure we open the right file.
        pass
    # 1) Does the old password really work? (stop here if the container secret went stale)
    kontrol = vault.open_vault(hedef, eski_sifre)
    kontrol.close()
    # 2) Safety backup (recovery takes its own backup too)
    if backup_dir:
        con = vault.open_vault(hedef, eski_sifre)
        try:
            backup.create_backup(con, hedef, eski_sifre, backup_dir, manual=True)
        finally:
            con.close()
    # 3) Replace with the new password (change_password makes its own backup + two-way verification)
    hedef_yedek = backup_dir or os.path.join(os.path.dirname(os.path.abspath(hedef)), "..", "Backups")
    backup.change_password(hedef, eski_sifre, yeni_sifre, hedef_yedek)
    # 4) Generate a new recovery key (the old key becomes invalid)
    yeni = new_key()
    write_container(hedef, yeni_sifre, yeni)
    write_key_file(hedef, yeni)
    return {"ok": True, "kasa": hedef, "yeni_anahtar": yeni,
            "anahtar_dosyasi": key_path(hedef)}


def refresh(vault_path: str, password: str) -> str:
    """Generate a new recovery key; invalidate the old one. Returns: new key."""
    anahtar = new_key()
    write_container(vault_path, password, anahtar)
    write_key_file(vault_path, anahtar)
    return anahtar


def remove(vault_path: str) -> dict:
    """Remove the recovery key (vault password stays the only way in)."""
    silinen = []
    for yol in (container_path(vault_path), key_path(vault_path)):
        try:
            if os.path.exists(yol):
                os.remove(yol)
                silinen.append(yol)
        except OSError:
            pass
    return {"silinen": silinen}


def status(vault_path: str) -> dict:
    """State for the Settings screen: present or not, vault matched or not."""
    yol = container_path(vault_path)
    if not os.path.isfile(yol):
        return {"var": False, "container": yol, "anahtar_dosyasi": key_path(vault_path)}
    sonuc = {"var": True, "container": yol, "anahtar_dosyasi": key_path(vault_path),
             "anahtar_var": os.path.isfile(key_path(vault_path))}
    try:
        veri = read_container(yol, load_key(vault_path)) if load_key(vault_path) else None
    except Exception:
        veri = None
    if veri:
        sonuc["created"] = veri.get("olusturma", "")
        kayitli = veri.get("parmak_izi", "")
        try:
            guncel = kasa_parmak_izi(vault_path)
        except OSError:
            guncel = ""
        sonuc["kasa_eslesiyor"] = bool(kayitli and kayitli == guncel)
        sonuc["kasa_eslesmiyor"] = not sonuc["kasa_eslesiyor"]
    return sonuc


def ensure_exists(vault_path: str, password: str) -> str:
    """Generate a recovery key when missing; return the current one when present."""
    mevcut = load_key(vault_path)
    if mevcut and verify_container(container_path(vault_path), mevcut)["ok"]:
        return mevcut
    return refresh(vault_path, password)
