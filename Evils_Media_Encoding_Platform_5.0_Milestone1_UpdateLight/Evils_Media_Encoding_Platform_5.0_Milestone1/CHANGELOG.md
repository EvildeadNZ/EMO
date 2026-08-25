# 5.0.0-m1.2 - Update Light Complete

- Completed the dashboard GitHub update indicator for `EvildeadNZ/EMO`.
- Added automatic startup update checks.
- Added readable checking, current, update available, failed, and downloading states.
- Added current/latest version, repository, source, and last-check time details.
- Clicking the indicator now opens an Update Status dialog with Check Again and Open GitHub.
- Newer builds offer one-click download, validation, install, and restart.

# 5.0.0-preview1 — Evil's Media Encoding Platform

- New first-run Platform Builder and EMP branding.
- Automatic HandBrakeCLI discovery and validation with official download handoff.
- Guided workflow, storage/scratch, network-location and media-server setup.
- Platform setup can be rerun later from Settings.
- Retains EMO 4.6.2 queue continuation fix.
- Dedicated-server and NAS-native modes are configuration previews pending the remote-worker backend.

# Changelog

## 4.6.2

- Fixed the queue stopping after the first completed movie.
- Added a persistent queue-advance timer for reliable automatic processing of all queued items.
- Preserved the optional safe pause-after-current behaviour.

## 4.6.1

- Removed the low-quality generated theme banner artwork.
- Restored the original polished EMO header for all themes.
- Kept theme colour palettes fully functional.
- Prioritised visual quality over unfinished experimental artwork.

## 4.6.0

- Added the 0–100 Optimization Score and visual-risk guidance.

## Preview 1 Hotfix - 2026-08-08
- Fixed Windows PowerShell 5 parsing failure caused by UTF-8 punctuation in the installer bootstrap.
- Installer bootstrap is now ASCII-safe.
- Normal shortcuts prefer pythonw.exe/pyw.exe so EMP launches without a console window.
- Installer batch now stays open when PowerShell exits with an error so diagnostics can be read.

## 5.0.0-m1 - Git Release Foundation
- Rebrands the preview milestone as Evil's Media Encoding Platform 5.0 Milestone 1.
- Adds a dashboard GitHub update-status light checked automatically on startup.
- Adds one-click download/install/restart for newer public GitHub Releases.
- Adds GitHub repository configuration under Settings > Updates.
- Adds milestone/prerelease-aware version comparison.
- Adds a GitHub Actions workflow that packages release tags into an EMP update ZIP.
- Adds a clearly named hidden installer launcher: INSTALL Evil's Media Encoding Platform.vbs.

- Milestone 1 Hotfix 1: installer now forces Platform Builder on install/reinstall and brings it to the foreground.
