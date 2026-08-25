# EMP GitHub release setup

1. Put this project in your GitHub repository.
2. In EMP Settings > Updates, enter the repository as `owner/repository`.
3. Commit and push updates normally.
4. For a public EMP release, update `emo/version.py` and tag it, e.g. `v5.0.0-m2`, then push the tag.
5. The included GitHub Actions workflow creates `Evils_Media_Encoding_Platform_Update.zip` and attaches it to the GitHub Release.
6. EMP checks the latest release on startup. If it is newer, the dashboard update light becomes active; clicking it downloads and installs the ZIP with rollback protection.

Private repositories will need authenticated API support in a later milestone; this first implementation targets public GitHub Releases.
