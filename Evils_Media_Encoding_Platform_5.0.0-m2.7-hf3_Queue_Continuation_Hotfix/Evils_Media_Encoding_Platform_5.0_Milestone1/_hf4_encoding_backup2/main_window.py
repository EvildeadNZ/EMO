from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from collections import deque
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .updater import UpdateError, launch_external_update
from .version import APP_VERSION

try:
    import psutil
except ImportError:
    psutil = None

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, QSize, QTimer, QRectF, QUrl
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPainterPath, QPen, QBrush, QCloseEvent, QAction, QFont, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter, QStackedLayout,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget, QListWidget, QScrollArea,
    QListWidgetItem, QTabWidget, QGroupBox, QAbstractItemView, QSystemTrayIcon, QMenu, QWizard, QWizardPage,
    QRadioButton, QButtonGroup, QSlider,
)

APP_NAME = "Evil's Media Encoding Platform"
APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = APP_DIR / "config.json"
HISTORY_FILE = APP_DIR / "history.json"
LOG_FILE = APP_DIR / "evils_media_optimizer.log"
POSTER_CACHE = APP_DIR / "cache" / "posters"
INTELLIGENCE_CACHE = APP_DIR / "cache" / "library_intelligence.json"
POSTER_CACHE.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "movie_root": r"\\VaultOne\MainMovies",
    "local_work": r"C:\Evil Media Optimizer Work",
    "minimum_size_gib": 3,
    "default_target_gib": 5,
    "handbrake": "HandBrakeCLI",
    "ffprobe": "ffprobe",
    "audio_kbps": 384,
    "encoder": "nvenc_h265",
    "encoder_preset": "medium",
    "jellyfin_url": "http://192.168.68.79:28096",
    "jellyfin_api_key": "",
    "jellyfin_username": "",
    "jellyfin_device_id": "",
    "update_manifest_url": "",
    "github_repo": "EvildeadNZ/EMO",
    "queue_finish_action": "Do nothing",
    "show_live_telemetry": True,
    "analyze_media_on_scan": True,
    "theme": "Skull Purple",
    "banner_theme": "Original Purple",
    "setup_complete": False,
    "workflow_mode": "nas_pc_nas",
    "output_root": r"\\VaultOne\MainMovies",
    "media_server_type": "Jellyfin",
    "remote_worker_host": "",
    "remote_worker_path": "",
    "ui_scale_percent": 100,
}
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".m2ts", ".webm"}

THEME_PALETTES = {
    "Skull Purple": {
        "bg": "#08080c",
        "surface": "#0d0c11",
        "surface2": "#121017",
        "border": "#35243e",
        "accent": "#d35cff",
        "accent_dark": "#4f1768",
        "accent_hover": "#70218f",
        "text": "#f3edf7",
        "muted": "#a99daf",
        "success": "#70df7b",
        "warning": "#ffbd59",
        "danger": "#ff6879",
        "blue": "#5db7ff",
    },
    "OLED Black": {
        "bg": "#000000",
        "surface": "#050505",
        "surface2": "#0b0b0b",
        "border": "#292929",
        "accent": "#ffffff",
        "accent_dark": "#242424",
        "accent_hover": "#3b3b3b",
        "text": "#f7f7f7",
        "muted": "#9b9b9b",
        "success": "#62e879",
        "warning": "#ffd166",
        "danger": "#ff5f70",
        "blue": "#65bfff",
    },
    "Diablo Ember": {
        "bg": "#090403",
        "surface": "#130807",
        "surface2": "#1b0d09",
        "border": "#542117",
        "accent": "#ff6a2a",
        "accent_dark": "#6b1e0c",
        "accent_hover": "#9a2c10",
        "text": "#f8e8df",
        "muted": "#c29b88",
        "success": "#8ad16a",
        "warning": "#ffb347",
        "danger": "#ff4040",
        "blue": "#69a9ff",
    },
    "Jellyfin Violet": {
        "bg": "#070711",
        "surface": "#0c0b1a",
        "surface2": "#141129",
        "border": "#342c67",
        "accent": "#aa5cff",
        "accent_dark": "#4d237d",
        "accent_hover": "#6c32a9",
        "text": "#f1edff",
        "muted": "#aaa0cf",
        "success": "#69df91",
        "warning": "#ffc857",
        "danger": "#ff667d",
        "blue": "#58c5ff",
    },
    "Matrix Green": {
        "bg": "#010602",
        "surface": "#041008",
        "surface2": "#07190d",
        "border": "#174f29",
        "accent": "#42ff72",
        "accent_dark": "#0d5a25",
        "accent_hover": "#12843a",
        "text": "#dfffe6",
        "muted": "#78b889",
        "success": "#42ff72",
        "warning": "#d6ff5c",
        "danger": "#ff596c",
        "blue": "#5bd7ff",
    },
    "Cyberpunk Neon": {
        "bg": "#07040d",
        "surface": "#10091b",
        "surface2": "#19102a",
        "border": "#4a2870",
        "accent": "#ff3bd4",
        "accent_dark": "#6c145f",
        "accent_hover": "#9a1b89",
        "text": "#fff0fc",
        "muted": "#c3a4c9",
        "success": "#5dffb0",
        "warning": "#ffe14f",
        "danger": "#ff4d6d",
        "blue": "#00d9ff",
    },
    "Blood Moon": {
        "bg": "#080203",
        "surface": "#120507",
        "surface2": "#1b090c",
        "border": "#57202a",
        "accent": "#ff3e5f",
        "accent_dark": "#711428",
        "accent_hover": "#9d1c38",
        "text": "#ffecef",
        "muted": "#c89ca5",
        "success": "#7bd987",
        "warning": "#ffbd59",
        "danger": "#ff334f",
        "blue": "#6bb8ff",
    },
    "Arctic Blue": {
        "bg": "#03080d",
        "surface": "#07121b",
        "surface2": "#0c1c29",
        "border": "#204b67",
        "accent": "#53c9ff",
        "accent_dark": "#145276",
        "accent_hover": "#1c78a7",
        "text": "#eaf8ff",
        "muted": "#91b9cc",
        "success": "#67e3a1",
        "warning": "#ffd166",
        "danger": "#ff667b",
        "blue": "#53c9ff",
    },
    "Toxic Lime": {
        "bg": "#050701",
        "surface": "#0d1205",
        "surface2": "#151d08",
        "border": "#425d19",
        "accent": "#b7ff38",
        "accent_dark": "#3f6810",
        "accent_hover": "#5c9418",
        "text": "#f3ffe5",
        "muted": "#a9c681",
        "success": "#b7ff38",
        "warning": "#ffe25b",
        "danger": "#ff5f6f",
        "blue": "#61c9ff",
    },
    "Retro Amber": {
        "bg": "#090702",
        "surface": "#151005",
        "surface2": "#211907",
        "border": "#684b16",
        "accent": "#ffbf3f",
        "accent_dark": "#72500f",
        "accent_hover": "#a06f16",
        "text": "#fff5d9",
        "muted": "#c7ad72",
        "success": "#9ad76b",
        "warning": "#ffbf3f",
        "danger": "#ff645f",
        "blue": "#6dbbff",
    },
    "Steel Grey": {
        "bg": "#07090b",
        "surface": "#0e1216",
        "surface2": "#171d23",
        "border": "#394550",
        "accent": "#9fb3c8",
        "accent_dark": "#3e4e5d",
        "accent_hover": "#566b7d",
        "text": "#edf2f6",
        "muted": "#9daab5",
        "success": "#6fd18a",
        "warning": "#e4bd62",
        "danger": "#ef6875",
        "blue": "#6eb8ef",
    },
}

THEME_BANNERS = {'Skull Purple': 'themes/skull_purple.png', 'OLED Black': 'themes/oled_black.png', 'Diablo Ember': 'themes/diablo_ember.png', 'Jellyfin Violet': 'themes/jellyfin_violet.png', 'Matrix Green': 'themes/matrix_green.png', 'Cyberpunk Neon': 'themes/cyberpunk_neon.png', 'Blood Moon': 'themes/blood_moon.png', 'Arctic Blue': 'themes/arctic_blue.png', 'Toxic Lime': 'themes/toxic_lime.png', 'Retro Amber': 'themes/retro_amber.png', 'Steel Grey': 'themes/steel_grey.png'}





def version_key(value: str):
    # Supports normal EMP milestone versions plus chained hotfix suffixes, e.g.
    # 5.0.0-m2.5-hf1.  Keeping the hotfix number in the comparison prevents
    # GitHub releases from being incorrectly reported as "UP TO DATE".
    match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(?:[-.]?(preview|m|milestone|rc)(\d+)(?:\.(\d+))?)?(?:[-.]?hf(\d+))?$",
        value.strip().lower().lstrip("v"),
    )
    if not match:
        nums = [int(x) for x in re.findall(r"\d+", value)]
        return tuple((nums + [0, 0, 0, 0, 0, 0, 0])[:7])
    major, minor, patch = map(int, match.group(1, 2, 3))
    kind = match.group(4)
    num = int(match.group(5) or 0)
    sub = int(match.group(6) or 0)
    hotfix = int(match.group(7) or 0)
    rank = {"preview": 0, "m": 1, "milestone": 1, "rc": 2, None: 3}[kind]
    return (major, minor, patch, rank, num, sub, hotfix)

class GitHubUpdateSignals(QObject):
    done = Signal(dict)

class GitHubUpdateWorker(QRunnable):
    def __init__(self, repo: str):
        super().__init__(); self.repo = repo.strip().strip('/')
        self.signals = GitHubUpdateSignals()

    def _json(self, url: str):
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "EMP-Updater",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.load(response)

    def run(self):
        result = {"ok": False, "error": "Unknown update error"}
        try:
            repo_info = self._json(f"https://api.github.com/repos/{self.repo}")
            branch = str(repo_info.get("default_branch") or "main")
            release = None
            try:
                release = self._json(
                    f"https://api.github.com/repos/{self.repo}/releases/latest"
                )
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise

            if release:
                tag = str(release.get("tag_name", "")).lstrip("vV")
                assets = release.get("assets") or []
                zip_asset = next(
                    (a for a in assets if str(a.get("name", "")).lower().endswith(".zip")),
                    None,
                )
                result = {
                    "ok": True,
                    "version": tag,
                    "newer": bool(tag) and version_key(tag) > version_key(APP_VERSION),
                    "release_url": release.get("html_url", ""),
                    "download_url": (zip_asset or {}).get("browser_download_url", ""),
                    "asset_name": (zip_asset or {}).get("name", ""),
                    "notes": release.get("body", ""),
                    "source": "release",
                    "repo": self.repo,
                    "branch": branch,
                }
            else:
                # Before formal GitHub Releases exist, use the repository's
                # update-package.json as the source of truth and download the
                # current branch archive when it advertises a newer build.
                manifest_url = (
                    f"https://raw.githubusercontent.com/{self.repo}/{branch}/"
                    "update-package.json"
                )
                manifest = self._json(manifest_url)
                tag = str(manifest.get("version", "")).lstrip("vV")
                result = {
                    "ok": True,
                    "version": tag,
                    "newer": bool(tag) and version_key(tag) > version_key(APP_VERSION),
                    "release_url": f"https://github.com/{self.repo}",
                    "download_url": (
                        f"https://codeload.github.com/{self.repo}/zip/refs/heads/{branch}"
                    ),
                    "asset_name": f"EMP-{branch}.zip",
                    "notes": "Latest build advertised by update-package.json",
                    "source": "branch",
                    "repo": self.repo,
                    "branch": branch,
                }
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                result = {
                    "ok": False,
                    "error": (
                        f"GitHub repository or update metadata was not found: {self.repo}. "
                        "Make sure the repository is public and contains update-package.json."
                    ),
                }
            else:
                result = {"ok": False, "error": f"GitHub HTTP {exc.code}: {exc.reason}"}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        self.signals.done.emit(result)

def scale_qss_font_sizes(qss: str, percent: int) -> str:
    """Scale pixel font sizes in EMP's stylesheet without changing layout dimensions."""
    factor = max(0.85, min(1.50, int(percent) / 100.0))

    def repl(match):
        value = int(match.group(1))
        return f"font-size:{max(8, round(value * factor))}px"

    return re.sub(r"font-size\s*:\s*(\d+)px", repl, qss)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        config = {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
        if not str(config.get("github_repo", "")).strip():
            config["github_repo"] = DEFAULT_CONFIG["github_repo"]
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def hidden_process_kwargs() -> dict:
    """Return subprocess options that suppress console windows on Windows."""
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }


