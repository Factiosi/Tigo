param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$ReleaseNotes = "",
    [switch]$Publish,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Repo ".venv\Scripts\python.exe"
$BuildScript = Join-Path $PSScriptRoot "build_nuitka.ps1"
$InstallerScript = Join-Path $PSScriptRoot "tigo_installer.iss"
$Dist = Join-Path $Repo "dist"
$Standalone = Join-Path $Dist "Tigo"
$InstallerDir = Join-Path $Dist "installer"
$Installer = Join-Path $InstallerDir "Tigo-Setup-$Version.exe"
$Checksum = "$Installer.sha256"
$Tag = "v$Version"
$Iscc = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

if ($Publish -and $DryRun) {
    throw "Use either -Publish or -DryRun, not both."
}

Set-Location $Repo
Assert-True (Test-Path $Py) "Python venv not found: $Py"
Assert-True (Test-Path $Iscc) "Inno Setup compiler not found: $Iscc"
Assert-True (Test-Path $BuildScript) "Build script not found."
Assert-True (Test-Path $InstallerScript) "Installer script not found."

$SourceVersion = & $Py -c "from src.core.version import __version__; print(__version__)"
Assert-True ($SourceVersion -eq $Version) "src/core/version.py is $SourceVersion, expected $Version."
$IssText = Get-Content $InstallerScript -Raw
Assert-True ($IssText -match "#define MyAppVersion `"$([regex]::Escape($Version))`"") "Inno version does not match $Version."
if ($Publish -and -not $ReleaseNotes.Trim()) {
    throw "Pass -ReleaseNotes for -Publish."
}

$Branch = (git branch --show-current).Trim()
Assert-True ($Branch -eq "master") "Release must run from master, current branch: $Branch"
if ($Publish) {
    Assert-True (-not (git status --porcelain)) "Working tree must be clean before publishing."
    Invoke-Checked "gh" @("auth", "status")
    $LocalTag = git tag --list $Tag
    Assert-True (-not $LocalTag) "Tag $Tag already exists locally."
    $RemoteTag = git ls-remote --tags origin "refs/tags/$Tag"
    Assert-True (-not $RemoteTag) "Tag $Tag already exists on origin."
}

Write-Host "Running tests..."
Invoke-Checked $Py @("-m", "unittest", "discover", "-s", "tests", "-v")

Remove-Item Env:TIGO_AUTOMATION -ErrorAction SilentlyContinue
$ReleaseProcesses = Get-CimInstance Win32_Process -Filter "Name = 'Tigo.exe'" |
    Where-Object { $_.ExecutablePath -like "$Standalone*" }
Assert-True (-not $ReleaseProcesses) "A Tigo process from dist is running. Close it before release build."

Write-Host "Building standalone..."
Invoke-Checked "powershell" @("-ExecutionPolicy", "Bypass", "-File", $BuildScript)

$Required = @(
    (Join-Path $Standalone "Tigo.exe"),
    (Join-Path $Standalone "TigoUpdate.exe"),
    (Join-Path $Standalone "flet_client\flet.exe"),
    (Join-Path $Standalone "icons\app.ico")
)
foreach ($Path in $Required) {
    Assert-True (Test-Path $Path) "Required release file is missing: $Path"
}
foreach ($Forbidden in @("bin", "utils", "lists", "runtime-version.txt")) {
    Assert-True (-not (Test-Path (Join-Path $Standalone $Forbidden))) "Forbidden runtime found in release: $Forbidden"
}
$McpFiles = Get-ChildItem $Standalone -Recurse -Force |
    Where-Object { $_.Name -match "(?i)mcp" }
Assert-True (-not $McpFiles) "MCP files found in final standalone."

if (Test-Path $InstallerDir) {
    Remove-Item $InstallerDir -Recurse -Force
}
New-Item $InstallerDir -ItemType Directory -Force | Out-Null
Write-Host "Building installer..."
Invoke-Checked $Iscc @($InstallerScript)
Assert-True (Test-Path $Installer) "Installer was not created: $Installer"

$Hash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $(Split-Path $Installer -Leaf)" | Set-Content $Checksum -Encoding ascii
Assert-True (Test-Path $Checksum) "Checksum file was not created."

Write-Host "Release artifact verified:"
Write-Host "  $Installer"
Write-Host "  $Checksum"

if ($DryRun -or -not $Publish) {
    Write-Host "Dry run complete. Git and GitHub were not changed."
    exit 0
}

Write-Host "Publishing $Tag..."
Invoke-Checked "git" @("push", "origin", "master")
Invoke-Checked "gh" @(
    "repo", "edit", "Factiosi/Tigo",
    "--visibility", "public",
    "--accept-visibility-change-consequences"
)
Invoke-Checked "git" @("tag", "-a", $Tag, "-m", "Tigo $Version")
Invoke-Checked "git" @("push", "origin", $Tag)

$NotesFile = Join-Path $env:TEMP "tigo-release-$Version.md"
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText(
    $NotesFile,
    $ReleaseNotes.Trim(),
    $Utf8NoBom
)
try {
    Invoke-Checked "gh" @(
        "release", "create", $Tag,
        $Installer, $Checksum,
        "--repo", "Factiosi/Tigo",
        "--title", "Tigo $Version",
        "--notes-file", $NotesFile,
        "--verify-tag"
    )
}
finally {
    Remove-Item $NotesFile -Force -ErrorAction SilentlyContinue
}

Write-Host "Published: https://github.com/Factiosi/Tigo/releases/tag/$Tag"
