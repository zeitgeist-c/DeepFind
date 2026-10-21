; Evrakçı kurulum betiği (Inno Setup 6). Surum build.py tarafindan ver.iss ile verilir.
; AppId SABİTTİR: asla değiştirme (yükseltme/kaldırma aynı uygulamayı bulmalı).
#define AppName "Evrakçı"
#include "ver.iss"
#ifdef TestPrevious
  #undef AppVersion
  #define AppVersion "0.9.0"
#endif
#ifdef TestInstall
  #define ModelDir "{app}\_internal\embedding"
#else
  #define ModelDir "{commonappdata}\Evrakçı\models"
#endif

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
Source: "..\build\embedding\embeddinggemma-2-Q8_0.gguf"; DestDir: "{#ModelDir}"; Flags: ignoreversion uninsneveruninstall; Check: ModelNeedsRepair
#endif
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Tasks: desktopicon
Name: "{group}\{#AppName} kaldır"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Description: "{#AppName}'ı başlat"; Flags: nowait postinstall skipifsilent

[Code]
function ModelNeedsRepair: Boolean;
var ModelPath: String;
begin
#ifdef TestInstall
  ModelPath := ExpandConstant('{param:DIR}\_internal\embedding\embeddinggemma-2-Q8_0.gguf');
#else
  ModelPath := ExpandConstant('{commonappdata}\Evrakçı\models\embeddinggemma-2-Q8_0.gguf');
#endif
  Result := True;
  if FileExists(ModelPath) then
    Result := CompareText(GetSHA256OfFile(ModelPath), '2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135') <> 0;
end;

function InitializeSetup: Boolean;
begin
  Result := True;
#ifdef UpdatePackage
  if ModelNeedsRepair then begin
    MsgBox('Yerel model bulunamadı veya doğrulanamadı. Tam kurulum paketini kullanın.', mbError, MB_OK);
    Result := False;
  end;
#endif
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
