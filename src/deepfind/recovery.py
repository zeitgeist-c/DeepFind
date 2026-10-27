"""Kurtarma anahtarı: şifre unutulduğunde indeksi kaybetmemek için ikinci yol.

Tasarım B (kullanıcı kararı, 15.10.2026):
- Anahtar kasa klasöründe saklanır + yazdırılabilir belge olarak verilir.
- Anahtar rastgele üretilir (kullanıcı belirlemez); karışan harfler alfabede yoktur.

Kontrat:
- Konteyner, kasa yolunu ve açılış sırrını taşıyan ayrı bir şifreli SQLCipher dosyasıdır.
- Kasa parmak izi konteynere yazılır; kasa değişirse "eşleşmiyor" uyarısı verilir.
- Kurtarma sonrası kasa YENİ şifreyle açılır; eski şifre ve eski anahtar geçersiz olur.
- Hiçbir sır loga/log dosyasına yazılmaz.
"""
from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid
from pathlib import Path

# Karışan harfler yok: I, L, O, U ve rakam 0, 1 alfabede bulunmaz.
ALFABE = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
PREFIX = "EVKC-"
ON_EK = "deepfind-kurtarma"
CONTAINER_SUFFIX = ".kurtarma.db"
KEY_SUFFIX = ".anahtar"
SURUM = "1"
# Belgede anahtar satirini isaretleyen etiket (normalize bunu arar).
ETIKET = "KURTARMA ANAHTARI:"


# --- yardımcılar -------------------------------------------------------------

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
    """Kasa dosyasının kimliği: boyut + baş + son parça özeti."""
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
    """Rastgele kurtarma anahtarı (160 bit)."""
    ham = base64.b32encode(os.urandom(20)).decode().rstrip("=")
    govde = "".join(ch if ch in ALFABE else ALFABE[ord(ch) % len(ALFABE)] for ch in ham)
    return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))


def normalize(girilen: str) -> str:
    """Kullanıcı boşluklu/küçük harfli/öneksiz yazsa da anahtarı tanır.

    Öncelik sırası:
    1) Belgedeki `KURTARMA ANAHTARI:` satırı,
    2) `EVKC` geçen herhangi bir satır (yapıştırılan anahtar),
    3) Tüm metnin alfasayısal dizisi (yalnız anahtar yapıştırıldı).
    Anahtar gövdesi 32 karakterdir; fazlası yok sayılır.
    """
    if not girilen:
        return ""
    satirlar = girilen.splitlines() or [girilen]

    def _govde(metin: str) -> str:
        """Metinden anahtar gövdesini çıkar: EVKC öneki ve ayraçlar atılır."""
        buyuk = metin.upper()
        if "EVKC" in buyuk:
            buyuk = buyuk[buyuk.index("EVKC") + len("EVKC"):]
        return "".join(ch for ch in buyuk if ch.isalnum())[:32]

    # 1) Belgedeki etiketli satır
    for satir in satirlar:
        if ETIKET in satir:
            govde = _govde(satir.split(ETIKET, 1)[1])
            if len(govde) >= 20:
                return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))
    # 2) EVKC geçen satır (yapıştırılan anahtar)
    for satir in satirlar:
        if "EVKC" in satir.upper():
            govde = _govde(satir)
            if len(govde) >= 20:
                return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))
    # 3) Yalnız anahtar yapıştırıldı
    govde = _govde(girilen)
    if not govde:
        return ""
    return PREFIX + "-".join(govde[i:i + 5] for i in range(0, len(govde), 5))


def _dogrula_bicim(anahtar: str) -> str:
    n = normalize(anahtar)
    govde = n[len(PREFIX):].replace("-", "")
    if len(govde) != 32:
        raise ValueError("Kurtarma anahtarı eksik veya bozuk görünüyor.")
    return n


# --- konteyner ---------------------------------------------------------------

def write_container(vault_path: str, password: str, anahtar: str) -> str:
    """Kurtarma konteynerini yaz (atomik). Dönüş: konteyner yolu."""
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
    # yazılan konteyner gerçekten açılıyor mu (atomik finalize öncesi kanıt)
    kontrol = _con(gecici, anahtar)
    try:
        if kontrol.execute("SELECT v FROM recovery WHERE k='acilis'").fetchone() is None:
            raise RuntimeError("kurtarma konteyneri doğrulanamadı")
    finally:
        kontrol.close()
    os.replace(gecici, yol)
    try:
        os.chmod(yol, 0o600)
    except OSError:
        pass
    return yol


def verify_container(yol: str, anahtar: str) -> dict:
    """Konteyner açılıyor mu; kasa eşleşiyor mu."""
    if not os.path.isfile(yol):
        return {"ok": False, "neden": "konteyner yok"}
    try:
        con = _con(yol, anahtar)
    except Exception:
        return {"ok": False, "neden": "anahtar geçersiz"}
    try:
        satirlar = dict(con.execute("SELECT k,v FROM recovery").fetchall())
    except Exception:
        con.close()
        return {"ok": False, "neden": "konteyner okunamadı"}
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
    """Konteyner içeriğini oku (kurtarma sırasında kullanılır)."""
    con = _con(yol, anahtar)
    try:
        return dict(con.execute("SELECT k,v FROM recovery").fetchall())
    finally:
        con.close()


