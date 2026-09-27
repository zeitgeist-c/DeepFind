# Evrakçı 0.1.4 — Üçüncü-taraf lisansları

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

PySide6 (LGPLv3): lisans metni pakette `licenses/` altında taşınır; Qt kaynak teklifi Qt Company kanalıyla (dinamik bağ, değişiklik yok).
Tesseract-OCR pakete dahil değildir; ayrı önkoşul kurulumdur (UB-Mannheim, Apache-2.0).
