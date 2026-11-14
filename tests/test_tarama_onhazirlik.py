"""Model/motor ön denetimi ve kısmi tarama regresyonları (0.10.12 madde 2-3).

Gerçek kullanıcı kasasına dokunmaz: her test kendi tmp dizininde sentetik
kasa + tek belgeden tarar. Vektörler yalnızca fake oturumla yazılır.
"""
import os
import time

from deepfind import coordinator as C
from deepfind import engine
from deepfind import gom as gom_mod
from deepfind import model_indir as mi
from test_scan_resume import database


def _tek_belge(tmp_path, ad="not.txt", icerik="Ankara kira sözleşmesi 2024"):
    kok = tmp_path / "kaynak"
    kok.mkdir(exist_ok=True)
    yol = kok / ad
    yol.write_text(icerik, encoding="utf-8")
    eski = time.time() - 10
    os.utime(yol, (eski, eski))
    return kok


def _tara(tmp_path, kok, **kw):
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = C.run_scan(con, db, str(kok), **kw)
        segmentler = con.execute("SELECT count(*) FROM segments").fetchone()[0]
        vektorler = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        kilit = os.path.join(os.path.dirname(os.path.abspath(db)), "scan.lock")
        return sonuc, segmentler, vektorler, os.path.isfile(kilit), con
    finally:
        con.close()


def test_eksik_modelde_sahte_vektor_yok_ve_partial(tmp_path):
    kok = _tek_belge(tmp_path)
    sonuc, segmentler, vektorler, kilit_duruyor, _ = _tara(tmp_path, kok)
    assert segmentler > 0  # metin çıkarıldı
    assert vektorler == 0  # sahte vektör yazılmadı
    assert (sonuc["documents_done"], sonuc["documents_total"]) == (0, 1)
    assert sonuc["result"] == "partial" and sonuc["complete"] is False
    assert sonuc["reason_code"] == "MODEL_MISSING"
    assert sonuc["reason_help"]  # kullanıcı ne yapacağını görür
    assert kilit_duruyor  # scan.lock silinmez


def test_bozuk_modelde_butunluk_kodu(tmp_path):
    engine.close()
    hedef = engine.user_model_path()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(b"bozuk-model-icerigi")
    kok = _tek_belge(tmp_path)
    sonuc, segmentler, vektorler, _, _ = _tara(tmp_path, kok)
    assert segmentler > 0 and vektorler == 0
    assert sonuc["result"] == "partial"
    assert sonuc["reason_code"] == "MODEL_CORRUPT"


def test_motor_hatasi_ayirt_edilir(tmp_path, monkeypatch):
    engine.close()
    monkeypatch.setattr(gom_mod, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: False)
    kok = _tek_belge(tmp_path)
    sonuc, _, vektorler, _, _ = _tara(tmp_path, kok)
    assert vektorler == 0
    assert sonuc["reason_code"] == "ENGINE_START_ERROR"
    assert sonuc["result"] == "partial"


def test_iptalde_hazirlik_kodu_cancelled(tmp_path):
    kok = _tek_belge(tmp_path)
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = C.run_scan(con, db, str(kok), stop=lambda: True)
    finally:
        con.close()
    assert sonuc["result"] == "cancelled"
    assert sonuc["reason_code"] == "CANCELLED"


def test_hazir_motorla_tarama_tamamlanir(tmp_path, monkeypatch):
    from semantic_helpers import FixedSession
    engine.close()
    monkeypatch.setattr(gom_mod, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: False)
    from deepfind import embed
    monkeypatch.setattr(embed, "isit_oturumu", lambda *a, **k: FixedSession())
    kok = _tek_belge(tmp_path)
    sonuc, segmentler, vektorler, _, _ = _tara(tmp_path, kok)
    assert segmentler > 0 and vektorler > 0
    assert sonuc["result"] == "complete" and sonuc["complete"] is True
    assert sonuc["reason_code"] is None


def test_indirme_isci_iptal_sonrasi_yeniden_baslayabilir():
    from deepfind.model_ui import _IndirmeIsci
    isci = _IndirmeIsci()
    assert not isci._dur.is_set()
    isci.iptal()
    assert isci._dur.is_set()
    isci._dur.clear()  # yeniden dene akışı
    assert not isci._dur.is_set()


def _sahte_indirme_duzenegi(monkeypatch, kilitli=False):
    """İptale duyarlı sahte model indirir; gerçek düğme akışını sürer.

    kilitli: işçi serbest bırakılana dek bitmez; çarpı testinde erken
    yok-etmeme oracledır.
    """
    import threading
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    uygulama = QApplication.instance() or QApplication([])
    from deepfind import model_indir as mi
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: True)
    blok = threading.Event()
    cagrilar = []

    def sahte_indir(url, oet, yol, ilerleme=None, cancel=None, deneme=3):
        cagrilar.append("indir")
        if kilitli:
            while not blok.wait(0.05):
                pass
        else:
            for _ in range(200):
                if cancel and cancel():
                    raise InterruptedError("İndirme iptal edildi")
                if blok.wait(0.05):
                    break
        if cancel and cancel():
            raise InterruptedError("İndirme iptal edildi")
        return yol

    monkeypatch.setattr(mi, "indir", sahte_indir)
    return uygulama, blok, cagrilar


