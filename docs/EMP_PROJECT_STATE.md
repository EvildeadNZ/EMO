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

## Current verified state

EMP 5.0.0-m2 successfully completed the project's first real end-to-end self-update through GitHub: EMP detected the newer GitHub Release, downloaded the attached EMP ZIP asset, installed it, and restarted successfully.

Treat 5.0.0-m2 as the known-good baseline for future patches unless a newer release supersedes it.

The m2 build includes the dashboard cleanup requested during Milestone 1:

- Removed `LIVE TO ENCODE / ENCODE TO LIVE` from the upper-right header.
- Removed `NO BITRATE LEFT BEHIND` from the lower-left sidebar.
- Preserved the GitHub update-status light and Update Status dialog.
- Includes the permanent milestone-version parsing improvement intended to support patch forms such as m2.1, m2.2, etc.

## Product direction

EMP is evolving from the EMO encoding utility into a simple, polished Windows media encoding platform. The goal is that a new user can install it, let the Platform Builder discover/configure the environment, and understand the application without needing technical knowledge.

Core principle: do not add a feature unless a first-time user can understand how to use it without needing external explanation.

## Current UI / branding

- Dark black/purple visual theme.
- Main dashboard is the Operations Center.
- Application/product identity is Evil's Media Encoding Platform (EMP), powered by EMO.
- About/splash branding should credit `Designed and Developed by Jason Seath`.

## Installer and first-run behaviour

- Installer should have one obvious entry point labelled `INSTALL Evil's Media Encoding Platform`.
- Avoid visible PowerShell/console windows for normal users.
- A console/troubleshooting launcher may remain for diagnostics.
- A previous installer bug was caused by Windows PowerShell 5 misreading UTF-8 punctuation. Installer/bootstrap scripts should remain ASCII-safe where practical.
- The install-complete popup must remain in front; the Platform Builder should not steal focus before the user dismisses it.
- Installing/reinstalling must force the Platform Builder even when an existing config contains `setup_complete: true`.
- Platform Builder should eventually auto-detect HandBrake, GPU, NAS/network paths, media locations and server/workflow options, while still allowing manual configuration.
- All setup choices must remain editable later in Settings.

## Encoding/workflow vision

EMP should support guided configurations such as:

1. Local PC encoding.
2. Pull media from NAS to PC scratch storage, encode locally, then send it back.
3. Use a separate server as the encoder.
4. Perform the workflow on the NAS when appropriate.
5. Custom paths/workflows for advanced users.

HandBrake is an external dependency. Setup should detect it and help the user locate/install it rather than failing obscurely.

## Update architecture

GitHub is the source of truth for releases and project state. Repository: `EvildeadNZ/EMO`.

The repository is now PUBLIC, so EMP can perform unauthenticated update checks without embedding a private GitHub credential.

EMP has a dashboard update indicator. Desired states:

- Amber: checking.
- Green: current/up to date.
- Purple: update available.
- Red: update/check failure.
- Grey: repository not configured.
- Downloading/installing: distinct active state.

On startup EMP checks for updates. Clicking the status opens an Update Status dialog with current version, latest version, repository/source, last-check time, Check Again, Open GitHub, and Install Update when appropriate.

### Important lesson from first update

The installed m1.2 checker preferred GitHub Releases over `update-package.json`. An old 4.1.0 GitHub Release therefore hid newer manifest versions. In addition, the old milestone parser treated `m1.2` and `m1.3` as effectively equal.

The bridge release was therefore promoted to `5.0.0-m2`, which the old parser could recognize as newer. Publishing an actual GitHub Release with the EMP ZIP attached allowed the first self-update to succeed.

For future releases:

1. Build/test the new EMP package.
2. Update application version metadata.
3. Update `update-package.json`.
4. Update `CHANGELOG.md` and this project-state file when appropriate.
5. Publish a GitHub Release/tag for the version.
6. Attach the actual EMP update ZIP as a Release asset. Do not rely on GitHub's automatic source-code ZIP as the application update payload.
7. Verify an existing EMP installation detects, downloads, installs and restarts into the new version.

