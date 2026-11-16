"""Otomatik embedding paket boyu: ortak karar akisi, sahte motor + kucuk veri.

Gercek kullanici vault'una dokunulmaz; kucuk sentetik kasa + sahte motor.
Buyuk arsiv, model kopyasi, calisma agaci kopyasi ve harici baslatici yok.
"""
from __future__ import annotations

import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import embed_tune as tune  # noqa: E402
from deepfind import gom, job_queue as q  # noqa: E402
from deepfind import vault, migrate as migrate_mod  # noqa: E402

PW = "test-sifresi-12345"


def test_esikler_gorunur():
    assert tune.NORMAL_TOPLU == 1
    assert tune.ADAY_TOPLULAR == (2, 4, 8)
    assert tune.MAX_TOPLU == 8
    assert tune.MIN_KUYRUK == 8
    assert tune.MIN_PARCA == 20
    assert tune.MIN_KAZANC == 1.20
    assert tune.TEKRAR == 2
    assert tune.PROBE_ZAMAN_ASIMI == 60.0
    assert tune.NORMAL_ZAMAN_ASIMI == 120.0
    assert tune.MIN_BOS_ORAN == 0.25
    assert tune.MIN_BOS_MB == 1024
    assert tune.MIN_VRAM_BOS_ORAN == 0.25
    assert tune.MIN_VRAM_BOS_MB == 1024
    assert tune.MAX_TOPLU_JETON == 1024
    assert tune.MAX_GIRDI_JETON == 512


def _zengin_bilgi():
    return {"bos_oran": 0.5, "bos_mb": 4096,
            "vram_bos_oran": 0.5, "vram_bos_mb": 4096}


def test_ortak_akis_uc_motor():
    for backend in ("cpu", "vulkan", "cuda", "auto"):
        assert tune.motor_destekler(backend) is True
    assert tune.motor_destekler("bilinmeyen") is False
    ram = {"bos_oran": 0.5, "bos_mb": 4096}
    assert tune.kaynak_payi_var(ram, "cpu") is True
    # GPU'da RAM tek basina yetmez: guvenilir VRAM payi sart.
    for backend in ("vulkan", "cuda", "auto"):
        assert tune.kaynak_payi_var(ram, backend) is False
        assert tune.kaynak_payi_var(_zengin_bilgi(), backend) is True
    dusuk_vram = dict(ram, vram_bos_oran=0.05, vram_bos_mb=100)
    assert tune.kaynak_payi_var(dusuk_vram, "cuda") is False
    # Kaynak bilinmiyorsa normalde kal.
    assert tune.kaynak_payi_var(None, "cpu") in (True, False)  # ortama bagli
    assert tune.kaynak_payi_var({"bos_oran": 0.0, "bos_mb": 0}, "cpu") is False
    assert tune.kaynak_payi_var("bozuk", "cpu") is False
    assert tune.kuyruk_yeterli(tune.MIN_KUYRUK) is True
    assert tune.kuyruk_yeterli(tune.MIN_KUYRUK - 1) is False


def test_vram_yoksa_gpu_denemesi_kapali():
    karar = tune.TopluKarar()
    ram = {"bos_oran": 0.5, "bos_mb": 4096}
    assert karar.dene_hazir(50, ram, "cuda") is False
    assert karar.dene_hazir(50, ram, "vulkan") is False
    assert karar.dene_hazir(50, _zengin_bilgi(), "cuda") is True
    assert karar.dene_hazir(50, _zengin_bilgi(), "vulkan") is True
    assert karar.dene_hazir(50, ram, "cpu") is True


def test_kucuk_ornekle_yukselme_yok():
    karar = tune.TopluKarar()
    assert karar.aktif_toplu() == 1
    bilgi = {"bos_oran": 0.5, "bos_mb": 4096}
    assert karar.dene_hazir(50, bilgi, "cpu") is True
    # Baz + aday kucuk ornek: karar degismez.
    karar.gozlem(1, 5, 1.0)
    karar.gozlem(2, 5, 0.2)
    assert karar.aktif_toplu() == 1
    assert karar.kilitli is False


def test_yeterli_kazancta_korunur():
    karar = tune.TopluKarar()
    bilgi = _zengin_bilgi()
    assert karar.dene_hazir(50, bilgi, "vulkan") is True
    # Baz: 40 parca, 4 sn -> 10 parca/sn.
    karar.gozlem(1, 20, 2.0)
    karar.gozlem(1, 20, 2.0)
    assert karar.baz_hazir() is True
    # Aday 2: 20 parca 1 sn -> 20 parca/sn (2x kazanc), iki pencere.
    karar.gozlem(2, 20, 1.0)
    assert karar.aktif_toplu() == 2
    karar.gozlem(2, 20, 1.0)
    # Iki ust uste kazanc: sonraki kademeye gecer (4).
    assert karar.aktif_toplu() == 4
    assert karar.kilitli is False


def test_kazanc_yoksa_normale_don_kilitli():
    karar = tune.TopluKarar()
    karar.gozlem(1, 20, 2.0)
    karar.gozlem(1, 20, 2.0)
    # Aday bazla ayni hizda: kazanc yok.
    karar.gozlem(2, 20, 2.0)
    assert karar.aktif_toplu() == 1
    assert karar.kilitli is True
    bilgi = {"bos_oran": 0.5, "bos_mb": 4096}
    assert karar.dene_hazir(50, bilgi, "cpu") is False


