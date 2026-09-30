# Evrakçı 0.3.4 — yerel teslim kaydı

Tarih: 01.10.2026. Yedi talebin uygulama ve kabul kaydı: [DENETIM-0.3.4.md](DENETIM-0.3.4.md).

## Doğrulananlar

- İzole sürüm kaynağında tam test paketi: **107 geçti**, 133,86 saniye. Kaynak smoke: 22 kontrol geçti.
- Teslim ZIP'i açılarak içindeki gerçek EXE çalıştırıldı: **22 paket kontrolü geçti**, ZIP CRC doğrulandı. Raporda ilk kurulum/tarama, arama, PDF/Excel popup, kilitleme/açma, kalıcı tarama geçmişi, dört kare kart, sayfalı evrak listesi ve resim OCR kontrolleri bulunur.
- EXE FileVersion/ProductVersion: **0.3.4**; ProductName: **Evrakçı**. BAT aynı sürümün EXE'sini çalıştırır. 23 kapsam dosyasının izole derleme kaynağıyla SHA-256 eşleşmesi doğrulandı.
- Paket: `Evrakçı-0.3.4.zip`, 168.909.544 bayt. SHA-256: `eb92cd8f2c28e091c31735917943681c099a6cb39ac577977bcb07409be02a92`.
- Sentetik 10.000 belge/10.000 bölüm/30 sorguda p95 arama: **11,06 ms**. 100 boşta sekme geçişinin en yüksek süresi **7,19 ms**; tarama sırasında 100 geçişte **10,95 ms**. Makine: Windows 11 10.0.26200, Python 3.13.15. Bunlar gerçek arşiv ölçümü değildir.
- Regresyonlar: 500'den fazla aday arasından doğru içerik, son PDF sayfası/Excel satırı/Word paragrafı, Türkçe toleranslı geç AI alıntısı, kesintiden devam, başarısız yeniden işlemede eski içerik, OCR motor eksikliği, 60'tan fazla popup bölümü ve başarısız şema dönüşümünde geri yükleme.

Ham yerel raporlar: `build/package-check-0.3.4.json`, `build/archive034/acceptance.json`. Açık/koyu ekran görüntüleri: `build/archive034/`.

## Güncelleme

Programı kapatıp ZIP'i yeni bir program klasörüne tamamen çıkarın. `Evrakçı-0.3.4/Evrakçı-0.3.4.exe` veya aynı klasördeki BAT'ı çalıştırın. EXE ile birlikte `_internal` ve diğer destek dosyaları da yenilenmelidir.

Varsayılan kasa `%LOCALAPPDATA%\Evrakci\Data\evrakci.db`, yedekler `%LOCALAPPDATA%\Evrakci\Backups` konumundadır; özel kasa seçimi korunur. Program klasörü değiştirilirken bu veriler silinmez. Güncellemede mevcut indeks korunur; yeni çıkarım sürümü gereken belgeleri kontrollü yeniden işleme kuyruğuna alır. Kaynak evraklar yeniden adlandırılmaz ve taşınmaz.

## Açık kabul kontrolleri

Canlı Gemini çağrısı, gerçek işyeri arşivinde pilot, güncel kapanma senaryosunun yeniden üretilmesi ve gerçek Windows ekran ölçekleri henüz doğrulanmadı. Sentetik ve paket kontrolleri gerçek kapanmanın düzeltildiği anlamına gelmez. Word/Excel içindeki gömülü resim OCR'ı bu sürümün kapsamı dışındadır.

Başlangıçtan kalan `DURUM.md`, `doc_adapter.py`, `ocr.py`, `ocr_setup.py`, `test_durability.py` değişiklikleri korunmuştur; izole sürüm kaynağına ve sürüm commit'ine alınmamıştır. Sürüm kaynakları ve ilgili derleme/test kayıtları yerel commit ve `v0.3.4` etiketiyle kaydedilir; harici yayın yapılmaz. Kesin commit kimliği teslim mesajında bildirilir.
