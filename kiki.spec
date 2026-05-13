# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
project_root = os.path.abspath(".")

a = Analysis(
    [os.path.join('src', 'kiki', 'main.py')],  # Cross-platform path
    pathex=[],
    binaries=[],
    datas=[
        # (Source folder on your PC, Destination folder inside the build)
        (os.path.join('assets', 'models'), 'models'),
    ],
    hiddenimports=['onnxruntime', 'tokenizers'],
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
    [],
    exclude_binaries=True,
    name='kiki',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to True if you want a terminal window for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=os.path.join('assets', 'icon.ico'), # Uncomment when you add an icon!
)

# COLLECT creates the Folder Mode build (Instant boot times!)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kiki'
)