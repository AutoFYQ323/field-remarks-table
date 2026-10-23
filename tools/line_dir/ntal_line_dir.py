# -*- coding: utf-8 -*-
from ...i18n import language_changed, tr
"""从光交往用户检查线数字化方向，并报告主干配线的结构硬错误。先出临时点，窗口不挡地图，再全部翻转或翻转勾选。"""
import time
from collections import defaultdict, deque

from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsRectangle
from qgis.PyQt.QtCore import QEventLoop, Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from ..window_theme import register_tool_window
from .layer_groups import resolve_group
from .ntal_engine import (
    ROLE_LABEL,
    _build_index,
    _snap_end,
    add_issue_temp_layers,
    collect_lines,
    collect_points,
    format_num,
    split_issue_levels,
    working_crs_from_layers,
)
from .ntal_graph import (
    ROLE_CABLE,
    ROLE_DIST,
    ROLE_DROP,
    ROLE_FAT,
    ROLE_OCC,
    ROLE_SPLICE,
    ROLE_TRUNK,
    ROLE_USER,
    analyze_graph,
    other_end,
)

from .ntal_roles import classify_cable_pair, classify_drop_pair, apply_role_label

STRUCT_KINDS = ("cycle", "fat_branch", "fat_multi_in", "splice_multi_in", "occ_in")
STRUCT_VISIBLE = ("line_reversed",)

try:
    CHECKED = Qt.CheckState.Checked
    UNCHECKED = Qt.CheckState.Unchecked
    ITEM_USER_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    ITEM_ENABLED = Qt.ItemFlag.ItemIsEnabled
    ITEM_SELECTABLE = Qt.ItemFlag.ItemIsSelectable
except AttributeError:
    CHECKED = Qt.CheckState.Checked
    UNCHECKED = Qt.CheckState.Unchecked
    ITEM_USER_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    ITEM_ENABLED = Qt.ItemFlag.ItemIsEnabled
    ITEM_SELECTABLE = Qt.ItemFlag.ItemIsSelectable


def _esc(text):
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _reverse_geom(geom):
    """只倒顶点顺序。保留 Z/M 和圆弧，不打散曲线。"""
    if geom is None or geom.isEmpty():
        return None
    try:
        src = geom.constGet()
        if geom.isMultipart():
            out = src.createEmptyWithSameType()
            for i in range(src.numGeometries()):
                out.addGeometry(src.geometryN(i).reversed())
            return QgsGeometry(out)
        return QgsGeometry(src.reversed())
    except Exception:
        return None


def reverse_line_geoms(rows):
    grouped = {}
    order = []
    for row in rows or []:
        layer = row.get("layer")
        if layer is None:
            continue
        key = layer.id()
        if key not in grouped:
            grouped[key] = (layer, [])
            order.append(key)
        grouped[key][1].append(row)
    updated = 0
    errors = []
    for key in order:
        layer, items = grouped[key]
        if not layer.isEditable():
            if not layer.startEditing():
                errors.append(tr("{} 无法进入编辑").format(layer.name()))
                continue
        layer.beginEditCommand(tr("NTAL 线方向修复"))
        try:
            for row in items:
                feat = layer.getFeature(row["fid"])
                if not feat.isValid():
                    errors.append(tr("{} #{} 找不到要素").format(layer.name(), row["fid"]))
                    continue
                new_geom = _reverse_geom(feat.geometry())
                if new_geom is None:
                    errors.append(tr("{} #{} 无法翻转").format(layer.name(), row["fid"]))
                    continue
                if not layer.changeGeometry(row["fid"], new_geom):
                    errors.append(tr("{} #{} 改几何失败").format(layer.name(), row["fid"]))
                    continue
                updated += 1
            layer.endEditCommand()
        except Exception as exc:
            try:
                layer.destroyEditCommand()
            except Exception:
                pass  # nosec B110
            errors.append(tr("{} 修复异常：{}").format(layer.name(), exc))
    return updated, errors


class _CheckProgress(object):
    """阶段进度。刷新间隔约 0.25 秒，不在每个要素上重绘。"""

    def __init__(self, parent):
        self.dlg = QProgressDialog(tr("正在检查…"), "", 0, 1000, parent)
        self.dlg.setWindowTitle(tr("NTAL 全面检测"))
        try:
            modal = Qt.WindowModality.ApplicationModal
        except AttributeError:
            modal = Qt.WindowModality.ApplicationModal
        self.dlg.setWindowModality(modal)
        self.dlg.setMinimumDuration(0)
        self.dlg.setAutoClose(False)
        self.dlg.setAutoReset(False)
        self.dlg.setMinimumWidth(320)
        try:
            self.dlg.setCancelButton(None)
        except Exception:
            pass  # nosec B110
        self.dlg.setValue(0)
        self._last = 0.0
        self.dlg.show()
        register_tool_window(self.dlg)
        try:
            flag = QEventLoop.ExcludeUserInputEvents
        except AttributeError:
            flag = QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        QApplication.processEvents(flag)

    def report(self, frac, text=None, force=False):
        now = time.monotonic()
        value = int(max(0.0, min(1.0, float(frac))) * 1000)
        if not force and value < 1000 and (now - self._last) < 0.25:
            return
        self._last = now
        try:
            if text:
                self.dlg.setLabelText(text)
            if self.dlg.value() != value:
                self.dlg.setValue(value)
        except Exception:
            pass  # nosec B110

    def close(self):
        try:
            self.dlg.setValue(1000)
            self.dlg.close()
        except Exception:
            pass  # nosec B110


