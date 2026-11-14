"""Build the release, EXE/BAT/ZIP and dependency licenses together."""
from pathlib import Path
import importlib.metadata
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from deepfind.version import __version__


def main():
    import re
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    stem = f"DeepFind-{__version__}"
    argv = sys.argv[1:]
    aday = None
    if "--aday" in argv:
        aday = Path(argv[argv.index("--aday") + 1])
        if not aday.is_absolute():
            aday = ROOT / aday
        aday.mkdir(parents=True, exist_ok=True)
    asama = None
    if "--asama" in argv:
        asama = argv[argv.index("--asama") + 1]
        assert asama in ("pyinstaller", "smoke", "iscc"), asama
    etkilesimli = "--etkilesimli" in argv
    if asama:
        asamalari = [asama]
    elif "--archive-only" in argv:
        asamalari = ["smoke", "iscc"]
    else:
        asamalari = ["pyinstaller", "smoke", "iscc"]
    if aday is not None:
        build(stem, aday, aday, asama, asamalari, etkilesimli)
    elif asama or "--archive-only" in argv:
        build(stem, ROOT / "build/package-work", None, asama, asamalari, etkilesimli)
    else:
        build_root = ROOT / "build"
        build_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="package-", dir=build_root) as folder:
            build(stem, Path(folder), None, asama, asamalari, etkilesimli)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def finish_release(artifacts, staging):
    import re

    checksum = staging / f"SHA256-{__version__}.txt"
    checksum.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
        encoding="utf-8",
    )
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    if release.is_symlink() or release.is_junction():
        raise RuntimeError(f"Release directory must be inside the project: {release}")

    managed = re.compile(r"(?:DeepFind-\d+\.\d+\.\d+\.(?:exe|zip|deepfind)|SHA256-\d+\.\d+\.\d+\.txt)")
    previous = [path for path in release.iterdir()
                if path.is_file() and not path.is_symlink() and managed.fullmatch(path.name)]
    installed = []
    backup = Path(tempfile.mkdtemp(prefix="previous-release-", dir=staging.parent))
    try:
        for path in previous:
            path.rename(backup / path.name)
        for path in (*artifacts, checksum):
            target = release / path.name
            if target.exists() or target.is_symlink():
                raise FileExistsError(target)
            path.rename(target)
            installed.append(target)
    except OSError:
        try:
            for target in reversed(installed):
                target.rename(staging / target.name)
            for path in backup.iterdir():
                path.rename(release / path.name)
        except OSError as error:
            raise RuntimeError(f"Release recovery required. Previous files: {backup}") from error
        backup.rmdir()
        raise
    result = {"release": str(release), "version": __version__,
              "files": [path.name for path in (*artifacts, checksum)]}
    # Keep a unique prior artifact until its backup can be verified.
    for path in backup.iterdir():
        replacement = release / path.name
        if replacement.is_file() and sha256(replacement) == sha256(path):
            path.unlink()
    if any(backup.iterdir()):
        result["previous_artifacts"] = str(backup)
    else:
        backup.rmdir()
    print(json.dumps(result))


