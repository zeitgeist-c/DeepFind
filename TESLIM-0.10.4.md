# Evrakçı 0.10.4 — eksik embedding tablosu ve tarama doğruluğu

21.10.2026. Kullanıcı taramada `OperationalError: no such table: embeddings` bildirdi. Hata eski kasa biçimiyle yeniden üretildi: şema sürümü 7/8/9 olan bir kasada temel şema hazırlığı atlanıyordu. Sürüm işareti, geçmişte isteğe bağlı olan embedding tablosunun gerçekten bulunduğunu garanti etmiyordu. Yeni kasa testleri bu eksikliği yakalamıyordu.

Kasa hazırlığı ve tarama girişinde eksik embedding tablosu ve model indeksi artık eklemeli olarak hazırlanır. Aynı tablo tanımı yeni ve eski kasalarda paylaşılır. Mevcut vektör, segment ve FTS içeriği silinmez; sırf tablo eksik diye metin indeksi baştan kurulmaz. Eksik vektörler sonraki taramanın normal embedding kuyruğunda doldurulur. İşlem tekrar çalıştırılabilir.

Tarama denetiminde iki ek tutarsızlık başarısız testlerle doğrulandı ve düzeltildi: kalıcı başarısız işi olan belge kalan sayısına dahil olsa da genel sonuç tamamlandı olabiliyordu; aynı model sürümünde hatalı boyuttaki vektör de geri doldurmada atlanıyordu. Genel sonuç artık belge tamamlanmasıyla tutarlıdır; yanlış boyutlu vektör tekrar üretilir. Kullanıcının kaynak evrakları değiştirilmez.

İlk beş regresyon kontrolü düzeltme öncesi başarısız, sonrasında geçti. Ek iki tutarlılık testi de önce başarısız oldu, ardından geçti. Şema onarımı, şifreli kasada gerçek dosya okuma ve vektör yazımı, tekrar taramada içerik/vektör koruma, v7/v8/v9 işaretleri, FTS korunması ve mevcut vektörlerin değişmemesi sınandı. Hedefli 39 test geçti. Model üretimi kaynak testlerinde kontrollü kodlayıcı kullanır; gerçek GGUF/Vulkan çalışması paket kabulünün konusudur.

Paket kabulüne mevcut işaretli bir kasadan embedding tablosunun çıkarılması ve normal arayüz taramasının bu kasayı onarıp gerçek vektör yazması eklendi. Son kanıtlar: `build/tests-final-0.10.4.xml`, `build/package-check-0.10.4.json`, `build/installer-acceptance-0.10.4.json`, `build/release-0.10.4.json`.

Kullanıcının kurulu programı salt okunur kontrolde 0.10.2 bulundu. Canlı kasası bu doğrulama için açılmadı veya değiştirilmedi; ekran görüntüsündeki hatanın kaynaktaki karşılığı ve temsili kasa onarımı doğrulandı. Gerçek büyük arşivinin tamamlandığına dair iddiada bulunulmaz. GitHub yayını yerel teslimden ayrıdır.
