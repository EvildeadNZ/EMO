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
- Current recovery candidate: 5.0.0-m2.8-recovery1

## Current verified state

EMP 5.0.0-m2 successfully completed the project's first real end-to-end self-update through GitHub: EMP detected the newer GitHub Release, downloaded the attached EMP ZIP asset, installed it, and restarted successfully.

Treat 5.0.0-m2 as the known-good **updater** baseline until a newer release is explicitly verified through the same full update path.

On 2026-08-25 the repository source was reconciled after discovering that `emo/main_window.py` on `main` had fallen behind later EMP development/release documentation. The later working August 16 source was recovered, syntax-checked, transported into GitHub with cryptographic verification, and transplanted onto the clean branch `emp-5-recovery-clean` as `5.0.0-m2.8-recovery1`.

Recovery verification:

- Recovered `emo/main_window.py` SHA-256: `4b766157a58b6be7fbebd1a2a8e70c15802bbd5373d302bcbc3771631e744798`
- Recovered `emo/main_window.py` Git blob: `b8de6526740b4f868acac90f7ca6bffcc7b4978a`
- GitHub Actions recovery run: `32779877043` — completed successfully
- The recovery job verified the compressed transport hash, decompressed the source, verified the final source SHA-256, Python-compiled it, then committed it.

`5.0.0-m2.8-recovery1` is a **source-verified recovery candidate**, not yet a public release. It must be launched and exercised on the Windows EMP workstation before publishing a release ZIP or using it as the bootstrap-installer target.

## Current release line

### 5.0.0-m2.8-recovery1 - Recovered Verified Baseline

- Restores the August 16 working EMP source after the repository executable source was found to be stale.
- Restores the multi-file queue snapshot/lifetime fix so processing continues beyond the first queued item.
- Restores the strong active-worker reference used by queued follow-up encoding jobs.
- Restores process-safe close and Windows system-tray handling from the `m2.7-hf4` lineage.
- Restores **Finish current movie, then exit**, **Keep processing**, and **Minimize to hidden icons** while processing is active.
- Restores Platform Builder, guided Jellyfin authentication/API-key setup, UI text scaling, themes/banner handling, update-status work and **Exclude Already Efficient**.
- Restores the missing service-status traffic-light indicator and the repaired encoding-calculation source block.
- Recovery source is cryptographically verified and Python syntax-checked, but Windows/PySide6 runtime testing is still required before publication.

### 5.0.0-m2.1 - Easier Jellyfin Setup

- Adds **Connect to Jellyfin** in Platform Builder and Settings.
- Users enter Jellyfin server, username and password once.
- EMP authenticates with Jellyfin and stores the returned access token.
- Jellyfin passwords are never saved to `config.json` and are cleared after successful connection.
- Existing manually-entered API keys remain supported.
- Release notes are written for end users with clear What changed / Why this helps / Security sections where appropriate.

### 5.0.0-m2.2 - Adjustable UI Text Size

- Adds **UI Text Size** under **Settings → Appearance**.
- Slider range: 85% to 150%; default 100%.
- The setting is saved and restored on future launches.
- EMP scales its main stylesheet typography, including navigation, dashboard metrics, tables, status panels and buttons.

### 5.0.0-m2.3 - Theme & Banner Choice

- Adds a Theme & Banner selector under **Settings → Appearance**.
- Keeps **Original Purple** as the classic/default option.
- Adds **Red Ember** as a second visual option.
- Theme selection changes the matching banner and visual accents together.
- The selected theme is saved and restored on future launches.
- Appearance controls stay in Settings rather than cluttering the dashboard.
- The theme system should remain extensible so more approved banner designs can be added later.

### 5.0.0-m2.3.1 - Red Ember HQ Hotfix

- Replaces the first Red Ember banner with the approved higher-quality banner asset.
- This is a visual-only hotfix; Original Purple and functional behaviour are unchanged.
- GitHub Release `v5.0.0-m2.3.1` exists with the official EMP ZIP attached.
- Repository version metadata and update manifest were synchronized to 5.0.0-m2.3.1 at that point in development.

## Product direction

EMP is evolving from the EMO encoding utility into a simple, polished Windows media encoding platform. A new user should be able to install it, let Platform Builder discover/configure the environment, and understand the application without needing technical knowledge.

Core principle: do not add a feature unless a first-time user can understand how to use it without external explanation.

## UI / branding

