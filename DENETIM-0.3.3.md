# Evrakçı 0.3.3 — AI model seçimi

Tarih: 30.09.2026. Başlangıç: `v0.3.2` / `c2027fc80eb9863cec323d95409d8239a4a085c6`.

## Değişiklik

- AI Yardımcısı'ndaki Gemini 3.8 Flash kaldırıldı; Gemini 3.6 Flash eklendi. Gemini 3.5 Flash yerine Gemini 3.5 Flash-Lite eklendi. Gemini 3.1 Flash-Lite ve Gemma 4 26B A4B korunur.
- Varsayılan model Gemini 3.6 Flash'tır. Kasa ayarlarında önceden kaydedilmiş 3.8 ve 3.5 Flash seçimleri açılışta sırasıyla 3.6 Flash ve 3.5 Flash-Lite kimliğine taşınır. Kullanıcı daha sonra listedeki her modeli seçebilir.
- Google'ın resmi model sayfaları `gemini-3.6-flash` ve `gemini-3.5-flash-lite` kimliklerini kararlı modeller olarak listeler: https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash ve https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite (erişim: 30.09.2026).

## Doğrulama sınırı

- Model listesi, API uç noktası ve eski seçimlerin dönüşümü kaynak testinde doğrulandı. Kapsam dışı çalışma ağacı değişikliklerinden arındırılmış izole kaynakta 94 test geçti. Paketli 0.3.3 EXE'de 19 sentetik smoke kontrolü geçti; bunlar menü sırası, kayıtlı eski seçimin dönüşümü ve yeni model seçiminin saklanmasını içerir.
- Gerçek Google hesabı ve API anahtarıyla canlı istek yapılmadı; servis yanıtı/ücretlendirme doğrulanmış sayılmaz.

Dağıtım kanıtı: `TESLIM-0.3.3.md`.
