"""Extra UI tables for the setup/engine/language work (part 1: en, de, es, fr, it, pt-BR).

Keys are the Turkish source strings, exactly as used in the code. Anything
missing here falls back to Turkish, which is what the audit tool reports.
"""

EN = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "A language change takes effect on the next start.",
    "Çalışma motoru": "Compute engine",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "The choice is saved and the engine restarts.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Language saved: {language}. The new language takes effect on the next start.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Engine saved: {motor}. It restarts with the next search.",
    "Görünüm ve dil": "Appearance and language",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menus, buttons and messages are shown in this language.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Which unit runs semantic search.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Recommended: automatic (graphics card, otherwise processor)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Tries the graphics card; if it is unsuitable, search moves to the processor.",
    "Yalnız işlemci (CPU)": "Processor only (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Works on every computer; slower on machines with a graphics card.",
    "Ekran kartı (Vulkan)": "Graphics card (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Without a suitable card or driver, search does not start.",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA graphics card (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Optional component; unusable until it is downloaded.",
    "kurulu değil": "not installed",
    "kurulu": "installed",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Press “Scan now” to start the first scan.",
    "Geri": "Back",
    "En az 12 karakter": "At least 12 characters",
    "Eklenen klasörler • {count}": "Added folders • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "Semantic search runs on this computer. The recommended option tries the fastest unit and falls back safely to the processor.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "“Finish setup” opens your workspace; you start the first scan from the Scan page.",
    "Açık tema": "Light theme",
    "Koyu tema": "Dark theme",
    "Son kontrol": "Final check",
    "Nasıl çalışsın?": "How should it run?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "It tries the graphics card. If the card is unsuitable, search moves to the processor; the status area shows which unit is used.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Works on every computer. Slower on systems with a graphics card.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Uses the graphics card on Windows. Without a suitable card or driver, search does not start.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "The fastest option on NVIDIA cards. Unusable until the optional component is downloaded.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "You can change this choice later in Settings.",
    "Otomatik": "Automatic",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "If the graphics card attempt fails, search continues on the processor; the status area shows which unit is used.",
    "Tema": "Theme",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "About 663 MB. You can download it from Settings.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "The CUDA component is not downloaded yet. You can download it from Settings after setup.",
    "yaklaşık {size} MB, indirilebilir": "about {size} MB, downloadable",
    "Motor": "Engine",
    "Kök: {count} adet\n": "Roots: {count}\n",
    'Saatli taramayı etkinleştir': 'Enable scheduled scanning',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Runs only while the app is open at this time; missed scans are never started later.',
    'Saatli tarama etkinken geçerlidir.': 'Used when scheduled scanning is on.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'The scheduled scan time arrived while another scan was running; no second scan was started.',
    'Anlamsal arama modelini indir (~296 MB)': 'Download the semantic search model (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'The model is required for offline search; it downloads once.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'I accept the model license (Apache-2.0)',
    'İndirmeyi başlat': 'Start download',
    'Model indiriliyor…': 'Downloading model…',
    'Model indirildi ve doğrulandı.': 'Model downloaded and verified.',
    'İndirme tamamlanamadı.': 'Download failed.',
    'İndirme iptal edildi.': 'Download cancelled.',
    'Model hazır.': 'Model ready.',
    'Yeniden dene': 'Retry',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Watched folders changed; press “Scan now” to update.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "This backup is in the old encrypted format; enter the backup password:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Applies when scheduled scan is on; runs at the time you chose.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Notifies you of changes; never starts a scan by itself.",
    "Kasa": "Vault",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "The vault on this computer opens without a password; there is no login, lock or recovery key.",
    "Yerel çalışır; kasa şifresizdir": "Runs locally; vault is password-free",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Setting up the password-free vault. DeepFind will open by itself when done.",
    "Eski şifreli kasa": "Old encrypted vault",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "This vault is in the old encrypted format. Enter the current password to convert it:",
    "Şifresiz kasa": "Password-free vault",
    "Kapat": "Close",
    "Kasa açılıyor…": "Opening vault…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Your source documents are kept.\nSearch data stays on this computer.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Your search data stays on this computer; there is no login password.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "CUDA engine was not found in this installation; repair the installation.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Your search data stays on this computer.",
    "Kasa: şifresiz\n": "Vault: password-free\n",
    "Dosya türleri": "File types",
    "Bu taramada işleme alınacak türler. Kapalı türdeki eski belgeler korunur.":
        "Types processed in this scan. Older documents of switched-off types are kept.",
    "Tüm türler": "All types",
    "Tüm dosya türlerine dön": "Back to all file types",
    "{secili} / {toplam} tür seçili": "{secili} / {toplam} types selected",
    "Dosya türü {tur}": "File type {tur}",
    "Kompakt": "Compact",
    "Izgara": "Grid",
    "Sayfa": "Page",
    "Hiç dosya türü seçili değil. Taramayı başlatmak için Tarama ekranından en az bir türü işaretleyin.":
        "No file type selected. Tick at least one type on the Scan page to start scanning.",
    "Pencerenin açık, koyu veya sistem görünümü. Üst çubuktaki seçimle aynıdır.":
        "Light, dark or system look of the window. Same as the top-bar choice.",
}

DE = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "Eine Sprachänderung wirkt beim nächsten Start.",
    "Çalışma motoru": "Rechenmodul",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "Die Auswahl wird gespeichert und das Modul neu gestartet.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Sprache gespeichert: {language}. Die neue Sprache wirkt beim nächsten Start.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Modul gespeichert: {motor}. Es startet bei der nächsten Suche neu.",
    "Görünüm ve dil": "Darstellung und Sprache",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menüs, Schaltflächen und Meldungen erscheinen in dieser Sprache.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Welche Einheit die semantische Suche ausführt.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Empfohlen: automatisch (Grafikkarte, sonst Prozessor)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Versucht die Grafikkarte; ist sie ungeeignet, läuft die Suche auf dem Prozessor.",
    "Yalnız işlemci (CPU)": "Nur Prozessor (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Läuft auf jedem Computer; langsamer auf Geräten mit Grafikkarte.",
    "Ekran kartı (Vulkan)": "Grafikkarte (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Ohne passende Karte oder Treiber startet die Suche nicht.",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA-Grafikkarte (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Optionales Paket; ohne Download nicht nutzbar.",
    "kurulu değil": "nicht installiert",
    "kurulu": "installiert",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Drücken Sie „Jetzt scannen“, um den ersten Scan zu starten.",
    "Geri": "Zurück",
    "En az 12 karakter": "Mindestens 12 Zeichen",
    "Eklenen klasörler • {count}": "Hinzugefügte Ordner • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "Die semantische Suche läuft auf diesem Computer. Die empfohlene Option versucht die schnellste Einheit und weicht sicher auf den Prozessor aus.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "„Setup abschließen“ öffnet Ihren Arbeitsbereich; den ersten Scan starten Sie auf der Seite „Scan“.",
    "Açık tema": "Helles Design",
    "Koyu tema": "Dunkles Design",
    "Son kontrol": "Letzte Prüfung",
    "Nasıl çalışsın?": "Wie soll es laufen?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Es versucht die Grafikkarte. Ist sie ungeeignet, läuft die Suche auf dem Prozessor; das Statusfeld zeigt die genutzte Einheit.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Läuft auf jedem Computer. Langsamer auf Systemen mit Grafikkarte.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Nutzt unter Windows die Grafikkarte. Ohne passende Karte oder Treiber startet die Suche nicht.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "Schnellste Option auf NVIDIA-Karten. Ohne Download des optionalen Pakets nicht nutzbar.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Sie können die Auswahl später in den Einstellungen ändern.",
    "Otomatik": "Automatisch",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Scheitert der Versuch mit der Grafikkarte, läuft die Suche auf dem Prozessor weiter; das Statusfeld zeigt die genutzte Einheit.",
    "Tema": "Design",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Etwa 663 MB. Download in den Einstellungen möglich.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Das CUDA-Paket ist noch nicht geladen. Nach der Installation können Sie es in den Einstellungen herunterladen.",
    "yaklaşık {size} MB, indirilebilir": "etwa {size} MB, herunterladbar",
    "Motor": "Modul",
    "Kök: {count} adet\n": "Wurzeln: {count}\n",
    'Saatli taramayı etkinleştir': 'Zeitgesteuerte Überprüfung aktivieren',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Läuft nur, wenn die App zu dieser Zeit geöffnet ist; verpasste Überprüfungen werden nicht nachgeholt.',
    'Saatli tarama etkinken geçerlidir.': 'Gilt, wenn die zeitgesteuerte Überprüfung aktiv ist.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Der Zeitpunkt der geplanten Überprüfung ist erreicht, aber eine andere Überprüfung läuft; es wurde keine zweite Überprüfung gestartet.',
    'Anlamsal arama modelini indir (~296 MB)': 'Semantisches Suchmodell herunterladen (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Das Modell ist für die Offline-Suche erforderlich; einmaliger Download.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Ich akzeptiere die Modelllizenz (Apache-2.0)',
    'İndirmeyi başlat': 'Download starten',
    'Model indiriliyor…': 'Modell wird heruntergeladen…',
    'Model indirildi ve doğrulandı.': 'Modell heruntergeladen und geprüft.',
    'İndirme tamamlanamadı.': 'Download fehlgeschlagen.',
    'İndirme iptal edildi.': 'Download abgebrochen.',
    'Model hazır.': 'Modell bereit.',
    'Yeniden dene': 'Wiederholen',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Überwachte Ordner geändert; zum Aktualisieren „Jetzt scannen“ drücken.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Diese Sicherung liegt im alten verschlüsselten Format vor; Sicherungspasswort eingeben:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Gilt bei aktiviertem Zeitplan; läuft zur gewählten Uhrzeit.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Meldet Änderungen; startet nie selbst einen Scan.",
    "Kasa": "Tresor",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "Der Tresor auf diesem Computer öffnet ohne Passwort; es gibt keine Anmeldung, Sperre oder Wiederherstellungsschlüssel.",
    "Yerel çalışır; kasa şifresizdir": "Läuft lokal; Tresor ist passwortfrei",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Passwortfreier Tresor wird eingerichtet. DeepFind öffnet sich danach von selbst.",
    "Eski şifreli kasa": "Alter verschlüsselter Tresor",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Dieser Tresor liegt im alten verschlüsselten Format vor. Zum Umwandeln das aktuelle Passwort eingeben:",
    "Şifresiz kasa": "Passwortfreier Tresor",
    "Kapat": "Schließen",
    "Kasa açılıyor…": "Tresor wird geöffnet…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Ihre Quelldokumente bleiben erhalten.\nSuchdaten bleiben auf diesem Computer.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Ihre Suchdaten bleiben auf diesem Computer; es gibt kein Anmeldepasswort.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "CUDA-Engine in dieser Installation nicht gefunden; Installation reparieren.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Ihre Suchdaten bleiben auf diesem Computer.",
    "Kasa: şifresiz\n": "Tresor: passwortfrei\n",
    "Dosya türleri": "Dateitypen",
    "Bu taramada işleme alınacak türler. Kapalı türdeki eski belgeler korunur.":
        "In diesem Scan verarbeitete Typen. Ältere Dokumente abgeschalteter Typen bleiben erhalten.",
    "Tüm türler": "Alle Typen",
    "Tüm dosya türlerine dön": "Zurück zu allen Dateitypen",
    "{secili} / {toplam} tür seçili": "{secili} / {toplam} Typen ausgewählt",
    "Dosya türü {tur}": "Dateityp {tur}",
    "Kompakt": "Kompakt",
    "Izgara": "Raster",
    "Sayfa": "Seite",
    "Hiç dosya türü seçili değil. Taramayı başlatmak için Tarama ekranından en az bir türü işaretleyin.":
        "Kein Dateityp ausgewählt. Zum Start mindestens einen Typ auf der Scan-Seite anhaken.",
    "Pencerenin açık, koyu veya sistem görünümü. Üst çubuktaki seçimle aynıdır.":
        "Helles, dunkles oder System-Aussehen des Fensters. Wie die Auswahl in der oberen Leiste.",
}

