from types import SimpleNamespace

from deepfind import app, update


def test_downloaded_installer_is_handed_off_with_recovery(tmp_path, monkeypatch):
    setup = tmp_path / "DeepFind-0.10.14.exe"
    setup.touch()
    recovery = (tmp_path / "DeepFind-0.10.13.exe", "0" * 64)
    monkeypatch.setattr(update, "prepare", lambda *args, **kwargs: setup)
    # Require that the real worker dependency exists before substituting I/O.
    monkeypatch.setattr(update, "prepare_recovery", lambda *args, **kwargs: recovery)
    worker = app.GuncellemeIsci("indir", info=SimpleNamespace(version="0.10.14"))
    handoffs = []
    errors = []
    worker.hazir.connect(lambda *args: handoffs.append(args))
    worker.hata.connect(errors.append)

    worker.kos()

    assert errors == []
    assert handoffs == [("0.10.14", str(setup), recovery)]
