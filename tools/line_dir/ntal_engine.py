# -*- coding: utf-8 -*-
from ...i18n import tr
import math
import random
import re

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsRendererCategory,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsSingleSymbolRenderer,
    QgsSpatialIndex,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
    NULL,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

from .layer_picker import attr_key
from .ntal_legend import FeatureCategoryFilter, filter_is_narrow
from .ntal_graph import (
    ROLE_CABLE,
    ROLE_DIST,
    ROLE_DROP,
    ROLE_FAT,
    ROLE_OCC,
    ROLE_SPLICE,
    ROLE_TRUNK,
    ROLE_USER,
    analyze_drops,
    analyze_graph,
)

NAME_FIELDS = (
    "NAME", "Name", "name", "名称", "编号", "CODE", "Code", "code",
    "ID", "id", "编码", "设备名称", "设备编号",
)
ROLE_LABEL = {
    ROLE_OCC: "光交",
    ROLE_SPLICE: "接头",
    ROLE_FAT: "分纤盒",
    ROLE_TRUNK: "主干",
    ROLE_DIST: "配线",
    ROLE_CABLE: "光缆",
    ROLE_DROP: "皮线",
    ROLE_USER: "用户",
}
TEMP_GROUP_NAME = "拓扑检查结果"
AUDIT_GROUP_NAME = "全面检测"
SNAP_TIE_M = 0.001
LEVEL_LABELS = {
    "hard": "硬错误",
    "soft": "软错误",
    "warn": "警告",
}
LEVEL_GROUPS = ("硬错误", "软错误", "警告")
# 允许但要复核：出「警告」图层。不挡赋值整单写入（方案另有规定除外）。
WARN_KINDS = {
    "multi_fat",
    "multi_fat_assign",
    "splice_no_out",
    "fat_no_drop",
}
KIND_SOURCE_TITLES = {
    "drop": "皮线赋值",
    "fat": "分纤盒赋值",
    "line": "线赋值",
    "splice_code": "接头 CODE",
    "fat_code": "分纤盒 CODE",
    "cable_code": "主干配线CODE",
    "line_dir": "线方向",
    "line_dir_free": "通用线方向",
    "audit": "全面检测",
}
KIND_LAYER_TITLES = {
    "dup_drop": "同分纤盒重复皮线",
    "multi_fat": "多分纤盒覆盖用户",
    "multi_fat_assign": "多分纤盒覆盖用户",
    "fat_no_drop": "分纤盒无皮线",
    "dangling": "一端空",
    "both_open": "两端空",
    "drop_both_fat": "皮线两端分纤盒",
    "drop_both_user": "皮线两端用户",
    "snap_ambig": "端点歧义",
    "cycle": "成环",
    "fat_branch": "分纤盒分叉",
    "fat_multi_in": "分纤盒多进线",
    "splice_multi_in": "接头多进线",
    "splice_trunk_branch": "接头主干分叉",
    "occ_in": "光交被当作下游",
    "self_loop": "自环",
    "unreached_edge": "未挂上的线",
    "unreached_node": "未挂上的点",
    "occ_no_out": "光交无出线",
    "bad_splice_name": "接头名称不合规",
    "code_conflict": "CODE重复",
    "city_pm_mismatch": "城市PM不一致",
    "splice_no_out": "接头无配线",
    "line_reversed": "线方向反了",
    "pseudo_cycle": "伪成环",
    "dir_conflict": "方向冲突",
    "bad_role": "角色异常",
    "fat_hh_zero": "分纤盒户数为0",
    "link_tie": "链路排名平局",
    "fat_no_in": "分纤盒无进线",
    "splice_no_in": "接头无进线",
    "user_no_drop": "用户点无皮线",
    "cable_dangling": "光缆一端空",
    "cable_both_open": "光缆两端空",
    "cable_bad_role": "光缆端点非法",
    "cable_unreached": "光缆未从光交挂上",
    "drop_dangling": "皮线一端空",
    "drop_both_open": "皮线两端空",
    "drop_bad_role": "皮线端点非法",
    "node_overlap": "设备点重叠",
    "end_near_multi": "端点附近多个设备",
    "code_empty": "CODE为空",
}
_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_FID_TAIL = re.compile(r"#\d+\s*$")
LINE_ISSUE_KINDS = {
    "dangling",
    "both_open",
    "drop_both_fat",
    "drop_both_user",
    "snap_ambig",
    "unreached_edge",
    "self_loop",
    "line_reversed",
    "pseudo_cycle",
    "dir_conflict",
    "bad_role",
    "link_tie",
    "cable_dangling",
    "cable_both_open",
    "cable_bad_role",
    "cable_unreached",
    "drop_dangling",
    "drop_both_open",
    "drop_bad_role",
    "end_near_multi",
}
_FW_TRANS = str.maketrans("０１２３４５６７８９．，", "0123456789.,")


def item_level(item, bucket="warn"):
    """bucket 是产出时的 hard/soft/warn；未标 soft 的旧结果按 kind 再拆。"""
    if bucket == "hard":
        return "hard"
    if bucket == "soft":
        return "soft"
    kind = (item or {}).get("kind") or ""
    if kind in WARN_KINDS:
        return "warn"
    return "soft"


def split_issue_levels(result):
    """返回 (硬错误, 软错误, 警告)。赋值/命名仍只产 hard+warn 时，这里按 kind 拆开。"""
    hard = list((result or {}).get("hard") or [])
    if (result or {}).get("soft") is not None:
        return hard, list(result.get("soft") or []), list(result.get("warn") or [])
    soft = []
    warn = []
    for item in (result or {}).get("warn") or []:
        if ((item or {}).get("kind") or "") in WARN_KINDS:
            warn.append(item)
        else:
            soft.append(item)
    return hard, soft, warn


def level_label(level):
    return LEVEL_LABELS.get(level, "警告")


def parse_hh(value):
    if value is None:
        return 0.0
    try:
        if value == NULL:
            return 0.0
    except Exception:
        pass
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        try:
            if math.isnan(value):
                return 0.0
        except Exception:
            pass
        return float(value)
    text = str(value).translate(_FW_TRANS).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        pass
    compact = text.replace(",", "")
    match = _NUM_RE.search(compact)
    if not match:
        return 0.0
    try:
        return float(match.group(0))
    except ValueError:
        return 0.0


def format_num(value):
    if value is None:
        return ""
    try:
        if value == NULL:
            return ""
    except Exception:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return ("{:.3f}".format(number)).rstrip("0").rstrip(".")


def _layer_crs(layer):
    try:
        crs = layer.crs() if layer is not None else None
        if crs is not None and crs.isValid():
            return crs
    except Exception:
        pass
    try:
        proj = QgsProject.instance().crs()
        if proj is not None and proj.isValid():
            return proj
    except Exception:
        pass
    return QgsCoordinateReferenceSystem("EPSG:4326")


def _project_crs():
    try:
        crs = QgsProject.instance().crs()
        if crs is not None and crs.isValid():
            return crs
    except Exception:
        pass
    return QgsCoordinateReferenceSystem("EPSG:4326")


def _xform(src, dst):
    if src is None or dst is None:
        return None
    try:
        if not src.isValid() or not dst.isValid():
            return None
        if src == dst:
            return None
    except Exception:
        return None
    try:
        return QgsCoordinateTransform(src, dst, QgsProject.instance().transformContext())
    except Exception:
        return None


def _transform_geom(geom, xform):
    copied = QgsGeometry(geom)
    if xform is None:
        return copied
    try:
        if copied.transform(xform) != 0:
            return None
    except Exception:
        return None
    if copied.isEmpty():
        return None
    return copied


