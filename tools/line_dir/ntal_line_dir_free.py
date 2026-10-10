# -*- coding: utf-8 -*-
from ...i18n import tr
"""通用线方向：自选一个起点和多个线图层，端点在容差内才相接，断口停下。不读正式图层配置。"""
import heapq
import json
import math
from collections import defaultdict

from qgis.core import QgsProject, QgsSettings, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox
try:
    from qgis.core import QgsMapLayerProxyModel
except ImportError:
    from qgis.gui import QgsMapLayerProxyModel
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDoubleSpinBox,
    QPushButton,
    QVBoxLayout,
)

from .layer_groups import CategoryFilterDialog, LayerGroupTable, find_layer_by_name
from .ntal_engine import (
    _feature_label,
    _layer_crs,
    _point_xy,
    _transform_geom,
    _xform,
    add_issue_temp_layers,
    format_num,
    working_crs_from_layers,
    _add_temp_points,
)
from .ntal_legend import FeatureCategoryFilter, filter_is_narrow
from ..window_theme import register_tool_window, resolve_tool_parent
from .ntal_line_dir import LineDirDialog, _CheckProgress


def _user_role():
    try:
        return Qt.ItemDataRole.UserRole
    except AttributeError:
        return Qt.ItemDataRole.UserRole

_SETTINGS_KEY = "AttributeTablePlus/line_dir_free"
_SETUP_DLG = None


def _load_memory():
    raw = QgsSettings().value(_SETTINGS_KEY, "") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_memory(data):
    QgsSettings().setValue(_SETTINGS_KEY, json.dumps(data, ensure_ascii=False))


def _layer_by_memory(layer_id, layer_name):
    layer = None
    if layer_id:
        try:
            layer = QgsProject.instance().mapLayer(layer_id)
        except Exception:
            layer = None
    if layer is None and layer_name:
        layer = find_layer_by_name(layer_name)
    return layer


def _parts_of(geom):
    if geom is None or geom.isEmpty() or geom.type() != QgsWkbTypes.LineGeometry:
        return []
    if geom.isMultipart():
        parts = geom.asMultiPolyline() or []
    else:
        line = geom.asPolyline()
        parts = [line] if line else []
    out = []
    for part in parts:
        if part and len(part) >= 2:
            out.append(part)
    return out


def _part_length(part):
    total = 0.0
    for i in range(1, len(part)):
        total += math.hypot(part[i].x() - part[i - 1].x(), part[i].y() - part[i - 1].y())
    return total


class _UnionFind(object):
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, index):
        parent = self.parent
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(self, left, right):
        ra = self.find(left)
        rb = self.find(right)
        if ra != rb:
            self.parent[rb] = ra


def _cluster_ends(start_xy, edges, tolerance, terminal_xys=None):
    """起点、终点和每条线段的两端。距离不超过容差的端点合成一个节点。"""
    coords = [start_xy]
    term_indexes = []
    for xy in terminal_xys or []:
        term_indexes.append(len(coords))
        coords.append(xy)
    edge_base = len(coords)
    for edge in edges:
        coords.append(edge["start"])
        coords.append(edge["end"])
    count = len(coords)
    uf = _UnionFind(count)
    if tolerance > 0 and count > 1:
        cell = float(tolerance)
        buckets = defaultdict(list)
        for index, (x, y) in enumerate(coords):
            buckets[(int(math.floor(x / cell)), int(math.floor(y / cell)))].append(index)
        for index, (x, y) in enumerate(coords):
            cx = int(math.floor(x / cell))
            cy = int(math.floor(y / cell))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other in buckets.get((cx + dx, cy + dy), ()):
                        if other <= index:
                            continue
                        ox, oy = coords[other]
                        if math.hypot(x - ox, y - oy) <= tolerance:
                            uf.union(index, other)
    root = uf.find(0)
    has_line = False
    for i in range(edge_base, count):
        if uf.find(i) == root:
            has_line = True
            break
    terminals = set()
    for index in term_indexes:
        terminals.add(uf.find(index))
    ends = {}
    for edge_index, edge in enumerate(edges):
        a = uf.find(edge_base + edge_index * 2)
        b = uf.find(edge_base + edge_index * 2 + 1)
        ends[edge["id"]] = (a, b)
    return root, has_line, ends, terminals


