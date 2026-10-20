"""Model indirici testleri (FAZ 5). Ag yok: file:// kullanilir."""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_indir_dogrular(tmp_path):
    from evrakci import model_indir

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

    from evrakci import model_indir

    kaynak = tmp_path / "kaynak.onnx"
    kaynak.write_bytes(b"bozuk-icerik")
    with pytest.raises(ValueError):
        model_indir.indir(url=kwargs_url(kaynak), oet="0" * 64,
                          yol=str(tmp_path / "m.onnx"))
    assert not os.path.exists(str(tmp_path / "m.onnx"))


def test_gerekli_mi(tmp_path):
    from evrakci import model_indir

    yol = str(tmp_path / "yok.onnx")
    assert model_indir.gerekli_mi(yol) is True


def kwargs_url(p):
    return p.as_uri()
