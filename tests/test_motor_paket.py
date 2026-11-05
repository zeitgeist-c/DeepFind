"""Motor paketi testleri: uc motor + paylasilan model + manifest kayitlari."""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import engine  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
VARLIK = KOK / "build" / "embedding"


def _sha(p):
    return hashlib.file_digest(p.open("rb"), "sha256").hexdigest()


def test_manifest_kayitlari_tam():
    man = json.loads((VARLIK / "manifest.json").read_text(encoding="utf-8"))
    assert man["engine"] == "b11765"
    assert man["files"]["embeddinggemma-2-Q8_0.gguf"]["sha256"] == \
        "2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135"
    for name in ("llama-b11765-bin-win-cuda-12.4-x64.zip",
                 "cudart-llama-bin-win-cuda-12.4-x64.zip"):
        assert man["files"][name]["sha256"], name
        assert (VARLIK / name).is_file(), name
    for backend in ("cpu", "vulkan", "cuda"):
        assert "llama-server.exe" in man["extracted"][backend], backend
        assert (VARLIK / backend / "llama-server.exe").is_file(), backend
    assert "llama-server.exe" in man["extracted"]["cuda"]
    assert "Blackwell" in man.get("cuda_note", "") or "5060" in man.get("cuda_note", "")


def test_uc_motor_diskte(monkeypatch):
    monkeypatch.setattr(engine, "asset_root", lambda: VARLIK)
    sec = {r["key"]: r for r in engine.motor_secenekleri()}
    assert set(sec) == {"auto", "cpu", "vulkan", "cuda"}
    for anahtar in ("cpu", "vulkan", "cuda"):
        assert sec[anahtar]["installed"] is True, anahtar
        assert sec[anahtar]["size_mb"] > 0, anahtar


def test_cuda_paket_oncelikli_kullanici_yedekli(tmp_path, monkeypatch):
    paketlenmis = tmp_path / "emb"
    (paketlenmis / "cuda").mkdir(parents=True)
    monkeypatch.setattr(engine, "asset_root", lambda: paketlenmis)
    monkeypatch.setattr(engine.paths, "engines_dir", lambda *_a: tmp_path / "kullanici")
    assert engine.cuda_root() == tmp_path / "kullanici"
    (paketlenmis / "cuda" / "llama-server.exe").write_bytes(b"x")
    assert engine.cuda_root() == paketlenmis / "cuda"


def test_paylasilan_dll_byte_identical():
    # Yanlis paylasim sessiz karisim uretir; bayt-esitlik sart.
    ortak = {"ggml-base.dll", "ggml.dll", "libomp.dll", "llama-common.dll",
             "llama-server-impl.dll", "llama.dll", "mtmd.dll",
             "llama-server.exe", "LICENSE-LLVM-OpenMP"}
    dizinler = {ad: VARLIK / ad for ad in ("cpu", "vulkan", "cuda", "common")
                if (VARLIK / ad).is_dir()}
    assert "cuda" in dizinler and "common" in dizinler
    for ad in sorted(ortak):
        huiler = {}
        for motor, dizin in dizinler.items():
            hedef = dizin / ad
            if hedef.is_file():
                huiler[motor] = _sha(hedef)
        assert len(set(huiler.values())) <= 1, (ad, huiler)
