"""V2 AI retrieval and network boundary tests with a synthetic local index."""
import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import ai, index, migrate, schema
from evrakci.extract import ExtractResult, Segment
from evrakci.scan import Entry
from evrakci.vocab import ensure_v5


@pytest.fixture()
def indexed():
    con = sqlite3.connect(":memory:")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_v7(con)
    entry = Entry("C:/synthetic/ankara.pdf", "ankara.pdf", ".pdf", 100, 1)
    fid = index.index_entry(con, entry, ExtractResult([
        Segment("pdf_page", 1, "Sayfa 1", "Ankara denetim raporu 2024: gelir 12 milyon TL."),
        Segment("pdf_page", 2, "Sayfa 2", "Ankara denetim sonucunda gider 8 milyon TL.")]))
    yield con, fid
    con.close()


def test_question_previews_real_index_evidence_without_network(indexed, monkeypatch):
    con, _ = indexed
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Hazırlık ağ çağrısı yapmamalı")
    monkeypatch.setattr(ai, "request_body", forbidden)
    preview = ai.prepare_question(con, "Ankara denetim gelir")
    assert preview.sources and "12 milyon" in ai.preview_text(preview)
    assert all(source["path"].endswith("ankara.pdf") for source in preview.sources)
    assert ai.still_current(con, preview)
    con.execute("UPDATE segments SET raw_text='değişti' WHERE seg_id=?", (preview.sources[0]["seg_id"],))
    assert not ai.still_current(con, preview)


def test_summary_is_bounded_and_marks_partial(indexed):
    con, fid = indexed
    con.execute("UPDATE segments SET raw_text=? WHERE page=1", ("A" * 5000,))
    preview = ai.prepare_summary(con, fid)
    assert preview.truncated
    assert len(preview.sources[0]["text"]) <= ai.MAX_EXCERPT
    assert "yalnız yukarıdaki kesitler" in ai.preview_text(preview)


def test_response_accepts_only_preview_source_ids(indexed):
    con, _ = indexed
    preview = ai.prepare_question(con, "Ankara denetim")
    sid = preview.sources[0]["id"]
    response = lambda ids: json.dumps({"candidates": [{"content": {"parts": [{"text":
        json.dumps({"answer": "Gelir 12 milyon TL.", "source_ids": ids})}]}}]}).encode()
    answer, citations = ai.parse_response(response([sid]), preview)
    assert "12 milyon" in answer and citations[0]["id"] == sid
    with pytest.raises(ValueError, match="kaynak"):
        ai.parse_response(response(["S999999"]), preview)
    body = json.loads(ai.request_body(preview))
    assert "Ankara" in body["contents"][0]["parts"][0]["text"]
    assert body["generationConfig"]["responseFormat"]["text"]["schema"]["required"] == ["answer", "source_ids"]


def test_no_content_evidence_is_rejected(indexed):
    con, fid = indexed
    con.execute("DELETE FROM segments WHERE file_id=? AND kind='pdf_page'", (fid,))
    with pytest.raises(ValueError, match="içerik kanıtı"):
        ai.prepare_question(con, "Ankara denetim")
    with pytest.raises(ValueError, match="aranabilir içeriği"):
        ai.prepare_summary(con, fid)
