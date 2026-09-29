# Evrakçı 0.3.2 — PDF ön izleme yanıt süresi

Tarih: 30.09.2026. Başlangıç: `v0.3.1` / `49efe7db10bb5cc7d4898d801f47343442279d7c`.

## Hata ve düzeltme

- PDF seçimi, sayfa çizimi arka planda başlamadan önce ana arayüzde `segments` tablosundan 60 tam metin satırı okuyordu. `segments.file_id` için indeks yok; büyük kasada bu sorgu arayüzü bekletebilir.
- PDF için bu sorgu kaldırıldı. Kaynak dosya açılamazsa arama sonucunda zaten bulunan kısa özet gösterilir. Böylece uzun metin ve veritabanı taraması ön izleme tıklamasını bekletmez.
- Sayfa hazırlanırken Qt'nin belirsiz süreli ilerleme çubuğu ve “PDF sayfası açılıyor…” yazısı görünür. Başarılı açılışta, hatada ve başka belge seçildiğinde gösterge kapanır. PDF çizimi mevcut arka plan işçisinde kalır.

## Doğrulama sınırı

- Hedefli arayüz testleri: PDF seçiminde `segments` sorgusu yasaklanarak normal açılış, gösterge ve kaynak hata akışı sınandı; 2 test geçti.
- Tüm çalışma ağacında 95 test geçti. Bu sayıya sürüm dışı mevcut bir dayanıklılık testi de dahildir.
- Kapsam dışı çalışma ağacı değişiklikleri çıkarılmış izole 0.3.2 kaynağında 94 test geçti. Aynı kaynaktan üretilmiş paketli EXE'de 18 sentetik smoke kontrolü geçti; bunlardan biri PDF seçimi sırasında göstergenin görünmesi, sayfa görüntüsünün oluşması ve göstergenin kapanmasıdır.
- Gerçek 8,62 GiB kasada PDF tıklamasının uçtan uca süresi henüz ölçülmedi.
- Büyük PDF'nin son görüntü ölçekleme aşaması ana Qt iş parçacığında kalır; aşırı büyük sayfada kısa bir bekleme olasılığı ayrıca ölçülmelidir.

Dağıtım kanıtı: `TESLIM-0.3.2.md`.
