# Evrakçı — DURUM

## 0.10.5: tarama sonu sözlük beklemesi ve boş sayfalar — 21.10.2026

Sözlük ham arşivi tekrar okumak yerine FTS terim/frekansını kullanır; değişmeyen
içerikte atlanır. İlerleme/iptal eklendi. Tamamen beyaz sayfalar OCR hatası
sayılmaz; eski NO_TEXT hataları bir kez yeniden kontrol edilir. 421 sayfalık
verilen kitabın kopyası ayrı kasada Vulkan ile 73,21 sn; sözlük 0,281 sn;
değişmeyen ikinci tarama 0,0071 sn ölçüldü ve 1/1 tamamlandı. Canlı büyük kasa
süresi ayrıca doğrulanmadı. Ayrıntı TESLIM-0.10.5.md.

## 0.10.4: eksik embedding şeması ve tarama doğruluğu — 21.10.2026

Güncel şema işaretli eski kasalarda bulunmayabilen embeddings tablosu ve
indeksi eklemeli hazırlanır; FTS ve mevcut vektörler korunur. Kalıcı başarısız
belgeler genel tarama sonucunda da eksik sayılır. Yanlış boyutlu vektörler
yeniden üretilir. Başarısız regresyonla yeniden üretim ve şifreli kasa testleri
yapıldı. Paket kabulü eski kasa onarımından sonra gerçek vektör yazımını da
sınar. Kanıt ve canlı kasa sınırı TESLIM-0.10.4.md içindedir.

## 0.10.3: taramada belge sayımı ve ilerleme — 21.10.2026

Seçili kaynakların tümünde önce envanter çıkarılır; içerik/OCR/embedding sonra
başlar. Sabit toplam üzerinden tamamlanan/kalan belge ve yüzde gösterilir.
Ayrı aşama çubuğu ve aşamanın hızından kalan süre tahmini bulunur; duraklama
tahmini şişirmez. Erişilemeyen klasör varsa envanter eksik olarak etiketlenir.
Sayım görüntüsü tekrar kullanılır ve işlem sonunda temizlenir. Kanıt ve
kabul sınırları TESLIM-0.10.3.md içindedir.

## 0.10.2: her açılışta indeks yeniden kurma hatası — 21.10.2026

Kök neden: ensure_current → ensure_v8 güncel 9 sürümünü 8 yapıyor, ensure_v9
bunun üzerine FTS indeksini yeniden kuruyordu. Şema işaretleri artık yalnız
yükselir. Tamamlanmış v9 şekli ve trigger/FTS işaretleri eski bir sürüm
işaretinden onarılır; güncel kasada yeniden kurma yapılmaz. Gerçek dönüşüm
256 bölümlük atomik partilerle ölçülür, aşama yüzdesi ve yaklaşık kalan süre
gösterilir. Kanıt ve kabul sınırları TESLIM-0.10.2.md içindedir.

## 0.10.1: kurulum ve güncelleme — 21.10.2026

Model setup içinde gelir ve programın `_internal/embedding` dizinine kurulur.
Güncelleme aynı AppId/dizini kullanır; eski PE sürümü doğrulanan EXE/BAT çiftleri
başarılı kurulumda temizlenir. Sağlam model tekrar kopyalanmaz, eski ProgramData
modeli doğrulanarak taşınır; eksik/bozuk model tam setup ile onarılır.
Modern istemci kurulum EXE'si olmayan ZIP yayınına düşmez. Eski ZIP istemcilerden
geçiş için tam setup bir kez çalıştırılır. Düzeltmeler 0.10.1, 0.10.2, 0.10.3 şeklindedir.

Gerçek izole Inno yükseltme/model taşıma/onarma/temizlik/kaldırma kabulü ve
kurulu EXE smoke geçti: `build/installer-acceptance-0.10.1.json`. Canlı kurulum
ve kasa test için değiştirilmedi. Son test/paket kimliği `build/release-0.10.1.json`;
kapsam ve sınırlar `TESLIM-0.10.1.md`.

## 0.10.0: EmbeddingGemma 2 yerel motor ve sade dağıtım — 21.10.2026

Gemini yardımcısı kaldırıldı; bağımsız anlamsal adaylar FTS ile birleşir.
Q8_0 GGUF, paylaşılan llama.cpp süreci, Vulkan/CPU ve isteğe bağlı CUDA motoru,
çevrimdışı model dağıtımı ve installer tabanlı güncelleme eklendi.
OCR, kasa, kaynaklar, önizleme ve yedekleme korunur.

