# Evrakçı 0.1.3 — Arayüzün yeniden tasarlanması

Tarih: 27.09.2026. Kaynak: kullanıcının 0.1.2 tasarımını beğenmediğini belirtmesi; yeni Qt ekranlarının görsel kontrolü.

Bu sürüm yalnız düğme/metin düzeltmesi değildir. Kurulum, kilit ve altı ana ekranın yerleşimi yeniden düzenlendi.

- Açık tema: açık gri çalışma zemini, beyaz kartlar, sabit lacivert gezinme alanı ve yeşil vurgu. Koyu tema: yumuşak lacivert yüzeyler, açık metin ve daha parlak yeşil vurgu.
- Tutarlı başlık, açıklama, küçük bölüm etiketi ve işlem hiyerarşisi. Düğme, seçim, odak, simge, açılır menü ve onay kutuları aynı tasarım dilinde.
- Kurulum: sol tarafta altı adımlı ilerleme; sağda içeriğe göre düzenlenen form ve kartlar. Klasör tarayıcısı ile eklenen klasörler yan yana. Ekle, yenileme, kaldırma ve hata açıklamaları korunuyor.
- Ana pencere: tam boy sol gezinme, üstte durum/tarama/tema/diğer işlemler; arama alanı yalnız arama ekranında. Sonuçlar simgeli belge kartları; önizleme ayrı panelde ve sayfa/yakınlaştırma araçları tek sırada.
- Kaynaklar, geçmiş ve yedekler: simgeli kart listeleri, sade bilgi satırları ve veri yokken sonraki işlemi açıklayan boş durumlar.
- Tarama: kaynak sayısı ve günlük saat için özet kartları; tarama/duraklatma/iptal araçları. Kaynak sayısı ve saat ayarlar değişince güncellenir.
- Ayarlar: çalışma düzeni ve kasa güvenliği ayrı kartlarda. Kilit/giriş/şifre değiştirme: marka paneli ile sade form yan yana.
- Hareketli efekt, ağır grafik veya yeni bağımlılık eklenmedi. Kartlar görünür satırlar çizilirken oluşturulur; küçük simgeler yerel çizimler ve paketlenen SVG'lerdir. Büyük arşiv performansı ayrıca ölçülmüş sayılmaz.

Görsel kontrol: build/review-ui-0.1.3/ altında kurulumun altı adımı ve ana ekranlar açık/koyu temada gerçek Qt bileşenleriyle kaydedildi. Gerçek müşteri belgesi kullanılmadı. Qt yan panelinin ilk gösteriminde sahiplik sorunu bulundu; sihirbaz yan panelinin kalıcı referansı tutularak düzeltildi ve tüm adımlar tekrar açıldı.

Test ve teslim ZIP sonuçları TESLIM-0.1.3.md dosyasında kayıtlıdır. Genel plan denetimindeki DOC/NAS/iki PC/büyük arşiv/temiz bilgisayar ve gerçek DPI pilotu eksikleri devam eder; DENETIM-0.1.1.md esas genel denetimdir. Bu sürüm, bu kabul kapılarını tamamladığını iddia etmez.
