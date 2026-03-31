"""
ConnectionManager — full connection cycle.
"""
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.adb_manager import AdbManager, AdbDevice
from core.phone_client import PhoneClient, AsyncPhoneCall
from core.file_transfer import FileTransferManager


class ConnectionManager(QObject):

    log                   = Signal(str)
    device_status_changed = Signal(str)
    server_status_changed = Signal(str)
    device_name_changed   = Signal(str)
    devices_listed        = Signal(list)
    ping_result           = Signal(dict)
    roots_result          = Signal(dict)
    list_result           = Signal(dict)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._port = settings.get("server_port", 8888)

        adb_path = settings.get("adb_path", "adb")
        self.adb = AdbManager(adb_path, parent=self)
        self.client = PhoneClient("127.0.0.1", self._port)
        self.transfer = FileTransferManager(self.client, parent=self)

        self._device_status = "no_device"
        self._server_status = "not_connected"
        self._selected_device: Optional[AdbDevice] = None
        self._auto_connect = False
        self._async_calls: list = []

        self.adb.adb_checked.connect(self._on_adb_checked)
        self.adb.devices_ready.connect(self._on_devices)
        self.adb.forward_done.connect(self._on_forward)
        self.adb.error.connect(self._on_adb_error)
        self.adb.raw_output.connect(self._on_raw)
        self.transfer.log.connect(self.log.emit)

    @property
    def is_server_connected(self) -> bool:
        return self._server_status == "connected"

    def update_settings(self):
        self.adb.set_adb_path(self._settings.get("adb_path", "adb"))
        self._port = self._settings.get("server_port", 8888)
        self.client.port = self._port

    # ════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ════════════════════════════════════════════════════════════

    def check_adb(self):
        self.log.emit("Checking ADB...")
        self.adb.check_adb()

    def request_devices(self):
        self.log.emit("Scanning for devices...")
        self._auto_connect = False
        self.adb.request_devices()

    def do_connect(self):
        self.log.emit("═══════════════════════════════════════")
        self.log.emit("CONNECTION — starting")
        self.log.emit("═══════════════════════════════════════")
        self.log.emit("Step 1/5: Searching for device (adb devices)...")
        self._auto_connect = True
        self.adb.request_devices()

    def do_disconnect(self):
        """Disconnect in background thread to avoid UI freeze."""
        self.log.emit("Disconnecting...")
        self._set_server("not_connected")
        threading.Thread(target=self._bg_disconnect, daemon=True).start()

    def _bg_disconnect(self):
        """Background disconnect — socket close can block."""
        try:
            self.client.close()
        except Exception:
            pass
        self.log.emit("Disconnected")

    def do_ping(self):
        if not self._ensure_connected():
            return
        self.log.emit("PING...")
        self._async_call("ping", callback=self._on_ping)

    def do_roots(self):
        if not self._ensure_connected():
            return
        self.log.emit("ROOTS...")
        self._async_call("roots", callback=self._on_roots)

    def do_list(self, path: str):
        if not self._ensure_connected():
            return
        self.log.emit(f"LIST: {path}")
        self._async_call("list_dir", path, callback=self._on_list)

    # ════════════════════════════════════════════════════════════
    #  INTERNAL
    # ════════════════════════════════════════════════════════════

    def _set_device(self, status: str):
        if status != self._device_status:
            self._device_status = status
            self.device_status_changed.emit(status)

    def _set_server(self, status: str):
        if status != self._server_status:
            self._server_status = status
            self.server_status_changed.emit(status)

    def _ensure_connected(self) -> bool:
        if not self.client.is_connected:
            self.log.emit("Not connected. Press Connect.")
            return False
        return True

    def _async_call(self, method: str, *args, callback=None):
        call = AsyncPhoneCall(self.client, method, *args, parent=self)
        if callback:
            call.finished.connect(callback)
        call.error.connect(self._on_call_error)
        self._async_calls.append(call)
        call.finished.connect(lambda: self._drop_call(call))
        call.error.connect(lambda: self._drop_call(call))
        call.start()

    def _drop_call(self, call):
        if call in self._async_calls:
            self._async_calls.remove(call)

    def _on_call_error(self, msg: str):
        self.log.emit(f"Error: {msg}")
        low = msg.lower()
        if any(w in low for w in ("not connected", "connection", "closed", "broken")):
            self._set_server("not_connected")

    # ════════════════════════════════════════════════════════════
    #  ADB CALLBACKS
    # ════════════════════════════════════════════════════════════

    def _on_adb_error(self, msg: str):
        self.log.emit(f"ADB error: {msg}")
        if self._auto_connect:
            self._auto_connect = False

    def _on_raw(self, msg: str):
        self.log.emit(f"<pre style='margin:2px 0; color:#888'>{msg}</pre>")

    def _on_adb_checked(self, found: bool, info: str):
        self.log.emit(f"ADB: {'OK' if found else 'NOT FOUND'} — {info}")

    def _on_devices(self, devices: list):
        if devices:
            self.log.emit(f"Devices found: {len(devices)}")
            for d in devices:
                icon = "OK" if d.is_online else "WARN"
                self.log.emit(f"   [{icon}] {d}")
        else:
            self.log.emit("No devices found")

        self.devices_listed.emit(devices)

        online = [d for d in devices if d.is_online]
        if online:
            self._set_device("device_detected")
        else:
            self._set_device("no_device")
            if devices:
                self.log.emit("   Devices exist but none has 'device' status")
                self.log.emit("   Confirm USB debugging on your phone")
            else:
                self.log.emit("   Connect phone via USB and enable USB debugging")

        if not self._auto_connect:
            return

        if not online:
            self._auto_connect = False
            self.log.emit("Connection aborted: no online devices")
            return

        self._selected_device = online[0]
        self.device_name_changed.emit(str(self._selected_device))
        self.log.emit(f"   Selected: {self._selected_device}")
        self.log.emit(f"Step 2/5: adb forward tcp:{self._port} tcp:{self._port}...")
        self.adb.request_forward(
            self._selected_device.serial,
            self._port,
            self._port,
        )

    def _on_forward(self, success: bool, msg: str):
        if not success:
            self._auto_connect = False
            self.log.emit(f"Forward failed: {msg}")
            return

        self.log.emit(f"   Forward OK: {msg}")

        if not self._auto_connect:
            return

        self.log.emit(f"Step 3/5: TCP connect to 127.0.0.1:{self._port}...")
        threading.Thread(target=self._bg_connect_ping_roots, daemon=True).start()

    def _bg_connect_ping_roots(self):
        # Step 3: TCP
        try:
            self.client.connect(timeout=5.0)
        except ConnectionRefusedError:
            self._auto_connect = False
            self._set_server("server_not_running")
            self.log.emit("Connection refused!")
            self.log.emit("   Open PhoneFlash on phone and tap 'Start Server'")
            return
        except Exception as e:
            self._auto_connect = False
            self._set_server("server_not_running")
            self.log.emit(f"TCP error: {e}")
            return

        self.log.emit("   TCP connected to 127.0.0.1:8888")

        # Step 4: PING
        self.log.emit("Step 4/5: PING...")
        try:
            result = self.client.ping()
        except Exception as e:
            self._auto_connect = False
            self._set_server("server_not_running")
            self.log.emit(f"PING failed: {e}")
            return

        if result.get("status") != "ok":
            self._auto_connect = False
            self._set_server("server_not_running")
            self.log.emit(f"PING response: {result}")
            return

        self.log.emit("   PING OK")
        self._set_server("connected")
        self.ping_result.emit(result)

        # Step 5: ROOTS
        self.log.emit("Step 5/5: ROOTS...")
        self._auto_connect = False

        try:
            result = self.client.roots()
        except Exception as e:
            self.log.emit(f"ROOTS failed: {e}")
            return

        roots = result.get("roots", [])
        self.log.emit(f"   ROOTS: {len(roots)} storage(s)")
        for r in roots:
            name = r.get("name", r.get("path", "?"))
            path = r.get("path", "?")
            free = r.get("freeSpace", 0)
            total = r.get("totalSpace", 0)
            free_gb = free / (1024 ** 3) if free > 0 else 0
            total_gb = total / (1024 ** 3) if total > 0 else 0
            self.log.emit(f"   {name}: {path}")
            self.log.emit(f"      {free_gb:.1f} GB free / {total_gb:.1f} GB total")

        self.log.emit("═══════════════════════════════════════")
        self.log.emit("CONNECTION SUCCESSFUL!")
        self.log.emit("═══════════════════════════════════════")

        self.roots_result.emit(result)

    def _on_ping(self, result: dict):
        s = result.get("status", "?")
        self.log.emit(f"PING: {'OK' if s == 'ok' else result}")
        self.ping_result.emit(result)

    def _on_roots(self, result: dict):
        roots = result.get("roots", [])
        self.log.emit(f"ROOTS: {len(roots)} storage(s)")
        for r in roots:
            self.log.emit(f"   {r.get('name', '?')}: {r.get('path', '?')}")
        self.roots_result.emit(result)

    def _on_list(self, result: dict):
        status = result.get("status", "?")
        files = result.get("files", [])
        dirs = sum(1 for f in files if f.get("isDir"))
        fls = len(files) - dirs
        self.log.emit(f"LIST ({status}): {dirs} folders, {fls} files")

        if len(files) == 0 and status == "ok":
            self.log.emit("   Empty directory or permission denied")

        if status == "error":
            self.log.emit(f"   Server error: {result.get('msg', '?')}")

        self.list_result.emit(result)