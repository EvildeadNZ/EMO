$ErrorActionPreference = "Stop"

$Root = Get-Location
$Main = Join-Path $Root "emo\main_window.py"
$Version = Join-Path $Root "emo\version.py"
$Manifest = Join-Path $Root "update-package.json"
$Notes = Join-Path $Root "docs\releases\5.0.0-m2.7-hf4.md"
$Zip = Join-Path $Root "EMP-5.0.0-m2.7-hf4-FIX1-Update.zip"

if (!(Test-Path $Main)) { throw "Cannot find emo\main_window.py. Run this from the EMP project root." }
if (!(Test-Path (Join-Path $Root "app.py"))) { throw "Cannot find app.py. Run this from the EMP project root." }

# Backup the current hotfix source before repairing its text encoding.
$BackupDir = Join-Path $Root "_hf4_encoding_backup"
New-Item -ItemType Directory -Force $BackupDir | Out-Null
Copy-Item $Main (Join-Path $BackupDir "main_window.py") -Force

# PowerShell 5.1 Get-Content previously decoded UTF-8 source using the Windows
# code page, producing classic mojibake such as â€™, â€“ and â€”.
# Repair only when the file contains those markers.
$bytes = [System.IO.File]::ReadAllBytes($Main)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)

$markers = @("â€™","â€œ","â€","â€“","â€”","â€¦","Â")
$hits = 0
foreach ($m in $markers) { $hits += ([regex]::Matches($text, [regex]::Escape($m))).Count }

if ($hits -gt 0) {
    try {
        $latin = [System.Text.Encoding]::GetEncoding(28591)
        $utf8 = [System.Text.Encoding]::UTF8
        $repaired = $utf8.GetString($latin.GetBytes($text))
        [System.IO.File]::WriteAllText($Main, $repaired, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "Repaired $hits mojibake markers in emo\main_window.py." -ForegroundColor Green
    }
    catch {
        Copy-Item (Join-Path $BackupDir "main_window.py") $Main -Force
        throw "Encoding repair failed. Original main_window.py restored."
    }
}
else {
    Write-Host "No mojibake markers detected in main_window.py."
}

# Ensure the release version remains correct without PowerShell text encoding.
[System.IO.File]::WriteAllText(
    $Version,
    'APP_VERSION = "5.0.0-m2.7-hf4"',
    (New-Object System.Text.UTF8Encoding($false))
)

# Validate Python syntax before packaging.
python -m py_compile $Main $Version
if ($LASTEXITCODE -ne 0) {
    Copy-Item (Join-Path $BackupDir "main_window.py") $Main -Force
    throw "Python syntax check failed. Original main_window.py restored."
}

# Rebuild the update package from the current project. Runtime/user data is excluded.
if (Test-Path $Zip) { Remove-Item $Zip -Force }

$Temp = Join-Path $env:TEMP ("EMP-hf4-fix1-" + [guid]::NewGuid().ToString())
$PackageRoot = Join-Path $Temp "EMP-5.0.0-m2.7-hf4-FIX1"
New-Item -ItemType Directory -Force $PackageRoot | Out-Null

$excludeNames = @(
    ".git",
    "_updates",
    "_hf4_encoding_backup",
    "cache",
    "__pycache__",
    "config.json",
    "history.json",
    "evils_media_optimizer.log"
)

Get-ChildItem -LiteralPath $Root -Force | Where-Object {
    $_.Name -notin $excludeNames -and
    $_.FullName -ne $Zip
} | ForEach-Object {
    Copy-Item $_.FullName $PackageRoot -Recurse -Force
}

Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $Zip -CompressionLevel Optimal
Remove-Item $Temp -Recurse -Force

Write-Host ""
Write-Host "HF4 FIX1 READY" -ForegroundColor Green
Write-Host "Version: 5.0.0-m2.7-hf4"
Write-Host "ZIP: $Zip"
Write-Host ""
Write-Host "This fixes the UTF-8/mojibake corruption caused by the previous build script."