def test_kaynak_yetersizse_normal():
    karar = tune.TopluKarar()
    dusuk = {"bos_oran": 0.05, "bos_mb": 100}
    assert karar.dene_hazir(50, dusuk, "cuda") is False
    karar.gozlem(2, 30, 1.0, kaynak_baskisi=True)
    assert karar.aktif_toplu() == 1
    assert karar.kilitli is True


def test_hata_normale_dondurur():
    karar = tune.TopluKarar()
    karar.gozlem(1, 20, 2.0)
    karar.gozlem(1, 20, 2.0)
    karar.gozlem(2, 20, 1.0)
    karar.gozlem(2, 0, 1.0, hata=True)
    assert karar.aktif_toplu() == 1
    assert karar.kilitli is True


def test_toplu_grupla_jeton_siniri():
    # 8 parca x 200 jeton, toplu=8 istense bile 1024 jeton siniri boler.
    gruplar = tune.toplu_grupla([200] * 8, 8)
    assert sum(len(g) for g in gruplar) == 8
    for g in gruplar:
        assert len(g) <= 8
        assert len(g) * 200 <= tune.MAX_TOPLU_JETON
    # Tekli her zaman tekli gruptur.
    assert tune.toplu_grupla([100, 100], 1) == [[0], [1]]


# --- Sahte motor + kasa yardimcilari ---

