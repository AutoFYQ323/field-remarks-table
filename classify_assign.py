# -*- coding: utf-8 -*-
"""Read QGIS categorized / rule-based symbology and reverse it into field assignments."""

import re

from qgis.core import (
    NULL,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateTransform,
    QgsExpression,
    QgsExpressionNode,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsProject,
    QgsRuleBasedRenderer,
)

try:
    from qgis.PyQt.QtCore import QTimer
except Exception:
    QTimer = None

try:
    from qgis.PyQt.QtWidgets import QApplication
except Exception:
    QApplication = None

try:
    from qgis.core import QgsExpressionNodeBinaryOperator
except Exception:
    QgsExpressionNodeBinaryOperator = None


_FIELD_EQ_RE = re.compile(
    r'(?<![<>!])(?:"([^"]+)"|([A-Za-z_][\w]*))\s*=\s*'
    r"(?:'([^']*)'|\"([^\"]*)\"|(-?\d+(?:\.\d+)?)|([^\s,;]+))",
)


def unwrap_renderer(renderer):
    """Only unwrap known wrappers; cap depth so clones cannot loop forever."""
    wrappers = {
        "invertedPolygonRenderer",
        "pointCluster",
        "pointDisplacement",
        "mergedFeatureRenderer",
    }
    current = renderer
    for _ in range(3):
        if current is None:
            return None
        rtype = ""
        try:
            rtype = current.type()
        except Exception:
            break
        if rtype not in wrappers:
            break
        getter = getattr(current, "embeddedRenderer", None)
        if not callable(getter):
            break
        try:
            inner = getter()
        except Exception:
            break
        if inner is None or inner is current:
            break
        current = inner
    return current


def parse_assignment_text(text):
    """Parse NAME=1 FAT=2 / NAME = 1 AND FAT = 2 into {field: value}."""
    text = (text or "").strip()
    if not text:
        return {}
    out = {}
    for match in _FIELD_EQ_RE.finditer(text):
        field = (match.group(1) or match.group(2) or "").strip()
        if not field or field.upper() in ("AND", "OR", "NOT", "IN", "IS"):
            continue
        raw = match.group(3)
        if raw is None:
            raw = match.group(4)
        if raw is None:
            raw = match.group(5)
        if raw is None:
            raw = match.group(6)
        if raw is None:
            continue
        token = str(raw).strip().rstrip(",;")
        if token.upper() in ("AND", "OR", "NULL"):
            if token.upper() == "NULL":
                out[field] = NULL
            continue
        out[field] = _literal_value(token)
    return out


def assignments_from_expression(expr_text):
    text = (expr_text or "").strip()
    if not text:
        return {}
    exp = QgsExpression(text)
    if not exp.hasParserError():
        root = None
        try:
            root = exp.rootNode()
        except Exception:
            root = None
        out = {}
        if root is not None and _collect_eq_assignments(root, out):
            return out
    return parse_assignment_text(text)


def format_assignments(assignments):
    parts = []
    for name, value in assignments.items():
        if value is None or value == NULL:
            parts.append("%s=NULL" % name)
        elif isinstance(value, str):
            parts.append("%s=%s" % (name, value))
        else:
            parts.append("%s=%s" % (name, value))
    return ", ".join(parts)


MAX_CATEGORIES = 400


def layer_categories(layer):
    """
    List of dicts:
      label, assignments, hint, symbol, assignable
    """
    if layer is None or not hasattr(layer, "renderer"):
        return [], "请选择一个矢量图层"
    try:
        renderer = unwrap_renderer(layer.renderer())
        if renderer is None:
            return [], "当前图层没有符号化"
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            return _from_categorized(layer, renderer), ""
        if isinstance(renderer, QgsRuleBasedRenderer):
            return _from_rules(layer, renderer), ""
        if isinstance(renderer, QgsGraduatedSymbolRenderer):
            return [], "当前是渐变符号化，无法反推成确定字段值"
        rtype = ""
        try:
            rtype = renderer.type()
        except Exception:
            rtype = renderer.__class__.__name__
        return [], "当前符号化不是分类/规则（%s），没有可点选的分类" % rtype
    except Exception as exc:
        return [], "读取分类失败：%s" % exc


