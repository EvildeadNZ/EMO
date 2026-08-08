# EMP Architecture

## Product layers

EMP is structured conceptually as four layers:

1. **Installer / Platform Builder** - installation, dependency detection, first-run workflow selection and configuration.
2. **EMP UI** - dashboard, Movies, Queue, History, Statistics, Jellyfin, Settings, Tools and About.
3. **EMO encoding engine** - media analysis, target decisions, queue processing and HandBrake execution.
4. **Updater / release layer** - GitHub version checks, package validation, rollback-capable installation and restart.

## Persistent configuration

Configuration must survive upgrades. Setup choices made by Platform Builder must be editable later from Settings. Reinstall/update code must not accidentally suppress a requested first-run/setup flow because an old config says setup is complete.

## External dependencies

HandBrake/HandBrakeCLI is external. EMP should detect it and guide installation/location configuration. Hardware acceleration and GPU capabilities should be detected rather than assumed.

## Storage/workflow model

The platform must be able to represent local, NAS-to-PC-to-NAS, server-encoding, NAS-local and custom workflows. Source, scratch/work, output and media-library locations should therefore be configuration concepts rather than hard-coded paths.

## Update subsystem

The application checks `EvildeadNZ/EMO` on startup. GitHub Releases are the preferred production release source; `update-package.json` is the development fallback. Packages are validated before being handed to the external updater. The external updater is responsible for safe replacement/rollback and relaunch.

Do not embed a personal GitHub token in distributed EMP builds. If the repository remains private, use a suitable authenticated or external distribution mechanism rather than shipping credentials.

## Reliability principles

- Normal launch should not expose a console window.
- Troubleshooting launch may expose a console/logging.
- Startup/update failures should be presented in persistent, readable UI rather than disappearing terminals.
- Preserve user configuration across updates unless an explicit migration requires change.
- Keep update/version parsing prerelease-aware.
- Prefer diagnostics that explain the failed component and next action.