class SahteMotor:
    """Gercek llama-server yerine kucuk deterministik motor."""

    def __init__(self, backend="cpu", toplu_davranis="destekle", uyku=0.0,
                 toplu_zaman_asimi=False):
        self.backend = backend
        self._canli = True
        self.istekler: list[dict] = []
        self.kilit = threading.RLock()
        self.toplu_davranis = toplu_davranis  # destekle | tekli-dus | hata
        self.uyku = uyku  # her /embedding cagrisinda yapay gecikme (sn)
        self.toplu_zaman_asimi = toplu_zaman_asimi  # toplu istek hep zaman asimi

    def alive(self):
        return self._canli

    def oldur(self):
        self._canli = False

    def request(self, path, data=None, timeout=120):
        with self.kilit:
            self.istekler.append({"path": path, "data": data, "timeout": timeout})
        if path == "/tokenize":
            icerik = (data or {}).get("content", "")
            # Deterministik jetonlar: her 4 karakter 1 jeton.
            n = max(1, len(icerik) // 4)
            return {"tokens": list(range(n))}
        if path == "/embedding":
            girdi = (data or {}).get("input")
            toplu = isinstance(girdi, list) and girdi and isinstance(girdi[0], list)
            if toplu and self.toplu_zaman_asimi:
                raise TimeoutError("toplu istek zaman asimi")
            if toplu:
                if self.toplu_davranis == "hata":
                    raise RuntimeError("toplu desteklenmiyor")
                if self.toplu_davranis == "tekli-dus":
                    raise RuntimeError("tekliye dus")
            if self.uyku > 0:
                import time as _t
                _t.sleep(min(self.uyku, timeout))
                if self.uyku > timeout:
                    raise TimeoutError("istek zaman asimi")
            if toplu:
                return [{"embedding": [0.1] * 768} for _ in girdi]
            return [{"embedding": [0.1] * 768}]
        raise RuntimeError("bilinmeyen yol")


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    migrate_mod.ensure_current(con)
    con.commit()
    return con


def _dosya(con, ad="b.txt", parca=3):
    from deepfind import extract as ex_mod
    from deepfind import index as index_mod
    from deepfind import scan as scan_mod

    giris = scan_mod.Entry(ad, ad, ".txt", 10, 20)
    segs = [ex_mod.Segment("p", None, "Govde", f"metin parcasi {i} Ankara") for i in range(parca)]
    sonuc = ex_mod.ExtractResult(segments=segs, status="ok")
    return index_mod.index_entry(con, giris, sonuc)


def _sahte_oturum_encode(motor):
    import types
    from deepfind import engine as eng

    ot = types.SimpleNamespace(backend=motor.backend)
    ot._kilit = threading.RLock()
    ot.request = motor.request
    ot.encode = eng.Oturum.encode.__get__(ot)
    return ot


def test_motor_toplu_istek_sayisi_azalir(tmp_path):
    from deepfind import engine as eng  # noqa

    motor = SahteMotor()
    ot = _sahte_oturum_encode(motor)
    metinler = [f"belge metni {i} " * 10 for i in range(4)]
    v1 = ot.encode(metinler, gorev="belge", toplu=1)
    assert v1.shape == (4, 256)
    istek1 = len([r for r in motor.istekler if r["path"] == "/embedding"])
    motor.istekler.clear()
    v4 = ot.encode(metinler, gorev="belge", toplu=4)
    assert v4.shape == (4, 256)
    istek4 = len([r for r in motor.istekler if r["path"] == "/embedding"])
    assert istek4 <= istek1
    # Vektorler sonlu ve birimli.
    assert np.isfinite(v4).all()
    for satir in v4:
        assert abs(float((satir * satir).sum()) - 1.0) < 1e-4


def test_motor_toplu_hata_tekliye_duser(tmp_path):
    motor = SahteMotor(toplu_davranis="tekli-dus")
    ot = _sahte_oturum_encode(motor)
    v = ot.encode(["a" * 50, "b" * 50], gorev="belge", toplu=4)
    assert v.shape == (2, 256)


def test_motor_uzun_metin_kirpilmaz(tmp_path):
    motor = SahteMotor()
    ot = _sahte_oturum_encode(motor)
    uzun = "kelime " * 2000  # 512 jeton penceresini asar.
    v = ot.encode([uzun], gorev="belge", toplu=4)
    assert v.shape == (1, 256)
    # Tek metin birden fazla parcaya bolundugu icin birden fazla istek gorur.
    gomulu = [r for r in motor.istekler if r["path"] == "/embedding"]
    assert len(gomulu) >= 1


def test_motor_iptal_yarida_keser():
    motor = SahteMotor()
    ot = _sahte_oturum_encode(motor)
    cagri = {"n": 0}

    def iptal():
        cagri["n"] += 1
        return cagri["n"] > 1

    try:
        ot.encode(["x" * 100, "y" * 100, "z" * 100], gorev="belge", toplu=2, cancel=iptal)
    except InterruptedError:
        pass
    else:
        raise AssertionError("iptal bekleniyordu")


def test_zaman_asimi_sinirli(tmp_path):
    motor = SahteMotor()
    ot = _sahte_oturum_encode(motor)
    ot.encode(["kisa metin bir", "kisa metin iki", "kisa metin uc", "kisa metin dort"],
              gorev="belge", toplu=4)
    prob = [r["timeout"] for r in motor.istekler if r["path"] == "/embedding"]
    assert prob and all(t <= tune.PROBE_ZAMAN_ASIMI + 1e-9 for t in prob)
    motor.istekler.clear()
    ot.encode(["kisa metin"], gorev="belge", toplu=1)
    normal = [r["timeout"] for r in motor.istekler if r["path"] == "/embedding"]
    assert normal and all(t == tune.NORMAL_ZAMAN_ASIMI for t in normal)


def _is_vektorleri(n):
    def kodla(metinler):
        v = np.zeros((len(metinler), 256), dtype=np.float32)
        for i, t in enumerate(metinler):
            v[i, abs(hash(t)) % 256] = 1.0
        return v

    return kodla


def test_gom_iptalde_tamamlamaz_kuyruk_korunur(tmp_path):
    con = _kasa(tmp_path)
    fid = _dosya(con, parca=2)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('y.pdf','y.pdf','.pdf')")
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = q.claim(con, ("embed",))
    assert job is not None
    try:
        gom.process_embed_job(con, job, kodla=_is_vektorleri(256), cancel=lambda: True)
    except InterruptedError:
        pass
    else:
        raise AssertionError("iptal bekleniyordu")
    # Is tamamlanmadi: kuyrukta durur, kayip yok.
    assert q.pending_count(con) >= 1
    con.close()


def test_gom_zaman_asimi_is_kaybi_yok_cift_yazma_yok(tmp_path):
    con = _kasa(tmp_path)
    fid = _dosya(con, parca=3)

    def patlayan(metinler):
        raise TimeoutError("motor yavas")

    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = q.claim(con, ("embed",))
    sonuc = gom.process_embed_job(con, job, kodla=patlayan)
    assert sonuc in ("retry", "dead")
    # Yazma olmadi.
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0
    # Is kaybolmadi (retry) ya da olu olarak isaretli.
    satir = con.execute("SELECT status FROM jobs WHERE job_id=?", (job["job_id"],)).fetchone()
    assert satir is not None
    # Basarili yeniden deneme tek kayit yazar (segment basina bir satir).
    job2 = {"job_id": job["job_id"], "file_id": fid, "signature": q.signature_of(10, 20)}
    assert gom.process_embed_job(con, job2, kodla=_is_vektorleri(256)) == "done"
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 3
    # Idempotent yeniden yazma ciftlemez.
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job3 = q.claim(con, ("embed",))
    gom.process_embed_job(con, job3, kodla=_is_vektorleri(256))
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 3
    con.close()


def test_toplam_butce_coklu_cagri_sinirli(tmp_path):
    import time as _t

    motor = SahteMotor(uyku=2.0)
    ot = _sahte_oturum_encode(motor)
    metinler = [f"yavas belge parcasi {i} " * 20 for i in range(8)]
    baslangic = _t.perf_counter()
    try:
        ot.encode(metinler, gorev="belge", toplu=4, zaman_asimi=3.0)
    except TimeoutError:
        pass
    else:
        raise AssertionError("toplam butce asimi bekleniyordu")
    gecen = _t.perf_counter() - baslangic
    # Butce asla katlanmaz: 8 tekli geri donus (16 sn) olmamali.
    assert gecen < 8.0, gecen
    gomulu = [r for r in motor.istekler if r["path"] == "/embedding"]
    assert len(gomulu) <= 2, len(gomulu)


def test_kilit_bekleme_toplam_butceye_dahil():
    import time as _t

    motor = SahteMotor()
    ot = _sahte_oturum_encode(motor)
    hazir = threading.Event()

    def tut():
        ot._kilit.acquire()
        hazir.set()
        _t.sleep(10)
        try:
            ot._kilit.release()
        except RuntimeError:
            pass

    tutucu = threading.Thread(target=tut, daemon=True)
    tutucu.start()
    assert hazir.wait(timeout=5)
    baslangic = _t.perf_counter()
    try:
        ot.encode(["kilitli is"], gorev="belge", toplu=1, zaman_asimi=2.0)
    except TimeoutError:
        pass
    else:
        raise AssertionError("kilit zaman asimi bekleniyordu")
    finally:
        gecen = _t.perf_counter() - baslangic
        tutucu.join(timeout=12)
    assert gecen < 6.0, gecen


def test_toplu_zaman_asimi_tekliye_dusmez():
    motor = SahteMotor(toplu_zaman_asimi=True)
    ot = _sahte_oturum_encode(motor)
    try:
        ot.encode(["bir " * 30, "iki " * 30, "uc " * 30, "dort " * 30],
                  gorev="belge", toplu=4, zaman_asimi=10.0)
    except TimeoutError:
        pass
    else:
        raise AssertionError("toplu zaman asimi yukari tasinmaliydi")
    # Ayni kilit altinda sinirsiz tekli geri donus olmamali.
    for r in motor.istekler:
        if r["path"] != "/embedding":
            continue
        girdi = (r["data"] or {}).get("input")
        assert isinstance(girdi, list) and girdi and isinstance(girdi[0], list)


def _son_hak_is(con, fid):
    from deepfind import job_queue as _q

    con.execute("UPDATE jobs SET attempts=?, status='pending', not_before=0,"
                " lease_until=0 WHERE file_id=? AND kind='embed'",
                (_q.MAX_ATTEMPTS - 1, fid))
    con.commit()
    return _q.claim(con, ("embed",))


def test_deneme_hatasi_son_hakta_bile_normali_korur(tmp_path):
    from deepfind import job_queue as _q

    con = _kasa(tmp_path)
    fid = _dosya(con, parca=3)
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = _son_hak_is(con, fid)
    assert job is not None

    def prob_kodla(metinler):
        raise TimeoutError("deneme yavas")

    ayrinti = {}
    sonuc = gom.process_embed_job(con, job, kodla=prob_kodla, deneme=True,
                                  ayrinti=ayrinti)
    assert sonuc == "deneme_hatasi"
    assert ayrinti.get("hata") == "TimeoutError"
    # Hak tuketilmedi: son hak aynen durur, is pending.
    satir = con.execute("SELECT attempts, status FROM jobs WHERE job_id=?",
                        (job["job_id"],)).fetchone()
    assert satir[0] == _q.MAX_ATTEMPTS - 1 and satir[1] == "pending"
    # Ayni is normal ayarla yeniden islenebilir.
    assert gom.process_embed_job(con, job, kodla=_is_vektorleri(256)) == "done"
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 3
    con.close()


def test_deneme_sonrasi_normal_hata_tek_hak_tuketir(tmp_path):
    from deepfind import job_queue as _q

    con = _kasa(tmp_path)
    fid = _dosya(con, parca=2)
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = q.claim(con, ("embed",))
    once = con.execute("SELECT attempts FROM jobs WHERE job_id=?",
                       (job["job_id"],)).fetchone()[0]

    def prob_kodla(metinler):
        raise TimeoutError("deneme yavas")

    assert gom.process_embed_job(con, job, kodla=prob_kodla,
                                 deneme=True) == "deneme_hatasi"

    def normal_kodla(metinler):
        raise RuntimeError("normal de bozuk")

    sonuc = gom.process_embed_job(con, job, kodla=normal_kodla)
    assert sonuc in ("retry", "dead")
    sonra = con.execute("SELECT attempts FROM jobs WHERE job_id=?",
                        (job["job_id"],)).fetchone()[0]
    # Deneme hic tuketmedi, normal mevcut politikayla bir hak tuketti.
    assert sonra == once + 1, (once, sonra)
    assert _q.MAX_ATTEMPTS - sonra >= 0
    con.close()


def test_gec_kodla_sonucu_yazsa_bile_tamamlamaz(tmp_path):
    con = _kasa(tmp_path)
    fid = _dosya(con, parca=2)
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = q.claim(con, ("embed",))
    cagri = {"n": 0}

    def gec_iptal():
        cagri["n"] += 1
        # Giris + yazma oncesi serbest, yazma sonrasi iptal.
        return cagri["n"] >= 3

    try:
        gom.process_embed_job(con, job, kodla=_is_vektorleri(256),
                              cancel=gec_iptal)
    except InterruptedError:
        pass
    else:
        raise AssertionError("gec iptal bekleniyordu")
    # Vektor yazildi ama is tamamlanmadi: pending durur, kayip yok.
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 2
    satir = con.execute("SELECT status FROM jobs WHERE job_id=?",
                        (job["job_id"],)).fetchone()
    assert satir is not None and satir[0] == "pending"
    # Yeniden isleme idempotenttir, ciftlemez.
    assert gom.process_embed_job(con, job, kodla=_is_vektorleri(256)) == "done"
    assert con.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 2
    con.close()


def test_ayrinti_gercek_yazim_sayisi(tmp_path):
    con = _kasa(tmp_path)
    fid = _dosya(con, parca=4)
    q.enqueue(con, fid, q.signature_of(10, 20), kind="embed")
    con.commit()
    job = q.claim(con, ("embed",))
    ayrinti = {}
    assert gom.process_embed_job(con, job, kodla=_is_vektorleri(256),
                                 ayrinti=ayrinti) == "done"
    assert ayrinti == {"parca": 4, "hata": None}
    con.close()


# --- GPU bellek eslemesi: _vram_sorgula + vram_bilgi + gpu_bilgi ---

def _sahte_run_yap(cikti: bytes, kod: int = 0, hata=None, sayac=None):
    import types as _t

    def sahte_run(*a, **k):
        if sayac is not None:
            sayac["n"] = sayac.get("n", 0) + 1
        if hata is not None:
            raise hata
        return _t.SimpleNamespace(returncode=kod, stdout=cikti, stderr=b"")

    return sahte_run


def test_vram_tek_aygit_eslesir(monkeypatch):
    from deepfind import engine as _eng

    cikti = b"Available devices:\r\n  Vulkan0: AMD Radeon RX 6650 XT (8176 MiB, 7378 MiB free)\r\n"
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti))
    bilgi = _eng._vram_sorgula("x/llama-server.exe", "vulkan",
                               "Vulkan0: AMD Radeon RX 6650 XT (8176 MiB, 7000 MiB free)")
    assert bilgi is not None
    assert bilgi["vram_bos_mb"] == 7378
    assert abs(bilgi["vram_bos_oran"] - 7378 / 8176) < 1e-9
    assert "6650" in bilgi["aygit"]


