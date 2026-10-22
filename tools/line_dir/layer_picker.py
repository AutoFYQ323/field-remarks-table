# -*- coding: utf-8 -*-
from ...i18n import tr
from qgis.core import QgsCategorizedSymbolRenderer, QgsProject, QgsVectorLayer, NULL
from qgis.PyQt.QtCore import QEvent, QPoint, QRect, QTimer, Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
)


def attr_key(value):
    if value is None:
        return ""
    try:
        if value == NULL:
            return ""
    except Exception:
        pass  # nosec B110
    return str(value)


def _qt_const(group, name, fallback):
    holder = getattr(Qt, group, None)
    if holder is not None:
        value = getattr(holder, name, None)
        if value is not None:
            return value
    return getattr(Qt, fallback)


CHECKED = _qt_const("CheckState", "Checked", "Checked")
UNCHECKED = _qt_const("CheckState", "Unchecked", "Unchecked")
PARTIAL = _qt_const("CheckState", "PartiallyChecked", "PartiallyChecked")
ITEM_USER_CHECKABLE = _qt_const("ItemFlag", "ItemIsUserCheckable", "ItemIsUserCheckable")
USER_ROLE = _qt_const("ItemDataRole", "UserRole", "UserRole")
KEY_ESCAPE = _qt_const("Key", "Key_Escape", "Key_Escape")
try:
    MOUSE_PRESS = QEvent.Type.MouseButtonPress
    KEY_PRESS = QEvent.Type.KeyPress
except AttributeError:
    MOUSE_PRESS = QEvent.Type.MouseButtonPress
    KEY_PRESS = QEvent.Type.KeyPress
try:
    POPUP_FLAGS = Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
except AttributeError:
    POPUP_FLAGS = Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint


