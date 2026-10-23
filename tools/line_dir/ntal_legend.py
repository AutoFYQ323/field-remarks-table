# -*- coding: utf-8 -*-
from ...i18n import tr
"""Read layer categorized / rule / graduated legend classes and match features."""

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsGraduatedSymbolRenderer,
    QgsRenderContext,
    QgsRuleBasedRenderer,
)

from .layer_picker import attr_key

WRAPPER_TYPES = {
    "invertedPolygonRenderer",
    "pointCluster",
    "pointDisplacement",
    "mergedFeatureRenderer",
}


def unwrap_renderer(renderer):
    current = renderer
    for _ in range(3):
        if current is None:
            return None
        rtype = ""
        try:
            rtype = current.type()
        except Exception:
            break
        if rtype not in WRAPPER_TYPES:
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


def _rule_children(rule):
    try:
        kids = list(rule.children() or [])
    except Exception:
        kids = []
    if kids:
        return kids
    try:
        count = int(rule.childrenCount())
    except Exception:
        return []
    out = []
    for i in range(count):
        try:
            child = rule.children()[i]
        except Exception:
            child = None
        if child is not None:
            out.append(child)
    return out


def _activate_rule_tree(renderer):
    """规则树里关掉的分类也打开。只改渲染器副本。"""
    getter = getattr(renderer, "rootRule", None)
    if not callable(getter):
        return
    try:
        root = getter()
    except Exception:
        return
    stack = [root]
    while stack:
        rule = stack.pop()
        if rule is None:
            continue  # nosec B112
        try:
            rule.setActive(True)
        except Exception:
            pass  # nosec B110
        try:
            key = str(rule.ruleKey() or "")
        except Exception:
            key = ""
        if key:
            try:
                renderer.checkLegendSymbolItem(key, True)
            except Exception:
                pass  # nosec B110
        stack.extend(_rule_children(rule))


def _enable_legend_items(renderer, include_unchecked=False):
    """副本上打开全部分类。图层面板的显示勾选不参与筛选。"""
    if renderer is None:
        return
    if include_unchecked:
        _activate_rule_tree(renderer)
    try:
        items = list(renderer.legendSymbolItems() or [])
    except Exception:
        return
    for item in items:
        try:
            key = str(item.ruleKey() or "")
        except Exception:
            key = ""
        if not key:
            continue  # nosec B112
        try:
            renderer.checkLegendSymbolItem(key, True)
        except Exception:
            continue  # nosec B112


def _clone_renderer(layer, include_unchecked=False):
    if layer is None or not hasattr(layer, "renderer"):
        return None
    renderer = unwrap_renderer(layer.renderer())
    if renderer is None:
        return None
    try:
        clone = renderer.clone()
        if clone is not None:
            _enable_legend_items(clone, include_unchecked=include_unchecked)
            return clone
    except Exception:
        pass  # nosec B110
    return renderer


def _is_classified(renderer):
    return isinstance(
        renderer,
        (QgsCategorizedSymbolRenderer, QgsRuleBasedRenderer, QgsGraduatedSymbolRenderer),
    )


def _as_key_set(keys):
    if not keys:
        return set()
    try:
        return set(str(k) for k in keys)
    except TypeError:
        return {str(keys)}


def _item_color(item):
    try:
        symbol = item.symbol()
    except Exception:
        symbol = None
    if symbol is None:
        return ""
    try:
        color = symbol.color()
        if color is not None:
            return color.name()
    except Exception:
        return ""
    return ""