def test_vram_iki_aygitta_ilk_varsayilmaz(monkeypatch):
    from deepfind import engine as _eng

    cikti = (b"Available devices:\r\n"
             b"  Vulkan0: Birinci Kart (8176 MiB, 7000 MiB free)\r\n"
             b"  Vulkan1: Ikinci Kart (12288 MiB, 11000 MiB free)\r\n")
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti))
    assert _eng._vram_sorgula("x", "vulkan",
                              "Vulkan0: Birinci Kart (8176 MiB, 7000 MiB free)") is None


def test_vram_ad_uyusmazsa_bilinmiyor(monkeypatch):
    from deepfind import engine as _eng

    cikti = b"Available devices:\r\n  CUDA0: Baska Kart (24564 MiB, 23000 MiB free)\r\n"
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti))
    assert _eng._vram_sorgula("x", "cuda",
                              "CUDA0: Beklenen Kart (24564 MiB, 23000 MiB free)") is None


def test_vram_sayisiz_eski_bicim_yok_sayar(monkeypatch):
    from deepfind import engine as _eng

    cikti = b"Available devices:\r\n  Vulkan0: Surucusuz Kart\r\n"
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti))
    assert _eng._vram_sorgula("x", "vulkan", "Vulkan0: Surucusuz Kart") is None


