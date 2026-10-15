# Evrakçı 0.6.2 — Denetim düzeltmeleri teslimi

Tarih: 15.10.2026. Kapsam: [DENETIM-0.6.2.md](DENETIM-0.6.2.md).

0.6.1 (kök kaldırma) üzerine denetim düzeltmeleri: Dışla sürücü kökü eşleşmesi,
atomik kaldırma/hariç işlemleri, Dışla'nın arka plana taşınması, çakışma
korumaları, sözlük senkronu.

- Tam test paketi: **199 geçti**.
- Kaynak smoke: **25 kontrol**.
- Paketli EXE smoke: **25 kontrol** (`root-remove-worker` + `exclusion-worker` dahil).
- EXE FileVersion/ProductVersion **0.6.2**; BAT aynı sürüm EXE'sini çalıştırır;
  manifest 0.6.2.
- `Evrakçı-0.6.2.zip`: **169.621.020 bayt**. SHA-256:
  `b0b3db0fba74273456fdeeaf5743c9fa4b91fce3567d7c6479264f3bfc75d8b6`. ZIP CRC doğrulanmış.

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın.
EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Not: mevcut canlı kasa `C:\` köküyle taranmış durumda (112.019 kayıt). "Kaldır"
artık gerçekten indeksi boşaltır ve "Dışla" sürücü kökünde çalışır; silmeden önce
emin olun. Bu teslimde canlı kasaya dokunulmadı.

İlgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py,
tests/test_durability.py) korunup commit dışında bırakıldı. Yerel commit ve
`v0.6.2` etiketi bu teslimle oluşturulur; 0.6.1 etiketi (Release oluşturulmamıştı)
tarihsel olarak korunur. Push/Release ayrı yetkiyle yapılır.
