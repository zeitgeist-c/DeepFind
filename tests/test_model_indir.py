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

    from deepfind.engine import shared_model_path
    hedef = model_indir.hedef_yol()
    assert os.path.abspath(hedef) == str(shared_model_path())
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
