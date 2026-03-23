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

# Excluir módulos Qt e bibliotecas não utilizados para reduzir tamanho e acelerar inicialização
excludes = [
    # Qt Web
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    # Qt Multimedia
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    # Qt 3D
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    # Qt Charts / DataViz
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    # Qt QML / Quick
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtQml",
    # Qt hardware / conectividade
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    # Qt extras não necessários
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtNetwork",
    "PySide6.QtRemoteObjects",
    "PySide6.QtStateMachine",
    "PySide6.QtSpatialAudio",
    # Bibliotecas Python pesadas não utilizadas
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "IPython",
    "notebook",
    "tkinter",
    "unittest",
    "xmlrpc",
    "distutils",
]


a = Analysis(
    [str(app_root / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=APP_EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
    onefile=True,
)
