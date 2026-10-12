"""Etiket sistemi: kurallar, otomatik etiketleme, filtre, elle etiket."""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import coordinator as C
from evrakci import migrate, rank, schema
from evrakci.extract import ExtractResult, Segment
from evrakci.scan import Entry
from evrakci.vocab import ensure_v5


def database(path=None):
    con = sqlite3.connect(str(path) if path else ":memory:")
    schema.ensure_schema(con)
    ensure_v5(con)
    migrate.ensure_current(con)
    return con


def _yaz(con, path, metin):
    entry = Entry(path, os.path.basename(path), ".pdf", 100, 1)
    return C.ensure_file(con, entry), entry


def test_kural_any_all():
    con = database()
    try:
        rank.add_rule(con, "muhasebe", "fatura, makbuz", mode="any")
        rank.add_rule(con, "kira", "kira, sözleşme", mode="all")
        f1 = C.ensure_file(con, Entry("C:/a/belge.pdf", "belge.pdf", ".pdf", 100, 1))
        f2 = C.ensure_file(con, Entry("C:/a/kira-sozlesmesi.pdf", "kira-sozlesmesi.pdf", ".pdf", 100, 1))
        assert C.apply_tag_rules(con, f1, "belge.pdf", "kira faturası 2023") == {"muhasebe"}
        assert C.apply_tag_rules(con, f2, "kira-sozlesmesi.pdf", "kira sözleşmesi") == {"kira"}
    finally:
        con.close()


def test_yeni_tarama_otomatik_etiketler():
    con = database()
    try:
        rank.add_rule(con, "muhasebe", "fatura", mode="any")
        fid, entry = _yaz(con, "C:/a/fatura.pdf", "")
        sig = "100:1"
        C.write_revision(con, fid, sig,
                         ExtractResult([Segment("pdf_page", 1, "Sayfa 1", "kira faturası")]), "")
        assert "muhasebe" in rank.file_tags(con, fid)
    finally:
        con.close()


def test_etiket_filtresi_daraltir():
    con = database()
    try:
        f1, _ = _yaz(con, "C:/a/bir.pdf", "")
        f2, _ = _yaz(con, "C:/a/iki.pdf", "")
        C.write_revision(con, f1, "100:1", ExtractResult([Segment("pdf_page", 1, "S1", "ortak kelime alfa")]), "")
        C.write_revision(con, f2, "100:1", ExtractResult([Segment("pdf_page", 1, "S1", "ortak kelime beta")]), "")
        rank.set_tag(con, f1, "muhasebe")
        tum = rank.search_ranked(con, "ortak")
        assert len(tum["results"]) == 2
        dar = rank.search_ranked(con, "ortak", tag="muhasebe")
        assert [r["path"] for r in dar["results"]] == ["C:/a/bir.pdf"]
        assert rank.search_ranked(con, "ortak", tag="yok")["results"] == []
    finally:
        con.close()


def test_elle_etiket_yeniden_taramada_korunur():
    con = database()
    try:
        rank.add_rule(con, "oto", "fatura", mode="any")
        fid, _ = _yaz(con, "C:/a/f.pdf", "")
        C.write_revision(con, fid, "100:1", ExtractResult([Segment("pdf_page", 1, "S1", "fatura")]), "")
        rank.set_tag(con, fid, "elle")
        C.write_revision(con, fid, "100:2", ExtractResult([Segment("pdf_page", 1, "S1", "fatura v2")]), "")
        tags = rank.file_tags(con, fid)
        assert "elle" in tags and "oto" in tags
        rank.remove_tag(con, fid, "elle")
        assert "elle" not in rank.file_tags(con, fid)
    finally:
        con.close()
