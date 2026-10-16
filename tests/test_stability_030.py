"""Recovery records and selectable model boundaries for the stability release."""
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from evrakci import ai, coordinator, migrate, schema, vault
from evrakci.vocab import ensure_v5, rebuild_vocab


def test_cancelled_scan_keeps_index_and_interrupted_run_is_recovered(tmp_path, monkeypatch):
    from openpyxl import Workbook
    root = tmp_path / "archive"
    root.mkdir()
    for number in range(10):
        path = root / f"{number}.xlsx"
        book = Workbook()
        book.active.append([f"Ankara evrak {number}"])
        book.save(path)
        old = time.time() - 10
        os.utime(path, (old, old))
    db = str(tmp_path / "index.db")
    password = "sentetik-kararlilik-1234"
    con = vault.open_vault(db, password)
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v8(con)
    original = coordinator._process_job
    stopped = False

    def process(*args, **kwargs):
        nonlocal stopped
        result = original(*args, **kwargs)
        stopped = True
        return result

    monkeypatch.setattr(coordinator, "_process_job", process)
    try:
        result = coordinator.run_scan(con, db, str(root), stop=lambda: stopped)
        assert result["result"] == "cancelled" and result["done"] > 0
        row = con.execute("SELECT result, done, found FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        assert row[0] == "cancelled" and row[1] == result["done"]
        preserved = con.execute("SELECT count(*) FROM segments").fetchone()[0]
        assert preserved > 0
        con.execute("INSERT INTO scan_runs(root, started_at) VALUES (?, ?)", (str(root), int(time.time())))
        con.commit()
    finally:
        con.close()
    con = vault.open_vault(db, password)
    try:
        assert migrate.recover_scan_runs(con) == 1
        assert con.execute("SELECT result FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()[0] == "interrupted"
        assert con.execute("SELECT count(*) FROM segments").fetchone()[0] == preserved
        monkeypatch.setattr(coordinator, "_process_job", original)
        resumed = coordinator.run_scan(con, db, str(root))
        assert resumed["complete"]
        assert con.execute("SELECT count(*) FROM file_revisions WHERE active=1").fetchone()[0] == 10
    finally:
        con.close()


def test_model_allowlist_and_gemma_body():
    assert list(ai.MODELS) == ["gemini-3.6-flash", "gemini-3.5-flash-lite",
                               "gemini-3.1-flash-lite", "gemma-4-26b-a4b-it"]
    assert ai.MODEL == "gemini-3.5-flash-lite"
    assert ai.selected_model("gemini-3.8-flash") == "gemini-3.6-flash"
    assert ai.selected_model("gemini-3.5-flash") == "gemini-3.5-flash-lite"
    assert ai.selected_model("gemma-4-26b-a4b-it") == "gemma-4-26b-a4b-it"
    assert ai.endpoint("gemini-3.6-flash").endswith("gemini-3.6-flash:generateContent")
    assert ai.endpoint("gemini-3.5-flash-lite").endswith("gemini-3.5-flash-lite:generateContent")
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        ai.endpoint("gemini-3.8-flash")
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        ai.endpoint("gemini-3.5-flash")
    assert ai.endpoint("gemini-3.1-flash-lite").endswith("gemini-3.1-flash-lite:generateContent")
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        ai.endpoint("../../other")
    preview = ai.Preview("question", "Ankara?", (), "", False)
    gemma = json.loads(ai.request_body(preview, "gemma-4-26b-a4b-it"))
    assert "generationConfig" not in gemma
    assert "systemInstruction" in gemma


def test_vocabulary_rebuild_uses_encrypted_stage(tmp_path):
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-sozluk-1234")
    try:
        schema.ensure_schema(con)
        ensure_v5(con)
        migrate.ensure_v8(con)
        for n in range(420):
            con.execute("INSERT INTO files(path, name, ext) VALUES (?, ?, '.doc')",
                        (f"c:/ornek/{n}.doc", f"Ankara {n}.doc"))
        con.commit()
        assert rebuild_vocab(con) > 0
        assert con.execute("SELECT freq FROM vocabulary WHERE term='ankara'").fetchone()[0] == 420
        assert con.execute("SELECT count(*) FROM vocabulary_build").fetchone()[0] == 0
    finally:
        con.close()


def test_hash_failure_marks_scan_partial(tmp_path, monkeypatch):
    from evrakci import dup
    root = tmp_path / "archive"
    root.mkdir()
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-hash-1234")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v8(con)

    def broken(*_args, **_kwargs):
        raise RuntimeError("sentetik hash hatası")

    monkeypatch.setattr(dup, "verify_pending", broken)
    try:
        result = coordinator.run_scan(con, db, str(root))
        assert result["result"] == "partial"
        assert con.execute("SELECT error_code FROM scan_runs ORDER BY run_id DESC LIMIT 1").fetchone()[0] == "HASH_ERROR"
    finally:
        con.close()


def test_existing_v7_vault_opens_without_legacy_backfill(tmp_path, monkeypatch):
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-mevcut-kasa-1234")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v7(con)
    con.execute("INSERT INTO files(path, name, ext) VALUES ('c:/ornek/koru.doc', 'koru.doc', '.doc')")
    # A prior interrupted startup may have rewritten only this marker to v3.
    con.execute("UPDATE schema_meta SET v='3' WHERE k='schema_version'")
    con.commit()
    con.close()

    from evrakci import vocab

    con = vault.open_vault(db, "sentetik-mevcut-kasa-1234")
    try:
        migrate.ensure_current(con)
        assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == "9"
        assert con.execute("SELECT name FROM files").fetchone()[0] == "koru.doc"
        migrate.ensure_current(con)
        assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == "9"
    finally:
        con.close()


def test_v9_folded_index_single_copy(tmp_path):
    """v9: segmentler tek kopya; docs_fts katlanmis icerir, folded_text yok."""
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-eski-kasa-1234")
    try:
        schema.ensure_schema(con)
        fid = con.execute("INSERT INTO files(path, name, ext) VALUES ('c:/ornek/belge.doc', 'belge.doc', '.doc')").lastrowid
        con.executemany(
            "INSERT INTO segments(file_id, kind, label, raw_text) VALUES (?, 'body', 'satır', ?)",
            [(fid, "Ankara Belge Şırnak")] * 225,
        )
        con.commit()
        ensure_v5(con)
        migrate.ensure_v9(con)
        cols = {r[1] for r in con.execute("PRAGMA table_info(segments)")}
        assert "folded_text" not in cols
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts_folded'").fetchone()
        assert con.execute("SELECT count(*) FROM docs_fts").fetchone()[0] == 225
        # katlanmis arama tek indekste calisir
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"sirnak\"'").fetchone()[0] == 225
        # silme trigger'i katlanmis indeksle tutarli
        con.execute("DELETE FROM segments WHERE seg_id=(SELECT min(seg_id) FROM segments)")
        con.commit()
        con.execute("INSERT INTO docs_fts(docs_fts) VALUES('integrity-check')")
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"sirnak\"'").fetchone()[0] == 224
    finally:
        con.close()


