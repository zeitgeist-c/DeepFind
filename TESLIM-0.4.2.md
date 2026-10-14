# Evrakçı 0.4.2 — 7 sekmede yeni iç tasarım dili teslimi

Tarih: 14.10.2026. Kapsam: [DENETIM-0.4.2.md](DENETIM-0.4.2.md).

- Tam test paketi: **163 geçti**.
- Son ZIP içindeki gerçek EXE: **23 kontrol geçti**, ZIP CRC doğrulandı.
- EXE FileVersion/ProductVersion **0.4.2**; BAT aynı sürüm EXE'sini çalıştırır.
- `Evrakçı-0.4.2.zip`: **169.301.817 bayt**. SHA-256: `c3fd439c74c406fa3c921434f67c2eaa65157a1da17e40cac38b327796142aa8`.
- 7 sekmenin açık/koyu görüntüleri değerlendirildi; 1440x860 ve 1100x700 boyutlarında ezilme, çakışma ve yatay kaydırma yok (ölçüldü).

Ham rapor: `build/package-check-0.4.2.json` (repo dışı).

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın. EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Canlı Gemini, gerçek arşiv pilotu ve gerçek Windows ekran ölçekleri henüz doğrulanmadı. İlgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py, tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı. Yerel commit ve `v0.4.2` etiketi push'landı; GitHub Release oluşturuldu, indirilen dosyanın karması doğrulandı.
