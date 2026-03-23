# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


APP_EXE_NAME = "Separador-de-Mandados-PJe"


app_root = Path(SPECPATH)
project_root = app_root.parent
hiddenimports = collect_submodules("pdfplumber") + collect_submodules("pypdf")

icon_file = app_root / "assets" / "app_icon.ico"
png_icon = app_root / "assets" / "app_icon.png"
datas = [(str(png_icon), "windows_app/assets")] if png_icon.exists() else []

block_cipher = None


a = Analysis(
    [str(app_root / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_EXE_NAME,
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
    icon=str(icon_file) if icon_file.exists() else None,
)