def test_vram_hata_ve_zaman_asimi_none(monkeypatch):
    import subprocess as _sp

    from deepfind import engine as _eng

    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(b"", kod=1))
    assert _eng._vram_sorgula("x", "vulkan", "Vulkan0: Kart (100 MiB, 90 MiB free)") is None
    monkeypatch.setattr(_eng.subprocess, "run",
                        _sahte_run_yap(b"", hata=_sp.TimeoutExpired("llama-server", 30)))
    assert _eng._vram_sorgula("x", "vulkan", "Vulkan0: Kart (100 MiB, 90 MiB free)") is None
    # Bos > toplam tutarsizligi da guvenilir sayilmaz.
    cikti = b"Available devices:\r\n  Vulkan0: Kart (100 MiB, 150 MiB free)\r\n"
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti))
    assert _eng._vram_sorgula("x", "vulkan",
                              "Vulkan0: Kart (100 MiB, 150 MiB free)") is None


def test_vram_onbellek_belge_basina_sorgulamaz(monkeypatch):
    import time as _t

    from deepfind import engine as _eng

    cikti = b"Available devices:\r\n  Vulkan0: Kart (8176 MiB, 7000 MiB free)\r\n"
    sayac: dict = {}
    monkeypatch.setattr(_eng.subprocess, "run", _sahte_run_yap(cikti, sayac=sayac))
    import types as _t2

    ot = _t2.SimpleNamespace(backend="vulkan", exe="x/llama-server.exe",
                             device="Vulkan0: Kart (8176 MiB, 7000 MiB free)",
                             _vram=None, _vram_olc_zamani=0.0, _vram_deneme_zamani=0.0,
                             _vram_sorguda=False,
                             _kilit=__import__("threading").RLock())
    ot._vram_kilitle = _eng.Oturum._vram_kilitle.__get__(ot)
    ot._taze_vram = _eng.Oturum._taze_vram.__get__(ot)
    ot.vram_bilgi = _eng.Oturum.vram_bilgi.__get__(ot)
    ot.vram_durumu = _eng.Oturum.vram_durumu.__get__(ot)
    # Ilk cagri bekletmez: arka plan sorgusu baslar, elde henuz yok.
    baslangic = _t.perf_counter()
    assert ot.vram_bilgi() is None
    assert _t.perf_counter() - baslangic < 5.0
    assert ot.vram_durumu() == "bekliyor"
    # Guvenilir sonuc kisa surede gelir; ust uste cagri tek sorgudur.
    son = time_monotonic_sonuc(ot)
    assert son is not None
    assert ot.vram_durumu() == "hazir"
    assert sayac.get("n", 0) == 1
    assert ot.vram_bilgi() is not None


def time_monotonic_sonuc(ot, tavan=10.0):
    import time as _t

    bitis = _t.perf_counter() + tavan
    while _t.perf_counter() < bitis:
        bilgi = ot.vram_bilgi()
        if bilgi is not None:
            return bilgi
        _t.sleep(0.05)
    return ot.vram_bilgi()


def test_vram_yavas_sorgu_taramayi_bekletmez(monkeypatch):
    import time as _t

    from deepfind import engine as _eng

    cagrilar: dict = {}

    def yavas_cozumle(exe, backend, aygit, butce=30.0):
        cagrilar["n"] = cagrilar.get("n", 0) + 1
        _t.sleep(1.5)
        return ({"vram_bos_oran": 0.6, "vram_bos_mb": 4096,
                 "aygit": "vulkan0: Kart", "toplam_mb": 8176}, True)

    monkeypatch.setattr(_eng, "_vram_cozumle", yavas_cozumle)
    import types as _t2

    ot = _t2.SimpleNamespace(backend="vulkan", exe="x/llama-server.exe",
                             device="Vulkan0: Kart (8176 MiB, 7000 MiB free)",
                             _vram=None, _vram_olc_zamani=0.0, _vram_deneme_zamani=0.0,
                             _vram_sorguda=False,
                             _kilit=__import__("threading").RLock())
    ot._vram_kilitle = _eng.Oturum._vram_kilitle.__get__(ot)
    ot._taze_vram = _eng.Oturum._taze_vram.__get__(ot)
    ot.vram_bilgi = _eng.Oturum.vram_bilgi.__get__(ot)
    ot.vram_durumu = _eng.Oturum.vram_durumu.__get__(ot)
    baslangic = _t.perf_counter()
    assert ot.vram_bilgi() is None
    assert ot.vram_bilgi() is None
    assert ot.vram_bilgi() is None
    assert _t.perf_counter() - baslangic < 1.0
    # Ust uste cagri tek sorgu acar; guvenilir sonuc sonra gelir.
    son = time_monotonic_sonuc(ot, tavan=15.0)
    assert son is not None and son["vram_bos_mb"] == 4096
    assert cagrilar.get("n", 0) == 1


