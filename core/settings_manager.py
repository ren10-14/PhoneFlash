"""
Менеджер настроек — чтение/запись settings.json.
"""
import json
import os
from typing import Any


DEFAULT_SETTINGS = {
    "theme": "dark",
    "adb_path": "adb",
    "server_port": 8888,
    "github_link": "https://github.com/ren10-14/PhoneFlash",
}


class SettingsManager:
    def __init__(self, path: str):
        self._path = path
        self._data: dict = {}
        self._load()

    # ── public ──────────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Ошибка сохранения: {e}")

    def all(self) -> dict:
        return dict(self._data)

    # ── private ─────────────────────────────────────────────────
    def _load(self):
        self._data = dict(DEFAULT_SETTINGS)
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except Exception as e:
                print(f"[Settings] Ошибка чтения: {e}")