# -*- coding: utf-8 -*-
"""Window themes shared by every plugin window.

"default" keeps the native QGIS look (no style sheet). Other themes are one
style sheet set on each top-level plugin window; child dialogs and message
boxes inherit it through their parent.
"""

from qgis.PyQt.QtCore import QSettings

SETTINGS_KEY = "AttributeTablePlus/theme"

THEME_ORDER = ("default", "pink", "mint")

THEME_LABELS = {
    "default": "默认（QGIS 原生）",
    "pink": "樱花粉",
    "mint": "薄荷清新",
}

THEME_ICONS = {
    "default": "plugin:theme_default_24.png",
    "pink": "plugin:theme_pink_24.png",
    "mint": "plugin:theme_mint_24.png",
}

# Text is always dark on light backgrounds; selection uses white on a colour
# dark enough for comfortable contrast (>= 4.5:1).
_PALETTES = {
    "pink": {
        "window": "#fff5f8",
        "panel": "#fde8ef",
        "base": "#ffffff",
        "alt": "#fff7fa",
        "text": "#4a2433",
        "muted": "#9a6b7d",
        "border": "#f2c4d3",
        "focus": "#e27a9e",
        "button": "#fdeaf1",
        "button_hover": "#fad6e3",
        "button_pressed": "#f6c1d4",
        "header": "#fbe0ea",
        "header_text": "#5a2139",
        "grid": "#f5dbe4",
        "hover": "#fbdbe6",
        "sel": "#c73a6f",
        "sel_text": "#ffffff",
        "track": "#fdf0f4",
        "handle": "#efbccd",
        "handle_hover": "#e38fae",
        "tooltip": "#fffafc",
        "accent": "#b0305f",
        "title": "#a3285a",
        "quick_bg": "#fdeef3",
        "quick_border": "#f2c4d3",
    },
    "mint": {
        "window": "#f4fbf9",
        "panel": "#e5f5f1",
        "base": "#ffffff",
        "alt": "#f6fcfa",
        "text": "#1e3b37",
        "muted": "#5d7d78",
        "border": "#bfe3db",
        "focus": "#4fb3a3",
        "button": "#e8f6f2",
        "button_hover": "#d3eee7",
        "button_pressed": "#bfe5dc",
        "header": "#dff2ed",
        "header_text": "#1d4540",
        "grid": "#d9eee9",
        "hover": "#d9f0ea",
        "sel": "#247d71",
        "sel_text": "#ffffff",
        "track": "#eef8f5",
        "handle": "#b5dfd6",
        "handle_hover": "#86cabd",
        "tooltip": "#fbfffe",
        "accent": "#1f7a6e",
        "title": "#1a6b60",
        "quick_bg": "#eaf7f3",
        "quick_border": "#bfe3db",
    },
}

# Colours the code needs in the native theme (matching the pre-theme look).
_DEFAULT_COLORS = {
    "title": "#0d47a1",
    "hover": "#d6e9ff",
    "quick_bg": "#e8f0e4",
    "quick_border": "#b7c9b0",
}

