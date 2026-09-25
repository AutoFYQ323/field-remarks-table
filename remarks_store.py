# -*- coding: utf-8 -*-
"""Field-remark packs: layer label/notes + per-field label/notes/meanings.

Keyed by layer name + field name (not layer id). Packs are user-global
(QGIS profile JSON), so the same dropdown works in every project.
Old .qgz copies are absorbed once, then profile is the source of truth.

JSON `version` / PACK_FORMAT is the data format (independent of plugin version).
Read through upgrade_to_current / normalize_*; write only the current keys.
Older files are converted on load and written back.
"""

import copy
import json
import os
import re

from qgis.core import QgsProject


SCOPE = "AttributeTablePlus"
KEY = "remarks_json"
SESSION_KEY = "remarks_session"
LAYER_ITEM_KEY = "__layer__"
GLOBAL_STORE_NAME = "remarks_session.json"
PACK_KIND = "attribute_table_plus.remark_pack"
PACK_FORMAT = 2
DATA_VERSION = 2
PLACEHOLDER_NAME = "默认（不可修改）"
PLACEHOLDER_ALIASES = (PLACEHOLDER_NAME, "默认")


def is_placeholder_name(name):
    return (name or "").strip() in PLACEHOLDER_ALIASES


def empty_data():
    return {"version": DATA_VERSION, "layers": {}}


def empty_layer():
    return {"label": "", "notes": "", "fields": {}}


def empty_field():
    return {"label": "", "notes": "", "meanings": []}


def normalize_notes(text):
    """Keep internal newlines; drop trailing blank lines. Missing key → empty."""
    if text is None:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip()


def _notes_lines(text):
    out = []
    seen = set()
    for line in normalize_notes(text).splitlines():
        item = line.rstrip()
        if not item.strip() or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def layer_needs_upgrade(data):
    """True if a layer blob still has pre-v2 keys (note / layer meanings)."""
    if not isinstance(data, dict):
        return False
    return "note" in data or "meanings" in data


def layers_need_upgrade(layers_map):
    if not isinstance(layers_map, dict):
        return False
    return any(layer_needs_upgrade(entry) for entry in layers_map.values())


def raw_packs_need_upgrade(parsed):
    if not isinstance(parsed, dict):
        return False
    packs = parsed.get("packs")
    if isinstance(packs, list) and packs:
        for item in packs:
            if isinstance(item, dict) and layers_need_upgrade(item.get("layers") or {}):
                return True
        return False
    if isinstance(parsed.get("layers"), dict):
        return layers_need_upgrade(parsed.get("layers") or {})
    pack = parsed.get("pack")
    if isinstance(pack, dict):
        return layers_need_upgrade(pack.get("layers") or {})
    return False


def upgrade_layer(data):
    """Any older layer blob → current {label, notes, fields}."""
    if not isinstance(data, dict):
        return empty_layer()
    fields_in = data.get("fields") or {}
    fields = {}
    if isinstance(fields_in, dict):
        for name, entry in fields_in.items():
            key = str(name).strip()
            if not key or key == LAYER_ITEM_KEY:
                continue
            fields[key] = normalize_field(entry)
    label = str(data.get("label") or "").strip()
    note = str(data.get("note") or "").strip()
    if not label:
        label = note
    parts = _notes_lines(data.get("notes"))
    seen = set(parts)
    extras = []
    if note and note != label:
        extras.append(note)
    extras.extend(normalize_presets(data.get("meanings")))
    for line in extras:
        text = (line or "").strip()
        if not text or text == label or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return {
        "label": label,
        "notes": "\n".join(parts),
        "fields": fields,
    }


def upgrade_layers_map(layers_map):
    """Return (current layers map, changed)."""
    out = {}
    changed = False
    if not isinstance(layers_map, dict):
        return out, False
    for name, entry in layers_map.items():
        key = str(name).strip()
        if not key:
            continue
        if layer_needs_upgrade(entry):
            changed = True
        out[key] = upgrade_layer(entry)
    return out, changed


def upgrade_to_current(data):
    """Return (current {version, layers}, changed). Current format is the only output."""
    if not isinstance(data, dict):
        return empty_data(), False
    layers_in = data.get("layers")
    if not isinstance(layers_in, dict):
        layers_in = {}
    try:
        ver = int(data.get("version") or 1)
    except (TypeError, ValueError):
        ver = 1
    layers, layer_changed = upgrade_layers_map(layers_in)
    changed = layer_changed or ver != DATA_VERSION
    return {"version": DATA_VERSION, "layers": layers}, changed


def normalize_presets(presets):
    if presets is None:
        return []
    if isinstance(presets, str):
        items = presets.splitlines()
    elif isinstance(presets, (list, tuple)):
        items = presets
    else:
        items = [presets]
    out = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


QGIS_MEANING_PREFIX = "QGIS:"
VAR_TOKEN_RE = re.compile(r"\{\{([^{}]+)\}\}")


def empty_variables():
    return []


def normalize_variable(item):
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or item.get("name") or item.get("label") or "").strip()
    if not title or "{{" in title or "}}" in title:
        return None
    value = item.get("value")
    if value is None:
        value = item.get("content")
    return {"title": title, "value": "" if value is None else str(value)}


