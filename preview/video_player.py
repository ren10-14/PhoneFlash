"""
Built-in video player window using QMediaPlayer (PySide6).
Downloads video from phone to temp, then plays in a separate window.
"""
import os
import tempfile
import threading
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal, QSize
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QSizePolicy, QStyle,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.phone_client import PhoneClient

CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".3gp", ".webm",
    ".wmv", ".flv", ".m4v", ".ts",
}


def is_video_file(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in VIDEO_EXTENSIONS


def _format_time(ms: int) -> str:
    """Format milliseconds to MM:SS or HH:MM:SS."""
    if ms < 0:
        ms = 0
    total_sec = ms // 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class VideoPlayerWindow(QWidget):
    """
    Standalone video player window.
    Call play_file(path) to play a local file.
    """

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PhoneFlash — Video Player")
        self.setMinimumSize(640, 480)
        self.resize(900, 600)
        self.setWindowFlags(Qt.Window)

        self._build_ui()
        self._setup_player()
        self._wire()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: #000;")
        layout.addWidget(self.video_widget, 1)

        # Controls panel
        ctrl_panel = QWidget()
        ctrl_panel.setStyleSheet("""
            QWidget { background-color: #1a1a2e; }
            QPushButton {
                background-color: #2e2e42;
                color: #e0e0e8;
                border: 1px solid #3c3c5c;
                border-radius: 4px;
                padding: 4px 12px;
                min-height: 24px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #7c6ff7; color: white; }
            QLabel { color: #9090a8; background: transparent; font-size: 12px; }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2e2e42;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #7c6ff7;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #7c6ff7;
                border-radius: 3px;
            }
        """)
        cl = QVBoxLayout(ctrl_panel)
        cl.setContentsMargins(12, 8, 12, 8)
        cl.setSpacing(6)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        cl.addWidget(self.seek_slider)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(36, 36)
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(36, 36)
        self.btn_back10 = QPushButton("−10s")
        self.btn_fwd10 = QPushButton("+10s")

        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_time.setFont(QFont("Consolas", 11))

        self.lbl_title = QLabel("")
        self.lbl_title.setFont(QFont("Segoe UI", 10))
        self.lbl_title.setStyleSheet("color: #e0e0e8;")

        # Volume
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)

        self.lbl_vol = QLabel("Vol")

        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_back10)
        btn_row.addWidget(self.btn_fwd10)
        btn_row.addWidget(self.lbl_time)
        btn_row.addStretch()
        btn_row.addWidget(self.lbl_title)
        btn_row.addStretch()
        btn_row.addWidget(self.lbl_vol)
        btn_row.addWidget(self.vol_slider)

        cl.addLayout(btn_row)
        layout.addWidget(ctrl_panel)

    def _setup_player(self):
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.audio.setVolume(0.8)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)

    def _wire(self):
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_back10.clicked.connect(lambda: self._seek_relative(-10000))
        self.btn_fwd10.clicked.connect(lambda: self._seek_relative(10000))

        self.player.durationChanged.connect(self._on_duration)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)

        self.seek_slider.sliderMoved.connect(self._on_seek)
        self.vol_slider.valueChanged.connect(self._on_volume)

    # ── Public ──────────────────────────────────────────────────

    def play_file(self, path: str):
        """Play a local video file."""
        self.lbl_title.setText(os.path.basename(path))
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.btn_play.setText("⏸")
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Controls ────────────────────────────────────────────────

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def _stop(self):
        self.player.stop()
        self.btn_play.setText("▶")

    def _seek_relative(self, ms: int):
        pos = self.player.position() + ms
        pos = max(0, min(pos, self.player.duration()))
        self.player.setPosition(pos)

    def _on_seek(self, pos: int):
        self.player.setPosition(pos)

    def _on_volume(self, val: int):
        self.audio.setVolume(val / 100.0)

    # ── Player callbacks ────────────────────────────────────────

    def _on_duration(self, dur: int):
        self.seek_slider.setRange(0, dur)

    def _on_position(self, pos: int):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(pos)
        dur = self.player.duration()
        self.lbl_time.setText(f"{_format_time(pos)} / {_format_time(dur)}")

    def _on_state(self, state):
        if state == QMediaPlayer.StoppedState:
            self.btn_play.setText("▶")

    # ── Close ───────────────────────────────────────────────────

    def closeEvent(self, event):
        self.player.stop()
        self.closed.emit()
        super().closeEvent(event)


class VideoDownloadAndPlay(QWidget):
    """
    Helper: downloads video from phone in background, then plays.
    Shows download progress.
    """

    log = Signal(str)
    download_progress = Signal(int, int)
    play_ready = Signal(str)  # local_path

    def __init__(self, client: PhoneClient, parent=None):
        super().__init__(parent)
        self._client = client
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def download_and_play(self, remote_path: str, file_name: str, file_size: int):
        if self._busy:
            self.log.emit("Video download already in progress")
            return

        self._busy = True
        tmp_dir = tempfile.mkdtemp(prefix="pf_video_")
        local_path = os.path.join(tmp_dir, file_name)

        self.log.emit(f"Downloading video: {file_name}...")

        threading.Thread(
            target=self._bg_download,
            args=(remote_path, local_path, file_size),
            daemon=True,
        ).start()

    def _bg_download(self, remote: str, local: str, size: int):
        try:
            offset = 0
            with open(local, "wb") as f:
                while offset < size:
                    length = min(CHUNK_SIZE, size - offset)
                    resp, data = self._client.read_chunk(remote, offset, length)
                    if resp.get("status") != "ok":
                        self.log.emit(f"READ error: {resp}")
                        return
                    if not data:
                        break
                    f.write(data)
                    offset += len(data)
                    self.download_progress.emit(offset, size)

            self.log.emit(f"Video ready: {os.path.basename(local)}")
            self.play_ready.emit(local)
        except Exception as e:
            self.log.emit(f"Video download error: {e}")
        finally:
            self._busy = False