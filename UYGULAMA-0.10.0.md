# DeepFind 0.10.0 uygulama planı

Başlangıç: 21.10.2026, temel HEAD `9f51658`. Kullanıcı 21.10.2026 tarihinde inceleme raporundaki kapsamı onayladı. Harici yayın yetkisi verilmedi.

1. Resmî sürüme ve özete sabitlenmiş GGUF model / llama.cpp motorunu hazırla. Mevcut ONNX referansı ile Türkçe kalite karşılaştırması; Vulkan/CPU gerçek çalışma denemesi.
2. Tek paylaşılan model süreci, yerel tokenizer ve görünür GPU durumu; token temelli parçalama ve kontrollü vektör yenilemesi.
3. Bağımsız vektör adaylarını tam aramayla birleştir; filtre, dışlama ve birleşim sonrası sayfalama testleri.
4. Gemini ağ yollarını/arayüzünü ve kullanılmayan bağımlılıkları kaldır. OCR, önizleme, kasa ve otomatik tarama regresyonlarını doğrula.
5. Installer yükseltmesi, eski ZIP sürümünden geçiş, sürüm sabitli model dağıtımı, SHA doğrulama ve geri dönüş kapıları.
6. Tam test, paket/sentetik kullanıcı akışı, boyut/provenans kaydı, yerel commit + v0.10.0 etiketi. Gerçek AMD/NVIDIA/temiz Windows sınırlarını dürüstçe kaydet.

Önceki inceleme raporu uygulama öncesi tarihsel kanıttır. Canlı kasa veya kaynak belgelerde deneme yapılmaz. Eski yayın paketleri korunur. Başarılı gerçek kurulum yalnız özeti bilinen eski ONNX modelini temizler; test kurulumları bu temizliği çalıştırmaz. Yeni dağıtım eski embedding yolunu içermez.