_WRITE_CHUNK = 2500


def attr_values_equal(current, target):
    cur_null = current is None or current == NULL
    tgt_null = target is None or target == NULL
    if cur_null or tgt_null:
        return cur_null and tgt_null
    if current == target:
        return True
    if isinstance(current, (int, float)) and isinstance(target, (int, float)):
        try:
            return float(current) == float(target)
        except (TypeError, ValueError):
            return False
    try:
        return str(current) == str(target)
    except Exception:
        return False


def assignment_key(assignments):
    if not assignments:
        return None
    parts = []
    for name in sorted(assignments.keys()):
        parts.append((str(name), _count_value_key(assignments[name])))
    return tuple(parts)


def _count_value_key(value):
    if value is None or value == NULL:
        return None
    if isinstance(value, bool):
        return ("b", value)
    if isinstance(value, (int, float)):
        try:
            return ("n", float(value))
        except (TypeError, ValueError):
            return ("s", str(value))
    return ("s", str(value))


def _name_index_map(layer, items):
    names = set()
    for info in items or []:
        names.update((info.get("assignments") or {}).keys())
    out = {}
    if layer is None:
        return out
    fields = layer.fields()
    for name in names:
        out[name] = fields.indexFromName(name)
    return out


def _bucket_keys(value):
    """Hashable buckets that overlap attr_values_equal (false positives OK, misses not)."""
    if value is None or value == NULL:
        return (("null",),)
    try:
        keys = [("s", str(value))]
    except Exception:
        return (("other",),)
    if isinstance(value, bool):
        keys.append(("n", float(value)))
        return tuple(keys)
    if isinstance(value, (int, float)):
        try:
            keys.append(("n", float(value)))
        except (TypeError, ValueError):
            pass
    return tuple(keys)


def _prepare_category_index(items, name_to_idx):
    """Precompute (field_idx, value) pairs and first-field buckets for fast matching."""
    prepared = []
    buckets = {}
    first_fields = []
    seen_fields = set()
    for info in items or []:
        assignments = info.get("assignments") or {}
        if not assignments:
            continue
        pairs = []
        valid = True
        for name, raw in assignments.items():
            idx = name_to_idx.get(name)
            if idx is None or idx < 0:
                valid = False
                break
            pairs.append((idx, raw))
        if not valid or not pairs:
            continue
        pi = len(prepared)
        prepared.append((pairs, assignment_key(assignments)))
        first_idx, first_raw = pairs[0]
        if first_idx not in seen_fields:
            seen_fields.add(first_idx)
            first_fields.append(first_idx)
        for bucket_key in _bucket_keys(first_raw):
            buckets.setdefault((first_idx, bucket_key), []).append(pi)
    return prepared, buckets, first_fields


def _match_prepared(feat, prepared, buckets, first_fields):
    if not prepared:
        return None
    seen = set()
    candidates = []
    for field_idx in first_fields:
        for bucket_key in _bucket_keys(feat.attribute(field_idx)):
            for pi in buckets.get((field_idx, bucket_key), ()):
                if pi in seen:
                    continue
                seen.add(pi)
                candidates.append(pi)
    if not candidates:
        return None
    candidates.sort()
    for pi in candidates:
        pairs, key = prepared[pi]
        matched = True
        for idx, raw in pairs:
            if not attr_values_equal(feat.attribute(idx), raw):
                matched = False
                break
        if matched:
            return key
    return None


def feature_assignment_key(feat, items, name_to_idx):
    prepared, buckets, first_fields = _prepare_category_index(items, name_to_idx)
    return _match_prepared(feat, prepared, buckets, first_fields)


