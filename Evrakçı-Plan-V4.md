# Evrakçı — Ayrıntılı Ürün ve Uygulama Planı V4

**Tarih:** 27 Eylül 2026; kaynak araştırması 26–27 Eylül 2026  
**Belge durumu:** Araştırılmış uygulama planı; uygulama geliştirmesi başlamadı.  
**Program:** Evrakçı  
**Uygulama sürümü:** Henüz belirlenmedi. V4, planın revizyonudur; uygulama sürümü değildir.  
**Öncelik:** Kaynak güvenliği → doğru ve açıklanabilir sonuç → dayanıklılık → kullanım kolaylığı → hız.  
**Dayanak:** Kullanıcının V3 planı, güncel kullanıcı açıklamaları ve eşlik eden araştırma/karar belgesi.

Bu belge V3'ün yerine geçmek üzere hazırlanmıştır. Bir AI kodlayıcı bu belgenin varlığını geliştirmeye başlama, NAS'a erişme veya GitHub'a yayın yapma yetkisi sayamaz. Kullanıcı geliştirmeyi ayrıca başlatır. Hiçbir plan hatasız yazılımı garanti etmez; aşağıdaki doğrulama kapıları ve kabul ölçütleri bu nedenle zorunludur.

## 1. Kullanıcıdan doğrulanmış bağlam

| Konu | Bilinen durum | Tasarıma etkisi |
|---|---|---|
| Kullanıcı sayısı | Yaklaşık 3–5 kişi, farklı bilgisayarlar | Her Windows kullanıcısına/PC'ye ayrı yerel indeks; ortak DB yok |
| Referans PC | AMD 5600 olarak belirtilen işlemci, 16 GB RAM, yaklaşık 8 GB kullanılabilir RAM | GPU zorunlu değil; CPU ve bellek bütçeli çalışma |
| Diğer cihazlar | Dizüstü ve farklı donanımlar olabilir | Desteklenen alt sınır pilotla doğrulanacak |
| NAS yetkisi | Kullanıcı NAS'ta dosya silebiliyor | Hesap salt okunur değil; uygulama hiçbir kaynak yazma işlemi başlatmayacak |
| Arşiv | Binlerce dosya; kesin sayı ve toplam boyut bilinmiyor | İlk keşif dosya/tür/boyut sayımı yapacak |
| Kaynak düzeni | Dosyalar NAS'ta kalacak | Kalıcı belge kopyası, yeniden adlandırma, taşıma ve düzenleme yok |
| Arayüz | Modern, güzel, temalı masaüstü arayüzü isteniyor | Açık/koyu/sistem teması, konumlu önizleme ve tutarlı tasarım sistemi |
| Kullanım | V3'te yaklaşık 10 yeni dosya/gün, 10–20 arama/gün | Bunlar başlangıç varsayımı; çok kullanıcılı gerçek ölçümle güncellenir |

NAS adresi, Windows sürümleri, belge türü dağılımı, şirket klasörü yapısı ve kötü tarama oranı henüz bilinmiyor. Bunlar uydurulmayacak. Planın çevrimdışı ve düşük kaynaklı çekirdeği bu bilgiler olmadan da tanımlanmıştır.

## 2. Ürün amacı ve sınırlar

Evrakçı, seçilen yerel/ağ klasörlerinde bulunan belgeleri okuyup yerelde şifreli bir arama indeksi oluşturan Windows masaüstü uygulamasıdır. Kullanıcı doğal dil benzeri bir ifade yazar; uygulama dosya adı, klasör bağlamı ve belge içeriğinde ilgili belgeleri bulur, neden eşleştiğini ve eşleşmenin konumunu gösterir.

V1 bir belge bulma aracıdır. Sorulara üretken modelle cevap üretmez; yazılan her cümlenin anlamsal olarak eksiksiz anlaşılacağı vaat edilmez. Örneğin “Ankara Ayşe 2024 vergi levhası” kelime, bağlam, yıl ve kontrollü toleransla aranır.

Kaynak belgelerin kalıcı kopyası oluşturulmaz. Çıkarılmış metin, dosya yolu ve konum bilgisi yerel şifreli DB'de saklanır. OCR için RAM'de sayfa görüntüsü ve gerektiğinde kontrollü yerel geçici türev oluşturulabilir. İndeks kaynak belgelerin yedeği değildir.

V1 kapsamında:

- Windows x64 masaüstü, Türkçe arayüz, 3–5 kişinin bağımsız kullanımı.
- Klasör seçimi, hariç tutma, keşif, artımlı tarama, duraklat/devam/iptal.
- PDF, XLSX, XLS, DOCX içerik arama; DOC için bölüm 8'deki destek kapısı.
- Sayfa bazlı yerel OCR ve düşük kaynaklı kalite iyileştirme geçişi.
- Ad/klasör/içerik araması, Türkçe tolerans, yıl/şirket/tür filtreleri.
- Doğrulanmış birebir kopyaların gruplanması.
- Dahili PDF görüntüsü, Excel veri bölgesi ve Word metin/tablo önizlemesi.
- Şifreli kasa, arama geçmişi, yedek/geri yükleme, zamanlama ve tepsi.
- Modern açık/koyu/sistem teması, erişilebilirlik ve DPI uyumu.

V1 kapsamı dışında:

- Sunucu kurulumu, ortak indeks, kullanıcılar arası indeks/şifre paylaşımı.
- Gemini veya başka internet AI servisi; otomatik model indirme ve telemetri.
- Kaynak dosyayı düzenleme/silme/taşıma/yeniden adlandırma/etiketleme.
- Excel'e sonuç aktarımı, muhasebe kaydı, ters belge arama.
- Sistem çapında global kısayollar. Normal klavye gezinmesi ve erişilebilirlik kapsam içindedir.
- El yazısını veya bozuk her belgeyi doğru okuma garantisi.
- OCR'den alınan tutarları doğrulanmış muhasebe verisi olarak sunma.

## 3. V3'ten değişen başlıca kararlar

| V3 | V4 kararı | Gerekçe |
|---|---|---|
| Tek PC | Ayrı yerel indekslerle 3–5 kullanıcı | Kullanıcının son açıklaması |
| PyQt6 değişmez | PySide6 + Qt Widgets önerilen temel | Resmi Qt bağlayıcısı; lisans ve dağıtım kapısı korunur |
| Python 3.11 kesin | CPython 3.13 x64 başlangıç adayı | Güncel Windows binary bakımı ve native bağımlılık uyumu; kesin yama sürümü pilotta kilitlenir |
| Tesseract ardından zorunlu Marker | CPU Tesseract + ölçülmüş iyileştirme geçişi; ağır OCR isteğe bağlı | Farklı donanımlar, bellek ve model lisansı |
| os.startfile ile salt okunur | Dahili önizleme varsayılan; harici açma ayrı | Harici uygulama salt okunurluk garanti etmez |
| İlk 64 KB metin hash'i = kopya | Tam dosya SHA-256 = birebir kopya | Farklı belgelerin yanlış gizlenmesini önleme |
| 41. dosyadan devam | Dosya sürümüne bağlı kalıcı iş kuyruğu | Sıralama değişebilir, dosya güncellenebilir |
| DB'yi doğrudan kopyala | Doğrulanmış şifreli snapshot + geri açma testi | WAL ve aktif yazma tutarlılığı |
| Her sorguda bütün metinde fuzzy | Kelime sözlüğü + sınırlı aday havuzu | Kaynak kullanımı ve gecikme |
| İnternet/ağ çıkışı yok | NAS erişimi var; internet servisleri yok | Ağ ve internet ayrımı |
| Her görev aynı tam testler | Değişime uygun testler; aşama sonunda bütünleşik kapı | Etkili ve gerekli doğrulama |
| İlk görev private repo + push | Yerel plan/uygulama; dış yayın ayrıca yetkilendirilir | Kullanıcının kalıcı talimatı |

PySide6 ve ikinci OCR yaklaşımı ürün gereksinimini değiştirmeden önerilen teknik revizyonlardır. Marker'a özel bağımlılık veya DOC kapsamını azaltma gibi ürün etkisi olan değişiklikler sessizce yapılmaz; uygulanabilirlik sonucu karar defterine yazılır.

## 4. Başarı ölçütleri ve hedef ortam

Bu bölümdeki sayılar hedef/başlangıç bütçesidir; yapılmış ölçüm değildir. Teknik pilotta onaylanan referans ortam ve veri kümesiyle raporlanır.

| Alan | Başlangıç hedefi | Ölçüm |
|---|---|---|
| Platform | Windows 11 x64 birincil | Temiz standart kullanıcı hesabında paket smoke |
| Ek Windows ortamı | Windows 10 ancak destek/lisans/bağımlılık uyumu ayrıca doğrulanır | Ayrı uyumluluk matrisi; genel destek varsayılmaz |
| Bellek alt sınırı | 8 GB toplam RAM, iş sırasında en az 2 GB kullanılabilir bellek adayı | Gerçek düşük donanım pilotu olmadan sertifikalı minimum denmez |
| GPU | Gerekmiyor | GPU bulunmayan cihazda tüm temel akış |
| Arama | 50.000 dosyalık testte p95 ≤ 2 sn, toleranslı aramada ≤ 3 sn | En az 100 sorgu; soğuk/sıcak, boşta/tarama sırasında ayrı |
| Arayüz | Ağ/OCR beklerken kullanılabilir kalır | Arama, pencere taşıma, iptal ve tema değiştirme denemeleri |
| Boşta bellek | Ana süreç ≤ 300 MB aday hedef | Private bytes/working set ayrı rapor |
| Normal indeksleme | Tüm süreçler toplamı ≤ 1,5 GB aday hedef | Çocuk süreçler dahil tepe ölçümü |
| Temel OCR | Tüm süreçler toplamı ≤ 2 GB aday hedef | Sayfa bazında, 8 GB RAM cihazda ölçüm |
| Arama kalitesi | En az 50 doğrulanmış sorguda ilk-3 doğru belge oranı ≥ %90 | Kolay/zor/yanlış yazım/no-result alt grupları ayrı |
| Kaynak güvenliği | Uygulama kaynaklara yazma/rename/delete işlemi başlatmaz | API denetimi + izlenen izinli test paylaşımı |
| Dayanıklılık | Kesintiden sonra tamamlanmış dosyalar gereksiz işlenmez | İşlem ortasında sonlandırma testleri |
| Gizlilik | İnternete belge/metin aktarımı sıfır | İnternet engelli koşulda paket testi ve süreç ağ gözlemi |

Çok büyük sayfa, ZIP açılımı veya kötü dosya bütçeyi aşarsa süreç kontrollü durdurulur; sonuç “başarılı” yapılmaz. Bellek hedefi işletim sistemi genelindeki toplam tüketim değildir. Düşük serbest RAM'de OCR ertelenir; mevcut indeks araması sürer.

İlk tarama süresi dosya sayısından tek başına hesaplanmaz. Dizin keşfi, okunan bayt, sayfa sayısı, OCR oranı ve ağ gecikmesi ayrı ölçülür. “10 yeni dosya 1–2 dakika” garanti değildir; eski dizinlerin listelenmesi de zaman alır.

## 5. Mimari ve modül sınırları

Tek kullanıcıya ait tek kasa, tek uygulama örneği. PC'ler arasında koordinasyon sunucusu veya NAS üzerinde kilit/checkpoint dosyası oluşturulmaz.

    Qt arayüzü
       ├─ Kasa / kilit / ayarlar
       ├─ Arama koordinatörü → ayrı okuyucu DB bağlantısı
       ├─ Dahili önizleme → kontrollü okuma/görüntüleme çalışanı
       └─ Tarama koordinatörü
             ├─ Kaynak keşfi ve salt okunur erişim
             ├─ Kalıcı iş kuyruğu
             ├─ Sonlandırılabilir çıkarma / OCR alt süreçleri
             └─ Tek DB yazıcısı → SQLCipher + FTS5

