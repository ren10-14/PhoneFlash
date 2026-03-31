"""
File transfer — download and upload in chunks.
"""
import os
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.phone_client import PhoneClient

CHUNK_SIZE = 1 * 1024 * 1024


class FileTransferManager(QObject):

    log               = Signal(str)
    download_progress = Signal(int, int)
    download_finished = Signal(str)
    upload_progress   = Signal(int, int)
    upload_finished   = Signal(str)

    def __init__(self, client: PhoneClient, parent=None):
        super().__init__(parent)
        self._client = client
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def download(self, remote_path: str, local_path: str, file_size: int):
        if self._busy:
            self.log.emit("Transfer already in progress, please wait")
            return
        self._busy = True
        threading.Thread(
            target=self._bg_download,
            args=(remote_path, local_path, file_size),
            daemon=True,
        ).start()

    def upload(self, local_path: str, remote_path: str):
        if self._busy:
            self.log.emit("Transfer already in progress, please wait")
            return
        self._busy = True
        threading.Thread(
            target=self._bg_upload,
            args=(local_path, remote_path),
            daemon=True,
        ).start()

    def _bg_download(self, remote, local, size):
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
            self.log.emit(f"Downloaded: {local}")
            self.download_finished.emit(local)
        except Exception as e:
            self.log.emit(f"Download error: {e}")
        finally:
            self._busy = False

    def _bg_upload(self, local, remote):
        try:
            file_size = os.path.getsize(local)
            offset = 0
            first = True
            with open(local, "rb") as f:
                while offset < file_size:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    resp = self._client.write_chunk(
                        remote, data=chunk, offset=offset, truncate=first,
                    )
                    first = False
                    if resp.get("status") != "ok":
                        self.log.emit(f"WRITE error: {resp}")
                        return
                    offset += len(chunk)
                    self.upload_progress.emit(offset, file_size)
            self.log.emit(f"Uploaded: {remote}")
            self.upload_finished.emit(remote)
        except Exception as e:
            self.log.emit(f"Upload error: {e}")
        finally:
            self._busy = False