_SHEET_TEMPLATE = """
QDialog, QMessageBox, QInputDialog {{ background-color: {window}; color: {text}; }}
QLabel, QCheckBox, QRadioButton, QGroupBox {{ color: {text}; }}
QGroupBox::title {{ color: {accent}; }}

QToolBar {{ background-color: {panel}; border: 1px solid {border}; border-radius: 4px; spacing: 2px; padding: 1px; }}
QToolBar::separator {{ background-color: {border}; width: 1px; margin: 4px 3px; }}
QToolButton {{ background-color: transparent; color: {text}; border: 1px solid transparent; border-radius: 4px; padding: 2px; }}
QToolButton:hover {{ background-color: {button_hover}; border-color: {border}; }}
QToolButton:pressed, QToolButton:checked {{ background-color: {button_pressed}; border-color: {focus}; }}

QPushButton {{ background-color: {button}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 3px 12px; }}
QPushButton:hover {{ background-color: {button_hover}; border-color: {focus}; }}
QPushButton:pressed, QPushButton:checked {{ background-color: {button_pressed}; }}
QPushButton:default {{ border-color: {focus}; }}
QPushButton:disabled {{ color: {muted}; background-color: {panel}; border-color: {border}; }}

QLineEdit, QComboBox {{ background-color: {base}; color: {text}; border: 1px solid {border}; border-radius: 3px; selection-background-color: {sel}; selection-color: {sel_text}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {focus}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {muted}; background-color: {panel}; }}
QComboBox QAbstractItemView {{ background-color: {base}; color: {text}; border: 1px solid {border}; selection-background-color: {sel}; selection-color: {sel_text}; outline: 0; }}
QTableView QLineEdit, QTableView QComboBox, QTreeView QLineEdit, QListView QLineEdit {{ border: none; border-radius: 0; }}

QTextEdit, QPlainTextEdit, QTextBrowser, QListWidget, QListView, QTreeWidget, QTreeView, QTableWidget, QTableView {{
    background-color: {base}; color: {text}; border: 1px solid {border};
    alternate-background-color: {alt}; gridline-color: {grid};
    selection-background-color: {sel}; selection-color: {sel_text};
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{ background-color: {hover}; }}

QHeaderView {{ background-color: {header}; border: none; }}
QHeaderView::section {{ background-color: {header}; color: {header_text}; border: none; border-right: 1px solid {grid}; border-bottom: 1px solid {border}; padding: 2px 4px; }}
QHeaderView::section:vertical {{ border-right: 1px solid {border}; border-bottom: 1px solid {grid}; padding: 0 4px; }}
QHeaderView::section:checked {{ background-color: {button_pressed}; }}
QTableCornerButton::section {{ background-color: {header}; border: none; border-right: 1px solid {grid}; border-bottom: 1px solid {border}; }}

QScrollBar:vertical {{ background: {track}; width: 12px; margin: 0; border: none; }}
QScrollBar:horizontal {{ background: {track}; height: 12px; margin: 0; border: none; }}
QScrollBar::handle:vertical {{ background: {handle}; min-height: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {handle}; min-width: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {handle_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QTabWidget::pane {{ background-color: {window}; border: 1px solid {border}; border-radius: 3px; top: -1px; }}
QTabBar::tab {{ background-color: {button}; color: {text}; border: 1px solid {border}; padding: 4px 12px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
QTabBar::tab:selected {{ background-color: {window}; color: {accent}; border-bottom-color: {window}; }}
QTabBar::tab:hover:!selected {{ background-color: {button_hover}; }}

QScrollArea {{ background-color: transparent; border: 1px solid {border}; }}
QScrollArea > QWidget > QWidget {{ background-color: {window}; }}
QSplitter::handle {{ background-color: {border}; }}

QStatusBar {{ background-color: {panel}; color: {text}; border-top: 1px solid {border}; }}
QStatusBar::item {{ border: none; }}

QMenu {{ background-color: {base}; color: {text}; border: 1px solid {border}; padding: 3px 0; }}
QMenu::item {{ padding: 5px 16px 5px 28px; background-color: transparent; }}
QMenu::item:selected {{ background-color: {hover}; color: {text}; }}
QMenu::item:disabled {{ color: {muted}; }}
QMenu::separator {{ height: 1px; background-color: {border}; margin: 3px 8px; }}

QToolTip {{ background-color: {tooltip}; color: {text}; border: 1px solid {border}; padding: 3px; }}
"""

_windows = []


def current_theme():
    try:
        key = QSettings().value(SETTINGS_KEY, "default")
    except Exception:
        key = "default"
    key = str(key or "default")
    return key if key in THEME_LABELS else "default"


def color(role, theme=None):
    """Theme colour for code that paints its own widgets."""
    key = theme or current_theme()
    pal = _PALETTES.get(key)
    if pal is not None and role in pal:
        return pal[role]
    return _DEFAULT_COLORS.get(role, "")


def style_sheet(theme=None):
    pal = _PALETTES.get(theme or current_theme())
    if pal is None:
        return ""
    return _SHEET_TEMPLATE.format(**pal)


def _alive(widget):
    try:
        widget.objectName()
        return True
    except RuntimeError:
        return False


def apply(widget, theme=None):
    """Set the theme style sheet on one top-level window (and its children)."""
    if widget is None:
        return
    try:
        widget.setStyleSheet(style_sheet(theme))
    except RuntimeError:
        return
    hook = getattr(widget, "on_theme_changed", None)
    if callable(hook):
        try:
            hook()
        except Exception:
            pass


def register(widget):
    """Theme a top-level window now and whenever the theme changes."""
    _windows[:] = [w for w in _windows if _alive(w) and w is not widget]
    _windows.append(widget)
    apply(widget)


def set_theme(key):
    if key not in THEME_LABELS:
        key = "default"
    try:
        QSettings().setValue(SETTINGS_KEY, key)
    except Exception:
        pass
    _windows[:] = [w for w in _windows if _alive(w)]
    for w in list(_windows):
        apply(w, key)
