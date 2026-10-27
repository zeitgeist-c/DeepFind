"""The rename must not cost the user their vault, credentials or settings.

Each test builds the pre-rename layout, then asserts the new code finds it.
"""

import os
import shutil

import pytest

from deepfind import identity, migration, paths

BYTES = b"SQLite format 3\x00not-a-real-vault"


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return tmp_path


def _old_layout(root):
    legacy = root / "Evrakci"
    (legacy / "Data").mkdir(parents=True)
    (legacy / "Data" / "evrakci.db").write_bytes(BYTES)
    (legacy / "Credentials").mkdir()
    (legacy / "Credentials" / "user.bin").write_bytes(b"dpapi-blob")
    (legacy / "Engines" / "b11765-cuda12").mkdir(parents=True)
    (legacy / "Logs").mkdir()
    (legacy / "Logs" / "lifecycle.log").write_text("old log", encoding="utf-8")
    return legacy


def test_folder_moves_and_content_survives(sandbox):
    legacy = _old_layout(sandbox)

    root = paths.data_root()

    assert root == sandbox / "DeepFind"
    assert root.is_dir()
    assert not legacy.exists()
    assert (root / "Credentials" / "user.bin").read_bytes() == b"dpapi-blob"
    assert (root / "Engines" / "b11765-cuda12").is_dir()
    assert (root / "Logs" / "lifecycle.log").read_text(encoding="utf-8") == "old log"


def test_vault_filename_migrates_without_touching_bytes(sandbox):
    _old_layout(sandbox)
    paths.data_root()                      # performs the folder move

    message = migration.migrate_vault_filename()

    assert message is not None
    assert paths.vault_db().exists()
    assert not paths.legacy_vault_db().exists()
    assert paths.vault_db().read_bytes() == BYTES


def test_migrations_are_idempotent(sandbox):
    _old_layout(sandbox)
    paths.data_root()
    assert migration.migrate_vault_filename() is not None

    assert migration.migrate_vault_filename() is None      # second call is a no-op
    assert paths.vault_db().read_bytes() == BYTES


def test_existing_new_folder_wins(sandbox):
    """If both folders exist the new one is authoritative; nothing is merged."""
    _old_layout(sandbox)
    new = sandbox / "DeepFind"
    new.mkdir()
    (new / "Data").mkdir()
    (new / "Data" / "deepfind.db").write_bytes(b"new-vault")

    assert paths.data_root() == new
    assert (new / "Data" / "deepfind.db").read_bytes() == b"new-vault"
    assert (sandbox / "Evrakci").exists()        # left alone, not deleted


def test_fresh_install_creates_nothing_eagerly(sandbox):
    root = paths.data_root()

    assert root == sandbox / "DeepFind"
    assert not root.exists(), "data_root() must not create the folder just by looking"


def test_locked_legacy_folder_is_reported_not_lost(sandbox, monkeypatch, capsys):
    """A failed move must leave the old folder usable and say so."""
    legacy = _old_layout(sandbox)

    def boom(*_a, **_k):
        raise OSError("file in use")

    monkeypatch.setattr(shutil, "move", boom)
    root = paths.data_root()

    assert root == legacy               # caller keeps working on the old path
    assert legacy.exists()
    assert (legacy / "Data" / "evrakci.db").exists()
    assert "could not move" in capsys.readouterr().err


def test_migrate_all_never_raises(sandbox, monkeypatch):
    monkeypatch.setattr(identity, "migrate_qsettings",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(identity, "migrate_autostart", lambda: "renamed")

    assert identity.migrate_all() == ["renamed"]
