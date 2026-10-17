# Evrakçı 0.8.0 — Denetim: OCR motoru Tesseract → RapidOCR

**Tarih:** 17.10.2026 · **Kapsam:** OCR motoru geçişi, kalite düzeltmeleri, proje temizliği.

## 1. Karar ve kanıt

- WordArc'te kanıtlanan RapidOCR (PP-OCR modelleri, ONNX Runtime) Evrakçı'ya taşındı.
- Ölçüm (bu makine, AMD 5600, Python 3.13): sentetik TR fatura sayfası 300 DPI —
  7/7 satır birebir, ortalama güven 0.991, motor yüklenme 0.65 sn, sayfa çıkarımı 1.27 sn.
- Modeller rapidocr wheel'i içinde gelir (det 1.9 MB + cls + rec ~6 MB): indirme,
  tessdata, SHA pin takibi, çevrimdışı klasör akışı ve sistem Tesseract varsayımı kalktı.

## 2. Kaldırılanlar (kanıtlı, ikili arama ile)

- `ocr.py`: Tesseract alt süreç zinciri (`_run_tess`, `parse_tsv`, `find_exe`,
  `tessdata_dir`, `langs_available`, `models_ok` SHA pinleri), kalite geçişi
  (`quality_of`/`score_of`, GARBLE/REPEAT regex'leri), PSM/döndürme iyileştirme
  denemeleri — RapidOCR'da gereksiz (doğruluk tek geçişte yüksek).
- `ocr_setup.py`: tessdata indirme/bütleme/çevrimdışı akışı; yerini paket içi
  varlık denetimi aldı. UI'da "çevrimdışı klasör seç" düğmesi kalktı.
- Ayarlar → "OCR dili" (tur/eng) kaldırıldı: model tek gövde, dil seçimi yok.
- `spec`/`build.py`: Tesseract exe/DLL/li̇sans gömme kapısı; `Evrakçı-Plan-V4` dışı
  referans temizliği; bayat `lang_compare.py` (yalnız Tesseract içindi) silindi.
- Kök temizlik: DENETIM/TESLIM 0.1.0–0.6.4, kök ZIP'ler, `maket/`, bitmiş
  `PLAN-kasa-boyut-optimizasyonu.md`, bayat `build/` artıkları (git geçmişinde durur).

## 3. Yeni kalite bulguları ve düzeltmeleri

| # | Bulgular | Kanıt | Düzeltme |
|---|---|---|---|
| 1 | PP-OCR dedektörü dev A4 boşluğunda tek satırı kaçırıyor (`detection empty`), 200–300 DPI tam sayfa girdide boş sonuç | varyant matrisi: crop 0.55 sn → tam isabet; crop yok → `[]` | `ocr._crop_content`: içerik sınır kutusu + 24 px pay; yoğun sayfada no-op |
| 2 | `max_side_len=0` rapidocr içinde `ResizeImgError` patlatıyor | doğrudan reproduce | motor varsayılanına dokunulmadı; kırpma akışı bundan bağımsız |
| 3 | Her OCR dosyası taze spawn → import+yükleme dosya başına ~5-8 sn tekrar | oturum dumanı: ilk iş 1.65 sn, ikinci 0.86 sn | `workers.OcrSession`: tarama turunda tek kalıcı işçi; timeout/ölümdeCoordinator taze oturum kurar |
| 4 | Aynı sayfa yeniden OCR'lanınca eski `ocr_page` segmenti silinmiyordu → çift metin | kod incelemesi (INSERT yalnız, DELETE yok) | yazım öncesi sayfa bazlı DELETE |
| 5 | Eski Tesseract dönemi `low/hatalı` ocr_coverage kayıtları RapidOCR'ın okuyabileceği sayfaları sonsuza dek dışlıyordu | coverage SQL (page NOT IN) | `ocr_setup.engine_backfill`: bir seferlik; bozuk coverage satırlarını siler, işi yeniden kuyruğa alır (`ocr_version=a6-1→rapid-1`) |
| 6 | `ensure()` motoru UI sürecinde ısıtıp örneği bellekte bırakıyordu | kod incelemesi | `ensure` sonrası `rapid.reset()` |
| 7 | `method="timeout"` ÖLDÜ: timeout artık spawn bekçisinde (`run_work/OcrSession.call`) — coordinator'daki ölü dallar temizlendi | grep: OcrPage timeout üretilmiyor | ölü `raise/blok` kaldırıldı |
| 8 | `evrakci/queue.py` donmuş pakette stdlib `queue`yu GÖLGELEDİ → urllib3 `queue.LifoQueue` hatası → RapidOCR iç import zinciri (requests) patladı; hata lazy `__getattr__` içinde `cannot import name 'RapidOCR'` olarak maskelendi | paket dumanı traceback'i (`AttributeError: module 'queue' has no attribute 'LifoQueue'`) | `queue.py → job_queue.py`, `sched.py → scheduler.py` yeniden adlandırıldı (sched aynı risk); `rapid.py` iç modülden `from rapidocr.main import RapidOCR` ile maskelenmeye dayanıklı |

## 4. Korunan sözleşmeler

- OCR-01 triyaj (`needs_ocr` eşiği), RAM kapısı (1.5 GB), kontrollü temp + çökme
  artığı temizliği, sayfa/belge bütçeleri, erteleme zinciri (`deferred` →
  `not_before`), dosya govde aramasının OCR'a bağımsız kalması — aynen geçerli.
- `unavailable`/`MODEL_MISSING`/`ENGINE_UNAVAILABLE` kodları ve `reopen_deferred`
  akışı korundu; `prepare_ocr` açılış kapısı aynı yerlerde duruyor.
- Eski `OcrPage.garbage/dpi/langs/attempts` alanları tüketicisiz olduğu için
  kaldırıldı (grep kanıtı: yalnız silinen eval okuyordu).

## 5. Doğrulama

- `pytest tests`: **238 passed** (geçiş öncesi baseline 237; +1 backfill testi,
  motorlu gerçek tanıma testleri RapidOCR ile canlı koşuyor).
- OcrSession dumanı: aynı işçide PDF→PDF→imaj, motor tek yükleme, hızlanma doğrulandı.
- CLI `tani` RapidOCR durumunu raporluyor; tüm modüller import temiz.
- Paket kapısı: `packaging/build.py` PyInstaller çıktısında `_internal/rapidocr/models/*.onnx`
  zorunlu; ek olarak kurulan EXE'ye `--package-smoke` koşturulur (açılış + OCR zinciri
  pakette doğrulanmadan ZIP üretilmez). `license_manifest` rapidocr/onnxruntime/opencv
  metinlerini kopyalıyor.
- `smoke` paketlenmiş EXE'de `recognize_png` ile gerçek tanıma denetliyor.

## 6. Kalan riskler

- Gerçek tarama havuzu (NAS, eğik/karma punto, çok sütun) üzerinde nicelik karşılaştırması
  yapılmadı; backfill sonrası `OCR_LOW_QUALITY` sayıları canlı kasada izlenmeli.
- PP-OCR el yazısını desteklemez (Tesseract da desteklemiyordu; davranış değişmedi).
- Paket boyutu ONNX stack'i ile büyür; ilk sürüm ZIP boyutu build çıktısında kayıtlanır.
