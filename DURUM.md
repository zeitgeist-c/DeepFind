# Evrakçı — DURUM

## 0.7.0 kendi kendini güncelleme — 17.10.2026

WordArc'ın çalışan güncelleme modeli Evrakçı'ya uyarlandı. Kaynak depo özel
kalır; paketler herkese açık `zeitgeist-c/Evrakci-Releases` deposunda
yayınlanır. Ayarlar → Güncellemeler: durum, denetle, indir ve kur, iptal,
ilerleme. Açılıştan 30 sn sonra günde bir sessiz denetim. İndirme boyut +
SHA-256 ile doğrulanır; ZIP açılışı Zip Slip + manifest sürüm kontrolünden
geçer; bekçi BAT eski sürecin çıkışını bekleyip yeni sürümü `--restarted`
ile açar ve kendini siler. Doğrulamayı geçemeyen paket asla çalışmaz.
Eski klasör/kasa silinmez. Ayrıntı: `DENETIM-0.7.0.md`, `TESLIM-0.7.0.md`.

Doğrulama: **234 test** (26 yeni), paketli EXE smoke 25/25, eval kapısı
geçti (holdout top1=1.0), swap mekaniği gerçek Windows süreçleriyle
kanıtlandı, canlı yayına karşı uçtan uca denetle→indir→doğrula→aç kanıtı
alındı. İlk gerçek otomatik güncelleme bir sonraki sürümde yaşanacak.

## 0.6.4 temizlik + v9 denetim turu — 16.10.2026

0.6.3 sonrası kapanış: kanıtlı gereksizler temizlendi (0.1.0 A8 tanı betikleri,
eski spec dosyaları, kullanılmayan importlar — AST kanıtlı), v9 değişiminin
dokunduğu yollar denetimden geçti (UDF'siz erişim davranışı, sürüm koruması,
snippet/fuzzy/OR/sayfalama yolları, integrity). Bulguların tamamı temiz çıktı;
kod değişikliği gerektiren denetim bulgusu olmadı. Ayrıntı:
`DENETIM-0.6.4.md`.

Doğrulama: **208 test** (3 kez, düşüş yok), AST import taraması temiz, ikinci
referans taraması kırık referans yok.

## 0.6.3 kasa boyut optimizasyonu (şema v9) — 16.10.2026

Kasa üç kopya yerine tek kopya taşıyor: `segments.folded_text` kolonu ve
`docs_fts_folded` tablosu tamamen kaldırıldı. `docs_fts` artık FTS trigger'larında
`fold()` Python UDF'i ile **katlanmış** metin yazıyor; toleranslı arama tek
indekste çalışıyor. `schema_version` 8 → 9.

- **Yazma yolu:** `vault.open_vault` her bağlantıya `fold()` UDF'ini kaydediyor
  (`normalize.install`); `seg_ai`/`seg_ad` trigger'ları `fold(new.x)` yazıyor.
  `index.py`, `coordinator.py`, OCR yolundan `folded_text` parametreleri çıkarıldı.
- **Okuma yolu:** `rank.py` strict+folded sınıflarını tek `docs_fts` üzerinden
  yürütüyor; sınıf kararı ham metinle veriliyor (diakritik aynıysa strict).
  Segment seçimi `instr(fold(s.raw_text), ?)` ile artık LIMIT sonrası çalışıyor.
  `search.py` (v1) terimleri de katlıyor. `ai.py` aynı UDF'i kullanıyor.
- **Kanıtlanan plan sapması:** FTS5 `rebuild` komutu trigger'ları **atlar** ve
  içerik tablosundan ham metin yazar (ölçüldü). Bu yüzden `rebuild_fts`
  `delete-all` + `fold()`lu `INSERT…SELECT` kullanıyor; migration da böyle kuruyor.
- **Migration (`ensure_v9`):** `docs_fts_folded` + `segf_*` trigger'ları düşer,
  indeks katlanmış doldurulur, `folded_text` kolonu silinir (SQLite ≥3.35),
  bitmiş taramaların `scan_scopes` kayıtları temizlenir. Açılışta otomatik koşar;
  startup migration öncesi otomatik yedek alır, hata olursa kasayı geri yükler.
  Eski kasa yeni sürümle açılmazsa koruma: `schema_version > 9` reddi.
- **Fiziksel küçülme:** `evrakci … sikistir` CLI komutu (VACUUM) — uygulama
  kapalıyken; VACUUM migration'a gömülü değil.
