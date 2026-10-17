# Evrakçı 0.8.1 — Yedek / sürüm teslimi

Tarih: 17.10.2026. Kapsam: [DENETIM-0.8.1.md](DENETIM-0.8.1.md),
[REA-DMS-Analizi.md](REA-DMS-Analizi.md).

Üç açık kaynak belge yönetim sisteminin (paperless-ngx, papermerge-core,
docspell) tersine mühendislik analizinden uyarlanan beş arayüz çalışması
(M1–M5): küçük resim hattı, görüntüleyici (yakınlaştırma kademeleri + sayfa rayı
+ klavye), filtre çipleri/görünüm modları, çoklu seçim + toplu etiket, sorgu
sözdizimi + satır içi doğrulama. Önceki sürüm: 0.8.0.

## Doğrulamalar

- **272 test geçti** (pytest, `.venv` Python 3.13.15; 237 → 272).
- Paket kapısı: `eval/package_check.py` **25/25 kontrol GEÇTİ** — gerçek EXE ile
  açılış + tarama akışı dahil; rapor `build/package-check-0.8.1.json`.
- Paket üretimi ayrıca kendi dumanını koştu (`packaging/build.py` → EXE
  `--package-smoke` OK).
- Görsel kanıt: `build/review-ui-0.8.1/` (34 ekran görüntüsü, açık/koyu).
- Güncelleyici uçtan uca doğrulandı: `/releases/latest` → sürüm `0.8.1`, boyut
  ve SHA-256 yayın özetiyle **birebir** aynı (aşağıdaki dağıtım bölümü).

## Paket

- `Evrakçı-0.8.1.zip`: **154.520.305 bayt**.
- SHA-256: `15f8f9389858cea3ca2a5f0c4b106a3edbbf609701d3a78caa8d983992c722fe`
- ZIP CRC doğrulanmış (`zip_crc: true`); iç sürüm `0.8.1` (`manifest.json` + EXE
  version info). Pakette ayrıca `DENETIM-0.8.1.md`, `README.md`, `LISANSLAR.md`,
  lisans klasörü (LGPL-3.0 metni dahil) ve RapidOCR ONNX modelleri bulunur.
- Eski EXE/sürümler silinmez; güncelleme yalnız yeni klasör açar.

## Dağıtım (halka açık indirme linki)

- Yayın: `zeitgeist-c/Evrakci-Releases` → **v0.8.1** (Latest).
- Sayfa: https://github.com/zeitgeist-c/Evrakci-Releases/releases/tag/v0.8.1
- İndirme: https://github.com/zeitgeist-c/Evrakci-Releases/releases/download/v0.8.1/Evrakci-0.8.1.zip
- Kaynak depo özel kalır; bu depo yalnız kurulum paketini taşır. GitHub varlık
  adını latinleştirdi (`Evrakci-0.8.1.zip`); güncelleyici iki yazımı da kabul eder.
- Uygulama içi güncelleme: kurulu 0.7.0/0.8.0 sürümleri günde bir sessiz denetim
  ya da Ayarlar → Güncellemeler ile doğrudan 0.8.1'e atlar. Güncelleyici
  doğrulaması: sürüm `0.8.1`, boyut `154520305`, özet
  `15f8f938…722fe`, indirme bağlantısı yukarıdakiyle aynı.

## Yerel teslim

- Sürüm kaynağı: `src/evrakci/version.py` → `0.8.1` (tek kanonik kaynak).
- Yerel commit + `v0.8.1` etiketi bu teslim kaydını içerir.
- Push: `origin/master` ve `v0.8.1` (tek yazar kuralı; kaynak depo özel).
