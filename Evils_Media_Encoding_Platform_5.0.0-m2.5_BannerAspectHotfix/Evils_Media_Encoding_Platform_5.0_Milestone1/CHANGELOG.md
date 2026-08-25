## 5.0.0-m2.7-hf3 - Queue Continuation Reliability Hotfix

- Fixed another queue continuation path that could complete the first movie and never start the second.
- EMP now keeps a strong reference to the active EncodeWorker until its completion/failure callback has finished.
- The next queue item is started through the GUI event loop after the previous worker has been released, avoiding QRunnable lifetime/thread-pool hand-off issues.
- Added `QUEUE START` and `QUEUE DONE` diagnostic log entries showing the remaining pending count.
- Retains the m2.7-hf2 live Already Efficient filter and all earlier fixes.

## 5.0.0-m2.7-hf2 - Live Efficient Library Filter

- Changed Exclude Already Efficient into a live scanned-list filter.
- When enabled, movies scored below 40 / ALREADY EFFICIENT disappear from the scanned library view.
- Turning the option off restores those movies immediately without rescanning.
- Efficient movies remain in the scan data; only their visibility changes.
- Hidden efficient movies are unchecked to avoid invisible bulk or queue actions.

# Changelog

## 5.0.0-m2.7-hf1 - Efficient Exclusion Hotfix

- Fixed **Exclude Already Efficient** only affecting Apply Size to Checked.
- With exclusion enabled, **Select All Visible** now leaves ALREADY EFFICIENT movies unchecked.
- Enabling exclusion immediately unchecks any already-efficient titles already selected.
- **Add Checked to Queue** now also skips already-efficient titles.
- Bulk target-size application continues to skip already-efficient titles.
- Exclusion remains enabled by default every time EMP starts.
- Retains all m2.7 sortable-column functionality and previous queue/Jellyfin/updater fixes.

## 5.0.0-m2.7 - Sortable Library + Efficient Exclusion

- Added click-to-sort headers for Movie, Score, Badges, Runtime, Current Size, Target Size, Saving, Saving %, Risk and Status.
- Repeated clicks on a header toggle smallest-to-largest / largest-to-smallest (or A-Z / Z-A for text).
- Added an **Exclude Already Efficient** toggle beside **Apply Size to Checked**.
- The exclusion toggle starts enabled every time EMP launches.
- With exclusion enabled, bulk target-size changes skip movies EMP already rates **ALREADY EFFICIENT** (optimization score below 40).
- Retains the queue continuation, Jellyfin API-key and updater fixes from m2.6.

## 5.0.0-m2.6 - Updater Version Comparison Hotfix

- Fixed GitHub update status incorrectly showing UP TO DATE for `-hf` releases.
- Added proper hotfix suffix comparison (`-hf1`, `-hf2`, etc.) to both GitHub checks and ZIP validation.
- Retains the queue continuation and Jellyfin API-key fixes from 5.0.0-m2.5-hf1.
- Published as m2.6 so installations containing the old parser can detect this release automatically.


## 5.0.0-m2.5-hf1 - Queue + Jellyfin API Key Hotfix

- Fixed active queues stopping after the first completed video by snapshotting a dedicated pending queue for each run and advancing directly to the next worker.
- Fixed Connect to Jellyfin so an authorised administrator login retrieves an existing EMP API key or creates one through Jellyfin's API-key endpoints.
- Falls back to the signed-in access token when the Jellyfin account is not permitted to manage API keys.

## 5.0.0-m2.5 - Banner Aspect Ratio Hotfix

### What changed
- Fixed theme banners being stretched to the current window dimensions.
- Banners now preserve their original aspect ratio and are centre-cropped cleanly when necessary.
- Replaced Red Ember with a true 1600x287 banner crop from the approved high-resolution artwork.
- Original Purple remains unchanged.

### Why this helps
The previous banner renderer used Qt's stretch-to-fill mode, which distorted skulls, text and artwork on displays whose window size did not exactly match the image ratio. m2.5 keeps the artwork proportional at all supported window sizes.

## 5.0.0-m2.3 - Banner Choice

### What changed
- Added **Banner style** under **Settings > Appearance**.
- Added **Original Purple** and **Red Ember** banner choices.
- Banner selection is remembered between launches.
- Kept the existing UI Text Size slider.
- Prepared the banner system so more approved banner designs can be added later.

### Why this helps
EMP can now be personalised without cluttering the main dashboard. The classic look remains available, while Red Ember gives users a clearly different visual option.

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
- Connection feedback now explains whether authentication succeeded and which account connected.

### Why this helps
Previously, users had to open the Jellyfin dashboard, find the API Keys section, create/copy a key, then paste it into EMP. This update makes the normal setup path a simple sign-in while still keeping manual API-key support for advanced users.

### Security
EMP stores only the Jellyfin access token needed for future API requests. It does not write the Jellyfin password to `config.json`.

## 5.0.0-m1.3 - Dashboard cleanup
- Removed the `LIVE TO ENCODE / ENCODE TO LIVE` badge from the header artwork.
- Removed the `NO BITRATE LEFT BEHIND` sidebar slogan.
- Prepared as the first GitHub-delivered EMP UI patch.

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
