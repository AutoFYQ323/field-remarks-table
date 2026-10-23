# -*- coding: utf-8 -*-
from ...i18n import tr
"""全面检测。只读图层配置，不改赋值和命名的写入规则。"""
import math
from collections import defaultdict

from qgis.core import QgsRectangle

from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
)

from .layer_groups import resolve_group
from .ntal_engine import (
    AUDIT_GROUP_NAME,
    _build_index,
    _snap_end,
    add_issue_temp_layers,
    collect_lines,
    collect_points,
    parse_hh,
    working_crs_from_layers,
)
from .ntal_graph import (
    ROLE_CABLE,
    ROLE_DROP,
    ROLE_FAT,
    ROLE_OCC,
    ROLE_SPLICE,
    ROLE_USER,
    analyze_graph,
)
from . import ntal_line_dir as line_dir_mod
from .layer_picker import attr_key
from .ntal_line_dir import LineDirDialog, _CheckProgress, _feat_total, _make_tick, run_line_dir_analysis
from .ntal_roles import classify_cable_pair, classify_drop_pair
from .ntal_scheme import (
    format_action_scheme_lines,
    host_action_schemes,
    host_scheme,
    household_of,
    result_meta,
)

CHECKS = (
    ("snap", "硬错误", "端点分不清：容差内同时靠近多个点，或一根线两头吸到同一个点"),
    ("cable_end", "硬错误", "光缆一端空，或两头角色不对（光交只能对接头，接头可接接头或分纤盒）。两端都空单独算软错误"),
    ("occ", "硬错误", "光交没有往外的光缆，或有光缆把光交当成下游"),
    ("splice", "硬错误", "接头从光交方向进来的光缆不是恰好 1 条（0 条或多于 1 条）。出去几条不限"),
    ("fat", "硬错误", "分纤盒从光交方向进来的光缆不是恰好 1 条，或出去超过 1 条。不出去是允许的，分纤盒可以再串分纤盒"),
    ("cycle", "硬错误", "从光交往外走时绕回去，网络成环"),
    ("cable_lost", "硬错误", "光缆两头角色是对的，但这根线从任何一个光交都走不到"),
    ("drop_end", "硬错误", "皮线两头必须是分纤盒和用户点。一端空、两头都是盒或都是用户、接到光交或接头。两端都空单独算软错误"),
    ("drop_over", "硬错误", "同一个分纤盒到同一个用户点只允许 1 条皮线。一个分纤盒接不同用户点允许"),
    ("user_drop", "硬错误", "用户点至少要有 1 条合格皮线接到分纤盒"),
    ("direction", "软错误", "线已经能从光交走到下游，但数字化起点不在上游。可在结果窗里翻转"),
    ("near", "软错误", "光交/接头/分纤盒之间相距不到吸附容差；线端点容差内有多个点（已按最近的接上，请人工复核）"),
    ("code", "软错误", "接头、分纤盒、光缆的 CODE 字段有重复值或空值（命名前可不勾）"),
    ("user_multi", "警告", "同一个用户点接到 2 个及以上分纤盒。允许，但请确认。出图层"),
    ("fat_drop", "警告", "分纤盒没有接到用户的合格皮线（后面赋户数会是 0）"),
    ("splice_out", "警告", "接头后面没有配线（这一支没有分纤盒）"),
)
CHECKS_OFF_BY_DEFAULT = {"code"}

_DIR_DLG = None


def _issue(kind, message, refs):
    return {"kind": kind, "message": message, "refs": list(refs or [])}


def _want(selected, key):
    return key in selected


