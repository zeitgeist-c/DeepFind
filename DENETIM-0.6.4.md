# Evrakçı 0.6.4 — Temizlik + v9 sonrası denetim (denetim)

Tarih: 16.10.2026. Kaynak: kullanıcı talimatı — "önce temizle, sonra denetle,
düzeltmeler sonrası sürüm üste çıkar". 0.6.3 (kasa boyut optimizasyonu) sonrası
kapanış turu. Kapsam: temizlik (kanıtlı gereksizler) + v9 değişikliğinin
dokunduğu yolların derin denetimi.

## Temizlik (kanıtla)

| Öğe | Kanıt | İşlem |
|---|---|---|
| `rank._files_with`, `rank._intersect` | 0.6.3'te yeniden yazılan `_query` sonrası repo/eval/tests içinde tek referans yok (grep) | Silindi |
| `smoke.py` `ParolaDialog` importu | Dosyada tek geçiş = import satırı; kullanım yok | Silindi |
| `app.py` `ayrac_d`, `QDialogButtonBox`, `QFormLayout`, `QSpinBox`; `archive_ui.py` `QUrl`, `QDesktopServices`, `QDialog`, `QProgressBar`, `time`, `diagnostics`, `card`; `auth.py` `Qt`; `ui.py` `QPen`; `wizard.py` `QStringListModel`, `QFormLayout`; `recovery.py` `json` | AST taraması: import ediliyor, gövdede kullanılmıyor (çoklu geçiş tek başına kanıt değil — AST Name/Attribute analizi) | Importlardan çıkarıldı |
| `eval/frozen_probe*.py` (4), `frozen_bisect.py`, `frozen_faz.py`, `frozen_router.py` | 0.1.0 A8 donma tanısı; sorun 0.1.0'da kapatıldı, hiçbir md/test/CI referans etmiyor, repo-dışı yollara log yazıyorlardı | Silindi (git rm) |
| `Evrakci-0.1.0.spec`, `evrakci-a1-smoke.spec` | 0.1.0 pilotuna ait; `packaging/Evrakci.spec` dışında hiçbir dosya referans etmiyor; a1-smoke repo dışı scratch yoluna işaret ediyor | Silindi (git rm) |

Korunan (bilinçli): `build/`, `dist/`, ZIP'ler (gitignore'lu; dağıtım geri dönüş
kopyaları), `__pycache__` (ignore'lu), md denetim/teslim kayıtları (geçmiş kanıt),
`eval/` çalışır betikler, `maket/` onaylı tasarım kanıtı, `.hermes/` (oturum).

**Doğrulama:** temizlik öncesi 208 test → sonrası 208 test (düşüş yok); AST
import taraması tamamen temiz; ikinci referans taraması kırık import/asset yok;
`pytest --co` 208 toplandı.

## Denetim (v9 dokunduğu yollar)

| # | Kontrol | Sonuç |
|---|---|---|
| 1 | UDF'siz bağlantıyla v9 kasada YAZMA | `no such function: fold` hatası — sessiz bozulma yok, geri dönüş güvenli |
| 2 | UDF'siz bağlantıyla OKUMA (MATCH) | Çalışıyor; indeks katlanmış içerik taşır, okuma UDF istemez |
| 3 | Eski sürüm koruması | `schema_version > 9` reddi `migrate`+`schema`'da aktif; eski sürüm (8 bekleyen) v9 kasayı açamaz |
| 4 | Bütün bağlantı yolları | `app` (8 nokta), `backup`, `recovery`, `cli`, `smoke`, `tasks`, `bootstrap`, `startup` → hepsi `vault.open_vault` (UDF otomatik); harici ham bağlantı kalmadı |
| 5 | Snippet (ham-metin vurgu) | `Şırnak`/`Iğdır` doğrulan birebir vurgulanıyor; folded offset == ham offset korunuyor |
| 6 | Fuzzy/yakınlık yolu | `ıstanbul nufus` → folded sınıfı buldu; öneri altyapısı sözlükten çalışıyor |
| 7 | OR/VEYA, dislama (-terim), tırnaklı kalıp | 4/4 doğru sonuç kümesi (aynı indekste) |
| 8 | Sayfalama (OFFSET) + yıl filtresi + CSV | Doğru sayfalama, doğru yıl filtresi, CSV başlık+3 satır |
| 9 | FTS `integrity-check` | sentetik v8→v9 + canlı kasa: GEÇTİ |

## Kalan risk

- Yeni kuran bir kullanıcı v9 kasayı **eski 0.6.2 sürümüyle** açarsa: kasa
  açılmaz (sürüm koruması) — doğru davranış; 0.6.3+ kurulmalı.
- `fold()` UDF'i Windows Credential/remember akışından bağımsız; kasa şifresi
  olmadan erişim zaten mümkün değil.

## Doğrulamalar

- 208 test geçti (3 kez: temizlik sonrası, import sonrası, final).
- Kaynak smoke 25 kontrol (0.6.3 paket kanıtında).
- Denetim deneyleri bu dosyada listelendi (kanıt: `v9_denetim_udf.py` çıktıları).

Durum: Temizlik kanıtlı yapıldı, v9 yolları denetimde kusur bulunmadı; 0.6.4 teslimi temiz.