def normalize_variables(items):
    out = []
    seen = set()
    source = items
    if items is None:
        source = []
    elif not isinstance(items, (list, tuple)):
        source = [items]
    for item in source:
        variable = normalize_variable(item)
        if variable is None or variable["title"] in seen:
            continue
        seen.add(variable["title"])
        out.append(variable)
    return out


def variable_map(variables):
    return {item["title"]: item["value"] for item in normalize_variables(variables)}


def meaning_has_var_tokens(text):
    return bool(VAR_TOKEN_RE.search("" if text is None else str(text)))


def template_parts(text):
    """Split '{{城市}}123' into [('var', '城市'), ('text', '123')]."""
    text = "" if text is None else str(text)
    parts = []
    pos = 0
    for match in VAR_TOKEN_RE.finditer(text):
        if match.start() > pos:
            parts.append(("text", text[pos : match.start()]))
        title = (match.group(1) or "").strip()
        if title:
            parts.append(("var", title))
        pos = match.end()
    if pos < len(text):
        parts.append(("text", text[pos:]))
    return parts


def format_var_template(text):
    """'{{城市}}123' -> '城市+123'. No tokens -> original text."""
    parts = template_parts(text)
    if not any(kind == "var" for kind, _piece in parts):
        return "" if text is None else str(text)
    shown = []
    for kind, piece in parts:
        if kind == "var":
            shown.append(piece)
        elif piece:
            shown.append(piece)
    return "+".join(shown) if shown else ("" if text is None else str(text))


def resolve_var_template(text, variables):
    """Return (resolved, missing_titles). Missing titles are unique, first-seen order."""
    text = "" if text is None else str(text)
    mapping = variable_map(variables)
    missing = []
    seen = set()
    out = []
    for kind, piece in template_parts(text):
        if kind == "text":
            out.append(piece)
            continue
        if piece not in mapping:
            if piece not in seen:
                seen.add(piece)
                missing.append(piece)
            continue
        out.append(mapping[piece])
    if not any(kind == "var" for kind, _piece in template_parts(text)):
        return text, []
    return "".join(out), missing


def pack_variables(pack):
    if not isinstance(pack, dict):
        return []
    return normalize_variables(pack.get("variables"))


def unpack_pack_item(item):
    """Accept (name, layers) or (name, layers, variables)."""
    if isinstance(item, dict):
        return (
            str(item.get("name") or "").strip() or "未命名",
            item.get("layers") or {},
            normalize_variables(item.get("variables")),
        )
    name = item[0] if item else "未命名"
    layers = item[1] if item and len(item) > 1 else {}
    variables = item[2] if item and len(item) > 2 else []
    return name, layers, normalize_variables(variables)


def parse_meaning(text):
    """'盒子=FAT' -> (盒子, FAT). No '=' -> both sides the same."""
    cn, value, _kind = parse_meaning_full(text)
    return cn, value


def parse_meaning_full(text):
    """Return (cn, value, kind) where kind is const or expr."""
    text = (text or "").strip()
    if not text:
        return "", "", "const"
    kind = "const"
    if "=" in text:
        left, right = text.split("=", 1)
        left, right = left.strip(), right.strip()
    else:
        left, right = text, text
    if right.upper().startswith(QGIS_MEANING_PREFIX):
        kind = "expr"
        right = right[len(QGIS_MEANING_PREFIX) :].strip()
    elif left.upper().startswith(QGIS_MEANING_PREFIX) and "=" not in text:
        kind = "expr"
        left = left[len(QGIS_MEANING_PREFIX) :].strip()
        right = left
    return left, right, kind


def normalize_meaning(item):
    if isinstance(item, dict):
        cn = str(item.get("cn") or item.get("label") or "").strip()
        value = str(item.get("value") or item.get("code") or "").strip()
        kind = (item.get("kind") or "const").strip().lower()
        if kind not in ("const", "expr"):
            kind = "const"
        if kind == "expr" and value.upper().startswith(QGIS_MEANING_PREFIX):
            value = value[len(QGIS_MEANING_PREFIX) :].strip()
        if not cn and not value:
            return None
        return {"cn": cn or value, "value": value or cn, "kind": kind}
    text = str(item).strip() if item is not None else ""
    if not text:
        return None
    cn, value, kind = parse_meaning_full(text)
    if not cn and not value:
        return None
    return {"cn": cn or value, "value": value or cn, "kind": kind}


def normalize_meanings(items):
    out = []
    seen = set()
    source = items
    if items is None:
        source = []
    elif isinstance(items, str):
        source = items.splitlines()
    elif not isinstance(items, (list, tuple)):
        source = [items]
    for item in source:
        meaning = normalize_meaning(item)
        if meaning is None:
            continue
        key = (meaning["kind"], meaning["cn"], meaning["value"])
        if key in seen:
            continue
        seen.add(key)
        out.append(meaning)
    return out


def meaning_display(item):
    meaning = normalize_meaning(item)
    if meaning is None:
        return ""
    if meaning["kind"] == "expr":
        if meaning["cn"] and meaning["cn"] != meaning["value"]:
            return "%s=%s%s" % (meaning["cn"], QGIS_MEANING_PREFIX, meaning["value"])
        return "%s%s" % (QGIS_MEANING_PREFIX, meaning["value"])
    shown = meaning["value"]
    if meaning_has_var_tokens(shown):
        shown = format_var_template(shown)
    return format_meaning(meaning["cn"], shown)


def meaning_kind(item):
    meaning = normalize_meaning(item)
    if meaning is None:
        return "const"
    return meaning["kind"]


