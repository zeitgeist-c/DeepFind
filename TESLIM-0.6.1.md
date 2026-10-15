# Evrakçı 0.6.1 — Kök kaldırma düzeltmesi teslimi

Tarih: 15.10.2026. Kapsam: [DENETIM-0.6.1.md](DENETIM-0.6.1.md).

- Tam test paketi: **193 geçti**.
- Paketli EXE: **24 paket kontrolü geçti** (`root-remove-worker` dahil — kök kaldırma
  ayrı thread'de çalışır, kayıtlar doğru temizlenir).
- EXE FileVersion/ProductVersion **0.6.1**; BAT aynı sürüm EXE'sini çalıştırır.
- `Evrakçı-0.6.1.zip`: **169.613.791 bayt**. SHA-256:
  `cfad25c907297004d4864bd6cf569bbdea1eade216c9ada6845756083c87910b`. ZIP CRC doğrulanmış.
- Sürüm 0.6.0'dan farkı yalnız: sürücü kökünde kaynak kaldırma artık gerçekten
  indeksi temizliyor ve arayüz donmuyor (QThread işçisi).

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın.
EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Not: mevcut canlı kasa C:\ köküyle taranmış durumda (112.019 kayıt). Bu sürümle kök
silme artık gerçekten işler; silmeden önce emin olunduğuna dikkat edin.

İlgisiz kullanıcı değişiklikleri (doc_adapter.py, ocr.py, ocr_setup.py,
tests/test_durability.py önceki not, DURUM.md önceki bölüm) korunup commit kapsamına
ayrıldı. Yerel commit ve `v0.6.1` etiketi; push/Release yok.