def _leaf_rule_items(renderer):
    getter = getattr(renderer, "rootRule", None)
    if not callable(getter):
        return []
    try:
        root = getter()
    except Exception:
        return []
    items = []
    stack = [(root, False)]
    while stack:
        rule, is_root = stack.pop()
        if rule is None:
            continue  # nosec B112
        kids = _rule_children(rule)
        if kids:
            for child in kids:
                stack.append((child, False))
            continue
        if is_root:
            continue
        try:
            key = str(rule.ruleKey() or "")
        except Exception:
            key = ""
        if not key:
            continue  # nosec B112
        label = ""
        try:
            label = (rule.label() or "").strip()
        except Exception:
            label = ""
        color = ""
        try:
            symbol = rule.symbol()
            if symbol is not None and symbol.color() is not None:
                color = symbol.color().name()
        except Exception:
            color = ""
        items.append({"key": key, "label": label or key, "color": color})
    return items


def list_layer_categories(layer, include_unchecked=False):
    """Return (items, error). items: key / label / color."""
    if layer is None or not hasattr(layer, "renderer"):
        return [], tr("请选择一个矢量图层")
    renderer = unwrap_renderer(layer.renderer())
    if renderer is None:
        return [], tr("当前图层没有符号化")
    if not _is_classified(renderer):
        rtype = ""
        try:
            rtype = renderer.type()
        except Exception:
            rtype = renderer.__class__.__name__
        return [], tr("当前符号化不是分类/规则（%s），没有可筛选的分组") % rtype
    raw = []
    try:
        raw = list(renderer.legendSymbolItems() or [])
    except Exception as exc:
        return [], tr("读取分类失败：%s") % exc
    parent_keys = set()
    for item in raw:
        try:
            parent = item.parentRuleKey() or ""
        except Exception:
            parent = ""
        if parent:
            parent_keys.add(str(parent))
    items = []
    seen = set()

    def _rule_key(item):
        try:
            return str(item.ruleKey() or "")
        except Exception:
            return ""

    source = [item for item in raw if _rule_key(item) not in parent_keys] or raw
    for item in source:
        key = _rule_key(item)
        if not key or key in seen:
            continue  # nosec B112
        seen.add(key)
        label = ""
        try:
            label = (item.label() or "").strip()
        except Exception:
            label = ""
        items.append({
            "key": key,
            "label": label or key,
            "color": _item_color(item),
        })
    if include_unchecked:
        for extra in _leaf_rule_items(renderer):
            key = extra.get("key") or ""
            if not key or key in seen:
                continue  # nosec B112
            seen.add(key)
            items.append(extra)
    if not items:
        return [], tr("当前符号化没有可勾选的分组")
    return items, ""


def filter_is_narrow(flt):
    """配置里勾了分类筛选（不是「全部」）。"""
    if not flt:
        return False
    if flt.get("keys") is not None:
        return True
    if flt.get("field") is not None and flt.get("values") is not None:
        return True
    return False


def _legend_label_map(layer, flt=None):
    mapping = {}
    items, _err = list_layer_categories(layer)
    for item in items:
        key = item.get("key")
        if key:
            mapping[str(key)] = item.get("label") or str(key)
    flt = flt or {}
    keys = [str(k) for k in (flt.get("keys") or [])]
    labels = list(flt.get("labels") or [])
    for i, key in enumerate(keys):
        if i < len(labels) and labels[i]:
            mapping[key] = labels[i]
    return mapping


def _render_context(layer):
    """带工程/图层表达式上下文，规则里用 @project_*、@layer_* 变量时才判得对。"""
    ctx = QgsRenderContext()
    try:
        ctx.setExpressionContext(
            QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        )
    except Exception:
        pass  # nosec B110
    return ctx


def remap_filter_keys(layer, flt, include_unchecked=False):
    """把配置里存的分类 key 对到当前符号。

    分类重排或规则重建后 key 会变；此时按保存的分类名称找回。
    返回 (当前可用的 key 集合, 对不上的个数)。
    """
    flt = flt or {}
    keys = [str(k) for k in (flt.get("keys") or [])]
    labels = list(flt.get("labels") or [])
    items, _err = list_layer_categories(layer, include_unchecked=include_unchecked)
    current = {}
    by_label = {}
    for item in items:
        key = str(item.get("key") or "")
        label = str(item.get("label") or key).strip()
        current[key] = label
        by_label.setdefault(label, []).append(key)
    allowed = set()
    stale = 0
    for i, key in enumerate(keys):
        label = str(labels[i]).strip() if i < len(labels) and labels[i] is not None else ""
        if key in current and (not label or current[key] == label):
            allowed.add(key)
        elif label and label in by_label:
            allowed.update(by_label[label])
            stale += 1
        elif key in current:
            allowed.add(key)
            stale += 1
        else:
            stale += 1
    return allowed, stale