def _reachable_without(root, banned, adj, end_nodes):
    seen = {root}
    stack = [root]
    banned = set(banned or [])
    while stack:
        node = stack.pop()
        for eid in adj.get(node, ()):
            if eid in banned:
                continue
            a, b = end_nodes[eid]
            if a == b:
                continue
            other = b if node == a else a
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return seen


def _pair_key(a, b):
    return (a, b) if a <= b else (b, a)


def _walk(root, edges, end_nodes, terminals=None):
    """从起点往外走。终点走到就停。同一对端点上的线要一起拿掉，两头仍走得到才是伪成环。"""
    edge_map = {edge["id"]: edge for edge in edges}
    terminals = set(terminals or [])
    adj = defaultdict(list)
    bundles = defaultdict(list)
    for edge in edges:
        a, b = end_nodes[edge["id"]]
        adj[a].append(edge["id"])
        if b != a:
            adj[b].append(edge["id"])
            bundles[_pair_key(a, b)].append(edge["id"])
    oriented = {}
    self_loops = []
    reached = {root}
    heap = [(0.0, root)]
    seen_nodes = set()
    chords = []
    while heap:
        dist, node = heapq.heappop(heap)
        if node in seen_nodes:
            continue
        seen_nodes.add(node)
        if node in terminals and node != root:
            continue
        for eid in adj.get(node, ()):
            a, b = end_nodes[eid]
            if a == b:
                if eid not in oriented:
                    oriented[eid] = (node, node)
                    self_loops.append(eid)
                continue
            if eid in oriented:
                continue
            other = b if node == a else a
            if other in reached and other in terminals:
                oriented[eid] = (node, other)
                continue
            if other in reached:
                chords.append(eid)
                continue
            oriented[eid] = (node, other)
            reached.add(other)
            edge = edge_map[eid]
            step = float(edge.get("length") or 0.0)
            if step <= 0:
                step = math.hypot(edge["start"][0] - edge["end"][0], edge["start"][1] - edge["end"][1])
            heapq.heappush(heap, (dist + step, other))
    pseudo = []
    decided = set()
    for eid in chords:
        a, b = end_nodes[eid]
        key = _pair_key(a, b)
        if key in decided:
            continue
        decided.add(key)
        bundle = bundles.get(key) or [eid]
        alive = _reachable_without(root, bundle, adj, end_nodes)
        if a in alive and b in alive:
            for item in bundle:
                if item not in oriented:
                    pseudo.append(item)
            continue
        upstream, downstream = (a, b) if a in alive else (b, a)
        for item in bundle:
            if item not in oriented:
                oriented[item] = (upstream, downstream)
    return oriented, self_loops, pseudo


def _collect_start_points(layer, flt, work_crs):
    rows = []
    if layer is None:
        return rows
    xform = _xform(_layer_crs(layer), work_crs)
    matcher = FeatureCategoryFilter(layer, flt, include_unchecked=True)
    narrow = filter_is_narrow(flt)
    try:
        for feat in layer.getFeatures():
            if not matcher.allow(feat):
                continue
            geom = feat.geometry()
            moved = _transform_geom(geom, xform)
            xy = _point_xy(moved)
            if xy is None:
                continue
            label = _feature_label(feat, layer.name(), tr("点"))
            rows.append({
                "id": "{}:{}".format(layer.id(), feat.id()),
                "role": "起点",
                "layer": layer,
                "layer_id": layer.id(),
                "layer_name": layer.name(),
                "cat_label": matcher.cat_label(feat) if narrow else "",
                "fid": feat.id(),
                "xy": xy,
                "src_xy": _point_xy(geom) or xy,
                "src_crs": _layer_crs(layer),
                "label": label,
            })
    finally:
        matcher.close()
    rows.sort(key=lambda row: (str(row.get("label") or ""), row["fid"]))
    return rows


