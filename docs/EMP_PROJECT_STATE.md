# EMP Project State

This file is the persistent handoff for Evil's Media Encoding Platform (EMP). Read this first when continuing development in a new ChatGPT conversation.

## Project identity

- Product: Evil's Media Encoding Platform (EMP)
- Engine heritage/name: EMO (Evil's Media Optimizer)
- Repository: EvildeadNZ/EMO
- Default branch: main
- Repository visibility: public
- Creator credit: Designed and Developed by Jason Seath
- Current development line: EMP 5.0
- Known-good updater baseline: 5.0.0-m2
- Current prepared patch: 5.0.0-m2.2

## Current verified state

EMP 5.0.0-m2 successfully completed the project's first real end-to-end self-update through GitHub: EMP detected the newer GitHub Release, downloaded the attached EMP ZIP asset, installed it, and restarted successfully.

Treat 5.0.0-m2 as the known-good baseline until a newer release is confirmed through the same end-to-end update path.

## Current prepared releases

### 5.0.0-m2.1 - Easier Jellyfin Setup

- Adds **Connect to Jellyfin** in Platform Builder and Settings.
- Users enter Jellyfin server, username and password once.
- EMP authenticates with Jellyfin and stores the returned access token.
- Jellyfin passwords are never saved to `config.json` and are cleared after successful connection.
- Existing manually-entered API keys remain supported.
- Release notes are now written for end users with clear What changed / Why this helps / Security sections where appropriate.

### 5.0.0-m2.2 - Adjustable UI Text Size

- Adds **UI Text Size** under **Settings → Appearance**.
- Slider range: 85% to 150%; default 100%.
- The setting is saved and restored on future launches.
- EMP scales its main stylesheet typography, including navigation, dashboard metrics, tables, status panels and buttons.
- The feature is intended to improve readability on high-resolution displays and screens viewed from further away without forcing the user to alter Windows-wide display scaling.
- Source patch: `patches/EMP-5.0.0-m2.2-TextSize.patch`.
- User release explanation: `docs/releases/5.0.0-m2.2.md`.

## Product direction

EMP is evolving from the EMO encoding utility into a simple, polished Windows media encoding platform. A new user should be able to install it, let Platform Builder discover/configure the environment, and understand the application without needing technical knowledge.

Core principle: do not add a feature unless a first-time user can understand how to use it without external explanation.

## UI / branding

- Dark black/purple visual theme by default, with multiple appearance themes.
- Main dashboard is the Operations Center.
- Application/product identity is Evil's Media Encoding Platform (EMP), powered by EMO.
- About/splash branding should credit `Designed and Developed by Jason Seath`.
- `LIVE TO ENCODE / ENCODE TO LIVE` and `NO BITRATE LEFT BEHIND` were removed from the dashboard in the m2 line.

## Installer and first-run behaviour

- Installer should have one obvious entry point labelled `INSTALL Evil's Media Encoding Platform`.
- Avoid visible PowerShell/console windows for normal users.
- A console/troubleshooting launcher may remain for diagnostics.
- Keep installer/bootstrap scripts ASCII-safe where practical because Windows PowerShell 5 previously corrupted UTF-8 punctuation.
- The install-complete popup must remain in front; Platform Builder should not steal focus before the user dismisses it.
- Installing/reinstalling must force Platform Builder when requested even if an old config contains `setup_complete: true`.
- Platform Builder and Settings should guide users to HandBrake, GPU, NAS/network paths, media locations, server/workflow options and Jellyfin.
- Setup choices must remain editable later in Settings.

## Encoding/workflow vision

EMP should support guided configurations such as:

1. Local PC encoding.
2. NAS → PC scratch → encode → NAS.
3. Separate server as encoder.
4. NAS-local workflow where appropriate.
5. Custom paths/workflows for advanced users.

HandBrake is an external dependency. EMP should detect it and guide installation/location configuration rather than failing obscurely.

## Update architecture

GitHub is the source of truth for releases and project state. Repository: `EvildeadNZ/EMO`.

The repository is public, so EMP can perform unauthenticated update checks without embedding private credentials.

Dashboard update indicator states:

- Amber: checking.
- Green: current/up to date.
- Purple: update available.
- Red: update/check failure.
- Grey: repository not configured.
- Downloading/installing: distinct active state.

On startup EMP checks for updates. Clicking status opens an Update Status dialog with current version, latest version, repository/source, last-check time, Check Again, Open GitHub, and Install Update when appropriate.

### Lessons from first Git update

The old m1.2 checker preferred GitHub Releases over `update-package.json`, allowing an old 4.1.0 release to hide newer manifest versions. The old version parser also treated `m1.2` and `m1.3` as effectively equal. The bridge release was promoted to `5.0.0-m2`, which the old parser could recognize as newer. Publishing an actual GitHub Release with the EMP ZIP attached allowed the first self-update to succeed.

For future releases:

1. Build and syntax-check the new EMP package.
2. Update application version metadata.
3. Update `update-package.json`.
4. Update `CHANGELOG.md`, user-facing release docs and this project-state file where appropriate.
5. Publish a GitHub Release/tag for the version.
6. Attach the actual EMP update ZIP as a Release asset; do not rely on GitHub's automatic source-code ZIP.
7. Verify an existing EMP installation detects, downloads, installs and restarts into the new version.

## Version/release conventions

Examples: `5.0.0-m2`, `5.0.0-m2.1`, `5.0.0-m2.2`, `5.0.0-rc1`, `5.0.0`.

Each release should maintain application source/version metadata, `CHANGELOG.md`, `update-package.json`, user-facing GitHub release notes and the actual EMP update ZIP asset.

## Persistent-source policy

Do not rely on a ChatGPT conversation as the only copy of EMP work. GitHub is the authoritative persistent project record. Keep current source/build inputs, source patches, documentation, changelog, update metadata and release history in the repository wherever practical. Official release ZIPs should be retained as GitHub Release assets.

## Near-term roadmap

- Continue dashboard/readability/usability polish.
- Finish installer and Platform Builder polish.
- Improve update error states and updater reliability.
- Add startup diagnostics/logging and exportable diagnostics.
- Platform Health for HandBrake, GPU, storage, NAS and Jellyfin.
- Useful encoding/storage statistics.
- Encoding/profile improvements and better workflow automation.
- Explore distributed/server encoding, NAS-local workflows, Jellyfin and Radarr/Sonarr integrations.

## Development workflow for a new ChatGPT conversation

When the user types `EMO`, treat it as the shortcut to resume this project: open `EvildeadNZ/EMO`, read `docs/EMP_PROJECT_STATE.md`, inspect the current repository/release state, and continue EMP development from the current code and documentation.

Update this file after meaningful feature, architecture, release, known-issue or workflow changes.
