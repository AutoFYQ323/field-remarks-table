# -*- coding: utf-8 -*-
"""Full field-mapping copy: layers, saved map, file load, type coercion."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout

from ..i18n import language_changed, tr
from .field_map.transfer_tab import TransferTab
from .window_theme import register_tool_window


class FieldMapDialog(QDialog):
    _instance = None

    @classmethod
    def open_for(cls, iface, parent=None):
        dlg = cls._instance
        if dlg is not None:
            try:
                dlg.windowTitle()
            except RuntimeError:
                dlg = None
                cls._instance = None
        if dlg is None:
            dlg = cls(iface, parent)
            cls._instance = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def __init__(self, iface, parent=None):
        host = parent
        if host is None and iface is not None:
            try:
                host = iface.mainWindow()
            except Exception:
                host = None
        super().__init__(host)
        self.iface = iface
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(tr("字段映射复制"))
        self.resize(980, 700)
        self.setSizeGripEnabled(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.transfer_tab = TransferTab(self)
        layout.addWidget(self.transfer_tab)
        self.transfer_tab.refresh_layers()
        register_tool_window(self)
        try:
            language_changed().connect(self._apply_language)
        except Exception:
            pass  # nosec B110

    def _apply_language(self, *_args):
        self.setWindowTitle(tr("字段映射复制"))
        self.transfer_tab.apply_language()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.transfer_tab.refresh_layers()
        except Exception:
            pass  # nosec B110

    def closeEvent(self, event):
        try:
            language_changed().disconnect(self._apply_language)
        except Exception:
            pass  # nosec B110
        FieldMapDialog._instance = None
        super().closeEvent(event)
