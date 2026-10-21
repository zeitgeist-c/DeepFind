# 0.10.1 kurulum ve güncelleme

Kullanıcı talebi (21.10.2026): kurulu uygulama aynı Program Files dizininde güncellensin; embedding modeli kurulumla aynı dizine yerleşsin; eski EXE/BAT birikmesin. Düzeltmeler 0.10.1, 0.10.2, 0.10.3 şeklinde ilerler.

1. Tam kurulum modeli çevrimdışı `{app}/_internal/embedding` içine yerleştirir ve SHA-256 ile doğrular. Küçük güncelleme mevcut yerel veya eski ProgramData modelini doğrular; gerekirse eski modeli kurulum içinde taşır. Eksik/bozuk modelde tam paket seçilir.
2. Güncelleyici kurulum dizinini bulur, işlem kapanmasını bekler, UAC ile Inno çalıştırır; başarılı yeni sürüm yeniden açılır. Kurulu düzende ZIP klasör taşıma yoluna düşülmez. Sonuç kaydı başarı/hata bilgisini gösterir.
3. Başarılı installer yalnız doğrulanmış eski uygulama sürümü EXE/BAT dosyalarını temizler. Kasa, belgeler ve yedekler korunur.
4. Hedefli testler, tam regresyon, gerçek paket ve izole Inno yükseltme/model onarma/eksik model/temizlik kabulü; ardından yerel commit/etiket ve temiz kaynaktan son paket.

GitHub yayını ayrı yetki gerektirir. Canlı kurulum ve kullanıcı kasası test hedefi değildir.