class AuditPickDialog(QDialog):
    def __init__(self, parent=None):
        super(AuditPickDialog, self).__init__(parent)
        self.setWindowTitle(tr("选择要检查的网络问题"))
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        hint = QLabel(
            tr('按下面每一类单独勾选。默认全部检查。反选会把当前勾选反过来。检测完会留下结果窗：硬错误、软错误、警告写在「检查」页，方向反了的线在「可修复」页，可以翻转。地图图层在「全面检测」组里，硬错误、软错误、警告分开。')
        )
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.boxes = []
        for key, level, text in CHECKS:
            box = QCheckBox("{}　{}".format(tr(level), tr(text)))
            box.setChecked(key not in CHECKS_OFF_BY_DEFAULT)
            box.setProperty("check_id", key)
            self.boxes.append(box)
            root.addWidget(box)
        row = QHBoxLayout()
        btn_all = QPushButton(tr("全选"))
        btn_inv = QPushButton(tr("反选"))
        btn_all.clicked.connect(self._select_all)
        btn_inv.clicked.connect(self._invert)
        row.addWidget(btn_all)
        row.addWidget(btn_inv)
        row.addStretch(1)
        root.addLayout(row)
        buttons = QDialogButtonBox()
        buttons.addButton(tr("开始检测"), QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(tr("取消"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _select_all(self):
        for box in self.boxes:
            box.setChecked(True)

    def _invert(self):
        for box in self.boxes:
            box.setChecked(not box.isChecked())

    def selected(self):
        picked = set()
        for box in self.boxes:
            if box.isChecked():
                picked.add(box.property("check_id"))
        return picked


def _near_nodes(xy, index, by_int, tolerance):
    if xy is None:
        return []
    x, y = xy
    rect = QgsRectangle(x - tolerance, y - tolerance, x + tolerance, y + tolerance)
    hits = []
    for nid in index.intersects(rect):
        node = by_int.get(nid)
        if node is None:
            continue
        if math.hypot(x - node["xy"][0], y - node["xy"][1]) <= tolerance:
            hits.append(node["id"])
    return hits


def _snap_edges(edges, index, by_int, node_map, tolerance, hard, check_snap):
    for edge in edges:
        a, amb_a = _snap_end(edge.get("start"), index, by_int, tolerance)
        b, amb_b = _snap_end(edge.get("end"), index, by_int, tolerance)
        edge["a"] = a
        edge["b"] = b
        edge["amb"] = bool(amb_a or amb_b)
        if not check_snap:
            continue
        for amb, side in ((amb_a, "起点"), (amb_b, "终点")):
            if not amb:
                continue
            hard.append(_issue(
                "snap_ambig",
                "{}同时靠近多个点：{}".format(side, edge.get("label") or ""),
                [("edge", edge["id"])] + [("node", nid) for nid in amb],
            ))
        if a and a == b:
            hard.append(_issue(
                "self_loop",
                "线两端接到同一点：{}".format(edge.get("label") or ""),
                [("edge", edge["id"]), ("node", a)],
            ))


def _role(node_map, nid):
    if not nid:
        return None
    return (node_map.get(nid) or {}).get("role")


def run_audit(host, selected, progress=None):
    occ_layers, occ_filters, _ = resolve_group(host.layers.get("occ"))
    splice_layers, splice_filters, splice_code_field = resolve_group(host.layers.get("splice"))
    fat_layers, fat_filters, fat_hh_field = resolve_group(host.layers.get("fat"))
    user_layers, user_filters, user_hh_field = resolve_group(host.layers.get("user"))
    cable_layers, cable_filters, _ = resolve_group(host.layers.get("cable"))
    drop_layers, drop_filters, drop_hh_field = resolve_group(host.layers.get("drop"))
    fat_code_field = ((host.layers.get("fat") or {}).get("code_field") or "").strip()
    cable_code_field = ((host.layers.get("cable") or {}).get("code_field") or "").strip()
    want_code = "code" in selected
    spec = host_scheme(host)
    action_ids = host_action_schemes(host)
    drop_hh_opts = household_of(action="drop", scheme_id=action_ids.get("drop"))
    fat_hh_opts = household_of(action="fat", scheme_id=action_ids.get("fat"))
    drop_multi = drop_hh_opts.get("drop_multi") or "skip"
    fat_check = fat_hh_opts.get("fat_check") or "totals"
    tolerance = float(host.tolerance or 0)
    config_errors = []
    if tolerance <= 0:
        config_errors.append(tr("吸附容差必须大于 0。"))
    need_net = selected - {"direction"}
    if need_net and not (occ_layers or splice_layers or fat_layers or user_layers or cable_layers or drop_layers):
        config_errors.append(tr("请先在图层配置里选择要检测的点线图层。"))
    if "direction" in selected and not occ_layers:
        config_errors.append(tr("线方向从光交往外走，请先配置光交。"))
    if "direction" in selected and not (cable_layers or drop_layers):
        config_errors.append(tr("线方向至少需要光缆或皮线。"))
    if config_errors:
        return {"ok": False, "config_errors": config_errors}

    all_layers = list(occ_layers) + list(splice_layers) + list(fat_layers)
    all_layers += list(user_layers) + list(cable_layers) + list(drop_layers)
    work_crs = working_crs_from_layers(all_layers)
    point_tick = _make_tick(
        progress, 0.02, 0.40,
        _feat_total(list(occ_layers) + list(splice_layers) + list(fat_layers) + list(user_layers)),
        "正在读取点",
    )
    occ_pack = collect_points(occ_layers, occ_filters, ROLE_OCC, work_crs, on_step=point_tick)
    splice_pack = collect_points(
        splice_layers, splice_filters, ROLE_SPLICE, work_crs,
        old_field=splice_code_field if want_code else None, on_step=point_tick,
    )
    fat_pack = collect_points(
        fat_layers, fat_filters, ROLE_FAT, work_crs,
        old_field=fat_code_field if want_code else None, on_step=point_tick,
    )
    user_pack = collect_points(
        user_layers, user_filters, ROLE_USER, work_crs,
        hh_field=user_hh_field or None, on_step=point_tick,
    )
    line_tick = _make_tick(
        progress, 0.42, 0.30,
        _feat_total(list(cable_layers) + list(drop_layers)),
        "正在读取线",
    )
    cable_pack = collect_lines(
        cable_layers, cable_filters, ROLE_CABLE, work_crs,
        cable_code_field if want_code else "", on_step=line_tick,
    )
    drop_pack = collect_lines(
        drop_layers, drop_filters, ROLE_DROP, work_crs,
        drop_hh_field or "", on_step=line_tick,
    )
    occ_rows, splice_rows, fat_rows, user_rows = occ_pack[0], splice_pack[0], fat_pack[0], user_pack[0]
    cable_rows, drop_rows = cable_pack[0], drop_pack[0]
    if progress is not None:
        progress.report(0.74, "正在检查网络结构", force=True)

    node_rows = list(occ_rows) + list(splice_rows) + list(fat_rows) + list(user_rows)
    node_map = {row["id"]: row for row in node_rows}
    edge_map = {row["id"]: row for row in list(cable_rows) + list(drop_rows)}
    index, by_int = _build_index(node_rows)
    hard = []
    soft = []
    warn = []
    check_snap = _want(selected, "snap")
    _snap_edges(cable_rows, index, by_int, node_map, tolerance, hard, check_snap)
    _snap_edges(drop_rows, index, by_int, node_map, tolerance, hard, check_snap)

    trunk_edges = {}
    dist_edges = {}
    if selected & {"cable_end", "occ", "splice", "fat", "cycle", "cable_lost", "splice_out"}:
        for edge in cable_rows:
            if edge.get("a") and edge.get("a") == edge.get("b"):
                continue
            ra = _role(node_map, edge.get("a"))
            rb = _role(node_map, edge.get("b"))
            role, severity, kind, tail = classify_cable_pair(ra, rb, spec)
            refs = [("edge", edge["id"])]
            if edge.get("a"):
                refs.append(("node", edge["a"]))
            if edge.get("b"):
                refs.append(("node", edge["b"]))
            if severity and kind in ("dangling", "both_open") and check_snap and edge.get("amb"):
                severity = None
            if _want(selected, "cable_end") and severity:
                mapped = {
                    "dangling": "cable_dangling",
                    "both_open": "cable_both_open",
                    "bad_role": "cable_bad_role",
                }.get(kind, "cable_bad_role")
                item = _issue(mapped, "{}：{}".format(tail, edge.get("label") or ""), refs)
                if kind == "both_open":
                    soft.append(item)
                else:
                    hard.append(item)
            if role == "trunk" and edge.get("a") and edge.get("b"):
                trunk_edges[edge["id"]] = {"a": edge["a"], "b": edge["b"], "label": edge.get("label")}
            elif role == "dist" and edge.get("a") and edge.get("b"):
                dist_edges[edge["id"]] = {"a": edge["a"], "b": edge["b"], "label": edge.get("label")}

    struct = None
    if selected & {"occ", "splice", "fat", "cycle", "cable_lost", "splice_out"}:
        struct_nodes = {}
        for row in list(occ_rows) + list(splice_rows) + list(fat_rows):
            struct_nodes[row["id"]] = {
                "role": row.get("role"),
                "hh": row.get("hh") or 0,
                "label": row.get("label"),
            }
        struct_edges = {}
        struct_edges.update(trunk_edges)
        struct_edges.update(dist_edges)
        struct = analyze_graph(
            struct_nodes, struct_edges, [row["id"] for row in occ_rows],
            accumulate=False, scheme=spec,
        )
        incoming = struct.get("incoming") or {}
        outgoing = struct.get("outgoing") or {}
        if _want(selected, "cycle"):
            for item in struct.get("hard") or []:
                if item.get("kind") == "cycle":
                    hard.append(item)
        if _want(selected, "occ"):
            for item in list(struct.get("hard") or []) + list(struct.get("warn") or []):
                if item.get("kind") in ("occ_in", "occ_no_out"):
                    hard.append(item)
        if _want(selected, "splice"):
            for item in struct.get("hard") or []:
                if item.get("kind") == "splice_multi_in":
                    hard.append(item)
            for row in splice_rows:
                if len(incoming.get(row["id"]) or []) == 0:
                    hard.append(_issue(
                        "splice_no_in",
                        "接头没有从光交方向来的进线：{}".format(row.get("label") or ""),
                        [("node", row["id"])],
                    ))
        if _want(selected, "fat"):
            for item in struct.get("hard") or []:
                if item.get("kind") in ("fat_multi_in", "fat_branch"):
                    hard.append(item)
            for row in fat_rows:
                if len(incoming.get(row["id"]) or []) == 0:
                    hard.append(_issue(
                        "fat_no_in",
                        "分纤盒没有从光交方向来的光缆：{}".format(row.get("label") or ""),
                        [("node", row["id"])],
                    ))
        if _want(selected, "cable_lost"):
            reached_edges = set((struct.get("oriented") or {}).keys())
            for eid, edge in list(trunk_edges.items()) + list(dist_edges.items()):
                if eid in reached_edges:
                    continue
                hard.append(_issue(
                    "cable_unreached",
                    "未从光交通到：{}".format(edge.get("label") or eid),
                    [("edge", eid), ("node", edge.get("a")), ("node", edge.get("b"))],
                ))
        if _want(selected, "splice_out"):
            has_dist = set()
            for edge in dist_edges.values():
                if _role(node_map, edge.get("a")) == ROLE_SPLICE:
                    has_dist.add(edge["a"])
                if _role(node_map, edge.get("b")) == ROLE_SPLICE:
                    has_dist.add(edge["b"])
            for row in splice_rows:
                if row["id"] in has_dist:
                    continue
                warn.append(_issue(
                    "splice_no_out",
                    "接头后面没有配线：{}".format(row.get("label") or ""),
                    [("node", row["id"])],
                ))
        del outgoing

    if selected & {"drop_end", "drop_over", "user_drop", "user_multi", "fat_drop"}:
        links = []
        for edge in drop_rows:
            if edge.get("a") and edge.get("a") == edge.get("b"):
                continue
            ra = _role(node_map, edge.get("a"))
            rb = _role(node_map, edge.get("b"))
            role, severity, kind, tail = classify_drop_pair(ra, rb, spec)
            if severity and kind in ("dangling", "both_open") and check_snap and edge.get("amb"):
                severity = None
            if severity and _want(selected, "drop_end"):
                mapped = {
                    "dangling": "drop_dangling",
                    "both_open": "drop_both_open",
                    "drop_both_fat": "drop_both_fat",
                    "drop_both_user": "drop_both_user",
                    "bad_role": "drop_bad_role",
                }.get(kind, "drop_bad_role")
                refs = [("edge", edge["id"])]
                if edge.get("a"):
                    refs.append(("node", edge["a"]))
                if edge.get("b"):
                    refs.append(("node", edge["b"]))
                item = _issue(mapped, "{}：{}".format(tail, edge.get("label") or ""), refs)
                if kind == "both_open":
                    soft.append(item)
                else:
                    hard.append(item)
            if role != ROLE_DROP:
                continue
            fat_id = edge["a"] if ra == ROLE_FAT else edge["b"]
            user_id = edge["a"] if ra == ROLE_USER else edge["b"]
            links.append((fat_id, user_id, edge["id"]))
        by_pair = defaultdict(list)
        users_hit = defaultdict(set)
        for fat_id, user_id, eid in links:
            by_pair[(fat_id, user_id)].append(eid)
            users_hit[user_id].add(fat_id)
        if _want(selected, "drop_over"):
            for (fat_id, user_id), eids in by_pair.items():
                if len(eids) <= 1:
                    continue
                fat = node_map.get(fat_id) or {}
                user = node_map.get(user_id) or {}
                hard.append(_issue(
                    "dup_drop",
                    "同一分纤盒到同一用户有 {} 条皮线，只允许 1 条：{} ← {}".format(
                        len(eids), user.get("label") or user_id, fat.get("label") or fat_id
                    ),
                    [("node", user_id), ("node", fat_id)] + [("edge", eid) for eid in eids],
                ))
        if _want(selected, "user_drop"):
            linked = set(users_hit)
            for row in user_rows:
                if row["id"] in linked:
                    continue
                hard.append(_issue(
                    "user_no_drop",
                    "用户点没有合格皮线：{}".format(row.get("label") or ""),
                    [("node", row["id"])],
                ))
        if _want(selected, "user_multi"):
            for user_id, fats in users_hit.items():
                if len(fats) <= 1:
                    continue
                user = node_map.get(user_id) or {}
                fat_names = "、".join(
                    (node_map.get(fid) or {}).get("label") or fid for fid in fats
                )
                extra = ""
                if drop_multi != "write":
                    extra = "。当前赋值·皮线方案不会写这些皮线"
                warn.append(_issue(
                    "multi_fat",
                    "用户接到 {} 个分纤盒：{}（{}）{}".format(
                        len(fats), user.get("label") or user_id, fat_names, extra
                    ),
                    [("node", user_id)] + [("node", fid) for fid in fats],
                ))
        if _want(selected, "fat_drop"):
            fats_hit = set(fat_id for fat_id, _user_id, _eid in links)
            for row in fat_rows:
                if row["id"] in fats_hit:
                    continue
                warn.append(_issue(
                    "fat_no_drop",
                    "分纤盒没有合格皮线：{}".format(row.get("label") or ""),
                    [("node", row["id"])],
                ))
        if fat_check != "none" and user_hh_field and drop_hh_field:
            user_hh_total = sum(float(row.get("hh") or 0.0) for row in user_rows)
            drop_hh_total = sum(parse_hh(row.get("old")) for row in drop_rows)
            if abs(user_hh_total - drop_hh_total) >= 1e-6:
                soft.append(_issue(
                    "hh_mismatch",
                    "用户点总户数 {} 与皮线字段总户数 {} 不一致。当前赋值·分纤盒方案核对总户数，赋值时整批不写。".format(
                        user_hh_total, drop_hh_total
                    ),
                    [],
                ))

    if _want(selected, "near"):
        _check_near(
            list(occ_rows) + list(splice_rows) + list(fat_rows),
            list(cable_rows) + list(drop_rows),
            index, by_int, tolerance, soft,
        )

    notes = [
        "容差 {} 米，{}，起始角 {}°。".format(
            tolerance,
            "顺时针" if getattr(host, "clockwise", False) else "逆时针",
            getattr(host, "start_angle", 100),
        )
    ]
    notes.extend(format_action_scheme_lines(action_ids))
    if want_code:
        for rows, field, title, ref_kind in (
            (splice_rows, splice_code_field, "接头", "node"),
            (fat_rows, fat_code_field, "分纤盒", "node"),
            (cable_rows, cable_code_field, "光缆", "edge"),
        ):
            if not field:
                notes.append("{} CODE 字段没配，跳过 CODE 检查。".format(title))
                continue
            _check_codes(rows, title, ref_kind, soft)

    reversible = []
    if _want(selected, "direction"):
        if progress is not None:
            progress.report(0.85, "正在检查线方向", force=True)
        directed = run_line_dir_analysis(
            occ_layers, splice_layers, fat_layers, user_layers,
            cable_layers, drop_layers,
            occ_filters, splice_filters, fat_filters, user_filters,
            cable_filters, drop_filters,
            tolerance,
            prepared={
                "work_crs": work_crs,
                "occ": occ_pack, "splice": splice_pack, "fat": fat_pack, "user": user_pack,
                "cable": cable_pack, "drop": drop_pack,
            },
            scheme=spec,
        )
        if not directed.get("ok"):
            return directed
        for item in directed.get("warn") or []:
            if item.get("kind") == "line_reversed":
                soft.append(item)
        reversible = list(directed.get("reversible") or [])
        if directed.get("nodes"):
            node_map.update(directed["nodes"])
        if directed.get("edges"):
            edge_map.update(directed["edges"])

    out = {
        "ok": True,
        "kind": "audit",
        "work_crs": work_crs,
        "nodes": node_map,
        "edges": edge_map,
        "hard": hard,
        "soft": soft,
        "warn": warn,
        "tolerance": tolerance,
        "reversible": reversible,
        "source_label": tr("全面检测"),
        "notes": notes,
    }
    out.update(result_meta(spec))
    return out


def _check_near(device_rows, edges, index, by_int, tolerance, warn):
    """设备点相距不到容差；线端点容差内有多个点但已按最近接上（歧义的不在这里重复报）。"""
    device_ids = set(row["id"] for row in device_rows)
    node_map = {node["id"]: node for node in by_int.values()}
    seen_pairs = set()
    for row in device_rows:
        for other in _near_nodes(row["xy"], index, by_int, tolerance):
            if other == row["id"] or other not in device_ids:
                continue
            pair = tuple(sorted((row["id"], other)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            warn.append(_issue(
                "node_overlap",
                "两个设备点相距不到容差 {} 米：{} / {}".format(
                    tolerance, row.get("label") or "", (node_map.get(other) or {}).get("label") or ""
                ),
                [("node", row["id"]), ("node", other)],
            ))
    for edge in edges:
        if edge.get("amb"):
            continue
        for side, xy, bound in (("起点", edge.get("start"), edge.get("a")), ("终点", edge.get("end"), edge.get("b"))):
            if not bound:
                continue
            hits = _near_nodes(xy, index, by_int, tolerance)
            if len(hits) < 2:
                continue
            others = [nid for nid in hits if nid != bound]
            warn.append(_issue(
                "end_near_multi",
                "{}容差内有 {} 个点，已接最近的 {}，请复核：{}".format(
                    side, len(hits), (node_map.get(bound) or {}).get("label") or "", edge.get("label") or ""
                ),
                [("edge", edge["id"]), ("node", bound)] + [("node", nid) for nid in others],
            ))


def _check_codes(rows, title, ref_kind, warn):
    by_code = defaultdict(list)
    for row in rows:
        text = attr_key(row.get("old")).strip()
        if not text:
            warn.append(_issue(
                "code_empty",
                "{} CODE 为空：{}".format(title, row.get("label") or ""),
                [(ref_kind, row["id"])],
            ))
            continue
        by_code[text].append(row)
    for code, items in by_code.items():
        if len(items) <= 1:
            continue
        warn.append(_issue(
            "code_conflict",
            "{} CODE 重复 {}（{} 个）：{}".format(
                title, code, len(items), "、".join(item.get("label") or "" for item in items)
            ),
            [(ref_kind, item["id"]) for item in items],
        ))


def open_audit(host):
    global _DIR_DLG
    dlg = AuditPickDialog(host)
    accepted = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
    if not accepted:
        return
    selected = dlg.selected()
    if not selected:
        QMessageBox.information(host, tr("NTAL 全面检测"), tr("没有勾选检查项。"))
        return
    try:
        progress_parent = host.iface.mainWindow() if host.iface is not None else host
    except Exception:
        progress_parent = host
    progress = _CheckProgress(progress_parent)
    try:
        result = run_audit(host, selected, progress=progress)
        if result.get("ok"):
            progress.report(0.97, "正在生成临时图层", force=True)
            added = add_issue_temp_layers([result], group_root=AUDIT_GROUP_NAME)
    finally:
        progress.close()
    if not result.get("ok"):
        text = "\n".join(result.get("config_errors") or [tr("配置不完整")])
        QMessageBox.warning(host, tr("NTAL 全面检测"), text)
        try:
            host.log.setPlainText(text)
        except Exception:
            pass  # nosec B110
        return
    lines = [
        tr("组网骨架固定（光交→主干→接头→配线→分纤盒→入户）。命名方案见参数「方案」页。"),
        tr("硬错误 {}，软错误 {}，警告 {}。").format(
            len(result.get("hard") or []),
            len(result.get("soft") or []),
            len(result.get("warn") or []),
        ),
    ]
    lines.extend(result.get("notes") or [])
    if added:
        lines.append(tr("已生成图层：") + tr("、").join(added))
    else:
        lines.append(tr("勾选的类里没有发现问题。"))
    lines.append(tr("结果窗置顶、不挡地图。检查页看问题列表，可修复页只列方向反了的线。"))
    result["summary_lines"] = lines
    detail = []
    for item in result.get("hard") or []:
        detail.append(tr("硬错误") + " " + (item.get("message") or ""))
    for item in result.get("soft") or []:
        detail.append(tr("软错误") + " " + (item.get("message") or ""))
    for item in result.get("warn") or []:
        detail.append(tr("警告") + " " + (item.get("message") or ""))
    result["tree_text"] = "\n".join(detail)
    try:
        host.log.setPlainText("\n".join(lines))
    except Exception:
        pass  # nosec B110
    seen = set()
    for old in (_DIR_DLG, line_dir_mod._DIR_DLG):
        if old is None or id(old) in seen:
            continue  # nosec B112
        seen.add(id(old))
        try:
            old.close()
        except Exception:
            pass  # nosec B110
    _DIR_DLG = None
    line_dir_mod._DIR_DLG = None
    parent = None
    try:
        parent = host.iface.mainWindow() if host.iface is not None else host
    except Exception:
        parent = host
    view = LineDirDialog(result, host, added=added, parent=parent)
    _DIR_DLG = view
    line_dir_mod._DIR_DLG = view
    view.show()
    view.raise_()
    view.activateWindow()
