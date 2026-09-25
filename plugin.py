# -*- coding: utf-8 -*-
"""Plugin class: toolbar + Vector menu + layer context menu entry."""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from qgis.core import QgsMapLayer, QgsProject

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

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, PLUGIN_TITLE, self.iface.mainWindow())
        self.action.setObjectName("fieldRemarksTableAction")
        self.action.setToolTip("Open Field Remarks Table / 打开字段备注表")
        self.action.setStatusTip(
            "Open an enhanced attribute table for the active vector layer"
        )
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
            pass
        self._on_project_read()

    def unload(self):
        if self.dialog is not None:
            try:
                self.dialog.close()
            except Exception:
                pass
            self.dialog = None
        try:
            from .remarks_dialog import QuickNameDialog, RemarksHubDialog

            for cls in (RemarksHubDialog, QuickNameDialog):
                dlg = getattr(cls, "_instance", None)
                if dlg is not None:
                    try:
                        dlg.close()
                    except Exception:
                        pass
        except Exception:
            pass
        if self.action is not None:
            try:
                self.iface.removePluginVectorMenu(PLUGIN_MENU, self.action)
            except Exception:
                pass
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        try:
            ltv = self.iface.layerTreeView()
            if ltv is not None:
                ltv.contextMenuAboutToShow.disconnect(self._on_legend_menu)
        except Exception:
            pass
        self._legend_action = None
        if self._legend_tip is not None:
            try:
                self._legend_tip.detach()
            except Exception:
                pass
            self._legend_tip = None
        try:
            QgsProject.instance().readProject.disconnect(self._on_project_read)
        except Exception:
            pass
        try:
            from .remarks_store import RemarksSession

            RemarksSession.reset_process()
        except Exception:
            pass

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
        except Exception:
            pass

    def _on_legend_menu(self, menu):
        if self._legend_action is None:
            return
        layer = self.iface.activeLayer()
        if layer is None or layer.type() != QgsMapLayer.VectorLayer:
            return
        menu.addSeparator()
        menu.addAction(self._legend_action)

    def open_table(self, layer=None):
        if layer is None:
            layer = self.iface.activeLayer()
        if layer is None or layer.type() != QgsMapLayer.VectorLayer:
            QMessageBox.information(
                self.iface.mainWindow(),
                PLUGIN_TITLE,
                "Please select a vector layer first.\n请先选择一个矢量图层。",
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
