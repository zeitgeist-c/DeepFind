# Evrakçı

Windows için yerel, şifreli belge arama uygulaması. Kaynak belgeler PDF/XLSX/XLS/DOCX/ODT/RTF/TXT/CSV ve JPG/PNG/TIFF olarak okunur; arama indeksi bu bilgisayarda, SQLCipher ile şifreli kasada tutulur. Sunucu, bulut, ayrı kurulum gerektirmez: ZIP'ten çıkarıp EXE'yi çalıştırırsınız.

## Güncelleme

Kurulu sürüm yeni bir yayın çıktığını denetler: program açıldıktan sonra günde bir kez sessizce, ayrıca **Ayarlar → Güncellemeler → Güncellemeyi denetle** ile istenildiği zaman. Yeni sürüm bulununca **İndir ve kur** ile paket indirilir; SHA-256 özeti ve sürüm bilgisi doğrulanır, ardından Evrakçı kendini yeniden başlatır. İndirme iptal edilebilir; doğrulamayı geçemeyen paket asla çalıştırılmaz. Eski program klasörü ve kasanız silinmez; güncelleme yalnız yeni sürüm klasörünü açar. Güncelleme yalnız kurulu programda çalışır (kaynak koddan çalıştırmada denetim görünmez). Yayınlar herkese açık `zeitgeist-c/Evrakci-Releases` deposundan gelir; kaynak kod ayrı ve özeldir.

## Çalıştırma

`Evrakçı-SÜRÜM.zip` dosyasını bir klasöre açın; içindeki `Evrakçı-SÜRÜM.exe` veya aynı adlı BAT dosyasını çalıştırın. ZIP içinden doğrudan çalıştırmayın; `_internal` ve `licenses` klasörlerini EXE yanında koruyun. Tek başına EXE'yi kopyalamak yeterli değildir. Güncellemeden önce programdan çıkın.

İlk açılışta şifreyi iki kez belirleyin ve kaynak klasörleri seçin. Sonraki açılışta aynı şifre kullanılır. Ayarlar → Parolayı değiştir: mevcut şifre + yeni şifre + yeni şifre tekrarı. Önceki yedekler eski şifreyi gerektirir. Şifre unutulursa kasanın açılacağı vaat edilmez; kaynak belgeler etkilenmez. Kurtarma anahtarı Ayarlar'da üretilir ve şifre yerine kasayı açabilir; onu ayrı ve güvenli yerde saklayın.

Varsayılan kasa `%LOCALAPPDATA%\Evrakci\Data\evrakci.db`, yedekler `%LOCALAPPDATA%\Evrakci\Backups` altındadır. Her bilgisayar kendi yerel kasasını kullanır.

Başka bilgisayarda mevcut arşivle devam etmek için uygulama klasörünü ve şifreli kasayı birlikte taşıyın; kaynak belgelerin kayıtlı yolları yeni bilgisayarda erişilebilir olmalıdır. Bu klasörler program güncellemesinde değiştirilmez/silinmez. Kaynak evraklar kendi klasörlerinde kalır; indeks yedeği kaynak evrakların yedeği değildir. Kasa şifresi gereklidir. İki bilgisayarda aynı kasayı eşzamanlı kullanmayın.

Büyük kasa açılışında tam geçiş yedeği yalnız indeks yapısı değişecekse alınır; başarılı geçiş tekrarı önler, yarım kalan geçiş sonraki açılışta yeniden denenir. İlk içerik taraması uzun sürer; sonraki taramalar değişenleri ve yarım işleri işler. Eski motor sürümünün düşük kaliteli OCR kayıtları kontrollü yeniden işlenir; güncellemede indeks silinmez. Kısmi/OCR bekleyen kayıtları tam içerik saymayın.

## OCR

Tarama/metin katmanı için RapidOCR (PP-OCR modelleri, ONNX Runtime) kullanılır; motor ve Türkçe modeller paketin içindedir — indirme, tessdata, ayrı kurulum, dil seçimi yoktur. Motor CPU'da, kaynak sınırlı alt süreçte çalışır; bellek düşükse OCR ertelenir, klasik arama sürer. Doğal metni yeterli sayfalar OCR'a girmez. Ayrı JPG/PNG/TIFF evraklar OCR kapsamındadır; Word/Excel içine gömülü resimler kapsam dışıdır. Eski DOC içeriği için LibreOffice gerekir.

## AI Yardımcısı

İsteğe bağlıdır. Gemini API anahtarını şifreli kasaya kaydedin. Soru veya özetlenecek belgeyi seçip **Alıntıları hazırla** ile yerel kanıtı görün; yalnız **Gösterilen alıntıları gönder** düğmesi Google API'sine ağ isteği yapar; bağlantı testi yalnız küçük bir metin ister, evrak göndermez. Yanıtlar kaynak segment kimlikleriyle doğrulanır ve belgelere geri dönülebilir. API anahtarı ve internet yoksa klasik arama ve OCR çalışmaya devam eder.

İlk denemeyi küçük izinli veya yapay bir klasörde yapın. Gerçek NAS, temiz Windows, yüksek DPI ve çok yüksek hacim testleri kurum ortamınızda ayrıca doğrulanmalıdır.

## Geliştirme ve doğrulama

Python 3.13 ve pyproject.toml bağımlılıkları kullanılır. Sürümün tek kaynağı `src/evrakci/version.py` dosyasıdır.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m evrakci
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe eval/run_eval.py
.\.venv\Scripts\python.exe eval/ui_shots.py
.\.venv\Scripts\python.exe packaging/build.py
```

Gerçek kasa şifresini CLI `--sifre` parametresinde kullanmayın. Arayüz, şifreyi etkileşimli alır. İşlemler gerçek kaynaklara yazmak için tasarlanmamıştır; harici uygulamada belge açma/silme/düzenleme özelliği yoktur.

Sürüm geçmişi ve doğrulama kayıtları: `DURUM.md` (güncel) ile güncel sürümün `DENETIM-*/TESLIM-*` dosyaları; eski sürüm kayıtları ağaçta tutulmaz, `git log`/`git show` ile erişilir.
