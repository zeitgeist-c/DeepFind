# Evrakçı 0.2.0

Windows için yerel, şifreli belge arama uygulaması. Kaynak belgeler PDF/XLSX/XLS/DOCX olarak okunur; arama indeksi bu bilgisayarda tutulur.

0.2.0, yerel şifreli arşivden kanıt seçerek isteğe bağlı AI soru-cevap ve belge özeti sunar. Alıntılar gönderimden önce gösterilir; hiçbir içerik kendiliğinden buluta aktarılmaz. 0.1.6'daki Türkçe/İngilizce OCR kurulumu sürer: Tesseract motoru paketlidir, doğrulanmış dil modelleri ilk açılışta indirilir veya çevrimdışı klasörden alınır.

Bu sürüm denetim/pilot sürümüdür. Plan V4'ün tüm kabul kapıları geçmiş değildir. AI kabulü ve sınırlar: DENETIM-0.2.0.md.

## Çalıştırma

Evrakçı-0.2.0.zip dosyasını bir klasöre açın; içindeki Evrakçı-0.2.0.exe veya aynı adlı BAT dosyasını çalıştırın. ZIP içinden doğrudan çalıştırmayın; _internal ve licenses klasörlerini EXE yanında koruyun.

İlk açılışta şifreyi iki kez belirleyin ve kaynak klasörleri seçin. Sonraki açılışta aynı şifre kullanılır. Ayarlar > Parolayı değiştir: mevcut şifre + yeni şifre + yeni şifre tekrarı. Önceki yedekler eski şifreyi gerektirir. Şifre unutulursa kasanın açılacağı vaat edilmez; kaynak belgeler etkilenmez.

Varsayılan kasa: %LOCALAPPDATA%/Evrakci/Data/evrakci.db. Her bilgisayar kendi yerel kasasını kullanır.

OCR motoru ZIP içinde bulunur. İlk açılışta `tur`, `eng` ve `osd` dil modelleri indirilip SHA-256 ile doğrulanır; bu aşama için internet veya aynı doğrulanmış dosyaları içeren çevrimdışı klasör gerekir. Modeller `%LOCALAPPDATA%/Evrakci/OCR/tessdata` içinde tutulur. Eski DOC biçiminin içerik araması bu sürümde desteklenmiş sayılmaz.

AI Yardımcısı isteğe bağlıdır. Gemini API anahtarını bu sayfada şifreli kasaya kaydedin. Soru veya özetlenecek belgeyi seçip **Alıntıları hazırla** ile yerel kanıtı görün; yalnız **Gösterilen alıntıları gönder** düğmesi Google Gemini'ye ağ isteği yapar. Yanıtlar kaynak segment kimlikleriyle doğrulanır ve kaynak belgelere geri dönülebilir. Uzun belgelerde yalnız ekranda belirtilen kesitler özetlenir; AI yanıtı belge yerine geçmez. API anahtarı ve internet yoksa klasik arama ve OCR çalışmaya devam eder.

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
