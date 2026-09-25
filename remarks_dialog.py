# -*- coding: utf-8 -*-
"""Remark packs + layer field editor (non-modal) + per-column quick fill."""

import os

from qgis.PyQt.QtCore import QEvent, QObject, Qt, pyqtSignal, QTimer
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPalette, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QSizePolicy,
    QSplitter,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from qgis.core import QgsLayerTree, QgsMapLayer, QgsProject, NULL

from . import theme
from .classify_assign import (
    apply_assignments,
    assignment_key,
    category_keys_for_fids,
    copy_geoms_and_assign,
    count_category_keys,
    format_assignments,
    layer_categories,
    layer_geom_kind,
    layers_are_same,
    notify_open_attribute_tables,
    refresh_layer_after_assign,
    refresh_legend_class_counts,
    save_edits_via_qgis,
)
from .value_map import (
    field_index,
    is_value_map_field,
    layer_value_map_meanings,
    meanings_signature,
    merge_value_map_meanings,
    value_key,
    value_map_bundle,
    value_map_defaults,
)
from .remarks_store import (
    LAYER_ITEM_KEY,
    PLACEHOLDER_NAME,
    RemarksSession,
    empty_field,
    empty_layer,
    format_meaning,
    configured_preview_nodes,
    is_placeholder_name,
    layer_legend_tooltip,
    meaning_display,
    meaning_has_var_tokens,
    meaning_payload,
    meaning_resolved_tip,
    normalize_field,
    normalize_meaning,
    parse_meaning_full,
    resolve_var_template,
    safe_pack_filename,
)

_QUICK_COMBO_QSS = (
    "QComboBox { background-color: #ffffff; color: #111111; }"
    "QComboBox QAbstractItemView { background-color: #ffffff; color: #111111;"
    " selection-background-color: #aed581; selection-color: #111111; }"
)


def _style_quick_combo(combo):
    combo.setStyleSheet(_QUICK_COMBO_QSS)
    pal = QPalette(combo.palette())
    pal.setColor(QPalette.Text, QColor("#111111"))
    pal.setColor(QPalette.WindowText, QColor("#111111"))
    pal.setColor(QPalette.ButtonText, QColor("#111111"))
    pal.setColor(QPalette.Base, QColor("#ffffff"))
    pal.setColor(QPalette.Window, QColor("#ffffff"))
    pal.setColor(QPalette.Button, QColor("#ffffff"))
    pal.setColor(QPalette.HighlightedText, QColor("#111111"))
    pal.setColor(QPalette.Highlight, QColor("#aed581"))
    try:
        pal.setColor(QPalette.PlaceholderText, QColor("#555555"))
    except Exception:
        pass
    combo.setPalette(pal)
    view = combo.view()
    if view is not None:
        view.setPalette(pal)
        view.setStyleSheet(
            "background-color: #ffffff; color: #111111;"
            " selection-background-color: #aed581; selection-color: #111111;"
        )


def _style_preview_item(item, kind):
    font = QFont(item.font(0))
    if kind == "layer":
        font.setBold(True)
        font.setPointSize(13)
        item.setForeground(0, QColor("#1565c0"))
    elif kind == "field":
        font.setBold(True)
        font.setPointSize(11)
        item.setForeground(0, QColor("#2e7d32"))
    else:
        font.setBold(False)
        font.setPointSize(9)
        item.setForeground(0, QColor("#424242"))
    item.setFont(0, font)


def _mark_preview_mismatch(item):
    item.setForeground(0, QColor("#c62828"))


def _as_window(widget):
    widget.setModal(False)
    widget.setWindowFlags(
        Qt.Window
        | Qt.WindowMinimizeButtonHint
        | Qt.WindowMaximizeButtonHint
        | Qt.WindowCloseButtonHint
    )
    theme.register(widget)


class ExportPacksDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出备注项目")
        self.resize(360, 320)
        self._items = list(items or [])
        root = QVBoxLayout(self)
        root.addWidget(QLabel("选择要导出的项目（可多选）："))
        self.list = QListWidget()
        for item_data in self._items:
            name = item_data[0] if item_data else ""
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        root.addWidget(self.list, 1)
        row = QHBoxLayout()
        btn_all = QPushButton("全选")
        btn_none = QPushButton("全不选")
        btn_all.clicked.connect(self._check_all)
        btn_none.clicked.connect(self._check_none)
        row.addWidget(btn_all)
        row.addWidget(btn_none)
        row.addStretch(1)
        root.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _check_all(self):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Checked)

    def _check_none(self):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Unchecked)

    def selected_items(self):
        picked = []
        for i in range(self.list.count()):
            if self.list.item(i).checkState() == Qt.Checked:
                picked.append(self._items[i])
        return picked

    def accept(self):
        if not self.selected_items():
            QMessageBox.information(self, "导出", "请至少勾选一个项目。")
            return
        super().accept()


class LayerLegendTooltipFilter(QObject):
    """Show field-style remarks when hovering a layer in the QGIS legend."""

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._view = None
        self._attached = []
        self.attach()

    def attach(self):
        self.detach()
        try:
            view = self.iface.layerTreeView()
        except Exception:
            view = None
        self._view = view
        if view is None:
            return
        viewport = view.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)
            self._attached.append(viewport)

    def detach(self):
        for obj in self._attached:
            try:
                obj.removeEventFilter(self)
            except Exception:
                pass
        self._attached = []
        self._view = None

    def eventFilter(self, obj, event):
        if event.type() != QEvent.ToolTip:
            return False
        view = self._view
        if view is None:
            return False
        try:
            pos = event.pos()
            index = view.indexAt(pos)
        except Exception:
            return False
        if not index.isValid():
            return False
        layer = self._layer_for_index(view, index)
        if layer is None:
            return False
        text = layer_legend_tooltip(layer)
        if not text:
            return False
        try:
            QToolTip.showText(event.globalPos(), text, view.viewport())
        except Exception:
            return False
        return True

    @staticmethod
    def _layer_for_index(view, index):
        node = None
        try:
            node = view.index2node(index)
        except Exception:
            try:
                node = view.layerTreeModel().index2node(index)
            except Exception:
                node = None
        if node is None:
            return None
        try:
            if not QgsLayerTree.isLayer(node):
                return None
            layer = node.layer()
        except Exception:
            return None
        if layer is None or not hasattr(layer, "type"):
            return None
        if layer.type() != QgsMapLayer.VectorLayer:
            return None
        return layer


class QuickFillBar(QWidget):
    """One combo per table column, aligned to column widths. Apply via 更新选中/更新筛选行."""

    def apply_theme(self):
        self.setStyleSheet(
            "QuickFillBar { background-color: %s; border: 1px solid %s; }"
            % (theme.color("quick_bg"), theme.color("quick_border"))
            + _QUICK_COMBO_QSS
        )

    def __init__(self, dialog):
        super().__init__(dialog)
        self._dialog = dialog
        self._combos = []
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAutoFillBackground(True)
        self.apply_theme()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(0)

        self.lbl_tag = QWidget()
        self.lbl_tag.setFixedHeight(26)
        lay.addWidget(self.lbl_tag)

        self.frozen_host = QWidget()
        self.frozen_host.setFixedHeight(26)
        self.frozen_host.setFixedWidth(0)
        lay.addWidget(self.frozen_host)

        self.table_vh_spacer = QWidget()
        self.table_vh_spacer.setFixedWidth(0)
        lay.addWidget(self.table_vh_spacer)

        self.table_host = QWidget()
        self.table_host.setFixedHeight(26)
        self.table_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.table_host.setMinimumWidth(0)
        lay.addWidget(self.table_host, 1)

        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self.sync)

    def schedule_sync(self, delay=20):
        self._sync_timer.start(max(0, int(delay)))

    def rebuild(self):
        dialog = self._dialog
        names = dialog.model.field_names() if dialog.model is not None else []
        for _name, combo in self._combos:
            combo.hide()
            combo.setParent(None)
            combo.deleteLater()
        self._combos = []
        for name in names:
            combo = QComboBox(self.table_host)
            combo.setMaxVisibleItems(12)
            combo.setFixedHeight(24)
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(2)
            _style_quick_combo(combo)
            combo.activated.connect(
                lambda index, n=name, c=combo: self._on_picked(n, c, index)
            )
            self._combos.append((name, combo))
            self._reload_combo(combo, name)
        self.sync()

    def _reload_combo(self, combo, field_name):
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("插入…", "")
        combo.setItemData(0, QColor("#111111"), Qt.ForegroundRole)
        combo.setItemData(0, QColor("#ffffff"), Qt.BackgroundRole)
        meanings = []
        model = self._dialog.model
        if model is not None and hasattr(model, "field_meanings"):
            meanings = model.field_meanings(field_name)
        for item in meanings:
            payload = meaning_payload(item)
            combo.addItem(meaning_display(item) or str(item), payload)
            combo.setItemData(combo.count() - 1, QColor("#111111"), Qt.ForegroundRole)
            combo.setItemData(combo.count() - 1, QColor("#ffffff"), Qt.BackgroundRole)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)
        combo.setEnabled(True)
        variables = []
        if model is not None and hasattr(model, "pack_variables"):
            variables = model.pack_variables()
        tips = [
            meaning_resolved_tip(item, variables)
            for item in meanings
            if meaning_display(item)
        ]
        combo.setToolTip(
            "\n".join(tips) if tips else "该字段还没有含义说明（图层管理里添加）"
        )

    def reload_items(self):
        pending = self.pending_values()
        for name, combo in self._combos:
            self._reload_combo(combo, name)
            if name in pending:
                wanted = pending[name]
                combo.blockSignals(True)
                for i in range(1, combo.count()):
                    if self._same_payload(combo.itemData(i), wanted):
                        combo.setCurrentIndex(i)
                        break
                combo.blockSignals(False)
        self.sync()

    @staticmethod
    def _same_payload(left, right):
        if left == right:
            return True
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        return (
            (left.get("kind") or "const") == (right.get("kind") or "const")
            and (left.get("value") or "") == (right.get("value") or "")
        )

    def pending_values(self):
        out = {}
        for name, combo in self._combos:
            idx = combo.currentIndex()
            if idx <= 0:
                continue
            data = combo.itemData(idx)
            if isinstance(data, dict):
                payload = data
            else:
                payload = meaning_payload(combo.itemText(idx))
            if payload.get("value"):
                out[name] = payload
        return out

    def clear_pending(self, names=None):
        wanted = None if names is None else set(names)
        for name, combo in self._combos:
            if wanted is not None and name not in wanted:
                continue
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def sync(self):
        dialog = self._dialog
        if not self.isVisible() or not hasattr(dialog, "table") or dialog.table is None:
            return
        table = dialog.table
        frozen = dialog.frozen
        header = table.horizontalHeader()
        names = dialog.model.field_names()
        freeze_on = bool(frozen.isVisible())
        table_vh = max(table.verticalHeader().width(), 36)
        host_h = 26

        if freeze_on:
            self.lbl_tag.setFixedWidth(max(frozen.verticalHeader().width(), 36))
            self.frozen_host.setFixedWidth(max(frozen.columnWidth(0), 0))
            self.frozen_host.show()
            self.table_vh_spacer.setFixedWidth(table_vh)
            self.table_vh_spacer.show()
        else:
            self.lbl_tag.setFixedWidth(table_vh)
            self.frozen_host.hide()
            self.frozen_host.setFixedWidth(0)
            self.table_vh_spacer.hide()
            self.table_vh_spacer.setFixedWidth(0)

        for name, combo in self._combos:
            try:
                logical = names.index(name)
            except ValueError:
                combo.hide()
                continue
            if freeze_on and logical == 0:
                combo.setParent(self.frozen_host)
                combo.setGeometry(0, 1, self.frozen_host.width(), host_h)
                combo.show()
                continue
            if header.isSectionHidden(logical):
                combo.hide()
                continue
            combo.setParent(self.table_host)
            x = header.sectionViewportPosition(logical)
            w = header.sectionSize(logical)
            combo.setGeometry(x, 1, max(w, 0), host_h)
            combo.show()

    def _on_picked(self, field_name, combo, index):
        if index <= 0:
            return
        value = combo.itemData(index)
        if not isinstance(value, dict):
            value = meaning_payload(combo.itemText(index))
        if not value or not value.get("value"):
            return
        if hasattr(self._dialog, "_sync_fill_from_quick"):
            self._dialog._sync_fill_from_quick(field_name, value)
        if hasattr(self._dialog, "_ask_quick_fill_scope"):
            self._dialog._ask_quick_fill_scope(field_name, value, combo)


