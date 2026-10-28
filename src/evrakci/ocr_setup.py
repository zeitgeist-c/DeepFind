"""OCR hazırlık denetimi: RapidOCR paketi modelleriyle birlikte gelir, indirme yok.

Motor Python bağımlılığıdır (rapidocr + onnxruntime); modeller rapidocr paketinin
içindedir. Bu modül kurululuğu doğrular ve ertelenmiş OCR işlerini yeniden sıraya
alır. Ağ erişimi gerektirmez.
"""
from __future__ import annotations

from . import rapid


def ready() -> tuple[bool, list[str]]:
    """(hazır_mı, eksik_liste). Pahalı motor kurulumu yapmaz, yalnız varlık denetimi."""
    from . import ocr
    return ocr.engine_ok()


def ensure(progress=None) -> None:
    """Kurulum adımı: motoru gerçekten kurmayı dener (ilk ~1 sn yükleme).

    Başarısızsa RuntimeError; UI onarım akışı mesajı gösterir.
    """
    if progress:
        progress("motor", 1, 1, 0, 1)
    ok, missing = ready()
    if not ok:
        raise RuntimeError("OCR bileşenleri eksik: " + ", ".join(missing) +
                           " — uygulama paketini yeniden edinin.")
    rapid.get_engine()
    # Isindirma amacliydi: ornek UI sürecinde durmasın (ONNX belleği boşuna tutulur).
    rapid.reset()
    if progress:
        progress("ready", 1, 1, 1, 1)


def reopen_deferred(con) -> int:
    """Yalnız daha önce motor/model yüzünden ertelenen OCR işlerini yeniden dene."""
    if not ready()[0]:
        return 0
    result = con.execute(
        "UPDATE jobs SET not_before=0 WHERE kind='ocr' AND status='pending'"
        " AND error_code IN ('MODEL_MISSING','ENGINE_UNAVAILABLE')")
    con.commit()
    return result.rowcount


def engine_backfill(con) -> int:
    """Motor değişiminde (Tesseract→RapidOCR) eski düşük kaliteli OCR kayıtlarını
    yeniden kuyruğa alır: bozuk/kapsanamayan kayıt satırları silinir, etkin
    revizyonu olan dosyalara OCR işi eklenir. ocr_version bir kez yürütür."""
    from .migrate import OCR_VERSION
    row = con.execute("SELECT v FROM schema_meta WHERE k='ocr_version'").fetchone()
    if not row or row[0] == OCR_VERSION:
        return 0
    bad = "(outcome='low' OR error_code IS NOT NULL)"
    if row[0] == 'rapid-1' and OCR_VERSION == 'rapid-2':
        # Revisit only old empty-page failures for this policy change, once.
        # Other low-quality pages are not forced through another OCR pass.
        bad = "error_code='NO_TEXT'"
    n = con.execute(
        "INSERT INTO jobs(file_id, signature, kind, status) "
        "SELECT c.file_id, r.signature, 'ocr', 'pending' FROM "
        " (SELECT DISTINCT file_id FROM ocr_coverage WHERE " + bad + ") c "
        " JOIN file_revisions r ON r.file_id=c.file_id AND r.active=1 "
        "ON CONFLICT(file_id, signature, kind) DO NOTHING").rowcount
    con.execute("DELETE FROM ocr_coverage WHERE " + bad)
    con.execute("INSERT INTO schema_meta(k,v) VALUES('ocr_version',?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (OCR_VERSION,))
    con.commit()
    return n
