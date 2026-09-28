"""OCR installer: resumable, verified activation and deferred work recovery."""
import hashlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import ocr_setup, schema, vault
from evrakci.migrate import ensure_v7


class _Response(io.BytesIO):
    status = 206

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def test_resumed_download_only_activates_verified_model(tmp_path, monkeypatch):
    data = b"verified-model-content"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(ocr_setup, "MODELS", {"tur": (len(data), digest)})
    monkeypatch.setattr(ocr_setup, "data_dir", lambda: tmp_path)
    exe = tmp_path / "tesseract.exe"
    exe.write_bytes(b"engine")
    monkeypatch.setattr(ocr_setup, "executable", lambda: exe)
    monkeypatch.setattr(ocr_setup, "_engine_check", lambda _: None)
    part = tmp_path / "tur.traineddata.part"
    part.write_bytes(data[:8])
    requested = []

    def download(req, timeout):
        requested.append(req.headers.get("Range"))
        return _Response(data[8:])

    monkeypatch.setattr(ocr_setup.urllib.request, "urlopen", download)
    ocr_setup.ensure()
    assert requested == ["bytes=8-"]
    assert (tmp_path / "tur.traineddata").read_bytes() == data
    assert not part.exists()
    assert ocr_setup.ready() == (True, [])


def test_corrupt_offline_model_does_not_activate(tmp_path, monkeypatch):
    good = b"correct-model"
    monkeypatch.setattr(ocr_setup, "MODELS", {"tur": (len(good), hashlib.sha256(good).hexdigest())})
    monkeypatch.setattr(ocr_setup, "data_dir", lambda: tmp_path / "active")
    exe = tmp_path / "tesseract.exe"
    exe.write_bytes(b"engine")
    monkeypatch.setattr(ocr_setup, "executable", lambda: exe)
    offline = tmp_path / "offline"
    offline.mkdir()
    (offline / "tur.traineddata").write_bytes(b"corrupt-model")
    import pytest
    with pytest.raises(RuntimeError, match="doğrulanamadı"):
        ocr_setup.ensure(offline_dir=str(offline))
    assert not (tmp_path / "active" / "tur.traineddata").exists()


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


def test_first_run_dialog_waits_for_install_thread(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from evrakci import ocr_setup_ui

    app = QApplication.instance() or QApplication([])
    state = {"ready": False}
    monkeypatch.setattr(ocr_setup, "ready", lambda: (state["ready"], []))

    def install(progress, offline_dir):
        assert offline_dir is None
        progress("tur", 1, 1, 10, 10)
        state["ready"] = True
        progress("ready", 1, 1, 1, 1)

    monkeypatch.setattr(ocr_setup, "ensure", install)
    assert ocr_setup_ui.prepare_ocr() is True
    app.processEvents()
