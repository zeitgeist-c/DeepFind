# Evrakçı

Windows için yerel, şifreli belge arama uygulaması. Kaynak belgeler PDF/XLSX/XLS/DOCX olarak okunur; arama indeksi bu bilgisayarda tutulur.

## Güncelleme

Kurulu sürüm yeni bir yayın çıktığını denetler: program açıldıktan sonra günde bir kez sessizce, ayrıca **Ayarlar → Güncellemeler → Güncellemeyi denetle** ile istenildiği zaman. Yeni sürüm bulununca **İndir ve kur** ile paket indirilir; SHA-256 özeti ve sürüm bilgisi doğrulanır, ardından Evrakçı kendini yeniden başlatır. İndirme iptal edilebilir; doğrulamayı geçemeyen paket asla çalıştırılmaz. Eski program klasörü ve kasanız silinmez; güncelleme yalnız yeni sürüm klasörünü açar. Güncelleme yalnız kurulu programda çalışır (kaynak koddan çalıştırmada denetim görünmez). Yayınlar herkese açık `zeitgeist-c/Evrakci-Releases` deposundan gelir; kaynak kod ayrı ve özeldir.

0.3.3, AI Yardımcısı model listesini Gemini 3.6 Flash, Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite ve Gemma 4 26B A4B olarak günceller. Eski 3.8 Flash ve 3.5 Flash seçimleri ilk açılışta karşılıklarına taşınır. 0.3.2'nin PDF ön izleme düzeltmesi ve önceki işlevler korunur.

Bu sürüm denetim/pilot sürümüdür. Plan V4'ün tüm kabul kapıları geçmiş değildir. Doğrulama ve sınırlar: DENETIM-0.3.3.md.

## Çalıştırma

Evrakçı-0.3.3.zip dosyasını bir klasöre açın; içindeki Evrakçı-0.3.3.exe veya aynı adlı BAT dosyasını çalıştırın. ZIP içinden doğrudan çalıştırmayın; `_internal` ve `licenses` klasörlerini EXE yanında koruyun. Tek başına EXE'yi kopyalamak yeterli değildir.

İlk açılışta şifreyi iki kez belirleyin ve kaynak klasörleri seçin. Sonraki açılışta aynı şifre kullanılır. Ayarlar > Parolayı değiştir: mevcut şifre + yeni şifre + yeni şifre tekrarı. Önceki yedekler eski şifreyi gerektirir. Şifre unutulursa kasanın açılacağı vaat edilmez; kaynak belgeler etkilenmez.

Varsayılan kasa: %LOCALAPPDATA%/Evrakci/Data/evrakci.db. Her bilgisayar kendi yerel kasasını kullanır.

Başka bilgisayarda mevcut arşivle devam etmek için uygulama klasörünü ve şifreli kasayı birlikte taşıyın. `%LOCALAPPDATA%/Evrakci/Data` içindeki kasa ile varsa ilgili yedekleri güvenli biçimde kopyalayın; kaynak belgelerin kayıtlı yolları yeni bilgisayarda erişilebilir olmalıdır. OCR dil modelleri `%LOCALAPPDATA%/Evrakci/OCR/tessdata` altında saklanır; bunları da taşıyabilir veya ilk açılışta yeniden kurabilirsiniz. Kasa şifresi gereklidir. İki bilgisayarda aynı kasayı eşzamanlı kullanmayın.

OCR motoru ZIP içinde bulunur. İlk açılışta `tur`, `eng` ve `osd` dil modelleri indirilip SHA-256 ile doğrulanır; bu aşama için internet veya aynı doğrulanmış dosyaları içeren çevrimdışı klasör gerekir. Modeller `%LOCALAPPDATA%/Evrakci/OCR/tessdata` içinde tutulur. Eski DOC biçiminin içerik araması bu sürümde desteklenmiş sayılmaz.

AI Yardımcısı isteğe bağlıdır. Gemini 3.6 Flash, Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite ve Gemma 4 26B A4B arasından model seçebilirsiniz. Gemini API anahtarını bu sayfada şifreli kasaya kaydedin. Soru veya özetlenecek belgeyi seçip **Alıntıları hazırla** ile yerel kanıtı görün; yalnız **Gösterilen alıntıları gönder** düğmesi Google API'sine ağ isteği yapar. Yanıtlar kaynak segment kimlikleriyle doğrulanır ve kaynak belgelere geri dönülebilir. Uzun belgelerde yalnız ekranda belirtilen kesitler özetlenir; AI yanıtı belge yerine geçmez. API anahtarı ve internet yoksa klasik arama ve OCR çalışmaya devam eder.

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
# Evrakçı 0.3.4 ile güncelleme ve içerik arşivi

Yeni dağıtım klasörünü ZIP'ten bütün olarak açın ve `Evrakçı-0.3.4.exe` dosyasını çalıştırın. EXE'nin yanındaki `_internal` ve diğer destek dosyaları aynı pakete ait olmalıdır; yalnız EXE kopyalamayın. Güncellemeden önce programdan çıkın; yeni paketi ayrı klasöre açarak önceki program klasörünü geri dönüş için koruyabilirsiniz.

Kasa varsayılan olarak `%LOCALAPPDATA%\Evrakci\Data\evrakci.db` altında, yedekler `%LOCALAPPDATA%\Evrakci\Backups` altında bulunur. Özel kasa yolu kullanıyorsanız yeni sürümü aynı kasa ile açın. Bu klasörler program güncellemesinde değiştirilmez/silinmez. Kaynak evraklar kendi klasörlerinde kalır; indeks yedeği kaynak evrakların yedeği değildir.

Ara ekranında Arama ve Sonuçlar kartları bulunur. Hemen altındaki “AI ile ara” sekmesinde Gemini anahtarı/modeli, arşive soru sorma, belge özetleme, alıntılar ve AI kaynakları yer alır. Yedekler, Ayarlar sekmesindeki Çalışma düzeni ve Kasa güvenliği kartlarının altındadır. “Taranmış Evraklar” dosya yolu ve içerik durumunu listeler. Evrakı çift tıklayarak veya Ön izle ile popup'ta açın; uzun metinde “Sonraki bölümleri yükle” kullanın. Kaynak erişilemiyorsa kayıtlı indeks metni gösterilir.

Büyük kasa açılışında tam geçiş yedeği yalnız indeks yapısına geçiş gerektiğinde alınır. Başarılı geçiş kaydı sonraki açılışlarda bu yedeğin tekrarını önler. Yarım kalan geçiş sonraki açılışta yeniden denenir; normal açılış süresi de kasa ve disk hızına bağlıdır.

İlk içerik taraması uzun sürebilir; sonraki taramalar değişen kaynakları ve yarım işleri işler. Eski çıkarım sürümünün kayıtları kontrollü yeniden işlemeye alınır; güncellemede indeks silinmez. Kısmi/OCR bekleyen/hatalı kayıtları tam içerik olarak değerlendirmeyin. Ayrı JPG/PNG/TIFF evraklar OCR kapsamındadır; Word/Excel içine gömülü resimler kapsam dışıdır. DOC içeriği için LibreOffice gerekir.

Gemini bağlantı testi küçük bir metin isteği yapar; evrak göndermez. Sorgu önerileri yalnız soruyu gönderir. Evrak alıntıları sadece açık Gönder işlemiyle iletilir. Kararlılık ve doğrulama sınırları: `DENETIM-0.3.4.md`.
