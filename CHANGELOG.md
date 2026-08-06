# Changelog

## 4.0.0

- Introduced modular `emo` package.
- Reduced root `app.py` to a thin launcher.
- Moved the main application into `emo/main_window.py`.
- Added modular updater and version modules.
- Added working Help, Settings and Updates quick buttons.
- Renamed Scan MainMovies to Scan.
- Made Dashboard, Movies and Queue navigation functional.
- Rebuilt updater to copy changed files individually.
- Added retry handling for Windows file locks.
- Stopped deleting entire assets folders during updates.
- Retained rollback backups and automatic restart.
