# Evrakçı 0.1.0 — Teslim Raporu (27.09.2026)

## Sürüm
- Uygulama: 0.1.0 (`src/evrakci/version.py` = `pyproject.toml`, test ile eşitlik doğrulandı)
- Commit: `729373d` (yerel), Tag: `v0.1.0` (annotated, commit ile eşleşti)
- Paket: `Evrakçı-0.1.0.zip` (102 MB, 2563 dosya)
  sha256: `4d901b8a0477c34e7a9473be8ec24fa767e9de29527e6636316e53893748888d`
- Push / Release / deploy: YAPILMADI (yetki yok)

## Doğrulananlar
- 59 test geçti (vertical/durability/search/ocr/backup/sched/ui + router regresyonu)
- Eval kapısı GEÇTİ: holdout top1=1.0 top3=1.0 (≥0.90), p95≈1ms
- Donmuş paket kanıtı (dist/Evrakci-0.1.0): init + tara + ara + tani uçtan uca
- Açık/koyu tema ekran görüntüsü + önizleme metin okunurluğu (offscreen, Segoe UI)
- Lisans manifesti: `LISANSLAR.md` (kurulu dağıtımdan üretildi); LGPL-3.0 metni pakette `licenses/`
- Kök neden düzeltmesi: CLI/arayüz yönlendirici `--kasa` değerini komut sanıyordu → bayrak-değer atlama + regresyon testi

## Bilinen sınırlar / yapılmayanlar
- NAS pilotu: gerçek NAS erişimi yok → YAPILMADI (kullanıcıda)
- Temiz makine denemesi (Python/Office yok, Win10, 8 GB): YAPILMADI
- 2 PC eşzamanlı + 125/150/200 DPI + ekran okuyucu + tray gerçek masaüstü: doğrulanmadı
- DOC: LibreOffice yok → ad/yol (içerik yok); Tesseract paket dışı önkoşul
- OCR varsayılan dil: tur (ölçüm: tur 1.000 > tur+eng 0.820)

## Çalıştırma
- Arayüz: `dist/Evrakci-0.1.0/Evrakci-0.1.0.exe --kasa <yol>`
- Kaynak: `.venv/Scripts/python -m evrakci --kasa <yol>`
- Önkoşul: Tesseract-OCR + `tur` traineddata
