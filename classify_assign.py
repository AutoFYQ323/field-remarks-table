# -*- coding: utf-8 -*-
"""Read QGIS categorized / rule-based symbology and reverse it into field assignments."""

import re

from .i18n import tr

from qgis.core import (
    NULL,
    QgsCategorizedSymbolRenderer,
    QgsExpression,
    QgsExpressionNode,
    QgsGraduatedSymbolRenderer,
    QgsRuleBasedRenderer,
)

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
        return [], tr("请选择一个矢量图层")
    try:
        renderer = unwrap_renderer(layer.renderer())
        if renderer is None:
            return [], tr("当前图层没有符号化")
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            return _from_categorized(layer, renderer), ""
        if isinstance(renderer, QgsRuleBasedRenderer):
            return _from_rules(layer, renderer), ""
        if isinstance(renderer, QgsGraduatedSymbolRenderer):
            return [], tr("当前是渐变符号化，无法反推成确定字段值")
        rtype = ""
        try:
            rtype = renderer.type()
        except Exception:
            rtype = renderer.__class__.__name__
        return [], tr("当前符号化不是分类/规则（%s），没有可点选的分类") % rtype
    except Exception as exc:
        return [], tr("读取分类失败：%s") % exc


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
                hint = tr("其它值 / 空类，无法反推赋值")
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
                else tr("表达式分类无法反推字段值")
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
            pass  # nosec B110
        items.append(
            {
                "label": label or tr("ELSE（其余）"),
                "assignments": {},
                "hint": tr("ELSE（其余）规则，无法反推赋值"),
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
        pass  # nosec B110
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
        raise ValueError(tr("字段「%s」存不下值「%s」（%s）") % (field.name(), raw, note))
    return value
