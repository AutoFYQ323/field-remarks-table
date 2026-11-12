# -*- coding: utf-8 -*-
"""Combo boxes whose open list shows the full item text."""

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QComboBox


def open_full_text_popup(combo):
    """The closed box stays narrow. The open list grows to the longest item.

    The first open used to keep a blank row: the list was still narrow, so Qt
    reserved a horizontal scrollbar and that strip looked like an extra item.
    The list is widened before it is shown, and its height is the real rows.
    """
    view = combo.view()
    metrics = view.fontMetrics()
    advance = getattr(metrics, "horizontalAdvance", None) or metrics.width
    width = combo.width()
    count = combo.count()
    for row in range(count):
        text = combo.itemText(row)
        if not text:
            continue
        width = max(width, advance(text) + 56)
    cap = 720
    screen_h = 640
    try:
        screen = combo.screen()
        if screen is not None:
            geo = screen.availableGeometry()
            cap = max(280, int(geo.width() * 0.7))
            screen_h = max(160, int(geo.height() * 0.7))
    except Exception:
        cap = 720
    width = min(max(width, combo.width()), cap)

    def apply():
        view.setTextElideMode(Qt.TextElideMode.ElideNone)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setMinimumWidth(width)
        container = view.parentWidget()
        if container is None or count <= 0:
            return
        row_h = view.sizeHintForRow(0)
        if row_h <= 0:
            row_h = metrics.height() + 10
        frame = 8
        try:
            frame = container.frameWidth() * 2 + 6
        except Exception:
            frame = 8
        height = min(row_h * count + frame, screen_h)
        container.setMinimumWidth(width)
        container.setMaximumWidth(16777215)
        container.setMaximumHeight(16777215)
        container.resize(width, height)
        container.setMinimumHeight(height)
        container.setMaximumHeight(height)

    view.setMinimumWidth(width)
    QComboBox.showPopup(combo)
    apply()
    # Qt sizes the popup to the closed box after showPopup returns.
    QTimer.singleShot(0, apply)


class WidePopupCombo(QComboBox):
    """Closed box stays narrow. The open list shows the full text, with a tooltip."""

    def addItem(self, text, userData=None):
        QComboBox.addItem(self, text, userData)
        shown = self.itemText(self.count() - 1)
        if shown:
            self.setItemData(self.count() - 1, shown, Qt.ItemDataRole.ToolTipRole)

    def showPopup(self):
        open_full_text_popup(self)