class RemarksHubDialog(QDialog):
    """Project packs + field remarks for the QGIS active layer. Non-modal."""

    packChanged = pyqtSignal()
    enabledChanged = pyqtSignal(bool)
    remarksChanged = pyqtSignal()
    _instance = None

    @classmethod
    def open_for(cls, iface, session=None, parent=None, focus_field=None):
        dlg = cls._instance
        try:
            if dlg is not None:
                dlg.windowTitle()
        except Exception:
            dlg = None
            cls._instance = None
        if dlg is None:
            if session is None:
                session = RemarksSession()
            dlg = cls(session, iface, parent=parent, focus_field=None)
            cls._instance = dlg
            created = True
        else:
            created = False
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg._reload_shared_config()
        if focus_field:
            dlg.focus_field(focus_field)
        if created:
            dlg._update_check_status()
        return dlg

    packChanged = pyqtSignal()
    enabledChanged = pyqtSignal(bool)
    remarksChanged = pyqtSignal()

    def __init__(self, session, iface, parent=None, focus_field=None):
        super().__init__(parent)
        self.session = session
        self.iface = iface
        self._layer = None
        self._current_field = None
        self._work = empty_layer()
        self._mean_edit_row = -1
        _as_window(self)
        self.setWindowTitle("字段备注")
        self.resize(760, 560)

        root = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("当前项目："))
        self.cmb_pack = QComboBox()
        self.cmb_pack.setMinimumWidth(180)
        self.cmb_pack.currentIndexChanged.connect(self._on_pack_changed)
        row.addWidget(self.cmb_pack, 1)
        root.addLayout(row)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("新建项目")
        self.btn_del = QPushButton("删除项目")
        self.btn_rename = QPushButton("修改名称")
        self.btn_preview = QPushButton("预览配置")
        self.btn_preview.setToolTip("只读查看当前项目已配置的图层、字段和含义。")
        self.btn_add.clicked.connect(self._add_pack)
        self.btn_del.clicked.connect(self._del_pack)
        self.btn_rename.clicked.connect(self._rename_pack)
        self.btn_preview.clicked.connect(self._preview_pack)
        self.btn_reload = QPushButton("刷新")
        self.btn_reload.setToolTip(
            "重新读取配置文件。另一边 QGIS 改完后，点这里，或点一下本窗口，即可看到，不用重启。"
        )
        self.btn_reload.clicked.connect(self._reload_shared_config)
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_del)
        btns.addWidget(self.btn_rename)
        btns.addWidget(self.btn_preview)
        btns.addWidget(self.btn_reload)
        root.addLayout(btns)

        mode = QHBoxLayout()
        self.btn_enable = QPushButton("启用")
        self.btn_enable.setToolTip("启用/关闭备注显示。默认关闭。")
        self.btn_enable.clicked.connect(self._toggle_enabled)
        self.btn_variables = QPushButton("变量配置")
        self.btn_variables.setToolTip(
            "给当前项目配置变量（标题给人看，内容才是写入值）。跟项目包走，导入导出一起带走。"
        )
        self.btn_variables.clicked.connect(self._open_variables)
        mode.addWidget(self.btn_enable)
        mode.addWidget(self.btn_variables)
        self.btn_import = QPushButton("导入")
        self.btn_export = QPushButton("导出")
        self.btn_import.setToolTip("导入备注项目（一份 JSON 可含多个项目）。同名时选择覆盖或换名。")
        self.btn_export.setToolTip("勾选要导出的项目。单项目文件名：属性表Plus(项目名).json")
        self.btn_import.clicked.connect(self._import_pack)
        self.btn_export.clicked.connect(self._export_pack)
        mode.addWidget(self.btn_import)
        mode.addWidget(self.btn_export)
        root.addLayout(mode)

        self.lbl_layer = QLabel("图层管理")
        self.lbl_layer.setStyleSheet("font-weight: bold;")
        root.addWidget(self.lbl_layer)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(QLabel("字段（末项为图层名，仅悬停用）："))
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_field_changed)
        left_lay.addWidget(self.list, 1)
        split.addWidget(left)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        pair = QHBoxLayout()
        pair.addWidget(QLabel("中文名："))
        self.ed_label = QLineEdit()
        self.ed_label.setPlaceholderText("表头第一行显示，如 Type → 类型")
        self.ed_label.textChanged.connect(self._on_label_text_changed)
        self.ed_label.editingFinished.connect(self._flush_and_notify)
        pair.addWidget(self.ed_label, 1)
        right_lay.addLayout(pair)

        self.lbl_notes = QLabel("悬停说明（多行，只显示，不赋值）：")
        right_lay.addWidget(self.lbl_notes)
        self.ed_notes = QPlainTextEdit()
        self.ed_notes.setPlaceholderText("悬停时显示在中文名下面，不写入字段、不进插入下拉")
        self.ed_notes.setTabChangesFocus(True)
        self.ed_notes.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        fm = self.ed_notes.fontMetrics()
        self._notes_field_height = max(fm.lineSpacing() * 4 + 14, 72)
        self.ed_notes.setFixedHeight(self._notes_field_height)
        self._notes_timer = QTimer(self)
        self._notes_timer.setSingleShot(True)
        self._notes_timer.timeout.connect(self._flush_notes_quiet)
        self.ed_notes.textChanged.connect(self._on_notes_text_changed)
        self._right_lay = right_lay
        right_lay.addWidget(self.ed_notes, 0)

        self.mean_panel = QWidget()
        mean_lay = QVBoxLayout(self.mean_panel)
        mean_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_meanings = QLabel("含义说明（双击一行改说明；值映射项后面的「原」不变，不能删除）：")
        mean_lay.addWidget(self.lbl_meanings)
        add_row = QHBoxLayout()
        self.ed_mean_cn = QLineEdit()
        self.ed_mean_cn.setPlaceholderText("中文，如 盒子")
        self.cmb_mean_kind = QComboBox()
        self.cmb_mean_kind.addItem("常量", "const")
        self.cmb_mean_kind.addItem("QGIS", "expr")
        self.cmb_mean_kind.setToolTip("常量写入固定值；QGIS 则右边粘贴表达式，赋值时按要素计算")
        self.cmb_mean_kind.currentIndexChanged.connect(self._on_mean_kind_changed)
        self.ed_mean_code = QLineEdit()
        self.ed_mean_code.setPlaceholderText("写入值，如 FAT；可插入变量")
        self.btn_mean_var = QPushButton("插入变量")
        self.btn_mean_var.setToolTip("把当前项目的变量插进写入值，如 {{城市}}123")
        self.btn_mean_var.clicked.connect(self._pick_insert_variable)
        self.btn_mean_add = QPushButton("添加")
        self.btn_mean_add.clicked.connect(self._add_meaning)
        self.ed_mean_code.returnPressed.connect(self._add_meaning)
        add_row.addWidget(self.ed_mean_cn, 1)
        add_row.addWidget(QLabel("="))
        add_row.addWidget(self.cmb_mean_kind)
        add_row.addWidget(self.ed_mean_code, 1)
        add_row.addWidget(self.btn_mean_var)
        add_row.addWidget(self.btn_mean_add)
        mean_lay.addLayout(add_row)

        self.mean_list = QListWidget()
        self.mean_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mean_list.itemDoubleClicked.connect(self._on_meaning_double_clicked)
        self.mean_list.currentItemChanged.connect(self._update_meaning_buttons)
        mean_lay.addWidget(self.mean_list, 1)
        mean_btns = QHBoxLayout()
        self.btn_mean_restore = QPushButton("恢复默认")
        self.btn_mean_restore.setToolTip("把选中的值映射项说明恢复成 QGIS 当前描述")
        self.btn_mean_restore.clicked.connect(self._restore_meaning_default)
        self.btn_mean_del = QPushButton("删除选中")
        self.btn_mean_del.clicked.connect(self._del_meaning)
        mean_btns.addWidget(self.btn_mean_restore)
        mean_btns.addWidget(self.btn_mean_del)
        mean_lay.addLayout(mean_btns)
        right_lay.addWidget(self.mean_panel, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        root.addWidget(split, 1)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self._reload_combo()
        self._sync_enable_buttons()
        self._set_layer(self._qgis_vector_layer())
        self._update_check_status()
        if focus_field:
            self.focus_field(focus_field)
        self._ui_ready = True

        try:
            self.iface.currentLayerChanged.connect(self._on_qgis_layer_changed)
        except Exception:
            pass

    def closeEvent(self, event):
        if hasattr(self, "_notes_timer"):
            self._notes_timer.stop()
        self._flush_current()
        try:
            self.iface.currentLayerChanged.disconnect(self._on_qgis_layer_changed)
        except Exception:
            pass
        RemarksHubDialog._instance = None
        super().closeEvent(event)

    def _qgis_vector_layer(self):
        layer = None
        try:
            layer = self.iface.activeLayer()
        except Exception:
            layer = None
        if layer is None or not hasattr(layer, "type"):
            return None
        if layer.type() != QgsMapLayer.VectorLayer:
            return None
        return layer

    def _on_qgis_layer_changed(self, layer):
        self._flush_current()
        if layer is not None and (
            not hasattr(layer, "type") or layer.type() != QgsMapLayer.VectorLayer
        ):
            layer = None
        self._set_layer(layer)

    def _can_edit_layer(self):
        try:
            if self.session.is_placeholder():
                return False
            return bool(self.session.enabled)
        except Exception:
            return False

    def _refresh_layer_caption(self):
        if not hasattr(self, "lbl_layer"):
            return
        if self._layer is None:
            self.lbl_layer.setText("图层管理 — 请在 QGIS 中选择一个矢量图层")
            return
        extra = ""
        if not self._can_edit_layer() and not self.session.is_placeholder():
            extra = "（未启用，只读）"
        elif self.session.is_placeholder():
            extra = "（%s）" % PLACEHOLDER_NAME
        self.lbl_layer.setText("图层管理 — %s%s" % (self._layer.name(), extra))

    def _set_layer(self, layer):
        self._layer = layer
        if layer is None:
            self._refresh_layer_caption()
            self._current_field = None
            self._work = empty_layer()
            self.list.clear()
            self._load_field_form(None)
            self._update_check_status()
            return
        self._current_field = None
        self._work = self.session.layer_entry(layer.name())
        self._absorb_value_maps()
        self._reload_field_list()
        self._refresh_layer_caption()
        self._update_check_status()

    def _reload_combo(self):
        self.cmb_pack.blockSignals(True)
        self.cmb_pack.clear()
        for name in self.session.pack_names():
            self.cmb_pack.addItem(name)
        self.cmb_pack.setCurrentIndex(self.session.current)
        self.cmb_pack.blockSignals(False)

    def changeEvent(self, event):
        super().changeEvent(event)
        if not getattr(self, "_ui_ready", False):
            return
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            if self.session.reload_from_disk():
                self.adopt_shared_config()

    def _reload_shared_config(self):
        self.session.reload_from_disk(force=True)
        self.adopt_shared_config()

    def adopt_shared_config(self):
        self._reload_combo()
        self._sync_enable_buttons()
        self.reload_from_session()
        self.packChanged.emit()
        self.enabledChanged.emit(bool(self.session.enabled))

    def _on_pack_changed(self, index):
        if index < 0:
            return
        self._flush_current()
        self.session.set_current(index)
        self.reload_from_session()
        if self.session.enabled:
            self._set_enabled(False)
        self.packChanged.emit()
        self._update_check_status()

    def _add_pack(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：", text="未命名")
        if not ok:
            return
        if is_placeholder_name(name):
            QMessageBox.information(
                self, "新建项目", "「%s」是占位名称，请换一个名字。" % PLACEHOLDER_NAME
            )
            return
        self._flush_current()
        self.session.add_pack(name)
        self._reload_combo()
        self.reload_from_session()
        self.packChanged.emit()

    def _del_pack(self):
        if self.session.is_placeholder():
            QMessageBox.information(
                self, "删除项目", "「%s」是占位项目，不能删除。" % PLACEHOLDER_NAME
            )
            return
        name = self.session.current_name()
        if (
            QMessageBox.question(self, "删除项目", f"确定删除项目「{name}」？")
            != QMessageBox.Yes
        ):
            return
        self._flush_current()
        self.session.delete_current()
        self._reload_combo()
        self.reload_from_session()
        self.packChanged.emit()
        self._update_check_status()

    def _preview_pack(self):
        from .remarks_remap import collect_orphans, project_vector_layers

        dlg = QDialog(self)
        dlg.setWindowTitle("已配置数据 — %s" % self.session.current_name())
        dlg.resize(560, 480)
        lay = QVBoxLayout(dlg)
        tip = QLabel(
            "只读预览。红色=当前工程对不上。"
            "默认只显示不匹配项：图层对不上只列图层；字段对不上会带上所属图层。"
        )
        tip.setWordWrap(True)
        lay.addWidget(tip)
        tree = QTreeWidget()
        tree.setHeaderLabels(["图层 / 字段 / 含义"])
        tree.setUniformRowHeights(False)
        try:
            nodes = configured_preview_nodes(self.session._layers())
        except Exception:
            nodes = []
        try:
            pack_vars = self.session.current_variables()
        except Exception:
            pack_vars = []
        try:
            missing_layers, field_orphans = collect_orphans(
                self.session._layers(), project_vector_layers()
            )
        except Exception:
            missing_layers, field_orphans = [], {}
        missing_layer_set = set(missing_layers or [])
        field_orphan_map = {
            lname: set(fields or []) for lname, fields in (field_orphans or {}).items()
        }
        state = {"only_mismatch": True}

        def _add_empty(text):
            empty = QTreeWidgetItem([text])
            _style_preview_item(empty, "meaning")
            tree.addTopLevelItem(empty)

        def rebuild():
            tree.clear()
            only = bool(state["only_mismatch"])
            shown = 0
            if not only and pack_vars:
                var_root = QTreeWidgetItem(["变量"])
                _style_preview_item(var_root, "layer")
                tree.addTopLevelItem(var_root)
                shown += 1
                for item in pack_vars:
                    title = item.get("title") or ""
                    value = item.get("value") or ""
                    child = QTreeWidgetItem(
                        ["%s = %s" % (title, value) if value else title]
                    )
                    _style_preview_item(child, "meaning")
                    var_root.addChild(child)
                var_root.setExpanded(True)
            if not nodes:
                if shown == 0:
                    _add_empty(
                        "当前项目还没有图层配置。"
                        if only
                        else "当前项目还没有图层配置和变量。"
                    )
                return
            for layer_name, layer_title, note, fields in nodes:
                layer_miss = layer_name in missing_layer_set
                bad_fields = field_orphan_map.get(layer_name) or set()
                if only:
                    if not layer_miss and not bad_fields:
                        continue
                layer_item = QTreeWidgetItem([layer_title])
                _style_preview_item(layer_item, "layer")
                if layer_miss:
                    _mark_preview_mismatch(layer_item)
                tree.addTopLevelItem(layer_item)
                shown += 1
                if only and layer_miss:
                    continue
                if only:
                    for field_name, field_title, _means in fields:
                        if field_name not in bad_fields:
                            continue
                        field_item = QTreeWidgetItem([field_title])
                        _style_preview_item(field_item, "field")
                        _mark_preview_mismatch(field_item)
                        layer_item.addChild(field_item)
                    layer_item.setExpanded(True)
                    continue
                if note:
                    note_item = QTreeWidgetItem(["悬停说明：%s" % note])
                    _style_preview_item(note_item, "meaning")
                    layer_item.addChild(note_item)
                if not fields:
                    empty_field = QTreeWidgetItem(["（无字段配置）"])
                    _style_preview_item(empty_field, "meaning")
                    layer_item.addChild(empty_field)
                for field_name, field_title, means in fields:
                    field_item = QTreeWidgetItem([field_title])
                    _style_preview_item(field_item, "field")
                    if field_name in bad_fields:
                        _mark_preview_mismatch(field_item)
                    layer_item.addChild(field_item)
                    if not means:
                        empty_mean = QTreeWidgetItem(["（无含义）"])
                        _style_preview_item(empty_mean, "meaning")
                        field_item.addChild(empty_mean)
                    for text in means:
                        mean_item = QTreeWidgetItem([text])
                        _style_preview_item(mean_item, "meaning")
                        field_item.addChild(mean_item)
            if shown == 0:
                _add_empty("配置的图层、字段在当前工程全部有效。")

        rebuild()
        lay.addWidget(tree, 1)
        btn_row = QHBoxLayout()
        btn_expand = QPushButton("全部展开")
        btn_collapse = QPushButton("全部折叠")
        btn_mismatch = QPushButton("只显示不匹配的")
        btn_all = QPushButton("显示全部")
        btn_expand.clicked.connect(tree.expandAll)
        btn_collapse.clicked.connect(tree.collapseAll)

        def _show_mismatch():
            state["only_mismatch"] = True
            rebuild()

        def _show_all():
            state["only_mismatch"] = False
            rebuild()
            tree.collapseAll()

        btn_mismatch.clicked.connect(_show_mismatch)
        btn_all.clicked.connect(_show_all)
        btn_row.addWidget(btn_expand)
        btn_row.addWidget(btn_collapse)
        btn_row.addWidget(btn_mismatch)
        btn_row.addWidget(btn_all)
        btn_row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("关闭")
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        btn_row.addWidget(buttons)
        lay.addLayout(btn_row)
        dlg.exec_()

    def _rename_pack(self):
        if self.session.is_placeholder():
            QMessageBox.information(
                self, "修改名称", "「%s」是占位项目，不能改名。" % PLACEHOLDER_NAME
            )
            return
        name, ok = QInputDialog.getText(
            self, "修改名称", "项目名称：", text=self.session.current_name()
        )
        if not ok:
            return
        if is_placeholder_name(name):
            QMessageBox.information(
                self, "修改名称", "「%s」是占位名称，请换一个名字。" % PLACEHOLDER_NAME
            )
            return
        if not self.session.rename_current(name):
            QMessageBox.warning(self, "修改名称", "名称无效或与其它项目重名。")
            return
        self._reload_combo()
        self.packChanged.emit()
        self._update_check_status()

    def _toggle_enabled(self):
        if self.session.is_placeholder():
            QMessageBox.information(
                self, "启用", "「%s」是占位项目，不能启用，也不能改数据。" % PLACEHOLDER_NAME
            )
            return
        if self.session.enabled:
            self._set_enabled(False)
            return
        from .remarks_remap import RESET_DEFAULT

        result = self._run_self_check()
        if result == RESET_DEFAULT:
            return
        self._set_enabled(True)

    def _set_enabled(self, enabled):
        self.session.set_enabled(enabled)
        self._sync_enable_buttons()
        if enabled and self._layer is not None:
            self._work = self.session.layer_entry(self._layer.name())
            self._absorb_value_maps()
            self._reload_field_list(keep_name=self._current_field)
        self._refresh_layer_caption()
        self._update_check_status()
        self.enabledChanged.emit(bool(enabled))

    def _sync_enable_buttons(self):
        placeholder = bool(self.session.is_placeholder())
        on = bool(self.session.enabled) and not placeholder
        self.btn_enable.setEnabled(not placeholder)
        self.btn_enable.setText("关闭" if on else "启用")
        if placeholder:
            self.btn_enable.setToolTip("占位项目不能启用，也不能改数据。")
        else:
            self.btn_enable.setToolTip(
                "点击关闭：不再把配置套到图层字段上"
                if on
                else "点击启用：先核对图层/字段，再把当前项目配置套到图层字段上"
            )
        self.btn_enable.setStyleSheet(
            "QPushButton { font-weight: bold; background: #c8e6c9; }"
            if on
            else "QPushButton { font-weight: bold; background: #ffcdd2; }"
        )

    def _open_variables(self):
        if self.session.is_placeholder():
            QMessageBox.information(
                self,
                "变量配置",
                "「%s」是占位项目，不能配变量。请先选一个真正项目。" % PLACEHOLDER_NAME,
            )
            return
        self._flush_current()
        dlg = VariablesDialog(self.session, self)
        dlg.exec_()
        self.remarksChanged.emit()
        if self._current_field and self._current_field != LAYER_ITEM_KEY:
            for i in range(self.mean_list.count()):
                self._style_meaning_item(self.mean_list.item(i))

    def _run_self_check(self):
        from .remarks_remap import RESET_DEFAULT, run_self_check

        self._flush_current()
        try:
            result = run_self_check(self.session, parent=self)
        except Exception:
            result = False
        if result == RESET_DEFAULT:
            self._revert_to_placeholder()
            return RESET_DEFAULT
        if result:
            self._reload_combo()
            self.reload_from_session()
            self.packChanged.emit()
            self.remarksChanged.emit()
        self._update_check_status()
        return result

    def _revert_to_placeholder(self):
        self.session.set_current(0)
        self._reload_combo()
        self.reload_from_session()
        self.packChanged.emit()
        self.remarksChanged.emit()
        self._update_check_status()

    def _on_mean_kind_changed(self, *_args):
        kind = "const"
        if hasattr(self, "cmb_mean_kind"):
            kind = self.cmb_mean_kind.currentData() or "const"
        if kind == "expr":
            self.ed_mean_code.setPlaceholderText("粘贴表达式，如 $length")
        else:
            self.ed_mean_code.setPlaceholderText("写入值，如 FAT；可插入变量")
        self._sync_var_insert_button()

    def _set_mean_kind(self, kind):
        if not hasattr(self, "cmb_mean_kind"):
            return
        idx = self.cmb_mean_kind.findData(kind or "const")
        self.cmb_mean_kind.blockSignals(True)
        self.cmb_mean_kind.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_mean_kind.blockSignals(False)
        self._on_mean_kind_changed()

    def _export_pack(self):
        self._flush_current()
        items = self.session.exportable_items()
        if not items:
            QMessageBox.information(self, "导出", "还没有可导出的项目。请先新建并配置。")
            return
        picker = ExportPacksDialog(items, self)
        if picker.exec_() != QDialog.Accepted:
            return
        selected = picker.selected_items()
        if not selected:
            return
        if len(selected) == 1:
            filename = "属性表Plus(%s).json" % safe_pack_filename(selected[0][0])
        else:
            filename = "属性表Plus(多项目).json"
        default = os.path.join(os.path.expanduser("~"), filename)
        path, _filt = QFileDialog.getSaveFileName(
            self, "导出备注项目", default, "备注项目 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path = path + ".json"
        try:
            self.session.write_packs(path, selected)
        except Exception as exc:
            QMessageBox.warning(self, "导出", "导出失败：%s" % exc)
            return
        if len(selected) == 1:
            QMessageBox.information(self, "导出", "已导出项目「%s」。" % selected[0][0])
        else:
            QMessageBox.information(
                self, "导出", "已导出 %s 个项目。" % len(selected)
            )

    def _import_pack(self):
        self._flush_current()
        path, _filt = QFileDialog.getOpenFileName(
            self,
            "导入备注项目",
            os.path.expanduser("~"),
            "备注项目 (*.json);;所有文件 (*.*)",
        )
        if not path:
            return
        try:
            items, newer = self.session.read_pack_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "导入", str(exc) or "无法读取该文件。")
            return
        names = set(self.session.pack_names())
        conflicts = [
            item_name
            for item_name, *_rest in items
            if item_name in names and not is_placeholder_name(item_name)
        ]
        overwrite = False
        if conflicts:
            box = QMessageBox(self)
            box.setWindowTitle("导入")
            box.setText("已有同名项目：%s" % "、".join(conflicts))
            btn_over = box.addButton("覆盖同名", QMessageBox.DestructiveRole)
            btn_new = box.addButton("全部换名", QMessageBox.ActionRole)
            box.addButton("取消", QMessageBox.RejectRole)
            box.setDefaultButton(btn_new)
            box.exec_()
            clicked = box.clickedButton()
            if clicked is None or clicked not in (btn_over, btn_new):
                return
            overwrite = clicked == btn_over
        imported = []
        try:
            for pack_item in items:
                item_name, layers, variables = (
                    pack_item[0],
                    pack_item[1],
                    pack_item[2] if len(pack_item) > 2 else [],
                )
                imported.append(
                    self.session.import_pack(
                        item_name, layers, overwrite=overwrite, variables=variables
                    )
                )
        except Exception as exc:
            QMessageBox.warning(self, "导入", "导入失败：%s" % exc)
            return
        self._current_field = None
        self._reload_combo()
        self.reload_from_session()
        self.packChanged.emit()
        self.remarksChanged.emit()
        extra = ""
        if newer:
            extra = "\n文件版本较新，已按能识别的部分导入。"
        if len(imported) == 1:
            tip = "已导入项目「%s」。%s" % (imported[0], extra)
        else:
            tip = "已导入 %s 个项目。%s" % (len(imported), extra)
        QMessageBox.information(self, "导入", tip.strip())
        self._update_check_status()

    def _field_names(self):
        layer = self._layer
        if layer is None:
            return []
        return [f.name() for f in layer.fields()]

    def _reload_field_list(self, keep_name=None):
        keep = keep_name or self._current_field
        self.list.blockSignals(True)
        self.list.clear()
        fields_map = self._work.get("fields") or {}
        for name in self._field_names():
            entry = normalize_field(fields_map.get(name) or empty_field())
            item = QListWidgetItem(self._field_list_text(name, entry))
            item.setData(Qt.UserRole, name)
            self._style_field_item(item, name)
            self.list.addItem(item)
        if self._layer is not None:
            layer_item = QListWidgetItem("%s (图层)" % self._layer.name())
            layer_item.setData(Qt.UserRole, LAYER_ITEM_KEY)
            layer_item.setToolTip("图层备注：图例悬停显示中文名和悬停说明，不用于赋值")
            self.list.addItem(layer_item)
        target = 0
        found = False
        if keep:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.UserRole) == keep:
                    target = i
                    found = True
                    break
        if self.list.count():
            self.list.setCurrentRow(target if found or keep is None else 0)
        self.list.blockSignals(False)
        item = self.list.currentItem()
        self._load_field_form(item.data(Qt.UserRole) if item else None)

    def _field_list_text(self, name, entry=None):
        if entry is None:
            fields_map = self._work.get("fields") or {}
            entry = normalize_field(fields_map.get(name) or empty_field())
        label = (entry.get("label") or "").strip()
        text = f"{name} ({label})" if label and label != name else name
        if entry.get("meanings"):
            text = "● " + text
        return text

    def _update_list_item_text(self, name, extra_label=None):
        if not name:
            return
        if name == LAYER_ITEM_KEY:
            if self._layer is None:
                return
            text = "%s (图层)" % self._layer.name()
        else:
            fields_map = self._work.get("fields") or {}
            entry = normalize_field(fields_map.get(name) or empty_field())
            if extra_label is not None:
                entry["label"] = extra_label
            text = self._field_list_text(name, entry)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == name:
                item.setText(text)
                self._style_field_item(item, name)
                return

    def _on_label_text_changed(self, _text):
        if self._current_field == LAYER_ITEM_KEY:
            return
        self._update_list_item_text(self._current_field, extra_label=self.ed_label.text())

    def focus_field(self, field_name):
        field_name = (field_name or "").strip()
        if not field_name:
            return
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == field_name:
                self.list.setCurrentRow(i)
                return

    def _on_notes_text_changed(self):
        if not hasattr(self, "_notes_timer"):
            return
        if not self._can_edit_layer() or not self._current_field:
            return
        self._notes_timer.start(1200)

    def _flush_notes_quiet(self):
        self._flush_current()
        self.remarksChanged.emit()

    def _set_notes_visible(self, visible):
        if hasattr(self, "lbl_notes"):
            self.lbl_notes.setVisible(visible)
        if hasattr(self, "ed_notes"):
            self.ed_notes.setVisible(visible)

    def _set_meanings_visible(self, visible):
        if hasattr(self, "mean_panel"):
            self.mean_panel.setVisible(visible)

    def _set_notes_layout(self, stretch):
        """stretch=True: layer mode, notes fill remaining height."""
        if not hasattr(self, "ed_notes"):
            return
        if stretch:
            self.ed_notes.setMinimumHeight(getattr(self, "_notes_field_height", 72))
            self.ed_notes.setMaximumHeight(16777215)
            self.ed_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            height = getattr(self, "_notes_field_height", 72)
            self.ed_notes.setFixedHeight(height)
            self.ed_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if hasattr(self, "_right_lay"):
            self._right_lay.setStretchFactor(self.ed_notes, 1 if stretch else 0)
            if hasattr(self, "mean_panel"):
                self._right_lay.setStretchFactor(self.mean_panel, 0 if stretch else 1)

    def _set_notes_text(self, text):
        if not hasattr(self, "ed_notes"):
            return
        self.ed_notes.blockSignals(True)
        self.ed_notes.setPlainText(text or "")
        self.ed_notes.blockSignals(False)

    def _notes_text(self):
        if not hasattr(self, "ed_notes"):
            return ""
        return self.ed_notes.toPlainText()

    def _set_form_enabled(self, enabled):
        self.ed_label.setEnabled(enabled)
        if hasattr(self, "ed_notes"):
            self.ed_notes.setEnabled(enabled)
            self.ed_notes.setReadOnly(not enabled)
        self.ed_mean_cn.setEnabled(enabled)
        self.ed_mean_code.setEnabled(enabled)
        self.btn_mean_add.setEnabled(enabled)
        if hasattr(self, "cmb_mean_kind"):
            self.cmb_mean_kind.setEnabled(enabled)
        self._sync_var_insert_button()
        self.mean_list.setEnabled(enabled)
        if not enabled:
            if hasattr(self, "btn_mean_restore"):
                self.btn_mean_restore.setEnabled(False)
            self.btn_mean_del.setEnabled(False)
            self._sync_meaning_inputs(False)
        else:
            self._update_meaning_buttons()

    def _meanings_from_list(self):
        out = []
        if self._current_field in (None, LAYER_ITEM_KEY):
            return out
        for i in range(self.mean_list.count()):
            item = self.mean_list.item(i)
            data = item.data(Qt.UserRole)
            meaning = normalize_meaning(data if data is not None else item.text())
            if meaning:
                out.append(meaning)
        return out

    def _new_meaning_item(self, meaning, defaults=None):
        data = normalize_meaning(meaning)
        if defaults is None:
            defaults = self._qgis_value_map_defaults()
        item = QListWidgetItem(self._meaning_list_text(data, defaults))
        item.setData(Qt.UserRole, data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self._style_meaning_item(item, defaults)
        return item

    def _meaning_list_text(self, meaning, defaults=None):
        if self._current_field == LAYER_ITEM_KEY:
            return ""
        data = normalize_meaning(meaning)
        if not data:
            return ""
        text = meaning_display(data)
        origin = self._value_map_origin_text(data, defaults)
        if origin:
            return "%s　　原 %s" % (text, origin)
        return text

    def _value_map_origin_text(self, meaning, defaults=None):
        if not meaning or meaning.get("kind") != "const":
            return ""
        if defaults is None:
            defaults = self._qgis_value_map_defaults()
        key = value_key(meaning.get("value"))
        if key not in defaults:
            return ""
        return format_meaning(defaults[key], meaning.get("value") or "")

    def _is_value_map_meaning(self, meaning, defaults=None):
        item = normalize_meaning(meaning)
        if not item or item.get("kind") != "const":
            return False
        if defaults is None:
            defaults = self._qgis_value_map_defaults()
        return value_key(item.get("value")) in defaults

    def _sync_meaning_inputs(self, lock_value_map):
        form_on = bool(self.mean_list.isEnabled())
        self.ed_mean_code.setReadOnly(bool(lock_value_map))
        if hasattr(self, "cmb_mean_kind"):
            self.cmb_mean_kind.setEnabled(form_on and not lock_value_map)
            if lock_value_map:
                self._set_mean_kind("const")
        self._sync_var_insert_button()

    def _style_field_item(self, item, name):
        if item is None or name == LAYER_ITEM_KEY or self._layer is None:
            return
        idx = field_index(self._layer, name)
        if is_value_map_field(self._layer, idx):
            item.setForeground(QColor("#1b7a3d"))
            item.setToolTip("该字段有 QGIS 值映射")
        else:
            item.setForeground(QColor("#111111"))

    def _qgis_value_map_defaults(self):
        if self._current_field in (None, LAYER_ITEM_KEY) or self._layer is None:
            return {}
        key = (id(self._layer), self._current_field)
        cached = getattr(self, "_vm_defaults_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        data = value_map_defaults(self._layer, self._current_field)
        self._vm_defaults_cache = (key, data)
        return data

    def _style_meaning_item(self, item, defaults=None):
        if item is None or self._current_field == LAYER_ITEM_KEY:
            return
        meaning = normalize_meaning(item.data(Qt.UserRole) or item.text())
        if defaults is None:
            defaults = self._qgis_value_map_defaults()
        if meaning:
            item.setText(self._meaning_list_text(meaning, defaults))
        if self._is_value_map_meaning(meaning, defaults):
            item.setForeground(QColor("#1b7a3d"))
            item.setToolTip("QGIS 值映射项：说明可改，值不可改，不能删除")
        else:
            item.setForeground(QColor("#111111"))
            preview = self._meaning_write_preview(meaning)
            item.setToolTip(preview)

    def _update_restore_button(self, *_args):
        self._update_meaning_buttons()

    def _update_meaning_buttons(self, *_args):
        form_on = bool(self.mean_list.isEnabled())
        item = self.mean_list.currentItem()
        meaning = None
        if item is not None:
            meaning = normalize_meaning(item.data(Qt.UserRole) or item.text())
        is_vm = self._is_value_map_meaning(meaning)
        if hasattr(self, "btn_mean_restore"):
            self.btn_mean_restore.setEnabled(form_on and is_vm)
        if hasattr(self, "btn_mean_del"):
            self.btn_mean_del.setEnabled(form_on and item is not None and not is_vm)
        if self._mean_edit_row >= 0:
            edit_item = self.mean_list.item(self._mean_edit_row)
            edit_meaning = (
                normalize_meaning(edit_item.data(Qt.UserRole) or edit_item.text())
                if edit_item is not None
                else None
            )
            self._sync_meaning_inputs(self._is_value_map_meaning(edit_meaning))
        else:
            self._sync_meaning_inputs(False)

    def _restore_meaning_default(self):
        if not self._can_edit_layer():
            return
        item = self.mean_list.currentItem()
        if item is None:
            QMessageBox.information(self, "含义说明", "请先选中一行。")
            return
        meaning = normalize_meaning(item.data(Qt.UserRole) or item.text())
        defaults = self._qgis_value_map_defaults()
        key = value_key(meaning.get("value") if meaning else None)
        if not meaning or meaning.get("kind") != "const" or key not in defaults:
            QMessageBox.information(self, "含义说明", "这项不在当前值映射里。")
            return
        data = normalize_meaning(
            {
                "cn": defaults[key],
                "value": meaning.get("value"),
                "kind": "const",
            }
        )
        self.mean_list.blockSignals(True)
        item.setData(Qt.UserRole, data)
        self._style_meaning_item(item, defaults)
        self.mean_list.blockSignals(False)
        self._reset_meaning_edit()
        self._flush_and_notify()

    def _save_work(self):
        if not self._can_edit_layer():
            return
        layer = self._layer
        if layer is None:
            return
        self.session.set_layer_bundle(
            layer.name(),
            self._work.get("fields") or {},
            label=self._work.get("label") or "",
            notes=self._work.get("notes") or "",
        )

    def _flush_current(self):
        if not self._can_edit_layer():
            return
        name = self._current_field
        layer = self._layer
        if not name or layer is None:
            return
        if name == LAYER_ITEM_KEY:
            self._work["label"] = self.ed_label.text().strip()
            self._work["notes"] = self._notes_text()
            self._save_work()
            self._update_list_item_text(name)
            return
        fields = self._work.setdefault("fields", {})
        fields[name] = {
            "label": self.ed_label.text().strip(),
            "notes": self._notes_text(),
            "meanings": self._meanings_from_list(),
        }
        self._save_work()
        self._update_list_item_text(name)

    def _flush_and_notify(self):
        self._flush_current()
        self._reload_field_list(keep_name=self._current_field)
        self.remarksChanged.emit()

    def _reset_meaning_edit(self):
        self._mean_edit_row = -1
        self.btn_mean_add.setText("添加")
        self._sync_meaning_inputs(False)

    def _on_meaning_double_clicked(self, item):
        if item is None or not self._can_edit_layer():
            return
        if self._current_field in (None, LAYER_ITEM_KEY):
            return
        self.mean_list.setCurrentItem(item)
        self._begin_edit_meaning()

    def _begin_edit_meaning(self, *_args):
        if not self._can_edit_layer():
            return
        if self._current_field in (None, LAYER_ITEM_KEY):
            return
        row = self.mean_list.currentRow()
        if row < 0:
            return
        text = (self.mean_list.item(row).text() or "").strip()
        data = self.mean_list.item(row).data(Qt.UserRole)
        meaning = normalize_meaning(data if data is not None else text)
        if meaning is None:
            left, right, kind = parse_meaning_full(text)
        else:
            left, right, kind = meaning.get("cn") or "", meaning.get("value") or "", meaning.get("kind") or "const"
        self.ed_mean_cn.setText(left)
        self.ed_mean_code.setText(right)
        self._set_mean_kind(kind)
        self._mean_edit_row = row
        self.btn_mean_add.setText("修改")
        self._sync_meaning_inputs(self._is_value_map_meaning(meaning))
        self.ed_mean_cn.setFocus()
        self.ed_mean_cn.selectAll()

    def _load_field_form(self, name):
        if hasattr(self, "_notes_timer"):
            self._notes_timer.stop()
        self._reset_meaning_edit()
        self._current_field = name
        self.mean_list.blockSignals(True)
        self.mean_list.clear()
        if not name:
            self.ed_label.clear()
            self._set_notes_text("")
            self._set_notes_visible(False)
            self._set_meanings_visible(False)
            self._set_notes_layout(False)
            self.ed_mean_cn.clear()
            self.ed_mean_code.clear()
            self._set_form_enabled(False)
            if hasattr(self, "cmb_mean_kind"):
                self.cmb_mean_kind.setVisible(False)
            self.mean_list.blockSignals(False)
            return
        self._set_form_enabled(self._can_edit_layer())
        if name == LAYER_ITEM_KEY:
            self._set_meanings_visible(False)
            self._set_notes_visible(True)
            self._set_notes_layout(True)
            if hasattr(self, "ed_notes"):
                self.ed_notes.setPlaceholderText("图例悬停说明，多行，不赋值")
            self.ed_label.setPlaceholderText("图例悬停第一行，如 道路")
            self.ed_label.setText(self._work.get("label") or "")
            self._set_notes_text(self._work.get("notes") or "")
            self.mean_list.blockSignals(False)
            self._update_restore_button()
            return
        self.ed_label.setPlaceholderText("表头第一行显示，如 Type → 类型")
        self.lbl_meanings.setText(
            "含义说明（双击一行改说明；值映射项后面的「原」不变，不能删除）："
        )
        self._set_meanings_visible(True)
        self._set_notes_visible(True)
        self._set_notes_layout(False)
        if hasattr(self, "ed_notes"):
            self.ed_notes.setPlaceholderText("悬停时显示在中文名下面，不写入字段、不进插入下拉")
        if hasattr(self, "cmb_mean_kind"):
            self.cmb_mean_kind.setVisible(True)
            self._set_mean_kind("const")
        entry = normalize_field((self._work.get("fields") or {}).get(name) or empty_field())
        incoming, defaults = value_map_bundle(self._layer, name)
        self._vm_defaults_cache = ((id(self._layer), name), defaults)
        if incoming:
            merged = merge_value_map_meanings(entry.get("meanings") or [], incoming)
            if meanings_signature(merged) != meanings_signature(entry.get("meanings") or []):
                entry["meanings"] = merged
                fields = self._work.setdefault("fields", {})
                fields[name] = entry
                try:
                    locked = bool(self.session.is_placeholder())
                except Exception:
                    locked = True
                if not locked:
                    self._save_work()
                    self.remarksChanged.emit()
        self.ed_label.setText(entry.get("label") or "")
        self._set_notes_text(entry.get("notes") or "")
        for item in entry.get("meanings") or []:
            self.mean_list.addItem(self._new_meaning_item(item, defaults))
        self.mean_list.blockSignals(False)
        self._update_restore_button()

    def _on_field_changed(self, current, _previous):
        self._flush_current()
        name = current.data(Qt.UserRole) if current else None
        self._load_field_form(name)

    def _add_meaning(self):
        if not self._can_edit_layer():
            return
        if self._current_field in (None, LAYER_ITEM_KEY):
            return
        left = self.ed_mean_cn.text().strip()
        right = self.ed_mean_code.text().strip()
        kind = "const"
        if hasattr(self, "cmb_mean_kind"):
            kind = self.cmb_mean_kind.currentData() or "const"
        if kind == "expr" and not right:
            QMessageBox.information(self, "含义说明", "请粘贴 QGIS 表达式。")
            return
        text = format_meaning(left, right, kind)
        if not text:
            QMessageBox.information(self, "含义说明", "请至少填写中文或写入值。")
            return
        meaning = normalize_meaning({"cn": left or right, "value": right or left, "kind": kind})
        replace_row = self._mean_edit_row
        if 0 <= replace_row < self.mean_list.count():
            old = normalize_meaning(self.mean_list.item(replace_row).data(Qt.UserRole))
            if self._is_value_map_meaning(old):
                meaning = normalize_meaning(
                    {
                        "cn": left or (old.get("cn") if old else right),
                        "value": (old.get("value") if old else right),
                        "kind": "const",
                    }
                )
        display = meaning_display(meaning)
        existing = []
        for i in range(self.mean_list.count()):
            if i == replace_row:
                continue
            item = self.mean_list.item(i)
            existing.append(meaning_display(item.data(Qt.UserRole) or item.text()))
        if display in existing:
            QMessageBox.information(self, "含义说明", "该含义已存在。")
            return
        self.mean_list.blockSignals(True)
        if 0 <= replace_row < self.mean_list.count():
            item = self.mean_list.item(replace_row)
            item.setData(Qt.UserRole, meaning)
            self._style_meaning_item(item)
        else:
            self.mean_list.addItem(self._new_meaning_item(meaning))
        self.mean_list.blockSignals(False)
        self.ed_mean_cn.clear()
        self.ed_mean_code.clear()
        self.ed_mean_cn.setFocus()
        self._reset_meaning_edit()
        self._flush_and_notify()

    def _del_meaning(self):
        if not self._can_edit_layer():
            return
        if self._current_field in (None, LAYER_ITEM_KEY):
            return
        row = self.mean_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "含义说明", "请先选中一行。")
            return
        item = self.mean_list.item(row)
        meaning = normalize_meaning(
            (item.data(Qt.UserRole) or item.text()) if item is not None else None
        )
        if self._is_value_map_meaning(meaning):
            QMessageBox.information(self, "含义说明", "值映射项不能删除。")
            return
        self.mean_list.takeItem(row)
        self._reset_meaning_edit()
        self._flush_and_notify()

    def reload_from_session(self):
        keep = self._current_field
        layer = self._layer
        self._current_field = None
        if layer is None:
            self._work = empty_layer()
            self._reload_field_list()
            self._update_check_status()
            return
        self._work = self.session.layer_entry(layer.name())
        self._absorb_value_maps()
        self._reload_field_list(keep_name=keep)
        self._update_check_status()

    def _absorb_value_maps(self):
        """Merge QGIS value maps into meanings; keep our descriptions for the same value."""
        if self._layer is None or not self._can_edit_layer():
            return False
        try:
            if self.session.is_placeholder():
                return False
        except Exception:
            return False
        fields = self._work.setdefault("fields", {})
        changed = False
        for name in self._field_names():
            incoming = layer_value_map_meanings(self._layer, name)
            if not incoming:
                continue
            entry = normalize_field(fields.get(name) or empty_field())
            merged = merge_value_map_meanings(entry.get("meanings") or [], incoming)
            if meanings_signature(merged) != meanings_signature(entry.get("meanings") or []):
                entry["meanings"] = merged
                fields[name] = entry
                changed = True
        if changed:
            self._save_work()
            self.remarksChanged.emit()
        return changed

    def _update_check_status(self):
        from .remarks_remap import self_check_summary

        self._sync_placeholder_ui()
        text = "当前项目还没有图层配置。"
        try:
            text = self_check_summary(self.session)
        except Exception:
            text = "无法核对当前配置。"
        if hasattr(self, "lbl_status"):
            self.lbl_status.setText(text)
            self.lbl_status.setToolTip(text)

    def _sync_placeholder_ui(self):
        placeholder = False
        try:
            placeholder = bool(self.session.is_placeholder())
        except Exception:
            placeholder = False
        if placeholder and getattr(self.session, "enabled", False):
            self.session.set_enabled(False)
        if hasattr(self, "btn_enable"):
            self._sync_enable_buttons()
        can_edit = self._can_edit_layer()
        if hasattr(self, "btn_del"):
            self.btn_del.setEnabled(not placeholder)
        if hasattr(self, "btn_rename"):
            self.btn_rename.setEnabled(not placeholder)
        if hasattr(self, "btn_variables"):
            self.btn_variables.setEnabled(not placeholder)
        if hasattr(self, "list"):
            self.list.setEnabled(not placeholder)
        if can_edit and self._current_field:
            self._set_form_enabled(True)
        else:
            self._set_form_enabled(False)
        self._refresh_layer_caption()

    def _sync_var_insert_button(self):
        if not hasattr(self, "btn_mean_var"):
            return
        form_on = bool(self.mean_list.isEnabled()) if hasattr(self, "mean_list") else False
        kind = "const"
        if hasattr(self, "cmb_mean_kind"):
            kind = self.cmb_mean_kind.currentData() or "const"
        lock = False
        if self._mean_edit_row >= 0 and hasattr(self, "mean_list"):
            edit_item = self.mean_list.item(self._mean_edit_row)
            edit_meaning = (
                normalize_meaning(edit_item.data(Qt.UserRole) or edit_item.text())
                if edit_item is not None
                else None
            )
            lock = self._is_value_map_meaning(edit_meaning)
        self.btn_mean_var.setEnabled(form_on and kind == "const" and not lock)

    def _pick_insert_variable(self):
        if not self._can_edit_layer():
            return
        kind = "const"
        if hasattr(self, "cmb_mean_kind"):
            kind = self.cmb_mean_kind.currentData() or "const"
        if kind != "const":
            QMessageBox.information(self, "插入变量", "QGIS 表达式里不插入变量。")
            return
        variables = []
        try:
            variables = self.session.current_variables()
        except Exception:
            variables = []
        if not variables:
            QMessageBox.information(self, "插入变量", "请先在变量配置里添加变量。")
            return
        menu = QMenu(self)
        for item in variables:
            title = item.get("title") or ""
            value = item.get("value") or ""
            text = "%s = %s" % (title, value) if value else title
            act = menu.addAction(text)
            act.setData(title)
        chosen = menu.exec_(
            self.btn_mean_var.mapToGlobal(self.btn_mean_var.rect().bottomLeft())
        )
        if chosen is None:
            return
        title = chosen.data()
        if title:
            self.ed_mean_code.insert("{{%s}}" % title)
            self.ed_mean_code.setFocus()

    def _meaning_write_preview(self, meaning):
        if not meaning or meaning.get("kind") == "expr":
            return ""
        raw = meaning.get("value") or ""
        if not meaning_has_var_tokens(raw):
            return ""
        resolved, missing = resolve_var_template(raw, self.session.current_variables())
        if missing:
            return "缺少变量：%s" % "、".join(missing)
        return "当前写入：%s" % resolved


class VariablesDialog(QDialog):
    """Edit pack-level variables: title (label) + value (written content)."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._edit_row = -1
        self.setWindowTitle("变量配置 — %s" % (session.current_name() or ""))
        self.resize(420, 360)
        root = QVBoxLayout(self)
        tip = QLabel(
            "变量跟当前项目走，不是全 QGIS 共用。"
            "标题给人看，内容才是写入值。含义里插入 {{标题}}，点插入时再替换成当前内容。"
        )
        tip.setWordWrap(True)
        root.addWidget(tip)
        row = QHBoxLayout()
        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("标题，如 城市")
        self.ed_value = QLineEdit()
        self.ed_value.setPlaceholderText("内容，如 CITY")
        self.btn_add = QPushButton("添加")
        self.btn_add.clicked.connect(self._add)
        self.ed_title.returnPressed.connect(self._add)
        self.ed_value.returnPressed.connect(self._add)
        row.addWidget(self.ed_title, 1)
        row.addWidget(self.ed_value, 1)
        row.addWidget(self.btn_add)
        root.addLayout(row)
        self.list = QListWidget()
        self.list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list.itemDoubleClicked.connect(self._on_double_clicked)
        self.list.currentItemChanged.connect(self._update_buttons)
        root.addWidget(self.list, 1)
        btns = QHBoxLayout()
        self.btn_del = QPushButton("删除选中")
        self.btn_del.clicked.connect(self._del)
        btns.addWidget(self.btn_del)
        btns.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        btns.addWidget(buttons)
        root.addLayout(btns)
        self._reload()
        self._update_buttons()

    def _items(self):
        return list(self.session.current_variables())

    def _reload(self):
        self.list.blockSignals(True)
        self.list.clear()
        for item in self._items():
            title = item.get("title") or ""
            value = item.get("value") or ""
            row = QListWidgetItem("%s = %s" % (title, value) if value else title)
            row.setData(Qt.UserRole, item)
            self.list.addItem(row)
        self.list.blockSignals(False)

    def _reset_edit(self):
        self._edit_row = -1
        self.btn_add.setText("添加")
        self.ed_title.clear()
        self.ed_value.clear()

    def _on_double_clicked(self, item):
        if item is None:
            return
        data = item.data(Qt.UserRole) or {}
        self.ed_title.setText(data.get("title") or "")
        self.ed_value.setText(data.get("value") or "")
        self._edit_row = self.list.row(item)
        self.btn_add.setText("修改")
        self.ed_title.setFocus()
        self.ed_title.selectAll()

    def _add(self):
        title = self.ed_title.text().strip()
        value = self.ed_value.text()
        if not title:
            QMessageBox.information(self, "变量配置", "请填写标题。")
            return
        if "{{" in title or "}}" in title:
            QMessageBox.information(self, "变量配置", "标题里不能含 {{ 或 }}。")
            return
        items = self._items()
        replace = self._edit_row
        if 0 <= replace < len(items):
            old = items[replace].get("title") or ""
            for i, item in enumerate(items):
                if i == replace:
                    continue
                if (item.get("title") or "") == title:
                    QMessageBox.information(self, "变量配置", "标题「%s」已存在。" % title)
                    return
            if old and old != title and self._variable_in_use(old):
                if (
                    QMessageBox.question(
                        self,
                        "变量配置",
                        "含义里还引用着「%s」。改标题后，那些含义插入时会提示找不到。继续？"
                        % old,
                    )
                    != QMessageBox.Yes
                ):
                    return
            items[replace] = {"title": title, "value": value}
        else:
            if any((item.get("title") or "") == title for item in items):
                QMessageBox.information(self, "变量配置", "标题「%s」已存在。" % title)
                return
            items.append({"title": title, "value": value})
        self.session.set_current_variables(items)
        self._reload()
        self._reset_edit()
        self.ed_title.setFocus()

    def _del(self):
        row = self.list.currentRow()
        if row < 0:
            QMessageBox.information(self, "变量配置", "请先选中一行。")
            return
        items = self._items()
        if row >= len(items):
            return
        title = items[row].get("title") or ""
        if title and self._variable_in_use(title):
            if (
                QMessageBox.question(
                    self,
                    "变量配置",
                    "含义里还引用着「%s」，删除后插入会提示找不到。确定删除？" % title,
                )
                != QMessageBox.Yes
            ):
                return
        del items[row]
        self.session.set_current_variables(items)
        self._reload()
        self._reset_edit()

    def _variable_in_use(self, title):
        token = "{{%s}}" % title
        try:
            layers = self.session._layers()
        except Exception:
            return False
        for ldata in (layers or {}).values():
            for fentry in ((ldata or {}).get("fields") or {}).values():
                for meaning in (fentry or {}).get("meanings") or []:
                    item = normalize_meaning(meaning)
                    if item and token in (item.get("value") or ""):
                        return True
        return False

    def _update_buttons(self, *_args):
        self.btn_del.setEnabled(self.list.currentRow() >= 0)


class QuickNameDialog(QDialog):
    """Mini window: click a symbology class to assign its rule to selected features."""

    _instance = None
    _AUTOSAVE_CHOICES = (
        (0, "不自动保存"),
        (1000, "1秒后保存"),
        (2000, "2秒后保存"),
        (3000, "3秒后保存"),
        (4000, "4秒后保存"),
        (5000, "5秒后保存"),
        (10000, "10秒后保存"),
    )

    @classmethod
    def open_for(cls, iface, parent=None):
        dlg = cls._instance
        try:
            if dlg is not None:
                dlg.windowTitle()
        except Exception:
            dlg = None
            cls._instance = None
        if dlg is None:
            dlg = cls(iface, parent=parent)
            cls._instance = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._layer = None
        self._reloading = False
        _as_window(self)
        self.setWindowTitle("快速命名")
        self.resize(300, 380)

        root = QVBoxLayout(self)
        self.lbl_layer = QLabel("请选择矢量图层")
        self.lbl_layer.setWordWrap(True)
        self.on_theme_changed()
        root.addWidget(self.lbl_layer)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self.list, 1)

        pin_row = QHBoxLayout()
        self.chk_pin = QCheckBox("钉住图层")
        self.chk_pin.setChecked(False)
        self.chk_pin.setToolTip(
            "钉住当前分类图层。在本层选中要素再点分类：只改属性、不复制。"
            "在其他层选中再点分类：把几何复制进钉住层，再按该类规则赋值。"
            "来源图层不改；钉住层不增加来源字段。"
        )
        self.chk_pin.toggled.connect(self._on_pin_toggled)
        self.cmb_autosave = QComboBox()
        for ms, label in self._AUTOSAVE_CHOICES:
            self.cmb_autosave.addItem(label, ms)
        self.cmb_autosave.setCurrentIndex(0)
        self.cmb_autosave.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb_autosave.setToolTip(
            "默认「不自动保存」：还能撤销/回滚，QGIS 图例数量不会马上变。"
            "选「N秒后保存」：先只写入，等 N 秒再点一次 QGIS 自带的「保存图层编辑」。"
            "连续命名会按当前秒数重新计时，只存一次。中途改成不自动保存则取消这次预约。"
            "图例由 QGIS 自己刷。会保存该层当前所有未保存修改，这次不能再撤销。"
            "关掉窗口会立刻补存。3 秒已验证能跟上图例；1 秒可能仍偏赶。"
        )
        self.cmb_autosave.currentIndexChanged.connect(self._on_autosave_mode_changed)
        pin_row.addWidget(self.chk_pin)
        pin_row.addWidget(self.cmb_autosave)
        pin_row.addStretch(1)
        root.addLayout(pin_row)

        self.chk_skip_confirm = QCheckBox("勾选后点分类不再确认，直接赋值")
        self.chk_skip_confirm.setChecked(False)
        self.chk_skip_confirm.setToolTip("默认不勾选：会弹出确认。勾选后直接写入。")
        root.addWidget(self.chk_skip_confirm)

        self.btn_legend_count = QPushButton("刷新图例计数")
        self.btn_legend_count.clicked.connect(self._on_refresh_legend_counts)
        root.addWidget(self.btn_legend_count)

        self._pinned_layer = None
        self._saving = False
        self._touching_legend = False
        self._autosave_layer = None
        self._cat_items = []
        self._counts = {}
        self._other_count = 0
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.reload)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._flush_autosave)

        try:
            self.iface.currentLayerChanged.connect(self._on_qgis_layer_changed)
        except Exception:
            pass
        try:
            QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_removed)
        except Exception:
            pass
        self._bind_layer(self._qgis_vector_layer())
        self._reload_timer.start(0)

    def on_theme_changed(self):
        lbl = getattr(self, "lbl_layer", None)
        if lbl is None:
            return
        lbl.setStyleSheet(
            "QLabel { font-size: 16px; font-weight: bold; color: %s; }" % theme.color("title")
        )

    def closeEvent(self, event):
        self._reload_timer.stop()
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
            self._flush_autosave()
        self._bind_layer(None)
        try:
            self.iface.currentLayerChanged.disconnect(self._on_qgis_layer_changed)
        except Exception:
            pass
        try:
            QgsProject.instance().layersWillBeRemoved.disconnect(self._on_layers_removed)
        except Exception:
            pass
        QuickNameDialog._instance = None
        super().closeEvent(event)

    @staticmethod
    def _layer_in(layer, layer_ids):
        if layer is None:
            return False
        try:
            return layer.id() in layer_ids
        except RuntimeError:
            return True

    def _on_layers_removed(self, layer_ids):
        ids = set(layer_ids or [])
        if self._layer_in(self._autosave_layer, ids):
            self._autosave_timer.stop()
            self._flush_autosave()
            self._autosave_layer = None
        pinned_gone = self._layer_in(self._pinned_layer, ids)
        if pinned_gone:
            self._pinned_layer = None
            self.chk_pin.blockSignals(True)
            self.chk_pin.setChecked(False)
            self.chk_pin.blockSignals(False)
        if self._layer_in(self._layer, ids):
            self._bind_layer(None)
            self._layer = None
        if pinned_gone or self._layer is None:
            active = self._qgis_vector_layer()
            if self._layer_in(active, ids):
                active = None
            self._bind_layer(active)
            self._schedule_reload()

    def _as_vector(self, layer):
        if layer is None or not hasattr(layer, "type"):
            return None
        if layer.type() != QgsMapLayer.VectorLayer:
            return None
        return layer

    def _qgis_vector_layer(self):
        layer = None
        try:
            layer = self.iface.activeLayer()
        except Exception:
            layer = None
        return self._as_vector(layer)

    def _on_pin_toggled(self, checked):
        if checked:
            self._pinned_layer = self._layer
            self._refresh_layer_caption()
            return
        self._pinned_layer = None
        self._bind_layer(self._qgis_vector_layer())
        self._schedule_reload()

    def _dest_layer(self):
        if self.chk_pin.isChecked() and self._pinned_layer is not None:
            return self._pinned_layer
        return self._layer

    def _selected_fids(self, layer):
        if layer is None:
            return []
        try:
            return [int(fid) for fid in layer.selectedFeatureIds()]
        except Exception:
            return []

    def _pick_source_layer(self, dest):
        active = self._qgis_vector_layer()
        if dest is None:
            return active
        if active is not None and not layers_are_same(active, dest) and self._selected_fids(active):
            return active
        if self._selected_fids(dest):
            return dest
        if self.chk_pin.isChecked():
            try:
                layers = QgsProject.instance().mapLayers().values()
            except Exception:
                layers = []
            for lyr in layers:
                lyr = self._as_vector(lyr)
                if lyr is None or layers_are_same(lyr, dest):
                    continue
                if self._selected_fids(lyr) and layer_geom_kind(lyr) == layer_geom_kind(dest):
                    return lyr
        return dest if dest is not None else active

    def _autosave_delay_ms(self):
        try:
            return int(self.cmb_autosave.currentData() or 0)
        except (TypeError, ValueError):
            return 0

    def _on_autosave_mode_changed(self, _index):
        delay = self._autosave_delay_ms()
        if delay <= 0:
            self._autosave_timer.stop()
            self._autosave_layer = None
            return
        if self._autosave_layer is not None:
            self._autosave_timer.start(delay)

    def _schedule_autosave(self, dest):
        delay = self._autosave_delay_ms()
        if dest is None or delay <= 0:
            return
        pending = self._autosave_layer
        if pending is not None and not layers_are_same(pending, dest):
            self._autosave_timer.stop()
            self._flush_autosave()
        self._autosave_layer = dest
        self._autosave_timer.start(delay)

    def _flush_autosave(self):
        dest = self._autosave_layer
        self._autosave_layer = None
        if dest is None:
            return
        try:
            if not dest.isEditable() or not dest.isModified():
                return
        except Exception:
            return
        self._saving = True
        try:
            save_err = save_edits_via_qgis(dest, self.iface)
        finally:
            self._saving = False
        if save_err:
            QMessageBox.information(self, "快速命名", "已写入，但 QGIS 保存失败：%s" % save_err)

    def _on_qgis_layer_changed(self, layer):
        if getattr(self, "_saving", False):
            return
        layer = self._as_vector(layer)
        if self.chk_pin.isChecked() and self._pinned_layer is not None:
            return
        self._bind_layer(layer)
        self._schedule_reload()

    def _schedule_reload(self):
        if self._reloading or getattr(self, "_touching_legend", False):
            return
        self._reload_timer.start(80)

    def _on_refresh_legend_counts(self):
        dest = self._dest_layer()
        if dest is None:
            QMessageBox.information(self, "快速命名", "请先选择一个矢量图层。")
            return
        self._touching_legend = True
        try:
            err = refresh_legend_class_counts(dest)
        finally:
            self._touching_legend = False
        if err:
            QMessageBox.information(self, "快速命名", err)

    def _bind_layer(self, layer):
        old = self._layer
        if old is not None:
            for signal, slot in (
                (getattr(old, "rendererChanged", None), self._schedule_reload),
            ):
                if signal is None:
                    continue
                try:
                    signal.disconnect(slot)
                except Exception:
                    pass
        self._layer = layer
        if layer is None:
            return
        try:
            layer.rendererChanged.connect(self._schedule_reload)
        except Exception:
            pass

    def _displayed_total(self):
        total = 0
        for i in range(self.list.count()):
            try:
                total += int(self.list.item(i).data(Qt.UserRole + 4) or 0)
            except (TypeError, ValueError):
                pass
        return total

    def _refresh_layer_caption(self):
        dest = self._dest_layer()
        if dest is None:
            self.lbl_layer.setText("请在 QGIS 中选择一个矢量图层")
            return
        name = dest.name()
        if self.chk_pin.isChecked():
            text = "钉住：%s" % name
        else:
            text = name
        if self.list.count():
            text = "%s（%s）" % (text, self._displayed_total())
        self.lbl_layer.setText(text)

    def reload(self):
        if self._reloading:
            return
        self._reloading = True
        layer = self._dest_layer()
        self.list.clear()
        self._cat_items = []
        self._counts = {}
        self._other_count = 0
        try:
            self._refresh_layer_caption()
            if layer is None:
                return
            try:
                items, _err = layer_categories(layer)
            except Exception:
                items = []
            self._cat_items = items
            if items:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    self._counts, self._other_count = count_category_keys(layer, items)
                except Exception:
                    self._counts, self._other_count = {}, 0
                finally:
                    QApplication.restoreOverrideCursor()
            other_used = False
            for info in items:
                label = info.get("label") or "(未命名)"
                hint = info.get("hint") or ""
                text = label
                if hint and hint != label:
                    text = "%s  [%s]" % (label, hint)
                key = assignment_key(info.get("assignments") or {})
                if key is None:
                    count = self._other_count if not other_used else 0
                    other_used = True
                else:
                    count = int(self._counts.get(key, 0))
                item = QListWidgetItem(_color_icon(info.get("color")), "%s  (%s)" % (text, count))
                item.setData(Qt.UserRole, info.get("assignments") or {})
                item.setData(Qt.UserRole + 1, bool(info.get("assignable")))
                item.setData(Qt.UserRole + 2, key)
                item.setData(Qt.UserRole + 3, text)
                item.setData(Qt.UserRole + 4, count)
                item.setToolTip(hint or label)
                if not info.get("assignable") or info.get("legend_on") is False:
                    item.setForeground(QColor("#888888"))
                self.list.addItem(item)
            self._refresh_layer_caption()
        finally:
            self._reloading = False

    def _adjust_item_count(self, key, delta):
        if not delta:
            return
        if key is None:
            self._other_count = max(0, self._other_count + delta)
        else:
            self._counts[key] = max(0, int(self._counts.get(key, 0)) + delta)
        other_used = False
        for i in range(self.list.count()):
            item = self.list.item(i)
            item_key = item.data(Qt.UserRole + 2)
            if item_key is None:
                if other_used:
                    continue
                other_used = True
                n = self._other_count
            elif item_key == key:
                n = int(self._counts.get(item_key, 0))
            else:
                continue
            base = item.data(Qt.UserRole + 3) or item.text()
            item.setData(Qt.UserRole + 4, n)
            item.setText("%s  (%s)" % (base, n))
        self._refresh_layer_caption()

    def _on_item_clicked(self, item):
        if item is None:
            return
        dest = self._dest_layer()
        if dest is None:
            return
        assignable = bool(item.data(Qt.UserRole + 1))
        assignments = item.data(Qt.UserRole) or {}
        if not assignable or not assignments:
            QMessageBox.information(self, "快速命名", "这个分类无法从符号化规则反推出要写的字段值。")
            return
        source = self._pick_source_layer(dest)
        fids = self._selected_fids(source)
        if not fids:
            QMessageBox.information(self, "快速命名", "请先在地图或属性表中选中要素。")
            return
        cat = item.data(Qt.UserRole + 3) or (item.text() or "").split("  (")[0]
        writes = format_assignments(assignments)
        same = layers_are_same(source, dest)
        if not self.chk_skip_confirm.isChecked():
            if same:
                msg = "已选中 %s 个要素。\n将归属到分类「%s」。\n写入：%s\n继续？" % (
                    len(fids),
                    cat,
                    writes,
                )
            else:
                msg = (
                    "将把 %s 个要素从「%s」复制到「%s」，并归属分类「%s」。\n"
                    "来源图层不改。写入：%s\n继续？"
                    % (len(fids), source.name(), dest.name(), cat, writes)
                )
            reply = QMessageBox.question(self, "快速命名", msg)
            if reply != QMessageBox.Yes:
                return
        old_keys = {}
        if same:
            try:
                old_keys = category_keys_for_fids(dest, self._cat_items, fids)
            except Exception:
                old_keys = {}
        updated, err, changed = self._apply_with_busy_ui(source, dest, assignments, fids)
        if err:
            QMessageBox.information(self, "快速命名", err)
            return
        if updated:
            new_key = assignment_key(assignments)
            if changed is None:
                self._adjust_item_count(new_key, int(updated))
            else:
                delta = {}
                for fid in changed:
                    old = old_keys.get(int(fid))
                    delta[old] = delta.get(old, 0) - 1
                    delta[new_key] = delta.get(new_key, 0) + 1
                for key, n in delta.items():
                    self._adjust_item_count(key, n)
            refresh_layer_after_assign(dest, self.iface)
            if self._autosave_delay_ms() > 0:
                self._schedule_autosave(dest)
            notify_open_attribute_tables(
                dest, list(assignments.keys()), force_reload=not same
            )

    def _apply_with_busy_ui(self, source, dest, assignments, fids):
        canvas = None
        frozen = False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            try:
                canvas = self.iface.mapCanvas()
                if canvas is not None and not canvas.isFrozen():
                    canvas.freeze(True)
                    frozen = True
            except Exception:
                frozen = False
            if layers_are_same(source, dest):
                return apply_assignments(dest, assignments, fids)
            return copy_geoms_and_assign(source, dest, fids, assignments)
        finally:
            if frozen and canvas is not None:
                try:
                    canvas.freeze(False)
                except Exception:
                    pass
            QApplication.restoreOverrideCursor()


def _color_icon(color_name, size=16):
    pix = QPixmap(size, size)
    color = QColor(color_name) if color_name else QColor("#cccccc")
    if not color.isValid():
        color = QColor("#cccccc")
    pix.fill(color)
    return QIcon(pix)


RemarksDialog = RemarksHubDialog
LayerRemarksDialog = RemarksHubDialog
