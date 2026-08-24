# Third-Party Software Notices

Evil's Media Encoding Platform (EMP), powered by EMO, coordinates several third-party tools and libraries. Those projects remain the work of their respective authors and are governed by their own licences.

EMP is not affiliated with, endorsed by, or sponsored by HandBrake, FFmpeg, The Qt Company, NVIDIA, the psutil project, the Pillow project, or the Jellyfin Project.

## Current distribution model

The current EMP source repository does **not** redistribute HandBrake, FFmpeg, NVIDIA driver/NVENC, or Jellyfin server binaries. EMP looks for compatible tools/services already installed or configured by the user and invokes or connects to them separately where required.

Future installers must preserve this distinction unless a later release intentionally redistributes a third-party component and satisfies that component's redistribution requirements.

## Components

### HandBrake / HandBrakeCLI

- Purpose in EMP: video transcoding / encoding.
- Current integration: EMP invokes `HandBrakeCLI` as an external executable.
- Upstream licence: GNU General Public License version 2 (GPLv2).
- Upstream project: https://handbrake.fr/
- Licence source: https://github.com/HandBrake/HandBrake/blob/master/COPYING

HandBrake is not part of EMP and is not currently bundled with EMP.

### FFmpeg / ffprobe

- Purpose in EMP: media inspection and metadata probing through `ffprobe`.
- Current integration: EMP invokes `ffprobe` as an external executable.
- Upstream licence: FFmpeg is principally LGPL 2.1-or-later; builds that include GPL-covered optional components are governed by the GPL terms described by FFmpeg.
- Upstream project and legal information: https://ffmpeg.org/legal.html

FFmpeg/ffprobe is not currently bundled with EMP.

### Qt for Python / PySide6

- Purpose in EMP: desktop user interface.
- Current integration: Python dependency declared in `requirements.txt`.
- Upstream licensing: Qt for Python is offered under LGPLv3/GPLv3 and commercial licensing terms.
- Upstream licensing information: https://doc.qt.io/qtforpython-6/

Any packaged EMP build that distributes PySide6/Qt files must include the notices and licence materials required by the applicable Qt/PySide6 licence terms.

### psutil

- Purpose in EMP: process and system monitoring/telemetry.
- Current integration: Python dependency declared in `requirements.txt`.
- Upstream licence: BSD 3-Clause.
- Upstream licence: https://github.com/giampaolo/psutil/blob/master/LICENSE

### Pillow

- Purpose in repository: currently declared as a Python dependency while its continued runtime requirement is being audited.
- Current integration: Python dependency declared in `requirements.txt`.
- Upstream licence: MIT-CMU.
- Upstream licence: https://github.com/python-pillow/Pillow/blob/main/LICENSE

If the Pillow dependency is confirmed unused, it should be removed from EMP rather than unnecessarily shipped.

### NVIDIA NVENC / NVIDIA driver tools

- Purpose in EMP: supported hardware-accelerated encoding through compatible NVIDIA hardware and drivers.
- Current integration: EMP detects NVIDIA tooling/hardware and requests NVENC-capable HandBrake encoders when configured.
- EMP does not currently redistribute NVIDIA drivers, `nvidia-smi`, or NVIDIA encoding libraries as standalone bundled components.

NVIDIA and NVENC are trademarks or technologies of NVIDIA Corporation. Use of those names in EMP describes compatibility only.

### Jellyfin

- Purpose in EMP: optional connection to a user-configured Jellyfin server for library, server and poster information.
- Current integration: EMP communicates with Jellyfin through its HTTP API; Jellyfin is not embedded in EMP.
- Upstream server licence: GNU General Public License version 2 (GPLv2).
- Upstream project: https://jellyfin.org/
- Source project: https://github.com/jellyfin/jellyfin

Jellyfin server software is not currently bundled with EMP.

## Packaging rule for EMP

Before any public installer is released, the installer/package must be reviewed against the exact versions and files it distributes. At minimum, the release process should:

1. record every bundled third-party component and version;
2. include required copyright and licence notices;
3. keep corresponding source/source-offer obligations where a licence requires them;
4. avoid implying ownership of or affiliation with third-party projects;
5. verify whether any change from external-tool/service integration to binary redistribution changes EMP's obligations.

This file is a project compliance record, not legal advice. Licence obligations should be rechecked whenever EMP changes what it bundles or distributes.
