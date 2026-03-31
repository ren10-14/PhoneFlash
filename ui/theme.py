"""
Темы PhoneFlash — Dark и Light.
"""
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtCore import Qt


# ═══════════════════════════════════════════════════════════════
#  DARK THEME
# ═══════════════════════════════════════════════════════════════

_DARK = {
    "BG_DARK":      "#1e1e2e",
    "BG_MID":       "#252536",
    "BG_LIGHT":     "#2e2e42",
    "BG_INPUT":     "#313147",
    "BORDER":       "#3c3c5c",
    "ACCENT":       "#7c6ff7",
    "ACCENT_HOVER": "#9a8dfc",
    "ACCENT_PRESS": "#5f54c4",
    "TEXT":         "#e0e0e8",
    "TEXT_DIM":     "#9090a8",
    "TEXT_BRIGHT":  "#ffffff",
    "DANGER":       "#f44060",
    "SUCCESS":      "#40d080",
    "WARNING":      "#f0a030",
    "SCROLLBAR":    "#404060",
    "SELECTION_BG": "#3d3a6e",
    "LOG_BG":       "#1a1a2e",
    "PREVIEW_BG":   "#1a1a2e",
}

# ═══════════════════════════════════════════════════════════════
#  LIGHT THEME
# ═══════════════════════════════════════════════════════════════

_LIGHT = {
    "BG_DARK":      "#f0f0f5",
    "BG_MID":       "#ffffff",
    "BG_LIGHT":     "#e8e8f0",
    "BG_INPUT":     "#ffffff",
    "BORDER":       "#c0c0d0",
    "ACCENT":       "#6c5ce7",
    "ACCENT_HOVER": "#7f70f0",
    "ACCENT_PRESS": "#5540c0",
    "TEXT":         "#2c2c3a",
    "TEXT_DIM":     "#6c6c80",
    "TEXT_BRIGHT":  "#ffffff",
    "DANGER":       "#e03050",
    "SUCCESS":      "#30b060",
    "WARNING":      "#d09020",
    "SCROLLBAR":    "#b0b0c0",
    "SELECTION_BG": "#d0d0f0",
    "LOG_BG":       "#f8f8ff",
    "PREVIEW_BG":   "#eaeaf4",
}

THEMES = {"dark": _DARK, "light": _LIGHT}


