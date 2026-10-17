# Evrakçı 0.7.0 — Güncelleme sistemi (denetim)

Tarih: 17.10.2026. Kapsam: kullanıcı isteği — Evrakçı'ya WordArc benzeri
kendi kendini güncelleme. WordArc'ın çalışan sistemi incelenip Evrakçı'nın
onedir (EXE + `_internal`) paket yapısına uyarlandı.

## Mimari

- Kaynak depo (`Evrakci`) özel kalır; paketler herkese açık
  `zeitgeist-c/Evrakci-Releases` deposunda yayınlanır. EXE içine kimlik
  bilgisi gömülmez; GitHub API herkese açık depolarda kimliksiz yanıt verir.
- Denetim: açılıştan 30 sn sonra günde bir sessiz + Ayarlar'dan elle.
  Damga kasada (`update_son_kontrol`); elle denetim güncel damgayı ezmez,
  her denetim sonucunda tazelenir.
- İndirme: `%LOCALAPPDATA%/Evrakci/Updates` alanına; boyut + SHA-256 yayın
  özetiyle doğrulanır. Hata/iptal → dosya silinir, asla çalıştırılmaz.
- Açma: ZIP hedef üst dizine açılır; Zip Slip koruması, kök klasör/EXE/
  `_internal`/manifest sürüm-PROGRAM çapraz kontrolü yapılır.
- Yerleşme: bekçi BAT, eski PID çıkışını bekler (System32 tasklist+find,
  en çok 300 sn), hazır klasörü çalışan EXE'nin yanına taşır, yeni EXE'yi
  `--restarted --kasa <yol>` ile başlatır, ZIP'i ve kendini siler. Taşıma
  başarısızsa (salt-okunur klasör) geçici kopyadan başlatır ve
  `son-guncelleme.txt`'ye `fallback` yazar; yeni sürüm açılışta duyurur.
- Eski program klasörü ve kasa silinmez (proje kuralı); kasa zaten
  AppData'da olduğundan güncellemeden etkilenmez.

## Kanıtlanan teknik riskler (ampirik test, scratch)

| Risk | Deney | Sonuç |
|---|---|---|
| UTF-8 BAT + unicode yollar (Evrakçı-…) | chcp 65001 + üst klasör `üst çğı` + move/start/del | Çalıştı, bat self-delete dahil |
| PID bekleme döngüsü | Kurban 6 sn yaşadı, BAT bekledi | 6,5/6,9 sn — bekleme doğrulandı |
| `timeout.exe` konsol gereği | CREATE_NO_WINDOW altında | Çalıştı; yine de `ping.exe` seçildi (konsol bağımsız, tam yol) |
| Görünmez çalışma | CREATE_NO_WINDOW | Konsol penceresi yok |
| System32 tam yolu | `%SystemRoot%\System32\tasklist/find/ping` | PATH kirliliğinden bağımsız (git-bash `find` gölgesi kapandı) |

## Bulgular ve düzeltmeler (geliştirme sırasında)

1. **Tasklist/find gölgelenmesi (P1).** Git-bash PATH'inde GNU `find`,
   Windows `find.exe`'yi gölgeleyebilir ve PID beklemesi hiç bitmez ya da
   hemen biter. Çözüm: BAT içinde tüm sistem araçları `%SystemRoot%\System32`
   tam yoluyla çağrılır. WordArc'ın çıplak `tasklist`/`find` desenine göre
   daha sağlam; kanıt scratch deneyinde.
2. **PID yeniden kullanımı (P2).** Eski PID başka sürece atanırsa bekleme
   uzayabilir. Çözüm: 300 sn üst sınır + süre dolunca yine ilerle (deadlock yok).
3. **Yarış: artık temizliği taze paketi silebilirdi (P2).** Açılışta Updates
   temizliği, değişim bekleyen paketi öldürebilirdi. Çözüm: `temizle` yalnız
   6 saatten eski öğeleri siler ve çalışılan klasöre dokunmaz; testli.
4. **Kaynak kopya koruması (P2).** Kaynak koddan çalıştırmada güncelleme
   denetimi kapalı ve açıklama görünür; sessiz/otomatik indirme yok. Testli.
5. **Varlık adı latinleşmesi (P3).** GitHub varlık adlarını latinleştirebilir
   (`Evrakçı` → `Evrakci`). `parse_release` iki yazımı da kabul eder; testli.
6. **Güvenlik testi istisnası.** `test_saf01_kaynaga_yazma_yok` kaynak tarama
   listesine `update.py`, `backup.py`/`recovery.py` ile aynı gerekçeyle
   eklendi: yalnız yönetilen yerel hedefe (`%LOCALAPPDATA%/Evrakci/Updates`)
   yazar; davranış kanıtı test_update.py runtime testleri.

## Kapanış denetimi ek bulguları (build sonrası tur, aynı sürümde yayın yenilendi)

7. **Worker ebeveynsiz olmalıydı (P1).** `GuncellemeIsci(parent=self)` ile
   üretilince Qt `moveToThread` çağrısı etkisiz kalır ve ağ işi GUI
   thread'inde donar. Çözüm: işçi ebeveynsiz; yaşam süresi pencere
   referansıyla yönetilir ve `thread.finished` ile `deleteLater` bağlanır.
   (offscreen Qt ile gerçek iptal akışı kanıtı alındı.)
8. **İptal edilen indirme thread'i kapatmıyordu (P1).** İşçi "iptal"
   durumunda sinyal göndermeden döner; thread hiç durmaz ve `temizle`
   çalışmaz → düğmeler kalıcı kilitlenir. Çözüm: iptal yolunda
   `thread.quit()` çağrılır. Gerçek yavaş indirme (yerel HTTP, ~1,7 MB/sn)
   üzerinde kanıtlandı: 2 MB inerken iptal → thread kapandı, yarım dosya
   silindi, mesaj düğmelere döndü.
9. **Swap kurulamazsa uygulama yine kapanıyordu (P2).** `spawn_swap`
   OSError atarsa pencere yine de kapanıyordu → güncelleme yok, program
   kapalı. Çözüm: hata yakalanır, kullanıcıya gösterilir, uygulama açık
   kalır; testli.
10. **Başarısız açma kalıntı bırakıyordu (P2).** Manifest/ZIP doğrulaması
    düşünce yarım klasör ve ZIP diskte kalıyordu. Çözüm: `extract_zip` ve
    `prepare` her hata yolunda açılmış klasörü ve ZIP'i temizler; testli.
11. **Açılış kaydı eski klasörü gösteriyordu (P2).** Güncelleme yeni
    klasöre taşındıktan sonra HKCU Run kaydı eski yolu gösterir; makine bir
    sonraki açılışta eski sürümü başlatırdı. Çözüm:
    `sched.autostart_guncelle` — kayıt varsa çalışan yola tazeler, kapalı
    kaydı açmaz; testli.

**Yayın notu:** İlk paket (SHA `1d8101ea…`) build sonrası eklenen 7–11
düzeltmelerini içermiyordu; yayın açıldıktan sonra, kimse indirmeden önce
fark edildi. Tüm düzeltmeler alındıktan sonra paket aynı sürümde yeniden
üretildi; güncel paket özeti `TESLIM-0.7.0.md`'de. Etiket ve her iki
depodaki yayın varlıkları bu son pakete göre güncellendi.

Durum: Uygulama tamam; davranış testleri 237/237, eval kapısı geçti,
paketli EXE smoke 25/25.
