# -*- coding: utf-8 -*-
"""Full free-start line direction check (pick one start, several line layers)."""


class _Log(object):
    def __init__(self):
        self.text = ""

    def setPlainText(self, text):
        self.text = text or ""


class _Host(object):
    def __init__(self, iface):
        self.iface = iface
        self.log = _Log()
        self.layers = {}
        self.tolerance = 0.6
        try:
            from qgis.core import QgsSettings

            raw = QgsSettings().value("AttributeTablePlus/line_dir_tolerance", 0.6)
            self.tolerance = float(raw)
        except Exception:
            self.tolerance = 0.6
        if self.tolerance <= 0:
            self.tolerance = 0.6

    def _refresh_canvas(self):
        try:
            canvas = self.iface.mapCanvas()
            canvas.refresh()
        except Exception:
            pass  # nosec B110


class LineDirDialog(object):
    @staticmethod
    def open_for(iface, parent=None):
        from .line_dir.ntal_line_dir_free import open_free_line_dir

        host = _Host(iface)
        host.ui_parent = parent
        open_free_line_dir(host)
