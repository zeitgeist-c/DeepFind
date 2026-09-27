# Evrakçı — Araştırma, Teknik Kararlar ve Doğrulama Kaydı

**Araştırma tarihi:** 26–27 Eylül 2026  
**Bağlı plan:** Evrakçı-Plan-V4.md  
**Çalışma türü:** Doküman incelemesi ve tasarım; uygulama geliştirmesi veya çalışan yazılım testi değil.

## 1. Kanıtların nasıl okunacağı

- **Kullanıcı bilgisi:** Bu konuşmada kullanıcının doğrudan verdiği gerçek kullanım bilgisi.
- **Kaynakla doğrulandı:** Resmi doküman/depo/paket dosya listesi bu dar iddiayı destekliyor.
- **Tasarım kararı:** Evrakçı için önerilen yaklaşım; harici kaynağın doğrudan verdiği reçete değil.
- **Teknik kapı:** Ancak hedef Windows ortamında prototip ve testle doğrulanabilir.
- **Bilinmiyor:** Eldeki bilgilerden çıkarılamaz; uydurulmamalı.

Bir Windows wheel'inin listelenmesi onun Evrakçı exe'sinde, FTS5 ile, backup ve bütün DLL'leriyle sorunsuz çalıştığı anlamına gelmez. Lisansların mevcut olması ilgili kullanım koşullarının otomatik karşılandığı anlamına gelmez. Performans tabloları bu projede ölçüm yapılmış gibi okunamaz.

## 2. Kullanıcı açıklamasının teknik sonucu

Kullanıcı yaklaşık 3–5 kişinin farklı masaüstü/dizüstülerde kullanacağını, kendi PC'sinde 16 GB RAM ve yaklaşık 8 GB serbest RAM bulunduğunu, işlemcisinin AMD 5600 olduğunu belirtti. NAS'ta silme yetkisi var; dolayısıyla kaynak hesabı salt okunur değil. Arşiv binlerce dosya içeriyor; kesin hacim bilinmiyor.

Sonuç olarak V3'ün tek PC ve zorunlu ağır ikinci OCR motoru yaklaşımı revize edildi. Temel ürün CPU-only, süreç/bellek limitli ve bağımsız kasalı. Salt okunurluk “hesap zaten izin vermiyor” varsayımıyla değil, uygulamanın kaynak erişim protokolü ve gerçek işlem gözlemiyle doğrulanacak.

Bu bilgiler güncel konuşmadan geliyor; eski projelerin donanım/veritabanı/release kayıtları Evrakçı için kanıt sayılmadı.

## 3. Araştırmayla düzeltilen teknik iddialar

