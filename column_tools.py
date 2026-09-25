# -*- coding: utf-8 -*-
"""Per-column helpers: value grouping, unique-value stats dialog, row-range parsing."""

import re

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from qgis.core import NULL

from .model import try_parse_number
from .value_map import value_key
from .value_utils import value_text

BLANK_KEY = ("blank", "")


def is_blank_value(raw):
    if raw is None or raw == NULL:
        return True
    return isinstance(raw, str) and raw.strip() == ""


def group_column(fids, values):
    """key -> [sample raw value, [fids]] in first-seen order; blanks share BLANK_KEY."""
    groups = {}
    for fid, raw in zip(fids, values):
        key = BLANK_KEY if is_blank_value(raw) else value_key(raw)
        slot = groups.get(key)
        if slot is None:
            groups[key] = [raw, [fid]]
        else:
            slot[1].append(fid)
    return groups


def parse_row_ranges(text, row_count):
    """'10-50, 80, 100~' -> sorted 0-based rows. Raises ValueError on bad input."""
    rows = set()
    parts = [p.strip() for p in re.split(r"[,，;；\s]+", text or "") if p.strip()]
    if not parts:
        raise ValueError("请输入行号，例如 10-50 或 1-20,35")
    for part in parts:
        m = re.fullmatch(r"(\d*)\s*[-~–—至到]\s*(\d*)", part)
        if m:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else row_count
        elif part.isdigit():
            a = b = int(part)
        else:
            raise ValueError("看不懂「%s」，请写成 10-50 这样的形式" % part)
        if a > b:
            a, b = b, a
        a = max(a, 1)
        b = min(b, row_count)
        if a <= b:
            rows.update(range(a - 1, b))
    if not rows:
        raise ValueError("行号超出范围（当前共 %d 行）" % row_count)
    return sorted(rows)


class _SortItem(QTableWidgetItem):
    """Sorts by a hidden key instead of display text."""

    def __init__(self, text, sort_key):
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other):
        other_key = getattr(other, "_sort_key", None)
        if other_key is None:
            return super().__lt__(other)
        try:
            return self._sort_key < other_key
        except TypeError:
            return str(self._sort_key) < str(other_key)


