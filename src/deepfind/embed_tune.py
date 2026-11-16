"""Otomatik embedding paket boyu: CUDA, Vulkan ve CPU icin ortak, yapay zekasiz karar.

Sozlesme: DeepFind her zaman normal ayarla baslar (`NORMAL_TOPLU = 1`).
Kuyrukta yeterli is, kaynakta guvenli pay ve motor destegi ayni anda varsa
kademeli olarak daha fazla metin parcasi tek embedding isteginde denenir
(1 -> 2 -> 4 -> 8). Tek degisken paket boyudur: eszamanli HTTP, sunucu
yuvasi ve ek motor sureci bu modulun disindadir.

Basari, gercek is akisinda indekse basariyla yazilan parca/sn ile olculur;
kucuk ornek gurultusuyle ayar yukseltilmez. Acik ve tekrarlanan kazanc
yoksa, kaynak baskisi ya da hata gorulurse normal ayara donulur ve ayni
oturumda yeniden denenmez. Esikler asagida ve testte gorunur tutulur.

Motorun paket/girdi uzunlugu sinirlari korunur (`MAX_TOPLU_JETON`,
`MAX_GIRDI_JETON`); metin sessizce kirpilamaz, uzun metin ortusmeli
parcalanir (`KAPLAMA_JETON`).
"""
from __future__ import annotations

import os
import time

# --- Gorunur esikler (nedenleriyle birlikte) ---
NORMAL_TOPLU = 1
ADAY_TOPLULAR = (2, 4, 8)
MAX_TOPLU = 8
# MIN_KUYRUK: kucuk kuyruk olcum bitmeden biter; 8 bekleyen is altinda
# deneme maliyeti kazanci gecer, normal ayarda kalinir.
MIN_KUYRUK = 8
# MIN_PARCA: zamanlama gurultusu kucuk ornekte baskindir; her duzeyde
# en az 20 yazilmis parca gorulmeden karar verilmez.
MIN_PARCA = 20
# MIN_KAZANC: ayni donanimda calismalar arasi dalgalanma ~%10-15 bandindadir;
# %20 alti "kazanc" gurultu sayilir, ayar yukseltilmez.
MIN_KAZANC = 1.20
# TEKRAR: tek pencerelik sicrama yetmez; ust uste 2 pencerede ayni kazanc
# gorulmeden kalici gecis yapilmaz.
TEKRAR = 2
# PROBE toplam butcedir: kilit bekleme + tokenizasyon + tum embedding
# cagrilari bu tavanin altinda kalir (arayuz beklemez). NORMAL mevcut
# motor varsayilaniyla ayni tavandadir (120 sn). Toplu istek zaman asimina
# ugrarsa ayni kilit altinda sinirsiz tekli geri donuse girilmez.
PROBE_ZAMAN_ASIMI = 60.0
NORMAL_ZAMAN_ASIMI = 120.0
# Kaynak payi: ucretsiz RAM orani + mutlak esik ayni anda aranir; biri bile
# saglanamazsa ya da guvenilir bicimde bilinemezse normal ayarda kalinir.
# CUDA/Vulkan'da ayrica guvenilir VRAM payi sarttir; VRAM bilgisi yoksa
# (sistem_bellek yalniz RAM dondurur) GPU motorlarinda deneme acilmaz.
# Tum motorlar icin ortak karar akisi gecerlidir, esikler ortaktir.
MIN_BOS_ORAN = 0.25
MIN_BOS_MB = 1024
MIN_VRAM_BOS_ORAN = 0.25
MIN_VRAM_BOS_MB = 1024
# Motor sinirlari: llama-server `--batch-size 1024`, `--ctx-size 2048`;
# girdi penceresi 512 jeton. Tek istekteki toplam jeton 1024'u asamaz;
# asan grup bolunur, metin dusurulmez.
MAX_TOPLU_JETON = 1024
MAX_GIRDI_JETON = 512
KAPLAMA_JETON = 64

DESTEKLENEN_MOTORLAR = ("cpu", "vulkan", "cuda", "auto")


def motor_destekler(backend: str) -> bool:
    """Ayni llama-server API'si uc motorda da gecerli; ortak karar akisi."""
    return (backend or "") in DESTEKLENEN_MOTORLAR


def kuyruk_yeterli(bekleyen: int) -> bool:
    try:
        return int(bekleyen) >= MIN_KUYRUK
    except (TypeError, ValueError):
        return False


