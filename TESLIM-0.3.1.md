# Evrakçı 0.3.1 — yerel teslim kaydı

Tarih: 30.09.2026.

- Kapsam dışı çalışma ağacı değişikliklerini dışarıda bırakan izole kaynakta **94 test geçti**.
- Aynı kaynaktan üretilen paketli EXE'de **17 sentetik smoke kontrolü geçti**. Kontroller ilk kurulum, arama, OCR, tarama, kilit ve AI yerel önizleme akışlarını kapsar.
- Gerçek 8,62 GiB kasada paketli 0.3.1 EXE, tanı günlüğüne göre yaklaşık **iki saniyede** `main_window_ready` aşamasına ulaştı; pencere yanıt veriyor. Önceki 0.3.0 açılışı yaklaşık üç dakika sürdü.
- Dağıtım: `Evrakçı-0.3.1.zip`; SHA-256: `9ab97c3b455b56c1b12a3bf3e76a56f8ed4a16ea86119153f298f40347c2b4e0`.
- ZIP içindeki EXE sürüm bilgisi 0.3.1, BAT başlatıcısı aynı EXE adını kullanır. ZIP CRC denetimi temizdir.
- Kaynak çalışma ağacındaki OCR konsol penceresi düzeltmeleri, `DURUM.md` ve kullanıcının `tests/test_durability.py` değişikliği bu paket ve sürüm commit'inin dışındadır. GitHub'a gönderim veya harici yayın yapılmadı.
- Kasa büyüklüğünde boş sayfaların payı yaklaşık 48 KiB; tablo/indeks bazında alan dağılımı henüz ölçülmedi. Uzun gerçek tarama ve iş bilgisayarı pilotu ayrı doğrulama gerektirir.

Değişiklik ve sınırlar: `DENETIM-0.3.1.md`.