def working_crs_from_layers(layers):
    """Local azimuthal metres. Project default is often EPSG:4326; mixed layer CRS is OK."""
    wgs = QgsCoordinateReferenceSystem("EPSG:4326")
    combined = None
    for layer in layers or []:
        extent = layer.extent()
        if extent is None or extent.isEmpty() or extent.isNull():
            continue
        geom = QgsGeometry.fromRect(extent)
        xform = _xform(_layer_crs(layer), wgs)
        if xform is not None:
            geom = _transform_geom(geom, xform)
            if geom is None:
                continue
        combined = geom if combined is None else combined.combine(geom)
    if combined is None or combined.isEmpty():
        try:
            ext = QgsProject.instance().viewSettings().fullExtent()
            if ext and not ext.isEmpty() and not ext.isNull():
                geom = QgsGeometry.fromRect(ext)
                xform = _xform(_project_crs(), wgs)
                if xform is not None:
                    geom = _transform_geom(geom, xform)
                if geom is not None:
                    combined = geom
        except Exception:
            pass
    lon, lat = 0.0, 0.0
    if combined is not None and not combined.isEmpty():
        try:
            center = combined.centroid().asPoint()
            lon, lat = float(center.x()), float(center.y())
        except Exception:
            lon, lat = 0.0, 0.0
    if abs(lon) > 180 or abs(lat) > 90:
        lon, lat = 0.0, 0.0
    proj = (
        "+proj=aeqd +lat_0={lat:.10f} +lon_0={lon:.10f} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    ).format(lat=lat, lon=lon)
    work = QgsCoordinateReferenceSystem()
    try:
        work.createFromProj(proj)
    except Exception:
        work = QgsCoordinateReferenceSystem()
    if not work.isValid():
        work = QgsCoordinateReferenceSystem("EPSG:3857")
    return work


def _point_xy(geom):
    if geom is None or geom.isEmpty():
        return None
    if geom.type() != QgsWkbTypes.PointGeometry:
        pt = geom.centroid().asPoint()
        return (pt.x(), pt.y())
    if geom.isMultipart():
        pts = geom.asMultiPoint()
        if not pts:
            return None
        return (pts[0].x(), pts[0].y())
    pt = geom.asPoint()
    return (pt.x(), pt.y())


def _straight_line(geom):
    if geom is None or geom.isEmpty():
        return None
    if geom.type() != QgsWkbTypes.LineGeometry:
        return None
    try:
        if QgsWkbTypes.isCurvedType(geom.wkbType()):
            lined = geom.curveToLine()
            if lined is not None and not lined.isEmpty():
                return lined
    except Exception:
        pass
    return geom


def _part_length(part):
    length = 0.0
    for i in range(1, len(part)):
        length += math.hypot(part[i].x() - part[i - 1].x(), part[i].y() - part[i - 1].y())
    return length


def _geom_parts(geom):
    if geom is None or geom.isEmpty():
        return []
    parts = []
    try:
        if geom.isMultipart():
            parts = [p for p in (geom.asGeometryCollection() or []) if p and not p.isEmpty()]
    except Exception:
        parts = []
    if not parts and geom.isMultipart():
        try:
            raw = geom.constGet()
            for i in range(raw.numGeometries()):
                piece = raw.geometryN(i)
                if piece is None:
                    continue
                parts.append(QgsGeometry(piece.clone()))
        except Exception:
            parts = []
    if not parts:
        parts = [geom]
    return parts


def _longest_line_geom(geom):
    """曲线先拉直，多段线只留最长一段。"""
    straight = _straight_line(geom)
    if straight is None or straight.isEmpty():
        return None
    best = None
    best_len = -1.0
    for part in _geom_parts(straight):
        if part.type() != QgsWkbTypes.LineGeometry:
            continue
        try:
            length = float(part.length())
        except Exception:
            length = 0.0
        if length > best_len:
            best = part
            best_len = length
    return best


def _part_vertices(geom):
    pts = []
    if geom is None or geom.isEmpty():
        return pts
    try:
        for vertex in geom.vertices():
            pts.append((float(vertex.x()), float(vertex.y())))
        if len(pts) >= 2:
            return pts
    except Exception:
        pts = []
    try:
        for pt in geom.asPolyline() or []:
            xy = _as_xy(pt)
            if xy:
                pts.append(xy)
    except Exception:
        pass
    return pts


def _line_polyline(geom):
    part = _longest_line_geom(geom)
    if part is None:
        return None
    pts = _part_vertices(part)
    if len(pts) < 2:
        return None
    return [QgsPointXY(xy[0], xy[1]) for xy in pts]


def _away_xy(line, origin_index, step):
    origin = line[origin_index]
    if step > 0:
        indexes = range(origin_index + 1, len(line))
    else:
        indexes = range(origin_index - 1, -1, -1)
    for i in indexes:
        pt = line[i]
        if math.hypot(pt.x() - origin.x(), pt.y() - origin.y()) > 1e-6:
            return (pt.x(), pt.y())
    other = line[-1] if origin_index == 0 else line[0]
    return (other.x(), other.y())


def _line_ends(geom):
    line = _line_polyline(geom)
    if line is None:
        return None
    # 只取线的两个端点，不看中间折点
    a, b = line[0], line[-1]
    return ((a.x(), a.y()), (b.x(), b.y()))


def _line_exits(geom):
    line = _line_polyline(geom)
    if line is None:
        return None
    return {
        "start_next": _away_xy(line, 0, 1),
        "end_prev": _away_xy(line, len(line) - 1, -1),
    }


def _as_xy(pt):
    if pt is None:
        return None
    if isinstance(pt, (tuple, list)) and len(pt) >= 2:
        try:
            return (float(pt[0]), float(pt[1]))
        except Exception:
            return None
    try:
        return (float(pt.x()), float(pt.y()))
    except Exception:
        return None


def _polyline_half_xy(line):
    """折线沿线长度一半，点一定在这段折线上。不用两端连线中点。"""
    pts = []
    for pt in line or []:
        xy = _as_xy(pt)
        if xy is not None:
            pts.append(xy)
    if len(pts) < 2:
        return pts[0] if pts else None
    total = 0.0
    segs = []
    for i in range(1, len(pts)):
        seg = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        segs.append(seg)
        total += seg
    if total <= 0:
        return pts[0]
    half = total / 2.0
    walked = 0.0
    for i, seg in enumerate(segs):
        a = pts[i]
        b = pts[i + 1]
        if walked + seg >= half:
            if seg <= 1e-15:
                return a
            t = (half - walked) / seg
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        walked += seg
    return pts[-1]


def _geom_half_point(geom):
    """该条线自己的几何中点：先拉直，多段线只取最长一段，沿线一半，点在线上。"""
    part = _longest_line_geom(geom)
    if part is None:
        return None
    return _polyline_half_xy(_part_vertices(part))


def _xy_to_project(xy, src_crs, project_crs):
    xy = _as_xy(xy)
    if not xy:
        return None
    geom = QgsGeometry.fromPointXY(QgsPointXY(xy[0], xy[1]))
    moved = _transform_geom(geom, _xform(src_crs, project_crs))
    if moved is None:
        moved = geom
    try:
        pt = moved.asPoint()
        return (pt.x(), pt.y())
    except Exception:
        return None


def _geom_to_project(geom, src_crs, project_crs):
    if geom is None or geom.isEmpty():
        return None
    moved = _transform_geom(QgsGeometry(geom), _xform(src_crs, project_crs))
    if moved is None or moved.isEmpty():
        return QgsGeometry(geom)
    return moved


def _point_on_line(line_geom, xy):
    """把点吸附回该条线，避免坐标变换后离开线。"""
    xy = _as_xy(xy)
    if line_geom is None or line_geom.isEmpty() or not xy:
        return None
    pt = QgsGeometry.fromPointXY(QgsPointXY(xy[0], xy[1]))
    try:
        snapped = line_geom.nearestPoint(pt)
        if snapped is not None and not snapped.isEmpty():
            out = snapped.asPoint()
            return (out.x(), out.y())
    except Exception:
        pass
    try:
        _dist, close_pt, _after, _left = line_geom.closestSegmentWithContext(QgsPointXY(xy[0], xy[1]))
        if close_pt is not None:
            return (close_pt.x(), close_pt.y())
    except Exception:
        pass
    return xy


def _line_mid(edge):
    start = edge.get("start")
    end = edge.get("end")
    if not start or not end:
        return None
    return ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)


def _feature_name(feat, name_field=None):
    names = feat.fields().names()
    if name_field and name_field in names:
        text = attr_key(feat[name_field]).strip()
        if text:
            return text
    for field in NAME_FIELDS:
        if field not in names:
            continue
        text = attr_key(feat[field]).strip()
        if text:
            return text
    return ""


def _feature_label(feat, layer_name, fallback_prefix, name_field=None):
    text = _feature_name(feat, name_field)
    if text:
        return text
    return "{}#{}".format(fallback_prefix or layer_name, feat.id())


def collect_points(layers, filters, role, work_crs, hh_field=None, old_field=None, name_field=None, on_step=None, include_unchecked=False):
    rows = []
    stats = {}
    for layer in layers:
        flt = (filters or {}).get(layer.id())
        src_crs = _layer_crs(layer)
        xform = _xform(src_crs, work_crs)
        layer_id = layer.id()
        layer_name = layer.name()
        field_names = layer.fields().names()
        hh_idx = layer.fields().indexOf(hh_field) if hh_field and hh_field in field_names else -1
        old_idx = layer.fields().indexOf(old_field) if old_field and old_field in field_names else -1
        extracted = 0
        seen = 0
        matcher = FeatureCategoryFilter(layer, flt, include_unchecked=include_unchecked)
        narrow = filter_is_narrow(flt)
        try:
            for feat in layer.getFeatures():
                if on_step is not None:
                    seen += 1
                    if (seen & 255) == 0:
                        on_step(256)
                if not matcher.allow(feat):
                    continue
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                moved = _transform_geom(geom, xform)
                if moved is None:
                    continue
                xy = _point_xy(moved)
                if xy is None:
                    continue
                extracted += 1
                hh = parse_hh(feat.attribute(hh_idx)) if hh_idx >= 0 else 0.0
                old = feat.attribute(old_idx) if old_idx >= 0 else None
                key = "{}:{}".format(layer_id, feat.id())
                src_xy = _point_xy(geom)
                rows.append({
                    "id": key,
                    "role": role,
                    "layer": layer,
                    "layer_id": layer_id,
                    "layer_name": layer_name,
                    "cat_label": matcher.cat_label(feat) if narrow else "",
                    "fid": feat.id(),
                    "xy": xy,
                    "src_xy": src_xy or xy,
                    "src_crs": src_crs,
                    "hh": hh,
                    "old": old,
                    "name": _feature_name(feat, name_field),
                    "label": "{} {}".format(
                        ROLE_LABEL[role],
                        _feature_label(feat, layer_name, ROLE_LABEL[role], name_field),
                    ),
                })
        finally:
            matcher.close()
        if on_step is not None and (seen & 255):
            on_step(seen & 255)
        stats[layer.id()] = {
            "layer": layer,
            "role": role,
            "extracted": extracted,
        }
    return rows, stats


