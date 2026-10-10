# -*- coding: utf-8 -*-
from ...i18n import tr
"""Field mapping copy UI (full version)."""
import html
from collections import Counter

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QCheckBox,
    QLabel,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QWidget,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from qgis.core import QgsProject

from .layer_utils import (
    FILTER_ALL,
    FILTER_POINT,
    FILTER_LINE,
    FILTER_POLYGON,
    FILTER_LABELS,
    list_vector_layers,
    layer_display_label,
    field_type_label,
)
from .layer_source import (
    VECTOR_OPEN_FILTER,
    query_file_sublayers,
    sublayer_label,
    load_vector_layer,
    add_layer_to_project,
)
from .field_transfer import (
    transfer_features,
    geometry_types_compatible,
    auto_match_target_to_source,
    field_fill_stats,
)
from .mapping_store import load_mapping_config, save_mapping_config

SKIP_LABEL = tr("（不映射）")
DUP_COMBO_STYLE = (
    "QComboBox { background: #ffebee; color: #c62828; font-weight: bold;"
    " border: 1px solid #e57373; }"
)


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class SublayerPickDialog(QDialog):
    def __init__(self, path, sublayers, parent=None):
        super().__init__(parent)
        self.path = path
        self.sublayers = sublayers
        self.selected = None
        self.setWindowTitle(tr("选择子图层"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("文件包含多个图层，请选择要加载的图层：")))
        self.list_widget = QListWidget()
        for i, sl in enumerate(sublayers):
            self.list_widget.addItem(QListWidgetItem(sublayer_label(sl, i)))
        self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        row = self.list_widget.currentRow()
        if row < 0:
            QMessageBox.warning(self, tr("字段映射复制"), tr("请选择一个子图层。"))
            return
        self.selected = self.sublayers[row]
        self.accept()


