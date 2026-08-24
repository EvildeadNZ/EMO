# EMP 5 Roadmap

## Milestone 0 - Public Distribution Foundation

- Choose and declare EMP's own open-source licence.
- Maintain `THIRD_PARTY_NOTICES.md` for software EMP uses or distributes.
- Clearly distinguish EMP from HandBrake, FFmpeg, NVIDIA and other upstream projects.
- Audit every bundled dependency before public installer releases.
- Add a professional About / Credits / Third-Party Licences experience in the app.
- Refresh the public README and release documentation around the EMP identity.

## Milestone 1 - Installer and Release Foundation

- Create one small, obvious EMP bootstrap installer.
- Keep the bootstrap installer in GitHub and have it retrieve the current stable EMP package from GitHub Releases.
- Verify downloads before installation using release metadata and cryptographic hashes.
- Keep the bootstrap installer largely version-independent so normal EMP releases do not require rebuilding it.
- Platform Builder first-run experience.
- HandBrake/GPU/storage/workflow detection and configuration.
- Settings persistence and ability to rerun/change setup.
- GitHub-backed version checking and update status UI.
- Safe updater with rollback/restart.
- Persistent project documentation.
- Startup diagnostics foundation.
- Preserve required licence and third-party notice files in installed builds.

## Milestone 2 - Professional EMP Interface

- Replace the personal skull-heavy presentation with a polished public-facing application design.
- Retain a restrained EMP/EMO identity without allowing branding to compete with the workflow.
- Refine navigation, typography, buttons, status cards, queue presentation and progress displays.
- Keep important platform health information visible and understandable.
- Add professional About, Credits, Licences and Support screens.
- Continue removing legacy wording and version references from the EMO 4-era interface.

## Milestone 3 - Dashboard and Platform Health

- Refine Operations Center dashboard.
- Platform Health status for HandBrake, GPU, storage, NAS and Jellyfin.
- Better status explanations and troubleshooting actions.
- Useful encoding/storage statistics.
- Diagnostics export.
- Clear logging and crash/error reporting suitable for public support.

## Milestone 4 - Encoding Platform

- Encoding/profile improvements.
- Better workflow automation.
- Server/distributed encoding exploration.
- NAS/local/server workflow hardening.
- Jellyfin integration improvements.
- Radarr/Sonarr integration where appropriate.

## Milestone 5 - Optional Project Support

- Add a simple optional donation/support path.
- Keep core EMP functionality free rather than creating paid encoding tiers.
- Keep donation prompts unobtrusive and separate from normal encoding workflows.
- Prefer Support/About placement over recurring nag screens.

## Release Candidate

- End-to-end bootstrap installer and update testing.
- Fresh-install and migration testing.
- Rollback and recovery testing.
- Verify the exact third-party components shipped in the release.
- Include all required licence notices/materials in the installed package.
- Error handling and recovery.
- UI/wording consistency.
- Documentation and release notes.

## EMP 5.0 Final

- Public-ready bootstrap installer.
- Stable in-app updater.
- Clear first-run setup.
- Reliable encoding/queue workflow.
- Professional public-facing UI.
- Platform health and diagnostics.
- Versioned release pipeline.
- Clear open-source and third-party attribution.
- Optional support/donation path without paid feature gating.
