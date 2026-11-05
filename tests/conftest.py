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
    # Makinedeki gercek model (kabulde indirilen kullanici modeli dahil)
    # birim testleri etkilemez: gom atlama karari ve guncelleme cozumu
    # yalitilmis gecici dizinlere bakar.
    (tmp_path / 'yerel').mkdir(exist_ok=True)
    (tmp_path / 'ortak').mkdir(exist_ok=True)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'yerel'))
    monkeypatch.setenv('PROGRAMDATA', str(tmp_path / 'ortak'))


@pytest.fixture(autouse=True)
def turkce_arayuz():
    """Birim testleri Turkce UI metinlerini dogrular; dili sabitle."""
    from deepfind import theme
    theme.set_language("tr")
