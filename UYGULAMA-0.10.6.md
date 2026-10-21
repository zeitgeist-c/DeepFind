# Evrakçı 0.10.6 — yalnız anlamsal arama

Kullanıcı kararı, 21.10.2026: kötü adlandırılmış belgeleri içeriklerini tarif ederek bulmak esastır. Kelime/FTS/fuzzy araması ve sözlük bakımı kaldırılır. OCR, şifreli metin, sayfa/dosya bağlantıları, filtreler ve vektörler korunur.

1. Arama: yalnız aynı model/sürüm/boyuttaki içerik vektörleri; belge başına en iyi bölüm, filtreleme ve kararlı sayfalama. Model yoksa açık durum, kelime aramasına dönüş yok. Kontrollü vektör ve gerçek model kabulü.
2. Depolama: yeni kasada FTS/sözlük yok. Eski kasada yeniden FTS üretmeden v10 geçişi; belge/vektör/ayarlar korunur. Geçiş öncesi doğrulanmış şifreli yedek ve başarısız geçişte geri dönüş.
3. Arayüz/tarama: sözlük aşaması ve eski açıklamalar kaldırılır. İlerleme/duraklatma/iptal korunur. Eski kelime araması testleri yeni sözleşmeyle değiştirilir; veri yaşam döngüsü testleri depolamayı arama modelinden bağımsız kontrol eder.
4. Kullanıcının eski kasası: kapalı süreç/dosya kilidi ve kesin yollar kontrol edilerek yalnız izin verilen kasa dosyaları silinir; özgün belgeler, modeller ve ayrı yedekler korunur. Yeni arşiv kullanıcı tarafından yeniden taranır.
5. Teslim: regresyonlar, gerçek kitap/gerçek model, paket EXE ve kurulum kabulü; yerel commit/tag; özel kaynak/herkese açık paket sınırıyla GitHub Release ve güncelleme kanalı.

Fiziksel Nvidia/CUDA kabulü bu AMD bilgisayarda doğrulanamaz; bu sınır teslimde belirtilir.
