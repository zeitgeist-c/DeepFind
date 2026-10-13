# Evrakçı 0.4.1 — sekme içleri işlik düzeni teslimi

Tarih: 13.10.2026. Kapsam: [DENETIM-0.4.1.md](DENETIM-0.4.1.md).

- Tam test paketi: **163 geçti**.
- Son ZIP içindeki gerçek EXE: **23 kontrol geçti** (`search-workbench` dahil), ZIP CRC doğrulandı.
- EXE FileVersion/ProductVersion **0.4.1**; BAT aynı sürüm EXE'sini çalıştırır.
- `Evrakçı-0.4.1.zip`: **169.298.477 bayt**. SHA-256: `95c3556845018f02ce5867d20ceff2c0b965e465a4da1084b1ecd0b8c71ec515`.
- Ara, Geçmiş ve Taranmış Evraklar ekranlarının açık/koyu görüntüleri değerlendirildi: üç sütun çakışmıyor, butonlar ezilmiyor, yatay kaydırma çıkmıyor. Sütun genişlikleri kullanıcı tarafından ayarlanabilir.

Ham rapor: `build/package-check-0.4.1.json` (repo dışı).

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın. EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Canlı Gemini, gerçek arşiv pilotu ve gerçek Windows ekran ölçekleri henüz doğrulanmadı. İlgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py, tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı. Yerel commit ve `v0.4.1` etiketi push'landı; GitHub Release oluşturuldu.
