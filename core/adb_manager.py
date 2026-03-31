"""
ADB Manager — works in both .py and .exe modes.
"""
import subprocess
import shutil
import os
import sys
import threading
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QObject, Signal


def _get_base_dir() -> str:
    """Base directory for resources."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


BUNDLED_ADB = os.path.join(_get_base_dir(), "resources", "adb", "adb.exe")


def find_adb(preferred_path: str = "adb") -> Optional[str]:
    """Find adb.exe. Returns full path or None."""
    # 1. Explicit path from settings
    if preferred_path and preferred_path != "adb":
        if os.path.isfile(preferred_path):
            return os.path.abspath(preferred_path)

    # 2. Bundled
    if os.path.isfile(BUNDLED_ADB):
        return BUNDLED_ADB

    # 3. System PATH
    in_path = shutil.which("adb")
    if in_path:
        return in_path

    # 4. Standard SDK locations
    home = os.path.expanduser("~")
    candidates = []
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(env)
        if val:
            candidates.append(os.path.join(val, "platform-tools", "adb.exe"))
    candidates += [
        os.path.join(home, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


@dataclass
class AdbDevice:
    serial: str
    state: str
    model: str = ""

    @property
    def is_online(self) -> bool:
        return self.state == "device"

    def __str__(self):
        m = f" ({self.model})" if self.model else ""
        return f"{self.serial} [{self.state}]{m}"


class AdbManager(QObject):

    devices_ready = Signal(list)
    forward_done  = Signal(bool, str)
    adb_checked   = Signal(bool, str)
    error         = Signal(str)
    raw_output    = Signal(str)

    def __init__(self, adb_path_setting: str = "adb", parent=None):
        super().__init__(parent)
        self._setting_path = adb_path_setting
        self._resolved: Optional[str] = None

    def set_adb_path(self, path: str):
        self._setting_path = path
        self._resolved = None

    def get_adb_path(self) -> str:
        return self._setting_path

    def _resolve(self) -> bool:
        if self._resolved and os.path.isfile(self._resolved):
            return True
        self._resolved = find_adb(self._setting_path)
        return self._resolved is not None

    def _exec(self, args: list, timeout: int = 15) -> subprocess.CompletedProcess:
        cmd = [self._resolved] + args
        cwd = os.path.dirname(self._resolved)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    # ── Public ──────────────────────────────────────────────────

    def check_adb(self):
        threading.Thread(target=self._bg_check, daemon=True).start()

    def request_devices(self):
        threading.Thread(target=self._bg_devices, daemon=True).start()

    def request_forward(self, serial: str, local_port: int, remote_port: int):
        threading.Thread(
            target=self._bg_forward,
            args=(serial, local_port, remote_port),
            daemon=True,
        ).start()

    # ── Background ──────────────────────────────────────────────

    def _bg_check(self):
        if not self._resolve():
            self.adb_checked.emit(False, self._not_found_msg())
            return
        try:
            r = self._exec(["version"], timeout=10)
            self.raw_output.emit(f"$ \"{self._resolved}\" version\n{r.stdout.strip()}")
            if r.returncode == 0 and "Android Debug Bridge" in r.stdout:
                info = f"{r.stdout.strip().splitlines()[0]}\nPath: {self._resolved}"
                self.adb_checked.emit(True, info)
            else:
                self.adb_checked.emit(False, f"Unexpected: {r.stdout[:200]}")
        except Exception as e:
            self.adb_checked.emit(False, f"Error: {e}")

    def _bg_devices(self):
        if not self._resolve():
            self.error.emit(self._not_found_msg())
            return
        try:
            r = self._exec(["devices", "-l"], timeout=15)
            raw = f"$ \"{self._resolved}\" devices -l\n{r.stdout.strip()}"
            if r.stderr.strip():
                raw += f"\nSTDERR: {r.stderr.strip()}"
            self.raw_output.emit(raw)

            if r.returncode != 0:
                self.error.emit(f"adb devices failed: {r.stderr.strip()}")
                return

            devices: List[AdbDevice] = []
            for line in r.stdout.strip().splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                serial = parts[0]
                state = parts[1]
                model = ""
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                        break
                devices.append(AdbDevice(serial=serial, state=state, model=model))

            self.devices_ready.emit(devices)
        except Exception as e:
            self.error.emit(f"adb devices error: {e}")

    def _bg_forward(self, serial: str, lp: int, rp: int):
        if not self._resolve():
            self.forward_done.emit(False, self._not_found_msg())
            return
        try:
            self._exec(["-s", serial, "forward", "--remove", f"tcp:{lp}"], timeout=5)
            r = self._exec(["-s", serial, "forward", f"tcp:{lp}", f"tcp:{rp}"], timeout=10)
            self.raw_output.emit(
                f"$ forward tcp:{lp} tcp:{rp}\nreturncode={r.returncode}"
            )
            if r.returncode == 0:
                self.forward_done.emit(True, f"{serial}: tcp:{lp} -> tcp:{rp}")
            else:
                self.forward_done.emit(False, r.stderr.strip() or "Unknown error")
        except Exception as e:
            self.forward_done.emit(False, f"Forward error: {e}")

    def _not_found_msg(self) -> str:
        return (
            f"ADB not found!\n"
            f"Setting: '{self._setting_path}'\n"
            f"Bundled: '{BUNDLED_ADB}' — {'EXISTS' if os.path.isfile(BUNDLED_ADB) else 'MISSING'}\n"
            f"Put adb.exe + DLLs in resources/adb/ or set path in Settings"
        )