Preferred long-term lookup behaviour is to consider both GitHub Release metadata and development manifest metadata safely, rather than allowing a stale release to hide a newer valid development manifest.

## Version/release conventions

Examples:

- 5.0.0-m1
- 5.0.0-m1.2
- 5.0.0-m2
- 5.0.0-m2.1
- 5.0.0-rc1
- 5.0.0

Use Git tags/releases such as `v5.0.0-m2`.

Each release should maintain:

- Application source/version metadata.
- `CHANGELOG.md`.
- `update-package.json`.
- GitHub release notes.
- The actual EMP update ZIP as a GitHub Release asset.

## Completed/tested work

- EMP installer/preview packaging.
- Platform Builder first-run flow.
- Fixed PowerShell installer encoding/parser failure.
- Fixed install-complete popup focus/order.
- Fixed Platform Builder being skipped because an old config had setup marked complete.
- Added GitHub repository configuration/default for `EvildeadNZ/EMO`.
- Repository made public for unauthenticated EMP update checking.
- Added dashboard update status/checking UI and Update Status dialog.
- Diagnosed milestone patch-version comparison problem.
- Removed the two requested dashboard branding/slogan elements.
- Published 5.0.0-m2 with an actual EMP ZIP Release asset.
- VERIFIED: first end-to-end EMP GitHub self-update succeeded.

## Persistent-source policy

Do not rely on a ChatGPT conversation as the only copy of EMP work.

From m2 onward, GitHub should be the authoritative persistent project record. Keep the current source/build inputs, documentation, changelog, update metadata and release history in the repository wherever practical. Release ZIPs should be retained as GitHub Release assets.

Generated throwaway/test packages do not all need permanent storage, but any package that becomes an official update/release should be retained as a Release asset and represented by source/version metadata in Git.

## Near-term roadmap

### Current / next patches

- Continue dashboard and usability polish from the known-good 5.0.0-m2 baseline.
- Harden updater/version handling based on lessons from the first Git update.
- Keep project state updated after significant changes.

### Platform foundation

- Finish installer polish.
- Finish Platform Builder and settings persistence.
- Improve update error states.
- Startup diagnostics/logging.

### Dashboard and Platform Health

- Professional dashboard polish.
- Platform Health for HandBrake, GPU, storage, NAS and Jellyfin.
- Useful statistics.
- Better automatic detection/status reporting.
- Diagnostics export.

### Encoding platform

- Encoding/profile improvements.
- Better workflow automation.
- Distributed/server encoding exploration.
- NAS/local/server workflow hardening.
- Jellyfin integration improvements.
- Radarr/Sonarr integration where appropriate.

### Release Candidate / 5.0 Final

- Reliability/testing/polish.
- Installer/updater hardening.
- Documentation.
- Public-ready release.

## Future ideas already discussed

- Platform Health panel showing HandBrake, GPU, scratch storage, NAS and Jellyfin state.
- Startup diagnostics/logging.
- Export Diagnostics package with non-sensitive settings, logs, version, update status, platform health, GPU, HandBrake and OS information.
- Lifetime statistics such as movies encoded, storage saved, average reduction and processing time.
- Jellyfin integration.
- Radarr/Sonarr integration.
- Potential distributed encoding/server workflows.
- Release codenames are optional; technical version numbers remain authoritative.

## Development workflow for a new ChatGPT conversation

The user can say:

`Continue EMP development from EvildeadNZ/EMO. Read docs/EMP_PROJECT_STATE.md first.`

Then inspect the repository/code before making changes. Git and this document should be treated as the persistent project record rather than relying on old chat context.

When a meaningful feature, architectural decision, release, known issue or workflow changes, update this file so the next conversation inherits the current state.
