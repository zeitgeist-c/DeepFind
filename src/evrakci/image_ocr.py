"""Read-only image/TIFF OCR using the existing local Tesseract engine."""
import time
from PIL import Image, ImageOps
from . import ocr

def ocr_images(path,pages,vault_dir,language='tur'):
    ok,missing=ocr.models_ok(language)
    if not ok:
        return [ocr.OcrPage(p+1,method='unavailable',error_code='MODEL_MISSING') for p in pages],None
    if not ocr.ram_allows():
        return [ocr.OcrPage(p+1,method='deferred',error_code='MEMORY_LIMIT') for p in pages],None
    work=ocr.temp_dir(vault_dir)
    try:
        results=[]
        with Image.open(path) as image:
            for page in pages:
                started=time.perf_counter(); image.seek(page)
                frame=ImageOps.exif_transpose(image).convert('RGB')
                frame.thumbnail((3000,3000))
                png=str(work)+f'/image-{page}.png'; frame.save(png)
                tsv,elapsed,error=ocr._run_tess(png,language,3,ocr.BASIC_TIMEOUT,work)
                text,confidence,words=ocr.parse_tsv(tsv)
                results.append(ocr.OcrPage(page+1,text=text,mean_conf=confidence,words=words,
                    method='timeout' if error else ('basic' if words else 'low'),
                    error_code=error or ('NO_TEXT' if not words else None),langs=language,
                    elapsed_ms=int((time.perf_counter()-started)*1000),attempts=1))
        return results,None
    finally: ocr._rmtree_tmp(work)