def meaning_payload(item):
    meaning = normalize_meaning(item)
    if meaning is None:
        return {"kind": "const", "value": "", "text": ""}
    return {
        "kind": meaning["kind"],
        "value": meaning["value"],
        "text": meaning_display(meaning),
    }


def meaning_resolved_tip(item, variables=None):
    """List/hover line: '编号=城市+123 → CITY123' or missing-variable note."""
    meaning = normalize_meaning(item)
    text = meaning_display(meaning)
    if not meaning or not text:
        return text
    if meaning.get("kind") == "expr":
        return text
    raw = meaning.get("value") or ""
    if not meaning_has_var_tokens(raw):
        return text
    resolved, missing = resolve_var_template(raw, variables)
    if missing:
        return "%s（缺少变量：%s）" % (text, "、".join(missing))
    if resolved != format_var_template(raw):
        return "%s → %s" % (text, resolved)
    return text


def format_hover_text(name, label="", meanings=None, notes="", variables=None):
    """Field-header tooltip: Chinese name, notes, then meaning lines.

    Original field name is omitted when any of those is present; otherwise
    fall back to the field name so an empty column is not a blank tooltip.
    """
    name = (name or "").strip()
    label = (label or "").strip()
    notes = normalize_notes(notes)
    lines = []
    if label:
        lines.append(label)
    for line in notes.splitlines():
        text = line.rstrip()
        if text.strip():
            lines.append(text)
    for item in meanings or []:
        if isinstance(item, dict) or meaning_has_var_tokens(str(item) if item is not None else ""):
            text = meaning_resolved_tip(item, variables)
        else:
            text = meaning_display(item) if not isinstance(item, str) else str(item).strip()
        if text:
            lines.append(text)
    if lines:
        return "\n".join(lines)
    return name


def format_meaning(left, right, kind="const"):
    left = (left or "").strip()
    right = (right or "").strip()
    if kind == "expr":
        body = "%s%s" % (QGIS_MEANING_PREFIX, right)
        if left and left != right:
            return "%s=%s" % (left, body)
        return body
    if left and right and left != right:
        return f"{left}={right}"
    return left or right


def meaning_write_value(text):
    """Value written into the attribute cell: right-hand side of 盒子=FAT."""
    meaning = normalize_meaning(text)
    if meaning is None:
        return (text or "").strip()
    return meaning["value"]


def normalize_field(data):
    if not isinstance(data, dict):
        return empty_field()
    meanings = data.get("meanings")
    if meanings is None:
        meanings = data.get("presets")
    return {
        "label": str(data.get("label") or "").strip(),
        "notes": normalize_notes(data.get("notes")),
        "meanings": normalize_meanings(meanings),
    }


def normalize_layer(data):
    return upgrade_layer(data)


def normalize_data(data):
    upgraded, _changed = upgrade_to_current(data)
    return upgraded


def field_is_empty(entry):
    entry = normalize_field(entry)
    return not entry["label"] and not entry["notes"] and not entry["meanings"]


def layer_is_empty(entry):
    entry = normalize_layer(entry)
    if entry.get("label") or entry.get("notes"):
        return False
    return all(field_is_empty(v) for v in entry["fields"].values())


def prune_data(data):
    data = normalize_data(data)
    layers = {}
    for name, entry in data["layers"].items():
        fields = {
            fname: fentry
            for fname, fentry in entry["fields"].items()
            if not field_is_empty(fentry)
        }
        cleaned = {
            "label": entry.get("label") or "",
            "notes": normalize_notes(entry.get("notes")),
            "fields": fields,
        }
        if not layer_is_empty(cleaned):
            layers[name] = cleaned
    return {"version": DATA_VERSION, "layers": layers}


