"""OCR readiness check: RapidOCR ships with its models, no download.

The engine is a Python dependency (rapidocr + onnxruntime); the models live
inside the rapidocr package. This module verifies installation and re-queues
deferred OCR jobs. Needs no network access."""
from __future__ import annotations

from . import rapid
from .theme import t


def ready() -> tuple[bool, list[str]]:
    """(is_ready, missing_list). Never performs the expensive engine setup, only an existence check."""
    from . import ocr
    return ocr.engine_ok()


def ensure(progress=None) -> None:
    """Setup step: genuinely try installing the engine (first ~1 s load).

RuntimeError on failure; the UI shows the repair-flow message."""
    if progress:
        progress("motor", 1, 1, 0, 1)
    ok, missing = ready()
    if not ok:
        raise RuntimeError(t("OCR bileşenleri eksik: ") + ", ".join(missing) +
                           t(" — uygulama paketini yeniden edinin."))
    rapid.get_engine()
    # It was meant as warm-up: must not stop in the sample UI process (would hold ONNX memory for nothing).
    rapid.reset()
    if progress:
        progress("ready", 1, 1, 1, 1)


def reopen_deferred(con) -> int:
    """Retry only OCR jobs previously deferred over engine/model gaps."""
    if not ready()[0]:
        return 0
    result = con.execute(
        "UPDATE jobs SET not_before=0 WHERE kind='ocr' AND status='pending'"
        " AND error_code IN ('MODEL_MISSING','ENGINE_UNAVAILABLE')")
    con.commit()
    return result.rowcount


def engine_backfill(con) -> int:
    """On engine change (Tesseract to RapidOCR), re-queue old low-quality OCR records:
broken/uncoverable record rows are deleted, files with a live
revision get an OCR job. ocr_version runs it once."""
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
