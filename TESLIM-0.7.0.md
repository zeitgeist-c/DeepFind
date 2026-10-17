# Evrakçı 0.7.0 — Kendi kendini güncelleme teslimi

Tarih: 17.10.2026. Kapsam: [DENETIM-0.7.0.md](DENETIM-0.7.0.md).

Kullanıcı isteğiyle Evrakçı'ya WordArc'ın çalışan güncelleme sistemi
uyarlandı. Kaynak depo özel kalır; paketler herkese açık
`zeitgeist-c/Evrakci-Releases` deposunda yayınlanır.

- Güncelleme bölümü: Ayarlar sayfasında; denetle / indir ve kur / iptal +
  ilerleme. Açılışta 30 sn sonra günde bir sessiz denetim.
- Güvenlik: yalnız HTTPS; boyut + SHA-256 özet doğrulaması; Zip Slip
  koruması; manifest sürüm/program çapraz kontrolü; doğrulama geçmeyen
  dosya asla yerleşmez/çalışmaz; iptal dosyayı siler.
- Yerleşme: bekçi BAT eski PID çıkışını bekler, hazır klasörü çalışan
  programın yanına taşır, `--restarted --kasa <yol>` ile açar, self-delete.
  Taşıma başarısızsa fallback + kullanıcı bildirimi.
- Eski program klasörü/kasa dokunulmaz; Updates artıkları 6 saat eşiğiyle
  toplanır, çalışılan klasör korunur.

## Doğrulamalar

- **234 test geçti** (26 yeni: sürüm karşılaştırma, yayın çözümleme iki
  varlık yazımı, indirme özet/boyut/iptal, ZIP açma + Zip Slip + manifest,
  hazırlama uçtan uca, bekçi betik içeriği, temizleme eşiği, UI akışı).
- **Paketli EXE smoke 25/25** (kaynak + paket; güncelleme bölümü
  kontrolleriyle). Eval kapısı: holdout top1=1.0 / top3=1.0.
- **Swap mekaniği gerçek süreçlerle kanıtlandı:** kurban süreç 6 sn yaşadı;
  BAT 6,5–6,9 sn bekledi, klasörü taşıdı, yeni EXE'yi başlattı, kendini
  sildi (CREATE_NO_WINDOW; unicode yollar; System32 tam yolları).
- **Canlı yayına karşı uçtan uca:** `check_for_update("0.6.4")` gerçek
  GitHub API'sinden 0.7.0'ı buldu; paket indirildi, SHA-256 özeti tuttu,
  ZIP açıldı, manifest sürümü doğrulandı (aşağıda).

## Paket

- `Evrakçı-0.7.0.zip`: **169.642.249 bayt**. SHA-256:
  `1d8101ea242514e1ff4c93e8acd2786bc40dffe17dd3f290c43b1771cd8b79e3`.
  ZIP CRC doğrulanmış.
- Sürüm kaynağı commit `9546783` + `v0.7.0` etiketi; `origin/master`'a
  push edildi. GitHub Release hem özel kaynak depoda hem herkese açık
  `Evrakci-Releases` deposunda açılır (bu teslimin kapanışı).
- Eski EXE'ler/sürümler silinmez; güncelleme yalnız yeni klasör açar.

## İlk gerçek otomatik güncelleme

Bu sürüm altyapıyı getirir: ilk gerçek "denetle → indir → yeniden başlat"
deneyimi bir sonraki sürüm (0.7.1+) yayınlandığında kendiliğinden yaşanır.
Bu turda aynı akışın tüm aşamaları canlı yayına karşı tek tek kanıtlandı;
swap aşaması gerçek Windows süreçleriyle ayrıca doğrulandı.
