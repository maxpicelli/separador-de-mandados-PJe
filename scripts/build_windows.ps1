$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

python scripts\generate_windows_icon.py
pyinstaller windows_app\separador_windows.spec --noconfirm

Write-Host "Build concluído em dist\Separador-de-Mandados-PJe.exe"