class RemarksStore:
    """Read/write the project remarks dictionary."""

    def __init__(self):
        self._cache = None

    def invalidate(self, *_args):
        self._cache = None

    def data(self):
        if self._cache is not None:
            return self._cache
        self._cache = self._read_project()
        return self._cache

    def _read_project(self):
        try:
            text, ok = QgsProject.instance().readEntry(SCOPE, KEY, "")
        except Exception:
            return empty_data()
        if not ok or not text:
            return empty_data()
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            return empty_data()
        return normalize_data(parsed)

    def save(self, data=None):
        if data is None:
            data = self.data()
        cleaned = prune_data(data)
        payload = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
        QgsProject.instance().writeEntry(SCOPE, KEY, payload)
        try:
            QgsProject.instance().setDirty(True)
        except Exception:
            pass
        self._cache = cleaned
        return cleaned

    def layer_entry(self, layer_name):
        name = (layer_name or "").strip()
        if not name:
            return empty_layer()
        layers = self.data().get("layers") or {}
        return normalize_layer(layers.get(name) or empty_layer())

    def layer_note(self, layer_name):
        return self.layer_entry(layer_name).get("notes") or ""

    def set_layer_note(self, layer_name, note):
        name = (layer_name or "").strip()
        if not name:
            return
        data = normalize_data(self.data())
        entry = normalize_layer(data["layers"].get(name) or empty_layer())
        entry["notes"] = normalize_notes(note)
        data["layers"][name] = entry
        self.save(data)

    def field_entry(self, layer_name, field_name):
        fields = self.layer_entry(layer_name).get("fields") or {}
        return normalize_field(fields.get(field_name) or empty_field())

    def fields_map(self, layer_name):
        return dict(self.layer_entry(layer_name).get("fields") or {})

    def set_layer_bundle(self, layer_name, fields_map, label=None, notes=None):
        """Replace one layer's fields; keep other layers. None keeps previous label/notes."""
        name = (layer_name or "").strip()
        if not name:
            return
        data = normalize_data(self.data())
        prev = normalize_layer(data["layers"].get(name) or empty_layer())
        entry = empty_layer()
        entry["label"] = prev.get("label") or "" if label is None else (label or "").strip()
        entry["notes"] = (
            prev.get("notes") or "" if notes is None else normalize_notes(notes)
        )
        normalized_fields = {}
        if isinstance(fields_map, dict):
            for fname, fentry in fields_map.items():
                key = str(fname).strip()
                if not key or key == LAYER_ITEM_KEY:
                    continue
                normalized_fields[key] = normalize_field(fentry)
        entry["fields"] = normalized_fields
        data["layers"][name] = entry
        self.save(data)

    def display_label(self, layer_name, field_name, fallback_alias=""):
        label = (self.field_entry(layer_name, field_name).get("label") or "").strip()
        if label:
            return label
        alias = (fallback_alias or "").strip()
        return alias

    def merge_data(self, incoming):
        """Merge by layer name + field name. Incoming fields overwrite."""
        current = normalize_data(self.data())
        other = normalize_data(incoming)
        layers = current.setdefault("layers", {})
        for lname, ldata in other.get("layers", {}).items():
            dest = normalize_layer(layers.get(lname) or empty_layer())
            if ldata.get("label"):
                dest["label"] = ldata.get("label") or ""
            if ldata.get("notes"):
                dest["notes"] = normalize_notes(ldata.get("notes"))
            dest_fields = dest.setdefault("fields", {})
            for fname, fentry in (ldata.get("fields") or {}).items():
                dest_fields[fname] = normalize_field(fentry)
            layers[lname] = dest
        return self.save(current)

    def export_to_path(self, path, data=None):
        payload = prune_data(data if data is not None else self.data())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload

    def import_from_path(self, path):
        with open(path, "r", encoding="utf-8-sig") as f:
            incoming = json.load(f)
        if not isinstance(incoming, dict):
            raise ValueError("JSON 根对象必须是 { \"layers\": { ... } }")
        return self.merge_data(incoming)


def configured_preview_nodes(layers_map):
    """[(layer_name, layer_title, note, [(field_name, field_title, [meanings])])."""
    nodes = []
    for lname, entry in (layers_map or {}).items():
        name = (lname or "").strip()
        if not name or name == LAYER_ITEM_KEY:
            continue
        entry = normalize_layer(entry)
        if layer_is_empty(entry):
            continue
        llabel = (entry.get("label") or "").strip()
        head = name if not llabel else "%s（%s）" % (name, llabel)
        note = normalize_notes(entry.get("notes"))
        fields = []
        for fname, fentry in (entry.get("fields") or {}).items():
            key = (fname or "").strip()
            if not key or key == LAYER_ITEM_KEY:
                continue
            fentry = normalize_field(fentry)
            if field_is_empty(fentry):
                continue
            flabel = (fentry.get("label") or "").strip()
            title = key if not flabel else "%s（%s）" % (key, flabel)
            means = []
            for line in normalize_notes(fentry.get("notes")).splitlines():
                text = line.rstrip()
                if text.strip():
                    means.append(text)
            for item in fentry.get("meanings") or []:
                text = meaning_display(item) if isinstance(item, dict) else str(item).strip()
                if text:
                    means.append(text)
            fields.append((key, title, means))
        nodes.append((name, head, note, fields))
    return nodes


def layer_legend_tooltip(layer):
    """Legend hover text when remarks are enabled; empty = keep QGIS default."""
    if layer is None:
        return ""
    try:
        name = layer.name()
    except Exception:
        return ""
    session = RemarksSession()
    if not getattr(session, "is_active", None) or not session.is_active():
        return ""
    entry = session.layer_entry(name)
    label = (entry.get("label") or "").strip()
    notes = entry.get("notes") or ""
    if not label and not notes:
        return ""
    return format_hover_text("", label, [], notes)


def pack_has_content(layers_map):
    if not isinstance(layers_map, dict):
        return False
    for entry in layers_map.values():
        if not layer_is_empty(entry):
            return True
    return False


def global_store_path():
    try:
        from qgis.core import QgsApplication

        base = QgsApplication.qgisSettingsDirPath()
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "AttributeTablePlus", GLOBAL_STORE_NAME)


def global_backup_path():
    return global_store_path() + ".bak"


def write_text_atomic(path, text):
    """Write via temp file + os.replace so a crash never leaves a half-written file."""
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def _read_session_file(path):
    """Return (parsed, state). state: 'missing' | 'ok' | 'broken'."""
    if not os.path.isfile(path):
        return None, "missing"
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
    except Exception:
        return None, "broken"
    if not text.strip():
        return None, "broken"
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        return None, "broken"
    if not isinstance(raw, dict):
        return None, "broken"
    return _parse_session_text(text), "ok"


def _quarantine_file(path):
    """Rename a broken file aside so it is never overwritten. Returns new path or ''."""
    import time

    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = "%s.broken-%s" % (path, stamp)
    try:
        os.replace(path, target)
        return target
    except Exception:
        return ""


