from __future__ import annotations

import hashlib
import json
import py_compile
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "4b766157a58b6be7fbebd1a2a8e70c15802bbd5373d302bcbc3771631e744798"
VERSION = "5.0.0-m2.8-recovery1"

source = Path("emo/main_window.py")
actual = hashlib.sha256(source.read_bytes()).hexdigest()
if actual != EXPECTED_SOURCE_SHA256:
    raise SystemExit(f"Recovered source hash mismatch: {actual}")

py_compile.compile(str(source), doraise=True)

Path("emo/version.py").write_text(
    f'APP_VERSION = "{VERSION}"\n',
    encoding="utf-8",
)
py_compile.compile("emo/version.py", doraise=True)

manifest_path = Path("update-package.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["name"] = "Evil's Media Encoding Platform"
manifest["version"] = VERSION
manifest["notes"] = [
    "Recovered and hash-verified EMP 5 working baseline from the August 16 development source.",
    "Restores the multi-file queue lifetime/snapshot fix so processing continues beyond the first item.",
    "Restores process-safe close and system-tray behavior from the m2.7-hf4 lineage.",
    "Restores Platform Builder, guided Jellyfin setup, UI text scaling, themes, update checks and later working-source fixes.",
    "Restores the missing service-status traffic-light indicator and repairs the corrupted encoding calculation block.",
    "This recovery release reconciles GitHub source with the later working EMP code before bootstrap-installer work begins.",
]
manifest_path.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

print(f"Verified recovered EMP source: {actual}")
print(f"Recovery version: {VERSION}")
