# Sürüm tek kaynaktan; kullanıcıya teslim edilen ad Evrakçı-X.Y.Z.
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo,
                                               StringTable, StringStruct, VarFileInfo, VarStruct)

root = Path(SPECPATH).parent
version_values = {}
exec((root / "src/evrakci/version.py").read_text(encoding="utf-8"), version_values)
stem = "Evrakçı-" + version_values["__version__"]
# RapidOCR motoru: ONNX DLL'leri + paket içi model/config verileri pakete girer.
ocr_datas = [entry for entry in collect_data_files("rapidocr")
             if entry[0].endswith((".onnx", ".yaml"))]
binaries = (collect_dynamic_libs("pypdfium2") + collect_dynamic_libs("sqlcipher3")
            + collect_dynamic_libs("onnxruntime"))
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
                                       *ocr_datas,
                                       (str(root / 'build/embedding/embeddinggemma-2-Q8_0.gguf'), 'embedding'),
                                       (str(root / 'build/embedding/cpu'), 'embedding/cpu'),
                                       (str(root / 'build/embedding/vulkan'), 'embedding/vulkan'),
                                       (str(root / 'build/embedding/manifest.json'), 'embedding'),
                                       (str(root / 'build/embedding/llama-LICENSE.txt'), 'embedding'),
                                       (str(root / 'build/embedding/model-LICENSE.txt'), 'embedding')], hiddenimports=["PySide6.QtWidgets",
                                       *collect_submodules("rapidocr"),
                                       "onnxruntime.capi.onnxruntime_pybind11_state",
                                       ],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=["torch", "transformers", "tokenizers", "huggingface_hub", "hf_xet", "safetensors",
                       "onnxruntime.tools", "onnxruntime.quantization", "pytest", "IPython", "matplotlib"], noarchive=False)
# Qt'nin Windows ICU bağımlılığı PATH'teki Poppler ICU ile aynı dosya adını taşır.
# Bu wheel Windows'un ICU API'sini kullanır; yabancı icuuc.dll onu gölgelememeli.
a.binaries = [entry for entry in a.binaries
              if not Path(entry[0]).name.lower().startswith('opencv_videoio_ffmpeg')
              and Path(entry[0]).name.lower() not in {"icuuc.dll", "icuin.dll", "icudt78.dll"}]
a.datas = [entry for entry in a.datas if Path(entry[0]).name.lower() != 'llama-quantize-impl.dll']
# Native server libraries are external processes, not Python dependencies.
# Share byte-identical core DLLs and remove bindepend's unused root copies.
import hashlib
shared_names = {'ggml-base.dll', 'ggml.dll', 'libomp.dll', 'llama-common.dll',
                'llama-server-impl.dll', 'llama.dll', 'mtmd.dll'}
shared = {}
for name in shared_names:
    cpu = root / 'build/embedding/cpu' / name
    vk = root / 'build/embedding/vulkan' / name
    if cpu.is_file() and vk.is_file() and cpu.read_bytes() == vk.read_bytes():
        shared[name] = cpu

def compact_native(entries):
    result, emitted = [], set()
    for target, source, kind in entries:
        path = Path(target)
        name = path.name.lower()
        if name.startswith('llama-') and name.endswith('-impl.dll') and name != 'llama-server-impl.dll':
            continue
        if name in shared_names and len(path.parts) == 1:
            continue
        if name in shared and len(path.parts)>2 and path.parts[0]=='embedding' and path.parts[1] in ('cpu','vulkan'):
            if name not in emitted:
                result.append((str(Path('embedding/common')/path.name),str(shared[name]),kind))
                emitted.add(name)
        else:
            result.append((target,source,kind))
    return result
a.binaries = compact_native(a.binaries)
a.datas = compact_native(a.datas)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=stem, console=False,
          debug=False, strip=False, upx=False, version=metadata,
          icon=str(root / "build/evrakci.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name=stem, strip=False, upx=False)
