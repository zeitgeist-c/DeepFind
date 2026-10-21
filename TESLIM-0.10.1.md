# Evrakçı 0.10.1 — kurulum ve güncelleme

21.10.2026. Düzeltme sürümleri bundan sonra 0.10.1, 0.10.2, 0.10.3 sırasıyla ilerler.

- Tam setup programı ve embedding modelini aynı kurulum dizinine yerleştirir. Varsayılan model yolu `C:\Program Files\Evrakçı\_internal\embedding\embeddinggemma-2-Q8_0.gguf`. Model setup'a gömülüdür; ilk kurulum için ek internet indirmesi gerekmez.
- Küçük güncelleme kurulu sağlam modeli yeniden kopyalamaz. 0.10.0'dan kalan doğrulanmış ProgramData modeli önce geçici dosyaya kopyalanıp SHA-256 ile tekrar doğrulanır; başarılı yerleştirmeden sonra eski kopya temizlenir. Eksik/bozuk modelde tam paket seçilir; tam setup bozuk modeli onarır.
- Sabit AppId ve mevcut kurulum dizini korunur. Program kapandıktan sonra Inno aynı dizini günceller, kısayollar yeni sürüme yönelir. Güncelleme sonuç kaydı ve kurulum log'u yazılır; UAC iptali/hata geçici klasörden çalışıyormuş gibi gösterilmez. İşlem kapanma zaman aşımında kurulum zorlanmaz.
- Başarılı kurulum yalnız eski sürüm numarası ile PE sürüm kaydı eşleşen uygulama EXE/BAT çiftlerini temizler. Bilinmeyen dosyalar, kasa, kaynak evraklar ve yedekler korunur. Kaldırma uygulamayla birlikte bu kurulumun modelini kaldırır.
- Modern güncelleyici ZIP klasör taşımasına düşmez; kurulum EXE'si bulunmayan yayın reddedilir. ZIP eski istemci/taşınabilir kullanım için kalır. 0.9.0 ve daha eski ZIP güncelleyicilerden bu düzene geçişte tam EXE bir kez çalıştırılmalıdır.

## Kabul kanıtı ve sınırlar

Tam regresyon normal Windows izinleriyle **296 geçti, 1 atlandı** (`build/tests-windows-0.10.1.xml`). İlk hedefli testler 52/52 geçti. Sandbox içindeki tam test/paket denemeleri normal Windows kabulünün yerine kullanılmadı.

İzole test AppId ile gerçek Inno kabulü: eksik modelde küçük güncelleme dosya değiştirmeden durdu; 0.9.0→0.10.1 yükseltmesi eski modeli kurulum dizinine aldı; eski EXE/BAT temizlendi; 0.10.0 EXE/BAT temizliği, tam setup ile bozuk model onarma, küçük güncellemede modelin zaman damgasının korunması ve kaldırmada kullanıcı dosyalarının korunması geçti. Kurulu EXE gerçek anlamsal arama dahil paket smoke testinden geçti. Kanıt: `build/installer-acceptance-0.10.1.json`.

Tam test, son paket ve kaynak kimliği teslim kapısında ayrıca doğrulanır. Canlı Program Files kurulumu ve kasa test için değiştirilmedi. Test AppId'si ayrı, hedef proje içindedir; gerçek üretim UAC diyaloğu, temiz Windows ve farklı GPU/sürücü ortamları doğrulanmış sayılmaz. NVIDIA donanım kabulü hâlâ açıktır.

Kaynak sürümü: `src/evrakci/version.py`. Paketler `Evrakçı-0.10.1.exe`, `.zip`, `.evrakci`; kesin commit, özet ve kabul raporları `build/release-0.10.1.json` ile kaydedilir. GitHub yayını bu sürümün yerel hazırlanmasından ayrıdır.
