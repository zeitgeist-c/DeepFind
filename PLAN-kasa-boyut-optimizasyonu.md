# Plan: Kasa Boyut Optimizasyonu — Etap 1 (Kanıtlanmış Mimari)

Tarih: 16.10.2026. Hedef: 21,95 GB canlı kasayı ~%40 küçültmek (beklenen: ~12–13 GB),
arama kalitesini **birebir** koruyarak.

## Durum

- **Adım 1-2 tamamlandı** (16.10.2026): Backups'taki yarım WAL artığı (4,3 GB) + eski
  yedek (8,8 GB) silindi. Evrakci klasörü 34 GB → 21 GB.
- Adım 3 (kod değişikliği) planı aşağıda. **Kanıt deneyleri tamamlandı** — mimari
  doğrulandı, artık uygulama aşamasında.

## Mevcut mimari (ölçülmüş)

| Bileşen | Boyut | Satır |
|---|---|---|
| `segments.raw_text` | 4,83 GB | 2.478.310 |
| `segments.folded_text` | 4,71 GB | (aynı satırlar, kopya) |
| `docs_fts` + yardımcıları | ~3–4 GB | — |
| `docs_fts_folded` + yardımcıları | ~3–4 GB | — |
| `scan_scopes` | 0,26 GB | 2.277.834 (17 run) |

Her belge içeriği 3 kopya: raw + folded + iki FTS indeksi.

## Kanıtlanmış çözüm (deney: 27/27 eşleşme, 0 kayıp)

**UDF tabanlı fold trigger'ı:**

1. SQLite'a `con.create_function("fold", 1, nz.folded)` ile Python normalizasyonu
   SQL içine taşınır.
2. `docs_fts` trigger'ları `INSERT ... VALUES (new.seg_id, new.label, fold(new.raw_text))`
   yapar → **FTS indeksine fold edilmiş metin yazılır**, ama `segments.folded_text`
   kolonunda **ayrı kopya tutulmaz**.
3. `docs_fts_folded` tablosu + 4 yardımcı tablosu + 2 trigger tamamen kaldırılır.
4. Sorgu tarafında `rank.py` terimleri `nz.folded()` ile fold edip **tek** `docs_fts`
   üzerinde arar.

**Deney sonuçları** (`fts_udf_cozum.py`, sqlcipher3 3.51.1):
- İstanbul/İSTANBUL/Istanbul/İstanbul → hepsi bulundu
- Iğdır/igdir/IGDIR/ıgdır → hepsi bulundu
- Şırnak/sirnak/ŞIRNAK/şırnak → hepsi bulundu
- ÇANKIRI/çankırı/cankiri, Diyarbakır tüm biçimleri → bulundu
- ıssız/issiz/ISSIZ → bulundu
- DELETE trigger'ı düzgün çalışıyor (external content tutarlı)

**Neden `remove_diacritics 2` tek başına YETERSİZ (kanıtlı):**
`unicode61 remove_diacritics 2` tokenizer'ı `ı` (U+0131) ile `i`'yi eşleştirmiyor:
`'ı'` indekslendiğinde `'i'` araması 0 sonuç veriyor. ğ/ş/ç/ö/ü fold edilirken
Türkçe ı/I/İ üçlüsü bozuluyor. Bu yüzden UDF fold şart.

## Milestone'lar

### M1 — Yazma yolu (yeni kasa)
- `vault.py` `open_vault`: her bağlantıda `con.create_function("fold", 1, nz.folded)`.
- `schema.py` trigger'ları: `seg_ai`/`seg_ad` → `fold(new.raw_text)` yazar.
- `vocab.py` `ensure_v5`: `docs_fts_folded` oluşturma + `folded_text` kolon ekleme
  bloğu kaldırılır (yeni kasalarda hiç oluşmaz).
- `coordinator.py`, `index.py`, `smoke.py` testleri: INSERT'lerden `folded_text` çıkar.