ES = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "El cambio de idioma se aplica en el próximo inicio.",
    "Çalışma motoru": "Motor de cálculo",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "La elección se guarda y el motor se reinicia.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Idioma guardado: {language}. El nuevo idioma se aplica en el próximo inicio.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Motor guardado: {motor}. Se reinicia en la próxima búsqueda.",
    "Görünüm ve dil": "Apariencia e idioma",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Los menús, botones y mensajes se muestran en este idioma.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Qué unidad ejecuta la búsqueda semántica.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Recomendado: automático (tarjeta gráfica; si no, procesador)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Prueba la tarjeta gráfica; si no es apta, la búsqueda pasa al procesador.",
    "Yalnız işlemci (CPU)": "Solo procesador (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Funciona en cualquier equipo; más lento en equipos con tarjeta gráfica.",
    "Ekran kartı (Vulkan)": "Tarjeta gráfica (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Sin una tarjeta o controlador adecuado, la búsqueda no se inicia.",
    "NVIDIA ekran kartı (CUDA)": "Tarjeta gráfica NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Componente opcional; no se puede usar sin descargarlo.",
    "kurulu değil": "no instalado",
    "kurulu": "instalado",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Pulse «Analizar ahora» para iniciar el primer análisis.",
    "Geri": "Atrás",
    "En az 12 karakter": "Al menos 12 caracteres",
    "Eklenen klasörler • {count}": "Carpetas añadidas • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "La búsqueda semántica se ejecuta en este equipo. La opción recomendada prueba la unidad más rápida y recurre al procesador si falla.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "«Terminar instalación» abre su espacio de trabajo; usted inicia el primer análisis desde la página Análisis.",
    "Açık tema": "Tema claro",
    "Koyu tema": "Tema oscuro",
    "Son kontrol": "Comprobación final",
    "Nasıl çalışsın?": "¿Cómo debe ejecutarse?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Prueba la tarjeta gráfica. Si no es apta, la búsqueda pasa al procesador; el área de estado indica qué unidad se usa.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Funciona en cualquier equipo. Más lento en sistemas con tarjeta gráfica.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Usa la tarjeta gráfica en Windows. Sin tarjeta o controlador adecuado, la búsqueda no se inicia.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "La opción más rápida en tarjetas NVIDIA. No se puede usar sin descargar el componente opcional.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Puede cambiar esta elección más tarde en Ajustes.",
    "Otomatik": "Automático",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Si falla el intento con la tarjeta gráfica, la búsqueda continúa en el procesador; el área de estado indica qué unidad se usa.",
    "Tema": "Tema",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Unos 663 MB. Puede descargarlo desde Ajustes.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "El componente CUDA aún no se ha descargado. Puede descargarlo desde Ajustes tras la instalación.",
    "yaklaşık {size} MB, indirilebilir": "unos {size} MB, descargable",
    "Motor": "Motor",
    "Kök: {count} adet\n": "Raíces: {count}\n",
    'Saatli taramayı etkinleştir': 'Activar el análisis programado',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Solo se ejecuta si la aplicación está abierta a esta hora; los análisis omitidos no se inician después.',
    'Saatli tarama etkinken geçerlidir.': 'Se aplica cuando el análisis programado está activado.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Llegó la hora del análisis programado pero hay otro análisis en curso; no se inició un segundo análisis.',
    'Anlamsal arama modelini indir (~296 MB)': 'Descargar el modelo de búsqueda semántica (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'El modelo es necesario para la búsqueda sin conexión; se descarga una vez.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Acepto la licencia del modelo (Apache-2.0)',
    'İndirmeyi başlat': 'Iniciar descarga',
    'Model indiriliyor…': 'Descargando el modelo…',
    'Model indirildi ve doğrulandı.': 'Modelo descargado y verificado.',
    'İndirme tamamlanamadı.': 'Descarga fallida.',
    'İndirme iptal edildi.': 'Descarga cancelada.',
    'Model hazır.': 'Modelo listo.',
    'Yeniden dene': 'Reintentar',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Hay cambios en las carpetas vigiladas; pulse «Escanear ahora» para actualizar.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Esta copia está en el formato cifrado antiguo; introduzca la contraseña de la copia:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Válido con el escaneo programado activado; se ejecuta a la hora elegida.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Avisa de los cambios; nunca inicia un escaneo por sí solo.",
    "Kasa": "Caja fuerte",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "La caja fuerte de este equipo se abre sin contraseña; no hay inicio de sesión, bloqueo ni clave de recuperación.",
    "Yerel çalışır; kasa şifresizdir": "Funciona en local; caja fuerte sin contraseña",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Configurando la caja fuerte sin contraseña. DeepFind se abrirá solo al terminar.",
    "Eski şifreli kasa": "Caja fuerte cifrada antigua",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Esta caja fuerte está en el formato cifrado antiguo. Introduzca la contraseña actual para convertirla:",
    "Şifresiz kasa": "Caja fuerte sin contraseña",
    "Kapat": "Cerrar",
    "Kasa açılıyor…": "Abriendo la caja fuerte…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Sus documentos fuente se conservan.\nLos datos de búsqueda quedan en este equipo.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Sus datos de búsqueda quedan en este equipo; no hay contraseña de acceso.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Motor CUDA no encontrado en esta instalación; repare la instalación.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Sus datos de búsqueda quedan en este equipo.",
    "Kasa: şifresiz\n": "Caja fuerte: sin contraseña\n",
}