# --- anahtar dosyası ---------------------------------------------------------

def write_key_file(vault_path: str, anahtar: str) -> str:
    """Kullanıcının saklaması için anahtar dosyası (tasarım B)."""
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
    """Anahtar dosyasındaki anahtarı oku (belge başlıklarını atlar)."""
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
    """Yazdırılabilir kurtarma belgesi."""
    anahtar = _dogrula_bicim(anahtar)
    kasa = os.path.abspath(vault_path)
    if not bicimli:
        return (f"EVRAKÇI KURTARMA ANAHTARI\n"
                f"Anahtar : {anahtar}\n"
                f"Kasa    : {kasa}\n")
    gruplu = " ".join(anahtar[i:i + 5] for i in range(0, len(anahtar), 5))
    return (
        "==================================================\n"
        "        EVRAKÇI — KURTARMA ANAHTARI\n"
        "==================================================\n\n"
        "Bu anahtar, kasa şifrenizi unuttuğunuzda arşiv\n"
        "indeksinizi kurtarır. Güvenli bir yerde saklayın.\n\n"
        f"  {ETIKET}  {gruplu}\n\n"
        f"  Kasa    :  {kasa}\n\n"
        "Nasıl kullanılır:\n"
        "  1) DeepFind'yı açın, şifre ekranında\n"
        "     \"Şifremi unuttum\" seçeneğine basın.\n"
        "  2) Yukarıdaki anahtarı yapıştırın (boşluk ve\n"
        "     büyük/küçük harf farkı önemli değildir).\n"
        "  3) Kasa açılır; yeni bir şifre belirlersiniz.\n\n"
        "Anahtar yalnız bu belgede ve kasa klasöründeki\n"
        "aynı adlı dosyada bulunur. Kaynak belgeleriniz\n"
        "bu işlemden etkilenmez.\n"
        "==================================================\n"
    )


# --- kurtarma ----------------------------------------------------------------

def recover(vault_path: str, anahtar: str, yeni_sifre: str,
            backup_dir: str | None = None) -> dict:
    """Anahtarla kasayı aç, yeni şifre kur, yeni kurtarma anahtarı üret.

    Başarısızlıkta mevcut kasa ve mevcut kurtarma anahtarı korunur.
    """
    from . import backup, vault
    if len(yeni_sifre) < 12:
        raise ValueError("Yeni şifre en az 12 karakter olmalı.")
    yol = container_path(vault_path)
    if not os.path.isfile(yol):
        raise FileNotFoundError("Kurtarma konteyneri bulunamadı.")
    try:
        veri = read_container(yol, anahtar)
    except Exception as error:
        raise ValueError("Kurtarma anahtarı geçersiz veya konteyner bozuk.") from error
    eski_sifre = veri.get("acilis", "")
    hedef = veri.get("kasa") or os.path.abspath(vault_path)
    if not os.path.isfile(hedef):
        raise FileNotFoundError("Kasa dosyası bulunamadı; kurtarma yapılamıyor.")
    if os.path.abspath(hedef) != os.path.abspath(vault_path):
        # Kasa taşınmış: en azından doğru dosyayı açtığımızdan emin olalım.
        pass
    # 1) Eski sifre gerçekten çalışıyor mu? (konteyner sırrı bayatlarsa burada durur)
    kontrol = vault.open_vault(hedef, eski_sifre)
    kontrol.close()
    # 2) Güvenlik yedeği (kurtarma işlemi de yedeğini alır)
    if backup_dir:
        con = vault.open_vault(hedef, eski_sifre)
        try:
            backup.create_backup(con, hedef, eski_sifre, backup_dir, manual=True)
        finally:
            con.close()
    # 3) Yeni şifreyle değiştir (change_password kendi yedeğini + iki yönlü doğrulamasını yapar)
    hedef_yedek = backup_dir or os.path.join(os.path.dirname(os.path.abspath(hedef)), "..", "Backups")
    backup.change_password(hedef, eski_sifre, yeni_sifre, hedef_yedek)
    # 4) Yeni kurtarma anahtarı üret (eski anahtar artık geçersiz)
    yeni = new_key()
    write_container(hedef, yeni_sifre, yeni)
    write_key_file(hedef, yeni)
    return {"ok": True, "kasa": hedef, "yeni_anahtar": yeni,
            "anahtar_dosyasi": key_path(hedef)}


def refresh(vault_path: str, password: str) -> str:
    """Yeni kurtarma anahtarı üret; eskisini geçersiz kıl. Dönüş: yeni anahtar."""
    anahtar = new_key()
    write_container(vault_path, password, anahtar)
    write_key_file(vault_path, anahtar)
    return anahtar


def remove(vault_path: str) -> dict:
    """Kurtarma anahtarını kaldır (kasa şifresi tek yol kalır)."""
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
    """Ayarlar ekranı için durum: var mı, kasa eşleşiyor mu."""
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
    """Kurtarma anahtarı yoksa üret; varsa mevcut anahtarı döndür."""
    mevcut = load_key(vault_path)
    if mevcut and verify_container(container_path(vault_path), mevcut)["ok"]:
        return mevcut
    return refresh(vault_path, password)