def collect_lines(layers, filters, role, work_crs, write_field, on_step=None, include_unchecked=False):
    rows = []
    stats = {}
    for layer in layers:
        flt = (filters or {}).get(layer.id())
        src_crs = _layer_crs(layer)
        xform = _xform(src_crs, work_crs)
        extracted = 0
        seen = 0
        field_ok = bool(write_field) and write_field in layer.fields().names()
        write_idx = layer.fields().indexOf(write_field) if field_ok else -1
        matcher = FeatureCategoryFilter(layer, flt, include_unchecked=include_unchecked)
        narrow = filter_is_narrow(flt)
        try:
            for feat in layer.getFeatures():
                if on_step is not None:
                    seen += 1
                    if (seen & 255) == 0:
                        on_step(256)
                if not matcher.allow(feat):
                    continue
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                moved = _transform_geom(geom, xform)
                if moved is None:
                    continue
                ends = _line_ends(moved)
                if ends is None:
                    continue
                extracted += 1
                old = feat.attribute(write_idx) if write_idx >= 0 else None
                key = "{}:{}".format(layer.id(), feat.id())
                src_ends = _line_ends(geom)
                exits = _line_exits(moved) or {}
                try:
                    length = float(moved.length())
                except Exception:
                    length = 0.0
                rows.append({
                    "id": key,
                    "role": role,
                    "layer": layer,
                    "layer_id": layer.id(),
                    "layer_name": layer.name(),
                    "cat_label": matcher.cat_label(feat) if narrow else "",
                    "fid": feat.id(),
                    "start": ends[0],
                    "end": ends[1],
                    "start_next": exits.get("start_next") or ends[1],
                    "end_prev": exits.get("end_prev") or ends[0],
                    "src_start": src_ends[0] if src_ends else None,
                    "src_end": src_ends[1] if src_ends else None,
                    "src_mid": _geom_half_point(geom),
                    "src_crs": src_crs,
                    "length": length,
                    "old": old,
                    "write_field": write_field,
                    "multipart": bool(geom.isMultipart()),
                    "label": "{} {}".format(ROLE_LABEL[role], _feature_label(feat, layer.name(), ROLE_LABEL[role])),
                })
        finally:
            matcher.close()
        if on_step is not None and (seen & 255):
            on_step(seen & 255)
        stats[layer.id()] = {
            "layer": layer,
            "role": role,
            "extracted": extracted,
            "field_ok": field_ok,
        }
    return rows, stats


def _snap_end(xy, index, nodes_by_int, tolerance):
    if xy is None:
        return None, []
    x, y = xy
    rect = QgsRectangle(x - tolerance, y - tolerance, x + tolerance, y + tolerance)
    hits = []
    for nid in index.intersects(rect):
        node = nodes_by_int.get(nid)
        if node is None:
            continue
        nx, ny = node["xy"]
        dist = math.hypot(x - nx, y - ny)
        if dist <= tolerance:
            hits.append((dist, node["id"]))
    if not hits:
        return None, []
    hits.sort(key=lambda item: (item[0], item[1]))
    best = hits[0]
    near = [item for item in hits if item[0] <= best[0] + SNAP_TIE_M]
    if len(near) > 1 and abs(near[0][0] - near[1][0]) <= SNAP_TIE_M:
        return None, [item[1] for item in near]
    return best[1], []


def run_analysis(occ_layers, splice_layers, fat_layers, cable_layers,
                 occ_filters, splice_filters, fat_filters, cable_filters,
                 hh_field, write_field, tolerance, accumulate=False,
                 user_layers=None, user_filters=None,
                 trunk_layers=None, dist_layers=None,
                 trunk_filters=None, dist_filters=None, dist_write_field=None,
                 scheme=None):
    from .ntal_link_rank import hh_is_zero_or_empty
    from .ntal_roles import snap_and_classify_cables
    from .ntal_scheme import cable_accumulate, resolve_scheme, result_meta, write_trunk_hh

    spec = resolve_scheme(scheme, accumulate=accumulate, action="line")
    accumulate = cable_accumulate(spec, action="line")
    do_write_trunk = write_trunk_hh(spec)

    if not cable_layers:
        cable_layers = list(trunk_layers or []) + list(dist_layers or [])
        cable_filters = dict(trunk_filters or {})
        cable_filters.update(dist_filters or {})
        write_field = write_field or dist_write_field
    config_errors = []
    if not occ_layers:
        config_errors.append("请选择光交点图层。")
    if not fat_layers:
        config_errors.append("请选择分纤盒点图层。")
    if not cable_layers:
        config_errors.append("请选择光缆图层。")
    if not hh_field:
        config_errors.append("请选择分纤盒户数字段（线赋值按此字段读取）。")
    if not write_field:
        config_errors.append("请选择光缆户数写入字段。")
    if tolerance <= 0:
        config_errors.append("吸附容差必须大于 0。")
    if fat_layers and hh_field:
        missing = [layer.name() for layer in fat_layers if hh_field not in layer.fields().names()]
        if missing:
            config_errors.append("户数字段「{}」不在分纤盒图层：{}".format(hh_field, "、".join(missing)))
    if cable_layers and write_field:
        missing = [layer.name() for layer in cable_layers if write_field not in layer.fields().names()]
        if missing:
            config_errors.append("光缆户数写入字段「{}」不在图层：{}".format(write_field, "、".join(missing)))
    if config_errors:
        return {"ok": False, "config_errors": config_errors}

    all_layers = list(occ_layers) + list(splice_layers or []) + list(fat_layers)
    all_layers += list(user_layers or []) + list(cable_layers)
    work_crs = working_crs_from_layers(all_layers)

    nodes = []
    layer_stats = {}
    occ_rows, occ_stats = collect_points(occ_layers, occ_filters, ROLE_OCC, work_crs)
    splice_rows, splice_stats = collect_points(splice_layers or [], splice_filters, ROLE_SPLICE, work_crs)
    fat_rows, fat_stats = collect_points(fat_layers, fat_filters, ROLE_FAT, work_crs, hh_field=hh_field)
    user_rows, user_stats = collect_points(user_layers or [], user_filters or {}, ROLE_USER, work_crs)
    nodes.extend(occ_rows)
    nodes.extend(splice_rows)
    nodes.extend(fat_rows)
    nodes.extend(user_rows)
    layer_stats.update(occ_stats)
    layer_stats.update(splice_stats)
    layer_stats.update(fat_stats)

    cable_rows, cable_stats = collect_lines(cable_layers, cable_filters, ROLE_CABLE, work_crs, write_field)
    layer_stats.update(cable_stats)

    hard = []
    warn = []
    if not occ_rows:
        hard.append({"kind": "config", "message": "光交图层筛选后没有可用点。", "refs": []})
    if not fat_rows:
        hard.append({"kind": "config", "message": "分纤盒图层筛选后没有可用点。", "refs": []})
    if not cable_rows:
        hard.append({"kind": "config", "message": "光缆图层筛选后没有可用线。", "refs": []})

    trunk_rows, dist_rows, bindings, _classified = snap_and_classify_cables(
        cable_rows, nodes, tolerance, hard, warn, ROLE_LABEL, spec
    )
    edges = list(trunk_rows) + list(dist_rows)
    node_map = {node["id"]: node for node in nodes}

    graph_nodes = {}
    for node in nodes:
        graph_nodes[node["id"]] = {
            "role": node["role"],
            "hh": node["hh"],
            "label": node["label"],
        }

    graph_edges = {}
    for edge in edges:
        graph_edges[edge["id"]] = {
            "a": edge.get("a"),
            "b": edge.get("b"),
            "label": edge["label"],
        }

    result = analyze_graph(
        graph_nodes, graph_edges, [row["id"] for row in occ_rows],
        accumulate=bool(accumulate), scheme=spec,
    )
    hard.extend(result["hard"])
    warn.extend(result["warn"])
    reached = result.get("reached_nodes") or set()
    for fat in fat_rows:
        if fat["id"] not in reached:
            continue
        if hh_is_zero_or_empty(fat):
            hard.append({
                "kind": "fat_hh_zero",
                "message": "分纤盒户数为 0 或空：{}".format(fat["label"]),
                "refs": [("node", fat["id"])],
            })

    writes = []
    edge_map = {edge["id"]: edge for edge in edges}
    for eid, value in result["values"].items():
        edge = edge_map.get(eid)
        if edge is None:
            continue
        if not do_write_trunk and edge.get("role") == ROLE_TRUNK:
            continue
        writes.append({
            "edge_id": eid,
            "layer": edge["layer"],
            "layer_id": edge["layer_id"],
            "layer_name": edge["layer_name"],
            "fid": edge["fid"],
            "role": edge["role"],
            "label": edge["label"],
            "old": edge["old"],
            "value": value,
            "write_field": edge.get("write_field") or write_field,
        })
    writes.sort(key=lambda row: (row["role"], row["layer_name"], row["fid"]))

    used_by_layer = {}
    for row in writes:
        used_by_layer[row["layer_id"]] = used_by_layer.get(row["layer_id"], 0) + 1
    for nid in result["reached_nodes"]:
        node = node_map.get(nid)
        if node is None:
            continue
        used_by_layer[node["layer_id"]] = used_by_layer.get(node["layer_id"], 0) + 1

    participation = []
    for layer_id, stat in layer_stats.items():
        extracted = stat["extracted"]
        used = used_by_layer.get(layer_id, 0)
        participation.append({
            "layer": stat["layer"],
            "layer_name": stat["layer"].name(),
            "role": stat["role"],
            "extracted": extracted,
            "used": min(used, extracted),
            "ok": extracted > 0 and used > 0,
        })
        if extracted <= 0:
            warn.append({
                "kind": "layer_empty",
                "message": "配置图层筛选后无要素：{}（{}）".format(
                    stat["layer"].name(), ROLE_LABEL.get(stat["role"], stat["role"])
                ),
                "refs": [],
            })
        elif used <= 0:
            warn.append({
                "kind": "layer_idle",
                "message": "配置图层未有效参与：{}（{}，筛选 {} 个）".format(
                    stat["layer"].name(), ROLE_LABEL.get(stat["role"], stat["role"]), extracted
                ),
                "refs": [],
            })

    tree_text = _build_tree_text(occ_rows, node_map, edge_map, result)
    reached = result.get("reached_nodes") or set()
    fat_reached = [node for node in fat_rows if node["id"] in reached]
    fat_miss = [node for node in fat_rows if node["id"] not in reached]
    out = {
        "ok": True,
        "config_errors": [],
        "work_crs": work_crs,
        "nodes": node_map,
        "edges": edge_map,
        "snap_edges": bindings,
        "oriented": result["oriented"],
        "outgoing": result["outgoing"],
        "values": result["values"],
        "writes": writes,
        "hard": hard,
        "warn": warn,
        "participation": participation,
        "tree_text": tree_text,
        "kind": "line",
        "write_field": write_field,
        "hh_field": hh_field,
        "tolerance": tolerance,
        "fat_total": len(fat_rows),
        "fat_hh_total": sum(float(node.get("hh") or 0.0) for node in fat_rows),
        "fat_reached_count": len(fat_reached),
        "fat_reached_hh": sum(float(node.get("hh") or 0.0) for node in fat_reached),
        "fat_unreached_count": len(fat_miss),
        "fat_unreached_hh": sum(float(node.get("hh") or 0.0) for node in fat_miss),
        "line_total": len(edges),
    }
    out.update(result_meta(spec, action="line"))
    return out


