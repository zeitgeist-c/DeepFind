# Evrakçı 0.4.2 — 7 sekmede yeni iç tasarım dili

Tarih: 14.10.2026. Kaynak: kullanıcının sekme içlerini amatör bulması; "yenidil" maketi onaylandı ve birebir kuruldu. Sol sekmeler ve genel kabuk değişmedi; davranış ve test kontratı korundu.

## Yeni dil

- İnce çizgili bölmeler + her bölmede başlık ve işlem çubuğu + sayaç rozetleri + sağda ayrıntı kartı.
- Ara: filtre rail (renkli yan panel) | sonuçlar (sayaç + CSV) | seçili evrak (Tür/Etiket satırları).
- AI: kurulum rail + numaralı adımlar (Soru, Alıntılar, Yanıt).
- Kaynaklar: işlem çubuğu (sayaç + Klasör ekle) + liste/ayrıntı; dışlananlar ayrıntı kartında.
- Tarama: 3 durum kartı (kapsam, saat, durum) + kapsam + işlem çubuğu (Başlat/Duraklat/İptal/Yeniden dene + ayrıntı) + son taramalar.
- Geçmiş: işlem çubuğu (sayaç + Temizle) + liste/ayrıntı; ham JSON satırı okunur özete çevrildi.
- Taranmış Evraklar: filtre satırında sayaç + liste/ayrıntı + sayfalama çubuğu.
- Ayarlar: bölmeli tek sütun (Çalışma, Tüketim, Etiket kuralları, Güvenlik, Yedekler).

## Ölçülen garantiler

- 1440x860 ve 1100x700 boyutlarında hiçbir etkileşimli öğe minimum boyunun altına ezilmiyor; yatay kaydırma çıkmıyor; sütunlar çakışmıyor.
- Uzun buton adları kısaltıldı, tam metin ipucunda duruyor.
- Kilitlenmede yeni sayaç ve ayrıntı panelleri de temizlenir.

## Sınırlar

- Gerçek müşteri arşivi, temiz Windows ve gerçek DPI pilotu bu değişiklikle doğrulanmış değildir.
- Ağaçtaki ilgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py, tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
