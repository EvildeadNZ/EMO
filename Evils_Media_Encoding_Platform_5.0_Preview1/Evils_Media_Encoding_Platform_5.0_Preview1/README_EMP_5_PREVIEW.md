# Evil's Media Encoding Platform — 5.0 Preview 1

This is the first installer/setup preview of the new platform experience, powered by EMO.

## Try it

On Windows, double-click **INSTALL EMP 5 PREVIEW.bat**. The preview bootstrap installs to your Local AppData folder, creates shortcuts, installs the current Python UI requirements, and launches the new Platform Builder.

This preview still uses Python on the machine. The production Windows installer will bundle the application/runtime so Python is not a user requirement.

## Working now

- First-run Platform Builder branded as **Evil's Media Encoding Platform**.
- Detects and verifies **HandBrakeCLI**.
- Official HandBrake download button if HandBrakeCLI is unavailable.
- Browse for a non-standard HandBrakeCLI installation.
- Workflow choices: NAS + this PC, local PC, dedicated server, NAS native.
- NAS + this PC and local PC correspond to the current local EMP/EMO engine.
- Dedicated server and NAS-native modes save configuration but are clearly marked as awaiting the remote-worker backend.
- Guided source, finished-media and work/scratch locations.
- Read/write and free-space test for locations.
- Windows mapped network share discovery.
- Jellyfin/Plex/Emby/None media-server selection (Jellyfin is the existing active integration).
- Platform Setup Wizard can be rerun later from Settings → General.
- Existing EMO queue/encoding functionality retained, including the 4.6.2 queue continuation fix.

## Safety

The preview does not pretend remote-server or NAS-native encoding is active before the worker backend exists. Existing encode behavior remains local/PC-driven.