Tam test: 292 geçti, 1 atlandı. Gerçek AMD RX 6650 XT Vulkan ve CPU kabulü,
izole AppId ile 0.9→0.10 installer yükseltmesi ve modelin tekrar
kopyalanmadığı güncelleme provası geçti. NVIDIA donanımı bulunmadığından
CUDA gerçek çalışma kabulü açık. Son paket/commit/etiket kapısı
TESLIM-0.10.0.md ve build/release-0.10.0.json ile izlenir.
Canlı kasa/kurulum üzerinde deneme veya harici yayın yapılmadı.

## 0.9.0 sürüm kaydı: yerel vektör araması (hibrit FTS + EmbeddingGemma-2) — 21.10.2026

Sürüm yükseltmesi: `0.8.1 → 0.9.0` (yeni yetenek; `src/evrakci/version.py` tek
kanonik kaynak). İçerik: EmbeddingGemma-2 metin kulesi (ONNX + DirectML, 271M),
hibrit arama, gömme kuyruğu + alt süreç yalıtımı, model dağıtıcısı.

- **Hız (ölçülen):** GPU 3 belge 86 ms, CPU yedek 280 ms; tam model CPU'da elendi.
- **Doğrulama:** 294 test (272 → 294), paket kapısı 26/26, donmuş EXE dumanı OK.
- **Paket:** `Evrakçı-0.9.0.zip` = 216.371.605 bayt, SHA-256
  `3aafa8ae…3918ca7242`. Model ilk açılışta indirilir (1 GB, sha sabitli).
- **Yayın:** `zeitgeist-c/Evrakci-Releases` → v0.9.0 (Latest). Ayrıntı: `TESLIM-0.9.0.md`.
- Sınırlar: "AI ile ara" (Gemini) aynen durur; model yokken arama FTS'ye düşer.

## 0.8.1 sürüm kaydı: DMS arayüz desenleri (M1–M5) — 17.10.2026

Sürüm yükseltmesi: `0.8.0 → 0.8.1` (yalnız yama hanesi; `src/evrakci/version.py`
tek kanonik kaynak). İçerik: açık kaynak DMS'lerin tersine mühendislik analizi
(`REA-DMS-Analizi.md`) sonucu uyarlanan beş arayüz çalışması:

| Milestone | İçerik | Test katkısı |
|---|---|---|
| M1 | Küçük resim hattı: yerel önbellek + üretim işi + liste/detay görselleri | +13 |
| M2 | Görüntüleyici: yakınlaştırma kademeleri, sayfa rayı, klavye, belge gezinmesi | +4 |
| M3 | Filtre çipleri, görünüm modları (kompakt/satır/ızgara), gösterilecek alanlar | +3 |
| M4 | Çoklu seçim + toplu etiket (tek işlem) + seçim CSV'si | +3 |
| M5 | Sorgu sözdizimi (`yil:`/`tur:`/`etiket:`/`klasor:`) + satır içi doğrulama | +12 |

Doğrulama: **272 test** (237 → 272), tam paket çıkış kodu 0; iki temada ekran
görüntüsü kanıtı (`build/review-ui-0.8.1/`). Bu turda beş gerçek kusur bulunup
kapatıldı: Qt iş parçacığı yok etme çökmesi, sığdırma kutusu taşması, görünür
kalan filtre çipleri, alan sözdiziminde sonuç eşleştirme hatası, küçük resim
yükleyicisinin pencere kapanışında yok edilmesi.

Sınırlar/notlar:
- Paket kapısı: `eval/package_check.py` **25/25 GEÇTİ** (gerçek EXE ile açılış +
  tarama akışı); `Evrakçı-0.8.1.zip` = 154.520.305 bayt, SHA-256
  `15f8f938…722fe`. Ayrıntı: `TESLIM-0.8.1.md`.
- **Halka açık yayın (indirme linki):** `zeitgeist-c/Evrakci-Releases` → v0.8.1
  (Latest) → https://github.com/zeitgeist-c/Evrakci-Releases/releases/tag/v0.8.1
  · Kurulu 0.7.0/0.8.0 sürümleri güncelleyiciyle doğrudan bu sürüme atlar;
  `/releases/latest` doğrulaması sürüm/boyut/özeti birebir gördü.