class UniqueValuesDialog(QDialog):
    """Value | meaning | count | share for one column of the current table rows."""

    COL_VALUE, COL_LABEL, COL_COUNT, COL_SHARE = range(4)

    def __init__(self, parent, field_title, groups, label_for, on_filter, on_select):
        super().__init__(parent)
        self.setWindowTitle("唯一值统计 - %s" % field_title)
        self.resize(560, 520)
        self._groups = groups
        self._on_filter = on_filter
        self._on_select = on_select
        self._keys = []

        total = sum(len(slot[1]) for slot in groups.values())
        lay = QVBoxLayout(self)
        info = QLabel(
            "范围：当前表格里的 %d 行（受范围/过滤/筛选影响），共 %d 个不同值。"
            "勾选后可筛选或选中。" % (total, len(groups))
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        self.ed_find = QLineEdit()
        self.ed_find.setPlaceholderText("在列表里查找…")
        self.ed_find.setClearButtonEnabled(True)
        self.ed_find.textChanged.connect(self._apply_find)
        lay.addWidget(self.ed_find)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["值", "含义", "条数", "占比"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.COL_VALUE, QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_LABEL, QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_COUNT, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_SHARE, QHeaderView.ResizeToContents)
        lay.addWidget(self.table, 1)

        self.table.setRowCount(len(groups))
        for row, (key, (raw, fids)) in enumerate(groups.items()):
            self._keys.append(key)
            count = len(fids)
            if key == BLANK_KEY:
                text, label, sort_val = "(空)", "", (0, 0.0, "")
            else:
                text = value_text(raw)
                label = label_for(raw) or ""
                if label == text:
                    label = ""
                num = try_parse_number(raw)
                sort_val = (1, float(num), "") if num is not None else (2, 0.0, text.casefold())
            it_value = _SortItem(text, sort_val)
            it_value.setFlags(it_value.flags() | Qt.ItemIsUserCheckable)
            it_value.setCheckState(Qt.Unchecked)
            it_value.setData(Qt.UserRole, row)
            self.table.setItem(row, self.COL_VALUE, it_value)
            self.table.setItem(row, self.COL_LABEL, _SortItem(label, label.casefold()))
            it_count = _SortItem(str(count), count)
            it_count.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_COUNT, it_count)
            share = (100.0 * count / total) if total else 0.0
            it_share = _SortItem("%.1f%%" % share, share)
            it_share.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_SHARE, it_share)
        self.table.setSortingEnabled(True)
        self.table.sortItems(self.COL_COUNT, Qt.DescendingOrder)

        pick = QHBoxLayout()
        btn_all = QPushButton("全勾")
        btn_none = QPushButton("全不勾")
        btn_dup = QPushButton("勾重复值")
        btn_dup.setToolTip("勾选出现 2 次及以上的非空值")
        btn_all.clicked.connect(lambda: self._check_where(lambda _k, _n: True))
        btn_none.clicked.connect(lambda: self._check_where(lambda _k, _n: False))
        btn_dup.clicked.connect(
            lambda: self._check_where(lambda k, n: k != BLANK_KEY and n > 1)
        )
        for b in (btn_all, btn_none, btn_dup):
            pick.addWidget(b)
        pick.addStretch(1)
        lay.addLayout(pick)

        acts = QHBoxLayout()
        btn_filter = QPushButton("按勾选筛选")
        btn_filter.setToolTip("把勾选的值填到顶栏「筛选」（字段取值模式）")
        btn_select = QPushButton("选中勾选要素")
        btn_select.setToolTip("在图层上选中勾选值对应的要素（替换当前选择）")
        btn_copy = QPushButton("复制列表")
        btn_close = QPushButton("关闭")
        btn_filter.clicked.connect(self._do_filter)
        btn_select.clicked.connect(self._do_select)
        btn_copy.clicked.connect(self._copy_table)
        btn_close.clicked.connect(self.close)
        for b in (btn_filter, btn_select, btn_copy):
            acts.addWidget(b)
        acts.addStretch(1)
        acts.addWidget(btn_close)
        lay.addLayout(acts)

    def _group_at(self, table_row):
        item = self.table.item(table_row, self.COL_VALUE)
        if item is None:
            return None, None
        key = self._keys[item.data(Qt.UserRole)]
        return key, self._groups[key]

    def _check_where(self, pred):
        for r in range(self.table.rowCount()):
            if self.table.isRowHidden(r):
                continue
            key, slot = self._group_at(r)
            if key is None:
                continue
            state = Qt.Checked if pred(key, len(slot[1])) else Qt.Unchecked
            self.table.item(r, self.COL_VALUE).setCheckState(state)

    def _apply_find(self, text):
        needle = (text or "").strip().casefold()
        for r in range(self.table.rowCount()):
            if not needle:
                self.table.setRowHidden(r, False)
                continue
            hay = " ".join(
                (self.table.item(r, c).text() if self.table.item(r, c) else "")
                for c in (self.COL_VALUE, self.COL_LABEL)
            ).casefold()
            self.table.setRowHidden(r, needle not in hay)

    def _checked(self):
        out = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, self.COL_VALUE)
            if item is not None and item.checkState() == Qt.Checked:
                key, slot = self._group_at(r)
                if key is not None:
                    out.append((key, slot))
        return out

    def _do_filter(self):
        checked = self._checked()
        if not checked:
            return
        self._on_filter(checked)

    def _do_select(self):
        checked = self._checked()
        if not checked:
            return
        fids = []
        for _key, (_raw, group_fids) in checked:
            fids.extend(group_fids)
        self._on_select(fids, len(checked))

    def _copy_table(self):
        lines = ["值\t含义\t条数\t占比"]
        for r in range(self.table.rowCount()):
            if self.table.isRowHidden(r):
                continue
            cells = [
                (self.table.item(r, c).text() if self.table.item(r, c) else "")
                for c in range(4)
            ]
            lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))
