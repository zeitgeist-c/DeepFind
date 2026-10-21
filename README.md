# Evrakçı

Windows için yerel, şifreli belge arama uygulaması. PDF, XLSX/XLS, DOCX, ODT, RTF, TXT/CSV ve JPG/PNG/TIFF kaynaklarını okur. Kaynak evraklar kendi klasörlerinde kalır; indeks SQLCipher ile yerel kasada tutulur.

## Kurulum ve güncelleme

`Evrakçı-0.10.3.exe` tam kurulum paketidir. EmbeddingGemma 2 metin modeli, Vulkan/CPU motorları ve OCR bileşenleri kurulumla gelir. Arama için internet, API anahtarı, Ollama veya Python kurulumu gerekmez. GPU için uygun ekran kartı sürücüsü gerekir.

Ayarlar → Güncellemeler ile yeni sürüm denetlenir; açılıştan sonra günde bir kez de sessiz denetim yapılır. İndirme SHA-256 ile, kurulum EXE'si sürüm kaydıyla doğrulanır. Güncelleme sabit AppId üzerinden aynı kurulumu yükseltir; kısayollar ve kaldırıcı aynı uygulamayı gösterir. UAC onayı istenebilir. Başarısız kurulumda önceki programı yeniden açma yolu vardır; canlı kasa kurulum tarafından değiştirilmez.

Tam kurulum modeli programla birlikte `C:\Program Files\Evrakçı\_internal\embedding` altında yerleştirir (özel kurulum dizini seçildiğinde onun altında). Model pakete gömülüdür; ilk kurulumda ayrıca indirme gerekmez. Aynı model için `.evrakci` güncellemesi modeli yeniden taşımaz. 0.10.0 döneminden kalan doğrulanmış ProgramData modeli varsa kurulum dizinine alınır ve yalnız doğrulama sonrası eski kopya temizlenir. Model eksik/bozuksa güncelleyici tam kurulum paketini seçer; tam paket modeli onarır. `.evrakci` dosyasını elle açmanız gerekmez; güncelleyici yönetir. Model değişirse tam kurulum kullanılmalıdır.

Eski sürümlerle uyum için ZIP de üretilir. ZIP içindeki EXE'nin yanında `_internal` ve `licenses` korunmalıdır; tek başına EXE taşınamaz. ZIP'ten kurulu düzene geçişte güncelleyici tam installer seçer. 0.10.1 ve sonraki istemciler kurulum EXE’si olmadan ZIP ile güncellenmez. 0.9.0 ve daha eski ZIP güncelleyicilerden bu düzene geçiş için tam EXE’yi bir kez çalıştırın. Sonraki güncellemeler uygulamanın içinden aynı kurulum dizinine uygulanır. Eski yayın paketleri korunur. Başarılı kurulum, eski sürüm numarası ile EXE sürüm kaydı eşleşen EXE/BAT çiftlerini kaldırır; bilinmeyen dosyaları korur. Ayrıca yalnız SHA-256 özeti bilinen 0.9 ONNX modelini ve artık kullanılmayan uygulama bağımlılıklarını temizler; tanınmayan dosyalar korunur. Canlı kasa, kaynak evraklar ve yedekler bu temizliğe dahil değildir.

Yayın kaynağı `zeitgeist-c/Evrakci-Releases` deposudur. Yerel derleme veya Git etiketi oluşturmak dış yayın yapıldığı anlamına gelmez.

## Açılış

Güncel kasanın arama indeksi her açılışta yeniden kurulmaz. Eski şema yardımcıları sürüm numarasını düşüremez. Gerçek bir indeks dönüşümü gerekirse önce güvenli yedek alınır; işlenen/toplam bölüm sayısı, aşama yüzdesi ve o aşamanın ölçülen hızından yaklaşık kalan süre gösterilir. Yedekleme sayfa sayısını kullanır. Doğrulama/sütun kaldırma/disk kaydı gibi toplamı ölçülemeyen aşamalar açık durum ve geçen süreyle gösterilir; bunlara yapay yüzde atanmaz. Yeni/değişen dosyaların normal taraması devam eder.

## Anlamsal arama ve GPU