def _build_tree_text(occ_rows, node_map, edge_map, result):
    outgoing = result["outgoing"]
    values = result["values"]
    lines = []

    def walk_dest(nid, prefix, last):
        node = node_map.get(nid)
        if node is None:
            return
        extra = ""
        if node["role"] == ROLE_FAT:
            extra = " 户数={}".format(format_num(node["hh"]))
        connector = "└─ " if last else "├─ "
        lines.append("{}{}{}{}".format(prefix, connector, node["label"], extra))
        outs = list(outgoing.get(nid, []))
        child_prefix = prefix + ("    " if last else "│   ")
        for i, eid in enumerate(outs):
            edge = edge_map.get(eid)
            _fr, to = result["oriented"][eid]
            is_last = i == len(outs) - 1
            value = values.get(eid)
            edge_label = edge["label"] if edge else eid
            branch = "└─ " if is_last else "├─ "
            lines.append("{}{}{} = {}".format(child_prefix, branch, edge_label, format_num(value)))
            next_prefix = child_prefix + ("    " if is_last else "│   ")
            walk_dest(to, next_prefix, True)

    if not occ_rows:
        return "没有光交。"
    for i, occ in enumerate(occ_rows):
        if i:
            lines.append("")
        lines.append(occ["label"])
        outs = list(outgoing.get(occ["id"], []))
        if not outs:
            lines.append("  （无出线）")
            continue
        for j, eid in enumerate(outs):
            edge = edge_map.get(eid)
            _fr, to = result["oriented"][eid]
            is_last = j == len(outs) - 1
            value = values.get(eid)
            edge_label = edge["label"] if edge else eid
            branch = "└─ " if is_last else "├─ "
            lines.append("{}{} = {}".format(branch, edge_label, format_num(value)))
            next_prefix = "    " if is_last else "│   "
            walk_dest(to, next_prefix, True)
    return "\n".join(lines)


def value_for_field(layer, field_name, value):
    if isinstance(value, str):
        return value
    idx = layer.fields().indexOf(field_name)
    if idx < 0:
        return value
    field = layer.fields().at(idx)
    ftype = field.type()
    if ftype in (QVariant.Int, QVariant.UInt, QVariant.LongLong, QVariant.ULongLong):
        return int(round(value))
    if ftype in (QVariant.Double,):
        return float(value)
    try:
        if field.isNumeric():
            return float(value)
    except Exception:
        pass
    return format_num(value)


def field_write_problems(writes):
    """写入前检查字段：CODE 只能写进文本字段，且不能超过字段长度（Shapefile 保存时会截断）。"""
    problems = []
    for layer, rows in defaultdict_writes(writes):
        by_field = {}
        for row in rows:
            field = row.get("write_field") or ""
            if field:
                by_field.setdefault(field, []).append(row)
        for field_name, items in by_field.items():
            idx = layer.fields().indexOf(field_name)
            if idx < 0:
                continue
            field = layer.fields().at(idx)
            texts = [row["value"] for row in items if isinstance(row.get("value"), str)]
            if not texts:
                continue
            if field.type() != QVariant.String:
                problems.append({
                    "kind": "field_bad",
                    "message": "字段「{}」（图层 {}）不是文本类型，写不进 CODE。".format(field_name, layer.name()),
                    "refs": [],
                })
                continue
            limit = int(field.length() or 0)
            longest = max(len(text) for text in texts)
            if limit > 0 and longest > limit:
                problems.append({
                    "kind": "field_bad",
                    "message": "字段「{}」（图层 {}）长度 {}，CODE 最长 {} 个字符，保存时会被截断。请先加宽字段。".format(
                        field_name, layer.name(), limit, longest
                    ),
                    "refs": [],
                })
    return problems


def code_conflicts_with_layer(writes, ref_kind, title):
    """新 CODE 和图层里其它要素已有的 CODE 相同（这次没有重写的要素）。"""
    from qgis.core import QgsFeatureRequest

    problems = []
    for layer, rows in defaultdict_writes(writes):
        field_name = rows[0].get("write_field") or ""
        idx = layer.fields().indexOf(field_name) if field_name else -1
        if idx < 0:
            continue
        rewritten = set(row["fid"] for row in rows)
        existing = {}
        request = QgsFeatureRequest()
        try:
            request.setFlags(QgsFeatureRequest.NoGeometry)
        except AttributeError:
            request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
        request.setSubsetOfAttributes([idx])
        for feat in layer.getFeatures(request):
            if feat.id() in rewritten:
                continue
            text = attr_key(feat.attribute(idx)).strip()
            if text:
                existing.setdefault(text, feat.id())
        for row in rows:
            code = str(row.get("value") or "").strip()
            other = existing.get(code)
            if other is None:
                continue
            problems.append({
                "kind": "code_conflict",
                "message": "{} CODE {} 已被图层 {} 里未重写的要素 #{} 占用：{}".format(
                    title, code, layer.name(), other, row.get("label") or ""
                ),
                "refs": [(ref_kind, "{}:{}".format(layer.id(), row["fid"]))],
            })
    return problems


def write_values(writes, write_field=None, command="NTAL 写入"):
    grouped = defaultdict_writes(writes)
    updated = 0
    errors = []
    for layer, rows in grouped:
        field = rows[0].get("write_field") or write_field
        if not field or field not in layer.fields().names():
            errors.append("{} 没有字段 {}".format(layer.name(), field or "(空)"))
            continue
        idx = layer.fields().indexOf(field)
        if not layer.isEditable():
            if not layer.startEditing():
                errors.append("{} 无法进入编辑".format(layer.name()))
                continue
        layer.beginEditCommand(command)
        try:
            for row in rows:
                row_field = row.get("write_field") or field
                row_idx = layer.fields().indexOf(row_field) if row_field in layer.fields().names() else idx
                typed = value_for_field(layer, row_field, row["value"])
                if not layer.changeAttributeValue(row["fid"], row_idx, typed):
                    errors.append("{} #{} 写入失败".format(layer.name(), row["fid"]))
                    continue
                updated += 1
            layer.endEditCommand()
        except Exception as exc:
            try:
                layer.destroyEditCommand()
            except Exception:
                pass
            errors.append("{} 写入异常：{}".format(layer.name(), exc))
    return updated, errors


def defaultdict_writes(writes):
    groups = {}
    order = []
    for row in writes:
        layer = row["layer"]
        key = layer.id()
        if key not in groups:
            groups[key] = (layer, [])
            order.append(key)
        groups[key][1].append(row)
    return [groups[key] for key in order]


def collect_refs(items, nodes, edges):
    by_layer = {}
    for item in items:
        for kind, key in item.get("refs") or []:
            rec = nodes.get(key) if kind == "node" else edges.get(key)
            if rec is None:
                continue
            layer = rec.get("layer")
            if layer is None:
                continue
            by_layer.setdefault(layer, set()).add(rec["fid"])
    return by_layer


def _build_index(rows):
    index = QgsSpatialIndex()
    by_int = {}
    for i, row in enumerate(rows, start=1):
        feat = QgsFeature()
        feat.setId(i)
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row["xy"][0], row["xy"][1])))
        index.insertFeature(feat)
        by_int[i] = row
    return index, by_int


def run_drop_analysis(fat_layers, user_layers, drop_layers,
                      fat_filters, user_filters, drop_filters,
                      drop_hh_field, user_hh_field, tolerance, scheme=None):
    return run_fat_analysis(
        fat_layers, user_layers, drop_layers,
        fat_filters, user_filters, drop_filters,
        "", user_hh_field, tolerance,
        drop_hh_field=drop_hh_field, mode="drop", scheme=scheme,
    )