def _collect_part_edges(layer, flt, work_crs):
    edges = []
    if layer is None:
        return edges
    xform = _xform(_layer_crs(layer), work_crs)
    matcher = FeatureCategoryFilter(layer, flt, include_unchecked=True)
    narrow = filter_is_narrow(flt)
    try:
        for feat in layer.getFeatures():
            if not matcher.allow(feat):
                continue
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            moved = _transform_geom(geom, xform)
            parts = _parts_of(moved)
            src_parts = _parts_of(geom)
            if not parts:
                continue
            base = _feature_label(feat, layer.name(), tr("线"))
            cat = matcher.cat_label(feat) if narrow else ""
            many = len(parts) > 1
            for index, part in enumerate(parts):
                src = src_parts[index] if index < len(src_parts) else part
                label = base if not many else tr("{} 段{}").format(base, index + 1)
                edges.append({
                    "id": "{}:{}:{}".format(layer.id(), feat.id(), index),
                    "role": "线",
                    "layer": layer,
                    "layer_id": layer.id(),
                    "layer_name": layer.name(),
                    "cat_label": cat,
                    "fid": feat.id(),
                    "part": index,
                    "part_count": len(parts),
                    "start": (part[0].x(), part[0].y()),
                    "end": (part[-1].x(), part[-1].y()),
                    "src_start": (src[0].x(), src[0].y()),
                    "src_end": (src[-1].x(), src[-1].y()),
                    "src_crs": _layer_crs(layer),
                    "length": _part_length(part),
                    "multipart": many,
                    "label": label,
                })
    finally:
        matcher.close()
    return edges


