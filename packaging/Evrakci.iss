; Evrakçı kurulum betiği (Inno Setup 6). Surum build.py tarafindan ver.iss ile verilir.
; AppId SABİTTİR: asla değiştirme (yükseltme/kaldırma aynı uygulamayı bulmalı).
#define AppName "Evrakçı"
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
AppPublisher=Evrakçı
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
DefaultGroupName=Evrakçı kabul testi
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
SetupIconFile=..\build\evrakci.ico
LicenseFile=..\LISANSLAR.md

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü simgesi oluştur"; Flags: unchecked

[Files]
Source: "..\dist\{#AppName}-{#AppVersion}\*"; DestDir: "{app}"; Excludes: "_internal\embedding\embeddinggemma-2-Q8_0.gguf"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifndef UpdatePackage
#ifndef TestPrevious
Source: "..\build\embedding\embeddinggemma-2-Q8_0.gguf"; DestDir: "{#ModelDir}"; Flags: ignoreversion; Check: ModelNeedsRepair
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
Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Description: "{#AppName}'ı başlat"; Flags: nowait postinstall skipifsilent

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
  Result := ExpandConstant('{commonappdata}\Evrakçı\models\embeddinggemma-2-Q8_0.gguf');
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
  if FindFirst(ExpandConstant('{app}\Evrakçı-*.exe'), Entry) then begin
    try
      repeat
        Stem := ChangeFileExt(Entry.Name, '');
        VersionText := Copy(Stem, Length('Evrakçı-') + 1, MaxInt);
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssDone) and (not ModelNeedsRepair) then begin
    CleanupOldLaunchers;
    if ValidModel(LegacyModelPath) then DeleteFile(LegacyModelPath);
  end;
#ifndef TestInstall
  if (CurStep = ssDone) and (not ModelNeedsRepair) then begin
    RemoveVerifiedLegacyModel(ExpandConstant('{localappdata}\Evrakçı\models\eg2-text.onnx'));
    RemoveVerifiedLegacyModel(ExpandConstant('{commonappdata}\Evrakçı\models\eg2-text.onnx'));
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
