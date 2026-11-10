"""Installer handoff keeps AppId, shortcuts and uninstall registration consistent.

The watcher script closes the app, its launcher and its own engine safely,
snapshots the install dir for rollback, runs the verified setup elevated,
then launches the new EXE and waits for its verified stamp. Until that stamp
appears the old version can be restored; failures relaunch the old version
so the user can retry from inside the app.
"""
from pathlib import Path
import ctypes
import os
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


def spawn_installer(pid, setup, current, vault):
    setup, current = Path(setup).resolve(), Path(current).resolve()
    destination = install_directory(current)
    version = '.'.join(map(str,windows_file_version(setup)))
    old_version = '.'.join(map(str,windows_file_version(current)))
    new_exe = destination / f'DeepFind-{version}.exe'
    rollback = setup.parent / f'rollback-{old_version}'
    stamp = setup.parent / 'son-guncelleme.txt'
    script = setup.parent / 'deepfind-install.ps1'
    def quote(text): return "'" + str(text).replace("'", "''") + "'"
    # Start-Process needs a correctly quoted single argument string for Inno.
    arguments = ('/SILENT /NORESTART /CLOSEAPPLICATIONS /DIR="' + str(destination)
                 + '" /LOG="' + str(setup.parent / 'kurulum.log') + '"')
    source = f'''$ErrorActionPreference = 'Stop'
$PID_ESKI = {int(pid)}
$KURULU = {quote(current)}
$HEDEF = {quote(destination)}
$KURULUM = {quote(setup)}
$YENI = {quote(new_exe)}
$ESKI_SURUM = {quote(old_version)}
$YENI_SURUM = {quote(version)}
$GERI = {quote(rollback)}
$DAMGA = {quote(stamp)}
$KASA = {quote(vault)}
$ARGSLAR = {quote(arguments)}
function Damga($deger) {{ Set-Content -LiteralPath $DAMGA -Value $deger -Encoding UTF8 }}
function Resim($p) {{ try {{ (Get-Process -Id $p -ErrorAction Stop).Path }} catch {{ '' }} }}
function EskiMi($p) {{
  $yol = Resim($p)
  if (-not $yol) {{ return $false }}
  return ($yol -eq $KURULU) -or ($yol -like ($HEDEF + '\\*'))
}}
function EskiCalistir {{
  $hedef = $KURULU
  if (-not (Test-Path -LiteralPath $hedef -PathType Leaf)) {{ return }}
  try {{
    $surum = (Get-Item -LiteralPath $hedef).VersionInfo.ProductVersion
    if ($surum -notlike ($ESKI_SURUM + '*')) {{ return }}
    Start-Process -FilePath $hedef -ArgumentList @('--restarted', '--kasa', $KASA)
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
  if (Test-Path -LiteralPath $GERI) {{ Remove-Item -LiteralPath $GERI -Recurse -Force -ErrorAction SilentlyContinue }}
  robocopy $HEDEF $GERI /MIR /R:2 /W:1 /NP /NFL /NDL | Out-Null
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
    robocopy $GERI $HEDEF /MIR /R:2 /W:1 /NP /NFL /NDL | Out-Null
    Damga('install_failed')
    EskiCalistir
    exit 0
  }}
  if (-not (Test-Path -LiteralPath $YENI -PathType Leaf)) {{
    robocopy $GERI $HEDEF /MIR /R:2 /W:1 /NP /NFL /NDL | Out-Null
    Damga('install_failed')
    EskiCalistir
    exit 0
  }}
  Start-Process -FilePath $YENI -ArgumentList @('--restarted', '--kasa', $KASA)
  $son = (Get-Date).AddSeconds(180)
  $dogrulandi = $false
  while ((Get-Date) -lt $son) {{
    if ((Test-Path -LiteralPath $DAMGA -PathType Leaf) -and ((Get-Content -LiteralPath $DAMGA -Raw -ErrorAction SilentlyContinue) -like ('verified:' + $YENI_SURUM + '*'))) {{
      $dogrulandi = $true
      break
    }}
    Start-Sleep -Seconds 2
  }}
  if ($dogrulandi) {{
    Remove-Item -LiteralPath $DAMGA -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $GERI -Recurse -Force -ErrorAction SilentlyContinue
    exit 0
  }}
  Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq $YENI }} | Stop-Process -Force -ErrorAction SilentlyContinue
  robocopy $GERI $HEDEF /MIR /R:2 /W:1 /NP /NFL /NDL | Out-Null
  Damga('restored')
  EskiCalistir
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