def count_category_keys(layer, items):
    """One pass: {assignment_key: n}, leftover for unassignable/other."""
    counts = {}
    other = 0
    if layer is None or not items:
        return counts, other
    name_to_idx = _name_index_map(layer, items)
    prepared, buckets, first_fields = _prepare_category_index(items, name_to_idx)
    indices = [idx for idx in name_to_idx.values() if idx is not None and idx >= 0]
    req = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    if indices:
        req.setSubsetOfAttributes(indices)
    for feat in layer.getFeatures(req):
        key = _match_prepared(feat, prepared, buckets, first_fields)
        if key is None:
            other += 1
        else:
            counts[key] = counts.get(key, 0) + 1
    return counts, other


def category_keys_for_fids(layer, items, fids):
    """fid -> assignment_key or None (other)."""
    out = {}
    if layer is None or not fids:
        return out
    name_to_idx = _name_index_map(layer, items)
    prepared, buckets, first_fields = _prepare_category_index(items, name_to_idx)
    indices = [idx for idx in name_to_idx.values() if idx is not None and idx >= 0]
    req = (
        QgsFeatureRequest()
        .setFilterFids([int(fid) for fid in fids])
        .setFlags(QgsFeatureRequest.NoGeometry)
    )
    if indices:
        req.setSubsetOfAttributes(indices)
    for feat in layer.getFeatures(req):
        out[int(feat.id())] = _match_prepared(feat, prepared, buckets, first_fields)
    return out


def apply_assignments(layer, assignments, fids):
    """Write assignments to fids. Returns (updated_count, error, changed_fids)."""
    if layer is None:
        return 0, "没有图层", []
    if not assignments:
        return 0, "该分类没有可反推的字段值", []
    if not fids:
        return 0, "请先在地图或属性表中选中要素", []
    if not layer.isEditable():
        try:
            ok = layer.startEditing()
        except Exception:
            ok = False
        if not ok:
            return 0, "无法开始编辑该图层", []
    try:
        prepared = _prepare_assignments(layer, assignments)
    except ValueError as exc:
        return 0, str(exc), []
    if not prepared:
        return 0, "规则里的字段在当前图层上不存在", []
    changed = _assignments_to_write(layer, fids, prepared)
    if not changed:
        return 0, "", []
    updated, err = _write_attribute_map(layer, changed, "快速命名")
    return updated, err, list(changed.keys()) if updated else []


def layers_are_same(a, b):
    if a is None or b is None:
        return False
    try:
        return a.id() == b.id()
    except Exception:
        return a is b


def layer_geom_kind(layer):
    try:
        return int(layer.geometryType())
    except Exception:
        return -1


def _prepare_assignments(layer, assignments):
    prepared = []
    for name, raw in assignments.items():
        idx = layer.fields().indexFromName(name)
        if idx < 0:
            continue
        field = layer.fields().at(idx)
        prepared.append((idx, coerce_value_for_field(field, raw)))
    return prepared


