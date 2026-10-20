; Evrakçı kurulum betiği (Inno Setup 6). Surum build.py tarafindan ver.iss ile verilir.
; AppId SABİTTİR: asla değiştirme (yükseltme/kaldırma aynı uygulamayı bulmalı).
#define AppName "Evrakçı"
#include "ver.iss"

[Setup]
AppId={{8E2B4F1A-3C7D-4E9A-B5F6-9A8C7D6E5F40}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Evrakçı
OutputDir=..
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=yes
OutputBaseFilename={#AppName}-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
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
Source: "..\dist\{#AppName}-{#AppVersion}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Tasks: desktopicon
Name: "{group}\{#AppName} kaldır"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppName}-{#AppVersion}.exe"; Description: "{#AppName}'ı başlat"; Flags: nowait postinstall skipifsilent
