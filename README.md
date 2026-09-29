# Evrakçı 0.3.0

Windows için yerel, şifreli belge arama uygulaması. Kaynak belgeler PDF/XLSX/XLS/DOCX olarak okunur; arama indeksi bu bilgisayarda tutulur.

0.3.0, tarama ilerlemesini ve sonuçlarını şifreli kasaya kaydeder; yarıda kesilen taramaların işlenmiş belge indeksi korunur. Dar menü simgeleri hizalanır, pencere boyutu hatırlanır ve açık uygulamanın ikinci kez başlatılması mevcut pencereyi öne getirir. AI Yardımcısı model seçimi sunar; alıntılar gönderimden önce gösterilir ve hiçbir içerik kendiliğinden buluta aktarılmaz.

Bu sürüm denetim/pilot sürümüdür. Plan V4'ün tüm kabul kapıları geçmiş değildir. Doğrulama ve sınırlar: DENETIM-0.3.0.md.

## Çalıştırma

Evrakçı-0.3.0.zip dosyasını bir klasöre açın; içindeki Evrakçı-0.3.0.exe veya aynı adlı BAT dosyasını çalıştırın. ZIP içinden doğrudan çalıştırmayın; `_internal` ve `licenses` klasörlerini EXE yanında koruyun. Tek başına EXE'yi kopyalamak yeterli değildir.

İlk açılışta şifreyi iki kez belirleyin ve kaynak klasörleri seçin. Sonraki açılışta aynı şifre kullanılır. Ayarlar > Parolayı değiştir: mevcut şifre + yeni şifre + yeni şifre tekrarı. Önceki yedekler eski şifreyi gerektirir. Şifre unutulursa kasanın açılacağı vaat edilmez; kaynak belgeler etkilenmez.

Varsayılan kasa: %LOCALAPPDATA%/Evrakci/Data/evrakci.db. Her bilgisayar kendi yerel kasasını kullanır.

Başka bilgisayarda mevcut arşivle devam etmek için uygulama klasörünü ve şifreli kasayı birlikte taşıyın. `%LOCALAPPDATA%/Evrakci/Data` içindeki kasa ile varsa ilgili yedekleri güvenli biçimde kopyalayın; kaynak belgelerin kayıtlı yolları yeni bilgisayarda erişilebilir olmalıdır. OCR dil modelleri `%LOCALAPPDATA%/Evrakci/OCR/tessdata` altında saklanır; bunları da taşıyabilir veya ilk açılışta yeniden kurabilirsiniz. Kasa şifresi gereklidir. İki bilgisayarda aynı kasayı eşzamanlı kullanmayın.

OCR motoru ZIP içinde bulunur. İlk açılışta `tur`, `eng` ve `osd` dil modelleri indirilip SHA-256 ile doğrulanır; bu aşama için internet veya aynı doğrulanmış dosyaları içeren çevrimdışı klasör gerekir. Modeller `%LOCALAPPDATA%/Evrakci/OCR/tessdata` içinde tutulur. Eski DOC biçiminin içerik araması bu sürümde desteklenmiş sayılmaz.

AI Yardımcısı isteğe bağlıdır. Gemini 3.8 Flash, Gemini 3.5 Flash, Gemini 3.1 Flash-Lite ve Gemma 4 26B A4B arasından model seçebilirsiniz. Gemini API anahtarını bu sayfada şifreli kasaya kaydedin. Soru veya özetlenecek belgeyi seçip **Alıntıları hazırla** ile yerel kanıtı görün; yalnız **Gösterilen alıntıları gönder** düğmesi Google API'sine ağ isteği yapar. Yanıtlar kaynak segment kimlikleriyle doğrulanır ve kaynak belgelere geri dönülebilir. Uzun belgelerde yalnız ekranda belirtilen kesitler özetlenir; AI yanıtı belge yerine geçmez. API anahtarı ve internet yoksa klasik arama ve OCR çalışmaya devam eder.

İlk denemeyi küçük izinli veya yapay bir klasörde yapın. Gerçek NAS, temiz Windows, yüksek DPI ve 50.000 dosya testleri ayrıca bekliyor.

## Geliştirme ve doğrulama

Python 3.13 ve pyproject.toml bağımlılıkları kullanılır. Sürümün tek kaynağı src/evrakci/version.py dosyasıdır.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m evrakci
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe eval/run_eval.py
.\.venv\Scripts\python.exe eval/ui_shots.py
.\.venv\Scripts\python.exe packaging/build.py
```

Gerçek kasa şifresini CLI --sifre parametresinde kullanmayın. Arayüz, şifreyi etkileşimli alır. İşlemler gerçek kaynaklara yazmak için tasarlanmamıştır; harici uygulamada belge açma/silme/düzenleme özelliği yoktur.