| Konu | Araştırma sonucu | Plan etkisi | Durum |
|---|---|---|---|
| os.startfile | İlişkili uygulama/işlem açar; read-only garantisi yok | Dahili viewer ana eylem | Kaynakla doğrulandı |
| FTS prefix | Önek eşlemesi; Türkçe kök çıkarmıyor | Kontrollü terim genişletme | Kaynakla doğrulandı |
| FTS rowid | İçerik/indeks bağlantısı açık kurulmalı | file_id/segment_id ve tutarlı transaction | Kaynakla doğrulandı + tasarım |
| Türkçe Unicode | Varsayılan tokenizer tek başına bütün TR toleransını tanımlamaz | Ortak normalizer, strict/folded testleri | Tasarım + teknik kapı |
| Fuzzy | Hızlı similarity kütüphanesi arşiv ölçeğini tek başına çözmez | Vocabulary ve aday sınırı | Tasarım |
| PDF renderer | V3'te OCR için sayfa render bağımlılığı eksik | PDFium adayı eklendi | Tasarım + teknik kapı |
| PDFium concurrency | Aynı süreçte eşzamanlı çağrılar güvenli değil | Serialize veya ayrı süreç | Kaynakla doğrulandı |
| DOC | python-docx eski DOC okuyucusu değil | Ayrı support kapısı | Kaynakla doğrulandı |
| Excel formülü | Cached değer son kaydedilmiş değer; yeni hesaplama değil | Değer/formül ve eksiklik ayrımı | Kaynakla doğrulandı |
| XML güvenliği | openpyxl defusedxml önlemini belgeliyor | XML/ZIP/bellek sınırları | Kaynakla doğrulandı + tasarım |
| SQLCipher Windows | sqlcipher3 0.6.2 CPython 3.13/3.12 x64 wheel mevcut | Somut aday; eski binary fallback ezberi kaldırıldı | Dosya listesiyle doğrulandı |
| Python bakım | 3.12 security-only, 3.13 binary bakım hattında | Temel aday 3.13; eski sürüm uyumluluk fallback'i gerekçeli | Kaynakla doğrulandı |
| SQLCipher temp | DB/WAL şifreleme bütün transient dosyaları kapsamaz | Temp-in-memory ve disk türev politikası | Kaynakla doğrulandı |
| Aktif DB backup | Aktif DB'yi sıradan kopyalamak snapshot protokolü değil | Encrypted backup/export ve reopen | Kaynakla doğrulandı + teknik kapı |
| PyQt/PySide | Farklı lisans seçenekleri ve module koşulları | PySide6 önerisi, lisans envanteri | Kaynakla doğrulandı |
| Marker | Kod/model lisansları ve runtime koşulları ayrıdır | Zorunlu motor değil; ayrı eklenti kapısı | Kaynakla doğrulandı |
| Tesseract kalite | Ön işleme/DPI/segmentation etkili, model türleri farklı | Ölçülen kalite geçişi | Kaynakla doğrulandı |
| PyInstaller | Onefile açılışta çıkarma ve süreç davranışı var | Önce onedir temiz makine doğrulaması | Kaynakla doğrulandı |
| Kopya hash | İlk 64 KB metin farklı son sayfaları ayıramaz | Tam bayt hash'iyle kesin kopya | Mantıksal hata düzeltmesi |
| Resume sıra | Dizin sırası ve dosya sürümü değişebilir | Kalıcı revision/job modeli | Tasarım |
| NAS offline | Erişim yokluğu silinme kanıtı değil | Scope completeness / missing ayrımı | Tasarım |

## 4. Mimari karar kayıtları

### ADR-01 — Her kullanıcıya/PC'ye ayrı yerel kasa

**Karar:** İndeks SQLCipher ile yerelde tutulur, NAS'a veya ortak veritabanına taşınmaz.  
**Gerekçe:** 3–5 kullanıcının şirket PC'lerinde sunucu kurmadan çalışması, kaynaklara yazmama ve bağımsız şifre.  
**Bedel:** Aynı arşiv farklı PC'lerde tekrar okunabilir; toplam NAS yükü artar.  
**Azaltma:** Kaynak profili, tarama saati dağılımı, artımlı okuma; çok PC pilotu.  
**Gelecek sınır:** Ortak indeks yeni mimari ve yetki projesidir, V1'e gizlice eklenmez.

### ADR-02 — PySide6/Qt Widgets temel arayüz adayı

**Karar:** Qt Widgets + model/view + token tabanlı tema.  
**Gerekçe:** Windows masaüstü, yerel belge işlemleri, büyük liste ve düşük kaynak hedefi. PyQt yerine resmi Qt Python bağlayıcısı önerildi.  
**Alternatifler:** PyQt6 uygun lisansla mümkündür; Electron/webview ek runtime maliyeti yaratır; WinUI/.NET tüm Python belge hattını farklı entegrasyonla kurmayı gerektirir.  
**Kapı:** Seçilen Qt modülleri, dynamic dağıtım ve lisans yükümlülükleri; temiz paket, DPI, keyboard ve theme kanıtı.  
**Durum:** Gerekçeli öneri; kütüphane kurulmadı.

### ADR-03 — CPU OCR ve isteğe bağlı ağır motor

**Karar:** Temel Tesseract, sayfa başına ölçülen ön işleme/iyileştirme. GPU gerekmez.  
**Gerekçe:** Kullanıcının cihaz çeşitliliği ve bellek sınırı.  
**Bedel:** Zor taramalarda ağır model kadar iyi olmayabilir; tekrar geçiş her belgede yarar sağlamaz.  
**Kapı:** Türkçe temsilci örneklerde kalite, sayfa süresi ve bellek.  
**Ağır motor koşulu:** Çevrimdışı, lisans uygun, bütçe içinde, gerçek kalite artışı kanıtlı. Marker sürümü ve model ailesi ayrıca pinlenir.

### ADR-04 — DB şifresiz fallback yok