def copy_geoms_and_assign(source, dest, fids, assignments):
    """Copy selected geometries from source into dest, then write dest's category values.

    Source layer is not modified. Dest does not gain source fields.
    Same layer is attribute-only (no copy).
    """
    if dest is None:
        return 0, "没有分类图层", None
    if not assignments:
        return 0, "该分类没有可反推的字段值", None
    if layers_are_same(source, dest):
        return apply_assignments(dest, assignments, fids)
    if source is None:
        return 0, "请先选中要复制的图层要素", None
    if layer_geom_kind(source) != layer_geom_kind(dest) or layer_geom_kind(dest) < 0:
        return 0, "几何类型不同，无法复制进分类图层（点/线/面须同类）", None
    if not fids:
        return 0, "请先在来源图层选中要素", None
    try:
        prepared = _prepare_assignments(dest, assignments)
    except ValueError as exc:
        return 0, str(exc), None
    if not prepared:
        return 0, "规则里的字段在分类图层上不存在", None
    if not dest.isEditable():
        try:
            ok = dest.startEditing()
        except Exception:
            ok = False
        if not ok:
            return 0, "无法开始编辑分类图层", None
    transform = None
    try:
        if source.crs() != dest.crs() and source.crs().isValid() and dest.crs().isValid():
            transform = QgsCoordinateTransform(source.crs(), dest.crs(), QgsProject.instance())
            if not transform.isValid():
                return 0, "来源图层和分类图层的坐标系无法转换，没有复制", None
    except Exception as exc:
        return 0, "坐标系转换失败，没有复制：%s" % exc, None
    try:
        dest_wkb = dest.wkbType()
    except Exception:
        dest_wkb = None
    dest.beginEditCommand("快速命名")
    added = 0
    try:
        req = QgsFeatureRequest().setFilterFids([int(fid) for fid in fids])
        try:
            req.setNoAttributes()
        except Exception:
            try:
                req.setSubsetOfAttributes([])
            except Exception:
                pass
        dest_fields = dest.fields()
        for feat in source.getFeatures(req):
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            g = QgsGeometry(geom)
            if transform is not None:
                if g.transform(transform) != 0:
                    dest.destroyEditCommand()
                    return 0, "要素 %s 坐标转换失败，没有复制" % feat.id(), None
            parts = _geometry_for_dest(g, dest_wkb)
            if not parts:
                dest.destroyEditCommand()
                return 0, "要素 %s 的几何无法转成分类图层的几何类型" % feat.id(), None
            for part in parts:
                newf = QgsFeature(dest_fields)
                newf.setGeometry(part)
                for idx, value in prepared:
                    newf.setAttribute(idx, value)
                if not dest.addFeature(newf):
                    dest.destroyEditCommand()
                    return 0, "复制要素失败", None
                added += 1
        if not added:
            dest.destroyEditCommand()
            return 0, "没有可复制的几何", None
        dest.endEditCommand()
        return added, "", None
    except Exception as exc:
        try:
            dest.destroyEditCommand()
        except Exception:
            pass
        return 0, str(exc), None


def _geometry_for_dest(geom, dest_wkb):
    """Single/multi part and Z/M adjusted copies of geom for a layer of dest_wkb."""
    if dest_wkb is None:
        return [geom]
    try:
        if geom.wkbType() == dest_wkb:
            return [geom]
    except Exception:
        return [geom]
    coerce = getattr(geom, "coerceToType", None)
    if callable(coerce):
        try:
            out = [g for g in coerce(dest_wkb) if g is not None and not g.isEmpty()]
            if out:
                return out
        except Exception:
            pass
    return []


def field_eq_expression(field, value):
    name = (field or "").replace('"', '""')
    quoted = '"%s"' % name
    if value is None or value == NULL:
        return "%s IS NULL" % quoted
    if isinstance(value, bool):
        return "%s = %s" % (quoted, "TRUE" if value else "FALSE")
    if isinstance(value, (int, float)):
        return "%s = %s" % (quoted, value)
    from .value_utils import value_text

    text = value_text(value).replace("'", "''")
    return "%s = '%s'" % (quoted, text)


def _assignments_to_write(layer, fids, prepared):
    """fid -> {field_idx: value} for features that still differ."""
    indices = [idx for idx, _ in prepared]
    wanted = {}
    fid_list = [int(fid) for fid in fids]
    for i in range(0, len(fid_list), _WRITE_CHUNK):
        batch = fid_list[i : i + _WRITE_CHUNK]
        req = (
            QgsFeatureRequest()
            .setFilterFids(batch)
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(indices)
        )
        for feat in layer.getFeatures(req):
            attr = {}
            for idx, value in prepared:
                if not attr_values_equal(feat.attribute(idx), value):
                    attr[idx] = value
            if attr:
                wanted[int(feat.id())] = attr
    return wanted


