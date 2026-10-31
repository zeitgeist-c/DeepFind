"""OCR hazırlık: RapidOCR varlık denetimi, motor ısınması ve iş kurtarma."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import ocr_setup, schema, vault
from deepfind.migrate import ensure_current, ensure_v7, OCR_VERSION


def test_ready_without_downloads():
    """Modeller paketle gelir: ready() ağ gitmeden varlık denetimi yapar."""
    ok, missing = ocr_setup.ready()
    assert isinstance(ok, bool) and isinstance(missing, list)
    assert set(missing) <= {"rapidocr-zinciri", "ocr-modelleri"}


def test_ensure_fails_cleanly_when_stack_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr_setup, "ready", lambda: (False, ["rapidocr-zinciri"]))
    import pytest
    with pytest.raises(RuntimeError, match="eksik"):
        ocr_setup.ensure()


def test_only_missing_ocr_jobs_reopened(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr_setup, "ready", lambda: (True, []))
    path = str(tmp_path / "vault.db")
    con = vault.open_vault(path, "test-ocr-password-1234")
    schema.ensure_schema(con)
    ensure_v7(con)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('one.pdf','one.pdf','.pdf')")
    fid = con.execute("SELECT file_id FROM files").fetchone()[0]
    con.execute("INSERT INTO jobs(file_id,signature,kind,status,not_before,error_code) VALUES (?,?,?,'pending',9999999999,?)",
                (fid, "a", "ocr", "MODEL_MISSING"))
    con.execute("INSERT INTO jobs(file_id,signature,kind,status,not_before,error_code) VALUES (?,?,?,'pending',9999999999,?)",
                (fid, "b", "ocr", "PROCESS_TIMEOUT"))
    con.commit()
    assert ocr_setup.reopen_deferred(con) == 1
    assert con.execute("SELECT not_before FROM jobs WHERE signature='a'").fetchone()[0] == 0
    assert con.execute("SELECT not_before FROM jobs WHERE signature='b'").fetchone()[0] == 9999999999
    con.close()


def test_engine_backfill_requeues_low_quality_once(tmp_path):
    """Eski Tesseract dönemi: 'low' kapsama satırları RapidOCR'a yeniden düşer."""
    path = str(tmp_path / "vault.db")
    con = vault.open_vault(path, "test-ocr-password-1234")
    schema.ensure_schema(con)
    ensure_current(con)
    con.execute("UPDATE schema_meta SET v='a6-1' WHERE k='ocr_version'")
    con.execute("INSERT INTO files(path,name,ext) VALUES ('t.pdf','t.pdf','.pdf')")
    fid = con.execute("SELECT file_id FROM files").fetchone()[0]
    con.execute("INSERT INTO file_revisions(file_id, signature, extractor, created_at, active)"
                " VALUES (?, 'x', 'archive-034', 1, 1)", (fid,))
    con.execute("INSERT INTO ocr_coverage VALUES (?,?,?,?,?)", (fid, 1, 1, "low", "NO_TEXT"))
    con.execute("INSERT INTO ocr_coverage VALUES (?,?,?,?,?)", (fid, 1, 2, "basic", None))
    con.commit()
    assert ocr_setup.engine_backfill(con) == 1
    # re-running does nothing (version bumped)
    assert ocr_setup.engine_backfill(con) == 0
    assert con.execute("SELECT count(*) FROM jobs WHERE kind='ocr'").fetchone()[0] == 1
    # broken row deleted, clean row kept
    assert con.execute("SELECT count(*) FROM ocr_coverage WHERE page=1").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM ocr_coverage WHERE page=2").fetchone()[0] == 1
    assert con.execute("SELECT v FROM schema_meta WHERE k='ocr_version'").fetchone()[0] == OCR_VERSION
    con.close()


def test_first_run_dialog_waits_for_verify_thread(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from deepfind import ocr_setup_ui

    app = QApplication.instance() or QApplication([])
    state = {"ready": False}
    monkeypatch.setattr(ocr_setup, "ready", lambda: (state["ready"], []))

    def install(progress):
        progress("motor", 1, 1, 0, 1)
        state["ready"] = True
        progress("ready", 1, 1, 1, 1)

    monkeypatch.setattr(ocr_setup, "ensure", install)
    assert ocr_setup_ui.prepare_ocr() is True
    app.processEvents()
