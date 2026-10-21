# Evrakçı 0.10.0 — Üçüncü-taraf lisansları

Üretim: kurulu dağıtımdan, dosya-içi METADATA + lisans metni adıyla.

- sqlcipher3==0.6.2 — MIT
  - sqlcipher3-0.6.2.dist-info/licenses/LICENSE
- pypdfium2==5.13.0 — BSD-3-Clause, Apache-2.0, dependency licenses
  - pypdfium2-5.13.0.dist-info/licenses/LICENSES/Apache-2.0.txt
  - pypdfium2-5.13.0.dist-info/licenses/LICENSES/BSD-3-Clause.txt
  - pypdfium2-5.13.0.dist-info/licenses/LICENSES/CC-BY-4.0.txt
  - pypdfium2-5.13.0.dist-info/licenses/data/windows_x64/BUILD_LICENSES/abseil.txt
- openpyxl==3.1.5 — MIT
  - openpyxl-3.1.5.dist-info/LICENCE.rst
- xlrd==2.0.2 — BSD
  - xlrd-2.0.2.dist-info/LICENSE
- python-docx==1.2.0 — MIT
  - python_docx-1.2.0.dist-info/licenses/LICENSE
- defusedxml==0.7.1 — PSFL
  - defusedxml-0.7.1.dist-info/LICENSE
- RapidFuzz==3.14.6 — MIT
  - rapidfuzz-3.14.6.dist-info/licenses/LICENSE
- pillow==12.3.0 — MIT-CMU
  - pillow-12.3.0.dist-info/licenses/LICENSE
- PySide6_Essentials==6.11.2 — LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
  - pyside6_essentials-6.11.2.dist-info/licenses/LicenseRef-Qt-Commercial.txt
- shiboken6==6.11.2 — LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
  - shiboken6-6.11.2.dist-info/licenses/LicenseRef-Qt-Commercial.txt
- rapidocr==3.10.0 — Apache-2.0
  - rapidocr-3.10.0.dist-info/licenses/LICENSE
  - rapidocr-3.10.0.dist-info/licenses/MODEL_LICENSES.md
- onnxruntime-directml==1.24.4 — MIT License
  - onnxruntime/LICENSE
  - onnxruntime/ThirdPartyNotices.txt
- opencv-python-headless==4.11.0.86 — Apache 2.0
  - cv2/LICENSE-3RD-PARTY.txt
  - cv2/LICENSE.txt
  - cv2/data/haarcascade_license_plate_rus_16stages.xml
  - opencv_python_headless-4.11.0.86.dist-info/LICENSE-3RD-PARTY.txt
- numpy==2.5.4 — BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0
  - numpy-2.5.4.dist-info/licenses/LICENSE.txt
  - numpy-2.5.4.dist-info/licenses/numpy/_core/include/numpy/libdivide/LICENSE.txt
  - numpy-2.5.4.dist-info/licenses/numpy/_core/src/common/pythoncapi-compat/COPYING
  - numpy-2.5.4.dist-info/licenses/numpy/_core/src/highway/LICENSE
- EmbeddingGemma 2 Q8_0 — Apache-2.0; Google modelinden ggml-org dönüşümü.
  - `embedding/model-LICENSE.txt`; kaynak ve SHA-256 `embedding/manifest.json`.
- llama.cpp b11765 — MIT; `embedding/llama-LICENSE.txt`.
- LLVM OpenMP — Apache-2.0 with LLVM exceptions; CPU/Vulkan motor klasörlerinde `LICENSE-LLVM-OpenMP`.
- İsteğe bağlı CUDA bileşeni: NVIDIA çalışma zamanlarının yeniden dağıtım koşulları geçerlidir.

PySide6 (LGPLv3): lisans metni pakette `licenses/` altında taşınır; Qt kaynak teklifi Qt Company kanalıyla (dinamik bağ, değişiklik yok).
RapidOCR (PP-OCR modelleri, Apache-2.0) + ONNX Runtime (MIT) + OpenCV-python-headless (Apache-2.0) bağımlılıkları licenses/ altında taşınır.
