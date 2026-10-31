"""A7 testleri: sifreli yedek/restore, parola, kilit, migration saglamligi."""
from semantic_helpers import indexed_content
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import backup, coordinator, exclusions, schema, vault  # noqa: E402
from deepfind.migrate import ensure_v4, ensure_v6  # noqa: E402
from deepfind.migrate import ensure_v5  # noqa: E402

PW = "yedek-sifresi-1234"


def _kasa(tmp_path, pw=PW):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, pw)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v5(con)
    ensure_v6(con)
    return con, db


def _pdf(kok, ad, metin):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 13)
    c.drawString(72, 750, metin)
    c.save()
    return p


def test_bak01_yedek_restore_tutarli(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara yedek testi 2024")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    assert indexed_content(con, "yedek")
    yb = str(tmp_path / "backups")
    y = backup.create_backup(con, db, PW, yb, forbid_under=[kok])
    assert os.path.isfile(y) and os.path.isfile(y + ".json")
    v = backup.verify_backup(y, PW)
    assert v["ok"] and v["counts"]["files"] == 1, v
    # kasayi boz: icerigi sil
    con.execute("DELETE FROM segments")
    con.commit()
    assert indexed_content(con, "yedek") == []
    con.close()
    # geri yukle (baglantilar kapali)
    rap = backup.restore_replace(db, PW, y, str(tmp_path / "staging"))
    assert rap["kasa_counts"]["files"] == 1, rap
    con = vault.open_vault(db, PW)
    assert indexed_content(con, "yedek"), "restore sonrasi arama calismali"
    con.close()


def test_bak02_yanlis_sifre_bozuk_yedek_kasayi_ezemez(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara koruma testi")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    y = backup.create_backup(con, db, PW, str(tmp_path / "backups"))
    con.close()
    with pytest.raises(Exception):
        backup.verify_backup(y, "yanlis-sifre-0000")
    sahte = str(tmp_path / "sahte.db")
    with open(sahte, "wb") as f:
        f.write(os.urandom(2048))
    with pytest.raises(Exception):
        backup.restore_replace(db, PW, sahte, str(tmp_path / "staging"))
    con = vault.open_vault(db, PW)
    assert indexed_content(con, "koruma"), "mevcut kasa bozulmamis olmali"
    con.close()


def test_bak02_yedek_sifreli_plaintext_yok(tmp_path):
    con, db = _kasa(tmp_path)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('gizli-yol/belge.pdf','belge.pdf','.pdf')")
    con.commit()
    y = backup.create_backup(con, db, PW, str(tmp_path / "backups"))
    con.close()
    ham = open(y, "rb").read()
    assert b"gizli-yol" not in ham, "sifreli yedekte acik metin sizdi"


def test_bak03_eski_yedek_harici_geri_acamaz(tmp_path):
    kok = str(tmp_path / "arsiv")
    alt = os.path.join(kok, "gizli")
    os.makedirs(alt)
    _pdf(kok, "acik.pdf", "acik belge Ankara")
    _pdf(alt, "sakli.pdf", "sakli belge Ankara")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    y_eski = backup.create_backup(con, db, PW, str(tmp_path / "backups"))
    # sonra: gizli klasor haric + purge
    exclusions.add(con, alt)
    exclusions.purge_rule(con, alt)
    assert indexed_content(con, "sakli") == []
    con.close()
    # eski yedegi geri yukle -> haric kural korunur, icerik donmez
    rap = backup.restore_replace(db, PW, y_eski, str(tmp_path / "staging"))
    assert alt in rap["korunan_kurallar"] or any(alt in k for k in rap["korunan_kurallar"]), rap
    con = vault.open_vault(db, PW)
    assert indexed_content(con, "sakli") == [], "haric icerik aktif aramaya donmemeli"
    assert indexed_content(con, "acik"), "haric disi icerik durmali"
    con.close()


def test_bak_hedef_kaynak_altinda_yasak(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    con, db = _kasa(tmp_path)
    with pytest.raises(ValueError):
        backup.create_backup(con, db, PW, os.path.join(kok, "backups"), forbid_under=[kok])
    con.close()


def test_bak_saklama_otomatik7_manuel_korunur(tmp_path):
    yb = str(tmp_path / "backups")
    os.makedirs(yb)
    for i in range(9):
        open(os.path.join(yb, f"deepfind-indeks-2026010{i}-000000.db"), "wb").close()
    open(os.path.join(yb, "deepfind-indeks-manuel-eski.db"), "wb").close()
    gone = backup.prune(None, yb)
    assert len(gone) == 2, gone
    kalan = [b["path"] for b in backup.list_backups(yb)]
    assert any("manuel" in k for k in kalan)
    assert len([k for k in kalan if "manuel" not in k]) == 7


def test_parola_degisimi_tirnakli_sifre(tmp_path):
    con, db = _kasa(tmp_path)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('a.pdf','a.pdf','.pdf')")
    con.commit()
    con.close()
    yeni = "yeni'sifre-\"karmasik\"-1234"
    rap = backup.change_password(db, PW, yeni, str(tmp_path / "backups"))
    assert os.path.isfile(rap["yedek"])
    con = vault.open_vault(db, yeni)
    assert con.execute("SELECT count(*) FROM files").fetchone()[0] == 1
    con.close()
    with pytest.raises(Exception):
        vault.open_vault(db, PW)


def test_mig01_yarim_migration_tamamlanir(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    # cokmede yarim kalmis v6 gibi: yalniz method sutunu var, surum eski
    con.execute("ALTER TABLE segments ADD COLUMN method TEXT DEFAULT ''")
    con.execute("UPDATE schema_meta SET v='4' WHERE k='schema_version'")
    con.commit()
    ensure_v6(con)  # idempotent tamamlar
    cols = [r[1] for r in con.execute("PRAGMA table_info(segments)").fetchall()]
    assert "rev_id" in cols and "method" in cols and "confidence" in cols
    assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0] == "6"
    con.close()


def test_sec03_kilit_baglanti_kapatir(tmp_path):
    con, db = _kasa(tmp_path)
    assert vault.lock(con, os.path.dirname(db)) is True
    with pytest.raises(Exception):
        con.execute("SELECT 1").fetchall()
    con2 = vault.open_vault(db, PW)  # yeniden acilabilir
    assert con2.execute("SELECT 1").fetchone()[0] == 1
    con2.close()


def _anlik(kok):
    out = {}
    for dp, _dn, fn in os.walk(kok):
        for f in fn:
            p = os.path.join(dp, f)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def test_bak_kaynaga_dokunmaz(tmp_path):
    """SAF-01 (runtime): yedek/restore/prune/parola cevrimi kaynaga yazmaz."""
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara dokunulmazlik 2024")
    time.sleep(2.5)
    once = _anlik(kok)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok, require_vectors=False)
    yb = str(tmp_path / "backups")
    y = backup.create_backup(con, db, PW, yb, forbid_under=[kok])
    backup.prune(None, yb)
    con.close()
    backup.restore_replace(db, PW, y, str(tmp_path / "staging"))
    backup.change_password(db, PW, "yeni-parola-12345", yb)
    backup.change_password(db, "yeni-parola-12345", PW, yb)
    assert _anlik(kok) == once, "yedek/restore kaynaga yazdi!"


def test_cli_yedek_tani_parola(tmp_path, capsys):
    """CLI: yedek-al/listele/tani/parola-degistir/geri-yukle uctan uca."""
    from deepfind import cli as _cli
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara cli yedek 2024")
    time.sleep(2.5)
    db = str(tmp_path / "k.db")
    yb = str(tmp_path / "backups")
    st = str(tmp_path / "staging")
    assert _cli.main(["--kasa", db, "--sifre", PW, "init"]) == 0
    assert _cli.main(["--kasa", db, "--sifre", PW, "tara", kok]) == 0
    assert _cli.main(["--kasa", db, "--sifre", PW, "yedek-al",
                      "--hedef", yb, "--kok", kok, "--manuel"]) == 0
    assert _cli.main(["--kasa", db, "--sifre", PW, "yedek-liste",
                      "--hedef", yb]) == 0
    out = capsys.readouterr().out
    assert "manuel" in out
    assert _cli.main(["--kasa", db, "--sifre", PW, "tani"]) == 0
    out = capsys.readouterr().out
    assert "DeepFind " in out and "belge=1" in out and "sifre" not in out.lower().replace(
        "kasa sifresi", "")
    yedekler = backup.list_backups(yb)
    assert len(yedekler) == 1
    assert _cli.main(["--kasa", db, "--sifre", PW, "geri-yukle",
                      yedekler[0]["path"], "--staging", st]) == 0
    assert _cli.main(["--kasa", db, "--sifre", PW, "parola-degistir",
                      "cli-yeni-parola-1", "--hedef", yb]) == 0
    assert _cli.main(["--kasa", db, "--sifre", "cli-yeni-parola-1", "tani"]) == 0
    out = capsys.readouterr().out
    assert "belge=1" in out
