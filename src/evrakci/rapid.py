"""RapidOCR motoru: tek paylaşılan motor örneği, tembel yükleme, kilitli çağrı.

PP-OCR modelleri ONNX Runtime üzerinde çalışır; Türkçeyi ek dil indirmeden okur.
Motor ilk kullanımda (~1 sn) yüklenir; süreç başına bir kez kurulur ve kilitli
tutulur. OCR işleri ayrı spawn süreçlerinde koştuğu için her işçi kendi motorunu
yükler — ana arayüz süreci bloklanmaz.
"""
from __future__ import annotations

import importlib.util
import logging
import threading

log = logging.getLogger("evrakci.rapid")

_lock = threading.Lock()
_engine = None
_failed = False

# rapidocr 3.x paket içi modeller (indirme yok): det + cls + rec
_MODEL_FILES = (
    "PP-OCRv6_det_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "PP-OCRv6_rec_small.onnx",
)


def stack_present() -> bool:
    """Pahalı import yapmadan RapidOCR zinciri kurulu mu?"""
    for mod in ("rapidocr", "onnxruntime", "cv2", "numpy"):
        try:
            if importlib.util.find_spec(mod) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def models_present() -> bool:
    """Modeller rapidocr paketinin içinde gelir; varlıkları yetir, boyut 0 değil."""
    try:
        import rapidocr
        from pathlib import Path
        root = Path(rapidocr.__file__).parent / "models"
        return all((root / f).is_file() and (root / f).stat().st_size > 0
                   for f in _MODEL_FILES)
    except Exception:
        return False


def get_engine():
    """Paylaşılan RapidOCR örneği; kurulamazsa RuntimeError (motor eksik)."""
    global _engine, _failed
    if _engine is not None:
        return _engine
    if _failed:
        raise RuntimeError("RapidOCR motoru daha önce kurulamadı")
    if not stack_present():
        raise RuntimeError("RapidOCR zinciri kurulu değil")
    with _lock:
        if _engine is None:
            try:
                # rapidocr model yüklerken INFO satırları basar; konsolsuz
                # masaüstü uygulamada bunlar gürültü — kendi ayarıyla kıs.
                # Not: `from rapidocr import RapidOCR` paketlenmiş (donmuş)
                # uygulamada lazy __getattr__ yüzünden kırılıyor; iç modülden
                # doğrudan import her ortamda kanıtlı çalışıyor.
                from rapidocr.main import RapidOCR
                _engine = RapidOCR(params={"Global.log_level": "warning"})
            except Exception as exc:
                _failed = True
                log.warning("RapidOCR kurulamadı: %s", exc)
                raise RuntimeError(f"RapidOCR motoru kurulamadı: {exc}") from exc
    return _engine


def run(image_bgr, use_det: bool = True, use_cls: bool = True, use_rec: bool = True):
    """BGR ndarray -> RapidOCR sonucu (kilitli tek çağrı)."""
    engine = get_engine()
    with _lock:
        return engine(image_bgr, use_det=use_det, use_cls=use_cls, use_rec=use_rec)


def reset() -> None:
    """Test/onarım: motor örneğini unut (yeniden kurulum izinli)."""
    global _engine, _failed
    with _lock:
        _engine = None
        _failed = False
