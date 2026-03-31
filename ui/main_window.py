"""
Main window — multi-select download, image preview, video/audio player.
"""
import os
from datetime import datetime
from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLabel, QSplitter, QFrame, QStatusBar,
    QHeaderView, QSizePolicy, QApplication, QFileDialog,
    QProgressBar,
)

from core.connection_manager import ConnectionManager
from preview.image_preview import ImagePreviewLoader, is_image_file
from preview.video_player import VideoPlayerWindow, VideoDownloadAndPlay, is_video_file
from preview.audio_player import AudioPlayerWindow, AudioDownloadAndPlay, is_audio_file
from ui.settings_dialog import SettingsDialog
from ui.theme import apply_theme, get_accent_color


# ─── Helpers ────────────────────────────────────────────────────

def _btn(text, accent=False):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if accent:
        b.setProperty("accent", True)
    return b


def _card():
    f = QFrame()
    f.setProperty("card", True)
    return f


def _sz(n):
    if n <= 0:
        return "—"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def _ts(ms):
    if ms <= 0:
        return "—"
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


def _ftype(name, is_dir):
    if is_dir:
        return "Folder"
    ext = os.path.splitext(name)[1].lower()
    m = {
        ".jpg": "Image", ".jpeg": "Image", ".png": "Image", ".gif": "Image",
        ".bmp": "Image", ".webp": "Image",
        ".mp4": "Video", ".mkv": "Video", ".avi": "Video", ".mov": "Video",
        ".3gp": "Video", ".webm": "Video",
        ".mp3": "Audio", ".wav": "Audio", ".ogg": "Audio", ".flac": "Audio",
        ".aac": "Audio", ".m4a": "Audio",
        ".txt": "Text", ".log": "Text", ".json": "Text", ".xml": "Text",
        ".apk": "APK", ".zip": "Archive", ".rar": "Archive", ".pdf": "PDF",
    }
    return m.get(ext, "File")


def _ficon(name, is_dir):
    if is_dir:
        return "📁"
    t = _ftype(name, False)
    return {
        "Image": "🖼", "Video": "🎬", "Audio": "🎵", "Text": "📄",
        "APK": "📦", "Archive": "🗜", "PDF": "📕",
    }.get(t, "📄")


def _is_media(name):
    return is_video_file(name) or is_audio_file(name)


