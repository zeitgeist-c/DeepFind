# Evrakçı 0.1.1 — Plan ve uygulama denetimi

Tarih: 27.09.2026. Referans: Evrakçı-Plan-V4.md. Plan bir karşılaştırma belgesidir; bu çalışmanın yetkisi kullanıcının denetim, tasarım ve şifre akışlarını tamamlama isteğidir.

## Karar

Önceki uygulamaya “her şey tamam, gerçek arşivde kullanın” onayı verilmiyor. Önemli hatalar düzeltildi ve arayüz yenilendi. 0.1.1 yerel denetim/pilot sürümüdür; V4'ün bütün kabul kapılarının kapandığı anlamına gelmez. İlk deneme yapay veya izinli küçük bir klasörde yapılmalıdır. Gerçek NAS'a bu denetimde erişilmedi.

## Bulunan ve düzeltilen hatalar

| Sorun | Sonuç ve düzeltme |
|---|---|
| Bir kökün taraması diğer köklerdeki kayıtları missing yapıyordu | Kayıp dosya temizliği yalnız taranan kökün sınırında çalışır |
| Dosya yeniden geldiğinde aynı boyut/mtime nedeniyle içerik geri gelmiyordu | missing/excluded kayıtlar yeniden kuyruğa alınır |
| rev_id BEGIN cursor'ından okunuyordu | Gerçek INSERT kimliği kullanılır |
| Dosya adı, içerik başarılıysa FTS'e eklenmiyordu | Dosya adı ayrı segment olarak her durumda aranabilir |
| Değiştiği bilinen dosyanın eski içeriği aktif aramada kalabiliyordu | Yeniden işleme bekleyen kayıtlar normal sonuçlardan çıkarılır |
| Extractor sürümü değişince aynı dosya yeniden işlenmiyordu | a4-2 çıkarıcı sürümü revizyon karşılaştırmasına katılır |
| strict FTS varsayılan diakritik silme kullanıyordu | Diakritik koruyan strict tokenizer, geçişte indeks yedeği ve rebuild |
| İçerik/yol yılları kayboluyor, eski yıllar revizyonda kalıyordu | Yıllar güncel revizyonun ad/yol/metninden yeniden üretilir |
| İlk kurulum sihirbazı açılışa bağlanmamıştı | Yeni kasada sihirbaz açılır, çift şifre ve kaynaklar kaydedilir |
| Yanlış kilit şifresi programı kapatıyordu | Aynı kilit ekranında hata ve yeniden deneme |
| Şifre değişiminde yeni şifre tekrar sorulmuyordu | Eski şifre doğrulama + yeni şifre + tekrar; eşleşme kontrolü |
| Parola doğrudan mevcut kasada rekey ediliyordu | Önce yedek, ayrı şifreli staging, doğrulama, atomik dosya geçişi |
| Eski şifreli yedek geri yüklenince uygulama mevcut şifreyle açamıyordu | Yedek şifresi ayrı alınır; staging güncel kasa şifresine geçirilir |
| Hariç kuralları okunamayınca restore devam ediyordu | Fail-closed; mevcut kurallar alınamıyorsa işlem durur |
| Kullanıcının manuel yedekleri otomatik yedek sayılıyordu | UI yedekleri manual=True; otomatik saklama manueli silmez |
| Aynı saniye yedek adları çakışabiliyordu | Yüksek çözünürlüklü benzersiz zaman damgası |
| Kilit, çalışan taramayı 5 sn sonra unutuyordu | İş referansları bitene kadar korunur; iptal, bağlantı kapama, model temizliği |
| Tarama hatasında QThread kapanmıyordu | Hata sinyali de thread quit akışına bağlı |
| UI arama/önizleme sırasında NAS/PDF/Excel'i bekliyordu | Ayrı okuyucu bağlantısı; arama thread'i; anahtarsız, süre sınırlı belge süreçleri |
| Eski sorgunun sonucu yeni sorguyla karışabiliyordu | Güncel istek karşılaştırması, iptal ve sıradaki istek yönetimi |
| Klasör filtresi ilk 50 sonuçtan sonra uygulanıyordu | Görünür sonuç sıralaması/limiti öncesinde filtre |
| Kilitte PDF pikseli/Excel hücreleri saklanıyordu | Pixmap, orijinal görüntü, tablo, indeks metni ve modeller temizlenir |
| Excel önizlemesi bütün sayfayı RAM'e alıyordu | 200 satır × en çok 50 sütun; XLS/XLSX okuma ayrı süreçte |
| PDF zoom yalnız yeniden render edip aynı boyuta sığdırıyordu | Kaydırılabilir tuval ve gerçek büyütme |
| UTF-8 Tesseract çıktısı Windows varsayılan kodlamasıyla çözülüyordu | Açık UTF-8; Türkçe OCR regresyonu |
| Metin kotası karakter sayıyor, kotadan sonraki segmentleri döndürüyordu | UTF-8 bayt bütçesi ve fazla segmentlerin atılması |
| DOCX üst/altbilgileri okunmuyordu | Normal ve ilk sayfa üst/altbilgi paragrafları dahil |
| Hash okuma sonrası dosya değişimi kontrol edilmiyordu | Hash sonrası imza kontrolü; gruplarda aktif revizyon eşleşmesi |
| Zamanlayıcı kontrolü periyodik yapılmıyordu | Dakikalık timer; başarılı taramada slot kaydı, kilitliyken iş yok |
| Windows oturum bildirimi kaydı yoktu | Native Windows platformunda WTS kaydı ve pointer boyutlu argümanlar |
| Tepsi simgesi yoktu, Çıkış tekrar tepsiye küçültüyordu | Marka simgesi, sahipli menü ve gerçek çıkış |
| Geçmişten seçilen sorgunun filtreleri geri gelmiyordu | Sorgu ve filtre ayrı model verisi; birlikte geri yükleme |
| Kaynak kaldırma yalnız kök satırını siliyordu | Başka etkin kök altında kalmayan yerel dosya kayıtları da kaldırılır |
| Tanı komutu olmayan queue tablosunu sayıyordu | jobs tablosunun pending/running sayımı |
| Gelecek şema sürümü eski uygulamayla açılıp numarası düşebiliyordu | Daha yeni şemada açılış durur |
| Paket sürümü/EXE adı elle çoğaltılmıştı | Kaynak sürümünden otomatik EXE/BAT/ZIP adları, dinamik pyproject sürümü |

