"""Model indirici testleri (FAZ 5). Ag yok: file:// kullanilir."""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_indir_dogrular(tmp_path):
    from deepfind import model_indir

    kaynak = tmp_path / "kaynak.onnx"
    kaynak.write_bytes(b"sahte-model-icerigi" * 100)
    oet = hashlib.sha256(kaynak.read_bytes()).hexdigest()
    hedef = str(tmp_path / "model" / "eg2-text.onnx")
    kayit = []
    sonuc = model_indir.indir(url=kwargs_url(kaynak), oet=oet, yol=hedef,
                              ilerleme=lambda o, t: kayit.append((o, t)))
    assert sonuc == hedef
    assert open(hedef, "rb").read() == kaynak.read_bytes()
    assert kayit, "ilerleme cagrilmali"
    assert not os.path.exists(hedef + ".indir")


def test_bozuk_oet_reddedilir(tmp_path):
    import pytest

    from deepfind import model_indir

    kaynak = tmp_path / "kaynak.onnx"
    kaynak.write_bytes(b"bozuk-icerik")
    with pytest.raises(ValueError):
        model_indir.indir(url=kwargs_url(kaynak), oet="0" * 64,
                          yol=str(tmp_path / "m.onnx"))
    assert not os.path.exists(str(tmp_path / "m.onnx"))


def test_gerekli_mi(tmp_path):
    from deepfind import model_indir

    yol = str(tmp_path / "yok.onnx")
    assert model_indir.gerekli_mi(yol) is True


def test_varsayilan_hedef_yonetilen_alan(tmp_path):
    import os

    from deepfind import model_indir

    from deepfind.engine import user_model_path
    hedef = model_indir.hedef_yol()
    assert os.path.abspath(hedef) == str(user_model_path())
    kaynak = str(tmp_path / "arsiv")
    assert not os.path.abspath(hedef).startswith(os.path.abspath(kaynak))


def kwargs_url(p):
    return p.as_uri()


def test_small_update_accepts_installed_or_legacy_model(tmp_path, monkeypatch):
    from deepfind import model_indir, engine
    assets = tmp_path / '_internal' / 'embedding'
    assets.mkdir(parents=True)
    (tmp_path / 'unins000.exe').write_bytes(b'test')
    monkeypatch.setattr(engine, 'asset_root', lambda: assets)
    checked = []
    def required(path=None):
        checked.append(path)
        return path != str(assets / model_indir.MODEL_DOSYA)
    monkeypatch.setattr(model_indir, 'gerekli_mi', required)
    assert model_indir.paylasilan_hazir()
    assert checked == [str(assets / model_indir.MODEL_DOSYA)]
    monkeypatch.setattr(model_indir, 'gerekli_mi', lambda path=None: path == str(assets / model_indir.MODEL_DOSYA))
    assert model_indir.paylasilan_hazir()
    monkeypatch.setattr(model_indir, 'gerekli_mi', lambda path=None: True)
    assert not model_indir.paylasilan_hazir()


def test_portable_model_cannot_select_small_installer(tmp_path, monkeypatch):
    from deepfind import model_indir, engine
    assets = tmp_path / '_internal' / 'embedding'
    monkeypatch.setattr(engine, 'asset_root', lambda: assets)
    monkeypatch.setattr(model_indir, 'gerekli_mi', lambda path=None: path != str(assets / model_indir.MODEL_DOSYA))
    assert not model_indir.paylasilan_hazir()


def test_runtime_prefers_model_beside_installed_exe(tmp_path, monkeypatch):
    from deepfind import engine
    assets = tmp_path / 'Program Files' / 'DeepFind' / '_internal' / 'embedding'
    assets.mkdir(parents=True)
    model = assets / engine.MODEL_DOSYA
    model.write_bytes(b'test')
    monkeypatch.setattr(engine, 'asset_root', lambda: assets)
    assert engine._varsayilan_model_yolu() == str(model)


ICERIK = bytes((i * 7919) % 256 for i in range(300_000))


class _Menzil(__import__("http.server", fromlist=["BaseHTTPRequestHandler"]).BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        aralik = self.headers.get("Range")
        bas, son = 0, len(ICERIK) - 1
        kod = 200
        if aralik and aralik.startswith("bytes="):
            try:
                bas = int(aralik.split("=")[1].split("-")[0])
                kod = 206
            except ValueError:
                bas = 0
        parca = ICERIK[bas:]
        self.send_response(kod)
        self.send_header("Content-Type", "application/octet-stream")
        if kod == 206:
            self.send_header("Content-Range", f"bytes {bas}-{son}/{len(ICERIK)}")
        self.send_header("Content-Length", str(len(parca)))
        self.end_headers()
        self.wfile.write(parca)


def _sunucu():
    import threading
    from http.server import HTTPServer
    srv = HTTPServer(("127.0.0.1", 0), _Menzil)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_ozet_dogruysa_ag_kullanilmaz(tmp_path, monkeypatch):
    from deepfind import model_indir
    hedef = tmp_path / "model.gguf"
    hedef.write_bytes(b"hazir-model")
    oet = hashlib.sha256(b"hazir-model").hexdigest()
    def yasak(*a, **k):
        raise AssertionError("ag kullanilmamali")
    monkeypatch.setattr(model_indir.urllib.request, "urlopen", yasak)
    assert model_indir.indir("http://yok/", oet, str(hedef)) == str(hedef)


def test_yarim_dosya_devam_eder(tmp_path):
    from deepfind import model_indir
    srv = _sunucu()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/model.gguf"
        hedef = tmp_path / "model.gguf"
        yarim = hedef.with_suffix(".gguf.part")
        yarim.write_bytes(ICERIK[:100_000])
        ilerlemeler = []
        yol = model_indir.indir(url, hashlib.sha256(ICERIK).hexdigest(), str(hedef),
                                ilerleme=lambda d, t: ilerlemeler.append((d, t)))
        assert open(yol, "rb").read() == ICERIK
        assert not yarim.exists()
        assert ilerlemeler and ilerlemeler[-1][0] == len(ICERIK)
    finally:
        srv.shutdown()


def test_bozuk_indirme_hedefi_degistirmez(tmp_path):
    from deepfind import model_indir
    srv = _sunucu()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/model.gguf"
        hedef = tmp_path / "model.gguf"
        with __import__("pytest").raises(ValueError):
            model_indir.indir(url, "0" * 64, str(hedef))
        assert not hedef.exists()
        assert not hedef.with_suffix(".gguf.part").exists()
    finally:
        srv.shutdown()


def test_iptal_hedef_olusturmaz(tmp_path):
    from deepfind import model_indir
    srv = _sunucu()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/model.gguf"
        hedef = tmp_path / "model.gguf"
        with __import__("pytest").raises(InterruptedError):
            model_indir.indir(url, hashlib.sha256(ICERIK).hexdigest(), str(hedef),
                              cancel=lambda: True)
        assert not hedef.exists()
    finally:
        srv.shutdown()


def test_kullanici_alani_admin_gerektirmez(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from deepfind import model_indir
    from deepfind.engine import user_model_path
    assert "Program Files" not in str(user_model_path())
    assert str(tmp_path) in model_indir.hedef_yol()
