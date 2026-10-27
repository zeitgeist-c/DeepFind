"""Read-only image/TIFF OCR using the shared RapidOCR engine."""
import time

from PIL import Image, ImageOps

from . import ocr


def ocr_images(path, pages, vault_dir):
    ok, _missing = ocr.engine_ok()
    if not ok:
        return [ocr.OcrPage(p + 1, method="unavailable",
                            error_code="ENGINE_UNAVAILABLE") for p in pages], None
    if not ocr.ram_allows():
        return [ocr.OcrPage(p + 1, method="deferred", error_code="MEMORY_LIMIT") for p in pages], None
    work = ocr.temp_dir(vault_dir)
    try:
        results = []
        with Image.open(path) as image:
            for page in pages:
                started = time.perf_counter()
                image.seek(page)
                frame = ImageOps.exif_transpose(image).convert("RGB")
                frame.thumbnail((3000, 3000))
                png = str(work) + f"/image-{page}.png"
                frame.save(png)
                try:
                    text, confidence, words = ocr.recognize_png(png)
                    method = "basic" if words else "low"
                    error_code = None if words else "NO_TEXT"
                except RuntimeError:
                    text, confidence, words = "", -1.0, 0
                    method, error_code = "unavailable", "ENGINE_UNAVAILABLE"
                except Exception:
                    text, confidence, words = "", -1.0, 0
                    method, error_code = "low", "OCR_FAILED"
                results.append(ocr.OcrPage(page + 1, text=text, mean_conf=confidence,
                                           words=words, method=method, error_code=error_code,
                                           elapsed_ms=int((time.perf_counter() - started) * 1000)))
        return results, None
    finally:
        ocr._rmtree_tmp(work)
