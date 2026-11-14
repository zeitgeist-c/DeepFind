"""Installer handoff keeps AppId, shortcuts and uninstall registration consistent.

The watcher waits for the application to exit, launches the verified setup
elevated, and waits for the new version's startup stamp. For an installed copy,
a failed upgrade can reinstall the verified previous release through UAC.
"""
from pathlib import Path
import ctypes
import os
import re
import subprocess


def windows_file_version(path):
    from ctypes import wintypes
    dll = ctypes.windll.version
    size = dll.GetFileVersionInfoSizeW(str(path), None)
    if not size: raise ValueError('EXE sürüm kaydı bulunamadı')
    data = ctypes.create_string_buffer(size)
    if not dll.GetFileVersionInfoW(str(path), 0, size, data): raise ValueError('EXE sürümü okunamadı')
    ptr = ctypes.c_void_p(); length = wintypes.UINT()
    if not dll.VerQueryValueW(data, '\\', ctypes.byref(ptr), ctypes.byref(length)):
        raise ValueError('EXE sürümü çözülemedi')
    values = ctypes.cast(ptr, ctypes.POINTER(wintypes.DWORD))
    return (values[2] >> 16, values[2] & 65535, values[3] >> 16)


def install_directory(current):
    current = Path(current).resolve()
    for parent in [current.parent, current.parent.parent]:
        if (parent / 'unins000.exe').is_file(): return parent
    import winreg
    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8E2B4F1A-3C7D-4E9A-B5F6-9A8C7D6E5F40}_is1'
    for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        try:
            with winreg.OpenKey(hive,key,0,winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
                location,_ = winreg.QueryValueEx(handle,'InstallLocation')
                root=Path(location)
                if root.is_absolute() and (root/'unins000.exe').is_file(): return root
        except OSError:
            continue
    return Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'DeepFind'


def is_installed_exe(current: Path) -> bool:
    current = Path(current).resolve()
    return any((parent / "unins000.exe").is_file()
               for parent in (current.parent, current.parent.parent))


def spawn_installer(pid, setup, current, vault, *, recovery=None):
    setup, current = Path(setup).resolve(), Path(current).resolve()
    destination = install_directory(current)
    version = '.'.join(map(str,windows_file_version(setup)))
    old_parts = windows_file_version(current)
    old_version = ".".join(map(str, old_parts))
    new_exe = destination / f'DeepFind-{version}.exe'
    installed = is_installed_exe(current)
    if installed and recovery is None:
        raise OSError("The installed release has no verified recovery installer.")
    recovery_path, recovery_hash = ("", "") if recovery is None else recovery
    if recovery is not None:
        recovery_path = Path(recovery_path).resolve(strict=True)
        if (not re.fullmatch(r"[0-9a-fA-F]{64}", recovery_hash)
                or recovery_path == setup
                or windows_file_version(recovery_path) != old_parts):
            raise OSError("The recovery installer does not match the installed release.")
    stamp = setup.parent / 'son-guncelleme.txt'
    script = setup.parent / 'deepfind-install.ps1'
    def quote(text): return "'" + str(text).replace("'", "''") + "'"
    # Start-Process needs a correctly quoted single argument string for Inno.
    arguments = ('/SILENT /NORESTART /CLOSEAPPLICATIONS /DIR="' + str(destination)
                 + '" /LOG="' + str(setup.parent / 'kurulum.log') + '"')
    recovery_arguments = ('/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /NOCLOSEAPPLICATIONS '
                          '/MERGETASKS="!fetchmodel" /DIR="' + str(destination)
                          + '" /LOG="' + str(setup.parent / 'geri-kurulum.log') + '"')
    source = f'''$ErrorActionPreference = 'Stop'
$PID_ESKI = {int(pid)}
$KURULU = {quote(current)}
$HEDEF = {quote(destination)}
$KURULUM = {quote(setup)}
$YENI = {quote(new_exe)}
$ESKI_SURUM = {quote(old_version)}
$YENI_SURUM = {quote(version)}
$GERI = {quote(recovery_path)}
$GERI_HASH = {quote(recovery_hash)}
$GERI_ARGLAR = {quote(recovery_arguments)}
$DAMGA = {quote(stamp)}
$KASA = {quote(vault)}
$ACILIS = '--restarted --kasa "' + $KASA + '"'
$ARGSLAR = {quote(arguments)}
function Damga($deger) {{ Set-Content -LiteralPath $DAMGA -Value $deger -Encoding UTF8 }}
function Resim($p) {{ try {{ (Get-Process -Id $p -ErrorAction Stop).Path }} catch {{ '' }} }}
function EskiMi($p) {{
  $yol = Resim($p)
  if (-not $yol) {{ return $false }}
  return ($yol -eq $KURULU) -or ($yol -like ($HEDEF + '\\*'))
}}
function BeklenenSurum($yol, $surum) {{
  if (-not (Test-Path -LiteralPath $yol -PathType Leaf)) {{ return $false }}
  $v = (Get-Item -LiteralPath $yol -ErrorAction Stop).VersionInfo
  return ('{{0}}.{{1}}.{{2}}' -f $v.FileMajorPart, $v.FileMinorPart, $v.FileBuildPart) -eq $surum
}}
function GeriYukle($basariDurumu) {{
  if (-not $GERI) {{
    Damga($basariDurumu)
    EskiCalistir
    return
  }}
  try {{
    if ((Get-FileHash -LiteralPath $GERI -Algorithm SHA256).Hash -ine $GERI_HASH) {{
      throw 'Recovery installer checksum mismatch'
    }}
    $geriKur = Start-Process -FilePath $GERI -ArgumentList $GERI_ARGLAR -Verb RunAs -Wait -PassThru
    if (($geriKur.ExitCode -ne 0) -or (-not (BeklenenSurum $KURULU $ESKI_SURUM))) {{
      throw 'Recovery installer did not restore the expected version'
    }}
    Damga($basariDurumu)
    EskiCalistir
  }} catch {{
    Damga('restore_failed')
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
      ("DeepFind geri yüklenemedi. Yönetici onayını kontrol edin. Kurulum paketi: " + $GERI),
      "DeepFind", 'OK', 'Error') | Out-Null
  }}
}}
function EskiCalistir {{
  $hedef = $KURULU
  if (-not (Test-Path -LiteralPath $hedef -PathType Leaf)) {{ return }}
  try {{
    if (-not (BeklenenSurum $hedef $ESKI_SURUM)) {{ return }}
    Start-Process -FilePath $hedef -ArgumentList ('--kasa "' + $KASA + '"')
  }} catch {{ }}
}}
try {{
  $son = (Get-Date).AddSeconds(300)
  while ((Get-Process -Id $PID_ESKI -ErrorAction SilentlyContinue) -and (EskiMi($PID_ESKI)) -and ((Get-Date) -lt $son)) {{ Start-Sleep -Seconds 2 }}
  if ((Get-Process -Id $PID_ESKI -ErrorAction SilentlyContinue) -and (EskiMi($PID_ESKI))) {{
    Damga('timeout')
    EskiCalistir
    exit 0
  }}
  $son = (Get-Date).AddSeconds(60)
  while (((Get-Date) -lt $son) -and @(Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like ($HEDEF + '\\*') }}).Count -gt 0) {{ Start-Sleep -Seconds 2 }}
  if (@(Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like ($HEDEF + '\\*') }}).Count -gt 0) {{
    Damga('timeout')
    EskiCalistir
    exit 0
  }}
  if ($GERI) {{
    try {{
      if ((Get-FileHash -LiteralPath $GERI -Algorithm SHA256).Hash -ine $GERI_HASH) {{
        throw 'Recovery installer checksum mismatch'
      }}
    }} catch {{
      Damga('backup_failed')
      EskiCalistir
      exit 0
    }}
  }}
  if (Test-Path -LiteralPath $DAMGA) {{ Remove-Item -LiteralPath $DAMGA -Force }}
  try {{
    $kur = Start-Process -FilePath $KURULUM -ArgumentList $ARGSLAR -Verb RunAs -Wait -PassThru
  }} catch {{
    if ($_.Exception.HResult -eq -2147023673 -or $_.FullyQualifiedErrorId -like '*Cancelled*') {{
      Damga('uac_cancelled')
    }} else {{
      Damga('install_failed')
    }}
    EskiCalistir
    exit 0
  }}
  if ($kur.ExitCode -ne 0) {{
    GeriYukle 'install_failed'
    exit 0
  }}
  if (-not (BeklenenSurum $YENI $YENI_SURUM)) {{
    GeriYukle 'install_failed'
    exit 0
  }}
  try {{
    Start-Process -FilePath $YENI -ArgumentList $ACILIS
  }} catch {{
    GeriYukle 'install_failed'
    exit 0
  }}
  $son = (Get-Date).AddSeconds(180)
  $dogrulandi = $false
  while ((Get-Date) -lt $son) {{
    $onay = Get-Content -LiteralPath $DAMGA -Raw -ErrorAction SilentlyContinue
    if ($onay -and ($onay.Trim() -eq ('verified:' + $YENI_SURUM))) {{
      $dogrulandi = $true
      break
    }}
    Start-Sleep -Seconds 2
  }}
  if ($dogrulandi) {{
    Remove-Item -LiteralPath $DAMGA -Force -ErrorAction SilentlyContinue
    exit 0
  }}
  $aday = Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq $YENI }}
  if ($aday) {{
    $aday | Stop-Process -Force -ErrorAction SilentlyContinue
    $aday | Wait-Process -Timeout 15 -ErrorAction SilentlyContinue
  }}
  GeriYukle 'restored'
}} catch {{
  try {{ Damga('install_failed') }} catch {{ }}
  try {{ EskiCalistir }} catch {{ }}
}}
Remove-Item -LiteralPath $PSCommandPath -Force
'''
    script.write_text(source,encoding='utf-8-sig')
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.Popen([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), close_fds=True)
    return script
