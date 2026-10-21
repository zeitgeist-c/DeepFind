# Evrakçı 0.10.0 — yerel anlamsal arama ve sade dağıtım

Tarih: 21.10.2026. Kullanıcı, EmbeddingGemma 2 incelemesinin uygulanmasını ve Gemini yardımcısının kaldırılmasını onayladı. Kaynak sürümü `src/evrakci/version.py`; yerel etiket `v0.10.0` yalnız son paket kapısı geçince oluşturulur. GitHub push/yayın yapılmaz.

## Değişiklikler

- EmbeddingGemma 2 Q8_0, 256 boyutlu yerel arama; model ve tokenizer kurulum/ZIP içinde. Üretimde Transformers, tokenizers, Hugging Face veya PyTorch kullanılmaz.
- CUDA/Vulkan/CPU motor seçimi; ana pakette Vulkan/CPU, isteğe bağlı SHA-256 sabitli CUDA 12.4 bileşeni. Kullanılan aygıt ve arıza/indeks kapsamı ayarlarda görünür.
- Arama ve indeksleme tek yönetilen model sürecini paylaşır. Yalnız 127.0.0.1, rastgele erişim anahtarı; kilitte/çıkışta süreç kapanır, Windows job sahipliği çökme durumunu kapsar. Yükleme iptali ve uzun metinde örtüşmeli token parçaları desteklenir.
- Vektör adayları kelime eşleşmesinden bağımsız bulunur; sonuçlar filtrelerden sonra birleşir, sıralanır ve sayfalanır. Tırnak/OR/dışlama sorguları klasik kurallarını korur. Eski model vektörleri yeni sürümle karıştırılmaz; tarama eksikleri geri doldurur. Vektör dosya işlemi atomiktir; bozuk/boş/NaN vektör eski kaydı bozmaz.
- Gemini ekranı, ağ çağrıları, API/model ayarları, özet ve üretilmiş cevap kaldırılır. OCR, FTS, şifreli kasa, kaynak takibi, önizleme ve yedekleme korunur.
- Installer sabit AppId ile yükseltir. Dosya sürümü ve SHA kontrol edilir; başarısız installer için eski programı yeniden açma yolu vardır. Model ortak ProgramData konumunda bir kez saklanır. `.evrakci` güncellemesi değişmeyen modeli içermez; model yoksa tam kurulum seçilir. Eski istemciler için tam ZIP korunur.
- Başarılı gerçek installer yalnız bilinen SHA-256'ya sahip eski ONNX modelini ve kullanılmayan program bağımlılıklarını temizler. Tanınmayan model dosyaları, kasalar, kaynak evraklar, yedekler ve eski yayın paketleri korunur. Test installer ayrı AppId kullanır; canlı kurulum temizliği onda kapalıdır.
- OpenCV video DLL'si, kullanılmayan gömme bağımlılıkları, model dönüştürme motorunun kullanılmayan DLL'si ve paketleyicinin gereksiz ortak DLL kopyaları dağıtımdan çıkarılır. Windows Türkçe yol büyük/küçük harf dönüşümünde küçük resim anahtarının değişmesi de düzeltildi.

## Doğrulanan kanıtlar

- Tam regresyon: **292 geçti, 1 atlandı**, `build/tests-0.10.0.xml` ve `.log`. Gerçek model kontrolü ayrı betikte çalışır; test izolasyonu her UI fixture'ında gerçek model yüklenmesini önler.
- Gerçek BF16/Q8 CPU karşılaştırması: 8 sentetik Türkçe belge, 6 sorgu; iki modelin ilk sonuçları aynı, her ikisi 5/6 beklenen belgeyi ilk sıraya koydu. En düşük vektör kosinüsü **0,99966**. Önceki gerçek ONNX modelinin ilk sonuçları da aynı; ONNX→Q8 en düşük kosinüs **0,97199**. Bu küçük küme kapsamlı doğruluk ölçümü değildir.
- Gerçek AMD Radeon RX 6650 XT Vulkan çalışması: kısa ve uzun metinlerde CPU ile **0,9998 üzerinde** kosinüs; sonlu 256 boyutlu çıktı. `build/embedding-gpu-acceptance.json`.
- CUDA paketleri SHA-256 ile indirildi. CUDA aygıt listesi bu bilgisayarda boş; **gerçek NVIDIA CUDA kabulü yapılmadı**.
- Derlenmiş EXE smoke: OCR, PDF/Excel önizlemesi, ilk kurulum/tarama, kilit/açma, gerçek modelle kelime eşleşmesiz anlamsal bulma ve model sürecinin kilitte kapanması dahil kabul akışları. Son kaynak için paket kapısı teslimden önce yeniden çalıştırılır.
- Ayrı test AppId ve proje içi dizinle gerçek Inno **0.9→0.10 yükseltmesi**, modelin zaman damgasını değiştirmeyen güncelleme, kurulu EXE smoke ve kaldırma geçti. Kullanıcının canlı kurulumuna veya kasasına dokunulmadı. `build/installer-acceptance.json`.
- Arşiv modül denetiminde yasaklanan Python ML modülleri bulunmadı; yalnız tek Q8_0 GGUF modeli dağıtıldı. Sayısal paket özeti/boyutu ve kaynak commit'i son derlemenin manifest/teslim makbuzunda kayıtlıdır.

## Teslim kapısı ve dosyalar

- Kullanıcı kurulumu: `Evrakçı-0.10.0.exe`.
- Taşınabilir/eski istemci uyumu: `Evrakçı-0.10.0.zip`, içinde aynı adlı EXE/BAT.
- Programın yönettiği küçük güncelleme: `Evrakçı-0.10.0.evrakci`.
- Kesin kaynak commit'i ve paket özetleri: dağıtım `manifest.json`, `build/release-0.10.0.json` ve son teslim mesajı. Son kaynak commit'inden tekrar derlenir; kirli kaynak manifest'i teslim edilmez. Yerel sürüm etiketi yalnız son doğrulamalar geçince eklenir.

## Açık kabul sınırları

NVIDIA CUDA donanımı, temiz Windows, başka AMD/NVIDIA sürücüleri, gerçek NAS ve büyük canlı arşiv pilotu burada doğrulanmadı. İzole installer testi üretim AppId'sini ve gerçek ProgramData hedefini kullanmaz; canlı UAC/kurum politikası kabulü ayrıdır. Gerçek yükseltme sonundaki eski önbellek temizliği yalnız hash eşleşen, tekrar indirilebilir model varlığıyla sınırlıdır; test kurulumu canlı önbelleği temizlemez. Otomatik rollback'in güç kesintisi senaryosu sınanmadı. Bu sınırlar genel “her donanımda sorunsuz” iddiasına dönüştürülmez.