## Tasarım

Arama, kaynaklar, tarama, geçmiş, yedekler, ayarlar, ilk kurulum ve kilit ekranı ortak tasarım sistemiyle düzenlendi. Segoe UI 15 px, açık/koyu yüzeyler, 24 px başlıklar, tutarlı boşluklar, seçili/hover/odak durumları, belirgin ana eylem ve büyütülebilir PDF tuvali. Belge listesi model/view kullanır; sonuç başına QWidget üretmez. Ayarlar ve bakım ekranlarında önizleme gizlenir. Koyu temadaki ana butonun metin kontrastı düzeltildi.

Kilit şifresi kasanın şifresidir; ikinci bir şifre sistemi veya şifresiz indeks yoktur. Şifre değiştirme kasa açıldıktan sonra Ayarlar'dadır. Şifre unutulması için doğrulanmamış bir bypass eklenmedi. Eski yedekler eski şifreyi gerektirir.

## Planın teker teker karşılaştırılması

| Plan bölümü | Denetim sonucu |
|---|---|
| 1–3 Bağlam/amaç/kararlar | Yerel, bağımsız indeks ve çevrimdışı V1 yönü korunuyor. Gerçek arşiv dağılımı bilinmiyor |
| 4 Başarı ölçütleri | Küçük sentetik kalite var; 50.000 dosya, toplam süreç belleği ve düşük donanım kanıtı yok |
| 5 Mimari | UI, arama okuyucusu, tarama ve belge süreçleri ayrıldı; toplam bellek rezervasyonu/Windows Job Object eksik |
| 6 Bileşenler | Mevcut pinli Python bağımlılıkları kullanılıyor; tam transitive wheel hash kilidi yok |
| 7 Kök/NAS | Kök sınırı, hariç dizin ve reparse atlama düzeltildi. UNC alias, mapped-drive çözümleme, kök başına ayrıntılı şirket seviyesi eksik |
| 8 Formatlar | PDF/XLSX/XLS/DOCX temel okuma var. DOC adaptörü ana extract hattına bağlı değil; DOC içerik desteği tamamlanmış sayılmaz. Excel formül hesaplama yok; tüm OOXML/textbox/header-table konum sözleşmesi tamam değil |
| 9–10 Tarama/dayanıklılık | Kritik kök, yeniden erişim ve eski içerik hataları düzeltildi. Detaylı erişim-reddi politikası ve kapsam bazlı kullanıcı durumları tamam değil |
| 11 OCR | UTF-8 ve iş yaşam döngüsü düzeltildi. Motor/model dış önkoşul; karma sayfada yeterli metin bulunan resimlerin kaçırılmaması kanıtlanmadı |
| 12 DB | FK/FTS/revizyon/yıl/geçiş koruması incelendi. Disk rezervi ve sınırlı DB büyüklüğü politikası eksik |
| 13 Arama | Güvenli parametreler, ayrı strict/folded, arka plan ve filtre düzeltmeleri var. Tam tırnaklı ifade/önek/birleşme-bölünme, 500 aday sınırının hacimde etkisi ve daha fazla sonuç akışı eksik |
| 14 Kopyalar | Tam SHA-256 ve revizyon kontrolü var; alternatif yolları açan tam UI gruplayıcısı eksik |
| 15 Güvenlik | Şifre kurulumu/değişimi/kilit/tek GUI örneği var. Üç yanlış girişte oturumu kapatan bekleme politikası ve bütün CLI işlemlerinde ortak örnek kilidi eksik |
| 16 Yerel veri/temp | Varsayılan kasa LocalAppData'da; kaynak süreçlerine anahtar aktarılmaz. Geçici ACL ve bütün türevlerin temizliği/sızıntı testi tamam değil. CLI --sifre seçeneği geçmiş uyumluluk için hâlâ mevcut; gerçek şifreyi komut satırında kullanmayın |
| 17 Yedek/migration | Şifreli snapshot ve staging geçişi iyileştirildi. Restore ayar farkı önizlemesi, disk rezervi ve günlük otomatik yedek tetiklemesi eksik |
| 18 Zamanlama/tepsi | Timer, slot kaydı, simge, gerçek çıkış, EXE+özel kasa startup kaydı düzeltildi; gerçek uyku/uyandırma pilotu yok |
| 19–20 UI/akış | Bütün mevcut ekranlar ve şifre akışları yeniden düzenlendi. Offscreen görsel kontrol yapıldı; gerçek DPI, ekran okuyucu, küçük ekran ve iki monitör kanıtı yok |
| 21 Kaynak bütçesi/çok PC | Tek tarama işi korunuyor. Toplam RAM sınırı, profil/histerezis ve iki PC NAS testi eksik |
| 22 Hatalar | Kritik başarısızlıklar artık sessiz başarıya çevrilmiyor. Bütün kodların kullanıcı diline ayrıntılı eşlemesi ve yeniden dene listesi eksik |
| 23–24 Test/kabul | Sentetik testler mevcut; gerçek paylaşım yazma çağrısı gözlemi, 200 belge ve 50.000 dosya hacim kapısı tamam değil |
| 25 Aşamalar | Önceki A7/A8 GEÇTİ notları bütün zorunlu pilotların geçtiği anlamına gelmiyor |
| 26 Paket/Git | 0.1.1 sürüm kaynağı, paket otomasyonu ve yerel commit/tag teslim kapısı; dış yayın yetkisi yok |
| 27–29 V2/açıklar/kontrol | Bulut/LLM/ters arama eklenmedi; bilinmeyen NAS ve donanım bilgileri uydurulmadı |

