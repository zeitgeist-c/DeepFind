# Evrakçı 0.6.1 — Kök kaldırma düzeltmesi (denetim)

Tarih: 15.10.2026. Kaynak: kullanıcı bildirimi — "Kaynaklar → Kaldır" kökü listeden
siliyor ama uygulama "Yanıt Vermiyor" oluyor.

## Semptom
- "Yanıt Vermiyor" (GUI donması) kök kaldırma sırasında.
- Kök listeden düşüyor ama indeksteki dosyalar aramada görünmeye devam ediyordu.

## Bulgular (kanıt)
1. **Sürücü kökü eşleşme hatası** — `src/evrakci/exclusions.py:32`:
   `os.path.normpath("C:\\")` → `C:\` (ayraçla biter). Kod `rl + "\\"` ile çift
   backslash (`C:\\`) arıyor, hiçbir path eşleşmiyor. Canlı kasada ölçüm:
   kök `C:\` altında **112.019 kayıt**, `is_excluded` eşleştirdiği **0**;
   `D:\`, `E:\`, `G:\` altında 0; `P:\` altında 61.
2. **Senkron işleme** — `src/evrakci/app.py:1416` (`_kok_kaldir`): GUI thread'inde
   112K satır tek tek DELETE + `rebuild_vocab` (2.48M segment yeniden tokenize) →
   dakikalar blokaj. Worker deseni (TaramaIsci) halihazırda var.

## Düzeltme
- `exclusions.is_excluded`: kural ayraçla bitiyorsa `pl == rl or pl.startswith(rl)`
  ile eşleştir; normal klasör dalları aynen korundu (regresyon testleri kapsadı).
- `_kok_kaldir` → `KokKaldirIsci` QThread işçisi: ayrı SQLCipher bağlantısı, silme +
  sözlük yenileme arka planda; arayüzde buton "Kaldırılıyor…" + durum çubuğu mesajı,
  kilit/çıkış sırasında işleme koruma, `_exclusive_ready` kapsamı.

## Regression
- `tests/test_review.py`: `test_drive_root_exclusion_matches_all_files_under_it`,
  `test_drive_root_removal_empties_index`.
- `tests/test_ui.py`: `test_kok_kaldir_isci_surucu_koku_ve_koruma`,
  `test_kok_kaldir_worker_gui_kilitlemez` (QThread + olay çevrimi).

## Doğrulama
- **193 test geçti** (önceki 189 + 4 yeni).
- Canlı kasada salt okunur ölçüm: fix sonrası `C:\` altında 112.019 kayıt eşleşiyor
  (eski 0); diğer köklerdeki kayıtlar korunuyor.
- Canlı veriye dokunulmadı (kullanıcı onayı).

## Kapsam dışı
- Canlı kasada kök kaldırma işlemi uygulanmadı (kullanıcı yalnız kod düzeltmesi istedi).
- Diğer ağaçtaki kullanıcı değişiklikleri (doc_adapter, ocr, ocr_setup,
  test_durability, DURUM.md önceki not) korundu; bu sürümün kapsamına girmedi.
