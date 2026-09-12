#!/usr/bin/env python3
"""Create a desktop shortcut for the biofilm-embeddings-gui (biofilm-embeddings).

Works on Linux, macOS, and Windows. Mirrors the pattern used in
~/biofilm-processing/scripts/installDesktopShortcut.py.

Usage:
    python scripts/installDesktopShortcut.py
"""

import os
import sys
import shutil
import platform
import subprocess
import stat
from pathlib import Path


APP_NAME = 'biofilm-embeddings'
APP_DISPLAY = 'biofilm-embeddings'
APP_COMMENT = 'Biofilm phenotyping + DINOv2 ViT embedding extraction'
APP_BUNDLE_ID = 'edu.cmu.biofilm-embeddings'
APP_VERSION = '0.1.0'
GUI_BIN_NAME = 'biofilm-embeddings-gui'


def _findCondaBase():
    """Locate the conda BASE install (the one holding Scripts/activate.bat).

    Several routes, because no single one is reliable:

    * `conda info --base` fails in PowerShell, where `conda` is a shell FUNCTION
      rather than an executable subprocess can spawn.
    * CONDA_EXE is set by every conda shell hook and points at the base's own
      conda executable, so it survives that -- the most dependable signal.
    * Deriving from CONDA_PREFIX only works when envs live inside the base. With
      an ALL-USERS install the base is under C:\\ProgramData while envs land in
      %USERPROFILE%\\.conda\\envs (ProgramData is not user-writable), so stripping
      two components yields "<user>\\.conda" -- an env store, not an install.
    * The directory scan therefore has to include the system-wide locations.

    Returns None if nothing is found; callers must not assume success.
    """
    try:
        return subprocess.check_output(
            ['conda', 'info', '--base'], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        pass

    condaExe = os.environ.get('CONDA_EXE', '')
    if condaExe:
        candidate = os.path.dirname(os.path.dirname(condaExe))
        if _looksLikeCondaBase(candidate):
            return candidate

    prefix = os.environ.get('CONDA_PREFIX', '')
    if prefix:
        if _looksLikeCondaBase(prefix):          # base env itself is active
            return prefix
        candidate = os.path.dirname(os.path.dirname(prefix))
        if _looksLikeCondaBase(candidate):
            return candidate

    roots = [str(Path.home()), os.environ.get('LOCALAPPDATA', ''),
             os.environ.get('PROGRAMDATA', ''), 'C:\\ProgramData', 'C:\\']
    names = ['miniforge3', 'mambaforge', 'miniconda3', 'anaconda3', 'Miniconda3',
             'Anaconda3', 'opt/miniconda3', 'opt/anaconda3']
    for root in [r for r in roots if r]:
        for name in names:
            candidate = os.path.join(root, name)
            if _looksLikeCondaBase(candidate):
                return candidate

    return None


def _looksLikeCondaBase(path):
    """True if `path` is a conda INSTALL rather than merely an env directory.

    Checks for the activation entry point we need on this platform; an env store
    such as %USERPROFILE%\\.conda has neither.
    """
    if not path or not os.path.isdir(path):
        return False
    if platform.system() == 'Windows':
        return os.path.isfile(os.path.join(path, 'Scripts', 'activate.bat')) or \
               os.path.isfile(os.path.join(path, 'condabin', 'conda.bat'))
    return os.path.isfile(os.path.join(path, 'etc', 'profile.d', 'conda.sh'))


def _envNameFromBin(guiBin):
    """Extract the conda env name from a gui-bin path, or None."""
    parts = Path(guiBin).resolve().parts
    try:
        idx = parts.index('envs')
        return parts[idx + 1]
    except (ValueError, IndexError):
        return None


def findGuiBin():
    """Find the biofilm-embeddings-gui executable.

    Order matters: the ACTIVE environment wins. Scanning `envs/` alphabetically
    first (as this used to do) returns whichever env happens to sort earliest
    that has the script, ignoring the env the user actually ran this installer
    from. The sibling biofilm-processing repo hit exactly that: with both
    `biofilm-embeddings` and `biofilm-processing` envs present, its shortcut was
    wired to the alphabetically-first env and launched a different (pinned,
    older) install than the user intended. Check the active env first here.
    """
    for envVar in ('CONDA_PREFIX', 'VIRTUAL_ENV'):
        prefix = os.environ.get(envVar)
        if prefix:
            if platform.system() == 'Windows':
                candidate = os.path.join(prefix, 'Scripts', f'{GUI_BIN_NAME}.exe')
            else:
                candidate = os.path.join(prefix, 'bin', GUI_BIN_NAME)
            if os.path.isfile(candidate):
                return candidate

    gui = shutil.which(GUI_BIN_NAME)
    if gui:
        return gui

    condaBase = _findCondaBase()
    if condaBase:
        envsDir = os.path.join(condaBase, 'envs')
        if os.path.isdir(envsDir):
            names = sorted(os.listdir(envsDir))
            names.sort(key=lambda n: n != 'biofilm-embeddings')
            for envName in names:
                if platform.system() == 'Windows':
                    candidate = os.path.join(envsDir, envName, 'Scripts', f'{GUI_BIN_NAME}.exe')
                else:
                    candidate = os.path.join(envsDir, envName, 'bin', GUI_BIN_NAME)
                if os.path.isfile(candidate):
                    return candidate

    return None


def getDesktopDir():
    if platform.system() == 'Windows':
        return os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
    return os.path.join(Path.home(), 'Desktop')


def getIconPath(fmt='auto'):
    """Return path to the app icon in the requested format, or None.

    Searches assets/ in order: dora5.<fmt> (the canonical icon), then any
    standard name. fmt='auto' picks the first existing image of any common
    raster format (Linux .desktop accepts jpg/png/svg).
    """
    repoDir = Path(__file__).resolve().parent.parent
    assets = repoDir / 'assets'

    if fmt == 'icns':
        for name in ('dora5.icns', 'biofilm-embeddings-icon.icns'):
            p = assets / name
            if p.exists():
                return str(p)
        return None
    if fmt == 'ico':
        for name in ('dora5.ico', 'biofilm-embeddings-icon.ico'):
            p = assets / name
            if p.exists():
                return str(p)
        return None
    if fmt == 'png':
        for name in ('dora5.png', 'biofilm-embeddings-icon.png'):
            p = assets / name
            if p.exists():
                return str(p)
        return None

    # 'auto' — any raster image. Linux .desktop happily reads jpg/png.
    for name in ('dora5.png', 'dora5.jpg', 'dora5.jpeg',
                 'biofilm-embeddings-icon.png', 'biofilm-embeddings-icon.jpg'):
        p = assets / name
        if p.exists():
            return str(p)
    return None


def installLinux(guiBin):
    """Create .desktop file for Linux."""
    desktopDir = getDesktopDir()
    appDir = os.path.join(Path.home(), '.local', 'share', 'applications')

    envName = _envNameFromBin(guiBin) or os.environ.get('CONDA_DEFAULT_ENV')
    condaPrefix = os.environ.get('CONDA_PREFIX')
    venv = os.environ.get('VIRTUAL_ENV')

    if condaPrefix and envName:
        condaBase = _findCondaBase() or os.path.join(str(Path.home()), 'anaconda3')
        execLine = (
            f'bash -c \'source "{condaBase}/etc/profile.d/conda.sh" '
            f'&& conda activate {envName} && {GUI_BIN_NAME}\''
        )
    elif venv:
        execLine = f'bash -c \'source "{venv}/bin/activate" && {GUI_BIN_NAME}\''
    else:
        execLine = guiBin

    iconPath = getIconPath('auto')
    iconLine = f'Icon={iconPath}\n' if iconPath else ''

    desktopEntry = (
        '[Desktop Entry]\n'
        f'Name={APP_DISPLAY}\n'
        f'Comment={APP_COMMENT}\n'
        f'Exec={execLine}\n'
        'Terminal=false\n'
        'Type=Application\n'
        'Categories=Science;Education;\n'
        f'{iconLine}'
    )

    os.makedirs(appDir, exist_ok=True)
    appPath = os.path.join(appDir, f'{APP_NAME.lower()}.desktop')
    with open(appPath, 'w') as f:
        f.write(desktopEntry)
    os.chmod(appPath, os.stat(appPath).st_mode | stat.S_IXUSR)
    print(f'Created: {appPath}')

    if os.path.isdir(desktopDir):
        deskPath = os.path.join(desktopDir, f'{APP_NAME.lower()}.desktop')
        with open(deskPath, 'w') as f:
            f.write(desktopEntry)
        os.chmod(deskPath, os.stat(deskPath).st_mode | stat.S_IXUSR)
        print(f'Created: {deskPath}')

        if shutil.which('gio'):
            subprocess.run(
                ['gio', 'set', deskPath, 'metadata::trusted', 'true'],
                capture_output=True
            )


def installMacos(guiBin):
    """Create a .app bundle for macOS."""
    desktopDir = getDesktopDir()
    logPath = os.path.join(Path.home(), 'Library', 'Logs', f'{APP_NAME}.log')

    envName = _envNameFromBin(guiBin) or os.environ.get('CONDA_DEFAULT_ENV')
    condaPrefix = os.environ.get('CONDA_PREFIX')
    venv = os.environ.get('VIRTUAL_ENV')
    guiBinAbs = os.path.realpath(guiBin)

    activateLines = ''
    if condaPrefix and envName:
        condaBase = _findCondaBase()
        if condaBase:
            activateLines = (
                '# Activate conda environment\n'
                f'source "{condaBase}/etc/profile.d/conda.sh"\n'
                f'conda activate {envName}\n'
            )
    elif venv:
        activateLines = f'source "{venv}/bin/activate"\n'

    appDirRoot = os.path.join(desktopDir, f'{APP_NAME}.app')
    macosDir = os.path.join(appDirRoot, 'Contents', 'MacOS')
    os.makedirs(macosDir, exist_ok=True)

    launcher = os.path.join(macosDir, APP_NAME.lower())
    with open(launcher, 'w') as f:
        f.write('#!/bin/zsh\n')
        f.write(f'# {APP_DISPLAY} launcher; errors logged to {logPath}\n')
        f.write(f'exec >> "{logPath}" 2>&1\n')
        f.write('echo "--- $(date) ---"\n')
        f.write('echo "PATH=$PATH"\n\n')
        f.write(activateLines)
        f.write(f'\n# Try {GUI_BIN_NAME} on PATH, then fall back to absolute path\n')
        f.write(f'if command -v {GUI_BIN_NAME} &>/dev/null; then\n')
        f.write(f'    {GUI_BIN_NAME}\n')
        f.write('else\n')
        f.write(f'    "{guiBinAbs}"\n')
        f.write('fi\n')
    os.chmod(launcher, 0o755)

    contentsDir = os.path.join(appDirRoot, 'Contents')
    with open(os.path.join(contentsDir, 'Info.plist'), 'w') as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '  <key>CFBundleName</key>\n'
            f'  <string>{APP_DISPLAY}</string>\n'
            '  <key>CFBundleExecutable</key>\n'
            f'  <string>{APP_NAME.lower()}</string>\n'
            '  <key>CFBundleIdentifier</key>\n'
            f'  <string>{APP_BUNDLE_ID}</string>\n'
            '  <key>CFBundleVersion</key>\n'
            f'  <string>{APP_VERSION}</string>\n'
            '  <key>CFBundleIconFile</key>\n'
            f'  <string>{APP_NAME.lower()}-icon</string>\n'
            '  <key>LSUIElement</key>\n'
            '  <false/>\n'
            '</dict>\n'
            '</plist>\n'
        )

    resDir = os.path.join(contentsDir, 'Resources')
    os.makedirs(resDir, exist_ok=True)
    icnsPath = getIconPath('icns')
    pngPath = getIconPath('png') or getIconPath('auto')
    if icnsPath:
        shutil.copy2(icnsPath, os.path.join(resDir, f'{APP_NAME.lower()}-icon.icns'))
    if pngPath:
        # copy whatever raster icon we have; macOS Finder will use it as a fallback
        ext = os.path.splitext(pngPath)[1]
        shutil.copy2(pngPath, os.path.join(resDir, f'{APP_NAME.lower()}-icon{ext}'))

    print(f'Created: {appDirRoot}')
    print(f'Errors will be logged to: {logPath}')
    print()
    print('If double-clicking does nothing, check the log above.')
    print('If macOS blocks it: right-click the app > Open > Open.')
    if not icnsPath:
        print('Note: no .icns file found in assets/. The Finder may show a generic icon.')
        print('To use dora5.jpg as the Finder icon, convert it: '
              '`sips -s format icns assets/dora5.jpg --out assets/dora5.icns`')