def run_free_line_dir(point_layer, point_filter, point_fid, line_pairs, tolerance, progress=None, terminal_pairs=None):
    errors = []
    pairs = []
    seen_layers = set()
    for layer, flt in line_pairs or []:
        if layer is None or layer.id() in seen_layers:
            continue
        seen_layers.add(layer.id())
        pairs.append((layer, flt))
    if point_layer is None:
        errors.append(tr("请选择点图层。"))
    if not pairs:
        errors.append(tr("请至少增加一个线图层。"))
    if point_fid is None:
        errors.append(tr("请在列表里点一个起点。"))
    if float(tolerance or 0) <= 0:
        errors.append(tr("吸附容差必须大于 0。请先在参数配置里设置。"))
    if errors:
        return {"ok": False, "kind": "line_dir_free", "config_errors": errors}

    work_crs = working_crs_from_layers([point_layer] + [layer for layer, _flt in pairs])
    if progress is not None:
        progress.report(0.05, tr("正在读取起点"), force=True)
    points = _collect_start_points(point_layer, point_filter, work_crs)
    start = None
    for row in points:
        if row["fid"] == point_fid:
            start = row
            break
    if start is None:
        return {"ok": False, "kind": "line_dir_free", "config_errors": [tr("筛选后的点里没有这个起点。")]}
    if progress is not None:
        progress.report(0.2, tr("正在读取线"), force=True)
    edges = []
    for layer, flt in pairs:
        edges.extend(_collect_part_edges(layer, flt, work_crs))
    if not edges:
        return {"ok": False, "kind": "line_dir_free", "config_errors": [tr("线图层筛选后没有可用的线。")]}

    if progress is not None:
        progress.report(0.55, tr("正在连接端点"), force=True)
    terminals_pts = []
    seen_term = set()
    for layer, flt in terminal_pairs or []:
        if layer is None or layer.id() in seen_term:
            continue
        seen_term.add(layer.id())
        terminals_pts.extend(_collect_start_points(layer, flt, work_crs))
    root, has_line, end_nodes, terminals = _cluster_ends(
        start["xy"], edges, float(tolerance), [row["xy"] for row in terminals_pts]
    )
    if not has_line:
        return {
            "ok": False,
            "kind": "line_dir_free",
            "config_errors": [tr("起点容差 {} 米内没有线的端点。缝更大的地方不会跨过去。").format(format_num(tolerance))],
        }

    if progress is not None:
        progress.report(0.7, tr("正在沿起点往外走"), force=True)
    oriented, self_loops, pseudo = _walk(root, edges, end_nodes, terminals)
    edge_map = {edge["id"]: edge for edge in edges}
    hard = []
    warn = []
    reversible_parts = []
    ok_count = 0
    tree = [
        tr("从所选起点往外走。线的两端在容差内才算接到同一个点，缝更大就停下。"),
        tr("容差 {} 米。起点 {}。").format(format_num(tolerance), start["label"]),
    ]
    loop_ids = set(self_loops)
    pseudo_ids = set(pseudo)
    for eid in loop_ids:
        edge = edge_map[eid]
        hard.append({
            "kind": "self_loop",
            "message": tr("两端接到同一点：{}").format(edge["label"]),
            "refs": [("edge", eid), ("node", start["id"])],
        })
        tree.append(tr("  自环  {}").format(edge["label"]))
    end_mark_edges = []
    for edge in edges:
        eid = edge["id"]
        if eid in loop_ids:
            continue
        if eid in pseudo_ids:
            warn.append({
                "kind": "pseudo_cycle",
                "message": tr("伪成环：这条线两边的接头，不靠它也能从起点走到，方向定不下来，不翻转：{}").format(edge["label"]),
                "refs": [("edge", eid)],
            })
            tree.append(tr("  伪成环  {}").format(edge["label"]))
            end_mark_edges.append(edge)
            edge["mark_seq"] = len(end_mark_edges)
            continue
        pair = oriented.get(eid)
        if pair is None:
            warn.append({
                "kind": "unreached_edge",
                "message": tr("未从起点走到（中间断开，不跨缝）：{}").format(edge["label"]),
                "refs": [("edge", eid)],
            })
            tree.append(tr("  未走到  {}").format(edge["label"]))
            continue
        upstream, downstream = pair
        a, b = end_nodes[eid]
        if upstream == a:
            ok_count += 1
            tree.append(tr("  正向  {}").format(edge["label"]))
            continue
        if upstream == b:
            msg = tr("数字化方向反了（终点在上游）：{}").format(edge["label"])
            if edge.get("multipart"):
                msg += tr("。多段线要各段都反了才整条翻转。")
            warn.append({
                "kind": "line_reversed",
                "message": msg,
                "refs": [("edge", eid), ("node", start["id"])],
            })
            reversible_parts.append(edge)
            end_mark_edges.append(edge)
            edge["mark_seq"] = len(end_mark_edges)
            tree.append(tr("  反了  {}").format(edge["label"]))

    by_fid = defaultdict(list)
    for edge in edges:
        by_fid[(edge["layer_id"], edge["fid"])].append(edge)
    reversible = []
    for key, parts in by_fid.items():
        active = [edge for edge in parts if edge["id"] not in loop_ids]
        if active and all(edge["id"] in pseudo_ids for edge in active):
            first = active[0]
            label = _mark_name(active) or (first["label"] if not first.get("multipart") else _feature_label_from_edge(first))
            reversible.append({
                "id": first["id"],
                "layer": first["layer"],
                "layer_name": first["layer_name"],
                "fid": first["fid"],
                "role": "线",
                "issue": "pseudo_cycle",
                "type_label": "伪成环",
                "label": label,
                "multipart": bool(first.get("multipart")),
                "message": "伪成环：两边不靠这条线也能从起点走到。默认不勾，打勾才对调两端。",
            })
            continue
        rev_parts = [edge for edge in parts if edge in reversible_parts]
        if not rev_parts:
            continue
        reached = [edge for edge in parts if edge["id"] in oriented and edge["id"] not in loop_ids]
        all_rev = len(rev_parts) == len(parts) and len(reached) == len(parts)
        sample = parts[0]
        if not all_rev:
            hard.append({
                "kind": "dir_conflict",
                "message": tr("多段线没有全部走到或各段方向不一致，不整条翻转：{}").format(
                    _feature_label_from_edge(sample)
                ),
                "refs": [("edge", rev_parts[0]["id"])],
            })
            continue
        first = parts[0]
        msg = tr("数字化方向反了：{}").format(first["label"] if not first.get("multipart") else _feature_label_from_edge(first))
        reversible.append({
            "id": first["id"],
            "layer": first["layer"],
            "layer_name": first["layer_name"],
            "fid": first["fid"],
            "role": "线",
            "issue": "line_reversed",
            "type_label": "方向反了",
            "label": _mark_name(parts) or (first["label"] if not first.get("multipart") else _feature_label_from_edge(first)),
            "multipart": bool(first.get("multipart")),
            "message": msg,
        })

    rev_n = sum(1 for row in reversible if row.get("issue") == "line_reversed")
    suggestions = [
        tr("方向反了 {} 条：可修复里默认打勾，用「翻转勾选」。伪成环也在表里，默认不勾。").format(rev_n),
        tr("修复只改线的顶点顺序，不改属性；写入编辑缓冲，需要你自己保存图层。"),
        tr("端点距离大于容差就停下，不会把断开的下一段接上。"),
    ]
    if self_loops:
        suggestions.append(tr("自环 {} 处：线两端落在同一个点上，不翻转。").format(len(self_loops)))
    if pseudo_ids:
        suggestions.append(
            tr("伪成环 {} 段：可修复里默认不勾。要翻就打勾。").format(len(pseudo_ids))
        )
    unreached = sum(1 for item in warn if item.get("kind") == "unreached_edge")
    if unreached:
        suggestions.append(tr("未走到 {} 段：和起点这条链中间断开了，这些段不翻。").format(unreached))
    if not rev_n and not hard and not unreached and not pseudo_ids:
        suggestions.append(tr("从起点走到的线方向都正确。"))

    node_map = {start["id"]: start}
    for edge in edges:
        edge["a"], edge["b"] = end_nodes[edge["id"]]
    summary_lines = [
        tr("起点 {}。线 {} 段（要素按段走，多段线各段分开接）。").format(start["label"], len(edges)),
        tr("走到 {} 段，方向正确 {} 段，方向反了 {} 条要素，伪成环 {} 段。").format(
            len(oriented) - len(loop_ids), ok_count, rev_n, len(pseudo_ids)
        ),
        tr("风险：硬错误 {}，软错误 {}（含方向反了）。").format(len(hard), len(warn)),
        tr("分叉会每条都走。断口大于容差 {} 米就停。").format(format_num(tolerance)),
        tr("建议："),
    ]
    summary_lines.extend("  · " + item for item in suggestions)
    participation = [
        {
            "role": "起点",
            "layer_name": point_layer.name(),
            "used": 1,
            "extracted": len(points),
            "ok": True,
        },
    ]
    for layer, _flt in pairs:
        layer_edges = [edge for edge in edges if edge.get("layer_id") == layer.id()]
        participation.append({
            "role": "线",
            "layer_name": layer.name(),
            "used": sum(1 for edge in layer_edges if edge["id"] in oriented),
            "extracted": len(layer_edges),
            "ok": True,
        })
    return {
        "ok": True,
        "kind": "line_dir_free",
        "tolerance": float(tolerance),
        "hard": hard,
        "warn": warn,
        "nodes": node_map,
        "edges": edge_map,
        "work_crs": work_crs,
        "reversible": reversible,
        "ok_count": ok_count,
        "oriented_count": len(oriented),
        "edge_total": len(edges),
        "participation": participation,
        "tree_text": "\n".join(tree),
        "summary_lines": summary_lines,
        "suggestions": suggestions,
        "source_label": "通用线方向",
        "writes": [],
        "end_mark_edges": end_mark_edges,
    }


