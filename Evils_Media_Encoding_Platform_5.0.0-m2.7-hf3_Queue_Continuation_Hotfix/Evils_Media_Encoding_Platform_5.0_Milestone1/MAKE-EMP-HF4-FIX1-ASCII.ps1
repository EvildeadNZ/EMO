$ErrorActionPreference = "Stop"

$Root = Get-Location
$Main = Join-Path $Root "emo\main_window.py"
$Version = Join-Path $Root "emo\version.py"
$Zip = Join-Path $Root "EMP-5.0.0-m2.7-hf4-FIX1-Update.zip"
$BackupDir = Join-Path $Root "_hf4_encoding_backup2"

if (!(Test-Path $Main)) { throw "Cannot find emo\main_window.py. Run this from the EMP project root." }
if (!(Test-Path (Join-Path $Root "app.py"))) { throw "Cannot find app.py. Run this from the EMP project root." }

New-Item -ItemType Directory -Force $BackupDir | Out-Null
Copy-Item $Main (Join-Path $BackupDir "main_window.py") -Force

# Read the Python file as UTF-8 bytes.
$bytes = [System.IO.File]::ReadAllBytes($Main)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)

# The previous build script used Windows PowerShell text handling and created
# UTF-8 mojibake. Repair one mojibake layer when the tell-tale characters exist.
$bad1 = [char]0x00E2
$bad2 = [char]0x00C2
if ($text.Contains($bad1) -or $text.Contains($bad2)) {
    $cp1252 = [System.Text.Encoding]::GetEncoding(1252)
    $utf8 = [System.Text.Encoding]::UTF8
    $repaired = $utf8.GetString($cp1252.GetBytes($text))

    # If a second layer exists, repair it too.
    if ($repaired.Contains($bad1) -or $repaired.Contains($bad2)) {
        $repaired2 = $utf8.GetString($cp1252.GetBytes($repaired))
        $repaired = $repaired2
    }

    [System.IO.File]::WriteAllText($Main, $repaired, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "UTF-8 text repair completed." -ForegroundColor Green
}
else {
    Write-Host "No mojibake marker found; source encoding left unchanged."
}

[System.IO.File]::WriteAllText(
    $Version,
    'APP_VERSION = "5.0.0-m2.7-hf4"',
    (New-Object System.Text.UTF8Encoding($false))
)

python -m py_compile $Main $Version
if ($LASTEXITCODE -ne 0) {
    Copy-Item (Join-Path $BackupDir "main_window.py") $Main -Force
    throw "Python syntax check failed. Original main_window.py restored."
}

if (Test-Path $Zip) { Remove-Item $Zip -Force }

$Temp = Join-Path $env:TEMP ("EMP-hf4-fix1-" + [guid]::NewGuid().ToString())
$PackageRoot = Join-Path $Temp "EMP-5.0.0-m2.7-hf4-FIX1"
New-Item -ItemType Directory -Force $PackageRoot | Out-Null

$exclude = @(
    ".git",
    "_updates",
    "_hf4_encoding_backup",
    "_hf4_encoding_backup2",
    "cache",
    "__pycache__",
    "config.json",
    "history.json",
    "evils_media_optimizer.log"
)

Get-ChildItem -LiteralPath $Root -Force | Where-Object {
    $_.Name -notin $exclude -and $_.FullName -ne $Zip
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
Write-Host "The ZIP contains the repaired UTF-8 source and the HF4 hotfix."
