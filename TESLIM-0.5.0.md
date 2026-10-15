# Evrakçı 0.5.0 — teslim

Tarih: 15.10.2026. Kapsam: [DENETIM-0.5.0.md](DENETIM-0.5.0.md). Arayüz sıfırdan yeniden tasarlandı.

- Tam test paketi: **163 geçti**.
- Kaynak smoke: **23 kontrol geçti** (kasa → tarama → arama → önizleme → kilit/açma → OCR → AI yerel önizleme).
- 7 sekmenin açık/koyu görüntüleri alındı; zemin renkleri ve taşma ölçüldü (1100–1600 px).
- Sürüm `0.5.0`; ray artık iki temada da tema-uyumlu, kart içinde kart yok.

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın.
EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Canlı Gemini, gerçek arşiv pilotu ve gerçek Windows ekran ölçekleri henüz doğrulanmadı.
İlgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py,
tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
