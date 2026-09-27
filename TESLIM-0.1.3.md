# Evrakçı 0.1.3 teslim kaydı

27.09.2026. Kurulum, kilit ve altı ana ekran yeniden tasarlandı. Detaylar: DENETIM-0.1.3.md.

- ZIP: Evrakçı-0.1.3.zip; 57.878.873 bayt.
- SHA-256: `4f5572959b78b939d051e60da1baa3fa841de4faa0752ebfb37f085b6cdd9ddb`.
- Kaynak, manifest ve EXE/BAT sürümü: 0.1.3.
- Ana yerleşim değişikliklerinden sonra tam test: 67 geçti / 102.65 saniye. Kullanıcının mevcut, commit kapsamı dışındaki bir testi bu sayıya dahildir.
- Son görsel/boş durum/önizleme düzenlemelerinden sonra 15 ilgili arayüz ve şifre regresyon testi geçti / 21.76 saniye. Ardından bütün ekranların görsel kontrolü ve kaynak smoke geçti.
- Teslim ZIP'i yeni geçici klasöre açıldı; CRC, Türkçe Qt çevirisi, dört SVG varlığı ve sürüm/adlar doğrulandı. İçindeki EXE çıkış kodu 0: SVG çizimi, Türkçe düğmeler/logo, klasör ekleme/yenileme, spawn çıkarım, şifreli kasa/FTS, arka plan arama, Excel önizleme, koyu tema ve kilit açma geçti.
- Görsel kanıtlar: build/review-ui-0.1.3/. Yalnız sentetik belgeler ve geçici kasa kullanıldı; gerçek Windows ekran/DPI pilotu yapılmadı.
- Yerel kaynak kaydı: v0.1.3 etiketi; kimlik `git rev-parse v0.1.3^{commit}` ile okunur. Önceki 0.1.2 dönüş noktası korunur.
- Çalışma ağacında yalnız kullanıcının tests/test_durability.py değişikliği kalır. GitHub push, Release veya deployment yapılmaz.

ZIP'i tamamen açıp Evrakçı-0.1.3.exe veya aynı adlı BAT dosyasını çalıştırın. Genel plan/pilot sınırları DENETIM-0.1.1.md dosyasındaki gibidir.