FR = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "Le changement de langue prend effet au prochain démarrage.",
    "Çalışma motoru": "Moteur de calcul",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "Le choix est enregistré et le moteur redémarre.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Langue enregistrée : {language}. La nouvelle langue prend effet au prochain démarrage.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Moteur enregistré : {motor}. Il redémarre à la prochaine recherche.",
    "Görünüm ve dil": "Apparence et langue",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Les menus, boutons et messages s'affichent dans cette langue.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "L'unité qui exécute la recherche sémantique.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Recommandé : automatique (carte graphique, sinon processeur)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Essaie la carte graphique ; si elle est inadaptée, la recherche passe au processeur.",
    "Yalnız işlemci (CPU)": "Processeur uniquement (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Fonctionne partout ; plus lent sur les machines dotées d'une carte graphique.",
    "Ekran kartı (Vulkan)": "Carte graphique (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Sans carte ni pilote adapté, la recherche ne démarre pas.",
    "NVIDIA ekran kartı (CUDA)": "Carte graphique NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Composant facultatif ; inutilisable tant qu'il n'est pas téléchargé.",
    "kurulu değil": "non installé",
    "kurulu": "installé",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Appuyez sur « Scanner » pour lancer la première analyse.",
    "Geri": "Retour",
    "En az 12 karakter": "Au moins 12 caractères",
    "Eklenen klasörler • {count}": "Dossiers ajoutés • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "La recherche sémantique s'exécute sur cet ordinateur. L'option recommandée essaie l'unité la plus rapide, puis revient au processeur en sécurité.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "« Terminer l'installation » ouvre votre espace de travail ; vous lancez la première analyse depuis la page Analyse.",
    "Açık tema": "Thème clair",
    "Koyu tema": "Thème sombre",
    "Son kontrol": "Vérification finale",
    "Nasıl çalışsın?": "Comment doit-il s'exécuter ?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Il essaie la carte graphique. Si elle est inadaptée, la recherche passe au processeur ; la zone d'état indique l'unité utilisée.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Fonctionne partout. Plus lent sur les systèmes dotés d'une carte graphique.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Utilise la carte graphique sous Windows. Sans carte ni pilote adapté, la recherche ne démarre pas.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "L'option la plus rapide sur les cartes NVIDIA. Inutilisable tant que le composant facultatif n'est pas téléchargé.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Vous pouvez modifier ce choix plus tard dans les Paramètres.",
    "Otomatik": "Automatique",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Si l'essai sur la carte graphique échoue, la recherche continue sur le processeur ; la zone d'état indique l'unité utilisée.",
    "Tema": "Thème",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Environ 663 Mo. Téléchargeable depuis les Paramètres.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Le composant CUDA n'est pas encore téléchargé. Vous pouvez le faire depuis les Paramètres après l'installation.",
    "yaklaşık {size} MB, indirilebilir": "environ {size} Mo, téléchargeable",
    "Motor": "Moteur",
    "Kök: {count} adet\n": "Racines : {count}\n",
    'Saatli taramayı etkinleştir': 'Activer l’analyse planifiée',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Ne s’exécute que si l’application est ouverte à cette heure ; les analyses manquées ne sont pas relancées plus tard.',
    'Saatli tarama etkinken geçerlidir.': 'S’applique lorsque l’analyse planifiée est activée.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'L’heure de l’analyse planifiée est arrivée mais une autre analyse est en cours ; aucune seconde analyse n’a été lancée.',
    'Anlamsal arama modelini indir (~296 MB)': 'Télécharger le modèle de recherche sémantique (~296 Mo)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Le modèle est requis pour la recherche hors ligne ; un seul téléchargement.',
    'Model lisansını (Apache-2.0) kabul ediyorum': "J'accepte la licence du modèle (Apache-2.0)",
    'İndirmeyi başlat': 'Démarrer le téléchargement',
    'Model indiriliyor…': 'Téléchargement du modèle…',
    'Model indirildi ve doğrulandı.': 'Modèle téléchargé et vérifié.',
    'İndirme tamamlanamadı.': 'Échec du téléchargement.',
    'İndirme iptal edildi.': 'Téléchargement annulé.',
    'Model hazır.': 'Modèle prêt.',
    'Yeniden dene': 'Réessayer',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Dossiers surveillés modifiés ; cliquez sur « Analyser » pour mettre à jour.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Cette sauvegarde utilise l’ancien format chiffré ; saisissez son mot de passe :",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Valable quand l’analyse planifiée est active ; s’exécute à l’heure choisie.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Signale les changements ; ne lance jamais d’analyse tout seul.",
    "Kasa": "Coffre",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "Le coffre de cet ordinateur s’ouvre sans mot de passe ; ni connexion, ni verrou, ni clé de récupération.",
    "Yerel çalışır; kasa şifresizdir": "Fonctionne en local ; coffre sans mot de passe",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Coffre sans mot de passe en cours de création. DeepFind s’ouvrira tout seul à la fin.",
    "Eski şifreli kasa": "Ancien coffre chiffré",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Ce coffre utilise l’ancien format chiffré. Saisissez le mot de passe actuel pour le convertir :",
    "Şifresiz kasa": "Coffre sans mot de passe",
    "Kapat": "Fermer",
    "Kasa açılıyor…": "Ouverture du coffre…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Vos documents sources sont conservés.\nLes données de recherche restent sur cet ordinateur.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Vos données de recherche restent sur cet ordinateur ; aucun mot de passe de connexion.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Moteur CUDA introuvable dans cette installation ; réparez l’installation.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Vos données de recherche restent sur cet ordinateur.",
    "Kasa: şifresiz\n": "Coffre : sans mot de passe\n",
}

IT = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "La modifica della lingua ha effetto al prossimo avvio.",
    "Çalışma motoru": "Motore di calcolo",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "La scelta viene salvata e il motore si riavvia.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Lingua salvata: {language}. La nuova lingua ha effetto al prossimo avvio.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Motore salvato: {motor}. Si riavvia alla prossima ricerca.",
    "Görünüm ve dil": "Aspetto e lingua",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menu, pulsanti e messaggi sono mostrati in questa lingua.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Quale unità esegue la ricerca semantica.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Consigliato: automatico (scheda grafica, altrimenti processore)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Prova la scheda grafica; se non è adatta, la ricerca passa al processore.",
    "Yalnız işlemci (CPU)": "Solo processore (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Funziona su ogni computer; più lento sui sistemi con scheda grafica.",
    "Ekran kartı (Vulkan)": "Scheda grafica (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Senza scheda o driver adatti la ricerca non parte.",
    "NVIDIA ekran kartı (CUDA)": "Scheda grafica NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Componente facoltativo; inutilizzabile finché non viene scaricato.",
    "kurulu değil": "non installato",
    "kurulu": "installato",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Premere «Analizza ora» per avviare la prima analisi.",
    "Geri": "Indietro",
    "En az 12 karakter": "Almeno 12 caratteri",
    "Eklenen klasörler • {count}": "Cartelle aggiunte • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "La ricerca semantica viene eseguita su questo computer. L'opzione consigliata prova l'unità più veloce e torna al processore in sicurezza.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "«Termina installazione» apre lo spazio di lavoro; la prima analisi si avvia dalla pagina Analisi.",
    "Açık tema": "Tema chiaro",
    "Koyu tema": "Tema scuro",
    "Son kontrol": "Controllo finale",
    "Nasıl çalışsın?": "Come deve funzionare?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Prova la scheda grafica. Se non è adatta, la ricerca passa al processore; l'area di stato mostra l'unità in uso.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Funziona su ogni computer. Più lento sui sistemi con scheda grafica.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Usa la scheda grafica su Windows. Senza scheda o driver adatti la ricerca non parte.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "L'opzione più rapida sulle schede NVIDIA. Inutilizzabile finché il componente facoltativo non è scaricato.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Puoi modificare questa scelta in seguito nelle Impostazioni.",
    "Otomatik": "Automatico",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Se il tentativo con la scheda grafica fallisce, la ricerca continua sul processore; l'area di stato mostra l'unità in uso.",
    "Tema": "Tema",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Circa 663 MB. Scaricabile dalle Impostazioni.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Il componente CUDA non è ancora scaricato. Puoi scaricarlo dalle Impostazioni dopo l'installazione.",
    "yaklaşık {size} MB, indirilebilir": "circa {size} MB, scaricabile",
    "Motor": "Motore",
    "Kök: {count} adet\n": "Radici: {count}\n",
    'Saatli taramayı etkinleştir': 'Attiva la scansione pianificata',
    "Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.": "Viene eseguita solo se l'app è aperta a quest'ora; le scansioni perse non vengono avviate in seguito.",
    'Saatli tarama etkinken geçerlidir.': 'Si applica quando la scansione pianificata è attiva.',
    "Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.": "È arrivata l'ora della scansione pianificata ma è in corso un'altra scansione; non è stata avviata una seconda scansione.",
    'Anlamsal arama modelini indir (~296 MB)': 'Scarica il modello di ricerca semantica (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Il modello è necessario per la ricerca offline; si scarica una volta sola.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Accetto la licenza del modello (Apache-2.0)',
    'İndirmeyi başlat': 'Avvia download',
    'Model indiriliyor…': 'Download del modello in corso…',
    'Model indirildi ve doğrulandı.': 'Modello scaricato e verificato.',
    'İndirme tamamlanamadı.': 'Download non riuscito.',
    'İndirme iptal edildi.': 'Download annullato.',
    'Model hazır.': 'Modello pronto.',
    'Yeniden dene': 'Riprova',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Cartelle monitorate modificate; premere «Scansiona ora» per aggiornare.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Questo backup usa il vecchio formato cifrato; inserire la password del backup:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Valido con la scansione programmata attiva; viene eseguita all’ora scelta.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Avvisa delle modifiche; non avvia mai una scansione da solo.",
    "Kasa": "Cassaforte",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "La cassaforte di questo computer si apre senza password; nessun accesso, blocco o chiave di recupero.",
    "Yerel çalışır; kasa şifresizdir": "Funziona in locale; cassaforte senza password",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Creazione della cassaforte senza password. Al termine DeepFind si aprirà da solo.",
    "Eski şifreli kasa": "Vecchia cassaforte cifrata",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Questa cassaforte usa il vecchio formato cifrato. Inserire la password attuale per convertirla:",
    "Şifresiz kasa": "Cassaforte senza password",
    "Kapat": "Chiudi",
    "Kasa açılıyor…": "Apertura della cassaforte…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "I documenti originali sono conservati.\nI dati di ricerca restano su questo computer.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "I dati di ricerca restano su questo computer; nessuna password di accesso.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Motore CUDA non trovato in questa installazione; riparare l’installazione.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "I dati di ricerca restano su questo computer.",
    "Kasa: şifresiz\n": "Cassaforte: senza password\n",
}

