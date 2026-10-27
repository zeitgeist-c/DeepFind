"""Managed llama.cpp process: shared model, authenticated loopback, offline assets."""
from __future__ import annotations
import atexit
import json
import os
import re
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import numpy as np
from . import paths

MODEL_VER = 'eg2-q8-256-v2'
DIM = 256
SORGU_ONEKI = 'task: search result | query: '
BELGE_ONEKI = 'title: none | text: '
VARSAYILAN_TOPLU = 1
VARSAYILAN_UZUNLUK = 512
MODEL_DOSYA = 'embeddinggemma-2-Q8_0.gguf'
_LOCK = threading.RLock()
_SESSION = None
_STATUS = {'state': 'Bekliyor', 'backend': '', 'error': ''}
_BACKEND = 'auto'
_START_LOCK = threading.Lock()
_GENERATION = 0


def asset_root():
    return Path(sys._MEIPASS) / 'embedding' if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2] / 'build' / 'embedding'


def _varsayilan_model_yolu():
    bundled = asset_root() / MODEL_DOSYA
    if bundled.is_file(): return str(bundled)
    return str(shared_model_path())


def shared_model_path():
    return Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'DeepFind' / 'models' / MODEL_DOSYA


def status():
    return dict(_STATUS)


def cuda_root():
    return paths.engines_dir('b11765-cuda12')


def close():
    global _SESSION, _GENERATION
    with _LOCK:
        _GENERATION += 1
        old, _SESSION = _SESSION, None
        _STATUS.update(state='Bekliyor', backend='', device='', error='')
    if old is not None: old.close()


def set_backend(name):
    global _BACKEND
    if name not in ('auto', 'cpu', 'vulkan', 'cuda'):
        raise ValueError('Geçersiz motor')
    close()
    _BACKEND = name


def hazir_oturum(yol=None):
    if _SESSION is not None:
        if _SESSION.alive(): return _SESSION
        _STATUS.update(state='Model süreci durdu', backend='', device='', error='Anlamsal arama için motoru yeniden başlatın.')
    return None


def isit_oturumu(yol=None, cancel=None):
    global _SESSION
    generation = _GENERATION
    with _START_LOCK:
        cancelled = lambda: generation != _GENERATION or bool(cancel and cancel())
        if cancelled(): return None
        if hazir_oturum(yol) is not None:
            return _SESSION
        if _SESSION is not None:
            _SESSION.close()
            _SESSION = None
        if not Path(yol or _varsayilan_model_yolu()).is_file():
            _STATUS.update(state='Model eksik', error='Kurulumu onarın; model dosyası bulunamadı.')
            return None
        _STATUS.update(state='Model yükleniyor', error='')
        try:
            if yol is None:
                from .model_indir import gerekli_mi
                if gerekli_mi():
                    raise ValueError('Model dosyasının SHA-256 doğrulaması başarısız; kurulumu onarın.')
            new = Oturum(yol, backend=_BACKEND, cancel=cancelled)
            with _LOCK:
                if cancelled():
                    new.close()
                    return None
                _SESSION = new
                _STATUS.update(state='Hazır', backend=new.backend, device=new.device, error=new.fallback)
                return new
        except Exception as exc:
            if generation == _GENERATION:
                _STATUS.update(state='Klasik arama etkin', error=str(exc))
            return None


atexit.register(close)


def normalize(v):
    v = np.asarray(v, dtype=np.float32)
    if not np.isfinite(v).all():
        raise ValueError('Model sonlu olmayan vektör üretti')
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    if np.any(norm < 1e-12):
        raise ValueError('Model boş vektör üretti')
    return (v / norm).astype(np.float32)


def _own_process(process):
    """Kill native worker if the application crashes (Windows job ownership)."""
    if os.name != 'nt': return None
    import ctypes as c
    from ctypes import wintypes as w
    class Limits(c.Structure):
        _fields_ = [('user',c.c_int64),('jobuser',c.c_int64),('flags',w.DWORD),
                    ('min',c.c_size_t),('max',c.c_size_t),('count',w.DWORD),
                    ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
    class Extended(c.Structure):
        _fields_ = [('basic',Limits),('io',c.c_uint64*6),('processmem',c.c_size_t),
                    ('jobmem',c.c_size_t),('peakprocess',c.c_size_t),('peakjob',c.c_size_t)]
    kernel = c.windll.kernel32
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE,w.HANDLE]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.CreateJobObjectW(None,None)
    info = Extended(); info.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
    if not handle: raise OSError('Model süreç sahipliği kurulamadı')
    if not kernel.SetInformationJobObject(handle,9,c.byref(info),c.sizeof(info)) or not kernel.AssignProcessToJobObject(handle,w.HANDLE(int(process._handle))):
        kernel.CloseHandle(handle)
        raise OSError('Model süreci uygulamaya bağlanamadı')
    return handle