Tek anlamsal model EmbeddingGemma 2 Q8_0'dır (256 boyutlu, L2 normalize). Dosya/kelime araması ve bağımsız anlamsal adaylar birleşir, filtrelenir, sıralanır ve sonra sayfalanır. Örneğin “ev kiralama anlaşması”, içerikte yalnız “kira sözleşmesi” yazan belgeyi bulabilir. Tırnaklı ifade, OR/VEYA ve dışlamalı sorgular tam arama kurallarını korur. Benzerlik sonucu kesin bilgi veya doğrulanmış cevap değildir.

Ayarlar → Yerel anlamsal arama bölümünde kullanılan motor, aygıt, hatalar ve indeks kapsamı görünür. Otomatik seçim önce kurulu CUDA motorunu, ardından Vulkan'ı, sonra CPU'yu dener. Vulkan/CPU ana pakettedir. NVIDIA CUDA bileşeni isteğe bağlı indirilir (yaklaşık 663 MB sıkıştırılmış indirme); sürüm ve SHA-256 sabitlidir. Uygun NVIDIA donanımı/sürücüsü gerekir. Her kartın çalışacağı garanti edilmez; CPU geri dönüşü ve hatalar görünürdür.

Model tek yerel alt süreçte paylaşılır. İletişim yalnız 127.0.0.1 üzerinde geçici erişim anahtarıyla yürür; belge içeriği harici servise gönderilmez. Uzun metinler token sınırına göre örtüşmeli bölünür. Kilit/çıkışta model süreci kapatılır; Windows süreç sahipliği uygulama çökmesinde de alt süreci kapatır.

Yeni modelin vektörleri önceki ONNX vektörleriyle karıştırılmaz. Eski kasadaki eksikler sonraki taramada tamamlanır; bu sırada klasik arama kullanılabilir. Güncelleme indeksi veya kaynak belgeleri silmez.

Gemini yardımcısı, API anahtarı/model ayarları, otomatik özet ve üretilmiş soru-cevap kaldırılmıştır. Embedding modeli yalnız arama temsili üretir.

## OCR ve önizleme

RapidOCR, paket içindeki PP-OCR modelleri ve ONNX Runtime ile taranmış PDF/görsellerden metin çıkarır. Embedding modeli OCR'ın yerine geçmez. Metin katmanı yeterli PDF sayfaları tekrar OCR'a girmez. Word/Excel içine gömülü resimler OCR kapsamında değildir; eski DOC içeriği için LibreOffice gerekir. PDF önizlemesi ve küçük resimler korunur.

## Kasa ve güvenlik

Varsayılan kasa `%LOCALAPPDATA%\Evrakci\Data\evrakci.db`, yedekler `%LOCALAPPDATA%\Evrakci\Backups` altındadır. Kaynak belgeler yedeğe dahil değildir. Eski yedekler alındıkları şifreyi gerektirir. Kurtarma anahtarını ayrı ve güvenli bir yerde saklayın; şifre ve anahtar olmadan kasa açılacağı vaat edilmez. İki bilgisayarda aynı kasayı eşzamanlı kullanmayın.

Önce küçük izinli veya sentetik klasörle deneyin. Gerçek NAS, temiz Windows, çok büyük arşiv ve farklı GPU/DPI ortamları ayrıca kabul gerektirir.

## Geliştirme

Belge taraması önce seçili kaynakların tamamını sayar, sonra içerik işlemlerine geçer. Tarama ayrıntıları toplam/tamamlanan/kalan belgeyi ve yüzdeyi gösterir. İçerik okuma, OCR ve vektör aşamalarında ayrı ilerleme ve aşamaya özgü yaklaşık kalan süre görünür. Sayım bitmeden yüzde üretilmez; erişilemeyen klasörler varsa envanterin eksik olduğu belirtilir.

Düzeltme sürümleri `0.10.1 → 0.10.2 → 0.10.3` şeklinde ilerler.

Sürümün tek kaynağı `src/evrakci/version.py` dosyasıdır. Python bağımlılıkları `pyproject.toml` içindedir. `packaging/fetch_engine.py` resmî model/motor sürümlerini proje `build/embedding` alanına indirir ve özetlerini doğrular. BF16 yalnız geliştirici karşılaştırması içindir; dağıtıma Q8_0 girer.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe eval/embedding_acceptance.py
.\.venv\Scripts\python.exe packaging/build.py
.\.venv\Scripts\python.exe eval/package_check.py
```

Gerçek kasa şifresini CLI argümanlarında kullanmayın. Güncel kabul ve sınırlamalar `TESLIM-0.10.3.md` dosyasında kaydedilir. Üçüncü taraf lisansları dağıtımda korunur.
