# Evrakçı 0.1.5 — 13 maddelik uygulama ve doğrulama kaydı

Tarih: 28.09.2026. Kaynak başlangıcı: f3d805d / v0.1.4.

## İzleme tablosu

| No | Değişiklik | Uygulama | Kanıt / kabul |
|---|---|---|---|
| 1 | Hakkında kaldırıldı | Tamam | Arayüz testi; buton ve pencere kodu yok |
| 2 | Kilitle / Çıkış yan yana | Tamam | Düğme geometrisi testi; açık/koyu görseller |
| 3 | Yerel ve şifreli alt yazısı kaldırıldı | Tamam | Kaynak ve görsel kontrol |
| 4 | Dar menü yatay çubuğu kaldırıldı | Tamam | Gezinme taşması ve scrollbar testi |
| 5 | Menü daraltma sol alta taşındı | Tamam | Düğme konum testi ve görseller |
| 6 | Kaynak listesi ve ayrıntı paneli | Tamam | 1280/1920 yatay; 1100 dikey kontrol; kaynak seçimi testi |
| 7 | Kompakt HH:mm saat | Tamam | 00:00 / 23:59 kayıt testleri; paket kontrolü |
| 8 | Canlı tarama metinleri | Tamam | Çalışma/duraklama/iptal/bitiş durum testleri |
| 9 | Başlık ve sürüm büyütüldü | Tamam | 24px / 13px; sürüm tek kaynaktan |
| 10 | Ana başlık alt yazısı kaldırıldı | Tamam | Kurulum/giriş ortak başlığı değişmedi |
| 11 | Logo/metin dikey ortalandı | Tamam | Açık/koyu görsel kontrol |
| 12 | Tepsi animasyonu | Uygulandı; görsel kabul bekliyor | Windows platformunda tepsi var, farklı simge kareleri gözlendi, idle durumunda timer durdu; Windows gizli simge alanındaki görüntü yakalanamadı |
| 13 | Modeless tarama pop-up | Tamam | Gerçek paket EXE’sinde kapat/aç ve aynı işçi; otomatik tarama pencere/sayfa değiştirmez |

## Mimari ve davranış

- Ana pencere, menü, üst düğme ve tepsi ortak tarama durumundan beslenir. İşçi güvenli duraklama noktasında duraklama sinyali verir.
- Tek modeless QDialog kullanılır. Kapatma/Escape ve Arka planda sürdür gizler; tarama sürer. Tekrar açma ikinci işçi oluşturmaz.
- Kapsam ana Tarama sayfasında; ayrıntılar, yedi sayaç, güncel yol, süre, sınırlı kayıt ve işlem kontrolleri pop-up’tadır.
- İşlem/OCR hata sayaçları ayrı gösterilir; tekil dosya hata toplamı gibi sunulmaz. Keşif toplamı belirsiz olduğundan genel yüzde/tahmini süre uydurulmaz.
- Tepsi için sekiz kare önceden çizilir; 150 ms timer çalışır. Duraklamada sabit işaret, bitiş/iptal/hata/kilitte normal simge kullanılır.
- Kasa kilidinde pop-up gizlenir; kapsam, yol, sayaç ve kayıtlar temizlenir. Çıkışta timer ve pencere temizlenir.
- Saat QTimeEdit üzerinden eski saat/dakika ayar anahtarlarına yazılır. Şema/kasa geçişi yoktur.
- Kaynak ayrıntısı yol ve etkinliği gösterir; etkinlik erişilebilirlik/başarılı tarama iddiası değildir. Kaynak kaldırma dosyaları silmez.

## Kanıtlar ve sınırlar

- Başlangıç: 74 test geçti. Ara arayüz kabulü: 14 test geçti; ara tam paket: 77 test geçti.
- Son tam test ve paket sonuçları TESLIM-0.1.5.md içinde kaydedilir.
- build/review-015 altında 1280x720 / 1920x1080, açık/koyu, geniş/dar menü ve pop-up görselleri; 1 / 1.25 / 1.5 ölçek raporları vardır.
- %125 ve %150 testleri Qt ölçek benzetimidir; gerçek Windows DPI oturumu değildir. Native oturum 96 DPI (%100) idi.
- build/native-015.json gerçek Windows tepsi davranışını kaydeder. Görsel yakalama sayısı sıfırdır; bununla tepsi animasyonunun görsel kabulü tamamlanmış sayılmaz.
- build/package-check-0.1.5.json paket EXE kabul raporudur.
- Gerçek NAS, iki PC, temiz Windows ve büyük gerçek arşiv pilotu bu değişiklikle doğrulanmış değildir. V4 bütünü tamamlandı denmez.
- Başlangıçta bulunan tests/test_durability.py değişikliği korunur ve bu sürüm commit’ine alınmaz.

## Yeniden doğrulama

- .venv/Scripts/python.exe -m pytest -q
- .venv/Scripts/python.exe eval/review_015.py (QT_SCALE_FACTOR=1, 1.25, 1.5)
- .venv/Scripts/python.exe eval/native_015.py (yalnız sentetik kasa; kısa süreli Windows test penceresi)
- .venv/Scripts/python.exe packaging/build.py
- .venv/Scripts/python.exe eval/package_check.py
- Son kaynak test sonucu: **79 geçti**, 122.02 saniye. Kullanıcının mevcut dayanıklılık testi de çalıştırıldı; dosyası değişmeden korundu.
- Gerçek Windows: 96 DPI, tepsi mevcut, 11 farklı simge anahtarı gözlendi, idle sonrası animasyon timer durdu. Gizli tepsi alanının görsel kabulü bekler.