def run_fat_analysis(fat_layers, user_layers, drop_layers,
                     fat_filters, user_filters, drop_filters,
                     fat_write_field, user_hh_field, tolerance,
                     drop_hh_field="", mode="fat", scheme=None):
    config_errors = []
    if not fat_layers:
        config_errors.append("请选择分纤盒点图层。")
    if not user_layers:
        config_errors.append("请选择用户点图层。")
    if not drop_layers:
        config_errors.append("请选择皮线图层。")
    if mode != "drop" and not fat_write_field:
        config_errors.append("请选择分纤盒写入字段。")
    if not drop_hh_field:
        config_errors.append("请选择皮线户数字段。")
    if not user_hh_field:
        config_errors.append("请选择用户户数字段。")
    if tolerance <= 0:
        config_errors.append("吸附容差必须大于 0。")
    if fat_layers and fat_write_field:
        missing = [layer.name() for layer in fat_layers if fat_write_field not in layer.fields().names()]
        if missing:
            config_errors.append("分纤盒写入字段「{}」不在图层：{}".format(fat_write_field, "、".join(missing)))
    if user_layers and user_hh_field:
        missing = [layer.name() for layer in user_layers if user_hh_field not in layer.fields().names()]
        if missing:
            config_errors.append("用户户数字段「{}」不在图层：{}".format(user_hh_field, "、".join(missing)))
    if drop_layers and drop_hh_field:
        missing = [layer.name() for layer in drop_layers if drop_hh_field not in layer.fields().names()]
        if missing:
            config_errors.append("皮线户数字段「{}」不在图层：{}".format(drop_hh_field, "、".join(missing)))
    if config_errors:
        return {"ok": False, "config_errors": config_errors}

    from .ntal_scheme import resolve_scheme
    action = "drop" if mode == "drop" else "fat"
    spec = resolve_scheme(scheme, action=action)
    hh_opts = spec.get("household") or {}
    drop_value = hh_opts.get("drop_value") or "user_hh"
    drop_multi = hh_opts.get("drop_multi") or "skip"
    fat_value = hh_opts.get("fat_value") or "sum_drop"
    fat_check = hh_opts.get("fat_check") or "totals"

    all_layers = list(fat_layers) + list(user_layers) + list(drop_layers)
    work_crs = working_crs_from_layers(all_layers)
    fat_rows, fat_stats = collect_points(
        fat_layers, fat_filters, ROLE_FAT, work_crs, old_field=fat_write_field
    )
    user_rows, user_stats = collect_points(
        user_layers, user_filters, ROLE_USER, work_crs, hh_field=user_hh_field
    )
    drop_rows, drop_stats = collect_lines(drop_layers, drop_filters, ROLE_DROP, work_crs, drop_hh_field)
    warn = []
    hard = []
    if not fat_rows:
        hard.append({"kind": "config", "message": "分纤盒图层筛选后没有可用点。", "refs": []})
    if not user_rows:
        hard.append({"kind": "config", "message": "用户图层筛选后没有可用点。", "refs": []})
    if not drop_rows:
        hard.append({"kind": "config", "message": "皮线图层筛选后没有可用线。", "refs": []})

    from .ntal_roles import classify_drop_pair

    end_index, end_by_int = _build_index(list(fat_rows) + list(user_rows))
    fat_map = {row["id"]: row for row in fat_rows}
    user_map = {row["id"]: row for row in user_rows}
    drop_map = {row["id"]: row for row in drop_rows}
    node_map = {}
    node_map.update(fat_map)
    node_map.update(user_map)

    links = []
    used_drops = set()
    used_fats = set()
    used_users = set()
    for drop in drop_rows:
        end_a, amb_a = _snap_end(drop["start"], end_index, end_by_int, tolerance)
        end_b, amb_b = _snap_end(drop["end"], end_index, end_by_int, tolerance)
        drop["a"] = end_a
        drop["b"] = end_b
        for amb, side in ((amb_a, "起点"), (amb_b, "终点")):
            if amb:
                warn.append({
                    "kind": "snap_ambig",
                    "message": "皮线{}同时靠近多个点：{}".format(side, drop["label"]),
                    "refs": [("edge", drop["id"])] + [("node", nid) for nid in amb],
                })
        if end_a and end_a == end_b:
            warn.append({
                "kind": "self_loop",
                "message": "皮线两端接到同一点：{}".format(drop["label"]),
                "refs": [("edge", drop["id"]), ("node", end_a)],
            })
            continue
        role_a = (node_map.get(end_a) or {}).get("role") if end_a else None
        role_b = (node_map.get(end_b) or {}).get("role") if end_b else None
        role, _severity, kind, _tail = classify_drop_pair(role_a, role_b, scheme)
        if role == ROLE_DROP:
            fat_id = end_a if role_a == ROLE_FAT else end_b
            user_id = end_a if role_a == ROLE_USER else end_b
            links.append({
                "drop_id": drop["id"],
                "fat_id": fat_id,
                "user_id": user_id,
                "hh": user_map[user_id]["hh"],
            })
            used_drops.add(drop["id"])
            used_fats.add(fat_id)
            used_users.add(user_id)
            continue
        if kind == "drop_both_fat":
            message = "皮线两端都是分纤盒：{}"
        elif kind == "drop_both_user":
            message = "皮线两端都是用户：{}"
        elif kind == "dangling":
            message = "皮线一端空：{}"
        else:
            kind = "both_open"
            message = "皮线两端都空：{}"
        warn.append({
            "kind": kind,
            "message": message.format(drop["label"]),
            "refs": [("edge", drop["id"])],
        })

    grouped = analyze_drops(links)
    if mode == "drop":
        for row in grouped["dup_rows"]:
            user = user_map.get(row["user_id"]) or {}
            fat = fat_map.get(row["fat_id"]) or {}
            hard.append({
                "kind": "dup_drop",
                "message": "同一分纤盒到同一用户有 {} 条皮线，已剔除：{} ← {}".format(
                    row["drop_count"], user.get("label") or row["user_id"], fat.get("label") or row["fat_id"]
                ),
                "refs": [("node", row["user_id"]), ("node", row["fat_id"])]
                + [("edge", did) for did in row["drop_ids"]],
            })
        for row in grouped["multi_rows"]:
            user = user_map.get(row["user_id"]) or {}
            fat_names = "、".join((fat_map.get(fid) or {}).get("label") or fid for fid in row["fat_ids"])
            if drop_multi == "write":
                message = "用户被 {} 个分纤盒覆盖，仍各写一条：{}（{}）"
            else:
                message = "用户被 {} 个分纤盒覆盖，不赋值：{}（{}）"
            warn.append({
                "kind": "multi_fat",
                "message": message.format(
                    row["fat_count"], user.get("label") or row["user_id"], fat_names
                ),
                "refs": [("node", row["user_id"])] + [("node", fid) for fid in row["fat_ids"]],
            })

    user_hh_total = sum(float(row.get("hh") or 0.0) for row in user_rows)
    drop_hh_total = sum(parse_hh(row.get("old")) for row in drop_rows)
    fat_drop_sums = {}
    fat_drop_counts = {}
    attributed_hh = 0.0
    for drop in drop_rows:
        hh = parse_hh(drop.get("old"))
        fat_ids = []
        for end_id in (drop.get("a"), drop.get("b")):
            if end_id in fat_map and end_id not in fat_ids:
                fat_ids.append(end_id)
        if len(fat_ids) != 1:
            continue
        fat_id = fat_ids[0]
        fat_drop_sums[fat_id] = fat_drop_sums.get(fat_id, 0.0) + hh
        fat_drop_counts[fat_id] = fat_drop_counts.get(fat_id, 0) + 1
        attributed_hh += hh

    writes = []
    if mode == "drop":
        skip_users = grouped["dup_users"] if drop_multi == "write" else grouped["excluded"]
        for link in links:
            if link["user_id"] in skip_users:
                continue
            drop = drop_map.get(link["drop_id"])
            if drop is None:
                continue
            if drop_value == "one":
                value = 1.0
            else:
                value = float(link.get("hh") or 0.0)
            writes.append({
                "layer": drop["layer"],
                "layer_id": drop["layer_id"],
                "layer_name": drop["layer_name"],
                "fid": drop["fid"],
                "role": ROLE_DROP,
                "label": drop["label"],
                "old": drop.get("old"),
                "value": value,
                "write_field": drop_hh_field,
            })
    else:
        totals_match = abs(user_hh_total - drop_hh_total) < 1e-6
        attributed_match = abs(attributed_hh - drop_hh_total) < 1e-6
        if not totals_match:
            msg = "用户点总户数 {} 与皮线字段总户数 {} 不一致，请先检查皮线值。".format(
                format_num(user_hh_total), format_num(drop_hh_total)
            )
            item = {"kind": "hh_mismatch", "message": msg + ("未写入。" if fat_check != "none" else ""), "refs": []}
            if fat_check == "none":
                warn.append(item)
            else:
                hard.append(item)
        elif not attributed_match:
            msg = "皮线字段总户数 {} 里有 {} 没有归到唯一分纤盒。".format(
                format_num(drop_hh_total), format_num(drop_hh_total - attributed_hh)
            )
            item = {
                "kind": "hh_unassigned",
                "message": msg + ("不赋值。请先检查皮线。" if fat_check != "none" else ""),
                "refs": [],
            }
            if fat_check == "none":
                warn.append(item)
            else:
                hard.append(item)
        if fat_check == "none" or (totals_match and attributed_match):
            for fat in fat_rows:
                if fat_value == "count_drop":
                    value = float(fat_drop_counts.get(fat["id"], 0))
                else:
                    value = fat_drop_sums.get(fat["id"], 0.0)
                writes.append({
                    "layer": fat["layer"],
                    "layer_id": fat["layer_id"],
                    "layer_name": fat["layer_name"],
                    "fid": fat["fid"],
                    "role": ROLE_FAT,
                    "label": fat["label"],
                    "old": fat.get("old"),
                    "value": value,
                    "user_count": fat_drop_counts.get(fat["id"], 0),
                    "write_field": fat_write_field,
                })
    writes.sort(key=lambda row: (row["layer_name"], row["fid"]))

    layer_stats = {}
    layer_stats.update(fat_stats)
    layer_stats.update(user_stats)
    layer_stats.update(drop_stats)
    used_by_layer = {}
    for fat_id in used_fats:
        fat = fat_map[fat_id]
        used_by_layer[fat["layer_id"]] = used_by_layer.get(fat["layer_id"], 0) + 1
    for user_id in used_users:
        user = user_map[user_id]
        used_by_layer[user["layer_id"]] = used_by_layer.get(user["layer_id"], 0) + 1
    for drop_id in used_drops:
        drop = drop_map[drop_id]
        used_by_layer[drop["layer_id"]] = used_by_layer.get(drop["layer_id"], 0) + 1

    participation = []
    for layer_id, stat in layer_stats.items():
        extracted = stat["extracted"]
        used = used_by_layer.get(layer_id, 0)
        participation.append({
            "layer": stat["layer"],
            "layer_name": stat["layer"].name(),
            "role": stat["role"],
            "extracted": extracted,
            "used": min(used, extracted),
            "ok": extracted > 0 and used > 0,
        })
        if extracted <= 0:
            warn.append({
                "kind": "layer_empty",
                "message": "配置图层筛选后无要素：{}（{}）".format(
                    stat["layer"].name(), ROLE_LABEL.get(stat["role"], stat["role"])
                ),
                "refs": [],
            })
        elif used <= 0:
            warn.append({
                "kind": "layer_idle",
                "message": "配置图层未有效参与：{}（{}，筛选 {} 个）".format(
                    stat["layer"].name(), ROLE_LABEL.get(stat["role"], stat["role"]), extracted
                ),
                "refs": [],
            })

    temp_dup = []
    temp_multi = []
    if mode == "drop":
        for row in grouped["dup_rows"]:
            user = user_map.get(row["user_id"])
            fat = fat_map.get(row["fat_id"])
            if user is None:
                continue
            temp_dup.append({
                "xy": user.get("src_xy") or user["xy"],
                "crs": user.get("src_crs"),
                "user_label": user["label"],
                "user_layer": user["layer_name"],
                "layer_name": user.get("layer_name") or "",
                "cat_label": user.get("cat_label") or "",
                "user_fid": user["fid"],
                "fat_label": (fat or {}).get("label") or "",
                "drop_count": row["drop_count"],
                "hh": row["hh"],
            })
        for row in grouped["multi_rows"]:
            user = user_map.get(row["user_id"])
            if user is None:
                continue
            fat_names = "、".join((fat_map.get(fid) or {}).get("label") or fid for fid in row["fat_ids"])
            temp_multi.append({
                "xy": user.get("src_xy") or user["xy"],
                "crs": user.get("src_crs"),
                "user_label": user["label"],
                "user_layer": user["layer_name"],
                "layer_name": user.get("layer_name") or "",
                "cat_label": user.get("cat_label") or "",
                "user_fid": user["fid"],
                "fat_count": row["fat_count"],
                "fat_names": fat_names,
                "drop_count": row["drop_count"],
                "hh": row["hh"],
            })

    if mode == "drop":
        if drop_value == "one":
            tree_head = "皮线户数（每条写 1"
        else:
            tree_head = "皮线户数（抄用户户数"
        if drop_multi == "write":
            tree_head += "；多盒覆盖也写 / 重复皮线跳过）"
        else:
            tree_head += "；已跳过多分纤盒覆盖 / 重复皮线）"
        tree_lines = [tree_head]
        for row in writes:
            tree_lines.append("  {} = {}".format(row["label"], format_num(row["value"])))
    else:
        if fat_value == "count_drop":
            tree_lines = ["分纤盒户数（按所出皮线条数）"]
        else:
            tree_lines = ["分纤盒户数（按所出皮线字段合计）"]
        tree_lines.append("用户点总户数 {}，皮线字段总户数 {}。".format(
            format_num(user_hh_total), format_num(drop_hh_total)
        ))
        for row in writes:
            tree_lines.append(
                "  {} = {}（皮线 {} 条）".format(
                    row["label"], format_num(row["value"]), row.get("user_count") or 0
                )
            )
    skip_assigned = grouped["dup_users"] if (mode == "drop" and drop_multi == "write") else grouped["excluded"]
    assigned_ids = set()
    for link in links:
        if link["user_id"] not in skip_assigned:
            assigned_ids.add(link["user_id"])
    unlinked_users = [row for row in user_rows if row["id"] not in used_users]
    unassigned_users = [row for row in user_rows if row["id"] not in assigned_ids]
    out = {
        "ok": True,
        "kind": "drop" if mode == "drop" else "fat",
        "config_errors": [],
        "work_crs": work_crs,
        "nodes": node_map,
        "edges": drop_map,
        "writes": writes,
        "hard": hard,
        "warn": warn,
        "participation": participation,
        "tree_text": "\n".join(tree_lines),
        "write_field": drop_hh_field if mode == "drop" else fat_write_field,
        "hh_field": user_hh_field,
        "tolerance": tolerance,
        "temp_dup": temp_dup,
        "temp_multi": temp_multi,
        "user_layer_count": len(user_layers or []),
        "user_total": len(user_rows),
        "user_hh_total": user_hh_total,
        "drop_hh_total": drop_hh_total,
        "fat_valid_hh": sum(float(row.get("value") or 0.0) for row in writes),
        "fat_valid_users": sum(int(row.get("user_count") or 0) for row in writes),
        "fat_count": len(fat_rows),
        "dup_user_count": len(grouped["dup_users"]),
        "multi_user_count": len(grouped["multi_users"]),
        "unlinked_user_count": len(unlinked_users),
        "unlinked_hh": sum(float(row.get("hh") or 0.0) for row in unlinked_users),
        "unassigned_user_count": len(unassigned_users),
        "unassigned_hh": sum(float(row.get("hh") or 0.0) for row in unassigned_users),
    }
    from .ntal_scheme import result_meta
    out.update(result_meta(scheme, action="drop" if mode == "drop" else "fat"))
    return out


