# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from windows_app import APP_EXE_NAME


project_root = Path(SPECPATH)
hiddenimports = collect_submodules("pdfplumber") + collect_submodules("pypdf")

icon_file = project_root / "windows_app" / "assets" / "app_icon.ico"
png_icon = project_root / "windows_app" / "assets" / "app_icon.png"
datas = [(str(png_icon), "windows_app/assets")] if png_icon.exists() else []

block_cipher = None


a = Analysis(
    [str(project_root / "windows_app" / "__main__.py")],
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