class TransferTab(QWidget):
    def __init__(self, parent_dialog):
        super().__init__()
        self.parent_dialog = parent_dialog
        self._building_table = False
        self._syncing_filter = False
        self._fill_stats = {}
        self._fill_stats_layer_id = None
        self._saved = load_mapping_config()
        self._init_ui()
        self._apply_saved_filter()
        self._apply_saved_options()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layer_box = QGroupBox(tr("图层选择"))
        layer_form = QFormLayout(layer_box)

        self.source_filter = self._make_filter_combo()
        self.target_filter = self._make_filter_combo()
        self.source_combo = QComboBox()
        self.target_combo = QComboBox()

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_filter)
        source_row.addWidget(self.source_combo, 1)
        self.load_file_btn = QPushButton(tr("从文件加载…"))
        source_row.addWidget(self.load_file_btn)

        target_row = QHBoxLayout()
        target_row.addWidget(self.target_filter)
        target_row.addWidget(self.target_combo, 1)

        layer_form.addRow(tr("源图层"), source_row)
        layer_form.addRow(tr("目标图层"), target_row)
        layout.addWidget(layer_box)

        self.lbl_unused = QLabel(tr("未匹配源字段："))
        self.lbl_unused.setWordWrap(True)
        self.lbl_unused.setTextFormat(Qt.RichText)
        self.lbl_unused.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_unused.setStyleSheet(
            "background:#fafafa; border: none; padding: 2px 6px; color:#37474f;"
        )
        unused_box = QScrollArea()
        unused_box.setWidget(self.lbl_unused)
        unused_box.setWidgetResizable(True)
        unused_box.setMaximumHeight(40)
        unused_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        unused_box.setFrameShape(QFrame.StyledPanel)
        unused_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        unused_box.setStyleSheet(
            "QScrollArea { background:#fafafa; border: 1px solid #cfd8dc; border-radius: 4px; }"
        )
        layout.addWidget(unused_box)

        self.chk_fuzzy = QCheckBox(tr("模糊匹配"))
        self.chk_fuzzy.setChecked(True)
        self.chk_fuzzy.setToolTip(
            tr('用于「按名称自动匹配」：去掉空格/下划线后仍唯一，或一方名称包含另一方且只能唯一配对时才自动填入。')
        )
        self.chk_hide_matched = QCheckBox(tr("隐藏已匹配源字段"))
        self.chk_hide_matched.setChecked(True)
        self.chk_hide_matched.setToolTip(
            tr('开启时：已经配给某一目标字段的源字段，不再出现在其它行的下拉里。关闭后可把同一源字段配给多个目标字段，重复项会标红。')
        )

        self.auto_match_btn = QPushButton(tr("按名称自动匹配"))
        self.clear_map_btn = QPushButton(tr("清空映射"))
        self.refresh_btn = QPushButton(tr("刷新图层列表"))
        self.save_btn = QPushButton(tr("保存"))
        self.transfer_btn = QPushButton(tr("开始复制"))
        map_btn_row = QHBoxLayout()
        map_btn_row.addWidget(self.chk_fuzzy)
        map_btn_row.addWidget(self.chk_hide_matched)
        map_btn_row.addWidget(self.auto_match_btn)
        map_btn_row.addWidget(self.clear_map_btn)
        map_btn_row.addStretch()
        map_btn_row.addWidget(self.refresh_btn)
        map_btn_row.addWidget(self.save_btn)
        map_btn_row.addWidget(self.transfer_btn)
        layout.addLayout(map_btn_row)

        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels(
            [tr("目标字段"), tr("目标类型"), tr("目标别名"), tr("源字段")]
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.mapping_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mapping_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mapping_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mapping_table.setMinimumSize(0, 0)
        layout.addWidget(self.mapping_table, 1)

        opt_box = QGroupBox(tr("复制选项"))
        opt_layout = QHBoxLayout(opt_box)
        self.only_selected_cb = QCheckBox(tr("仅复制源图层中选中的要素"))
        self.reproject_cb = QCheckBox(tr("坐标系不同时自动重投影到目标图层"))
        self.reproject_cb.setChecked(True)
        opt_layout.addWidget(self.only_selected_cb)
        opt_layout.addWidget(self.reproject_cb)
        opt_layout.addStretch()
        layout.addWidget(opt_box)

        self.source_filter.currentIndexChanged.connect(self._on_source_filter_changed)
        self.target_filter.currentIndexChanged.connect(self._on_target_filter_changed)
        self.source_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.target_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.chk_hide_matched.toggled.connect(self._rebuild_source_combos)
        self.auto_match_btn.clicked.connect(self._auto_match)
        self.clear_map_btn.clicked.connect(self._clear_mapping)
        self.refresh_btn.clicked.connect(self.refresh_layers)
        self.save_btn.clicked.connect(self._save_clicked)
        self.load_file_btn.clicked.connect(self._load_from_file)
        self.transfer_btn.clicked.connect(self._run_transfer)

    def _make_filter_combo(self):
        combo = QComboBox()
        for key in (FILTER_ALL, FILTER_POINT, FILTER_LINE, FILTER_POLYGON):
            combo.addItem(tr(FILTER_LABELS[key]), key)
        return combo

    def _filter_mode(self, combo):
        return combo.currentData() or FILTER_ALL

    def _apply_saved_filter(self):
        mode = self._saved.get("filter_mode")
        idx = self.source_filter.findData(mode)
        if idx < 0:
            return
        self._syncing_filter = True
        self.source_filter.blockSignals(True)
        self.target_filter.blockSignals(True)
        self.source_filter.setCurrentIndex(idx)
        self.target_filter.setCurrentIndex(idx)
        self.source_filter.blockSignals(False)
        self.target_filter.blockSignals(False)
        self._syncing_filter = False

    def _apply_saved_options(self):
        if "only_selected" in self._saved:
            self.only_selected_cb.setChecked(bool(self._saved["only_selected"]))
        if "reproject" in self._saved:
            self.reproject_cb.setChecked(bool(self._saved["reproject"]))
        if "fuzzy_match" in self._saved:
            self.chk_fuzzy.setChecked(bool(self._saved["fuzzy_match"]))
        if "hide_matched" in self._saved:
            self.chk_hide_matched.blockSignals(True)
            self.chk_hide_matched.setChecked(bool(self._saved["hide_matched"]))
            self.chk_hide_matched.blockSignals(False)

    def _on_source_filter_changed(self, index):
        if self._syncing_filter:
            return
        self._syncing_filter = True
        self.target_filter.setCurrentIndex(index)
        self._syncing_filter = False
        self.refresh_layers()

    def _on_target_filter_changed(self, index):
        if self._syncing_filter:
            return
        self._syncing_filter = True
        self.source_filter.setCurrentIndex(index)
        self._syncing_filter = False
        self.refresh_layers()

    def refresh_layers(self):
        current_source = self.source_combo.currentData()
        current_target = self.target_combo.currentData()

        self.source_combo.blockSignals(True)
        self.target_combo.blockSignals(True)
        self.source_combo.clear()
        self.target_combo.clear()

        filter_mode = self._filter_mode(self.source_filter)
        for layer in list_vector_layers(filter_mode):
            self.source_combo.addItem(layer_display_label(layer), layer.id())
        for layer in list_vector_layers(filter_mode):
            self.target_combo.addItem(layer_display_label(layer), layer.id())

        if not self._restore_combo(self.source_combo, current_source):
            self._restore_layer_combo(
                self.source_combo,
                self._saved.get("source_layer_id"),
                self._saved.get("source_layer_name"),
            )
        if not self._restore_combo(self.target_combo, current_target):
            self._restore_layer_combo(
                self.target_combo,
                self._saved.get("target_layer_id"),
                self._saved.get("target_layer_name"),
            )

        self.source_combo.blockSignals(False)
        self.target_combo.blockSignals(False)
        self._rebuild_mapping_table()

    def _restore_combo(self, combo, layer_id):
        if not layer_id:
            return False
        idx = combo.findData(layer_id)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return True
        return False

    def _restore_layer_combo(self, combo, layer_id, layer_name):
        if self._restore_combo(combo, layer_id):
            return True
        if layer_name:
            for i in range(combo.count()):
                layer = QgsProject.instance().mapLayer(combo.itemData(i))
                if layer is not None and layer.name() == layer_name:
                    combo.setCurrentIndex(i)
                    return True
        combo.setCurrentIndex(-1)
        return False

    def _current_layer(self, combo):
        layer_id = combo.currentData()
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _on_layer_changed(self):
        self._rebuild_mapping_table()

    def _source_field_names(self):
        layer = self._current_layer(self.source_combo)
        if not layer:
            return []
        return [f.name() for f in layer.fields()]

    def _source_fill_stats(self):
        layer = self._current_layer(self.source_combo)
        if not layer:
            self._fill_stats = {}
            self._fill_stats_layer_id = None
            return {}
        if self._fill_stats_layer_id == layer.id() and self._fill_stats:
            return self._fill_stats
        self._fill_stats = field_fill_stats(layer)
        self._fill_stats_layer_id = layer.id()
        return self._fill_stats

    def _source_field_label(self, name):
        filled, total = self._source_fill_stats().get(name, (0, 0))
        return "{}({}/{})".format(name, filled, total)

    def _make_source_combo(self, keep_name="", used_others=None):
        combo = NoWheelComboBox()
        combo.addItem(SKIP_LABEL, "")
        hide_used = self.chk_hide_matched.isChecked()
        used_others = used_others or set()
        for src_name in self._source_field_names():
            if hide_used and src_name and src_name != keep_name and src_name in used_others:
                continue
            combo.addItem(self._source_field_label(src_name), src_name)
        if keep_name and combo.findData(keep_name) < 0:
            combo.addItem(self._source_field_label(keep_name), keep_name)
        combo.currentIndexChanged.connect(self._on_mapping_combo_changed)
        return combo

    def _on_mapping_combo_changed(self):
        if self._building_table:
            return
        self._rebuild_source_combos()

    def _rebuild_source_combos(self):
        if self._building_table:
            return
        rows = list(self._iter_mapping_combos())
        used_map = {row: combo.currentData() or "" for row, combo in rows}
        self._building_table = True
        for row, _combo in rows:
            keep = used_map.get(row) or ""
            used_others = set(name for other, name in used_map.items() if other != row and name)
            new_combo = self._make_source_combo(keep_name=keep, used_others=used_others)
            idx = new_combo.findData(keep) if keep else 0
            new_combo.blockSignals(True)
            new_combo.setCurrentIndex(idx if idx >= 0 else 0)
            new_combo.blockSignals(False)
            self.mapping_table.setCellWidget(row, 3, new_combo)
        self._building_table = False
        self._refresh_mapping_status()

    def _refresh_mapping_status(self):
        source_names = self._source_field_names()
        used = []
        for _row, combo in self._iter_mapping_combos():
            used.append(combo.currentData() or "")
        counts = Counter(name for name in used if name)
        dup_names = {name for name, count in counts.items() if count > 1}

        for _row, combo in self._iter_mapping_combos():
            name = combo.currentData() or ""
            if name in dup_names:
                combo.setStyleSheet(DUP_COMBO_STYLE)
                combo.setToolTip(
                    tr("源字段「{}」已被 {} 个目标字段使用").format(name, counts[name])
                )
            else:
                combo.setStyleSheet("")
                combo.setToolTip(self._source_field_label(name) if name else "")

        lines = []
        unused = [name for name in source_names if name not in counts]
        if self._current_layer(self.source_combo) is None:
            lines.append(tr("未匹配源字段：请先选择源图层"))
        elif not unused:
            lines.append(tr("未匹配源字段：无"))
        else:
            parts = [
                '<span style="color:#37474f;">{}</span>'.format(html.escape(name))
                for name in unused
            ]
            lines.append(tr("未匹配源字段（{}）：{}").format(len(unused), "、".join(parts)))

        if dup_names:
            dup_parts = [
                '<span style="color:#c62828; font-weight:bold;">{}（{}）</span>'.format(
                    html.escape(name), counts[name]
                )
                for name in source_names
                if name in dup_names
            ]
            lines.append(
                tr("重复使用源字段（{}）：{}").format(len(dup_names), "、".join(dup_parts))
            )
        self.lbl_unused.setText("<br>".join(lines))

    def _rebuild_mapping_table(self):
        self._building_table = True
        self._fill_stats = {}
        self._fill_stats_layer_id = None
        target_layer = self._current_layer(self.target_combo)
        self.mapping_table.setRowCount(0)

        if target_layer is None:
            self._building_table = False
            self._refresh_mapping_status()
            return

        fields = target_layer.fields()
        self.mapping_table.setRowCount(len(fields))
        for row, field in enumerate(fields):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(field.name()))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(field_type_label(field)))
            alias = field.alias() or "—"
            self.mapping_table.setItem(row, 2, QTableWidgetItem(alias if alias else "—"))

            combo = self._make_source_combo()
            saved_src = (self._saved.get("mapping") or {}).get(field.name())
            combo.blockSignals(True)
            if saved_src:
                saved_idx = combo.findData(saved_src)
                if saved_idx >= 0:
                    combo.setCurrentIndex(saved_idx)
            combo.blockSignals(False)
            self.mapping_table.setCellWidget(row, 3, combo)

        self._building_table = False
        self._rebuild_source_combos()

    def _iter_mapping_combos(self):
        for row in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(row, 3)
            if combo is not None:
                yield row, combo

    def _auto_match(self):
        target_layer = self._current_layer(self.target_combo)
        if target_layer is None:
            return
        target_names = [field.name() for field in target_layer.fields()]
        mapping = auto_match_target_to_source(
            target_names,
            self._source_field_names(),
            fuzzy=self.chk_fuzzy.isChecked(),
        )
        source_names = self._source_field_names()
        self._building_table = True
        for row, combo in self._iter_mapping_combos():
            src_name = mapping.get(target_names[row], "")
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(SKIP_LABEL, "")
            for src_opt in source_names:
                combo.addItem(self._source_field_label(src_opt), src_opt)
            idx = combo.findData(src_name) if src_name else 0
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        self._building_table = False
        self._rebuild_source_combos()

    def _clear_mapping(self):
        self._building_table = True
        for _, combo in self._iter_mapping_combos():
            combo.setCurrentIndex(0)
        self._building_table = False
        self._rebuild_source_combos()

    def _collect_mapping(self):
        target_layer = self._current_layer(self.target_combo)
        if target_layer is None:
            return {}
        mapping = {}
        fields = target_layer.fields()
        for row, combo in self._iter_mapping_combos():
            src_name = combo.currentData()
            if src_name:
                mapping[fields.at(row).name()] = src_name
        return mapping

    def _collect_mapping_for_save(self):
        mapping = dict(self._saved.get("mapping") or {})
        target_layer = self._current_layer(self.target_combo)
        if target_layer is None:
            return mapping
        fields = target_layer.fields()
        for row, combo in self._iter_mapping_combos():
            mapping[fields.at(row).name()] = combo.currentData() or ""
        return mapping

    def _build_save_payload(self):
        source = self._current_layer(self.source_combo)
        target = self._current_layer(self.target_combo)
        return {
            "filter_mode": self._filter_mode(self.source_filter),
            "source_layer_id": source.id() if source else "",
            "source_layer_name": source.name() if source else "",
            "target_layer_id": target.id() if target else "",
            "target_layer_name": target.name() if target else "",
            "mapping": self._collect_mapping_for_save(),
            "only_selected": self.only_selected_cb.isChecked(),
            "reproject": self.reproject_cb.isChecked(),
            "fuzzy_match": self.chk_fuzzy.isChecked(),
            "hide_matched": self.chk_hide_matched.isChecked(),
        }

    def _persist_config(self, silent=True):
        payload = self._build_save_payload()
        ok, error = save_mapping_config(payload)
        if ok:
            self._saved = payload
        return ok, error

    def _save_clicked(self):
        ok, error = self._persist_config()
        if ok:
            QMessageBox.information(self, tr("字段映射复制"), tr("已保存当前图层选择和字段映射。"))
        else:
            QMessageBox.critical(self, tr("字段映射复制"), tr("保存失败：{}").format(error))

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("选择矢量文件"), "", VECTOR_OPEN_FILTER)
        if not path:
            return

        sublayers = query_file_sublayers(path)
        if not sublayers:
            QMessageBox.warning(
                self,
                tr("字段映射复制"),
                tr('无法读取该文件或未包含矢量图层。\nKMZ 已尝试直接打开、读取压缩包内 KML，以及解压后再读。\n请确认文件能被 QGIS「数据源管理器」打开。'),
            )
            return

        sublayer = sublayers[0]
        if len(sublayers) > 1:
            dlg = SublayerPickDialog(path, sublayers, self)
            if dlg.exec_() != QDialog.Accepted:
                return
            sublayer = dlg.selected

        layer, error = load_vector_layer(path, sublayer)
        if layer is None:
            QMessageBox.critical(self, tr("字段映射复制"), error)
            return

        add_layer_to_project(layer)
        self.refresh_layers()
        idx = self.source_combo.findData(layer.id())
        if idx >= 0:
            self.source_combo.setCurrentIndex(idx)
        QMessageBox.information(self, tr("字段映射复制"), tr("已加载图层：{}").format(layer.name()))

    def _run_transfer(self):
        self._persist_config(silent=True)

        source_layer = self._current_layer(self.source_combo)
        target_layer = self._current_layer(self.target_combo)

        if source_layer is None or target_layer is None:
            QMessageBox.warning(self, tr("字段映射复制"), tr("请先选择源图层和目标图层。"))
            return
        if source_layer.id() == target_layer.id():
            QMessageBox.warning(self, tr("字段映射复制"), tr("源图层与目标图层不能相同。"))
            return

        if not geometry_types_compatible(source_layer, target_layer):
            reply = QMessageBox.question(
                self, tr("字段映射复制"), tr("源与目标几何类型不同，仍要继续吗？"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        mapping = self._collect_mapping()
        if not mapping:
            reply = QMessageBox.question(
                self, tr("字段映射复制"), tr("未配置字段映射，将只复制几何。是否继续？"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        result = transfer_features(
            source_layer, target_layer, mapping,
            only_selected=self.only_selected_cb.isChecked(),
            reproject=self.reproject_cb.isChecked(),
        )

        if result["success"]:
            msg = tr("成功复制 {} 条要素到「{}」。").format(result["copied"], target_layer.name())
            if result["skipped"]:
                msg += tr("\n跳过 {} 条。").format(result["skipped"])
            msg += tr("\n\n请记得在目标图层上保存编辑。")
            QMessageBox.information(self, tr("字段映射复制"), msg)
        else:
            QMessageBox.critical(self, tr("字段映射复制"), tr("复制失败：\n") + "\n".join(result["errors"]))