Kurallar:

- Qt widget ve model güncellemeleri yalnız arayüz iş parçacığında.
- NAS'a erişim, hash, metin çıkarma ve OCR arayüz iş parçacığında yapılmaz.
- DB bağlantıları iş parçacıkları arasında paylaşılmaz. Okuyucu ve yazıcı ayrı bağlantı kullanır.
- Varsayılan bir kaynak okuma/çıkarma işi ve bir ağır OCR işi; aynı kaynağı gereksiz paralel okumaz.
- Önizleme ve etkileşimli arama arka plan işlerinden önceliklidir.
- Çocuk süreçler DB anahtarını almaz; sonuçları yerel IPC ile koordinatöre verir.
- Çalışanların giriş/çıkış verisi boyut, süre ve biçim açısından doğrulanır.
- Sonlandırılan çalışanın kuyruğu güvenilir kabul edilmez; yeni iş için temiz kanal açılır.
- Windows süreç grubu/job object ile bellek ve süreç ağacı yaşam döngüsü denetlenmesi pilotta doğrulanır. Bu tek başına bir güvenlik sandbox'ı sayılmaz.
- PDFium çağrıları aynı süreçte eşzamanlı yürütülmez; önizleme ve OCR render ayrı süreçlerde olabilir.
- Paketlenmiş Windows süreç başlatma, tekrar pencere açılmaması ve düzgün çocuk kapanması ayrıca test edilir.

Önerilen ilerideki kaynak yapısı; bu planlama sırasında oluşturulmayacaktır:

    src/evrakci/
      main.py
      domain/           # modeller, durumlar, hata sözleşmeleri
      application/      # tarama, arama, kasa, yedek koordinatörleri
      infrastructure/   # Windows, NAS, SQLCipher, çalışan süreçleri
      extraction/       # PDF, XLSX, XLS, DOCX, DOC adaptörleri
      ocr/              # Tesseract, kalite, opsiyonel motor
      search/           # normalizasyon, sorgu, adaylar, sıralama
      presentation/     # pencereler, modeller, tasarım tokenları
    assets/             # SVG, ikonlar, tema tanımları
    tests/              # birim, entegrasyon, hata, paket ve UI testleri
    testdata/synthetic/ # yalnız yapay/izinli örnekler
    docs/               # mimari kararlar, kullanım ve bakım
    packaging/          # spec, build, smoke, lisans manifesti

Dosya başına katı liste değil, işlevsel sınırlar bağlayıcıdır. Kodlayıcı bir modülü sırf bu listede yok diye devasa başka dosyaya sıkıştıramaz.

## 6. Teknik bileşenler ve sürüm kilitleme

| İş | Önerilen bileşen | Zorunlu doğrulama |
|---|---|---|
| Arayüz | PySide6 + Qt Widgets | Windows, model/view, tema, lisans, paket |
| Çalışma zamanı | CPython 3.13 x64 adayı, GIL'li standart build | Bütün native wheel'ler ve paketli çalışan süreçleri; free-threaded deneysel hat kullanılmaz |
| Şifreli DB | SQLCipher; sqlcipher3 Windows wheel adayı | cipher_version, FTS5, yanlış anahtar, WAL ve yedek |
| PDF görüntüsü | pypdfium2/PDFium | Thread sınırı, bellek, JS/XFA kapalı yapı, lisans |
| PDF metin | PDFium temel; pypdf gerektiğinde fallback | Konum, okuma sırası, bozuk font, şifreli dosya |
| XLSX | openpyxl read-only + defusedxml | Formül/cached değer, harici link ve XML sınırları |
| XLS | xlrd | Eski biçim, satır/hücre, kodlama ve limitler |
| DOCX | python-docx + sınırlı OOXML okuma | Tablo, üst/altbilgi, metin kutusu sınırları |
| DOC | Bölüm 8'deki adaptör kapısı | Office şartı olmadan veya açık önkoşulla gerçek destek |
| OCR | Tesseract 5; tur/eng/osd doğrulanmış modeller | CPU hızı, kalite, yerel temp ve paket |
| Yanlış yazım | rapidfuzz | Sözlük adayları; bütün arşive fuzzy uygulanmaz |
| Paket | PyInstaller onedir başlangıç tercihi | Python kurulu olmayan temiz makine |
| Test | pytest, Qt test yardımcıları | Gerçek sonuç ve süreç exit code kontrolü |

26–27.09.2026 araştırmasında sqlcipher3 0.6.2 için CPython 3.13 ve 3.12 Windows x64 wheel listeleniyor. Bu, uygulama içinde çalışma ve FTS5 başarısının kanıtı değildir. sqlcipher3-binary adının Windows fallback'i olduğu varsayılmayacak. Python 3.12 security-only dönemde olduğundan temel Windows runtime adayı 3.13'tür; kurulum sırasında güncel güvenlik yamalı binary ve tüm native bağımlılıkları doğrulanır. 3.12'ye dönüş ancak güvenlik bakımı/uyumluluk gerekçesi kaydedilerek yapılır. [PyPI dosya listesi](https://pypi.org/project/sqlcipher3/), [Python bakım durumları](https://devguide.python.org/versions/)

Teknik pilotta seçilen paketlerin kesin sürümleri, transitive bağımlılıkları, wheel hash'leri, Tesseract exe sürümü ve traineddata hash'leri kilitlenir. Sürüm numarası içermeyen requirements listesine “pinli” denmez. Çalışma anında pip/model güncellemesi yok. Runtime ve opsiyonel ağır OCR bağımlılıkları ayrı kilitlenir.

