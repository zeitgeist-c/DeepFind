"""Denetimde bulunan veri ve parola regresyonları; yalnız yapay veri."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from evrakci import backup, coordinator, extract, schema, search, vault
from evrakci.migrate import ensure_v7
from evrakci.vocab import ensure_v5

PW = "denetim-sifresi-1234"
APP = None


def make_vault(tmp_path):
    path = str(tmp_path / "vault.db")
    con = vault.open_vault(path, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    return con, path


def test_scanning_second_root_preserves_first_and_reappearance(tmp_path, monkeypatch):
    con, db = make_vault(tmp_path)
    roots = [tmp_path / "a", tmp_path / "b"]
    monkeypatch.setattr(extract, "extract", lambda *a: extract.ExtractResult(
        [extract.Segment("para", None, "Paragraf 1", "Ankara denetim")]))
    for root in roots:
        root.mkdir()
        p = root / "belge.docx"
        p.write_bytes(b"sentetik")
        os.utime(p, (1_700_000_000, 1_700_000_000))
        coordinator.run_scan(con, db, str(root))
    assert len(search.search(con, "denetim")) == 2
    p = roots[0] / "belge.docx"
    data = p.read_bytes()
    p.unlink()
    coordinator.run_scan(con, db, str(roots[0]))
    assert len(search.search(con, "denetim")) == 1
    p.write_bytes(data)
    os.utime(p, (1_700_000_000, 1_700_000_000))
    coordinator.run_scan(con, db, str(roots[0]))
    assert len(search.search(con, "denetim")) == 2
    rows = con.execute("SELECT s.rev_id,r.rev_id FROM segments s JOIN file_revisions r ON r.file_id=s.file_id AND r.active=1").fetchall()
    assert rows and all(a == b for a, b in rows)
    con.close()


def test_old_backup_restores_with_current_password(tmp_path):
    con, db = make_vault(tmp_path)
    dest = str(tmp_path / "backups")
    old = backup.create_backup(con, db, PW, dest, manual=True)
    con.close()
    new = "yeni-denetim-sifresi-1234"
    backup.change_password(db, PW, new, dest)
    backup.restore_replace(db, new, old, str(tmp_path / "staging"), backup_password=PW)
    con = vault.open_vault(db, new)
    con.close()
    with pytest.raises(Exception):
        vault.open_vault(db, PW)


def test_failed_password_verification_keeps_original(tmp_path, monkeypatch):
    con, db = make_vault(tmp_path)
    con.close()
    original = backup.verify_backup
    def fail_staging(path, password):
        if ".rekey-" in path:
            return {"ok": False}
        return original(path, password)
    monkeypatch.setattr(backup, "verify_backup", fail_staging)
    with pytest.raises(RuntimeError):
        backup.change_password(db, PW, "yeni-denetim-12345", str(tmp_path / "backups"))
    con = vault.open_vault(db, PW)
    con.close()


def test_filename_is_searchable_even_when_content_differs(tmp_path):
    con, db = make_vault(tmp_path)
    from evrakci import rank
    from evrakci.scan import Entry
    p = str(tmp_path / "Ankara-vergi-2024.docx")
    fid = coordinator.ensure_file(con, Entry(p, os.path.basename(p), ".docx", 10, 1))
    coordinator.write_revision(con, fid, "10:1", extract.ExtractResult(
        [extract.Segment("para", None, "Paragraf 1", "İçerik tamamen farklı.")]))
    assert rank.search_ranked(con, "Ankara vergi")["results"]
    con.close()


def test_utf8_budget_removes_excess_segments_and_future_schema_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "MAX_TEXT_DOC", 5)
    cut, status, code = extract._budget_text(["şşş", "sonraki"])
    assert len("".join(cut).encode("utf-8")) <= 5
    assert status == "partial" and code == "SIZE_LIMIT"
    con, db = make_vault(tmp_path)
    con.execute("UPDATE schema_meta SET v='99' WHERE k='schema_version'")
    con.commit()
    with pytest.raises(RuntimeError):
        schema.ensure_schema(con)
    assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == "99"
    con.close()


def test_password_confirmation_and_wrong_login_stay_open():
    global APP
    from PySide6.QtWidgets import QApplication, QDialog
    from evrakci.auth import ParolaDialog
    app = QApplication.instance() or QApplication([])
    APP = app
    d = ParolaDialog(change=True)
    d.old.setText(PW)
    d.new.setText("yeni-denetim-12345")
    d.confirm.setText("farkli-denetim-1234")
    d._submit()
    assert "eşleşmiyor" in d.error.text()
    assert d.result() != QDialog.Accepted
    d.confirm.setText(d.new.text())
    d._submit()
    assert d.result() == QDialog.Accepted
    def wrong(_):
        raise ValueError()
    login = ParolaDialog(verify=wrong)
    login.old.setText("yanlis")
    login._submit()
    assert login.result() != QDialog.Accepted
    assert login.error.text()
    login.close()
    d.close()
    login.deleteLater()
    d.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