## Doğrulama

Son tam test: **66 geçti, 104.92 saniye**. Son küçük zamanlayıcı koruması: 6 scheduler testi ve kaynak uygulamada kasa/FTS/arka plan arama/Excel önizleme/koyu tema/kilit açma smoke akışı geçti. Sentetik değerlendirme: 74 belge, 83 sorgu; holdout 16 sorguda top1=1.0, top3=1.0, p95=1.3 ms; bulunmaması gereken sorgularda yanlış sonuç yok. Bu küçük veri kümesi, 50.000 dosya veya gerçek OCR kalitesi için genel garanti değildir.

İlk denetimde 60 testten biri UTF-8 OCR hatasıyla başarısızdı. İnceleme sırasında opsiyonel SQLCipher cipher_memory_security ayarı bu build'de native stack overflow yaptı; ayar etkinleştirilmedi. Python/Qt bellek kopyalarının kusursuz silindiği iddia edilmez. Qt yaşam döngüsü testlerinde kapanış sırasında tekrar arama/iş ve nesne silme sorunları görüldü; Enter debounce iptali, UI ana iş parçacığında nesne temizliği ve çalışanları bekleyen kapanıştan sonra 14 ilgili test birlikte, ardından 66 testin tamamı geçti.

Paketli EXE'de spawn belge çıkarımı, şifreli kasa/FTS, arka plan arama, Excel önizleme, koyu tema ve kilit açma geçti. İlk EXE denemesinde PATH'teki başka bir programın ICU DLL'si Windows ICU bağımlılığını gölgeledi; derleme PATH'i sınırlandı, yabancı ICU dağıtımdan çıkarıldı ve temiz derleme tekrar doğrulandı. Derleme her seferinde yeni çalışma dizini kullanır, önceki paketi proje içinde korur.

Paket hash'i ve yerel Git bilgileri `TESLIM-0.1.1.md` dosyasında kayıtlıdır. Temiz bilgisayar ve gerçek Windows ekran/DPI pilotu yapılmadı.

Görsel kanıtlar: `build/review-ui/` (yalnız sentetik belge isimleri). Gerçek şirket belgesi, NAS yolu veya şifre repoya alınmadı. Kullanıcıya ait başlangıçtaki `tests/test_durability.py` değişikliği sürüm commit'ine alınmaz.

## Gerçek kullanımdan önce

DOC dosyalarında içerik araması zorunluysa bu sürüm henüz uygun değildir. Önce küçük izinli klasörde PDF/Excel/Word arama, kilit ve yedek/geri yükleme pilotu; sonra gerçek NAS erişim/kesinti ve iki PC testi yapılmalıdır. Performans ve kaynak güvenliği yalnız bu bilgisayardaki sentetik testlerle bütün ortamlara genellenmez.