PB = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "A troca de idioma vale na próxima inicialização.",
    "Çalışma motoru": "Motor de cálculo",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "A escolha é salva e o motor é reiniciado.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Idioma salvo: {language}. O novo idioma vale na próxima inicialização.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Motor salvo: {motor}. Ele reinicia na próxima busca.",
    "Görünüm ve dil": "Aparência e idioma",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menus, botões e mensagens são exibidos neste idioma.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Qual unidade executa a busca semântica.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Recomendado: automático (placa de vídeo, senão processador)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Tenta a placa de vídeo; se não for adequada, a busca passa para o processador.",
    "Yalnız işlemci (CPU)": "Somente processador (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Funciona em qualquer computador; mais lento em máquinas com placa de vídeo.",
    "Ekran kartı (Vulkan)": "Placa de vídeo (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Sem placa ou driver adequado, a busca não inicia.",
    "NVIDIA ekran kartı (CUDA)": "Placa de vídeo NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Componente opcional; inutilizável enquanto não for baixado.",
    "kurulu değil": "não instalado",
    "kurulu": "instalado",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Pressione “Analisar agora” para iniciar a primeira varredura.",
    "Geri": "Voltar",
    "En az 12 karakter": "Pelo menos 12 caracteres",
    "Eklenen klasörler • {count}": "Pastas adicionadas • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "A busca semântica roda neste computador. A opção recomendada tenta a unidade mais rápida e recorre ao processador com segurança.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "“Concluir instalação” abre seu espaço de trabalho; você inicia a primeira varredura na página Varredura.",
    "Açık tema": "Tema claro",
    "Koyu tema": "Tema escuro",
    "Son kontrol": "Verificação final",
    "Nasıl çalışsın?": "Como deve rodar?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Tenta a placa de vídeo. Se ela não for adequada, a busca passa para o processador; a área de status mostra a unidade usada.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Funciona em qualquer computador. Mais lento em sistemas com placa de vídeo.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Usa a placa de vídeo no Windows. Sem placa ou driver adequado, a busca não inicia.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "A opção mais rápida em placas NVIDIA. Inutilizável sem baixar o componente opcional.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Você pode mudar esta escolha depois em Configurações.",
    "Otomatik": "Automático",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Se a tentativa com a placa de vídeo falhar, a busca continua no processador; a área de status mostra a unidade usada.",
    "Tema": "Tema",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Cerca de 663 MB. Pode baixar em Configurações.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "O componente CUDA ainda não foi baixado. Você pode baixá-lo em Configurações após a instalação.",
    "yaklaşık {size} MB, indirilebilir": "cerca de {size} MB, pode ser baixado",
    "Motor": "Motor",
    "Kök: {count} adet\n": "Raízes: {count}\n",
    'Saatli taramayı etkinleştir': 'Ativar a verificação agendada',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Só é executada se o aplicativo estiver aberto neste horário; verificações perdidas não são iniciadas depois.',
    'Saatli tarama etkinken geçerlidir.': 'Aplica-se quando a verificação agendada está ativada.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Chegou o horário da verificação agendada, mas outra verificação está em andamento; nenhuma segunda verificação foi iniciada.',
    'Anlamsal arama modelini indir (~296 MB)': 'Baixar o modelo de pesquisa semântica (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'O modelo é necessário para a pesquisa offline; baixa-se uma vez.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Aceito a licença do modelo (Apache-2.0)',
    'İndirmeyi başlat': 'Iniciar download',
    'Model indiriliyor…': 'Baixando o modelo…',
    'Model indirildi ve doğrulandı.': 'Modelo baixado e verificado.',
    'İndirme tamamlanamadı.': 'Falha no download.',
    'İndirme iptal edildi.': 'Download cancelado.',
    'Model hazır.': 'Modelo pronto.',
    'Yeniden dene': 'Tentar novamente',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Pastas monitoradas alteradas; pressione “Verificar agora” para atualizar.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Este backup está no formato criptografado antigo; digite a senha do backup:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Válido com a verificação agendada ativada; executa no horário escolhido.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Avisa sobre alterações; nunca inicia uma verificação sozinho.",
    "Kasa": "Cofre",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "O cofre deste computador abre sem senha; sem login, bloqueio ou chave de recuperação.",
    "Yerel çalışır; kasa şifresizdir": "Roda localmente; cofre sem senha",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Criando o cofre sem senha. O DeepFind abrirá sozinho ao concluir.",
    "Eski şifreli kasa": "Cofre criptografado antigo",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Este cofre está no formato criptografado antigo. Digite a senha atual para convertê-lo:",
    "Şifresiz kasa": "Cofre sem senha",
    "Kapat": "Fechar",
    "Kasa açılıyor…": "Abrindo o cofre…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Seus documentos originais são mantidos.\nOs dados de pesquisa ficam neste computador.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Seus dados de pesquisa ficam neste computador; sem senha de acesso.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Mecanismo CUDA não encontrado nesta instalação; repare a instalação.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Seus dados de pesquisa ficam neste computador.",
    "Kasa: şifresiz\n": "Cofre: sem senha\n",
}

