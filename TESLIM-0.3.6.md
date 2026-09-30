# Evrakçı 0.3.6 — arayüz düzeni teslimi

Tarih: 01.10.2026. Kapsam: [DENETIM-0.3.6.md](DENETIM-0.3.6.md).

- İzole son kaynakta tam test paketi: **109 geçti**, 137,30 saniye. Test pencerelerinin temizlik adımı AI listeleme işlerini de bekleyecek şekilde düzeltildi; Qt işçisi çalışırken pencere silinmez.
- Son ZIP içindeki gerçek EXE: **23 kontrol geçti**, ZIP CRC doğrulandı. Yeni sekme sırası, Ara'da iki kart, AI kontrollerinin AI sekmesinde ve yedek listesinin Ayarlar'da olması, kilitleme, kaynak popup ve ilk kurulum dahil.
- EXE FileVersion/ProductVersion **0.3.6**, ProductName **Evrakçı**; BAT aynı sürüm EXE'sini çalıştırır. Dokuz kapsam dosyası izole sürüm kaynağıyla SHA-256 üzerinden eşleşti.
- `Evrakçı-0.3.6.zip`: **168.916.847 bayt**. SHA-256: `04f78559bd8bf6fd8ca7f60e81e8ad18a0a9e865d294824428ae69c37df251d9`.
- Ara, AI ile ara ve Ayarlar ekranlarının açık/koyu 1500/1050 boyutlarında 12 görüntüsü değerlendirildi. Dar pencerede AI kartları tek sütuna geçer; sayfa kaydırılabilir. Yedekler iki ayar kartının altındadır.
- Sentetik 10.000 belge/30 sorguda p95 16,84 ms; 100 boşta sekme geçişinde maksimum 7,65 ms, tarama sırasında 100 geçişte 8,38 ms. Windows 11 10.0.26300, Python 3.13.15. Gerçek arşiv ölçümü değildir.

Ham raporlar: `build/package-check-0.3.6.json`, `build/release036-tests-verified.log`, `build/archive036/acceptance.json`; görüntüler `build/archive036/`.

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın. EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Tam geçiş yedeği **her açılışta alınmaz**: başarılı şema geçişi kaydedilince sonraki açılış bunu atlar. Kesilen geçiş yeniden denenir. Regresyon, başarılı geçişten sonra aynı kasanın ikinci açılışında yedek sayısının artmadığını doğrular. Normal açılışın süresi kasa büyüklüğü ve disk hızına bağlıdır; gerçek 9,39 GB kasada tamamlanan açılış süresi ayrıca ölçülmelidir.

Canlı Gemini, gerçek arşiv pilotu ve gerçek Windows ekran ölçekleri henüz doğrulanmadı. Önceki beş ilgisiz kullanıcı değişikliği korunup paket ve commit dışında bırakıldı. Yerel commit ve `v0.3.6` etiketiyle kayıt oluşturulur; kesin kimlik teslim mesajında verilir. Harici yayın yapılmaz.