class _StepTick(object):
    def __init__(self, progress, base, span, total, text):
        self.progress = progress
        self.base = float(base)
        self.span = float(span)
        self.total = max(int(total or 0), 1)
        self.text = text
        self.done = 0

    def __call__(self, count=1):
        self.done += int(count)
        frac = self.base + self.span * min(self.done, self.total) / float(self.total)
        self.progress.report(frac, self.text)


def _feat_total(layers):
    total = 0
    for layer in layers or []:
        try:
            count = int(layer.featureCount())
        except Exception:
            count = 0
        if count > 0:
            total += count
    return total


def _make_tick(progress, base, span, total, text):
    if progress is None:
        return None
    progress.report(base, text, force=True)
    return _StepTick(progress, base, span, total, text)


def run_line_dir_analysis(
    occ_layers, splice_layers, fat_layers, user_layers,
    cable_layers, drop_layers,
    occ_filters, splice_filters, fat_filters, user_filters,
    cable_filters, drop_filters,
    tolerance,
    trunk_layers=None, dist_layers=None, trunk_filters=None, dist_filters=None,
    progress=None, prepared=None, scheme=None,
):
    """prepared：全面检测已经采集好的点线，传进来就不再读一遍图层。"""
    config_errors = []
    if not cable_layers:
        cable_layers = list(trunk_layers or []) + list(dist_layers or [])
        cable_filters = dict(trunk_filters or {})
        cable_filters.update(dist_filters or {})
    if not occ_layers:
        config_errors.append(tr("请在图层配置里选择光交。方向从光交往外走。"))
    line_ok = bool(cable_layers or drop_layers)
    if not line_ok:
        config_errors.append(tr("请至少配置光缆或皮线其中一类。"))
    if float(tolerance or 0) <= 0:
        config_errors.append(tr("吸附容差必须大于 0。"))
    if config_errors:
        return {"ok": False, "kind": "line_dir", "config_errors": config_errors}
    from .ntal_scheme import resolve_scheme, result_meta
    scheme = resolve_scheme(scheme)

    if prepared:
        work_crs = prepared["work_crs"]
        occ_rows, occ_stats = [dict(r) for r in prepared["occ"][0]], prepared["occ"][1]
        splice_rows, splice_stats = [dict(r) for r in prepared["splice"][0]], prepared["splice"][1]
        fat_rows, fat_stats = [dict(r) for r in prepared["fat"][0]], prepared["fat"][1]
        user_rows, user_stats = [dict(r) for r in prepared["user"][0]], prepared["user"][1]
        cable_rows, cable_stats = [dict(r) for r in prepared["cable"][0]], prepared["cable"][1]
        drop_rows, drop_stats = [dict(r) for r in prepared["drop"][0]], prepared["drop"][1]
    else:
        all_layers = list(occ_layers or []) + list(splice_layers or []) + list(fat_layers or [])
        all_layers += list(user_layers or []) + list(cable_layers or []) + list(drop_layers or [])
        work_crs = working_crs_from_layers(all_layers)
        point_tick = _make_tick(
            progress, 0.02, 0.46,
            _feat_total(list(occ_layers or []) + list(splice_layers or []) + list(fat_layers or []) + list(user_layers or [])),
            tr("正在读取点"),
        )
        occ_rows, occ_stats = collect_points(occ_layers or [], occ_filters, ROLE_OCC, work_crs, on_step=point_tick)
        splice_rows, splice_stats = collect_points(splice_layers or [], splice_filters, ROLE_SPLICE, work_crs, on_step=point_tick)
        fat_rows, fat_stats = collect_points(fat_layers or [], fat_filters, ROLE_FAT, work_crs, on_step=point_tick)
        user_rows, user_stats = collect_points(user_layers or [], user_filters, ROLE_USER, work_crs, on_step=point_tick)
        line_tick = _make_tick(
            progress, 0.48, 0.32,
            _feat_total(list(cable_layers or []) + list(drop_layers or [])),
            tr("正在读取线"),
        )
        cable_rows, cable_stats = collect_lines(cable_layers or [], cable_filters, ROLE_CABLE, work_crs, "", on_step=line_tick)
        drop_rows, drop_stats = collect_lines(drop_layers or [], drop_filters, ROLE_DROP, work_crs, "", on_step=line_tick)
    trunk_rows, dist_rows = [], []
    trunk_stats, dist_stats = {}, {}

    hard = []
    warn = []
    if not occ_rows:
        hard.append({"kind": "config", "message": tr("光交图层筛选后没有可用点。"), "refs": []})
    edge_rows = list(cable_rows) + list(drop_rows)
    if not edge_rows:
        hard.append({"kind": "config", "message": tr("没有可用的线。"), "refs": []})

    node_rows = list(occ_rows) + list(splice_rows) + list(fat_rows) + list(user_rows)
    node_map = {row["id"]: row for row in node_rows}
    edge_map = {row["id"]: row for row in edge_rows}
    index, by_int = _build_index(node_rows)
    graph_edges = {}
    adj = defaultdict(list)
    edge_tick = _make_tick(progress, 0.80, 0.10, len(edge_rows), tr("正在检查线端"))
    edge_seen = 0
    for edge in edge_rows:
        edge_seen += 1
        if edge_tick is not None and (edge_seen & 255) == 0:
            edge_tick(256)
        a, amb_a = _snap_end(edge["start"], index, by_int, tolerance)
        b, amb_b = _snap_end(edge["end"], index, by_int, tolerance)
        edge["a"] = a
        edge["b"] = b
        if amb_a:
            hard.append({
                "kind": "snap_ambig",
                "message": tr("起点同时靠近多个点：{}").format(edge["label"]),
                "refs": [("edge", edge["id"])] + [("node", nid) for nid in amb_a],
            })
        if amb_b:
            hard.append({
                "kind": "snap_ambig",
                "message": tr("终点同时靠近多个点：{}").format(edge["label"]),
                "refs": [("edge", edge["id"])] + [("node", nid) for nid in amb_b],
            })
        ra = (node_map.get(a) or {}).get("role") if a else None
        rb = (node_map.get(b) or {}).get("role") if b else None
        if edge.get("role") == ROLE_DROP:
            role, severity, kind, tail = classify_drop_pair(ra, rb, scheme)
        else:
            role, severity, kind, tail = classify_cable_pair(ra, rb, scheme)
            if role:
                apply_role_label(edge, role, ROLE_LABEL)
                if role == ROLE_TRUNK:
                    trunk_rows.append(edge)
                elif role == ROLE_DIST:
                    dist_rows.append(edge)
        if severity and kind not in ("dangling", "both_open"):
            item = {
                "kind": kind,
                "message": "{}：{}".format(tail, edge["label"]),
                "refs": [("edge", edge["id"])]
                + ([("node", a)] if a else [])
                + ([("node", b)] if b else []),
            }
            if severity == "hard":
                hard.append(item)
            else:
                warn.append(item)
        graph_edges[edge["id"]] = {"a": a, "b": b, "label": edge["label"]}
        if a:
            adj[a].append(edge["id"])
        if b and b != a:
            adj[b].append(edge["id"])

    oriented = {}
    queue = deque()
    reached = set()
    for occ in occ_rows:
        queue.append(occ["id"])
        reached.add(occ["id"])
    while queue:
        nid = queue.popleft()
        if (node_map.get(nid) or {}).get("role") == ROLE_USER:
            continue
        for eid in adj.get(nid, []):
            if eid in oriented:
                continue
            dest = other_end(graph_edges[eid], nid)
            if dest == nid:
                hard.append({
                    "kind": "self_loop",
                    "message": tr("线两端接到同一点：{}").format(edge_map[eid]["label"]),
                    "refs": [("edge", eid), ("node", nid)],
                })
                oriented[eid] = (nid, nid)
                continue
            if dest is None:
                is_drop = (edge_map.get(eid) or {}).get("role") == ROLE_DROP
                item = {
                    "kind": "dangling",
                    "message": tr("一端空：{}").format(edge_map[eid]["label"]),
                    "refs": [("edge", eid), ("node", nid)],
                }
                if is_drop:
                    warn.append(item)
                else:
                    hard.append(item)
                oriented[eid] = (nid, None)
                continue
            oriented[eid] = (nid, dest)
            if dest not in reached:
                reached.add(dest)
                queue.append(dest)

    reversible = []
    ok_count = 0
    by_role = defaultdict(lambda: {"ok": 0, "rev": 0})
    tree = [tr("从光交往外走，数字化起点应在上游。")]
    tree.append(tr("容差 {} 米。").format(format_num(tolerance)))
    for edge in edge_rows:
        eid = edge["id"]
        pair = oriented.get(eid)
        role = edge.get("role") or ""
        title = ROLE_LABEL.get(role, role)
        if pair is None:
            continue
        fr, to = pair
        start_id = graph_edges[eid].get("a")
        if fr == start_id:
            ok_count += 1
            by_role[role]["ok"] += 1
            tree.append(tr("  正向  {}  {} → {}").format(
                edge["label"],
                (node_map.get(fr) or {}).get("label") or "",
                (node_map.get(to) or {}).get("label") or "（空）",
            ))
            continue
        if fr and fr == graph_edges[eid].get("b"):
            by_role[role]["rev"] += 1
            msg = tr("数字化方向反了（终点在上游）：{}  上游 {}  下游 {}").format(
                edge["label"],
                (node_map.get(fr) or {}).get("label") or "",
                (node_map.get(to) or {}).get("label") or "（空）",
            )
            if edge.get("multipart"):
                msg += tr("。多段线会整条一起倒转。")
            warn.append({
                "kind": "line_reversed",
                "message": msg,
                "refs": [("edge", eid), ("node", fr)] + ([("node", to)] if to else []),
            })
            reversible.append({
                "id": eid,
                "layer": edge["layer"],
                "layer_name": edge["layer_name"],
                "fid": edge["fid"],
                "role": role,
                "label": edge["label"],
                "upstream": (node_map.get(fr) or {}).get("label") or "",
                "downstream": (node_map.get(to) or {}).get("label") or "",
                "multipart": bool(edge.get("multipart")),
                "message": msg,
            })
            tree.append(tr("  反了  {}").format(msg))

    for edge in edge_rows:
        if edge["id"] in oriented:
            continue
        pair = graph_edges.get(edge["id"]) or {}
        a, b = pair.get("a"), pair.get("b")
        if not a and not b:
            warn.append({
                "kind": "both_open",
                "message": tr("两端都空，无法判断方向：{}").format(edge["label"]),
                "refs": [("edge", edge["id"])],
            })
        elif a and b:
            warn.append({
                "kind": "unreached_edge",
                "message": tr("未从光交通到，不判断方向：{}").format(edge["label"]),
                "refs": [("edge", edge["id"])],
            })
        else:
            item = {
                "kind": "dangling",
                "message": tr("一端空，无法判断方向：{}").format(edge["label"]),
                "refs": [("edge", edge["id"])],
            }
            if edge.get("role") == ROLE_DROP:
                warn.append(item)
            else:
                hard.append(item)

    for occ in occ_rows:
        if not adj.get(occ["id"]):
            warn.append({
                "kind": "occ_no_out",
                "message": tr("光交没有出线：{}").format(occ["label"]),
                "refs": [("node", occ["id"])],
            })

    if progress is not None:
        progress.report(0.92, tr("正在检查网络结构"), force=True)
    struct_nodes = {}
    for row in list(occ_rows) + list(splice_rows) + list(fat_rows):
        struct_nodes[row["id"]] = {
            "role": row.get("role"),
            "hh": row.get("hh") or 0,
            "label": row.get("label"),
        }
    struct_edges = {}
    for edge in list(trunk_rows) + list(dist_rows):
        struct_edges[edge["id"]] = {
            "a": edge.get("a"),
            "b": edge.get("b"),
            "label": edge.get("label"),
        }
    struct = analyze_graph(
        struct_nodes, struct_edges, [row["id"] for row in occ_rows],
        accumulate=False, scheme=scheme,
    )
    for item in list(struct.get("hard") or []) + list(struct.get("warn") or []):
        if item.get("kind") in STRUCT_KINDS:
            hard.append(item)

    suggestions = []
    rev_n = len(reversible)
    dang = sum(1 for item in warn if item.get("kind") == "dangling")
    open2 = sum(1 for item in warn if item.get("kind") == "both_open")
    unreached = sum(1 for item in warn if item.get("kind") == "unreached_edge")
    ambig = sum(1 for item in hard if item.get("kind") == "snap_ambig")
    loops = sum(1 for item in hard if item.get("kind") == "self_loop")
    suggestions.append(tr("方向反了 {} 条：数字化终点在上游。可用「全部翻转」，或在表里勾选后「翻转勾选」。").format(rev_n))
    suggestions.append(tr("修复只改线的顶点顺序，不改属性；写入编辑缓冲，需要你自己保存图层。"))
    if dang or open2:
        suggestions.append(tr("一端空/两端空 {} 处：建议先用「线显示」看端点，或把吸附容差改大一点。").format(dang + open2))
    if unreached:
        suggestions.append(tr("未从光交通到 {} 条：可能断在接头/分纤盒，或图层没配齐。通不到的线程序不会翻。").format(unreached))
    if ambig:
        suggestions.append(tr("端点歧义 {} 处：容差内有多个点，先错开点或改小容差，否则方向不可靠。").format(ambig))
    if loops:
        suggestions.append(tr("自环 {} 处：线两端接到同一点，不会自动翻。").format(loops))
    struct_n = sum(1 for item in hard if item.get("kind") in STRUCT_KINDS)
    if struct_n:
        suggestions.append(tr("结构硬错误 {} 处：成环、分叉、多进线或光交被当成下游。只报告，不翻转。").format(struct_n))
    if rev_n:
        suggestions.append(tr("修完再用「线显示」看：圆点（起点）应更靠近光交一侧。"))
    if not rev_n and not dang and not unreached and not ambig and not hard:
        suggestions.append(tr("从光交通到的线方向都正确。"))

    def _part(stats_map, role):
        rows = []
        for layer_id, stat in (stats_map or {}).items():
            layer = stat.get("layer")
            extracted = int(stat.get("extracted") or 0)
            used = 0
            if role in (ROLE_OCC, ROLE_SPLICE, ROLE_FAT, ROLE_USER):
                used = sum(1 for item in node_rows if item.get("layer_id") == layer_id and item["id"] in reached)
            else:
                used = sum(1 for item in edge_rows if item.get("layer_id") == layer_id and item["id"] in oriented)
            rows.append({
                "role": role,
                "layer_name": layer.name() if layer is not None else "",
                "used": used,
                "extracted": extracted,
                "ok": extracted > 0,
            })
        return rows

    participation = []
    participation.extend(_part(occ_stats, ROLE_OCC))
    participation.extend(_part(splice_stats, ROLE_SPLICE))
    participation.extend(_part(fat_stats, ROLE_FAT))
    participation.extend(_part(user_stats, ROLE_USER))
    participation.extend(_part(cable_stats, ROLE_CABLE))
    participation.extend(_part(drop_stats, ROLE_DROP))

    summary_lines = [
        tr("检查了线 {} 条（光缆 {}，其中主干 {}、配线 {}，皮线 {}）。").format(
            len(edge_rows), len(cable_rows), len(trunk_rows), len(dist_rows), len(drop_rows)
        ),
        tr("从光交通到 {} 条，方向正确 {} 条，方向反了 {} 条。").format(
            len(oriented), ok_count, rev_n
        ),
    ]
    for role in (ROLE_TRUNK, ROLE_DIST, ROLE_DROP):
        info = by_role.get(role) or {"ok": 0, "rev": 0}
        if info["ok"] or info["rev"]:
            summary_lines.append(tr("  {}：正向 {}，反了 {}。").format(
                ROLE_LABEL.get(role, role), info["ok"], info["rev"]
            ))
    _hard, _soft, _warn = split_issue_levels({"hard": hard, "warn": warn})
    summary_lines.append(tr("风险：硬错误 {}，软错误 {}，警告 {}（含方向反了）。").format(
        len(_hard), len(_soft), len(_warn)
    ))
    summary_lines.append(tr("结构硬错误 {} 处（成环、分叉、多进线、光交被当成下游），不参与翻转。").format(
        sum(1 for item in hard if item.get("kind") in STRUCT_KINDS)
    ))
    summary_lines.append(tr("建议："))
    summary_lines.extend("  · " + item for item in suggestions)

    out = {
        "ok": True,
        "kind": "line_dir",
        "tolerance": tolerance,
        "hard": hard,
        "warn": warn,
        "nodes": node_map,
        "edges": edge_map,
        "work_crs": work_crs,
        "reversible": reversible,
        "ok_count": ok_count,
        "oriented_count": len(oriented),
        "edge_total": len(edge_rows),
        "participation": participation,
        "tree_text": "\n".join(tree),
        "summary_lines": summary_lines,
        "suggestions": suggestions,
        "source_label": tr("线方向"),
        "writes": [],
    }
    out.update(result_meta(scheme))
    return out