RU = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "Смена языка вступит в силу при следующем запуске.",
    "Çalışma motoru": "Вычислительный движок",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "Выбор сохраняется, движок перезапускается.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Язык сохранён: {language}. Новый язык вступит в силу при следующем запуске.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Движок сохранён: {motor}. Он перезапустится при следующем поиске.",
    "Görünüm ve dil": "Оформление и язык",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Меню, кнопки и сообщения отображаются на этом языке.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Какое устройство выполняет семантический поиск.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Рекомендуется: автоматически (видеокарта, иначе процессор)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Пробует видеокарту; если она не подходит, поиск идёт на процессоре.",
    "Yalnız işlemci (CPU)": "Только процессор (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Работает на любом компьютере; медленнее там, где есть видеокарта.",
    "Ekran kartı (Vulkan)": "Видеокарта (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Без подходящей видеокарты или драйвера поиск не начнётся.",
    "NVIDIA ekran kartı (CUDA)": "Видеокарта NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Необязательный компонент; без загрузки не используется.",
    "kurulu değil": "не установлено",
    "kurulu": "установлено",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Нажмите «Сканировать сейчас», чтобы начать первое сканирование.",
    "Geri": "Назад",
    "En az 12 karakter": "Не менее 12 символов",
    "Eklenen klasörler • {count}": "Добавленные папки • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "Семантический поиск выполняется на этом компьютере. Рекомендуемый вариант пробует самое быстрое устройство и безопасно возвращается к процессору.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "Кнопка «Завершить установку» откроет рабочую область; первое сканирование вы запускаете на странице «Сканирование».",
    "Açık tema": "Светлая тема",
    "Koyu tema": "Тёмная тема",
    "Son kontrol": "Последняя проверка",
    "Nasıl çalışsın?": "Как работать?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Пробует видеокарту. Если она не подходит, поиск переходит на процессор; используемое устройство видно в области состояния.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Работает на любом компьютере. Медленнее на системах с видеокартой.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Использует видеокарту в Windows. Без подходящей карты или драйвера поиск не начнётся.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "Самый быстрый вариант на картах NVIDIA. Недоступен без загрузки необязательного компонента.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Выбор можно изменить позже в разделе «Настройки».",
    "Otomatik": "Автоматически",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Если попытка с видеокартой не удалась, поиск продолжается на процессоре; используемое устройство указано в области состояния.",
    "Tema": "Тема",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Около 663 МБ. Загрузка доступна в настройках.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Компонент CUDA ещё не загружен. Его можно загрузить в настройках после установки.",
    "yaklaşık {size} MB, indirilebilir": "около {size} МБ, можно загрузить",
    "Motor": "Движок",
    "Kök: {count} adet\n": "Корни: {count}\n",
    'Saatli taramayı etkinleştir': 'Включить проверку по расписанию',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Выполняется, только если приложение открыто в это время; пропущенные проверки потом не запускаются.',
    'Saatli tarama etkinken geçerlidir.': 'Действует, если проверка по расписанию включена.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Наступило время проверки по расписанию, но идёт другая проверка; вторая проверка не запущена.',
    'Anlamsal arama modelini indir (~296 MB)': 'Скачать модель семантического поиска (~296 МБ)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Модель нужна для офлайн-поиска; скачивается один раз.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Принимаю лицензию модели (Apache-2.0)',
    'İndirmeyi başlat': 'Начать загрузку',
    'Model indiriliyor…': 'Загрузка модели…',
    'Model indirildi ve doğrulandı.': 'Модель загружена и проверена.',
    'İndirme tamamlanamadı.': 'Ошибка загрузки.',
    'İndirme iptal edildi.': 'Загрузка отменена.',
    'Model hazır.': 'Модель готова.',
    'Yeniden dene': 'Повторить',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Отслеживаемые папки изменились; нажмите «Сканировать», чтобы обновить.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Эта копия в старом зашифрованном формате; введите пароль копии:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Действует при включённом сканировании по расписанию; запускается в выбранное время.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Сообщает об изменениях; само сканирование не запускает.",
    "Kasa": "Хранилище",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "Хранилище на этом компьютере открывается без пароля; входа, блокировки и ключа восстановления нет.",
    "Yerel çalışır; kasa şifresizdir": "Работает локально; хранилище без пароля",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Создание хранилища без пароля. По завершении DeepFind откроется сам.",
    "Eski şifreli kasa": "Старое зашифрованное хранилище",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Это хранилище в старом зашифрованном формате. Введите текущий пароль для преобразования:",
    "Şifresiz kasa": "Хранилище без пароля",
    "Kapat": "Закрыть",
    "Kasa açılıyor…": "Открытие хранилища…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Исходные документы сохраняются.\nДанные поиска хранятся на этом компьютере.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Данные поиска хранятся на этом компьютере; пароля для входа нет.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Движок CUDA не найден в этой установке; восстановите установку.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Данные поиска хранятся на этом компьютере.",
    "Kasa: şifresiz\n": "Хранилище: без пароля\n",
}

PL = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "Zmiana języka zadziała przy następnym uruchomieniu.",
    "Çalışma motoru": "Silnik obliczeniowy",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "Wybór jest zapisywany, a silnik uruchamiany ponownie.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Język zapisany: {language}. Nowy język zadziała przy następnym uruchomieniu.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Silnik zapisany: {motor}. Zostanie uruchomiony ponownie przy następnym wyszukiwaniu.",
    "Görünüm ve dil": "Wygląd i język",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menu, przyciski i komunikaty są wyświetlane w tym języku.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Która jednostka wykonuje wyszukiwanie semantyczne.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Zalecane: automatycznie (karta graficzna, w razie potrzeby procesor)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Próbuje użyć karty graficznej; jeśli jest nieodpowiednia, wyszukiwanie przechodzi na procesor.",
    "Yalnız işlemci (CPU)": "Tylko procesor (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Działa na każdym komputerze; wolniej na maszynach z kartą graficzną.",
    "Ekran kartı (Vulkan)": "Karta graficzna (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Bez odpowiedniej karty lub sterownika wyszukiwanie nie rozpocznie się.",
    "NVIDIA ekran kartı (CUDA)": "Karta graficzna NVIDIA (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Składnik opcjonalny; niedostępny przed pobraniem.",
    "kurulu değil": "nie zainstalowano",
    "kurulu": "zainstalowano",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Naciśnij „Skanuj teraz”, aby rozpocząć pierwsze skanowanie.",
    "Geri": "Wstecz",
    "En az 12 karakter": "Co najmniej 12 znaków",
    "Eklenen klasörler • {count}": "Dodane foldery • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "Wyszukiwanie semantyczne działa na tym komputerze. Zalecana opcja próbuje najszybszej jednostki i bezpiecznie wraca do procesora.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "„Zakończ konfigurację” otworzy obszar roboczy; pierwsze skanowanie uruchamiasz na stronie Skanowanie.",
    "Açık tema": "Motyw jasny",
    "Koyu tema": "Motyw ciemny",
    "Son kontrol": "Ostatnia kontrola",
    "Nasıl çalışsın?": "Jak ma działać?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Próbuje użyć karty graficznej. Jeśli jest nieodpowiednia, wyszukiwanie przechodzi na procesor; użytą jednostkę widać w polu stanu.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Działa na każdym komputerze. Wolniej na systemach z kartą graficzną.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Używa karty graficznej w Windows. Bez odpowiedniej karty lub sterownika wyszukiwanie nie rozpocznie się.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "Najszybsza opcja na kartach NVIDIA. Niedostępna bez pobrania składnika opcjonalnego.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "Wybór możesz później zmienić w Ustawieniach.",
    "Otomatik": "Automatycznie",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Jeśli próba z kartą graficzną się nie uda, wyszukiwanie trwa na procesorze; użytą jednostkę pokazuje pole stanu.",
    "Tema": "Motyw",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Około 663 MB. Można pobrać w Ustawieniach.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Składnik CUDA nie został jeszcze pobrany. Możesz go pobrać w Ustawieniach po instalacji.",
    "yaklaşık {size} MB, indirilebilir": "około {size} MB, do pobrania",
    "Motor": "Silnik",
    "Kök: {count} adet\n": "Korzenie: {count}\n",
    'Saatli taramayı etkinleştir': 'Włącz skanowanie według harmonogramu',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Uruchamia się tylko wtedy, gdy aplikacja jest otwarta o tej godzinie; pominięte skanowania nie są później uruchamiane.',
    'Saatli tarama etkinken geçerlidir.': 'Dotyczy sytuacji, gdy skanowanie według harmonogramu jest włączone.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Nadszedł czas zaplanowanego skanowania, ale trwa inne skanowanie; nie uruchomiono drugiego skanowania.',
    'Anlamsal arama modelini indir (~296 MB)': 'Pobierz model wyszukiwania semantycznego (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Model jest wymagany do wyszukiwania offline; pobiera się raz.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Akceptuję licencję modelu (Apache-2.0)',
    'İndirmeyi başlat': 'Rozpocznij pobieranie',
    'Model indiriliyor…': 'Pobieranie modelu…',
    'Model indirildi ve doğrulandı.': 'Model pobrany i zweryfikowany.',
    'İndirme tamamlanamadı.': 'Pobieranie nie powiodło się.',
    'İndirme iptal edildi.': 'Pobieranie anulowane.',
    'Model hazır.': 'Model gotowy.',
    'Yeniden dene': 'Ponów',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Obserwowane foldery zmienione; naciśnij „Skanuj teraz\", aby zaktualizować.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Ta kopia jest w starym zaszyfrowanym formacie; podaj hasło kopii:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Obowiązuje przy włączonym skanowaniu o czasie; działa o wybranej godzinie.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Powiadamia o zmianach; nigdy nie uruchamia skanowania samoistnie.",
    "Kasa": "Sejf",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "Sejf na tym komputerze otwiera się bez hasła; brak logowania, blokady i klucza odzyskiwania.",
    "Yerel çalışır; kasa şifresizdir": "Działa lokalnie; sejf bez hasła",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Tworzenie sejfu bez hasła. Po zakończeniu DeepFind otworzy się sam.",
    "Eski şifreli kasa": "Stary zaszyfrowany sejf",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Ten sejf jest w starym zaszyfrowanym formacie. Podaj bieżące hasło, aby go przekształcić:",
    "Şifresiz kasa": "Sejf bez hasła",
    "Kapat": "Zamknij",
    "Kasa açılıyor…": "Otwieranie sejfu…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Dokumenty źródłowe są zachowane.\nDane wyszukiwania zostają na tym komputerze.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Dane wyszukiwania zostają na tym komputerze; brak hasła logowania.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "Nie znaleziono silnika CUDA w tej instalacji; napraw instalację.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Dane wyszukiwania zostają na tym komputerze.",
    "Kasa: şifresiz\n": "Sejf: bez hasła\n",
}

