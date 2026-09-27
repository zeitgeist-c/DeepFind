# Evrakçı 0.1.5 teslim kaydı

Tarih: 28.09.2026.

13 isteğin uygulaması ve madde bazlı kanıtları: DENETIM-0.1.5.md.
Tepsi animasyonu uygulandı ve gerçek Windows olay döngüsünde doğrulandı; gizli tepsi alanındaki görsel kabul henüz tamam değil. %125/%150 gerçek DPI oturumları doğrulanmadı; ölçek benzetimleri geçti.

Paket adları: Evrakçı-0.1.5.zip, paket içindeki Evrakçı-0.1.5.exe ve Evrakçı-0.1.5.bat. BAT aynı isimli EXE’yi çalıştırır. EXE tek başına taşınabilir tek dosya değildir; ZIP içindeki _internal klasörü gerekir.

Son test ve paket hash bilgisi doğrulama tamamlanınca eklenir.
Yerel sürüm etiketi: v0.1.5. Commit kimliği teslim yanıtında/git geçmişinde belirtilir.
GitHub push, Release veya deployment yapılmaz.
Kullanıcıya ait tests/test_durability.py değişikliği çalışma ağacında korunur.

## Nihai doğrulama

- Son tam test: **79 geçti** (122.02 saniye).
- Son ZIP içindeki gerçek EXE: **13 paket kontrolü geçti**; CRC ve sürüm/manifest/BAT hedefi doğrulandı.
- ZIP SHA-256: c924847a05f1be6cc6471c11cf97b1dce021422110794e34133720d698cf213f.
- Paket boyutu: 57.912.179 bayt.
- 12 maddenin kabulü tamam; 12 numaralı tepsi animasyonu kod ve gerçek Windows davranışı olarak doğrulandı, fakat gizli tepsi alanındaki görsel kabul bekler. Tüm 13 maddenin kabulü tamamlandı iddiası yapılmaz.
