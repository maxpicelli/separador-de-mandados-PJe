$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

python scripts\generate_windows_icon.py
pyinstaller windows_app\separador_windows.spec --noconfirm

# O PyInstaller (onefile) gera dist\Separador-de-Mandados-PJe.exe diretamente
$exePath = Join-Path $projectRoot 'dist\Separador-de-Mandados-PJe.exe'

if (-not (Test-Path $exePath)) {
    Write-Host 'Conteudo atual de dist:'
    Get-ChildItem -Path (Join-Path $projectRoot 'dist') -Recurse | Select-Object FullName
    throw 'PyInstaller nao gerou Separador-de-Mandados-PJe.exe em dist\.'
}

Write-Host "Build concluido. Executavel: $exePath"