def _write_attribute_map(layer, changed, command_name):
    """Batch-write {fid: {field_idx: value}}. Returns (updated_count, error)."""
    if not changed:
        return 0, ""
    layer.beginEditCommand(command_name)
    updated = 0
    try:
        items = list(changed.items())
        try:
            for i in range(0, len(items), _WRITE_CHUNK):
                part = dict(items[i : i + _WRITE_CHUNK])
                if not bool(layer.changeAttributeValues(part)):
                    layer.destroyEditCommand()
                    return 0, "写入失败"
                updated += len(part)
            layer.endEditCommand()
            return updated, ""
        except TypeError:
            updated = 0
            for fid, attr in changed.items():
                try:
                    ok = layer.changeAttributeValues(int(fid), attr)
                except TypeError:
                    ok = True
                    for idx, value in attr.items():
                        if not layer.changeAttributeValue(int(fid), idx, value):
                            ok = False
                if ok:
                    updated += 1
            if updated:
                layer.endEditCommand()
                return updated, ""
            layer.destroyEditCommand()
            return 0, "写入失败"
    except Exception as exc:
        try:
            layer.destroyEditCommand()
        except Exception:
            pass
        return 0, str(exc)


def notify_open_attribute_tables(layer, field_names, force_reload=False):
    """Refresh an open 属性表 Plus after writes from another window."""
    if layer is None:
        return
    names = list(field_names or [])
    seen = set()
    candidates = []
    try:
        from qgis.utils import plugins

        for plugin in (plugins or {}).values():
            dlg = getattr(plugin, "dialog", None)
            if dlg is not None:
                candidates.append(dlg)
    except Exception:
        pass
    if QApplication is not None:
        try:
            candidates.extend(QApplication.topLevelWidgets())
        except Exception:
            pass
    for widget in candidates:
        marker = id(widget)
        if marker in seen:
            continue
        seen.add(marker)
        if getattr(widget, "_layer", None) is not layer:
            continue
        if force_reload:
            reload_fn = getattr(widget, "reload_table", None)
            if callable(reload_fn):
                try:
                    reload_fn()
                except Exception:
                    pass
                continue
        fn = getattr(widget, "refresh_after_external_edit", None)
        if not callable(fn):
            continue
        try:
            fn(names)
        except Exception:
            pass


def refresh_layer_after_assign(layer, iface=None, bump_feature_count=False):
    """Redraw the map only. Do not touch legend [n] (avoids painting stale counts)."""
    _ = bump_feature_count
    if layer is None:
        return
    try:
        layer.triggerRepaint()
    except Exception:
        pass
    if iface is None:
        return
    try:
        canvas = iface.mapCanvas()
        if canvas is not None:
            canvas.refresh()
    except Exception:
        pass


def refresh_legend_class_counts(layer):
    """Manual only. Mimic Layer Properties → OK: set the same renderer back.

    QGIS then drops the stuck per-class [n] cache and recounts itself.
    Does not change attributes, geometries, class values, or which classes
    are checked. The *project* may become dirty (style was set); this is
    not layer attribute edits and does not write shp/gpkg.
    """
    if layer is None:
        return "没有图层"
    renderer = None
    try:
        renderer = layer.renderer()
    except Exception:
        renderer = None
    if renderer is None:
        return "图层没有符号化"
    try:
        clone = renderer.clone()
    except Exception as exc:
        return "无法复制符号化：%s" % exc
    if clone is None:
        return "无法复制符号化"
    try:
        layer.setRenderer(clone)
    except Exception as exc:
        return str(exc)
    return ""


def save_edits_via_qgis(layer, iface):
    """Trigger QGIS Digitizing 'Save Layer Edits' for this layer. No custom recount."""
    if layer is None:
        return "没有图层"
    if iface is None:
        return "无法调用 QGIS 保存"
    try:
        if not layer.isEditable():
            return ""
    except Exception:
        return "图层无法保存"
    prev = None
    try:
        prev = iface.activeLayer()
    except Exception:
        prev = None
    try:
        if prev is None or not layers_are_same(prev, layer):
            iface.setActiveLayer(layer)
    except Exception:
        return "无法切到要保存的图层"
    action = None
    for name in ("actionSaveActiveLayerEdits", "actionSaveEdits"):
        getter = getattr(iface, name, None)
        if not callable(getter):
            continue
        try:
            action = getter()
        except Exception:
            action = None
        if action is not None:
            break
    if action is None:
        try:
            from qgis.PyQt.QtWidgets import QAction

            win = iface.mainWindow()
            for obj_name in ("mActionSaveEdits", "mActionSaveLayerEdits"):
                action = win.findChild(QAction, obj_name)
                if action is not None:
                    break
        except Exception:
            action = None
    if action is None:
        return "找不到 QGIS 自带的保存编辑"
    try:
        action.trigger()
    except Exception as exc:
        return str(exc)
    finally:
        if prev is not None and not layers_are_same(prev, layer):
            def _restore_active():
                try:
                    iface.setActiveLayer(prev)
                except Exception:
                    pass

            if QTimer is not None:
                QTimer.singleShot(0, _restore_active)
            else:
                _restore_active()
    return ""


