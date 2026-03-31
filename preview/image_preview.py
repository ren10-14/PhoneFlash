"""
Image Preview — downloads image from phone and shows in UI.
"""
import os
import threading
import tempfile
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from core.phone_client import PhoneClient

MAX_PREVIEW_SIZE = 10 * 1024 * 1024

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    ".tiff", ".tif", ".ico",
}

PREVIEW_CACHE_DIR = os.path.join(tempfile.gettempdir(), "phoneflash_preview")


def is_image_file(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in IMAGE_EXTENSIONS


def _ensure_cache_dir():
    os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)


class ImagePreviewLoader(QObject):

    preview_ready = Signal(QPixmap, str)
    preview_error = Signal(str)
    loading_started = Signal(str)

    def __init__(self, client: PhoneClient, parent=None):
        super().__init__(parent)
        self._client = client
        self._current_file: Optional[str] = None
        self._loading = False

    @property
    def is_loading(self) -> bool:
        return self._loading

    def load_preview(self, remote_path: str, file_name: str, file_size: int):
        if file_size > MAX_PREVIEW_SIZE:
            self.preview_error.emit(f"File too large for preview: {file_size // 1024 // 1024} MB")
            return
        if file_size <= 0:
            self.preview_error.emit("File size is 0")
            return

        self._current_file = remote_path
        self._loading = True
        self.loading_started.emit(file_name)

        threading.Thread(
            target=self._bg_load,
            args=(remote_path, file_name, file_size),
            daemon=True,
        ).start()

    def _bg_load(self, remote_path, file_name, file_size):
        try:
            if self._current_file != remote_path:
                return

            _ensure_cache_dir()

            safe_name = remote_path.replace("/", "_").replace("\\", "_")
            if len(safe_name) > 100:
                safe_name = safe_name[-100:]
            cache_path = os.path.join(PREVIEW_CACHE_DIR, safe_name)

            if os.path.isfile(cache_path) and os.path.getsize(cache_path) == file_size:
                pixmap = self._load_pixmap(cache_path)
                if pixmap and self._current_file == remote_path:
                    self.preview_ready.emit(pixmap, file_name)
                    self._loading = False
                    return

            CHUNK = 1024 * 1024
            offset = 0
            with open(cache_path, "wb") as f:
                while offset < file_size:
                    if self._current_file != remote_path:
                        self._loading = False
                        return
                    length = min(CHUNK, file_size - offset)
                    resp, data = self._client.read_chunk(remote_path, offset, length)
                    if resp.get("status") != "ok":
                        self.preview_error.emit(f"READ error: {resp.get('msg', '?')}")
                        self._loading = False
                        return
                    if not data:
                        break
                    f.write(data)
                    offset += len(data)

            if self._current_file != remote_path:
                self._loading = False
                return

            pixmap = self._load_pixmap(cache_path)
            if pixmap:
                self.preview_ready.emit(pixmap, file_name)
            else:
                self.preview_error.emit("Cannot decode image")

        except Exception as e:
            if self._current_file == remote_path:
                self.preview_error.emit(str(e))
        finally:
            self._loading = False

    def _load_pixmap(self, path: str) -> Optional[QPixmap]:
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
            return pixmap
        except Exception:
            return None

    def clear(self):
        self._current_file = None