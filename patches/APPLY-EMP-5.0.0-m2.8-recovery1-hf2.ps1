$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Python = @'
from pathlib import Path
import hashlib
import json
import py_compile

root = Path.cwd()
source = root / "emo" / "main_window.py"
version_file = root / "emo" / "version.py"
manifest_file = root / "update-package.json"

expected_before = "47648049aa9775b8b5b860c12ad38b3858174e5b8d09bc092771cc47222d1c83"

raw = source.read_bytes()
normalized = raw.replace(b"\r\n", b"\n")
before = hashlib.sha256(normalized).hexdigest()
if before != expected_before:
    raise SystemExit(f"Refusing patch: unexpected normalized EMP HF1 source SHA-256: {before}")

old = b"total_kbps = (target_bytes * 8 * 0.96) / (duration / 1000)"
new = b"total_kbps = (target_bytes * 8 * 0.96) / duration / 1000"
if raw.count(old) != 1:
    raise SystemExit("Refusing patch: expected exactly one broken bitrate formula")

expected_after = hashlib.sha256(normalized.replace(old, new, 1)).hexdigest()
patched = raw.replace(old, new, 1)
source.write_bytes(patched)
py_compile.compile(str(source), doraise=True)

after_normalized = source.read_bytes().replace(b"\r\n", b"\n")
after = hashlib.sha256(after_normalized).hexdigest()
if after != expected_after:
    raise SystemExit(f"Refusing patch: unexpected normalized HF2 source SHA-256: {after}")

version = "5.0.0-m2.8-recovery1-hf2"
version_file.write_text(f'APP_VERSION = "{version}"\n', encoding="utf-8")

manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
manifest["version"] = version
manifest["notes"] = [
    "Hotfix 2: corrected target bitrate calculation that could request an impossibly high NVENC bitrate and cause HandBrake exit code 3.",
    "Hotfix 1: corrected subprocess.list2cmd1 to subprocess.list2cmdline so HandBrake can launch during encoding.",
] + [n for n in manifest.get("notes", []) if not str(n).startswith("Hotfix")]
manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

print("EMP HF2 applied successfully")
print("Normalized source SHA-256:", after)
print("Version:", version)
'@

Push-Location $Root
try {
    $Python | python -
    if ($LASTEXITCODE -ne 0) { throw "HF2 Python patch failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "EMP recovery HF2 applied successfully." -ForegroundColor Green
Write-Host "Restart EMP and retry the same test movie." -ForegroundColor Green
