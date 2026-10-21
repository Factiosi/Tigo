# Обновить токены Factiosi Umbrae в Tigo: копия python/umbrae.py из соседнего репозитория Factiosi.
# После синхронизации — python tools/build_brand.py и python tools/generate_icons.py, если менялся материал знаков.
param(
    [string]$FactiosiRoot = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "Factiosi")
)

$ErrorActionPreference = "Stop"
$source = Join-Path $FactiosiRoot "python\umbrae.py"
$dest = Join-Path (Split-Path $PSScriptRoot -Parent) "src\ui\theme\umbrae.py"
if (-not (Test-Path $source)) {
    throw "Factiosi Umbrae not found: $source. Run npm run tokens in Factiosi or pass -FactiosiRoot."
}
Copy-Item -Path $source -Destination $dest -Force
Write-Host "Copied $source -> $dest"