class Oturum:
    def __init__(self, model_yolu=None, *, backend='auto', cancel=None):
        self.model = str(Path(model_yolu or _varsayilan_model_yolu()).resolve())
        self._kilit = threading.RLock()
        self.proc = None
        self.fallback = ''
        self.cancel = cancel
        errors = []
        for choice in (['cuda', 'vulkan', 'cpu'] if backend == 'auto' else [backend]):
            if cancel and cancel(): raise InterruptedError('Model yüklemesi iptal edildi')
            directory = cuda_root() if choice == 'cuda' else asset_root() / choice
            exe = directory / 'llama-server.exe'
            if not exe.is_file():
                if backend != 'auto': errors.append(f'{choice}: motor kurulu değil')
                continue
            try:
                self._start(exe, choice)
                self.backend, self.fallback = choice, '; '.join(errors)
                return
            except Exception as exc:
                self.close()
                errors.append(f'{choice}: {exc}')
        raise RuntimeError('; '.join(errors) or 'Embedding motoru bulunamadı')

    def _start(self, exe, backend):
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        child_env = os.environ.copy()
        common = asset_root() / 'common'
        if common.is_dir():
            child_env['PATH'] = str(common) + os.pathsep + child_env.get('PATH','')
        if backend != 'cpu':
            check = subprocess.run([str(exe), '--list-devices'], capture_output=True, timeout=45, creationflags=flags, env=child_env)
            devices = (check.stdout + check.stderr).decode('utf-8', 'replace')
            required = 'CUDA' if backend == 'cuda' else 'Vulkan'
            if check.returncode or not re.search(r'^\s*'+required+r'\d+:',devices,re.MULTILINE):
                raise RuntimeError('Uygun GPU/sürücü bulunamadı')
            self.device = next(line.strip() for line in devices.splitlines() if re.match(r'\s*'+required+r'\d+:',line))
        else:
            self.device = 'CPU'
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.key = secrets.token_hex(32)
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        cmd = [str(exe), '-m', self.model, '--host', '127.0.0.1', '--port', str(self.port),
               '--api-key', self.key, '--embeddings', '--pooling', 'mean', '--ctx-size', '2048',
               '--batch-size', '1024', '--ubatch-size', '512', '--parallel', '1',
               '--n-gpu-layers', '0' if backend == 'cpu' else '99', '--no-webui', '--log-disable']
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, creationflags=flags, cwd=exe.parent, env=child_env)
        self._job = _own_process(self.proc)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.cancel and self.cancel(): raise InterruptedError('Model yüklemesi iptal edildi')
            if not self.alive(): raise RuntimeError('Model süreci açılamadı')
            try:
                self.request('/health', timeout=1)
                return
            except Exception: time.sleep(0.1)
        raise TimeoutError('Model yükleme zaman aşımı')

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def close(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try: self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
            self.proc = None
        job = getattr(self, '_job', None)
        if job:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(job)
            self._job = None

    @property
    def gpu_mu(self):
        return self.backend != 'cpu'

    def request(self, path, data=None, timeout=120):
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body,
                                     headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        with self.http.open(req, timeout=timeout) as response: return json.load(response)

    def encode(self, metinler, gorev='sorgu', toplu=1, cancel=None):
        if not metinler: return np.zeros((0, DIM), dtype=np.float32)
        prefix = SORGU_ONEKI if gorev == 'sorgu' else BELGE_ONEKI
        vectors = []
        for text in metinler:
            with self._kilit:
                if cancel and cancel(): raise InterruptedError('Gömme iptal edildi')
                header = self.request('/tokenize', {'content': prefix, 'add_special': True})['tokens']
                tokens = self.request('/tokenize', {'content': text or ' ', 'add_special': False})['tokens']
                capacity = 512 - len(header)
                if capacity < 128: raise ValueError('Geçersiz görev öneki')
                chunks = []
                for start in range(0, max(1,len(tokens)), capacity - 64):
                    if cancel and cancel(): raise InterruptedError('Gömme iptal edildi')
                    part = header + tokens[start:start + capacity]
                    response = self.request('/embedding', {'input': part})
                    vector = np.asarray(response[0]['embedding'], dtype=np.float32).reshape(-1)
                    if vector.size != 768: raise ValueError('Beklenmeyen model çıktı boyutu')
                    chunks.append(normalize(vector[:DIM]))
                    if start + capacity >= len(tokens): break
                vectors.append(normalize(np.mean(chunks, axis=0)))
        return np.asarray(vectors, dtype=np.float32)
