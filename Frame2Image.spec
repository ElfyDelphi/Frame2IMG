# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all

# App metadata
app_name = 'Frame2Image'
entry_script = 'app.py'

# Collect all PySide6 data/binaries/hidden imports (platform plugins, etc.)
datas, binaries, hiddenimports = collect_all('PySide6')

# Ensure OpenCV is discovered
hiddenimports += ['cv2']

# Bundle ffmpeg.exe and license files if present under third_party/ffmpeg
ffmpeg_dir = os.path.join('third_party', 'ffmpeg')
ffmpeg_path = os.path.join(ffmpeg_dir, 'bin', 'ffmpeg.exe')
if os.path.exists(ffmpeg_path):
    # Place next to the executable at runtime (PyInstaller onefile extracts to _MEIPASS)
    binaries.append((ffmpeg_path, '.'))
    # Include common license/readme files to comply with FFmpeg licensing
    for name in (
        'LICENSE', 'LICENSE.txt', 'LICENSE.md',
        'README', 'README.txt', 'README.md',
        'COPYING', 'COPYRIGHT'
    ):
        p = os.path.join(ffmpeg_dir, name)
        if os.path.exists(p):
            datas.append((p, 'licenses/ffmpeg'))

# Bundle ffprobe.exe if present
ffprobe_path = os.path.join(ffmpeg_dir, 'bin', 'ffprobe.exe')
if os.path.exists(ffprobe_path):
    binaries.append((ffprobe_path, '.'))

# Optional app icon (.ico)
icon_path = os.path.join('assets', 'icons', 'frame2image.ico')
icon_arg = icon_path if os.path.exists(icon_path) else None

block_cipher = None


a = Analysis(
    [entry_script],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Onefile GUI executable (no console)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