def _is_group_node(node):
    try:
        from qgis.core import QgsLayerTreeNode
        return node.nodeType() == QgsLayerTreeNode.NodeGroup
    except Exception:
        return hasattr(node, "insertGroup")


def _child_group(parent, name):
    for child in parent.children():
        if _is_group_node(child) and child.name() == name:
            return child
    return parent.insertGroup(0, name)


def _ensure_group_path(names):
    node = QgsProject.instance().layerTreeRoot()
    for name in names or []:
        node = _child_group(node, name)
    return node


def _ensure_result_group():
    return _ensure_group_path([TEMP_GROUP_NAME])


TEMP_PROP = "ntal/temp_source"
_RESULT_GROUP_NAMES = {TEMP_GROUP_NAME, AUDIT_GROUP_NAME, "硬错误", "软错误", "警告"}


def _is_ntal_temp(layer):
    """只认插件自己建的临时点层。旧工程里没打标记的，按「内存图层 + 在结果组里」认。"""
    try:
        if layer.customProperty(TEMP_PROP) not in (None, ""):
            return True
    except Exception:
        pass
    try:
        if layer.providerType() != "memory":
            return False
        node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        parent = node.parent() if node is not None else None
        return parent is not None and parent.name() in _RESULT_GROUP_NAMES
    except Exception:
        return False


def _remove_layer_by_name(name):
    project = QgsProject.instance()
    for layer in list(project.mapLayers().values()):
        if layer.name() == name and _is_ntal_temp(layer):
            try:
                project.removeMapLayer(layer.id())
            except Exception:
                pass


def clear_temp_layers(sources):
    """清掉同一来源上次留下的临时点层，避免已修好的问题还挂在组里。"""
    wanted = set(item for item in (sources or []) if item)
    if not wanted:
        return
    project = QgsProject.instance()
    for layer in list(project.mapLayers().values()):
        if not _is_ntal_temp(layer):
            continue
        source = ""
        try:
            source = layer.customProperty(TEMP_PROP) or ""
        except Exception:
            source = ""
        if not source:
            name = layer.name() or ""
            source = next((item for item in wanted if name.endswith("_" + item)), "")
        if source in wanted:
            try:
                project.removeMapLayer(layer.id())
            except Exception:
                pass


def _add_layer_to_result_group(layer, checked=True, group_path=None):
    group = _ensure_group_path(group_path) if group_path else _ensure_result_group()
    QgsProject.instance().addMapLayer(layer, False)
    node = group.addLayer(layer)
    if node is not None and not checked:
        try:
            node.setItemVisibilityChecked(False)
        except Exception:
            pass
    return node


def _distinct_outline_colors(count):
    colors = []
    if count <= 0:
        return colors
    start = random.random()
    for i in range(count):
        hue = (start + float(i) / float(count)) % 1.0
        sat = 0.82 + (random.random() * 0.12)
        val = 0.78 + (random.random() * 0.16)
        color = QColor.fromHsvF(hue, min(sat, 1.0), min(val, 1.0))
        colors.append(color.name())
    return colors


def _outline_symbol(color, shape="circle"):
    return QgsMarkerSymbol.createSimple({
        "name": shape or "circle",
        "color": "255,255,255,0",
        "outline_color": color,
        "outline_style": "solid",
        "outline_width": "1",
        "outline_width_unit": "MM",
        "size": "5",
        "size_unit": "MM",
    })


def _apply_marker_renderer(layer, rows, color):
    shapes = []
    for row in rows or []:
        if not row.get("xy"):
            continue
        shape = "diamond" if row.get("marker") == "diamond" else "circle"
        if shape not in shapes:
            shapes.append(shape)
    if len(shapes) <= 1:
        layer.setRenderer(QgsSingleSymbolRenderer(_outline_symbol(color, shapes[0] if shapes else "circle")))
        return
    titles = {"diamond": "线", "circle": "点"}
    categories = []
    for shape in shapes:
        categories.append(QgsRendererCategory(
            shape, _outline_symbol(color, shape), titles.get(shape, shape)
        ))
    layer.setRenderer(QgsCategorizedSymbolRenderer("marker", categories))