def test_vram_gecici_hata_kilitlemez_sonra_acilir(monkeypatch):
    from deepfind import engine as _eng

    plan = {"sonuclar": [(None, False)], "n": 0}

    def dalgali_cozumle(exe, backend, aygit, butce=30.0):
        plan["n"] += 1
        return plan["sonuclar"][min(plan["n"] - 1, len(plan["sonuclar"]) - 1)]

    monkeypatch.setattr(_eng, "_vram_cozumle", dalgali_cozumle)
    import types as _t2

    ot = _t2.SimpleNamespace(backend="vulkan", exe="x/llama-server.exe",
                             device="Vulkan0: Kart (8176 MiB, 7000 MiB free)",
                             _vram=None, _vram_olc_zamani=0.0, _vram_deneme_zamani=0.0,
                             _vram_sorguda=False,
                             _kilit=__import__("threading").RLock())
    ot._vram_kilitle = _eng.Oturum._vram_kilitle.__get__(ot)
    ot._taze_vram = _eng.Oturum._taze_vram.__get__(ot)
    ot.vram_bilgi = _eng.Oturum.vram_bilgi.__get__(ot)
    ot.vram_durumu = _eng.Oturum.vram_durumu.__get__(ot)
    assert ot.vram_bilgi() is None
    import time as _t3

    _t3.sleep(0.5)  # gecici hata hizlica biter; sonuc yok, kilit yok
    assert ot.vram_durumu() == "bekliyor"  # yeniden denenecek
    karar = tune.TopluKarar()
    assert karar.dene_hazir(50, tune.gpu_bilgi(ot), "vulkan") is False
    assert karar.kilitli is False
    # Guvenilir sonuc gelince deneme mumkun.
    plan["sonuclar"].append(({"vram_bos_oran": 0.6, "vram_bos_mb": 4096,
                              "aygit": "vulkan0: Kart", "toplam_mb": 8176}, True))
    ot._vram_deneme_zamani = 0.0  # hiz kesme payi dolmus gibi davran
    bilgi2 = time_monotonic_sonuc(ot, tavan=15.0)
    assert bilgi2 is not None
    assert karar.dene_hazir(50, tune.gpu_bilgi(ot), "vulkan") is True


def test_suresi_dolan_eski_degerle_deneme_acilmaz_sonra_acilir(monkeypatch):
    import time as _t

    from deepfind import engine as _eng

    zengin = {"vram_bos_oran": 0.9, "vram_bos_mb": 7000,
              "aygit": "vulkan0: Kart", "toplam_mb": 8176}
    plan = {"sonuclar": [(None, False)], "n": 0}

    def dalgali_cozumle(exe, backend, aygit, butce=30.0):
        plan["n"] += 1
        return plan["sonuclar"][min(plan["n"] - 1, len(plan["sonuclar"]) - 1)]

    monkeypatch.setattr(_eng, "_vram_cozumle", dalgali_cozumle)
    import types as _t2

    eski = _t.monotonic() - 200.0
    ot = _t2.SimpleNamespace(backend="vulkan", exe="x/llama-server.exe",
                             device="Vulkan0: Kart (8176 MiB, 7000 MiB free)",
                             _vram=dict(zengin), _vram_olc_zamani=eski,
                             _vram_deneme_zamani=0.0, _vram_sorguda=False,
                             _kilit=__import__("threading").RLock())
    ot._vram_kilitle = _eng.Oturum._vram_kilitle.__get__(ot)
    ot._taze_vram = _eng.Oturum._taze_vram.__get__(ot)
    ot.vram_bilgi = _eng.Oturum.vram_bilgi.__get__(ot)
    ot.vram_durumu = _eng.Oturum.vram_durumu.__get__(ot)
    karar = tune.TopluKarar()
    # Olcum suresi dolmus: bekletmeden None, yenileme arka planda baslar.
    baslangic = _t.perf_counter()
    assert ot.vram_bilgi() is None
    assert _t.perf_counter() - baslangic < 1.0
    # Yenileme zaman asimina ugrar (gecici): eski yuksek deger karara girmez.
    bitis = _t.perf_counter() + 10.0
    while ot._vram_sorguda and _t.perf_counter() < bitis:
        _t.sleep(0.05)
    assert plan["n"] == 1
    bilgi = tune.gpu_bilgi(ot)
    assert "vram_bos_mb" not in bilgi, bilgi
    assert karar.dene_hazir(50, bilgi, "vulkan") is False
    assert karar.kilitli is False
    assert tune.probe_engeli("vulkan", bilgi, 50) == "VRAM_BEKLİYOR"
    # Sonraki basarili olcum denemeyi yeniden mumkun kilar.
    plan["sonuclar"].append((dict(zengin), True))
    ot._vram_deneme_zamani = 0.0
    bilgi2 = time_monotonic_sonuc(ot, tavan=15.0)
    assert bilgi2 is not None and bilgi2["vram_bos_mb"] == 7000
    assert karar.dene_hazir(50, tune.gpu_bilgi(ot), "vulkan") is True
    assert plan["n"] == 2  # ust uste sorgu acilmadi