def test_v9_migration_from_v8_shape(tmp_path):
    """Eski bicim (folded_text kolonu + docs_fts_folded + ham docs_fts) -> v9."""
    db = str(tmp_path / "index.db")
    con = vault.open_vault(db, "sentetik-v8-kasa-1234")
    try:
        # Once gercek zincirle tam sema, sonra FTS kismini v8 bicimine dusur:
        # folded_text kolonu + docs_fts_folded + HAM yazan docs_fts trigger'lari.
        migrate.ensure_current(con)  # v9 temiz kasa (tum tablolar + v9 isaretleri)
        con.executescript("""
ALTER TABLE segments ADD COLUMN folded_text TEXT DEFAULT '';
CREATE VIRTUAL TABLE docs_fts_folded USING fts5(label, raw_text, content='segments', content_rowid='seg_id');
CREATE TRIGGER segf_ai AFTER INSERT ON segments BEGIN
  INSERT INTO docs_fts_folded(rowid,label,raw_text) VALUES(new.seg_id,new.label,new.folded_text); END;
CREATE TRIGGER segf_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts_folded(docs_fts_folded,rowid,label,raw_text) VALUES('delete',old.seg_id,old.label,old.folded_text); END;
DROP TRIGGER seg_ai;
DROP TRIGGER seg_ad;
CREATE TRIGGER seg_ai AFTER INSERT ON segments BEGIN
  INSERT INTO docs_fts(rowid,label,raw_text) VALUES(new.seg_id,new.label,new.raw_text); END;
CREATE TRIGGER seg_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts(docs_fts,rowid,label,raw_text) VALUES('delete',old.seg_id,old.label,old.raw_text); END;
DELETE FROM schema_meta WHERE k='fts_folded';
UPDATE schema_meta SET v='8' WHERE k='schema_version';
""")
        from evrakci import normalize as nz
        fid = con.execute("INSERT INTO files(path,name,ext,index_status) VALUES ('c:/a/istanbul.pdf','istanbul.pdf','.pdf','ok')").lastrowid
        for ham in ("İstanbul nüfusu", "Iğdır ili", "ÇANKIRI merkez", "Şırnak ilçesi"):
            con.execute("INSERT INTO segments(file_id,kind,label,raw_text,folded_text) VALUES (?,'body','Sayfa 1',?,?)",
                        (fid, ham, nz.folded(ham)))
        con.commit()
        # ham indeks: katlanmis sorgu bulamaz, ham sorgu bulur
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"sirnak\"'").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"Şırnak\"'").fetchone()[0] == 1

        migrate.ensure_current(con)

        assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == "9"
        cols = {r[1] for r in con.execute("PRAGMA table_info(segments)")}
        assert "folded_text" not in cols
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts_folded'").fetchone()
        # katlanmis arama artik tek indekste
        for sorgu in ("istanbul", "igdir", "cankiri", "sirnak"):
            assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH ?", ('"'+sorgu+'"',)).fetchone()[0] == 1
        # yazma yolu da fold'lu: yeni eklenen segment katlanmis bulunur
        con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'body','Sayfa 2','ıssız sokak')", (fid,))
        con.commit()
        assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"issiz\"'").fetchone()[0] == 1
        con.execute("INSERT INTO docs_fts(docs_fts) VALUES('integrity-check')")
    finally:
        con.close()


def test_second_launch_wakes_hidden_window():
    from concurrent.futures import ThreadPoolExecutor
    from PySide6.QtWidgets import QApplication
    from evrakci.app import _serve_activation, _wake_existing

    app = QApplication.instance() or QApplication([])

    class Window:
        calls = 0

        def _bring_forward(self):
            self.calls += 1

    window = Window()
    app._main_window = window
    server = _serve_activation(app, "Evrakci-Test-" + uuid.uuid4().hex)
    assert server is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_wake_existing, server.serverName())
            deadline = time.monotonic() + 4
            while not future.done() or window.calls == 0:
                app.processEvents()
                time.sleep(.01)
                assert time.monotonic() < deadline
            assert (future.result(), window.calls) == (True, 1)
    finally:
        server.close()
        del app._main_window