def count_legend_keys(layer, keys, include_unchecked=False):
    counts = {str(k): 0 for k in keys}
    if layer is None or not keys:
        return counts
    rend = _clone_renderer(layer, include_unchecked=include_unchecked)
    if rend is None:
        return counts
    ctx = _render_context(layer)
    started = False
    try:
        try:
            result = rend.startRender(ctx, layer.fields())
        except Exception:
            result = False
        if result is False:
            return counts
        started = True
        for feat in layer.getFeatures():
            try:
                found = rend.legendKeysForFeature(feat, ctx)
            except Exception:
                continue  # nosec B112
            for key in _as_key_set(found):
                if key in counts:
                    counts[key] += 1
    finally:
        if started:
            try:
                rend.stopRender(ctx)
            except Exception:
                pass  # nosec B110
    return counts


class FeatureCategoryFilter(object):
    """Allow features by renderer legend keys, or legacy field+values filter."""

    def __init__(self, layer, attr_filter, include_unchecked=False):
        self._mode = "all"
        self._allowed = None
        self._field = ""
        self._renderer = None
        self._ctx = None
        self._started = False
        self._key_labels = {}
        flt = attr_filter or {}
        if flt.get("keys") is not None:
            keys, _stale = remap_filter_keys(layer, flt, include_unchecked=include_unchecked)
            if not keys:
                self._mode = "none"
                return
            rend = _clone_renderer(layer, include_unchecked=include_unchecked)
            if rend is None:
                self._mode = "none"
                return
            ctx = _render_context(layer)
            try:
                result = rend.startRender(ctx, layer.fields())
            except Exception:
                result = False
            if result is False:
                self._mode = "none"
                return
            self._mode = "keys"
            self._allowed = set(keys)
            self._renderer = rend
            self._ctx = ctx
            self._started = True
            self._key_labels = _legend_label_map(layer, flt)
            return
        field = flt.get("field")
        values = flt.get("values")
        if field and values is not None:
            self._mode = "field"
            self._field = field
            self._allowed = set(attr_key(v) for v in values)

    def allow(self, feat):
        if self._mode == "all":
            return True
        if self._mode == "none":
            return False
        if self._mode == "field":
            if self._field not in feat.fields().names():
                return False
            return attr_key(feat[self._field]) in self._allowed
        try:
            found = self._renderer.legendKeysForFeature(feat, self._ctx)
        except Exception:
            return False
        return bool(self._allowed.intersection(_as_key_set(found)))

    def cat_label(self, feat):
        """要素自己的分类名。未筛分类时为空。"""
        if self._mode == "field":
            if self._field not in feat.fields().names():
                return ""
            return str(attr_key(feat[self._field]) or "").strip()
        if self._mode != "keys":
            return ""
        try:
            found = self._renderer.legendKeysForFeature(feat, self._ctx)
        except Exception:
            return ""
        seen = set()
        for key in _as_key_set(found):
            if key not in self._allowed:
                continue  # nosec B112
            text = (self._key_labels.get(key) or key or "").strip()
            if text and text not in seen:
                seen.add(text)
                return text
        return ""

    def close(self):
        if self._started and self._renderer is not None and self._ctx is not None:
            try:
                self._renderer.stopRender(self._ctx)
            except Exception:
                pass  # nosec B110
        self._started = False
        self._renderer = None
        self._ctx = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
