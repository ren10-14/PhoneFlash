"""
Диалог настроек PhoneFlash.
  - Тема (dark / light)
  - ADB path (с кнопкой Browse)
  - GitHub link
"""
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QGroupBox,
    QFormLayout, QFileDialog,
)

from core.adb_manager import find_adb


class SettingsDialog(QDialog):
    """Окно настроек."""

    theme_changed = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings — PhoneFlash")
        self.setMinimumSize(520, 440)
        self.resize(560, 480)
        self.setModal(True)

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("⚙  Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        # ── Appearance ──────────────────────────────────────────
        grp_appear = QGroupBox("Appearance")
        form_appear = QFormLayout(grp_appear)
        form_appear.setContentsMargins(16, 20, 16, 12)
        form_appear.setSpacing(10)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"])
        self.combo_theme.setMinimumWidth(180)
        form_appear.addRow("Theme:", self.combo_theme)

        layout.addWidget(grp_appear)

        # ── ADB ─────────────────────────────────────────────────
        grp_adb = QGroupBox("ADB")
        adb_layout = QVBoxLayout(grp_adb)
        adb_layout.setContentsMargins(16, 20, 16, 12)
        adb_layout.setSpacing(8)

        adb_label = QLabel("Path to adb.exe:")
        adb_layout.addWidget(adb_label)

        adb_row = QHBoxLayout()
        adb_row.setSpacing(6)

        self.edit_adb_path = QLineEdit()
        self.edit_adb_path.setPlaceholderText("adb  (или полный путь к adb.exe)")
        adb_row.addWidget(self.edit_adb_path, 1)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._browse_adb)
        adb_row.addWidget(self.btn_browse)

        self.btn_auto = QPushButton("Auto-detect")
        self.btn_auto.setCursor(Qt.PointingHandCursor)
        self.btn_auto.clicked.connect(self._auto_detect_adb)
        adb_row.addWidget(self.btn_auto)

        adb_layout.addLayout(adb_row)

        # Подсказка
        self.lbl_adb_status = QLabel("")
        self.lbl_adb_status.setProperty("dim", True)
        self.lbl_adb_status.setWordWrap(True)
        adb_layout.addWidget(self.lbl_adb_status)

        layout.addWidget(grp_adb)

        # ── About ───────────────────────────────────────────────
        grp_about = QGroupBox("About")
        about_layout = QVBoxLayout(grp_about)
        about_layout.setContentsMargins(16, 20, 16, 12)
        about_layout.setSpacing(8)

        self.lbl_github = QLabel()
        self.lbl_github.setOpenExternalLinks(True)
        self.lbl_github.setTextInteractionFlags(Qt.TextBrowserInteraction)
        about_layout.addWidget(self.lbl_github)

        version_lbl = QLabel("PhoneFlash PC  v0.3.0")
        version_lbl.setProperty("dim", True)
        about_layout.addWidget(version_lbl)

        layout.addWidget(grp_about)

        layout.addStretch()

        # ── Buttons ─────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save")
        self.btn_save.setProperty("accent", True)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_and_accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _load_values(self):
        # Theme
        theme = self._settings.get("theme", "dark")
        idx = self.combo_theme.findText(theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)

        # ADB path
        adb_path = self._settings.get("adb_path", "adb")
        self.edit_adb_path.setText(adb_path)

        # Проверяем статус
        self._check_adb_status(adb_path)

        # GitHub
        github = self._settings.get("github_link", "Ссылка")
        if github.startswith("http"):
            self.lbl_github.setText(
                f'GitHub: <a href="{github}" style="color:#7c6ff7;">{github}</a>'
            )
        else:
            self.lbl_github.setText(f"GitHub: {github}")

    def _browse_adb(self):
        """Открыть диалог выбора файла adb.exe."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select adb.exe",
            "",
            "ADB executable (adb.exe);;All files (*)",
        )
        if path:
            self.edit_adb_path.setText(path)
            self._check_adb_status(path)

    def _auto_detect_adb(self):
        """Автопоиск ADB в стандартных местах."""
        found = find_adb()
        if found:
            self.edit_adb_path.setText(found)
            self.lbl_adb_status.setText(f"✅ Найден: {found}")
            self.lbl_adb_status.setStyleSheet("color: #40d080;")
        else:
            self.lbl_adb_status.setText(
                "❌ ADB не найден автоматически.\n"
                "Установите Android SDK Platform Tools и укажите путь вручную."
            )
            self.lbl_adb_status.setStyleSheet("color: #f44060;")

    def _check_adb_status(self, path: str):
        """Показывает статус: найден ли adb по указанному пути."""
        if not path or path == "adb":
            found = find_adb()
            if found:
                self.lbl_adb_status.setText(f"ℹ 'adb' не в PATH, но найден: {found}")
                self.lbl_adb_status.setStyleSheet("color: #f0a030;")
            else:
                self.lbl_adb_status.setText("⚠ 'adb' не найден в PATH. Укажите полный путь.")
                self.lbl_adb_status.setStyleSheet("color: #f44060;")
        elif os.path.isfile(path):
            self.lbl_adb_status.setText(f"✅ Файл существует: {path}")
            self.lbl_adb_status.setStyleSheet("color: #40d080;")
        else:
            self.lbl_adb_status.setText(f"❌ Файл не найден: {path}")
            self.lbl_adb_status.setStyleSheet("color: #f44060;")

    def _save_and_accept(self):
        old_theme = self._settings.get("theme", "dark")
        new_theme = self.combo_theme.currentText()

        adb_path = self.edit_adb_path.text().strip()
        if not adb_path:
            adb_path = "adb"

        self._settings.set("theme", new_theme)
        self._settings.set("adb_path", adb_path)
        self._settings.save()

        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        self.accept()