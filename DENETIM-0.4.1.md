# Evrakçı 0.4.1 — Sekme içleri üç sütun işlik düzeni

Tarih: 13.10.2026. Kaynak: kullanıcının sekme içlerini modern bulmaması; C tasarımı ("Üç sütun işlik") seçildi ve uygulandı. Sol sekmeler ve genel kabuk değişmedi.

## Değişiklikler

- Ara ekranı: sabit kare iki kart kalktı; yerine Filtreler | Sonuçlar | Seçili evrak üç sütunu (QSplitter, kullanıcı ayarlayabilir). 7 butonluk kalabalık satır, etiketli gruplara bölündü (filtreler, kayıtlı aramalar, etiket). Tek tık ayrıntıyı gösterir, çift tık önizlemeyi açar. CSV indir sonuç başlığında.
- Geçmiş: liste + ayrıntı (sorgu, okunur filtre özeti, "Bu aramayı çalıştır"); ham JSON satırı kalktı.
- Taranmış Evraklar: liste + ayrıntı (ad, yol, durum, kaynak, Ön izle).
- AI / Kaynaklar / Tarama / Ayarlar: yapısı korundu (liste+ayrıntı veya pano düzenindeydi).
- Dar pencerede filtre paneli kendi içinde kayar; hiçbir buton minimum boyunun altına ezilmez, yatay kaydırma çıkmaz (ölçüldü).
- `smoke.py` paket kabulü yeni işliğe uyarlandı (kare-kart kabulü kalktı).

## Davranış garantileri

- Tüm widget/fonksiyon adları korundu; test ve eval kontratı bozulmadı.
- Kilitlenmede yeni ayrıntı panelleri de temizlenir.

## Sınırlar

- Gerçek müşteri arşivi, temiz Windows ve gerçek DPI pilotu bu değişiklikle doğrulanmış değildir.
- Ağaçtaki ilgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py, ocr_setup.py, tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
