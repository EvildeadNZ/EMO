# Changelog

## 5.0.0-m2.8-recovery1 - Recovered Verified Baseline

### What changed
- Restored the hash-verified August 16 EMP working source after discovering that the repository's executable `main_window.py` had fallen behind later development/release documentation.
- Restored the multi-file queue snapshot/lifetime fix so processing continues beyond the first queued movie.
- Restored the active encode-worker lifetime fix used by queued follow-up jobs.
- Restored process-safe closing and Windows system-tray behaviour from the `m2.7-hf4` lineage.
- Restored Platform Builder, guided Jellyfin setup, UI text scaling, themes/banner handling, update-status work and the **Exclude Already Efficient** control.
- Restored the missing service-status traffic-light indicator and the repaired encoding-calculation source block.

### Recovery verification
- Recovered-source SHA-256: `4b766157a58b6be7fbebd1a2a8e70c15802bbd5373d302bcbc3771631e744798`.
- Verified Git blob for `emo/main_window.py`: `b8de6526740b4f868acac90f7ca6bffcc7b4978a`.
- GitHub recovery run `32779877043` verified the compressed transport, final source hash and Python syntax before committing the recovered source.
- This remains a recovery candidate until the restored application is exercised on the Windows EMP workstation.

## 5.0.0-m2.3.1 - Red Ember HQ Hotfix

### What changed
- Replaced the Red Ember banner with a much higher-quality version.
- Improved sharpness, skull detail, red glow/ember effects and readability across wide displays.
- Original Purple remains unchanged.

### Why this helps
The first Red Ember banner looked soft when stretched across the full EMP header. This hotfix improves only the banner asset so the theme looks crisp without changing encoding, Jellyfin, updater or queue behaviour.

## 5.0.0-m2.3 - Theme & Banner Choice

### What changed
- Added a Theme & Banner selector under **Settings → Appearance**.
- Added **Original Purple** and **Red Ember** choices.
- Theme choice changes the matching banner and visual accents together.
- The selected theme is saved and restored on future launches.
- The theme system is structured so more approved banner designs can be added later.

### Why this helps
EMP can now have multiple visual styles without cluttering the dashboard. Appearance controls stay in Settings, and users can choose the look they prefer.

## 5.0.0-m2.2 - Adjustable UI Text Size

### What changed
- Added **UI Text Size** under **Settings → Appearance**.
- Added a slider from **85% to 150%**, with **100%** as the normal EMP size.
- EMP remembers the selected size and restores it on the next launch.
- Main navigation, dashboard metrics, tables, status text, buttons and other stylesheet-driven text scale together.

### Why this helps
EMP contains a lot of useful information on one screen, but the original sizing can be too small on high-resolution displays or when the monitor is further away. Users can now make EMP easier to read without changing Windows display scaling for every other application.

### How to use it
Open **Settings → Appearance**, move **UI Text Size** to the size you prefer, then click **Save**.

## 5.0.0-m2.1 - Easier Jellyfin Setup

### What changed
- Added a new **Connect to Jellyfin** button in Settings and Platform Builder.
- Enter your Jellyfin server address, username and password once; EMP asks Jellyfin for an access token and fills the API credential automatically.
- EMP **does not save your Jellyfin password**. The password field is cleared after a successful connection.
- Existing manually entered Jellyfin API keys continue to work.
- Connection feedback explains whether authentication succeeded and which Jellyfin account connected.

### Why this helps
Previously, users had to open the Jellyfin dashboard, find the API Keys section, create or copy a key, then paste it into EMP. This update makes the normal setup path a simple sign-in while keeping manual API-key support for advanced users.

### Security
EMP stores only the Jellyfin access token needed for future API requests. It does not write the Jellyfin password to `config.json`.

## 5.0.0-m2 - First Git Update

### What changed
- Delivered the first successful EMP self-update through GitHub.
- Removed `LIVE TO ENCODE / ENCODE TO LIVE` from the upper-right dashboard header.
- Removed `NO BITRATE LEFT BEHIND` from the lower-left sidebar.
- Fixed milestone version handling so patch versions such as m2.1 and m2.2 can be compared correctly.

### Why this matters
EMP can now detect a newer GitHub release, download the attached EMP update ZIP, install it safely and restart itself.

## 5.0.0-m1.3 - Dashboard Cleanup

- Removed `LIVE TO ENCODE / ENCODE TO LIVE` from the upper-right dashboard header.
- Removed `NO BITRATE LEFT BEHIND` from the lower-left sidebar.
- Preserved the Milestone 1 GitHub update-status light and Update Status dialog.
- GitHub repository is now the persistent source of truth for EMP project state and updates.

## 4.3.0

- Added the Queue Control Centre.
- Added drag-and-drop ordering and queue totals.
- Added move top, move bottom, move up and move down.
- Added queue sorting by title and potential saving.
- Added remove and clear queue controls.
- Added Pause After Current.
- Added completion summaries between queued movies.
- Removed baked-in Help and Settings symbols from the banner.

## 4.2.2

- Fixed network adapter telemetry and blank command windows.
