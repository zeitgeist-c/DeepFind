# Evrakçı 0.3.0 — yerel teslim kaydı

Tarih: 29.09.2026.

- Kaynak testleri: **93 geçti** (`python -m pytest -q`).
- `dist/Evrakçı-0.3.0/Evrakçı-0.3.0.exe` paket içi sentetik smoke: **17 kontrol geçti**. Sonuç: `build/package-check-0.3.0.json`.
- Dağıtım: `Evrakçı-0.3.0.zip`; SHA-256: `ef7ae03fceadd1b32f8f9e1451d2d8f06e9592f6461d967452d8a02c72e13870`.
- Paket adı program + sürüm biçimindedir; uygulama klasöründeki `_internal` ve lisans dosyaları EXE ile birlikte taşınır.
- Gerçek iş bilgisayarında uzun tarama ve Windows açılışında başlatma ayrıca doğrulanmadı. Kullanıcının yaşadığı önceki kapanmanın kesin kök nedeni bu sentetik ortamda üretilemedi. Bu sürümde yaşam döngüsü tanı günlüğü ve kalıcı tarama kayıtları eklendi.
- Kullanıcının mevcut `tests/test_durability.py` değişikliği korunur ve sürüm commit'ine alınmaz. GitHub'a gönderim veya harici yayın yapılmaz.

Değişiklik kapsamı ve sınırlamalar: `DENETIM-0.3.0.md`.
