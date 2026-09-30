# Evrakçı 0.3.5 — açılış düzeltmesi teslimi

Tarih: 01.10.2026. Sorun kanıtı ve kapsam: [DENETIM-0.3.5.md](DENETIM-0.3.5.md).

- İzole kaynakta tam test paketi: **109 geçti**, 132,86 saniye.
- Kaynak smoke ve son ZIP'teki gerçek EXE: **23 kontrol geçti**. Eski şemadan arka plan hazırlığı ve yedek/doğrulama/şema ilerleme aşamaları dahil. ZIP CRC doğrulandı.
- EXE FileVersion/ProductVersion **0.3.5**, ProductName **Evrakçı**; BAT aynı sürüm EXE'sini çalıştırır. Yedi kapsam dosyası izole derleme kaynağıyla SHA-256 üzerinden eşleşti.
- `Evrakçı-0.3.5.zip`: **168.916.351 bayt**. SHA-256: `ffcfe15d93b7939107593b1ef4b62e2ef8b0d96774a4d03d8e010726552b2fde`.
- Ham rapor: `build/package-check-0.3.5.json`. Yerel commit ve `v0.3.5` etiketi teslimden önce oluşturulur; kesin kimlik teslim mesajında verilir. Harici yayın yapılmaz.

Programı kapatın, ZIP'i tamamen yeni bir klasöre çıkarın ve içindeki `Evrakçı-0.3.5.exe` veya BAT'ı çalıştırın. EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve veriler korunur. Eski şemada ilk açılışta tam güvenli yedek ve bütünlük kontrolü yine gerekir; büyük kasa için süreye ihtiyaç vardır. Açılış penceresi bu işlemleri arka planda yürütüp aşama ve yedekleme yüzdesini gösterir.

Gerçek 9,39 GB kasada yeni sürümün tamamlanan açılışı henüz ölçülmedi. Önceki sürecin sonlanma nedeni belirlenemedi; bu teslim, kanıtlanan arayüzün bloke olması ve ilerleme gösterilmemesi sorununu düzeltir. Gerçek kasaya ve kalan yarım yedeklere inceleme sırasında müdahale edilmedi.

Önceki beş ilgisiz kullanıcı değişikliği (`DURUM.md`, `doc_adapter.py`, `ocr.py`, `ocr_setup.py`, `test_durability.py`) korunup paket ve sürüm commit'i dışında bırakıldı. 0.3.4'teki gerçek arşiv, canlı Gemini ve gömülü resim OCR kapsam sınırları devam eder.