NL = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "Een taalwijziging geldt bij de volgende start.",
    "Çalışma motoru": "Rekenengine",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "De keuze wordt opgeslagen en de engine start opnieuw.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "Taal opgeslagen: {language}. De nieuwe taal geldt bij de volgende start.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "Engine opgeslagen: {motor}. Deze start opnieuw bij de volgende zoekopdracht.",
    "Görünüm ve dil": "Weergave en taal",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.":
        "Menu's, knoppen en meldingen worden in deze taal getoond.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "Welke eenheid het semantisch zoeken uitvoert.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)":
        "Aanbevolen: automatisch (videokaart, anders processor)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "Probeert de videokaart; is die ongeschikt, dan zoekt de processor verder.",
    "Yalnız işlemci (CPU)": "Alleen processor (CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "Werkt op elke computer; langzamer op machines met een videokaart.",
    "Ekran kartı (Vulkan)": "Videokaart (Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Zonder geschikte kaart of stuurprogramma start het zoeken niet.",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA-videokaart (CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.":
        "Optioneel onderdeel; niet te gebruiken zonder download.",
    "kurulu değil": "niet geïnstalleerd",
    "kurulu": "geïnstalleerd",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.":
        "Druk op ‘Nu scannen’ om de eerste scan te starten.",
    "Geri": "Terug",
    "En az 12 karakter": "Minstens 12 tekens",
    "Eklenen klasörler • {count}": "Toegevoegde mappen • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "Semantisch zoeken draait op deze computer. De aanbevolen optie probeert de snelste eenheid en valt veilig terug op de processor.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "‘Installatie voltooien’ opent uw werkruimte; u start de eerste scan op de pagina Scannen.",
    "Açık tema": "Licht thema",
    "Koyu tema": "Donker thema",
    "Son kontrol": "Laatste controle",
    "Nasıl çalışsın?": "Hoe moet het werken?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "Het probeert de videokaart. Is die ongeschikt, dan gaat het zoeken naar de processor; het statusveld toont welke eenheid wordt gebruikt.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "Werkt op elke computer. Langzamer op systemen met een videokaart.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Gebruikt de videokaart in Windows. Zonder geschikte kaart of stuurprogramma start het zoeken niet.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "De snelste optie op NVIDIA-kaarten. Niet te gebruiken zonder het optionele onderdeel te downloaden.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.":
        "U kunt deze keuze later wijzigen bij Instellingen.",
    "Otomatik": "Automatisch",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "Mislukt de poging met de videokaart, dan gaat het zoeken verder op de processor; het statusveld toont welke eenheid wordt gebruikt.",
    "Tema": "Thema",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.":
        "Ongeveer 663 MB. Te downloaden bij Instellingen.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "Het CUDA-onderdeel is nog niet gedownload. U kunt het na de installatie downloaden bij Instellingen.",
    "yaklaşık {size} MB, indirilebilir": "ongeveer {size} MB, te downloaden",
    "Motor": "Engine",
    "Kök: {count} adet\n": "Hoofdmappen: {count}\n",
    'Saatli taramayı etkinleştir': 'Geplande scan inschakelen',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'Wordt alleen uitgevoerd als de app op dit tijdstip open is; gemiste scans worden niet later gestart.',
    'Saatli tarama etkinken geçerlidir.': 'Geldt wanneer gepland scannen is ingeschakeld.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': 'Het tijdstip van de geplande scan is aangebroken, maar er loopt nog een andere scan; er is geen tweede scan gestart.',
    'Anlamsal arama modelini indir (~296 MB)': 'Semantisch zoekmodel downloaden (~296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'Het model is nodig voor offline zoeken; wordt eenmaal gedownload.',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'Ik accepteer de modellicentie (Apache-2.0)',
    'İndirmeyi başlat': 'Download starten',
    'Model indiriliyor…': 'Model wordt gedownload…',
    'Model indirildi ve doğrulandı.': 'Model gedownload en geverifieerd.',
    'İndirme tamamlanamadı.': 'Download mislukt.',
    'İndirme iptal edildi.': 'Download geannuleerd.',
    'Model hazır.': 'Model klaar.',
    'Yeniden dene': 'Opnieuw proberen',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "Gevolgde mappen gewijzigd; druk op „Nu scannen” om bij te werken.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "Deze backup gebruikt het oude versleutelde formaat; voer het backupwachtwoord in:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "Geldt bij ingeschakelde geplande scan; draait op het gekozen tijdstip.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "Meldt wijzigingen; start nooit zelf een scan.",
    "Kasa": "Kluis",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "De kluis op deze computer opent zonder wachtwoord; geen login, vergrendeling of herstelsleutel.",
    "Yerel çalışır; kasa şifresizdir": "Draait lokaal; kluis zonder wachtwoord",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "Kluis zonder wachtwoord wordt ingesteld. DeepFind opent daarna vanzelf.",
    "Eski şifreli kasa": "Oude versleutelde kluis",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "Deze kluis gebruikt het oude versleutelde formaat. Voer het huidige wachtwoord in om te converteren:",
    "Şifresiz kasa": "Kluis zonder wachtwoord",
    "Kapat": "Sluiten",
    "Kasa açılıyor…": "Kluis wordt geopend…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "Uw brondocumenten blijven bewaard.\nZoekgegevens blijven op deze computer.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "Uw zoekgegevens blijven op deze computer; geen loginwachtwoord.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "CUDA-engine niet gevonden in deze installatie; herstel de installatie.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "Uw zoekgegevens blijven op deze computer.",
    "Kasa: şifresiz\n": "Kluis: zonder wachtwoord\n",
}