_DIR_DLG = None


def _qt_flag(*names):
    for name in names:
        if hasattr(Qt, name):
            return getattr(Qt, name)
        types = getattr(Qt, "WindowType", None)
        if types is not None and hasattr(types, name):
            return getattr(types, name)
        widget = getattr(Qt, "WidgetAttribute", None)
        if widget is not None and hasattr(widget, name):
            return getattr(widget, name)
    return 0


class LineDirDialog(QDialog):
    AUTO = 1
    PICK = 2

    def __init__(self, result, host, added=None, parent=None):
        super(LineDirDialog, self).__init__(parent)
        self.result = result
        self.host = host
        self.added = list(added or [])
        self._applied = False
        self._free = (result or {}).get("kind") == "line_dir_free"
        self.setModal(False)
        flags = (
            _qt_flag("Tool")
            | _qt_flag("WindowStaysOnTopHint")
            | _qt_flag("WindowCloseButtonHint")
            | _qt_flag("WindowTitleHint")
        )
        self.setWindowFlags(flags)
        self.setWindowTitle(tr("NTAL 全面检测"))
        self.setMinimumSize(420, 320)
        self.resize(520, 400)
        try:
            self.setAttribute(_qt_flag("WA_DeleteOnClose"), True)
        except Exception:
            pass  # nosec B110
        root = QVBoxLayout(self)
        if self._free:
            hint_text = tr("不挡地图，窗口置顶。打勾的翻转，不打勾的不动。方向反了默认打勾，伪成环默认不勾。")
        elif (result or {}).get("kind") == "audit":
            hint_text = tr("不挡地图，窗口置顶。检查页是这次的硬错误、软错误和警告；可修复页是方向反了的线。全部翻转=这些线一次翻；翻转勾选=只翻表里打勾的。")
        else:
            hint_text = tr("不挡地图，窗口置顶。全部翻转=所有方向反了的线；翻转勾选=只翻表里打勾的。")
        self.hint = QLabel(hint_text)
        hint = self.hint
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.tabs = QTabWidget()
        tabs = self.tabs
        self.txt_check = QTextEdit()
        self.txt_check.setReadOnly(True)
        self.txt_tree = QTextEdit()
        self.txt_tree.setReadOnly(True)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([tr("修"), tr("类型"), tr("图层"), "FID", tr("名称"), tr("说明")])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        tabs.addTab(self.txt_check, tr("检查"))
        tabs.addTab(self.txt_tree, tr("明细"))
        tabs.addTab(self.table, tr("可修复"))
        self.table.cellDoubleClicked.connect(self._zoom_to_row)
        root.addWidget(tabs, 1)
        try:
            reject_role = QDialogButtonBox.ButtonRole.RejectRole
            action_role = QDialogButtonBox.ButtonRole.ActionRole
        except AttributeError:
            reject_role = QDialogButtonBox.ButtonRole.RejectRole
            action_role = QDialogButtonBox.ButtonRole.ActionRole
        buttons = QDialogButtonBox()
        reversible = result.get("reversible") or []
        self.btn_auto = None
        if not self._free:
            self.btn_auto = buttons.addButton(tr("全部翻转"), action_role)
            self.btn_auto.setEnabled(bool(reversible))
            self.btn_auto.setToolTip(tr("不管表格勾选，把检查到的全部「方向反了」的线一次翻转。"))
            self.btn_auto.clicked.connect(self._do_auto)
        self.btn_pick = buttons.addButton(tr("翻转勾选"), action_role)
        self.btn_close = buttons.addButton(tr("关闭"), reject_role)
        self.btn_pick.setEnabled(bool(reversible))
        if self._free:
            self.btn_pick.setToolTip(tr("只翻转打勾的线。方向反了默认打勾，伪成环默认不勾。"))
        else:
            self.btn_pick.setToolTip(tr("只翻转「可修复」表里打勾的线，可先对照地图去掉不确定的。"))
        self.btn_pick.clicked.connect(self._do_pick)
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)
        self._fill()
        try:
            language_changed().connect(self._apply_language)
        except Exception:
            pass  # nosec B110
        register_tool_window(self)

    def _fill(self):
        result = self.result
        html = ['<div style="font-size:12px; line-height:1.45; font-family:\'Microsoft YaHei\',sans-serif;">']
        html.append(tr("<b>全面检测</b>　含线方向　容差 {} 米<br>").format(format_num(result.get("tolerance"))))
        if result.get("config_errors"):
            html.append(tr('<span style="color:#c62828; font-weight:700;">配置</span>'))
            for msg in result.get("config_errors") or []:
                html.append('<div style="color:#c62828;">· {}</div>'.format(_esc(msg)))
        for line in result.get("summary_lines") or []:
            html.append("<div>{}</div>".format(_esc(line)))
        hard, soft, warn = split_issue_levels(result)
        html.append(tr('<br><span style="color:#c62828; font-weight:700;">硬错误：{}</span>').format(len(hard)))
        if hard:
            for item in hard:
                html.append('<div style="color:#c62828;">· {}</div>'.format(_esc(item.get("message") or "")))
        else:
            html.append(tr("<div>（无）</div>"))
        html.append(tr('<span style="color:#ef6c00; font-weight:700;">软错误：{}</span>').format(len(soft)))
        if soft:
            for item in soft[:40]:
                html.append('<div style="color:#ef6c00;">· {}</div>'.format(_esc(item.get("message") or "")))
            if len(soft) > 40:
                html.append(tr("<div>… 还有 {} 条</div>").format(len(soft) - 40))
        else:
            html.append(tr("<div>（无）</div>"))
        html.append(tr('<span style="color:#f9a825; font-weight:700;">警告：{}</span>').format(len(warn)))
        if warn:
            for item in warn[:40]:
                html.append('<div style="color:#f9a825;">· {}</div>'.format(_esc(item.get("message") or "")))
            if len(warn) > 40:
                html.append(tr("<div>… 还有 {} 条</div>").format(len(warn) - 40))
        else:
            html.append(tr("<div>（无）</div>"))
        html.append(tr("<b>图层参与</b>（走到 / 筛出）"))
        for row in result.get("participation") or []:
            role_name = ROLE_LABEL.get(row["role"], row["role"])
            html.append("<div>· [{}] {}　{} / {}</div>".format(
                _esc(tr(role_name) if role_name else ""),
                _esc(row["layer_name"]),
                row["used"],
                row["extracted"],
            ))
        if (result or {}).get("kind") == "audit":
            html.append(tr("问题点在图层组「全面检测」里，下面分「硬错误」「软错误」「警告」。关掉本窗后图层还在，双击「可修复」表可缩放到对应点。"))
        else:
            html.append(tr("问题点已写入图层组「拓扑检查结果」。默认只显示「线方向反了」，其余图层在该组里，需要时再勾选。"))
        html.append("</div>")
        self.txt_check.setHtml("".join(html))
        self.txt_tree.setPlainText(result.get("tree_text") or "")
        rows = result.get("reversible") or []
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(ITEM_USER_CHECKABLE | ITEM_ENABLED | ITEM_SELECTABLE)
            if self._free and row.get("issue") == "pseudo_cycle":
                chk.setCheckState(UNCHECKED)
            else:
                chk.setCheckState(CHECKED)
            self.table.setItem(i, 0, chk)
            kind_text = row.get("type_label") or ROLE_LABEL.get(row.get("role"), row.get("role") or "")
            kind_text = tr(kind_text) if kind_text else ""
            values = [
                kind_text,
                row.get("layer_name") or "",
                str(row.get("fid") or ""),
                row.get("label") or "",
                row.get("message") or "",
            ]
            for col, text in enumerate(values, start=1):
                self.table.setItem(i, col, QTableWidgetItem(text))

    def _zoom_to_row(self, index, _column=0):
        rows = self.result.get("reversible") or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        layer = row.get("layer")
        fid = row.get("fid")
        if layer is None or fid is None:
            return
        canvas = None
        try:
            canvas = self.host.iface.mapCanvas()
        except Exception:
            canvas = None
        if canvas is None:
            return
        try:
            feat = layer.getFeature(fid)
        except Exception:
            return
        geom = feat.geometry() if feat.isValid() else None
        if geom is None or geom.isEmpty():
            return
        box = geom.boundingBox()
        try:
            dst = canvas.mapSettings().destinationCrs()
            if layer.crs() != dst:
                xform = QgsCoordinateTransform(layer.crs(), dst, QgsProject.instance().transformContext())
                box = xform.transformBoundingBox(box)
        except Exception:
            pass  # nosec B110
        span = max(box.width(), box.height())
        if span <= 0:
            span = max(canvas.extent().width(), canvas.extent().height()) * 0.05 or 40.0
        center = box.center()
        half = span * 0.8
        canvas.setExtent(QgsRectangle(center.x() - half, center.y() - half, center.x() + half, center.y() + half))
        canvas.refresh()
        try:
            canvas.flashFeatureIds(layer, [fid])
        except Exception:
            pass  # nosec B110

    def picked_rows(self):
        rows = self.result.get("reversible") or []
        picked = []
        for i, row in enumerate(rows):
            item = self.table.item(i, 0)
            if item is not None and item.checkState() == CHECKED:
                picked.append(row)
        return picked

    def _log_summary(self):
        lines = list(self.result.get("summary_lines") or [])
        if self.added:
            lines.append(tr("已生成临时图层：") + "、".join(self.added))
        return lines

    def _apply(self, rows, title):
        host = self.host
        updated, errors = reverse_line_geoms(rows)
        msg = "\n".join(self._log_summary())
        msg += tr("\n已翻转 {} 条线到编辑缓冲。请保存图层。").format(updated)
        if errors:
            msg += "\n" + "\n".join(errors)
        if host is not None and hasattr(host, "log"):
            host.log.setPlainText(msg)
        QMessageBox.information(self, title, msg)
        if host is not None and hasattr(host, "_refresh_canvas"):
            host._refresh_canvas()
        self._applied = True
        self.close()

    def _do_auto(self):
        n = len(self.result.get("reversible") or [])
        if n <= 0:
            return
        reply = QMessageBox.question(
            self,
            tr("全部翻转"),
            tr("将翻转全部 {} 条「方向反了」的线，不看勾选。\n只改顶点顺序，写入编辑缓冲，不保存。\n一端空、未挂上、歧义的线不会动。\n继续？").format(n),
        )
        try:
            yes = QMessageBox.StandardButton.Yes
        except AttributeError:
            yes = QMessageBox.StandardButton.Yes
        if reply != yes:
            return
        self._apply(self.result.get("reversible") or [], tr("全部翻转"))

    def _do_pick(self):
        picked = self.picked_rows()
        if not picked:
            QMessageBox.information(self, tr("翻转勾选"), tr("没有打勾的线。"))
            return
        reply = QMessageBox.question(
            self,
            tr("翻转勾选"),
            tr("将翻转勾选的 {} 条线。\n只改顶点顺序，写入编辑缓冲，不保存。\n继续？").format(len(picked)),
        )
        try:
            yes = QMessageBox.StandardButton.Yes
        except AttributeError:
            yes = QMessageBox.StandardButton.Yes
        if reply != yes:
            return
        self._apply(picked, tr("翻转勾选"))

    def _apply_language(self, *_args):
        if self._free:
            self.setWindowTitle(tr("线方向检查"))
            self.hint.setText(tr("不挡地图，窗口置顶。打勾的翻转，不打勾的不动。方向反了默认打勾，伪成环默认不勾。"))
            self.btn_pick.setToolTip(tr("只翻转打勾的线。方向反了默认打勾，伪成环默认不勾。"))
        elif (self.result or {}).get("kind") == "audit":
            self.setWindowTitle(tr("NTAL 全面检测"))
            self.hint.setText(tr("不挡地图，窗口置顶。检查页是这次的硬错误、软错误和警告；可修复页是方向反了的线。全部翻转=这些线一次翻；翻转勾选=只翻表里打勾的。"))
            self.btn_pick.setToolTip(tr("只翻转「可修复」表里打勾的线，可先对照地图去掉不确定的。"))
        else:
            self.setWindowTitle(tr("NTAL 全面检测"))
            self.hint.setText(tr("不挡地图，窗口置顶。全部翻转=所有方向反了的线；翻转勾选=只翻表里打勾的。"))
            self.btn_pick.setToolTip(tr("只翻转「可修复」表里打勾的线，可先对照地图去掉不确定的。"))
        self.tabs.setTabText(0, tr("检查"))
        self.tabs.setTabText(1, tr("明细"))
        self.tabs.setTabText(2, tr("可修复"))
        self.table.setHorizontalHeaderLabels([tr("修"), tr("类型"), tr("图层"), "FID", tr("名称"), tr("说明")])
        if self.btn_auto is not None:
            self.btn_auto.setText(tr("全部翻转"))
            self.btn_auto.setToolTip(tr("不管表格勾选，把检查到的全部「方向反了」的线一次翻转。"))
        self.btn_pick.setText(tr("翻转勾选"))
        self.btn_close.setText(tr("关闭"))
        self._fill()

    def closeEvent(self, event):
        try:
            language_changed().disconnect(self._apply_language)
        except Exception:
            pass  # nosec B110
        global _DIR_DLG
        if _DIR_DLG is self:
            _DIR_DLG = None
        if not self._applied and self.host is not None and hasattr(self.host, "log"):
            self.host.log.setPlainText("\n".join(self._log_summary()))
        super(LineDirDialog, self).closeEvent(event)


