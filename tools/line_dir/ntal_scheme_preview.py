# -*- coding: utf-8 -*-
from ...i18n import tr
"""方案页右侧：模拟预览 + 实际测试（不写入）。不塞进 ntal_engine。"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QColor
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ntal_code import format_splice_code
from .ntal_scheme import (
    ACTION_KEYS,
    ACTION_TITLES,
    resolve_action_scheme,
)

_LIVE_ATTRS = (
    "tolerance",
    "clockwise",
    "start_angle",
    "prefix_box",
    "prefix_cable",
    "prefix_splice",
    "accumulate",
    "scheme_id",
    "action_schemes",
    "city_code",
    "pm_code",
)


def snapshot_host(host):
    return {key: getattr(host, key, None) for key in _LIVE_ATTRS}


def restore_host(host, old):
    for key, value in (old or {}).items():
        setattr(host, key, value)


def apply_dialog_to_host(host, dlg):
    host.tolerance = dlg.tolerance()
    host.clockwise = dlg.clockwise()
    host.start_angle = dlg.start_angle()
    host.prefix_box = dlg.prefix_box()
    host.prefix_cable = dlg.prefix_cable()
    host.prefix_splice = dlg.prefix_splice()
    host.action_schemes = dlg.action_schemes()
    host.scheme_id = dlg.scheme_id()
    host.accumulate = dlg.accumulate()
    if hasattr(host, "edit_city"):
        host.city_code = (host.edit_city.text() or "").strip()
        host.pm_code = (host.edit_pm.text() or "").strip()


def _code(prefix, city, pm, odf, link, box):
    return format_splice_code(prefix, city or "城市", pm or "PM", odf, link, box, width=2)


def build_sim_rows(action, scheme_id, prefix_splice="BPE", prefix_box="PBO", prefix_cable="CDI", city="", pm=""):
    """固定示意网：光交O，短干90°→A→B，A 分叉到 C（户数少），长干180°→D。"""
    spec = resolve_action_scheme(action, scheme_id)
    sid = spec["id"]
    city = city or "城市"
    pm = pm or "PM"
    splice = prefix_splice or "BPE"
    box = prefix_box or "PBO"
    cable = prefix_cable or "CDI"
    if action == "drop":
        return _sim_drop(sid)
    if action == "fat":
        return _sim_fat(sid)
    if action == "line":
        return _sim_line(sid)
    if action == "splice_code":
        return _sim_splice(sid, splice, city, pm)
    if action == "fat_code":
        return _sim_fat_code(sid, box, city, pm)
    if action == "cable_code":
        return _sim_cable(sid, splice, box, cable, city, pm)
    return []


def _sim_drop(sid):
    if sid == "write_one":
        return [
            ("单盒用户甲（户数 8）", "皮线甲", "1", "不读户数，合格皮线写 1"),
            ("双盒用户乙（户数 4）", "皮线乙1 / 乙2", "不写", "多盒覆盖仍跳过"),
            ("没挂上的皮线", "皮线丙", "保持原值", "两端没吸到盒+用户"),
        ]
    if sid == "allow_multi":
        return [
            ("单盒用户甲（户数 8）", "皮线甲", "8", "抄用户户数"),
            ("双盒用户乙（户数 4）", "皮线乙1", "4", "多盒也写，各写一遍 4"),
            ("双盒用户乙（户数 4）", "皮线乙2", "4", "两条都写，不是对半拆"),
            ("同盒重复皮线", "皮线丁", "不写", "同一盒到同一用户多于 1 条仍不写"),
        ]
    return [
        ("单盒用户甲（户数 8）", "皮线甲", "8", "抄用户户数"),
        ("双盒用户乙（户数 4）", "皮线乙1 / 乙2", "不写", "一个用户接多个盒，该皮线不写"),
        ("没挂上的皮线", "皮线丙", "保持原值", "不改成 0"),
    ]


def _sim_fat(sid):
    if sid == "count_drops":
        return [
            ("盒1 出 2 条皮线（8+4）", "分纤盒1", "2", "写条数，不加户数"),
            ("用户合计 ≠ 皮线合计", "整批", "不写", "仍先核对两个总户数"),
        ]
    if sid == "no_total_check":
        return [
            ("盒1 出皮线 8+4", "分纤盒1", "12", "仍按皮线户数加总"),
            ("用户合计 ≠ 皮线合计", "整批", "照写，只软错误", "对不上不挡写入"),
        ]
    return [
        ("盒1 出皮线 8+4", "分纤盒1", "12", "所出皮线户数之和"),
        ("用户合计 ≠ 皮线合计", "整批", "不写", "先检查皮线值"),
        ("没有所出皮线", "分纤盒2", "0", "写 0 允许"),
    ]


def _sim_line(sid):
    if sid == "legacy_hh":
        return [
            ("光交→接头A", "主干", "20", "下游盒1(8)+盒2(12) 累加，主干也写"),
            ("接头A→盒1→盒2 第一段", "配线1", "20", "8+12"),
            ("盒1→盒2 第二段", "配线2", "12", "只到盒2"),
        ]
    if sid == "dist_sum":
        return [
            ("光交→接头A", "主干", "不写", "配线累加，主干仍空着"),
            ("接头A→盒1→盒2 第一段", "配线1", "20", "8+12"),
            ("盒1→盒2 第二段", "配线2", "12", "只到盒2"),
        ]
    return [
        ("光交→接头A", "主干", "不写", "主干不写户数"),
        ("接头A→盒1→盒2 第一段", "配线1", "8", "只写到达的盒1，不加盒2"),
        ("盒1→盒2 第二段", "配线2", "12", "只写到达的盒2"),
    ]


def _sim_splice(sid, prefix, city, pm):
    a = _code(prefix, city, pm, 1, 1, 1)
    if sid == "linear":
        return [
            ("短干 90°（ODF01）", "接头A", a, "第一个接头固定 01-01"),
            ("A 后主支（户数多）", "接头B", _code(prefix, city, pm, 1, 1, 2), "第五段一直 01"),
            ("A 分叉（户数少）", "接头C", _code(prefix, city, pm, 1, 1, 3), "分叉也接着编，不新开第五段"),
            ("长干 180°（ODF02）", "接头D", _code(prefix, city, pm, 2, 1, 1), "另一条出线自己的第四段"),
        ]
    if sid == "new_link":
        return [
            ("短干 90°（ODF01）", "接头A", a, "第一个 01-01"),
            ("A 后主支（户数多）", "接头B", _code(prefix, city, pm, 1, 2, 1), "每到一个接头新开第五段"),
            ("A 分叉（户数少）", "接头C", _code(prefix, city, pm, 1, 3, 1), "第六段固定 01"),
            ("长干 180°（ODF02）", "接头D", _code(prefix, city, pm, 2, 1, 1), "另一条出线从 01-01"),
        ]
    if sid == "odf_angle":
        return [
            ("长干 180° 更接近起始角 100°", "接头D", a, "第四段先比出线角度"),
            ("短干 90° 排第二", "接头A", _code(prefix, city, pm, 2, 1, 1), "角度定完再比主干长短"),
            ("A 后主支（户数多）", "接头B", _code(prefix, city, pm, 2, 1, 2), "后两段仍按分叉另开第五段"),
            ("A 分叉（户数少）", "接头C", _code(prefix, city, pm, 2, 2, 3), "户数少的新开第五段"),
        ]
    return [
        ("短干 90° 更短，ODF01", "接头A", a, "第四段按第一段主干长短，短的号小"),
        ("A 后主支（户数多）", "接头B", _code(prefix, city, pm, 1, 1, 2), "户数多的接着当前第五段"),
        ("A 分叉（户数少）", "接头C", _code(prefix, city, pm, 1, 2, 3), "新开第五段，第六段接最大号后面"),
        ("长干 180°（ODF02）", "接头D", _code(prefix, city, pm, 2, 1, 1), "另一条出线从 01-01"),
    ]


def _sim_fat_code(sid, prefix, city, pm):
    if sid == "share_5th":
        return [
            ("接头A 是 01-01，下挂盒甲（户数多）", "分纤盒甲", _code(prefix, city, pm, 1, 1, 1), "第五段跟所接接头相同"),
            ("同一接头下另一条配线 盒乙", "分纤盒乙", _code(prefix, city, pm, 1, 1, 2), "第六段接着编，不每条链从 01 起"),
        ]
    if sid == "per_splice":
        return [
            ("接头A 下 盒甲（户数多）", "分纤盒甲", _code(prefix, city, pm, 1, 1, 1), "每个接头自己的配线从 01 起"),
            ("接头B 下 盒丙", "分纤盒丙", _code(prefix, city, pm, 1, 1, 1), "不看同 ODF 其它接头用到几"),
        ]
    if sid == "continue_6th":
        return [
            ("接头第五段最大 02，户数多的链", "分纤盒甲", _code(prefix, city, pm, 1, 3, 1), "第五段从 03 起"),
            ("同链第二个盒", "分纤盒乙", _code(prefix, city, pm, 1, 3, 2), "同链接着 02"),
            ("下一条配线", "分纤盒丙", _code(prefix, city, pm, 1, 4, 3), "第六段整条 ODF 连续，不按链归零"),
        ]
    return [
        ("接头第五段最大 02，户数多的链", "分纤盒甲", _code(prefix, city, pm, 1, 3, 1), "第五段从接头最大 +1 起"),
        ("同链离接头近的是 01", "分纤盒乙", _code(prefix, city, pm, 1, 3, 2), "每条链第六段从 01 起"),
        ("户数少的另一条配线", "分纤盒丙", _code(prefix, city, pm, 1, 4, 1), "不跟接头共用第五段"),
    ]


def _sim_cable(sid, splice, box, cable, city, pm):
    dest_a = _code(splice, city, pm, 1, 1, 1)
    dest_fat = _code(box, city, pm, 1, 3, 1)
    if sid == "from_upstream":
        return [
            ("光交→接头A", "主干", _code(cable, city, pm, 1, 1, 1), "光交没有 CODE，第一段仍抄到达接头"),
            ("接头A→接头B", "主干", _code(cable, city, pm, 1, 1, 1), "抄离开的接头A，不是到达的 B"),
            ("接头A→分纤盒甲", "配线", _code(cable, city, pm, 1, 1, 1), "抄离开的接头A"),
        ]
    if sid == "keep_dest":
        return [
            ("光交→接头A", "主干", dest_a, "到达接头 CODE 原样写入，不换光缆前缀"),
            ("接头A→分纤盒甲", "配线", dest_fat, "到达分纤盒 CODE 原样写入"),
        ]
    if sid == "last3":
        return [
            ("到达接头后三段 01-01-01", "主干", _code(cable, city, pm, 1, 1, 1), "只抄后三段，前缀/城市/PM 用光缆和主窗口"),
            ("到达盒后三段 01-03-01", "配线", _code(cable, city, pm, 1, 3, 1), "不检查到达对象自己的城市/PM"),
        ]
    return [
        ("光交→接头A", "主干", _code(cable, city, pm, 1, 1, 1), "抄到达接头，换光缆前缀"),
        ("接头A→分纤盒甲", "配线", _code(cable, city, pm, 1, 3, 1), "抄到达分纤盒，换光缆前缀"),
    ]


def _qt_enum(owner, *names):
    for name in names:
        cur = owner
        ok = True
        for part in name.split("."):
            if not hasattr(cur, part):
                ok = False
                break
            cur = getattr(cur, part)
        if ok:
            return cur
    return 0


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels([tr(text) for text in headers])
    table.setEditTriggers(_qt_enum(QAbstractItemView, "EditTrigger.NoEditTriggers", "NoEditTriggers"))
    table.setSelectionMode(_qt_enum(QAbstractItemView, "SelectionMode.NoSelection", "NoSelection"))
    table.setFocusPolicy(_qt_enum(Qt, "FocusPolicy.NoFocus", "NoFocus"))
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    try:
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    except AttributeError:
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
    table.verticalHeader().setDefaultSectionSize(22)
    return table


# 与主窗口 TIP_TARGET_STYLE 同一套：写入终点加粗橙色
_TARGET_COLOR = QColor("#c05600")


def _fill(table, rows, value_col=2):
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            item = QTableWidgetItem(str(text))
            if j == value_col and str(text).strip():
                item.setForeground(QBrush(_TARGET_COLOR))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            table.setItem(i, j, item)
    table.resizeColumnsToContents()


class SchemePreviewPane(QWidget):
    def __init__(self, dialog, parent=None):
        super(SchemePreviewPane, self).__init__(parent)
        self._dialog = dialog
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 0, 0, 0)
        title = QLabel(tr("看懂当前选项"))
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        self.combo_focus = QComboBox()
        for key in ACTION_KEYS:
            self.combo_focus.addItem(tr(ACTION_TITLES[key]), key)
        self.combo_focus.currentIndexChanged.connect(self.refresh_sim)
        root.addWidget(self.combo_focus)
        self.lbl_scheme = QLabel("")
        self.lbl_scheme.setWordWrap(True)
        self.lbl_scheme.setStyleSheet("color: #1b5e20; font-weight: 700;")
        root.addWidget(self.lbl_scheme)
        self.lbl_tip = QLabel("")
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet("color: #555;")
        root.addWidget(self.lbl_tip)
        sim_lab = QLabel(tr("模拟预览（固定示意网，不读图层）"))
        sim_lab.setStyleSheet("font-weight: 700;")
        root.addWidget(sim_lab)
        self.sim_table = _table(("场景", "对象", "将写成", "说明"))
        self.sim_table.setMinimumHeight(140)
        root.addWidget(self.sim_table, 3)
        test_lab = QLabel(tr("实际测试（读当前图层，不写入）"))
        test_lab.setStyleSheet("font-weight: 700;")
        root.addWidget(test_lab)
        btn_row = QHBoxLayout()
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 200)
        self.spin_limit.setValue(20)
        self.spin_limit.setPrefix(tr("最多 "))
        self.spin_limit.setSuffix(tr(" 条"))
        self.btn_test = QPushButton(tr("运行测试"))
        self.btn_audit = QPushButton(tr("全面检测"))
        self.btn_test.setToolTip(tr("按左边当前方案和上面选的功能，对图层跑一遍分析。只出表，不写字段、不出临时图层。"))
        self.btn_audit.setToolTip(
            tr("用本窗里还没确定的容差、角度、六个方案做全面检测。只出表，不写字段、不翻线、不出图层。")
        )
        self.btn_test.clicked.connect(self.run_live_test)
        self.btn_audit.clicked.connect(self.run_live_audit)
        btn_row.addWidget(self.btn_test)
        btn_row.addWidget(self.btn_audit)
        btn_row.addWidget(self.spin_limit)
        btn_row.addStretch(1)
        root.addLayout(btn_row)
        self.test_table = _table(("对象", "原值", "将写成", "备注"))
        self.test_table.setMinimumHeight(140)
        root.addWidget(self.test_table, 3)
        self.lbl_status = QLabel(tr("换下拉会立刻改模拟预览。测试和全面检测用本窗当前参数，点取消不会保存。"))
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #555;")
        root.addWidget(self.lbl_status)

    def focus_action(self, action):
        idx = self.combo_focus.findData(action)
        if idx >= 0 and idx != self.combo_focus.currentIndex():
            self.combo_focus.blockSignals(True)
            self.combo_focus.setCurrentIndex(idx)
            self.combo_focus.blockSignals(False)
        self.refresh_sim()

    def current_action(self):
        return self.combo_focus.currentData() or "splice_code"

    def _city_pm(self):
        host = self._dialog.parent() if self._dialog is not None else None
        city = ""
        pm = ""
        if host is not None:
            if hasattr(host, "edit_city"):
                city = (host.edit_city.text() or "").strip()
            if hasattr(host, "edit_pm"):
                pm = (host.edit_pm.text() or "").strip()
        return city, pm

    def refresh_sim(self):
        dlg = self._dialog
        action = self.current_action()
        sid = (dlg.action_schemes() or {}).get(action) or "current"
        spec = resolve_action_scheme(action, sid)
        self.lbl_scheme.setText(spec.get("label") or sid)
        self.lbl_tip.setText(spec.get("tip") or "")
        city, pm = self._city_pm()
        rows = build_sim_rows(
            action,
            sid,
            prefix_splice=dlg.prefix_splice(),
            prefix_box=dlg.prefix_box(),
            prefix_cable=dlg.prefix_cable(),
            city=city,
            pm=pm,
        )
        _fill(self.sim_table, rows)

    def run_live_test(self):
        host = self._dialog.parent() if self._dialog is not None else None
        if host is None or not hasattr(host, "_action_runner"):
            self.lbl_status.setText(tr("没有主窗口，跑不了实际测试。"))
            return
        action = self.current_action()
        runner, payload_fn, noun, _cmd = host._action_runner(action)
        old = snapshot_host(host)
        QApplication.setOverrideCursor(_qt_enum(Qt, "CursorShape.WaitCursor", "WaitCursor"))
        try:
            apply_dialog_to_host(host, self._dialog)
            QApplication.processEvents()
            result = runner(**payload_fn())
        except Exception as exc:
            result = {"ok": False, "config_errors": [str(exc)]}
        finally:
            restore_host(host, old)
            QApplication.restoreOverrideCursor()
        self._show_action_result(result, noun)

    def run_live_audit(self):
        host = self._dialog.parent() if self._dialog is not None else None
        if host is None:
            self.lbl_status.setText(tr("没有主窗口，跑不了全面检测。"))
            return
        from .ntal_audit import CHECKS, CHECKS_OFF_BY_DEFAULT, run_audit

        selected = set(key for key, _level, _text in CHECKS if key not in CHECKS_OFF_BY_DEFAULT)
        old = snapshot_host(host)
        QApplication.setOverrideCursor(_qt_enum(Qt, "CursorShape.WaitCursor", "WaitCursor"))
        try:
            apply_dialog_to_host(host, self._dialog)
            QApplication.processEvents()
            result = run_audit(host, selected, progress=None)
        except Exception as exc:
            result = {"ok": False, "config_errors": [str(exc)]}
        finally:
            restore_host(host, old)
            QApplication.restoreOverrideCursor()
        self._show_audit_result(result)

    def _show_action_result(self, result, noun):
        if not result.get("ok"):
            errs = result.get("config_errors") or ["配置不完整"]
            _fill(self.test_table, [(line, "", "", "配置") for line in errs])
            self.lbl_status.setText("测试没跑成：{}".format("；".join(errs)))
            return
        writes = list(result.get("writes") or [])
        from .ntal_engine import split_issue_levels
        hard, soft, warn = split_issue_levels(result)
        limit = int(self.spin_limit.value())
        rows = []
        for row in writes[:limit]:
            rows.append((
                row.get("label") or "",
                "" if row.get("old") is None else row.get("old"),
                "" if row.get("value") is None else row.get("value"),
                "",
            ))
        extra = max(0, len(writes) - limit)
        if extra:
            rows.append(("……还有 {} 条".format(extra), "", "", "把上面数字调大"))
        if not rows:
            rows.append(("（没有将写入的要素）", "", "", result.get("scheme_label") or ""))
        _fill(self.test_table, rows)
        self.lbl_status.setText(
            "本功能方案：{}。将写入 {} {}，硬错误 {}，软错误 {}，警告 {}。没有写入，也没有出临时图层。".format(
                result.get("scheme_label") or "",
                len(writes),
                noun,
                len(hard),
                len(soft),
                len(warn),
            )
        )

    def _show_audit_result(self, result):
        if not result.get("ok"):
            errs = result.get("config_errors") or ["配置不完整"]
            _fill(self.test_table, [(line, "", "", "配置") for line in errs])
            self.lbl_status.setText("全面检测没跑成：{}".format("；".join(errs)))
            return
        from .ntal_engine import split_issue_levels
        hard, soft, warn = split_issue_levels(result)
        notes = result.get("notes") or []
        limit = int(self.spin_limit.value())
        rows = []
        leftover_src = []
        for item in hard:
            leftover_src.append((item.get("message") or "", "", "", "硬错误"))
        for item in soft:
            leftover_src.append((item.get("message") or "", "", "", "软错误"))
        for item in warn:
            leftover_src.append((item.get("message") or "", "", "", "警告"))
        rows.extend(leftover_src[:limit])
        leftover = len(leftover_src) - len(rows)
        if leftover > 0:
            rows.append(("……还有 {} 条".format(leftover), "", "", "把上面数字调大"))
        for note in notes[:3]:
            rows.append((note, "", "", "说明"))
        if not rows:
            rows.append(("勾选的类里没有发现问题。", "", "", "全面检测"))
        _fill(self.test_table, rows)
        self.lbl_status.setText(
            "按本窗当前容差 / 角度 / 六个方案检测。硬错误 {}，软错误 {}，警告 {}。没有写入，没有翻转，没有出图层。".format(
                len(hard), len(soft), len(warn)
            )
        )