ZH = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "语言更改将在下次启动时生效。",
    "Çalışma motoru": "计算引擎",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "选择已保存，引擎将重新启动。",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "语言已保存：{language}。新语言将在下次启动时生效。",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "引擎已保存：{motor}。下次搜索时会重新启动。",
    "Görünüm ve dil": "外观与语言",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.": "菜单、按钮和提示将以该语言显示。",
    "Anlamsal aramanın hangi birimde çalışacağı.": "语义搜索由哪个单元执行。",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)": "推荐：自动（显卡，否则处理器）",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.": "尝试使用显卡；若不适用，搜索将转到处理器。",
    "Yalnız işlemci (CPU)": "仅处理器（CPU）",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.": "适用于任何电脑；在有显卡的机器上较慢。",
    "Ekran kartı (Vulkan)": "显卡（Vulkan）",
    "Uygun kart ya da sürücü yoksa arama başlamaz.": "没有合适的显卡或驱动时，搜索不会启动。",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA 显卡（CUDA）",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.": "可选组件；未下载前无法使用。",
    "kurulu değil": "未安装",
    "kurulu": "已安装",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.": "按“立即扫描”开始首次扫描。",
    "Geri": "返回",
    "En az 12 karakter": "至少 12 个字符",
    "Eklenen klasörler • {count}": "已添加的文件夹 • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "语义搜索在本机运行。推荐选项会尝试最快的单元，若不可用则安全地回退到处理器。",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "按“完成安装”打开工作区；首次扫描请在“扫描”页面自行启动。",
    "Açık tema": "浅色主题",
    "Koyu tema": "深色主题",
    "Son kontrol": "最后检查",
    "Nasıl çalışsın?": "如何运行？",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "会尝试使用显卡。若显卡不适用，搜索转到处理器；状态区会显示所用的单元。",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.": "适用于任何电脑。在有显卡的系统上较慢。",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "在 Windows 上使用显卡。没有合适的显卡或驱动时，搜索不会启动。",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "在 NVIDIA 显卡上最快。未下载可选组件前无法使用。",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.": "之后可在“设置”中更改此选择。",
    "Otomatik": "自动",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "若显卡尝试失败，搜索将在处理器上继续；状态区会显示所用的单元。",
    "Tema": "主题",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.": "约 663 MB。可在“设置”中下载。",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "CUDA 组件尚未下载。安装后可在“设置”中下载。",
    "yaklaşık {size} MB, indirilebilir": "约 {size} MB，可下载",
    "Motor": "引擎",
    "Kök: {count} adet\n": "根目录：{count}\n",
    'Saatli taramayı etkinleştir': '启用定时扫描',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': '仅在应用于此时间处于打开状态时运行；错过的扫描不会稍后启动。',
    'Saatli tarama etkinken geçerlidir.': '在启用定时扫描时适用。',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': '已到定时扫描时间，但另一个扫描正在进行；未启动第二次扫描。',
    'Anlamsal arama modelini indir (~296 MB)': '下载语义搜索模型（约296 MB）',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': '离线搜索需要该模型；只需下载一次。',
    'Model lisansını (Apache-2.0) kabul ediyorum': '我接受模型许可（Apache-2.0）',
    'İndirmeyi başlat': '开始下载',
    'Model indiriliyor…': '正在下载模型…',
    'Model indirildi ve doğrulandı.': '模型已下载并验证。',
    'İndirme tamamlanamadı.': '下载失败。',
    'İndirme iptal edildi.': '下载已取消。',
    'Model hazır.': '模型就绪。',
    'Yeniden dene': '重试',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "受监控文件夹有变化；请按“立即扫描”更新。",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "此备份为旧加密格式；请输入备份密码：",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "定时扫描开启时有效；按所选时间运行。",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "有变化时提醒；不会自动开始扫描。",
    "Kasa": "保管库",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "本机保管库无需密码即可打开；没有登录、锁定和恢复密钥。",
    "Yerel çalışır; kasa şifresizdir": "本地运行；保管库无密码",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "正在创建无密码保管库。完成后 DeepFind 将自动打开。",
    "Eski şifreli kasa": "旧加密保管库",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "此保管库为旧加密格式。请输入当前密码进行转换：",
    "Şifresiz kasa": "无密码保管库",
    "Kapat": "关闭",
    "Kasa açılıyor…": "正在打开保管库…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "源文档予以保留。\n搜索数据保存在本机。",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "搜索数据保存在本机；没有登录密码。",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "此安装中未找到 CUDA 引擎；请修复安装。",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "搜索数据保存在本机。",
    "Kasa: şifresiz\n": "保管库：无密码\n",
}

JA = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "言語の変更は次回の起動時に反映されます。",
    "Çalışma motoru": "演算エンジン",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "選択は保存され、エンジンが再起動します。",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "言語を保存しました: {language}。新しい言語は次回の起動時に反映されます。",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "エンジンを保存しました: {motor}。次の検索時に再起動します。",
    "Görünüm ve dil": "表示と言語",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.": "メニュー、ボタン、メッセージはこの言語で表示されます。",
    "Anlamsal aramanın hangi birimde çalışacağı.": "セマンティック検索を実行する単位。",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)": "推奨: 自動（グラフィックカード、不可ならプロセッサ）",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "グラフィックカードを試します。適していない場合はプロセッサで検索します。",
    "Yalnız işlemci (CPU)": "プロセッサのみ（CPU）",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "どのパソコンでも動作します。グラフィックカードのある環境では遅くなります。",
    "Ekran kartı (Vulkan)": "グラフィックカード（Vulkan）",
    "Uygun kart ya da sürücü yoksa arama başlamaz.":
        "対応するカードやドライバーがない場合、検索は開始されません。",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA グラフィックカード（CUDA）",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.": "任意のコンポーネントです。ダウンロードするまで使用できません。",
    "kurulu değil": "未インストール",
    "kurulu": "インストール済み",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.": "初回スキャンを始めるには「今すぐスキャン」を押します。",
    "Geri": "戻る",
    "En az 12 karakter": "12 文字以上",
    "Eklenen klasörler • {count}": "追加したフォルダー • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "セマンティック検索はこのパソコンで実行されます。推奨設定は最速の単位を試し、使えない場合は安全にプロセッサへ切り替えます。",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "「セットアップを完了」で作業領域が開きます。初回スキャンはスキャンページからご自身で開始します。",
    "Açık tema": "ライトテーマ",
    "Koyu tema": "ダークテーマ",
    "Son kontrol": "最終確認",
    "Nasıl çalışsın?": "どのように実行しますか？",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "グラフィックカードを試します。適していない場合はプロセッサに切り替わります。使用中の単位は状態欄に表示されます。",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "どのパソコンでも動作します。グラフィックカードのある環境では遅くなります。",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Windows でグラフィックカードを使用します。対応するカードやドライバーがない場合、検索は開始されません。",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "NVIDIA カードでは最速の選択肢です。任意のコンポーネントをダウンロードするまで使用できません。",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.": "この選択は後で設定から変更できます。",
    "Otomatik": "自動",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "グラフィックカードでの試行が失敗した場合、検索はプロセッサで続きます。使用中の単位は状態欄に表示されます。",
    "Tema": "テーマ",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.": "約 663 MB。設定からダウンロードできます。",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "CUDA コンポーネントはまだダウンロードされていません。セットアップ後に設定からダウンロードできます。",
    "yaklaşık {size} MB, indirilebilir": "約 {size} MB、ダウンロード可能",
    "Motor": "エンジン",
    "Kök: {count} adet\n": "ルート: {count}\n",
    'Saatli taramayı etkinleştir': '定期スキャンを有効にする',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': 'この時刻にアプリが開いている場合のみ実行されます。逃したスキャンは後から開始されません。',
    'Saatli tarama etkinken geçerlidir.': '定期スキャンが有効なときに適用されます。',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': '定期スキャンの時刻になりましたが、別のスキャンが実行中です。2 回目のスキャンは開始していません。',
    'Anlamsal arama modelini indir (~296 MB)': 'セマンティック検索モデルをダウンロード（約296 MB）',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': 'オフライン検索にはモデルが必要です。ダウンロードは1回だけです。',
    'Model lisansını (Apache-2.0) kabul ediyorum': 'モデルライセンス（Apache-2.0）に同意します',
    'İndirmeyi başlat': 'ダウンロード開始',
    'Model indiriliyor…': 'モデルをダウンロード中…',
    'Model indirildi ve doğrulandı.': 'モデルをダウンロードして検証しました。',
    'İndirme tamamlanamadı.': 'ダウンロードに失敗しました。',
    'İndirme iptal edildi.': 'ダウンロードをキャンセルしました。',
    'Model hazır.': 'モデルの準備ができました。',
    'Yeniden dene': '再試行',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "監視フォルダに変更あり。更新には「今すぐスキャン」を押してください。",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "このバックアップは旧暗号化形式です。バックアップのパスワードを入力してください：",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "時刻指定スキャン有効時に適用。選択した時刻に実行されます。",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "変更を通知します。自動でスキャンは開始しません。",
    "Kasa": "保管庫",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "このPCの保管庫はパスワードなしで開きます。ログイン・ロック・回復キーはありません。",
    "Yerel çalışır; kasa şifresizdir": "ローカル動作。保管庫はパスワードなし",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "パスワードなし保管庫を作成中。完了後DeepFindが自動で開きます。",
    "Eski şifreli kasa": "旧暗号化保管庫",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "この保管庫は旧暗号化形式です。変換には現在のパスワードを入力してください：",
    "Şifresiz kasa": "パスワードなし保管庫",
    "Kapat": "閉じる",
    "Kasa açılıyor…": "保管庫を開いています…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "元の文書は保持されます。\n検索データはこのPCに保存されます。",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "検索データはこのPCに保存されます。ログインパスワードはありません。",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "このインストールにCUDAエンジンが見つかりません。修復してください。",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "検索データはこのPCに保存されます。",
    "Kasa: şifresiz\n": "保管庫：パスワードなし\n",
}

