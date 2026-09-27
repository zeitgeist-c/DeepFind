# Evrakçı 0.1.2 — Kurulum ve klasör seçimi düzeltmesi

Tarih: 27.09.2026. Kaynak: kullanıcının ilk kurulum ekran görüntüleri ve kod denetimi.

0.1.1'de kurulum düğmeleri İngilizce kaldı, logo yalnız ana pencerenin simgesinde kullanıldı ve şifre açıklaması teknik dil içeriyordu. Ekle düğmesi ağaç seçimini okumuyor, yalnız yazılan yolu okuyordu; erişilemeyen yol sessizce yok sayılıyordu.

- Kurulumun her adımına logo ve marka eklendi; giriş/kilit ve ana pencere içinde de logo gösterilir.
- Geri/İleri/Vazgeç/Kurulumu tamamla düğmeleri Türkçe. Qt'nin Türkçe çevirisi ve Türkçe yerel ayar yüklenir. İngilizce Name sütun başlığı kaldırıldı; klasör ağacı yalnız klasör gösterir.
- Şifre açıklaması: “En az 12 karakter kullanın ve aynı şifreyi iki kez girin.” Kullanım, Ayarlar'dan değiştirme ve unutulursa ne olacağı sade Türkçeyle açıklanır. Şifreyi göster seçeneği vardır.
- Ekle, yazılan yol varsa onu; yoksa ağaçtaki seçili klasörü ekler. Çift tıklama ve Enter desteklenir. Dosya, bulunamayan yol ve yinelenen klasör için açıklama görünür.
- Klasör seç, Yenile, Seçileni kaldır ve klasör sayısı eklendi. Yenile gerçekten dosya sistemi modelini yeniden oluşturur; eklenen klasörler korunur. Kaldır asıl klasörü silmez.
- Tema adları Sistem teması/Açık/Koyu olarak gösterilir; saklanan ayar anahtarları değişmedi. Zamanlama mesajından teknik hata kodu çıkarıldı.

Yeni davranışlar gerçek düğme tıklamasıyla sentetik klasörde test edilir. Kurulumun altı adımı açık ve koyu temada görsel olarak kontrol edilir. Test ve teslim ZIP doğrulamasının sonucu TESLIM-0.1.2.md dosyasında belirtilir.

Bu sürüm 0.1.1'de belgelenen plan eksiklerini kapatmış sayılmaz. Genel V4 denetimi DENETIM-0.1.1.md dosyasındadır; gerçek NAS, temiz bilgisayar, büyük arşiv ve ekran/DPI pilotları hâlâ yapılmadı.
