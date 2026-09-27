# Evrakçı 0.1.1 teslim kaydı

27.09.2026. Yerel denetim/pilot sürümü. Plan V4'ün tüm kabul kapıları tamamlanmış değildir; ayrıntılar DENETIM-0.1.1.md dosyasındadır.

- Paket: `Evrakçı-0.1.1.zip`, 57.858.106 bayt.
- SHA-256: `b7293e7b82f0eac1fb86ab86cb481acecda2cea0e54ddb6c87d2c7f176f1c6d4`.
- EXE/BAT: `Evrakçı-0.1.1.exe` / `Evrakçı-0.1.1.bat`.
- EXE FileVersion ve kaynak sürümü: `0.1.1`.
- Son tam test: 66 geçti / 104.92 saniye. Bu sayı kullanıcının önceden eklediği, commit kapsamı dışındaki bir dayanıklılık testini de içerir.
- Ardından küçük scheduler koruması için 6 ilgili test ve kaynak smoke geçti.
- Teslim ZIP'i yeni geçici klasöre açıldı; CRC, sürüm manifesti ve EXE/BAT adları kontrol edildi. İçindeki EXE spawn belge çıkarımı, şifreli kasa/FTS, arka plan arama, Excel önizleme, koyu tema, kilit ve kilit açma testlerini tamamladı (çıkış kodu 0). Yalnız sentetik belge ve geçici kasa kullanıldı.
- Arama değerlendirmesi: 74 belge / 83 sorgu; 16 holdout sorgusunda top1/top3=1.0, p95=1.3 ms. Büyük arşiv performansı için kanıt değildir.
- Başlangıç Git dönüş noktası: `a21fc57`. Bu sürümün kaynak kaydı yerel `v0.1.1` etiketiyle tanımlanır; commit kimliği `git rev-parse v0.1.1^{commit}` ile okunur.
- Kullanıcıya ait `tests/test_durability.py` değişikliği korunur ve sürüm commit'ine alınmaz. Dolayısıyla teslim sonrası çalışma ağacı bu dosya nedeniyle kirli kalır.
- GitHub push, GitHub Release ve harici deployment yapılmadı.

Temiz bilgisayar, gerçek NAS/iki PC, 50.000 dosya, ekran/DPI ve ekran okuyucu pilotları yapılmadı. DOC içerik araması tamamlanmış sayılmaz; OCR için harici motor/model gerekir.

ZIP'i tamamen açın ve içindeki EXE/BAT'ı çalıştırın. İlk açılışta şifreyi iki kez belirleyin. Sonradan Ayarlar bölümünde mevcut şifreyi doğrulayarak yeni şifreyi iki kez girin. İlk denemede küçük yapay veya izinli bir kaynak klasörü seçin.
