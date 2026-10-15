# Evrakçı 0.5.0 — teslim

Tarih: 15.10.2026. Kapsam: [DENETIM-0.5.0.md](DENETIM-0.5.0.md). Arayüz sıfırdan yeniden tasarlandı.

- Tam test paketi: **163 geçti**.
- Son ZIP içindeki gerçek EXE: **23 kontrol geçti**, ZIP CRC doğrulandı.
- EXE FileVersion/ProductVersion **0.5.0**; BAT aynı sürüm EXE'sini çalıştırır.
- `Evrakçı-0.5.0.zip`: **169.311.257 bayt**. SHA-256: `138df74aaa45fba530cd708bfb1d7bf36c9d117e4d2ec66e5e29cb18fdcc8485`.
- 7 sekmenin açık/koyu görüntüleri değerlendirildi; zemin renkleri ve taşma ölçüldü (1100–1600 px).
- Ray artık iki temada da tema-uyumlu; kart içinde kart yok; kodda sabit renk kalmadı.

Ham rapor: `build/package-check-0.5.0.json` (repo dışı).

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın.
EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Canlı Gemini, gerçek arşiv pilotu ve gerçek Windows ekran ölçekleri henüz doğrulanmadı.
İlgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py,
tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
Yerel commit ve `v0.5.0` etiketi push'landı; GitHub Release oluşturuldu, indirilen dosya
`cmp` ile birebir doğrulandı.

