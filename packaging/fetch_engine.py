"""Fetch pinned official runtime/model assets; never execute unverified downloads."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'build' / 'embedding'
TAG = 'b11765'
BASE = f'https://github.com/ggml-org/llama.cpp/releases/download/{TAG}/'
RUNTIMES = {
    'cpu': (f'llama-{TAG}-bin-win-cpu-x64.zip', '51188c5e887e49507a4df0baf57b0ac842df3f97e7c92950209e3b0e13b04548'),
    'vulkan': (f'llama-{TAG}-bin-win-vulkan-x64.zip', '950f31438859814166547b7d70feb3fb3a7afeffc413a95487cd80a98dd05b45'),
}
# CUDA 12.4 runtime (NVIDIA Turing ve sonrasi; Blackwell/RTX 50xx bu pinle
# desteklenmez, bk. manifest notu). Kaynak model_indir.CUDA ile ayni pin.
CUDA_ARCHIVES = [
    (f'llama-{TAG}-bin-win-cuda-12.4-x64.zip', '1dd1eddb867a7ab8eca08f972ee3e623fb3d52d298d451aacba3cf0393c5eae'),
    (f'cudart-llama-bin-win-cuda-12.4-x64.zip', '8c79a9b226de4b3cacbf962d0773be79f1e7b75c6af4ded7e32ae1d6'),
]
# Blackwell (RTX 50xx) CUDA 12.4 derlemesinde calismaz; pin bilerek sabit.
CUDA_NOTE = ('CUDA 12.4 derlemesi Turing/Ampere/Ada/Lovelace mimarilerini '
             'destekler. Blackwell (RTX 50xx) icin CUDA 12.8+ gerekir; '
             'mevcut b11765 pini korundu, 5060 destegi dogrulanmadi.')


def download(url, target, sha):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == sha:
        return
    temp = target.with_suffix(target.suffix + '.part')
    with urllib.request.urlopen(url, timeout=90) as response, temp.open('wb') as out:
        while block := response.read(4 * 1024 * 1024):
            out.write(block)
    with temp.open('rb') as source:
        actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != sha:
        temp.unlink()
        raise ValueError(f'Hash mismatch: {target.name}')
    temp.replace(target)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    meta = json.load(urllib.request.urlopen('https://huggingface.co/api/models/ggml-org/embeddinggemma-2-GGUF/revision/58faf90940886df2d62be555c8765d00dac362c5?blobs=true'))
    manifest = {'engine': TAG, 'model_revision': meta['sha'], 'files': {}}
    for precision in ('Q8_0', 'BF16'):
        name = f'embeddinggemma-2-{precision}.gguf'
        info = next(x for x in meta['siblings'] if x['rfilename'] == name)
        sha = info['lfs']['sha256']
        url = f'https://huggingface.co/ggml-org/embeddinggemma-2-GGUF/resolve/{meta["sha"]}/{name}'
        print('fetch', name, flush=True)
        download(url, ASSETS / name, sha)
        manifest['files'][name] = {'url': url, 'sha256': sha, 'size': info['lfs']['size']}
    manifest['extracted'] = {}
    for backend, (name, sha) in RUNTIMES.items():
        print('fetch', name, flush=True)
        archive = ASSETS / name
        download(BASE + name, archive, sha)
        out = ASSETS / backend
        out.mkdir(exist_ok=True)
        manifest['extracted'][backend] = _extract_runtime(archive, out)
        manifest['files'][name] = {'url': BASE + name, 'sha256': sha}
    print('fetch cuda', flush=True)
    cuda_out = ASSETS / 'cuda'
    cuda_out.mkdir(exist_ok=True)
    staged = {}
    for name, sha in CUDA_ARCHIVES:
        print('fetch', name, flush=True)
        archive = ASSETS / name
        download(BASE + name, archive, sha)
        manifest['files'][name] = {'url': BASE + name, 'sha256': sha}
        for leaf, payload in _iter_runtime(archive):
            if leaf in staged and staged[leaf] != payload:
                raise ValueError(f'Çakışan CUDA dosyası: {leaf}')
            staged[leaf] = payload
    if 'llama-server.exe' not in staged:
        raise ValueError('CUDA motoru eksik: llama-server.exe yok')
    manifest['extracted']['cuda'] = _write_staged(staged, cuda_out)
    manifest['cuda_note'] = CUDA_NOTE
def _iter_runtime(archive):
    """Sunucu + gerekli DLL/lisanslar; ilgisiz araclar disarida."""
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            leaf = Path(item.filename).name
            if leaf.startswith('llama-') and leaf.endswith('-impl.dll') and leaf != 'llama-server-impl.dll':
                continue
            if leaf.lower().endswith('.dll') or leaf == 'llama-server.exe' or leaf.startswith('LICENSE'):
                yield leaf, z.read(item)


def _write_staged(staged, out):
    out.mkdir(parents=True, exist_ok=True)
    kayit = {}
    for leaf in sorted(staged):
        target = out / leaf
        if not target.is_file() or target.read_bytes() != staged[leaf]:
            target.write_bytes(staged[leaf])
        kayit[leaf] = {'sha256': hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(),
                       'size': target.stat().st_size}
    return kayit


def _extract_runtime(archive, out):
    return _write_staged(dict(_iter_runtime(archive)), out)


    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for name, url in {
        'llama-LICENSE.txt': f'https://raw.githubusercontent.com/ggml-org/llama.cpp/{TAG}/LICENSE',
        'model-LICENSE.txt': 'https://www.apache.org/licenses/LICENSE-2.0.txt',
    }.items():
        (ASSETS / name).write_bytes(urllib.request.urlopen(url, timeout=30).read())
    print('verified assets ready', flush=True)


if __name__ == '__main__':
    main()