def notify_user(message, level="warning"):
    """Message bar + log; never raises."""
    try:
        from qgis.core import Qgis, QgsMessageLog

        QgsMessageLog.logMessage(message, "属性表 Plus", Qgis.Warning)
    except Exception:
        pass
    try:
        from qgis.utils import iface

        if iface is not None:
            bar = iface.messageBar()
            if level == "critical":
                bar.pushCritical("属性表 Plus", message)
            else:
                bar.pushWarning("属性表 Plus", message)
    except Exception:
        pass


def _unique_pack_name(name, existing):
    name = (name or "").strip() or "未命名"
    if name not in existing:
        return name
    n = 2
    while True:
        cand = "%s (%s)" % (name, n)
        if cand not in existing:
            return cand
        n += 1


def _layers_signature(layers_map):
    cleaned = prune_data({"version": 1, "layers": layers_map or {}})
    return json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def packs_from_parsed(parsed):
    packs = []
    if not isinstance(parsed, dict):
        return packs
    for item in parsed.get("packs") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip() or "未命名"
        layers = item.get("layers") or {}
        if not isinstance(layers, dict):
            layers = {}
        cleaned = {}
        for lname, ldata in layers.items():
            key = str(lname).strip()
            if key:
                cleaned[key] = normalize_layer(ldata)
        packs.append(
            {
                "name": name,
                "layers": cleaned,
                "variables": normalize_variables(item.get("variables")),
            }
        )
    return packs


def merge_pack_list(base, incoming, conflict_suffix="工程"):
    _ = conflict_suffix
    out = []
    by_name = {}
    names = set()
    for pack in base or []:
        name = pack.get("name") or "未命名"
        layers = pack.get("layers") or {}
        item = {
            "name": name,
            "layers": layers,
            "variables": normalize_variables(pack.get("variables")),
        }
        out.append(item)
        by_name[name] = item
        names.add(name)
    for pack in incoming or []:
        name = pack.get("name") or "未命名"
        layers = pack.get("layers") or {}
        variables = normalize_variables(pack.get("variables"))
        if name not in names:
            item = {"name": name, "layers": layers, "variables": variables}
            out.append(item)
            by_name[name] = item
            names.add(name)
            continue
        existing = by_name[name]
        if not pack_has_content(layers) and not variables:
            continue
        if not pack_has_content(existing.get("layers")) and not existing.get("variables"):
            existing["layers"] = layers
            existing["variables"] = variables
            continue
        if not pack_has_content(existing.get("layers")) and pack_has_content(layers):
            existing["layers"] = layers
        if not existing.get("variables") and variables:
            existing["variables"] = variables
        continue
    return out or [{"name": PLACEHOLDER_NAME, "layers": {}, "variables": []}]


def ensure_placeholder_packs(packs):
    others = []
    seen = set()
    for pack in packs or []:
        name = str(pack.get("name") or "").strip() or "未命名"
        if is_placeholder_name(name):
            continue
        if name in seen:
            name = _unique_pack_name(name, seen)
        seen.add(name)
        others.append(
            {
                "name": name,
                "layers": pack.get("layers") or {},
                "variables": normalize_variables(pack.get("variables")),
            }
        )
    return [{"name": PLACEHOLDER_NAME, "layers": {}, "variables": []}] + others


def _parse_session_text(text):
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict) or not parsed.get("packs"):
        return None
    return parsed


def safe_pack_filename(name):
    text = (name or "未命名").strip() or "未命名"
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "_")
    text = text.strip(" .") or "未命名"
    return text[:80]


def build_pack_file(name, layers, variables=None):
    """Current on-disk shape for one remark pack. Extra keys may be added later."""
    return {
        "kind": PACK_KIND,
        "format": PACK_FORMAT,
        "name": (name or "").strip() or "未命名",
        "layers": prune_data({"version": DATA_VERSION, "layers": layers or {}}).get("layers") or {},
        "variables": normalize_variables(variables),
    }


def build_packs_file(items):
    cleaned = []
    for item in items or []:
        name, layers, variables = unpack_pack_item(item)
        if is_placeholder_name(name):
            continue
        cleaned.append((name, layers, variables))
    if not cleaned:
        raise ValueError("没有可导出的项目。")
    if len(cleaned) == 1:
        return build_pack_file(cleaned[0][0], cleaned[0][1], cleaned[0][2])
    return {
        "kind": PACK_KIND,
        "format": PACK_FORMAT,
        "packs": [
            {
                "name": item_name,
                "layers": prune_data({"version": DATA_VERSION, "layers": layers or {}}).get(
                    "layers"
                )
                or {},
                "variables": normalize_variables(variables),
            }
            for item_name, layers, variables in cleaned
        ],
    }


def _clean_pack_layers(layers_in):
    cleaned = {}
    if not isinstance(layers_in, dict):
        return cleaned
    for lname, ldata in layers_in.items():
        key = str(lname).strip()
        if key:
            cleaned[key] = normalize_layer(ldata)
    return cleaned


