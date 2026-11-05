"""Sifresiz kasa testleri: yeni profil, eski sifreli donusum, CLI.

Sifre/isaret/kilit/kurtarma ozellikleri kaldirildi. Eski sifreli kasa
`vault_convert` ile tek yonlu donusur; yanlis parola veya bozuk kaynakta
eski kasa korunur.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deepfind import backup, migrate, schema, vault, vault_convert  # noqa: E402


def _yeni_kasa(tmp_path, ad="k.db"):
    db = str(tmp_path / ad)
    con = vault.open_vault(db)
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    con.close()
    return db


def _eski_kasa(tmp_path, ad="eski.db", pw="eski-parola-12345678"):
    """Gercekci eski kasa: tam sema + ornek icerik, sonra sqlcipher ile sifrele."""
    import sqlcipher3
    duz = str(tmp_path / (ad + ".duz.db"))
    from deepfind import embed as _embed
    con = vault.open_vault(duz)
    schema.ensure_schema(con)
    migrate.ensure_current(con)
    con.execute("INSERT INTO files(path,name,ext,source_status,index_status) VALUES (?,?,?, 'ok','indexed')",
                ("/x/ahmet.txt", "ahmet.txt", ".txt"))
    fid = con.execute("SELECT file_id FROM files").fetchone()[0]
    con.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) VALUES (?,?,?,?,?)",
                (fid, "body", 1, "g\u00f6vde", "VEK\u00c2LETNAME Ahmet \u00d6z"))
    sid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute("INSERT INTO embeddings(seg_id,model_ver,dim,vec) VALUES (?,?,?,?)",
                (sid, _embed.MODEL_VER, _embed.DIM, b"\x00" * (_embed.DIM * 4)))
    con.commit()
    con.close()
    db = str(tmp_path / ad)
    ham = sqlcipher3.connect(duz)
    try:
        ham.execute("ATTACH DATABASE '" + db.replace("'", "''") + "' AS enc KEY '" + pw.replace("'", "''") + "'")
        ham.execute("SELECT sqlcipher_export('enc')")
        ham.execute("DETACH DATABASE enc")
    finally:
        ham.close()
    os.remove(duz)
    return db


def test_yeni_profil_parolasiz_acilir(tmp_path):
    db = _yeni_kasa(tmp_path)
    assert vault.is_encrypted(db) is False
    assert vault.sifresiz_mi(db) is True
    con = vault.open_vault(db)
    assert con.execute("SELECT count(*) FROM files").fetchone()[0] == 0
    con.close()


def test_eski_kasa_parolasiz_acilmaz(tmp_path):
    eski = _eski_kasa(tmp_path)
    assert vault.is_encrypted(eski) is True
    assert vault.sifresiz_mi(eski) is False
    with pytest.raises(vault.EncryptedVaultError):
        vault.open_vault(eski)


def test_yanlis_parola_eskisini_korur(tmp_path):
    eski = _eski_kasa(tmp_path)
    with pytest.raises(ValueError):
        vault_convert.convert(eski, "yanlis-parola-0000")
    assert vault.is_encrypted(eski) is True


def test_donusum_icerigi_korur(tmp_path):
    eski = _eski_kasa(tmp_path)
    rapor = vault_convert.convert(eski, "eski-parola-12345678",
                                  dest=str(tmp_path / "yeni.db"))
    assert rapor["eski"]["files"] == rapor["yeni"]["files"] == 1
    assert rapor["yeni"]["integrity"] is True
    con = vault.open_vault(str(tmp_path / "yeni.db"))
    try:
        assert con.execute("SELECT raw_text FROM segments").fetchone()[0] == "VEKÂLETNAME Ahmet Öz"
        from deepfind import embed as _embed2
        assert len(bytes(con.execute("SELECT vec FROM embeddings").fetchone()[0])) == _embed2.DIM * 4
    finally:
        con.close()
    assert vault.is_encrypted(eski) is True


def test_donusmus_kasa_yeniden_acilista_sormaz(tmp_path):
    eski = _eski_kasa(tmp_path)
    yeni = str(tmp_path / "yeni.db")
    vault_convert.convert(eski, "eski-parola-12345678", dest=yeni)
    con = vault.open_vault(yeni)
    migrate.ensure_current(con)
    con.close()
    assert vault.sifresiz_mi(yeni) is True


def test_eski_yedek_parolayla_okunur(tmp_path):
    eski = _eski_kasa(tmp_path)
    assert backup.verify_backup(eski)["ok"] is False
    assert backup.verify_backup(eski, "yanlis")["ok"] is False
    assert vault_convert.verify_encrypted(eski, "eski-parola-12345678")["ok"] is True


def test_cli_donustur_ve_tani(tmp_path, capsys, monkeypatch):
    from deepfind import cli as _cli
    eski = _eski_kasa(tmp_path, ad="k.db")
    monkeypatch.setattr("getpass.getpass", lambda *_a, **_k: "eski-parola-12345678")
    assert _cli.main(["--kasa", eski, "kasa-donustur"]) == 0
    assert vault.is_encrypted(eski) is False
    assert _cli.main(["--kasa", eski, "kasa-donustur"]) == 0
    out = capsys.readouterr().out
    assert "gerekmedi" in out
