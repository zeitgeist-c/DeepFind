# Evrakçı — DURUM

Son güncelleme: 27.09.2026 (A0 + A1 tamamlandı)

## Aktif aşama
- A0 GEÇTİ, A1 GEÇTİ.
- A2 GEÇTİ (27.09.2026): Varyant A onaylı (sol gezinme + sonuç + sağ önizleme).
- A3 GEÇTİ: kasa→tara→ara uçtan uca (CLI + 3 test). FTS harici-içerik sütun düzeltmesi yapıldı.
- A4 GEÇTİ: kuyruk/retry/kurtarma/kilit/hariç/kayıp (12 test + CLI). Yol ayraç hatası CLI kanıtıyla yakalanıp düzeltildi. DOC: LO yok → ad/yol + önkoşul.
- A5 GEÇTİ (27.09.2026): 74 sentetik belge, 83 sorgu; holdout top1=1.0 top3=1.0 (≥0.90), no-result temiz, p95≈1ms. Sınıflı retrieval (strict/folded/fuzzy) + belge-düzeyi kesişim + yıl/tür filtresi + geçmiş + SHA-256 kopya. 21 test geçti.
- A6 GEÇTİ (27.09.2026): Tesseract CPU hattı (triyaj + 300DPI/12MP + TSV-conf + tek iyileştirme/keep-better + timeout-kill + RAM kapısı + kontrollü temp). Dil ölçümü: tur=1.000, tur+eng=0.820 → varsayılan tur. Rapor: ocr conf 92.4, tepe 114MB, ocr_failed=0. Bütçeler: sayfa/metin/ZIP/hücre/OCR-sayfa kotaları. Ağır OCR eklenmedi (kapı aranmaz). 33 test geçti.
- A7 GEÇTİ (27.09.2026): Varyant A PySide6 arayüz (arama + filtre + sağ önizleme PDF/Excel/Word + kaynaklar/tarama/geçmiş/yedekler/ayarlar/kilit + 6 adımlı sihirbaz + açık/koyu/sistem teması). Şifreli yedek/geri-yükleme (rollback + hariç-kural koruma + 7 saklama) + parola-değiştirme (önce yedek,tırnak-güvenli rekey) + tanı komutu + zamanlayıcı (12:30+cihaz-gecikmesi, catch-up-tek, çift-koşma kilidi, HKCU autostart) + uyku/oturum-kilidinde kasa kilidi. 58 test geçti (backup 11 + sched 6 + ui 8 dahil); eval holdout top1=1.0 top3=1.0 kapı GEÇTİ. Görsel kanıt: açık/koyu ekran görüntüsü + önizleme metin okunurluğu doğrulandı.
- Doğrulanmayanlar (A8 pilota): gerçek monitörde tray simgesi, 125/150/200 DPI, ekran okuyucu, uyku/uyandırma sonrası zamanlayıcı, temiz-makine paketi, 2 PC NAS.
- A8 GEÇTİ (27.09.2026): 0.1.0 kesinleşti. Donmuş onedir kanıtı (init+tara+ara+tani, exit 0). Kök neden: yönlendirici `--kasa` değerini komut sanıp arayüz dalına düşüyordu (asılma + yanlış-dal HMAC izlenimi) → bayrak-değer atlama + regresyon testi. Paket `Evrakçı-0.1.0.zip` (102 MB, sha256 raporlu) + LGPL metni pakette. Yerel commit `729373d` + tag `v0.1.0` (eşleşti). Push/Release/deploy yok. 59 test + eval kapısı GEÇTİ.
- Yapılmayanlar: NAS pilotu + temiz-makine denemesi (erişim yok, kullanıcıda).
- Kapanış: yerel commit + `v0.1.0` (push/release/deploy yok).

## Kilitli runtime adayları (A1 kanıtlı)
- CPython 3.13.15 x64 (birincil) + 3.12.10 (ikincil); sqlcipher3==0.6.2 (cipher 4.12.0 community, FTS5, WAL, şifreli yedek OK).
- pypdfium2==5.13.0, openpyxl==3.1.5, xlrd==2.0.2, python-docx==1.2.0, defusedxml==0.7.1.
- rapidfuzz==3.14.6, Pillow==12.3.0, PySide6-Essentials==6.11.2, pyinstaller==6.22.3.
- Tesseract 5.4.0.20240606 + tur/eng/osd (tur sha256: 489b9504…; eng: 7d4322bd…; osd: 9cf5d576…).
- PyInstaller onedir frozen exe: DB+FTS+PDFIUM+spawn/kill geçti.

## Pilot konumu (repo dışı)
- `…/hermes/cache/scratch/evrakci-a1/`: venv, venv313, smoke_db.py, smoke_ext.py, pkg_app.py, dist/.
- Repo'ya kod girmedi; plan belgeleri değişmedi; push/release yok.

## Kullanıcıdan bekleyen (karar)
1. DOC zorunluluğu: KAPSAMDA — adaptör denenecek (27.09.2026 kullanıcı kararı).
2. Disk temp türev kabulü: KABUL — kontrollü temp (27.09.2026 kullanıcı kararı).

## Bilinen sınırlar
- Temiz makine (Python/Office yok) + 8 GB RAM + Win10 + 2 PC NAS testi: A8'e kaldı.
- sqlcipher3/rapidfuzz/Pillow lisans metni A8'de dosyadan doğrulanacak.
- PySide6 LGPL dağıtım yükümlülüğü A8'de kapatılacak.