def parse_pack_file(data):
    """
    Return ([(name, layers), ...], newer).
    newer=True if file format is newer than this plugin; still import known keys.
    """
    if not isinstance(data, dict):
        raise ValueError("不是有效的备注项目文件。")
    kind = str(data.get("kind") or data.get("type") or "").strip()
    if kind != PACK_KIND:
        raise ValueError("不是本插件导出的备注项目文件。")
    fmt = data.get("format")
    if fmt is None:
        fmt = PACK_FORMAT
    try:
        fmt = int(fmt)
    except (TypeError, ValueError):
        raise ValueError("文件格式版本无法识别。")
    if fmt < 1:
        raise ValueError("文件格式版本无法识别。")
    items = []
    packs_in = data.get("packs")
    if isinstance(packs_in, list) and packs_in:
        for item in packs_in:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip() or "未命名"
            layers = _clean_pack_layers(item.get("layers"))
            items.append((name, layers, normalize_variables(item.get("variables"))))
    else:
        name = str(data.get("name") or "").strip() or "未命名"
        layers_in = data.get("layers")
        variables_in = data.get("variables")
        if not isinstance(layers_in, dict):
            pack = data.get("pack")
            if isinstance(pack, dict):
                name = str(pack.get("name") or name).strip() or name
                layers_in = pack.get("layers")
                if variables_in is None:
                    variables_in = pack.get("variables")
        if not isinstance(layers_in, dict):
            raise ValueError("文件里没有图层配置。")
        items.append((name, _clean_pack_layers(layers_in), normalize_variables(variables_in)))
    if not items:
        raise ValueError("文件里没有可导入的项目。")
    return items, fmt > PACK_FORMAT