- Dark black/purple visual theme by default, with multiple appearance themes.
- Main dashboard is the Operations Center.
- Application/product identity is Evil's Media Encoding Platform (EMP), powered by EMO.
- About/splash branding should credit `Designed and Developed by Jason Seath`.
- `LIVE TO ENCODE / ENCODE TO LIVE` and `NO BITRATE LEFT BEHIND` were removed from the dashboard in the m2 line.
- Approved banner/theme set currently includes Original Purple and Red Ember.
- When additional banner themes are requested later, add them through the same Appearance banner library rather than creating one-off controls.
- Public-foundation work added a dedicated About/Credits/Licence system and third-party notices. Preserve that integration when testing and merging the recovered source.

## Installer and first-run behaviour

- Installer should have one obvious entry point labelled `INSTALL Evil's Media Encoding Platform`.
- Avoid visible PowerShell/console windows for normal users.
- A console/troubleshooting launcher may remain for diagnostics.
- Keep installer/bootstrap scripts ASCII-safe where practical because Windows PowerShell 5 previously corrupted UTF-8 punctuation.
- The install-complete popup must remain in front; Platform Builder should not steal focus before the user dismisses it.
- Installing/reinstalling must force Platform Builder when requested even if an old config contains `setup_complete: true`.
- Platform Builder and Settings should guide users to HandBrake, GPU, NAS/network paths, media locations, server/workflow options and Jellyfin.
- Setup choices must remain editable later in Settings.
- Do not build the public bootstrap installer against stale or untested source. The recovered baseline must pass Windows runtime/queue/process-safety testing first.

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

### Lessons from the 2026-08 source recovery

Release notes and patch files are not substitutes for keeping the executable source current. GitHub can only be the source of truth when later working source changes are actually committed.

For every functional patch going forward:

1. Update the actual source first on a branch.
2. Syntax-check/build the exact source that will be committed.
3. Commit the source and version metadata together.
4. Add release notes/changelog after the source commit exists.
5. Verify the branch source corresponds to the tested build before merging or publishing.

For future releases:

1. Build and syntax-check the new EMP package.
2. Update application version metadata in `emo/version.py`.
3. Update `update-package.json`.
4. Update `CHANGELOG.md`, user-facing release docs and this project-state file where appropriate.
5. Publish a GitHub Release/tag for the version.
6. Attach the actual EMP update ZIP as a Release asset; do not rely on GitHub's automatic source-code ZIP.
7. Verify an existing EMP installation detects, downloads, installs and restarts into the new version.

## Version/release conventions

Examples: `5.0.0-m2`, `5.0.0-m2.1`, `5.0.0-m2.2`, `5.0.0-m2.3`, `5.0.0-m2.3.1`, `5.0.0-m2.8-recovery1`, `5.0.0-rc1`, `5.0.0`.

Each release should maintain application source/version metadata, `CHANGELOG.md`, `update-package.json`, user-facing GitHub release notes and the actual EMP update ZIP asset.

## Persistent-source policy

Do not rely on a ChatGPT conversation as the only copy of EMP work. GitHub is the authoritative persistent project record. Keep current source/build inputs, source patches, documentation, changelog, update metadata and release history in the repository wherever practical. Official release ZIPs should be retained as GitHub Release assets.

A patch file or release note does **not** count as the current implementation unless the matching source change is also present in the repository's executable source.

## Near-term roadmap

1. Runtime-test `5.0.0-m2.8-recovery1` on the Windows EMP workstation, including a two-item queue and all protected-close/tray paths.
2. Merge the clean recovery baseline only after that test passes.
3. Continue public-distribution readiness: licensing/credits verification, GitHub release packaging and bootstrap installer.
4. Redesign the UI toward a polished professional application while retaining EMP identity.
5. Add optional donation/support mechanisms without paid feature tiers.
6. Improve startup diagnostics/logging and exportable diagnostics.
7. Continue Platform Health and encoding/profile/workflow improvements.
8. Explore distributed/server encoding, NAS-local workflows, Jellyfin and Radarr/Sonarr integrations.

## Development workflow for a new ChatGPT conversation

When the user types `EMO`, treat it as the shortcut to resume this project: open `EvildeadNZ/EMO`, read `docs/EMP_PROJECT_STATE.md`, inspect the current repository/release state, and continue EMP development from the current code and documentation.

Until the recovery candidate is merged, inspect `emp-5-recovery-clean` as the current source-recovery candidate in addition to `main`.

Update this file after meaningful feature, architecture, release, known-issue or workflow changes.
