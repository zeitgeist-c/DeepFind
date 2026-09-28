# Sürüm tek kaynaktan; kullanıcıya teslim edilen ad Evrakçı-X.Y.Z.
from pathlib import Path
import os
import hashlib
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo,
                                               StringTable, StringStruct, VarFileInfo, VarStruct)

root = Path(SPECPATH).parent
ocr_runtime = Path(os.environ.get("EVRAKCI_BUILD_TESSERACT", "C:/Program Files/Tesseract-OCR"))
ocr_exe = ocr_runtime / "tesseract.exe"
if not ocr_exe.is_file() or hashlib.sha256(ocr_exe.read_bytes()).hexdigest() != "babb405f4366b480d02cd8ff2bac8d497170f6c1711ce6f3d5d8bf0fb7fa6ed9":
    raise RuntimeError("Pinli Tesseract v5.4.0.20240606 motoru bulunamadı")
ocr_files = [ocr_exe, *sorted(ocr_runtime.glob("*.dll"))]
ocr_license = ocr_runtime / "doc" / "LICENSE"
if not ocr_license.is_file():
    raise RuntimeError("Tesseract lisans metni bulunamadı")
version_values = {}
exec((root / "src/evrakci/version.py").read_text(encoding="utf-8"), version_values)
stem = "Evrakçı-" + version_values["__version__"]
binaries = collect_dynamic_libs("pypdfium2") + collect_dynamic_libs("sqlcipher3")
numbers = tuple(int(x) for x in version_values["__version__"].split(".")) + (0,)
metadata = VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f,
                                         flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
    kids=[StringFileInfo([StringTable("041f04b0", [StringStruct("ProductName", "Evrakçı"),
          StringStruct("FileVersion", version_values["__version__"]),
          StringStruct("ProductVersion", version_values["__version__"]),
          StringStruct("OriginalFilename", stem + ".exe")])]),
          VarFileInfo([VarStruct("Translation", [1055,1200])])])
a = Analysis([str(root / "src/evrakci/__main__.py")], pathex=[str(root / "src")],
             binaries=binaries, datas=[(str(root / "src/evrakci/assets"), "evrakci/assets"),
                                       *[(str(path), "evrakci/ocr_runtime") for path in ocr_files],
                                       (str(ocr_license), "evrakci/ocr_runtime/doc")], hiddenimports=["PySide6.QtWidgets"],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
# Qt'nin Windows ICU bağımlılığı PATH'teki Poppler ICU ile aynı dosya adını taşır.
# Bu wheel Windows'un ICU API'sini kullanır; yabancı icuuc.dll onu gölgelememeli.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {"icuuc.dll", "icuin.dll", "icudt78.dll"}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=stem, console=False,
          debug=False, strip=False, upx=False, version=metadata,
          icon=str(root / "build/evrakci.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name=stem, strip=False, upx=False)
