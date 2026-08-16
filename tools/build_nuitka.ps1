# Build Tigo standalone with Nuitka.
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
    Write-Host "Generating icon assets..."
    Push-Location (Join-Path $Repo "tools")
    npm install --silent 2>$null
    node generate_icons.mjs
    Pop-Location
}

$fletVersion = & $Py -c "import flet; print(flet.version.flet_version)"
$fletCache = Join-Path $env:USERPROFILE ".flet\client\flet-desktop-full-$fletVersion"
$fletExe = Join-Path $fletCache "flet\flet.exe"
if (-not (Test-Path $fletExe)) {
    throw "Flet desktop client not found at $fletExe. Run 'python run.py' once to download it."
}

Write-Host "Building Tigo $Version with Nuitka..."
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

$buildArgs = @(
    "-m", "nuitka",
    "--standalone",
    "--assume-yes-for-downloads",
    "--output-dir=$DistRoot",
    "--output-filename=Tigo.exe",
    "--windows-icon-from-ico=$icon",
    "--windows-console-mode=disable",
    "--windows-uac-admin",
    "--product-name=Tigo",
    "--file-version=$Version",
    "--company-name=Tigo",
    "--include-data-dir=$(Join-Path $Repo 'icons')=icons",
    "--include-package=src",
    "--include-package=flet",
    "--include-package-data=flet",
    "--include-package=flet_desktop",
    "--include-package=httpx",
    "--include-package=httpcore",
    "--include-package=anyio",
    "--include-package=h11",
    "--include-package=certifi",
    "--include-package=idna",
    "--include-package=PIL",
    "--include-package=pystray",
    "--nofollow-import-to=tkinter",
    "--nofollow-import-to=unittest",
    "--nofollow-import-to=test",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=mcp",
    (Join-Path $Repo "run.py")
)

& $Py @buildArgs
if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed with exit code $LASTEXITCODE" }

$builtDir = Join-Path $DistRoot "run.dist"
if (-not (Test-Path $builtDir)) {
    $builtDir = Get-ChildItem $DistRoot -Directory | Where-Object { $_.Name -like "*.dist" } | Select-Object -First 1
    if ($builtDir) { $builtDir = $builtDir.FullName }
}
if (-not (Test-Path $builtDir)) { throw "Nuitka output directory not found in dist/" }

if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
Rename-Item $builtDir $OutDir

$exe = Join-Path $OutDir "Tigo.exe"
if (-not (Test-Path $exe)) {
    $legacy = Join-Path $OutDir "run.exe"
    if (Test-Path $legacy) { Rename-Item $legacy "Tigo.exe" }
}

$fletDest = Join-Path $OutDir "flet_client"
New-Item -ItemType Directory -Force -Path $fletDest | Out-Null
Copy-Item -Path (Join-Path $fletCache "flet\*") -Destination $fletDest -Recurse -Force

foreach ($intermediate in @("run.build", "run.onefile-build")) {
    $path = Join-Path $DistRoot $intermediate
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
    }
}

Write-Host "Building TigoUpdate splash..."
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
Copy-Item -Path (Join-Path $splashBuiltDir "TigoUpdate.exe") -Destination (Join-Path $OutDir "TigoUpdate.exe") -Force

foreach ($intermediate in @("update_splash_main.build", "update_splash_main.dist", "update_splash_main.onefile-build")) {
    $path = Join-Path $DistRoot $intermediate
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
    }
}

Write-Host ""
Write-Host "Build complete: $OutDir"
Write-Host "  Tigo.exe"
Write-Host "  TigoUpdate.exe"
Write-Host "  flet_client\flet.exe"
