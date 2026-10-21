# Evrakçı 0.10.3 — belge taramasında sayım ve ilerleme

21.10.2026. Seçili kaynakların tamamında önce dosya listesi oluşturulur. İçerik okuma, OCR ve embedding işlemleri bu sayım bittikten sonra başlar. İşleme sırasında aynı klasör listesi yeniden gezilmez; sayımın kasa içindeki geçici görüntüsü kullanılır. İşlem sonunda bu görüntü temizlenir.

Tarama ayrıntıları toplam, tamamlanan ve kalan belge sayısını ve belge tamamlanma yüzdesini gösterir. İçerik okuma, OCR ve vektör dizini aşamalarının ayrıca kendi ilerleme çubuğu bulunur. Çok parçalı belge işleri bir aşamada tek belge sayılır. Belge ancak gereken içerik/OCR/vektör işlemleri tamamlandığında tamamlanan sayısına katılır; başarısız veya bekleyen işler tamamlanmış gösterilmez. Zaten güncel belgeler de tamamlanan sayısına katılır.

Sayım devam ederken bulunan belge sayısı görünür; toplam henüz bilinmediğinden yüzde gösterilmez. Erişilemeyen klasör varsa envanterin eksik olduğu ve sayacın yalnız bilinen belgelere ait olduğu belirtilir. Hariç tutulan ve desteklenmeyen dosyalar taranacak belge toplamına eklenmez. Kaynakların sonradan değişmesi yeni bir tarama gerektirebilir; toplam sayım anındaki kapsamı temsil eder.

Geçen süre ve ölçülen işlem hızından **o aşamanın yaklaşık kalan süresi** gösterilir. İlk işler bitmeden süre hesaplanıyor denir. OCR ve embedding maliyetleri farklı olduğundan bütün tarama için kesin süre sözü verilmez. Duraklatılan süre hız hesabına eklenmez. Son doğrulama ve sözlük işlemlerinde ölçülemeyen işe yapay yüzde verilmez.

Doğrulama; tüm kaynakların işleme başlamadan sayılması, sayımın yeniden kullanılabilmesi, iptal sırasında kaynakların korunması, erişim hatası, çok parçalı işler, OCR/embedding hatalarının belge tamamlanmasını engellemesi ve duraklatmanın süre hesabından çıkarılmasını kapsar. Arayüzde yüzdeler, kalan sayı ve aşama süresi ayrıca kontrol edilir. Dağıtım kabulü gerçek paketli uygulamada sayım/yüzde ve duraklat/devam et akışlarını da çalıştırır.

İlk tam turda 310 test geçti; eski bir testin erken işleme beklentisi yeni sayım şartıyla çelişti. Beklenti tam sayım yönünde güncellendi; kapsam dışındaki işlerin korunması kontrolleri korundu. Bu testle yeni tarama testlerinin birlikte koşumu 11/11 geçti. Son tam tur ayrıca çalıştırılır.

Son doğrulama sonuçları ve paket/kaynak kimliği `build/release-0.10.3.json`, `build/tests-final-0.10.3.xml`, `build/package-check-0.10.3.json` ve `build/installer-acceptance-0.10.3.json` içinde tutulur. Canlı kasa ve Program Files kurulumu test hedefi değildir. GitHub yayını yerel teslimden ayrıdır.
