from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .main_window import APP_DIR, APP_NAME, APP_VERSION, MainWindow


PROJECT_NAME = "Evil's Media Encoding Platform"
PROJECT_SHORT_NAME = "EMP"
PROJECT_IDENTITY = "Powered by EMO — Evil's Media Optimizer"


def _read_project_file(name: str, fallback: str) -> str:
    path = Path(APP_DIR) / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def _text_tab(text: str, *, markdown: bool = False) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 10, 10, 10)

    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction
    )
    if markdown:
        browser.setMarkdown(text)
    else:
        browser.setPlainText(text)
    layout.addWidget(browser)
    return page


def _html_tab(html: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 10, 10, 10)

    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.setHtml(html)
    layout.addWidget(browser)
    return page


class PublicAboutDialog(QDialog):
    """Public-facing EMP identity, credits and licence information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {PROJECT_SHORT_NAME}")
        self.resize(880, 680)
        self.setMinimumSize(720, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        heading = QLabel(
            f"<h2>{PROJECT_NAME} ({PROJECT_SHORT_NAME})</h2>"
            f"<p><b>{PROJECT_IDENTITY}</b></p>"
            f"<p>Application build: <b>{APP_VERSION}</b></p>"
        )
        heading.setWordWrap(True)
        layout.addWidget(heading)

        tabs = QTabWidget()
        tabs.addTab(self._about_tab(), "About")
        tabs.addTab(self._credits_tab(), "Credits")

        licence_text = _read_project_file(
            "LICENSE",
            "EMP licence text is not available in this installation.",
        )
        tabs.addTab(
            _text_tab(licence_text),
            "EMP Licence",
        )

        notices_text = _read_project_file(
            "THIRD_PARTY_NOTICES.md",
            "Third-party notices are not available in this installation.",
        )
        tabs.addTab(
            _text_tab(notices_text, markdown=True),
            "Third-Party Licences",
        )
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _about_tab(self) -> QWidget:
        return _html_tab(
            f"""
            <h2>{PROJECT_NAME}</h2>
            <p><b>{PROJECT_IDENTITY}</b></p>
            <p>
                EMP is a free, open-source media analysis, queue management
                and encoding workflow platform. EMP coordinates established
                media tools while keeping queue, target-size and replacement
                decisions visible to the user.
            </p>
            <h3>Free software</h3>
            <p>
                EMP/EMO is released under the GNU General Public License,
                version 3 or later (GPL-3.0-or-later). You may redistribute
                and modify EMP under that licence. EMP is provided without
                warranty; see the <b>EMP Licence</b> tab for the complete
                licence terms.
            </p>
            <h3>Third-party software</h3>
            <p>
                EMP uses or interoperates with third-party projects including
                HandBrake, FFmpeg/ffprobe, Qt for Python/PySide6, psutil and
                compatible NVIDIA NVENC hardware/software. Those projects
                remain the work of their respective authors and are governed
                by their own licences.
            </p>
            <p>
                EMP is not affiliated with, endorsed by, or sponsored by
                HandBrake, FFmpeg, The Qt Company, NVIDIA, psutil or Pillow.
                See <b>Credits</b> and <b>Third-Party Licences</b> for details.
            </p>
            """
        )

    def _credits_tab(self) -> QWidget:
        return _html_tab(
            """
            <h2>Technology &amp; Credits</h2>
            <p>
                EMP stands on the work of established open-source and
                hardware projects. The names below describe technologies EMP
                uses or interoperates with; they are not EMP-owned products.
            </p>

            <h3>HandBrake / HandBrakeCLI</h3>
            <p>
                Used as EMP's external video transcoding engine. The current
                EMP distribution expects HandBrakeCLI to be installed
                separately and does not bundle the HandBrake binary.
            </p>
            <p><a href="https://handbrake.fr/">handbrake.fr</a></p>

            <h3>FFmpeg / ffprobe</h3>
            <p>
                ffprobe is used externally for media inspection, including
                codec, runtime, resolution, audio and subtitle information.
                The current EMP distribution does not bundle FFmpeg/ffprobe.
            </p>
            <p><a href="https://ffmpeg.org/">ffmpeg.org</a></p>

            <h3>Qt for Python / PySide6</h3>
            <p>
                Provides the desktop user-interface framework used by EMP.
            </p>
            <p><a href="https://doc.qt.io/qtforpython-6/">Qt for Python</a></p>

            <h3>psutil</h3>
            <p>
                Used for process and system monitoring/telemetry where
                available.
            </p>
            <p><a href="https://github.com/giampaolo/psutil">psutil</a></p>

            <h3>Pillow</h3>
            <p>
                Currently declared as a project dependency while its runtime
                requirement is being audited. It will be removed if confirmed
                unnecessary rather than shipped without need.
            </p>
            <p><a href="https://python-pillow.org/">python-pillow.org</a></p>

            <h3>NVIDIA NVENC</h3>
            <p>
                EMP can request NVIDIA NVENC hardware-accelerated encoding
                through compatible hardware, drivers and HandBrake builds.
                NVIDIA drivers and NVENC technology are not EMP software.
            </p>
            <p><a href="https://developer.nvidia.com/video-codec-sdk">NVIDIA Video Codec SDK</a></p>

            <h3>Jellyfin</h3>
            <p>
                EMP can connect to a user-configured Jellyfin server for
                library and poster information. Jellyfin is a separate
                project and is not bundled with EMP.
            </p>
            <p><a href="https://jellyfin.org/">jellyfin.org</a></p>
            """
        )


def show_public_about(self: MainWindow) -> None:
    PublicAboutDialog(self).exec()


def install_public_about() -> None:
    """Install the public About dialog without changing queue/encode code."""
    MainWindow.show_about = show_public_about
