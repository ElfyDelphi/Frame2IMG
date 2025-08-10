# -*- mode: python ; coding: utf-8 -*-

import os

# Auto-detect optional Windows resources
icon_path = 'icon.ico' if os.path.exists('icon.ico') else None
version_file = 'file_version.txt' if os.path.exists('file_version.txt') else None
extra_exe_args = {}
if icon_path:
    extra_exe_args['icon'] = icon_path
if version_file:
    extra_exe_args['version'] = version_file


datas_list = [('icon.ico','.'), ('icon.png','.')]
if os.path.exists('bin/ffprobe.exe'):
    datas_list.append(('bin/ffprobe.exe', 'bin'))
if os.path.exists('bin/ffprobe'):
    datas_list.append(('bin/ffprobe', 'bin'))
# Include ffmpeg if present for FFmpeg-based extraction
if os.path.exists('bin/ffmpeg.exe'):
    datas_list.append(('bin/ffmpeg.exe', 'bin'))
if os.path.exists('bin/ffmpeg'):
    datas_list.append(('bin/ffmpeg', 'bin'))
if os.path.exists('licenses/FFmpeg-LGPL.txt'):
    datas_list.append(('licenses/FFmpeg-LGPL.txt', 'licenses'))
if os.path.exists('LICENSE'):
    datas_list.append(('LICENSE', '.'))

a = Analysis(
    ['frame_extractor_app.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Frame2IMG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    **extra_exe_args,
)