def _build_stylesheet(c: dict) -> str:
    return f"""
/* ── Глобальные ── */
QWidget {{
    background-color: {c['BG_DARK']};
    color: {c['TEXT']};
    font-size: 13px;
}}
QMainWindow {{
    background-color: {c['BG_DARK']};
}}

/* ── Кнопки ── */
QPushButton {{
    background-color: {c['BG_LIGHT']};
    color: {c['TEXT']};
    border: 1px solid {c['BORDER']};
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 28px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['ACCENT']};
    color: {c['TEXT_BRIGHT']};
    border-color: {c['ACCENT']};
}}
QPushButton:pressed {{
    background-color: {c['ACCENT_PRESS']};
}}
QPushButton:disabled {{
    background-color: {c['BG_MID']};
    color: {c['TEXT_DIM']};
    border-color: {c['BG_MID']};
}}

QPushButton[accent="true"] {{
    background-color: {c['ACCENT']};
    color: {c['TEXT_BRIGHT']};
    border: 1px solid {c['ACCENT']};
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{
    background-color: {c['ACCENT_HOVER']};
    border-color: {c['ACCENT_HOVER']};
}}
QPushButton[accent="true"]:pressed {{
    background-color: {c['ACCENT_PRESS']};
}}

/* ── QLineEdit ── */
QLineEdit {{
    background-color: {c['BG_INPUT']};
    color: {c['TEXT']};
    border: 1px solid {c['BORDER']};
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: {c['ACCENT']};
}}
QLineEdit:focus {{
    border-color: {c['ACCENT']};
}}

/* ── QComboBox ── */
QComboBox {{
    background-color: {c['BG_INPUT']};
    color: {c['TEXT']};
    border: 1px solid {c['BORDER']};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 28px;
}}
QComboBox:hover {{
    border-color: {c['ACCENT']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['BG_MID']};
    color: {c['TEXT']};
    border: 1px solid {c['BORDER']};
    selection-background-color: {c['SELECTION_BG']};
}}

/* ── QTreeWidget / QListWidget ── */
QTreeWidget, QListWidget, QTableWidget {{
    background-color: {c['BG_MID']};
    alternate-background-color: {c['BG_LIGHT']};
    border: 1px solid {c['BORDER']};
    border-radius: 6px;
    outline: none;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {c['SELECTION_BG']};
    color: {c['TEXT_BRIGHT'] if c is _DARK else c['TEXT']};
}}
QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {c['BG_LIGHT']};
}}
QHeaderView::section {{
    background-color: {c['BG_LIGHT']};
    color: {c['TEXT_DIM']};
    border: none;
    border-bottom: 1px solid {c['BORDER']};
    padding: 6px 10px;
    font-weight: 600;
    font-size: 12px;
}}

/* ── QTextEdit (логи) ── */
QTextEdit {{
    background-color: {c['LOG_BG']};
    color: {c['TEXT_DIM']};
    border: 1px solid {c['BORDER']};
    border-radius: 6px;
    padding: 6px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}}

/* ── QSplitter ── */
QSplitter::handle {{
    background-color: {c['BORDER']};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ── QLabel ── */
QLabel {{
    background-color: transparent;
    color: {c['TEXT']};
}}
QLabel[dim="true"] {{
    color: {c['TEXT_DIM']};
    font-size: 12px;
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {c['BG_DARK']};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {c['SCROLLBAR']};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['ACCENT']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {c['BG_DARK']};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {c['SCROLLBAR']};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c['ACCENT']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {c['BORDER']};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {c['TEXT_DIM']};
}}

/* ── StatusBar ── */
QStatusBar {{
    background-color: {c['BG_MID']};
    color: {c['TEXT_DIM']};
    border-top: 1px solid {c['BORDER']};
    font-size: 12px;
}}

/* ── ToolTip ── */
QToolTip {{
    background-color: {c['BG_LIGHT']};
    color: {c['TEXT']};
    border: 1px solid {c['BORDER']};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── Dialog ── */
QDialog {{
    background-color: {c['BG_DARK']};
}}

/* ── Frame карточка ── */
QFrame[card="true"] {{
    background-color: {c['BG_MID']};
    border: 1px solid {c['BORDER']};
    border-radius: 8px;
}}
"""


def _build_palette(c: dict) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(c["BG_DARK"]))
    p.setColor(QPalette.WindowText,      QColor(c["TEXT"]))
    p.setColor(QPalette.Base,            QColor(c["BG_MID"]))
    p.setColor(QPalette.AlternateBase,   QColor(c["BG_LIGHT"]))
    p.setColor(QPalette.ToolTipBase,     QColor(c["BG_LIGHT"]))
    p.setColor(QPalette.ToolTipText,     QColor(c["TEXT"]))
    p.setColor(QPalette.Text,            QColor(c["TEXT"]))
    p.setColor(QPalette.Button,          QColor(c["BG_LIGHT"]))
    p.setColor(QPalette.ButtonText,      QColor(c["TEXT"]))
    p.setColor(QPalette.BrightText,      QColor(c["TEXT_BRIGHT"]))
    p.setColor(QPalette.Highlight,       QColor(c["ACCENT"]))
    p.setColor(QPalette.HighlightedText, QColor(c["TEXT_BRIGHT"]))
    p.setColor(QPalette.Link,            QColor(c["ACCENT"]))
    return p


def apply_theme(app: QApplication, theme_name: str = "dark"):
    """Применяет тему (dark / light) ко всему приложению."""
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    colors = THEMES.get(theme_name, _DARK)
    app.setPalette(_build_palette(colors))
    app.setStyleSheet(_build_stylesheet(colors))


def get_accent_color(theme_name: str = "dark") -> str:
    colors = THEMES.get(theme_name, _DARK)
    return colors["ACCENT"]