# Evrakçı 0.3.0 — kararlılık denetimi

Tarih: 29.09.2026. Başlangıç sürümü: `v0.2.0` / `ab814c80c54619882034e28eb77c1469db9a00b3`.

## Uygulananlar

- Dar gezinme menüsündeki simgeler hücre içinde ortalanır. Ana pencere ilk açılışta kullanılabilir ekran alanının ortasında yaklaşık 1440×860 açılır; sonraki boyut ve konum kaydedilir ve ekrana sığacak biçimde geri yüklenir.
- Açık kasanın ikinci kez başlatılması, yerel uygulama kanalı üzerinden mevcut pencereyi öne getirir. Tepsi simgesine tıklamak ve Aç menüsü aynı işlevi kullanır. Tepsi yoksa pencere görünür açılır; kapatma işlemi arka planda görünmez süreç bırakmaz.
- Uygulama yaşam döngüsü ve tarama aşamaları `%LOCALAPPDATA%/Evrakci/Logs/lifecycle.log` içinde yollar ve sırlar olmadan kaydedilir. Beklenmeyen Python hatası veya yerel çökme için tanı izi etkinleştirilir.
- Tarama aşaması ve sayaçlar şifreli `scan_runs` tablosuna düzenli kaydedilir. İşlenen belgeler zaten ayrı işlemlerle indekslendiği için iptal veya güç kesintisi bunları geri almaz. Kapanmamış çalışma sonraki açılışta “Kesintiye uğradı” olarak görünür. Tarama ekranı son 12 çalışmayı gösterir.
- Sözlük oluşturma tüm içerikleri belleğe almadan şifreli ara tabloyu gruplar halinde kullanır. Kopya doğrulaması ve sözlük hataları başarılı tarama gibi gösterilmez.
- AI Yardımcısı mevcut Gemini 3.8 Flash, Gemini 3.5 Flash, Gemini 3.1 Flash-Lite ve Gemma 4 26B A4B modellerini seçebilir; seçilen model şifreli ayarda saklanır. Model değişince hazırlanmış alıntı geçersizleşir. Canlı API çağrısı yapılmadı.
- Windows açılışında başlatma ayarı mevcut paket yolunu kaydeder; eski EXE yolunu işaret eden kayıt kullanıcıya bildirilir. Günlük tarama davranışı korunmuştur.

## Doğrulama ve kalan sınırlar

- Kaynak testleri: **93 geçti**. İptal sonrası indeksin korunması, yarım tarama kaydı, ikinci açılış, model seçimi, sınırlı bellekle sözlük oluşturma ve hash hatasının kısmi kaydı sınandı.
- Dar menü ve AI ekranları sentetik açık/koyu Qt görüntüleriyle incelendi.
- Paketli EXE ve iş bilgisayarında uzun gerçek tarama doğrulaması aşağıdaki teslim kaydında ayrı gösterilir. Gerçek kapanmanın kök nedeni eldeki sentetik ortamda yeniden üretilemedi; tanı günlüğü bu tür bir sonraki olayı incelemeye yöneliktir.
- Tek EXE taşınabilir paket değildir; `_internal` dahil tüm dağıtım klasörü gerekir. Yerel kasa ve OCR verisi EXE klasöründen ayrıdır.
- Kullanıcının önceden değiştirdiği `tests/test_durability.py` bu sürümün kapsamı dışında korunur. Gerçek NAS, temiz Windows, yüksek DPI ve 50.000 dosya pilotları V4 kabulünden ayrıdır.

Paket SHA-256, yerel commit ve etiket: `TESLIM-0.3.0.md`.