- **Doğrulama:** 208 test (yeni: 6 parametrize İ/ı/İ-ğ-ş-ç vakası, strict/folded
  sınıf, tek-kopya şema, v8→v9 migration, integrity-check), kaynak smoke 25
  kontrol, eval holdout top1=1.0 top3=1.0 (p95 1.6 ms). Sentetik boyut kanalı
  (`eval/kasa_boyut_kanit.py`): 200k segmentlik v8 biçimli kasa **918 MB → 424 MB
  (%54)**, migration 37 s, katlanmış sorgu 15 ms, integrity-check GEÇTİ.
  Canlı 21 GB kasa için beklenen ~%40 (plandan iyi).
- **Canlı kasa migration'ı:** ilk açılışta otomatik (yedek + doğrulamalı);
  VACUUM sonrası `sikistir` CLI ile yapılır, uygulama kapalıyken.

## 0.6.2 denetim düzeltmeleri — 15.10.2026

0.6.1 kök kaldırma düzeltmesinin ardından yapılan derin denetimde aynı sınıftan üç
ek kusur bulundu ve kapatıldı:

1. **Dışla da sürücü kökünde eşleşmiyordu:** `exclusions.purge_rule` SQL LIKE'ı kök
   `C:\` için çift ayraç kalıbı arıyordu; canlı kasa ölçümü 112K kayıtta 0 eşleşme.
   Ayrıca SQL wildcard içeren klasör adları yanlış eşleşiyordu. Artık aday daraltma
   kök-ayraç farkındalıklı, kesin karar tekil `is_excluded` ile veriliyor.
2. **Kaldırma/Dışla işlemleri atomik değildi:** kök silinip sözlük yenilemesi
   başarısız olursa kayıtlar yarım kalıyordu. Her iki işlem artık tek transaction:
   hata olursa kök/kural/dosya/sözlük birlikte geri alınır.
3. **Dışla ve tarama/izleme çakışabiliyordu:** Dışla GUI thread'inde senkron koşup
   arayüzü kilitleyebiliyordu ve arka plan mutasyonu varken tarama/kilit/çıkış
   başlayabiliyordu. Dışla `HaricIsci` QThread işçisine taşındı; tarama izleme,
   zamanlayıcı, kilit ve çıkış yolları mutasyon sırasında kapalı; mutasyonlar
   `ScanLock` ile çapraz süreç taramalara karşı da korunuyor.

Ek: hariç temizliği artık sözlükten içerik terimlerini düşürüyor (dosya-adı terimleri
korunur); kök kaldırma tarama izleyicisini yeni kök listesine göre tazeliyor.

Doğrulama: **199 test**, kaynak smoke **25 kontrol**; paketli EXE smoke aynı 25 kontrolle
koşacak. Canlı kasaya dokunulmadı.

## 0.6.1 kök kaldırma düzeltmesi — 15.10.2026

Kullanıcı "Kaynaklar → Kaldır" ile kök kaldırırken uygulama "Yanıt Vermiyor" durumuna
düştü ve kök listeden silinse de indeksteki kayıtlar kaldı. İki kök neden:

1. `exclusions.is_excluded` sürücü köklerinde (C:\, G:\) çalışmıyordu: kök zaten
   ayraçla bittiği için kod çift ayraç (C:\) arıyor, hiçbir dosyayla eşleşmiyordu.
   Canlı kasada C:\ altında 112.019 kaydın 0'ı eşleşiyordu; kaldırma indeks
   boşaltamıyordu.
2. `_kok_kaldir` GUI thread'inde senkron koşuyordu: 112K satır DELETE + 2.48M
   segmentlik sözlük yeniden üretimi arayüzü dakikalarca donduruyordu.

Düzeltme: `is_excluded` kök-ayraç çakışması giderildi (klasör yolları davranışı
korundu); kök kaldırma `KokKaldirIsci` QThread işçisine taşındı — arayüz kilitlenmez,
süreçte buton "Kaldırılıyor…" durumunda ve kilit/çıkış korumalı. Doğrulama: **193 test
geçti** (2 yeni exclusions + 2 yeni UI worker testi dahil).

## 0.5.0 arayüz yenilemesi — 15.10.2026

Kullanıcının arayüzü hiç beğenmemesi üzerine tüm arayüz sıfırdan yeniden tasarlandı. Önce mevcut 16 ekran görüntüsü alınıp piksel ölçümüyle sorunlar kanıtlandı, tasarım maketi onaylandı, birebir uygulandı.

Tek yüzey + kıl payı ayırıcı (kart içinde kart yok), ray iki temada da tema-uyumlu, kod içindeki sabit renkler `theme.pal()` jetonlarına taşındı. Yeni buton takımı, sayfa başlığı şeridi, ölçü şeridi, düz satır delegesi ve pencere içi onay şeridi. Özellik kaybı yok; 7 sekme, arama, etiket, CSV, AI, tarama, geçmiş, yedekler, ayarlar, sihirbaz ve kilitleme aynen çalışıyor.

Doğrulama: **163 test**, son ZIP içindeki gerçek EXE ile **23 paket kontrolü**, iki temada 7/7 sekmenin zemin rengi ölçüldü, 1100–1600 px taşma kontrolü. Ayrıntı: `DENETIM-0.5.0.md` ve `TESLIM-0.5.0.md`.

## 0.4.2 sekme içi tasarım dili — 14.10.2026

Sekme içleri üç sütun işlik düzenine alındı; sol sekmeler ve genel kabuk o sürümde değişmedi. Ayrıntı: `DENETIM-0.4.2.md`.

## 0.1.1 denetim notu — 27.09.2026

Kullanıcının bağımsız denetim ve tasarım yenileme isteğiyle mevcut uygulama yeniden incelendi. Önceki A7/A8 GEÇTİ ifadeleri gerçek NAS, temiz Windows, DPI ve hacim kapılarının geçtiği anlamına gelmez. Bu kapılar halen açıktır. Ayrıntılı bölüm karşılaştırması, düzeltmeler ve kalanlar `DENETIM-0.1.1.md` dosyasındadır.

0.1.1: bütün mevcut ekranların tasarımı, ilk kurulum/şifre doğrulama/değiştirme, arka plan arama ve süreçte önizleme, çok kök indeks güvenliği, Türkçe OCR kodlaması, yedek/rekey/restore staging ve kapanış yaşam döngüsü düzeltildi. Son tam test: **66 geçti**. Son küçük zamanlayıcı koruması ayrıca 6 scheduler testi ve kaynak uygulama smoke akışıyla doğrulandı. Sentetik eval: 74 belge, 83 sorgu; holdout top1/top3=1.0, p95=1.3 ms. Bu 50.000 belge/NAS performans kanıtı değildir.

Paket ve yerel Git kaydı `TESLIM-0.1.1.md` dosyasında raporlanır. Push/Release/deployment yapılmaz. Gerçek DOC içerik desteği, temiz makine, gerçek NAS ve donanım pilotu tamamlanmış sayılmaz. Aşağıdaki 0.1.0 kayıtları tarihsel geliştirme notları olarak korunmuştur.

Son güncelleme: 27.09.2026 (A0 + A1 tamamlandı)

## Aktif aşama
- A0 GEÇTİ, A1 GEÇTİ.
- A2 GEÇTİ (27.09.2026): Varyant A onaylı (sol gezinme + sonuç + sağ önizleme).
- A3 GEÇTİ: kasa→tara→ara uçtan uca (CLI + 3 test). FTS harici-içerik sütun düzeltmesi yapıldı.
- A4 GEÇTİ: kuyruk/retry/kurtarma/kilit/hariç/kayıp (12 test + CLI). Yol ayraç hatası CLI kanıtıyla yakalanıp düzeltildi. DOC: LO yok → ad/yol + önkoşul.
- A5 GEÇTİ (27.09.2026): 74 sentetik belge, 83 sorgu; holdout top1=1.0 top3=1.0 (≥0.90), no-result temiz, p95≈1ms. Sınıflı retrieval (strict/folded/fuzzy) + belge-düzeyi kesişim + yıl/tür filtresi + geçmiş + SHA-256 kopya. 21 test geçti.
- A6 GEÇTİ (27.09.2026): Tesseract CPU hattı (triyaj + 300DPI/12MP + TSV-conf + tek iyileştirme/keep-better + timeout-kill + RAM kapısı + kontrollü temp). Dil ölçümü: tur=1.000, tur+eng=0.820 → varsayılan tur. Rapor: ocr conf 92.4, tepe 114MB, ocr_failed=0. Bütçeler: sayfa/metin/ZIP/hücre/OCR-sayfa kotaları. Ağır OCR eklenmedi (kapı aranmaz). 33 test geçti.
- A7 GEÇTİ (27.09.2026): Varyant A PySide6 arayüz (arama + filtre + sağ önizleme PDF/Excel/Word + kaynaklar/tarama/geçmiş/yedekler/ayarlar/kilit + 6 adımlı sihirbaz + açık/koyu/sistem teması). Şifreli yedek/geri-yükleme (rollback + hariç-kural koruma + 7 saklama) + parola-değiştirme (önce yedek,tırnak-güvenli rekey) + tanı komutu + zamanlayıcı (12:30+cihaz-gecikmesi, catch-up-tek, çift-koşma kilidi, HKCU autostart) + uyku/oturum-kilidinde kasa kilidi. 58 test geçti (backup 11 + sched 6 + ui 8 dahil); eval holdout top1=1.0 top3=1.0 kapı GEÇTİ. Görsel kanıt: açık/koyu ekran görüntüsü + önizleme metin okunurluğu doğrulandı.
- Doğrulanmayanlar (A8 pilota): gerçek monitörde tray simgesi, 125/150/200 DPI, ekran okuyucu, uyku/uyandırma sonrası zamanlayıcı, temiz-makine paketi, 2 PC NAS.
- A8 GEÇTİ (27.09.2026): 0.1.0 kesinleşti. Donmuş onedir kanıtı (init+tara+ara+tani, exit 0). Kök neden: yönlendirici `--kasa` değerini komut sanıp arayüz dalına düşüyordu (asılma + yanlış-dal HMAC izlenimi) → bayrak-değer atlama + regresyon testi. Paket `Evrakçı-0.1.0.zip` (102 MB, sha256 raporlu) + LGPL metni pakette. Yerel commit `729373d` + tag `v0.1.0` (eşleşti). Push/Release/deploy yok. 59 test + eval kapısı GEÇTİ.
- Yapılmayanlar: NAS pilotu + temiz-makine denemesi (erişim yok, kullanıcıda).
- Kapanış: yerel commit + `v0.1.0` (push/release/deploy yok).

## Çalışma ağacındaki düzeltme (commitlenmedi — 29.09.2026)
- OCR'da sayfa başına açılıp kapanan konsol penceresi: `ocr.py` (`_run_tess`, `langs_available`), `ocr_setup.py` (`_engine_check`) ve `doc_adapter.py` (`convert_doc`) artık Windows'ta `CREATE_NO_WINDOW` ile çalışıyor. Doğrulama: `test_ocr.py` + `test_ocr_setup.py` 16 geçti.

## Kilitli runtime adayları (A1 kanıtlı)
- CPython 3.13.15 x64 (birincil) + 3.12.10 (ikincil); sqlcipher3==0.6.2 (cipher 4.12.0 community, FTS5, WAL, şifreli yedek OK).
- pypdfium2==5.13.0, openpyxl==3.1.5, xlrd==2.0.2, python-docx==1.2.0, defusedxml==0.7.1.
- rapidfuzz==3.14.6, Pillow==12.3.0, PySide6-Essentials==6.11.2, pyinstaller==6.22.3.
- Tesseract 5.4.0.20240606 + tur/eng/osd (tur sha256: 489b9504…; eng: 7d4322bd…; osd: 9cf5d576…).
- PyInstaller onedir frozen exe: DB+FTS+PDFIUM+spawn/kill geçti.

## Pilot konumu (repo dışı)
- `…/hermes/cache/scratch/evrakci-a1/`: venv, venv313, smoke_db.py, smoke_ext.py, pkg_app.py, dist/.
- Repo'ya kod girmedi; plan belgeleri değişmedi; push/release yok.

## Kullanıcıdan bekleyen (karar)
1. DOC zorunluluğu: KAPSAMDA — adaptör denenecek (27.09.2026 kullanıcı kararı).
2. Disk temp türev kabulü: KABUL — kontrollü temp (27.09.2026 kullanıcı kararı).
3. Sorunlu dosyalar listesi: yol + hata nedeni + aç (29.09.2026 kullanıcı isteği, sonraya kaldı).
4. Dosyaya elle not/içerik girişi: aramada çıkar, yeniden taramada silinmez, ayrı saklanır (29.09.2026 kullanıcı isteği, sonraya kaldı).

## Bilinen sınırlar
- Temiz makine (Python/Office yok) + 8 GB RAM + Win10 + 2 PC NAS testi: A8'e kaldı.
- sqlcipher3/rapidfuzz/Pillow lisans metni A8'de dosyadan doğrulanacak.
- PySide6 LGPL dağıtım yükümlülüğü A8'de kapatılacak.
