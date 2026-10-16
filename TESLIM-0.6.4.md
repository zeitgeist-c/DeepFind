# Evrakçı 0.6.4 — Temizlik + v9 denetim teslimi

Tarih: 16.10.2026. Kapsam: [DENETIM-0.6.4.md](DENETIM-0.6.4.md).

0.6.3 (tek katlanmış FTS) sonrası kapanış turu: kanıtlı temizlik + v9
değişiminin dokunduğu yolların denetimi. Kod davranışı değişmedi; denetim
bulgusu kod değişikliği gerektirmedi.

- Tam test paketi: **208 geçti** (temizlik öncesi/sonrası aynı; düşüş yok).
- Eval kapısı: holdout top1=1.0 / top3=1.0, p95 1.6 ms — KAPI: GEÇTİ.
- Temizlenen: 7 A8 tanı betiği + 2 eski spec + 15 kullanılmayan import (AST kanıtlı).
- Kaynak smoke: **25 kontrol**; paketli EXE smoke aynı 25 kontrol.
- `Evrakçı-0.6.4.zip`: **169.624.127 bayt**. SHA-256:
  `c9e7bac70f78357fa1acae57fb07196689a9853e48fe186351942d6e1f168642`. ZIP CRC
  doğrulanmış; paketli EXE smoke 25/25 GEÇTİ.
- EXE FileVersion/ProductVersion **0.6.4**; BAT aynı sürüm EXE'sini çalıştırır;
  manifest 0.6.4.

Canlı kasa 0.6.3'te v9'a geçti (20,44 → 8,62 GB). Bu sürümde kasa geçişi yok;
yeni ZIP'i kurunca doğrudan açılır.

Yerel commit ve `v0.6.4` etiketi bu teslimle oluşturulur; push + GitHub Release
bu teslimin kapanış adımıdır. Eski EXE'ler/sürümler silinmez.
