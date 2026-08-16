# Optional one-off build for TigoUpdate.exe (shipped only in release 1.3.0).
# Source stays in the repo; regular Tigo releases no longer bundle this binary.
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

$DistRoot = Join-Path $Repo "dist"
$OutDir = Join-Path $DistRoot "Tigo"
$VersionFile = Join-Path $Repo "src\core\version.py"
$Version = "1.0.0.0"
if (Test-Path $VersionFile) {
    $match = Select-String -Path $VersionFile -Pattern '__version__\s*=\s*"([^"]+)"'
    if ($match) {
        $Version = ($match.Matches[0].Groups[1].Value + ".0")
    }
}

$icon = Join-Path $Repo "icons\app.ico"
if (-not (Test-Path $icon)) {
    throw "icons\app.ico is required."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Building TigoUpdate $Version with Nuitka..."
$splashArgs = @(
    "-m", "nuitka",
    "--standalone",
    "--assume-yes-for-downloads",
    "--output-dir=$DistRoot",
    "--output-filename=TigoUpdate.exe",
    "--windows-icon-from-ico=$icon",
    "--windows-console-mode=disable",
    "--product-name=Tigo Update",
    "--file-version=$Version",
    "--company-name=Tigo",
    "--include-module=src.modules.updates.splash_status",
    "--include-module=src.update_splash.app",
    "--nofollow-import-to=tkinter",
    "--nofollow-import-to=unittest",
    "--nofollow-import-to=test",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=mcp",
    "--nofollow-import-to=flet",
    (Join-Path $Repo "update_splash_main.py")
)

& $Py @splashArgs
if ($LASTEXITCODE -ne 0) { throw "Nuitka splash build failed with exit code $LASTEXITCODE" }

$splashBuiltDir = Join-Path $DistRoot "update_splash_main.dist"
if (-not (Test-Path $splashBuiltDir)) {
    $splashBuiltDir = Get-ChildItem $DistRoot -Directory | Where-Object { $_.Name -like "update_splash_main*.dist" } | Select-Object -First 1
    if ($splashBuiltDir) { $splashBuiltDir = $splashBuiltDir.FullName }
}
if (-not (Test-Path $splashBuiltDir)) { throw "Nuitka splash output directory not found in dist/" }

$splashExe = Join-Path $splashBuiltDir "TigoUpdate.exe"
if (-not (Test-Path $splashExe)) {
    $legacySplash = Join-Path $splashBuiltDir "update_splash_main.exe"
    if (Test-Path $legacySplash) { Rename-Item $legacySplash "TigoUpdate.exe" }
}

Copy-Item -Path $splashExe -Destination (Join-Path $OutDir "TigoUpdate.exe") -Force

foreach ($intermediate in @("update_splash_main.build", "update_splash_main.dist", "update_splash_main.onefile-build")) {
    $path = Join-Path $DistRoot $intermediate
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
    }
}

Write-Host "TigoUpdate.exe -> $OutDir"
