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

## Kalan risk

- İlk GERÇEK otomatik güncelleme, 0.7.0'dan SONRAKİ sürüm yayınlanınca
  yaşanır; bu turda canlı uçtan uca akış kanıtı olarak gerçek yayına karşı
  denetleme + indirme + açma + doğrulama kanıtlandı, swap mekaniği gerçek
  Windows süreçlerle ayrıca kanıtlandı (bkz. TESLIM-0.7.0.md).
- Program klasörü salt-okunur konumdaysa (Program Files'a elle kopya) taşıma
  başarısız olur; fallback devreye girer ve kullanıcı bilgilendirilir.

Durum: Uygulama tamam; davranış testleri 234/234, eval kapısı geçti.
