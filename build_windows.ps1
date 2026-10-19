$ErrorActionPreference = "Stop"
python -m PyInstaller --noconfirm --clean --onedir --console --name ProcesadorArchivos app.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$packageDir = Join-Path $PSScriptRoot "dist\ProcesadorArchivos"
$carteraDir = Join-Path $packageDir "folders\Cartera"
$sgaDir = Join-Path $packageDir "folders\SGA"
New-Item -ItemType Directory -Force -Path $carteraDir, $sgaDir | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "folders\Cartera\LEEME.txt") -Destination $carteraDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "folders\SGA\LEEME.txt") -Destination $sgaDir
Write-Host "Paquete listo en: $packageDir"
