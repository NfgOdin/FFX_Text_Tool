# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['FFX_Text_Tool.py'],
    pathex=[],
    binaries=[],
    datas=[('FFXTextTool.ico', '.'), ('default_macros.json', '.'), ('ffx_encoding', 'ffx_encoding')],
    hiddenimports=['canonical_lore', 'ffx_codec'],
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
    name='FFX_Text_Tool',
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
    version='ffx_text_tool_version.txt',
    icon='FFXTextTool.ico',
)
