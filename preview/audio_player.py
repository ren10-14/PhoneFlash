"""
Built-in audio player window using QMediaPlayer (PySide6).
Downloads audio from phone to temp, then plays in a compact window.
"""
import os
import tempfile
import threading
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from core.phone_client import PhoneClient

CHUNK_SIZE = 1 * 1024 * 1024

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
    ".wma", ".opus", ".amr", ".mid", ".midi",
}


def is_audio_file(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in AUDIO_EXTENSIONS


def _format_time(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_sec = ms // 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class AudioPlayerWindow(QWidget):
    """Compact audio player window."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PhoneFlash — Audio Player")
        self.setMinimumSize(420, 180)
        self.resize(500, 200)
        self.setMaximumHeight(250)
        self.setWindowFlags(Qt.Window)

        self._build_ui()
        self._setup_player()
        self._wire()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #e0e0e8;
            }
            QPushButton {
                background-color: #2e2e42;
                color: #e0e0e8;
                border: 1px solid #3c3c5c;
                border-radius: 4px;
                padding: 4px 12px;
                min-height: 28px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7c6ff7;
                color: white;
            }
            QLabel {
                color: #9090a8;
                background: transparent;
            }
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Title
        self.lbl_title = QLabel("No track loaded")
        self.lbl_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_title.setStyleSheet("color: #e0e0e8;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        layout.addWidget(self.seek_slider)

        # Time
        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_time.setFont(QFont("Consolas", 10))
        self.lbl_time.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_time)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.btn_back10 = QPushButton("-10s")
        self.btn_back10.setFixedWidth(50)

        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(60)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #7c6ff7;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #9a8dfc;
            }
        """)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setFixedWidth(50)

        self.btn_fwd10 = QPushButton("+10s")
        self.btn_fwd10.setFixedWidth(50)

        self.lbl_vol = QLabel("Vol")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(90)

        ctrl.addStretch()
        ctrl.addWidget(self.btn_back10)
        ctrl.addWidget(self.btn_play)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_fwd10)
        ctrl.addSpacing(16)
        ctrl.addWidget(self.lbl_vol)
        ctrl.addWidget(self.vol_slider)
        ctrl.addStretch()

        layout.addLayout(ctrl)

    def _setup_player(self):
        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.audio_out.setVolume(0.8)
        self.player.setAudioOutput(self.audio_out)

    def _wire(self):
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_back10.clicked.connect(lambda: self._seek_rel(-10000))
        self.btn_fwd10.clicked.connect(lambda: self._seek_rel(10000))

        self.player.durationChanged.connect(self._on_duration)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)

        self.seek_slider.sliderMoved.connect(self._on_seek)
        self.vol_slider.valueChanged.connect(self._on_volume)

    def play_file(self, path: str):
        name = os.path.basename(path)
        self.lbl_title.setText(name)
        self.setWindowTitle(f"PhoneFlash — {name}")
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.btn_play.setText("Pause")
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("Play")
        else:
            self.player.play()
            self.btn_play.setText("Pause")

    def _stop(self):
        self.player.stop()
        self.btn_play.setText("Play")

    def _seek_rel(self, ms: int):
        pos = max(0, min(self.player.position() + ms, self.player.duration()))
        self.player.setPosition(pos)

    def _on_seek(self, pos: int):
        self.player.setPosition(pos)

    def _on_volume(self, val: int):
        self.audio_out.setVolume(val / 100.0)

    def _on_duration(self, dur: int):
        self.seek_slider.setRange(0, dur)

    def _on_position(self, pos: int):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(pos)
        self.lbl_time.setText(
            f"{_format_time(pos)} / {_format_time(self.player.duration())}"
        )

    def _on_state(self, state):
        if state == QMediaPlayer.StoppedState:
            self.btn_play.setText("Play")

    def closeEvent(self, event):
        self.player.stop()
        self.closed.emit()
        super().closeEvent(event)


class AudioDownloadAndPlay(QObject):
    """Downloads audio from phone in background, then emits play_ready."""

    log = Signal(str)
    download_progress = Signal(int, int)
    play_ready = Signal(str)

    def __init__(self, client: PhoneClient, parent=None):
        super().__init__(parent)
        self._client = client
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def download_and_play(self, remote_path: str, file_name: str, file_size: int):
        if self._busy:
            self.log.emit("Audio download already in progress")
            return

        self._busy = True
        tmp_dir = tempfile.mkdtemp(prefix="pf_audio_")
        local_path = os.path.join(tmp_dir, file_name)
        self.log.emit(f"Downloading audio: {file_name}...")

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

            self.log.emit(f"Audio ready: {os.path.basename(local)}")
            self.play_ready.emit(local)
        except Exception as e:
            self.log.emit(f"Audio download error: {e}")
        finally:
            self._busy = False