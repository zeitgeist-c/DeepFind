"""Teslim ZIP'ini açıp içindeki gerçek EXE ile sentetik kabul akışını çalıştırır."""
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evrakci.version import __version__


def main():
    stem = "Evrakçı-" + __version__
    archive = ROOT / (stem + ".zip")
    with tempfile.TemporaryDirectory(prefix="evrakci-package-check-") as directory:
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            z.extractall(directory)
        package = Path(directory) / stem
        exe = package / (stem + ".exe")
        assert exe.is_file()
        assert stem + ".exe" in (package / (stem + ".bat")).read_text(encoding="utf-8")
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["version"] == __version__ and manifest["program"] == "Evrakçı"
        assert len(list((package / "_internal" / "evrakci" / "assets").glob("*.svg"))) == 4
        report = Path(directory) / "smoke.json"
        # Duman 60 sn'yi asar: 216 MB soguk acilis + transformers/ORT + model isinma
        # olculdu (~85 sn bu makinede). Esik olcume bagli; davranis degistirmez.
        process = subprocess.run([str(exe), "--package-smoke", str(report)], cwd=package,
                                 timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
        smoke = json.loads(report.read_text(encoding="utf-8"))
        assert process.returncode == 0 and smoke["ok"], smoke
        assert "actual-first-run-to-main-and-scan" in smoke["checks"]
        assert "vektor-model-durumu" in smoke["checks"]
        result = dict(smoke, package=str(archive), size=archive.stat().st_size,
                      sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), zip_crc=True)
        output = ROOT / "build" / ("package-check-" + __version__ + ".json")
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