**Karar:** SQLCipher kurulumu/paketi başarısızsa düz SQLite ile devam edilmez.  
**Gerekçe:** Yerel indeks hassas belge içeriği barındırıyor.  
**Kapı:** Cipher sürümü, yanlış key, FTS, WAL, memory-temp, backup/restore ve packaged exe.  
**Somut aday:** Araştırma tarihindeki sqlcipher3 0.6.2 Windows x64 CPython 3.13 wheel. 3.12 wheel de mevcut; 3.12 security-only olduğundan yeni Windows runtime temel adayı 3.13'tür. Bu bir bütünleşik test sonucu değildir.

### ADR-05 — Belge düzeyi retrieval, parça düzeyi konum

**Karar:** Başlık/klasör/tüm içerikten aday; segmentlerden konum ve alıntı.  
**Gerekçe:** Sorgu kelimeleri klasör ve farklı sayfalara dağılabilir.  
**Bedel:** Yeniden üretilebilir arama temsilleri ve indeks disk hacmi.  
**Azaltma:** External-content tasarımı, ölçülen DB boyutu, gereksiz metadata tekrarından kaçınma.  
**Kapı:** Cross-page query, raw snippet offset ve rebuild.

### ADR-06 — Harici açma salt okunur garanti olarak sunulmaz

**Karar:** Dahili önizleme varsayılan. Harici açma açık ayrı kullanıcı eylemi.  
**Gerekçe:** Kullanıcının NAS hesabı yazma yetkili; Windows shell açması Office'in geçici/yazma davranışını kontrol etmez.  
**Bedel:** Dahili Office önizlemesi tam sayfa görünümü sunmayabilir.  
**Kapı:** Kaynak işlemleri gözlemi, extension doğrulama, kaynak sürümü ve cache yönetimi.

### ADR-07 — Process isolation ve bütçe

**Karar:** Takılabilen NAS/parse/OCR/render işler sonlandırılabilir süreçlere ayrılır.  
**Gerekçe:** Thread timeout işlemi durdurmayabilir; UI kullanılabilir kalmalı.  
**Bedel:** Windows spawn, IPC ve paket karmaşıklığı.  
**Kapı:** Süreç ağacı kapanışı, timeout, disk/RAM limit, lock sırasında late-result reddi.  
**Sınır:** Job object veya ayrı süreç tam zararlı belge sandbox'ı değildir; patched bağımlılıklar ve sınırlar gerekir.

### ADR-08 — Önce onedir dağıtım

**Karar:** Versioned exe içeren onedir klasörü, versioned ZIP ile teslim adayı.  
**Gerekçe:** Native DLL/OCR dağıtımı, hızlı açılış ve hata tanısı.  
**Bedel:** Tek exe hissi yerine klasörle dağıtım.  
**Kapı:** Temiz makine, taşınmış klasör, standard user, Türkçe yol, start-up kaydı.  
**Gelecek:** Onefile ancak ölçülmüş avantaj ve bütün bağımlılık/lisans davranışı doğrulanırsa.

## 5. Resmi kaynaklar ve dar doğrulama kapsamları

Kaynaklar bağımlılık davranışını doğrular; Evrakçı'nın performans ve güvenlik testlerinin yerine geçmez. Araştırma sırasında web sonuçlarındaki üçüncü taraf tartışmalar teknik karar kanıtı olarak kullanılmadı.

