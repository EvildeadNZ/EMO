$ErrorActionPreference = "Stop"

$Root = Get-Location
$Main = Join-Path $Root "emo\main_window.py"
$Version = Join-Path $Root "emo\version.py"
$Manifest = Join-Path $Root "update-package.json"
$Notes = Join-Path $Root "docs\releases\5.0.0-m2.7-hf4.md"
$Backup = Join-Path $Root "_hf4_backup"

if (!(Test-Path $Main)) { throw "Cannot find emo\main_window.py. Run this from the EMP project root." }
if (!(Test-Path (Join-Path $Root "app.py"))) { throw "Cannot find app.py. Run this from the EMP project root." }
if (!(Test-Path (Join-Path $Root "external_updater.pyw"))) { throw "Cannot find external_updater.pyw." }

New-Item -ItemType Directory -Force $Backup | Out-Null
Copy-Item $Main (Join-Path $Backup "main_window.py") -Force
if (Test-Path $Version) { Copy-Item $Version (Join-Path $Backup "version.py") -Force }
if (Test-Path $Manifest) { Copy-Item $Manifest (Join-Path $Backup "update-package.json") -Force }

$text = Get-Content $Main -Raw

# Imports
$old = 'from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPainterPath, QPen, QBrush'
$new = 'from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPainterPath, QPen, QBrush, QCloseEvent, QAction'
if ($text.Contains($old)) {
    $text = $text.Replace($old, $new)
} elseif (!$text.Contains('QCloseEvent') -or !$text.Contains('QAction')) {
    throw "Could not find the expected QtGui import line. No source changes were made."
}

$old = '    QListWidgetItem, QTabWidget, QGroupBox, QAbstractItemView,'
$new = '    QListWidgetItem, QTabWidget, QGroupBox, QAbstractItemView, QSystemTrayIcon, QMenu,'
if ($text.Contains($old)) {
    $text = $text.Replace($old, $new)
} elseif (!$text.Contains('QSystemTrayIcon')) {
    throw "Could not find the expected QtWidgets import line. No source changes were made."
}

# State + tray setup
$old = '        self.queue_running = False'
if (!$text.Contains($old)) { throw "Could not find queue_running state." }
$new = @'
        self.queue_running = False
        self.exit_after_current = False
'@
$text = $text.Remove($text.IndexOf($old), $old.Length).Insert($text.IndexOf($old), $new)

$old = '        self.build_ui()'
if (!$text.Contains($old)) { throw "Could not find MainWindow build_ui call." }
$new = @'
        self.build_ui()
        self.setup_system_tray()
'@
$text = $text.Remove($text.IndexOf($old), $old.Length).Insert($text.IndexOf($old), $new)

# Tray/close methods inserted before the next existing MainWindow method.
$anchor = '    def '
$pos = $text.IndexOf($anchor, $text.IndexOf('class MainWindow(QMainWindow):') + 1)
if ($pos -lt 0) { throw "Could not locate MainWindow methods." }

$methods = @'
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(
            QIcon(str(APP_DIR / "assets" / "evils_skull.ico")),
            self,
        )
        self.tray_icon.setToolTip(f"{APP_NAME} {APP_VERSION}")

        menu = QMenu(self)
        restore_action = QAction("Restore EMP", self)
        restore_action.triggered.connect(self.restore_from_tray)
        menu.addAction(restore_action)
        menu.addSeparator()

        exit_action = QAction("Exit EMP", self)
        exit_action.triggered.connect(self.request_exit)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def tray_activated(self, reason):
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.restore_from_tray()

    def restore_from_tray(self):
        self.show()
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized
        )
        self.raise_()
        self.activateWindow()

    def minimize_to_tray(self):
        if not hasattr(self, "tray_icon"):
            return
        if not self.tray_icon.isVisible():
            self.tray_icon.show()
        self.hide()
        self.tray_icon.showMessage(
            APP_NAME,
            "EMP is still running. The current movie will continue safely.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def request_exit(self):
        self.close()

    def request_exit_after_current(self):
        if not self.queue_running or self.current_movie is None:
            self.close()
            return
        self.exit_after_current = True
        self.status.setText(
            "Exit requested â€” the current movie will finish, then EMP will close."
        )
        self.operations.set_process_status("Exit requested after current movie")
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                APP_NAME,
                "Exit queued. EMP will close after the current movie finishes.",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )

    def closeEvent(self, event: QCloseEvent):
        if self.queue_running and self.current_movie is not None:
            choice = QMessageBox(self)
            choice.setIcon(QMessageBox.Icon.Warning)
            choice.setWindowTitle("Movie processing is active")
            choice.setText("EMP is currently processing a movie.")
            choice.setInformativeText(
                f'Do you want EMP to finish "{self.current_movie.title}" before closing?'
            )

            finish_exit = choice.addButton(
                "Finish current movie, then exit",
                QMessageBox.ButtonRole.AcceptRole,
            )
            keep_processing = choice.addButton(
                "Keep processing",
                QMessageBox.ButtonRole.RejectRole,
            )
            minimize = choice.addButton(
                "Minimize to hidden icons",
                QMessageBox.ButtonRole.ActionRole,
            )
            choice.exec()

            if choice.clickedButton() is finish_exit:
                self.request_exit_after_current()
            elif choice.clickedButton() is minimize:
                self.minimize_to_tray()

            event.ignore()
            return

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        event.accept()

