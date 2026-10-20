"""Sürüm, EXE/BAT/ZIP ve bağımlılık lisanslarını birlikte üretir."""
from pathlib import Path
import importlib.metadata
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from evrakci.version import __version__


def main():
    import re
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    stem = f"Evrakçı-{__version__}"
    if "--archive-only" not in sys.argv:
        import os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from evrakci.theme import app_icon
        from PIL import Image
        app = QApplication.instance() or QApplication([])
        (ROOT / "build").mkdir(exist_ok=True)
        png = ROOT / "build/evrakci.png"
        app_icon().pixmap(64,64).save(str(png))
        Image.open(png).save(ROOT / "build/evrakci.ico")
        build_env = os.environ.copy()
        windows = Path(os.environ["SystemRoot"])
        # Başka programların PATH DLL'leri dağıtıma sızmamalı (Poppler ICU vb.).
        build_env["PATH"] = os.pathsep.join(map(str, [Path(sys.executable).parent,
            Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
            windows / "System32", windows]))
        work = ROOT / "build" / ("pyinstaller-" + uuid.uuid4().hex)
        build_env["PYINSTALLER_CONFIG_DIR"] = str(work / "cache")
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--workpath", str(work),
                        "--distpath", str(work / "dist"),
                        str(ROOT / "packaging/Evrakci.spec")], cwd=ROOT, env=build_env, check=True)
        package_target = ROOT / "dist" / stem
        if package_target.exists():
            package_target.rename(work / ("previous-" + stem))
        package_target.parent.mkdir(exist_ok=True)
        shutil.move(str(work / "dist" / stem), str(package_target))
    package = ROOT / "dist" / stem
    assert (package / (stem + ".exe")).is_file()
    (package / (stem + ".bat")).write_text(
        f'@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\nstart "" "%~dp0{stem}.exe" %*\n',
        encoding="utf-8")
    licenses = package / "licenses"
    licenses.mkdir(exist_ok=True)
    deps = ["sqlcipher3", "pypdfium2", "openpyxl", "xlrd", "python-docx", "defusedxml",
            "rapidfuzz", "pillow", "pyside6-essentials", "shiboken6",
            "rapidocr", "onnxruntime-directml", "opencv-python-headless", "numpy", "pyclipper",
            "transformers", "tokenizers", "huggingface-hub", "hf-xet", "safetensors",
            "regex", "filelock",
            "shapely", "omegaconf", "pyyaml", "six", "requests", "tqdm", "colorlog",
            "protobuf", "flatbuffers", "idna", "certifi", "urllib3", "charset-normalizer"]
    manifest = {"program": "Evrakçı", "version": __version__, "dependencies": {}}
    for name in deps:
        dist = importlib.metadata.distribution(name)
        manifest["dependencies"][name] = dist.version
        for file in dist.files or []:
            parts = str(file).lower()
            if any(word in parts for word in ("license", "licence", "copying", "notice")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    safe_parts = [p for p in Path(str(file)).parts if p not in ("..", ".")]
                    target = licenses / name / Path(*safe_parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    # Kurulu Qt dağıtımında LGPL metni bulunmuyorsa önceki doğrulanmış metni kullan.
    lgpl = ROOT / "packaging/licenses/LGPL-3.0-only.txt"
    if lgpl.is_file():
        shutil.copyfile(lgpl, licenses / "LGPL-3.0-only.txt")
    if not (licenses / "LGPL-3.0-only.txt").is_file():
        raise RuntimeError("LGPL lisans metni bulunamadı; paket teslim edilemez")
    # RapidOCR motoru pakettir: model + config verileri _internal/rapidocr altında olmalı.
    model_root = package / "_internal" / "rapidocr" / "models"
    if not any(model_root.glob("*.onnx")):
        raise RuntimeError("RapidOCR ONNX modelleri pakette bulunamadı")
    # Paket dumanı: kurulu EXE gerçekten açılıp OCR zincirini çalıştırabiliyor mu?
    import tempfile
    smoke_report = Path(tempfile.gettempdir()) / f"evrakci-smoke-{__version__}.json"
    if smoke_report.exists():
        smoke_report.unlink()
    proc = subprocess.run([str(package / (stem + ".exe")), "--package-smoke", str(smoke_report)],
                          capture_output=True, text=True, timeout=900)
    try:
        rapor = json.loads(smoke_report.read_text(encoding="utf-8"))
    except Exception:
        rapor = {"ok": False, "stage": f"rapor-okunamadi exit={proc.returncode}"}
    if proc.returncode != 0 or not rapor.get("ok"):
        raise RuntimeError(f"paket dumanı başarısız: {rapor} | {(proc.stderr or '')[-500:]}")
    for name in ("README.md", "LISANSLAR.md", f"DENETIM-{__version__}.md"):
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, package / name)
    (package / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    destination = ROOT / (stem + ".zip")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package.parent))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    print(json.dumps({"package": str(destination), "sha256": digest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