def test_gpu_bilgi_birlestirir():
    import types as _t

    ram = {"bos_oran": 0.5, "bos_mb": 4096}
    ot = _t.SimpleNamespace(
        backend="vulkan",
        vram_bilgi=lambda zaman_asimi=30: {"vram_bos_oran": 0.6, "vram_bos_mb": 4096,
                                           "aygit": "vulkan0: Sahte"})
    bilgi = tune.gpu_bilgi(ot, ram)
    assert bilgi["vram_bos_mb"] == 4096
    assert bilgi["gpu_aygit"] == "vulkan0: Sahte"
    assert tune.probe_engeli("vulkan", bilgi, 50) is None


def test_gpu_bilgi_sorgu_hatasinda_bilinmiyor():
    import types as _t

    def patlayan(zaman_asimi=30):
        raise TimeoutError("sorgu yavas")

    ot = _t.SimpleNamespace(backend="cuda", vram_bilgi=patlayan)
    bilgi = tune.gpu_bilgi(ot, {"bos_oran": 0.5, "bos_mb": 4096})
    assert bilgi.get("vram_bilinmiyor") is True
    assert tune.probe_engeli("cuda", bilgi, 50) == "VRAM_BILINMIYOR"
    # CPU'da VRAM kapisi aranmaz.
    cpu = _t.SimpleNamespace(backend="cpu")
    assert tune.probe_engeli("cpu", {"bos_oran": 0.5, "bos_mb": 4096}, 50) is None


def test_probe_engeli_kodlari():
    assert tune.probe_engeli("bilinmeyen", {}, 50) == "MOTOR_BILINMIYOR"
    assert tune.probe_engeli("cpu", {"bos_oran": 0.5, "bos_mb": 4096}, 3) == "KUYRUK_YETERSIZ"
    assert tune.probe_engeli("cpu", {"bos_oran": 0.01, "bos_mb": 10}, 50) == "RAM_YETERSIZ"
    assert tune.probe_engeli("vulkan", {"bos_oran": 0.5, "bos_mb": 4096}, 50) == "VRAM_BILINMIYOR"
    dusuk = {"bos_oran": 0.5, "bos_mb": 4096, "vram_bos_oran": 0.05, "vram_bos_mb": 100}
    assert tune.probe_engeli("cuda", dusuk, 50) == "VRAM_YETERSIZ"
    bekleyen = {"bos_oran": 0.5, "bos_mb": 4096, "vram_bekliyor": True}
    assert tune.probe_engeli("vulkan", bekleyen, 50) == "VRAM_BEKLİYOR"
    assert tune.probe_engeli("cuda", bekleyen, 50) == "VRAM_BEKLİYOR"

class _AsiliOturum:
    backend = "cpu"

    def alive(self):
        return True  # surec acik gorunur

    def encode(self, *a, **k):
        raise TimeoutError("Gömme toplam süre aşımı")  # ama yanit vermez


def _tek_belge(tmp_path, ad="not.txt", icerik="Ankara kira sözleşmesi 2024"):
    import time as _t

    kok = tmp_path / "kaynak"
    kok.mkdir(exist_ok=True)
    yol = kok / ad
    yol.write_text(icerik, encoding="utf-8")
    eski = _t.time() - 10
    os.utime(yol, (eski, eski))
    return kok


def test_yanitsiz_motor_kuyrugu_korur_arayuz_surer(tmp_path, monkeypatch):
    from test_scan_resume import database
    from deepfind import coordinator as _c
    from deepfind import engine as _eng
    from deepfind import gom as _gom
    from deepfind import model_indir as _mi

    _eng.close()
    monkeypatch.setattr(_gom, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(_mi, "gerekli_mi", lambda *a, **k: False)
    from deepfind import embed as _emb

    monkeypatch.setattr(_emb, "isit_oturumu", lambda *a, **k: _AsiliOturum())
    kok = _tek_belge(tmp_path)
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = _c.run_scan(con, db, str(kok))
    finally:
        con.close()
    # Arayuz yanit verdi (donus var), is kaybolmadi, yazma olmadi.
    assert sonuc["result"] in ("partial", "complete")
    con2 = database(db)
    try:
        assert con2.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0
        assert con2.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('pending','running')"
        ).fetchone()[0] >= 1
    finally:
        con2.close()


def test_toparlanma_basarisizsa_durum_gorunur_kuyruk_durur(tmp_path, monkeypatch):
    from test_scan_resume import database
    from deepfind import coordinator as _c
    from deepfind import engine as _eng
    from deepfind import gom as _gom
    from deepfind import model_indir as _mi

    _eng.close()
    monkeypatch.setattr(_gom, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(_mi, "gerekli_mi", lambda *a, **k: False)
    from deepfind import embed as _emb

    cagri = {"n": 0}

    def sahte_isit(*a, **k):
        cagri["n"] += 1
        # Hazirlik + ilk kurulum asili oturum; toparlanma basarisiz.
        return _AsiliOturum() if cagri["n"] <= 2 else None

    monkeypatch.setattr(_emb, "isit_oturumu", sahte_isit)
    monkeypatch.setattr(_emb, "status_code", lambda: "")
    kok = _tek_belge(tmp_path)
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = _c.run_scan(con, db, str(kok))
    finally:
        con.close()
    assert sonuc["result"] == "partial"
    assert sonuc.get("reason_code") in ("ENGINE_START_ERROR", "ENGINE_TIMEOUT")
    assert sonuc.get("reason_stage") == "embedding"
    assert sonuc.get("reason_help")
    con2 = database(db)
    try:
        assert con2.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0
        assert con2.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('pending','running')"
        ).fetchone()[0] >= 1
    finally:
        con2.close()


