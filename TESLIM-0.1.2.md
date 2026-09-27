# Evrakçı 0.1.2 teslim kaydı

27.09.2026. İlk kurulum, Türkçe arayüz, logo ve klasör ekleme düzeltmesi.

- ZIP: Evrakçı-0.1.2.zip; 57.864.114 bayt.
- SHA-256: `4b25465addd6774b1afc7787533daf96f0018cc849085b322bdc2059552ed030`.
- Kaynak sürümü, manifest ve EXE/BAT adı 0.1.2.
- Tam test: 67 geçti / 102.34 saniye. Kullanıcının önceden eklediği bir test bu sayıya dahil; ilgili dosya sürüm commit'ine alınmaz.
- ZIP yeni geçici klasöre açıldı; CRC, Türkçe Qt çeviri dosyası ve ad/sürüm doğrulandı. Paketli EXE çıkış kodu 0: kurulumdaki Türkçe düğmeler/logo, seçili klasörü Ekle düğmesiyle ekleme, Yenile sonrası seçim listesinin korunması, spawn çıkarım, şifreli kasa/FTS, arka plan arama, Excel önizleme, koyu tema ve kilit açma geçti.
- Kurulumun altı adımı açık/koyu temada, yalnız sentetik klasörle görsel olarak kontrol edildi: build/review-ui-0.1.2/.
- Yerel kaynak sürümü `v0.1.2` etiketiyle belirlenir; commit kimliği `git rev-parse v0.1.2^{commit}` ile okunur. Önceki dönüş noktası `v0.1.1` / `40bcb6b` korunur.
- Çalışma ağacında yalnız kullanıcının tests/test_durability.py değişikliği kalır. GitHub push/Release/deployment yapılmaz.

ZIP tamamen açıldıktan sonra Evrakçı-0.1.2.exe veya aynı adlı BAT çalıştırılır. 0.1.1'deki genel plan/pilot sınırları devam eder; DENETIM-0.1.2.md ve DENETIM-0.1.1.md dosyalarına bakın.
