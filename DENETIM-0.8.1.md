# Evrakçı 0.8.1 — Denetim: DMS arayüz desenleri (M1–M5)

Tarih: 17.10.2026. Kapsam: `REA-DMS-Analizi.md` planındaki M1–M5 değişiklikleri
(`src/evrakci/{thumbs,sorgu,preview,ui,app,rank,workers,theme,archive_ui}.py`,
`tests/{test_thumbs,test_sorgu,test_tags,test_ui,test_durability}.py`,
`eval/ui_shots.py`). Önceki sürüm: 0.8.0.

## Yöntem

- **Kaynak öncelikli REA:** hedefler açık kaynak olduğu için depo kaynağı okundu
  (REA CLI `doctor` kanıtı kayıtlı; native motorlar kurulu değil ve gerekmedi);
  kod alınmadı, desen uyarlandı (GPL-3.0 / Apache-2.0 / AGPL-3.0 hedefler).
- Her milestone: birim/entegrasyon testi + iki temada ekran görüntüsü kanıtı +
  `DURUM.md` kaydı. Değişiklik yüzeyi arama/görüntüleyici/liste yollarıyla
  sınırlı tutuldu; **veri şeması değişmedi** (yeni tablo/kolon yok).

## Bulunan ve kapatılan kusurlar (hepsi test/görsel kanıtlı)

1. **Qt iş parçacığı çökmesi:** koşan bir `QThread` nesnesi pencereyle birlikte
   yok edilince süreç 0xC0000409 ile düşüyordu. Kapanış yolları (ana pencere,
   görüntüleyici, test fixture'ı) yükleyicileri senkron durdurup bekliyor.
2. **Önizleme kutusu taşması:** sabit yükseklik, koyu temada alt metinle
   çakışıyordu. `ui.GorselKutusu` kutuya uyan ölçekleme + alt/üst sınır getirdi.
3. **Sığdırma tazelenmiyordu:** sayfa rayı görününce tuval daralıyor ama yeniden
   render olmuyordu. Tuval görüntü alanı izleniyor; yalnız kutu gerçekten
   değiştiyse render ediliyor (naif döngü engellendi).
4. **Görünür kalan filtre çipleri:** yeniden kurulumda eski `Cip` widget'ları
   görünür kalıp alanın üstüne biniyordu. Gizle + ebeveynden ayır + regresyon
   testi (pencere altındaki `Cip` sayısı = aktif çip sayısı).
5. **Sorgu eşleştirme hatası:** alan sözdizimi kullanan aramalarda sonuç, ham
   kutu metniyle karşılaştırıldığı için düşürülüyordu (0 sonuç). Eşleştirme
   artık çözülen serbest metinle yapılıyor.

## Doğrulama

- `pytest`: **272 test** (237 → 272), tam paket çıkış kodu 0.
- Paket kapısı: `eval/package_check.py` — sonuç `TESLIM-0.8.1.md` içinde.
- Görsel kanıt: `build/review-ui-0.8.1/` (34 görüntü; açık/koyu tema).
- Kaynak güvenliği bekçisi (`test_durability`): `thumbs.py` için gerekçeli
  istisna + "kaynak dizine dokunmaz" runtime testi ile geçti.
- Toplu etiket sözleşmesi: tek `commit`, hatada `rollback` (sahte bağlantı
  testiyle kanıtlandı).

## Sınırlar / bilinmeyenler

- Donmuş pakette küçük resim **görsel** üretimi paket dumanında kapsanmıyor
  (duman testi veri yolunu doğrular); Pillow WebP yazamıyorsa kod JPEG'e düşer.
- `eval/ui_shots.py` kapanışta 0xC0000409 ile düşüyor; değişiklik öncesi temel
  çizgide de aynı (stash ile ölçüldü), görüntüler sorunsuz üretiliyor.
- Temiz makine (Python/Office yok) pilotu bu sürüm kapsamı dışında; açık kalem.
