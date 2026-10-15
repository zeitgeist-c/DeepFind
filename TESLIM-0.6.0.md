# Evrakçı 0.6.0 — kurtarma anahtarı ve şifresiz kasa teslimi

Tarih: 15.10.2026. Kapsam: [DENETIM-0.6.0.md](DENETIM-0.6.0.md).

- Tam test paketi: **189 geçti**.
- Son ZIP içindeki gerçek EXE: **23 kontrol geçti**, ZIP CRC doğrulandı.
- Şifresiz kasa paketli EXE'de doğrulandı: şifre sorulmadan açıldı (`passwordless_open`),
  giriş diyaloğu hiç açılmadı; pencere "Evrakçı 0.6.0" başlığıyla göründü, kasa kilidi oluştu.
- EXE FileVersion/ProductVersion **0.6.0**; BAT aynı sürüm EXE'sini çalıştırır.
- `Evrakçı-0.6.0.zip`: **169.611.402 bayt**. SHA-256: `826768d306299c744d85a429f1142bf0adc36eeb18119aef8c7bb1f355f92f84`.
- Paketli pencerenin ekran görüntüsü incelendi: koyu tema düzgün, "Kasa açık", hata veya
  kilit/şifre diyaloğu yok.

Ham rapor: `build/package-check-0.6.0.json` (repo dışı).

Programı kapatın; ZIP'i tamamen yeni klasöre çıkarıp içindeki EXE/BAT'ı çalıştırın.
EXE ve `_internal` birlikte yenilenmelidir. Mevcut kasa yolu ve kayıtlar korunur.

Kurtarma anahtarı: Ayarlar → "Kurtarma anahtarı" bölümünden görüntülenir/yazdırılır.
Şifre unutulursa giriş ekranındaki "Şifremi unuttum" ile kasa yeni şifreyle açılır;
kaynak belgeler değişmez. Şifre kullanmayacaksanız ilk kurulumda alanı boş bırakmanız
veya "Şifre kullanmayacağım" seçeneğini işaretlemeniz yeterlidir; sonradan Ayarlar →
"Şifre ekle" ile şifre koyabilirsiniz.

Canlı Gemini, gerçek müşteri arşivi pilotu, gerçek Windows ekran ölçekleri ve temiz
Windows makinesi henüz doğrulanmadı. İlgisiz kullanıcı değişiklikleri (DURUM.md,
doc_adapter.py, ocr.py, ocr_setup.py, tests/test_durability.py, .hermes/) korunup
commit dışında bırakıldı. Yerel commit ve `v0.6.0` etiketi push'landı; GitHub Release
oluşturuldu, indirilen dosya birebir doğrulandı.
