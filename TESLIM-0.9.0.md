# Evrakçı 0.9.0 — Yedek / sürüm teslimi

Tarih: 21.10.2026. Kapsam: yerel vektör araması (EmbeddingGemma-2 metin kulesi,
ONNX + DirectML), hibrit FTS + vektör, gömme kuyruğu, model dağıtıcısı.
Önceki sürüm: 0.8.1.

## Doğrulamalar

- **294 test geçti** (pytest, `.venv` Python 3.13.15; 272 → 294).
- Paket kapısı: `eval/package_check.py` **26/26 kontrol GEÇTİ** — gerçek EXE ile
  açılış + tarama akışı dahil (`vektor-model-durumu` dahil); rapor
  `build/package-check-0.9.0.json`.
- Paket üretimi ayrıca kendi dumanını koştu (`packaging/build.py` → EXE
  `--package-smoke` OK, 84 sn soğuk açılış ölçüldü; kapı eşiği ölçüme göre 300 sn).
- Denetim (proje-denetim): 4 bulgu kapatıldı (kilit dışı oturum kurulumu,
  indirici timeout, lisans listesi, bekçi muafiyeti + runtime kanıtı); temizlikte
  silinecek öğe bulunamadı (korunan yayın artifaktları yerinde durur).

## Paket

- `Evrakçı-0.9.0.zip`: **216.371.605 bayt** (büyüme: ONNX Runtime DirectML +
  transformers/tokenizers zinciri; model pakette değil).
- SHA-256: `3aafa8ae891679f5c23a3b2dafca9884d173157d8cf63f144516ff3918ca7242`
- ZIP CRC doğrulanmış (`zip_crc: true`); iç sürüm `0.9.0` (`manifest.json` + EXE
  version info).
- Vektör modeli ilk açılışta indirilir (sürüm kilitli):
  `eg2-text.onnx` (1.085.617.477 bayt),
  SHA-256: `2cabcf6413a22497987da2a092635ade33530614fce978ad11d9828b30dbd843`,
  adres: `.../releases/download/v0.9.0/eg2-text.onnx`.
- Eski EXE/sürümler silinmez; güncelleme yalnız yeni klasör açar.

## Dağıtım (halka açık indirme linki)

- Yayın: `zeitgeist-c/Evrakci-Releases` → **v0.9.0** (Latest).
- Sayfa: https://github.com/zeitgeist-c/Evrakci-Releases/releases/tag/v0.9.0
- İndirme: https://github.com/zeitgeist-c/Evrakci-Releases/releases/download/v0.9.0/Evrakci-0.9.0.zip
  (GitHub varlık adını latinleştirirse `Evrakci-0.9.0.zip` olur; güncelleyici
  iki yazımı da kabul eder).
- Kaynak depo özel kalır; bu depo yalnız kurulum paketini + vektör modelini taşır.

## Notlar

- "Ara" sayfası hibrit arar: model hazırsa vektörle yeniden sıralar, yoksa FTS.
  "AI ile ara" (Gemini) aynen durur; karar sonraki sürüme bırakıldı.
- İlk taramada gömme kuyruğu alt süreçte çalışır; sürücü hatası uygulamayı
  öldürmez, iş `EMBED_FAILED` ile yeniden denenir.
