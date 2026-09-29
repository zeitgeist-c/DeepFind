# Evrakçı 0.3.1 — büyük kasada açılış düzeltmesi

Tarih: 30.09.2026. Başlangıç: `v0.3.0` / `401aec60ec975dd8a5e47a283528b621db44237b`.

## Hata kanıtı

- Kullanıcının mevcut kasası yaklaşık 9 GB idi. 0.3.0 işlemi 29.09.2026 19:56:29'da başladı; tanı günlüğünde `ocr_ready` sonrasında pencere uzun süre oluşmadı. `main_window_ready` yaklaşık üç dakika sonra kaydedildi. Aynı işlem sonrasında kullanıcı tarama başlatabildi. Bu, açılış gecikmesini doğrular; tek başına kesin maliyet dağılımını göstermez.
- 0.3.0 her açılışta `ensure_schema` ve `ensure_v5` çağırıyordu. `ensure_v5`, mevcut `segments` tablosunu tarıyor, boş dönüştürülmüş metinleri sınırsız `fetchall()` ile belleğe alabiliyordu. Eski şema sürüm işaretleri her kontrol zincirinde yeniden yazılıyordu.

## Düzeltme

- Tamamlanmış v7/v8 kasalarda eski metin doldurma işlemi atlanır; v8 tarama alanları gerektiğinde tamamlanır. Önceki açılışın sürüm işaretini geriye yazıp yarıda kalmış olabileceği durumda, tamamlanmış normalleştirici işareti ve gerekli tablolar denetlenerek gereksiz tekrar engellenir.
- Gerçekten eski kasalarda doldurma işlemi 100 satırlık gruplarla yapılır; tüm metinler aynı anda belleğe alınmaz.
- 100 MB üstü kasalar açılırken bekleme penceresi gösterilir. Açılışın kasa, şema ve arayüz aşamaları yerel tanı günlüğüne kaydedilir.
- Devam eden 0.3.0 taramasına veya kullanıcı kasasına bakım işlemi uygulanmadı.

## Sınırlar

- Kasa dosyası 8,62 GiB ölçüldü; boş SQLite sayfaları yaklaşık 48 KiB. Tablo bazında boyut dağılımı ölçülmedi; belge içeriği ve şifre raporlanmadı. Kod yapısında çıkartılmış ham metin, dönüştürülmüş metin, iki FTS arama indeksi ve metadata yer kaplayabilir. Kaynak belgelerin kopyaları kasada tutulmaz.
- Gerçek 8,62 GiB kasada 0.3.1 paketli EXE, 30.09.2026 00:42:48'de başladı ve 00:42:50'de `main_window_ready` kaydına ulaştı. Pencere yanıt veriyor. Bu tek açılış ölçümüdür; uzun tarama ve diğer bilgisayar pilotu ayrıca gerekir.
- 0.3.0 ve önceki paketler kullanıcı yeni sürümü gerçek ortamda kabul edene kadar silinmez.

Test ve paket kanıtları: `TESLIM-0.3.1.md`.
