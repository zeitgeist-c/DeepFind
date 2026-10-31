"""Public embedding API; llama.cpp runtime, offline GGUF model.

Names like `embed.MODEL_VER`, `embed.close()`, `embed.isit_oturumu()` are used
from this module; re-export from engine is deliberate (ruff F401
is a false positive here). Never deleted, flagged with `noqa`."""
import numpy as np
from .engine import (MODEL_VER, DIM, SORGU_ONEKI, BELGE_ONEKI,  # noqa: F401
    VARSAYILAN_TOPLU, VARSAYILAN_UZUNLUK, Oturum,  # noqa: F401
    hazir_oturum, isit_oturumu, status, set_backend, close,  # noqa: F401
    _varsayilan_model_yolu)  # noqa: F401

def isle(hiddens: np.ndarray, maske: np.ndarray, kirp: int = DIM) -> np.ndarray:
    """Maskeli mean-pool + ilk `kirp` boyut + L2. Cikti (n, kirp) float32."""
    m = maske.astype(np.float32)[..., None]
    top = (hiddens.astype(np.float32) * m).sum(axis=1)
    payda = np.maximum(m.sum(axis=1), 1e-9)
    v = (top / payda)[:, :kirp]
    norm = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    return (v / norm).astype(np.float32)
