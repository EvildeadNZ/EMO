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
from collections import deque
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

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, QSize, QTimer, QRectF
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter, QStackedLayout,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget, QListWidget, QScrollArea,
    QListWidgetItem, QTabWidget, QGroupBox, QAbstractItemView,
)

APP_NAME = "Evil's Media Optimizer"
APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = APP_DIR / "config.json"
HISTORY_FILE = APP_DIR / "history.json"
LOG_FILE = APP_DIR / "evils_media_optimizer.log"
POSTER_CACHE = APP_DIR / "cache" / "posters"
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
    "update_manifest_url": "",
    "queue_finish_action": "Do nothing",
    "show_live_telemetry": True,
}
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".m2ts", ".webm"}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


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


@dataclass
class Movie:
    path: Path
    size: int
    target_gib: int = 5
    queued: bool = False
    selected: bool = False
    status: str = "Ready"

    @property
    def title(self) -> str:
        return self.path.parent.name

    @property
    def saving(self) -> int:
        return max(0, self.size - int(self.target_gib * 1024**3))

    @property
    def saving_percent(self) -> int:
        return int(self.saving / self.size * 100) if self.size else 0

    def poster_path(self) -> Path | None:
        candidates = (
            "poster.jpg", "poster.png", "folder.jpg", "folder.png",
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
                    and candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
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
        result = subprocess.run([
            self.config["ffprobe"], "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(source)
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffprobe could not read the movie duration.")
        value = float(result.stdout.strip())
        if value <= 0:
            raise RuntimeError("Invalid movie duration.")
        return value

    def run_handbrake(self, command: list[str]) -> None:
        log("Running: " + subprocess.list2cmdline(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", bufsize=1)
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip()
            log(line)
            if "Encoding:" in line and "%" in line:
                try:
                    percent = float(line.split("%", 1)[0].rsplit(",", 1)[1].strip())
                    eta = line.split("ETA ", 1)[1].rstrip(")") if "ETA " in line else "calculating"
                    self.signals.progress.emit(int(percent), f"Encoding {percent:.1f}% — ETA {eta}")
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
                self.copy_with_progress(source, local_source, "NAS → PC")
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
            self.copy_with_progress(local_output, partial, "PC → NAS")
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
        if self.unit == "°C":
            return f"{self.current_value:.0f}°C"
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
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.sample)

        self.previous_network = None
        self.previous_time = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 9)
        layout.setSpacing(6)

        heading_row = QHBoxLayout()
        self.heading = QLabel("LIVE PROCESS TELEMETRY")
        self.heading.setObjectName("telemetryHeading")
        heading_row.addWidget(self.heading)

        self.current_job = QLabel("No active movie")
        self.current_job.setObjectName("telemetryJob")
        heading_row.addWidget(self.current_job, 1)

        self.stage_label = QLabel("IDLE")
        self.stage_label.setObjectName("telemetryStage")
        heading_row.addWidget(self.stage_label)
        layout.addLayout(heading_row)

        graph_row = QHBoxLayout()
        graph_row.setSpacing(7)

        self.gpu_graph = SparklineWidget(
            "GPU USAGE",
            "%",
            maximum=100,
        )
        self.temperature_graph = SparklineWidget(
            "GPU TEMP",
            "°C",
            maximum=100,
        )
        self.vram_graph = SparklineWidget(
            "VRAM USED",
            "GB",
        )
        self.network_down_graph = SparklineWidget(
            "NAS DOWNLOAD",
            "MB/s",
        )
        self.network_up_graph = SparklineWidget(
            "NAS UPLOAD",
            "MB/s",
        )

        graph_row.addWidget(self.gpu_graph, 1)
        graph_row.addWidget(self.temperature_graph, 1)
        graph_row.addWidget(self.vram_graph, 1)
        graph_row.addWidget(self.network_down_graph, 1)
        graph_row.addWidget(self.network_up_graph, 1)
        layout.addLayout(graph_row)

    def set_current_job(
        self,
        movie_title: str,
        remaining: int,
    ):
        self.current_job.setText(
            f"{movie_title}  •  {remaining} remaining"
        )

    def begin_stage(self, stage: str):
        self.stage_name = stage
        labels = {
            "download": "NAS → PC",
            "encoding": "NVENC ENCODING",
            "upload": "PC → NAS",
            "verifying": "VERIFYING",
            "complete": "COMPLETE",
        }
        self.stage_label.setText(
            labels.get(stage, stage.upper())
        )

        if stage in {
            "download",
            "encoding",
            "upload",
            "verifying",
        }:
            self.setVisible(True)
            if not self.timer.isActive():
                self.reset_network_baseline()
                self.timer.start()
            self.sample()
        elif stage == "complete":
            self.setVisible(True)
            QTimer.singleShot(2500, self.stop_and_hide)

    def reset_network_baseline(self):
        self.previous_time = time.monotonic()
        if psutil is not None:
            self.previous_network = psutil.net_io_counters()
        else:
            self.previous_network = None

    def nvidia_metrics(self) -> tuple[float, float, float]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,temperature.gpu,memory.used",
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
            if result.returncode != 0:
                return 0.0, 0.0, 0.0

            first_line = result.stdout.strip().splitlines()[0]
            usage, temperature, memory_mib = [
                float(part.strip())
                for part in first_line.split(",")[:3]
            ]
            return usage, temperature, memory_mib / 1024
        except Exception:
            return 0.0, 0.0, 0.0

    def network_metrics(self) -> tuple[float, float]:
        if psutil is None:
            return 0.0, 0.0

        current_time = time.monotonic()
        current = psutil.net_io_counters()

        if self.previous_network is None or self.previous_time is None:
            self.previous_network = current
            self.previous_time = current_time
            return 0.0, 0.0

        elapsed = max(0.1, current_time - self.previous_time)

        download = (
            current.bytes_recv - self.previous_network.bytes_recv
        ) / elapsed / (1024 * 1024)
        upload = (
            current.bytes_sent - self.previous_network.bytes_sent
        ) / elapsed / (1024 * 1024)

        self.previous_network = current
        self.previous_time = current_time

        return max(0.0, download), max(0.0, upload)

    def sample(self):
        gpu, temperature, vram = self.nvidia_metrics()
        download, upload = self.network_metrics()

        self.gpu_graph.set_value(gpu)
        self.temperature_graph.set_value(temperature)
        self.vram_graph.set_value(vram)
        self.network_down_graph.set_value(download)
        self.network_up_graph.set_value(upload)

    def stop_and_hide(self):
        self.timer.stop()
        self.setVisible(False)
        self.stage_name = "idle"
        self.stage_label.setText("IDLE")
        self.current_job.setText("No active movie")
        for graph in (
            self.gpu_graph,
            self.temperature_graph,
            self.vram_graph,
            self.network_down_graph,
            self.network_up_graph,
        ):
            graph.clear_values()



class OperationsMetric(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "—",
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
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(9)

        heading_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("OPERATIONS CENTER")
        title.setObjectName("operationsTitle")
        subtitle = QLabel(
            "VaultOne media optimization status at a glance"
        )
        subtitle.setObjectName("operationsSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading_row.addLayout(title_box)
        heading_row.addStretch()

        self.last_refresh = QLabel("Not checked yet")
        self.last_refresh.setObjectName("operationsRefresh")
        heading_row.addWidget(self.last_refresh)

        refresh_button = QPushButton("↻ REFRESH")
        refresh_button.clicked.connect(self.refresh_services)
        heading_row.addWidget(refresh_button)
        outer.addLayout(heading_row)

        metrics = QGridLayout()
        metrics.setSpacing(8)

        self.nas_metric = OperationsMetric("NAS", "Checking…")
        self.jellyfin_metric = OperationsMetric(
            "JELLYFIN",
            "Checking…",
        )
        self.gpu_metric = OperationsMetric("GPU", "Checking…")
        self.handbrake_metric = OperationsMetric(
            "HANDBRAKE",
            "Checking…",
        )
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
            "—",
            "Configured movie library",
        )

        cards = (
            self.nas_metric,
            self.jellyfin_metric,
            self.gpu_metric,
            self.handbrake_metric,
            self.movies_metric,
            self.queue_metric,
            self.saving_metric,
            self.free_metric,
        )
        for index, card in enumerate(cards):
            metrics.addWidget(card, index // 4, index % 4)
        outer.addLayout(metrics)

        action_row = QHBoxLayout()
        self.current_status = QLabel("STATUS: READY")
        self.current_status.setObjectName("operationsCurrent")
        action_row.addWidget(self.current_status, 1)

        scan_button = QPushButton("☠  SCAN")
        scan_button.setObjectName("primaryButton")
        scan_button.clicked.connect(self.scan_requested.emit)
        action_row.addWidget(scan_button)

        start_button = QPushButton("▶  START PROCESS")
        start_button.setObjectName("startButton")
        start_button.clicked.connect(self.start_requested.emit)
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
        self.nas_metric.update_value(
            "ONLINE" if nas_ok else "OFFLINE",
            str(root) if root else "No library configured",
            "good" if nas_ok else "bad",
        )

        if nas_ok:
            try:
                free = shutil.disk_usage(root).free
                self.free_metric.update_value(
                    human_size(free),
                    "Available on the library volume",
                    "good" if free > 100 * 1024**3 else "warning",
                )
            except OSError as exc:
                self.free_metric.update_value(
                    "UNKNOWN",
                    str(exc),
                    "warning",
                )
        else:
            self.free_metric.update_value(
                "—",
                "NAS library is unavailable",
                "bad",
            )

        jellyfin_ok, jellyfin_detail = test_jellyfin(
            self.config
        )
        self.jellyfin_metric.update_value(
            "CONNECTED" if jellyfin_ok else "OFFLINE",
            jellyfin_detail,
            "good" if jellyfin_ok else "bad",
        )

        handbrake_path = shutil.which(
            self.config.get("handbrake", "HandBrakeCLI")
        )
        self.handbrake_metric.update_value(
            "READY" if handbrake_path else "MISSING",
            handbrake_path or "HandBrakeCLI was not found",
            "good" if handbrake_path else "bad",
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
                gpu_detail = result.stdout.strip().splitlines()[0]
        except Exception as exc:
            gpu_detail = str(exc)

        self.gpu_metric.update_value(
            "NVENC READY" if gpu_ok else "UNAVAILABLE",
            gpu_detail,
            "good" if gpu_ok else "bad",
        )
        self.last_refresh.setText(
            "Checked " + time.strftime("%H:%M:%S")
        )



class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Settings")
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

        key_row = QHBoxLayout()
        self.jellyfin_api_key = QLineEdit(
            self.config.get("jellyfin_api_key", "")
        )
        self.jellyfin_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.jellyfin_api_key.setPlaceholderText(
            "Dashboard → Advanced → API Keys"
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
            "Enter the URL and API key, then test the connection."
        )
        self.jellyfin_test_result.setWordWrap(True)
        integration_form.addRow("Status:", self.jellyfin_test_result)

        note = QLabel(
            "Posters are downloaded from Jellyfin and cached locally. "
            "The API key is stored in this app folder's config.json."
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

        self.update_manifest_url = QLineEdit(
            self.config.get("update_manifest_url", "")
        )
        self.update_manifest_url.setPlaceholderText(
            "Optional future update-manifest URL"
        )
        updates_layout.addWidget(QLabel("Automatic update source:"))
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
        appearance_layout = QVBoxLayout(appearance)
        appearance_layout.addWidget(QLabel(
            "Active theme: Skull Purple\n\n"
            "Planned themes: Diablo, Jellyfin, OLED Black, Matrix and Cyberpunk."
        ))
        appearance_layout.addStretch()
        tabs.addTab(appearance, "Appearance")

        outer.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def browse_root(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose movie library", self.root.text())
        if folder: self.root.setText(folder)

    def browse_work(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose local work folder", self.work.text())
        if folder: self.work.setText(folder)

    def test_jellyfin_connection(self):
        temporary_config = {
            **self.config,
            "jellyfin_url": self.jellyfin_url.text().strip().rstrip("/"),
            "jellyfin_api_key": self.jellyfin_api_key.text().strip(),
            "update_manifest_url": self.update_manifest_url.text().strip(),
            "queue_finish_action": self.queue_finish_action.currentText(),
            "show_live_telemetry": self.show_live_telemetry.isChecked(),
        }

        self.jellyfin_test_result.setText("Testing...")
        QApplication.processEvents()

        ok, detail = test_jellyfin(temporary_config)
        self.jellyfin_test_result.setText(
            ("✓ " if ok else "✕ ") + detail
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
        }


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Help")
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
    def __init__(self, movies: list[Movie], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Queue Manager")
        self.resize(850, 610)
        self.movies = movies
        layout = QVBoxLayout(self)
        intro = QLabel("Drag items to reorder the queue. Use the buttons to fine-tune or remove titles.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.list, 1)

        controls = QHBoxLayout()
        up = QPushButton("↑ Move Up"); up.clicked.connect(lambda: self.move_selected(-1)); controls.addWidget(up)
        down = QPushButton("↓ Move Down"); down.clicked.connect(lambda: self.move_selected(1)); controls.addWidget(down)
        remove = QPushButton("✕ Remove"); remove.clicked.connect(self.remove_selected); controls.addWidget(remove)
        controls.addStretch()
        close = QPushButton("Save Queue Order"); close.setObjectName("primaryButton"); close.clicked.connect(self.accept); controls.addWidget(close)
        layout.addLayout(controls)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for movie in self.movies:
            item = QListWidgetItem(
                f"{movie.title}    {human_size(movie.size)}  →  {movie.target_gib} GiB    "
                f"save {human_size(movie.saving)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, movie)
            self.list.addItem(item)

    def move_selected(self, direction: int):
        row = self.list.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.list.count():
            return
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)

    def remove_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)

    def ordered_movies(self) -> list[Movie]:
        return [
            self.list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list.count())
        ]


class HealthDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — System Health")
        self.resize(650, 500)
        layout = QVBoxLayout(self)
        heading = QLabel("💀 EVIL'S SYSTEM STATUS")
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
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=15, check=False,
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
            item = QListWidgetItem(f"{'🟢' if ok else '🔴'}  {label}\n      {detail}")
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
    def __init__(self):
        super().__init__()
        self.config = load_config(); self.movies=[]; self.visible_movies=[]; self.queue=[]; self.pool=QThreadPool.globalInstance(); self.current_movie=None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}"); self.setWindowIcon(QIcon(str(APP_DIR/'assets'/'evils_skull.ico'))); self.resize(1660, 980); self.setMinimumSize(1320, 800)
        self.build_ui()
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

    def build_ui(self):
        central=QWidget(); page=QVBoxLayout(central); page.setContentsMargins(0,0,0,0); page.setSpacing(0)
        header_wrap=QWidget()
        header_layout=QVBoxLayout(header_wrap)
        header_layout.setContentsMargins(0,0,0,0)
        self.header=QLabel()
        self.header.setObjectName("header")
        self.header.setPixmap(QPixmap(str(APP_DIR/'assets'/'header.png')))
        self.header.setScaledContents(True)
        self.header.setFixedHeight(190)
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

        settings_button = QPushButton("⚙  SETTINGS")
        settings_button.setObjectName("quickButton")
        settings_button.clicked.connect(self.show_settings)
        quick_layout.addWidget(settings_button)

        self.update_button = QPushButton("↻  UPDATES")
        self.update_button.setObjectName("updateButton")
        self.update_button.clicked.connect(self.show_update_center)
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
        self.filter_box=QComboBox(); self.filter_box.addItems(["All movies","Queued only","Not queued"]); self.filter_box.currentTextChanged.connect(self.apply_filter); toolbar.addWidget(self.filter_box)
        self.sort_box=QComboBox(); self.sort_box.addItems(["Size: High to low","Size: Low to high","Title: A to Z"]); self.sort_box.currentTextChanged.connect(self.apply_filter); toolbar.addWidget(self.sort_box)
        queue_manager_btn=QPushButton("☷ QUEUE MANAGER"); queue_manager_btn.clicked.connect(self.show_queue_manager); toolbar.addWidget(queue_manager_btn)
        health_btn=QPushButton("♥ SYSTEM HEALTH"); health_btn.clicked.connect(self.show_health); toolbar.addWidget(health_btn)
        self.scan_btn=QPushButton("☠  SCAN"); self.scan_btn.setObjectName("primaryButton"); self.scan_btn.clicked.connect(self.scan); toolbar.addWidget(self.scan_btn); content_layout.addLayout(toolbar)
        bulk_bar=QFrame(); bulk_bar.setObjectName("bulkBar"); bulk=QHBoxLayout(bulk_bar); bulk.setContentsMargins(10,7,10,7); bulk.setSpacing(7)
        bulk.addWidget(QLabel("BULK SELECTION:"))
        select_all_btn=QPushButton("☑ SELECT ALL VISIBLE"); select_all_btn.clicked.connect(lambda:self.set_visible_checked(True)); bulk.addWidget(select_all_btn)
        clear_btn=QPushButton("☐ CLEAR CHECKS"); clear_btn.clicked.connect(lambda:self.set_visible_checked(False)); bulk.addWidget(clear_btn)
        bulk.addSpacing(10); bulk.addWidget(QLabel("TARGET:"))
        self.bulk_target=QComboBox(); self.bulk_target.addItems(["3 GB","5 GB","10 GB","15 GB","20 GB"]); self.bulk_target.setCurrentText(f"{self.config['default_target_gib']} GB"); bulk.addWidget(self.bulk_target)
        apply_bulk_btn=QPushButton("APPLY SIZE TO CHECKED"); apply_bulk_btn.clicked.connect(self.apply_bulk_target); bulk.addWidget(apply_bulk_btn)
        bulk.addStretch()
        add_checked_btn=QPushButton("▶ ADD CHECKED TO QUEUE"); add_checked_btn.setObjectName("startButton"); add_checked_btn.clicked.connect(self.add_checked_to_queue); bulk.addWidget(add_checked_btn)
        remove_checked_btn=QPushButton("✕ REMOVE CHECKED"); remove_checked_btn.clicked.connect(self.remove_checked_from_queue); bulk.addWidget(remove_checked_btn)
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
        self.status=QLabel("Ready — scan your configured library to begin"); self.status.setObjectName("statusText"); bottom_layout.addWidget(self.status,1)
        self.progress=QProgressBar(); self.progress.setFixedWidth(320); self.progress.setValue(0); bottom_layout.addWidget(self.progress)
        self.start_btn=QPushButton("▶  START PROCESS"); self.start_btn.setObjectName("startButton"); self.start_btn.clicked.connect(self.start_queue); bottom_layout.addWidget(self.start_btn); content_layout.addWidget(bottom)
        body_layout.addWidget(content,1); page.addWidget(body,1); self.setCentralWidget(central)

    def make_sidebar(self):
        side=QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(185); layout=QVBoxLayout(side); layout.setContentsMargins(8,12,8,12); layout.setSpacing(6)
        items=[("⌂","DASHBOARD",self.show_dashboard),("▣","MOVIES",self.focus_movies),("☷","QUEUE",self.show_queue_manager),("◷","HISTORY",self.show_history),("▥","STATISTICS",self.show_statistics),("△","JELLYFIN",self.show_jellyfin_info),("⚙","SETTINGS",self.show_settings),("⚒","TOOLS",self.show_tools),("●","ABOUT",self.show_about)]
        for index,(icon,text,action) in enumerate(items):
            button=QPushButton(f"{icon}   {text}"); button.setObjectName("navActive" if index==0 else "navButton"); button.setCursor(Qt.CursorShape.PointingHandCursor)
            if action: button.clicked.connect(action)
            layout.addWidget(button)
        layout.addStretch(); motto=QLabel("NO BITRATE\nLEFT BEHIND"); motto.setObjectName("motto"); motto.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(motto); return side

    def make_table_panel(self):
        panel=QFrame(); panel.setObjectName("panel"); layout=QVBoxLayout(panel); layout.setContentsMargins(0,0,0,0)
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["SELECT","MOVIE","CURRENT SIZE","TARGET SIZE","SAVING","STATUS"]); self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection); self.table.itemSelectionChanged.connect(self.update_inspector); self.table.itemChanged.connect(self.table_item_changed)
        header=self.table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for column in range(2,6): header.setSectionResizeMode(column,QHeaderView.ResizeMode.ResizeToContents)
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
        refresh_poster = QPushButton("↻ REFRESH POSTER")
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

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        self.size_summary = QLabel("CURRENT — → TARGET —")
        self.size_summary.setObjectName("sizeSummary")
        self.size_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_summary.setWordWrap(True)
        layout.addWidget(self.size_summary)

        self.saving_summary = QLabel("SAVING —")
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
            "▶ ADD / REMOVE FROM QUEUE"
        )
        self.queue_selected_btn.setObjectName("startButton")
        self.queue_selected_btn.clicked.connect(
            self.toggle_selected_queue
        )
        layout.addWidget(self.queue_selected_btn)

        layout.addStretch()
        scroll.setWidget(self.inspector)
        return scroll

    def apply_style(self):
        self.setStyleSheet("""
        QMainWindow,QWidget{background:#08080c;color:#f3edf7;font-family:'Segoe UI';} QLabel#header{background:#08080c;border-bottom:2px solid #61217f;}
        QPushButton#headerIcon{background:rgba(20,10,28,210);border:1px solid #a943d0;border-radius:20px;color:#e582ff;font-size:21px;font-weight:900;padding:0;} QPushButton#headerIcon:hover{background:#6e218c;color:white;}
        QFrame#sidebar{background:#0c0b10;border:1px solid #29202f;border-radius:8px;} QPushButton#navButton,QPushButton#navActive{text-align:left;border:none;border-radius:6px;padding:11px 12px;font-size:13px;font-weight:700;color:#d9d2dd;background:transparent;} QPushButton#navButton:hover{background:#211627;color:white;} QPushButton#navActive{background:#46205a;color:white;border-left:3px solid #d554ff;} QLabel#motto{color:#bd43ec;font-size:18px;font-weight:900;font-style:italic;padding:18px 4px;}
        QFrame#statCard{background:#111016;border:1px solid #2f2636;border-radius:9px;} QLabel#statHeading{color:#a9a0ae;font-size:10px;font-weight:700;} QLabel#statValue{font-size:22px;font-weight:800;} QLabel#statSub{color:#77707d;font-size:10px;}
        QLineEdit,QComboBox,QSpinBox{background:#101015;border:1px solid #34283c;border-radius:6px;padding:8px;color:#e9e1ed;} QLineEdit:focus,QComboBox:focus,QSpinBox:focus{border:1px solid #9d3cc2;}
        QPushButton{background:#18141c;border:1px solid #493453;border-radius:6px;padding:8px 11px;font-weight:700;color:#ddd5e2;} QPushButton:hover{background:#2d1937;border-color:#a743ce;color:white;} QPushButton#primaryButton,QPushButton#startButton{background:#4f1768;border:1px solid #bf4bea;color:white;} QPushButton#startButton:hover,QPushButton#primaryButton:hover{background:#70218f;} QPushButton#presetButton{padding:7px 6px;font-size:11px;}
        QFrame#bulkBar{background:#0d0c11;border:1px solid #35243e;border-radius:7px;} QFrame#bulkBar QLabel{color:#b8aebd;font-size:10px;font-weight:800;}
        QCheckBox::indicator,QTableWidget::indicator{width:18px;height:18px;} QTableWidget::indicator:unchecked{border:1px solid #765184;background:#151119;border-radius:3px;} QTableWidget::indicator:checked{border:1px solid #d25cff;background:#8d2bb2;border-radius:3px;}
        QScrollArea#inspectorScroll{background:#0d0c11;border:1px solid #2d2333;border-radius:8px;} QScrollArea#inspectorScroll QWidget{background:#0d0c11;} QFrame#panel,QFrame#inspector{background:#0d0c11;border:1px solid #2d2333;border-radius:8px;} QTableWidget{background:#0d0c11;alternate-background-color:#131117;border:none;gridline-color:#24202a;selection-background-color:#32153f;} QHeaderView::section{background:#111016;color:#bdb4c2;border:none;border-bottom:1px solid #33253c;padding:9px;font-size:10px;font-weight:800;} QTableWidget::item{padding:8px;}
        QLabel#detailTitle{color:#cf55f6;font-size:18px;font-weight:900;font-style:italic;} QFrame#posterPlaceholder{background:#151119;border:1px solid #493254;border-radius:7px;min-height:250px;} QLabel#posterImage{color:#8f8296;font-size:18px;font-weight:900;background:transparent;} QLabel#detailPath{color:#958b9b;font-size:11px;} QFrame#divider{color:#382b40;} QLabel#sizeSummary{font-size:14px;font-weight:800;color:#eee8f1;} QLabel#savingSummary{color:#70df7b;font-size:13px;font-weight:800;} QLabel#recommendation{background:#17101c;border:1px solid #4d2c5b;border-radius:7px;padding:8px;color:#dfb5f4;font-size:11px;font-weight:800;} QLabel#smallHeading{color:#aea3b3;font-size:10px;font-weight:800;}
        QFrame#operationsCenter{background:#0b0910;border:1px solid #4b2858;border-radius:9px;}
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
        QLabel#telemetryStage{background:#351342;border:1px solid #8e35ad;border-radius:9px;padding:4px 10px;color:#e8c8f5;font-size:10px;font-weight:900;}
        QFrame#quickBar{background:#0b0910;border-bottom:1px solid #35253e;}
        QPushButton#quickButton,QPushButton#updateButton{background:#15111a;border:1px solid #493453;border-radius:6px;padding:6px 10px;color:#ded5e3;font-size:10px;font-weight:800;}
        QPushButton#quickButton:hover,QPushButton#updateButton:hover{background:#32183d;border-color:#a943d0;color:white;}
        QFrame#bottomBar{background:#0d0c11;border:1px solid #2c2133;border-radius:8px;} QLabel#statusText{color:#c9becf;} QProgressBar{background:#17121b;border:1px solid #3d2946;border-radius:6px;text-align:center;color:white;} QProgressBar::chunk{background:#9f36c8;border-radius:5px;} QSplitter::handle{background:#1e1723;width:5px;}
        """)

    def scan(self):
        self.scan_btn.setEnabled(False); root=Path(self.config["movie_root"]); self.status.setText(f"Scanning {root}..."); self.progress.setRange(0,0)
        worker=Scanner(root,int(self.config["minimum_size_gib"]*1024**3),int(self.config["default_target_gib"])); worker.signals.finished.connect(self.scan_done); worker.signals.failed.connect(self.failed); self.pool.start(worker)
    def scan_done(self,movies):
        self.movies=movies
        self.queue=[]
        self.progress.setRange(0,100)
        self.progress.setValue(0)
        self.scan_btn.setEnabled(True)
        self.apply_filter()
        self.found_card.value.setText(str(len(movies)))
        self.library_card.value.setText(
            human_size(sum(m.size for m in movies))
        )
        self.update_stats()
        self.operations.set_process_status("Ready")

        if not movies:
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
            self.status.setText(
                f"Found {len(movies)} movies. "
                "Configure Jellyfin to download posters automatically."
            )

    def poster_prefetch_progress(self, percent, message):
        self.progress.setValue(percent)
        self.status.setText(message)

    def poster_prefetch_done(self, result):
        self.scan_btn.setEnabled(True)
        self.progress.setValue(100)
        self.status.setText(
            f"Scan complete: {result['total']} movies, "
            f"{result['available']} posters available "
            f"({result['downloaded']} downloaded)."
        )
        self.update_inspector()

    def poster_prefetch_failed(self, message):
        self.scan_btn.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText(
            f"Movie scan completed, but poster download stopped: {message}"
        )
    def apply_filter(self):
        search=self.search.text().strip().lower(); mode=self.filter_box.currentText(); items=[m for m in self.movies if search in m.title.lower()]
        if mode=="Queued only": items=[m for m in items if m.queued]
        elif mode=="Not queued": items=[m for m in items if not m.queued]
        sort=self.sort_box.currentText(); items.sort(key=(lambda m:m.size) if sort=="Size: Low to high" else (lambda m:m.title.lower()) if sort=="Title: A to Z" else (lambda m:-m.size)); self.visible_movies=items; self.populate_table()
    def populate_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.visible_movies))
        for row,movie in enumerate(self.visible_movies):
            check=QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsSelectable)
            check.setCheckState(Qt.CheckState.Checked if movie.selected else Qt.CheckState.Unchecked)
            check.setData(Qt.ItemDataRole.UserRole,movie)
            check.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row,0,check)

            title=QTableWidgetItem(movie.title); title.setToolTip(str(movie.path)); title.setData(Qt.ItemDataRole.UserRole,movie); title.setForeground(QColor("#d35cff" if movie.queued else "#f3edf7")); self.table.setItem(row,1,title); self.table.setItem(row,2,QTableWidgetItem(human_size(movie.size)))
            target=QComboBox(); choices=[3,5,10,15,20]
            if movie.target_gib not in choices: choices.append(movie.target_gib); choices.sort()
            target.addItems([f"{x} GB" for x in choices]); target.setCurrentText(f"{movie.target_gib} GB"); target.currentTextChanged.connect(lambda value,m=movie,r=row:self.change_target(m,r,value)); self.table.setCellWidget(row,3,target)
            saving=QTableWidgetItem(human_size(movie.saving)); saving.setForeground(QColor("#70df7b")); self.table.setItem(row,4,saving); status=QTableWidgetItem(movie.status if movie.status!="Ready" else ("Queued" if movie.queued else "Ready")); status.setForeground(QColor("#d45aff" if movie.queued else "#b4a9ba")); self.table.setItem(row,5,status)
        self.table.blockSignals(False)
        if self.table.rowCount(): self.table.selectRow(0)

    def selected_movie(self):
        row=self.table.currentRow(); item=self.table.item(row,1) if row>=0 else None; return item.data(Qt.ItemDataRole.UserRole) if item else None

    def table_item_changed(self,item):
        if item.column()!=0:return
        movie=item.data(Qt.ItemDataRole.UserRole)
        if movie:
            movie.selected=item.checkState()==Qt.CheckState.Checked

    def checked_movies(self):
        return [movie for movie in self.movies if movie.selected]

    def set_visible_checked(self,checked):
        for movie in self.visible_movies:
            movie.selected=checked
        self.populate_table()
        count=len([movie for movie in self.visible_movies if movie.selected])
        self.status.setText(f"{count} visible movie(s) checked.")

    def apply_bulk_target(self):
        checked=self.checked_movies()
        if not checked:
            QMessageBox.information(self,APP_NAME,"Tick the boxes beside the movies first.")
            return
        size=int(self.bulk_target.currentText().split()[0])
        for movie in checked:
            movie.target_gib=size
        self.populate_table(); self.update_stats()
        self.status.setText(f"Applied a {size} GiB target to {len(checked)} checked movie(s).")

    def add_checked_to_queue(self):
        checked=self.checked_movies()
        if not checked:
            QMessageBox.information(self,APP_NAME,"Tick the boxes beside the movies first.")
            return
        for movie in checked:
            movie.queued=True
            movie.selected=False
        self.apply_filter(); self.update_stats()
        self.status.setText(f"Added {len(checked)} movie(s) to the queue.")

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
        self.size_summary.setText(f"CURRENT {human_size(movie.size)} → TARGET {movie.target_gib} GB")
        self.saving_summary.setText(f"SAVING {human_size(movie.saving)} ({movie.saving_percent}%)")
        if movie.saving_percent >= 70 and movie.saving >= 10 * 1024**3:
            recommendation="★★★★★  HIGH-VALUE OPTIMIZATION"
        elif movie.saving_percent >= 45:
            recommendation="★★★★☆  RECOMMENDED"
        elif movie.saving >= 2 * 1024**3:
            recommendation="★★★☆☆  MODERATE SAVING"
        else:
            recommendation="★☆☆☆☆  PROBABLY LEAVE ALONE"
        self.recommendation.setText(recommendation)
        self.queue_selected_btn.setText("✕ REMOVE FROM QUEUE" if movie.queued else "▶ ADD TO QUEUE")
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
    def change_target(self,movie,row,value): movie.target_gib=int(value.split()[0]); self.table.setItem(row,4,QTableWidgetItem(human_size(movie.saving))); self.update_inspector(); self.update_stats()
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
        if not self.queue: QMessageBox.information(self,APP_NAME,"Add at least one movie to the queue first."); return
        answer=QMessageBox.warning(self,APP_NAME,"Queued movies will be encoded and safely replace their originals after verification. Start now?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        self.start_btn.setEnabled(False); self.scan_btn.setEnabled(False); self.process_next()
    def process_next(self):
        self.queue=[m for m in self.movies if m.queued]
        if not self.queue:
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
        movie=self.queue[0]
        self.current_movie=movie
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
            len(self.queue) - 1,
        )
        self.progress.setValue(0)
        worker=EncodeWorker(movie,self.config)
        worker.signals.progress.connect(self.progress_update)
        worker.signals.message.connect(self.status.setText)
        worker.signals.stage.connect(self.process_stage_changed)
        worker.signals.finished.connect(
            lambda path,m=movie:self.encode_done(m,path)
        )
        worker.signals.failed.connect(
            lambda msg,m=movie:self.encode_failed(m,msg)
        )
        self.pool.start(worker)
    def process_stage_changed(self, stage):
        if self.config.get("show_live_telemetry", True):
            self.telemetry.begin_stage(stage)

    def progress_update(self,percent,message):
        self.progress.setValue(percent)
        self.status.setText(message)

    def encode_done(self,movie,path): movie.status="Done"; self.status.setText(f"Completed: {movie.title}"); self.populate_table(); self.process_next()
    def encode_failed(self,movie,message):
        movie.status="Failed"
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

    def show_update_center(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def show_queue_manager(self):
        queued=[movie for movie in self.movies if movie.queued]
        if not queued:
            QMessageBox.information(self,APP_NAME,"The queue is empty. Add checked movies first.")
            return
        dialog=QueueManagerDialog(queued,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            ordered=dialog.ordered_movies()
            for movie in self.movies:
                movie.queued=False
            for movie in ordered:
                movie.queued=True
            order_map={id(movie):index for index,movie in enumerate(ordered)}
            self.movies.sort(key=lambda movie:(0,order_map[id(movie)]) if id(movie) in order_map else (1,-movie.size))
            self.apply_filter(); self.update_stats()
            self.status.setText(f"Queue order saved for {len(ordered)} movie(s).")

    def show_health(self):
        HealthDialog(self.config,self).exec()

    def show_settings(self):
        dialog=SettingsDialog(self.config,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.config=dialog.values()
            save_config(self.config)
            self.operations.config=self.config
            self.operations.refresh_services()
            self.status.setText(
                "Settings saved. Run a new scan to apply library changes."
            )
    def show_help(self): HelpDialog(self).exec()
    def show_about(self):
        QMessageBox.about(
            self,
            APP_NAME,
            f"<h2>Evil's Media Optimizer {APP_VERSION}</h2>"
            "<p>A media optimization dashboard with automatic Jellyfin "
            "poster caching, queue management, hidden-console launching, "
            "a modular media optimizer with safe HandBrake/NVENC encoding, Jellyfin posters, live telemetry and a resilient external updater.</p>"
            "<p>Open <b>Settings → Updates</b> to install future fixes "
            "without losing your settings or cache.</p>"
            "<p>Built for Jason's VaultOne media workflow.</p>",
        )
    def show_tools(self): self.show_health()
    def show_jellyfin_info(self):
        ok, detail = test_jellyfin(self.config)
        QMessageBox.information(
            self,
            "Jellyfin",
            ("✓ " if ok else "✕ ")
            + detail
            + "\n\nPosters use this Jellyfin connection. "
            "Configure it under Settings → Integrations.",
        )
    def show_history(self):
        if not HISTORY_FILE.exists(): QMessageBox.information(self,"History","No completed encodes have been recorded yet."); return
        try: rows=json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception: rows=[]
        text='\n'.join(f"{r.get('completed','')} — {r.get('movie','')} — saved {human_size(max(0,r.get('original',0)-r.get('new',0)))}" for r in rows[-30:]) or 'No history.'; QMessageBox.information(self,"Recent history",text)
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
                f"{APP_NAME} — Error",
                "Something went wrong. The error has been saved to:\n\n"
                f"{LOG_FILE}\n\n"
                f"{exc_value}",
            )

    sys.excepthook = handle_exception

def main():
    install_exception_handler()
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); window=MainWindow(); window.show(); return app.exec()
if __name__=='__main__': raise SystemExit(main())
