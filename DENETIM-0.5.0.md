# Evrakçı 0.5.0 — Arayüz sıfırdan yeniden tasarlandı

Tarih: 15.10.2026. Kaynak: kullanıcının arayüzü hiç beğenmemesi; "iç içe geçen kutular, görünmeyen
çizgiler, uyumsuz renk paleti" şikâyeti. Yeni tasarım dili maket olarak onaylandı
(`maket/evrakci-0.5-yeni-arayuz.html`) ve birebir uygulandı.

## Ölçülen sorunlar (önce/sonra)

Önce mevcut arayüzün 16 ekran görüntüsü alınıp piksel ölçümüyle doğrulandı:

| Sorun | Önce | Sonra |
|---|---|---|
| Ray her iki temada sabit lacivert | `#112039` | Açıkta `#F6F8FB`, koyuda `#12171D` (tema uyumlu) |
| Beyaz üstüne beyaz | zemin `#F4F6FA` / panel `#FFFFFF` | zemin `#F1F3F7` / panel `#FFFFFF` / tonlu `#F6F8FB` |
| Kart içinde kart | `pageCard` + `card()` + `sideRail` = 3 kat | Sayfa başına **tek yüzey** + kıl payı ayırıcı |
| Görünmeyen ayırıcı | `#E1E7F0`, beyaz zeminde kayboluyor | `#E4E7EC` (açık) / `#333B47` (koyu) |
| Kodda sabit renkler | buton `#1B304C`, ikon `#65748B`/`#91A3BF` | Tek kaynak: `theme.pal()`; kodda sabit renk yok |
| Ayarlar gruplanmamış | 5 ayrı form, "Kaydet" ortada | 5 bölüm başlığı, satır düzeni, Kaydet başlıkta |
| Koyu temada ayırıcı yok | sütun sınırları okunmuyor | Ayırıcı belirginleştirildi, ikincil metin `#9BA6B4` |

## Yeni tasarım dili

- **Tek yüzey:** Liste + ayrıntı aynı kartın içinde, arada dikey kıl payı ayırıcı.
- **Filtre paneli:** Çerçeveli kutu yerine hafif tonlu sütun (`yuzey2`).
- **Üç buton çeşidi:** dolgulu (asıl iş) / çerçeveli (ikincil) / yazı (üçüncül) + `tehlike` ve `kucuk`.
- **Sayfa başlığı şeridi:** başlık + açıklama solda, durum rozeti + ortak işlemler sağda.
- **Ölçü şeridi:** Tarama sayaçları ayrı kutular değil, ayırıcıyla bölünmüş tek şerit.
- **Satır delegesi:** kart yerine düz satır; seçimde sol vurgu çubuğu, `yuzey2` zemin.
- **Ray:** tema uyumlu yüzey, nav öğeleri, altta ayırıcı + daraltma + kasa eylemleri alt alta.
- **Toast:** onay artık durum çubuğunda değil, pencerede kendiliğinden kaybolan şerit.
- **İkon takımı:** 13 çizgi simge (yeni: `ai`, `check`, `document`), hepsi `pal()` renginde.

## Yapısal düzeltmeler

- `archive_ui.install` sayfaları artık **kimlikle** buluyor (indeks kayması hatası giderildi).
- Yedekler ayrı sekme değil, Ayarlar içinde bölüm (7 sekme ↔ 7 sayfa doğrulandı).
- `_sayfa_kartlari()` yığındaki her sayfaya zemin veriyor; QScrollArea iç gövdesi de kapsandı.
- `_source_layout` silinmiş nesne yarışına karşı korumalı (kapanış sırasında RuntimeError giderildi).

## Ölçülen garantiler

- **163 test geçti** (öncesi 162; ray düzeni testi tasarıma uyarlandı).
- Uçtan uca smoke: **23 kontrol, exit 0** (kasa → tarama → arama → önizleme → kilit/açma → OCR → AI yerel önizleme).
- Her iki temada **7/7 sekmenin zemin rengi** doğru ölçüldü; Fusion sızıntısı yok.
- 1100–1600 px genişlikte yatay kaydırma yok, hiçbir buton taşmıyor.
- 16 ekran görüntüsü + 6'lı kolaj ile gözle doğrulandı (açık/koyu × yedi sekme + kilit + sihirbaz).

## Sınırlar

- Gerçek müşteri arşivi, temiz Windows ve gerçek DPI pilotu bu değişiklikle doğrulanmış değildir.
- Ekran görüntüleri `WA_DontShowOnScreen` ile alındı (gerçek font, ekranda görünmez).
- Ağaçtaki ilgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py,
  tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
