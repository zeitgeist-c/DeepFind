"""Yerel vektor motoru: EmbeddingGemma-2 metin kulesi (ONNX).

Birincil ORT DirectML (GPU), yedek CPU. Uretimde torch yok.
Vektorler 256d MRL, birim kurede (L2).
"""
from __future__ import annotations

import os

import numpy as np

MODEL_VER = "eg2-text-256-v1"
DIM = 256
SORGU_ONEKI = "task: search result | query: "
BELGE_ONEKI = "title: none | text: "
TOKENIZER_KAYNAGI = "google/embeddinggemma-2"
VARSAYILAN_TOPLU = 16
VARSAYILAN_UZUNLUK = 512


def isle(hiddens: np.ndarray, maske: np.ndarray, kirp: int = DIM) -> np.ndarray:
    """Maskeli mean-pool + ilk `kirp` boyut + L2. Cikti (n, kirp) float32."""
    m = maske.astype(np.float32)[..., None]
    top = (hiddens.astype(np.float32) * m).sum(axis=1)
    payda = np.maximum(m.sum(axis=1), 1e-9)
    v = (top / payda)[:, :kirp]
    norm = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    return (v / norm).astype(np.float32)


def _varsayilan_model_yolu() -> str:
    kok = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(kok, "Evrakçı", "models", "eg2-text.onnx")


class Oturum:
    """Tek ORT oturumu: DML dener, yoksa CPU'ya duser. Thread-safe degil;
    arayuz QThread basina bir Oturum acar."""

    def __init__(self, model_yolu: str | None = None,
                 tokenizer_kaynagi: str = TOKENIZER_KAYNAGI):
        import onnxruntime as ort

        self.saglayicilar = ["DmlExecutionProvider", "CPUExecutionProvider"]
        try:
            self.ot = ort.InferenceSession(model_yolu or _varsayilan_model_yolu(),
                                           providers=self.saglayicilar)
        except Exception:
            self.ot = ort.InferenceSession(model_yolu or _varsayilan_model_yolu(),
                                           providers=["CPUExecutionProvider"])
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(tokenizer_kaynagi)
        self.girdiler = [i.name for i in self.ot.get_inputs()]

    @property
    def gpu_mu(self) -> bool:
        return self.ot.get_providers()[0] == "DmlExecutionProvider"

    def encode(self, metinler: list[str], gorev: str = "sorgu",
               toplu: int = VARSAYILAN_TOPLU) -> np.ndarray:
        """gorev: 'sorgu' | 'belge'. Donus (n, 256) float32."""
        onek = SORGU_ONEKI if gorev == "sorgu" else BELGE_ONEKI
        parcalar = []
        for i in range(0, len(metinler), toplu):
            grup = [onek + (t or "") for t in metinler[i:i + toplu]]
            kod = self.tok(grup, padding=True, truncation=True,
                           max_length=VARSAYILAN_UZUNLUK, return_tensors="np")
            besle = {"input_ids": kod["input_ids"].astype(np.int64),
                     "attention_mask": kod["attention_mask"].astype(np.int64)}
            h = self.ot.run(None, {k: besle[k] for k in self.girdiler})[0]
            parcalar.append(isle(h, kod["attention_mask"], DIM))
        return np.concatenate(parcalar, axis=0).astype(np.float32)