Lisans envanteri tutulur. Qt modüllerinin her biri, PDFium ek lisansları ve OCR model ağırlıkları değerlendirilir. “PySide6 kullanıldı, dolayısıyla tüm dağıtım koşulları otomatik karşılandı” sonucu çıkarılmaz. [Qt lisans bilgisi](https://doc.qt.io/qt-6/licensing.html)

## 7. Kök seçimi, yollar ve NAS erişim politikası

İlk sihirbaz ve Kökler ekranında sürücü listesi, UNC girişi ve klasör ağacı birlikte sunulur. Ağaç yalnız açılan dalları yükler; tüm NAS'ı pencere açılırken gezmez. Yükleme, erişim hatası ve çevrimdışı durumları görünürdür.

- Ağ sürücüsünün eşlemesi Windows API ile çözülebiliyorsa UNC saklanır.
- Gerçek yerel sürücüye UNC uydurulmaz; yerel mutlak yol saklanır.
- NAS kimlik bilgisi uygulamada saklanmaz; Windows oturumunun erişimi kullanılır.
- Kök başına değişmez kimlik, gösterim yolu ve karşılaştırma yolu ayrı tutulur.
- Yol karşılaştırması Windows kurallarına uygun yapılır; Unicode metin arama normalizasyonu dosya yoluna uygulanmaz.
- Büyük/küçük harf ve son ayraç farkıyla aynı kök ikinci kez eklenmez.
- İç içe kökler ortak dosyayı iki kez indekslemez; hangi şirket kuralının üstün olduğu açıkça belirlenir.
- Aynı NAS'ın IP ve adla gösterilmesi otomatik olarak aynı fiziksel kaynak sayılmaz. Alias birleştirme doğrulama ister.
- “C:\\Belgeler” ile “C:\\Belgeler2” metin önekiyle aynı kapsam sayılmaz; yol bileşenleri kullanılır.
- Symlink, junction ve reparse point varsayılan izlenmez; döngü ve kök dışına yönlenme önlenir.
- DFS/uzun yol desteği ve erişim hataları Windows/NAS pilotunda ayrı test edilir; tüm sağlayıcılarda çalıştığı varsayılmaz.
- Hariçler alt dallara uygulanır. $RECYCLE.BIN, System Volume Information, Office geçici ~$ dosyaları varsayılan atlanır.
- Kullanıcıya ait noktayla başlayan klasörler toptan sistem çöpü sayılmaz.
- Gizli dosya politikası ayarlanabilir; varsayılan filtre ve desteklenmeyen tür sayıları açıklanır.
- Klasör sürükle-bırak yalnız Kökler ekranında kaynak ekler. Ana arama ekranında dosya bırakılması V2 ters arama gibi davranmaz.

Şirket kuralı kök başına seçilir: “bu kök tek şirket”, “şirket şu alt klasör seviyesinde” veya “belirlenemiyor”. Kullanıcı örnek yolların nasıl yorumlanacağını kaydetmeden önce görür. Belge bazında etiket istenmez.

Kaynak okuma sağlayıcısı tüm tarama/çıkarma/önizleme işlemlerinin tek giriş kapısıdır. Yalnız okuma erişimi ister; rename/delete/create/write/truncate/set-attribute işlemleri içermez. Kaynak dizine lock, temp, cache, thumbnail, checkpoint veya DB dosyası oluşturmaz.

NAS hesabının yazma yetkili olması otomatik güvence sağlamaz. Uygulama güvenliği uygulamanın işlemleriyle test edilir. Mutlak işletim sistemi düzeyinde yazma engeli istenirse ayrıca salt okunur hesap/paylaşım gerekir; program bunu sessizce ayarlamaz.

3–5 PC için günlük tarama, varsayılan 12:30 tabanı etrafında cihaz başına sabit küçük bir gecikmeyle dağıtılabilir. Gerçek “sonraki tarama” saati ekranda görünür ve gecikme kapatılabilir. Bu, NAS üzerinde merkezi kilit oluşturmaz ve toplam yükü kesin garanti etmez.

## 8. Dosya türlerinin gerçek destek sözleşmesi

| Tür | Okunacak içerik | Konum | Sınır |
|---|---|---|---|
| PDF | Sayfa metni, gerekirse OCR | Gerçek PDF sayfa indeksi + varsa etiket; bbox uygunsa | Sayfa okuma sırası kusurlu olabilir; düşük kalite gösterilir |
| XLSX | Dolu hücreler, satır bağlamı, sheet adı | Sheet + hücre/alan, ör. Vergi!B14:D14 | Formül hesaplama yok; gömülü resim OCR'si varsayılan V1 dışında |
| XLS | Dolu hücreler, sheet ve satır | Sheet + hücre/alan | Şifre/bozuk biçim ayrı hata; xlrd yalnız eski XLS içindir |
| DOCX | Paragraflar, tablolar, üst/altbilgiler | Bölüm/paragraf veya tablo/satır/hücre | Word sayfa numarası vaat edilmez; desteklenmeyen metin kutuları bildirilir |
| DOC | Ayrı eski Word adaptörü | Çıkarıcıya göre paragraf/bölüm | Teknik destek kapısı geçmeden tam destek ilan edilmez |

Metinli PDF sayfası içerdi diye bütün dosyada OCR atlanmaz. Sayfa içindeki resim bölgelerinde önemli metin varsa mevcut metnin miktarı tek başına “tam” kabul edilmez. Bölgesel OCR desteğinin kapsamı pilotta belirlenir; destek yoksa karma sayfa kısıtı açıkça raporlanır.

XLSX, salt okuma akışıyla satır satır işlenir. Formül metni ve mevcut cached değer mümkün olduğunda ayrı tutulur; cached değer yoksa “hesaplanmış değer yok” denir. Dış veri bağlantıları yenilenmez, Excel/Office otomasyonu başlatılmaz. Değer biçimlemesi; tarih, yüzde, para ve uzun kimlik numaraları için sınanır. Sayıları bütün biçimleriyle doğru yorumladığı varsayılmaz. [openpyxl okuma API](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html)

DOCX'te paragraf/tablo sırası korunur, iç içe tablolar ve tekrar eden üstbilgi metni kontrol edilir. Metin kutusu, yorum ve izlenen değişiklik içeriğinin hangi kısmının okunacağı destek matrisinde belirtilir; güncel/görünür metin yaklaşımı seçilir. HTML render yerine güvenli düz metin/model tabanlı önizleme kullanılır.

DOC için karar kapısı:

1. Pilot arşivde DOC varlığı ve oranı ölçülür.
2. Salt okuyucu adaptör tercih edilir; Windows'taki IFilter/Office bağımlılığı her cihazda mevcut kabul edilmez.
3. Gerekiyorsa LibreOffice tabanlı yerel dönüşüm adayı değerlendirilir: ayrı profil, makrolar ve bağlantı yenileme kapalı, kaynaklara yazmayan doğrulanmış akış, süreç/bellek sınırı ve kontrollü geçici türev.
4. Dönüşümün kaynak dosya veya yan klasör oluşturmadığı gözlemle test edilir. Headless komut tek başına güvenlik kanıtı değildir.
5. Uygun yöntem doğrulanamazsa DOC dosyaları ad/yol üzerinden bulunur, “içerik desteği doğrulanmadı” durumu taşır. Bu eksiklik kullanıcıya sunulur; kullanıcı kapsam revizyonunu kabul etmeden V1'in DOC desteği tamamlandı denmez.

Şifreli dosyalar ayrı listelenir. V1 belge şifrelerini toplamaz veya brute force denemez. Boş metin, boş sayfa, taranmış belge, şifreli belge ve bozuk belge farklıdır.

Dosya boyutu başlangıç limiti 200 MB'dir ve ayarlanabilir. Büyük dosya ad/yol düzeyinde görünür; içerik limiti yüzünden listeden kaybolmaz. Bir sınır nedeniyle kesilen içerik “tam indeks” sayılmaz.

İlk teknik pilot için limit adayları; aynı işte bütün bütçeler birlikte uygulanır:

| Bütçe | İlk aday değer | Aşım davranışı |
|---|---|---|
| Kaynak dosyası | 200 MB | Metadata bulunabilir, içerik işi atlanır |
| PDF sayfası | Belge başına 1.000 | İşlenmiş kısım partial; hangi sayfaların eksik olduğu görünür |
| Render görüntüsü | Sayfa başına 12 megapiksel | DPI düşürülür; kalite yetersizse açık düşük kaynak durumu |
| OOXML ZIP toplam açılımı | 256 MB ve en fazla 10.000 entry | Çıkarma durur; kaynak değişmez |
| ZIP genişleme oranı | 100:1 aday güvenlik eşiği | Dosya sınır nedeniyle ertelenir; güvenilir örneklerde ayarlanabilir |
| Excel taranan hücre alanı | Belge başına 2 milyon ziyaret | Sonraki bölge partial; şekil/formatla büyümüş boş alan sonsuz gezilmez |
| Çıkarılmış metin | Belge başına 10 MB UTF-8 | UTF-8/token sınırında kes; partial ve eksik alan bilgisi |
| Fuzzy belge adayları | En fazla 500 | Sonraki genişletme kullanıcı eylemiyle; tam arşiv similarity yok |
| Yerel preview cache | Toplam 128 MB RAM adayı | LRU tahliye; disk plaintext cache yok |

ZIP/XML kitaplıkları için tek entry boyutu, öğe/derinlik ve decompression süresi de sınırlandırılır. Toplam tablo limitleri native parser'ın kendi erken kontrolünün yerine geçmez; süreç bellek/süre sınırı son savunmadır. Bunlar evrensel format limitleri değil, kullanıcı PC'lerini koruyan başlangıç ürün limitleridir; temsilci veriyle gerekçeli ayarlanır.

## 9. Keşif, iş kuyruğu ve artımlı tarama

Tarama aşamaları: keşif → metin çıkarma → temel OCR → kalite iyileştirme → kopya doğrulama → tamamlanma. Aşamalar ekranı kilitlemez. Dosya adları keşif sırasında aranmaya başlayabilir; ilk taramanın tamamı bitene kadar kullanıcı bekletilmez.

Kalıcı iş kimliği; kaynak/dosya kimliği, gözlenen boyut, mtime_ns veya sağlayıcının zaman hassasiyeti, çıkarıcı sürümü ve iş türünü içerir. Aynı dosya sürümü için aynı iş tekrar kuyruğa alınmaz.

İş akışı:

1. Kök erişimi kontrol edilir; başarısızlık o kökü çevrimdışı yapar.
2. Dizinler lazy/sınırlı biçimde listelenir, hariçler uygulanır.
3. Dosyanın destek durumu ve metadata kaydedilir; metadata hatası dosya bazında sınıflanır.
4. Yeni/değişmiş dosyalara çıkarma işi oluşturulur. Önceden başarısız işler yeniden deneme politikasına tabidir.
5. Küçük ve doğal metinli belgeler öncelik alır; eski büyük işler sonsuza kadar aç kalmaz.
6. Okuma öncesi metadata alınır. Dosya kısa aralıkta değişiyorsa “kararlılık bekliyor” olarak ertelenir.
7. Çıkarma süreçte yapılır; bitince metadata yeniden kontrol edilir.
8. Dosya değişmişse sonuç atılır ve yeni sürüm işi oluşturulur.
9. Dosya/parçalar/FTS/iş sonucu tek DB transaction'ında güncellenir.
10. Çıkarma başarısızsa ad/yol sonucu kalır. Değiştiği bilinen dosyanın önceki içeriği normal arama kapsamından çıkarılır; yalnız açık “önceki indeks içeriğini göster” eyleminde sürüm/tarih bilgisiyle erişilebilir. Eski metin yeni dosyanın içeriği gibi sunulmaz.

Boyut+mtime değişiklik tespiti yaygın bir optimizasyondur; aynı boyut ve zamanla yapılan değişikliği matematiksel olarak garanti edemez. “İçeriği yeniden doğrula” komutu ve isteğe bağlı periyodik içerik denetimi bu sınıra karşı tanımlanır. Tam hash dosya sürümüyle bağlı tutulur.

İlk keşifte toplam bilinmiyorsa “keşfedilen dosya” ve belirsiz ilerleme gösterilir. Yanlış bir yüzde gösterilmez. Keşif tamamlanınca ilgili iş kuyruğu toplamı üzerinden ilerleme yapılır. OCR sayfaları ayrıca sayılır.

Günlük tarama mevcut ağacı yeniden listeleyebilir; yalnız yeni dosyaları bilmenin bedelsiz bir yolu varmış gibi davranılmaz. Sürekli filesystem watcher ve NAS'a yazılan değişiklik günlüğü yok.

Yeniden deneme başlangıç politikası: geçici hata için örneğin 1, 5 ve 30 dakika artan gecikme; sınırlı otomatik deneme; sonra sonraki günlük tarama veya kullanıcı “yeniden dene”. Saatler ve tekrar sayısı pilotta sabitlenir. Bozuk dosya her dakika açılmaz. Düşük RAM/OCR modeli eksik gibi sistem koşulları dosya bozukluğu sayılmaz.

Dosya açıkken okunabiliyorsa okunur. Share violation “kilitli”, access denied “erişim yok”, NAS kesintisi “kaynak çevrimdışı” olur. “Başka biri açmış” varsayımıyla dosya atlanmaz.

Duraklat, yeni iş başlatmayı durdurur; devam eden iş güvenli noktada tamamlanabilir. İptal, gerekirse çalışanı sonlandırır ve yarım işi pending yapar. Güç kesintisinden sonra running işler süresi dolmuş kabul edilip yeniden denenir; tamamlanmış sürümler korunur.

Kaynak güvenliği kaynakları değiştirmemeyi kapsar; NAS'ın kendi erişim zamanı/audit kayıtlarını güncellememesi garanti edilemez. Test bunun için kaynak içeriği/yazma isteği/namespace değişikliği üzerinden değerlendirilir.

## 10. Silinme, taşınma, erişim ve hariç tutma

Kök başarıyla ve ilgili alt kapsam eksiksiz listelenmeden dosya “silindi” yapılmaz. Kısmen erişilemeyen dizinin altındaki görülmeyen kayıtlar korunur; son görülme ve erişim durumu gösterilir. Bir dizindeki hata bütün taramayı “tamamlandı” yapmaz; tarama “kısmi” sonuç verir.

Tam listeleme sonrası artık olmayan dosya normal sonuçlardan kaldırılır; yerel metadata/iş geçmişi için başlangıç 30 günlük tombstone adayı tutulabilir. İçerik saklama politikasıyla uyumlu biçimde aktif parça/FTS temizlenir. Bu işlem NAS dosyasını silmez.

Taşınan/yeniden adlandırılan dosya, NAS kimliği güvenilir değilse yeni yol olarak görülür. Aynı tam hash bulunursa yol ilişkisi güncellenebilir; dosya kimliği veya tek kopya olduğu tahminle birleştirilmez.

Yeni hariç kuralı kaydedildiğinde:

- Yeni iş girişleri engellenir ve bekleyen işler iptal edilir.
- Çalışan işin sonucunun DB'ye yazılması da son kapsam kontrolüyle engellenir.
- Mevcut aktif içerik, arama temsilleri, FTS ve önizleme cache'i temizlenir.
- Hariç tutulan dosyalar hakkında yeni içerik/metadata tutulmaz; hariç kuralının kendisi kasada durabilir.
- Eski yedeklerin daha önce indekslenen içeriği barındırabileceği açıklanır. Otomatik geri alma veya güvenli fiziksel silme vaat edilmez.

DB'den mantıksal silme ile SSD/backup üzerinden adli olarak geri getirilemez silme farklıdır. Gerekirse yeniden oluşturulan kasa ve yedek yaşam döngüsü kullanılır; normal DELETE “güvenli silme” olarak adlandırılmaz.

Offline arama: son yerel metinle sonuç üretilebilir; “kaynak erişilemiyor, son indeks …” bilgisi görünür. Başarıyla erişilen NAS'ta yeni bir access denied görülürse kayıt normal aramadan gizlenir ve içerik temizleme politikası uygulanır. Eski yedek/çevrimdışı indeks NAS izinlerinin gerçek zamanlı kopyası değildir. V1 kurumsal merkezi yetki iptali sistemi sunmaz.

Güncellik sözleşmesi: kaynak yalnız erişilemiyorsa son doğrulanmış içerik uyarıyla aranabilir; kaynakta değişiklik doğrulandıysa eski içerik normal aramaya girmez; dosya missing/erişim reddedildi/hariçse normal sonuçlarda görünmez. Kullanıcı eski sürüme açıkça bakmayı seçerse yalnız hâlâ izinli kapsamda gösterilir. Aktif eski metin saklama bütçesi en fazla bir önceki revision ve varsayılan 7 gün adayıdır; hariç ve access-denied temizliği bu süreyi beklemez.

## 11. OCR: kaliteyi kaynak bütçesiyle koruma

Varsayılan temel motor GPU'suz Tesseract'tır. Türkçe tur ve gerekli İngilizce eng modeli; yön analizi için osd paketlenir. “TR önce sonra EN” ezberi yerine dil kombinasyonları pilotta aynı sayfalarda ölçülür; gereksiz tüm dilleri yüklemek yok.

Temel geçiş:

- Sayfa metni ve metin içeren görüntü varlığı değerlendirilir.
- Gerekirse sınırlı çözünürlükte render; başlangıç 300 DPI, piksel/bellek limitiyle.
- Gri ton, yön düzeltme, makul eğiklik düzeltmesi ve gürültü yaklaşımı uygulanır.
- Tesseract fast/best model profili referans CPU'da kalite-hız karşılaştırmasıyla seçilir.
- Metin, token confidence, satır ve mümkünse bbox saklanır.

Kalite iyileştirme geçişi:

- Yalnız sorunlu sayfalar; en fazla belirlenmiş ek deneme sayısı.
- Best model, farklı segmentation ve kontrollü farklı görüntü ön işleme adayları.
- Sayfa boşsa sonsuza kadar OCR denemek yok.
- İlk sonuçla karşılaştırılır; daha uzun çıktı otomatik olarak daha iyi değildir.
- Çıktı kötüleşirse önceki sürüm korunur. Sonuç “düşük güven” olarak kalabilir.

Bu ikinci geçiş V3'teki iki katmanlı kalite hedefini düşük kaynaklı temel üründe korumayı amaçlar; aynı motorun tekrarının daha iyi olacağı garanti değildir. Kazanç gerçek Türkçe örneklerde ölçülmelidir. [Tesseract kalite rehberi](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)

Ağır yerel OCR eklentisi:

- Marker veya başka motor temel kurulumun şartı değildir.
- Ek paket seçilirse sürüm/model/lisans/hash manifesti ayrı kilitlenir.
- Önce CPU-only veya mevcut GPU'da hedef RAM ve süre kanıtlanır.
- Model otomatik internetten indirilmez; eksik paket uygulamayı düşürmez.
- Cloud/LLM modu kapalı; ağ gözlemi ve internet engelli test zorunlu.
- Bütün arşive otomatik çalıştırılmaz; yalnız kalite kuyruğu veya seçili belge.
- Örneklerde anlamlı kalite artışı göstermeyen motor eklenmez.

Marker'ın kod ve model lisansları ayrı; güncel sürüm/model çalışma koşulları değişebilir. Bu yüzden V3'ün “3–5 GB, ücretsiz, her PC'de uygun” varsayımı kaldırılmıştır. [Marker resmi deposu](https://github.com/datalab-to/marker)

OCR kalite ölçüsü confidence yanında anlamsız karakter oranı, tekrar patlaması, sayfa metin yoğunluğu, bilinen belge sözcükleri ve kontrollü doğrulama örneklerini içerir. Alan sözlüğü yeni isimleri reddetmez. VKN/TCKN gibi biçim kontrolleri doğruluk kanıtı sayılmaz.

Başlangıç timeout profili: sayfa render/temel OCR 60 saniye adayı, iyileştirme 120 saniye adayı. Toplam belge limiti sayfa sayısına bağlı ve üst sınırlıdır. Büyük belgeye tek 30 sn kuralı uygulanmaz. Süre dolunca ilgili süreç gerçekten sonlandırılır; kuyruğa yalnız timeout bayrağı eklemek yeterli değildir.

## 12. Veritabanı: mantıksal şema ve tutarlılık

Veritabanı %LOCALAPPDATA%/Evrakci/Data/evrakci.db altında. Kaynaklarda, çalışma klasöründe veya kurulum dizininde oluşturulmaz. Gerçek DDL teknik pilot sonrasında bu sözleşmeden türetilir; şema sürümü migration ile yönetilir.

| Varlık | Temel alanlar / ilişkiler |
|---|---|
| roots | root_id, display_path, canonical_path, type, company_rule, enabled, health |
| exclusions | exclusion_id, root_id, path_rule, created_at |
| companies | company_id, display_name, aliases; kök kurallarından türeyebilir |
| files | file_id, root_id, path, canonical_path, relative_path, name, ext, size, mtime, signature, company_id, last_seen_scan, source_status, index_status, active_revision |
| file_revisions | revision_id, file_id, observed_signature, extractor_version, extraction_time, quality, completeness, error_code |
| segments | segment_id, revision_id, kind, ordinal, page, page_label, sheet, row/col range, paragraph/table location, raw_text, quality, bbox/offset_map |
| file_years | file_id, year, source_kind, evidence_segment, confidence; çoklu yıl destekler |
| search_documents | file_id ve active_revision ile bağlı strict/folded title/context/body; segments'ten yeniden üretilebilir |
| document FTS | file_id rowid ile strict/folded indeks; title/context/body alanları |
| segment search / FTS | segment_id bağlantılı, konumlu snippet için; metadata her parçada gereksiz tekrarlanmaz |
| vocabulary | normalized_term, frequency, varyant bilgisi; aktif indeksle tutarlı |
| file_hashes | file_id, revision_signature, full_sha256, hash_status, verified_at |
| jobs | job_id, file_id/revision, kind, status, attempts, not_before, lease_until, progress, error_code |
| scan_runs / scan_scopes | run_id, başlangıç/sonuç; kök/alt kapsam enumeration completeness |
| history | query_id, original_query, normalized_query, filters, pinned, used_at |
| settings | şifreli uygulama tercihleri ve kaynak ayarları |
| schema_meta | schema_version, normalizer_version, extractor_version ve uyumluluk |

Dosya düzeyinde aday bulma ve parça düzeyinde konum bulma ayrıdır. “Ankara” klasör adında, “Ayşe” 1. sayfada ve “vergi levhası” 3. sayfadaysa belge bulunabilmelidir. Bütün sorgu kelimelerinin tek segmentte bulunması zorunlu değildir. Tek snippet'te tüm kelimeler varmış gibi gösterilmez.

FTS dış içerik ve açık rowid ilişkisiyle uygulanabilir. Tablo ve FTS güncellemeleri transaction/trigger veya tek repository protokolüyle tutarlı tutulur. FTS'e dosya yolunu bağlamak için gizli sıra varsayımı yok. Rebuild, segment/search_documents verisinden yapılabilir; kaynak NAS'ın o anda erişilebilir olması gerekmez. [FTS5 harici içerik](https://www.sqlite.org/fts5.html#external_content_tables)

Zorunlu DB kuralları:

- foreign_keys açık; FK ve indeksler gerçek sorgularla doğrulanır.
- WAL yalnız yerel diskte, SQLCipher ile; write transaction'ları kısa tutulur.
- busy_timeout ve sınırlı retry; kilitli DB nedeniyle arayüz sonsuza kadar beklemez.
- Disk dolduğunda transaction geri alınır; son başarılı indeks korunur.
- Checkpoint bakım içindir; her dosyada ağır checkpoint zorunlu değildir.
- Ayrı düz metin checkpoint/settings dosyası yok.
- FTS bozulması ile ana DB bozulması ayrılır. FTS rebuild ana kasayı silmez.
- Yeni sürümde çıkarıcı/normalizasyon değişikliği gereken kayıtları yeniden işler; bütün arşiv körlemesine silinmez.
- Orijinal metin ve arama için normalize metin ayrılır. Snippet raw_text'ten ve doğru offset dönüşümünden üretilir.
- Arama verisinin çoğaltma maliyeti ölçülür; RAM'i büyütmeden DB hacmi optimize edilir.

Yerel disk yönetimi: en az 1 GB veya tahmin edilen sıradaki iş+transaction/yedek hacmi için daha büyük bir boş alan rezervi adayı. İndeks büyüklüğü üst sınırı örneğin 5 GB başlangıç ayarı olabilir; limit yaklaşınca kullanıcıya neden ve seçenekler gösterilir. Sınır için kaynaklar veya sessizce kullanıcı geçmişi silinmez. Yedek/migration öncesi gerekli staging alanı hesaplanır; alan yoksa işlem başlamaz. Kaynak hacminin belirli bir yüzdesinin DB olacağı vaat edilmez.

Durumlar tek bir status sütununda karıştırılmaz: source_status (erişim), index_status (içerik tamamlığı), job_status (iş yaşam döngüsü), error_code (neden) farklıdır. OCR kullandı bilgisi hata/durum yerine yöntem metadata'sıdır.

## 13. Arama sözleşmesi

### 13.1 Girdi ve normalizasyon

- Arama kutusu Türkçe Unicode metni, sayıları ve tırnaklı ifadeleri kabul eder.
- NFC ve Türkçe I→ı, İ→i dönüşümü; çoklu boşluk düzenleme.
- Tire/apostrof gibi ayrımlar kontrollü tokenizasyon; orijinal ifade korunur.
- Ana normalizasyon Türkçe harfleri korur. Tolerans katmanı ş/s, ğ/g, ç/c, ö/o, ü/u, ı/i eşlemesini ayrı yapar.
- Strict indeksin diakritik politikası açık seçilir; unicode61 varsayılanı körlemesine kullanılmaz.
- Sorgu ve belgede aynı normalizer_version uygulanır.
- Tek harfler koşulsuz silinmez; “A Blok” ve dosya kimlikleri korunur.
- Dur kelimeler tırnaklı ibarelerde ve anlamlı kimliklerde kaldırılmaz; ilk geçişte bütün sorguyu bozacak sadeleştirme yok.
- 19xx/20xx tam tokenları yıl adayı; tarih ve belge numarası bağlamı gözlenir. Çoklu yıl korunur.
- Yalnız dur kelime/boş girdi tüm arşivi yanlışlıkla fuzzy taramaz; açık boş durum gösterir.
- Sorgu uzunluğu/token sayısı üst sınırı ve iptal edilebilir timeout vardır.
- Kullanıcı metni SQL veya ham FTS dili olarak çalıştırılmaz. Parametreli SQL ve ayrı güvenli FTS query builder kullanılır.

### 13.2 Aday bulma ve kontrollü genişletme

1. Ad, şirket/klasör bağlamı ve içerikte güçlü strict eşleşmeler.
2. İfadenin güçlü eşleşmeleri korunurken diakritik tolerans ve kontrollü önek genişletme.
3. Sonuç az/yetersizse vocabulary üzerinden fuzzy adaylar.
4. Yeniden oluşturulan sınırlı sorgularla belge adayları.
5. Belge ve en iyi segmentler puanlanır; kopya grubu ve filtreler uygulanır.

Prefix kök bulma değildir. “levhası” → “levha” ancak uygulamanın ölçülmüş terim/ek kuralıyla oluşur. Sınırsız suffix kesme kişi ve şirket adlarını bozar. İlk sürümde belge terimleri için küçük, testli alias listesi ve indeks sözlüğü önerilir; tam Türkçe morfoloji motoru zorunlu değildir.

Fuzzy sınırları başlangıç adayları: token başına en fazla 3 düzeltme, en fazla 20 genişletilmiş kombinasyon, sıralama için en fazla 500 belge. Kısa tokenlarda daha katı eşik. Tam kimlik numaraları/yıllar otomatik yaklaşık eşleşmeye çevrilmez. Eşik “her kelimede 80” olarak sabitlenmez; holdout sorgularla ayarlanır.

“vergile evha” birleşme/bölünme hatası için komşu token adayları sınırlı olarak denenir. Bu örneğin mutlaka bulunması vocabulary, belge ve test kümesiyle doğrulanır; sadece similarity çağrısı var diye geçti sayılmaz.

Sorgu yazarken yaklaşık 300 ms debounce; Enter hemen çalıştırır. Önceki sorgu iptal edilir, eski sonuç yeni sorgunun ekranını sonradan dolduramaz. Tarama sırasında sonuçlar kontrollü güncellenir; seçili belge gereksiz yere zıplamaz.

### 13.3 Sıralama ve açıklama

Basit ad×3/içerik×1 toplamı tek sıralama algoritması değildir. Önce eşleşme sınıfı, ardından sorgu kapsamı, alan ağırlıkları, terim yakınlığı ve BM25 benzeri alaka değerlendirmesi kullanılır. Büyük belgeler sırf daha çok tekrar içerdi diye öne çıkmaz.

Başlangıç alan önceliği: dosya adı ve doğrulanmış şirket/klasör bağlamı > içerik; açık tam ifade > tek sözcük; strict > toleranslı > yaklaşık. Aynı durumda belirleyici sabit son sıralama vardır. Özel puanlar testten önce “doğru” kabul edilmez.

Yıl sorguda varsayılan alaka etkisidir; kullanıcının açık yıl filtresi katı kuraldır. Dosya/klasör yılı daha güçlü bağlam, içerikte geçen yıl gözlenen kanıttır. Dosya mtime yılı belge yılı olarak kullanılmaz. Birden fazla yıl “birden çok yıl” olarak gösterilebilir.

Sonuç başına: belge adı, şirket veya bilinmiyor, dosya türü, yıl/kanıt özeti, eşleşen snippet, gerçek konum, erişim/güncellik, kopya rozeti. İsteyen kullanıcı “neden bulundu” detayında hangi alanların eşleştiğini görür. Matematiksel puan kullanıcıya güven yüzdesi diye sunulmaz.

İlk 50 sonuç, “daha fazla göster” ile sayfalama. Üst limit yüzünden gerçek eşleşmeler kaybolmuş gibi gösterilmez. Toplam sayı pahalıysa “en az …” veya yüklenen sayı dürüstçe kullanılır.

Güçlü eşleşme yoksa açık mesaj ve ayrı yakın öneriler. Her koşulda beş alakasız dosya üretmek yok. Önerilerde eşleşmeyen önemli kelimeler açıklanabilir. Filtreler sonucu daralttıysa “filtreleri temizle” eylemi vardır; filtreler sessizce gevşetilmez.

### 13.4 Geçmiş

Son 20 sabitlenmemiş arama + başlangıç en fazla 50 sabitlenmiş arama. Sorgu ve filtre birlikte saklanır, tekrar kullanım used_at günceller. Geçmiş ekranında tek kaydı sil ve tüm geçmişi temizle var. Kasa kilitliyken geçmiş görünmez. Harici düz metin log veya telemetry'ye yazılmaz.

## 14. Kopya ve benzerlik

Tam dosya SHA-256'sı aynı ve mevcut dosya sürümünde doğrulanmışsa birebir kopya grubu. İki boş çıkarılmış metin veya ilk 64 KB metin aynı diye grup yok. Aynı metin fakat farklı dosya “birebir kopya” değildir; V1'de sonuçları gizlemeyen ayrı bilgi olabilir.

Hash arka plan işidir; kaynak tekrar okuma maliyeti ölçülür. Uygunsa çıkarma sırasında edinilen okuma akışıyla bütünlük hash'i birlikte hesaplanır; seek kullanan okuyucularda tek geçiş garanti edilmez. Büyük dosya her sorguda tekrar hash edilmez.

Filtreler ve erişilebilirlik grup oluşturmadan önce değerlendirilir. Grup yalnız görünür yolları sayar; başka şirket filtresindeki yolu sessizce göstermez. Temsilci mevcut/erişilebilir en uygun dosya; alternatif yollar açılır panelde. Kaynak metadata değişince eski hash doğrulanmış sayılmaz.

Gruplama tamamlanmamışsa “kopya denetimi bekliyor” denebilir. Benzer belgeler V2 ters aramaya kalır; zayıf benzerlik yüzünden belge gizlemek yok.

## 15. Kasa, güvenlik ve yaşam döngüsü

İlk açılışta şifre iki kez; minimum 12 karakter önerilen V4 varsayılanı, uzun Türkçe passphrase kabulü, katı karmaşıklık oyunu yok. Şifre/anahtar diske, komut satırına, environment'a, loga veya ayarlara yazılmaz. SQLCipher'ın key derivation mekanizması kullanılır; özel kripto icat edilmez.

Yanlış şifre: ilk üç başarısız denemede artan bekleme, üçüncüde kasa oturumu kapanır. Kaynak veya DB silinmez. Başarısız giriş logu şifre içermeyen sınırlı güvenlik olayıdır. Uygulamayı tekrar açmayı engelleyen bu kural DB'yi çevrimdışı kaba kuvvetten tek başına korumaz.

Yanlış anahtar ile DB bozulması her hatada kesin ayrılabilir varsayılmaz. Hata ekranı veriyi değiştirmez; yeniden şifre dene, doğrulanmış yedek aç veya ayrı yeni kasa oluştur seçeneklerini sunar.

Kilit politikası:

- Windows açılışında tepside kilitli başlar; varsayılan hiçbir şifre hatırlama yok.
- Kilit açılmadan NAS kökleri, geçmiş ve belge metni görünmez; tarama yok.
- Windows oturum kilidi/uyku geçişinde kasa kilitlenir; devam eden işler iptal/ertelenir.
- Kullanıcı “Kasayı kilitle” dediğinde yeni işler durur, çocuklar kapanır, DB bağlantıları kapanır, sonuç/önizleme/geçmiş ve cache temizlenir.
- Salt kullanıcı hareketsizliğine bağlı otomatik kilit ilk sürümde kapalı olabilir; 5/15/30 dk ayarı ve tarama etkisi açıklanır.
- Python/Qt nesnelerindeki tüm RAM kopyalarının veya pagefile/crash dump içeriğinin kusursuz silindiği iddia edilmez.
- SQLCipher memory_security ve temp store ayarları gerçek build'de doğrulanır; DB şifreli diye bütün türevler şifreli kabul edilmez.

V1'in güvenlik amacı kapalı kasanın yerel DB/backup gizliliği ve uygulamanın kaynaklara yazmamasıdır. Aynı Windows oturumunda yönetici/malware, kaynak NAS erişimi, ekran görüntüsü ve kullanıcı tarafından açılan harici programlar karşısında mutlak koruma vaat edilmez.

## 16. Yerel veri, geçiciler ve loglar

| Yer | İçerik | Politika |
|---|---|---|
| %LOCALAPPDATA%/Evrakci/Data | Şifreli DB, WAL ve yönetilen kasa dosyaları | Kullanıcı hesabına ait; plaintext export yok |
| %LOCALAPPDATA%/Evrakci/Backups | Şifreli indeks snapshot'ları | Aynı disktekinin felaket yedeği olmadığı açıklanır |
| %LOCALAPPDATA%/Evrakci/Temp | Gerekirse OCR/dönüşüm türevleri | İşe özel rastgele dizin; sıkı ACL; iş/çökme sonrası temizlik |
| %LOCALAPPDATA%/Evrakci/Logs | Sınırlı teknik tanı | İçerik, tam yol, kişi adı, query ve anahtar yok |
| %LOCALAPPDATA%/Evrakci/bootstrap.json | Tema, pencere ölçüsü, data-format sürümü gibi hassas olmayan başlangıç tercihleri | NAS kökü, belge bilgisi ve şifre bulunmaz |
| Kurulum dizini | Exe, kütüphane, logo, lisans, temel OCR | Runtime veri buraya yazılmaz |
| Opsiyonel model dizini | Önceden hazırlanmış ağır modeller | Manifestle doğrula, otomatik indirme yok |

Uygulama verisi için yollar mutlak ve çalışma dizininden bağımsız. Geçici dosya üreten üçüncü taraf kütüphanelerin çalışma/temp yolu da kontrollü yönlendirilir. Cache varsayılan RAM'de, sınırlı LRU; plaintext thumbnail cache yok.

Gerekli yerel plaintext OCR türevleri geçicidir; silinmelerinin SSD'den geri getirilemezliği garanti edilmez. Yüksek gizlilik modunda disk türevleri kapatılıp uyumsuz motor kullanılamaz olarak bildirilir. Parola değiştirme/yedek dahil hiçbir işlem otomatik şifresiz DB yaratmaz.

Loglar döner: başlangıç 5 × 2 MB gibi küçük üst sınır. Hata kodu, süre, job_id, bileşen sürümü ve anonim sayı yeterlidir. Destek raporu kullanıcı isteğiyle yerel oluşturulur ve gönderilmez. İsim, path, snippet, sorgu ve sır taraması yapılarak temizliği doğrulanır.

Çalışma sırasında internet update/telemetry/download yok. NAS erişimi dışında internet bağlantıları test edilir. Kod üzerinde HTTP kelimesi aramak tek başına yeterli değildir; paketli süreç ve çocukların ağ davranışı gözlenir.

## 17. Şifreli yedek, geri yükleme ve migration

Yedek = kasa, indeks, geçmiş ve ayarların şifreli snapshot'ı. Kaynak PDF/Office belgeleri yedeklenmez. Kullanıcı “İndeks yedeği” ifadesini görür.

Varsayılan hedef yerel Backups. Kullanıcı açıkça başka yerel/USB hedef seçebilir; seçilen hedef kaynak kökleri veya onların altı olamaz. NAS kaynağına hiçbir yedek yazılmaz. İzin verilen runtime yazmaları yönetilen yerel dizinler ve kullanıcının açık yedek hedefidir; kaynaklar kesin reddedilir.

Yedek protokolü:

1. Yeni indeks transaction'ları kısa süre bekletilir; aktif işlem güvenli noktaya gelir.
2. Seçilen SQLCipher sürücüsüyle doğrulanmış encrypted backup/export yolu kullanılır.
3. Hedef geçici isimle oluşturulur, hata/iptalde yarım dosya tamamlanmış listesine alınmaz.
4. Ayrı bağlantıda doğru şifreyle yeniden açılır, cipher/integrity ve örnek içerik/arama kontrolü yapılır.
5. FTS dahil tutarlılık doğrulanır, hedef son ada atomik finalize edilir.
6. Tarih, şema ve uygulama sürümü gibi hassas olmayan manifest/hash kaydı oluşturulur.

SQLite backup API veya SQLCipher export adayının şifreleme uyumu bu build'de kanıtlanmadan kullanıldığı ilan edilmez. Çalışan evrakci.db dosyasını tek başına shutil.copy ile kopyalamak yasak. [SQLite backup](https://www.sqlite.org/backup.html), [SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/)

Başlangıç saklama politikası: 7 son başarılı otomatik yerel indeks yedeği adayı; kullanıcı manuel yedekleri ayrı listelenir ve sessizce silinmez. Disk üst sınırı ve temizleme kapsamı ayarlarda görünür. Her taramada pahalı full backup şart değil; günlük başarılı çalışmadan sonra ve migration öncesi önerilir. Başarısız taramayı başarılı durumla karıştırmaz.

Geri yükleme: tarama/arama yazmaları durur; seçilen yedek ayrı staging dizininde doğrulanır. Mevcut kasa değiştirilmeden rollback snapshot korunur. Şema uyumluysa kapalı bağlantılarla kontrollü değişim, yeniden açma, örnek arama. NAS'a yazma yok; kaynakların yeniden doğrulanması kuyruğa alınır. Eski yedek şifresi mevcut şifreden farklı olabilir.

Restore öncesinde kaynak/hariç/ayar farkları kullanıcıya özetlenir. Mevcut hariç kuralları varsayılan korunur ve geri getirilen DB'ye arama açılmadan uygulanır; eski yedekte bulunması bir klasörü kendiliğinden yeniden kapsama sokmaz. Kullanıcı eski kaynak ayarlarını da geri getirmeyi açıkça seçerse bu bir kapsam değişikliğidir. Kaynak erişimleri yeniden doğrulanana kadar eski dosya durumu “güncelliği doğrulanmadı” kalır. Backup listesindeki bir dosyanın eski olması onu otomatik güvenilir yapmaz.

Parola değiştirme: eski parola doğrulanır, önce yedek, crash-safe yeni şifreli kasa/verified export ve atomik geçiş tercih edilir. Eski yedeklerin eski parolayla açılacağı belirtilir. Başarısız değişimde eski kasa korunur. Şema migration aynı rollback/restore testine tabidir; geri dönüş yolu doğrulanmadan eski sürüm destekleniyor denmez.

## 18. Zamanlama, otomatik başlatma ve tepsi

- Varsayılan yerel saat 12:30; saat/dilimi açık, ayarlanabilir.
- Uygulama kapalıyken iş çalışmaz; Windows görev zamanlayıcısı/sunucu servisi yok.
- Uygulama kilitliyken iş çalışmaz. Kilit açılınca o gün kaçırılan planlı iş bir kez başlatılabilir.
- Uyku sonrası dönüş ve saat değişimi yeniden değerlendirilir; aynı günlük plan slotu iki kez koşmaz.
- Manuel “Şimdi tara” aynı koordinatörü kullanır; ikinci tarama açmaz.
- Tarama sürerken düğme “Tarama sürüyor”/durum ekranına git davranışı verir; tekrar tekrar kuyruk çoğaltmaz.
- Kaçırılan birkaç gün için tek catch-up tarama; her geçmiş güne ayrı tarama yok.
- Otomatik başlatma kullanıcı hesabı düzeyinde, kapatılabilir; yönetici yetkisi istenmez.
- Exe yeri değişince eski startup kaydı ve eksik yol durumu tespit edilir; kullanıcıya düzeltme eylemi sunulur.
- Pencere X ile kapanınca varsayılan tepsiye küçülme ilk kullanımda açıklanır; ayarda gerçekten çıkma seçeneği.
- Tepsi: Aç, Tarama durumu, Kasayı kilitle, Çıkış. Kilitliyken hassas bilgi/şirket adı göstermez.
- Bildirimlerde belge/kişi adları yok; yalnız tamamlanma, önemli hata veya kullanıcı eylemi gerektiği durumlar.

## 19. Modern arayüz ve tasarım sistemi

Tasarım yönü: sade, resmi ve rahat okunur belge çalışma alanı. Mavi marka, kontrollü yüzeyler, ince ayırıcılar, tutarlı ikonlar. Aşırı cam efekti, ağır animasyon, küçük yazı ve gereksiz gösterge kartları yok.

Ana yerleşim:

    ┌ Evrakçı             Arama kutusu                   Şimdi tara  Tema  Menü ┐
    │ Sol gezinme     │ Sonuçlar + etkin filtreler       │ Belge önizlemesi     │
    │ Ara             │ Ad / tür / şirket / yıl          │ Eşleşme / konum      │
    │ Kaynaklar       │ Alıntı + bulunma gerekçesi       │ PDF sayfası veya     │
    │ Tarama durumu   │ Kopya ve güncellik               │ veri / metin bölgesi │
    │ Geçmiş          │                                  │ Alternatif yollar    │
    │ Yedekler        │                                  │                     │
    │ Ayarlar         │                                  │                     │
    └ Kasa açık • Kaynak durumu • Son başarılı tarama • Aktif iş özeti ─────────┘

Sol gezinme daraltılabilir; filtreler arama alanında küçük bir paneldir. Şirket, tür ve yıl seçimleri arama bağlamını kaybetmeden değiştirilir. Tarama ayrıntısı ayrı ekran/panel; arama ekranı bir kontrol merkezi karmaşasına dönüşmez.

Sonuç görünümü kompakt iki satırlı liste/table model. Binlerce QWidget/kart yaratılmaz. Çok sütunlu ayrıntı görünümü isteğe bağlı; ilk kullanımda okunur belge listesi. Sağ önizleme yeniden boyutlandırılabilir ve kapatılabilir. Dar ekranda önizleme seçilen belgeye geçici panel olarak açılır; arama listesi kaybolmaz.

Tema tokenları, önerilen başlangıç paleti:

| Token | Açık | Koyu |
|---|---|---|
| Ana zemin | #F5F7FB | #111827 |
| Panel | #FFFFFF | #1B2434 |
| Ana metin | #172033 | #F3F6FC |
| İkincil metin | #526176 | #BAC5D6 |
| Marka/etkileşim | #1D3FAA | #8FAEFF |
| Sınır | #DCE3ED | #39465C |

Renkler tasarım başlangıcıdır; bütün text/background ve durum kombinasyonlarında kontrast ölçülür. Marka SVG mavi korunur; koyu temada uygun açık çizgi/zemin varyantı olabilir. Açık/koyu/sistem seçimi ayarlarda ve pratik tema menüsünde; sistem teması program açıkken değiştiğinde uygulanır. Başlangıç ekranı da doğru tema ile açılır.

- Font: Windows Segoe UI/uygun sistem fontu; Türkçe glifler doğrulanır.
- Temel yazı yaklaşık 15–16 logical px; başlık 20–24; DPI/font ölçeğinde okunurluk korunur.
- Boşluk sistemi 4/8/12/16/24; bileşen yüksekliği yaklaşık 36–40 logical px.
- Odak halkası, seçili/hover/disabled/busy durumları ayrı tokenlarla.
- Köşe yarıçapı tutarlı, yaklaşık 8–10 px; gölgeler hafif.
- Standart Windows pencere çerçevesi, resize/snap davranışı korunur.
- İkonlar tek SVG ailesi; durum yalnız renkle anlatılmaz, metin/ikon eşlik eder.
- Kısa animasyonlar yaklaşık 120–180 ms; reduced motion ayarı/OS tercihi dikkate alınır.
- Normal metin için 4,5:1 kontrast hedefi; W3C ölçütleri masaüstü tasarım rehberi olarak kullanılır, otomatik WCAG sertifikası iddia edilmez.
- Tab sırası, ekran okuyucu etiketleri, tooltip ve erişilebilir isimler test edilir.
- 100/125/150/200% Windows DPI, yüksek font ölçeği ve iki monitör geçişi doğrulanır.
- Başlangıç hedef viewport 1366×768; daha dar alanlarda panel daraltma. Pencere ölçüsü DPI sonrası yanlış minimuma kilitlenmez.
- Pencere boyutu/splitter tercihleri kaydedilir; kaybolmuş monitörde açılan pencere görünür ekrana taşınır.

Qt model/view büyük sonuç listeleri için, sistem color scheme sinyalleri tema takibi için kullanılır. [Qt model/view](https://doc.qt.io/qt-6/model-view-programming.html), [Qt DPI](https://doc.qt.io/qt-6/highdpi.html), [Qt tema](https://doc.qt.io/qt-6/qstylehints.html), [Kontrast rehberi](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum)

## 20. Ekranlar ve kullanıcı akışları

### 20.1 İlk açılış sihirbazı

1. Kısa amaç/gizlilik açıklaması: kaynaklar değişmez; yerel indeks metin içerir.
2. Kasa şifresi ve unutulması halinde yeni indeks gerekeceği bilgisi.
3. Kaynak seçimi: lazy ağaç, UNC/yol girişi, hariçler, erişim örnekleri.
4. Gerekliyse kök başına şirket kuralı; örnek yorumlama önizlemesi.
5. Tema tercihi isteğe bağlı; varsayılan sistem. Gelişmiş ayar zorunlu değil.
6. Tarama özeti: seçilen kapsam, 200 MB içerik limiti, temel OCR, kaynak profili.
7. Kullanıcı “İlk taramayı başlat”; keşif ekranı ve eşzamanlı kullanılabilir arama.

Henüz dosya sayısı bilinmiyorsa tahmini kesin süre verilmez. Sihirbaz yarıda kapanırsa kasa bozuk sayılmaz; kaldığı ayar adımından devam eder.

### 20.2 Arama

Giriş → debounce/Enter → iptal edilebilir arama → güçlü sonuçlar/ayrı öneriler → tek tık snippet → çift tık dahili ayrıntı. Filtre değişimi sorguyu yeniden çalıştırır ve aktif filtreler görünür. Boş sorguda son aramalar veya ilk kullanım açıklaması; bütün içerik kendiliğinden listelenmez.

### 20.3 Önizleme

PDF gerçek sayfaya gider, zoom ve önceki/sonraki eşleşme. Güvenilir bbox yoksa kutu uydurulmaz; metin ve sayfa gösterilir. Excel ilgili sheet/hücre alanının sınırlı grid'i; Word paragraf/tablo bölgesi. Office sayfa düzeninin birebir render'ı V1 vaadi değildir.

Önizleme okuma öncesi dosya sürümü kontrol edilir. Kaynak değişmişse eski snippet ile yeni görüntü aynı sürümmüş gibi sunulmaz; “kaynak değişti, yeniden indeksleme bekliyor” uyarısı ve yeni görüntü ayrımı vardır. NAS erişilemiyorsa son indeks metni gösterilebilir, gerçek sayfa görüntüsü yoksa yok denir.

Harici açma varsayılan ana eylem değildir. “Varsayılan uygulamada aç” açık kullanıcı eylemi; ilk kullanımda harici uygulamanın dosya değişikliği yapabileceği kısa bilgi. Salt okunurluk garantisi gibi sunulmaz. Dosya uzantısı/değeri açılmadan doğrulanır; exe/script açma yok. Otomatik harici link takip edilmez.

### 20.4 Kaynaklar ve hariçler

Her kök: erişim, son tam tarama, şirket kuralı, kapsamdaki kayıt sayısı. “Kaynağı kaldır” yerel indeks kapsamını kaldırır; NAS dosyalarını kaldırmadığı belirtilir. “Hariç tut” etkisi içerik temizleme ve eski backup sınırıyla açıklanır.

### 20.5 Tarama durumu

Keşfedilen/indekslenen/yeni/değişen/ertelenen/okunamayan/OCR sayfa sayıları. Aşama, geçen süre, okunan veri, tahmini kalan ancak yeterli örnekten sonra. Son tam başarılı ve son deneme ayrı. Hata listesinde dosya, kullanıcıya anlaşılır neden, tekrar dene eylemi; burada hassas yol kullanıcıya gösterilebilir ama loga kopyalanmaz.

Duraklat/devam/iptal aynı koordinatör; hata listesi için ayrı “kilitli” sekmesi olabilir. “Bazı dosyalar okunamadı” durumu başarılı tam tarama rozetiyle gizlenmez.

### 20.6 Yedekler ve ayarlar

Yedek oluştur, doğrulama durumu, hedef, tarih, geri yükle. Ayarlar: tema, font ölçeği/yoğunluk, saat, kaynak profili, OCR kalite profili, otomatik başlat, pencere kapatma davranışı, kilit, parola değiştir, limitler ve geçmiş. Teknik motor ayrıntıları varsayılan temel ekrana yığılmaz.

Her ekran için durumlar: ilk kullanım, yükleniyor, normal, boş, filtre nedeniyle boş, kaynak offline, kısmi indeks, düşük RAM, disk dolu, hata, kilitli. Modal diyalog yalnız riskli yerel silme/restore gibi karar gerektiren işlemlerde; sıradan hata tüm programı durdurmaz.

## 21. Kaynak profili ve çok bilgisayarlı kullanım

Varsayılan “Dengeli” profil: tek kaynak okuma, tek CPU OCR, OCR için en fazla 2 CPU thread adayı, sınırlı render ve cache. “Sessiz” profil daha düşük öncelik ve dosyalar arası bekleme. Sabit 50/300 ms tek NAS koruması değildir; okuma hızı ve kaynak cevabı ölçülür.

Toplam bellek bütçesi bir koordinatör tarafından rezerve edilir: normal extractor + OCR + önizleme ayrı ayrı kendi sınırında olsa bile toplam sınırı aşacaksa arka plan işi bekletilir. Önizlemeye yer açmak için sonraki OCR sayfası ertelenebilir. Açık süreç sayısı ve her sürecin thread sayısı sınırlıdır. Kullanıcı profilini değiştirdiğinde çalışan işin ortasında güvensiz biçimde model/renderer değişmez; yeni politika sonraki işte uygulanır.

Başlangıç yerel davranış: kullanılabilir RAM 1,5 GB altında OCR duraklat, 2,5 GB üstünde kararlılık aralığı sonrası devam gibi histerezis adayları. Eşikler süreç bütçesi ve pilotla doğrulanır; normal arama kapatılmaz. Büyük iş bellek sınırında sonlandırılır, düşük kaynak olarak ertelenir.

3–5 kişi aynı anda tararsa NAS toplam yükü artar. Uygulama instance bazında sınırlar ve sabit tarama gecikmesi kullanır; ortak DB/merkezi servis olmadığından şirket çapında tek tarama garantisi yok. Pilot aynı anda en az iki PC ile yapılır; gerekirse saatler kullanıcıya göre dağıtılır.

Yeni PC: yeni kasa, kendi kaynak seçimi ve indeks. Eski PC'nin DB'sini NAS'a taşıyarak paylaşma yok. İsteğe bağlı şifreli indeks taşıma ancak ayrı doğrulanan restore akışıyla; yerel Windows yolları ve yetkiler yeniden doğrulanır. Temel V1 bunu zorunlu tutmaz.

## 22. Hata kodları ve kullanıcı mesajları

| Kod | Anlam / davranış |
|---|---|
| SOURCE_OFFLINE | Kök erişilemiyor; kayıtlar silinmiş sayılmaz |
| ACCESS_DENIED | Gerçek izin sorunu; source ve visibility politikası uygulanır |
| SHARING_VIOLATION | Okuma paylaşım kilidi; sınırlı retry |
| FILE_UNSTABLE | Okuma sırasında değişti/kopyalama sürüyor; ertelenir |
| PASSWORD_REQUIRED | Belge şifreli; otomatik parola denemesi yok |
| CORRUPT_DOCUMENT | Ayrıştırma bozuk; diğer işler sürer |
| NO_TEXT | Görünür metin bulunmadı; sayfa/format bağlamına göre OCR veya boş belge |
| UNSUPPORTED_CONTENT | İçerik biçimi/bölgesi desteklenmiyor; ad/yol bulunabilir |
| SIZE_LIMIT / PAGE_LIMIT / CELL_LIMIT | Limit aşıldı; kısmi durum ve ayar eylemi |
| ZIP_LIMIT / XML_LIMIT | Açılım/öğe güvenlik sınırı; başarısız iş |
| PROCESS_TIMEOUT | Süre doldu; çocuk gerçekten sonlandırılır |
| MEMORY_LIMIT | Süreç bütçesi aşıldı; düşük kaynak kuyruğu |
| MODEL_MISSING / ENGINE_UNAVAILABLE | Sistem OCR koşulu eksik; belge bozuk değil |
| DB_LOCKED | Sınırlı bekleme/retry; UI donmaz |
| DISK_FULL | Transaction rollback, yeni işler durur, kullanıcı eylemi |
| FTS_INCONSISTENT | Yeniden indeks yapısını kurma; kaynak metin korunur |
| VAULT_OPEN_FAILED | Şifre/format/bozukluk olası; otomatik overwrite yok |

Teknik hata stack'i kullanıcı mesajı değildir. Kullanıcı mesajları ne oldu, ne korunuyor, hangi eylem mümkün üçlüsünü kısa anlatır.

## 23. Test verisi, arama değerlendirmesi ve gizlilik

Otomatik testler yapay belgelerle; gerçek şirket arşivi repo'ya/test fixture'a konmaz. Gerçek pilot sadece yetkili yerel ortamda. Ekran görüntüleri ve raporlar kişisel veri içeriyorsa paylaşılmaz veya temizlenir.

Başlangıç sentetik corpus: en az 200 belge; tüm temel formatlar, çok sayfalı/karma PDF, benzer başlıklı farklı belgeler, farklı şirket/yıl, aynı dosyanın kopyaları, boş/şifreli/bozuk belgeler, Türkçe karakter ve kimlik örnekleri. 50.000 dosyalık hacim testi ayrıca, yapay veriyle.

Gerçek kalite pilotu: kullanıcının yetkili erişimiyle 100–300 temsilci belge ve en az 50 beklenen sonucu doğrulanmış sorgu. Özel veriler kopyalanmadan yerelde örneklenir; değerlendirme çıktıları şifreli veya anonim. Konum doğruluğu ayrıca doğrulanır.

Sorgu kümeleri: tam ifade, kişi/şirket, diakritik yokluğu, ı/i, yanlış yazım, çoklu yıl, başka sayfalara dağılmış terimler, belge numarası, filtre, bulunmaması gereken soru. Ayar kümesi ve en az %20 holdout ayrılır; test örneklerini ezberleyen özel kurallar yazılmaz.

Metrikler: ilk-1/ilk-3/ilk-10 bulunurluk, yanlış güçlü eşleşme, öneri ayrımı, konum doğruluğu, p50/p95, okunan bayt, OCR sayfa/süre/kalite, toplam süreç belleği, DB büyüklüğü ve NAS'a tekrar okuma. “Test yeşil” gerçek NAS kanıtı değildir.

## 24. Zorunlu kabul senaryoları

| ID | Senaryo | Kabul |
|---|---|---|
| SAF-01 | Yazma yetkili izlenen test paylaşımında tarama/OCR/önizleme/hata | Uygulamadan kaynak write/create/delete/rename isteği yok |
| SAF-02 | Salt okunur paylaşımda aynı akış | Temel işlevler çalışır; kaynakta lock/temp yok |
| SAF-03 | Junction, kök dışı yönlenme, kök önek çakışması | Kapsam dışı dosya okunmaz |
| SAF-04 | XML/ZIP bomb ve dev resim | Sınır uygulanır, UI/DB sağlam |
| SEC-01 | Doğru/yanlış şifre, Türkçe passphrase | Doğru açılır; yanlış açılmaz; disk/log/env'de anahtar yok |
| SEC-02 | DB+WAL+temp+backup üzerinde bilinen hassas canary | Kalıcı plaintext sızıntı yok; temp sınırı raporlanır |
| SEC-03 | Lock/Windows lock/uyku sırasında arama ve OCR | Sonuçlar temizlenir; eski worker çıktısı kasaya yazılmaz |
| SEC-04 | İnternet engellenmiş paketli uygulama | NAS ve temel OCR çalışır; indirme/AI isteği yok |
| DB-01 | Yazma transaction'ı sırasında süreç sonlandırma | Eski veya yeni tutarlı revision; yarım FTS yok |
| DB-02 | Yalnız FTS bozma | Metinden rebuild; kaynak listesi kaybolmaz |
| DB-03 | Disk dolu, locked DB | Hata dürüst, son başarılı indeks korunur |
| SCN-01 | 100 dosyada 40 tamamlandıktan sonra kesinti | Tamamlanan aynı sürümler tekrarlanmaz; yarım iş yeniden |
| SCN-02 | NAS kopması ve kısmi dizin izni | Toplu silinme yok; incomplete scope |
| SCN-03 | Dosya okuma sırasında değişir | Karışık çıktı aktif yapılmaz |
| SCN-04 | Yeni/değişen/silinen/taşınan/yeniden erişilen dosya | Kaynak ve yerel durumlar doğru |
| SCN-05 | Aynı saat manuel ve planlı tarama | Tek koordinatör/tek aktif tarama |
| SCN-06 | Kaynak değişti ama yeni içerik okunamadı | Eski metin normal sonuç değil; açık önceki sürüm ayrımı |
| EXC-01 | İndeksli klasör sonradan hariç | Aktif arama/FTS/cache/kuyrukta içerik yok |
| EXT-01 | PDF karma sayfalar, XLSX tablo/formül, XLS, DOCX tablo/header | Destek sözleşmesi ve gerçek konum doğru |
| EXT-02 | DOC adaptörü | Doğrulanmış support veya kullanıcıya açık kapsam engeli |
| OCR-01 | İyi metinli ve yalnız tarama sayfaları | Gereksiz OCR yok; gerekli sayfa kaçmaz |
| OCR-02 | İyileştirme ilk çıktıyı kötüleştirir | İyi çıktı korunur; confidence dürüst |
| OCR-03 | RAM/timeout/model yok | Kontrollü erteleme/sonlandırma; klasik arama çalışır |
| SRC-01 | Ankara Ayşe 2024 vergi levhası | Tanımlı corpus'ta beklenen sıralama ve kaynak açıklaması |
| SRC-02 | Ayse/Ayşe, I/İ/ı/i, vergile evha | Tolerans kapsamı geçer; yanlış güçlü eşleşme üretmez |
| SRC-03 | Yıl/kimlik/tırnak/boş/sadece dur kelime/FTS özel karakter | Güvenli ve öngörülebilir sorgu |
| SRC-04 | Terimler metadata ve farklı sayfalarda | Belge bulunur; konum açıklaması doğru |
| DUP-01 | İlk 64 KB aynı, son sayfa farklı | Tek kopya grubuna gizlenmez |
| DUP-02 | Tam bayt kopya, farklı company filtreleri | Grup ve görünür yol sayısı doğru |
| BAK-01 | Aktif indeks sırasında backup, ardından restore | Şifreli tutarlı snapshot; örnek arama doğru |
| BAK-02 | Yanlış şifre/bozuk/yarım yedek | Mevcut kasa overwrite edilmez |
| BAK-03 | Hariç ekledikten sonra daha eski backup restore | Hariç içerik aktif aramaya kendiliğinden dönmez |
| MIG-01 | Şema/parola değişimi sırasında çökme | Doğrulanabilir eski veya yeni kasa; geri dönüş |
| UI-01 | Tüm ekranlar üç tema, DPI/font/small viewport | Taşma/kırpma/okunmaz kontrast yok |
| UI-02 | Klavye, screen reader isimleri, yüksek kontrast | Ana akış erişilebilir |
| UI-03 | Arama devam ederken hızlı yeni sorgu/tema/iptal | Eski sonuç yeni sorguya karışmaz |
| PKG-01 | Python/Office/GPU olmayan temiz Windows | V1 temel akış; DOC önkoşulu varsa açık |
| PKG-02 | Türkçe kullanıcı/path, boşluk, uzun path, taşınmış exe | Runtime verisi doğru yerde; startup tutarlı |
| MULTI-01 | En az iki PC aynı NAS'ı tarar | İndeksler bağımsız, kaynak yükü ölçülmüş |

Yazma çağrısı grep'i yardımcı kontrol olabilir; native kütüphane ve harici süreçleri kapsamadığından tek kanıt değildir. UI offscreen testleri layout/işlevi ölçer, gerçek Windows görsel denetiminin yerine geçmez.

## 25. Uygulama aşamaları ve geçiş kapıları

### A0 — Gereksinim ve temsilci veri

Çıktı: işletim sistemi/donanım matrisi, kaynak yapısı örneği, format dağılımı, kullanıcı akışları, güvenlik sınırı ve seçili test senaryoları. İlk salt-okunur metadata keşfi ancak kullanıcı geliştirmeyi başlattıktan ve kaynağı seçtikten sonra yapılır. Şimdi gerçek NAS taraması yok.

Kapı: unknown'lar kayıtlı; hiçbir sayı uydurulmamış; DOC ve ağır OCR kararları ürün etkisiyle belirlenmiş.

### A1 — Teknik uygulanabilirlik

Çıktı: temiz Windows'ta paketli SQLCipher+FTS5 smoke; PDF render/metin; temel OCR; çalışan süreç sınırları; dependency/license lock adayları. Bu aşama gelecekteki geliştirme işidir, bu plan hazırlanırken yapılmaz.

Kapı: şifreleme, FTS5, yanlış key, encrypted backup, CPU-only OCR, native DLL ve süreç kapanışı kanıtları. DB'nin şifresiz fallback'i yasak. Doğrulanamazsa özellik tamamlandı değil, engel.

### A2 — Tasarım sistemi ve ekran sözleşmeleri

Çıktı: üç tema tokenları, temel bileşenler, arama/önizleme/kaynak/tarama/lock/sihirbaz durum tasarımları; 1366×768 ve yüksek DPI örnekleri. Koddan önce UI yönü review edilebilir; görsel prototip sonradan uygulama onayıyla hazırlanır.

Kapı: okunur hiyerarşi, kontrast, bütün hata/boş durumlar, ekranlar arasında tutarlılık. Modernlik ağır webview kurma gerekçesi değildir.

### A3 — Çalışan ilk dikey akış

Çıktı: kasa → kaynak seçimi → birkaç belge → metin/parça → indeks → sorgu → konumlu dahili önizleme. Logo ve marka bu akışa bağlanır.

Kapı: uçtan uca güvenli okuma, transaction tutarlılığı, ad/metadata sonucu ve gerçek snippet. Sadece modül testleriyle geçilmez.

### A4 — NAS dayanıklılığı ve iş kuyruğu

Çıktı: artımlı keşif, kısmi kapsam, kopma, retry, değişen dosya, pause/cancel/restart, hariç temizliği.

Kapı: SCN/EXC/SAF kesinti senaryoları; NAS kaynağında hiçbir uygulama yazması.

### A5 — Arama kalitesi ve kopya

Çıktı: strict/folded arama, vocabulary fuzzy, belge düzeyinde adaylar, filtreler, açıklama, geçmiş, tam hash grupları.

Kapı: holdout kalite raporu, no-result dürüstlüğü, yanlış gruplama testi ve hacim ölçümü.

### A6 — OCR kalitesi ve kaynak bütçesi

Çıktı: karma sayfa yaklaşımı, ön işleme, kalite iyileştirme, düşük RAM ve timeout; opsiyonel ağır motor yalnız kapıyı geçerse.

Kapı: CPU-only paket, bellek/süre/kalite raporu; iyi çıktıyı kötüleştirmeme ve eksik motor toleransı.

### A7 — Kullanım, bakım ve güvenlik

Çıktı: tam modern UI, scheduler/autostart/tray, kasa lock, backup/restore/parola/migration, tanı ve help.

Kapı: gerçek Windows tema/DPI denetimi, BAK/MIG/SEC/UI senaryoları; etkinlik saatleri ve izinler açık.

### A8 — Paket, gerçek pilot ve sürüm teslimi

Çıktı: kesin sürüm, bağımlılık/lisans manifesti, temiz makine paketi, yetkili NAS pilotu, yerel Git kayıtları ve teslim raporu.

Kapı: bütün kapsam ölçütleri; açıklanmamış başarısızlık yok. Pilot/test sonuçları ayrı raporlanır. Gerekli format/çekirdek güvenlik başarısızsa tamamlanmış sürüm denmez.

Aşamalar geliştirme sırasıdır; yeni kullanıcı yetkisi olmadan bu dosya onları yürütme emri değildir. Bütün aşamalarda kapsam dışı kullanıcı dosyaları korunur.

## 26. Paketleme, Git ve yayın

Başlangıç dağıtım tercihi PyInstaller onedir + versioned ZIP; Qt/native DLL/OCR bağımlılıklarının temiz Windows'ta doğrulanmasını kolaylaştırır. Onefile seçeneği sonraki ölçümle değerlendirilebilir; her açılışta extraction, antivirüs/startup ve lisans gereksinimleri dikkate alınır. [PyInstaller çalışma modu](https://pyinstaller.org/en/stable/operating-mode.html)

Kullanıcıya teslim edilen paket/çalıştırıcı adı yalnız program ve kesin sürümü içerir: Evrakçı-X.Y.Z.zip, Evrakçı-X.Y.Z.exe, varsa Evrakçı-X.Y.Z.bat. Setup/Installer/Extension eki yok. ASCII teknik kimlik evrakci olabilir; görünen marka Evrakçı'dır. Paket adı program sürümü belirlenmeden oluşturulmaz.

Exe metadata, pencere hakkında ekranı, paket manifesti, launcher ve kaynak sürümü tek version source'tan üretilir. Uygulama version'ı, schema version'ı, normalizer ve extraction/model version'ları farklı kavramdır.

Temiz makine denemesi: Python, Office ve GPU yok; standart kullanıcı hesabı; internet bloklu ama NAS erişimi var. Opsiyonel DOC/ağır OCR önkoşulları ayrıca raporlanır. Paket açıldı diye bütün formatlar doğrulandı sayılmaz.

Git kuralları, kullanıcının kalıcı talimatına göre:

- Tamamlanan her yeni uygulama sürümü için ilgili testler ve sürüm doğrulaması.
- Yalnız kapsam içindeki kaynak ve build/config dosyaları yerel commit'e alınır.
- Teslimden önce yerel commit ve aynı sürümün vX.Y.Z etiketi; ayrıca onay beklenmez.
- Tag mevcutsa doğrulanır; başka commit'i gösteriyorsa sessizce taşınmaz/üzerine yazılmaz.
- GitHub private evrakci hedefi ancak açık dış yayın yetkisiyle oluşturulur/push edilir.
- GitHub Release, upload, external deploy ayrı yetki ister.
- DB, WAL/SHM/journal, history/settings, backups, gerçek belgeler, temp/log, model ağırlıkları, API anahtarları ve hassas screenshot repo'ya alınmaz.
- .gitignore tek güvence değil; staged diff ve sır/hassas dosya kontrolü yapılır.
- İlgisiz kullanıcı değişiklikleri korunur; çalışma ağacı dirty ise teslimde neyin kaldığı açıklanır.
- Planın V4 olması uygulama version bump/commit/tag/push gerekçesi değildir.

Teslim raporu: sürüm, paket yolu/hash, commit kimliği, tag, çalışma ağacı, yapılan test/pilot, bilinen sınır, yapılmayan push/release/deploy. Commit veya tag oluşturulamamışsa “sürüm tamamlandı” denmez.

## 27. V2: şimdiden korunacak mimari sınırlar

V2 kodu V1 tamamlanmadan yazılmaz. V1'de gerçek kaynak konumu ve segment kimliği tutulması gelecekteki özelliklere yeterli hazırlıktır; gereksiz AI katmanı kurulmaz.

Gemini/üretken cevap için gelecek sözleşme:

- Varsayılan kapalı; sağlayıcı/model/kota/fiyat ve veri koşulları uygulama anında güncel resmi kaynakla değerlendirilir. “Ücretsiz Flash her zaman yeterli” varsayılmaz.
- Kullanıcı soru → yerel retrieval → kaynak parça seçim önizlemesi → açık gönderim eylemi.
- Tam DB veya arşiv değil; sınırlı seçili parçalar. Gerekirse hassas alan maskeleme.
- Belge içindeki talimatlar güvenilmeyen veri; modele araç/komut veya belge dışı erişim yetkisi verilmez.
- Kaynak id'leri uygulamanın izinli listesinden; model uydurmuş yol/sayfa üretirse kabul edilmez.
- Yeterli kanıt yoksa cevap üretmeme. Alıntı ve kaynak konumu cevapla bağlı.
- API anahtarı kilitli kasada; log/env/komut satırında değil. Tekrarlı retry aynı veriyi kontrolsüz göndermez.
- Kota/ağ hatasında klasik arama sürer; cloud OCR fallback'i yok.
- Google'a belge parçası gönderme izni, kodun private GitHub'a push yetkisi veya NAS izinleriyle aynı şey değildir.

Ters arama: düşürülen belgenin tam hash'i ve ayrı benzerlik; kopya ile benzer ayrımı; kalıcı kaynak kopyası yok; format/limit/timeout aynı temel sözleşmeler. Ana pencereye drop V1'de bu özelliği varmış gibi göstermez.

## 28. Açık kararlar ve ileride sorulacak bilgiler

Şu anda planı hazırlamayı durduran bilgi yok. Uygulama öncesinde:

| Bilgi | Nasıl elde edilir | Kararı etkiler |
|---|---|---|
| 3–5 PC'nin Windows ve RAM bilgisi | Kullanıcı kısa liste / yetkili yerel tanı | Destek matrisi ve minimum |
| NAS adresi ve klasör örneği | Kaynak seçimi ve örnek yol | Canonical path ve şirket kuralı |
| Format/sayfa dağılımı | Salt-okunur keşif | DOC ve OCR kapsamı |
| DOC zorunluluğu | Gerçek örnek ve kullanıcı kullanım ihtiyacı | Adaptör veya açık kapsam revizyonu |
| Hassasiyet seviyesi / temp türev kabulü | Kısa kullanıcı tercihi | Disk temp vs memory-only motor |
| Şifreyle açılış alışkanlığı | Pilot kullanıcı geri bildirimi | Kasa ile zamanlama dengesi |
| Gerçek arama örnekleri | Kullanıcıdan beklenen belgeli sorgular | Sıralama ve kalite hedefi |
| Aynı NAS'ta eşzamanlı pilot | En az iki yetkili PC | Saat/profil ayarı |

Varsayılanlar kullanıcıya uygun güvenli ve geri döndürülebilir seçeneklerdir. Merkezi sunucu, bulut, şifresiz kasa, kaynak yazma, zorunlu ağır model veya desteklenen format azaltımı kullanıcı onayı olmadan eklenmez.

## 29. Kodlayıcıya son kontrol listesi

1. Kullanıcı geliştirmeyi açıkça başlattı mı? Bu plan hazırlığı yetki değildir.
2. Önce A1 teknik kapıları; şifreli DB ve Windows paket kanıtı olmadan büyük UI geliştirmesi yok.
3. Kaynak dosyaları hiçbir şekilde değiştirme; open_ro gibi istisna modülü yok.
4. Her bilgisayarda ayrı indeks; ortak DB veya kaynakta checkpoint yok.
5. Testli kapsam dışında özellik ekleme, bilinmeyen destek/performans iddiası kurma.
6. Hataları yutma; “ok” durumuna düşürme; başarısız formatı listeden gizleme.
7. Türkçe aramayı gerçek test kümesiyle; tek örnek sorguya özel kod yazma.
8. Tema, DPI, klavye ve bütün boş/hata durumlarını ürünün parçası say.
9. Paket testini kaynak kodu testinden, gerçek NAS pilotunu sentetik testten ayrı raporla.
10. Yeni uygulama sürümünü yerel commit/tag olmadan teslim edilmiş sayma; dış yayın yetkisini ayrı tut.

**Bu belgenin hazırlanması sonunda:** yalnız plan belgeleri mevcut; uygulama kodu, dependency kurulumu, gerçek NAS erişimi, test/paket, Git commit/tag ve dış yayın yapılmış değildir.
