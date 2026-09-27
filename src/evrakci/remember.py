"""Windows kullanıcı hesabına bağlı, isteğe bağlı giriş hatırlama."""
import ctypes
import hashlib
import os
from ctypes import wintypes
from pathlib import Path


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _path(vault):
    key = hashlib.sha256(os.path.normcase(os.path.abspath(vault)).encode()).hexdigest()
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Evrakci" / "Credentials" / (key + ".bin")


def _crypt(data, decrypt=False):
    if os.name != "nt":
        raise OSError("Giriş hatırlama yalnız Windows üzerinde kullanılabilir.")
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, output = _Blob(len(data), buffer), _Blob()
    api = ctypes.windll.crypt32
    fn = api.CryptUnprotectData if decrypt else api.CryptProtectData
    fn.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError("Windows güvenli giriş kaydı açılamadı.")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(output.data)


def save(vault, password):
    path = _path(vault)
    encrypted = _crypt(password.encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(encrypted)
    temp.replace(path)


def load(vault):
    try:
        return _crypt(_path(vault).read_bytes(), True).decode("utf-8")
    except (OSError, UnicodeError):
        return None


def forget(vault):
    _path(vault).unlink(missing_ok=True)


def enabled(vault):
    return _path(vault).exists()
