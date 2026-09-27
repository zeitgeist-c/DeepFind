# Evrakçı 0.1.4 — Düzeltme denetimi

Tarih: 27.09.2026. Kapsam: kullanıcı tarafından bildirilen kurulum, tarama ve görünüm sorunları.

## Değişiklikler

- İlk kurulumdan sonra sihirbazın yaşam döngüsü sonlandırılır; şifreli kasa ayrı iş parçacığında hazırlanır. İlerleme penceresinden ana pencereye otomatik geçilir ve ilk tarama başlar. Hazırlık hatası yeniden denenebilir. Gerçek giriş akışında yeniden üretilen Qt erişim ihlali bu yaşam döngüsü düzenlemesiyle giderildi.
- Keşif sırasında 32 dosyada bir ve her klasör sonunda sınırlı içerik işi işlenir. SQLCipher bağlantısındaki geçici kapsam tablosu içerik/OCR/kopya kuyruğunu seçilen dosyalarla sınırlar. Yarım/erişilemeyen tarama kayıp dosya temizliği yapmaz.
- Günlük görevin ele alındığı tarih kalıcı saklanır. Başlama, iptal veya hata sonrasında aynı gün otomatik tekrar çalışmaz. Kullanıcı elle tekrar başlatabilir; sonraki gün ayarlanan saatten önce geçmiş gün için tarama tetiklenmez. Yeni kurulumda cihaz gecikmesi kapalıdır; mevcut kullanıcının tercihi korunur.
- Duraklatma iş parçacığını güvenli kontrol noktasında bekletir; Devam et kaldığı taramayı sürdürür. İptal tamamlanan indeksleri korur ve çalışmayı sonlandırır.
- Tüm kaynaklar, seçili kaynaklar veya tek seferlik klasör/disk kapsamı; aşama, yol, başlangıç/süre ve sayaçlar; son 200 satır işlem kaydı ve sorunlu işleri elle yeniden deneme eklendi. Arayüz sinyalleri saniyede en fazla beş güncellemeyle sınırlandı; güncel iş ayrıca saniyelik anlık görüntüden okunur.
- Kurulum beş adıma indirildi; tema sürekli erişilebilir düğmeden anında değişir. Tema tercihi giriş ekranı için de saklanır. Koyu tema yüzey/kenarlık/seçimleri belirginleştirildi.
- Eklenen klasörler kompakt simgeli kartlarda; çoklu seçim, Tümünü seç, Seçilenleri kaldır, Tümünü kaldır. Kaynak dosyalar silinmez.
- Üç nokta menüsü kaldırıldı. Kilitle, Hakkında ve Çıkış sol gezinmede; yedek oluşturma Yedekler ekranında. Gezinme daraltılabilir; sürüm marka yanında bulunur.
- İsteğe bağlı Beni hatırla, Windows DPAPI ile kullanıcı hesabına bağlı şifreli kayıt kullanır. Otomatik kilit hatırlama açıkken kapanır. Elle kilitleme ve başarılı şifre değişimi hatırlama kaydını kaldırır. Ayarlardan kaldırılabilir. Kilitte tarama yolları ve ayrıntı kayıtları temizlenir.

## Kabul ve sınırlar

Test sonucu ve paket doğrulama kanıtları TESLIM-0.1.4.md içinde kaydedilir. Kaynak ve paket smoke testleri gerçek uygulama girişinden ilk kurulum → ana pencere → ilk tarama → indeks kaydı zincirini içerir.

Bu sürüm V4 planının bütün kabul kapılarını tamamlamaz. Gerçek NAS/bulut sürücüsü, iki bilgisayar, temiz Windows ve 50.000 gerçek belge pilotları yapılmamıştır. Ağ dosya sisteminin engellenen sistem çağrısı sırasında duraklatma/iptal, çağrı dönene kadar bekleyebilir. DOC içerik adaptörü ve önceki genel denetimde listelenen kapsam eksikleri devam eder. OCR harici motor/model gerektirir. Görsel kontroller sentetik arşiv ve ekran görüntüleriyle yapılır; kullanıcının gerçek monitöründeki kabul ayrıca yapılmalıdır.