def build(stem, cikti, aday, asama, asamalari, etkilesimli):
    cikti.mkdir(parents=True, exist_ok=True)
    if "pyinstaller" in asamalari:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from deepfind.theme import app_icon
        from PIL import Image
        app = QApplication.instance() or QApplication([])
        (ROOT / "build").mkdir(exist_ok=True)
        png = ROOT / "build/deepfind.png"
        app_icon().pixmap(64,64).save(str(png))
        Image.open(png).save(ROOT / "build/deepfind.ico")
        build_env = os.environ.copy()
        windows = Path(os.environ["SystemRoot"])
        # Other programs' PATH DLLs must not leak into the bundle (Poppler ICU etc.).
        build_env["PATH"] = os.pathsep.join(map(str, [Path(sys.executable).parent,
            Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
            windows / "System32", windows]))
        work = cikti / ("pyinstaller-" + uuid.uuid4().hex)
        build_env["PYINSTALLER_CONFIG_DIR"] = str(work / "cache")
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--workpath", str(work),
                        "--distpath", str(work / "dist"),
                        str(ROOT / "packaging/DeepFind.spec")], cwd=ROOT, env=build_env, check=True)
        package_target = cikti / stem
        if package_target.exists():
            # Yeniden denemeli tasi: yeni cikan ikililerde virus tarayici /
            # esitleme kilidi kisa sure tutabilir (WinError 5).
            for _deneme in range(12):
                try:
                    package_target.rename(work / ("previous-" + stem))
                    break
                except PermissionError:
                    if _deneme == 11:
                        raise
                    time.sleep(5)
        package_target.parent.mkdir(exist_ok=True)
        shutil.move(str(work / "dist" / stem), str(package_target))
        print(json.dumps({"pyinstaller": str(package_target)}, ensure_ascii=False))
    if asama == "pyinstaller":
        return
    package = cikti / stem
    assert (package / (stem + ".exe")).is_file()
    (package / (stem + ".bat")).write_text(
        f'@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\nstart "" "%~dp0{stem}.exe" %*\n',
        encoding="utf-8")
    licenses = package / "licenses"
    licenses.mkdir(exist_ok=True)
    deps = ["pypdfium2", "openpyxl", "xlrd", "python-docx", "defusedxml",
            "pillow", "pyside6-essentials", "shiboken6",
            "rapidocr", "onnxruntime-directml", "opencv-python-headless", "numpy", "pyclipper",
            "shapely", "omegaconf", "pyyaml", "six", "requests", "tqdm", "colorlog",
            "protobuf", "flatbuffers", "idna", "certifi", "urllib3", "charset-normalizer"]
    manifest = {"program": "DeepFind", "version": __version__, "dependencies": {},
                "source_commit":subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                "source_dirty":bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip())}
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
    # When the installed Qt bundle lacks the LGPL text, reuse the previously verified text.
    lgpl = ROOT / "packaging/licenses/LGPL-3.0-only.txt"
    if lgpl.is_file():
        shutil.copyfile(lgpl, licenses / "LGPL-3.0-only.txt")
    if not (licenses / "LGPL-3.0-only.txt").is_file():
        raise RuntimeError("LGPL lisans metni bulunamadı; paket teslim edilemez")
    from deepfind.model_indir import gerekli_mi
    if gerekli_mi(str(package / '_internal/embedding/embeddinggemma-2-Q8_0.gguf')):
        raise RuntimeError('GGUF model pakette eksik veya özeti geçersiz')
    shutil.copyfile(ROOT / 'build/embedding/manifest.json', licenses / 'embedding-manifest.json')
    # RapidOCR engine is packaged: model + config data must sit under _internal/rapidocr.
    model_root = package / "_internal" / "rapidocr" / "models"
    if not any(model_root.glob("*.onnx")):
        raise RuntimeError("RapidOCR ONNX modelleri pakette bulunamadı")
    # Package smoke: does the installed EXE really open and run the OCR chain?
    if "smoke" in asamalari:
        import tempfile
        smoke_report = Path(tempfile.gettempdir()) / f"deepfind-smoke-{__version__}.json"
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
    for name in ("README.md", "LICENSE"):
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, package / name)
    (package / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    destination = cikti / (stem + ".zip")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package.parent))
    digest = sha256(destination)
    print(json.dumps({"package": str(destination), "sha256": digest}, ensure_ascii=False))
    if "iscc" in asamalari:
        # Kurulum (Inno Setup): taze kurulumlar icin tek EXE.
        iscc = os.environ.get("INNO_ISCC", r"C:\tmp\Inno\ISCC.exe")
        if not Path(iscc).is_file():
            for yol in (r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                        r"C:\Program Files\Inno Setup 6\ISCC.exe",
                        r"C:\Users\mahmu\AppData\Local\Programs\Inno Setup 6\ISCC.exe"):
                if Path(yol).is_file():
                    iscc = yol
                    break
        if aday:
            # Sürüm damgası her Inno derlemesinde tazelenir; yoksa önceki
            # üretim/bayat ver.iss aday kurulum adını bozar.
            (ROOT / "packaging" / "ver.iss").write_text(
                f'#define AppVersion "{__version__}"\n', encoding="utf-8")
            # Yerel aday: yayim dosyalarina dokunulmaz; test AppId ile
            # build/test-installer altina kurulur, ayni taze aday paketlenir.
            # --etkilesimli: TestRunAlways YOK (normal skipifsilent [Run]) ve ayri
            # cikti; etkilesimli kabulde kutucuk davranisi uretimle birebir olur.
            if etkilesimli:
                outdir = aday / "kurulum"
                outdir.mkdir(parents=True, exist_ok=True)
                kurulacak = [iscc, "/DTestInstall", f"/DAdayKaynak={package}",
                             "/O" + str(outdir),
                             str(ROOT / "packaging/DeepFind.iss")]
            else:
                kurulacak = [iscc, "/DTestInstall", "/DTestRunAlways",
                             f"/DAdayKaynak={package}",
                             str(ROOT / "packaging/DeepFind.iss")]
            subprocess.run(kurulacak, cwd=str(ROOT / "packaging"), check=True, timeout=600)
            kurulum = (aday / "kurulum" / (stem + ".exe")) if etkilesimli \
                else (ROOT / "build" / "test-installer" / (stem + ".exe"))
            assert kurulum.is_file(), "aday kurulum EXE uretilemedi"
            print(json.dumps({"aday_kurulum": str(kurulum),
                              "sha256": sha256(kurulum)},
                             ensure_ascii=False))
        else:
            (ROOT / "packaging" / "ver.iss").write_text(
                f'#define AppVersion "{__version__}"\n', encoding="utf-8")
            setup_dir = cikti / "installer"
            update_dir = cikti / "update-installer"
            setup_dir.mkdir(exist_ok=True)
            update_dir.mkdir(exist_ok=True)
            setup_script = str(ROOT / "packaging/DeepFind.iss")
            source_arg = f"/DAdayKaynak={package}"
            subprocess.run([iscc, source_arg, "/O" + str(setup_dir), setup_script],
                           cwd=str(ROOT / "packaging"), check=True, timeout=600)
            kurulum = setup_dir / (stem + ".exe")
            assert kurulum.is_file(), "kurulum EXE uretilemedi"
            print(json.dumps({"setup": str(kurulum),
                              "sha256": sha256(kurulum)},
                             ensure_ascii=False))
            subprocess.run([iscc, "/DUpdatePackage", source_arg, "/O" + str(update_dir), setup_script],
                           cwd=str(ROOT / 'packaging'), check=True, timeout=600)
            from deepfind.model_indir import MODEL_SHA256
            incremental = cikti / (stem + '.deepfind')
            with zipfile.ZipFile(incremental, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(update_dir / (stem + '.exe'), stem + '.exe')
                archive.writestr('manifest.json', json.dumps({'program':'DeepFind', 'version':__version__,
                                                             'model_sha256':MODEL_SHA256},ensure_ascii=False))
            print(json.dumps({'incremental':str(incremental), 'size':incremental.stat().st_size,
                              'sha256':sha256(incremental)},ensure_ascii=False))
            if asama != "iscc":
                finish_release((destination, kurulum, incremental), cikti)


if __name__ == "__main__":
    main()