def _label_layer(layer, field_name, color):
    settings = QgsPalLayerSettings()
    settings.fieldName = field_name
    settings.enabled = True
    try:
        settings.placement = QgsPalLayerSettings.OverPoint
    except Exception:
        pass
    fmt = QgsTextFormat()
    fmt.setSize(9)
    fmt.setFont(QFont("Microsoft YaHei", 9))
    fmt.setColor(QColor(color))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1)
    buf.setColor(QColor("#ffffff"))
    fmt.setBuffer(buf)
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def _add_temp_points(name, rows, color, fields_spec, fallback_crs=None, checked=True, group_path=None, source=""):
    _remove_layer_by_name(name)
    if not rows:
        return None
    project_crs = _project_crs()
    uri = "Point?crs={}".format(project_crs.authid() or "EPSG:4326")
    layer = QgsVectorLayer(uri, name, "memory")
    layer.setCustomProperty(TEMP_PROP, source or name)
    if project_crs is not None and project_crs.isValid():
        try:
            layer.setCrs(project_crs)
        except Exception:
            pass
    provider = layer.dataProvider()
    qfields = QgsFields()
    for fname, ftype in fields_spec:
        qfields.append(QgsField(fname, ftype))
    provider.addAttributes(qfields.toList())
    layer.updateFields()
    feats = []
    for row in rows:
        xy = row.get("xy")
        if not xy:
            continue
        geom = QgsGeometry.fromPointXY(QgsPointXY(xy[0], xy[1]))
        src_crs = row.get("crs")
        if src_crs is not None:
            moved = _transform_geom(geom, _xform(src_crs, project_crs))
        else:
            moved = geom
        if moved is None:
            moved = geom
        feat = QgsFeature(layer.fields())
        feat.setGeometry(moved)
        values = []
        for fname, _ftype in fields_spec:
            values.append(row.get(fname, ""))
        feat.setAttributes(values)
        feats.append(feat)
    if not feats:
        return None
    provider.addFeatures(feats)
    _apply_marker_renderer(layer, rows, color)
    if layer.fields().indexOf("label") >= 0:
        _label_layer(layer, "label", color)
    elif layer.fields().indexOf("user_label") >= 0:
        _label_layer(layer, "user_label", color)
    _add_layer_to_result_group(layer, checked=checked, group_path=group_path)
    return layer


def _issue_title(kind):
    return KIND_LAYER_TITLES.get(kind) or ""


def _issue_source(result):
    return KIND_SOURCE_TITLES.get(result.get("kind") or "", "") or (result.get("source_label") or "")


def _issue_parts(kind, severity, source=""):
    title = _issue_title(kind)
    if not title:
        return None
    prefix = LEVEL_LABELS.get(severity, "警告")
    parts = [prefix, title]
    if source:
        parts.append(source)
    return "_".join(parts)


def _issue_layer_name(kind, severity, source=""):
    return _issue_parts(kind, severity, source)


def _issue_feature_label(temp_name, rec, extra_parts=None):
    parts = [temp_name]
    layer_name = ((rec or {}).get("layer_name") or "").strip()
    if layer_name:
        parts.append(layer_name)
    cat = ((rec or {}).get("cat_label") or "").strip()
    if cat:
        parts.append(cat)
    for part in extra_parts or []:
        text = (part or "").strip()
        if text:
            parts.append(text)
    return "_".join(parts)


def _role_text(rec):
    role = (rec or {}).get("role")
    return ROLE_LABEL.get(role) or ""


def _name_after_role(label, role_text):
    text = (label or "").strip()
    role_text = (role_text or "").strip()
    if role_text and text.startswith(role_text):
        text = text[len(role_text):].strip()
    if not text or _FID_TAIL.search(text):
        return ""
    return text


def _record_name(rec):
    if not rec:
        return ""
    name = (rec.get("name") or "").strip()
    if name and not _FID_TAIL.search(name):
        return name
    return _name_after_role(rec.get("label") or "", _role_text(rec))


def _end_phrase(node):
    role = _role_text(node) or "点"
    name = _record_name(node)
    if name:
        return role + name
    return role


def _snap_node_at(xy, nodes, tolerance):
    if not xy or not tolerance or tolerance <= 0:
        return None
    hits = []
    for node in (nodes or {}).values():
        nxy = node.get("xy")
        if not nxy:
            continue
        dist = math.hypot(float(xy[0]) - float(nxy[0]), float(xy[1]) - float(nxy[1]))
        if dist <= float(tolerance) + 1e-9:
            hits.append((dist, node.get("id") or "", node))
    if not hits:
        return None
    hits.sort(key=lambda item: (item[0], item[1]))
    best = hits[0][0]
    near = [item for item in hits if item[0] <= best + SNAP_TIE_M]
    if len(near) > 1 and abs(near[0][0] - near[1][0]) <= SNAP_TIE_M:
        return None
    return hits[0][2]


def _edge_end_nodes(edge, nodes, tolerance):
    if "a" in edge or "b" in edge:
        return nodes.get(edge.get("a")), nodes.get(edge.get("b")), True
    if not tolerance or tolerance <= 0:
        return None, None, False
    return (
        _snap_node_at(edge.get("start"), nodes, tolerance),
        _snap_node_at(edge.get("end"), nodes, tolerance),
        True,
    )


def _line_hint_parts(kind, edge, nodes, tolerance):
    parts = []
    role = _role_text(edge)
    if role:
        parts.append(role)
    name = _record_name(edge)
    if name:
        parts.append(name)
    start_node, end_node, known = _edge_end_nodes(edge, nodes, tolerance)
    if not known:
        return parts
    same = (
        start_node and end_node
        and start_node.get("id") and start_node.get("id") == end_node.get("id")
    )
    if same:
        parts.append("两端接到" + _end_phrase(start_node))
        return parts
    gap_word = "歧义" if kind == "snap_ambig" else "空"
    if start_node and not end_node:
        parts.append("终点" + gap_word)
        parts.append("另一头是" + _end_phrase(start_node))
    elif end_node and not start_node:
        parts.append("起点" + gap_word)
        parts.append("另一头是" + _end_phrase(end_node))
    elif not start_node and not end_node:
        parts.append("两端歧义" if kind == "snap_ambig" else "两端都空")
    else:
        parts.append("起点是" + _end_phrase(start_node))
        parts.append("终点是" + _end_phrase(end_node))
    return parts


def _point_hint_parts(node):
    parts = []
    role = _role_text(node)
    if role:
        parts.append(role)
    name = _record_name(node)
    if name:
        parts.append(name)
    return parts


def _temp_user_parts(row):
    parts = ["用户"]
    name = _name_after_role(row.get("user_label") or "", "用户")
    if name:
        parts.append(name)
    fat_names = (row.get("fat_names") or "").strip()
    if fat_names:
        bits = []
        for piece in re.split(r"[、,，]", fat_names):
            piece = piece.strip()
            if not piece:
                continue
            fat_name = _name_after_role(piece, "分纤盒")
            bits.append("分纤盒" + fat_name if fat_name else "分纤盒")
        if bits:
            parts.append("另一头是" + "、".join(bits))
        return parts
    fat = (row.get("fat_label") or "").strip()
    if fat:
        fat_name = _name_after_role(fat, "分纤盒")
        parts.append("另一头是分纤盒" + fat_name if fat_name else "另一头是分纤盒")
    return parts


def _edges_for_issues(result):
    edges = {}
    for eid, edge in (result.get("edges") or {}).items():
        edges[eid] = edge
    for eid, edge in (result.get("snap_edges") or {}).items():
        current = edges.get(eid)
        if current is None:
            edges[eid] = edge
            continue
        if "a" not in current and "b" not in current and ("a" in edge or "b" in edge):
            merged = dict(current)
            merged["a"] = edge.get("a")
            merged["b"] = edge.get("b")
            if edge.get("role"):
                merged["role"] = edge.get("role")
            if edge.get("label"):
                merged["label"] = edge.get("label")
            edges[eid] = merged
    return edges


def _first_ref(item, wanted, table):
    for kind, key in item.get("refs") or []:
        if kind == wanted and key in table:
            return table[key]
    return None


def _issue_on_line(kind, item, nodes, edges):
    if kind in LINE_ISSUE_KINDS:
        return True
    refs = item.get("refs") or []
    has_node = any(ref_kind == "node" and key in nodes for ref_kind, key in refs)
    has_edge = any(ref_kind == "edge" and key in edges for ref_kind, key in refs)
    if has_node:
        return False
    return has_edge


def _edge_geom_mid(edge):
    """该条线自己的几何中点。算出后转到工程 CRS，再吸附回这条线。"""
    edge = edge or {}
    layer = edge.get("layer")
    src_crs = edge.get("src_crs") if edge.get("src_crs") is not None else _layer_crs(layer)
    project_crs = _project_crs()
    geom = None
    fid = edge.get("fid")
    if layer is not None and fid is not None:
        try:
            feat = layer.getFeature(fid)
        except Exception:
            feat = None
        if feat is not None and feat.isValid():
            geom = feat.geometry()
            src_crs = _layer_crs(layer)
    part = _longest_line_geom(geom) if geom else None
    line_proj = _geom_to_project(part or geom, src_crs, project_crs) if (part or geom) else None
    mid_src = _geom_half_point(geom) if geom else None
    if mid_src is None:
        mid_src = edge.get("src_mid")
        if mid_src is not None and edge.get("src_crs") is not None:
            src_crs = edge.get("src_crs")
    mid_proj = _xy_to_project(mid_src, src_crs, project_crs) if mid_src else None
    if mid_proj is None and line_proj is not None and not line_proj.isEmpty():
        try:
            length = float(line_proj.length())
            if length > 0:
                half = line_proj.interpolate(length / 2.0)
                if half is not None and not half.isEmpty():
                    pt = half.asPoint()
                    mid_proj = (pt.x(), pt.y())
        except Exception:
            mid_proj = None
    if line_proj is not None and not line_proj.isEmpty():
        snapped = _point_on_line(line_proj, mid_proj)
        if snapped:
            return snapped, project_crs
    if mid_proj:
        return mid_proj, project_crs
    return None, None


