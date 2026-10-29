"""Unit/UI fixtures must not load a real 310 MB model on every window creation.

Real offline CPU/Vulkan/quantization coverage is eval/embedding_acceptance.py;
the packaged smoke test also encodes and searches actual synthetic documents.
"""
import pytest


@pytest.fixture(autouse=True)
def isolated_model_assets(tmp_path, monkeypatch):
    from deepfind import engine, embed
    monkeypatch.setattr(engine, 'asset_root', lambda: tmp_path / 'absent-model-assets')
    monkeypatch.setattr(embed, 'isit_oturumu', lambda *a, **k: None)
    monkeypatch.setattr(embed, 'hazir_oturum', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def turkce_arayuz():
    """Birim testleri Turkce UI metinlerini dogrular; dili sabitle."""
    from deepfind import theme
    theme.set_language("tr")
