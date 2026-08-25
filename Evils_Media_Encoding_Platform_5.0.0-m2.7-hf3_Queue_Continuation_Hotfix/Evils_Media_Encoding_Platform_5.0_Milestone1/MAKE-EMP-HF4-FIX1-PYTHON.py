from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

root = Path.cwd()
main = root / "emo" / "main_window.py"
version = root / "emo" / "version.py"
zip_path = root / "EMP-5.0.0-m2.7-hf4-FIX1-Update.zip"
backup = root / "_hf4_encoding_backup3"
backup.mkdir(exist_ok=True)

if not main.exists():
    raise SystemExit("Cannot find emo/main_window.py. Run this from the EMP project root.")

shutil.copy2(main, backup / "main_window.py")

raw = main.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"):
    raw = raw[3:]

text = raw.decode("utf-8")

# Common UTF-8 mojibake markers, expressed with escapes so this script is ASCII-only.
bad = ("\u00e2", "\u00c3", "\u00c2", "\u00f0", "\ufffd")

if any(x in text for x in bad):
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        repaired = text.encode("latin1").decode("utf-8")

    if repaired.startswith("\ufeff"):
        repaired = repaired[1:]
    if repaired.startswith("?from __future__"):
        repaired = repaired[1:]

    main.write_text(repaired, encoding="utf-8", newline="")
    print("Repaired one mojibake layer.")
else:
    print("No mojibake markers found.")

version.write_text('APP_VERSION = "5.0.0-m2.7-hf4"\n', encoding="utf-8")

subprocess.run(["python", "-m", "py_compile", str(main), str(version)], check=True)
print("Python syntax check: OK")

if zip_path.exists():
    zip_path.unlink()

exclude = {
    ".git", "_updates", "_hf4_encoding_backup", "_hf4_encoding_backup2",
    "_hf4_encoding_backup3", "cache", "__pycache__",
    "config.json", "history.json", "evils_media_optimizer.log",
    zip_path.name
}

with tempfile.TemporaryDirectory() as td:
    package = Path(td) / "EMP-5.0.0-m2.7-hf4-FIX1"
    package.mkdir()

    for item in root.iterdir():
        if item.name in exclude:
            continue
        dest = package / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in package.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(package))

print()
print("HF4 FIX1 READY")
print("Version: 5.0.0-m2.7-hf4")
print("ZIP:", zip_path)
