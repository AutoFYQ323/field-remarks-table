# -*- coding: utf-8 -*-
"""Plugin class: toolbar + Vector menu + layer context menu entry."""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox
from .qt_compat import QAction

from qgis.core import QgsMapLayer, QgsProject
from .i18n import tr

PLUGIN_TITLE = "Field Remarks Table"
PLUGIN_MENU = "&Field Remarks Table"


class AttributeTablePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None
        self._legend_action = None
        self._legend_tip = None
        self._shortcut_carriers = []

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, PLUGIN_TITLE, self.iface.mainWindow())
        self.action.setObjectName("fieldRemarksTableAction")
        self.action.setToolTip(tr("Open Field Remarks Table / 打开字段备注表"))
        self.action.setStatusTip(tr("为当前矢量图层打开增强属性表"))
        self.action.triggered.connect(lambda: self.open_table())
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(PLUGIN_MENU, self.action)

        # Layer tree right-click entry
        try:
            ltv = self.iface.layerTreeView()
            if ltv is not None:
                self._legend_action = QAction(icon, PLUGIN_TITLE, ltv)
                self._legend_action.triggered.connect(lambda: self.open_table())
                ltv.contextMenuAboutToShow.connect(self._on_legend_menu)
        except Exception:
            self._legend_action = None

        try:
            from .remarks_dialog import LayerLegendTooltipFilter

            self._legend_tip = LayerLegendTooltipFilter(self.iface)
        except Exception:
            self._legend_tip = None

        try:
            QgsProject.instance().readProject.connect(self._on_project_read)
        except Exception:
            pass  # nosec B110
        self._on_project_read()
        self.apply_shortcuts()
        try:
            from .i18n import language_changed

            language_changed().connect(self._on_language_changed)
        except Exception:
            pass  # nosec B110
        self._on_language_changed()

    def _on_language_changed(self, *_args):
        if self.action is not None:
            self.action.setToolTip(tr("Open Field Remarks Table / 打开字段备注表"))
            self.action.setStatusTip(tr("为当前矢量图层打开增强属性表"))
        if self._legend_action is not None:
            self._legend_action.setText(PLUGIN_TITLE)
        self._retitle_temp_legend()

    def apply_shortcuts(self):
        """Hang the saved shortcuts on the QGIS main window.

        They fire whenever the main window has focus (table closed or not the
        active window). The table dialog carries its own copies while it is
        open, so the keys work with either window focused. Carriers carry the
        property atp_shortcut_id so conflict checks skip them.
        """
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtGui import QKeySequence

        from .settings_store import SettingsStore

        window = None
        try:
            window = self.iface.mainWindow()
        except Exception:
            window = None
        if window is None:
            return
        for act in self._shortcut_carriers:
            try:
                window.removeAction(act)
                act.deleteLater()
            except Exception:
                pass  # nosec B110
        self._shortcut_carriers = []
        try:
            from .settings_dialog import shortcut_holder

            for raw_id, raw_text in SettingsStore().load_shortcuts().items():
                tool_id = str(raw_id or "").strip()
                text = str(raw_text or "").strip()
                if not tool_id or not text:
                    continue
                seq = QKeySequence.fromString(text)
                if seq.isEmpty():
                    continue
                if shortcut_holder(text, tool_id):
                    # Taken by QGIS; the settings page already refused this,
                    # but stay silent here to avoid a warning on every start.
                    continue
                carrier = QAction(window)
                carrier.setProperty("atp_shortcut_id", tool_id)
                carrier.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
                carrier.setShortcut(seq)
                carrier.triggered.connect(
                    lambda _checked=False, t=tool_id: self._fire_tool(t)
                )
                window.addAction(carrier)
                self._shortcut_carriers.append(carrier)
        except Exception:
            pass  # nosec B110

    def _fire_tool(self, tool_id):
        """Shortcut fired from the main window: open the table, then run."""
        layer = None
        try:
            layer = self.iface.activeLayer()
        except Exception:
            layer = None
        self.open_table(layer)
        dlg = self.dialog
        if dlg is not None:
            try:
                dlg.fire_tool(tool_id)
            except Exception:
                pass  # nosec B110

    def _retitle_temp_legend(self, *_args):
        try:
            from .tools.line_dir.ntal_engine import retitle_temp_legend

            retitle_temp_legend()
        except Exception:
            pass  # nosec B110
        try:
            from .tools.field_map.layer_source import retitle_field_map_group

            retitle_field_map_group()
        except Exception:
            pass  # nosec B110

    def unload(self):
        try:
            from .i18n import language_changed

            language_changed().disconnect(self._on_language_changed)
        except Exception:
            pass  # nosec B110
        if self.dialog is not None:
            try:
                self.dialog.close()
            except Exception:
                pass  # nosec B110
            self.dialog = None
        window = None
        try:
            window = self.iface.mainWindow()
        except Exception:
            window = None
        if window is not None:
            for act in self._shortcut_carriers:
                try:
                    window.removeAction(act)
                    act.deleteLater()
                except Exception:
                    pass  # nosec B110
        self._shortcut_carriers = []
        try:
            from .remarks_dialog import RemarksHubDialog

            dlg = getattr(RemarksHubDialog, "_instance", None)
            if dlg is not None:
                try:
                    dlg.close()
                except Exception:
                    pass  # nosec B110
        except Exception:
            pass  # nosec B110
        if self.action is not None:
            try:
                self.iface.removePluginVectorMenu(PLUGIN_MENU, self.action)
            except Exception:
                pass  # nosec B110
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        try:
            ltv = self.iface.layerTreeView()
            if ltv is not None:
                ltv.contextMenuAboutToShow.disconnect(self._on_legend_menu)
        except Exception:
            pass  # nosec B110
        self._legend_action = None
        if self._legend_tip is not None:
            try:
                self._legend_tip.detach()
            except Exception:
                pass  # nosec B110
            self._legend_tip = None
        try:
            QgsProject.instance().readProject.disconnect(self._on_project_read)
        except Exception:
            pass  # nosec B110
        try:
            from .remarks_store import RemarksSession

            RemarksSession.reset_process()
        except Exception:
            pass  # nosec B110

    def _on_project_read(self, *_args):
        try:
            from .remarks_store import RemarksSession
            from .remarks_dialog import RemarksHubDialog

            hub = getattr(RemarksHubDialog, "_instance", None)
            try:
                if hub is not None:
                    hub.windowTitle()
            except Exception:
                hub = None
            session = None
            if self.dialog is not None:
                session = getattr(self.dialog, "_remarks", None)
            if session is None and hub is not None:
                session = getattr(hub, "session", None)
            if session is None:
                RemarksSession()
            else:
                session.absorb_project_packs()
            if hub is not None:
                hub._reload_combo()
                hub.reload_from_session()
                hub.packChanged.emit()
                hub._update_check_status()
            elif self.dialog is not None:
                self.dialog._apply_remarks_to_ui()
            self._retitle_temp_legend()
        except Exception:
            pass  # nosec B110

    def _on_legend_menu(self, menu):
        if self._legend_action is None:
            return
        layer = self.iface.activeLayer()
        if layer is None or layer.type() != QgsMapLayer.LayerType.VectorLayer:
            return
        menu.addSeparator()
        menu.addAction(self._legend_action)

    def open_table(self, layer=None):
        if layer is None:
            layer = self.iface.activeLayer()
        if layer is None or layer.type() != QgsMapLayer.LayerType.VectorLayer:
            QMessageBox.information(
                self.iface.mainWindow(),
                PLUGIN_TITLE,
                tr("请先选择一个矢量图层"),
            )
            return

        if self.dialog is None:
            from .dialog import AttributeTableDialog

            # Parent to QGIS main window: stay above QGIS when switching layers
            # (independent taskbar minimize dropped — conflicts with that z-order).
            self.dialog = AttributeTableDialog(
                self.iface, parent=self.iface.mainWindow()
            )
            self.dialog.finished.connect(self._on_dialog_finished)

        self.dialog.set_layer(layer)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _on_dialog_finished(self, _result):
        self.dialog = None
        # Settings may have changed while the table was open; refresh carriers.
        self.apply_shortcuts()