class LayerCheckCombo(QComboBox):
    """Multi-select layers; categorized layers expand so classes can be ticked."""

    def __init__(self, geom_type, parent=None):
        super(LayerCheckCombo, self).__init__(parent)
        self._geom_type = geom_type
        self._checked_names = []
        self._filters = {}
        self._changed_slot = None
        self._block = False
        self._filter_on = False
        self._suppress_outside = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(220)
        try:
            self.setEditable(True)
            self.lineEdit().setReadOnly(True)
            try:
                self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            except AttributeError:
                pass  # nosec B110
        except Exception:
            pass  # nosec B110
        try:
            self.lineEdit().setPlaceholderText(tr("未选"))
            self.lineEdit().installEventFilter(self)
        except Exception:
            pass  # nosec B110
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        try:
            self._tree.setRootIsDecorated(True)
        except Exception:
            pass  # nosec B110
        try:
            self._tree.setWindowFlags(POPUP_FLAGS)
        except Exception:
            self._tree.setWindowFlags(Qt.WindowType.Popup)
        self._tree.setMinimumWidth(220)
        self._tree.itemChanged.connect(self._on_tree_item_changed)
        self._refresh_display()

    def eventFilter(self, obj, event):
        try:
            etype = event.type()
        except Exception:
            return super(LayerCheckCombo, self).eventFilter(obj, event)
        try:
            if obj is self.lineEdit() and etype == MOUSE_PRESS:
                if self._tree.isVisible():
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
        except Exception:
            pass  # nosec B110
        if self._tree.isVisible() and not self._suppress_outside:
            if etype == KEY_PRESS:
                try:
                    if event.key() == KEY_ESCAPE:
                        self.hidePopup()
                        return True
                except Exception:
                    pass  # nosec B110
            if etype == MOUSE_PRESS:
                pos = self._event_global_pos(event)
                if pos is not None and not self._popup_contains(pos):
                    self.hidePopup()
        return super(LayerCheckCombo, self).eventFilter(obj, event)

    def _event_global_pos(self, event):
        try:
            if hasattr(event, "globalPosition"):
                return event.globalPosition().toPoint()
        except Exception:
            pass  # nosec B110
        try:
            return event.globalPos()
        except Exception:
            return None

    def _popup_contains(self, global_pos):
        def contains(widget):
            if widget is None:
                return False
            try:
                origin = widget.mapToGlobal(QPoint(0, 0))
                return QRect(origin, widget.size()).contains(global_pos)
            except Exception:
                return False

        return contains(self._tree) or contains(self) or contains(self.lineEdit())

    def connect_changed(self, slot):
        self._changed_slot = slot

    def load_filters(self, data):
        self._filters = dict(data) if isinstance(data, dict) else {}

    def filters(self):
        return dict(self._filters)

    def filters_by_layer_id(self):
        out = {}
        for layer in self.checked_layers():
            flt = self._filters.get(layer.name())
            if flt and flt.get("field") is not None:
                out[layer.id()] = {
                    "field": flt["field"],
                    "values": list(flt.get("values") or []),
                }
        return out

    def _layers(self):
        rows = []
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            if layer.geometryType() != self._geom_type:
                continue
            rows.append(layer)
        return rows

    def _layer_categories(self, layer):
        renderer = layer.renderer() if layer is not None else None
        if renderer is None or not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return "", []
        field = renderer.classAttribute() or ""
        if not field:
            return "", []
        rows = []
        seen = set()
        for cat in renderer.categories():
            key = attr_key(cat.value())
            if key in seen:
                continue
            seen.add(key)
            label = cat.label() or key or tr("(空)")
            rows.append((key, label))
        return field, rows

    def reload(self, checked_names=None):
        if checked_names is not None:
            self._checked_names = [name for name in checked_names if name]
        alive = {layer.name() for layer in self._layers()}
        self._checked_names = [name for name in self._checked_names if name in alive]
        self._filters = {k: v for k, v in self._filters.items() if k in alive}
        self._refresh_display()

    def checked_names(self):
        return list(self._checked_names)

    def checked_layers(self):
        wanted = set(self._checked_names)
        return [layer for layer in self._layers() if layer.name() in wanted]

    def _refresh_display(self):
        parts = []
        by_name = {layer.name(): layer for layer in self._layers()}
        for name in self._checked_names:
            layer = by_name.get(name)
            flt = self._filters.get(name)
            field, cats = self._layer_categories(layer) if layer is not None else ("", [])
            if field and cats and flt and flt.get("values") is not None:
                allowed = set(attr_key(v) for v in flt.get("values") or [])
                labels = [label for key, label in cats if key in allowed]
                if labels and len(labels) < len(cats):
                    parts.append("{}（{}）".format(name, ", ".join(labels)))
                else:
                    parts.append(name)
            else:
                parts.append(name)
        text = ", ".join(parts)
        try:
            self.lineEdit().setText(text)
            self.lineEdit().setPlaceholderText(tr("未选"))
        except Exception:
            pass  # nosec B110
        self.setToolTip(text or tr("未选"))

    def showPopup(self):
        if self._tree.isVisible():
            self.hidePopup()
            return
        self._rebuild_tree()
        width = max(self.width(), 260)
        rows = max(self._tree.topLevelItemCount(), 1)
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.isExpanded():
                rows += item.childCount()
        height = min(320, max(120, rows * 22 + 12))
        self._tree.resize(width, height)
        self._tree.move(self.mapToGlobal(QPoint(0, self.height())))
        self._suppress_outside = True
        self._tree.show()
        self._tree.setFocus()
        self._install_outside_filter()
        try:
            QTimer.singleShot(0, self._arm_outside_close)
        except Exception:
            self._suppress_outside = False

    def _arm_outside_close(self):
        self._suppress_outside = False

    def _install_outside_filter(self):
        if self._filter_on:
            return
        app = QApplication.instance()
        if app is None:
            return
        app.installEventFilter(self)
        self._filter_on = True

    def _remove_outside_filter(self):
        if not self._filter_on:
            return
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass  # nosec B110
        self._filter_on = False

    def hidePopup(self):
        self._remove_outside_filter()
        self._suppress_outside = False
        try:
            self._tree.hide()
        except Exception:
            pass  # nosec B110
        try:
            super(LayerCheckCombo, self).hidePopup()
        except Exception:
            pass  # nosec B110

    def _rebuild_tree(self):
        self._block = True
        try:
            self._tree.clear()
            wanted = set(self._checked_names)
            for layer in self._layers():
                name = layer.name()
                field, cats = self._layer_categories(layer)
                parent = QTreeWidgetItem([name])
                parent.setFlags(parent.flags() | ITEM_USER_CHECKABLE)
                parent.setData(0, USER_ROLE, layer.id())
                parent.setData(0, USER_ROLE + 1, name)
                parent.setData(0, USER_ROLE + 2, field)
                parent.setData(0, USER_ROLE + 3, "layer")
                flt = self._filters.get(name) if name in wanted else None
                allowed = None
                if flt and flt.get("values") is not None:
                    allowed = set(attr_key(v) for v in flt.get("values") or [])
                child_checked = 0
                for key, label in cats:
                    child = QTreeWidgetItem([label])
                    child.setFlags(child.flags() | ITEM_USER_CHECKABLE)
                    child.setData(0, USER_ROLE + 2, key)
                    child.setData(0, USER_ROLE + 3, "cat")
                    on = name in wanted and (allowed is None or key in allowed)
                    child.setCheckState(0, CHECKED if on else UNCHECKED)
                    if on:
                        child_checked += 1
                    parent.addChild(child)
                if name not in wanted:
                    parent.setCheckState(0, UNCHECKED)
                elif cats and allowed is not None and child_checked < len(cats):
                    parent.setCheckState(0, PARTIAL if child_checked else UNCHECKED)
                else:
                    parent.setCheckState(0, CHECKED)
                self._tree.addTopLevelItem(parent)
                if cats and name in wanted:
                    parent.setExpanded(True)
        finally:
            self._block = False

    def _sync_parent(self, parent):
        if parent is None:
            return
        total = parent.childCount()
        if total <= 0:
            return
        checked = sum(
            1 for i in range(total) if parent.child(i).checkState(0) == CHECKED
        )
        if checked == 0:
            parent.setCheckState(0, UNCHECKED)
        elif checked == total:
            parent.setCheckState(0, CHECKED)
        else:
            parent.setCheckState(0, PARTIAL)

    def _on_tree_item_changed(self, item, _col):
        if self._block or item is None:
            return
        self._block = True
        try:
            kind = item.data(0, USER_ROLE + 3)
            if kind == "layer":
                state = item.checkState(0)
                if state == PARTIAL:
                    state = CHECKED
                    item.setCheckState(0, CHECKED)
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, state)
            else:
                self._sync_parent(item.parent())
            self._capture_from_tree()
        finally:
            self._block = False
        self._refresh_display()
        if callable(self._changed_slot):
            self._changed_slot()

    def _capture_from_tree(self):
        names = []
        filters = {}
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.checkState(0) == UNCHECKED:
                continue
            name = item.data(0, USER_ROLE + 1) or item.text(0)
            names.append(name)
            field = item.data(0, USER_ROLE + 2) or ""
            total = item.childCount()
            if not field or total <= 0:
                continue
            values = []
            for j in range(total):
                child = item.child(j)
                if child.checkState(0) == CHECKED:
                    values.append(child.data(0, USER_ROLE + 2))
            if values and len(values) < total:
                filters[name] = {"field": field, "values": values}
        self._checked_names = names
        self._filters = filters
