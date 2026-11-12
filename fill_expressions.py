# -*- coding: utf-8 -*-
"""Saved fill expressions: storage and the «note» expression display form.

The fill box shows a saved item as ``«note» expression``. The note is only a
label: whatever follows the closing guillemet is what runs, so the user can
edit the expression in place without touching the saved one. A QGIS
expression cannot start with a bare guillemet (identifiers and fields are
written plainly or in double quotes), so the label never collides with a
real expression. Text without the label runs as typed.
"""

import json
import re

SETTINGS_KEY = "AttributeTablePlus/fill_expressions"
OPEN = "\u00ab"
CLOSE = "\u00bb"
_LABELED = re.compile(r"^\s*\u00ab([^\u00ab\u00bb\r\n]*)\u00bb[ \t]?(.*)$", re.S)


def clean_note(text):
    text = str(text or "").replace(OPEN, "").replace(CLOSE, "")
    return " ".join(text.split())


def clean_expression(text):
    return str(text or "").strip()


def display_text(expr, note=""):
    expr = clean_expression(expr)
    note = clean_note(note)
    if note:
        return "%s%s%s %s" % (OPEN, note, CLOSE, expr)
    return expr


def split_text(text):
    """(note, expression) of what the fill box holds."""
    raw = str(text or "")
    match = _LABELED.match(raw)
    if match:
        return clean_note(match.group(1)), clean_expression(match.group(2))
    return "", clean_expression(raw)


def expression_from_text(text):
    return split_text(text)[1]


def normalize_items(raw):
    out = []
    seen = set()
    for item in raw or []:
        if isinstance(item, dict):
            expr = clean_expression(item.get("expr"))
            note = clean_note(item.get("note"))
        elif isinstance(item, (list, tuple)) and item:
            expr = clean_expression(item[0])
            note = clean_note(item[1] if len(item) > 1 else "")
        else:
            expr, note = clean_expression(item), ""
        if not expr:
            continue
        key = (expr, note)
        if key in seen:
            continue
        seen.add(key)
        out.append({"expr": expr, "note": note})
    return out


def parse_items(raw):
    if raw in (None, ""):
        return []
    try:
        data = json.loads(str(raw))
    except (TypeError, ValueError):
        return []
    return normalize_items(data if isinstance(data, list) else [])


def dump_items(items):
    return json.dumps(normalize_items(items), ensure_ascii=False)


def load_items():
    from qgis.PyQt.QtCore import QSettings

    return parse_items(QSettings().value(SETTINGS_KEY, ""))


def save_items(items):
    from qgis.PyQt.QtCore import QSettings

    QSettings().setValue(SETTINGS_KEY, dump_items(items))


def display_list(items):
    return [display_text(item["expr"], item["note"]) for item in normalize_items(items)]
