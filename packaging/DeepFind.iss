; DeepFind setup script (Inno Setup 6). The version comes from build.py via ver.iss.
; AppId is FIXED: never change it (upgrade/uninstall must find the same app).
#define AppName "DeepFind"
#include "ver.iss"
#ifdef TestPrevious
  #undef AppVersion
  #define AppVersion "0.10.4"
#endif
#define ModelDir "{app}\_internal\embedding"

[Setup]
#ifdef TestInstall
AppId={{58C903CC-4524-4EAA-ACE9-1E473C59656C}
#else
AppId={{8E2B4F1A-3C7D-4E9A-B5F6-9A8C7D6E5F40}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
AppPublisher=Geeker
#ifdef TestInstall
OutputDir=..\build\test-installer
#else
#ifdef UpdatePackage
OutputDir=..\build\update-installer
#else
OutputDir=..
#endif
#endif
DefaultDirName={autopf}\{#AppName}
#ifdef TestInstall
DefaultGroupName=DeepFind kabul testi
#else
DefaultGroupName={#AppName}
#endif
ArchitecturesInstallIn64BitMode=x64compatible
#ifdef TestInstall
PrivilegesRequired=lowest
#else
PrivilegesRequired=admin
#endif
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
OutputBaseFilename={#AppName}-{#AppVersion}
#ifdef TestInstall
Compression=none
SolidCompression=no
#else
Compression=lzma2/max
SolidCompression=yes
#endif
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName} {#AppVersion}
SetupIconFile=..\build\deepfind.ico
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"; LicenseFile: "licenses\MIT-tr.txt"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"; LicenseFile: "licenses\MIT-de.txt"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"; LicenseFile: "licenses\MIT-es.txt"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"; LicenseFile: "licenses\MIT-fr.txt"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"; LicenseFile: "licenses\MIT-it.txt"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; LicenseFile: "licenses\MIT-pt.txt"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"; LicenseFile: "licenses\MIT-ru.txt"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"; LicenseFile: "licenses\MIT-pl.txt"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"; LicenseFile: "licenses\MIT-nl.txt"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"; LicenseFile: "licenses\MIT-zh.txt"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"; LicenseFile: "licenses\MIT-ja.txt"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"; LicenseFile: "licenses\MIT-ko.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked
Name: "fetchmodel"; Description: "{cm:FetchModel}"; Flags: checkedonce

[CustomMessages]
english.DesktopIcon=Create a desktop icon
turkish.DesktopIcon=Masaüstü simgesi oluştur
german.DesktopIcon=Desktopsymbol erstellen
spanish.DesktopIcon=Crear un icono en el escritorio
french.DesktopIcon=Créer une icône sur le bureau
italian.DesktopIcon=Crea un'icona sul desktop
brazilianportuguese.DesktopIcon=Criar um ícone na área de trabalho
russian.DesktopIcon=Создать значок на рабочем столе
polish.DesktopIcon=Utwórz ikonę na pulpicie
dutch.DesktopIcon=Een bureaubladpictogram maken
chinesesimplified.DesktopIcon=创建桌面图标
japanese.DesktopIcon=デスクトップにアイコンを作成する
korean.DesktopIcon=바탕 화면 아이콘 만들기
english.LaunchProgram=Launch %1
turkish.LaunchProgram=%1'ı başlat
german.LaunchProgram=%1 starten
spanish.LaunchProgram=Iniciar %1
french.LaunchProgram=Lancer %1
italian.LaunchProgram=Avvia %1
brazilianportuguese.LaunchProgram=Iniciar %1
russian.LaunchProgram=Запустить %1
polish.LaunchProgram=Uruchom %1
dutch.LaunchProgram=%1 starten
chinesesimplified.LaunchProgram=启动 %1
japanese.LaunchProgram=%1 を起動
korean.LaunchProgram=%1 시작
english.FetchModel=Download the semantic search model on first launch (~296 MB, for offline search)
turkish.FetchModel=İlk açılışta anlamsal arama modelini indir (~296 MB, çevrimdışı arama için)
german.FetchModel=Semantisches Suchmodell beim ersten Start laden (~296 MB, für Offline-Suche)
spanish.FetchModel=Descargar el modelo de búsqueda semántica en el primer inicio (~296 MB, para búsqueda sin conexión)
french.FetchModel=Télécharger le modèle de recherche sémantique au premier lancement (~296 Mo, pour la recherche hors ligne)
italian.FetchModel=Scarica il modello di ricerca semantica al primo avvio (~296 MB, per la ricerca offline)
brazilianportuguese.FetchModel=Baixar o modelo de pesquisa semântica na primeira execução (~296 MB, para pesquisa offline)
russian.FetchModel=Загрузить модель семантического поиска при первом запуске (~296 МБ, для офлайн-поиска)
polish.FetchModel=Pobierz model wyszukiwania semantycznego przy pierwszym uruchomieniu (~296 MB, do wyszukiwania offline)
dutch.FetchModel=Semantisch zoekmodel downloaden bij eerste start (~296 MB, voor offline zoeken)
chinesesimplified.FetchModel=首次启动时下载语义搜索模型（约296 MB，用于离线搜索）
japanese.FetchModel=初回起動時にセマンティック検索モデルをダウンロード（約296 MB、オフライン検索用）
korean.FetchModel=첫 실행 시 시맨틱 검색 모델 다운로드(약 296 MB, 오프라인 검색용)

[Files]
#ifdef AdayKaynak
Source: "{#AdayKaynak}\*"; DestDir: "{app}"; Excludes: "_internal\embedding\embeddinggemma-2-Q8_0.gguf"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
Source: "..\dist\{#AppName}-{#AppVersion}\*"; DestDir: "{app}"; Excludes: "_internal\embedding\embeddinggemma-2-Q8_0.gguf"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif
#ifndef UpdatePackage
#ifndef TestPrevious
; Model ayri indirilir (ilk acilis veya Ayarlar); kurulum paketinde tasinmaz.
; Mevcut kullanicilarin modeli yerinde kalir, tekrar indirilmez.
#endif
#endif

[InstallDelete]
#ifndef TestPrevious
; Owned legacy keyword-search runtime; no document/model/data folders.
Type: filesandordirs; Name: "{app}\_internal\rapidfuzz"
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Tasks: desktopicon
Name: "{group}\{#AppName} kaldır"; Filename: "{uninstallexe}"

[Run]
; Launch through the interactive shell instead of Setup's original-user spawn
; server: the spawn-server handshake ("CallSpawnServer") failed on real
; installs and surfaced as an internal error. explorer.exe relays the request
; to the already running (non-elevated) shell, so the app still starts as the
; normal user while Setup only needs a plain process start.
#ifdef TestRunAlways
; Kabul kontrolu: sessiz kurulumda bile [Run] komutunu gercek Setup motoru
; isletir; etkilesimli kurulumdaki isaretli dugmenin tetikledigi komutla aynidir.
Filename: "{win}\explorer.exe"; Parameters: """{app}\{#AppName}-{#AppVersion}.exe"""; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall
#else
Filename: "{win}\explorer.exe"; Parameters: """{app}\{#AppName}-{#AppVersion}.exe"""; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
#endif

[UninstallDelete]
Type: files; Name: "{#ModelDir}\embeddinggemma-2-Q8_0.gguf"

[Code]
const ModelHash = '2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135';

function ValidModel(const ModelPath: String): Boolean;
begin
  Result := False;
  if FileExists(ModelPath) then begin
    try
      Result := CompareText(GetSHA256OfFile(ModelPath), ModelHash) = 0;
    except
      Log('Model doğrulanamadı: ' + ModelPath);
    end;
  end;
end;

function ModelPath: String;
begin
  Result := ExpandConstant('{#ModelDir}\embeddinggemma-2-Q8_0.gguf');
end;

function LegacyModelPath: String;
begin
#ifdef TestInstall
  Result := ExpandConstant('{app}\legacy-model\embeddinggemma-2-Q8_0.gguf');
#else
  Result := ExpandConstant('{commonappdata}\DeepFind\models\embeddinggemma-2-Q8_0.gguf');
#endif
end;

function ModelNeedsRepair: Boolean;
begin
  Result := not ValidModel(ModelPath);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Staged: String;
begin
  Result := '';
#ifdef UpdatePackage
  if ModelNeedsRepair then begin
    if not ValidModel(LegacyModelPath) then begin
      Result := 'Yerel model eksik veya bozuk. Tam kurulum paketini kullanın.';
      Exit;
    end;
    Staged := ModelPath + '.migrating';
    if not ForceDirectories(ExtractFileDir(ModelPath)) then begin
      Result := 'Model klasörü oluşturulamadı.';
      Exit;
    end;
    if not FileCopy(LegacyModelPath, Staged, False) then begin
      DeleteFile(Staged);
      Result := 'Mevcut model taşınamadı; eski kurulum korundu.';
      Exit;
    end;
    if not ValidModel(Staged) then begin
      DeleteFile(Staged);
      Result := 'Taşınan model doğrulanamadı; eski kurulum korundu.';
      Exit;
    end;
    if FileExists(ModelPath) then DeleteFile(ModelPath);
    if not RenameFile(Staged, ModelPath) then begin
      DeleteFile(Staged);
      Result := 'Model yerleştirilemedi; eski kurulum korundu.';
    end;
  end;
#endif
end;

function StrictVersion(const Text: String): Boolean;
var I, Dots, Digits: Integer;
begin
  Result := False;
  Dots := 0; Digits := 0;
  for I := 1 to Length(Text) do begin
    if Text[I] = '.' then begin
      if Digits = 0 then Exit;
      Dots := Dots + 1; Digits := 0;
    end else begin
      if (Text[I] < '0') or (Text[I] > '9') then Exit;
      Digits := Digits + 1;
    end;
  end;
  Result := (Dots = 2) and (Digits > 0);
end;

procedure CleanupOldLaunchers;
var Entry: TFindRec; Stem, VersionText, ExePath: String;
    NamedVersion, FileVersion, CurrentVersion: Int64;
begin
  StrToVersion('{#AppVersion}', CurrentVersion);
  if FindFirst(ExpandConstant('{app}\DeepFind-*.exe'), Entry) then begin
    try
      repeat
        Stem := ChangeFileExt(Entry.Name, '');
        VersionText := Copy(Stem, Length('DeepFind-') + 1, MaxInt);
        ExePath := ExpandConstant('{app}\') + Entry.Name;
        if StrictVersion(VersionText) and StrToVersion(VersionText, NamedVersion) then
          if (ComparePackedVersion(NamedVersion, CurrentVersion) < 0) and
             GetPackedVersion(ExePath, FileVersion) then
            if ComparePackedVersion(NamedVersion, FileVersion) = 0 then begin
              if DeleteFile(ExePath) then
                DeleteFile(ExpandConstant('{app}\') + Stem + '.bat')
              else Log('Eski program kullanımda; korundu: ' + ExePath);
            end;
      until not FindNext(Entry);
    finally
      FindClose(Entry);
    end;
  end;
end;

procedure RemoveVerifiedLegacyModel(const ModelPath: String);
begin
  { Only the known, reproducible 0.9 model asset; never arbitrary ONNX files. }
  if FileExists(ModelPath) then begin
    try
      if CompareText(GetSHA256OfFile(ModelPath), '2cabcf6413a22497987da2a092635ade33530614fce978ad11d9828b30dbd843') = 0 then
        if not DeleteFile(ModelPath) then Log('Eski model kullanımda; korundu.');
    except
      Log('Eski model doğrulanamadı; korundu.');
    end;
  end;
end;

procedure WriteModelFlag();
var Istek: String;
begin
  if WizardIsTaskSelected('fetchmodel') then Istek := '1' else Istek := '0';
  SaveStringToFile(ExpandConstant('{app}') + '\model-indir-iste.txt', Istek, False);
end;

procedure WriteInstallLanguage();
var LangCode: String;
begin
  case ActiveLanguage of
    'english': LangCode := 'en';
    'turkish': LangCode := 'tr';
    'german': LangCode := 'de';
    'spanish': LangCode := 'es';
    'french': LangCode := 'fr';
    'italian': LangCode := 'it';
    'brazilianportuguese': LangCode := 'pt-BR';
    'russian': LangCode := 'ru';
    'polish': LangCode := 'pl';
    'dutch': LangCode := 'nl';
    'chinesesimplified': LangCode := 'zh-CN';
    'japanese': LangCode := 'ja';
    'korean': LangCode := 'ko';
  else
    LangCode := 'en';
  end;
  SaveStringToFile(ExpandConstant('{app}') + '\install-language.txt', LangCode, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin WriteInstallLanguage; WriteModelFlag; end;
  { Eski baslatıcılar her zaman temizlenir: tam kurulum paylasilan dosyalari
    degistirdigi icin eski exe zaten calismaz; birakmak kirik kalinti demektir.
    Model onarim durumu yalniz eski model dosyalarinin silinmesini kapsar. }
  if CurStep = ssDone then CleanupOldLaunchers;
  if (CurStep = ssDone) and (not ModelNeedsRepair) then begin
    if ValidModel(LegacyModelPath) then DeleteFile(LegacyModelPath);
  end;
#ifndef TestInstall
  if (CurStep = ssDone) and (not ModelNeedsRepair) then begin
    RemoveVerifiedLegacyModel(ExpandConstant('{localappdata}\DeepFind\models\eg2-text.onnx'));
    RemoveVerifiedLegacyModel(ExpandConstant('{commonappdata}\DeepFind\models\eg2-text.onnx'));
    { These are obsolete program dependencies, never source documents/vaults. }
    DelTree(ExpandConstant('{app}\_internal\transformers'), True, True, True);
    DelTree(ExpandConstant('{app}\_internal\tokenizers'), True, True, True);
    DelTree(ExpandConstant('{app}\_internal\huggingface_hub'), True, True, True);
    DelTree(ExpandConstant('{app}\_internal\hf_xet'), True, True, True);
    DelTree(ExpandConstant('{app}\_internal\safetensors'), True, True, True);
    DeleteFile(ExpandConstant('{app}\_internal\cv2\opencv_videoio_ffmpeg4110_64.dll'));
  end;
#endif
end;
