# Evrakçı 0.1.6 — OCR kurulum ve içerik araması denetimi

Tarih: 28.09.2026. Başlangıç: 808e80c / v0.1.5.

- Windows paketi Tesseract 5.4.0.20240606 motorunu, çalışma DLL'lerini ve lisansını taşır. Derleme, motor EXE'sinin SHA-256 değerini doğrular.
- İlk kurulum ve mevcut kasa açılışı, OCR hazır değilse doğrulama/indirme sayfasını gösterir. Sayfa bitmeden ana pencereye geçilmez. Hata halinde yeniden deneme veya çevrimdışı model klasörü seçme mümkündür.
- `tur`, `eng`, `osd` modelleri `tessdata_fast` commit `87416418657359cb625c412a48b6e1d6d41c29bd` sürümüne sabitlenmiştir. Boyut ve SHA-256 doğrulaması ardından atomik olarak etkinleşir. Kısmi indirmede Range ile sürdürülür.
- OCR dili ayarlardan Türkçe veya Türkçe+İngilizce seçilebilir. Mevcut kasadaki eksik model yüzünden ertelenen OCR işleri hazır olduktan sonra yeniden işlenebilir.
- Yerel arama indeksinde metin seçilebilir PDF ve fotoğraf tabanlı PDF sayfalarından çıkarılan içerik bulunur. İçerik SQLCipher kasasında tutulur; kaynak belgelere yazılmaz.
- Son tam kaynak testinde 83 test geçti. İlk kurulum işçi yaşam döngüsüne ek hedefli testte 4 test geçti. ZIP içindeki gerçek EXE 14 sentetik kabul kontrolünden geçti; Türkçe OCR çağrısı da çalıştı. ZIP CRC doğrulandı.
- Paket SHA-256 ve boyut: `TESLIM-0.1.6.md`. Paket denetim kaydı: `build/package-check-0.1.6.json`.

Sınırlar: Temiz bir Windows bilgisayarında ağ üzerinden ilk model indirmesi ve gerçek büyük arşiv henüz doğrulanmadı. İnternet yoksa aynı sabit modellerin çevrimdışı kopyası gerekir. Eski `.doc` biçiminin içerik çıkarımı desteklenmiş sayılmaz. Kullanıcının mevcut `tests/test_durability.py` değişikliği bu sürüm kapsamı dışındadır.