KO = {
    "Dil değişikliği bir sonraki açılışta geçerli olur.": "언어 변경은 다음 실행 시 적용됩니다.",
    "Çalışma motoru": "연산 엔진",
    "Seçim kaydedilir ve motor yeniden başlatılır.": "선택이 저장되고 엔진이 다시 시작됩니다.",
    "Dil kaydedildi: {language}. Yeni dil bir sonraki açılışta geçerli olur.":
        "언어가 저장되었습니다: {language}. 새 언어는 다음 실행 시 적용됩니다.",
    "Motor seçimi kaydedildi: {motor}. Sonraki aramada yeniden başlatılır.":
        "엔진이 저장되었습니다: {motor}. 다음 검색 시 다시 시작됩니다.",
    "Görünüm ve dil": "화면 및 언어",
    "Menüler, düğmeler ve iletiler bu dilde gösterilir.": "메뉴, 버튼, 메시지가 이 언어로 표시됩니다.",
    "Anlamsal aramanın hangi birimde çalışacağı.": "의미 검색을 실행할 장치입니다.",
    "Önerilen: otomatik (ekran kartı, olmazsa işlemci)": "권장: 자동(그래픽 카드, 불가 시 프로세서)",
    "Ekran kartını dener; uygun değilse arama işlemciye geçer.":
        "그래픽 카드를 시도합니다. 적합하지 않으면 검색이 프로세서로 전환됩니다.",
    "Yalnız işlemci (CPU)": "프로세서만(CPU)",
    "Her bilgisayarda çalışır, ekran kartı olanlarda daha yavaştır.":
        "모든 컴퓨터에서 동작합니다. 그래픽 카드가 있는 환경에서는 더 느립니다.",
    "Ekran kartı (Vulkan)": "그래픽 카드(Vulkan)",
    "Uygun kart ya da sürücü yoksa arama başlamaz.": "적합한 카드나 드라이버가 없으면 검색이 시작되지 않습니다.",
    "NVIDIA ekran kartı (CUDA)": "NVIDIA 그래픽 카드(CUDA)",
    "İsteğe bağlı bileşen; indirilmeden kullanılamaz.": "선택 구성 요소이며, 다운로드 전에는 사용할 수 없습니다.",
    "kurulu değil": "설치되지 않음",
    "kurulu": "설치됨",
    "İlk taramayı başlatmak için “Şimdi tara”ya basın.": "첫 검사를 시작하려면 ‘지금 검사’를 누르세요.",
    "Geri": "뒤로",
    "En az 12 karakter": "12자 이상",
    "Eklenen klasörler • {count}": "추가한 폴더 • {count}",
    "Anlamsal arama bu bilgisayarda çalışır. Önerilen seçenek en hızlı olanı dener, olmazsa güvenli biçimde işlemciye döner.":
        "의미 검색은 이 컴퓨터에서 실행됩니다. 권장 옵션은 가장 빠른 장치를 시도하고, 불가하면 안전하게 프로세서로 돌아갑니다.",
    "“Kurulumu tamamla” ile çalışma alanınızı açın; ilk taramayı Tarama sayfasından siz başlatın.":
        "‘설정 완료’를 누르면 작업 공간이 열립니다. 첫 검사는 검사 페이지에서 직접 시작하세요.",
    "Açık tema": "밝은 테마",
    "Koyu tema": "어두운 테마",
    "Son kontrol": "최종 확인",
    "Nasıl çalışsın?": "어떻게 실행할까요?",
    "Ekran kartını dener. Ekran kartı uygun değilse arama işlemciye geçer; bunu durum alanında görürsünüz.":
        "그래픽 카드를 시도합니다. 적합하지 않으면 검색이 프로세서로 전환되며, 사용 장치는 상태 영역에 표시됩니다.",
    "Her bilgisayarda çalışır. Ekran kartı olan sistemlerde daha yavaştır.":
        "모든 컴퓨터에서 동작합니다. 그래픽 카드가 있는 시스템에서는 더 느립니다.",
    "Windows'ta ekran kartını kullanır. Uygun kart ya da sürücü yoksa arama başlamaz.":
        "Windows에서 그래픽 카드를 사용합니다. 적합한 카드나 드라이버가 없으면 검색이 시작되지 않습니다.",
    "NVIDIA kartlarda en hızlı seçenek. İsteğe bağlı bileşen indirilmeden kullanılamaz.":
        "NVIDIA 카드에서 가장 빠른 옵션입니다. 선택 구성 요소를 다운로드하기 전에는 사용할 수 없습니다.",
    "Seçiminizi sonradan Ayarlar bölümünden değiştirebilirsiniz.": "이 선택은 나중에 설정에서 변경할 수 있습니다.",
    "Otomatik": "자동",
    "Ekran kartı denemesi başarısız olursa arama işlemcide sürer; hangi birimin kullanıldığı durum alanında yazar.":
        "그래픽 카드 시도가 실패하면 검색이 프로세서에서 계속되며, 사용 장치는 상태 영역에 표시됩니다.",
    "Tema": "테마",
    "Yaklaşık 663 MB. Ayarlar bölümünden indirebilirsiniz.": "약 663MB. 설정에서 내려받을 수 있습니다.",
    "CUDA bileşeni henüz indirilmedi. Kurulumdan sonra Ayarlar bölümünden indirebilirsiniz.":
        "CUDA 구성 요소가 아직 내려받기되지 않았습니다. 설치 후 설정에서 내려받을 수 있습니다.",
    "yaklaşık {size} MB, indirilebilir": "약 {size}MB, 내려받기 가능",
    "Motor": "엔진",
    "Kök: {count} adet\n": "루트: {count}\n",
    'Saatli taramayı etkinleştir': '예약 검사 사용',
    'Yalnız uygulama bu saatte açıksa çalışır; kaçırılan taramalar sonradan başlatılmaz.': '이 시간에 앱이 열려 있을 때만 실행되며, 놓친 검사는 나중에 시작되지 않습니다.',
    'Saatli tarama etkinken geçerlidir.': '예약 검사가 켜져 있을 때 적용됩니다.',
    'Planlı tarama saati geldi ancak başka bir tarama sürüyor; ikinci tarama başlatılmadı.': '예약 검사 시간이 되었지만 다른 검사가 실행 중입니다. 두 번째 검사는 시작되지 않았습니다.',
    'Anlamsal arama modelini indir (~296 MB)': '시맨틱 검색 모델 다운로드(약 296 MB)',
    'Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir.': '오프라인 검색에 모델이 필요합니다. 한 번만 다운로드합니다.',
    'Model lisansını (Apache-2.0) kabul ediyorum': '모델 라이선스(Apache-2.0)에 동의합니다',
    'İndirmeyi başlat': '다운로드 시작',
    'Model indiriliyor…': '모델 다운로드 중…',
    'Model indirildi ve doğrulandı.': '모델을 다운로드하고 검증했습니다.',
    'İndirme tamamlanamadı.': '다운로드하지 못했습니다.',
    'İndirme iptal edildi.': '다운로드가 취소되었습니다.',
    'Model hazır.': '모델 준비 완료.',
    'Yeniden dene': '다시 시도',
    "İzlenen klasörlerde değişiklik var; taramak için “Şimdi tara”ya basın.": "주시 폴더에 변경 있음. 업데이트하려면 “지금 검색”을 누르세요.",
    "Bu yedek eski şifreli biçimde; yedek parolasını girin:": "이 백업은 구 암호화 형식입니다. 백업 암호를 입력하세요:",
    "Saatli tarama etkinken geçerlidir; seçtiğiniz saatte çalışır.": "예약 검색이 켜져 있을 때 적용되며 선택한 시간에 실행됩니다.",
    "Değişiklik olunca haber verir; kendiliğinden tarama başlatmaz.": "변경 사항을 알립니다. 스스로 검색을 시작하지 않습니다.",
    "Kasa": "보관함",
    "Bu bilgisayardaki kasa şifresiz açılır; giriş, kilit ve kurtarma anahtarı yoktur.": "이 PC의 보관함은 암호 없이 열립니다. 로그인·잠금·복구 키가 없습니다.",
    "Yerel çalışır; kasa şifresizdir": "로컬 실행. 보관함은 암호 없음",
    "Şifresiz kasa kuruluyor. Tamamlandığında DeepFind kendiliğinden açılacak.": "암호 없는 보관함을 만드는 중. 완료되면 DeepFind가 자동으로 열립니다.",
    "Eski şifreli kasa": "구 암호화 보관함",
    "Bu kasa eski şifreli biçimde. Dönüştürmek için mevcut parolayı girin:": "이 보관함은 구 암호화 형식입니다. 변환하려면 현재 암호를 입력하세요:",
    "Şifresiz kasa": "암호 없는 보관함",
    "Kapat": "닫기",
    "Kasa açılıyor…": "보관함 여는 중…",
    "Kaynak belgeleriniz korunur.\nArama bilgileri bu bilgisayarda saklanır.": "원본 문서는 보존됩니다.\n검색 데이터는 이 PC에 저장됩니다.",
    "Arama bilgileriniz bu bilgisayarda saklanır; giriş şifresi yoktur.": "검색 데이터는 이 PC에 저장됩니다. 로그인 암호가 없습니다.",
    "CUDA motoru bu kurulumda bulunamadı; kurulumu onarın.": "이 설치에서 CUDA 엔진을 찾을 수 없습니다. 설치를 복구하세요.",
    "Arama bilgileriniz bu bilgisayarda saklanır.": "검색 데이터는 이 PC에 저장됩니다.",
    "Kasa: şifresiz\n": "보관함: 암호 없음\n",
}