def _from_categorized(layer, renderer):
    attr = (renderer.classAttribute() or "").strip().strip('"')
    field_names = _field_name_set(layer)
    is_field = attr in field_names
    if not is_field and attr:
        try:
            idx = layer.fields().lookupField(attr)
        except Exception:
            idx = -1
        if idx >= 0:
            attr = layer.fields().at(idx).name()
            is_field = True
    items = []
    try:
        categories = list(renderer.categories() or [])
    except Exception:
        return items
    for cat in categories:
        if len(items) >= MAX_CATEGORIES:
            break
        legend_on = True
        try:
            if hasattr(cat, "renderState"):
                legend_on = bool(cat.renderState())
        except Exception:
            legend_on = True
        value = cat.value()
        label = (cat.label() or "").strip() or _display_value(value)
        assignments = {}
        filter_expr = ""
        if is_field:
            if _is_blank_value(value):
                hint = "其它值 / 空类，无法反推赋值"
            else:
                assignments = {attr: value}
                hint = format_assignments(assignments)
                filter_expr = field_eq_expression(attr, value)
        else:
            # One expression for all classes: its own "a = b" parts say nothing about
            # which class is which, so only the class value / label can be reversed.
            assignments = parse_assignment_text(_display_value(value))
            if not assignments:
                assignments = parse_assignment_text(label)
            hint = (
                format_assignments(assignments)
                if assignments
                else "表达式分类无法反推字段值"
            )
        items.append(
            {
                "label": label,
                "assignments": assignments,
                "hint": hint,
                "filter_expr": filter_expr,
                "color": _symbol_color(cat.symbol() if hasattr(cat, "symbol") else None),
                "assignable": bool(assignments),
                "legend_on": legend_on,
            }
        )
    return items


def _from_rules(layer, renderer):
    items = []
    try:
        root = renderer.rootRule()
    except Exception:
        return items
    _walk_rules(root, items, [], set(), 0)
    return items


def _walk_rules(rule, items, inherited, seen, depth):
    if rule is None or depth > 30 or len(items) >= MAX_CATEGORIES:
        return
    marker = id(rule)
    if marker in seen:
        return
    seen.add(marker)
    legend_on = True
    try:
        if hasattr(rule, "active"):
            legend_on = bool(rule.active())
    except Exception:
        legend_on = True
    try:
        is_else = bool(hasattr(rule, "isElse") and rule.isElse())
    except Exception:
        is_else = False
    if is_else:
        label = ""
        color = None
        try:
            label = (rule.label() or "").strip()
            color = _symbol_color(rule.symbol()) if hasattr(rule, "symbol") else None
        except Exception:
            pass
        items.append(
            {
                "label": label or "ELSE（其余）",
                "assignments": {},
                "hint": "ELSE（其余）规则，无法反推赋值",
                "filter_expr": "",
                "color": color,
                "assignable": False,
                "legend_on": legend_on,
            }
        )
        return
    expr = ""
    try:
        expr = (rule.filterExpression() or "").strip()
    except Exception:
        expr = ""
    parts = list(inherited)
    if expr:
        parts.append(expr)
    children = []
    try:
        children = list(rule.children() or [])
    except Exception:
        children = []
    if children:
        for child in children:
            _walk_rules(child, items, parts, seen, depth + 1)
        return
    if not parts:
        return
    if len(items) >= MAX_CATEGORIES:
        return
    combined = " AND ".join("(%s)" % p if _needs_paren(p) else p for p in parts)
    label = ""
    try:
        label = (rule.label() or "").strip()
    except Exception:
        label = ""
    if not label:
        label = combined
    try:
        assignments = assignments_from_expression(combined)
    except Exception:
        assignments = {}
    if not assignments:
        assignments = parse_assignment_text(label)
    color = None
    try:
        if hasattr(rule, "symbol"):
            color = _symbol_color(rule.symbol())
    except Exception:
        color = None
    items.append(
        {
            "label": label,
            "assignments": assignments,
            "hint": format_assignments(assignments) if assignments else combined,
            "filter_expr": combined,
            "color": color,
            "assignable": bool(assignments),
            "legend_on": legend_on,
        }
    )


