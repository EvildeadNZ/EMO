# Evil's Media Encoding Platform (EMP)

**Powered by EMO — Evil's Media Optimizer**

EMP is a free, open-source desktop platform for analysing, queueing and optimising large media libraries while keeping the user in control of target sizes and replacement decisions.

EMP coordinates established media tools rather than pretending to be the encoder itself. The current application uses external **HandBrakeCLI** for transcoding, **ffprobe** for media inspection, and can use **NVIDIA NVENC** hardware acceleration when compatible hardware and drivers are available.

> **Development status:** EMP 5 is under active development. Back up important media and treat current builds as pre-release software.

## What EMP is designed to do

- Scan large movie libraries and surface useful optimisation candidates.
- Analyse runtime, codec, resolution, HDR, audio and subtitle information.
- Let the user choose target sizes rather than silently changing quality targets.
- Build and reorder multi-file encoding queues.
- Copy media to local working storage, encode, verify and safely return completed files.
- Preserve the original until the replacement workflow has completed its verification steps.
- Integrate with Jellyfin for library/poster information.
- Show platform health for storage, HandBrake, NVIDIA hardware and connected services.
- Maintain an updater/rollback path as EMP moves toward a public installer.

## Third-party software

EMP is its own project. It is **not** HandBrake, FFmpeg or NVIDIA software and is not affiliated with those projects or companies.

The current source build expects compatible external tools such as `HandBrakeCLI` and `ffprobe` to be installed on the computer. They are not currently redistributed in this repository.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the current dependency and attribution record.

## Python requirements

The source build currently declares:

- PySide6
- psutil
- Pillow (continued need is being audited)

Install the declared Python dependencies with:

```powershell
python -m pip install -r requirements.txt
```

## Encoding requirements

At present, EMP expects:

- `HandBrakeCLI` available in PATH or configured in Settings.
- `ffprobe` available in PATH or configured in Settings.
- A reachable media library/NAS path.
- Compatible NVIDIA hardware and drivers when using NVENC encoding profiles.

## Safety model

EMP is being developed around a conservative replacement workflow:

1. keep the original media in place;
2. copy work to local storage;
3. encode the local copy;
4. verify the result;
5. return the completed file;
6. only complete replacement after verification.

Encoding and storage operations can never be made risk-free. Keep independent backups of important media.

## Project direction

EMP 5 is moving toward:

- a small bootstrap installer that downloads the current stable EMP package from GitHub;
- a professional public-facing interface while retaining EMP's identity;
- clear in-app About, Credits and third-party licence information;
- reliable update, rollback, diagnostics and recovery workflows;
- an optional donation/support path with no paid feature tier required to use EMP.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the working development roadmap.

## Free software and support

EMP is intended to remain free software. The project may provide an optional way for users to financially support development, but the goal is not to lock encoding features behind a paid tier.

## Licence

EMP/EMO is released under the **GNU General Public License version 3 or later (GPL-3.0-or-later)**. See [LICENSE](LICENSE).

Third-party projects retain their own copyrights and licences. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Repository

The repository remains named **EMO** because EMO is the optimisation engine/project foundation. The public application identity is **Evil's Media Encoding Platform (EMP), powered by EMO**.
