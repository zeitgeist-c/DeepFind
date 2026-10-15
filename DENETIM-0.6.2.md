# Evrakçı 0.6.2 — Denetim düzeltmeleri (denetim)

Tarih: 15.10.2026. Kaynak: 0.6.1 sonrası kullanıcı isteğiyle yapılan derin denetim
("bir hata yapmış mıyım, daha iyi yapılabilecek eksik var mı").

## Bulgular (kanıt)

### 1. `purge_rule` sürücü kökünde eşleşmiyor (P1, yüksek kesinlik)

`src/evrakci/exclusions.py` — "Dışla" kuralı `C:\` yazılınca SQL LIKE kalıbı çift
ayraç (`C:\\%`) arıyordu; ayrıca `%`/`_` içeren klasör adlarında SQL wildcard kaçışı
yanlış genişliyordu. Canlı kasa ölçümü: `C:\` kuralı 112.019 kaydın **0**'ını buldu
(`tests/test_ui.py::test_haric_isci_*` ve repo dışı ölçüm betiği).

### 2. Kaldırma/Dışla atomik değildi (P1)

Dosya kayıtları commit edildikten sonra sözlük yenilemesi başarısız olursa kök
listeden düşmüş, indeks yarım kalıyordu. Dışla'da kural commit'i ile temizlik ayrı
işlemdi.

### 3. Dışla GUI thread'inde senkron (P2, performans/UI)

`_haric_ekle` doğrudan çağrı ile 112K satırlık kökte arayüzü dakikalarca
kilitleyebiliyordu; ayrıca arka plan mutasyonu (kök kaldırma) sürerken tarama
zamanlayıcısı/izleme/kilit/çıkış yolları çakışabiliyordu.

### 4. Sözlük senkron drift (P3)

Hariç temizliği segment içeriğini siliyor ama `vocabulary` içerik terimlerini
bırakıyordu; öneriler silinen içerikten gelebiliyordu.

## Düzeltmeler (dosya)

- `exclusions.py` — sürücü kökü/kılasör ayraç farkındalıklı aday daraltma; kesin
  karar tekil `is_excluded`'da; `add_and_purge` atomik işlem; `purge_rule` commit
  seçenekli, sözlükten içerik terimlerini düşürür (dosya-adı terimleri korunur).
- `app.py` — `HaricIsci` QThread işçisi (transaction + `ScanLock`); `KokKaldirIsci`
  tek transaction (kök + scan_selected + scan_manifest + dosya + sözlük birlikte,
  hata → ROLLBACK); tüm çakışma noktaları (tarama, izleme döngüsü, zamanlayıcı,
  kilit, çıkış, closeEvent) mutasyon sırasında korumalı; merkez widget işlem
  sırasında devre dışı; kaldırma bitince izleyiciler yeni kök listesiyle tazelenir.
- `vocab.py` — `rebuild_vocab(transactional=True)`; `remove_files_from_vocab`
  (opsiyonel dosya-adı dahil).
- `queue.py`, `coordinator.py` — `recover_running(commit=...)`; `ScanLock.__exit__`
  güvenli kapanış; hata yolunda `fh=None`.
- `cli.py`, `backup.py` — `add_and_purge` atomik yol; CLI `ScanLock` içinde.
- `smoke.py` — `root-remove-worker` + `exclusion-worker` paket kontrolleri.

## Regression testleri

- `tests/test_review.py::test_purge_rule_handles_drive_root_and_literal_wildcards`
- `tests/test_ui.py`: `test_kok_kaldir_isci_surucu_koku_ve_koruma`,
  `test_kok_kaldir_worker_gui_kilitlemez` (GUI timer kanıtlı),
  `test_kok_kaldir_geri_alir_hata_olursa`, `test_haric_isci_atomik_surucu_koku_temizligi`,
  `test_haric_isci_hata_geri_alir_kural_ve_icerik`,
  `test_haric_ve_kok_mutasyonlari_scan_kilidini_sayar`,
  `test_haric_ui_islemi_arka_planda_ve_geri_acilir`.

## Doğrulama

- **199 test geçti** (0.6.1'de 193).
- Kaynak smoke: **25 kontrol** (`ok=true`).
- `con.in_transaction` sqlcipher3'te doğrulandı (BEGIN/DDL/rollback).
- Canlı kasada salt okunur ölçüm; canlı veriye **dokunulmadı**.

## Kapsam dışı

- Canlı kasada kök kaldırma/Dışla çalıştırılmadı.
- İlgisiz ağaç değişiklikleri (doc_adapter, ocr, ocr_setup, test_durability,
  DURUM.md önceki bölümleri) korundu; bu sürümün commit kapsamına alınmadı.