def open_line_dir(host):
    global _DIR_DLG
    occ_layers, occ_filters, _ = resolve_group(host.layers.get("occ"))
    splice_layers, splice_filters, _ = resolve_group(host.layers.get("splice"))
    fat_layers, fat_filters, _ = resolve_group(host.layers.get("fat"))
    user_layers, user_filters, _ = resolve_group(host.layers.get("user"))
    cable_layers, cable_filters, _ = resolve_group(host.layers.get("cable"))
    drop_layers, drop_filters, _ = resolve_group(host.layers.get("drop"))
    parent = None
    try:
        parent = host.iface.mainWindow() if host.iface is not None else host
    except Exception:
        parent = host
    progress = _CheckProgress(parent)
    try:
        result = run_line_dir_analysis(
            occ_layers, splice_layers, fat_layers, user_layers,
            cable_layers, drop_layers,
            occ_filters, splice_filters, fat_filters, user_filters,
            cable_filters, drop_filters,
            host.tolerance,
            progress=progress,
            scheme=getattr(host, "scheme_id", None),
        )
        if not result.get("ok"):
            QMessageBox.warning(
                host,
                tr("NTAL 线方向"),
                "\n".join(result.get("config_errors") or [tr("配置不完整")]),
            )
            host.log.setPlainText("\n".join(result.get("config_errors") or []))
            return
        progress.report(0.97, tr("正在生成临时图层"), force=True)
        added = add_issue_temp_layers([result], visible_kinds=STRUCT_VISIBLE)
    finally:
        progress.close()
    old = _DIR_DLG
    _DIR_DLG = None
    if old is not None:
        try:
            old.close()
        except Exception:
            pass  # nosec B110
    parent = None
    try:
        parent = host.iface.mainWindow() if host.iface is not None else host
    except Exception:
        parent = host
    dlg = LineDirDialog(result, host, added=added, parent=parent)
    _DIR_DLG = dlg
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    lines = list(result.get("summary_lines") or [])
    if added:
        lines.append(tr("已生成临时图层：") + "、".join(added))
    host.log.setPlainText("\n".join(lines))


def close_line_dir():
    global _DIR_DLG
    dlg = _DIR_DLG
    _DIR_DLG = None
    if dlg is None:
        return
    try:
        dlg.close()
    except Exception:
        pass  # nosec B110
