# Evrakçı 0.10.2 — açılışta indeksin korunması ve gerçek ilerleme

21.10.2026. Kullanıcı her açılışta dakikalar süren “İndeks yapısı güncelleniyor” ekranını ve yüzdesiz ilerlemeyi bildirdi.

Kök neden kaynakta ve başarısız regresyon testiyle yeniden üretildi: `ensure_current` her defasında `ensure_v8` çağırıyordu; bu yardımcı güncel `9` işaretini `8` yapıyor, `ensure_v9` de FTS'yi baştan kuruyordu. Eski yardımcıların diğer sürüm yazımları da geriye gidebiliyordu.

- Tüm şema sürümü yazımları yalnız yükselir. Güncel v8/v9 kontrolü hızlıdır. Tamamlanmış katlanmış indeks, v9 tablo şekli ve doğru trigger'lar varsa eski sürüm işareti yalnız metadata üzerinden onarılır; FTS korunur.
- Gerçekten gerekli FTS dönüşümü 256 bölümlük partilerle aynı savepoint içinde yapılır. Hata halinde önceki indeks geri gelir. Seyrek veya negatif bölüm kimlikleri sıra sayacı olarak kullanılmaz; gerçek işlenen/toplam satır sayılır. Eski kolon/tablo şekli değişecekse önceden güvenli yedek alınır.
- Açılış göstergesi her aşamayı adlandırır. Barın yüksekliği yüzde metnini görünür kılacak şekilde açılış ekranında artırılmıştır. Bölüm/sayfa sayısı mevcutsa aşama yüzdesi ve aşamanın kendi süresinden yaklaşık kalan süre gösterilir. Önceki yedekleme süresi sonraki indeks aşamasının tahminini şişirmez. Disk doğrulama/kolon kaldırma/kayıt aşamalarında toplam ölçülemediği açıkça gösterilir; yapay genel yüzde verilmez. Normal açılış metni “Kasa sürümü kontrol ediliyor” olur.
- Açılıştaki yeni/değişmiş kaynakların normal taraması korunur. Kaynak evraklar değiştirilmez; indeks, embedding ve kasa verisi silinmez.

Tam regresyon: **302 geçti, 1 atlandı** (`build/tests-final-0.10.2.xml`). Açılış/yüzde/şifreli kasa hedefli testleri 9/9 geçti. İlk turdaki kurtarma testi ilerleme callback imzasına uyarlandı; gerçek sentetik hata ve geri yükleme doğrulaması korunarak sonraki tam tur geçti.

Regresyon kapsamı: üç tekrar açılışta FTS yeniden kurulmaması; eski yardımcılarla sürüm düşmemesi; yalnız düşük işaretli tamamlanmış indeksin korunması; seyrek kimliklerle gerçek bölüm yüzdesi; dönüşüm yarıda hata verince eski aramanın korunması; şifreli SQLCipher kasasında bir dönüşüm ve ardından üç açılışta tek yedek/tek yeniden kurma; aşamaya özgü ETA ve ölçülemeyen aşamada doğru gösterim.

Son test, paket ve kaynak kimliği `build/release-0.10.2.json`, `build/tests-windows-0.10.2.xml`, `build/package-check-0.10.2.json` ile kaydedilir. Kullanıcının canlı kasası test hedefi değildir; gerçek büyük kasanın açılış süresi sentetik test süresiyle garanti edilmez. 0.10.1 kurulum/model yerleşimi ve eski dosya temizliği bu sürümde korunur. GitHub yayını yerel teslimden ayrıdır.