def sistem_bellek() -> dict | None:
    """Guvenilir bos bellek bilgisi; bilinemezse None.

    Windows'ta GlobalMemoryStatusEx (ctypes), POSIX'te sysconf; ucuncu
    parti bagimlilik yok. None donusu "bilinmiyor" demektir.
    """
    try:
        if os.name == "nt":
            import ctypes

            class _Durum(ctypes.Structure):
                _fields_ = [("uzunluk", ctypes.c_ulong),
                            ("bellek_yuku", ctypes.c_ulong),
                            ("toplam_fiz", ctypes.c_ulonglong),
                            ("bos_fiz", ctypes.c_ulonglong),
                            ("toplam_sayfa", ctypes.c_ulonglong),
                            ("bos_sayfa", ctypes.c_ulonglong),
                            ("toplam_sanal", ctypes.c_ulonglong),
                            ("bos_sanal", ctypes.c_ulonglong),
                            ("uzanti", ctypes.c_ulonglong)]

            durum = _Durum()
            durum.uzunluk = ctypes.sizeof(_Durum)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(durum)):
                return None
            toplam = int(durum.toplam_fiz)
            bos = int(durum.bos_fiz)
            if toplam <= 0:
                return None
            return {"bos_mb": bos / 1048576.0, "bos_oran": bos / toplam}
        # POSIX: sayfa sayisi x sayfa boyutu.
        try:
            sayfa = os.sysconf("SC_PHYS_PAGES")
            bos_sayfa = os.sysconf("SC_AVPHYS_PAGES")
            boyut = os.sysconf("SC_PAGE_SIZE")
        except (AttributeError, ValueError, OSError):
            return None
        toplam = sayfa * boyut
        bos = bos_sayfa * boyut
        if toplam <= 0:
            return None
        return {"bos_mb": bos / 1048576.0, "bos_oran": bos / toplam}
    except Exception:
        return None


def _ram_yeterli(bilgi: dict) -> bool:
    try:
        oran = float(bilgi.get("bos_oran", -1))
        mb = float(bilgi.get("bos_mb", -1))
    except (TypeError, ValueError):
        return False
    return oran >= MIN_BOS_ORAN and mb >= MIN_BOS_MB


def _vram_yeterli(bilgi: dict) -> bool | None:
    """True/False; anahtar yoksa None (bilinmiyor)."""
    try:
        v_oran = bilgi.get("vram_bos_oran")
        v_mb = bilgi.get("vram_bos_mb")
        if v_oran is None or v_mb is None:
            return None
        v_oran, v_mb = float(v_oran), float(v_mb)
    except (TypeError, ValueError):
        return None
    return v_oran >= MIN_VRAM_BOS_ORAN and v_mb >= MIN_VRAM_BOS_MB


def gpu_bilgi(ot, ram: dict | None = None) -> dict:
    """Karar sozlugu: RAM (taze) + GPU VRAM (oturum onbellekli, bekletmez).

    `ot` sahte oturum olabilir (`vram_bilgi` yoksa VRAM bilinmiyor
    sayilir). Sorgu hatasi/uzamasi yukseltilemez: None doner, cagiran
    normal ayarda kalir; indeksleme beklemez. Sorgu suruyorsa
    `vram_bekliyor` isareti konur: ilk olcum hazir degil diye deneme
    kalici kilitlenmez, guvenilir sonuc gelince deneme mumkundur.
    """
    bilgi = dict(ram) if isinstance(ram, dict) else {}
    if not bilgi:
        try:
            bilgi = sistem_bellek() or {}
        except Exception:
            bilgi = {}
    backend = getattr(ot, "backend", "cpu") or "cpu"
    if backend in ("cuda", "vulkan"):
        vram = None
        sorgu = getattr(ot, "vram_bilgi", None)
        if callable(sorgu):
            try:
                vram = sorgu()
            except Exception:
                vram = None
        durum = None
        durum_sorgu = getattr(ot, "vram_durumu", None)
        if callable(durum_sorgu):
            try:
                durum = durum_sorgu()
            except Exception:
                durum = None
        if isinstance(vram, dict):
            for anahtar in ("vram_bos_oran", "vram_bos_mb"):
                if vram.get(anahtar) is not None:
                    bilgi[anahtar] = vram[anahtar]
            if vram.get("aygit"):
                bilgi["gpu_aygit"] = vram["aygit"]
            if durum == "bekliyor":
                # Taze sonuc yolda: bu tur normal, kilit yok.
                bilgi["vram_bekliyor"] = True
        elif durum == "bekliyor":
            bilgi["vram_bekliyor"] = True
        else:
            bilgi["vram_bilinmiyor"] = True
    return bilgi


def kaynak_payi_var(bilgi: dict | None = None, backend: str = "cpu") -> bool:
    """Guvenli pay yoksa/bilinmiyorsa False (normal ayarda kal).

    Kuyruksuz kisa yol: `probe_engeli` ile ayni RAM/VRAM kurali.
    GPU'da `sistem_bellek()` yalniz RAM dondurdugu icin tek basina
    yeterli degildir (VRAM_BILINMIYOR -> False).
    """
    if bilgi is None:
        try:
            bilgi = sistem_bellek()
        except Exception:
            bilgi = None
    return probe_engeli(backend, bilgi, MIN_KUYRUK) is None


