"""EmbeddingGemma-2 metin kulesi -> ONNX disari aktarim (tek seferlik, gelistirici).

Girdi: HF `google/embeddinggemma-2` (hizli: onbellekteki agirliklar kullanilir).
Cikti: `eg2-text.onnx` (opset 18, dinamik batch/seq).
Dogrulama: ORT-CPU ciktisi torch referansla kosinus >= 0.999 olmali.

Gerektirir (yalniz bu betik icin): torch, transformers, onnx. Uretim
paketi bunlari icermez; uretimde yalniz onnxruntime-directml + model vardir.
Kullanim: bench venv'inde `python eval/export_eg2_onnx.py [cikti.onnx]`
"""
from __future__ import annotations

import sys

MODEL_ID = "google/embeddinggemma-2"
SEQ = 128
ESIK = 0.999


def main(cikti: str = "eg2-text.onnx") -> None:
    import numpy as np
    import torch
    from transformers import AutoConfig, AutoModel, AutoTokenizer

    print("yukleniyor:", MODEL_ID, flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    cfg = AutoConfig.from_pretrained(MODEL_ID, vision_config=None,
                                     audio_config=None, trust_remote_code=True)
    model = AutoModel.from_pretrained(MODEL_ID, config=cfg, dtype=torch.float32,
                                      trust_remote_code=True).eval()
    ornek = ["elektrik faturasi tutar 1.250 TL", "kira sozlesmesi aylik 40.000 TL"]
    kod = tok(ornek, padding="max_length", max_length=SEQ, truncation=True,
              return_tensors="pt")
    ids, mask = kod["input_ids"], kod["attention_mask"]
    with torch.no_grad():
        ref = model(input_ids=ids, attention_mask=mask).last_hidden_state

    class TextOnly(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask):
            return self.m(input_ids=input_ids,
                          attention_mask=attention_mask).last_hidden_state

    print("aktariliyor ->", cikti, flush=True)
    torch.onnx.export(TextOnly(model), (ids, mask), cikti,
                      input_names=["input_ids", "attention_mask"],
                      output_names=["hidden"],
                      dynamic_axes={"input_ids": {0: "batch", 1: "seq"},
                                    "attention_mask": {0: "batch", 1: "seq"},
                                    "hidden": {0: "batch", 1: "seq"}},
                      dynamo=False, opset_version=18)

    import onnxruntime as ort

    sess = ort.InferenceSession(cikti, providers=["CPUExecutionProvider"])
    h = sess.run(None, {"input_ids": ids.numpy().astype(np.int64),
                        "attention_mask": mask.numpy().astype(np.int64)})[0]
    a = ref.numpy().reshape(-1)
    b = h.reshape(-1)
    benzer = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
    print("kosinus:", round(benzer, 6), flush=True)
    if benzer < ESIK:
        raise SystemExit(f"dogrulama basarisiz: {benzer} < {ESIK}")
    print("TAMAM:", cikti)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eg2-text.onnx")