- `eval/ui_shots.py` kapanışta 0xC0000409 ile düşüyor; temel çizgide de aynı,
  görüntüler sorunsuz üretiliyor.
- `LISANSLAR.md` bağımlılık değişmediği için 0.8.0 içeriğiyle geçerli.

## M5 sorgu sözdizimi + satır içi doğrulama (REA/DMS deseni) — 17.10.2026

Desen kaynağı: docspell `PowerSearchInput` — yazarken çözümle, hatalı girdide
konumu (şapka) göster, geçersiz sorguda aramayı çalıştırma.

- **Yeni `sorgu.py`** (saf işlev): `alan:değer` çözümleyicisi. Alanlar arayüzdeki
  filtrelerle aynı: `yil:` (4 hane), `tur:` (`pdf` → `.pdf`), `etiket:`
  (tırnak boşluk taşır: `etiket:"vergi 2024"`), `klasor:`. Alan adları Türkçe
  harf katlamasına dayanıklı (`yıl` = `yil`). Alan dışı sözcükler serbest metin
  olur; hata → mesaj + imleç konumu.
- **Arayüz:** arama kutusunun altında satır içi uyarı (`Sorgu hatası: …` + sorgu
  satırı + `^`); hatalı sorguda **arama koşmaz, önceki sonuçlar korunur**.
  Geçerli alanlar filtre denetimlerini besler ve mevcut çip/sayaç akışında
  görünür; kutu ipucu sözdizimini tanıtır.
- **Sahiplik kuralı:** sorgu yalnız **kendi kurduğu** alanı temizler — kullanıcının
  elle girdiği filtre, sorgu metni değişti diye silinmez; sorgudan çıkarılan alan
  geri alınır.
- **Bulunan ve düzeltilen gerçek hata (test kanıtı):** sonuç eşleştirmesi ham kutu
  metniyle karşılaştırıldığı için alan sözdizimi kullanan aramaların sonucu
  düşürülüyordu (0 sonuç). Eşleştirme artık çözülen serbest metinle yapılıyor.
