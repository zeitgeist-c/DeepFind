# Evrakçı 0.6.3 — Kasa boyut optimizasyonu teslimi

Tarih: 16.10.2026. Kapsam: [DENETIM-0.6.3.md](DENETIM-0.6.3.md) ve
[PLAN-kasa-boyut-optimizasyonu.md](PLAN-kasa-boyut-optimizasyonu.md) (Etap 1).

Kasa içeriği artık tek kopya: `segments.folded_text` kolonu ve `docs_fts_folded`
tablosu kaldırıldı; `docs_fts` tek indekste katlanmış metin taşıyor
(şema v9, `fold()` UDF'li trigger'lar). Beklenen ~%40 küçülme; sentetik kanıt
%54 (918 MB → 424 MB).

- Tam test paketi: **208 geçti** (yeni: 27 vakalık İ/ı/İ-ğ-ş-ç katlanmış arama
  regresyonu, strict/folded sınıf, tek-kopya şema, v8→v9 migration + integrity).
- Kaynak smoke: **25 kontrol**. Paketli EXE smoke: aynı 25 kontrol.
- Eval kapısı: holdout top1=1.0 / top3=1.0, p95 1.6 ms.
- Boyut kanalı: `eval/kasa_boyut_kanit.py` (migration 37 s / 200k segment,
  katlanmış sorgu 15 ms).
- EXE FileVersion/ProductVersion **0.6.3**; BAT aynı sürüm EXE'sini çalıştırır;
  manifest 0.6.3.
- `Evrakçı-0.6.3.zip`: **169.624.208 bayt**. SHA-256:
  `264e7875d15bbdcaa018209ebf14483e55d5a6fe453511cdda06963e833a5ecb`. ZIP CRC
  doğrulanmış; paketli EXE smoke 25/25 GEÇTİ.
- Yeni CLI: `evrakci --kasa <yol> sikistir` — VACUUM ile fiziksel küçülme
  (uygulama kapalıyken; ~kasa boyutu kadar geçici disk ister).

## Canlı kasa sonucu (16.10.2026, kullanıcı onayıyla)

`C:\Users\user\AppData\Local\Evrakci\Data\evrakci.db` — migration + VACUUM
koştu: **20,44 GB → 8,62 GB (%58 küçülme)**; migration 4036 s, VACUUM 753 s,
2.478.310 segment, `schema_version=9`, `folded_text` yok, `docs_fts_folded` yok,
`integrity-check` OK. Canlı arama doğrulaması: "istanbul" strict, "sırnak"→sirnak
folded sınıfıyla bulundu.

## Kullanıcı için akış (canlı kasa, 21 GB)

1. Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp EXE/BAT'ı çalıştırın.
   EXE ve `_internal` birlikte yenilenmelidir.
2. İlk açılış: açılış ekranı "İndeks yapısı güncelleniyor…" aşamasında migration
   otomatik koşar. Öncesinde otomatik yedek alınır; hata olursa kasa geri
   yüklenir. 21 GB kasada birkaç dakika sürebilir — pencereyi kapatmayın.
3. Uygulamayı kapatın, sonra küçülmeyi uygulayın:
   `Evrakçı-0.6.3.exe --kasa "<kasa yolu>" --sifre "<sifre>" sikistir`
   (boyut ölçümü çıktıya yazılır: `once=.. GB sonar=.. GB`).

NOT: Canlı kasada migration + VACUUM bu teslimle birlikte koştu (yukarıdaki
canlı sonuç). Yeni ZIP'i kurduğunuzda kasa zaten v9 olduğundan açılışta ek
geçiş çalışmaz; `sikistir`a da gerek kalmaz.

Yerel commit ve `v0.6.3` etiketi bu teslimle oluşturulur. Push/Release ayrı
yetkiyle yapılır. Bu teslimde canlı kasaya dokunulmadı.