def installWindows(guiBin):
    """Create a .bat launcher and a Start Menu shortcut for Windows."""
    desktopDir = getDesktopDir()

    envName = _envNameFromBin(guiBin) or os.environ.get('CONDA_DEFAULT_ENV')
    condaBase = _findCondaBase()
    venv = os.environ.get('VIRTUAL_ENV')

    # Launch the executable by ABSOLUTE PATH and set PATH ourselves, rather than
    # relying on `conda activate`. guiBin is already resolved, so activation was
    # never load-bearing -- and it is the fragile part: with an all-users conda
    # install `_findCondaBase()` can legitimately return None, and the launcher
    # was then written with NO activation line, failing with
    # "'GUI' is not recognized as an internal or external command".
    # Scripts + Library\\bin + the env root are what activation would prepend;
    # including them keeps conda-provided DLLs (Qt, MKL) reachable.
    envDir = os.path.dirname(os.path.dirname(guiBin))     # ...\\envs\\<name>
    lines = [
        '@echo off\n',
        f'set "ENVDIR={envDir}"\n',
        'set "PATH=%ENVDIR%;%ENVDIR%\\Scripts;%ENVDIR%\\Library\\bin;%PATH%"\n',
    ]
    # Best-effort activation on top, when a base was actually located: it sets
    # the conda-managed variables some packages expect. The launch below does
    # not depend on it succeeding.
    if condaBase and envName:
        lines.append(f'call "{condaBase}\\Scripts\\activate.bat" {envName} 2>nul\n')
    elif venv:
        lines.append(f'call "{venv}\\Scripts\\activate.bat" 2>nul\n')
    lines.append(f'"{guiBin}"\n')
    # Keep the window up on failure: the .lnk is created minimized, so without
    # this any startup error vanishes with the closing console.
    lines.append('if errorlevel 1 pause\n')

    appDataDir = os.path.join(os.environ.get('APPDATA', ''), APP_NAME)
    os.makedirs(appDataDir, exist_ok=True)
    batPath = os.path.join(appDataDir, f'{APP_NAME}.bat')
    with open(batPath, 'w') as f:
        f.writelines(lines)
    print(f'Created launcher: {batPath}')

    lnkPath = os.path.join(desktopDir, f'{APP_NAME}.lnk')
    iconPath = getIconPath('ico')
    iconArg = f'$s.IconLocation = "{iconPath}"; ' if iconPath else ''
    psScript = (
        '$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{lnkPath}"); '
        f'$s.TargetPath = "{batPath}"; '
        f'$s.Description = "{APP_DISPLAY} - {APP_COMMENT}"; '
        f'{iconArg}'
        '$s.WindowStyle = 7; '
        '$s.Save()'
    )
    try:
        subprocess.run(
            ['powershell', '-Command', psScript],
            capture_output=True, check=True
        )
        print(f'Created shortcut: {lnkPath}')
        if not iconPath:
            print('Note: no .ico file found in assets/. Windows will show a default icon.')
            print('To use dora5.jpg as the Windows icon, convert it: '
                  '`magick convert assets/dora5.jpg -define icon:auto-resize=256,128,64,48,32,16 assets/dora5.ico`')
    except Exception:
        fallback = os.path.join(desktopDir, f'{APP_NAME}.bat')
        shutil.copy2(batPath, fallback)
        print(f'Created: {fallback} (could not create .lnk shortcut)')


def main():
    guiBin = findGuiBin()
    if not guiBin:
        print(f'Error: {GUI_BIN_NAME} not found.')
        print('Make sure you have run: pip install -e .')
        print('And that your conda/virtualenv is activated.')
        sys.exit(1)

    print(f'Found {GUI_BIN_NAME} at: {guiBin}')
    envName = _envNameFromBin(guiBin)
    if envName:
        print(f'Detected conda env: {envName}')

    iconPath = getIconPath('auto')
    if iconPath:
        print(f'Using icon: {iconPath}')
    else:
        print('No icon found in assets/ (expected dora5.jpg or dora5.png).')

    system = platform.system()
    if system == 'Linux':
        installLinux(guiBin)
    elif system == 'Darwin':
        installMacos(guiBin)
    elif system == 'Windows':
        installWindows(guiBin)
    else:
        print(f'Unsupported platform: {system}')
        sys.exit(1)

    print(f'\n{APP_DISPLAY} shortcut installed.')
    print('You can launch it from your desktop or application menu.')


if __name__ == '__main__':
    main()
