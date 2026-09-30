# Evrakçı 0.3.6 — gezinme düzenlemesi

Tarih: 01.10.2026.

- Ara ekranında yalnız Arama ve Sonuçlar kartları kalır.
- Ara'nın hemen altında AI ile ara sekmesi bulunur. Gemini model/anahtar/bağlantı ayarları, sorgu önerisi, arşive soru sorma, belge özetleme, gönderilecek alıntılar, yanıt ve kaynaklar bu sekmeye taşınmıştır. Ayrı AI popup kaldırılmıştır; kaynak evraklar ortak ön izleme popup'ını kullanır.
- Yedekler kartı Ayarlar sekmesinde Çalışma düzeni ve Kasa güvenliği kartlarının altındadır. Uzun Ayarlar sayfası kaydırılabilir. Yedek oluşturma/geri yükleme davranışı korunur.
- Sekme yenilemeleri, kısayollar ve menüyü daraltma yeni gezinme sırasıyla çalışır.
- Uzun tam geçiş yedeği her açılışta alınmaz. Tamamlanan archive_version kaydı varsa sonraki açılışta atlanır. Kesilen geçiş tekrar denenir. Aynı kasayı başarılı geçişten sonra yeniden açan regresyonda yedek sayısının artmadığı kontrol edilir.

İlgili UI ve paket kontrolleri yeni sekme sırasını, AI kontrollerinin AI sekmesine ve yedek listesinin Ayarlar'a ait olduğunu sınar. Açık/koyu ve geniş/dar ekran görüntüleri sentetik kasayla değerlendirilir. Gerçek büyük kasa açılışının süresi, canlı Gemini ve gerçek Windows ekran ölçeği ayrı kabul kontrolleridir.

Son test/paket sonuçları TESLIM-0.3.6.md içinde kaydedilir. Önceki beş ilgisiz kullanıcı değişikliği korunur; sürüm kaynağına alınmaz. Harici yayın kapsam dışıdır.
