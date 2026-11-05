"""Pinned embedding model: ayri indirme, devamli, dogrulamali.

Motorlar kurulum paketindedir; model ayri indirilir:
- Hedef: once paket ici, sonra kullanici veri alani, sonra ortak alan.
  Indirme her zaman kullanici alanina yapilir (yonetici yetkisi gerekmez).
- Ozeti dogru model tekrar indirilmez.
- Yarim/bozuk indirme calisan modelin yerini almaz (atomik degisim).
- Devam (Range) ve yeniden deneme desteklenir.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
import tempfile
import urllib.request
import zipfile
from .engine import cuda_root, _varsayilan_model_yolu

MODEL_SURUM = 'eg2-q8-256-v2'
MODEL_DOSYA = 'embeddinggemma-2-Q8_0.gguf'
MODEL_SHA256 = '2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135'
MODEL_BOYUT = 309855456
MODEL_URL = ('https://huggingface.co/ggml-org/embeddinggemma-2-GGUF/resolve/'
             '58faf90940886df2d62be555c8765d00dac362c5/embeddinggemma-2-Q8_0.gguf')
BASE = 'https://github.com/ggml-org/llama.cpp/releases/download/b11765/'
CUDA = [
 ('llama-b11765-bin-win-cuda-12.4-x64.zip','1dd1eddb867a7ab8eca08f972ee3e623fb32d298d451aacba3cf0f0393c5eae'),
 ('cudart-llama-bin-win-cuda-12.4-x64.zip','8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6'),
]
DENEME = 3


def hedef_yol(kok=None):
    return str(Path(kok) / MODEL_DOSYA) if kok else _varsayilan_model_yolu()


def _sha256_yoksa(path):
    if not Path(path).is_file(): return None
    with open(path,'rb') as source:
        return hashlib.file_digest(source,'sha256').hexdigest()


def gerekli_mi(yol=None):
    return _sha256_yoksa(yol or hedef_yol()) != MODEL_SHA256


def paylasilan_hazir():
    """Kurulu ya da ortak alanda ozeti dogru model var mi."""
    from .engine import shared_model_path, asset_root, user_model_path
    assets = asset_root()
    installed = (assets.parent.parent / 'unins000.exe').is_file()
    return ((installed and not gerekli_mi(str(assets / MODEL_DOSYA)))
            or not gerekli_mi(str(user_model_path()))
            or not gerekli_mi(str(shared_model_path())))


def _aralik_iste(url, baslangic):
    istek = urllib.request.Request(url, headers={'Range': f'bytes={baslangic}-'})
    return urllib.request.urlopen(istek, timeout=90)


def indir(url, oet, yol, ilerleme=None, cancel=None, deneme=DENEME):
    """Modeli indir: ozet tutuyorsa atla, yarim dosyaya devam et, dogrula, ata.

    `deneme` kez yeniden dener; iptal ve dogrulama hatasi disinda sessizce
    gecmez. Hedef yalniz dogrulama gectiginde degisir.
    """
    from .engine import user_model_path
    target = Path(yol or str(user_model_path()))
    target.parent.mkdir(parents=True, exist_ok=True)
    if oet and _sha256_yoksa(target) == oet:
        if ilerleme:
            try:
                ilerleme(target.stat().st_size, target.stat().st_size)
            except OSError:
                pass
        return str(target)
    partial = target.with_suffix(target.suffix + '.part')
    hata = None
    for tur in range(max(1, int(deneme))):
        try:
            baslangic = partial.stat().st_size if partial.is_file() else 0
            if baslangic:
                try:
                    yanit = _aralik_iste(url, baslangic)
                    kod = yanit.status
                except Exception:
                    yanit, kod = None, 0
                if yanit is None or kod != 206:
                    try:
                        if yanit is not None: yanit.close()
                    except Exception:
                        pass
                    partial.unlink(missing_ok=True)
                    baslangic = 0
                    yanit = urllib.request.urlopen(url, timeout=90)
            else:
                yanit = urllib.request.urlopen(url, timeout=90)
            with yanit, partial.open('ab' if baslangic else 'wb') as out:
                alinan = yanit.headers.get('Content-Range')
                if alinan:
                    try:
                        toplam = int(alinan.rsplit('/', 1)[1])
                    except ValueError:
                        toplam = 0
                else:
                    try:
                        toplam = baslangic + int(yanit.headers.get('Content-Length', 0))
                    except ValueError:
                        toplam = 0
                done = baslangic
                if ilerleme and (done or toplam):
                    ilerleme(done, toplam)
                while True:
                    if cancel and cancel(): raise InterruptedError('İndirme iptal edildi')
                    block = yanit.read(1024 * 1024)
                    if not block: break
                    out.write(block); done += len(block)
                    if ilerleme: ilerleme(done, toplam)
            if not oet or _sha256_yoksa(partial) != oet:
                # Bozuk parca saklanmaz: devam etse yine dogrulamadan gecemez.
                partial.unlink(missing_ok=True)
                raise ValueError('model dosyasi dogrulamasi basarisiz')
            partial.replace(target)
            return str(target)
        except (InterruptedError, ValueError):
            raise
        except Exception as exc:
            hata = exc
            if tur < max(1, int(deneme)) - 1:
                time.sleep(2 * (tur + 1))
                continue
            raise
    raise RuntimeError(f'indirme tamamlanamadi: {hata}')
    return None


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
