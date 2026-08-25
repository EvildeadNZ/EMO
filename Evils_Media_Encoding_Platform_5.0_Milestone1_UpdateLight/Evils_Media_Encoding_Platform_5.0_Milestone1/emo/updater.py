from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


class UpdateError(RuntimeError):
    pass


def _version_tuple(value: str) -> tuple[int, ...]:
    value = value.strip().lower().lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-.]?(preview|m|milestone|rc)(\d+)?)?$", value)
    if not match:
        nums = [int(x) for x in re.findall(r"\d+", value)]
        if not nums:
            raise UpdateError(f"Invalid version number: {value}")
        return tuple((nums + [0, 0, 0])[:3]) + (0, 0)
    major, minor, patch = map(int, match.group(1, 2, 3))
    kind = match.group(4)
    num = int(match.group(5) or 0)
    rank = {"preview": 0, "m": 1, "milestone": 1, "rc": 2, None: 3}[kind]
    return major, minor, patch, rank, num


def _find_package_root(extracted: Path) -> Path:
    candidates = []
    for app_file in extracted.rglob("app.py"):
        parent = app_file.parent
        if (
            (parent / "emo" / "version.py").exists()
            and (parent / "external_updater.pyw").exists()
        ):
            candidates.append(parent)

    if len(candidates) != 1:
        raise UpdateError(
            "The ZIP must contain exactly one valid Evil's Media "
            "Media Encoding Platform update folder."
        )
    return candidates[0]


def _read_version(package_root: Path) -> str:
    namespace: dict[str, object] = {}
    version_file = package_root / "emo" / "version.py"
    try:
        exec(version_file.read_text(encoding="utf-8"), namespace)
    except Exception as exc:
        raise UpdateError(
            f"Could not read update version: {exc}"
        ) from exc

    value = namespace.get("APP_VERSION")
    if not isinstance(value, str) or not value.strip():
        raise UpdateError("Update package has no valid APP_VERSION.")
    return value.strip()


def validate_update_zip(
    update_zip: Path,
    current_version: str,
) -> str:
    update_zip = update_zip.resolve()

    if not update_zip.exists():
        raise UpdateError(f"Update ZIP not found: {update_zip}")
    if not zipfile.is_zipfile(update_zip):
        raise UpdateError("The selected file is not a valid ZIP.")

    with tempfile.TemporaryDirectory(
        prefix="evils-media-validate-"
    ) as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(update_zip, "r") as archive:
            archive.extractall(extracted)

        package_root = _find_package_root(extracted)
        new_version = _read_version(package_root)

        if _version_tuple(new_version) <= _version_tuple(
            current_version
        ):
            raise UpdateError(
                f"Package version {new_version} is not newer than "
                f"installed version {current_version}."
            )

    return new_version


def launch_external_update(
    update_zip: Path,
    app_dir: Path,
    *,
    current_version: str,
    current_pid: int,
) -> str:
    update_zip = update_zip.resolve()
    app_dir = app_dir.resolve()

    new_version = validate_update_zip(
        update_zip,
        current_version,
    )

    runner_source = app_dir / "external_updater.pyw"
    if not runner_source.exists():
        raise UpdateError("The external updater is missing.")

    staging = Path(tempfile.mkdtemp(prefix="evils-media-updater-"))
    runner = staging / "external_updater.pyw"
    shutil.copy2(runner_source, runner)

    pythonw = Path(sys.executable)
    if pythonw.name.lower() == "python.exe":
        candidate = pythonw.with_name("pythonw.exe")
        if candidate.exists():
            pythonw = candidate

    command = [
        str(pythonw),
        str(runner),
        "--zip",
        str(update_zip),
        "--app-dir",
        str(app_dir),
        "--pid",
        str(current_pid),
        "--old-version",
        current_version,
        "--new-version",
        new_version,
    ]

    try:
        subprocess.Popen(
            command,
            cwd=str(staging),
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
            close_fds=True,
        )
    except Exception as exc:
        raise UpdateError(
            f"Could not launch updater: {exc}"
        ) from exc

    return new_version
