# Evrakçı — EmbeddingGemma 2 incelemesi ve onay kapsamı

Tarih: 21.10.2026. Bu belge inceleme raporudur; uygulama kodu değiştirilmedi, yeni sürüm veya paket üretilmedi. İnceleme sonunda kaynak sürümü 0.9.0, HEAD `9f5165877b078dfd44d24e1085296c6fc307bb3b`. İnceleme sırasında başka bir işlem `.gitignore` için bu commit'i oluşturdu; incelemenin yaptığı bir değişiklik değildir.

## Sonuç

EmbeddingGemma 2, Evrakçı'nın yerel anlamsal arama modeli olabilir. Mevcut ONNX entegrasyonu gerçek modelle çalışıyor; ancak arama yalnız kelime aramasının bulduğu sonuçları yeniden sıralıyor. Bu, modelin temel faydasını sınırlıyor. CUDA/Vulkan desteği de mevcut değil.

Öneri: Tek anlamsal model olarak EmbeddingGemma 2, programla dağıtılan llama.cpp motoru, Vulkan/CPU temel desteği ve NVIDIA için isteğe bağlı CUDA bileşeni. Tam kelime/sayı araması, belge okuyucuları, OCR, şifreli kasa, önizleme ve güncelleme korunmalı. Gemini yardımcısını kaldırmak mümkün; bunun karşılığı otomatik özet ve üretilmiş soru-cevap özelliğinin kalkmasıdır.

## Modelin yapabildikleri ve sınırları

Google'ın model kartına göre model metin, görsel, ses ve videoyu aynı 768 boyutlu uzaya dönüştürüyor. Metin kısmı 270 milyon, metin + görsel 440 milyon, tam model 740 milyon parametre. Kullanılmayan kodlayıcılar yüklenmeyebilir. 256 boyutlu kesme ve sonrasında L2 normalizasyon destekleniyor; bağlam 8.192 token. FP16 kullanımına ilişkin açık kalite/NaN uyarısı var; referans BF16/FP32 olmalı.

Bu bir üretken sohbet modeli değildir. Belgeyi özetleyemez, kaynaklara dayanarak yazılı cevap üretemez veya taranmış belgeden kullanılabilir OCR metni çıkaramaz. Görsel benzerlik araması, okunabilir metin çıkarımının yerine geçmez. Ayrıca PDF/Word/Excel dosyalarını açmak, sayfaları göstermek ve şifreli indeksi yönetmek modelin işi değildir.

