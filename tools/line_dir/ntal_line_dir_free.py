# -*- coding: utf-8 -*-
from ...i18n import language_changed, tr
from ...qt_compat import run_exec
"""通用线方向：自选一个起点和多个线图层，端点在容差内才相接，断口停下。不读正式图层配置。"""
import json
import math
from collections import defaultdict

from qgis.core import QgsProject, QgsSettings, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox
try:
    from qgis.core import QgsMapLayerProxyModel
except ImportError:
    from qgis.gui import QgsMapLayerProxyModel
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
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
from .ntal_walk import _walk


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
    if geom is None or geom.isEmpty() or geom.type() != QgsWkbTypes.GeometryType.LineGeometry:
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


def _cluster_ends(start_xys, edges, tolerance, terminal_xys=None):
    """起点（可多个）、终点和每条线段的两端。距离不超过容差的端点合成一个节点。

    返回 (roots, used_roots, ends, terminals)：
    roots 是全部起点所在节点的集合；used_roots 是其中真的接到线端点的节点。
    """
    coords = [tuple(xy) for xy in (start_xys or [])]
    start_count = len(coords)
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
    roots = set(uf.find(i) for i in range(start_count))
    used_roots = set()
    for i in range(edge_base, count):
        cluster = uf.find(i)
        if cluster in roots:
            used_roots.add(cluster)
    terminals = set()
    for index in term_indexes:
        terminals.add(uf.find(index))
    ends = {}
    for edge_index, edge in enumerate(edges):
        a = uf.find(edge_base + edge_index * 2)
        b = uf.find(edge_base + edge_index * 2 + 1)
        ends[edge["id"]] = (a, b)
    return roots, used_roots, ends, terminals


def _dist_point_seg(px, py, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    len2 = dx * dx + dy * dy
    if len2 <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / len2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _interior_terminal_edges(edges, terminal_xys, tolerance):
    """终点贴在线的中间、但没贴到这条线任一端点。

    这种终点不在两根线的接头上，不能把环断开。
    """
    tol = float(tolerance or 0)
    points = [xy for xy in (terminal_xys or []) if xy]
    if tol <= 0 or not points:
        return set()
    hits = set()
    for edge in edges:
        verts = edge.get("verts") or (edge.get("start"), edge.get("end"))
        if not verts or len(verts) < 2:
            continue
        ax0, ay0 = verts[0]
        bx0, by0 = verts[-1]
        for tx, ty in points:
            if math.hypot(tx - ax0, ty - ay0) <= tol or math.hypot(tx - bx0, ty - by0) <= tol:
                continue
            for index in range(len(verts) - 1):
                ax, ay = verts[index]
                bx, by = verts[index + 1]
                if _dist_point_seg(tx, ty, ax, ay, bx, by) <= tol:
                    hits.add(edge["id"])
                    break
            else:
                continue
            break
    return hits


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
                    "verts": [(pt.x(), pt.y()) for pt in part],
                    "multipart": many,
                    "label": label,
                })
    finally:
        matcher.close()
    return edges


