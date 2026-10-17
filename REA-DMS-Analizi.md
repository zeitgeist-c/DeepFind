# REA — DMS Arayüz Analizi ve Evrakçı Entegrasyon Planı

Tarih: 17.10.2026 · Taban sürüm: Evrakçı 0.8.0 → 0.8.1 (M1–M5 bu sürümde)
Yöntem: `reverse-engineering` (REA) skill — **kaynak öncelikli** ("kaynak varken binary'ye bakma").
Kanıt: `doctor` çıktısı (REA CLI 6.5.0, Node 24.13.1; Ghidra/IDA/JADX/Hopper **kurulu değil** — kaynak
analizi için gerekmiyor). Üç hedef de açık kaynak; derin analiz depo kaynağından yapıldı.
Klonlar: `…\Temp\opencode\rea-targets\` (salt okunur analiz; hedef depolar değiştirilmedi).

## Hedef kimlikleri (kullanıcı onaylı — S1.md G7)

| Hedef | Commit | Tarih | Lisans | Kapsam (okunan dizinler) |
|---|---|---|---|---|
| paperless-ngx/paperless-ngx | `0cb2cdb` | 2026-10-16 | GPL-3.0 | `src-ui/` (Angular), `src/documents/` (Django) |
| papermerge/papermerge-core | `1f0c8c4` | 2026-10-11 | Apache-2.0 | `frontend/` (React), `papermerge/core/` (Django) |
| eikek/docspell | `f5ffc74` | 2026-10-16 | AGPL-3.0 | `modules/webapp/` (Elm), `modules/backend`, `modules/convert`, `modules/extract`, `modules/query` (Scala) |

Kural: **kod kopyalanmaz**; desen ve fikir uyarlanır. Üç lisans da (GPL-3.0 / Apache-2.0 / AGPL-3.0)
Evrakçı'ya kod taşımaya uygun değil; yalnız etkileşim ve sunum desenleri alınır.

## 1. paperless-ngx bulguları

**Liste ve filtreleme (gözlem)**
- Görünüm modları **tablo / küçük kart / büyük kart** olarak değiştirilebiliyor
  (`src-ui/src/app/components/document-list/document-list.component.html:48-61`).
- Çoklu seçim: **Hiçbiri / Sayfa / Tümü** + seçim sayısını gösteren temizlenebilir rozet
  (`document-list.component.html:2-32, 132-151`).
- **"Göster"** açılır menüsü: listede hangi meta alanlarının görüneceği kullanıcıya bırakılmış
  (`:33-47`). Sıralama alanı + yön ayrı menüde (`:63-86`).
- **Kayıtlı görünümler** ("Views"): aktif görünüm değiştiyse nokta rozeti; "Kaydet / Farklı kaydet /
  Tüm kayıtlı görünümler" (`:88-115`).
- Filtre çubuğu: metin filtresi hedef seçici (başlık/içerik/ASN/kopya) + **yazarken öneri**;
  etiket/kurum/tür/yol için **belge sayacı gösteren** ve **klavye kısayolu** olan filtre dropdown'ları
  (t/y/u/i); tarih filtresi **göreli tarih** destekliyor; tek tuşla "Filtreleri sıfırla"
  (`filter-editor/filter-editor.component.html:4-32, 38-109`).

**Kart/satır sunumu (gözlem)**
- Kartta: **thumbnail görseli**, üzerine bindirilmiş etiket rozetleri (+N taşma), not sayısı rozeti,
  alt bölümde kurum/tür/depolama yolu/**tarih (ipucunda oluşturma/ekleme/değişiklik)**/sayfa sayısı/ASN/
  sahip/paylaşım/özel alanlar ve **Aç / Önizleme açılır penceresi / İndir** düğmeleri
  (`document-card-small/document-card-small.component.html:3-19, 21-41, 46-139, 144-162`).
- Yükleme sırasında **iskelet (skeleton) yer tutucular** (`:17-19, 140-142`).

**Belge detayı ve görüntüleyici (gözlem)**
- Üst şeritte **"Sayfa N / M"** girdisi, **yakınlaştırma kademeleri** ("Sayfaya sığdır" + yüzde
  kademeleri) ve −/+ (`document-detail/document-detail.component.html:2-21`; kademe listesi
  `document-detail.component.ts:1671-1678`). **Önceki/Sonraki belge** gezinmesi (`:116-127`).
- İşlem menüsü: yeniden işle, yazdır, "buna benzer", PDF düzenleyici, parola kaldır; indirme menüsünde
  **orijinali indir** ve "biçimli dosya adı" seçeneği (`:37-62, 64-91`).

**Thumbnail hattı (gözlem)**
- Thumbnail'lar **sunucuda önceden üretilir ve dosyada tutulur**: `THUMBNAIL_DIR/{pk:07}.webp`
  (`src/documents/models.py:526-535`); `thumb` uç noktası `image/webp` döndürür, ETag/koşullu önbellek
  kullanır (`src/documents/views.py:1843-1866`); `preview` uç noktası dosyayı `inline` sunar
  (`:1818-1841`). Çıkarım: tarayıcı önbelleği, `webp` + sabit adlandırma ile ucuz; masaüstü karşılığı
  yerel önbellek dizini.

## 2. papermerge-core bulguları

**Kabuk (gözlem)**
- **İki panelli** (`DualPanel`) ve **tek panelli** (`SinglePanel`) gezinme bileşenleri ayrı bileşenler
  (`frontend/apps/ui/src/components/DualPanel`, `SinglePanel`); ayrıca `Breadcrumbs`, `QuickFilter`,
  `TableSort`, `NodeThumbnail`, `FilterByUser` ve belge içinde `ThumbnailsToggle` /
  `DocumentDetailsToggle` / `Zoom` (`frontend/apps/ui/src/components/**`). Çıkarım: panel düzeni ve
  görünürlük anahtarları kullanıcı denetiminde.

**Sayfa yönetimi / görüntüleyici (gözlem) — imza özelliği**
- Sayfa rayı: dikey **sayfa küçük resimleri yığını**, altta zoom şeridi, sayfalama sürerken yükleyici
  (`frontend/packages/viewer/src/components/PageList/PageList.tsx:11-29`).
- Sağ tık menüsü işlemleri: başlık değiştir, **OCR metnini gör**, saat yönü / tersine **döndür**,
  **değişiklikleri geri al**, **kaydet**, sayfaları sil, belgeyi taşı, sayfa çıkar, belgeyi sil
  (`ContextMenu/ContextMenu.tsx:3-13, 103-110`). Çıkarım: düzenlemeler **sahnelenir**, açık
  kaydet/geri al ile onaylanır (kaza koruması).
- Çıkarılan/aktarılan sayfalar için ayrı onay diyalogları (`ExtractPagesModal`, `TransferPagesModal`,
  `DeleteEntireDocumentConfirmDialog`, `PagesHaveChangedDialog`).
- Sayfa döndürme ve taşıma sunucu tarafında: `papermerge/core/utils/__init__.py:442-453`
  (`rotate_pdf_pages`, `page.rotate(angle, relative=True)`), `papermerge/core/features/page_mngm/db/api.py`
  (`move_pages`).

**Diğer (gözlem)**
- Arama özelliği ayrı bir Django modülü: `papermerge/core/features/search/{router,schema,db/api}.py`.
- Özel klasör kavramı **Gelen/Ana** (`features/special_folders`) ve `preferences`, `tasks`, `tags`,
  `custom_fields`, `nodes` modülleri. Çıkarım: "Gelen kutusu" ayrımı yerel arşivde de işe yarar.

## 3. docspell bulguları

**Arama (gözlem)**
- **Güçlü arama girdisi**: yazarken 100 ms kısıtlamalı ayrıştırma; hata varsa **girdinin altında
  şapka (`^`) işaretiyle konum** ve mesaj listesi gösterilir (`Comp/PowerSearchInput.elm:35-61, 177-210`).
- Sorgu dili alan ve işleçleri (`modules/query/shared/src/main/scala/docspell/query/internal/Constants.scala:12-57`):
  `corr`, `tag`, `date`, `due`, `folder`, `notes`, `id`, `year`, `exist`, `inbox`, `created`, özel alan `f`;
  işleçler `= > >= ~= : < <= !=`, `!` ile olumsuzlama. Çıkarım: filtre alanları zaten var olan Evrakçı'da
  bu sözdizimi **güç kullanıcı kısayolu** olarak eklenebilir.
- Kayıtlı sorgular ("bookmarks") ayrı yönetim ekranıyla (`Comp/BookmarkManage.elm`,
  `BookmarkQueryForm.elm`).

**Liste ve detay (gözlem)**
- Liste kartında ek **önizleme eki** ve **ekler arasında gezinme** (`CyclePreview`), satır aç/kapa,
  sürükle-bırak, seçim ve bağlantı hedefi (`Comp/ItemCard.elm:46-55, 85-110`); liste bileşeni
  `Comp/ItemCardList.elm`.
- Detay: bilgi başlığı, sekmeli alan durumu, tek ek görünümü, düzenleme formu
  (`Comp/ItemDetail/{View2,ItemInfoHeader,SingleAttachment,EditForm,Tabs,FieldTabState}.elm`).
- **PDF görüntüleme modları**: `detect / native / server` (tarayıcı PDF desteklemiyorsa sunucu görünümü)
  (`Data/Pdf.elm:19-74`). Çıkarım: masaüstünde karşılığı "uygulama içi görüntüleyici ↔ harici açıcı"
  tercihi.

**Diğer (gözlem)**
- Yükleme ve kuyruk ekranları: `Comp/Dropzone.elm`, `Page/Upload/*`, `Page/Queue/*`, `Comp/Progress.elm`.
- Tema yalnız açık/koyu (`Data/UiTheme.elm:16-51`) — Evrakçı'da zaten sistem/açık/koyu var.
- Dönüştürme/çıkarma hattı: `modules/convert/*` (OCRmyPDF, Tesseract, Unoconv, WeasyPrint, PDF şifre
  kaldırma) ve `modules/extract/*` (Tika + OCR). Çıkarım: Evrakçı'nın RapidOCR hattı bu işlevi yerelde
  karşılıyor; uyarlanacak yeni bir hat yok.

## 4. Sentez — Evrakçı'ya uyarlanabilir desenler (öncelik sırası)

| # | Desen | Kaynak | Evrakçı karşılığı | Fayda |
|---|---|---|---|---|
| P1 | Thumbnail'ın önbellekte üretilip **listedeki satırda ve detay panelinde** gösterilmesi; iskelet yer tutucular | paperless `thumb` + kart; papermerge `NodeThumbnail` | pypdfium2 ile ilk sayfa küçük resmi → yerel önbellek dizini; `CardDelegate` satırına küçük resim, "Seçili evrak" paneline büyük önizleme | Arşivin "görsel katalog" gibi okunması; en büyük algısal kalite sıçraması |
| P2 | Görüntüleyicide **yakınlaştırma kademeleri** ("Sayfaya sığdır"/"Genişliğe sığdır" + %), sayfa küçük resmi rayı, önceki/sonraki belge, klavye kısayolları | paperless detay; papermerge `PageList`+`Zoom` | `Onizleme` bileşenine kademeler + sayfa rayı + kısayollar | "Tek sayfa görüntüleme"nin profesyonel okuma deneyimi |
| P3 | **Filtre çipleri** (kaldırılabilir etiketler) + "tümünü sıfırla"; görünüm modu (kompakt/satır/**ızgara**) ve "gösterilecek alanlar" anahtarları | paperless `filter-editor`, görünüm modu + "Göster" | Filtre sütununda çip satırı; sonuç listesine mod düğmeleri | Filtrenin görünür ve tek tıkla geri alınabilir olması |
| P4 | **Çoklu seçim + toplu işlem** (Hiçbiri/Sayfa/Tümü, toplu etiket) | paperless seçim + `bulk-editor`; docspell `MultiEditMenu` | Sonuç listesine seçim kutuları; toplu etiket ekle/çıkar, seçimi CSV'ye yaz | Yüzlerce evrakta toplu düzenleme |
| P5 | **Sorgu sözdizimi** `alan:değer` + satır içi doğrulama (şapka işareti) | docspell `PowerSearchInput` + `Constants.scala` | Arama kutusuna `yil: tur: etiket: klasor:` çözümleyicisi ve anlık hata gösterimi | Klavyeden hızlı, güçlü arama |

Reddedilen/uygulanmayan desenler: Docker/sunucu mimarisi, kullanıcı-rol izin sistemi, e-posta/IMAP
alımı, paylaşım bağlantıları, e-arşiv entegrasyonu (kullanıcı kapsamı dışı); bunlar Evrakçı'nın yerel,
şifreli, tek kullanıcılı modeline uymuyor.

## 5. Entegrasyon planı (milestone'lar)

Her milestone: kod + testler (`tests/`) + offscreen ekran görüntüsü kanıtı (`eval/ui_shots.py`) +
`DURUM.md` güncellemesi. Commit/push yok ("tmm/yedek" beklenir).

- **M1 — Thumbnail hattı ve liste/detay görselleri (P1) — TAMAMLANDI (17.10.2026)**
  - Yeni `thumbs.py`: yol+`size`+`mtime` anahtarıyla yerel önbellek
    (`%LOCALAPPDATA%\Evrakçı\thumbs`); `workers.py`'ye `thumb` işi ve tekrarlı
    işler için kalıcı işçi (`WorkerSession`); üretilemezse simgeye geri düşüş.
  - UI: sonuç satırlarında ve "Taranmış Evraklar" listesinde küçük resim;
    "Seçili evrak" panelinde kutuya uyan büyük önizleme (`ui.GorselKutusu`).
  - Kanıt: 13 yeni test (toplam **250**), açık/koyu ekran görüntüleri;
    `DURUM.md` M1 bölümü. Taşma kusuru görsel kanıtla bulunup düzeltildi.
  - Kabul: ✅ donma yok (üretim alt süreçte, sıralı), ✅ önbellek tekrar
    kullanımı, ✅ kaynak değişince anahtar değişir, ✅ PDF dışı türlerde simge.
- **M2 — Görüntüleyici derinleştirme (P2) — TAMAMLANDI (17.10.2026)**
  - Yakınlaştırma kademeleri: Genişliğe sığdır (varsayılan) / Sayfaya sığdır /
    %50–%200; işçi tek render yapar (`fit` kutusu ya da yoğunluk). −/+ kademe
    adımlar, `0` %100, klavye gezinmesi (←/→/↑/↓/PageUp/PageDown, +/-, Esc).
  - Sayfa rayı: 12'lik gruplarla tembel küçük resim üretimi, tıklayınca sayfa,
    geçerli sayfa vurgusu (papermerge `PageList`).
  - Önizlemede "Önceki/Sonraki belge + N / M"; indeks metni ↔ sayfa görüntüsü
    geçişi.
  - Kanıt: 4 yeni test (toplam **254**, çıkış kodu 0) + `onizleme-*.png`.
  - Yan bulgu (düzeltildi): koşan QThread pencereyle yok edilince Qt düşüyordu
    (0xC0000409); kapanış yolları artık yükleyicileri bekliyor.
  - Kabul: ✅ klavye ile tam gezinme, ✅ ray seçimi sayfayı değiştirir,
    ✅ ray tembel yüklenir, ✅ sığdırma kutusu değişince yeniden render.
- **M3 — Filtre çipleri ve görünüm modları (P3) — TAMAMLANDI (17.10.2026)**
  - Aktif filtreler kaldırılabilir çip + etkin filtre sayacı + "Filtreleri
    sıfırla"; çipler boş sorguda da görünür ve yalnız ilgili filtreyi düşürür.
  - Görünüm modu Kompakt/Satırlar/Izgara; mod ve alan seçimi kasada saklanır ve
    açılışta geri yüklenir (`gorunum_modu`, `goster_alanlari`).
  - "Göster" menüsüyle satır alanları (yol/tür/özet/etiket) açılıp kapanır.
  - Kanıt: 3 yeni test (toplam **257**, çıkış kodu 0) + `ara-filtre-*.png`,
    `ara-izgara-*.png`.
  - Kabul: ✅ çip kaldırma filtreyi düşürüp aramayı yeniler, ✅ mod kalıcı,
    ✅ ızgarada küçük resim.
- **M4 — Çoklu seçim ve toplu işlem (P4) — TAMAMLANDI (17.10.2026)**
  - `ExtendedSelection` + Hiçbiri/Sayfa/Tümü + "N seçili" rozeti; panel etkin
    yüzeyin geçerli satırını izler.
  - `rank.tags_many`: toplu etiket ekle/kaldır tek işlem; hata → rollback
    (yarı uygulanmış işlem yok). Toplu işlem `archive_ui.job` ile arka planda.
  - "Seçimi CSV" yalnız seçili sonuçları indirir.
  - Kanıt: 3 yeni test (toplam **260**, çıkış kodu 0) + `ara-secim-*.png`.
  - Yan bulgu (düzeltildi): eski filtre çipleri görünür kalıp alanın üstüne
    biniyordu; regresyon testi eklendi.
  - Kabul: ✅ seçim/sayfa/tümü, ✅ toplu etiket tek transaction + geri alma,
    ✅ seçim CSV'si.
- **M5 — Sorgu sözdizimi (P5) — TAMAMLANDI (17.10.2026)**
  - `sorgu.py`: `yil:`, `tur:`, `etiket:`, `klasor:` alanları; tırnaklı değer,
    Türkçe harf katlaması, hata için imleç konumu.
  - Arayüzde satır içi doğrulama: hatalı sorguda arama koşmaz, önceki sonuçlar
    korunur; geçerli alanlar filtre denetimlerini besler (çip/sayaç akışı).
  - Sahiplik kuralı: sorgu yalnız kendi kurduğu alanı temizler.
  - Kanıt: 12 yeni test (toplam **272**, çıkış kodu 0) + `ara-sorgu-*.png`,
    `ara-sorgu-hata-*.png`.
  - Kabul: ✅ alan sözdizimi çözülüp filtrelere bağlanıyor, ✅ hatalı girişte
    satır içi uyarı + imleç ve arama duruyor.

## 6. Lisans ve sınır

- Kod alınmadı; yalnız etkileşim desenleri uyarlanacak. Desen uyarlamaları Evrakçı'nın kendi
  bileşenleriyle (PySide6, `theme.pal()`) yeniden yazılır.
- `LISANSLAR.md` bu çalışmadan sonra **yeni bir bağımlılık gerektirmiyor**: thumbnail için mevcut
  `pypdfium2` + `Pillow` yeterli.

## 7. Bilinmeyenler / açık sorular

- [cevaplandı] Hedeflerin kaynağı var → REA CLI yerine kaynak okuması yapıldı.
- [cevaplandı] Analiz için native motor (Ghidra/IDA/JADX) gerekmez; `doctor` kanıtı kayıtlı.
- [kısmen] paperless thumbnail **üretim** kodu (kuyruk/görev) derinlemesine okunmadı; önbellek
  adlandırması ve uç nokta davranışı yeterli kanıt sağladı.
- [açık] docspell/papermerge arayüzlerinin **çalışırken** davranışı (ör. akıcılık, animasyon) statik
  okumayla doğrulanamaz; gerekirse canlı demo ile runtime gözlem yapılabilir (kullanıcı onayı).
