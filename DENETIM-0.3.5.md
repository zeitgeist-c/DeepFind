# Evrakçı 0.3.5 — büyük kasa açılışı

Tarih: 01.10.2026.

## Yakalanan sorun

Kullanıcı ekran görüntüsünde “Şifreli kasa açılıyor…” penceresinde kaldı. Yerel yaşam döngüsü günlüğünün son kaydı `vault_open_ready`, sonrasında `schema_begin` yoktu. Mevcut kasa 9.393.872.896 bayt; geçici geçiş yedeğinin WAL dosyası 4.551.030.312 bayttı. İnceleme sırasında ilgili süreç artık çalışmıyordu; sonlanmanın nedeni bu kanıtlarla belirlenemedi.

0.3.4 geçiş öncesi doğrulanmış tam yedeği ana arayüz iş parçacığında alıyordu. Bu sırada olay döngüsü çalışmıyor, açılış penceresi ilerleme göstermiyordu. Bu, kaynakta doğrulanan açılış tasarımı hatasıdır; tam yedek gereksinimi kaldırılmadı.

## Düzeltme

- Kasa hazırlığı, geçiş yedeği, bütünlük doğrulaması ve şema değişimi kendi bağlantısını kullanan arka plan işçisinde yapılır. Ana pencere hazırlık tamamlandıktan sonra kendi bağlantısını açar.
- Açılış penceresi yedekleme yüzdesini, doğrulama ve şema aşamalarını gösterir. Büyük kasaların hazırlanmasının zaman alacağı açıklanır.
- Kapatma isteği yedekleme/doğrulamada güvenli iptal edilir; şema değişimi başlamışsa tamamlanması beklenir. İşçi kapanmadan uygulama sonlanmaz.
- Geçiş başlangıç/bitiş/hata aşamaları, sır veya evrak yolu içermeden yaşam döngüsü günlüğüne yazılır.
- Yeni yedek hedefi bağımsız snapshot olduğundan DELETE günlük kipini kullanır; ek bir kasa büyüklüğünde WAL birikimi önlenir. Şifreleme, bütünlük kontrolü ve atomik teslim korunur.
- Mevcut gerçek kasa ve yarım yedek dosyalarına inceleme sırasında yazılmadı/silinmedi.

## Doğrulama sınırı

Regresyon testi geciktirilmiş gerçek yedekleme sırasında Qt zamanlayıcısının çalıştığını, ilerleme aşamalarını ve iptalde eski kasanın korunmasını sınar. Paketli EXE eski şema ile arka plan hazırlığını çalıştırır. Gerçek 9,39 GB kasanın yeni sürümle tamamlanan açılışı ayrıca kullanıcı pilotunda doğrulanacaktır; açılış süresinin kısa olduğu veya süreç sonlanmasının nedeninin giderildiği iddia edilmez.

Nihai test/paket kayıtları: TESLIM-0.3.5.md. Önceki beş ilgisiz kullanıcı değişikliği korunur ve izole sürümün dışında kalır.
