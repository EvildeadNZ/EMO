# EMP Project State

This file is the persistent handoff for Evil's Media Encoding Platform (EMP). Read this first when continuing development in a new ChatGPT conversation.

## Project identity

- Product: Evil's Media Encoding Platform (EMP)
- Engine heritage/name: EMO (Evil's Media Optimizer)
- Repository: EvildeadNZ/EMO
- Default branch: main
- Creator credit: Designed and Developed by Jason Seath
- Current development line: EMP 5.0 Milestone 1
- Current patch target at time of this handoff: 5.0.0-m1.3

## Product direction

EMP is evolving from the EMO encoding utility into a simple, polished Windows media encoding platform. The goal is that a new user can install it, let the Platform Builder discover/configure the environment, and understand the application without needing technical knowledge.

Core principle: do not add a feature unless a first-time user can understand how to use it without needing external explanation.

## Current UI / branding

- Dark black/purple visual theme.
- Main dashboard is the Operations Center.
- Header uses Evil's Media Optimizer artwork while the application/product identity is EMP.
- The old top-right header block reading `LIVE TO ENCODE / ENCODE TO LIVE` is being removed in 5.0.0-m1.3.
- The old bottom-left sidebar slogan `NO BITRATE LEFT BEHIND` is being removed in 5.0.0-m1.3.
- About/splash branding should identify Evil's Media Encoding Platform, Powered by EMO, and credit Jason Seath.

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

GitHub is the source of truth for releases and project state.

Repository: `EvildeadNZ/EMO`

EMP has a dashboard update indicator. Desired behaviour:

- Amber: checking.
- Green: current/up to date.
- Purple: update available.
- Red: update/check failure.
- Grey: repository not configured.
- Downloading/installing should have a distinct active state.

On application startup EMP checks for updates. Clicking the status opens an Update Status dialog with current version, latest version, repository/source, last-check time, Check Again, Open GitHub, and Install Update when appropriate.

Preferred update lookup order:

1. GitHub Releases.
2. `update-package.json` on the repository/default branch as development fallback.
3. If the repository exists but neither provides a published update, report that clearly as a development/no-release state rather than a generic connection failure.

The updater should support milestone/prerelease versions such as `5.0.0-m1`, `5.0.0-m1.3`, `5.0.0-rc1`, and final `5.0.0`.

Updates should be downloaded, validated, installed using the rollback-capable external updater, then EMP should restart. Long-term goal: after initial installation, users should normally update from inside EMP rather than manually downloading ZIPs.

## Important update issue discovered

The repository is private at the time this file was created. EMP's unauthenticated public GitHub update requests may therefore fail even though ChatGPT/GitHub integration can access the repository. Before public/self-update testing, decide whether to make the repo public or implement an appropriate release/update distribution mechanism that does not require embedding private GitHub credentials in EMP.

## Version/release conventions

Development version examples:

- 5.0.0-m1
- 5.0.0-m1.2
- 5.0.0-m1.3
- 5.0.0-m2
- 5.0.0-rc1
- 5.0.0

Use Git tags/releases such as `v5.0.0-m1.3`.

Each release should maintain:

- `CHANGELOG.md`
- `update-package.json`
- GitHub release notes
- Version metadata used by the application/updater

## Current Milestone 1 work

Completed/tested during development:

- EMP installer/preview packaging.
- Platform Builder first-run flow.
- Fixed PowerShell installer encoding/parser failure.
- Fixed install-complete popup focus/order.
- Fixed Platform Builder being skipped because an old config had setup marked complete.
- Added GitHub repository configuration/default for `EvildeadNZ/EMO`.
- Added dashboard update status/checking UI and Update Status dialog.
- Added milestone-aware version comparison.

Current patch 5.0.0-m1.3:

- Remove `LIVE TO ENCODE / ENCODE TO LIVE` artwork/block from the upper-right header.
- Remove `NO BITRATE LEFT BEHIND` from the lower-left sidebar.
- Preserve the update-light functionality from m1.2.

## Near-term roadmap

### Milestone 1

- Finish installer polish.
- Finish Platform Builder and settings persistence.
- Finish reliable GitHub update/release flow.
- Improve update error states.
- Establish persistent project documentation in Git.

### Milestone 2

- Professional dashboard polish.
- Platform Health.
- Useful statistics.
- Better automatic detection/status reporting.

### Milestone 3

- Encoding engine/workflow improvements.
- Profiles.
- Distributed/server encoding concepts.

### Release Candidate

- Reliability/testing/polish.
- Installer/updater hardening.
- Documentation.

### 5.0 Final

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

## Development workflow

For future ChatGPT conversations, the user can say:

`Continue EMP development from EvildeadNZ/EMO. Read docs/EMP_PROJECT_STATE.md first.`

Then inspect the repository/code before making changes. Git and this document should be treated as the persistent project record rather than relying on old chat context.

When a meaningful feature, architectural decision, release, known issue or workflow changes, update this file so the next conversation inherits the current state.
