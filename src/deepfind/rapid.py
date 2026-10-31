"""RapidOCR engine: one shared engine instance, lazy load, locked calls.

PP-OCR models run on ONNX Runtime; they read Turkish with no extra language download.
The engine loads on first use (~1 s); it is installed once per process and kept
locked. OCR jobs run in separate spawn processes, so every worker loads
its own engine — the main UI process never blocks."""
from __future__ import annotations

import importlib.util
import logging
import threading
from .theme import t

log = logging.getLogger("deepfind.rapid")

_lock = threading.Lock()
_engine = None
_failed = False

# rapidocr 3.x in-package models (no download): det + cls + rec
_MODEL_FILES = (
    "PP-OCRv6_det_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "PP-OCRv6_rec_small.onnx",
)


def stack_present() -> bool:
    """Is the RapidOCR chain installed, without an expensive import?"""
    for mod in ("rapidocr", "onnxruntime", "cv2", "numpy"):
        try:
            if importlib.util.find_spec(mod) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def models_present() -> bool:
    """Models ship inside the rapidocr package; existence suffices, size non-zero."""
    try:
        import rapidocr
        from pathlib import Path
        root = Path(rapidocr.__file__).parent / "models"
        return all((root / f).is_file() and (root / f).stat().st_size > 0
                   for f in _MODEL_FILES)
    except Exception:
        return False


def get_engine():
    """The shared RapidOCR instance; RuntimeError when uninstallable (engine missing)."""
    global _engine, _failed
    if _engine is not None:
        return _engine
    if _failed:
        raise RuntimeError(t("RapidOCR motoru daha önce kurulamadı"))
    if not stack_present():
        raise RuntimeError(t("RapidOCR zinciri kurulu değil"))
    with _lock:
        if _engine is None:
            try:
                # rapidocr prints INFO lines while loading models; console-free
                # in the desktop app these are noise — mute with its own setting.
                # Note: `from rapidocr import RapidOCR` is packaged (frozen)
                # breaks in the app because of lazy __getattr__; from the inner module
                # direct import is proven to work in every environment.
                from rapidocr.main import RapidOCR
                _engine = RapidOCR(params={"Global.log_level": "warning"})
            except Exception as exc:
                _failed = True
                log.warning(t("RapidOCR kurulamadı: %s"), exc)
                raise RuntimeError(t("RapidOCR motoru kurulamadı: {exc}", exc=exc)) from exc
    return _engine


def run(image_bgr, use_det: bool = True, use_cls: bool = True, use_rec: bool = True):
    """BGR ndarray -> RapidOCR result (single locked call)."""
    engine = get_engine()
    with _lock:
        return engine(image_bgr, use_det=use_det, use_cls=use_cls, use_rec=use_rec)


def reset() -> None:
    """Test/repair: forget the engine instance (reinstall allowed)."""
    global _engine, _failed
    with _lock:
        _engine = None
        _failed = False