'@

$text = $text.Insert($pos, $methods)

# Add completion handling immediately before the existing pause-after-current block.
$anchor = '        if self.pause_after_current:'
$pos = $text.IndexOf($anchor)
if ($pos -lt 0) { throw "Could not find pause_after_current completion point." }

$completion = @'
        if self.exit_after_current:
            self.exit_after_current = False
            self.queue_running = False
            self.current_movie = None
            self.telemetry.stop_and_hide()
            self.start_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.status.setText(
                f"Completed {movie.title}. EMP will now close as requested."
            )
            self.operations.set_process_status(
                "Current movie complete â€” exiting"
            )
            if self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    APP_NAME,
                    "Current movie finished. EMP is closing.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )
            QTimer.singleShot(500, QApplication.instance().quit)
            return

'@
$text = $text.Insert($pos, $completion)

Set-Content $Main $text -Encoding UTF8

# Version
Set-Content $Version 'APP_VERSION = "5.0.0-m2.7-hf4"' -Encoding UTF8

# Update manifest
$manifestObject = @{
    name = "Evil's Media Encoding Platform"
    version = "5.0.0-m2.7-hf4"
    minimum_updater_version = "5.0.0-m2"
    architecture = "modular"
    notes = @(
        "Ultra-urgent process-safety hotfix: EMP cannot close while a movie is actively being processed."
        "Closing during active processing offers Finish current movie, then exit; Keep processing; or Minimize to hidden icons."
        "A Windows system-tray icon provides Restore EMP and Exit EMP controls."
        "Exit is queued safely and the current movie is allowed to finish before EMP closes."
    )
}
$manifestObject | ConvertTo-Json -Depth 5 | Set-Content $Manifest -Encoding UTF8

# Release notes
$notesText = @'
# EMP 5.0.0-m2.7-hf4 â€” Process Safety & System Tray Hotfix

## Release details
- **Tag:** `v5.0.0-m2.7-hf4`
- **Release title:** **EMP 5.0.0-m2.7-hf4 â€” Process Safety & System Tray Hotfix**

## What changed
- EMP can no longer close while a movie is actively being processed.
- Closing during active processing offers:
  - **Finish current movie, then exit**
  - **Keep processing**
  - **Minimize to hidden icons**
- **Finish current movie, then exit** queues the exit without interrupting the current movie.
- The current movie is allowed to complete before EMP closes.
- EMP now has a Windows system-tray icon.
- Double-clicking the tray icon restores EMP.
- The tray menu provides **Restore EMP** and **Exit EMP**.
- Tray exit uses the same process-safety protection.

## Why this is urgent
This prevents an accidental window close from interrupting an active movie-processing job.

## Testing
1. Start a movie and press X â†’ **Keep processing** â†’ movie continues.
2. Start a movie and press X â†’ **Finish current movie, then exit** â†’ movie finishes, then EMP closes.
3. Start a movie and press X â†’ **Minimize to hidden icons** â†’ EMP disappears to the Windows notification area while processing continues.
'@
New-Item -ItemType Directory -Force (Split-Path $Notes) | Out-Null
Set-Content $Notes $notesText -Encoding UTF8

# Syntax check
python -m py_compile emo\main_window.py emo\version.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Syntax check FAILED. Restoring main_window.py and version.py..." -ForegroundColor Red
    Copy-Item (Join-Path $Backup "main_window.py") $Main -Force
    if (Test-Path (Join-Path $Backup "version.py")) { Copy-Item (Join-Path $Backup "version.py") $Version -Force }
    throw "Python syntax check failed. Your original files were restored."
}

# Build update ZIP. Runtime/user data is intentionally excluded because the updater preserves it.
$Zip = Join-Path $Root "EMP-5.0.0-m2.7-hf4-Update.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }

$Temp = Join-Path $env:TEMP ("EMP-hf4-package-" + [guid]::NewGuid().ToString())
$PackageRoot = Join-Path $Temp "EMP-5.0.0-m2.7-hf4"
New-Item -ItemType Directory -Force $PackageRoot | Out-Null

$exclude = @(
    ".git",
    "_updates",
    "cache",
    "__pycache__",
    "config.json",
    "history.json",
    "evils_media_optimizer.log",
    "*.pyc",
    "*.pyo"
)

Get-ChildItem -LiteralPath $Root -Force | Where-Object {
    $_.Name -notin @(".git","_updates","cache","__pycache__","config.json","history.json","evils_media_optimizer.log") -and
    $_.FullName -ne $Zip -and
    $_.FullName -ne $Backup
} | ForEach-Object {
    Copy-Item $_.FullName $PackageRoot -Recurse -Force
}

Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $Zip -CompressionLevel Optimal

Remove-Item $Temp -Recurse -Force

Write-Host ""
Write-Host "HF4 READY" -ForegroundColor Green
Write-Host "Version: 5.0.0-m2.7-hf4"
Write-Host "ZIP: $Zip"
Write-Host ""
Write-Host "IMPORTANT: test EMP before publishing the ZIP."

