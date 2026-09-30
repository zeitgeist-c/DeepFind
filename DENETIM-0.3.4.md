# Evrakçı 0.3.4 — içerik arşivi ve kararlılık denetimi

Tarih: 30.09.2026. Bu kayıt yedi kullanıcı talebini ayrı izler.

| Talep | Uygulama | Doğrulama |
|---|---|---|
| Gemini anahtarı | Arama kartında maskeli giriş, şifreli saklama, kaydet/sil, bağlantı testi | Otomatik akışlar; canlı Google kontrolü kullanıcı anahtarıyla yapılmadı |
| Taranmış evraklar | Ayrı sekme, 100 kayıtlık sayfalar, ad/yol/durum filtreleri | Dosya listesi ve aynı evrak popup akışı |
| Arama ve popup | Tam yol/içerik, yükleme animasyonu, sonuç sayfalama, ortak popup | 500+ aday regresyonu; 60+ bölüm; değişmiş/erişilemeyen kaynak |
| Dört kare kart | Arama/Sonuçlar/Gemini/Yedekler; ayrı AI/yedek sekmeleri taşındı | Açık/koyu 1500/1050 ekran görüntüleri; gerçek Windows/DPI pilotu ayrı |
| Güncellemede koruma | Sabit kasa, geçiş öncesi doğrulanmış yedek, başarısız dönüşümde geri yükleme | Eski kayıtlarla açılış ve dönüşüm hatası regresyonu |
| Donma/kapanma | Arka plan sorguları, tek etkin iş/anahtar, iptal/eski sonuç koruması, yaşam döngüsü | 100 boşta + 100 taramada sekme geçişi; gerçek işyeri kapanması yeniden üretilmedi |
| Ayrıntılı indeks/AI | PDF/Excel/Word devam pencereleri, kalıcı staging, konumlu parçalar, resim OCR, eşleşme çevresinden AI alıntıları | Son sayfa/satır/paragraf, kesintiden devam, OCR eksikliği, geç alıntı ve eski içerik korunması |

## Ölçüm ve sınırlar

- Windows 11 10.0.26200, Python 3.13.15; sentetik 10.000 belge/10.000 bölüm, 30 sorgu. Son ölçümde arama p95 11,06 ms; 100 boşta geçişte maksimum 7,19 ms; 100 taramada geçişte maksimum 10,95 ms. Ham rapor: `build/archive034/acceptance.json`. Gerçek arşiv performansı için kanıt değildir.
- Windows Application kayıtlarında 27.09.2026 tarihli 0.1.3/Python süreçlerinde Qt6Widgets.dll / c0000005 görüldü. Güncel sürümde bildirilen kapanmayla nedensellik kurulmadı.
- PDF/Word/Excel metni ve ayrı JPG/JPEG/PNG/TIFF OCR kapsamındadır. Word/Excel içine gömülü resimler kapsam dışıdır. DOC için LibreOffice gerekir; motor yoksa eksiklik açıkça gösterilir.
- Kaynak dosyalara yazılmaz. 200 MB dosya, OOXML açılım ve alt süreç zaman/RAM sınırları korunur; sınırı aşan kaynaklar kısmi/hatalı kaydedilir. Her dosyanın eksiksiz okunacağı iddia edilmez.
- AI bütün arşivi göndermez. Yerel parçalar seçilir; kullanıcı alıntıları inceleyip gönderir. İsteğe bağlı Gemini sorgu önerisi yalnız soruyu gönderir. Kaynak kimlikleri doğrulanır; cevap metninin anlamsal doğruluğu otomatik kanıtlanmış sayılmaz.
- Mevcut kullanıcı OCR/dayanıklılık değişiklikleri bu sürümün kaynak commit ve paketinden ayrılır; çalışma ağacında korunur.

## Teslim kapısı

İzole teslim kaynağında tam test, kaynak smoke, derlenmiş EXE smoke ve ZIP CRC sonuçları TESLIM-0.3.4.md içinde kaydedilir. Canlı Gemini, gerçek işyeri arşivi ve gerçek kapanma pilotu yapılmadığı sürece ürünün bütün kullanım koşullarında kabulü açık kalır. Harici yayın kapsam dışıdır.
