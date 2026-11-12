# -*- coding: utf-8 -*-
"""Local settings: toolbar order, shortcuts, and parameters."""

import json

from qgis.PyQt.QtCore import QSettings


class SettingsStore:
    ROOT = "AttributeTablePlus"

    def __init__(self):
        self._s = QSettings()

    # ------------------------------------------------------------------
    # toolbar order / hidden buttons

    def load_toolbar_order(self):
        val = self._s.value(f"{self.ROOT}/toolbar_order")
        if not val:
            return None
        if isinstance(val, str):
            return [x for x in val.split(",") if x]
        try:
            return list(val)
        except Exception:
            return None

    def save_toolbar_order(self, order):
        # store as comma-separated for reliability across Qt versions
        self._s.setValue(f"{self.ROOT}/toolbar_order", ",".join(order))

    def load_toolbar_hidden(self):
        val = self._s.value(f"{self.ROOT}/toolbar_hidden")
        if not val:
            return []
        if isinstance(val, str):
            return [x for x in val.split(",") if x]
        try:
            return [str(x) for x in list(val) if x]
        except Exception:
            return []

    def save_toolbar_hidden(self, hidden):
        ids = []
        for item in hidden or []:
            text = str(item or "").strip()
            if text and text not in ids:
                ids.append(text)
        self._s.setValue(f"{self.ROOT}/toolbar_hidden", ",".join(ids))

    # ------------------------------------------------------------------
    # keyboard shortcuts: {tool_id: "Ctrl+K"}

    def load_shortcuts(self):
        raw = self._s.value(f"{self.ROOT}/shortcuts", "")
        if raw in (None, ""):
            return {}
        try:
            data = json.loads(str(raw))
        except (TypeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(key): str(value)
            for key, value in data.items()
            if str(value or "").strip()
        }

    def save_shortcuts(self, shortcuts):
        clean = {
            str(key): str(value)
            for key, value in (shortcuts or {}).items()
            if str(key or "").strip() and str(value or "").strip()
        }
        self._s.setValue(
            f"{self.ROOT}/shortcuts", json.dumps(clean, ensure_ascii=False)
        )

    # ------------------------------------------------------------------
    # parameters (settings dialog, 参数 tab)

    def _flag(self, key, default):
        val = self._s.value(f"{self.ROOT}/{key}", default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        text = str(val or "").strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
        return bool(default)

    def _number(self, key, default, cast=float):
        val = self._s.value(f"{self.ROOT}/{key}", default)
        try:
            return cast(val)
        except (TypeError, ValueError):
            return cast(default)

    def load_show_line_length(self):
        """Bottom-center length of selected features. Off by default."""
        return self._flag("show_line_length", False)

    def save_show_line_length(self, on):
        self._s.setValue(f"{self.ROOT}/show_line_length", bool(on))

    def load_filter_follow_field(self):
        """Quick filter follows the current column on non-categorized layers."""
        return self._flag("filter_follow_field", True)

    def save_filter_follow_field(self, on):
        self._s.setValue(f"{self.ROOT}/filter_follow_field", bool(on))

    def load_quick_value_limit(self):
        """Max distinct values listed in the quick filter box."""
        limit = self._number("quick_value_limit", 400, int)
        return max(10, min(5000, limit))

    def save_quick_value_limit(self, limit):
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 400
        self._s.setValue(f"{self.ROOT}/quick_value_limit", max(10, min(5000, limit)))

    def load_line_dir_tolerance(self):
        """Line-direction check snap tolerance, meters."""
        tol = self._number("line_dir_tolerance", 0.6)
        return tol if tol > 0 else 0.6

    def save_line_dir_tolerance(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.6
        self._s.setValue(f"{self.ROOT}/line_dir_tolerance", value if value > 0 else 0.6)

    # Column header: "name" = field name only, "alias" = alias (or remark
    # label) when there is one, else the name, "both" = alias over name.
    HEADER_MODES = ("both", "alias", "name")

    def load_header_mode(self):
        val = str(self._s.value(f"{self.ROOT}/header_mode", "both") or "").strip()
        return val if val in self.HEADER_MODES else "both"

    def save_header_mode(self, mode):
        mode = str(mode or "").strip()
        self._s.setValue(f"{self.ROOT}/header_mode", mode if mode in self.HEADER_MODES else "both")

    # Edit-mode fill method the window opens with. "remember" reopens the
    # method used last; the others are the fill-bar methods themselves.
    FILL_MODES = ("const", "around_seq", "affix", "expr", "replace")

    def load_fill_mode_default(self):
        val = str(self._s.value(f"{self.ROOT}/fill_mode_default", "remember") or "").strip()
        return val if val == "remember" or val in self.FILL_MODES else "remember"

    def save_fill_mode_default(self, mode):
        mode = str(mode or "").strip()
        if mode != "remember" and mode not in self.FILL_MODES:
            mode = "remember"
        self._s.setValue(f"{self.ROOT}/fill_mode_default", mode)

    def load_fill_mode_last(self):
        val = str(self._s.value(f"{self.ROOT}/fill_mode_last", "const") or "").strip()
        return val if val in self.FILL_MODES else "const"

    def save_fill_mode_last(self, mode):
        mode = str(mode or "").strip()
        if mode in self.FILL_MODES:
            self._s.setValue(f"{self.ROOT}/fill_mode_last", mode)

    def startup_fill_mode(self):
        mode = self.load_fill_mode_default()
        return self.load_fill_mode_last() if mode == "remember" else mode