- **Sınır (bilinçli):** yalnız alan verilen sorguda (ör. `yil:2024`) liste boş
  kalır; kullanıcı "bir sözcük de yazın" diye yönlendirilir (mevcut "boş sorgu
  listelemez" kuralı korunur).
- Doğrulama: **272 test** (12 yeni: 10 çözümleyici + 2 arayüz akışı; tam paket
  çıkış kodu 0). Görsel kanıt: `ara-sorgu-{acik,koyu}.png` (geçerli alan sorgusu)
  ve `ara-sorgu-hata-{acik,koyu}.png` (imleçli hata, eski sonuçlar duruyor).
- REA planı (M1–M5) tamamlandı. Sonraki adım: sürüm kapısı (paket + lisans +
  temiz makine) ve kullanıcı onayıyla commit. Commit/push yok.

## M4 çoklu seçim + toplu işlem (REA/DMS deseni) — 17.10.2026

Desen kaynakları: paperless-ngx seçim denetimleri (None / Select page / Select
all + seçim rozeti) ve toplu düzenleme; docspell çoklu düzenleme menüsü.

- **Çoklu seçim:** sonuç listesi ve ızgara `ExtendedSelection` (Ctrl/Shift tık);
  "Hiçbiri / Sayfa (ilk 50) / Tümü" düğmeleri ve "N seçili" rozeti. İki görünüm
  ayrı seçim tuttuğu için görünüm değişiminde etkin olmayan yüzeyin seçimi
  temizlenir; panel/önizleme etkin yüzeyin geçerli satırını izler.
- **Toplu etiket:** `rank.tags_many` tek işlemde tüm satırları yazar, hata olursa
  `rollback` (yarı uygulanmış toplu işlem kalmaz). Arayüz akışı `archive_ui.job`
  ile yazılabilir bağlantıda koşar; başarıda toast + arama tazeleme, hatada
  "işlem geri alındı" uyarısı.
- **Seçimi CSV:** yalnız seçili sonuçlar indirilir (tüm sonuçlar için mevcut
  "CSV indir" korunur).
- **Bulunan ve düzeltilen gerçek kusur (görsel kanıtla):** çip listesi
  yeniden kurulurken eski `Cip` widget'ları `deleteLater` ile bekletiliyor ve
  layout'tan çıksa da görünür kalıp altındaki filtre alanının üzerine biniyordu;
  artık gizlenip ebeveyninden ayrılıyor. Regresyon testi: pencere altındaki
  `Cip` örnekleri ile aktif çip sayısı eşit olmalı.
- Doğrulama: **260 test** (3 yeni: toplu etiket ekle/kaldır + boş etiket
  sözleşmesi, hata sözleşmesi (tek commit + rollback), arayüzde seçim/toplu
  etiket/seçim CSV'si). Görsel kanıt: `ara-secim-{acik,koyu}.png` (seçim
  denetimleri + toplu işlem çubuğu) ve düzeltilmiş `ara-filtre-*.png`.
- Sıradaki: M5 sorgu sözdizimi. Commit/push yok (kullanıcı onayı beklenir).

## M3 filtre çipleri + görünüm modları (REA/DMS deseni) — 17.10.2026

Desen kaynakları: paperless-ngx filtre çubuğu (kaldırılabilir filtre rozetleri,
tek tuşla "Filtreleri sıfırla", etkin filtre sayısı), görünüm anahtarı
(tablo/kart) ve "Göster" (display fields) menüsü.

- **Filtre çipleri:** aktif filtreler "Filtreler" başlığının altında
  kaldırılabilir çip olur (`ui.Cip`); `×` yalnız o filtreyi düşürüp aramayı
  yeniler. Etkin filtre sayısı rozeti ve "Filtreleri sıfırla" düğmesi yalnız
  filtre varken görünür. Çipler arama sonucundan bağımsız olarak filtre
  değişiminde tazelenir (boş sorguda da görünür).
- **Görünüm modları:** Kompakt / Satırlar / Izgara düğmeleri; mod kasada
  saklanır (`gorunum_modu`) ve kasa açılışında geri yüklenir. Izgara, aynı
  modeli paylaşan `QListView.IconMode` yüzeyi + `ui.GridDelegate` (üstte
  küçük resim, altta ad + tek satır) kullanır; seçim/çift tık/önizleme her iki
  yüzeyde de çalışır (`_aktif_gosterim`).
- **Gösterilecek alanlar:** "Göster" menüsünde Yol / Tür ve etiket / İçerik
  özeti / Etiketler anahtarları; satır metni seçime göre yazılır, ayar
  `goster_alanlari` olarak saklanır (boş ayar = yalnız ad). İpucunda yol ve
  özet korunur; ızgarada alan seçimi kapatılır.
- Doğrulama: **257 test** (3 yeni: çip kaldırma + yeniden arama + sıfırlama,
  görünüm modu kalıcılığı + kompakt/ızgara yüzeyi, gösterilecek alanların
  satır/ayar etkisi). Görsel kanıt: `ara-filtre-{acik,koyu}.png` (çip + sayaç +
  sıfırla) ve `ara-izgara-{acik,koyu}.png` (ızgara kartı).
- Not: satır metni üretimi tek yerde (`_satirlari_yaz`) toplandı; durum notu
  (kısmi/erişilemiyor) alan seçiminden bağımsız olarak korunur.
- Sıradaki: M4 toplu işlem (seçim + toplu etiket/CSV), M5 sorgu sözdizimi.
  Commit/push yok (kullanıcı onayı beklenir).

## M2 görüntüleyici derinleştirme (REA/DMS deseni) — 17.10.2026

Desen kaynakları: paperless-ngx yakınlaştırma kademeleri ("Sayfaya sığdır" +
yüzde kademeleri) ve belge görüntüleyici; papermerge `PageList` (sayfa küçük
resmi rayı); paperless "önceki/sonraki belge".

- **Yakınlaştırma kademeleri:** Genişliğe sığdır (varsayılan), Sayfaya sığdır,
  %50–%200. İşçi, istenen yoğunlukta ya da sığdırma kutusuna göre **tek**
  render yapar (çift render yok). `−/+` düğmeleri kademe adımlar; `0` tuşu
  %100'e döner.
- **Sayfa rayı:** solda dikey küçük resim şeridi; 12'lik gruplarla **tembel**
  üretim (kaydırdıkça sonraki grup), tıklayınca sayfaya gidiş, geçerli sayfa
  vurgusu. Küçük resimler M1 önbellek hattını `pN` anahtarıyla kullanır.
- **Klavye:** ←/→, ↑/↓, PageUp/PageDown sayfa; `+/-` kademe; `0` %100; Esc
  pencereyi kapatır (QDialog).
- **Belge gezinmesi:** önizleme penceresinde "‹ Önceki belge / N / M / Sonraki
  belge ›" — arama sonuçlarındaki sıraya göre.
- **İndeks metni:** düğme artık sayfa görüntüsü ↔ OCR/indeks metni arasında
  gidip gelir (metin görünümünden geri dönüş eklendi).
- **Sığdırma tazeleme:** tuval görüntü alanı değişince (ray görünmesi, pencere
  boyutu, kaydırma çubuğu) sığdırma kutusu **yalnız gerçekten değiştiyse**
  yeniden render edilir — naif "her boyut değişiminde render" döngüsü engellendi.
- **Bulunan ve kapatılan gerçek kusur (test kanıtı):** koşan bir `QThread`
  nesnesi pencereyle birlikte yok edilirse Qt süreci düşürüyordu
  (0xC0000409). `AnaPencere.closeEvent` küçük resim yükleyicilerini senkron
  durduruyor ve önizlemeyi kapatıyor; `Onizleme.closeEvent` render iş
  parçacıklarını bekliyor; test fixture'ı da yükleyiciyi durduruyor.
- Doğrulama: **254 test** (4 yeni: zoom kademeleri, sayfa rayı + klavye, indeks
  metni gidiş-dönüş, önceki/sonraki belge; tam paket çıkış kodu 0). Görsel
  kanıt: `build/review-ui-0.8.0/onizleme-{acik,koyu}.png` (sayfa rayı, kademe
  seçici, sayfa render'ı); `eval/ui_shots.py` artık önizleme penceresini de
  yakalıyor.
- Bilinen sınır: her ray grubu kendi kalıcı işçi oturumunu açar (12 sayfa);
  sığdırma render'ı 8 MP ile sınırlı.
- Süren not: `eval/ui_shots.py` kapanışta 0xC0000409 ile düşüyor; değişiklik
  öncesi temel çizgide de aynı (M1/M2 kaynaklı değil), görüntüler üretiliyor.
- Sıradaki: M3 filtre çipleri + görünüm modları, M4 toplu işlem, M5 sorgu
  sözdizimi. Commit/push yok (kullanıcı onayı beklenir).

## M1 küçük resim hattı (REA/DMS deseni) — 17.10.2026

Üç açık kaynak DMS'in (paperless-ngx, papermerge-core, docspell) tersine
mühendislik analizi yapıldı; desen envanteri, kanıt referansları ve uyarlama
planı `REA-DMS-Analizi.md` dosyasında (M1–M5). Kaynak öncelikli REA kuralı
uygulandı: hedefler açık kaynak olduğu için binary/REA CLI analizi yerine depo
kaynağı okundu (`doctor` çıktısı kanıt olarak kayıtlı; native motorlar kurulu
değil ve gerekmedi).

**M1 — görsel katalog deneyimi (tamamlandı):**
- `thumbs.py`: (yol, boyut, mtime) anahtarlı yerel önbellek
  (`%LOCALAPPDATA%\Evrakçı\thumbs`), Qt+Pillow yeteneğine göre biçim seçimi
  (webp → jpg geri düşüş), 4000 dosya sınırında yaşlandırma (`buda`), arka
  planda sıralı üretim (`OnbellekYukleyici`).
- `workers.py`: `thumb` işi (pypdfium2 ile ilk sayfa ~2x render + Pillow
  küçültme; görsellerde EXIF yönü) ve tekrarlı işler için kalıcı işçi
  (`WorkerSession`). Hedef dizin yoksa oluşturulur.
- Arayüz: sonuç satırlarında (`CardDelegate(thumb=True)`) ve "Taranmış
  Evraklar" listesinde küçük resim; "Seçili evrak" panelinde kutuya uyan ve
  ölçeklenen büyük önizleme (`ui.GorselKutusu`, `QLabel#thumbBox` jetonu).
  Üretim başarısızsa satır simge yer tutucusunda kalır (akış bozulmaz).
  Sinyaller bağlı metoda bağlı: `QPixmap` yalnız GUI iş parçacığında kurulur.
- Doğrulama: **250 test** (13 yeni: önbellek anahtarı/biçim/buda/temizleme,
  worker üretimi ve hata yolu, yükleyici önbellek ve eksik dosya yolu, UI'da
  satır+panel görseli ve düzen çakışmasızlığı, kaynak dizine dokunmama).
  Görsel kanıt: `eval/ui_shots.py` açık/koyu — satır küçük resmi, panel
  önizlemesi ve taşma düzeltmesi ekran görüntüleriyle doğrulandı
  (`build/review-ui-0.8.0/`).
- Not: `eval/ui_shots.py` bu ortamda kapanışta `0xC0000409` ile düşüyor;
  aynı kod **değişiklik öncesi temel çizgide de** aynı kodla düştü (stash ile
  ölçüldü) — M1 kaynaklı değil, ekran görüntüleri sorunsuz üretiliyor.
  Paket kapısında (bir sonraki sürüm) donmuş EXE'de bir küçük resmin
  üretildiği ayrıca doğrulanmalı (Pillow WebP eklentisi).
- Sıradaki: M3 filtre çipleri + görünüm modları, M4 toplu işlem, M5 sorgu
  sözdizimi. Commit/push yok (kullanıcı onayı beklenir).

## 0.8.0 OCR motoru: RapidOCR — 17.10.2026

Tesseract 5 zinciri tamamen kaldırıldı; yerini RapidOCR 3.10 (PP-OCRv6
det/rec + yön sınıflandırıcı, ONNX Runtime 1.30) aldı. Kanıt: WordArc'te
4/4 tam isabet sonrası Evrakçı ölçümü — 7/7 satır hatasız, güven 0.991,
yüklenme 0.65 sn, sayfa başına ~1-3 sn. Modeller rapidocr paketiyle gelir:
indirme, tessdata, sistem kurulumu yok. Eski "OCR dili" ayarı kalktı
(model Türkçe+İngilizce tek gövde). Kalite düzeltmeleri: içerik kırpma
(PP-OCR dev boşlukta küçük metni kaçırıyordu — tek satır A4'te boş sonuç
saptandı ve giderildi), tarama başına tek işçi oturumu (motor yükleme
dosya başına değil bir kez), yeniden OCR'da eski segment temizliği (çift
metin birikimi), düşük kaliteli eski Tesseract sayfaları için bir seferlik
backfill (`engine_backfill`). Kalite denetiminde kritik bulgu:
`evrakci/queue.py` donmuş pakette stdlib `queue` modülünü gölgeliyordu —
urllib3/requests zinciri `queue.LifoQueue` hatasıyla patlıyor, hata lazy
içeride `cannot import name 'RapidOCR'` olarak maskeleniyordu; `queue.py →
job_queue.py`, `sched.py → scheduler.py` yeniden adlandırıldı. Eski dosyalar
temizlendi: DENETIM/TESLIM 0.1.0–0.6.4 kayıtları ve kök ZIP'ler silindi
(git geçmişinde duruyor).
Aşağıdaki eski bölüm kayıtlarındaki `DENETIM-*` / `TESLIM-*` dosya
adları artık ağaçta yoktur; içerikleri yalnız `git log`/`git show` ile
görülebilir. Ayrıntı: `DENETIM-0.8.0.md`.

Doğrulama: tam test paketi + oturum duman testi + PyInstaller paket kapısı
(aşağıda). Canlı kasada ilk açılışta backfill eski düşük kaliteli OCR
sayfalarını RapidOCR'a yeniden düşürür.

## 0.7.0 kendi kendini güncelleme — 17.10.2026

WordArc'ın çalışan güncelleme modeli Evrakçı'ya uyarlandı. Kaynak depo özel
kalır; paketler herkese açık `zeitgeist-c/Evrakci-Releases` deposunda
yayınlanır. Ayarlar → Güncellemeler: durum, denetle, indir ve kur, iptal,
ilerleme. Açılıştan 30 sn sonra günde bir sessiz denetim. İndirme boyut +
SHA-256 ile doğrulanır; ZIP açılışı Zip Slip + manifest sürüm kontrolünden
geçer; bekçi BAT eski sürecin çıkışını bekleyip yeni sürümü `--restarted`
ile açar ve kendini siler. Doğrulamayı geçemeyen paket asla çalışmaz.
Eski klasör/kasa silinmez. Ayrıntı: `DENETIM-0.7.0.md`, `TESLIM-0.7.0.md`.

Doğrulama: **237 test** (29 yeni), paketli EXE smoke 25/25, eval kapısı
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
