# Evrakçı 0.1.1

Windows için yerel, şifreli belge arama uygulaması. Kaynak belgeler PDF/XLSX/XLS/DOCX olarak okunur; arama indeksi bu bilgisayarda tutulur.

Bu sürüm denetim/pilot sürümüdür. Plan V4'ün tüm kabul kapıları geçmiş değildir. Kapsam karşılaştırması ve kalanlar: DENETIM-0.1.1.md.

## Çalıştırma

Evrakçı-0.1.1.zip dosyasını bir klasöre açın; içindeki Evrakçı-0.1.1.exe veya aynı adlı BAT dosyasını çalıştırın. ZIP içinden doğrudan çalıştırmayın; _internal ve licenses klasörlerini EXE yanında koruyun.

İlk açılışta şifreyi iki kez belirleyin ve kaynak klasörleri seçin. Sonraki açılışta aynı şifre kullanılır. Ayarlar > Parolayı değiştir: mevcut şifre + yeni şifre + yeni şifre tekrarı. Önceki yedekler eski şifreyi gerektirir. Şifre unutulursa kasanın açılacağı vaat edilmez; kaynak belgeler etkilenmez.

Varsayılan kasa: %LOCALAPPDATA%/Evrakci/Data/evrakci.db. Her bilgisayar kendi yerel kasasını kullanır.

OCR için Tesseract-OCR ve doğrulanmış tur traineddata ayrıca gereklidir; temel metin araması OCR motoru yokken kullanılabilir. Eski DOC biçiminin içerik araması bu sürümde desteklenmiş sayılmaz.

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