def _dugme(uygulama, metin):
    from PySide6.QtWidgets import QPushButton
    dlg = uygulama.activeModalWidget()
    assert dlg is not None
    for dugme in dlg.findChildren(QPushButton):
        if dugme.text().replace("&", "") == metin:
            return dugme
    raise AssertionError("düğme yok: " + metin)


def test_indirme_dugme_akisinda_iptal_yeniden_dene_kapat(monkeypatch):
    import threading
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QCheckBox
    uygulama, blok, cagrilar = _sahte_indirme_duzenegi(monkeypatch)
    hatalar = []

    def sar(fonk):
        def ic():
            try:
                fonk()
            except Exception as exc:
                hatalar.append(exc)
        return ic

    def t0():
        uygulama.activeModalWidget().findChildren(QCheckBox)[0].setChecked(True)
        _dugme(uygulama, "İndirmeyi başlat").click()

    def t1():
        _dugme(uygulama, "İptal").click()

    def t2():
        yinele = _dugme(uygulama, "Yeniden dene")
        assert yinele.isVisible()
        yinele.click()
        assert _dugme(uygulama, "İptal").isVisible()  # yinele İptal'i geri getirir

    def t3():
        _dugme(uygulama, "Kapat").click()  # işçi çalışırken güvenli kapanış

    QTimer.singleShot(200, sar(t0))
    QTimer.singleShot(700, sar(t1))
    QTimer.singleShot(1300, sar(t2))
    QTimer.singleShot(1900, sar(t3))
    QTimer.singleShot(2500, blok.set)
    QTimer.singleShot(20000, sar(lambda: (_ for _ in ()).throw(AssertionError("pencere kapanmadı"))))
    from deepfind import model_ui
    model_ui.indir_penceresi(None)
    if hatalar:
        raise hatalar[0]
    assert cagrilar.count("indir") >= 2  # ilk deneme + yeniden dene
    assert uygulama.activeModalWidget() is None


