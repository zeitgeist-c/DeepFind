# Evrakçı 0.6.3 — Kasa boyut optimizasyonu şeması (denetim)

Tarih: 16.10.2026. Kaynak: `PLAN-kasa-boyut-optimizasyonu.md` (Etap 1) uygulaması
sırasında bulunan ve kanıtlanan kusurlar. Kasa üç kopya (raw + folded kolon + iki
FTS) yerine tek ham kopya + tek katlanmış FTS taşıyor (şema v9).

## Bulgular (kanıt)

### 1. FTS5 `rebuild` trigger'ları atlar — plandaki migration adımı yanlış (P1, kritik)

Plan M3 adım 6 `INSERT INTO docs_fts(docs_fts) VALUES('rebuild')` ile katlanmış
indeksin yeniden kurulacağını varsayıyordu. Deney (sqlcipher3 3.51.1,
`v9_probe.py`/`v9_probe2.py`): `rebuild` trigger'a **girmez**, içerik
tablosundan **ham** metin okur. Kanıt: fold'lu trigger + `rebuild` sonrası
`"sirnak"` eşleşmesi 0, ham `"Şırnak"` eşleşmesi 1. Yani plan uygulansaydı
migration sonrası toleranslı arama sessizce bozulurdu.

**Düzeltme:** `schema.rebuild_fts` artık `delete-all` + `INSERT … SELECT
fold(label), fold(raw_text)` kullanıyor; migration da aynı yolu izliyor.
`delete-all` + fold'lu dolum iki turda idempotent doğrulandı, silme trigger'ı ile
`integrity-check` GEÇTİ.

### 2. `fold()` UDF'i bağlantı bazlı — unutulursa yazma sessiz bozulurdu (P1)

UDF tanımsızken trigger'lı INSERT `no such function: fold` ile **hata veriyor**
(kanıt; sessiz değil — iyi). Risk, hata alan yolun kısmi kalmasıydı.

**Düzeltme:** tanım tek noktadan `normalize.install(con)`; `vault.open_vault` her
bağlantıda çağırır. Test/CLI köklerinden gelen ham `sqlite3` bağlantıları için
`index_entry`, `run_scan`, `search_ranked`, `prepare_question` kendi
bağlantılarına `install` eder (savunma katmanı). `install` idempotent: ikinci
`create_function` aynı bağlantıda `Error creating function` verdiği için önce
deneme sorgusu yapılır (yakalanan kusur: `test_ai` stdlib sqlite akışı).

### 3. strict/folded sınıf kararı tek indeksle geçersizleşti (P2, ürün davranışı)

Eski akış "strict"i ham `docs_fts` eşleşmesinden, "folded"i ikinci indeksten
türetiyordu. Tek katlanmış indekste "İstanbul" sorgusu da "istanbul" da aynı
eşleşmeyi veriyor; kapı sınıfı anlamını yitirdi (`test_src01` strict yerine
folded döndürdü).

**Düzeltme:** sınıf kararı ham metne taşındı — sorgunun `tr_lower` token kümesi
seçilen segment+adın ham metninde aynen geçiyorsa `strict`, geçmiyorsa `folded`;
tırnaklı (kalıp) sorgularda eski kapı davranışı korunur. `test_src01/src02`
yeniden geçti; eval holdout top1/top3 = 1.0.

### 4. `rank._query` SQL yeniden yazımı: parametre sırası ve tabma takması (P2)

Segment seçimi eskiden `chosen` CTE'sinde `LIMIT`'ten önce `hit_expr`
çalıştırıyordu; fold artık SQL UDF'i olduğundan bu, LIMIT'ten **önce** tüm
adaylarda Python'a girer (canlı 21 GB kasada duraklama riski).

**Düzeltme:** SQL iki aşamaya alındı — önce dokuman sayfası (`picked`, LIMIT
uygulanan), sonra segment seçimi. `hit_tokens` argümanı SQL'deki gerçek
konumuna (LIMIT/OFFSET'ten sonra) taşındı; yanlış sıra `datatype mismatch` ile
yakalandı ve düzeltildi. İç alt sorgu tabma `s2` ile netleştirildi
(`no such column: s.raw_text` ile yakalandı). Katlanmış sorgu süresi 200k
segmentte 15 ms ölçüldü.

### 5. Eski (v1) `search.search` katlamıyordu (P3)

`build_match` terimleri ham yazıyordu; katlanmış indekste Türkçe diakritikli
arama (test_vertical: "Ayşe") boş dönebiliyordu. Terimler artık
`nz.folded()` ile kuşatılıyor.

### 6. Sözlük yeniden kurumu `folded_text` okuyordu (P3, migration sonrası kırılırdı)

`rebuild_vocab`/`remove_files_from_vocab` `SELECT folded_text FROM segments`
kullanıyordu; kolon migration'da düştüğü için patlardı. Ham `raw_text` üzerine
`nz.tokens_folded()` ile aynı sonucu veriyor (fold, tokenlaştırmada zaten
uygulanıyordu).

## Ölçülen sonuç

`eval/kasa_boyut_kanit.py` — 200.000 segment (~1 KB/seg), v8 biçiminden:

- kasa: **918 MB → 424 MB (%54 küçülme)**
- migration: 37 s · katlanmış sorgu: 15 ms · `integrity-check`: GEÇTİ
- şema: `folded_text` yok, `docs_fts_folded` yok, `schema_version=9`

Canlı 21 GB kasa için plan bekleneni ~%40'tı; bileşen oranları aynı olduğundan
gerçek kazancın plandan iyi olması bekleniyor.

## Kapsam dışı (bilinçli)

- Segment birleştirme ve zlib sıkıştırma: planın sonraki etapları.
- VACUUM migration'a gömülmedi — `sikistir` CLI komutu, uygulama kapalıyken.
- Canlı kasa migration'ı ayrı onay ister: ilk açılışta otomatik koşar, öncesinde
  startup otomatik yedek alır ve hata olursa kasayı geri yükler.