Kaynak: [Google model kartı](https://huggingface.co/google/embeddinggemma-2), erişim 21.10.2026.

## Mevcut kodda doğrulanan bulgular

1. **Model çalışıyor, fakat kuruluma gömülü değil.** `embed.py` ONNX Runtime kullanıyor. `model_indir.py` yaklaşık 1,09 GB'lık ONNX dosyasını ayrı indirmek üzere tasarlanmış. İnceleme ortamından erişilebilen gerçek model eski kullanıcı klasöründe bulundu. Yerel tokenizer ile, ağ erişimini kapatarak model yüklendi; çıktı `(2, 256)` ve tüm değerler sonluydu. Oturum sağlayıcıları DirectML ve CPU olarak bildirildi. Bu, bütün işlemlerin GPU'da yürüdüğünün veya bütün ekran kartlarının desteklendiğinin kanıtı değildir.

2. **İlk açılışta model indirme akışı bağlı değil.** Üretim kaynaklarında indiricinin `indir()` veya `gerekli_mi()` işlevlerine çağrı bulunmadı. Açılış yalnız mevcut modeli ısıtmaya çalışıyor. Dolayısıyla teslim notundaki “ilk açılışta indirilir” ifadesi kodla örtüşmüyor. Model dosyası varlık kontrolü de içerik doğrulaması yerine geçmiyor.

3. **Bağımsız anlamsal aday araması yok.** `rank.py::search_hybrid` önce `search_ranked` çağırıyor; sonuç boşsa dönüyor. Vektörler yalnız bu adayların sıralamasına etki ediyor. Sentetik kasada “kedi” belgeleri ve iki vektör varken “evcil hayvan” sorgusunda sonuç sıfır, kodlayıcı çağrısı sıfır oldu. Sayfalama da vektör sıralamasından önce yapılıyor.

4. **CUDA/Vulkan yolu yok.** `embed.py` yalnız DirectML/CPU seçiyor. Ortamda bildirilen ONNX sağlayıcıları da bunlar. DirectML başlatma veya ısıtma hataları sessizce CPU/klasik aramaya dönüşebiliyor. Arayüz gerçek motor, aygıt, yükleme hatası ve vektör kapsamını yeterince açıklamıyor. DirectML için belgelenen bellek kalıbı ayarı kodda açıkça verilmemiş; mevcut gerçek denemede oturum yine açıldı, bu yüzden bunu gözlenmiş bir GPU arızası olarak sınıflandırmıyorum.

5. **Uzun içerik kesilebiliyor.** Gömme öncesi parçalar 4.000 karaktere kadar çıkarken tokenizer 512 token'da kesiyor. Parçanın sonu vektöre girmeyebilir. Modelin daha uzun bağlam desteği, belleği gözeten token temelli parçalama ile kullanılmalı.

6. **Tokenizer dağıtımı eksik.** ONNX dosyası yerel olsa da `AutoTokenizer.from_pretrained` varsayılan olarak Hugging Face model kimliğini kullanıyor. Önbelleksiz bilgisayarda bu ek internet bağımlılığı yaratıyor. Tokenizer da sürüm sabitli yerel varlık olarak dağıtılmalı.

7. **Kurulum ile güncelleme farklı düzenlerde.** Inno Setup EXE'si Program Files altında sabit AppId ile kuruyor. Güncelleyici ZIP indirip yeni klasör açıyor; yazma izni yoksa Updates içindeki kopyayı çalıştırıyor. Bu, kısayolların/kaldırıcının önceki kurulumu göstermesine ve kopyaların birikmesine yol açabilir. Gerçek kurulu sürüm yükseltmesi ayrıca doğrulanmalı.

8. **Paket testleri model kalitesini kanıtlamıyor.** Mevcut paket kontrolündeki `vektor_model` yalnız dosya varlığına bakıyor. Gerçek model testi varsayılan koşuda etkin değil; mevcut hibrit testler yapay vektörlerle yeniden sıralamayı sınamakta. Eski performans notları yeni kabul kanıtı sayılmadı.

## Boyut ve sadeleştirme

Diskten ölçülen mevcut değerler, sıkıştırma öncesi/sonrası ayrımıyla:

| Öğe | Yaklaşık boyut |
|---|---:|
| Kurulum EXE'si | 163,4 MB |
| Dağıtım ZIP'i | 216,4 MB |
| Açılmış 0.9.0 program klasörü | 476,8 MB |
| Ayrı ONNX model dosyası | 1.085,6 MB |
| Program klasörü + tek ONNX modeli | 1.562,4 MB |

Son satır kasa, yedek, indirme önbelleği ve eski sürümleri içermez. En büyük paket bileşenleri arasında OpenCV ana kitaplığı 74,7 MB, FFmpeg DLL'si 28 MB, ONNX Runtime/DirectML kitaplıkları ve OCR modelleri var. Bunların hepsi gereksiz değildir; OCR bağımlılıklarını körlemesine silmek belge kapsamını bozar.

llama.cpp ekibinin GGUF deposunda metin modeli Q8_0 yaklaşık 310 MB, BF16 yaklaşık 558 MB. Görsel/ses tarafı ek dosya gerektiriyor. Q8_0 modeli mevcut ONNX dosyasından yaklaşık %71 küçük; arama kalitesi ve GPU hesap hassasiyeti gerçek karşılaştırmayla kabul edilmeli. Bu oran toplam program veya RAM tasarrufu değildir.

Kaynak: [GGUF dosya envanteri](https://huggingface.co/ggml-org/embeddinggemma-2-GGUF/tree/main), erişim 21.10.2026.

### Kaldırılması önerilenler

- Yeni motor kabul testlerini geçtikten sonra eski ONNX embedding yolu ve model kopyası.
- Uygulama dağıtımındaki Transformers/Hugging Face/tokenizer zinciri; tokenizer GGUF motoruyla yönetilecek. Geliştirici referans ortamı ayrı tutulabilir.
- Kullanıcı onayıyla Gemini model seçimi, API anahtarı ayarları ve üretken AI yardımcısı. Özet ve üretilmiş cevap yeteneği birlikte kalkar; disk kazancının büyük olacağı varsayılmamalı.
- Kullanılmadığı bağımlılık ve paket testleriyle doğrulanan codec/veri dosyaları, yinelenen varlıklar ve güvenle temizlenebilen eski güncelleme artıkları.
- Ses/video kullanılmadığı sürece bunlara ait model kodlayıcıları. Metin + OCR ile başlamayı öneriyorum; görsel arama ayrıca kapsamlandırılabilir.

### Korunması gerekenler

- PDF/Office okuyucuları, PDF önizlemesi ve küçük resimler.
- Taranmış evrakların metni için RapidOCR; dolayısıyla onun kullandığı ONNX Runtime ve gereken OpenCV işlevleri. Embedding motorunu değiştirmek OCR çalışma zamanını kendiliğinden gereksiz yapmaz.
- FTS tam metin araması: fatura numarası, tutar, tarih ve tam ifade eşleşmesi için küçük ve gerekli bir tamamlayıcıdır.
- SQLCipher şifrelemesi, kaynak izleme, filtreler, etiketler, yedekleme, kurtarma, otomatik tarama ve güncelleme.

Modeli tek kurulum EXE'sine dahil etmek ilk kurulumdan sonra çevrimdışı kullanımı kolaylaştırır. Buna karşılık şu an modeli içermeyen 163 MB'lık kurulumdan daha büyük bir EXE çıkabilir. Hedef ölçüt yalnız EXE değil toplam kurulu alan, açılış süresi ve çalışma belleği olmalı. CUDA dosyalarını her bilgisayara eklemek yerine gerektiğinde doğrulanmış bileşen olarak kurmak boyutu sınırlar.

## Önerilen uygulama sırası

1. **Model/motor kabul kapısı:** Aynı Türkçe sentetik belge kümesinde mevcut ONNX ile GGUF referansını karşılaştır. Q8_0 kaliteyi koruyorsa seç; BF16/FP32 referansla sonlu değer ve sıralama kontrolü yap. Sabit model/motor sürümü, SHA-256 ve lisans envanteri kullan.
2. **GPU ve süreç yönetimi:** Programın yönettiği tek embedding işçisi oluştur; modelin arama ve indeksleme için ayrı ayrı belleğe yüklenmesini önle. NVIDIA'da CUDA, AMD'de Vulkan; desteklenen sistemlerde Vulkan ve CPU geri dönüşü. Gerçek kullanılan aygıt ve hata nedeni görünür olsun. Kullanıcının ayrıca Ollama/Python/CUDA Toolkit kurması hedeflenmesin; gerekli dağıtılabilir kitaplıklar ve sürücü şartları paket bazında doğrulansın.
3. **Arama ve indeks geçişi:** Kelime ve vektör adaylarını bağımsız getir, filtreleri iki yola da uygula, sonuçları birleştirdikten sonra sırala ve sayfala. Uzun metni token sayısına göre örtüşmeli böl. Yeni model sürümü için vektörleri kontrollü yeniden üret; kaynak evraklara dokunma, mevcut kasayı yedekle ve geçiş yarıda kalırsa devam ettir.
4. **Sadeleştirme:** Gemini kaldırma kararını uygula; ardından gerçekten kullanılmayan bağımlılıkları ve varlıkları ölçerek çıkar. OCR veya diğer korunacak özelliklerde kayıp olmadığını doğrula.
5. **Kurulum/güncelleme:** Modeli/tokenizer'ı kurulumla dağıt. AppId ve veri konumunu koruyan installer yükseltmesi kur; eski ZIP sürümlerinden geçişi de ele al. Değişmeyen modeli her program güncellemesinde tekrar indirme. Yarım indirme, bozuk özet, yetki, kısayol, kaldırma ve başarısız yükseltmeden geri dönüşü doğrula.
6. **Teslim kapısı:** Temiz Windows'ta kurulum → ilk açılış → tarama → anlamsal/tam arama → kapanış → yükseltme testi; NVIDIA CUDA, AMD Vulkan ve CPU gerçek çalışma kanıtları. Yalnız sağlayıcı adı veya sentetik test tüm GPU'ların sorunsuz çalıştığı iddiasına yetmez. Yeni sürüm doğrulanınca ad `Evrakçı-X.Y.Z.exe`, yerel kapsamlı commit ve `vX.Y.Z` etiketi; harici yayın ayrı yetkilendirilir.

llama.cpp modelin GGUF sürümünü ve CUDA/Vulkan derleme yollarını sunuyor. Bu, Evrakçı için uygun bir uygulama adayıdır; bu incelemede yeni motor indirilip çalıştırılmadı ve AMD/NVIDIA donanım matrisi denenmedi. İlk kapı başarısız olursa mevcut çalışan yolu kaldırmadan bulgular yeniden sunulmalı.

Kaynak: [llama.cpp derleme belgeleri](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [DirectML oturum şartları](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html), erişim 21.10.2026.

## Bu incelemenin doğrulaması

- Embedding, hibrit arama, gömme kuyruğu, indirici ve güncelleyici testleri: **48 geçti, 1 atlandı**. İlk koşunun Windows sandbox geçici klasör izin sorunu, test geçici alanını proje altına alarak çözüldü; ürün hatası diye sayılmadı.
- Gerçek mevcut ONNX + yerel tokenizer, çevrimdışı: oturum yaklaşık 15,4 saniyede açıldı; iki belge ve bir sorgu yaklaşık 0,91 saniyede kodlandı. Bunlar küçük tek denemedir; kapsamlı hız testi değildir. “Ev kiralama anlaşması” sorgusu kira belgesine elektrik faturasından daha yüksek benzerlik verdi. Testte kurulu uygulama, canlı kasa ve kaynak evraklar kullanılmadı.
- Gerçek CUDA, Vulkan, temiz bilgisayarda kurulum/yükseltme ve büyük arşiv kabulü yapılmadı. GPU envanteri sorgusu ortam izni nedeniyle çalışmadı; ekran kartı modeli varsayılmadı.

## İstenen onay

Önerilen kapsam: EmbeddingGemma 2'yi tek anlamsal model yaparak yerel arama odaklı sade sürüm; GGUF/llama.cpp geçişini kabul kapısıyla gerçekleştirme; Gemini yardımcısı ve onun özet/üretilmiş cevap özelliklerini kaldırma; OCR/tam arama/şifreli kasa/önizleme/kurulum/güncellemeyi koruma. Uygulama ve kaldırmalar kullanıcı bu kapsamı onayladıktan sonra başlayacak.