def test_carpi_isci_durunca_kapatir(monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QCheckBox
    uygulama, blok, _ = _sahte_indirme_duzenegi(monkeypatch, kilitli=True)
    hatalar = []

    def sar(fonk):
        def ic():
            try:
                fonk()
            except Exception as exc:
                hatalar.append(exc)
        return ic

    def t0():
        uygulama.activeModalWidget().findChildren(QCheckBox)[0].setChecked(True)
        _dugme(uygulama, "İndirmeyi başlat").click()

    def t1():
        uygulama.activeModalWidget().close()  # çarpı: işçi durmadan yok edilmez

    def t2():
        assert uygulama.activeModalWidget() is not None  # bloke işçi varken açık

    def t3():
        blok.set()  # işçi iptali görür, pencere kendiliğinden kapanır

    QTimer.singleShot(200, sar(t0))
    QTimer.singleShot(600, sar(t1))
    QTimer.singleShot(1000, sar(t2))
    QTimer.singleShot(1400, sar(t3))
    QTimer.singleShot(20000, sar(lambda: (_ for _ in ()).throw(AssertionError("pencere kapanmadı"))))
    from deepfind import model_ui
    model_ui.indir_penceresi(None)
    if hatalar:
        raise hatalar[0]
    assert uygulama.activeModalWidget() is None


def test_ikinci_tarama_kilitliyse_ilk_kayit_acik_kalir(tmp_path):
    import pytest
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        kok = tmp_path / "kaynak"
        kok.mkdir()
        rid = con.execute(
            "INSERT INTO scan_runs(root, started_at) VALUES (?, ?)",
            (str(kok), int(time.time()))).lastrowid
        con.commit()
        from deepfind import coordinator as C
        with C.ScanLock(db):
            with pytest.raises(C.AlreadyRunning):
                C.run_scan(con, db, str(kok))
            satir = con.execute(
                "SELECT finished_at, result FROM scan_runs WHERE run_id=?", (rid,)).fetchone()
            assert satir == (None, None)  # ilk kayıt açık, el değmedi
            kilit = os.path.join(os.path.dirname(os.path.abspath(db)), "scan.lock")
            assert os.path.isfile(kilit)
    finally:
        con.close()


def test_hash_hatasi_kapanista_korunur(tmp_path, monkeypatch):
    kok = _tek_belge(tmp_path)
    from deepfind import dup
    monkeypatch.setattr(dup, "verify_pending", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sentetik-hash")))
    db = str(tmp_path / "kasa.db")
    con = database(db)
    try:
        sonuc = C.run_scan(con, db, str(kok), require_vectors=False)
        satir = con.execute(
            "SELECT result, error_code, finished_at FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        segmentler = con.execute("SELECT count(*) FROM segments").fetchone()[0]
    finally:
        con.close()
    assert segmentler > 0
    assert sonuc["result"] == "partial"
    assert satir[0] == "partial" and satir[1] == "HASH_ERROR" and satir[2] is not None


def test_motor_zaman_asimi_ust_katmanda_kodlanir(tmp_path, monkeypatch):
    from deepfind import embed
    monkeypatch.setattr(gom_mod, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: False)
    monkeypatch.setattr(embed, "isit_oturumu", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("Model yükleme zaman aşımı")))
    kok = _tek_belge(tmp_path)
    sonuc, _, vektorler, _, _ = _tara(tmp_path, kok)
    assert vektorler == 0
    assert sonuc["reason_code"] == "ENGINE_TIMEOUT"
    assert sonuc["result"] == "partial"


def test_motor_zaman_asimi_engine_yutmaz(tmp_path, monkeypatch):
    import pytest
    from deepfind import engine
    engine.close()
    kok = tmp_path / "motorlar"
    (kok / "cpu").mkdir(parents=True)
    (kok / "cpu" / "llama-server.exe").write_bytes(b"sentetik")
    monkeypatch.setattr(engine, "asset_root", lambda: kok)
    monkeypatch.setattr(engine, "_BACKEND", "auto")

    def yavas_start(self, exe, backend, zaman_asimi=90):
        raise TimeoutError("Model yükleme zaman aşımı")

    monkeypatch.setattr(engine.Oturum, "_start", yavas_start)
    yol = tmp_path / "model.gguf"
    yol.write_bytes(b"sentetik")
    # Oturum birleşik RuntimeError yükseltir; bilgi metinde taşınır.
    with pytest.raises(RuntimeError, match="zaman aşımı"):
        engine.Oturum(str(yol), backend="cpu")
    # Üst katman metinden ENGINE_TIMEOUT üretir, yutmaz.
    assert engine.isit_oturumu(yol=str(yol)) is None
    assert engine.status_code() == "ENGINE_TIMEOUT"


def test_motor_seciminde_zaman_asimi_yoksa_runtime_hata(tmp_path, monkeypatch):
    import pytest
    from deepfind import engine
    engine.close()
    kok = tmp_path / "motorlar"
    (kok / "cpu").mkdir(parents=True)
    (kok / "cpu" / "llama-server.exe").write_bytes(b"sentetik")
    monkeypatch.setattr(engine, "asset_root", lambda: kok)

    def bozuk_start(self, exe, backend, zaman_asimi=90):
        raise RuntimeError("Model süreci açılamadı")

    monkeypatch.setattr(engine.Oturum, "_start", bozuk_start)
    yol = tmp_path / "model.gguf"
    yol.write_bytes(b"sentetik")
    with pytest.raises(RuntimeError):
        engine.Oturum(str(yol), backend="cpu")


def test_gercek_oturum_zaman_asimi_taramada_engine_timeout(tmp_path, monkeypatch):
    from deepfind import embed, engine
    engine.close()
    kok = tmp_path / "motorlar"
    (kok / "cpu").mkdir(parents=True)
    (kok / "cpu" / "llama-server.exe").write_bytes(b"sentetik")
    monkeypatch.setattr(engine, "asset_root", lambda: kok)
    monkeypatch.setattr(engine, "_BACKEND", "auto")
    hedef = engine.user_model_path()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(b"sentetik-model")

    def yavas_start(self, exe, backend, zaman_asimi=90):
        raise TimeoutError("Model yükleme zaman aşımı")

    monkeypatch.setattr(engine.Oturum, "_start", yavas_start)
    monkeypatch.setattr(gom_mod, "model_var_mi", lambda *a, **k: True)
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: False)
    monkeypatch.setattr(embed, "isit_oturumu", engine.isit_oturumu)
    kaynak = _tek_belge(tmp_path)
    sonuc, _, vektorler, _, _ = _tara(tmp_path, kaynak)
    assert vektorler == 0
    assert sonuc["reason_code"] == "ENGINE_TIMEOUT"
    assert sonuc["result"] == "partial"


def test_successful_download_continues_scan_without_closing_manually(monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QCheckBox
    from deepfind import model_indir, model_ui

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(model_indir, 'gerekli_mi', lambda: True)
    monkeypatch.setattr(model_indir, 'indir', lambda *a, **kw: 'dogrulanmis.gguf')

    def start():
        app.activeModalWidget().findChild(QCheckBox).setChecked(True)
        _dugme(app, 'İndirmeyi başlat').click()

    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(lambda: app.activeModalWidget().close())
    timeout.start(5000)
    QTimer.singleShot(100, start)
    try:
        assert model_ui.indir_penceresi(None, tarama=True)
    finally:
        timeout.stop()


def test_indir_penceresi_acilir(monkeypatch):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    uygulama = QApplication.instance() or QApplication([])
    from deepfind import model_ui
    monkeypatch.setattr(mi, "gerekli_mi", lambda *a, **k: True)
    QTimer.singleShot(500, lambda: (uygulama.activeModalWidget().reject()
                                    if uygulama.activeModalWidget() else None))
    model_ui.indir_penceresi(None)  # QThread ImportError verirse burada patlar