### M2 — Okuma yolu
- `rank.py`: `docs_fts_folded` referansları kaldır; folded arama = `nz.folded(terim)`
  ile `docs_fts` MATCH. Strict/folded puan farkı: strict sorgu orijinal terimle,
  folded sorgu fold edilmiş terimle — **ikisi de aynı indekste**; farklı sonuç
  verirse strict önce, folded sonra (mevcut puanlama korunur).
- `hit_expr` (`instr(s.folded_text, ?)`) → SQL `instr(fold(s.raw_text), ?)` (UDF var)
  ya da Python tarafında hesaplanmış parametre.
- `ai.py`: `s.folded_text` kullanan sorgu → `fold(s.raw_text)`.
- `snippet.py`: folded konum hesabı Python tarafında `nz.folded()` ile.

### M3 — Migration (mevcut kasalar, schema_version 9)
Sıra şart (backup'a karşı `startup.py` otomatik yedek alıyor zaten):
1. `con.create_function("fold", 1, nz.folded)` bağlan.
2. `DROP TRIGGER segf_ai; DROP TRIGGER segf_ad;`
3. `DROP TABLE docs_fts_folded;` (shadow tabloları otomatik düşer)
4. `ALTER TABLE segments DROP COLUMN folded_text;` (SQLite ≥3.35; 3.51 var)
5. Eski `seg_ai`/`seg_ad` trigger'larını `fold(new.raw_text)` yazan yeni sürüme
   değiştir (`DROP TRIGGER` + `CREATE TRIGGER`).
6. `INSERT INTO docs_fts(docs_fts) VALUES('rebuild')` — UDF sayesinde fold edilmiş
   indeks yeniden kurulur.
7. `DELETE FROM scan_scopes WHERE run_id NOT IN (SELECT max(run_id) FROM scan_runs)`.
8. `VACUUM`.

**VACUUM notu:** 21 GB kasa için dakikalar sürer, ~22 GB geçici disk gerekir
(şu an 308 GB boş — yeterli). Uygulama açıkken yapılmaz.

### M4 — Test kapıları
- Mevcut 199 test + yeni: İ/ı/ğ/ş/ç sorguları (yukarıdaki deneydeki 27 vaka
  `tests/test_search.py`'ye folded-search regression olarak eklenir).
- `test_stability_030.py`'nin 2 `folded_text` assertion'ı güncellenir.
- Sentetik eval (`eval/run_eval.py`): holdout top1/top3 ≥ 0.90.
- Boyut kanıtı: migration sonrası `PRAGMA page_count` + dosya boyutu raporu.

## Riskler ve önlemler

| Risk | Önlem |
|---|---|
| UDF bağlantı başına tanımlı olmalı; unutulursa trigger sessiz hata verir | `vault.open_vault` tek noktadan tanımlar; `backup.py` staging bağlantıları da |
| `ALTER TABLE DROP COLUMN` eski SQLite'ta yok | sqlcipher3 3.51.1 — destekli (>=3.35); yine de migration öncesi sürüm kontrolü |
| Rebuild sırasında UDF tanımsızsa yanlış indeks | Migration adım 1'i şart koş; test kapsasını ekle |
| strict/folded puan sınıfı davranışı | M2'de puanlama korunur; eval kapısı doğrular |

## Beklenen kazanç

- `folded_text` kolonu: **4,71 GB**
- `docs_fts_folded` + 4 shadow tablo: **~3–4 GB**
- `scan_scopes` eski run'lar: **~0,25 GB**
- Toplam: **~8–9 GB** → kasa ~**13 GB**'a iner (VACUUM sonrası fiziksel).

## Uygulama sırası

M1 → M2 → testler → M3 (migration kodu + sentetik kasada doğrulama) → M4 →
sürüm 0.6.3. **Canlı kasada migration** ayrı onay ister (VACUUM dakikalar sürer,
o sırada uygulama kapalı olmalı).

## Etap 1 dışı (sonraki etaplar, şimdi değil)
- Segment birleştirme (belge başına tek segment) — daha büyük refactor.
- Metin sıkıştırma (zlib) — CPU maliyeti.
