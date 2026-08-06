# Evil's Media Optimizer 4.0.0

Version 4.0 is a foundation release with a modular application package and a
new updater that replaces files individually instead of deleting whole folders.

## Install 4.0

Install this version into a new folder one final time because older updater
versions cannot reliably replace their locked assets folder.

To retain your setup, copy these from the old installation into the new folder:

- `config.json`
- `history.json` if present
- `cache` folder

Then launch:

    START Evil's Media Optimizer.vbs

## Visible changes

- The button now says **SCAN**.
- Functional Help, Settings and Updates buttons below the banner.
- Functional Dashboard, Movies and Queue sidebar buttons.
- Existing poster, queue, NVENC, telemetry and settings features remain.

## New updater

Future 4.x updates use a separate updater that:

- Waits for the app to close.
- Updates individual changed files.
- Skips identical files.
- Retries temporarily locked files.
- Never deletes the complete assets folder.
- Creates a rollback backup.
- Restarts the app automatically.
- Keeps the five newest backups.