# ─── MainWindow ────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, app: QApplication, settings):
        super().__init__()
        self._app = app
        self._settings = settings
        self.setWindowTitle("PhoneFlash")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 780)

        self._current_path: Optional[str] = None
        self._history: List[Optional[str]] = []

        # Download queue for multi-file download
        self._dl_queue: List[dict] = []
        self._dl_folder: str = ""
        self._dl_current_name: str = ""

        # Connection
        self._conn = ConnectionManager(settings, parent=self)
        self._conn.log.connect(self._log)
        self._conn.device_status_changed.connect(self._on_dev_status)
        self._conn.server_status_changed.connect(self._on_srv_status)
        self._conn.device_name_changed.connect(self._on_dev_name)
        self._conn.roots_result.connect(self._on_roots)
        self._conn.list_result.connect(self._on_list)
        self._conn.transfer.download_progress.connect(self._on_dl_prog)
        self._conn.transfer.download_finished.connect(self._on_dl_done)
        self._conn.transfer.upload_progress.connect(self._on_ul_prog)
        self._conn.transfer.upload_finished.connect(self._on_ul_done)

        # Image preview
        self._img_loader = ImagePreviewLoader(self._conn.client, parent=self)
        self._img_loader.preview_ready.connect(self._on_preview_ready)
        self._img_loader.preview_error.connect(self._on_preview_error)
        self._img_loader.loading_started.connect(self._on_preview_loading)

        # Video player
        self._video_player: Optional[VideoPlayerWindow] = None
        self._video_dl = VideoDownloadAndPlay(self._conn.client, parent=self)
        self._video_dl.log.connect(self._log)
        self._video_dl.download_progress.connect(self._on_media_dl_prog)
        self._video_dl.play_ready.connect(self._on_video_ready)

        # Audio player
        self._audio_player: Optional[AudioPlayerWindow] = None
        self._audio_dl = AudioDownloadAndPlay(self._conn.client, parent=self)
        self._audio_dl.log.connect(self._log)
        self._audio_dl.download_progress.connect(self._on_media_dl_prog)
        self._audio_dl.play_ready.connect(self._on_audio_ready)

        self._build()
        self._wire()
        self._log("PhoneFlash PC started")
        self._log("Press <b>Connect</b> to connect to phone")
        self._log("Tip: Hold <b>Ctrl</b> to select multiple files for download")

    # ════════════════════════════════════════════════════════════
    #  LOG
    # ════════════════════════════════════════════════════════════

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        accent = get_accent_color(self._settings.get("theme", "dark"))
        self.log_box.append(f"<span style='color:{accent}'>[{ts}]</span> {msg}")
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ════════════════════════════════════════════════════════════
    #  BUILD UI
    # ════════════════════════════════════════════════════════════

    def _build(self):
        c = QWidget()
        self.setCentralWidget(c)
        root = QVBoxLayout(c)
        root.setContentsMargins(10, 10, 10, 6)
        root.setSpacing(8)

        # ── Toolbar ─────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(6)

        self.btn_adb     = _btn("📱 ADB Devices")
        self.btn_connect = _btn("🔗 Connect", accent=True)
        self.btn_ping    = _btn("🏓 Ping")
        self.btn_refresh = _btn("🔄 Refresh")
        self.btn_dl      = _btn("⬇ Download")
        self.btn_ul      = _btn("⬆ Upload")
        self.btn_play    = _btn("▶ Play Media")
        self.btn_set     = _btn("⚙ Settings")

        for b in (self.btn_adb, self.btn_connect, self.btn_ping,
                  self.btn_refresh, self.btn_dl, self.btn_ul,
                  self.btn_play, self.btn_set):
            tb.addWidget(b)

        tb.addStretch()

        self.lbl_device = QLabel("")
        self.lbl_device.setProperty("dim", True)
        tb.addWidget(self.lbl_device)

        self.lbl_dev = QLabel("📱 No device")
        self.lbl_dev.setStyleSheet("color:#f44060; font-weight:600; margin-right:12px;")
        tb.addWidget(self.lbl_dev)

        self.lbl_srv = QLabel("🖥 Not connected")
        self.lbl_srv.setStyleSheet("color:#f44060; font-weight:600;")
        tb.addWidget(self.lbl_srv)

        root.addLayout(tb)

        # ── Progress ────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar{background:#2e2e42;border:none;border-radius:3px}"
            "QProgressBar::chunk{background:#7c6ff7;border-radius:3px}"
        )
        root.addWidget(self.progress)

        # ── Navigation ──────────────────────────────────────────
        nav = QHBoxLayout()
        nav.setSpacing(6)

        self.btn_back = QPushButton("Back")
        self.btn_back.setFixedHeight(36)
        self.btn_back.setMinimumWidth(60)
        self.btn_back.setCursor(Qt.PointingHandCursor)

        self.btn_home = QPushButton("Home")
        self.btn_home.setFixedHeight(36)
        self.btn_home.setMinimumWidth(60)
        self.btn_home.setCursor(Qt.PointingHandCursor)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Phone path...")
        self.path_edit.setReadOnly(True)

        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_home)
        nav.addWidget(self.path_edit, 1)
        root.addLayout(nav)

        # ── Files + Preview ─────────────────────────────────────
        sp_h = QSplitter(Qt.Horizontal)
        sp_h.setHandleWidth(3)

        fw = QWidget()
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        # ExtendedSelection: Ctrl+Click, Shift+Click for multi-select
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Name", "Size", "Type", "Modified"])
        h = self.tree.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in (1, 2, 3):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        fl.addWidget(self.tree)

        # Selection count label
        self.lbl_selection = QLabel("")
        self.lbl_selection.setProperty("dim", True)
        self.lbl_selection.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        fl.addWidget(self.lbl_selection)

        pf = _card()
        pl = QVBoxLayout(pf)
        pl.setContentsMargins(12, 12, 12, 12)
        pl.setSpacing(8)

        self.prev_title = QLabel("Preview")
        self.prev_title.setAlignment(Qt.AlignCenter)
        self.prev_title.setFont(QFont("Segoe UI", 11, QFont.Bold))

        self.prev_img = QLabel("Select a file")
        self.prev_img.setAlignment(Qt.AlignCenter)
        self.prev_img.setMinimumSize(280, 220)
        self.prev_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._update_preview_bg()

        self.prev_info = QLabel("")
        self.prev_info.setProperty("dim", True)
        self.prev_info.setAlignment(Qt.AlignCenter)
        self.prev_info.setWordWrap(True)

        pl.addWidget(self.prev_title)
        pl.addWidget(self.prev_img, 1)
        pl.addWidget(self.prev_info)

        sp_h.addWidget(fw)
        sp_h.addWidget(pf)
        sp_h.setSizes([700, 360])

        # ── Log ─────────────────────────────────────────────────
        lf = _card()
        ll = QVBoxLayout(lf)
        ll.setContentsMargins(8, 6, 8, 6)
        ll.setSpacing(2)

        lh = QHBoxLayout()
        lb = QLabel("Log")
        lb.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_clr = QPushButton("Clear")
        self.btn_clr.setFixedHeight(24)
        self.btn_clr.setCursor(Qt.PointingHandCursor)
        lh.addWidget(lb)
        lh.addStretch()
        lh.addWidget(self.btn_clr)
        ll.addLayout(lh)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        ll.addWidget(self.log_box)

        sp_v = QSplitter(Qt.Vertical)
        sp_v.setHandleWidth(3)
        sp_v.addWidget(sp_h)
        sp_v.addWidget(lf)
        sp_v.setSizes([520, 180])
        root.addWidget(sp_v, 1)

        self.sbar = QStatusBar()
        self.setStatusBar(self.sbar)
        self.sbar.showMessage("Ready")

    # ════════════════════════════════════════════════════════════
    #  WIRE
    # ════════════════════════════════════════════════════════════

    def _wire(self):
        self.btn_adb.clicked.connect(lambda: self._conn.request_devices())
        self.btn_connect.clicked.connect(self._click_connect)
        self.btn_ping.clicked.connect(lambda: self._conn.do_ping())
        self.btn_refresh.clicked.connect(self._click_refresh)
        self.btn_dl.clicked.connect(self._click_download)
        self.btn_ul.clicked.connect(self._click_upload)
        self.btn_play.clicked.connect(self._click_play_media)
        self.btn_set.clicked.connect(self._click_settings)
        self.btn_back.clicked.connect(self._click_back)
        self.btn_home.clicked.connect(self._click_home)
        self.btn_clr.clicked.connect(self.log_box.clear)
        self.tree.itemClicked.connect(self._item_click)
        self.tree.itemDoubleClicked.connect(self._item_dbl)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

    # ════════════════════════════════════════════════════════════
    #  SELECTION INFO
    # ════════════════════════════════════════════════════════════

    def _on_selection_changed(self):
        """Update selection count label."""
        items = self.tree.selectedItems()
        files = []
        total_size = 0
        for item in items:
            d = item.data(0, Qt.UserRole)
            if d and not d.get("isDir"):
                files.append(d)
                total_size += d.get("size", 0)

        if len(files) == 0:
            self.lbl_selection.setText("")
        elif len(files) == 1:
            self.lbl_selection.setText(f"1 file selected ({_sz(total_size)})")
        else:
            self.lbl_selection.setText(
                f"{len(files)} files selected ({_sz(total_size)}) — Press Download"
            )

    # ════════════════════════════════════════════════════════════
    #  CLICK HANDLERS
    # ════════════════════════════════════════════════════════════

    def _click_connect(self):
        if self._conn.is_server_connected:
            self._conn.do_disconnect()
            self.btn_connect.setText("🔗 Connect")
            self.tree.clear()
            self.path_edit.setText("")
            self._clear_preview()
        else:
            self._conn.do_connect()

    def _click_refresh(self):
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return
        if self._current_path is None:
            self._conn.do_roots()
        else:
            self._conn.do_list(self._current_path)

    def _click_download(self):
        """Download selected files. Supports multi-select."""
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return

        # Collect selected files (not folders)
        items = self.tree.selectedItems()
        files_to_dl = []
        for item in items:
            d = item.data(0, Qt.UserRole)
            if d and not d.get("isDir") and d.get("size", 0) > 0:
                files_to_dl.append(d)

        if not files_to_dl:
            self._log("Select one or more files to download")
            return

        if len(files_to_dl) == 1:
            # Single file — ask for save path
            d = files_to_dl[0]
            path, _ = QFileDialog.getSaveFileName(self, "Save file", d["name"])
            if not path:
                return
            self._show_progress()
            self._conn.transfer.download(d["full_path"], path, d["size"])
        else:
            # Multiple files — ask for folder
            folder = QFileDialog.getExistingDirectory(
                self, "Select folder to save files"
            )
            if not folder:
                return

            self._log(f"Downloading {len(files_to_dl)} files to: {folder}")

            # Build download queue
            self._dl_queue = list(files_to_dl)
            self._dl_folder = folder
            self._show_progress()
            self._start_next_download()

    def _start_next_download(self):
        """Start downloading next file in queue."""
        if not self._dl_queue:
            self.progress.setVisible(False)
            self._log("All downloads complete!")
            self.sbar.showMessage("All downloads complete")
            return

        d = self._dl_queue.pop(0)
        name = d["name"]
        remote = d["full_path"]
        size = d["size"]
        remaining = len(self._dl_queue)

        local_path = os.path.join(self._dl_folder, name)

        # Avoid overwriting — add number if exists
        if os.path.exists(local_path):
            base, ext = os.path.splitext(name)
            counter = 1
            while os.path.exists(local_path):
                local_path = os.path.join(self._dl_folder, f"{base} ({counter}){ext}")
                counter += 1

        self._dl_current_name = name
        self._log(f"Downloading: {name} ({_sz(size)}) — {remaining} remaining")
        self._conn.transfer.download(remote, local_path, size)

    def _click_upload(self):
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return
        if self._current_path is None:
            self._log("Open a folder first")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Upload")
        if not path:
            return
        name = os.path.basename(path)
        remote = f"{self._current_path}/{name}"
        self._show_progress()
        self._conn.transfer.upload(path, remote)

    def _click_play_media(self):
        item = self.tree.currentItem()
        if not item:
            self._log("Select a media file")
            return
        d = item.data(0, Qt.UserRole)
        if not d or d.get("isDir"):
            self._log("Select a file")
            return
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return

        name = d["name"]
        size = d.get("size", 0)
        if size <= 0:
            return

        if is_video_file(name):
            self._show_progress()
            self._video_dl.download_and_play(d["full_path"], name, size)
        elif is_audio_file(name):
            self._show_progress()
            self._audio_dl.download_and_play(d["full_path"], name, size)
        else:
            self._log("Not a media file (video/audio)")

    def _click_settings(self):
        dlg = SettingsDialog(self._settings, parent=self)
        dlg.theme_changed.connect(self._apply_theme)
        dlg.exec()
        self._conn.update_settings()

    def _apply_theme(self, name):
        apply_theme(self._app, name)
        self._update_preview_bg()

    def _click_back(self):
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return
        if not self._history:
            self._log("No history")
            return
        prev = self._history.pop()
        if prev is None:
            self._current_path = None
            self.path_edit.setText("")
            self._conn.do_roots()
        else:
            self._current_path = prev
            self.path_edit.setText(prev)
            self._conn.do_list(prev)

    def _click_home(self):
        if not self._conn.is_server_connected:
            self._log("Not connected")
            return
        self._history.clear()
        self._current_path = None
        self.path_edit.setText("")
        self._conn.do_roots()

    # ════════════════════════════════════════════════════════════
    #  TREE ITEMS
    # ════════════════════════════════════════════════════════════

    def _item_click(self, item, _):
        d = item.data(0, Qt.UserRole)
        if not d:
            return

        name = d.get("name", "?")
        is_dir = d.get("isDir", False)
        size = d.get("size", 0)
        ft = _ftype(name, is_dir)

        self.prev_title.setText(name)
        parts = [f"Type: {ft}"]
        if not is_dir:
            parts.append(f"Size: {_sz(size)}")
        self.prev_info.setText("   ".join(parts))
        self.sbar.showMessage(f"Selected: {name}")

        if not is_dir and is_image_file(name) and self._conn.is_server_connected:
            fp = d.get("full_path", "")
            if fp and size > 0:
                self._img_loader.load_preview(fp, name, size)
            else:
                self._set_preview_text("Cannot preview")
        elif not is_dir and is_video_file(name):
            self._set_preview_text("Video — double-click or press Play Media")
        elif not is_dir and is_audio_file(name):
            self._set_preview_text("Audio — double-click or press Play Media")
        elif is_dir:
            self._set_preview_text("Folder")
        else:
            self._set_preview_text(f"No preview for {ft}")

    def _item_dbl(self, item, _):
        d = item.data(0, Qt.UserRole)
        if not d:
            return

        if d.get("isDir"):
            if not self._conn.is_server_connected:
                self._log("Not connected")
                return
            path = d.get("full_path", "")
            if path:
                self._history.append(self._current_path)
                self._current_path = path
                self.path_edit.setText(path)
                self._conn.do_list(path)
        elif _is_media(d.get("name", "")):
            self._click_play_media()

    # ════════════════════════════════════════════════════════════
    #  PREVIEW
    # ════════════════════════════════════════════════════════════

    def _on_preview_loading(self, name):
        self._set_preview_text(f"Loading {name}...")

    def _on_preview_ready(self, pixmap, name):
        if pixmap.isNull():
            self._set_preview_text("Cannot display")
            return
        scaled = pixmap.scaled(
            self.prev_img.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.prev_img.setPixmap(scaled)
        self.prev_info.setText(f"{pixmap.width()} x {pixmap.height()} px")

    def _on_preview_error(self, msg):
        self._set_preview_text(f"Error: {msg}")

    def _clear_preview(self):
        self.prev_title.setText("Preview")
        self._set_preview_text("Select a file")
        self.prev_info.setText("")
        self._img_loader.clear()

    def _set_preview_text(self, text):
        self.prev_img.setPixmap(QPixmap())
        self.prev_img.setText(text)

    # ════════════════════════════════════════════════════════════
    #  MEDIA PLAYERS
    # ════════════════════════════════════════════════════════════

    def _on_media_dl_prog(self, done, total):
        if total > 0:
            self.progress.setValue(int(done * 100 / total))
            self.sbar.showMessage(f"Downloading: {_sz(done)} / {_sz(total)}")

    def _on_video_ready(self, path):
        self.progress.setVisible(False)
        self.sbar.showMessage(f"Playing: {os.path.basename(path)}")
        if self._video_player is None:
            self._video_player = VideoPlayerWindow()
            self._video_player.closed.connect(self._on_video_player_closed)
        self._video_player.play_file(path)

    def _on_video_player_closed(self):
        self._video_player = None

    def _on_audio_ready(self, path):
        self.progress.setVisible(False)
        self.sbar.showMessage(f"Playing: {os.path.basename(path)}")
        if self._audio_player is None:
            self._audio_player = AudioPlayerWindow()
            self._audio_player.closed.connect(self._on_audio_player_closed)
        self._audio_player.play_file(path)

    def _on_audio_player_closed(self):
        self._audio_player = None

    # ════════════════════════════════════════════════════════════
    #  STATUS
    # ════════════════════════════════════════════════════════════

    def _on_dev_status(self, s):
        if s == "device_detected":
            self.lbl_dev.setText("📱 Device detected")
            self.lbl_dev.setStyleSheet("color:#40d080; font-weight:600; margin-right:12px;")
        else:
            self.lbl_dev.setText("📱 No device")
            self.lbl_dev.setStyleSheet("color:#f44060; font-weight:600; margin-right:12px;")

    def _on_srv_status(self, s):
        if s == "connected":
            self.lbl_srv.setText("🖥 Server connected")
            self.lbl_srv.setStyleSheet("color:#40d080; font-weight:600;")
            self.btn_connect.setText("🔌 Disconnect")
            self.sbar.showMessage("Connected")
        elif s == "server_not_running":
            self.lbl_srv.setText("🖥 Server not running")
            self.lbl_srv.setStyleSheet("color:#f0a030; font-weight:600;")
            self.btn_connect.setText("🔗 Connect")
        else:
            self.lbl_srv.setText("🖥 Not connected")
            self.lbl_srv.setStyleSheet("color:#f44060; font-weight:600;")
            self.btn_connect.setText("🔗 Connect")

    def _on_dev_name(self, name):
        self.lbl_device.setText(f"📱 {name}")

    # ════════════════════════════════════════════════════════════
    #  DATA CALLBACKS
    # ════════════════════════════════════════════════════════════

    def _on_roots(self, result):
        self._current_path = None
        self._history.clear()
        self.path_edit.setText("")
        self.tree.clear()
        self._clear_preview()
        self.lbl_selection.setText("")

        for r in result.get("roots", []):
            path = r.get("path", "?")
            name = r.get("name", path)
            free = r.get("freeSpace", 0)
            total = r.get("totalSpace", 0)

            it = QTreeWidgetItem()
            it.setText(0, f"💾  {name}")
            it.setText(1, f"{_sz(free)} free")
            it.setText(2, "Storage")
            it.setText(3, f"Total: {_sz(total)}")
            it.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            it.setData(0, Qt.UserRole, {
                "isDir": True, "full_path": path, "name": name, "size": 0,
            })
            self.tree.addTopLevelItem(it)

    def _on_list(self, result):
        self.tree.clear()
        self._clear_preview()
        self.lbl_selection.setText("")

        if result.get("status") != "ok":
            self._log(f"LIST error: {result.get('msg', '?')}")
            return

        files = result.get("files", [])
        dirs = sorted(
            [f for f in files if f.get("isDir")],
            key=lambda x: x["name"].lower(),
        )
        nds = sorted(
            [f for f in files if not f.get("isDir")],
            key=lambda x: x["name"].lower(),
        )

        for f in dirs + nds:
            nm = f.get("name", "?")
            isd = f.get("isDir", False)
            sz = f.get("size", 0)
            mod = f.get("lastModified", 0)

            it = QTreeWidgetItem()
            it.setText(0, f"{_ficon(nm, isd)}  {nm}")
            it.setText(1, "—" if isd else _sz(sz))
            it.setText(2, _ftype(nm, isd))
            it.setText(3, _ts(mod))
            it.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)

            fp = f"{self._current_path}/{nm}" if self._current_path else nm
            it.setData(0, Qt.UserRole, {
                "isDir": isd, "full_path": fp, "name": nm, "size": sz,
            })
            self.tree.addTopLevelItem(it)

        self.sbar.showMessage(
            f"{self._current_path or '/'} — {len(dirs)} folders, {len(nds)} files"
        )

    # ════════════════════════════════════════════════════════════
    #  TRANSFER CALLBACKS
    # ════════════════════════════════════════════════════════════

    def _show_progress(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setMaximum(100)

    def _on_dl_prog(self, done, total):
        if total > 0:
            pct = int(done * 100 / total)
            self.progress.setValue(pct)
            if self._dl_queue:
                remaining = len(self._dl_queue)
                self.sbar.showMessage(
                    f"Downloading {self._dl_current_name}: "
                    f"{_sz(done)} / {_sz(total)} ({pct}%) — "
                    f"{remaining} more in queue"
                )
            else:
                self.sbar.showMessage(f"Download: {_sz(done)} / {_sz(total)} ({pct}%)")

    def _on_dl_done(self, path):
        # If there are more files in queue — download next
        if self._dl_queue:
            self._log(f"Done: {os.path.basename(path)}")
            self._start_next_download()
        else:
            self.progress.setVisible(False)
            self.sbar.showMessage(f"Downloaded: {path}")

    def _on_ul_prog(self, done, total):
        if total > 0:
            self.progress.setValue(int(done * 100 / total))
            self.sbar.showMessage(f"Upload: {_sz(done)} / {_sz(total)}")

    def _on_ul_done(self, remote):
        self.progress.setVisible(False)
        self.sbar.showMessage(f"Uploaded: {remote}")
        if self._current_path:
            self._conn.do_list(self._current_path)

    # ════════════════════════════════════════════════════════════
    #  HELPERS
    # ════════════════════════════════════════════════════════════

    def _update_preview_bg(self):
        t = self._settings.get("theme", "dark")
        bg = "#eaeaf4" if t == "light" else "#1a1a2e"
        self.prev_img.setStyleSheet(f"background-color:{bg}; border-radius:6px;")