def _symbol_color(symbol):
    if symbol is None:
        return None
    try:
        color = symbol.color()
        if color is not None:
            return color.name()
    except Exception:
        return None
    return None


def _needs_paren(text):
    upper = (text or "").upper()
    return " AND " in upper or " OR " in upper


def _collect_eq_assignments(node, out):
    if node is None:
        return False
    try:
        ntype = node.nodeType()
    except Exception:
        return False
    nt_bin = getattr(QgsExpressionNode, "ntBinaryOperator", None)
    if nt_bin is not None and ntype == nt_bin:
        try:
            op = node.op()
        except Exception:
            return False
        bo_and = _bin_op("boAnd")
        bo_eq = _bin_op("boEQ")
        bo_is = _bin_op("boIs")
        if bo_and is not None and op == bo_and:
            return _collect_eq_assignments(node.opLeft(), out) and _collect_eq_assignments(
                node.opRight(), out
            )
        if (bo_eq is not None and op == bo_eq) or (bo_is is not None and op == bo_is):
            field, value = _eq_sides(node.opLeft(), node.opRight())
            if not field:
                return False
            out[field] = value
            return True
        return False
    return False


def _eq_sides(left, right):
    field = _column_name(left)
    if field:
        return field, _node_literal(right)
    field = _column_name(right)
    if field:
        return field, _node_literal(left)
    return "", None


def _column_name(node):
    if node is None:
        return ""
    try:
        ntype = node.nodeType()
    except Exception:
        return ""
    nt_col = getattr(QgsExpressionNode, "ntColumnRef", None)
    if nt_col is not None and ntype == nt_col:
        try:
            return (node.name() or "").strip()
        except Exception:
            return ""
    return ""


def _node_literal(node):
    if node is None:
        return None
    try:
        ntype = node.nodeType()
    except Exception:
        return None
    nt_lit = getattr(QgsExpressionNode, "ntLiteral", None)
    if nt_lit is not None and ntype == nt_lit:
        try:
            return node.value()
        except Exception:
            return None
    return None


def _bin_op(name):
    if QgsExpressionNodeBinaryOperator is None:
        return None
    value = getattr(QgsExpressionNodeBinaryOperator, name, None)
    if value is not None:
        return value
    nested = getattr(QgsExpressionNodeBinaryOperator, "BinaryOperator", None)
    if nested is not None:
        return getattr(nested, name, None)
    return None


def _field_name_set(layer):
    names = set()
    try:
        for field in layer.fields():
            names.add(field.name())
    except Exception:
        pass
    return names


def _is_blank_value(value):
    if value is None or value == NULL:
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "null"


def _display_value(value):
    from .value_utils import value_text

    return value_text(value)


def _literal_value(token):
    token = (token or "").strip()
    if token.lower() == "null":
        return NULL
    if re.match(r"^-?\d+$", token):
        try:
            return int(token)
        except ValueError:
            return token
    if re.match(r"^-?\d+\.\d+$", token):
        try:
            return float(token)
        except ValueError:
            return token
    return token


def coerce_value_for_field(field, raw):
    """Field-ready value. Raises ValueError when raw cannot be stored in the field."""
    from .value_utils import coerce_for_field

    status, value, note = coerce_for_field(field, raw)
    if status == "invalid":
        raise ValueError("字段「%s」存不下值「%s」（%s）" % (field.name(), raw, note))
    return value
