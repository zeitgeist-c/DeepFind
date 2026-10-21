"""Optional pinned NVIDIA CUDA runtime; model itself is bundled offline."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile
from .engine import cuda_root, _varsayilan_model_yolu

MODEL_SURUM = 'eg2-q8-256-v2'
MODEL_DOSYA = 'embeddinggemma-2-Q8_0.gguf'
MODEL_SHA256 = '2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135'
MODEL_BOYUT = 309855456
BASE = 'https://github.com/ggml-org/llama.cpp/releases/download/b11765/'
CUDA = [
 ('llama-b11765-bin-win-cuda-12.4-x64.zip','1dd1eddb867a7ab8eca08f972ee3e623fb32d298d4511aacba3cf0f0393c5eae'),
 ('cudart-llama-bin-win-cuda-12.4-x64.zip','8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6'),
]


def hedef_yol(kok=None):
    return str(Path(kok) / MODEL_DOSYA) if kok else _varsayilan_model_yolu()


def _sha256_yoksa(path):
    if not Path(path).is_file(): return None
    with open(path,'rb') as source:
        return hashlib.file_digest(source,'sha256').hexdigest()


def gerekli_mi(yol=None):
    return _sha256_yoksa(yol or hedef_yol()) != MODEL_SHA256


def paylasilan_hazir():
    from .engine import shared_model_path
    return not gerekli_mi(str(shared_model_path()))


def indir(url, oet, yol, ilerleme=None, cancel=None):
    target = Path(yol)
    target.parent.mkdir(parents=True,exist_ok=True)
    partial = target.with_suffix(target.suffix+'.part')
    try:
        with urllib.request.urlopen(url,timeout=30) as response, partial.open('wb') as out:
            total = int(response.headers.get('Content-Length',0))
            done = 0
            while True:
                if cancel and cancel(): raise InterruptedError('İndirme iptal edildi')
                block = response.read(1024*1024)
                if not block: break
                out.write(block); done += len(block)
                if ilerleme: ilerleme(done,total)
        if not oet or _sha256_yoksa(partial) != oet:
            raise ValueError('model dosyasi dogrulamasi basarisiz')
        partial.replace(target)
        return str(target)
    finally:
        partial.unlink(missing_ok=True)


def install_cuda(cancel=None, destination=None):
    target = Path(destination) if destination else cuda_root()
    target.parent.mkdir(parents=True,exist_ok=True)
    ready = target / 'verified.json'
    if ready.is_file():
        hashes = json.loads(ready.read_text(encoding='utf-8'))
        if hashes and all(_sha256_yoksa(target/name)==sha for name,sha in hashes.items()): return target
    with tempfile.TemporaryDirectory(prefix='cuda-',dir=target.parent) as temp:
        stage = Path(temp)/'runtime'; stage.mkdir()
        for name,sha in CUDA:
            archive = Path(temp)/name
            indir(BASE+name,sha,str(archive),cancel=cancel)
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    leaf = Path(item.filename).name
                    if leaf.startswith('llama-') and leaf.endswith('-impl.dll') and leaf!='llama-server-impl.dll': continue
                    if leaf.lower().endswith('.dll') or leaf=='llama-server.exe' or any(t in leaf.lower() for t in ('license','notice','copying')):
                        payload = z.read(item)
                        dest = stage/leaf
                        if dest.exists() and dest.read_bytes()!=payload:
                            raise ValueError('Çakışan CUDA dosyası')
                        dest.write_bytes(payload)
        if not (stage/'llama-server.exe').is_file(): raise ValueError('CUDA motoru eksik')
        hashes = {p.name:_sha256_yoksa(p) for p in stage.iterdir()}
        (stage/'verified.json').write_text(json.dumps(hashes),encoding='utf-8')
        previous = Path(temp)/'previous'
        if target.exists(): target.rename(previous)
        try: stage.rename(target)
        except Exception:
            if previous.exists(): previous.rename(target)
            raise
    return target