def _line_issue_xy(edge):
    mid, crs = _edge_geom_mid(edge)
    if mid:
        return mid, crs, edge
    return None, None, None


def _node_issue_xy(node, work_crs=None):
    project_crs = _project_crs()
    if node.get("src_xy") is not None:
        xy = _xy_to_project(node["src_xy"], node.get("src_crs"), project_crs)
        if xy:
            return xy, project_crs, node
    if node.get("xy") is not None:
        xy = _xy_to_project(node["xy"], work_crs, project_crs)
        if xy:
            return xy, project_crs, node
    return None, None, None


def _issue_point(item, nodes, edges, work_crs=None):
    if _issue_on_line(item.get("kind") or "", item, nodes, edges):
        edge = _first_ref(item, "edge", edges)
        if edge is not None:
            return _line_issue_xy(edge)
    node = _first_ref(item, "node", nodes)
    if node is not None:
        return _node_issue_xy(node, work_crs=work_crs)
    edge = _first_ref(item, "edge", edges)
    if edge is not None:
        return _line_issue_xy(edge)
    return None, None, None


def collect_issue_points(result):
    nodes = result.get("nodes") or {}
    edges = _edges_for_issues(result)
    source = _issue_source(result)
    tolerance = result.get("tolerance")
    work_crs = result.get("work_crs")
    grouped = {}
    seen = set()

    def add_row(layer_name, xy, crs, label, kind, severity, source_text, message="", marker="circle", fids=""):
        if not layer_name or not xy:
            return
        grouped.setdefault(layer_name, []).append({
            "xy": xy,
            "crs": crs,
            "label": label,
            "kind": kind,
            "severity": LEVEL_LABELS.get(severity, "警告"),
            "source": source_text,
            "message": message,
            "marker": marker,
            "fids": fids,
        })

    for bucket, items in (
        ("hard", result.get("hard") or []),
        ("soft", result.get("soft") or []),
        ("warn", result.get("warn") or []),
    ):
        for item in items:
            kind = item.get("kind") or "other"
            severity = item_level(item, bucket)
            layer_name = _issue_layer_name(kind, severity, source)
            if not layer_name:
                continue
            on_line = _issue_on_line(kind, item, nodes, edges)
            xy = crs = rec = None
            extra = []
            marker = "circle"
            fids = ""
            if on_line:
                edge = _first_ref(item, "edge", edges)
                if edge is None:
                    continue
                xy, crs, rec = _line_issue_xy(edge)
                if xy is None or rec is None:
                    continue
                lid = edge.get("layer_id") or ""
                if not lid and edge.get("layer") is not None:
                    try:
                        lid = edge["layer"].id()
                    except Exception:
                        lid = ""
                if edge.get("fid") is not None:
                    fids = "{}:{}".format(lid, edge.get("fid"))
                if result.get("kind") != "line_dir_free":
                    extra = _line_hint_parts(kind, edge, nodes, tolerance)
                marker = "diamond"
            else:
                node = _first_ref(item, "node", nodes)
                if node is None:
                    continue
                xy, crs, rec = _node_issue_xy(node, work_crs=work_crs)
                extra = _point_hint_parts(node)
                marker = "circle"
            if xy is None or rec is None:
                continue
            seen.add(kind)
            add_row(
                layer_name,
                xy,
                crs,
                _issue_feature_label(layer_name, rec, extra),
                kind,
                severity,
                source,
                item.get("message") or "",
                marker,
                fids,
            )
    if "dup_drop" not in seen:
        name = _issue_layer_name("dup_drop", "hard", source)
        for row in result.get("temp_dup") or []:
            add_row(
                name,
                row.get("xy"),
                row.get("crs"),
                _issue_feature_label(name, row, _temp_user_parts(row)),
                "dup_drop",
                "hard",
                source,
                row.get("user_label") or "",
                "circle",
            )
    if "multi_fat" not in seen:
        name = _issue_layer_name("multi_fat", "warn", source)
        for row in result.get("temp_multi") or []:
            add_row(
                name,
                row.get("xy"),
                row.get("crs"),
                _issue_feature_label(name, row, _temp_user_parts(row)),
                "multi_fat",
                "warn",
                source,
                row.get("user_label") or "",
                "circle",
            )
    return grouped


def _issue_short(kind):
    shorts = {
        "line_reversed": "反了",
        "pseudo_cycle": "伪成环",
        "cycle": "成环",
        "self_loop": "自环",
        "dangling": "一端空",
        "both_open": "两端空",
        "snap_ambig": "歧义",
        "unreached_edge": "未挂上",
        "unreached_node": "未挂上",
        "fat_branch": "分叉",
        "fat_multi_in": "多进线",
        "splice_multi_in": "多进线",
        "splice_trunk_branch": "主干分叉",
        "occ_in": "光交下游",
        "dup_drop": "重复皮线",
        "multi_fat": "多盒覆盖",
        "fat_no_drop": "无皮线",
        "splice_no_out": "无配线",
        "dir_conflict": "方向冲突",
    }
    if kind in shorts:
        return shorts[kind]
    return KIND_LAYER_TITLES.get(kind) or "问题"


def _same_spot_distance(crs):
    try:
        unit = crs.mapUnits()
    except Exception:
        unit = None
    try:
        degrees = QgsUnitTypes.DistanceDegrees
    except Exception:
        degrees = None
    if degrees is not None and unit == degrees:
        return 1e-6
    return 0.05


def _project_xy(xy, src_crs, fallback_crs):
    if not xy:
        return None
    project_crs = _project_crs()
    geom = QgsGeometry.fromPointXY(QgsPointXY(xy[0], xy[1]))
    moved = _transform_geom(geom, _xform(src_crs, project_crs)) if src_crs is not None else None
    if moved is None and fallback_crs is not None:
        moved = _transform_geom(geom, _xform(fallback_crs, project_crs))
    if moved is None or moved.isEmpty():
        moved = geom
    try:
        pt = moved.asPoint()
    except Exception:
        return None
    return pt.x(), pt.y()


def _collapse_stacked_issue_rows(rows, fallback_crs):
    """同一位置只留一个临时点。地图用一行短名，完整标题放进 detail。"""
    if not rows:
        return []
    limit = _same_spot_distance(_project_crs())
    groups = []
    buckets = {}
    for row in rows:
        xy = _project_xy(row.get("xy"), row.get("crs"), fallback_crs)
        if xy is None:
            continue
        cx = int(math.floor(xy[0] / limit))
        cy = int(math.floor(xy[1] / limit))
        found = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for group in buckets.get((cx + dx, cy + dy), ()):
                    gx, gy = group["xy"]
                    if math.hypot(xy[0] - gx, xy[1] - gy) <= limit:
                        found = group
                        break
                if found is not None:
                    break
            if found is not None:
                break
        if found is None:
            group = {"xy": xy, "rows": [row]}
            groups.append(group)
            buckets.setdefault((cx, cy), []).append(group)
        else:
            found["rows"].append(row)
    out = []
    for group in groups:
        members = group["rows"]
        if len(members) == 1:
            one = dict(members[0])
            one["detail"] = one.get("label") or ""
            out.append(one)
            continue
        merged = dict(members[0])
        shorts = []
        details = []
        messages = []
        fid_parts = []
        for index, item in enumerate(members, start=1):
            shorts.append("{}{}".format(_issue_short(item.get("kind")), index))
            text = (item.get("label") or "").strip()
            if text:
                details.append(text)
            msg = (item.get("message") or "").strip()
            if msg and msg not in messages:
                messages.append(msg)
            for part in str(item.get("fids") or "").split(","):
                part = part.strip()
                if part and part not in fid_parts:
                    fid_parts.append(part)
        merged["label"] = "、".join(shorts)
        merged["detail"] = "\n".join(details)
        merged["message"] = "\n".join(messages)
        merged["fids"] = ",".join(fid_parts)
        out.append(merged)
    return out


def add_fat_temp_layers(result):
    return add_issue_temp_layers([result])


def _audit_layer_name(name, severity):
    for prefix in ("硬错误_", "软错误_", "警告_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def add_issue_temp_layers(results, visible_kinds=None, group_root=None):
    added = []
    merged = {}
    fallback_crs = None
    sources = [_issue_source(result) for result in results or [] if result]
    clear_temp_layers(sources)
    source_of = {}
    for result in results or []:
        if not result:
            continue
        fallback_crs = result.get("work_crs") or fallback_crs
        source = _issue_source(result)
        for name, rows in collect_issue_points(result).items():
            if group_root and rows:
                severity = rows[0].get("severity") or ""
                name = _audit_layer_name(name, severity)
                for row in rows:
                    row["_group"] = severity if severity in LEVEL_GROUPS else "警告"
            merged.setdefault(name, []).extend(rows)
            source_of.setdefault(name, source)
    names = sorted(merged.keys())
    palette = _distinct_outline_colors(len(names))
    want = None if visible_kinds is None else set(visible_kinds)
    for i, name in enumerate(names):
        color = palette[i] if i < len(palette) else "#e53935"
        rows = _collapse_stacked_issue_rows(merged[name], fallback_crs)
        checked = True if want is None else any(row.get("kind") in want for row in rows)
        group_path = None
        if group_root and rows:
            group_path = [group_root, rows[0].get("_group") or "警告"]
        layer = _add_temp_points(
            name,
            rows,
            color,
            [
                ("label", QVariant.String),
                ("detail", QVariant.String),
                ("kind", QVariant.String),
                ("severity", QVariant.String),
                ("source", QVariant.String),
                ("message", QVariant.String),
                ("marker", QVariant.String),
                ("fids", QVariant.String),
            ],
            fallback_crs=fallback_crs,
            checked=checked,
            group_path=group_path,
            source=source_of.get(name) or "",
        )
        if layer is not None:
            added.append(layer.name())
    return added