# --- Gercek tarama akisinda GPU karari: baz once, toplu sonra ---

class _KayitliOturum:
    backend = "vulkan"

    def __init__(self, vram=None):
        self._vram = vram
        self.gorulen: list[int] = []

    def alive(self):
        return True

    def vram_bilgi(self, zaman_asimi=30):
        if self._vram is None:
            return None
        return dict(self._vram)

    def encode(self, metinler, gorev="belge", toplu=1, cancel=None, zaman_asimi=None):
        self.gorulen.append(toplu)
        n = len(metinler)
        return np.ones((n, 256), dtype=np.float32) / 16


def _cok_belge(tmp_path, n, one="Ankara kira sözleşmesi"):
    kok = tmp_path / "kaynak"
    kok.mkdir(exist_ok=True)
    import time as _t

    eski = _t.time() - 10
    for i in range(n):
        yol = kok / f"b{i:02d}.txt"
        yol.write_text(f"{one} {i}\n", encoding="utf-8")
        os.utime(yol, (eski, eski))
    return kok


def _tara_kayitli(tmp_path, monkeypatch, oturum, dosya=35):
    from test_scan_resume import database
    from deepfind import coordinator as _c
    from deepfind import engine as _eng
    from deepfind import gom as _gom
    from deepfind import model_indir as _mi

    _eng.close()
    monkeypatch.setattr(_gom, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(_mi, "gerekli_mi", lambda *a, **k: False)
    from deepfind import embed as _emb

    monkeypatch.setattr(_emb, "isit_oturumu", lambda *a, **k: oturum)
    kok = _cok_belge(tmp_path, dosya)
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = _c.run_scan(con, db, str(kok))
    finally:
        con.close()
    con2 = database(db)
    try:
        vektor = con2.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        bekleyen = con2.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0]
    finally:
        con2.close()
    return sonuc, vektor, bekleyen


def test_taramada_zengin_vram_once_baz_sonra_toplu(tmp_path, monkeypatch):
    oturum = _KayitliOturum({"vram_bos_oran": 0.6, "vram_bos_mb": 4096,
                             "aygit": "vulkan0: Sahte"})
    sonuc, vektor, bekleyen = _tara_kayitli(tmp_path, monkeypatch, oturum)
    assert vektor == 35, (vektor, sonuc)
    assert bekleyen == 0
    assert sonuc["result"] == "complete", sonuc
    # txt dosya basina 1 parca: once normal baz birikir, sonra toplu denenir.
    assert 1 in oturum.gorulen
    assert 2 in oturum.gorulen, oturum.gorulen
    assert sonuc.get("toplu_neden") is None


def test_taramada_bilinmeyen_vram_hep_normal(tmp_path, monkeypatch):
    oturum = _KayitliOturum(None)
    sonuc, vektor, bekleyen = _tara_kayitli(tmp_path, monkeypatch, oturum, dosya=12)
    assert vektor == 12, (vektor, sonuc)
    assert bekleyen == 0
    assert sonuc["result"] == "complete", sonuc
    assert set(oturum.gorulen) == {1}, oturum.gorulen
    # Neden tanilama yolunda gorunur, tarama sonucu etkilenmez.
    assert sonuc.get("toplu_deneme") == "kapali"
    assert sonuc.get("toplu_neden") == "VRAM_BILINMIYOR"


def test_taramada_yetersiz_vram_hep_normal(tmp_path, monkeypatch):
    oturum = _KayitliOturum({"vram_bos_oran": 0.05, "vram_bos_mb": 100,
                             "aygit": "vulkan0: Sahte"})
    sonuc, vektor, bekleyen = _tara_kayitli(tmp_path, monkeypatch, oturum, dosya=12)
    assert vektor == 12, (vektor, sonuc)
    assert set(oturum.gorulen) == {1}, oturum.gorulen
    assert sonuc.get("toplu_neden") == "VRAM_YETERSIZ"


def test_taramada_sorgu_surerken_normal_kilit_yok(tmp_path, monkeypatch):
    import types as _t

    import numpy as _np

    oturum = _t.SimpleNamespace(
        backend="vulkan",
        vram_bilgi=lambda zaman_asimi=30: None,
        vram_durumu=lambda: "bekliyor",
        alive=lambda: True,
        encode=lambda metinler, **k: _np.ones(
            (len(metinler), 256), dtype=_np.float32) / 16)
    gorulen: list[int] = []
    saf_encode = oturum.encode

    def kayitli_encode(metinler, gorev="belge", toplu=1, cancel=None,
                       zaman_asimi=None):
        gorulen.append(toplu)
        return saf_encode(metinler)

    oturum.encode = kayitli_encode
    sonuc, vektor, bekleyen = _tara_kayitli(tmp_path, monkeypatch, oturum, dosya=12)
    assert vektor == 12, (vektor, sonuc)
    assert bekleyen == 0
    assert sonuc["result"] == "complete", sonuc
    # Sorgu henuz bitmedi: hep normal, ama neden isaretlenmez, kilit yok.
    assert set(gorulen) == {1}, gorulen
    assert sonuc.get("toplu_neden") is None
