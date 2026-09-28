# Evrakçı 0.2.0 — AI Yardımcısı denetimi

Tarih: 28.09.2026. Başlangıç: 7c21561 / v0.1.6.

## Uygulama

- İsteğe bağlı AI Yardımcısı sekmesi, yerel şifreli arşivdeki metinlerden soru-cevap ve seçili belge özeti hazırlar. Klasik arama ve OCR, API anahtarı olmadan çalışır.
- Soru için mevcut yerel arama sıralaması kullanılır. İndeksin gerçek içerik segmentlerinden sınırlı alıntılar seçilir; yalnız dosya adı veya klasör bağlamı kanıt olarak gönderilmez. Özet, seçilen belgenin en çok 12 kesitini kullanır. Uzun belgelerde kısmi özet olduğu açıkça belirtilir.
- Kullanıcı alıntıları önizlemeden ağ isteği yapılamaz. Gönderim öncesi ve yanıt geldiğinde segmentlerin güncelliği doğrulanır. Kullanıcı soru/işlem türünü değiştirirse devam eden istek iptal edilir.
- Gemini API anahtarı SQLCipher kasasındaki `settings` tablosuna kaydedilir; ağ gövdesine veya loga eklenmez. Anahtar isteğin `x-goog-api-key` başlığında gönderilir. İstek 30 saniyede zaman aşımına uğrar.
- Yanıt için JSON şeması istenir; gösterdiği kaynak kimlikleri gönderilmiş alıntıların izin listesiyle ayrıca doğrulanır. Kaynak tıklanınca mevcut belge önizlemesi açılır. Kasa kilidinde alıntılar, yanıt, anahtar giriş alanı ve kaynak listesi temizlenir; ağ isteği iptal edilir.
- Kullanılan model: Google'ın resmi model kimliği `gemini-3.8-flash`; GenerateContent REST uç noktası. Kaynaklar: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash/ ve https://ai.google.dev/gemini-api/docs/generate-content/structured-output.

## Doğrulama ve sınırlar

- Sentetik yerel kanıt seçimi, değiştirilmiş segment reddi, kısmi özet, kaynak izin listesi, gönderim öncesi ağsız önizleme, taklit edilmiş HTTP yanıtı, istek iptali ve kilitte temizleme test edildi.
- Açık/koyu temada 1366×768 AI ekranları `build/review-ui-0.2.0` altındadır. Paket içindeki EXE, sentetik AI önizlemesi ve önceki OCR/tarama/arama akışlarıyla sınanır.
- Kullanıcı API anahtarı sağlanmadığı için gerçek Gemini hesabına canlı çağrı yapılmadı. Bulut servisinin gerçek yanıtı, hesap/kota ve ağ koşulları doğrulanmış kabul edilmez.
- Uzun belge özeti yalnız gösterilen kesitleri kapsar. AI yanıtının anlamsal doğruluğu kaynak kimliği kontrolünden bağımsız olarak kullanıcı tarafından değerlendirilmelidir. Bu sürümde benzer belge arama veya arşivin tümünü buluta yükleme yoktur.
- Kullanıcının mevcut `tests/test_durability.py` değişikliği sürüm commit'ine alınmaz. Gerçek NAS, temiz Windows ve yüksek DPI pilotları hâlâ ayrıdır.

Son test, paket SHA-256 ve yerel sürüm kaydı: `TESLIM-0.2.0.md`.