def run_free_line_dir(point_layer, point_filter, line_pairs, tolerance, progress=None, terminal_pairs=None):
    """全部起点（起点图层分类筛选后的所有点）同时作为根往外走。

    参考拓扑预览的组网规则：不挑起点，图层里筛选后剩几个点，就同时从几个点出发；
    一条线的方向由先走到它的那个起点决定（离线近的先算）。
    """
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
    if float(tolerance or 0) <= 0:
        errors.append(tr("吸附容差必须大于 0。请先在参数配置里设置。"))
    if errors:
        return {"ok": False, "kind": "line_dir_free", "config_errors": errors}

    work_crs = working_crs_from_layers([point_layer] + [layer for layer, _flt in pairs])
    if progress is not None:
        progress.report(0.05, tr("正在读取起点"), force=True)
    points = _collect_start_points(point_layer, point_filter, work_crs)
    if not points:
        return {"ok": False, "kind": "line_dir_free", "config_errors": [tr("筛选后的起点图层里没有点。")]}
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
    roots, used_roots, end_nodes, terminals = _cluster_ends(
        [row["xy"] for row in points], edges, float(tolerance),
        [row["xy"] for row in terminals_pts],
    )
    if not used_roots:
        return {
            "ok": False,
            "kind": "line_dir_free",
            "config_errors": [tr("全部起点在容差 {} 米内都没接到线的端点。缝更大的地方不会跨过去。").format(format_num(tolerance))],
        }

    if progress is not None:
        progress.report(0.7, tr("正在沿起点往外走"), force=True)
    interior = _interior_terminal_edges(
        edges, [row["xy"] for row in terminals_pts], float(tolerance)
    )
    oriented, self_loops, pseudo, cut_ends, ambiguous = _walk(
        roots, edges, end_nodes, terminals, interior
    )
    edge_map = {edge["id"]: edge for edge in edges}
    hard = []
    warn = []
    reversible_parts = []
    ok_count = 0
    tree = [
        tr("从起点图层的全部点同时往外走，离线近的起点先算。线的两端在容差内才算接到同一个点，缝更大就停下。"),
        tr("每个线端点是一个连接点：从一个点分出几条线，每条都顺着往外走，分叉不算错误。"),
        tr("容差 {} 米。起点 {} 个（分类筛选后），接上线 {} 个。").format(
            format_num(tolerance), len(points), len(used_roots)
        ),
    ]
    end_total = len(set(terminals) - set(roots))
    if end_total:
        tree.append(tr("终点 {} 处，其中 {} 处在环上，把环在那里断开；其余不在环上，不起作用。").format(
            end_total, len(cut_ends)
        ))
    loop_ids = set(self_loops)
    pseudo_ids = set(pseudo)
    amb_ids = set(ambiguous)
    # Unreached is the only hard error. A ring whose direction cannot be
    # settled is not "fine": it is written to a temporary layer.
    hard = []
    for eid in loop_ids:
        edge = edge_map[eid]
        tree.append(tr("  自环  {}").format(edge["label"]))
    end_mark_edges = []
    for edge in edges:
        eid = edge["id"]
        if eid in loop_ids:
            continue
        if eid in amb_ids:
            tree.append(tr("  方向无法判断  {}").format(edge["label"]))
            warn.append({
                "kind": "dir_ambiguous",
                "message": tr("方向无法判断：环上有多个终点，或终点不在接头上，无法确定该在哪一处断开。已写入临时图层。"),
                "refs": [("edge", eid)],
            })
            continue
        if eid in pseudo_ids:
            tree.append(tr("  伪成环  {}").format(edge["label"]))
            warn.append({
                "kind": "pseudo_cycle",
                "message": tr("伪成环：两边不靠这条线也能从起点走到，分不出方向。已写入临时图层。"),
                "refs": [("edge", eid)],
            })
            continue
        pair = oriented.get(eid)
        if pair is None:
            # The only error left: unreachable from every start.
            warn.append({
                "kind": "unreached_edge",
                "message": tr("未从任何起点走到：{}").format(edge["label"]),
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
        if active and all(edge["id"] in amb_ids for edge in active):
            first = active[0]
            reversible.append({
                "id": first["id"],
                "layer": first["layer"],
                "layer_name": first["layer_name"],
                "fid": first["fid"],
                "role": "线",
                "issue": "dir_ambiguous",
                "type_label": tr("方向无法判断"),
                "label": first["label"] if not first.get("multipart") else _feature_label_from_edge(first),
                "multipart": bool(first.get("multipart")),
                "message": tr("方向无法判断：环上有多个终点，或终点不在接头上，无法确定该在哪一处断开。已写入临时图层。默认不勾。"),
            })
            continue
        if active and all(edge["id"] in pseudo_ids for edge in active):
            first = active[0]
            label = _mark_name(active) or (
                first["label"] if not first.get("multipart") else _feature_label_from_edge(first)
            )
            reversible.append({
                "id": first["id"],
                "layer": first["layer"],
                "layer_name": first["layer_name"],
                "fid": first["fid"],
                "role": "线",
                "issue": "pseudo_cycle",
                "type_label": tr("伪成环"),
                "label": label,
                "multipart": bool(first.get("multipart")),
                "message": tr("伪成环：两边不靠这条线也能从起点走到，分不出方向。已写入临时图层。默认不勾，打勾才对调两端。"),
            })
            continue
        rev_parts = [edge for edge in parts if edge in reversible_parts]
        if not rev_parts:
            continue
        reached = [edge for edge in parts if edge["id"] in oriented and edge["id"] not in loop_ids]
        all_rev = len(rev_parts) == len(parts) and len(reached) == len(parts)
        sample = parts[0]
        if not all_rev:
            # Not an error either — the feature just cannot be flipped as a whole.
            tree.append(tr("  各段未全走到或方向不一致，不整条翻转  {}").format(
                _feature_label_from_edge(sample)
            ))
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
            "label": _mark_name(parts) or (
                first["label"] if not first.get("multipart") else _feature_label_from_edge(first)
            ),
            "multipart": bool(first.get("multipart")),
            "message": msg,
        })

    rev_n = sum(1 for row in reversible if row.get("issue") == "line_reversed")
    unreached = sum(1 for item in warn if item.get("kind") == "unreached_edge")
    suggestions = [
        tr("方向反了 {} 条：可修复里默认打勾，用「翻转勾选」。伪成环也在表里，默认不勾。").format(rev_n),
        tr("修复只改线的顶点顺序，不改属性；写入编辑缓冲，需要你自己保存图层。"),
        tr("线走到头断掉是正常现象，不算错误。"),
    ]
    if unreached:
        suggestions.append(
            tr("未走到 {} 段：无法从任何起点到达，这是唯一的错误。").format(unreached)
        )
    if not unreached and not pseudo_ids and not amb_ids:
        suggestions.append(tr("所选线图层没有错误：每一段都能从起点走到。"))
    if pseudo_ids:
        suggestions.append(
            tr("伪成环 {} 段：环上没有终点，两头都能走到，分不出方向。已写入临时图层。环上只放一个终点、并且落在线的接头上，再检查一次才能定方向。").format(
                len(pseudo_ids)
            )
        )
    if amb_ids:
        suggestions.append(
            tr("方向无法判断 {} 段：环上的终点不能唯一断开这个环。已写入临时图层，请在地图上查看。").format(
                len(amb_ids)
            )
        )
    if not rev_n and not unreached and not pseudo_ids and not amb_ids:
        suggestions.append(tr("从起点走到的线方向都正确。"))

    node_map = {row["id"]: row for row in points}
    for edge in edges:
        edge["a"], edge["b"] = end_nodes[edge["id"]]
    summary_lines = [
        tr("起点 {} 个（分类筛选后），接上线 {} 个。线 {} 段（要素按段走，多段线各段分开接）。").format(
            len(points), len(used_roots), len(edges)
        ),
        tr("走到 {} 段，方向正确 {} 段，方向反了 {} 条要素，伪成环 {} 段。").format(
            len(oriented) - len(loop_ids), ok_count, rev_n, len(pseudo_ids)
        ),
        tr("错误（唯一一类）：未从任何起点走到 {} 段。").format(unreached),
        tr("分叉会每条都走。断口大于容差 {} 米就停。").format(format_num(tolerance)),
    ]
    if end_total:
        summary_lines.append(
            tr("终点 {} 处，其中 {} 处在环上，把环在那里断开；其余不在环上，不起作用。").format(
                end_total, len(cut_ends)
            )
        )
    summary_lines += [
        tr("建议："),
    ]
    summary_lines.extend("  · " + item for item in suggestions)
    participation = [
        {
            "role": "起点",
            "layer_name": point_layer.name(),
            "used": len(used_roots),
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
        "source_label": tr("通用线方向"),
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
        return tr("全部")
    labels = flt.get("labels") or flt.get("keys") or []
    if not labels:
        return tr("无")
    if len(labels) <= 2:
        return ",".join(str(item) for item in labels)
    return tr("{}类").format(len(labels))


def _hint_text():
    return tr(
        "起点是起点图层筛选后的全部点，不用挑：有几个点就同时从几个点出发，离线近的先算。"
        "线在左，终点在右，都可以加多条并各自筛选分类。终点可以不选。"
        "每个线端点是一个连接点：从一个点分出多条线时，每条都顺着往外走，分叉不算错误。"
        "终点只在线成环的地方起作用：环在终点处断开，两边的线各自朝终点走；不成环的地方放了终点也不起作用。"
        "环上没有终点时，两头碰面的那条线分不出方向，叫伪成环，并写入临时图层。"
        "环上有多个终点，或终点落在线的中间而不是接头上，也无法判断该在哪一处断开，这些线同样写入临时图层，不会当成方向正确。"
    )


def _end_tip():
    return tr("可选。可增加多个终点图层，每条各自筛选分类。终点只在成环、并且能唯一断开时起作用：环上正好一个终点，并且落在线的接头上，环就在那里断开。不成环的地方放了也不起作用。没有唯一断开处时，方向无法判断的线会写入临时图层。")


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
        hint = QLabel(_hint_text())
        hint.setWordWrap(True)
        self.hint = hint
        root.addWidget(hint)
        self.tol_label = QLabel(
            tr("端点按容差链式合并：A 靠近 B、B 靠近 C 时，三个端点算同一个点，即使 A 和 C 相距超过容差。端点很密的地方要留意。")
        )
        self.tol_label.setWordWrap(True)
        root.addWidget(self.tol_label)
        tol_row = QHBoxLayout()
        self.lbl_tol_caption = QLabel(tr("吸附容差（米）"))
        tol_row.addWidget(self.lbl_tol_caption)
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
        self.lbl_point = QLabel(tr("起点图层"))
        point_row.addWidget(self.lbl_point)
        self.point_combo = QgsMapLayerComboBox()
        self.point_combo.setFilters(QgsMapLayerProxyModel.Filter.PointLayer)
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
            group_tip=_end_tip(),
        )
        tables = QHBoxLayout()
        tables.addWidget(self.line_table, 1)
        tables.addWidget(self.end_table, 1)
        root.addLayout(tables, 1)

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
        self._buttons = buttons
        row = QHBoxLayout()
        self.btn_save = QPushButton(tr("保存"))
        self.btn_save.setAutoDefault(False)
        self.btn_save.setToolTip(tr("保存当前选择的起点、线和终点图层。只有点这里，下次打开才会恢复这些图层。"))
        self.btn_save.clicked.connect(self._save_layers)
        row.addWidget(self.btn_save)
        row.addStretch(1)
        row.addWidget(buttons)
        root.addLayout(row)

        self.point_combo.layerChanged.connect(self._on_point_layer)
        self.btn_point_filter.clicked.connect(self._edit_point_filter)
        self._restore()
        try:
            language_changed().connect(self._apply_language)
        except Exception:
            pass  # nosec B110
        register_tool_window(self)

    def _apply_language(self, *_args):
        self.setWindowTitle(tr("线方向检查"))
        self.hint.setText(_hint_text())
        self.tol_label.setText(tr(
            "端点按容差链式合并：A 靠近 B、B 靠近 C 时，三个端点算同一个点，即使 A 和 C 相距超过容差。端点很密的地方要留意。"
        ))
        self.lbl_tol_caption.setText(tr("吸附容差（米）"))
        self.lbl_point.setText(tr("起点图层"))
        self.btn_point_filter.setToolTip(tr("按分类筛选。图例未勾选的分类也会列出来，勾上即可参与。"))
        self.btn_point_filter.setText(_filter_caption(self._point_filter))
        self.line_table.retranslate(
            tr("线"),
            tr("可增加多个线图层。每条线各自按分类筛选。"),
        )
        self.end_table.retranslate(
            tr("终点"),
            _end_tip(),
        )
        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText(tr("开始"))
        cancel_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText(tr("取消"))
        self.btn_save.setText(tr("保存"))
        self.btn_save.setToolTip(tr("保存当前选择的起点、线和终点图层。只有点这里，下次打开才会恢复这些图层。"))

    def closeEvent(self, event):
        try:
            language_changed().disconnect(self._apply_language)
        except Exception:
            pass  # nosec B110
        super(FreeLineDirSetup, self).closeEvent(event)

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

    def _on_point_layer(self, _layer):
        self._point_filter = None
        self.btn_point_filter.setText(_filter_caption(self._point_filter))

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
        accepted = run_exec(dlg)
        if not accepted:
            return current
        return dlg.result_filter()

    def _edit_point_filter(self):
        self._point_filter = self._edit_filter(self.point_combo.currentLayer(), self._point_filter)
        self.btn_point_filter.setText(_filter_caption(self._point_filter))

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

    def _accept(self):
        pairs = self._line_pairs()
        if self.point_combo.currentLayer() is None or not pairs:
            QMessageBox.warning(self, tr("通用线方向"), tr("请选择点图层，并至少增加一个线图层。"))
            return
        self.accept()

    def _layer_memory(self):
        point = self.point_combo.currentLayer()
        return {
            "point_layer_id": point.id() if point is not None else "",
            "point_layer_name": point.name() if point is not None else "",
            "point_filter": self._point_filter,
            "line_rows": self.line_table.get_group().get("rows") or [],
            "end_rows": self.end_table.get_group().get("rows") or [],
        }

    def _save_layers(self):
        _save_memory(self._layer_memory())
        self._memory = _load_memory()
        QMessageBox.information(self, tr("线方向检查"), tr("已保存当前图层。下次打开会恢复这些图层。"))

    def values(self):
        return {
            "point_layer": self.point_combo.currentLayer(),
            "point_filter": self._point_filter,
            "line_pairs": self._line_pairs(),
            "terminal_pairs": self._end_pairs(),
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
        "通用线方向_起点终点",
        rows,
        "#6a1b9a",
        [("label", QVariant.String), ("detail", QVariant.String)],
        fallback_crs=result.get("work_crs"),
        checked=True,  # 1.18.8: the start/end marks are on by default
        source="通用线方向",
    )
    if layer is None:
        return []
    return [layer.name()]


def open_free_line_dir(host):
    global _SETUP_DLG
    parent = resolve_tool_parent(host)
    setup = FreeLineDirSetup(host, parent)
    _SETUP_DLG = setup
    accepted = run_exec(setup)
    _SETUP_DLG = None
    if not accepted:
        return
    picked = setup.values()
    progress = _CheckProgress(parent)
    try:
        progress.dlg.setWindowTitle(tr("线方向检查"))
    except Exception:
        pass  # nosec B110
    try:
        result = run_free_line_dir(
            picked["point_layer"],
            picked["point_filter"],
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
            [result], visible_kinds=("line_reversed", "pseudo_cycle", "dir_ambiguous")
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
            pass  # nosec B110
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
        pass  # nosec B110