class RemarksSession:
    """Remark packs in the QGIS user profile. Selected pack is process-memory only."""

    _process = None

    def __new__(cls, *args, **kwargs):
        if cls._process is None:
            cls._process = super(RemarksSession, cls).__new__(cls)
            cls._process._ready = False
        return cls._process

    @classmethod
    def reset_process(cls):
        cls._process = None

    def __init__(self):
        if getattr(self, "_ready", False):
            return
        self._ready = True
        self.packs = [{"name": PLACEHOLDER_NAME, "layers": {}, "variables": []}]
        self.current = 0
        self.enabled = False
        self.load()

    def _clamp(self):
        self.packs = ensure_placeholder_packs(self.packs)
        if self.current < 0:
            self.current = 0
        if self.current >= len(self.packs):
            self.current = 0

    def is_placeholder(self):
        return is_placeholder_name(self.current_name())

    def is_active(self):
        """启用开关打开，且当前不是占位项目时，才把配置套到图层/字段上。"""
        return bool(self.enabled) and not self.is_placeholder()

    def _default_state(self):
        return {
            "version": 1,
            "enabled": False,
            "current": 0,
            "packs": [{"name": PLACEHOLDER_NAME, "layers": {}, "variables": []}],
        }

    def _read_global(self):
        parsed, _state = _read_session_file(global_store_path())
        return parsed

    def _read_global_for_load(self):
        """Like _read_global, but a broken file is moved aside and the backup is tried."""
        path = global_store_path()
        parsed, state = _read_session_file(path)
        if state != "broken":
            return parsed
        moved = _quarantine_file(path)
        backup, bstate = _read_session_file(global_backup_path())
        if bstate == "ok" and backup:
            self._recovered = True
            notify_user(
                "字段备注配置文件损坏，已从备份恢复。损坏的文件另存为：%s" % (moved or path)
            )
            return backup
        notify_user(
            "字段备注配置文件损坏且没有可用备份，本次从空配置开始。"
            "损坏的文件已另存为：%s" % (moved or "（改名失败，原文件未动）"),
            level="critical",
        )
        if not moved:
            self._save_blocked = True
        return None

    def _read_project_session(self):
        try:
            text, ok = QgsProject.instance().readEntry(SCOPE, SESSION_KEY, "")
        except Exception:
            return None
        if not ok:
            return None
        return _parse_session_text(text)

    def _read_project_legacy(self):
        try:
            old, old_ok = QgsProject.instance().readEntry(SCOPE, KEY, "")
        except Exception:
            return None
        if not old_ok or not old:
            return None
        try:
            data = normalize_data(json.loads(old))
        except (TypeError, ValueError):
            return None
        if not data.get("layers"):
            return None
        return {
            "version": 1,
            "enabled": False,
            "current": 0,
            "packs": [{"name": "默认", "layers": data.get("layers") or {}, "variables": []}],
        }

    def _current_name_of(self, parsed, packs=None):
        packs = packs if packs is not None else packs_from_parsed(parsed)
        if not packs:
            return None
        try:
            idx = int((parsed or {}).get("current") or 0)
        except (TypeError, ValueError):
            idx = 0
        if idx < 0 or idx >= len(packs):
            idx = 0
        return packs[idx].get("name")

    def absorb_project_packs(self):
        """Pull packs from the open .qgz into the global list. Returns True if changed."""
        self.reload_from_disk(force=True)
        incoming = []
        for parsed, suffix in (
            (self._read_project_session(), "工程"),
            (self._read_project_legacy(), "旧版"),
        ):
            extra = packs_from_parsed(parsed) if parsed else []
            if extra:
                incoming = merge_pack_list(incoming, extra, suffix)
        if not incoming:
            return False
        before = _layers_signature(
            {p.get("name"): p.get("layers") for p in self.packs}
        ) + "|" + "|".join(self.pack_names())
        merged = merge_pack_list(self.packs, incoming, "工程")
        after = _layers_signature(
            {p.get("name"): p.get("layers") for p in merged}
        ) + "|" + "|".join(str(p.get("name") or "") for p in merged)
        if before == after:
            return False
        keep = self.current_name()
        self.packs = ensure_placeholder_packs(merged)
        names = self.pack_names()
        if keep in names and not is_placeholder_name(keep):
            self.current = names.index(keep)
        self._clamp()
        self.save()
        return True

    def load(self):
        global_parsed = self._read_global_for_load()
        need_save = raw_packs_need_upgrade(global_parsed)
        packs = packs_from_parsed(global_parsed) if global_parsed else []
        enabled = bool(global_parsed.get("enabled")) if global_parsed else False
        before = (
            _layers_signature({p.get("name"): p.get("layers") for p in packs})
            + "|"
            + "|".join(p.get("name") or "" for p in packs)
            if packs
            else ""
        )

        for parsed, suffix in (
            (self._read_project_session(), "工程"),
            (self._read_project_legacy(), "旧版"),
        ):
            if raw_packs_need_upgrade(parsed):
                need_save = True
            extra = packs_from_parsed(parsed) if parsed else []
            if not extra:
                continue
            if not packs:
                packs = extra
                if not enabled:
                    enabled = bool(parsed.get("enabled"))
            else:
                packs = merge_pack_list(packs, extra, suffix)

        self.packs = ensure_placeholder_packs(packs)
        self.enabled = enabled
        self.current = 0
        upgraded_any = False
        for pack in self.packs:
            layers, changed = upgrade_layers_map(pack.get("layers") or {})
            pack["layers"] = layers
            cleaned_vars = normalize_variables(pack.get("variables"))
            if pack.get("variables") != cleaned_vars:
                upgraded_any = True
            pack["variables"] = [] if is_placeholder_name(pack.get("name")) else cleaned_vars
            if changed:
                upgraded_any = True
        after = _layers_signature(
            {p.get("name"): p.get("layers") for p in self.packs}
        ) + "|" + "|".join(self.pack_names())
        recovered = bool(getattr(self, "_recovered", False))
        self._recovered = False
        if before != after or need_save or upgraded_any or recovered:
            self.save()
        self._loaded_mtime = self._global_mtime()

    def _global_mtime(self):
        try:
            return os.path.getmtime(global_store_path())
        except Exception:
            return None

    def reload_from_disk(self, force=False):
        """用配置文件替换本进程内存。不写回，避免盖住另一边刚保存的内容。"""
        mtime = self._global_mtime()
        if not force and mtime == getattr(self, "_loaded_mtime", None):
            return False
        parsed = self._read_global()
        if not parsed:
            return False
        keep = None
        try:
            keep = self.current_name()
        except Exception:
            keep = None
        packs = packs_from_parsed(parsed)
        self.packs = ensure_placeholder_packs(packs)
        self.enabled = bool(parsed.get("enabled"))
        for pack in self.packs:
            layers, _changed = upgrade_layers_map(pack.get("layers") or {})
            pack["layers"] = layers
            if is_placeholder_name(pack.get("name")):
                pack["variables"] = []
            else:
                pack["variables"] = normalize_variables(pack.get("variables"))
        names = self.pack_names()
        if keep and keep in names:
            self.current = names.index(keep)
        else:
            self.current = 0
        self._clamp()
        self._loaded_mtime = mtime
        return True

    def save(self):
        self._clamp()
        payload = {
            "version": 1,
            "enabled": bool(self.enabled),
            "packs": [],
        }
        for pack in self.packs:
            name = pack.get("name") or "未命名"
            layers = {} if is_placeholder_name(name) else (pack.get("layers") or {})
            payload["packs"].append(
                {
                    "name": name,
                    "layers": prune_data({"version": DATA_VERSION, "layers": layers}).get("layers")
                    or {},
                    "variables": []
                    if is_placeholder_name(name)
                    else normalize_variables(pack.get("variables")),
                }
            )
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if getattr(self, "_save_blocked", False):
            return
        path = global_store_path()
        try:
            if not getattr(self, "_backup_done", False):
                self._backup_done = True
                _parsed, state = _read_session_file(path)
                if state == "ok":
                    import shutil

                    try:
                        shutil.copy2(path, global_backup_path())
                    except Exception:
                        pass
            write_text_atomic(path, text)
            self._loaded_mtime = self._global_mtime()
            self._save_error_shown = False
        except Exception as exc:
            if not getattr(self, "_save_error_shown", False):
                self._save_error_shown = True
                notify_user("字段备注保存失败：%s（%s）" % (exc, path), level="critical")

    def set_enabled(self, enabled):
        self.enabled = bool(enabled) and not self.is_placeholder()
        self.save()

    def pack_names(self):
        return [str(p.get("name") or "") for p in self.packs]

    def current_name(self):
        self._clamp()
        return self.packs[self.current].get("name") or PLACEHOLDER_NAME

    def set_current(self, index):
        if 0 <= index < len(self.packs):
            self.current = index

    def add_pack(self, name):
        name = (name or "").strip() or "未命名"
        if is_placeholder_name(name):
            name = "未命名"
        names = set(self.pack_names())
        base = name
        n = 2
        while name in names:
            name = f"{base} ({n})"
            n += 1
        self.packs.append({"name": name, "layers": {}, "variables": []})
        self.current = len(self.packs) - 1
        self.save()
        return name

    def duplicate_current(self, name):
        self._clamp()
        if self.is_placeholder():
            return self.add_pack(name)
        name = (name or "").strip() or "未命名"
        if is_placeholder_name(name):
            name = "未命名"
        names = set(self.pack_names())
        base = name
        n = 2
        while name in names:
            name = f"{base} ({n})"
            n += 1
        layers = copy.deepcopy(self.packs[self.current].get("layers") or {})
        variables = copy.deepcopy(normalize_variables(self.packs[self.current].get("variables")))
        self.packs.append({"name": name, "layers": layers, "variables": variables})
        self.current = len(self.packs) - 1
        self.save()
        return name

    def replace_current_layers(self, layers_map):
        self._clamp()
        if self.is_placeholder():
            return
        data = prune_data({"version": 1, "layers": layers_map or {}})
        self.packs[self.current]["layers"] = data.get("layers") or {}
        self.save()

    def delete_current(self):
        self._clamp()
        if self.is_placeholder():
            return False
        del self.packs[self.current]
        self.packs = ensure_placeholder_packs(self.packs)
        self.current = 0
        self.save()
        return True

    def rename_current(self, name):
        name = (name or "").strip()
        if not name or is_placeholder_name(name) or self.is_placeholder():
            return False
        self._clamp()
        others = {
            self.packs[i].get("name")
            for i in range(len(self.packs))
            if i != self.current
        }
        if name in others:
            return False
        self.packs[self.current]["name"] = name
        self.save()
        return True

    def exportable_items(self):
        self._clamp()
        items = []
        for pack in self.packs:
            name = pack.get("name") or ""
            if is_placeholder_name(name):
                continue
            items.append(
                (
                    name,
                    pack.get("layers") or {},
                    normalize_variables(pack.get("variables")),
                )
            )
        return items

    def write_packs(self, path, items):
        payload = build_packs_file(items)
        write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    def read_pack_file(self, path):
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        return parse_pack_file(data)

    def import_pack(self, name, layers, overwrite=False, variables=None):
        name = (name or "").strip() or "未命名"
        if is_placeholder_name(name):
            overwrite = False
            name = "未命名"
        cleaned = prune_data({"version": 1, "layers": layers or {}}).get("layers") or {}
        vars_in = normalize_variables(variables)
        names = self.pack_names()
        if overwrite and name in names and not is_placeholder_name(name):
            idx = names.index(name)
            self.packs[idx]["layers"] = cleaned
            self.packs[idx]["variables"] = vars_in
            self.current = idx
            self.save()
            return name
        base = name
        n = 2
        while name in names:
            name = "%s (%s)" % (base, n)
            n += 1
        self.packs.append({"name": name, "layers": cleaned, "variables": vars_in})
        self.current = len(self.packs) - 1
        self.save()
        return name

    def current_variables(self):
        self._clamp()
        if self.is_placeholder():
            return []
        return normalize_variables(self.packs[self.current].get("variables"))

    def set_current_variables(self, items):
        self._clamp()
        if self.is_placeholder():
            return []
        cleaned = normalize_variables(items)
        self.packs[self.current]["variables"] = cleaned
        self.save()
        return cleaned

    def _layers(self):
        self._clamp()
        layers = self.packs[self.current].setdefault("layers", {})
        if not isinstance(layers, dict):
            layers = {}
            self.packs[self.current]["layers"] = layers
        return layers

    def layer_entry(self, layer_name):
        name = (layer_name or "").strip()
        if not name:
            return empty_layer()
        return normalize_layer(self._layers().get(name) or empty_layer())

    def layer_note(self, layer_name):
        return self.layer_entry(layer_name).get("notes") or ""

    def fields_map(self, layer_name):
        return dict(self.layer_entry(layer_name).get("fields") or {})

    def field_entry(self, layer_name, field_name):
        fields = self.layer_entry(layer_name).get("fields") or {}
        return normalize_field(fields.get(field_name) or empty_field())

    def set_layer_bundle(self, layer_name, fields_map, label=None, notes=None):
        if self.is_placeholder():
            return
        name = (layer_name or "").strip()
        if not name:
            return
        prev = self.layer_entry(name)
        entry = empty_layer()
        entry["label"] = prev.get("label") or "" if label is None else (label or "").strip()
        entry["notes"] = (
            prev.get("notes") or "" if notes is None else normalize_notes(notes)
        )
        normalized_fields = {}
        if isinstance(fields_map, dict):
            for fname, fentry in fields_map.items():
                key = str(fname).strip()
                if not key or key == LAYER_ITEM_KEY:
                    continue
                normalized_fields[key] = normalize_field(fentry)
        entry["fields"] = normalized_fields
        self._layers()[name] = entry
        self.save()

    def set_field_entry(self, layer_name, field_name, label, meanings, notes=None):
        lname = (layer_name or "").strip()
        fname = (field_name or "").strip()
        if not lname or not fname:
            return
        bundle = self.layer_entry(lname)
        fields = dict(bundle.get("fields") or {})
        prev = normalize_field(fields.get(fname) or empty_field())
        payload = {
            "label": label,
            "meanings": meanings,
            "notes": prev.get("notes") or "" if notes is None else notes,
        }
        fields[fname] = normalize_field(payload)
        self.set_layer_bundle(lname, fields)

    def display_label(self, layer_name, field_name, fallback_alias=""):
        label = (self.field_entry(layer_name, field_name).get("label") or "").strip()
        if label:
            return label
        return (fallback_alias or "").strip()

    def meanings(self, layer_name, field_name):
        return list(self.field_entry(layer_name, field_name).get("meanings") or [])

