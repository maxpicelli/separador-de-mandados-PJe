$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

python scripts\generate_windows_icon.py
pyinstaller windows_app\separador_windows.spec --noconfirm

$expectedExe = Join-Path $projectRoot 'dist\Separador-de-Mandados-PJe.exe'
$recursiveExe = Get-ChildItem -Path (Join-Path $projectRoot 'dist') -Filter 'Separador-de-Mandados-PJe.exe' -Recurse -File | Select-Object -First 1

if (-not $recursiveExe) {
	Write-Host 'Conteudo atual de dist:'
	Get-ChildItem -Path (Join-Path $projectRoot 'dist') -Recurse | Select-Object FullName
	throw 'PyInstaller nao gerou Separador-de-Mandados-PJe.exe em nenhuma subpasta de dist.'
}

if ($recursiveExe.FullName -ne $expectedExe) {
	Copy-Item -Path $recursiveExe.FullName -Destination $expectedExe -Force
}

Write-Host 'Conteudo final de dist:'
Get-ChildItem -Path (Join-Path $projectRoot 'dist') -Recurse | Select-Object FullName
Write-Host "Build concluido em $expectedExe"