def _mark_name(parts):
    names = []
    for edge in parts or []:
        seq = edge.get("mark_seq")
        if not seq:
            continue
        text = tr("起点{}").format(seq)
        if text not in names:
            names.append(text)
    return "、".join(names)


def _feature_label_from_edge(edge):
    text = edge.get("label") or ""
    if " 段" in text:
        return text.rsplit(tr(" 段"), 1)[0]
    return text


def _filter_caption(flt):
    if not flt:
        return "全部"
    labels = flt.get("labels") or flt.get("keys") or []
    if not labels:
        return "无"
    if len(labels) <= 2:
        return ",".join(str(item) for item in labels)
    return tr("{}类").format(len(labels))


class FreeLineDirSetup(QDialog):
    def __init__(self, host, parent=None):
        super(FreeLineDirSetup, self).__init__(parent)
        self.host = host
        self.setWindowTitle(tr("线方向检查"))
        self.setMinimumWidth(640)
        self.resize(760, 560)
        self._point_filter = None
        self._memory = _load_memory()
        root = QVBoxLayout(self)
        hint = QLabel(
            tr('起点只用一个点。线在左，终点在右，都可以加多条并各自筛选分类。终点可以不选。走到终点就停。不选终点时，拿掉某条线后若有一头从起点走不到，就不叫伪成环。')
        )
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.tol_label = QLabel(
            tr("端点按容差链式合并：A 靠近 B、B 靠近 C 时，三个端点算同一个点，即使 A 和 C 相距超过容差。端点很密的地方要留意。")
        )
        self.tol_label.setWordWrap(True)
        root.addWidget(self.tol_label)
        tol_row = QHBoxLayout()
        tol_row.addWidget(QLabel(tr("吸附容差（米）")))
        self.tol_spin = QDoubleSpinBox()
        self.tol_spin.setRange(0.01, 1000.0)
        self.tol_spin.setDecimals(2)
        self.tol_spin.setSingleStep(0.1)
        self.tol_spin.setValue(float(host.tolerance or 0.6))

        def _on_tol(value):
            host.tolerance = float(value)
            try:
                QgsSettings().setValue("AttributeTablePlus/line_dir_tolerance", float(value))
            except Exception:
                pass  # nosec B110

        self.tol_spin.valueChanged.connect(_on_tol)
        tol_row.addWidget(self.tol_spin)
        tol_row.addStretch()
        root.addLayout(tol_row)

        point_row = QHBoxLayout()
        point_row.addWidget(QLabel(tr("起点图层")))
        self.point_combo = QgsMapLayerComboBox()
        self.point_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.btn_point_filter = QPushButton(tr("全部"))
        self.btn_point_filter.setToolTip(tr("按分类筛选。图例未勾选的分类也会列出来，勾上即可参与。"))
        point_row.addWidget(self.point_combo, 1)
        point_row.addWidget(self.btn_point_filter)
        root.addLayout(point_row)

        self.line_table = LayerGroupTable(
            tr("线"), "line", "", False, "━", "#2e7d32",
            hide_primary=True,
            include_unchecked=True,
            group_tip=tr("可增加多个线图层。每条线各自按分类筛选。"),
        )
        self.end_table = LayerGroupTable(
            tr("终点"), "point", "", False, "●", "#c62828",
            hide_primary=True,
            include_unchecked=True,
            group_tip=tr("可选。可增加多个终点图层，每条各自筛选分类。走到终点就停。"),
        )
        tables = QHBoxLayout()
        tables.addWidget(self.line_table, 1)
        tables.addWidget(self.end_table, 1)
        root.addLayout(tables, 1)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(tr("起点（筛选后的点，点一个）")))
        self.point_search = QLineEdit()
        self.point_search.setPlaceholderText(tr("搜索名称或 FID"))
        self.point_search.setClearButtonEnabled(True)
        self.point_search.textChanged.connect(self._apply_point_search)
        search_row.addWidget(self.point_search, 1)
        root.addLayout(search_row)
        self.point_list = QListWidget()
        self.point_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        root.addWidget(self.point_list, 1)

        try:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("开始"))
        except AttributeError:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("开始"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.point_combo.layerChanged.connect(self._on_point_layer)
        self.btn_point_filter.clicked.connect(self._edit_point_filter)
        self._restore()
        register_tool_window(self)

    def _line_rows_from_memory(self, memory):
        rows = memory.get("line_rows")
        if isinstance(rows, list) and rows:
            return rows
        name = memory.get("line_layer_name") or ""
        flt = memory.get("line_filter") if isinstance(memory.get("line_filter"), dict) else None
        if name:
            item = {"layer": name}
            if flt:
                item["filter"] = flt
            return [item]
        return []

    def _restore(self):
        memory = self._memory
        point = _layer_by_memory(memory.get("point_layer_id"), memory.get("point_layer_name"))
        if point is not None:
            self.point_combo.setLayer(point)
        self._point_filter = memory.get("point_filter") if isinstance(memory.get("point_filter"), dict) else None
        self.btn_point_filter.setText(_filter_caption(self._point_filter))
        self.line_table.set_group({"rows": self._line_rows_from_memory(memory)})
        self.end_table.set_group({"rows": memory.get("end_rows") if isinstance(memory.get("end_rows"), list) else []})
        self._reload_points()

    def _on_point_layer(self, _layer):
        self._point_filter = None
        self.btn_point_filter.setText(_filter_caption(self._point_filter))
        self._reload_points()

    def _edit_filter(self, layer, current):
        if layer is None:
            QMessageBox.information(self, tr("通用线方向"), tr("请先选择图层。"))
            return current
        dlg = CategoryFilterDialog(
            layer,
            current_filter=current,
            parent=self,
            include_unchecked=True,
        )
        accepted = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
        if not accepted:
            return current
        return dlg.result_filter()

    def _edit_point_filter(self):
        self._point_filter = self._edit_filter(self.point_combo.currentLayer(), self._point_filter)
        self.btn_point_filter.setText(_filter_caption(self._point_filter))
        self._reload_points()

    def _line_pairs(self):
        pairs = []
        seen = set()
        for item in (self.line_table.get_group().get("rows") or []):
            layer = find_layer_by_name(item.get("layer"))
            if layer is None or layer.id() in seen:
                continue
            seen.add(layer.id())
            pairs.append((layer, item.get("filter")))
        return pairs

    def _end_pairs(self):
        pairs = []
        seen = set()
        for item in (self.end_table.get_group().get("rows") or []):
            layer = find_layer_by_name(item.get("layer"))
            if layer is None or layer.id() in seen:
                continue
            seen.add(layer.id())
            pairs.append((layer, item.get("filter")))
        return pairs

    def _reload_points(self):
        self.point_list.clear()
        layer = self.point_combo.currentLayer()
        if layer is None:
            return
        work_crs = working_crs_from_layers([layer] + [item[0] for item in self._line_pairs()])
        rows = _collect_start_points(layer, self._point_filter, work_crs)
        for row in rows:
            item = QListWidgetItem("{}    #{}".format(row["label"], row["fid"]))
            item.setData(_user_role(), row["fid"])
            self.point_list.addItem(item)
        if self.point_list.count() == 1:
            self.point_list.setCurrentRow(0)
        self._apply_point_search()

    def _apply_point_search(self, _text=None):
        needle = (self.point_search.text() or "").strip().lower()
        for i in range(self.point_list.count()):
            item = self.point_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _selected_fid(self):
        item = self.point_list.currentItem()
        if item is None:
            return None
        return item.data(_user_role())

    def _accept(self):
        pairs = self._line_pairs()
        if self.point_combo.currentLayer() is None or not pairs:
            QMessageBox.warning(self, tr("通用线方向"), tr("请选择点图层，并至少增加一个线图层。"))
            return
        if self._selected_fid() is None:
            QMessageBox.warning(self, tr("通用线方向"), tr("请在列表里点一个起点。"))
            return
        point = self.point_combo.currentLayer()
        _save_memory({
            "point_layer_id": point.id(),
            "point_layer_name": point.name(),
            "point_filter": self._point_filter,
            "line_rows": self.line_table.get_group().get("rows") or [],
            "end_rows": self.end_table.get_group().get("rows") or [],
        })
        self.accept()

    def values(self):
        return {
            "point_layer": self.point_combo.currentLayer(),
            "point_filter": self._point_filter,
            "line_pairs": self._line_pairs(),
            "terminal_pairs": self._end_pairs(),
            "point_fid": self._selected_fid(),
        }


def _add_end_marks(result):
    marks = []
    for edge in result.get("end_mark_edges") or []:
        seq = edge.get("mark_seq")
        if not seq:
            continue
        label = edge.get("label") or ""
        marks.append({
            "xy": edge.get("start"),
            "src": edge.get("src_start"),
            "crs": edge.get("src_crs"),
            "kind": "起点",
            "seq": seq,
            "full": tr("起点{} {}").format(seq, label),
        })
        marks.append({
            "xy": edge.get("end"),
            "src": edge.get("src_end"),
            "crs": edge.get("src_crs"),
            "kind": "终点",
            "seq": seq,
            "full": tr("终点{} {}").format(seq, label),
        })
    tolerance = float(result.get("tolerance") or 0.0)
    groups = []
    for mark in marks:
        xy = mark.get("xy")
        if not xy:
            continue
        placed = None
        for group in groups:
            gx, gy = group[0]["xy"]
            if math.hypot(xy[0] - gx, xy[1] - gy) <= max(tolerance, 1e-6):
                placed = group
                break
        if placed is None:
            groups.append([mark])
        else:
            placed.append(mark)
    rows = []
    for group in groups:
        short = "、".join("{}{}".format(item["kind"], item["seq"]) for item in group)
        detail = "\n".join(item["full"] for item in group)
        sample = group[0]
        rows.append({
            "xy": sample.get("src") or sample.get("xy"),
            "crs": sample.get("crs"),
            "label": short,
            "detail": detail,
        })
    layer = _add_temp_points(
        tr("通用线方向_起点终点"),
        rows,
        "#6a1b9a",
        [("label", QVariant.String), ("detail", QVariant.String)],
        fallback_crs=result.get("work_crs"),
        checked=False,
        source=tr("通用线方向"),
    )
    if layer is None:
        return []
    return [layer.name()]


def open_free_line_dir(host):
    global _SETUP_DLG
    parent = resolve_tool_parent(host)
    setup = FreeLineDirSetup(host, parent)
    _SETUP_DLG = setup
    accepted = setup.exec() if hasattr(setup, "exec") else setup.exec_()
    _SETUP_DLG = None
    if not accepted:
        return
    picked = setup.values()
    progress = _CheckProgress(parent)
    try:
        progress.dlg.setWindowTitle(tr("线方向检查"))
    except Exception:
        pass
    try:
        result = run_free_line_dir(
            picked["point_layer"],
            picked["point_filter"],
            picked["point_fid"],
            picked["line_pairs"],
            host.tolerance,
            progress=progress,
            terminal_pairs=picked.get("terminal_pairs"),
        )
        if not result.get("ok"):
            QMessageBox.warning(
                host,
                tr("通用线方向"),
                "\n".join(result.get("config_errors") or [tr("无法开始")]),
            )
            host.log.setPlainText("\n".join(result.get("config_errors") or []))
            return
        progress.report(0.97, tr("正在生成临时图层"), force=True)
        added = add_issue_temp_layers(
            [result], visible_kinds=("line_reversed",)
        )
        added.extend(_add_end_marks(result))
    finally:
        progress.close()
    from . import ntal_line_dir as line_dir_mod
    old = line_dir_mod._DIR_DLG
    line_dir_mod._DIR_DLG = None
    if old is not None:
        try:
            old.close()
        except Exception:
            pass
    dlg = LineDirDialog(result, host, added=added, parent=parent)
    dlg.setWindowTitle(tr("线方向检查"))
    line_dir_mod._DIR_DLG = dlg
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    lines = list(result.get("summary_lines") or [])
    if added:
        lines.append(tr("已生成临时图层：") + "、".join(added))
    host.log.setPlainText("\n".join(lines))


def close_free_line_dir():
    global _SETUP_DLG
    dlg = _SETUP_DLG
    _SETUP_DLG = None
    if dlg is None:
        return
    try:
        dlg.close()
    except Exception:
        pass
