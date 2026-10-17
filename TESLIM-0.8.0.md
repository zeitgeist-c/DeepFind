# Evrakçı 0.8.0 — Yedek / sürüm teslimi

Tarih: 17.10.2026. Kapsam: [DENETIM-0.8.0.md](DENETIM-0.8.0.md).

OCR motoru Tesseract 5'ten RapidOCR 3.10'a (PP-OCRv6 det/rec + yön
sınıflandırıcı, ONNX Runtime 1.30) geçirildi. Kalite düzeltmeleri, kök
temizliği ve `queue.py → job_queue.py`, `sched.py → scheduler.py`
yeniden adlandırmaları (donmuş pakette stdlib gölgeleme hatası)
alındı. Önceki sürüm: 0.7.0.

## Doğrulamalar

- **238 test geçti** (pytest, `.venv` Python 3.13.15).
- Paket kapısı: `eval/package_check.py` **25/25 kontrol GEÇTİ** (açılış +
  OCR zinciri pakette doğrulandı).
- Eval kapısı: holdout top1 = 1.0 (mevcut).

## Paket

- `Evrakçı-0.8.0.zip`: **154.483.936 bayt**.
- SHA-256: `81c3624b252491760a8149d584acff32a3260ecce407def7cb62aa8d37f3dcdf`
- ZIP CRC doğrulanmış; iç sürüm `0.8.0` (manifest + EXE version info).
- Eski EXE/sürümler silinmez; güncelleme yalnız yeni klasör açar.

## Yerel teslim

- Sürüm kaynağı: `src/evrakci/version.py` → `0.8.0` (tek kanonik kaynak).
- Yerel commit + `v0.8.0` etiketi bu teslim kaydını içerir.
- Push/tag: yedek zinciri kapsamında `origin/master` ve `v0.8.0` gönderilir.
- GitHub Release sayfası ve canlı kurulum (deployment) bu yedek adımı
  dışında, ayrıca istenirse yapılır.
