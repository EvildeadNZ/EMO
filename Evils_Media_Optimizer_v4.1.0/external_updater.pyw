from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


PRESERVE_FILES = {
    "config.json",
    "history.json",
    "evils_media_optimizer.log",
}
PRESERVE_DIRS = {
    "cache",
    "_updates",
    "__pycache__",
}
MAX_BACKUPS = 5
RETRIES = 12


def wait_for_process(pid: int, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        if str(pid) not in result.stdout:
            time.sleep(1.5)
            return
        time.sleep(0.5)
    raise RuntimeError("The main app did not close in time.")


def find_package_root(extracted: Path) -> Path:
    candidates = [
        item.parent
        for item in extracted.rglob("app.py")
        if (item.parent / "emo" / "version.py").exists()
    ]
    if len(candidates) != 1:
        raise RuntimeError("Update package layout is invalid.")
    return candidates[0]


def retry(action, description: str):
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            return action()
        except (PermissionError, OSError) as exc:
            last_error = exc
            time.sleep(min(0.5 * attempt, 3.0))
    raise RuntimeError(
        f"Could not update {description} after {RETRIES} attempts: "
        f"{last_error}"
    )


def same_file(source: Path, destination: Path) -> bool:
    try:
        return (
            destination.exists()
            and source.stat().st_size == destination.stat().st_size
            and filecmp.cmp(source, destination, shallow=False)
        )
    except OSError:
        return False


def backup_application(app_dir: Path, old_version: str) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        app_dir / "_updates" / "backups"
        / f"{old_version}-{timestamp}"
    )
    backup.mkdir(parents=True, exist_ok=False)

    for item in app_dir.iterdir():
        if item.name in PRESERVE_FILES or item.name in PRESERVE_DIRS:
            continue
        target = backup / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return backup


def collect_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in PRESERVE_DIRS for part in path.parts)
        and path.name not in PRESERVE_FILES
    ]


def copy_update(
    package_root: Path,
    app_dir: Path,
    progress_callback,
) -> None:
    files = collect_files(package_root)
    total = max(1, len(files))

    for index, source in enumerate(files, 1):
        relative = source.relative_to(package_root)
        destination = app_dir / relative
        progress_callback(
            35 + int(index / total * 48),
            f"Updating {relative}",
        )

        if same_file(source, destination):
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            destination.name + ".new"
        )

        retry(
            lambda: shutil.copy2(source, temporary),
            str(relative),
        )

        def replace():
            if destination.exists():
                os.replace(temporary, destination)
            else:
                temporary.replace(destination)

        retry(replace, str(relative))


def clean_old_backups(app_dir: Path) -> None:
    root = app_dir / "_updates" / "backups"
    if not root.exists():
        return
    backups = sorted(
        [item for item in root.iterdir() if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for old in backups[MAX_BACKUPS:]:
        shutil.rmtree(old, ignore_errors=True)


def restore_backup(backup: Path, app_dir: Path) -> None:
    for source in collect_files(backup):
        relative = source.relative_to(backup)
        destination = app_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        retry(
            lambda s=source, d=destination: shutil.copy2(s, d),
            str(relative),
        )


def launch_app(app_dir: Path) -> None:
    pythonw = Path(sys.executable)
    if pythonw.name.lower() == "python.exe":
        candidate = pythonw.with_name("pythonw.exe")
        if candidate.exists():
            pythonw = candidate
    subprocess.Popen(
        [str(pythonw), str(app_dir / "EvilsMediaOptimizer.pyw")],
        cwd=str(app_dir),
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )


class UpdaterWindow:
    def __init__(self, args):
        self.args = args
        self.root = tk.Tk()
        self.root.title("Evil's Media Optimizer — Updating")
        self.root.geometry("600x220")
        self.root.resizable(False, False)
        self.root.configure(bg="#0a080d")

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Purple.Horizontal.TProgressbar",
            troughcolor="#19121f",
            background="#a23bcc",
        )

        tk.Label(
            self.root,
            text="EVIL'S MEDIA OPTIMIZER 4",
            bg="#0a080d",
            fg="#d75cff",
            font=("Segoe UI", 17, "bold"),
        ).pack(pady=(18, 4))

        self.status = tk.Label(
            self.root,
            text="Preparing update...",
            bg="#0a080d",
            fg="#eee7f2",
            font=("Segoe UI", 10),
            wraplength=550,
        )
        self.status.pack(pady=(4, 14))

        self.progress = ttk.Progressbar(
            self.root,
            style="Purple.Horizontal.TProgressbar",
            length=530,
            mode="determinate",
            maximum=100,
        )
        self.progress.pack()

        tk.Label(
            self.root,
            text=f"{args.old_version}  →  {args.new_version}",
            bg="#0a080d",
            fg="#a99eb0",
            font=("Segoe UI", 9),
        ).pack(pady=(12, 0))

        self.root.after(300, self.run_update)

    def step(self, value: int, message: str):
        self.progress["value"] = value
        self.status.configure(text=message)
        self.root.update_idletasks()

    def run_update(self):
        app_dir = Path(self.args.app_dir).resolve()
        update_zip = Path(self.args.zip).resolve()
        backup = None

        try:
            self.step(5, "Waiting for the main app to close...")
            wait_for_process(self.args.pid)

            self.step(18, "Extracting update...")
            with tempfile.TemporaryDirectory(
                prefix="evils-media-install-"
            ) as temporary:
                extracted = Path(temporary)
                with zipfile.ZipFile(update_zip, "r") as archive:
                    archive.extractall(extracted)
                package_root = find_package_root(extracted)

                self.step(28, "Creating rollback backup...")
                backup = backup_application(
                    app_dir,
                    self.args.old_version,
                )

                copy_update(
                    package_root,
                    app_dir,
                    self.step,
                )

            self.step(88, "Verifying update...")
            clean_old_backups(app_dir)

            self.step(96, "Launching updated application...")
            launch_app(app_dir)

            self.step(100, "Update complete.")
            self.root.after(1200, self.root.destroy)

        except Exception as exc:
            details = traceback.format_exc()
            log_path = (
                app_dir / "_updates" / "last-update-error.log"
            )
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(details, encoding="utf-8")

            if backup and backup.exists():
                try:
                    self.step(72, "Restoring previous version...")
                    restore_backup(backup, app_dir)
                    launch_app(app_dir)
                except Exception:
                    pass

            messagebox.showerror(
                "Update failed",
                "The update failed. The previous version was restored "
                f"where possible.\n\n{exc}\n\n"
                "Details were saved under _updates.",
            )
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--old-version", required=True)
    parser.add_argument("--new-version", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    UpdaterWindow(parse_args()).run()
