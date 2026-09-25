# -*- coding: utf-8 -*-
"""Local settings: toolbar button order only."""

from qgis.PyQt.QtCore import QSettings


class SettingsStore:
    ROOT = "AttributeTablePlus"

    def __init__(self):
        self._s = QSettings()

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

    def load_quick_name_toolbar(self):
        val = self._s.value(f"{self.ROOT}/quick_name_toolbar", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        text = str(val or "").strip().lower()
        return text in ("1", "true", "yes", "on")

    def save_quick_name_toolbar(self, on):
        self._s.setValue(f"{self.ROOT}/quick_name_toolbar", bool(on))
