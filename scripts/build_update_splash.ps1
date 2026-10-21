# Сборка TigoUpdate (окно самообновления) в scripts/release_assets/TigoUpdate/.
# Папка не коммитится; build_nuitka.ps1 кладёт её в dist\Tigo\updater\.
# Пересобирать при изменении src/update_splash/ и поднимать UPDATER_REVISION в splash_launcher.py.
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

$DistRoot = Join-Path $Repo "dist"
$AssetDir = Join-Path $Repo "scripts\release_assets\TigoUpdate"
$icon = Join-Path $Repo "assets\icons\app.ico"
if (-not (Test-Path $icon)) {
    throw "assets\icons\app.ico is required."
}
$revision = (Select-String -Path (Join-Path $Repo "src\modules\updates\splash_launcher.py") -Pattern 'UPDATER_REVISION\s*=\s*(\d+)').Matches[0].Groups[1].Value

Write-Host "Building TigoUpdate revision $revision with Nuitka..."
$splashArgs = @(
    "-m", "nuitka",
    "--standalone",
    "--assume-yes-for-downloads",
    "--output-dir=$DistRoot",
    "--output-filename=TigoUpdate.exe",
    "--windows-icon-from-ico=$icon",
    "--windows-console-mode=disable",
    "--product-name=Tigo Update",
    "--file-version=$revision.0.0.0",
    "--product-version=$revision.0.0.0",
    "--company-name=Tigo",
    "--include-module=src.update_splash.app",
    "--include-module=src.update_splash.worker",
    "--include-module=src.ui.theme.umbrae",
    "--include-data-files=$(Join-Path $Repo 'assets\fonts\Inter.ttf')=Inter.ttf",
    "--include-data-files=$(Join-Path $Repo 'assets\icons\mark-dark.png')=mark-dark.png",
    "--include-data-files=$icon=app.ico",
    "--nofollow-import-to=tkinter",
    "--nofollow-import-to=unittest",
    "--nofollow-import-to=test",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=mcp",
    "--nofollow-import-to=flet",
    "--nofollow-import-to=httpx",
    (Join-Path $Repo "src\update_splash\main.py")
)

& $Py @splashArgs
if ($LASTEXITCODE -ne 0) { throw "Nuitka TigoUpdate build failed with exit code $LASTEXITCODE" }

$built = Join-Path $DistRoot "main.dist"
if (-not (Test-Path (Join-Path $built "TigoUpdate.exe"))) { throw "TigoUpdate.exe not found in $built" }

if (Test-Path $AssetDir) { Remove-Item -Recurse -Force $AssetDir }
New-Item -ItemType Directory -Force -Path (Split-Path $AssetDir) | Out-Null
Move-Item $built $AssetDir
$buildDir = Join-Path $DistRoot "main.build"
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }

Write-Host "Saved: $AssetDir"