def log(message: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TiB"


def is_sample(path: Path) -> bool:
    low = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return any(word in low for word in ("sample", "trailer", "featurette")) or "extras" in parts or "sample" in parts



def split_title_year(folder_name: str) -> tuple[str, int | None]:
    match = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", folder_name.strip())
    if match:
        return match.group(1).strip(), int(match.group(2))
    return folder_name.strip(), None


def jellyfin_poster_path(
    movie: "Movie",
    config: dict,
    force_refresh: bool = False,
) -> tuple[Path | None, str]:
    base_url = str(config.get("jellyfin_url", "")).strip().rstrip("/")
    api_key = str(config.get("jellyfin_api_key", "")).strip()

    if not base_url or not api_key:
        return None, "Jellyfin URL or API key is not configured."

    cache_key = hashlib.sha256(
        str(movie.path).encode("utf-8")
    ).hexdigest()[:20]
    cached = POSTER_CACHE / f"{cache_key}.jpg"

    if (
        not force_refresh
        and cached.exists()
        and cached.stat().st_size > 0
    ):
        return cached, "Loaded cached Jellyfin poster."

    cached.unlink(missing_ok=True)

    title, year = split_title_year(movie.title)

    # Jellyfin's item Path may use the Docker-visible path, so start with
    # a broad movie list and match on title/year, then fall back to search.
    item_fields = "Path,ProductionYear,ImageTags,ProviderIds"
    candidate_queries = [
        {
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": item_fields,
            "Limit": "10000",
            "api_key": api_key,
        },
        {
            "SearchTerm": title,
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": item_fields,
            "Limit": "100",
            "api_key": api_key,
        },
    ]

    try:
        items: list[dict] = []
        for query in candidate_queries:
            url = f"{base_url}/Items?{urllib.parse.urlencode(query)}"
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(
                    response.read().decode("utf-8", errors="replace")
                )
            items = payload.get("Items", [])
            if items:
                break

        if not items:
            return None, f"Jellyfin returned no movie items for {movie.title}."

        def clean(value: str) -> str:
            return re.sub(r"[^a-z0-9]+", "", value.casefold())

        wanted_title = clean(title)
        wanted_folder = clean(movie.title)
        wanted_filename = clean(movie.path.stem)

        def score(item: dict) -> tuple[int, int, int, int, int]:
            item_name = str(item.get("Name", ""))
            item_path = str(item.get("Path", ""))
            item_year = item.get("ProductionYear")

            name_clean = clean(item_name)
            path_clean = clean(Path(item_path).parent.name) if item_path else ""
            filename_clean = clean(Path(item_path).stem) if item_path else ""

            exact_title = int(name_clean == wanted_title)
            exact_folder = int(path_clean == wanted_folder)
            filename_match = int(
                wanted_title in filename_clean
                or name_clean in wanted_filename
            )
            year_match = int(year is not None and item_year == year)
            has_primary = int(
                bool(item.get("ImageTags", {}).get("Primary"))
            )
            return (
                exact_folder,
                exact_title,
                year_match,
                filename_match,
                has_primary,
            )

        item = max(items, key=score)
        best_score = score(item)

        if not any(best_score[:4]):
            return (
                None,
                f"No confident Jellyfin match for {movie.title}. "
                f"Best result was {item.get('Name', 'unknown')}.",
            )

        item_id = item.get("Id")
        if not item_id:
            return None, "The matched Jellyfin item had no item ID."

        image_url = (
            f"{base_url}/Items/"
            f"{urllib.parse.quote(str(item_id))}/Images/Primary?"
            + urllib.parse.urlencode(
                {
                    "maxWidth": 600,
                    "quality": 92,
                    "api_key": api_key,
                }
            )
        )
        image_request = urllib.request.Request(
            image_url,
            headers={"Accept": "image/*"},
        )
        with urllib.request.urlopen(
            image_request,
            timeout=20,
        ) as response:
            content_type = response.headers.get(
                "Content-Type",
                "",
            )
            data = response.read()

        if not data:
            return None, "Jellyfin returned an empty poster image."

        if not content_type.startswith("image/"):
            return (
                None,
                f"Jellyfin returned {content_type or 'non-image data'} "
                "instead of a poster.",
            )

        cached.write_bytes(data)

        pixmap = QPixmap(str(cached))
        if pixmap.isNull():
            cached.unlink(missing_ok=True)
            return None, "The downloaded poster was not a valid image."

        return (
            cached,
            f"Loaded Jellyfin poster for "
            f"{item.get('Name', movie.title)}"
            + (
                f" ({item.get('ProductionYear')})"
                if item.get("ProductionYear")
                else ""
            ),
        )

    except Exception as exc:
        message = f"Jellyfin poster lookup failed for {movie.title}: {exc}"
        log(message)
        return None, str(exc)


def _jellyfin_token_headers(token: str, device_id: str) -> dict[str, str]:
    auth_header = (
        'MediaBrowser Client="Evil\'s Media Encoding Platform", '
        'Device="Windows PC", '
        f'DeviceId="{device_id}", '
        f'Version="{APP_VERSION}", '
        f'Token="{token}"'
    )
    return {
        "Accept": "application/json",
        "Authorization": auth_header,
        "X-Emby-Authorization": auth_header,
        "X-Emby-Token": token,
    }


def _get_or_create_jellyfin_api_key(
    base_url: str,
    login_token: str,
    device_id: str,
) -> tuple[str, str]:
    """Return a persistent EMP API key when the signed-in user may manage keys."""
    app_name = "Evil's Media Encoding Platform"
    headers = _jellyfin_token_headers(login_token, device_id)

    def fetch_keys() -> list[dict]:
        request = urllib.request.Request(
            f"{base_url}/Auth/Keys",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(
                response.read().decode("utf-8", errors="replace")
            )
        if isinstance(payload, dict):
            items = payload.get("Items") or payload.get("items") or []
            return items if isinstance(items, list) else []
        return []

    def matching_key(items: list[dict]) -> str:
        for item in reversed(items):
            name = str(
                item.get("AppName")
                or item.get("appName")
                or item.get("App")
                or ""
            ).strip()
            token = str(
                item.get("AccessToken")
                or item.get("accessToken")
                or item.get("Token")
                or ""
            ).strip()
            if name.casefold() == app_name.casefold() and token:
                return token
        return ""

    items = fetch_keys()
    existing = matching_key(items)
    if existing:
        return existing, "Existing EMP API key retrieved from Jellyfin."

    create_url = (
        f"{base_url}/Auth/Keys?"
        + urllib.parse.urlencode({"app": app_name})
    )
    create_request = urllib.request.Request(
        create_url,
        data=b"",
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(create_request, timeout=10):
        pass

    created = matching_key(fetch_keys())
    if not created:
        raise RuntimeError(
            "Jellyfin created the EMP key but did not return it when keys were refreshed."
        )
    return created, "New EMP API key created and retrieved from Jellyfin."


def authenticate_jellyfin(
    base_url: str,
    username: str,
    password: str,
    *,
    device_id: str = "",
) -> tuple[bool, str, str, str]:
    """Sign in once, then retrieve/create EMP's persistent Jellyfin API key."""
    base_url = str(base_url or "").strip().rstrip("/")
    username = str(username or "").strip()
    if not base_url:
        return False, "Enter the Jellyfin server URL.", "", device_id
    if not username:
        return False, "Enter your Jellyfin username.", "", device_id

    device_id = str(device_id or "").strip() or str(uuid.uuid4())
    auth_header = (
        'MediaBrowser Client="Evil\'s Media Encoding Platform", '
        'Device="Windows PC", '
        f'DeviceId="{device_id}", '
        f'Version="{APP_VERSION}"'
    )
    payload = json.dumps({
        "Username": username,
        "Pw": password or "",
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/Users/AuthenticateByName",
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "X-Emby-Authorization": auth_header,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8", errors="replace"))
        login_token = str(result.get("AccessToken", "")).strip()
        if not login_token:
            return False, "Jellyfin authenticated but did not return an access token.", "", device_id
        user = result.get("User") or {}
        display_name = str(user.get("Name") or username).strip()

        try:
            api_key, key_detail = _get_or_create_jellyfin_api_key(
                base_url, login_token, device_id
            )
            return (
                True,
                f"Connected as {display_name}. {key_detail} Password was not stored.",
                api_key,
                device_id,
            )
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return (
                    True,
                    f"Connected as {display_name}. This account cannot manage Jellyfin API keys, "
                    "so EMP saved the signed-in access token instead. Use an administrator account "
                    "with Connect to Jellyfin to let EMP retrieve/create its persistent API key.",
                    login_token,
                    device_id,
                )
            raise
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, "Jellyfin rejected the username or password.", "", device_id
        return False, f"Jellyfin returned HTTP {exc.code}.", "", device_id
    except Exception as exc:
        return False, str(exc), "", device_id


def test_jellyfin(config: dict) -> tuple[bool, str]:
    base_url = str(config.get("jellyfin_url", "")).strip().rstrip("/")
    api_key = str(config.get("jellyfin_api_key", "")).strip()

    if not base_url:
        return False, "Enter the Jellyfin URL."
    if not api_key:
        return False, "Enter a Jellyfin API key."

    try:
        url = f"{base_url}/System/Info?" + urllib.parse.urlencode(
            {"api_key": api_key}
        )
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(
                response.read().decode("utf-8", errors="replace")
            )

        server_name = payload.get("ServerName", "Jellyfin")
        version = payload.get("Version", "")
        return True, f"Connected to {server_name} {version}".strip()

    except Exception as exc:
        return False, str(exc)


def format_runtime(seconds: float) -> str:
    if seconds <= 0:
        return "Unknown"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def normalize_movie_title(value: str) -> str:
    title, _year = split_title_year(value)
    cleaned = re.sub(
        r"\b(2160p|1080p|720p|4k|uhd|bluray|blu-ray|webrip|web-dl|remux|x264|x265|hevc|h264)\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[^a-z0-9]+", "", cleaned.casefold())


def load_intelligence_cache() -> dict:
    try:
        if INTELLIGENCE_CACHE.exists():
            payload = json.loads(
                INTELLIGENCE_CACHE.read_text(encoding="utf-8")
            )
            if isinstance(payload, dict):
                return payload
    except Exception as exc:
        log(f"Could not load intelligence cache: {exc}")
    return {}


def save_intelligence_cache(payload: dict) -> None:
    try:
        INTELLIGENCE_CACHE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = INTELLIGENCE_CACHE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        temporary.replace(INTELLIGENCE_CACHE)
    except Exception as exc:
        log(f"Could not save intelligence cache: {exc}")


@dataclass
class Movie:
    path: Path
    size: int
    target_gib: int = 5
    queued: bool = False
    selected: bool = False
    status: str = "Ready"
    duration_seconds: float = 0.0
    video_codec: str = ""
    video_profile: str = ""
    width: int = 0
    height: int = 0
    pix_fmt: str = ""
    hdr_format: str = ""
    audio_codec: str = ""
    audio_channels: int = 0
    subtitle_count: int = 0
    overall_bitrate: int = 0
    metadata_status: str = "Pending"
    duplicate_count: int = 0

    @property
    def title(self) -> str:
        return self.path.parent.name

    @property
    def saving(self) -> int:
        return max(
            0,
            self.size - int(self.target_gib * 1024**3),
        )

    @property
    def saving_percent(self) -> int:
        return (
            int(self.saving / self.size * 100)
            if self.size
            else 0
        )

    @property
    def runtime_text(self) -> str:
        return format_runtime(self.duration_seconds)

    @property
    def resolution_text(self) -> str:
        if self.height >= 2100 or self.width >= 3800:
            return "2160p"
        if self.height >= 1400:
            return "1440p"
        if self.height >= 1000:
            return "1080p"
        if self.height >= 700:
            return "720p"
        if self.height:
            return f"{self.height}p"
        return "Unknown"

    @property
    def video_text(self) -> str:
        labels = {
            "hevc": "HEVC",
            "h265": "HEVC",
            "h264": "H.264",
            "av1": "AV1",
            "mpeg2video": "MPEG-2",
            "vc1": "VC-1",
            "vp9": "VP9",
        }
        codec = labels.get(
            self.video_codec.casefold(),
            self.video_codec.upper()
            if self.video_codec
            else "Unknown",
        )
        pieces = [codec, self.resolution_text]
        if self.hdr_format:
            pieces.append(self.hdr_format)
        return " â€¢ ".join(piece for piece in pieces if piece)

    @property
    def audio_text(self) -> str:
        labels = {
            "aac": "AAC",
            "ac3": "AC-3",
            "eac3": "E-AC-3",
            "dts": "DTS",
            "truehd": "TrueHD",
            "flac": "FLAC",
        }
        codec = labels.get(
            self.audio_codec.casefold(),
            self.audio_codec.upper()
            if self.audio_codec
            else "Unknown",
        )
        if self.audio_channels:
            return f"{codec} â€¢ {self.audio_channels} ch"
        return codec

    @property
    def bitrate_mbps(self) -> float:
        return (
            self.overall_bitrate / 1_000_000
            if self.overall_bitrate
            else 0.0
        )

    @property
    def optimization_breakdown(self) -> dict[str, int]:
        """
        Return the score components used by EMO.

        Positive values increase optimization priority. Negative values
        reduce it. This is advice only and never changes queue selection.
        """
        codec = self.video_codec.casefold()
        bitrate = self.bitrate_mbps
        saving_gib = self.saving / 1024**3

        breakdown = {
            "Codec": 0,
            "Bitrate": 0,
            "Recoverable storage": 0,
            "Saving percentage": 0,
            "Resolution": 0,
            "Efficiency penalty": 0,
        }

        if codec in {"mpeg2video", "vc1", "mpeg4"}:
            breakdown["Codec"] = 28
        elif codec in {"h264", "avc"}:
            breakdown["Codec"] = 20
        elif codec in {"hevc", "h265", "vp9"}:
            breakdown["Codec"] = 7
        elif codec == "av1":
            breakdown["Codec"] = 3
        elif codec:
            breakdown["Codec"] = 12

        if bitrate >= 45:
            breakdown["Bitrate"] = 20
        elif bitrate >= 30:
            breakdown["Bitrate"] = 16
        elif bitrate >= 18:
            breakdown["Bitrate"] = 11
        elif bitrate >= 10:
            breakdown["Bitrate"] = 6
        elif bitrate > 0:
            breakdown["Bitrate"] = 2

        if saving_gib >= 30:
            breakdown["Recoverable storage"] = 22
        elif saving_gib >= 15:
            breakdown["Recoverable storage"] = 18
        elif saving_gib >= 7:
            breakdown["Recoverable storage"] = 12
        elif saving_gib >= 3:
            breakdown["Recoverable storage"] = 7
        elif saving_gib > 1:
            breakdown["Recoverable storage"] = 3

        if self.saving_percent >= 80:
            breakdown["Saving percentage"] = 20
        elif self.saving_percent >= 65:
            breakdown["Saving percentage"] = 16
        elif self.saving_percent >= 50:
            breakdown["Saving percentage"] = 11
        elif self.saving_percent >= 30:
            breakdown["Saving percentage"] = 5

        if self.resolution_text == "2160p":
            breakdown["Resolution"] = 8
        elif self.resolution_text in {"1440p", "1080p"}:
            breakdown["Resolution"] = 5
        elif self.height:
            breakdown["Resolution"] = 3

        if codec in {"hevc", "h265", "av1"} and bitrate < 18:
            breakdown["Efficiency penalty"] = -12
        elif codec in {"hevc", "h265", "vp9"}:
            breakdown["Efficiency penalty"] = -5

        if self.target_gib * 1024**3 >= self.size:
            breakdown["Efficiency penalty"] = -40

        return breakdown

    @property
    def optimization_score(self) -> int:
        base = 12
        score = base + sum(self.optimization_breakdown.values())
        return max(0, min(100, score))

    @property
    def optimization_rating(self) -> str:
        score = self.optimization_score
        if score >= 90:
            return "EXCELLENT CANDIDATE"
        if score >= 75:
            return "VERY GOOD CANDIDATE"
        if score >= 60:
            return "GOOD CANDIDATE"
        if score >= 40:
            return "WORTH REVIEWING"
        return "ALREADY EFFICIENT"

    @property
    def score_colour(self) -> str:
        score = self.optimization_score
        if score >= 90:
            return "#d35cff"
        if score >= 75:
            return "#70df7b"
        if score >= 60:
            return "#5db7ff"
        if score >= 40:
            return "#ffbd59"
        return "#a59aa9"

    @property
    def visual_risk(self) -> str:
        codec = self.video_codec.casefold()
        if self.hdr_badge not in {"SDR", "UNKNOWN"}:
            return "MEDIUM"
        if codec in {"hevc", "h265", "av1"} and self.saving_percent >= 65:
            return "MEDIUM"
        if self.saving_percent >= 80:
            return "MEDIUM"
        return "LOW"

    @property
    def health_score(self) -> int:
        """Convert the 100-point Optimization Score to one to five stars."""
        score = self.optimization_score
        if score >= 90:
            return 5
        if score >= 75:
            return 4
        if score >= 60:
            return 3
        if score >= 40:
            return 2
        return 1

    @property
    def health_stars(self) -> str:
        return (
            "â˜…" * self.health_score
            + "â˜†" * (5 - self.health_score)
        )

    @property
    def recommendation_reasons(self) -> list[str]:
        reasons: list[str] = []
        codec = self.video_codec.casefold()
        saving_gib = self.saving / 1024**3
        bitrate = self.bitrate_mbps

        if codec in {"mpeg2video", "vc1", "mpeg4"}:
            reasons.append(
                f"Older {self.codec_badge} source usually compresses very well"
            )
        elif codec in {"h264", "avc"}:
            reasons.append(
                "H.264 source is a strong candidate for HEVC NVENC"
            )
        elif codec in {"hevc", "h265", "av1", "vp9"}:
            reasons.append(
                f"{self.codec_badge} is already a modern efficient codec"
            )
        elif self.video_codec:
            reasons.append(f"Source codec: {self.codec_badge}")

        if bitrate >= 35:
            reasons.append(
                f"Very high source bitrate ({bitrate:.1f} Mb/s)"
            )
        elif bitrate >= 18:
            reasons.append(
                f"High source bitrate ({bitrate:.1f} Mb/s)"
            )
        elif bitrate:
            reasons.append(
                f"Source bitrate is {bitrate:.1f} Mb/s"
            )

        if saving_gib >= 5:
            reasons.append(
                f"Manual target could recover about {saving_gib:.1f} GiB"
            )
        else:
            reasons.append(
                "Only a small amount of storage is expected to be recovered"
            )

        if self.hdr_badge not in {"SDR", "UNKNOWN"}:
            reasons.append(
                f"{self.hdr_badge} detected â€” review quality after encoding"
            )

        if self.subtitle_count == 0:
            reasons.append("No subtitle streams were detected")

        return reasons[:5]

    @property
    def recommendation(self) -> tuple[str, str]:
        reasons = self.recommendation_reasons
        return (
            self.optimization_rating,
            reasons[0]
            if reasons
            else "Insufficient metadata for detailed reasoning.",
        )


    @property
    def codec_badge(self) -> str:
        labels = {
            "hevc": "HEVC",
            "h265": "HEVC",
            "h264": "H.264",
            "avc": "H.264",
            "av1": "AV1",
            "mpeg2video": "MPEG-2",
            "vc1": "VC-1",
            "vp9": "VP9",
            "mpeg4": "MPEG-4",
        }
        return labels.get(
            self.video_codec.casefold(),
            self.video_codec.upper()
            if self.video_codec
            else "UNKNOWN",
        )

    @property
    def resolution_badge(self) -> str:
        if self.resolution_text == "2160p":
            return "4K"
        if self.height and self.height < 700:
            return "DVD"
        return self.resolution_text.upper()

    @property
    def hdr_badge(self) -> str:
        value = self.hdr_format.strip()
        return value.upper() if value else "SDR"

    @property
    def audio_badge(self) -> str:
        labels = {
            "truehd": "TRUEHD",
            "dts": "DTS",
            "eac3": "E-AC-3",
            "ac3": "AC-3",
            "aac": "AAC",
            "flac": "FLAC",
        }
        return labels.get(
            self.audio_codec.casefold(),
            self.audio_codec.upper()
            if self.audio_codec
            else "AUDIO?",
        )

    @property
    def subtitle_badge(self) -> str:
        return (
            f"{self.subtitle_count} SUB"
            if self.subtitle_count
            else "NO SUBS"
        )

    @property
    def badges_text(self) -> str:
        return "  ".join(
            (
                self.codec_badge,
                self.resolution_badge,
                self.hdr_badge,
                self.audio_badge,
                self.subtitle_badge,
            )
        )

    def apply_metadata(self, payload: dict) -> None:
        self.duration_seconds = float(
            payload.get("duration_seconds", 0) or 0
        )
        self.video_codec = str(
            payload.get("video_codec", "") or ""
        )
        self.video_profile = str(
            payload.get("video_profile", "") or ""
        )
        self.width = int(payload.get("width", 0) or 0)
        self.height = int(payload.get("height", 0) or 0)
        self.pix_fmt = str(payload.get("pix_fmt", "") or "")
        self.hdr_format = str(
            payload.get("hdr_format", "") or ""
        )
        self.audio_codec = str(
            payload.get("audio_codec", "") or ""
        )
        self.audio_channels = int(
            payload.get("audio_channels", 0) or 0
        )
        self.subtitle_count = int(
            payload.get("subtitle_count", 0) or 0
        )
        self.overall_bitrate = int(
            payload.get("overall_bitrate", 0) or 0
        )
        self.metadata_status = str(
            payload.get("metadata_status", "Ready")
        )

    def metadata_payload(self) -> dict:
        return {
            "duration_seconds": self.duration_seconds,
            "video_codec": self.video_codec,
            "video_profile": self.video_profile,
            "width": self.width,
            "height": self.height,
            "pix_fmt": self.pix_fmt,
            "hdr_format": self.hdr_format,
            "audio_codec": self.audio_codec,
            "audio_channels": self.audio_channels,
            "subtitle_count": self.subtitle_count,
            "overall_bitrate": self.overall_bitrate,
            "metadata_status": self.metadata_status,
        }

    def poster_path(self) -> Path | None:
        candidates = (
            "poster.jpg",
            "poster.png",
            "folder.jpg",
            "folder.png",
            f"{self.path.parent.name}-poster.jpg",
        )
        for name in candidates:
            candidate = self.path.parent / name
            if candidate.exists():
                return candidate
        try:
            for candidate in self.path.parent.iterdir():
                if (
                    candidate.is_file()
                    and candidate.suffix.lower()
                    in {".jpg", ".jpeg", ".png", ".webp"}
                    and "trickplay" not in candidate.name.lower()
                    and "fanart" not in candidate.name.lower()
                    and "backdrop" not in candidate.name.lower()
                ):
                    return candidate
        except OSError:
            pass
        return None


class Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)
    message = Signal(str)
    stage = Signal(str)


class Scanner(QRunnable):
    def __init__(self, root: Path, minimum_bytes: int, default_target: int):
        super().__init__()
        self.root = root
        self.minimum_bytes = minimum_bytes
        self.default_target = default_target
        self.signals = Signals()

    def run(self):
        try:
            if not self.root.exists():
                raise FileNotFoundError(f"Cannot access {self.root}. Open it in File Explorer first.")
            found: list[Movie] = []
            bluray_streams: dict[str, Path] = {}
            for root, dirs, files in os.walk(self.root):
                dirs[:] = [d for d in dirs if d.lower() != "#recycle" and not d.lower().endswith(".trickplay")]
                for name in files:
                    path = Path(root) / name
                    if path.suffix.lower() not in VIDEO_EXTENSIONS or is_sample(path):
                        continue
                    if name.lower().endswith((".partial", ".evils-backup", ".dvdrobot-backup")):
                        continue
                    try:
                        size = path.stat().st_size
                    except OSError:
                        continue
                    if size <= self.minimum_bytes:
                        continue
                    upper = [part.upper() for part in path.parts]
                    if path.suffix.lower() == ".m2ts" and "BDMV" in upper and "STREAM" in upper:
                        index = upper.index("BDMV")
                        key = str(Path(*path.parts[:index])).lower()
                        old = bluray_streams.get(key)
                        if old is None or size > old.stat().st_size:
                            bluray_streams[key] = path
                    else:
                        found.append(Movie(path, size, self.default_target))
            found.extend(Movie(path, path.stat().st_size, self.default_target) for path in bluray_streams.values())
            found.sort(key=lambda movie: movie.size, reverse=True)
            self.signals.finished.emit(found)
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class PosterPrefetchWorker(QRunnable):
    def __init__(self, movies: list[Movie], config: dict):
        super().__init__()
        self.movies = list(movies)
        self.config = config.copy()
        self.signals = Signals()

    def run(self):
        try:
            total = len(self.movies)
            downloaded = 0
            available = 0

            for index, movie in enumerate(self.movies, 1):
                local = movie.poster_path()
                if local:
                    available += 1
                    detail = f"Existing poster: {movie.title}"
                else:
                    poster, detail = jellyfin_poster_path(
                        movie,
                        self.config,
                    )
                    if poster:
                        downloaded += 1
                        available += 1

                percent = int(index / total * 100) if total else 100
                self.signals.progress.emit(
                    percent,
                    f"Posters {index}/{total}: {movie.title}",
                )

            self.signals.finished.emit(
                {
                    "downloaded": downloaded,
                    "available": available,
                    "total": total,
                }
            )
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class MetadataWorker(QRunnable):
    def __init__(
        self,
        movies: list[Movie],
        config: dict,
    ):
        super().__init__()
        self.movies = list(movies)
        self.config = config.copy()
        self.signals = Signals()

    def cache_key(self, movie: Movie) -> str:
        try:
            modified = movie.path.stat().st_mtime_ns
        except OSError:
            modified = 0
        raw = f"{movie.path}|{movie.size}|{modified}"
        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def inspect_movie(self, movie: Movie) -> dict:
        command = [
            self.config.get("ffprobe", "ffprobe"),
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(movie.path),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
            **hidden_process_kwargs(),
        )
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "ffprobe could not inspect this movie."
            )

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        format_data = data.get("format", {})

        videos = [
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
            and not stream.get("disposition", {}).get(
                "attached_pic",
                0,
            )
        ]
        audios = [
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ]
        subtitles = [
            stream
            for stream in streams
            if stream.get("codec_type") == "subtitle"
        ]

        video = videos[0] if videos else {}
        audio = audios[0] if audios else {}
        transfer = str(
            video.get("color_transfer", "")
        ).casefold()
        pix_fmt = str(video.get("pix_fmt", "") or "")
        hdr_format = ""

        if transfer == "smpte2084":
            hdr_format = "HDR10"
        elif transfer == "arib-std-b67":
            hdr_format = "HLG"
        elif "dvhe" in str(
            video.get("codec_tag_string", "")
        ).casefold():
            hdr_format = "Dolby Vision"
        elif any(
            token in pix_fmt.casefold()
            for token in (
                "p10",
                "10le",
                "10be",
                "12le",
                "12be",
            )
        ):
            hdr_format = "10-bit"

        return {
            "duration_seconds": float(
                format_data.get("duration", 0) or 0
            ),
            "video_codec": video.get("codec_name", "") or "",
            "video_profile": video.get("profile", "") or "",
            "width": int(video.get("width", 0) or 0),
            "height": int(video.get("height", 0) or 0),
            "pix_fmt": pix_fmt,
            "hdr_format": hdr_format,
            "audio_codec": audio.get("codec_name", "") or "",
            "audio_channels": int(
                audio.get("channels", 0) or 0
            ),
            "subtitle_count": len(subtitles),
            "overall_bitrate": int(
                format_data.get("bit_rate", 0) or 0
            ),
            "metadata_status": "Ready",
        }

    def run(self):
        try:
            ffprobe = self.config.get("ffprobe", "ffprobe")
            if shutil.which(ffprobe) is None:
                raise FileNotFoundError(
                    f"{ffprobe} was not found in PATH."
                )

            cache = load_intelligence_cache()
            updated_cache = dict(cache)
            analyzed = 0
            cached_count = 0
            failed = 0
            total = len(self.movies)

            for index, movie in enumerate(self.movies, 1):
                key = self.cache_key(movie)
                payload = cache.get(key)

                if isinstance(payload, dict):
                    movie.apply_metadata(payload)
                    cached_count += 1
                else:
                    try:
                        payload = self.inspect_movie(movie)
                        movie.apply_metadata(payload)
                        updated_cache[key] = payload
                        analyzed += 1
                    except Exception as exc:
                        movie.metadata_status = "Failed"
                        failed += 1
                        log(
                            f"Metadata failed for {movie.path}: {exc}"
                        )

                percent = (
                    int(index / total * 100)
                    if total
                    else 100
                )
                self.signals.progress.emit(
                    percent,
                    f"Analyzing {index}/{total}: {movie.title}",
                )

            save_intelligence_cache(updated_cache)
            self.signals.finished.emit(
                {
                    "analyzed": analyzed,
                    "cached": cached_count,
                    "failed": failed,
                    "total": total,
                }
            )
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class EncodeWorker(QRunnable):
    def __init__(self, movie: Movie, config: dict):
        super().__init__()
        self.movie = movie
        self.config = config.copy()
        self.signals = Signals()

    def copy_with_progress(self, source: Path, destination: Path, label: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = source.stat().st_size
        copied = 0
        with source.open("rb") as src, destination.open("wb") as dst:
            while True:
                chunk = src.read(16 * 1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                self.signals.progress.emit(int(copied / total * 100), f"{label}: {human_size(copied)} / {human_size(total)}")
            dst.flush(); os.fsync(dst.fileno())

    def duration(self, source: Path) -> float:
        result = subprocess.run(
            [
                self.config["ffprobe"],
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(source),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **hidden_process_kwargs(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffprobe could not read the movie duration.")
        value = float(result.stdout.strip())
        if value <= 0:
            raise RuntimeError("Invalid movie duration.")
        return value

    def run_handbrake(self, command: list[str]) -> None:
        log("Running: " + subprocess.list2cmdline(command))
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **hidden_process_kwargs(),
        )
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip()
            log(line)
            if "Encoding:" in line and "%" in line:
                try:
                    percent = float(line.split("%", 1)[0].rsplit(",", 1)[1].strip())
                    eta = line.split("ETA ", 1)[1].rstrip(")") if "ETA " in line else "calculating"
                    self.signals.progress.emit(int(percent), f"Encoding {percent:.1f}% â€” ETA {eta}")
                except Exception:
                    pass
        code = process.wait()
        if code != 0:
            raise RuntimeError(f"HandBrake failed with exit code {code}.")

    def run(self):
        source = self.movie.path
        job_hash = hashlib.sha256(str(source).encode()).hexdigest()[:12]
        work = Path(self.config["local_work"]) / f"job_{job_hash}"
        local_source = work / f"source{source.suffix.lower()}"
        local_output = work / "output.mkv"
        try:
            for name in (self.config["handbrake"], self.config["ffprobe"]):
                if shutil.which(name) is None:
                    raise FileNotFoundError(f"{name} is not installed or is not available in PATH.")
            work.mkdir(parents=True, exist_ok=True)
            self.signals.stage.emit("download")
            self.signals.message.emit(f"Copying {self.movie.title} from NAS to PC...")
            if not local_source.exists() or local_source.stat().st_size != source.stat().st_size:
                local_source.unlink(missing_ok=True)
                self.copy_with_progress(source, local_source, "NAS â†’ PC")
            duration = self.duration(local_source)
            target_bytes = int(self.movie.target_gib * 0.96 * 1024**3)
            total_kbps = target_bytes * 8 * 0.96 / duration / 1000
            video_kbps = int(total_kbps - int(self.config["audio_kbps"]))
            if video_kbps < 500:
                raise RuntimeError("The selected target size is too small for this movie.")
            local_output.unlink(missing_ok=True)
            self.signals.stage.emit("encoding")
            self.signals.message.emit(f"Encoding {self.movie.title} to about {self.movie.target_gib} GiB...")
            command = [
                self.config["handbrake"], "-i", str(local_source), "-o", str(local_output),
                "-f", "av_mkv", "-m", "--keep-metadata", "-e", self.config["encoder"],
                "--encoder-preset", self.config["encoder_preset"], "-b", str(video_kbps),
                "--multi-pass", "--vfr", "--audio-lang-list", "eng,und", "--first-audio",
                "-E", "av_aac", "-B", str(self.config["audio_kbps"]),
                "--subtitle-lang-list", "eng", "--all-subtitles", "--subtitle-default=none"
            ]
            self.run_handbrake(command)
            if not local_output.exists() or local_output.stat().st_size == 0:
                raise RuntimeError("HandBrake did not produce an output file.")
            final = source.with_suffix(".mkv")
            partial = final.with_name(final.name + ".partial")
            backup = source.with_name(source.name + ".evils-backup")
            if final.exists() and final != source:
                raise FileExistsError(f"A different MKV already exists: {final}")
            if backup.exists():
                raise FileExistsError(f"A backup already exists: {backup}")
            partial.unlink(missing_ok=True)
            self.signals.stage.emit("upload")
            self.signals.message.emit("Copying optimized movie back to NAS...")
            self.copy_with_progress(local_output, partial, "PC â†’ NAS")
            self.signals.stage.emit("verifying")
            if partial.stat().st_size != local_output.stat().st_size:
                raise RuntimeError("NAS copy verification failed.")
            source.rename(backup)
            try:
                partial.rename(final)
                if not final.exists() or final.stat().st_size != local_output.stat().st_size:
                    raise RuntimeError("Final NAS verification failed.")
                backup.unlink()
            except Exception:
                final.unlink(missing_ok=True)
                if backup.exists() and not source.exists():
                    backup.rename(source)
                raise
            history = []
            if HISTORY_FILE.exists():
                try: history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                except Exception: history = []
            history.append({"movie": self.movie.title, "original": self.movie.size,
                            "new": final.stat().st_size, "target_gib": self.movie.target_gib,
                            "completed": time.strftime("%Y-%m-%d %H:%M:%S")})
            HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
            shutil.rmtree(work, ignore_errors=True)
            self.signals.stage.emit("complete")
            self.signals.progress.emit(100, "Complete")
            self.signals.finished.emit(final)
        except Exception as exc:
            log(f"FAILED {self.movie.title}: {exc}")
            self.signals.failed.emit(str(exc))


class SparklineWidget(QWidget):
    def __init__(
        self,
        title: str,
        unit: str,
        maximum: float | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.maximum = maximum
        self.values = deque([0.0] * 60, maxlen=60)
        self.current_value = 0.0
        self.setMinimumHeight(82)
        self.setMaximumHeight(82)

    def set_metric(
        self,
        title: str,
        unit: str,
        maximum: float | None = None,
    ):
        changed = (
            self.title != title
            or self.unit != unit
            or self.maximum != maximum
        )
        self.title = title
        self.unit = unit
        self.maximum = maximum
        if changed:
            self.clear_values()
        self.update()

    def set_value(self, value: float):
        self.current_value = max(0.0, float(value))
        self.values.append(self.current_value)
        self.update()

    def clear_values(self):
        self.values.clear()
        self.values.extend([0.0] * 60)
        self.current_value = 0.0
        self.update()

    def formatted_value(self) -> str:
        if self.unit == "%":
            return f"{self.current_value:.0f}%"
        if self.unit == "MB/s":
            return f"{self.current_value:.1f} MB/s"
        if self.unit == "Â°C":
            return f"{self.current_value:.0f}Â°C"
        if self.unit == "GB":
            return f"{self.current_value:.1f} GB"
        return f"{self.current_value:.1f} {self.unit}"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bounds = QRectF(self.rect())
        painter.fillRect(bounds, QColor("#0d0a11"))

        painter.setPen(QColor("#d5c9dc"))
        title_font = painter.font()
        title_font.setBold(True)
        title_font.setPointSize(8)
        painter.setFont(title_font)
        painter.drawText(9, 17, self.title)

        painter.setPen(QColor("#d35cff"))
        value_font = painter.font()
        value_font.setBold(True)
        value_font.setPointSize(10)
        painter.setFont(value_font)
        value_text = self.formatted_value()
        value_width = painter.fontMetrics().horizontalAdvance(value_text)
        painter.drawText(
            max(9, self.width() - value_width - 9),
            17,
            value_text,
        )

        graph = QRectF(7, 27, max(10, self.width() - 14), 47)

        painter.setPen(QPen(QColor("#2d2134")))
        for fraction in (0.25, 0.5, 0.75):
            y = graph.top() + graph.height() * fraction
            painter.drawLine(
                int(graph.left()),
                int(y),
                int(graph.right()),
                int(y),
            )

        values = list(self.values)
        scale_max = self.maximum or max(1.0, max(values) * 1.15)

        line_path = QPainterPath()
        fill_path = QPainterPath()
        for index, value in enumerate(values):
            x = graph.left() + (
                graph.width() * index / max(1, len(values) - 1)
            )
            y = graph.bottom() - (
                min(value, scale_max) / scale_max * graph.height()
            )
            if index == 0:
                line_path.moveTo(x, y)
                fill_path.moveTo(x, graph.bottom())
                fill_path.lineTo(x, y)
            else:
                line_path.lineTo(x, y)
                fill_path.lineTo(x, y)

        fill_path.lineTo(graph.right(), graph.bottom())
        fill_path.closeSubpath()

        painter.fillPath(
            fill_path,
            QBrush(QColor(117, 38, 145, 78)),
        )
        painter.setPen(QPen(QColor("#c54cff"), 2))
        painter.drawPath(line_path)

        painter.setPen(QPen(QColor("#3d2b47")))
        painter.drawRoundedRect(
            bounds.adjusted(1, 1, -1, -1),
            7,
            7,
        )


class LiveTelemetryPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("telemetryPanel")
        self.setVisible(False)

        self.stage_name = "idle"
        self.verification_pulse = 0
        self.verification_direction = 1

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.sample)

        self.previous_network = None
        self.previous_network_by_adapter = {}
        self.previous_time = None
        self.active_adapter = ""
        self.network_available = psutil is not None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 9)
        layout.setSpacing(6)

        heading_row = QHBoxLayout()
        self.heading = QLabel("LIVE PROCESS")
        self.heading.setObjectName("telemetryHeading")
        heading_row.addWidget(self.heading)

        self.current_job = QLabel("No active movie")
        self.current_job.setObjectName("telemetryJob")
        heading_row.addWidget(self.current_job, 1)

        self.stage_label = QLabel("IDLE")
        self.stage_label.setObjectName("telemetryStage")
        heading_row.addWidget(self.stage_label)
        layout.addLayout(heading_row)

        self.active_graph = SparklineWidget(
            "WAITING",
            "%",
            maximum=100,
        )
        self.active_graph.setMinimumHeight(92)
        self.active_graph.setMaximumHeight(92)
        layout.addWidget(self.active_graph)

        self.secondary_status = QLabel("")
        self.secondary_status.setObjectName("telemetrySecondary")
        self.secondary_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.secondary_status)

    def set_current_job(
        self,
        movie_title: str,
        remaining: int,
    ):
        self.current_job.setText(
            f"{movie_title}  â€¢  {remaining} remaining"
        )

    def begin_stage(self, stage: str):
        self.stage_name = stage
        labels = {
            "download": "VAULTONE â†’ PC",
            "encoding": "NVENC ENCODING",
            "upload": "PC â†’ VAULTONE",
            "verifying": "VERIFYING",
            "complete": "COMPLETE",
        }
        self.stage_label.setText(
            labels.get(stage, stage.upper())
        )

        if stage == "download":
            self.active_graph.set_metric(
                "DOWNLOAD TO PC",
                "MB/s",
                None,
            )
            self.secondary_status.setText(
                "Preparing to read the original movie from VaultOne"
            )
            self.reset_network_baseline()

        elif stage == "encoding":
            self.active_graph.set_metric(
                "VIDEO ENCODE",
                "%",
                100,
            )
            self.secondary_status.setText(
                "Dedicated NVIDIA Video Encode engine"
            )

        elif stage == "upload":
            self.active_graph.set_metric(
                "UPLOAD FROM PC",
                "MB/s",
                None,
            )
            self.secondary_status.setText(
                "Preparing to write the optimized movie back to VaultOne"
            )
            self.reset_network_baseline()

        elif stage == "verifying":
            self.active_graph.set_metric(
                "VERIFICATION",
                "%",
                100,
            )
            self.secondary_status.setText(
                "Checking the copied file before replacement"
            )
            self.verification_pulse = 12
            self.verification_direction = 1

        elif stage == "complete":
            self.active_graph.set_metric(
                "COMPLETE",
                "%",
                100,
            )
            self.active_graph.set_value(100)
            self.secondary_status.setText(
                "Movie processing completed successfully"
            )

        if stage in {
            "download",
            "encoding",
            "upload",
            "verifying",
        }:
            self.setVisible(True)
            if not self.timer.isActive():
                self.timer.start()
            self.sample()
        elif stage == "complete":
            self.setVisible(True)
            self.timer.stop()
            QTimer.singleShot(2500, self.stop_and_hide)

    def reset_network_baseline(self):
        self.previous_time = time.monotonic()
        self.active_adapter = ""

        if psutil is None:
            self.network_available = False
            self.previous_network = None
            self.previous_network_by_adapter = {}
            self.secondary_status.setText(
                "Network telemetry unavailable â€” install psutil"
            )
            return

        self.network_available = True
        self.previous_network = psutil.net_io_counters()
        self.previous_network_by_adapter = (
            psutil.net_io_counters(pernic=True)
        )

    def nvidia_metrics(self) -> tuple[float, float, float]:
        """
        Return dedicated Video Encode %, general GPU %, and temperature.

        Task Manager's Video Encode graph reports a dedicated engine, so
        utilization.encoder is the primary reading during NVENC work.
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.encoder,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                values = [
                    float(part.strip())
                    for part in result.stdout.strip().splitlines()[0].split(",")[:3]
                ]
                if len(values) == 3:
                    return values[0], values[1], values[2]
        except Exception:
            pass

        # Fallback to nvidia-smi dmon. Its "enc" column is the dedicated
        # encoder engine percentage on supported NVIDIA drivers.
        try:
            result = subprocess.run(
                ["nvidia-smi", "dmon", "-s", "u", "-c", "1"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=4,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
                check=False,
            )
            data_lines = [
                line
                for line in result.stdout.splitlines()
                if line.strip()
                and not line.lstrip().startswith("#")
            ]
            if data_lines:
                columns = data_lines[-1].split()
                # gpu, sm, mem, enc, dec, jpg, ofa
                if len(columns) >= 5:
                    general = float(columns[1])
                    encoder = float(columns[3])
                    return encoder, general, 0.0
        except Exception:
            pass

        return 0.0, 0.0, 0.0

    def network_metrics(
        self,
    ) -> tuple[float, float, str]:
        if psutil is None:
            self.network_available = False
            return 0.0, 0.0, ""

        current_time = time.monotonic()
        current_by_adapter = psutil.net_io_counters(
            pernic=True
        )

        if (
            not self.previous_network_by_adapter
            or self.previous_time is None
        ):
            self.previous_network_by_adapter = (
                current_by_adapter
            )
            self.previous_time = current_time
            return 0.0, 0.0, self.active_adapter

        elapsed = max(
            0.1,
            current_time - self.previous_time,
        )

        ignored_tokens = (
            "loopback",
            "isatap",
            "teredo",
            "bluetooth",
            "virtualbox",
            "vmware",
            "hyper-v",
            "vethernet",
        )

        candidates = []
        for name, current in current_by_adapter.items():
            previous = self.previous_network_by_adapter.get(
                name
            )
            if previous is None:
                continue

            lowered = name.casefold()
            if any(
                token in lowered
                for token in ignored_tokens
            ):
                continue

            received = max(
                0,
                current.bytes_recv - previous.bytes_recv,
            )
            sent = max(
                0,
                current.bytes_sent - previous.bytes_sent,
            )
            total = received + sent
            candidates.append(
                (total, received, sent, name)
            )

        self.previous_network_by_adapter = (
            current_by_adapter
        )
        self.previous_time = current_time

        if not candidates:
            self.network_available = True
            return 0.0, 0.0, self.active_adapter

        _total, received, sent, adapter = max(
            candidates,
            key=lambda item: item[0],
        )
        self.active_adapter = adapter
        self.network_available = True

        return (
            received / elapsed / (1024 * 1024),
            sent / elapsed / (1024 * 1024),
            adapter,
        )

    def sample(self):
        download, upload, adapter = self.network_metrics()

        if self.stage_name == "download":
            self.active_graph.set_value(download)
            if not self.network_available:
                self.secondary_status.setText(
                    "Network telemetry unavailable â€” psutil is missing"
                )
            elif adapter:
                self.secondary_status.setText(
                    f"Reading from VaultOne via {adapter}"
                )
            else:
                self.secondary_status.setText(
                    "Waiting for traffic from VaultOne"
                )

        elif self.stage_name == "upload":
            self.active_graph.set_value(upload)
            if not self.network_available:
                self.secondary_status.setText(
                    "Network telemetry unavailable â€” psutil is missing"
                )
            elif adapter:
                self.secondary_status.setText(
                    f"Writing to VaultOne via {adapter}"
                )
            else:
                self.secondary_status.setText(
                    "Waiting for traffic to VaultOne"
                )

        elif self.stage_name == "encoding":
            encoder, general, temperature = self.nvidia_metrics()
            self.active_graph.set_value(encoder)
            temperature_text = (
                f" â€¢ {temperature:.0f}Â°C"
                if temperature
                else ""
            )
            self.secondary_status.setText(
                f"Video Encode {encoder:.0f}%"
                f" â€¢ GPU Core {general:.0f}%"
                f"{temperature_text}"
            )

        elif self.stage_name == "verifying":
            self.verification_pulse += (
                14 * self.verification_direction
            )
            if self.verification_pulse >= 92:
                self.verification_pulse = 92
                self.verification_direction = -1
            elif self.verification_pulse <= 12:
                self.verification_pulse = 12
                self.verification_direction = 1
            self.active_graph.set_value(
                self.verification_pulse
            )

    def stop_and_hide(self):
        self.timer.stop()
        self.setVisible(False)
        self.stage_name = "idle"
        self.stage_label.setText("IDLE")
        self.current_job.setText("No active movie")
        self.secondary_status.setText("")
        self.active_graph.set_metric(
            "WAITING",
            "%",
            100,
        )
        self.active_graph.clear_values()



class TrafficLightStatus(QFrame):
    def __init__(
        self,
        name: str,
        parent=None,
    ):
        super().__init__(parent)
        self.name = name
        self.state = "unknown"
        self.setObjectName("trafficStatus")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 4, 7, 4)
        layout.setSpacing(5)

        self.light = QLabel("â—")
        self.light.setObjectName("trafficLight")
        self.label = QLabel(name)
        self.label.setObjectName("trafficLabel")

        layout.addWidget(self.light)
        layout.addWidget(self.label)
        self.set_status(
            "unknown",
            f"{name}: Not checked yet",
        )

    def set_status(
        self,
        state: str,
        detail: str,
    ):
        self.state = state
        colors = {
            "good": "#62df78",
            "warning": "#ffbd59",
            "bad": "#ff5f72",
            "unknown": "#77707d",
        }
        color = colors.get(state, colors["unknown"])
        self.light.setStyleSheet(
            f"color:{color};font-size:16px;"
        )
        self.setToolTip(detail)
        self.light.setToolTip(detail)
        self.label.setToolTip(detail)

class OperationsMetric(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "â€”",
        detail: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("operationsMetric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(1)

        heading = QLabel(title)
        heading.setObjectName("operationsMetricTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("operationsMetricValue")
        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("operationsMetricDetail")
        self.detail_label.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def update_value(
        self,
        value: str,
        detail: str = "",
        state: str = "normal",
    ):
        self.value_label.setText(value)
        self.detail_label.setText(detail)
        colors = {
            "good": "#70df7b",
            "warning": "#ffbd59",
            "bad": "#ff6879",
            "normal": "#d35cff",
            "blue": "#5db7ff",
        }
        self.value_label.setStyleSheet(
            f"color:{colors.get(state, colors['normal'])};"
        )


class OperationsCenterPanel(QFrame):
    scan_requested = Signal()
    start_requested = Signal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("operationsCenter")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        heading_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("OPERATIONS CENTER")
        title.setObjectName("operationsTitle")
        subtitle = QLabel(
            "Compact health lights â€” hover any light for details"
        )
        subtitle.setObjectName("operationsSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading_row.addLayout(title_box)
        heading_row.addStretch()

        self.last_refresh = QLabel("Not checked yet")
        self.last_refresh.setObjectName("operationsRefresh")
        heading_row.addWidget(self.last_refresh)

        refresh_button = QPushButton("â†» REFRESH")
        refresh_button.clicked.connect(self.refresh_services)
        heading_row.addWidget(refresh_button)
        outer.addLayout(heading_row)

        health_row = QHBoxLayout()
        health_row.setSpacing(6)

        self.nas_status = TrafficLightStatus("NAS")
        self.jellyfin_status = TrafficLightStatus("Jellyfin")
        self.gpu_status = TrafficLightStatus("GPU")
        self.handbrake_status = TrafficLightStatus("HandBrake")

        health_row.addWidget(self.nas_status)
        health_row.addWidget(self.jellyfin_status)
        health_row.addWidget(self.gpu_status)
        health_row.addWidget(self.handbrake_status)
        health_row.addStretch()
        outer.addLayout(health_row)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)

        self.movies_metric = OperationsMetric(
            "MOVIES LOADED",
            "0",
            "Run a scan to populate the library",
        )
        self.queue_metric = OperationsMetric(
            "QUEUE",
            "0",
            "No movies waiting",
        )
        self.saving_metric = OperationsMetric(
            "POTENTIAL SAVING",
            "0 B",
            "Based on queued targets",
        )
        self.free_metric = OperationsMetric(
            "FREE SPACE",
            "â€”",
            "Configured movie library",
        )

        for card in (
            self.movies_metric,
            self.queue_metric,
            self.saving_metric,
            self.free_metric,
        ):
            metrics.addWidget(card, 1)
        outer.addLayout(metrics)

        action_row = QHBoxLayout()
        self.current_status = QLabel("STATUS: READY")
        self.current_status.setObjectName("operationsCurrent")
        action_row.addWidget(self.current_status, 1)

        scan_button = QPushButton("â˜   SCAN")
        scan_button.setObjectName("primaryButton")
        scan_button.clicked.connect(
            self.scan_requested.emit
        )
        action_row.addWidget(scan_button)

        start_button = QPushButton("â–¶  START PROCESS")
        start_button.setObjectName("startButton")
        start_button.clicked.connect(
            self.start_requested.emit
        )
        action_row.addWidget(start_button)
        outer.addLayout(action_row)

    def update_library(
        self,
        movies: list,
        queued: list,
    ):
        self.movies_metric.update_value(
            str(len(movies)),
            "Movies above the configured size limit",
            "blue",
        )
        self.queue_metric.update_value(
            str(len(queued)),
            (
                "Ready to process"
                if queued
                else "No movies waiting"
            ),
            "good" if queued else "normal",
        )
        saving = sum(movie.saving for movie in queued)
        self.saving_metric.update_value(
            human_size(saving),
            "Based on queued target sizes",
            "good" if saving else "normal",
        )

    def set_process_status(self, text: str):
        self.current_status.setText(
            f"STATUS: {text.upper()}"
        )

    def refresh_services(self):
        root = Path(
            str(self.config.get("movie_root", "")).strip()
        )
        nas_ok = root.exists()

        if nas_ok:
            try:
                free = shutil.disk_usage(root).free
                free_text = human_size(free)
                nas_state = (
                    "good"
                    if free > 100 * 1024**3
                    else "warning"
                )
                self.nas_status.set_status(
                    nas_state,
                    f"NAS: Connected\n"
                    f"Library: {root}\n"
                    f"Free space: {free_text}",
                )
                self.free_metric.update_value(
                    free_text,
                    "Available on the library volume",
                    nas_state,
                )
            except OSError as exc:
                self.nas_status.set_status(
                    "warning",
                    f"NAS: Connected, but free space could not "
                    f"be read.\n{exc}",
                )
                self.free_metric.update_value(
                    "UNKNOWN",
                    str(exc),
                    "warning",
                )
        else:
            self.nas_status.set_status(
                "bad",
                f"NAS: Library unavailable\n"
                f"Configured path: {root or 'Not configured'}",
            )
            self.free_metric.update_value(
                "â€”",
                "NAS library is unavailable",
                "bad",
            )

        jellyfin_ok, jellyfin_detail = test_jellyfin(
            self.config
        )
        self.jellyfin_status.set_status(
            "good" if jellyfin_ok else "bad",
            (
                "Jellyfin: Connected\n"
                if jellyfin_ok
                else "Jellyfin: Connection failed\n"
            )
            + jellyfin_detail,
        )

        handbrake_path = shutil.which(
            self.config.get(
                "handbrake",
                "HandBrakeCLI",
            )
        )
        self.handbrake_status.set_status(
            "good" if handbrake_path else "bad",
            (
                f"HandBrake: Ready\n{handbrake_path}"
                if handbrake_path
                else "HandBrake: HandBrakeCLI was not found"
            ),
        )

        gpu_ok = False
        gpu_detail = "nvidia-smi was not found"
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=4,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_ok = True
                gpu_detail = (
                    result.stdout.strip().splitlines()[0]
                )
        except Exception as exc:
            gpu_detail = str(exc)

        self.gpu_status.set_status(
            "good" if gpu_ok else "bad",
            (
                f"GPU: NVENC ready\n{gpu_detail}"
                if gpu_ok
                else f"GPU: NVIDIA telemetry unavailable\n"
                f"{gpu_detail}"
            ),
        )

        self.last_refresh.setText(
            "Checked " + time.strftime("%H:%M:%S")
        )



def find_handbrake_cli(configured: str = "") -> tuple[str, str]:
    """Return (path/command, version). Empty values mean HandBrakeCLI was not found."""
    candidates = []
    if configured:
        candidates.append(configured)
    resolved = shutil.which("HandBrakeCLI") or shutil.which("HandBrakeCLI.exe")
    if resolved:
        candidates.append(resolved)
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.extend([
                    str(Path(base) / "HandBrake" / "HandBrakeCLI.exe"),
                    str(Path(base) / "Programs" / "HandBrake" / "HandBrakeCLI.exe"),
                ])
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        path = shutil.which(candidate) or candidate
        if not Path(path).exists() and not shutil.which(path):
            continue
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=8, **hidden_process_kwargs())
            output = (result.stdout or result.stderr or "").strip().splitlines()
            if result.returncode == 0 and output:
                return str(path), output[0]
        except Exception:
            continue
    return "", ""


def detected_network_locations() -> list[str]:
    locations = []
    if os.name == "nt":
        try:
            result = subprocess.run(["net", "use"], capture_output=True, text=True, timeout=6, **hidden_process_kwargs())
            for line in result.stdout.splitlines():
                m = re.search(r'(\\\\[^\\\s]+\\[^\s]+)', line)
                if m:
                    locations.append(m.group(1))
        except Exception:
            pass
    return list(dict.fromkeys(locations))


class PlatformSetupWizard(QWizard):
    HANDBRAKE_URL = "https://handbrake.fr/downloads.php"

    def __init__(self, config: dict, parent=None, first_run: bool = False):
        super().__init__(parent)
        self.config = config.copy()
        self.first_run = first_run
        self.setWindowTitle("Evil's Media Encoding Platform â€” Platform Builder")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(860, 650)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.FinishButton, "BUILD MY PLATFORM")
        self._build_pages()
        self.currentIdChanged.connect(self._page_changed)

    def heading(self, title: str, text: str) -> tuple[QLabel, QLabel]:
        h = QLabel(title); h.setStyleSheet("font-size:26px;font-weight:900;color:#d35cff;")
        b = QLabel(text); b.setWordWrap(True); b.setStyleSheet("font-size:14px;color:#d6ceda;")
        return h, b

    def _build_pages(self):
        welcome = QWizardPage(); welcome.setTitle("")
        layout = QVBoxLayout(welcome)
        h,b=self.heading("EVIL'S MEDIA ENCODING PLATFORM", "Professional media encoding and workflow automation. Let's build the platform around the way your media actually lives.")
        layout.addStretch(); layout.addWidget(h); layout.addWidget(b)
        badge=QLabel("POWERED BY EMO  â€¢  PLATFORM 5.0 PREVIEW"); badge.setStyleSheet("font-weight:800;color:#8d8292;margin-top:16px;"); layout.addWidget(badge)
        layout.addStretch(); self.addPage(welcome)

        hb = QWizardPage(); hb.setTitle("HandBrake")
        l=QVBoxLayout(hb); h,b=self.heading("ENCODER CHECK", "EMP uses HandBrakeCLI as its encoding engine. We'll find it automatically and verify that it runs."); l.addWidget(h); l.addWidget(b)
        self.hb_status=QLabel("Checkingâ€¦"); self.hb_status.setWordWrap(True); self.hb_status.setStyleSheet("font-size:17px;font-weight:800;padding:18px;background:#111018;border:1px solid #35243e;border-radius:8px;"); l.addWidget(self.hb_status)
        row=QHBoxLayout(); self.hb_browse=QPushButton("BROWSE FOR HANDBRAKECLI"); self.hb_browse.clicked.connect(self._browse_handbrake); row.addWidget(self.hb_browse)
        self.hb_download=QPushButton("OPEN OFFICIAL HANDBRAKE DOWNLOAD"); self.hb_download.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.HANDBRAKE_URL))); row.addWidget(self.hb_download); l.addLayout(row)
        self.hb_path=QLineEdit(self.config.get("handbrake","HandBrakeCLI")); self.hb_path.setPlaceholderText("HandBrakeCLI.exe path"); l.addWidget(self.hb_path); l.addStretch(); self.addPage(hb)

        flow=QWizardPage(); flow.setTitle("Workflow"); l=QVBoxLayout(flow); h,b=self.heading("HOW SHOULD EMP WORK?", "Choose the picture that best matches your setup. You can run this Platform Builder again from Settings at any time."); l.addWidget(h); l.addWidget(b)
        self.flow_group=QButtonGroup(self); self.flow_buttons={}
        choices=[
            ("nas_pc_nas","NAS + THIS PC  â€”  Recommended","Media stays on your NAS. EMP copies one job to this PC, encodes locally, verifies it, and sends it back.",True),
            ("local","JUST THIS PC","Media and encoding both live on this computer.",True),
            ("remote_server","DEDICATED ENCODING SERVER","Another computer/server performs the encode. Configuration is saved in this preview; remote-worker execution is the next platform module.",False),
            ("nas_native","NAS DOES EVERYTHING","Run encoding on the NAS itself. Configuration is saved in this preview; NAS-native execution requires the remote-worker module.",False),
        ]
        current=self.config.get("workflow_mode","nas_pc_nas")
        for key,title,desc,ready in choices:
            rb=QRadioButton(f"{title}\n{desc}" + ("" if ready else "\n[PLATFORM MODE â€” worker backend pending]")); rb.setStyleSheet("QRadioButton{padding:12px;font-size:14px;} QRadioButton::indicator{width:18px;height:18px;}"); self.flow_group.addButton(rb); self.flow_buttons[key]=rb; l.addWidget(rb)
            if key==current: rb.setChecked(True)
        if not any(x.isChecked() for x in self.flow_buttons.values()): self.flow_buttons["nas_pc_nas"].setChecked(True)
        l.addStretch(); self.addPage(flow)

        paths=QWizardPage(); paths.setTitle("Locations"); l=QVBoxLayout(paths); h,b=self.heading("YOUR MEDIA LOCATIONS", "Tell EMP where media starts, where finished media belongs, and where this PC may work temporarily. Use Test to check access."); l.addWidget(h); l.addWidget(b)
        form=QFormLayout()
        self.source_edit=QLineEdit(self.config.get("movie_root","")); form.addRow("Where are your movies?", self._path_row(self.source_edit,"source"))
        self.output_edit=QLineEdit(self.config.get("output_root",self.config.get("movie_root",""))); form.addRow("Where should finished movies go?", self._path_row(self.output_edit,"output"))
        self.work_edit=QLineEdit(self.config.get("local_work",r"C:\Evil Media Optimizer Work")); form.addRow("Where should EMP work?", self._path_row(self.work_edit,"work"))
        l.addLayout(form)
        self.path_status=QLabel("Tip: an SSD/NVMe is recommended for EMP's work folder."); self.path_status.setWordWrap(True); l.addWidget(self.path_status)
        find_net=QPushButton("FIND NETWORK LOCATIONS"); find_net.clicked.connect(self._show_network_locations); l.addWidget(find_net); l.addStretch(); self.addPage(paths)

        media=QWizardPage(); media.setTitle("Media Server"); l=QVBoxLayout(media); h,b=self.heading("MEDIA SERVER", "If you use a media server, EMP can keep its connection details with the platform configuration. Jellyfin integration already exists; Plex and Emby are staged for later modules."); l.addWidget(h); l.addWidget(b)
        self.server_group=QButtonGroup(self); self.server_buttons={}
        for name in ("Jellyfin","Plex","Emby","None"):
            rb=QRadioButton(name); self.server_group.addButton(rb); self.server_buttons[name]=rb; l.addWidget(rb)
        self.server_buttons.get(self.config.get("media_server_type","Jellyfin"), self.server_buttons["None"]).setChecked(True)
        self.jf_url=QLineEdit(self.config.get("jellyfin_url","")); self.jf_url.setPlaceholderText("Jellyfin URL - e.g. http://server:8096"); l.addWidget(self.jf_url)
        jf_form=QFormLayout()
        self.jf_username=QLineEdit(self.config.get("jellyfin_username", "")); self.jf_username.setPlaceholderText("Jellyfin username"); jf_form.addRow("Username:", self.jf_username)
        self.jf_password=QLineEdit(); self.jf_password.setEchoMode(QLineEdit.EchoMode.Password); self.jf_password.setPlaceholderText("Used once - EMP does not save this password"); jf_form.addRow("Password:", self.jf_password)
        self.jf_connect=QPushButton("CONNECT TO JELLYFIN"); self.jf_connect.clicked.connect(self._connect_jellyfin); jf_form.addRow("", self.jf_connect)
        self.jf_connect_status=QLabel("EMP can sign in once with an administrator account and retrieve/create its own persistent Jellyfin API key. You can still use an existing API key later in Settings."); self.jf_connect_status.setWordWrap(True); jf_form.addRow("Status:", self.jf_connect_status)
        l.addLayout(jf_form)
        l.addStretch(); self.addPage(media)

        review=QWizardPage(); review.setTitle("Build"); l=QVBoxLayout(review); h,b=self.heading("BUILDING YOUR PLATFORM", "EMP will save this as your active platform profile. You can change any of it later from Settings â†’ Platform Setup."); l.addWidget(h); l.addWidget(b)
        self.review=QLabel(); self.review.setWordWrap(True); self.review.setTextFormat(Qt.TextFormat.RichText); self.review.setStyleSheet("font-size:14px;padding:18px;background:#111018;border:1px solid #35243e;border-radius:8px;"); l.addWidget(self.review); l.addStretch(); self.addPage(review)

    def _path_row(self, edit, role):
        w=QWidget(); row=QHBoxLayout(w); row.setContentsMargins(0,0,0,0); row.addWidget(edit,1)
        browse=QPushButton("Browse"); browse.clicked.connect(lambda _=False,e=edit: self._browse_folder(e)); row.addWidget(browse)
        test=QPushButton("Test"); test.clicked.connect(lambda _=False,e=edit,r=role: self._test_path(e,r)); row.addWidget(test)
        return w

    def _browse_folder(self, edit):
        folder=QFileDialog.getExistingDirectory(self,"Choose location",edit.text() or str(Path.home()))
        if folder: edit.setText(folder)

    def _browse_handbrake(self):
        path,_=QFileDialog.getOpenFileName(self,"Find HandBrakeCLI",str(Path.home()),"HandBrakeCLI (HandBrakeCLI.exe HandBrakeCLI);;All files (*)")
        if path: self.hb_path.setText(path); self._check_handbrake(path)

    def _check_handbrake(self, configured=None):
        path,version=find_handbrake_cli(configured or self.hb_path.text().strip())
        if path:
            self.hb_path.setText(path); self.hb_status.setText(f"âœ“ HandBrakeCLI detected\n{version}\n{path}"); self.hb_status.setStyleSheet("font-size:17px;font-weight:800;padding:18px;background:#0a170d;border:1px solid #2f7d3f;border-radius:8px;color:#70df7b;")
        else:
            self.hb_status.setText("âœ• HandBrakeCLI was not found. Install HandBrake from the official site, then return here and click Browse or Next to re-check."); self.hb_status.setStyleSheet("font-size:17px;font-weight:800;padding:18px;background:#190b0d;border:1px solid #8d3340;border-radius:8px;color:#ff6879;")
        return bool(path)

    def _test_path(self, edit, role):
        raw=edit.text().strip()
        if not raw:
            self.path_status.setText("âœ• Choose a location first."); return
        p=Path(raw)
        try:
            if role=="work": p.mkdir(parents=True,exist_ok=True)
            exists=p.exists(); writable=False
            if exists and p.is_dir():
                probe=p/".emp_write_test.tmp"
                try: probe.write_text("EMP",encoding="utf-8"); probe.unlink(); writable=True
                except Exception: writable=False
            free=""
            try: free=f" â€¢ {shutil.disk_usage(p).free/(1024**3):.1f} GiB free"
            except Exception: pass
            self.path_status.setText(("âœ“" if exists else "âœ•")+f" {raw} â€¢ " + ("write access" if writable else "read-only/unavailable")+free)
        except Exception as exc:
            self.path_status.setText(f"âœ• {exc}")

    def _show_network_locations(self):
        found=detected_network_locations()
        text="\n".join(found) if found else "No mapped UNC shares were reported by Windows. You can still type a path such as \\\\NAS\\Movies or use Browse if the share is mounted."
        QMessageBox.information(self,"Network locations",text)

    def _selected_flow(self):
        for key,button in self.flow_buttons.items():
            if button.isChecked(): return key
        return "nas_pc_nas"

    def _selected_server(self):
        for name,button in self.server_buttons.items():
            if button.isChecked(): return name
        return "None"

    def _connect_jellyfin(self):
        self.jf_connect_status.setText("Connecting to Jellyfin...")
        QApplication.processEvents()
        ok, detail, token, device_id = authenticate_jellyfin(
            self.jf_url.text(),
            self.jf_username.text(),
            self.jf_password.text(),
            device_id=self.config.get("jellyfin_device_id", ""),
        )
        self.jf_connect_status.setText(("âœ“ " if ok else "âœ• ") + detail)
        self.jf_connect_status.setStyleSheet(
            "color:#78e286;font-weight:700;" if ok else "color:#ff6879;font-weight:700;"
        )
        if ok:
            self.config["jellyfin_api_key"] = token
            self.config["jellyfin_device_id"] = device_id
            self.config["jellyfin_username"] = self.jf_username.text().strip()
            self.jf_password.clear()

    def _page_changed(self, page_id):
        if page_id==1: self._check_handbrake()
        if page_id==5:
            flow=self._selected_flow(); ready=flow in {"nas_pc_nas","local"}
            self.review.setText(
                f"<b>Workflow:</b> {flow.replace('_',' ').title()} {'âœ“ ready now' if ready else 'â€¢ worker backend pending'}<br><br>"
                f"<b>HandBrake:</b> {self.hb_path.text().strip() or 'Not found'}<br>"
                f"<b>Media source:</b> {self.source_edit.text().strip() or 'Not set'}<br>"
                f"<b>Finished media:</b> {self.output_edit.text().strip() or 'Not set'}<br>"
                f"<b>EMP work area:</b> {self.work_edit.text().strip() or 'Not set'}<br>"
                f"<b>Media server:</b> {self._selected_server()}"
            )

    def validateCurrentPage(self):
        if self.currentId()==1 and not self._check_handbrake():
            answer=QMessageBox.question(self,"HandBrake required","HandBrakeCLI is not available yet. Open the official HandBrake download page now?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            if answer==QMessageBox.StandardButton.Yes: QDesktopServices.openUrl(QUrl(self.HANDBRAKE_URL))
            return False
        if self.currentId()==3:
            if not self.source_edit.text().strip() or not self.work_edit.text().strip():
                QMessageBox.warning(self,"Locations needed","Choose at least your media source and EMP work location."); return False
        return super().validateCurrentPage()

    def values(self):
        return {
            **self.config,
            "setup_complete": True,
            "workflow_mode": self._selected_flow(),
            "handbrake": self.hb_path.text().strip() or "HandBrakeCLI",
            "movie_root": self.source_edit.text().strip(),
            "output_root": self.output_edit.text().strip() or self.source_edit.text().strip(),
            "local_work": self.work_edit.text().strip(),
            "media_server_type": self._selected_server(),
            "jellyfin_url": self.jf_url.text().strip().rstrip("/"),
            "jellyfin_username": self.jf_username.text().strip(),
            "jellyfin_api_key": self.config.get("jellyfin_api_key", ""),
            "jellyfin_device_id": self.config.get("jellyfin_device_id", ""),
        }


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} â€” Settings")
        self.resize(760, 560)
        self.config = config.copy()
        outer = QVBoxLayout(self)
        tabs = QTabWidget()

        general = QWidget()
        general_form = QFormLayout(general)
        self.root = QLineEdit(self.config["movie_root"])
        root_row = QHBoxLayout(); root_row.addWidget(self.root)
        browse_root = QPushButton("Browse"); browse_root.clicked.connect(self.browse_root); root_row.addWidget(browse_root)
        root_widget = QWidget(); root_widget.setLayout(root_row)
        general_form.addRow("Movie library:", root_widget)
        self.work = QLineEdit(self.config["local_work"])
        work_row = QHBoxLayout(); work_row.addWidget(self.work)
        browse_work = QPushButton("Browse"); browse_work.clicked.connect(self.browse_work); work_row.addWidget(browse_work)
        work_widget = QWidget(); work_widget.setLayout(work_row)
        general_form.addRow("Local work folder:", work_widget)
        self.minimum = QSpinBox(); self.minimum.setRange(1, 100); self.minimum.setValue(int(self.config["minimum_size_gib"]))
        general_form.addRow("Scan movies larger than (GiB):", self.minimum)
        self.default_target = QSpinBox(); self.default_target.setRange(1, 100); self.default_target.setValue(int(self.config["default_target_gib"]))
        general_form.addRow("Default target (GiB):", self.default_target)
        self.platform_setup_button = QPushButton("RUN PLATFORM SETUP WIZARDâ€¦")
        self.platform_setup_button.setObjectName("primaryButton")
        self.platform_setup_button.clicked.connect(self.run_platform_setup)
        general_form.addRow("Platform setup:", self.platform_setup_button)
        tabs.addTab(general, "General")

        encoding = QWidget()
        enc_form = QFormLayout(encoding)
        self.audio = QSpinBox(); self.audio.setRange(96, 1024); self.audio.setValue(int(self.config["audio_kbps"]))
        enc_form.addRow("Audio bitrate (kbps):", self.audio)
        self.handbrake = QLineEdit(self.config["handbrake"]); enc_form.addRow("HandBrakeCLI command:", self.handbrake)
        self.ffprobe = QLineEdit(self.config["ffprobe"]); enc_form.addRow("ffprobe command:", self.ffprobe)
        self.encoder = QComboBox(); self.encoder.addItems(["nvenc_h265", "nvenc_h264"]); self.encoder.setCurrentText(self.config["encoder"])
        enc_form.addRow("NVIDIA encoder:", self.encoder)
        self.preset = QComboBox(); self.preset.addItems(["slow", "medium", "fast", "faster"]); self.preset.setCurrentText(self.config.get("encoder_preset", "medium"))
        enc_form.addRow("Encoder preset:", self.preset)
        self.analyze_media = QCheckBox(
            "Analyze codec, runtime, HDR, audio and subtitles after scans"
        )
        self.analyze_media.setChecked(
            bool(self.config.get("analyze_media_on_scan", True))
        )
        enc_form.addRow(self.analyze_media)

        analysis_note = QLabel(
            "Analysis never changes target sizes or queues movies. "
            "Your size choices remain completely manual."
        )
        analysis_note.setWordWrap(True)
        enc_form.addRow(analysis_note)

        tabs.addTab(encoding, "Encoding")

        queue_settings = QWidget()
        queue_form = QFormLayout(queue_settings)

        self.queue_finish_action = QComboBox()
        self.queue_finish_action.addItems(
            [
                "Do nothing",
                "Shut down",
                "Sleep",
                "Hibernate",
                "Restart",
            ]
        )
        self.queue_finish_action.setCurrentText(
            self.config.get(
                "queue_finish_action",
                "Do nothing",
            )
        )
        queue_form.addRow(
            "When the full process finishes:",
            self.queue_finish_action,
        )

        finish_note = QLabel(
            "The safety default is Do nothing. "
            "No automatic power action is enabled on first install."
        )
        finish_note.setWordWrap(True)
        queue_form.addRow(finish_note)

        self.show_live_telemetry = QCheckBox(
            "Show live GPU and NAS network graphs while processing"
        )
        self.show_live_telemetry.setChecked(
            bool(
                self.config.get(
                    "show_live_telemetry",
                    True,
                )
            )
        )
        queue_form.addRow(self.show_live_telemetry)

        tabs.addTab(queue_settings, "Queue")

        integration = QWidget()
        integration_form = QFormLayout(integration)

        self.jellyfin_url = QLineEdit(
            self.config.get(
                "jellyfin_url",
                "http://192.168.68.79:28096",
            )
        )
        self.jellyfin_url.setPlaceholderText(
            "http://192.168.68.79:28096"
        )
        integration_form.addRow("Jellyfin URL:", self.jellyfin_url)

        self.jellyfin_username = QLineEdit(self.config.get("jellyfin_username", ""))
        self.jellyfin_username.setPlaceholderText("Jellyfin username")
        integration_form.addRow("Jellyfin username:", self.jellyfin_username)

        self.jellyfin_password = QLineEdit()
        self.jellyfin_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.jellyfin_password.setPlaceholderText("Used only while connecting - never saved")
        integration_form.addRow("Jellyfin password:", self.jellyfin_password)

        self.connect_jellyfin_button = QPushButton("CONNECT TO JELLYFIN")
        self.connect_jellyfin_button.clicked.connect(self.connect_jellyfin)
        integration_form.addRow("", self.connect_jellyfin_button)

        key_row = QHBoxLayout()
        self.jellyfin_api_key = QLineEdit(
            self.config.get("jellyfin_api_key", "")
        )
        self.jellyfin_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.jellyfin_api_key.setPlaceholderText(
            "Automatically filled by Connect to Jellyfin, or paste an existing API key"
        )
        key_row.addWidget(self.jellyfin_api_key, 1)

        self.show_jellyfin_key = QCheckBox("Show")
        self.show_jellyfin_key.toggled.connect(
            lambda checked: self.jellyfin_api_key.setEchoMode(
                QLineEdit.EchoMode.Normal
                if checked
                else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self.show_jellyfin_key)

        key_widget = QWidget()
        key_widget.setLayout(key_row)
        integration_form.addRow("Jellyfin API key:", key_widget)

        self.test_jellyfin_button = QPushButton(
            "TEST JELLYFIN CONNECTION"
        )
        self.test_jellyfin_button.clicked.connect(
            self.test_jellyfin_connection
        )
        integration_form.addRow("", self.test_jellyfin_button)

        self.jellyfin_test_result = QLabel(
            "Use Connect to Jellyfin for automatic setup, or enter an existing API key and test it."
        )
        self.jellyfin_test_result.setWordWrap(True)
        integration_form.addRow("Status:", self.jellyfin_test_result)

        note = QLabel(
            "Connect to Jellyfin signs in once and saves only the returned EMP access token. "
            "Your Jellyfin password is never written to config.json. Existing API keys remain supported."
        )
        note.setWordWrap(True)
        integration_form.addRow(note)

        tabs.addTab(integration, "Integrations")

        updates = QWidget()
        updates_layout = QVBoxLayout(updates)

        updates_intro = QLabel(
            "Install future Evil's Media Optimizer update ZIP files "
            "without replacing your settings, poster cache, history or logs."
        )
        updates_intro.setWordWrap(True)
        updates_layout.addWidget(updates_intro)

        version_label = QLabel(f"Installed version: {APP_VERSION}")
        version_label.setStyleSheet(
            "font-size:16px;font-weight:800;color:#d15cff;"
        )
        updates_layout.addWidget(version_label)

        self.github_repo = QLineEdit(self.config.get("github_repo", ""))
        self.github_repo.setPlaceholderText("owner/repository  (example: EvildeadNZ/EMO)")
        updates_layout.addWidget(QLabel("GitHub release repository:"))
        updates_layout.addWidget(self.github_repo)
        github_note = QLabel("EMP checks this repository's latest GitHub Release when the dashboard opens. The release should contain the EMP update ZIP as an asset.")
        github_note.setWordWrap(True); updates_layout.addWidget(github_note)

        self.update_manifest_url = QLineEdit(
            self.config.get("update_manifest_url", "")
        )
        self.update_manifest_url.setPlaceholderText("Legacy/custom manifest URL (optional)")
        updates_layout.addWidget(QLabel("Custom update source:"))
        updates_layout.addWidget(self.update_manifest_url)

        install_zip = QPushButton("INSTALL UPDATE FROM ZIP...")
        install_zip.setObjectName("primaryButton")
        install_zip.clicked.connect(self.install_update_from_zip)
        updates_layout.addWidget(install_zip)

        updates_note = QLabel(
            "The updater creates a backup before copying new program files. "
            "After installation, close and reopen the app."
        )
        updates_note.setWordWrap(True)
        updates_layout.addWidget(updates_note)
        updates_layout.addStretch()
        tabs.addTab(updates, "Updates")

        appearance = QWidget()
        appearance_form = QFormLayout(appearance)

        self.theme = QComboBox()
        self.theme.addItems(list(THEME_PALETTES))
        self.theme.setCurrentText(
            self.config.get("theme", "Skull Purple")
        )
        appearance_form.addRow("Application theme:", self.theme)

        self.banner_theme = QComboBox()
        self.banner_theme.addItems(["Original Purple", "Red Ember"])
        self.banner_theme.setCurrentText(self.config.get("banner_theme", "Original Purple"))
        appearance_form.addRow("Banner style:", self.banner_theme)

        banner_note = QLabel(
            "Choose the artwork shown across the top of EMP. Original Purple keeps the classic skull banner; "
            "Red Ember adds the new red/black skull banner. Your choice is saved, and more banner packs can be added later."
        )
        banner_note.setWordWrap(True)
        appearance_form.addRow("", banner_note)

        scale_row = QHBoxLayout()
        self.ui_scale = QSlider(Qt.Orientation.Horizontal)
        self.ui_scale.setRange(85, 150)
        self.ui_scale.setSingleStep(5)
        self.ui_scale.setPageStep(10)
        self.ui_scale.setTickInterval(5)
        self.ui_scale.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ui_scale.setValue(int(self.config.get("ui_scale_percent", 100)))
        self.ui_scale_value = QLabel(f"{self.ui_scale.value()}%")
        self.ui_scale_value.setMinimumWidth(48)
        self.ui_scale_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ui_scale.valueChanged.connect(lambda value: self.ui_scale_value.setText(f"{value}%"))
        scale_row.addWidget(self.ui_scale, 1)
        scale_row.addWidget(self.ui_scale_value)
        scale_widget = QWidget(); scale_widget.setLayout(scale_row)
        appearance_form.addRow("UI text size:", scale_widget)

        scale_note = QLabel(
            "100% is the normal EMP size. Increase this if labels, buttons, tables or status text are difficult to read. "
            "The setting applies after Save and is remembered for future launches."
        )
        scale_note.setWordWrap(True)
        appearance_form.addRow("", scale_note)

        theme_note = QLabel(
            "The selected theme is applied after you click Save. "
            "It changes the full interface while keeping status colours "
            "consistent and readable."
        )
        theme_note.setWordWrap(True)
        appearance_form.addRow(theme_note)

        theme_list = QLabel(
            "Included themes:\n"
            "Skull Purple â€¢ OLED Black â€¢ Diablo Ember â€¢ Jellyfin Violet â€¢ "
            "Matrix Green â€¢ Cyberpunk Neon â€¢ Blood Moon â€¢ Arctic Blue â€¢ "
            "Toxic Lime â€¢ Retro Amber â€¢ Steel Grey"
        )
        theme_list.setWordWrap(True)
        appearance_form.addRow("Available:", theme_list)

        tabs.addTab(appearance, "Appearance")

        outer.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def run_platform_setup(self):
        wizard = PlatformSetupWizard(self.values(), self, first_run=False)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            updated = wizard.values()
            self.config.update(updated)
            self.root.setText(updated.get("movie_root", self.root.text()))
            self.work.setText(updated.get("local_work", self.work.text()))
            self.handbrake.setText(updated.get("handbrake", self.handbrake.text()))
            self.jellyfin_url.setText(updated.get("jellyfin_url", self.jellyfin_url.text()))
            self.jellyfin_username.setText(updated.get("jellyfin_username", self.jellyfin_username.text()))
            self.jellyfin_api_key.setText(updated.get("jellyfin_api_key", self.jellyfin_api_key.text()))
            QMessageBox.information(self, "Platform setup", "Platform settings loaded into this Settings window. Click Save to apply them.")

    def browse_root(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose movie library", self.root.text())
        if folder: self.root.setText(folder)

    def browse_work(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose local work folder", self.work.text())
        if folder: self.work.setText(folder)

    def connect_jellyfin(self):
        self.jellyfin_test_result.setText("Connecting to Jellyfin...")
        QApplication.processEvents()
        ok, detail, token, device_id = authenticate_jellyfin(
            self.jellyfin_url.text(),
            self.jellyfin_username.text(),
            self.jellyfin_password.text(),
            device_id=self.config.get("jellyfin_device_id", ""),
        )
        self.jellyfin_test_result.setText(("âœ“ " if ok else "âœ• ") + detail)
        self.jellyfin_test_result.setStyleSheet(
            "color:#78e286;font-weight:700;" if ok else "color:#ff6879;font-weight:700;"
        )
        if ok:
            self.jellyfin_api_key.setText(token)
            self.config["jellyfin_device_id"] = device_id
            self.jellyfin_password.clear()

    def test_jellyfin_connection(self):
        temporary_config = {
            **self.config,
            "jellyfin_url": self.jellyfin_url.text().strip().rstrip("/"),
            "jellyfin_username": self.jellyfin_username.text().strip(),
            "jellyfin_api_key": self.jellyfin_api_key.text().strip(),
            "jellyfin_device_id": self.config.get("jellyfin_device_id", ""),
            "update_manifest_url": self.update_manifest_url.text().strip(),
            "github_repo": self.github_repo.text().strip(),
            "queue_finish_action": self.queue_finish_action.currentText(),
            "show_live_telemetry": self.show_live_telemetry.isChecked(),
            "analyze_media_on_scan": self.analyze_media.isChecked(),
        }

        self.jellyfin_test_result.setText("Testing...")
        QApplication.processEvents()

        ok, detail = test_jellyfin(temporary_config)
        self.jellyfin_test_result.setText(
            ("âœ“ " if ok else "âœ• ") + detail
        )
        self.jellyfin_test_result.setStyleSheet(
            "color:#78e286;font-weight:700;"
            if ok
            else "color:#ff6879;font-weight:700;"
        )

    def install_update_from_zip(self):
        update_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Evil's Media Optimizer update",
            str(APP_DIR),
            "Update packages (*.zip)",
        )
        if not update_path:
            return

        answer = QMessageBox.question(
            self,
            "Install and restart",
            "Evil's Media Optimizer will close, install the update using "
            "a separate updater, and then reopen automatically.\n\n"
            "Your settings, Jellyfin key, history, poster cache and logs "
            "will be preserved.\n\nContinue?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            new_version = launch_external_update(
                Path(update_path),
                APP_DIR,
                current_version=APP_VERSION,
                current_pid=os.getpid(),
            )
        except UpdateError as exc:
            QMessageBox.critical(
                self,
                "Update could not start",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Update ready",
            f"Version {new_version} is ready to install.\n\n"
            "The app will now close. The separate updater will show "
            "its progress and reopen Evil's Media Optimizer when done.",
        )
        QTimer.singleShot(250, QApplication.instance().quit)

    def values(self) -> dict:
        return {
            **self.config,
            "movie_root": self.root.text().strip(),
            "local_work": self.work.text().strip(),
            "minimum_size_gib": self.minimum.value(),
            "default_target_gib": self.default_target.value(),
            "audio_kbps": self.audio.value(),
            "handbrake": self.handbrake.text().strip(),
            "ffprobe": self.ffprobe.text().strip(),
            "encoder": self.encoder.currentText(),
            "encoder_preset": self.preset.currentText(),
            "jellyfin_url": self.jellyfin_url.text().strip().rstrip("/"),
            "jellyfin_api_key": self.jellyfin_api_key.text().strip(),
            "update_manifest_url": self.update_manifest_url.text().strip(),
            "github_repo": self.github_repo.text().strip(),
            "queue_finish_action": self.queue_finish_action.currentText(),
            "show_live_telemetry": self.show_live_telemetry.isChecked(),
            "analyze_media_on_scan": self.analyze_media.isChecked(),
            "theme": self.theme.currentText(),
            "banner_theme": self.banner_theme.currentText(),
            "ui_scale_percent": self.ui_scale.value(),
        }



class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} â€” Help")
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml("""
        <h1 style='color:#cf55f6'>Evil's Media Optimizer</h1>
        <p><b>1.</b> Click <b>Scan MainMovies</b>.</p>
        <p><b>2.</b> Select a movie and choose a target size: 3, 5, 10, 15, 20 GiB, or enter a custom size.</p>
        <p><b>3.</b> Tick the boxes beside as many movies as you want, apply one target size to all checked movies, then click <b>Add Checked to Queue</b>.</p>
        <p><b>4.</b> Click <b>Start Queue</b>. The app copies each source to the PC, encodes with your RTX NVENC, verifies the result, then safely replaces the original.</p>
        <h3>Safety</h3>
        <ul><li>The original stays in place until the encoded file has copied back and been verified.</li>
        <li>A temporary backup is used during final replacement.</li><li>On failure, local work files are retained.</li></ul>
        <h3>Version 2.0 features</h3><ul><li>Bulk checkbox selection</li><li>Drag-and-drop queue manager</li><li>Local poster discovery</li><li>Optimization recommendations</li><li>System health checker</li><li>Tabbed settings</li></ul><h3>Requirements</h3>
        <p>HandBrakeCLI and ffprobe must be installed and available in PATH. The NAS share must be reachable at the path shown in Settings.</p>
        <h3>Important</h3>
        <p>Do not restart the PC or NAS while a movie is being copied or replaced.</p>
        """)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(self.reject); buttons.clicked.connect(self.accept); layout.addWidget(buttons)



class QueueManagerDialog(QDialog):
    def __init__(
        self,
        movies: list[Movie],
        pause_after_current: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(
            f"{APP_NAME} â€” Queue Control Centre"
        )
        self.resize(980, 690)
        self.movies = list(movies)

        layout = QVBoxLayout(self)

        heading = QLabel("QUEUE CONTROL CENTRE")
        heading.setStyleSheet(
            "font-size:21px;font-weight:900;color:#d15cff;"
        )
        layout.addWidget(heading)

        intro = QLabel(
            "Drag movies to reorder them. Nothing is encoded until "
            "you press Start Process in the main window."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        summary = QFrame()
        summary.setObjectName("queueSummary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(12, 8, 12, 8)

        self.count_label = QLabel()
        self.current_label = QLabel()
        self.target_label = QLabel()
        self.saving_label = QLabel()

        for widget in (
            self.count_label,
            self.current_label,
            self.target_label,
            self.saving_label,
        ):
            widget.setObjectName("queueSummaryValue")
            summary_layout.addWidget(widget, 1)

        layout.addWidget(summary)

        self.list = QListWidget()
        self.list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.list.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )
        self.list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list.model().rowsMoved.connect(
            lambda *_args: self.update_summary()
        )
        layout.addWidget(self.list, 1)

        controls = QHBoxLayout()

        top = QPushButton("â‡ˆ TOP")
        top.clicked.connect(self.move_top)
        controls.addWidget(top)

        up = QPushButton("â†‘ UP")
        up.clicked.connect(
            lambda: self.move_selected(-1)
        )
        controls.addWidget(up)

        down = QPushButton("â†“ DOWN")
        down.clicked.connect(
            lambda: self.move_selected(1)
        )
        controls.addWidget(down)

        bottom = QPushButton("â‡Š BOTTOM")
        bottom.clicked.connect(self.move_bottom)
        controls.addWidget(bottom)

        remove = QPushButton("âœ• REMOVE")
        remove.clicked.connect(self.remove_selected)
        controls.addWidget(remove)

        clear = QPushButton("CLEAR QUEUE")
        clear.clicked.connect(self.clear_queue)
        controls.addWidget(clear)

        controls.addStretch()

        sort_title = QPushButton("SORT Aâ€“Z")
        sort_title.clicked.connect(self.sort_title)
        controls.addWidget(sort_title)

        sort_saving = QPushButton("BIGGEST SAVING")
        sort_saving.clicked.connect(self.sort_saving)
        controls.addWidget(sort_saving)

        layout.addLayout(controls)

        option_row = QHBoxLayout()
        self.pause_checkbox = QCheckBox(
            "Pause after the current movie finishes"
        )
        self.pause_checkbox.setChecked(
            pause_after_current
        )
        self.pause_checkbox.setToolTip(
            "The current movie completes safely. Remaining queued "
            "movies stay queued until Start Process is pressed again."
        )
        option_row.addWidget(self.pause_checkbox)
        option_row.addStretch()

        cancel = QPushButton("CANCEL")
        cancel.clicked.connect(self.reject)
        option_row.addWidget(cancel)

        save = QPushButton("SAVE QUEUE")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.accept)
        option_row.addWidget(save)

        layout.addLayout(option_row)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for index, movie in enumerate(self.movies, 1):
            item = QListWidgetItem(
                f"{index:02d}   {movie.title}\n"
                f"       Score {movie.optimization_score}/100  â€¢  "
                f"Risk {movie.visual_risk}  â€¢  "
                f"save {human_size(movie.saving)}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                movie,
            )
            self.list.addItem(item)
        self.update_summary()

    def update_summary(self):
        movies = self.ordered_movies()
        current = sum(movie.size for movie in movies)
        target = sum(
            int(movie.target_gib * 1024**3)
            for movie in movies
        )
        saving = sum(movie.saving for movie in movies)

        self.count_label.setText(
            f"QUEUE\n{len(movies)} movies"
        )
        self.current_label.setText(
            f"CURRENT\n{human_size(current)}"
        )
        self.target_label.setText(
            f"TARGET\n{human_size(target)}"
        )
        self.saving_label.setText(
            f"SAVING\n{human_size(saving)}"
        )

    def rebuild_from_movies(
        self,
        movies: list[Movie],
        selected_movie: Movie | None = None,
    ):
        self.movies = list(movies)
        self.refresh()
        if selected_movie is not None:
            for row in range(self.list.count()):
                if (
                    self.list.item(row).data(
                        Qt.ItemDataRole.UserRole
                    )
                    is selected_movie
                ):
                    self.list.setCurrentRow(row)
                    break

    def move_selected(self, direction: int):
        row = self.list.currentRow()
        target = row + direction
        if (
            row < 0
            or target < 0
            or target >= self.list.count()
        ):
            return
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)
        self.update_summary()

    def move_top(self):
        row = self.list.currentRow()
        if row <= 0:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(0, item)
        self.list.setCurrentRow(0)
        self.update_summary()

    def move_bottom(self):
        row = self.list.currentRow()
        if row < 0 or row == self.list.count() - 1:
            return
        item = self.list.takeItem(row)
        self.list.addItem(item)
        self.list.setCurrentRow(
            self.list.count() - 1
        )
        self.update_summary()

    def remove_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self.update_summary()

    def clear_queue(self):
        answer = QMessageBox.question(
            self,
            "Clear queue",
            "Remove every movie from this queue?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.list.clear()
            self.update_summary()

    def sort_title(self):
        movies = sorted(
            self.ordered_movies(),
            key=lambda movie: movie.title.casefold(),
        )
        self.rebuild_from_movies(movies)

    def sort_saving(self):
        movies = sorted(
            self.ordered_movies(),
            key=lambda movie: movie.saving,
            reverse=True,
        )
        self.rebuild_from_movies(movies)

    def ordered_movies(self) -> list[Movie]:
        return [
            self.list.item(i).data(
                Qt.ItemDataRole.UserRole
            )
            for i in range(self.list.count())
        ]

    def pause_after_current(self) -> bool:
        return self.pause_checkbox.isChecked()


class HealthDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} â€” System Health")
        self.resize(650, 500)
        layout = QVBoxLayout(self)
        heading = QLabel("ðŸ’€ EVIL'S SYSTEM STATUS")
        heading.setStyleSheet("font-size:22px;font-weight:900;color:#d15cff;")
        layout.addWidget(heading)

        self.results = QListWidget()
        layout.addWidget(self.results, 1)

        checks = []
        nas_ok = Path(config["movie_root"]).exists()
        checks.append(("NAS configured library", nas_ok, config["movie_root"]))
        hb_path = shutil.which(config["handbrake"])
        checks.append(("HandBrakeCLI", bool(hb_path), hb_path or "Not found in PATH"))
        fp_path = shutil.which(config["ffprobe"])
        checks.append(("ffprobe", bool(fp_path), fp_path or "Not found in PATH"))

        nvenc_ok = False
        nvenc_detail = "Could not test"
        if hb_path:
            try:
                result = subprocess.run(
                    [config["handbrake"], "--help"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    check=False,
                    **hidden_process_kwargs(),
                )
                output = (result.stdout + result.stderr).lower()
                nvenc_ok = "nvenc" in output
                nvenc_detail = "NVENC detected" if nvenc_ok else "NVENC not listed by HandBrake"
            except Exception as exc:
                nvenc_detail = str(exc)
        checks.append(("NVIDIA NVENC", nvenc_ok, nvenc_detail))

        jellyfin_ok = False
        jellyfin_detail = "API key not configured"
        base_url = str(config.get("jellyfin_url", "")).strip().rstrip("/")
        api_key = str(config.get("jellyfin_api_key", "")).strip()
        if base_url and api_key:
            try:
                request = urllib.request.Request(
                    f"{base_url}/System/Info?api_key={urllib.parse.quote(api_key)}",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=6) as response:
                    info = json.loads(response.read().decode("utf-8", errors="replace"))
                jellyfin_ok = True
                jellyfin_detail = f"{info.get('ServerName', 'Jellyfin')} {info.get('Version', '')}".strip()
            except Exception as exc:
                jellyfin_detail = str(exc)
        checks.append(("Jellyfin poster API", jellyfin_ok, jellyfin_detail))

        work = Path(config["local_work"])
        try:
            work.mkdir(parents=True, exist_ok=True)
            work_ok = work.exists() and os.access(work, os.W_OK)
        except OSError:
            work_ok = False
        checks.append(("Local work folder", work_ok, str(work)))

        passed = 0
        for label, ok, detail in checks:
            passed += int(ok)
            item = QListWidgetItem(f"{'ðŸŸ¢' if ok else 'ðŸ”´'}  {label}\n      {detail}")
            item.setForeground(QColor("#78e286" if ok else "#ff6879"))
            self.results.addItem(item)

        score = int(passed / len(checks) * 100)
        score_label = QLabel(f"Overall readiness: {score}%")
        score_label.setStyleSheet(
            f"font-size:18px;font-weight:800;color:{'#78e286' if score == 100 else '#ffbd59'};"
        )
        layout.addWidget(score_label)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject); close.clicked.connect(self.accept)
        layout.addWidget(close)


class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str, accent: str):
        super().__init__(); self.setObjectName("statCard")
        layout = QVBoxLayout(self); layout.setContentsMargins(15, 11, 15, 11); layout.setSpacing(1)
        heading = QLabel(title); heading.setObjectName("statHeading")
        self.value = QLabel(value); self.value.setObjectName("statValue"); self.value.setStyleSheet(f"color:{accent};")
        sub = QLabel(subtitle); sub.setObjectName("statSub")
        layout.addWidget(heading); layout.addWidget(self.value); layout.addWidget(sub)


class MainWindow(QMainWindow):
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(
            QIcon(str(APP_DIR / "assets" / "evils_skull.ico")),
            self,
        )
        self.tray_icon.setToolTip(f"{APP_NAME} {APP_VERSION}")

        menu = QMenu(self)
        restore_action = QAction("Restore EMP", self)
        restore_action.triggered.connect(self.restore_from_tray)
        menu.addAction(restore_action)
        menu.addSeparator()

        exit_action = QAction("Exit EMP", self)
        exit_action.triggered.connect(self.request_exit)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def tray_activated(self, reason):
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.restore_from_tray()

    def restore_from_tray(self):
        self.show()
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized
        )
        self.raise_()
        self.activateWindow()

    def minimize_to_tray(self):
        if not hasattr(self, "tray_icon"):
            return
        if not self.tray_icon.isVisible():
            self.tray_icon.show()
        self.hide()
        self.tray_icon.showMessage(
            APP_NAME,
            "EMP is still running. The current movie will continue safely.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def request_exit(self):
        self.close()

    def request_exit_after_current(self):
        if not self.queue_running or self.current_movie is None:
            self.close()
            return
        self.exit_after_current = True
        self.status.setText(
            "Exit requested â€” the current movie will finish, then EMP will close."
        )
        self.operations.set_process_status("Exit requested after current movie")
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                APP_NAME,
                "Exit queued. EMP will close after the current movie finishes.",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )

    def closeEvent(self, event: QCloseEvent):
        if self.queue_running and self.current_movie is not None:
            choice = QMessageBox(self)
            choice.setIcon(QMessageBox.Icon.Warning)
            choice.setWindowTitle("Movie processing is active")
            choice.setText("EMP is currently processing a movie.")
            choice.setInformativeText(
                f'Do you want EMP to finish "{self.current_movie.title}" before closing?'
            )

            finish_exit = choice.addButton(
                "Finish current movie, then exit",
                QMessageBox.ButtonRole.AcceptRole,
            )
            keep_processing = choice.addButton(
                "Keep processing",
                QMessageBox.ButtonRole.RejectRole,
            )
            minimize = choice.addButton(
                "Minimize to hidden icons",
                QMessageBox.ButtonRole.ActionRole,
            )
            choice.exec()

            if choice.clickedButton() is finish_exit:
                self.request_exit_after_current()
            elif choice.clickedButton() is minimize:
                self.minimize_to_tray()

            event.ignore()
            return

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        event.accept()
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.movies = []
        self.visible_movies = []
        self.queue = []
        self.header_sort_column = None
        self.header_sort_ascending = True
        self.pending_queue = []
        # Keep a strong Python reference to the active QRunnable.  Without this,
        # a queued follow-up EncodeWorker can be garbage-collected before the
        # QThreadPool gets a chance to start it on systems with a busy/single
        # worker thread.
        self.active_encode_worker = None
        self.pool = QThreadPool.globalInstance()
        self.current_movie = None
        self.current_started_at = 0.0
        self.pause_after_current = False
        self.queue_running = False
        self.exit_after_current = False
        self.queue_advance_timer = QTimer(self)
        self.queue_advance_timer.setSingleShot(True)
        self.queue_advance_timer.timeout.connect(self.process_next)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}"); self.setWindowIcon(QIcon(str(APP_DIR/'assets'/'evils_skull.ico'))); self.resize(1660, 980); self.setMinimumSize(1320, 800)
        self.build_ui()
        self.setup_system_tray()
        self.apply_style()
        self.operations_timer = QTimer(self)
        self.operations_timer.setInterval(30000)
        self.operations_timer.timeout.connect(
            self.operations.refresh_services
        )
        self.operations_timer.start()
        QTimer.singleShot(
            500,
            self.operations.refresh_services,
        )
        self.latest_release = None
        self.update_checked_at = "Not checked yet"
        QTimer.singleShot(1400, self.check_for_updates)

    def build_ui(self):
        central=QWidget(); page=QVBoxLayout(central); page.setContentsMargins(0,0,0,0); page.setSpacing(0)
        header_wrap=QWidget()
        header_layout=QVBoxLayout(header_wrap)
        header_layout.setContentsMargins(0,0,0,0)
        self.header=QLabel()
        self.header.setObjectName("header")
        self.header.setScaledContents(False)
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header.setFixedHeight(190)
        self.update_theme_banner()
        header_layout.addWidget(self.header)

        quick_bar = QFrame()
        quick_bar.setObjectName("quickBar")
        quick_layout = QHBoxLayout(quick_bar)
        quick_layout.setContentsMargins(10, 5, 10, 5)
        quick_layout.addStretch()

        help_button = QPushButton("?  HELP")
        help_button.setObjectName("quickButton")
        help_button.clicked.connect(self.show_help)
        quick_layout.addWidget(help_button)

        settings_button = QPushButton("âš™  SETTINGS")
        settings_button.setObjectName("quickButton")
        settings_button.clicked.connect(self.show_settings)
        quick_layout.addWidget(settings_button)

        self.update_button = QPushButton("â—  UPDATE STATUS")
        self.update_button.setObjectName("updateButton")
        self.update_button.setToolTip("EMP update status")
        self.update_button.clicked.connect(self.update_button_clicked)
        quick_layout.addWidget(self.update_button)

        header_layout.addWidget(quick_bar)
        page.addWidget(header_wrap)
        body=QWidget(); body_layout=QHBoxLayout(body); body_layout.setContentsMargins(8,8,8,8); body_layout.setSpacing(8); body_layout.addWidget(self.make_sidebar())
        content=QWidget(); content_layout=QVBoxLayout(content); content_layout.setContentsMargins(0,0,0,0); content_layout.setSpacing(8)
        self.operations = OperationsCenterPanel(self.config)
        self.operations.scan_requested.connect(self.scan)
        self.operations.start_requested.connect(self.start_queue)
        content_layout.addWidget(self.operations)

        stats=QHBoxLayout(); stats.setSpacing(8)
        self.found_card=StatCard("MOVIES FOUND","0",f"Over {self.config['minimum_size_gib']} GiB","#c956ff")
        self.optimized_card=StatCard("QUEUED","0","Ready to optimize","#4eb2ff")
        self.library_card=StatCard("VISIBLE LIBRARY","0 B","Scanned total","#70df7b")
        self.saving_card=StatCard("POTENTIAL SAVING","0 B","Selected titles","#ff5fa8")
        for card in (self.found_card,self.optimized_card,self.library_card,self.saving_card): stats.addWidget(card)
        content_layout.addLayout(stats)
        toolbar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search movies..."); self.search.textChanged.connect(self.apply_filter); toolbar.addWidget(self.search,1)
        self.filter_box=QComboBox(); self.filter_box.addItems([
            "All movies",
            "Queued only",
            "Not queued",
            "Excellent (90+)",
            "Very Good (75+)",
            "HDR movies",
            "Modern codecs",
            "No subtitles",
            "Possible duplicates",
            "Metadata failed",
        ]); self.filter_box.currentTextChanged.connect(self.apply_filter); toolbar.addWidget(self.filter_box)
        self.sort_box=QComboBox(); self.sort_box.addItems([
            "Size: High to low",
            "Size: Low to high",
            "Title: A to Z",
            "Optimization score: High to low",
            "Saving: High to low",
            "Runtime: Longest first",
        ]); self.sort_box.currentTextChanged.connect(self.apply_filter); toolbar.addWidget(self.sort_box)
        queue_manager_btn=QPushButton("â˜· QUEUE MANAGER"); queue_manager_btn.clicked.connect(self.show_queue_manager); toolbar.addWidget(queue_manager_btn)
        health_btn=QPushButton("â™¥ SYSTEM HEALTH"); health_btn.clicked.connect(self.show_health); toolbar.addWidget(health_btn)
        duplicate_btn=QPushButton("â‰¡ DUPLICATES"); duplicate_btn.clicked.connect(self.show_duplicates); toolbar.addWidget(duplicate_btn)
        self.scan_btn=QPushButton("â˜   SCAN"); self.scan_btn.setObjectName("primaryButton"); self.scan_btn.clicked.connect(self.scan); toolbar.addWidget(self.scan_btn); content_layout.addLayout(toolbar)

        chips=QHBoxLayout()
        chips.setSpacing(5)
        chips.addWidget(QLabel("QUICK FILTERS:"))
        for caption, mode in (
            ("90+", "Excellent (90+)"),
            ("75+", "Very Good (75+)"),
            ("HDR", "HDR movies"),
            ("MODERN", "Modern codecs"),
            ("NO SUBS", "No subtitles"),
            ("DUPLICATES", "Possible duplicates"),
            ("CLEAR", "All movies"),
        ):
            chip=QPushButton(caption)
            chip.setObjectName("filterChip")
            chip.clicked.connect(
                lambda _checked=False, value=mode:
                self.set_quick_filter(value)
            )
            chips.addWidget(chip)
        chips.addStretch()
        content_layout.addLayout(chips)
        bulk_bar=QFrame(); bulk_bar.setObjectName("bulkBar"); bulk=QHBoxLayout(bulk_bar); bulk.setContentsMargins(10,7,10,7); bulk.setSpacing(7)
        bulk.addWidget(QLabel("BULK SELECTION:"))
        select_all_btn=QPushButton("â˜‘ SELECT ALL VISIBLE"); select_all_btn.clicked.connect(lambda:self.set_visible_checked(True)); bulk.addWidget(select_all_btn)
        clear_btn=QPushButton("â˜ CLEAR CHECKS"); clear_btn.clicked.connect(lambda:self.set_visible_checked(False)); bulk.addWidget(clear_btn)
        bulk.addSpacing(10); bulk.addWidget(QLabel("TARGET:"))
        self.bulk_target=QComboBox(); self.bulk_target.addItems(["3 GB","5 GB","10 GB","15 GB","20 GB"]); self.bulk_target.setCurrentText(f"{self.config['default_target_gib']} GB"); bulk.addWidget(self.bulk_target)
        apply_bulk_btn=QPushButton("APPLY SIZE TO CHECKED"); apply_bulk_btn.clicked.connect(self.apply_bulk_target); bulk.addWidget(apply_bulk_btn)
        self.exclude_efficient_btn=QPushButton("â˜‘ EXCLUDE ALREADY EFFICIENT")
        self.exclude_efficient_btn.setCheckable(True)
        self.exclude_efficient_btn.setChecked(True)
        self.exclude_efficient_btn.setToolTip("When enabled, movies EMP rates as ALREADY EFFICIENT (score below 40) are hidden from the scanned list. Turn it off to show them again instantly. This starts enabled every time EMP opens.")
        self.exclude_efficient_btn.toggled.connect(self.update_exclude_efficient_button)
        bulk.addWidget(self.exclude_efficient_btn)
        bulk.addStretch()
        add_checked_btn=QPushButton("â–¶ ADD CHECKED TO QUEUE"); add_checked_btn.setObjectName("startButton"); add_checked_btn.clicked.connect(self.add_checked_to_queue); bulk.addWidget(add_checked_btn)
        remove_checked_btn=QPushButton("âœ• REMOVE CHECKED"); remove_checked_btn.clicked.connect(self.remove_checked_from_queue); bulk.addWidget(remove_checked_btn)
        content_layout.addWidget(bulk_bar)
        splitter=QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.make_table_panel())
        splitter.addWidget(self.make_inspector())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([1030, 430])
        content_layout.addWidget(splitter,1)
        self.telemetry = LiveTelemetryPanel()
        content_layout.addWidget(self.telemetry)

        bottom=QFrame(); bottom.setObjectName("bottomBar"); bottom_layout=QHBoxLayout(bottom); bottom_layout.setContentsMargins(14,8,14,8)
        self.status=QLabel("Ready â€” scan your configured library to begin"); self.status.setObjectName("statusText"); bottom_layout.addWidget(self.status,1)
        self.progress=QProgressBar(); self.progress.setFixedWidth(320); self.progress.setValue(0); bottom_layout.addWidget(self.progress)
        self.start_btn=QPushButton("â–¶  START PROCESS"); self.start_btn.setObjectName("startButton"); self.start_btn.clicked.connect(self.start_queue); bottom_layout.addWidget(self.start_btn); content_layout.addWidget(bottom)
        body_layout.addWidget(content,1); page.addWidget(body,1); self.setCentralWidget(central)

    def make_sidebar(self):
        side=QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(185); layout=QVBoxLayout(side); layout.setContentsMargins(8,12,8,12); layout.setSpacing(6)
        items=[("âŒ‚","DASHBOARD",self.show_dashboard),("â–£","MOVIES",self.focus_movies),("â˜·","QUEUE",self.show_queue_manager),("â—·","HISTORY",self.show_history),("â–¥","STATISTICS",self.show_statistics),("â–³","JELLYFIN",self.show_jellyfin_info),("âš™","SETTINGS",self.show_settings),("âš’","TOOLS",self.show_tools),("â—","ABOUT",self.show_about)]
        for index,(icon,text,action) in enumerate(items):
            button=QPushButton(f"{icon}   {text}"); button.setObjectName("navActive" if index==0 else "navButton"); button.setCursor(Qt.CursorShape.PointingHandCursor)
            if action: button.clicked.connect(action)
            layout.addWidget(button)
        layout.addStretch(); return side

    def make_table_panel(self):
        panel=QFrame(); panel.setObjectName("panel"); layout=QVBoxLayout(panel); layout.setContentsMargins(0,0,0,0)
        self.table=QTableWidget(0,11); self.table.setHorizontalHeaderLabels(["SELECT","MOVIE","SCORE","BADGES","RUNTIME","CURRENT SIZE","TARGET SIZE","SAVING","SAVING %","RISK","STATUS"]); self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection); self.table.itemSelectionChanged.connect(self.update_inspector); self.table.itemChanged.connect(self.table_item_changed)
        header=self.table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for column in range(2,11): header.setSectionResizeMode(column,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self.table_header_clicked)
        layout.addWidget(self.table); return panel

    def make_inspector(self):
        scroll = QScrollArea()
        scroll.setObjectName("inspectorScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(390)

        self.inspector = QFrame()
        self.inspector.setObjectName("inspector")
        self.inspector.setMinimumWidth(370)

        layout = QVBoxLayout(self.inspector)
        layout.setContentsMargins(16, 14, 16, 18)
        layout.setSpacing(9)

        self.detail_title = QLabel("SELECT A MOVIE")
        self.detail_title.setObjectName("detailTitle")
        self.detail_title.setWordWrap(True)
        layout.addWidget(self.detail_title)

        poster_frame = QFrame()
        poster_frame.setObjectName("posterPlaceholder")
        poster_layout = QVBoxLayout(poster_frame)
        poster_layout.setContentsMargins(8, 8, 8, 8)

        self.poster = QLabel("NO\nPOSTER")
        self.poster.setObjectName("posterImage")
        self.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster.setFixedSize(200, 285)
        self.poster.setScaledContents(False)
        poster_layout.addWidget(
            self.poster,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addWidget(poster_frame)

        poster_buttons = QHBoxLayout()
        refresh_poster = QPushButton("â†» REFRESH POSTER")
        refresh_poster.clicked.connect(self.refresh_selected_poster)
        poster_buttons.addWidget(refresh_poster)
        clear_cache = QPushButton("CLEAR POSTER CACHE")
        clear_cache.clicked.connect(self.clear_poster_cache)
        poster_buttons.addWidget(clear_cache)
        layout.addLayout(poster_buttons)

        self.detail_path = QLabel("Choose a row to inspect its file.")
        self.detail_path.setObjectName("detailPath")
        self.detail_path.setWordWrap(True)
        self.detail_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.detail_path)

        self.media_summary = QLabel(
            "MEDIA DETAILS PENDING"
        )
        self.media_summary.setObjectName("mediaSummary")
        self.media_summary.setWordWrap(True)
        self.media_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.media_summary)

        self.badge_summary = QLabel("BADGES PENDING")
        self.badge_summary.setObjectName("badgeSummary")
        self.badge_summary.setWordWrap(True)
        self.badge_summary.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.badge_summary)

        self.reason_summary = QLabel(
            "RECOMMENDATION REASONS PENDING"
        )
        self.reason_summary.setObjectName("reasonSummary")
        self.reason_summary.setWordWrap(True)
        self.reason_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.reason_summary)

        self.duplicate_warning = QLabel("")
        self.duplicate_warning.setObjectName(
            "duplicateWarning"
        )
        self.duplicate_warning.setWordWrap(True)
        self.duplicate_warning.setVisible(False)
        layout.addWidget(self.duplicate_warning)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        self.size_summary = QLabel("CURRENT â€” â†’ TARGET â€”")
        self.size_summary.setObjectName("sizeSummary")
        self.size_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_summary.setWordWrap(True)
        layout.addWidget(self.size_summary)

        self.saving_summary = QLabel("SAVING â€”")
        self.saving_summary.setObjectName("savingSummary")
        self.saving_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.saving_summary.setWordWrap(True)
        layout.addWidget(self.saving_summary)

        self.recommendation = QLabel("SELECT A MOVIE")
        self.recommendation.setObjectName("recommendation")
        self.recommendation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recommendation.setWordWrap(True)
        layout.addWidget(self.recommendation)

        label = QLabel("TARGET SIZE PRESET")
        label.setObjectName("smallHeading")
        layout.addWidget(label)

        preset_grid = QGridLayout()
        for index, size in enumerate((3, 5, 10, 15, 20)):
            button = QPushButton(f"{size} GB")
            button.setObjectName("presetButton")
            button.clicked.connect(
                lambda _checked=False, value=size: self.set_selected_target(value)
            )
            preset_grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(preset_grid)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("CUSTOM:"))
        self.custom_target = QSpinBox()
        self.custom_target.setRange(1, 100)
        self.custom_target.setSuffix(" GiB")
        self.custom_target.setValue(10)
        custom_row.addWidget(self.custom_target, 1)
        apply_custom = QPushButton("APPLY")
        apply_custom.clicked.connect(
            lambda: self.set_selected_target(
                self.custom_target.value()
            )
        )
        custom_row.addWidget(apply_custom)
        layout.addLayout(custom_row)

        self.queue_selected_btn = QPushButton(
            "â–¶ ADD / REMOVE FROM QUEUE"
        )
        self.queue_selected_btn.setObjectName("startButton")
        self.queue_selected_btn.clicked.connect(
            self.toggle_selected_queue
        )
        layout.addWidget(self.queue_selected_btn)

        layout.addStretch()
        scroll.setWidget(self.inspector)
        return scroll

    def update_theme_banner(self):
        """Apply the user-selected EMP banner artwork.

        Banner choice is intentionally independent from the colour palette so
        future banner packs can be added without redesigning the theme engine.
        """
        banner_name = self.config.get("banner_theme", "Original Purple")
        banner_files = {
            "Original Purple": "header.png",
            "Red Ember": "red_ember_banner.png",
        }
        banner_path = APP_DIR / "assets" / banner_files.get(banner_name, "header.png")
        if not banner_path.exists():
            banner_path = APP_DIR / "assets" / "header.png"
        pixmap = QPixmap(str(banner_path))
        if pixmap.isNull():
            return
        # Preserve the artwork's aspect ratio. Scale to cover the banner area,
        # then let the QLabel clip the excess from the centre instead of
        # stretching skulls/text to whatever shape the window happens to be.
        target = self.header.size()
        if target.width() > 0 and target.height() > 0:
            pixmap = pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.header.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "header"):
            self.update_theme_banner()

    def apply_style(self):
        if hasattr(self, "header"):
            self.update_theme_banner()
        palette = THEME_PALETTES.get(
            self.config.get("theme", "Skull Purple"),
            THEME_PALETTES["Skull Purple"],
        )

        qss = r"""
        QMainWindow,QWidget{background:#08080c;color:#f3edf7;font-family:'Segoe UI';} QLabel#header{background:#08080c;border-bottom:2px solid #61217f;}
        QPushButton#headerIcon{background:rgba(20,10,28,210);border:1px solid #a943d0;border-radius:20px;color:#e582ff;font-size:21px;font-weight:900;padding:0;} QPushButton#headerIcon:hover{background:#6e218c;color:white;}
        QFrame#sidebar{background:#0c0b10;border:1px solid #29202f;border-radius:8px;} QPushButton#navButton,QPushButton#navActive{text-align:left;border:none;border-radius:6px;padding:11px 12px;font-size:13px;font-weight:700;color:#d9d2dd;background:transparent;} QPushButton#navButton:hover{background:#211627;color:white;} QPushButton#navActive{background:#46205a;color:white;border-left:3px solid #d554ff;} QLabel#motto{color:#bd43ec;font-size:18px;font-weight:900;font-style:italic;padding:18px 4px;}
        QFrame#statCard{background:#111016;border:1px solid #2f2636;border-radius:9px;} QLabel#statHeading{color:#a9a0ae;font-size:10px;font-weight:700;} QLabel#statValue{font-size:22px;font-weight:800;} QLabel#statSub{color:#77707d;font-size:10px;}
        QLineEdit,QComboBox,QSpinBox{background:#101015;border:1px solid #34283c;border-radius:6px;padding:8px;color:#e9e1ed;} QLineEdit:focus,QComboBox:focus,QSpinBox:focus{border:1px solid #9d3cc2;}
        QPushButton{background:#18141c;border:1px solid #493453;border-radius:6px;padding:8px 11px;font-weight:700;color:#ddd5e2;} QPushButton:hover{background:#2d1937;border-color:#a743ce;color:white;} QPushButton#primaryButton,QPushButton#startButton{background:#4f1768;border:1px solid #bf4bea;color:white;} QPushButton#startButton:hover,QPushButton#primaryButton:hover{background:#70218f;} QPushButton#presetButton{padding:7px 6px;font-size:11px;}
        QFrame#bulkBar{background:#0d0c11;border:1px solid #35243e;border-radius:7px;} QFrame#bulkBar QLabel{color:#b8aebd;font-size:10px;font-weight:800;}
        QCheckBox::indicator,QTableWidget::indicator{width:18px;height:18px;} QTableWidget::indicator:unchecked{border:1px solid #765184;background:#151119;border-radius:3px;} QTableWidget::indicator:checked{border:1px solid #d25cff;background:#8d2bb2;border-radius:3px;}
        QScrollArea#inspectorScroll{background:#0d0c11;border:1px solid #2d2333;border-radius:8px;} QScrollArea#inspectorScroll QWidget{background:#0d0c11;} QFrame#panel,QFrame#inspector{background:#0d0c11;border:1px solid #2d2333;border-radius:8px;} QTableWidget{background:#0d0c11;alternate-background-color:#131117;border:none;gridline-color:#24202a;selection-background-color:#32153f;} QHeaderView::section{background:#111016;color:#bdb4c2;border:none;border-bottom:1px solid #33253c;padding:9px;font-size:10px;font-weight:800;} QTableWidget::item{padding:8px;}
        QLabel#detailTitle{color:#cf55f6;font-size:18px;font-weight:900;font-style:italic;} QFrame#posterPlaceholder{background:#151119;border:1px solid #493254;border-radius:7px;min-height:250px;} QLabel#posterImage{color:#8f8296;font-size:18px;font-weight:900;background:transparent;} QLabel#detailPath{color:#958b9b;font-size:11px;} QLabel#mediaSummary{background:#121017;border:1px solid #312438;border-radius:7px;padding:9px;color:#cfc5d4;font-size:10px;} QLabel#badgeSummary{background:#15101c;border:1px solid #5b3270;border-radius:7px;padding:8px;color:#70cfff;font-size:10px;font-weight:900;} QLabel#reasonSummary{background:#101014;border:1px solid #39303e;border-radius:7px;padding:9px;color:#d8cedd;font-size:10px;} QPushButton#filterChip{background:#16111b;border:1px solid #4b3354;border-radius:10px;padding:4px 9px;color:#cfc4d4;font-size:9px;font-weight:800;} QPushButton#filterChip:hover{background:#3b1b48;border-color:#c956ff;color:white;} QLabel#duplicateWarning{background:#2b1d0d;border:1px solid #b17825;border-radius:7px;padding:9px;color:#ffcf78;font-size:10px;font-weight:800;} QFrame#divider{color:#382b40;} QLabel#sizeSummary{font-size:14px;font-weight:800;color:#eee8f1;} QLabel#savingSummary{color:#70df7b;font-size:13px;font-weight:800;} QLabel#recommendation{background:#17101c;border:1px solid #4d2c5b;border-radius:7px;padding:8px;color:#dfb5f4;font-size:11px;font-weight:800;} QLabel#smallHeading{color:#aea3b3;font-size:10px;font-weight:800;}
        QFrame#operationsCenter{background:#0b0910;border:1px solid #4b2858;border-radius:9px;}
        QFrame#trafficStatus{background:#121017;border:1px solid #302437;border-radius:10px;}
        QFrame#queueSummary{background:#0f0c14;border:1px solid #4b2858;border-radius:8px;}
        QLabel#queueSummaryValue{color:#d8cedd;font-size:12px;font-weight:900;padding:3px 8px;}
        QLabel#trafficLabel{color:#d3c9d8;font-size:10px;font-weight:800;}
        QFrame#operationsMetric{background:#121017;border:1px solid #302437;border-radius:7px;}
        QLabel#operationsTitle{color:#d35cff;font-size:17px;font-weight:900;}
        QLabel#operationsSubtitle,QLabel#operationsRefresh{color:#93889a;font-size:10px;}
        QLabel#operationsMetricTitle{color:#a99daf;font-size:9px;font-weight:900;}
        QLabel#operationsMetricValue{color:#d35cff;font-size:16px;font-weight:900;}
        QLabel#operationsMetricDetail{color:#817786;font-size:9px;}
        QLabel#operationsCurrent{color:#d8cedd;font-size:11px;font-weight:900;}
        QFrame#telemetryPanel{background:#09070d;border:1px solid #4b2858;border-radius:9px;}
        QLabel#telemetryHeading{color:#d7c8de;font-size:11px;font-weight:900;letter-spacing:1px;}
        QLabel#telemetryJob{color:#b9aebe;font-size:10px;font-weight:700;}
        QLabel#telemetrySecondary{color:#988ca0;font-size:9px;font-weight:700;}
        QLabel#telemetryStage{background:#351342;border:1px solid #8e35ad;border-radius:9px;padding:4px 10px;color:#e8c8f5;font-size:10px;font-weight:900;}
        QFrame#quickBar{background:#0b0910;border-bottom:1px solid #35253e;}
        QPushButton#quickButton,QPushButton#updateButton{background:#15111a;border:1px solid #493453;border-radius:6px;padding:6px 10px;color:#ded5e3;font-size:10px;font-weight:800;}
        QPushButton#quickButton:hover,QPushButton#updateButton:hover{background:#32183d;border-color:#a943d0;color:white;}
        QFrame#bottomBar{background:#0d0c11;border:1px solid #2c2133;border-radius:8px;} QLabel#statusText{color:#c9becf;} QProgressBar{background:#17121b;border:1px solid #3d2946;border-radius:6px;text-align:center;color:white;} QProgressBar::chunk{background:#9f36c8;border-radius:5px;} QSplitter::handle{background:#1e1723;width:5px;}
        """

        replacements = {
            "#08080c": palette["bg"],
            "#0d0c11": palette["surface"],
            "#121017": palette["surface2"],
            "#111016": palette["surface2"],
            "#0c0b10": palette["surface"],
            "#0b0910": palette["surface"],
            "#09070d": palette["bg"],
            "#101015": palette["surface2"],
            "#151119": palette["surface2"],
            "#17121b": palette["surface2"],
            "#18141c": palette["surface2"],
            "#29202f": palette["border"],
            "#2d2333": palette["border"],
            "#302437": palette["border"],
            "#312438": palette["border"],
            "#35243e": palette["border"],
            "#35253e": palette["border"],
            "#34283c": palette["border"],
            "#493453": palette["border"],
            "#4b2858": palette["border"],
            "#4b3354": palette["border"],
            "#61217f": palette["accent_dark"],
            "#9d3cc2": palette["accent"],
            "#a743ce": palette["accent"],
            "#a943d0": palette["accent"],
            "#bf4bea": palette["accent"],
            "#cf55f6": palette["accent"],
            "#d25cff": palette["accent"],
            "#d35cff": palette["accent"],
            "#d554ff": palette["accent"],
            "#e582ff": palette["accent"],
            "#4f1768": palette["accent_dark"],
            "#46205a": palette["accent_dark"],
            "#351342": palette["accent_dark"],
            "#70218f": palette["accent_hover"],
            "#6e218c": palette["accent_hover"],
            "#32183d": palette["accent_hover"],
            "#2d1937": palette["accent_hover"],
            "#f3edf7": palette["text"],
            "#eee8f1": palette["text"],
            "#e9e1ed": palette["text"],
            "#ddd5e2": palette["text"],
            "#d9d2dd": palette["text"],
            "#d8cedd": palette["text"],
            "#cfc5d4": palette["text"],
            "#c9becf": palette["text"],
            "#a9a0ae": palette["muted"],
            "#a99daf": palette["muted"],
            "#aea3b3": palette["muted"],
            "#958b9b": palette["muted"],
            "#93889a": palette["muted"],
            "#70df7b": palette["success"],
            "#ffbd59": palette["warning"],
            "#ff6879": palette["danger"],
            "#5db7ff": palette["blue"],
            "#70cfff": palette["blue"],
            "#9f36c8": palette["accent"],
            "#8d2bb2": palette["accent_dark"],
        }

        for original, replacement in replacements.items():
            qss = qss.replace(original, replacement)

        ui_scale = int(self.config.get("ui_scale_percent", 100))
        qss = scale_qss_font_sizes(qss, ui_scale)

        app = QApplication.instance()
        if app is not None:
            font = QFont("Segoe UI")
            font.setPointSizeF(9.0 * max(0.85, min(1.50, ui_scale / 100.0)))
            app.setFont(font)

        self.setStyleSheet(qss)

    def scan(self):
        self.scan_btn.setEnabled(False); root=Path(self.config["movie_root"]); self.status.setText(f"Scanning {root}..."); self.progress.setRange(0,0)
        worker=Scanner(root,int(self.config["minimum_size_gib"]*1024**3),int(self.config["default_target_gib"])); worker.signals.finished.connect(self.scan_done); worker.signals.failed.connect(self.failed); self.pool.start(worker)
    def scan_done(self,movies):
        self.movies = movies
        self.queue = []
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.apply_filter()
        self.found_card.value.setText(str(len(movies)))
        self.library_card.value.setText(
            human_size(sum(movie.size for movie in movies))
        )
        self.update_stats()
        self.operations.set_process_status("Ready")

        if not movies:
            self.scan_btn.setEnabled(True)
            self.status.setText(
                "No movies matched the current scan limit."
            )
            return

        if (
            self.config.get("jellyfin_url")
            and self.config.get("jellyfin_api_key")
        ):
            self.status.setText(
                f"Found {len(movies)} movies. Pulling all posters..."
            )
            self.progress.setValue(0)
            self.scan_btn.setEnabled(False)
            worker = PosterPrefetchWorker(
                movies,
                self.config,
            )
            worker.signals.progress.connect(
                self.poster_prefetch_progress
            )
            worker.signals.finished.connect(
                self.poster_prefetch_done
            )
            worker.signals.failed.connect(
                self.poster_prefetch_failed
            )
            self.pool.start(worker)
        else:
            self.start_metadata_analysis(
                "Movie scan complete."
            )

    def poster_prefetch_progress(
        self,
        percent,
        message,
    ):
        self.progress.setValue(percent)
        self.status.setText(message)

    def poster_prefetch_done(self, result):
        detail = (
            f"{result['available']} posters available "
            f"({result['downloaded']} downloaded)."
        )
        self.start_metadata_analysis(detail)

    def poster_prefetch_failed(self, message):
        log(f"Poster prefetch failed: {message}")
        self.start_metadata_analysis(
            f"Poster download stopped: {message}"
        )

    def start_metadata_analysis(
        self,
        previous_detail: str = "",
    ):
        if not self.config.get(
            "analyze_media_on_scan",
            True,
        ):
            self.scan_btn.setEnabled(True)
            self.progress.setValue(100)
            self.update_duplicate_groups()
            self.apply_filter()
            self.status.setText(
                f"Scan complete. {previous_detail}".strip()
            )
            self.update_inspector()
            return

        self.status.setText(
            "Analyzing codec, runtime, HDR, audio and subtitles..."
        )
        self.progress.setValue(0)
        self.scan_btn.setEnabled(False)

        worker = MetadataWorker(
            self.movies,
            self.config,
        )
        worker.signals.progress.connect(
            self.metadata_progress
        )
        worker.signals.finished.connect(
            self.metadata_done
        )
        worker.signals.failed.connect(
            self.metadata_failed
        )
        self.pool.start(worker)

    def metadata_progress(
        self,
        percent: int,
        message: str,
    ):
        self.progress.setValue(percent)
        self.status.setText(message)

    def metadata_done(self, result: dict):
        self.scan_btn.setEnabled(True)
        self.progress.setValue(100)
        self.update_duplicate_groups()
        self.apply_filter()
        self.update_inspector()

        duplicate_titles = len(
            {
                normalize_movie_title(movie.title)
                for movie in self.movies
                if movie.duplicate_count > 1
            }
        )
        self.status.setText(
            f"Scan complete: {result['total']} movies; "
            f"{result['analyzed']} analyzed, "
            f"{result['cached']} loaded from cache, "
            f"{result['failed']} failed; "
            f"{duplicate_titles} possible duplicate title groups."
        )

    def metadata_failed(self, message: str):
        self.scan_btn.setEnabled(True)
        self.progress.setValue(0)
        self.update_duplicate_groups()
        self.apply_filter()
        self.status.setText(
            "Movie scan completed, but media analysis stopped: "
            f"{message}"
        )

    def set_quick_filter(self, mode: str):
        index = self.filter_box.findText(mode)
        if index >= 0:
            self.filter_box.setCurrentIndex(index)
        else:
            self.apply_filter()

    def sort_box_changed(self, _text: str):
        self.header_sort_column = None
        if hasattr(self, "table"):
            self.table.horizontalHeader().setSortIndicatorShown(False)
        self.apply_filter()

    def table_header_clicked(self, column: int):
        # SELECT is a checkbox column, not a useful sortable data field.
        if column == 0:
            return
        if self.header_sort_column == column:
            self.header_sort_ascending = not self.header_sort_ascending
        else:
            self.header_sort_column = column
            # Text starts A-Z; numeric values start biggest-first.
            self.header_sort_ascending = column in {1, 3, 9, 10}
        header = self.table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(
            column,
            Qt.SortOrder.AscendingOrder
            if self.header_sort_ascending
            else Qt.SortOrder.DescendingOrder,
        )
        self.apply_filter()

    def movie_status_sort_text(self, movie: Movie) -> str:
        if movie.duplicate_count > 1:
            return f"possible duplicate {movie.duplicate_count:06d}"
        if movie.status != "Ready":
            return movie.status.casefold()
        if movie.queued:
            return "queued"
        return movie.optimization_rating.casefold()

    def header_sort_value(self, movie: Movie, column: int):
        if column == 1:
            return movie.title.casefold()
        if column == 2:
            return movie.optimization_score
        if column == 3:
            return movie.badges_text.casefold()
        if column == 4:
            return movie.duration_seconds
        if column == 5:
            return movie.size
        if column == 6:
            return movie.target_gib
        if column == 7:
            return movie.saving
        if column == 8:
            return movie.saving_percent
        if column == 9:
            return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(movie.visual_risk.upper(), 99)
        if column == 10:
            return self.movie_status_sort_text(movie)
        return movie.title.casefold()

    def apply_filter(self):
        search = self.search.text().strip().lower()
        mode = self.filter_box.currentText()

        items = [
            movie
            for movie in self.movies
            if search in movie.title.lower()
            or search in movie.video_text.lower()
            or search in movie.badges_text.lower()
        ]

        # Live library filter: hide titles EMP already considers efficient while
        # the exclusion toggle is enabled. The movies remain in self.movies so
        # switching the toggle off restores them instantly without a rescan.
        if (
            hasattr(self, "exclude_efficient_btn")
            and self.exclude_efficient_btn.isChecked()
        ):
            items = [
                movie for movie in items
                if not self.is_already_efficient(movie)
            ]

        if mode == "Queued only":
            items = [
                movie
                for movie in items
                if movie.queued
            ]
        elif mode == "Not queued":
            items = [
                movie
                for movie in items
                if not movie.queued
            ]
        elif mode == "Excellent (90+)":
            items = [
                movie for movie in items
                if movie.optimization_score >= 90
            ]
        elif mode == "Very Good (75+)":
            items = [
                movie for movie in items
                if movie.optimization_score >= 75
            ]
        elif mode == "HDR movies":
            items = [
                movie for movie in items
                if movie.hdr_badge not in {"SDR", "UNKNOWN"}
            ]
        elif mode == "Modern codecs":
            items = [
                movie for movie in items
                if movie.video_codec.casefold()
                in {"hevc", "h265", "av1", "vp9"}
            ]
        elif mode == "No subtitles":
            items = [
                movie for movie in items
                if movie.metadata_status == "Ready"
                and movie.subtitle_count == 0
            ]
        elif mode == "Possible duplicates":
            items = [
                movie
                for movie in items
                if movie.duplicate_count > 1
            ]
        elif mode == "Metadata failed":
            items = [
                movie
                for movie in items
                if movie.metadata_status == "Failed"
            ]

        if self.header_sort_column is not None:
            items.sort(
                key=lambda movie: self.header_sort_value(
                    movie, self.header_sort_column
                ),
                reverse=not self.header_sort_ascending,
            )
        else:
            sort = self.sort_box.currentText()
            if sort == "Size: Low to high":
                items.sort(key=lambda movie: movie.size)
            elif sort == "Title: A to Z":
                items.sort(key=lambda movie: movie.title.lower())
            elif sort == "Optimization score: High to low":
                items.sort(
                    key=lambda movie: (
                        -movie.optimization_score,
                        -movie.saving,
                    )
                )
            elif sort == "Saving: High to low":
                items.sort(key=lambda movie: -movie.saving)
            elif sort == "Runtime: Longest first":
                items.sort(
                    key=lambda movie: -movie.duration_seconds
                )
            else:
                items.sort(key=lambda movie: -movie.size)

        self.visible_movies = items
        self.populate_table()

    def update_duplicate_groups(self):
        groups: dict[str, list[Movie]] = {}
        for movie in self.movies:
            key = normalize_movie_title(movie.title)
            if key:
                groups.setdefault(key, []).append(movie)

        for movie in self.movies:
            movie.duplicate_count = 0

        for group in groups.values():
            if len(group) > 1:
                for movie in group:
                    movie.duplicate_count = len(group)

    def show_duplicates(self):
        groups: dict[str, list[Movie]] = {}
        for movie in self.movies:
            if movie.duplicate_count > 1:
                groups.setdefault(
                    normalize_movie_title(movie.title),
                    [],
                ).append(movie)

        if not groups:
            QMessageBox.information(
                self,
                "Duplicate review",
                "No possible duplicate movie titles were found "
                "in the current scan.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(
            "Possible Duplicate Movies"
        )
        dialog.resize(920, 620)
        layout = QVBoxLayout(dialog)

        note = QLabel(
            "These are title-based matches for manual review. "
            "Evil's Media Optimizer will not delete or modify any "
            "duplicate automatically."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        listing = QListWidget()
        for group in sorted(
            groups.values(),
            key=lambda value: value[0].title.lower(),
        ):
            header = QListWidgetItem(
                f"âš  {group[0].title} â€” {len(group)} files"
            )
            header.setForeground(QColor("#ffbd59"))
            listing.addItem(header)
            for movie in sorted(
                group,
                key=lambda value: -value.size,
            ):
                item = QListWidgetItem(
                    f"    {human_size(movie.size)}  â€¢  "
                    f"{movie.video_text}  â€¢  {movie.path}"
                )
                item.setForeground(QColor("#cfc5d4"))
                listing.addItem(item)
        layout.addWidget(listing, 1)

        close = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def populate_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.visible_movies))

        score_colors = {
            5: "#70df7b",
            4: "#a8e66f",
            3: "#ffbd59",
            2: "#ff8f59",
            1: "#a59aa9",
        }

        for row, movie in enumerate(self.visible_movies):
            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            check.setCheckState(
                Qt.CheckState.Checked
                if movie.selected
                else Qt.CheckState.Unchecked
            )
            check.setData(Qt.ItemDataRole.UserRole, movie)
            check.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, check)

            title = QTableWidgetItem(movie.title)
            title.setToolTip(str(movie.path))
            title.setData(Qt.ItemDataRole.UserRole, movie)
            title.setForeground(
                QColor(
                    "#ffbd59"
                    if movie.duplicate_count > 1
                    else "#d35cff"
                    if movie.queued
                    else "#f3edf7"
                )
            )
            self.table.setItem(row, 1, title)

            score_item = QTableWidgetItem(
                f"{movie.optimization_score}/100"
            )
            score_item.setForeground(QColor(movie.score_colour))
            score_item.setToolTip(
                movie.optimization_rating
                + "\n\n"
                + "\n".join(
                    f"{name}: {value:+d}"
                    for name, value
                    in movie.optimization_breakdown.items()
                )
            )
            self.table.setItem(row, 2, score_item)

            badges = QTableWidgetItem(
                movie.badges_text
                if movie.metadata_status == "Ready"
                else movie.metadata_status
            )
            badges.setForeground(QColor("#5db7ff"))
            badges.setToolTip(
                movie.video_text + "\n" + movie.audio_text
            )
            self.table.setItem(row, 3, badges)

            self.table.setItem(
                row,
                4,
                QTableWidgetItem(movie.runtime_text),
            )
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(human_size(movie.size)),
            )

            target = QComboBox()
            choices = [3, 5, 10, 15, 20]
            if movie.target_gib not in choices:
                choices.append(movie.target_gib)
                choices.sort()
            target.addItems(
                [f"{value} GB" for value in choices]
            )
            target.setCurrentText(f"{movie.target_gib} GB")
            target.currentTextChanged.connect(
                lambda value, m=movie, r=row:
                self.change_target(m, r, value)
            )
            self.table.setCellWidget(row, 6, target)

            saving = QTableWidgetItem(
                human_size(movie.saving)
            )
            saving.setForeground(QColor("#70df7b"))
            self.table.setItem(row, 7, saving)

            percent = QTableWidgetItem(
                f"{movie.saving_percent}%"
            )
            percent.setForeground(
                QColor(
                    "#70df7b"
                    if movie.saving_percent >= 60
                    else "#ffbd59"
                )
            )
            self.table.setItem(row, 8, percent)

            label, _detail = movie.recommendation
            if movie.duplicate_count > 1:
                status_text = (
                    f"Possible duplicate Ã—{movie.duplicate_count}"
                )
                status_color = "#ffbd59"
            elif movie.status != "Ready":
                status_text = movie.status
                status_color = "#b4a9ba"
            elif movie.queued:
                status_text = "Queued"
                status_color = "#d45aff"
            else:
                status_text = label
                status_color = movie.score_colour

            status = QTableWidgetItem(status_text)
            status.setForeground(QColor(status_color))
            status.setToolTip(
                "\n".join(movie.recommendation_reasons)
            )
            risk = QTableWidgetItem(movie.visual_risk)
            risk.setForeground(
                QColor(
                    "#ffbd59"
                    if movie.visual_risk == "MEDIUM"
                    else "#70df7b"
                )
            )
            self.table.setItem(row, 9, risk)
            self.table.setItem(row, 10, status)

        self.table.blockSignals(False)
        if self.table.rowCount():
            self.table.selectRow(0)

    def selected_movie(self):
        row=self.table.currentRow(); item=self.table.item(row,1) if row>=0 else None; return item.data(Qt.ItemDataRole.UserRole) if item else None

    def table_item_changed(self,item):
        if item.column()!=0:return
        movie=item.data(Qt.ItemDataRole.UserRole)
        if movie:
            movie.selected=item.checkState()==Qt.CheckState.Checked

    def checked_movies(self):
        return [movie for movie in self.movies if movie.selected]

    def is_already_efficient(self, movie):
        return movie.optimization_score < 40

    def set_visible_checked(self,checked):
        skipped = 0
        exclude_efficient = (
            checked
            and hasattr(self, "exclude_efficient_btn")
            and self.exclude_efficient_btn.isChecked()
        )
        for movie in self.visible_movies:
            if exclude_efficient and self.is_already_efficient(movie):
                movie.selected = False
                skipped += 1
            else:
                movie.selected=checked
        self.populate_table()
        count=len([movie for movie in self.visible_movies if movie.selected])
        message = f"{count} visible movie(s) checked."
        if skipped:
            message += f" Excluded {skipped} already-efficient movie(s)."
        self.status.setText(message)

    def update_exclude_efficient_button(self, enabled: bool):
        self.exclude_efficient_btn.setText(
            "â˜‘ EXCLUDE ALREADY EFFICIENT"
            if enabled
            else "â˜ INCLUDE ALREADY EFFICIENT"
        )
        deselected = 0
        if enabled:
            # Hidden titles must not remain silently checked and later be
            # actioned by a bulk/queue command while they are invisible.
            for movie in self.movies:
                if movie.selected and self.is_already_efficient(movie):
                    movie.selected = False
                    deselected += 1

        # Rebuild visible_movies from the full scan. This makes the toggle a
        # true live filter: ON hides efficient movies, OFF restores them.
        self.apply_filter()
        self.update_stats()
        hidden = sum(1 for movie in self.movies if self.is_already_efficient(movie))
        if enabled:
            message = f"Hidden {hidden} already-efficient movie(s) from the scanned list."
            if deselected:
                message += f" Unchecked {deselected} hidden movie(s)."
        else:
            message = f"Showing all scanned movies, including {hidden} already-efficient movie(s)."
        self.status.setText(message)

    def apply_bulk_target(self):
        checked=self.checked_movies()
        if not checked:
            QMessageBox.information(self,APP_NAME,"Tick the boxes beside the movies first.")
            return
        eligible = checked
        skipped = []
        if self.exclude_efficient_btn.isChecked():
            eligible = [
                movie for movie in checked
                if not self.is_already_efficient(movie)
            ]
            skipped = [
                movie for movie in checked
                if self.is_already_efficient(movie)
            ]
        if not eligible:
            self.status.setText(
                f"No target sizes changed â€” {len(skipped)} checked movie(s) are already efficient and were excluded."
            )
            return
        size=int(self.bulk_target.currentText().split()[0])
        for movie in eligible:
            movie.target_gib=size
        self.populate_table(); self.update_stats()
        message = f"Applied a {size} GiB target to {len(eligible)} checked movie(s)."
        if skipped:
            message += f" Skipped {len(skipped)} already-efficient movie(s)."
        self.status.setText(message)

    def add_checked_to_queue(self):
        checked=self.checked_movies()
        if not checked:
            QMessageBox.information(self,APP_NAME,"Tick the boxes beside the movies first.")
            return
        eligible = checked
        skipped = []
        if self.exclude_efficient_btn.isChecked():
            eligible = [
                movie for movie in checked
                if not self.is_already_efficient(movie)
            ]
            skipped = [
                movie for movie in checked
                if self.is_already_efficient(movie)
            ]
        for movie in skipped:
            movie.selected = False
        if not eligible:
            self.apply_filter(); self.update_stats()
            self.status.setText(
                f"Nothing added â€” excluded {len(skipped)} already-efficient movie(s)."
            )
            return
        for movie in eligible:
            movie.queued=True
            movie.selected=False
        self.apply_filter(); self.update_stats()
        message = f"Added {len(eligible)} movie(s) to the queue."
        if skipped:
            message += f" Excluded {len(skipped)} already-efficient movie(s)."
        self.status.setText(message)

    def remove_checked_from_queue(self):
        checked=self.checked_movies()
        if not checked:
            QMessageBox.information(self,APP_NAME,"Tick the boxes beside the movies first.")
            return
        for movie in checked:
            movie.queued=False
            movie.selected=False
        self.apply_filter(); self.update_stats()
        self.status.setText(f"Removed {len(checked)} movie(s) from the queue.")

    def refresh_selected_poster(self):
        movie = self.selected_movie()
        if not movie:
            return

        self.status.setText(
            f"Refreshing Jellyfin poster for {movie.title}..."
        )
        QApplication.processEvents()

        poster_path, detail = jellyfin_poster_path(
            movie,
            self.config,
            force_refresh=True,
        )

        self.poster.clear()

        if poster_path:
            pixmap = QPixmap(str(poster_path))
            if not pixmap.isNull():
                target_size = QSize(
                    max(160, self.poster.width() - 10),
                    max(220, self.poster.height() - 10),
                )
                self.poster.setPixmap(
                    pixmap.scaled(
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.status.setText(detail)
                return

        self.poster.setText("NO\nPOSTER")
        self.status.setText(detail)

        ok, connection_detail = test_jellyfin(self.config)
        if not ok:
            QMessageBox.warning(
                self,
                "Jellyfin poster",
                "The poster could not be loaded.\n\n"
                f"Connection test: {connection_detail}\n\n"
                f"Poster lookup: {detail}",
            )
        else:
            QMessageBox.information(
                self,
                "Jellyfin poster",
                "Jellyfin is connected, but the poster lookup did not "
                "complete.\n\n"
                f"{detail}",
            )

    def clear_poster_cache(self):
        removed = 0
        for file in POSTER_CACHE.glob("*"):
            if file.is_file():
                try:
                    file.unlink()
                    removed += 1
                except OSError:
                    pass

        self.poster.clear()
        self.poster.setText("NO\nPOSTER")
        self.status.setText(
            f"Cleared {removed} cached poster(s). "
            "Select a movie to download its poster again."
        )

    def update_inspector(self):
        movie=self.selected_movie()
        if not movie:return
        self.detail_title.setText(movie.title.upper())
        self.detail_path.setText(str(movie.path))
        self.size_summary.setText(f"CURRENT {human_size(movie.size)} â†’ TARGET {movie.target_gib} GB")
        self.saving_summary.setText(f"SAVING {human_size(movie.saving)} ({movie.saving_percent}%)")
        label, reason = movie.recommendation
        self.recommendation.setText(
            f"{movie.optimization_score}/100  {label}\n"
            f"{movie.health_stars}  â€¢  VISUAL RISK: {movie.visual_risk}"
        )

        bitrate_mbps = movie.bitrate_mbps
        metadata_lines = [
            f"VIDEO: {movie.video_text}",
            f"PROFILE: {movie.video_profile or 'Unknown'}",
            f"RUNTIME: {movie.runtime_text}",
            f"AUDIO: {movie.audio_text}",
            f"SUBTITLES: {movie.subtitle_count}",
            (
                f"BITRATE: {bitrate_mbps:.1f} Mb/s"
                if bitrate_mbps
                else "BITRATE: Unknown"
            ),
        ]
        self.media_summary.setText(
            "\n".join(metadata_lines)
            if movie.metadata_status == "Ready"
            else f"MEDIA ANALYSIS: {movie.metadata_status}"
        )

        self.badge_summary.setText(
            movie.badges_text
            if movie.metadata_status == "Ready"
            else "BADGES UNAVAILABLE"
        )
        breakdown_lines = [
            f"{name}: {value:+d}"
            for name, value
            in movie.optimization_breakdown.items()
        ]
        self.reason_summary.setText(
            "OPTIMIZATION SCORE BREAKDOWN\n\n"
            + "\n".join(breakdown_lines)
            + "\n\nWHY EMO SCORED IT THIS WAY\n"
            + "\n".join(
                f"â€¢ {item}"
                for item in movie.recommendation_reasons
            )
        )

        if movie.duplicate_count > 1:
            self.duplicate_warning.setText(
                f"âš  POSSIBLE DUPLICATE: "
                f"{movie.duplicate_count} matching titles were found. "
                "Use the Duplicates button to review them. "
                "Nothing will be deleted automatically."
            )
            self.duplicate_warning.setVisible(True)
        else:
            self.duplicate_warning.setVisible(False)
        self.queue_selected_btn.setText("âœ• REMOVE FROM QUEUE" if movie.queued else "â–¶ ADD TO QUEUE")
        local_poster = movie.poster_path()
        poster_detail = ""
        if local_poster:
            poster_path = local_poster
            poster_detail = "Loaded poster from the movie folder."
        else:
            poster_path, poster_detail = jellyfin_poster_path(
                movie,
                self.config,
            )
        self.poster.clear()
        if poster_path:
            pixmap = QPixmap(str(poster_path))
            if not pixmap.isNull():
                target_size = QSize(
                    max(160, self.poster.width() - 10),
                    max(220, self.poster.height() - 10),
                )
                self.poster.setPixmap(
                    pixmap.scaled(
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.poster.setText("NO\nPOSTER")
        else:
            self.poster.setText("NO\nPOSTER")
        if poster_detail:
            self.status.setText(poster_detail)
    def change_target(self,movie,row,value):
        movie.target_gib=int(value.split()[0])
        self.apply_filter()
        self.update_stats()
        self.update_inspector()
    def set_selected_target(self,size):
        movie=self.selected_movie()
        if not movie:return
        movie.target_gib=size; self.populate_table();
        for row,candidate in enumerate(self.visible_movies):
            if candidate is movie:self.table.selectRow(row);break
        self.update_stats()
    def toggle_selected_queue(self):
        movie=self.selected_movie()
        if not movie:return
        movie.queued=not movie.queued; self.apply_filter(); self.update_stats()
    def update_stats(self):
        self.queue=[m for m in self.movies if m.queued]
        self.optimized_card.value.setText(str(len(self.queue)))
        self.saving_card.value.setText(
            human_size(sum(m.saving for m in self.queue))
        )
        self.operations.update_library(
            self.movies,
            self.queue,
        )
    def start_queue(self):
        self.update_stats()
        if not self.queue:
            QMessageBox.information(
                self,
                APP_NAME,
                "Add at least one movie to the queue first.",
            )
            return

        answer = QMessageBox.warning(
            self,
            APP_NAME,
            "Queued movies will be encoded and safely replace their "
            "originals after verification. Start now?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Snapshot the queue for this run.  Do not rebuild the active run from
        # checkbox flags after each movie; UI refreshes can legitimately change
        # those flags and previously caused a multi-item run to stop after #1.
        self.pending_queue = list(self.queue)
        self.queue_running = True
        self.start_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.process_next()
    def process_next(self):
        if not self.queue_running:
            return
        if self.queue_advance_timer.isActive():
            self.queue_advance_timer.stop()
        if not self.pending_queue:
            self.queue_running = False
            self.start_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.status.setText("Process complete")
            self.operations.set_process_status("Process complete")
            self.progress.setValue(100)
            if self.config.get("show_live_telemetry", True):
                self.telemetry.begin_stage("complete")
            QMessageBox.information(
                self,
                APP_NAME,
                "The optimization process has finished.",
            )
            self.perform_queue_finish_action()
            return
        movie=self.pending_queue.pop(0)
        self.current_movie=movie
        self.current_started_at = time.monotonic()
        movie.status="Working"
        movie.queued=False
        self.update_stats()
        self.populate_table()
        self.status.setText(f"Starting {movie.title}...")
        self.operations.set_process_status(
            f"Processing {movie.title}"
        )
        self.telemetry.set_current_job(
            movie.title,
            len(self.pending_queue),
        )
        self.progress.setValue(0)
        # Retain the worker until it has emitted finished/failed.  A local-only
        # QRunnable reference is unsafe when the thread pool must queue the next
        # job instead of starting it immediately.
        worker=EncodeWorker(movie,self.config)
        self.active_encode_worker = worker
        worker.signals.progress.connect(self.progress_update)
        worker.signals.message.connect(self.status.setText)
        worker.signals.stage.connect(self.process_stage_changed)
        worker.signals.finished.connect(
            lambda path,m=movie:self.encode_done(m,path)
        )
        worker.signals.failed.connect(
            lambda msg,m=movie:self.encode_failed(m,msg)
        )
        log(
            f"QUEUE START: {movie.title} | "
            f"{len(self.pending_queue)} pending after this item"
        )
        self.pool.start(worker)
    def process_stage_changed(self, stage):
        if self.config.get("show_live_telemetry", True):
            self.telemetry.begin_stage(stage)

    def progress_update(self,percent,message):
        self.progress.setValue(percent)
        self.status.setText(message)

    def encode_done(self, movie, path):
        movie.status = "Done"
        elapsed = max(
            0,
            time.monotonic() - self.current_started_at,
        )
        try:
            new_size = Path(path).stat().st_size
        except OSError:
            new_size = 0

        saved = max(0, movie.size - new_size)
        elapsed_text = format_runtime(elapsed)
        remaining = len(self.pending_queue)

        self.status.setText(
            f"Completed: {movie.title} â€” "
            f"saved {human_size(saved)} in {elapsed_text}"
        )
        self.operations.set_process_status(
            f"Complete: {movie.title} â€¢ "
            f"saved {human_size(saved)} â€¢ "
            f"{remaining} remaining"
        )
        self.populate_table()

        if self.exit_after_current:
            self.exit_after_current = False
            self.queue_running = False
            self.current_movie = None
            self.telemetry.stop_and_hide()
            self.start_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.status.setText(
                f"Completed {movie.title}. EMP will now close as requested."
            )
            self.operations.set_process_status(
                "Current movie complete â€” exiting"
            )
            if self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    APP_NAME,
                    "Current movie finished. EMP is closing.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )
            QTimer.singleShot(500, QApplication.instance().quit)
            return
        if self.pause_after_current:
            self.pause_after_current = False
            self.queue_running = False
            self.start_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.telemetry.stop_and_hide()
            self.status.setText(
                f"Paused after {movie.title}. "
                f"{remaining} movie(s) remain queued."
            )
            QMessageBox.information(
                self,
                "Queue paused safely",
                f"{movie.title} completed successfully.\n\n"
                f"Saved: {human_size(saved)}\n"
                f"Elapsed: {elapsed_text}\n"
                f"Remaining: {remaining}\n\n"
                "Press Start Process when you are ready to continue.",
            )
            return

        # Release our Python reference to the completed worker, then hand the
        # queue back to the GUI event loop before starting the next one.  This
        # avoids launching/replacing a QRunnable from inside its completion
        # callback and guarantees the next worker remains strongly referenced.
        self.active_encode_worker = None
        log(
            f"QUEUE DONE: {movie.title} | {remaining} item(s) pending | "
            f"running={self.queue_running}"
        )
        if remaining > 0 and self.queue_running:
            self.status.setText(
                f"Completed: {movie.title} â€” starting next queue item..."
            )
            QTimer.singleShot(250, self.process_next)
        else:
            QTimer.singleShot(0, self.process_next)
    def encode_failed(self,movie,message):
        movie.status="Failed"
        self.active_encode_worker = None
        self.queue_running = False
        self.pending_queue = []
        if self.queue_advance_timer.isActive():
            self.queue_advance_timer.stop()
        self.telemetry.stop_and_hide()
        self.start_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.populate_table()
        self.failed(message)
    def failed(self,message): self.scan_btn.setEnabled(True); self.progress.setRange(0,100); self.status.setText("Stopped safely"); QMessageBox.critical(self,APP_NAME,message+"\n\nThe original NAS movie was not intentionally deleted. Local work files were retained where useful.")
    def perform_queue_finish_action(self):
        action = self.config.get(
            "queue_finish_action",
            "Do nothing",
        )
        if action == "Do nothing":
            return

        confirmation = QMessageBox.question(
            self,
            "Process finish action",
            f"The process is complete. Perform this action now?\n\n"
            f"{action}",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        commands = {
            "Shut down": ["shutdown", "/s", "/t", "30"],
            "Restart": ["shutdown", "/r", "/t", "30"],
            "Hibernate": ["shutdown", "/h"],
            "Sleep": [
                "rundll32.exe",
                "powrprof.dll,SetSuspendState",
                "0,1,0",
            ],
        }

        command = commands.get(action)
        if command:
            subprocess.Popen(
                command,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

    def show_dashboard(self):
        self.operations.refresh_services()
        self.operations.update_library(
            self.movies,
            [movie for movie in self.movies if movie.queued],
        )
        self.operations.setFocus()
        self.status.setText("Operations Center refreshed.")

    def focus_movies(self):
        self.table.setFocus()
        if self.table.rowCount():
            self.table.selectRow(max(0, self.table.currentRow()))
        self.status.setText("Movie library view active.")

    def set_update_light(self, text: str, color: str, tip: str = ""):
        self.update_button.setText(text)
        self.update_button.setToolTip(tip)
        self.update_button.setStyleSheet(
            f"color:{color};font-weight:800;border-color:{color};"
        )

    def check_for_updates(self):
        repo = str(self.config.get("github_repo", "")).strip() or DEFAULT_CONFIG["github_repo"]
        self.config["github_repo"] = repo
        self.latest_release = {"checking": True, "repo": repo}
        self.update_checked_at = "Checking now..."
        self.set_update_light(
            "â—  CHECKING GITHUB...",
            "#ffbd59",
            f"Checking {repo} for the latest EMP build...",
        )
        worker = GitHubUpdateWorker(repo)
        worker.signals.done.connect(self.on_update_checked)
        self.pool.start(worker)

    def on_update_checked(self, result: dict):
        self.latest_release = result
        self.update_checked_at = time.strftime("%Y-%m-%d %H:%M:%S")
        if not result.get("ok"):
            self.set_update_light(
                "â—  UPDATE CHECK FAILED",
                "#ff6879",
                f"{result.get('error', 'Update check failed')}\nLast checked: {self.update_checked_at}\nClick for details or to retry.",
            )
        elif result.get("newer"):
            source = "GitHub Release" if result.get("source") == "release" else f"Git {result.get('branch','main')} branch"
            self.set_update_light(
                f"â—  UPDATE {result.get('version','')} AVAILABLE",
                "#d35cff",
                f"Installed: {APP_VERSION}\nLatest: {result.get('version','?')}\nSource: {source}\nLast checked: {self.update_checked_at}\nClick to install.",
            )
        else:
            source = "GitHub Release" if result.get("source") == "release" else f"Git {result.get('branch', 'main')} branch"
            self.set_update_light(
                "â—  UP TO DATE",
                "#70df7b",
                f"Installed: {APP_VERSION}\nLatest: {result.get('version', APP_VERSION)}\nRepository: {result.get('repo', DEFAULT_CONFIG['github_repo'])}\nSource: {source}\nLast checked: {self.update_checked_at}\nClick for details or to re-check.",
            )

    def install_github_update(self, result: dict):
        try:
            updates_dir = APP_DIR / "_updates"
            updates_dir.mkdir(exist_ok=True)
            target = updates_dir / (result.get("asset_name") or "EMP-update.zip")
            self.set_update_light(
                f"â—  DOWNLOADING {result.get('version','UPDATE')}...",
                "#5db7ff",
                "Downloading the selected EMP update from GitHub.",
            )
            QApplication.processEvents()
            req = urllib.request.Request(
                result["download_url"],
                headers={"User-Agent": "EMP-Updater"},
            )
            with urllib.request.urlopen(req, timeout=60) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            new_version = launch_external_update(
                target,
                APP_DIR,
                current_version=APP_VERSION,
                current_pid=os.getpid(),
            )
            QMessageBox.information(
                self,
                "EMP update ready",
                f"EMP {new_version} has been downloaded and validated.\n\n"
                "EMP will now close, install the update, and reopen.",
            )
            QTimer.singleShot(250, QApplication.instance().quit)
        except Exception as exc:
            self.set_update_light(
                "â—  UPDATE FAILED",
                "#ff6879",
                f"{exc}\nClick for details or to retry.",
            )
            QMessageBox.critical(self, "EMP update failed", str(exc))

    def update_button_clicked(self):
        result = self.latest_release or {}
        if result.get("checking"):
            QMessageBox.information(
                self,
                "EMP update check",
                "EMP is currently checking GitHub for updates.",
            )
            return

        repo = str(self.config.get("github_repo", "")).strip() or DEFAULT_CONFIG["github_repo"]
        current = APP_VERSION
        latest = result.get("version") or "Unknown"
        source = (
            "GitHub Release"
            if result.get("source") == "release"
            else f"Git {result.get('branch', 'main')} branch"
        )

        box = QMessageBox(self)
        box.setWindowTitle("EMP Update Status")
        box.setIcon(
            QMessageBox.Icon.Information
            if result.get("ok")
            else QMessageBox.Icon.Warning
        )
        if result.get("ok") and result.get("newer"):
            box.setText(f"EMP {latest} is available")
            box.setInformativeText(
                f"Installed version: {current}\n"
                f"Latest version: {latest}\n"
                f"Repository: {repo}\n"
                f"Source: {source}\n"
                f"Last checked: {self.update_checked_at}"
            )
            install_btn = box.addButton("Install Update", QMessageBox.ButtonRole.AcceptRole)
        elif result.get("ok"):
            box.setText("EMP is up to date")
            box.setInformativeText(
                f"Installed version: {current}\n"
                f"Latest version: {latest}\n"
                f"Repository: {repo}\n"
                f"Source: {source}\n"
                f"Last checked: {self.update_checked_at}"
            )
            install_btn = None
        else:
            box.setText("EMP could not check for updates")
            box.setInformativeText(
                f"Repository: {repo}\n"
                f"Last checked: {self.update_checked_at}\n\n"
                f"{result.get('error', 'No update information is available yet.')}"
            )
            install_btn = None

        check_btn = box.addButton("Check Again", QMessageBox.ButtonRole.ActionRole)
        repo_btn = box.addButton("Open GitHub", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()

        clicked = box.clickedButton()
        if install_btn is not None and clicked is install_btn:
            if result.get("download_url"):
                self.install_github_update(result)
            else:
                QMessageBox.warning(
                    self,
                    "EMP update",
                    "The GitHub release does not contain a downloadable EMP ZIP yet.",
                )
        elif clicked is check_btn:
            self.check_for_updates()
        elif clicked is repo_btn:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{repo}"))

    def show_update_center(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def show_queue_manager(self):
        queued = [
            movie
            for movie in self.movies
            if movie.queued
        ]
        if not queued:
            QMessageBox.information(
                self,
                APP_NAME,
                "The queue is empty. Add checked movies first.",
            )
            return

        dialog = QueueManagerDialog(
            queued,
            self.pause_after_current,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ordered = dialog.ordered_movies()
            self.pause_after_current = (
                dialog.pause_after_current()
            )

            for movie in self.movies:
                movie.queued = False
            for movie in ordered:
                movie.queued = True

            order_map = {
                id(movie): index
                for index, movie in enumerate(ordered)
            }
            self.movies.sort(
                key=lambda movie: (
                    (0, order_map[id(movie)])
                    if id(movie) in order_map
                    else (1, -movie.size)
                )
            )

            self.apply_filter()
            self.update_stats()

            pause_text = (
                " Pause after current is enabled."
                if self.pause_after_current
                else ""
            )
            self.status.setText(
                f"Queue saved with {len(ordered)} movie(s)."
                f"{pause_text}"
            )

    def show_health(self):
        HealthDialog(self.config,self).exec()

    def show_settings(self):
        dialog=SettingsDialog(self.config,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.config=dialog.values()
            save_config(self.config)
            self.operations.config=self.config
            self.apply_style()
            self.operations.refresh_services()
            self.status.setText(
                f"Settings saved. Theme: {self.config.get('theme', 'Skull Purple')}; "
                f"banner: {self.config.get('banner_theme', 'Original Purple')}; "
                f"text size: {self.config.get('ui_scale_percent', 100)}%."
            )
    def show_help(self): HelpDialog(self).exec()
    def show_about(self):
        QMessageBox.about(
            self,
            APP_NAME,
            f"<h2>Evil's Media Encoding Platform {APP_VERSION}</h2><p><b>Powered by EMO</b></p>"
            "<p>A media optimization dashboard with automatic Jellyfin "
            "poster caching, queue management, hidden-console launching, "
            "a modular media optimizer with safe HandBrake/NVENC encoding, Jellyfin posters, live telemetry and a resilient external updater.</p>"
            "<p>Open <b>Settings â†’ Updates</b> to install future fixes "
            "without losing your settings or cache.</p>"
            "<p>Built for Jason's VaultOne media workflow.</p>",
        )
    def show_tools(self): self.show_health()
    def show_jellyfin_info(self):
        ok, detail = test_jellyfin(self.config)
        QMessageBox.information(
            self,
            "Jellyfin",
            ("âœ“ " if ok else "âœ• ")
            + detail
            + "\n\nPosters use this Jellyfin connection. "
            "Configure it under Settings â†’ Integrations.",
        )
    def show_history(self):
        if not HISTORY_FILE.exists(): QMessageBox.information(self,"History","No completed encodes have been recorded yet."); return
        try: rows=json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception: rows=[]
        text='\n'.join(f"{r.get('completed','')} â€” {r.get('movie','')} â€” saved {human_size(max(0,r.get('original',0)-r.get('new',0)))}" for r in rows[-30:]) or 'No history.'; QMessageBox.information(self,"Recent history",text)
    def show_statistics(self):
        if not HISTORY_FILE.exists(): QMessageBox.information(self,"Statistics","No completed encodes yet."); return
        try: rows=json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception: rows=[]
        saved=sum(max(0,r.get('original',0)-r.get('new',0)) for r in rows); QMessageBox.information(self,"Statistics",f"Movies processed: {len(rows)}\nTotal space saved: {human_size(saved)}")



def install_exception_handler() -> None:
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(
                exc_type,
                exc_value,
                exc_traceback,
            )
            return

        details = "".join(
            traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback,
            )
        )
        log("UNHANDLED ERROR\n" + details)

        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                f"{APP_NAME} â€” Error",
                "Something went wrong. The error has been saved to:\n\n"
                f"{LOG_FILE}\n\n"
                f"{exc_value}",
            )

    sys.excepthook = handle_exception

def main():
    install_exception_handler()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    config = load_config()
    force_platform_builder = "--platform-builder" in sys.argv or "--setup" in sys.argv
    if force_platform_builder or not bool(config.get("setup_complete", False)):
        wizard = PlatformSetupWizard(config, first_run=True)
        wizard.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        wizard.show()
        wizard.raise_()
        wizard.activateWindow()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return 0
        save_config(wizard.values())
    window = MainWindow()
    window.show()
    return app.exec()
if __name__=='__main__': raise SystemExit(main())