1. [Python os.startfile](https://docs.python.org/3/library/os.html#os.startfile): Windows dosya ilişkisiyle açma davranışı. Salt okunurluk sağlayan API olarak tanımlanmıyor.
2. [SQLite FTS5](https://www.sqlite.org/fts5.html): Prefix, phrase, rowid, alanlar, sıralama ve external-content özellikleri. Türkçe morfoloji iddiası buradan çıkmıyor.
3. [SQLite Backup API](https://www.sqlite.org/backup.html): Aktif DB için tutarlı snapshot mekanizması. SQLCipher şifreleme uyumu ayrıca build üzerinde doğrulanacak.
4. [SQLCipher tasarım](https://www.zetetic.net/sqlcipher/design/): DB sayfa şifreleme, parola türetme, WAL/journal ve geçici dosya sınırları. Kapalı kasa ile tüm Python/Qt RAM'inin korunması aynı şey değil.
5. [SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/): Key/rekey, cipher version/integrity, export ve bağlantı ayarları. Özelliklerin edition/build kapsamı gözlenmeli.
6. [sqlcipher3 PyPI](https://pypi.org/project/sqlcipher3/): 0.6.2 ve CPython 3.13/3.12 Windows x64 wheel dosya listesi, sürüm/ABI/platform bilgisi. Pilot adayı mevcut.
7. [sqlcipher3-binary PyPI](https://pypi.org/project/sqlcipher3-binary/): İncelenen listede win_amd64 dosyası görünmedi. Paket adının kendisi Windows fallback kanıtı değil.
8. [sqlcipher3-wheels PyPI](https://pypi.org/project/sqlcipher3-wheels/): Windows wheel üreten ayrı fork seçeneği. Upstream adayı çalışıyorsa ek fork varsayılan yapılmaz; ABI/lisans/supply-chain kontrolü gerekir.
9. [Python sürüm yaşam döngüsü](https://devguide.python.org/versions/): 3.12 security-only döneminde, 3.13 bugfix/binary bakım döneminde listeleniyor. Security-only dönemde yeni binary yayınlanmaması yeni Windows temel adayı seçiminde dikkate alındı. Belirli bir Python sürümünün OCR/native paketlerle çalışması bu tabloyla kanıtlanmaz.
10. [Qt for Python](https://doc.qt.io/qtforpython-6/): PySide6 resmi Python bağlayıcısı ve lisans seçenekleri.
11. [Qt lisans](https://doc.qt.io/qt-6/licensing.html): Modül ve dağıtım koşulları; tüm modüller aynı şartta değil.
12. [PyQt resmi sayfası](https://www.riverbankcomputing.com/software/pyqt): PyQt GPLv3/ticari lisans seçenekleri. Şirket içi özel kullanımın otomatik ücret gerektirdiği sonucu çıkarılmadı; dağıtım senaryosu önemlidir.
13. [PyQt lisans FAQ](https://www.riverbankcomputing.com/commercial/license-faq): Lisans seçimi uygulama dağıtım koşullarıyla ilişkili. Nihai uygunluk kullanılan sürüm ve dağıtımla değerlendirilir.
14. [Qt model/view](https://doc.qt.io/qt-6/model-view-programming.html): Büyük liste/tabloyu veri modeli ve view üzerinden yönetme. Binlerce ayrı widget zorunlu değil.
15. [Qt high DPI](https://doc.qt.io/qt-6/highdpi.html): Windows ölçek ve monitör DPI davranışı. Gerçek görsel doğrulama yine gerekir.
16. [Qt QStyleHints](https://doc.qt.io/qt-6/qstylehints.html): Sistem renk şeması ve değişim sinyalleri; platforma göre destek farkı olabilir.
17. [W3C kontrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum): Okunabilirlik için 4,5:1 normal metin hedefinin dayanağı; masaüstü ürün sertifikası değildir.
18. [pypdfium2 API](https://pypdfium2.readthedocs.io/en/stable/python_api.html): PDFium aynı süreçte eşzamanlı thread çağrıları için güvenli değil. Render ve extraction adaptörü bunu gözetir.
19. [pypdfium2 giriş/lisans](https://pypdfium2.readthedocs.io/en/stable/readme.html): PDF render/inspection, binary dağıtım ve JS/XFA enabled build seçenekleri; ek lisanslar paketle taşınmalı.
20. [python-docx](https://python-docx.readthedocs.io/en/latest/): DOCX okuma/yazma; eski DOC için doğrudan destek kanıtı yok.
21. [openpyxl okuma API](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html): Read-only ve data_only; formül veya son kayıtlı değer ayrımı.
22. [openpyxl optimized modes](https://openpyxl.readthedocs.io/en/stable/optimized.html): Büyük worksheet için read-only akışı ve kapatma gereği; boyut metadata sorunları düşünülmeli.
23. [openpyxl güvenlik](https://openpyxl.readthedocs.io/en/stable/): XML saldırılarına karşı defusedxml önerisi; ZIP boyutu/süre/bellek sınırlaması ayrıca tasarlanır.
24. [xlrd](https://xlrd.readthedocs.io/en/latest/): Eski XLS odaklı okuyucu; modern XLSX için kullanılmaz.
25. [Tesseract resmi kılavuz](https://tesseract-ocr.github.io/tessdoc/): Motor, model dağılımları, lisans ve kurulum dayanakları.
26. [Tesseract model farkları](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html): Fast/best/legacy türleri. Evrakçı'nın seçimi gerçek Türkçe örneklerde ölçülecek.
27. [Tesseract kalite rehberi](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html): DPI, deskew, görüntü temizliği ve segmentation. Tüm ön işleme adımlarının her sayfada yararlı olduğu iddia edilmiyor.
28. [Marker resmi depo](https://github.com/datalab-to/marker): Kod/model lisans farkı, model ve LLM modları, çalışma/çıktı özellikleri. Güncel ana dalın tüm eski sürümlerle aynı hardware gereksiniminde olduğu varsayılmıyor.
29. [LibreOffice başlatma parametreleri](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html): Headless conversion, output ve profil parametreleri. Tek başına makro güvenliği/source-write engeli kanıtı değil.
30. [LibreOffice güvenlik](https://www.libreoffice.org/security/): Dönüştürücü bağımlılığın güncel güvenlik sürümüyle değerlendirilmesi gerektiğini destekleyen resmi advisories. Otomatik online güncelleme gerektirmiyor.
31. [Windows UNC dönüşümü](https://learn.microsoft.com/en-us/windows/win32/api/winnetwk/nf-winnetwk-wnetgetuniversalnamew): Eşlenmiş ağ sürücüsündeki yol için universal name. Yerel sürücüye UNC uydurma gerekçesi değil.
32. [Windows path formatları](https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats): UNC, yerel yol ve dosya yolu çeşitleri; alias/DFS eşdeğerliğini uygulama doğrulamalı.
33. [Windows access rights](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-rights): Okuma, yazma, delete ve ilgili erişim hakları ayrı. Uygulama yalnız gerekli okuma erişimini istemeli.
34. [Windows job objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects): Süreç grubu ve kaynak denetimi için aday mekanizma; tam sandbox olarak sunulmadı.
35. [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html): Windows spawn ve process yaşam döngüsü; frozen exe entegrasyonu ayrıca test.
36. [PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html): Onedir/onefile davranışı ve onefile runtime extraction; onedir tercihi Evrakçı tasarım kararı.

## 6. V3 eksiklerinin kapanış matrisi

| Eksik / çelişki | V4'te karşılığı |
|---|---|
| Kullanıcı sayısı değişti | Bağımsız PC kasaları ve çok PC NAS pilotu |
| Modern UI/tema yeterince tarifli değil | Tasarım tokenları, tüm ekran durumları, DPI/kontrast/keyboard |
| Salt okunurluk open_ro istisnası | Kaynak okuma sağlayıcısı; istisnasız kaynak write yasağı |
| Harici dosya açma garantisi yanlış | Dahili viewer ve ayrı external action |
| Ağ yok ifadesi NAS ile çelişiyor | NAS erişimi ile internet servisleri ayrıldı |
| Windows SQLCipher fallback belirsiz | Gerçek platform wheel adayı + encrypted smoke kapısı |
| Pinli liste aslında pinsiz | Tam sürüm/transitive/hash/runtime/model lock kapısı |
| PDF OCR render eksik | PDFium render bileşeni |
| DOC support uygulanmamış | Adaptör/format kapısı, kullanıcıya açık kapsam engeli |
| Excel formül/tablo ve Word tablo eksik | Tür bazlı kapsam/konum ve cached value kuralları |
| OCR dosya bazında taranmış sayfa kaçırıyor | Sayfa/karma içerik değerlendirmesi |
| İkinci motor mutlaka kaliteli varsayılmış | Çıktı karşılaştırma ve kötüleşmede geri koruma |
| Marker maliyet/lisans/hardware varsayımı | CPU çekirdek, ayrı ağır motor manifest ve lisans |
| Timeout yalnız işaret | Sonlandırılabilir süreç ve IPC recovery |
| Memory/ZIP/XML/page limit yok | Limitler, düşük RAM davranışı, partial index |
| FTS-file-locs bağlantısı eksik | Revision/segments/search_documents açık ilişkisi |
| Değişen dosyada eski FTS kalabilir | Atomik update; aktif revision ve completeness |
| Eski içerik güncel sonuç sanılabilir | Offline ile bilinen değişiklik ayrı; eski revision explicit-only |
| Checkpoint sıraya bağlı | Kalıcı revision job ve running recovery |
| Ağ kesintisi/silinme karışıyor | Başarılı scope enumeration şartı |
| Boyut/mtime kusursuz sayılmış | Bilinen sınır ve yeniden içerik doğrulama |
| Aynı yıl/şirket çıkarımı belirsiz | Root rule ve kanıt kaynaklı çoklu yıl |
| Türkçe stem iddiası yanlış | Strict/folded + kontrollü alias/prefix |
| Fuzzy bütün metne uygulanıyor | Kelime sözlüğü ve sınırlı aday |
| Güçlü/yakın sonuç karışıyor | Ayrı sonuç sınıfları, no-result dürüstlüğü |
| Tam sorgu tek segmentte aranabilir | Belge retrieval ile parça konumu ayrıldı |
| Kopya ilk 64 KB ve boş metin hatası | Tam bayt hash'i, filtre-aware grouping |
| İlk 50 sınırı erişim kaybı | Daha fazla göster ve dürüst sayım |
| History pinned limit belirsiz | 20 unpinned + sınırlı pinned, temizleme |
| Lock ve autostart çelişiyor | Kilitli startup; unlock catch-up |
| Üç yanlış şifre aşırı güven iddiası | Rate limit ve offline brute-force sınırı |
| Parola/temp/log/OS leakage belirsiz | Kasa threat scope, temp, canary, log redaction |
| Hariçler eski içeriği bırakıyor | Aktif metin/FTS/cache/job temizleme |
| NAS izin iptali/offline cache belirsiz | Gözlenen access denied ve yerel cache sınırı |
| Backup sıradan kopyalama | Şifreli snapshot + reopen + restore |
| Restore/migration/şifre değişimi yok | Staging, rollback ve crash senaryoları |
| Eski backup hariç içeriği geri getirebilir | Mevcut exclusion varsayılan korunur; restore öncesi kapsam farkı |
| Paket ad/sürüm/Git talimatı çelişiyor | Kullanıcının kalıcı commit/tag ve adlandırma kuralları |
| GitHub/push planla yetkilendiriliyor | Dış yayın ayrıca açık yetki |
| Testler tek arama örneğine bağlı | Temsilci corpus, holdout, no-result, p95 |
| Grep/offscreen gerçek kanıt sanılıyor | Native/process write gözlemi ve Windows görsel QA |
| V2 kaynak/AI güvenliği zayıf | Kaynak allowlist, prompt injection sınırı, gönderim önizlemesi |

## 7. Hâlâ test edilmemiş olanlar

Bu çalışma kapsamında paket kurulmadı; SQLCipher DB oluşturulmadı; FTS/OCR test edilmedi; gerçek belge/NAS okunmadı; performans ölçülmedi; UI render veya görsel mockup üretilmedi. Logo tasarlanmadı. Git repo/commit/tag/push/release işlemi yapılmadı.

Ana plandaki bellek, hız, corpus ve timeout değerleri aday hedeflerdir. Uygulama başlatılınca A1/A4/A5/A6/A8 kapıları bunları ölçülebilir kanıta dönüştürür. Ölçüm başarısızsa hedef/hardware/support kararları kullanıcıya açıklanarak revize edilir; sessizce başarılmış gibi raporlanmaz.

## 8. Plan kalite denetimi

Bu revizyonda belge düzeyinde kontrol edilenler:

- V3 kararları ile son kullanıcı açıklaması arasındaki değişiklikler işaretlendi.
- Kaynak okumaları ve runtime/backup yazma alanları birbirinden ayrıldı.
- Aynı PC'de kasa kilidi, iş kuyruğu, zamanlama ve geç gelen sonuçların ilişkisi tanımlandı.
- Belge güncelliği, kısmi erişim, silinme ve hariç tutma aynı durum modeliyle bağlandı.
- Her kritik özellik en az bir kabul senaryosu ve bir geçiş kapısıyla eşleştirildi.
- Kullanıcıya teslim adlandırması ve yerel sürüm kaydı talimatı uygulandı; plan dokümanının app release olmadığı belirtildi.
- Araştırılan teknik gerçekler ile test gerektiren tasarım hedefleri ayrıldı.

Bu kontrol doküman tutarlılık incelemesidir; çalışan ürün için test PASS beyanı değildir.
