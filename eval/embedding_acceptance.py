"""Real offline model comparison; synthetic Turkish content only."""
import json
from pathlib import Path
import subprocess
import sys
import time
import types
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from deepfind import engine


def main():
    docs = ['elektrik faturası tüketim bedeli 1250 TL', 'kira sözleşmesi aylık 40000 TL',
            'personel maaş bordrosu çalışan ücreti', 'vergi levhası mükellef bilgileri',
            'araç bakım onarım servis faturası', 'iş sağlığı güvenliği denetim raporu',
            'banka hesap hareketleri havale dekontu', 'satın alma sipariş teslim tutanağı']
    queries = ['ev kiralama anlaşması', 'çalışanlara yapılan aylık ödeme',
               'otomobil tamir masrafı', 'elektrik kullanım ücreti',
               'işyerinde güvenlik incelemesi', 'para transferi belgesi']
    expected = [1, 2, 4, 0, 5, 6]
    result = {}
    outputs = {}
    for precision in ['BF16', 'Q8_0']:
        session = engine.Oturum(str(engine.asset_root() / f'embeddinggemma-2-{precision}.gguf'), backend='cpu')
        try:
            t = time.perf_counter()
            d, q = session.encode(docs, gorev='belge'), session.encode(queries)
            scores = q @ d.T
            outputs[precision] = (d, q)
            top = scores.argmax(axis=1).tolist()
            result[precision] = {'top': top, 'correct': sum(a == b for a,b in zip(top,expected)),
                                 'seconds': round(time.perf_counter()-t, 3)}
        finally: session.close()
    d0,q0 = outputs['BF16']; d1,q1 = outputs['Q8_0']
    result['reference_cosine_min'] = float(np.min(np.sum(np.vstack([d0,q0])*np.vstack([d1,q1]), axis=1)))
    old_path = Path.home() / 'AppData/Local/DeepFind/models/eg2-text.onnx'
    snapshots = Path.home() / '.cache/huggingface/hub/models--google--embeddinggemma-2/snapshots'
    if old_path.is_file() and snapshots.is_dir():
        source = subprocess.check_output(['git','show','9f51658:src/deepfind/embed.py'],cwd=ROOT,text=True,encoding='utf-8')
        reference = types.ModuleType('deepfind.reference_embedding')
        reference.__package__ = 'deepfind'
        exec(compile(source,'reference_embedding','exec'),reference.__dict__)
        old = reference.Oturum(str(old_path),tokenizer_kaynagi=str(next(snapshots.iterdir())))
        old_d,old_q = old.encode(docs,gorev='belge'),old.encode(queries)
        result['previous_onnx'] = {'top':(old_q@old_d.T).argmax(axis=1).tolist(),
            'cosine_min_to_q8':float(np.min(np.sum(np.vstack([old_d,old_q])*np.vstack([d1,q1]),axis=1)))}
    for backend in ['vulkan', 'cuda']:
        try:
            session = engine.Oturum(backend=backend)
            try:
                v = session.encode(['yerel GPU doğrulama'])
                result[backend] = {'ok': bool(np.isfinite(v).all()), 'shape': list(v.shape), 'device':session.device}
            finally: session.close()
        except Exception as exc: result[backend] = {'ok': False, 'error': str(exc)}
    assert result['Q8_0']['correct'] >= result['BF16']['correct']
    assert result['reference_cosine_min'] > .99
    print(json.dumps(result, indent=2, ensure_ascii=True), flush=True)
    (ROOT / 'build' / 'embedding-acceptance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__ == '__main__': main()
