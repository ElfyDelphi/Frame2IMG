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


a = Analysis(
    ['frame_extractor_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
