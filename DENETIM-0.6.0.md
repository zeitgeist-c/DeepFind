# Evrakçı 0.6.0 — Kurtarma anahtarı ve şifresiz kasa

Tarih: 15.10.2026. Kaynak: kullanıcı istekleri — (1) şifre unutulduğunda indeks kaybını
önleyen kurtarma anahtarı, (2) ilk kurulumda şifresiz kullanım (şifre alanı boş
bırakılabilir).

## Kurtarma anahtarı (yeni)

- Format `EVKC-XXXXX-…` (160 bit, base32; karışan I/L/O/U ve 0/1 alfabede yok; boşluk ve
  küçük harf toleranslı okunur).
- Kasa klasöründe şifreli SQLCipher konteyneri (`evrakci-kurtarma.kurtarma.db`) +
  yazdırılabilir belge (`evrakci-kurtarma.anahtar`). Kullanıcıya Ayarlar → "Kurtarma
  anahtarı" bölümünden gösterilir, yazdırılır veya dosyaya kaydedilir.
- Girişte "Şifremi unuttum": anahtar + yeni şifre → kasa yeni şifreyle açılır, yeni
  anahtar üretilir; eski şifre ve eski anahtar geçersizleşir. Kaynak belgelere dokunulmaz.
- Şifre değişiminde anahtar kendiliğinden tazelenir; şifre eklenince kendiliğinden üretilir.
- Yanlış anahtar temiz reddedilir, kasa bozulmaz. Konteyner sırsız doğrulandı: kasa
  şifresi ve dosya yolları açık metin değil, boyut 200 KB altında.

## Şifresiz kasa (yeni)

- **Kritik teknik bulgu:** SQLCipher boş anahtarı reddediyor ("PRAGMA key requires a key
  of one or more characters"). Bu yüzden şifresiz kasa sabit bir iç anahtarla
  (`vault.SIFRESIZ_ANAHTAR`) açılır; işaret `settings.kasa_sifresiz`. Kullanıcıya hiç
  sorulmaz; görünür davranış "şifre yok".
- İlk kurulumda şifre alanı boş bırakılır veya "Şifre kullanmayacağım" işaretlenir.
- Sonraki açılışlar doğrudan olur; kilit ekranı hiç görünmez, ana pencerede
  "Kasayı kilitle" eylemi ve oturum kilidi (elle/otomatik/uyku) devre dışıdır.
- Ayarlar → "Şifre ekle": rekey + işaret güncelleme + kurtarma anahtarı üretimi;
  izleyen açılışlarda şifre sorulur. Hatalı denemede kasa şifresiz hâlinde korunur.
- CLI şifresiz kasayı sormadan açar. Yedekler iç anahtarla alınır; şifreye geçildikten
  sonra eski (iç anahtarlı) yedekler geri yüklemede otomatik tanınır.
- Koruma düzeyi açıkça: uygulama şifresi yok; korumayı Windows hesabı ve disk
  şifrelemesi sağlar. Kasada şifre sorulmadığı için kurtarma anahtarı üretilmez
  (kurtarılacak şifre yok); şifre eklenince otomatik üretilir.

## Düzeltmeler (önceki turdan)

- Giriş ekranında "Şifremi unuttum → Şifremi biliyorum" artık uygulamayı kapatmıyor;
  giriş ekranına dönüyor.
- İlk kurulumda sessizce üretilen kurtarma anahtarı artık bir kez bildiriliyor
  (toast + durum çubuğu; engelleyici diyalog yok).

## Ölçülen garantiler

- Tam test paketi: **189 geçti** (öncesi 183; +6 şifresiz kasa testi).
- Uçtan uca şifresiz akış: **20/20 kontrol** (kurulum → şifresiz açılış → CLI →
  yedek → "Şifre ekle" → dönüşüm öncesi yedek kurtarma).
- Kurtarma uçtan uca: yanlış anahtar reddi, doğru anahtarla kurtarma, eski şifre/anahtar
  geçersizliği, otomatik tazeleme; kaynak belgelerin değişmediği bayt düzeyinde doğrulandı.
- Kaynaktan gerçek uygulama dumansı: yaşam döngüsü kaydında `passwordless_open` var,
  `login_dialog` yok; pencere açıldı (`main_window_ready`).
- Paket kontrolleri: 23 smoke kontrolü + EXE FileVersion/ProductVersion + paket DLL +
  gerçek pencere testi (ayrıntı: TESLIM-0.6.0.md).

## Sınırlar

- Canlı Gemini, gerçek müşteri arşivi pilotu, gerçek DPI ölçekleri ve temiz Windows
  makinesi bu sürümde de doğrulanmadı (kullanıcı ortamında denenecek).
- Şifresiz kasada koruma Windows hesabı düzeyindedir; disk şifrelemesi önerilir.
- Ağaçtaki ilgisiz kullanıcı değişiklikleri (DURUM.md, doc_adapter.py, ocr.py,
  ocr_setup.py, tests/test_durability.py, .hermes/) korunup commit dışında bırakıldı.
