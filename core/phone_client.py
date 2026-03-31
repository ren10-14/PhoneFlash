"""
TCP-клиент к Android-серверу PhoneFlash.

Схема:
  adb forward tcp:8888 tcp:8888
  Python → socket 127.0.0.1:8888 → ADB → USB → Android app

Протокол (совпадает с Java DataOutputStream):
  [4 байта big-endian int] длина JSON
  [JSON UTF-8]             заголовок
  [N байт]                 данные (если dataLength > 0)
"""
import json
import socket
import struct
import threading
from typing import Optional, Tuple

from PySide6.QtCore import QObject, Signal


class PhoneClient:
    """
    Синхронный TCP-клиент. Thread-safe (Lock).
    Вызывать из фоновых потоков.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    # ── Соединение ──────────────────────────────────────────────

    def connect(self, timeout: float = 5.0):
        """Открывает TCP к 127.0.0.1:port (ADB forward уже должен быть)."""
        with self._lock:
            self._close_unsafe()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                s.connect((self.host, self.port))
            except Exception:
                s.close()
                raise
            s.settimeout(60.0)
            self._sock = s

    def close(self):
        with self._lock:
            self._close_unsafe()

    def _close_unsafe(self):
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    # ── Протокол ────────────────────────────────────────────────

    def _send(self, header: dict, payload: bytes = b""):
        if self._sock is None:
            raise ConnectionError("Not connected")
        raw_json = json.dumps(header, ensure_ascii=False).encode("utf-8")
        # struct.pack(">I") = Java DataOutputStream.writeInt()
        self._sock.sendall(struct.pack(">I", len(raw_json)))
        self._sock.sendall(raw_json)
        if payload:
            self._sock.sendall(payload)

    def _recv_exact(self, n: int) -> bytes:
        if self._sock is None:
            raise ConnectionError("Not connected")
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(min(n - len(buf), 65536))
            if not chunk:
                raise ConnectionError("Connection closed by phone")
            buf.extend(chunk)
        return bytes(buf)

    def _recv(self) -> Tuple[dict, bytes]:
        # 4 байта = длина JSON (big-endian int, как Java writeInt)
        raw_len = self._recv_exact(4)
        header_len = struct.unpack(">I", raw_len)[0]

        if header_len <= 0 or header_len > 10 * 1024 * 1024:
            raise ValueError(f"Invalid header length: {header_len}")

        raw_header = self._recv_exact(header_len)
        header = json.loads(raw_header.decode("utf-8"))

        # Бинарные данные (если сервер указал dataLength)
        data = b""
        data_len = header.get("dataLength", 0)
        if data_len > 0:
            data = self._recv_exact(data_len)

        return header, data

    def _command(self, header: dict, payload: bytes = b"") -> Tuple[dict, bytes]:
        """Отправить → получить. Thread-safe."""
        with self._lock:
            self._send(header, payload)
            return self._recv()

    # ── Команды (соответствуют Android FileServer) ──────────────

    def ping(self) -> dict:
        resp, _ = self._command({"cmd": "PING"})
        return resp

    def roots(self) -> dict:
        resp, _ = self._command({"cmd": "ROOTS"})
        return resp

    def list_dir(self, path: str) -> dict:
        resp, _ = self._command({"cmd": "LIST", "path": path})
        return resp

    def info(self, path: str) -> dict:
        resp, _ = self._command({"cmd": "INFO", "path": path})
        return resp

    def read_chunk(self, path: str, offset: int = 0,
                   length: int = 1048576) -> Tuple[dict, bytes]:
        """READ — один чанк файла."""
        resp, data = self._command({
            "cmd": "READ",
            "path": path,
            "offset": offset,
            "length": length,
        })
        return resp, data

    def write_chunk(self, path: str, data: bytes,
                    offset: int = 0, truncate: bool = False) -> dict:
        """WRITE — один чанк в файл."""
        header = {
            "cmd": "WRITE",
            "path": path,
            "offset": offset,
            "truncate": truncate,
            "dataLength": len(data),
        }
        resp, _ = self._command(header, data)
        return resp

    def delete(self, path: str) -> dict:
        resp, _ = self._command({"cmd": "DELETE", "path": path})
        return resp

    def mkdir(self, path: str) -> dict:
        resp, _ = self._command({"cmd": "MKDIR", "path": path})
        return resp

    def rename(self, old_path: str, new_path: str) -> dict:
        # Android: h.getString("path") и h.getString("newPath")
        resp, _ = self._command({
            "cmd": "RENAME",
            "path": old_path,
            "newPath": new_path,
        })
        return resp


# ── Async обёртка ───────────────────────────────────────────────

class AsyncPhoneCall(QObject):
    """Запускает метод PhoneClient в threading.Thread."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, client: PhoneClient, method: str, *args, parent=None):
        super().__init__(parent)
        self._client = client
        self._method = method
        self._args = args

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            fn = getattr(self._client, self._method)
            result = fn(*self._args)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))