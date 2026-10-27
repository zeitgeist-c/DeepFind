"""Installer handoff keeps AppId, shortcuts and uninstall registration consistent."""
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
    new_exe = destination / f'DeepFind-{version}.exe'
    script = setup.parent / 'deepfind-install.ps1'
    def quote(text): return "'" + str(text).replace("'", "''") + "'"
    # Start-Process needs a correctly quoted single argument string for Inno.
    arguments = ('/SILENT /NORESTART /CLOSEAPPLICATIONS /DIR="' + str(destination)
                 + '" /LOG="' + str(setup.parent / 'kurulum.log') + '"')
    source = f'''$ErrorActionPreference = 'Stop'
try {{
  if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{
    Wait-Process -Id {int(pid)} -Timeout 300 -ErrorAction Stop
  }}
  $install = Start-Process -FilePath {quote(setup)} -ArgumentList {quote(arguments)} -Verb RunAs -Wait -PassThru
  if ($install.ExitCode -ne 0) {{ throw 'Kurulum tamamlanamadı' }}
  if (-not (Test-Path -LiteralPath {quote(new_exe)} -PathType Leaf)) {{ throw 'Yeni program bulunamadı' }}
  Set-Content -LiteralPath {quote(setup.parent/'son-guncelleme.txt')} -Value 'ok' -Encoding UTF8
  Start-Process -FilePath {quote(new_exe)} -ArgumentList @('--restarted', '--kasa', {quote('"'+str(vault)+'"')})
}} catch {{
  Set-Content -LiteralPath {quote(setup.parent/'son-guncelleme.txt')} -Value 'install_failed' -Encoding UTF8
  $recover = {quote(current)}
  if (-not (Test-Path -LiteralPath $recover)) {{ $recover = {quote(new_exe)} }}
  if ((Test-Path -LiteralPath $recover) -and -not (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue)) {{
    Start-Process -FilePath $recover -ArgumentList @('--restarted', '--kasa', {quote('"'+str(vault)+'"')})
  }}
}}
Remove-Item -LiteralPath $PSCommandPath -Force
'''
    script.write_text(source,encoding='utf-8-sig')
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.Popen([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), close_fds=True)
    return script