def probe_engeli(backend: str, bilgi: dict | None, bekleyen: int) -> str | None:
    """Deneme kapaliysa ilk engelin kodu, aciksa None.

    Kodlar: MOTOR_BILINMIYOR | KUYRUK_YETERSIZ | RAM_YETERSIZ |
    VRAM_BEKLİYOR | VRAM_BILINMIYOR | VRAM_YETERSIZ. GPU eslemesi
    (birden fazla aygit, ad/indis uyusmazligi) cozulemeyince
    VRAM_BILINMIYOR doner. Taze sonuc yoldaysa VRAM_BEKLİYOR: bu tur
    normal gecilir, deneme kilitlenmez.
    """
    if not motor_destekler(backend):
        return "MOTOR_BILINMIYOR"
    if not kuyruk_yeterli(bekleyen):
        return "KUYRUK_YETERSIZ"
    if not isinstance(bilgi, dict) or not _ram_yeterli(bilgi):
        return "RAM_YETERSIZ"
    if (backend or "") in ("cuda", "vulkan", "auto"):
        if bilgi.get("vram_bekliyor"):
            return "VRAM_BEKLİYOR"
        vram = _vram_yeterli(bilgi)
        if vram is None:
            return "VRAM_BILINMIYOR"
        if not vram:
            return "VRAM_YETERSIZ"
    return None


def toplu_grupla(uzunluklar: list[int], toplu: int) -> list[list[int]]:
    """Parca indislerini tek istekte gonderilecek gruplara bol.

    Her grupta en fazla `toplu` parca ve toplamda `MAX_TOPLU_JETON` jeton
    bulunur. Metin birlestirilmez, jeton dusurulmez; sinir asimi grubu
    boler (istek sayisi artar, veri kaybi olmaz). Saf ve test edilebilir.
    """
    try:
        adet = max(1, min(MAX_TOPLU, int(toplu)))
    except (TypeError, ValueError):
        adet = NORMAL_TOPLU
    gruplar: list[list[int]] = []
    oanki: list[int] = []
    oanki_jeton = 0
    for sira, uzunluk in enumerate(uzunluklar):
        uz = max(1, int(uzunluk))
        if oanki and (len(oanki) >= adet or oanki_jeton + uz > MAX_TOPLU_JETON):
            gruplar.append(oanki)
            oanki, oanki_jeton = [], 0
        oanki.append(sira)
        oanki_jeton += uz
    if oanki:
        gruplar.append(oanki)
    return gruplar


class TopluKarar:
    """Oturumluk karar durumu: normal baslar, kilitlenince donmez.

    Olcum birimi basariyla yazilmis parca/sn'dir; cagri tarafi her `gozlem`
    cagrisina yazilan parca sayisi ile gecen sureyi verir. Kucuk ornek
    (`MIN_PARCA` alti) karar degistirmez.
    """

    def __init__(self) -> None:
        self.aktif = NORMAL_TOPLU
        self.kilitli = False
        self._baz_parca = 0
        self._baz_sure = 0.0
        self._aday_parca: dict[int, int] = {}
        self._aday_sure: dict[int, float] = {}
        self._ust_uste = 0

    def aktif_toplu(self) -> int:
        return self.aktif

    def dene_hazir(self, bekleyen: int, bilgi: dict | None, backend: str) -> bool:
        if self.kilitli:
            return False
        return probe_engeli(backend, bilgi, bekleyen) is None

    def baz_hazir(self) -> bool:
        return self._baz_parca >= MIN_PARCA and self._baz_sure > 0

    def _sonraki_aday(self, simdiki: int) -> int:
        for aday in ADAY_TOPLULAR:
            if aday > simdiki:
                return aday
        return simdiki

    def gozlem(self, toplu: int, parca: int, saniye: float,
               hata: bool = False, kaynak_baskisi: bool = False) -> int:
        """Bir pencere sonucunu isle; yeni aktif topluyu dondur."""
        if hata or kaynak_baskisi:
            self.aktif = NORMAL_TOPLU
            self.kilitli = True
            self._ust_uste = 0
            return self.aktif
        try:
            parca = int(parca)
            saniye = float(saniye)
        except (TypeError, ValueError):
            return self.aktif
        if parca <= 0 or saniye <= 0:
            return self.aktif
        if toplu == NORMAL_TOPLU:
            self._baz_parca += parca
            self._baz_sure += saniye
            return self.aktif
        self._aday_parca[toplu] = self._aday_parca.get(toplu, 0) + parca
        self._aday_sure[toplu] = self._aday_sure.get(toplu, 0.0) + saniye
        if self._aday_parca[toplu] < MIN_PARCA:
            return self.aktif
        if self._baz_parca < MIN_PARCA or self._baz_sure <= 0:
            # Karsilastirilabilir baz yoksa yukseltme yapilmaz.
            return self.aktif
        baz_hiz = self._baz_parca / self._baz_sure
        aday_hiz = self._aday_parca[toplu] / self._aday_sure[toplu]
        if baz_hiz <= 0:
            return self.aktif
        kazanc = aday_hiz / baz_hiz
        if kazanc >= MIN_KAZANC:
            self._ust_uste += 1
            if self._ust_uste >= TEKRAR:
                self._ust_uste = 0
                self.aktif = self._sonraki_aday(toplu)
                # Bir sonraki kademeyi sifirdan olc; eski aday sayaclari durur.
                return self.aktif
            self.aktif = toplu
            return self.aktif
        # Acik kazanc yok: normale don, oturumda yeniden deneme.
        self.aktif = NORMAL_TOPLU
        self.kilitli = True
        self._ust_uste = 0
        return self.aktif


def simdi() -> float:
    return time.perf_counter()
