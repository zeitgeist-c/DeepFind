"""Güvenlik regresyonları: yayın sürümüyle dizin kaçışı ve CSV formül enjeksiyonu."""
import sqlite3

import pytest

from evrakci import rank, update


def _payload(tag, name):
    return {
        "tag_name": tag,
        "html_url": "https://example.invalid/x",
        "assets": [{
            "name": name,
            "browser_download_url": "https://example.invalid/a.exe",
            "size": 10,
            "digest": "sha256:" + "a" * 64,
        }],
    }


@pytest.mark.parametrize("tag", [
    "v0.11.0/../../../evil",
    "v0.11.0\\..\\..\\evil",
    "v1.2.3 ",
    "v..",
])
def test_yayin_surumu_yol_tasimaz(tag):
    with pytest.raises(update.UpdateError):
        update.parse_release(_payload(tag, "Evrakci-0.11.0.exe"))


def test_gecerli_surum_kabul_edilir():
    info = update.parse_release(_payload("v0.11.0", "Evrakci-0.11.0.exe"))
    assert info.version == "0.11.0"
    assert "/" not in info.version and "\\" not in info.version


@pytest.fixture()
def con():
    baglanti = sqlite3.connect(":memory:")
    baglanti.execute("CREATE TABLE file_tags(file_id INTEGER, tag TEXT)")
    yield baglanti
    baglanti.close()


@pytest.mark.parametrize("ad", [
    '=HYPERLINK("http://x","tikla").pdf',
    "+cmd|calc.pdf",
    "-2+3.pdf",
    "@SUM(1).pdf",
    "\tsekmeli.pdf",
])
def test_csv_hucreleri_formul_olarak_baslamaz(con, ad):
    out = rank.results_csv(con, [dict(name=ad, path="C:/a/b.pdf", ext=".pdf",
                                      file_id=1)])
    satir = out.splitlines()[1]
    # Alan tırnaklanmış olsa da gerçek değer tek tırnakla başlamalı.
    assert "'" in satir.split(",")[0]


def test_csv_normal_adlar_degismez(con):
    out = rank.results_csv(con, [dict(name="fatura.pdf", path="C:/a/fatura.pdf",
                                      ext=".pdf", file_id=1)])
    assert out.splitlines()[1].startswith("fatura.pdf,")
