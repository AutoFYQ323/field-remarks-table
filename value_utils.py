# -*- coding: utf-8 -*-
"""Shared value -> text and value -> field-type conversion."""

import re

from qgis.PyQt.QtCore import QDate, QDateTime, QTime, QVariant, Qt
from qgis.core import NULL

_INT_RE = re.compile(r"^[+-]?\d+$")
_NUM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

_INT_TYPES = {QVariant.Int, QVariant.UInt, QVariant.LongLong, QVariant.ULongLong}
_TRUE_TEXT = {"true", "t", "1", "yes", "y", "是", "真"}
_FALSE_TEXT = {"false", "f", "0", "no", "n", "否", "假"}


def is_null(value):
    return value is None or value == NULL


def temporal_text(value):
    """QDate / QDateTime / QTime as ISO-like text, or None if not temporal."""
    if isinstance(value, QDateTime):
        if not value.isValid():
            return ""
        if value.time().msec():
            return value.toString("yyyy-MM-dd HH:mm:ss.zzz")
        return value.toString("yyyy-MM-dd HH:mm:ss")
    if isinstance(value, QDate):
        return value.toString("yyyy-MM-dd") if value.isValid() else ""
    if isinstance(value, QTime):
        if not value.isValid():
            return ""
        if value.msec():
            return value.toString("HH:mm:ss.zzz")
        return value.toString("HH:mm:ss")
    return None


def value_text(value):
    """Human text for a raw attribute value (NULL -> '')."""
    if is_null(value):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    temporal = temporal_text(value)
    if temporal is not None:
        return temporal
    return str(value)


def field_kind(field):
    """'string' | 'int' | 'real' | 'bool' | 'date' | 'datetime' | 'time' | 'other'."""
    try:
        vtype = field.type()
    except Exception:
        vtype = None
    if vtype == QVariant.String:
        return "string"
    if vtype in _INT_TYPES:
        return "int"
    if vtype == QVariant.Double:
        return "real"
    if vtype == QVariant.Bool:
        return "bool"
    if vtype == QVariant.Date:
        return "date"
    if vtype == QVariant.DateTime:
        return "datetime"
    if vtype == QVariant.Time:
        return "time"
    type_name = (field.typeName() or "").lower()
    if any(t in type_name for t in ("string", "text", "char", "varchar")):
        return "string"
    if any(t in type_name for t in ("int", "long", "integer")):
        return "int"
    if any(t in type_name for t in ("real", "double", "float", "numeric", "decimal")):
        return "real"
    return "other"


def _parse_number_text(text):
    cleaned = text.strip().replace(",", "")
    if not cleaned:
        return None
    if _INT_RE.match(cleaned):
        return int(cleaned)
    if _NUM_RE.match(cleaned):
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_date(text):
    for fmt in ("yyyy-MM-dd", "yyyy/MM/dd", "yyyy.MM.dd", "yyyyMMdd"):
        d = QDate.fromString(text, fmt)
        if d.isValid():
            return d
    d = QDate.fromString(text, Qt.ISODate)
    if d.isValid():
        return d
    dt = _parse_datetime(text, allow_date=False)
    if dt is not None:
        return dt.date()
    return None


def _parse_datetime(text, allow_date=True):
    dt = QDateTime.fromString(text, Qt.ISODate)
    if dt.isValid():
        return dt
    for fmt in (
        "yyyy-MM-dd HH:mm:ss.zzz",
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy/MM/dd HH:mm:ss",
        "yyyy/MM/dd HH:mm",
    ):
        dt = QDateTime.fromString(text, fmt)
        if dt.isValid():
            return dt
    if allow_date:
        d = _parse_date(text)
        if d is not None:
            return QDateTime(d, QTime(0, 0, 0))
    return None


def _parse_time(text):
    for fmt in ("HH:mm:ss.zzz", "HH:mm:ss", "HH:mm"):
        t = QTime.fromString(text, fmt)
        if t.isValid():
            return t
    return None


def coerce_for_field(field, raw):
    """
    Convert raw to a value the field can store.

    Returns (status, value, note):
      'ok'       value is ready
      'rounded'  int field got a non-integral number; value is the rounded int
      'toolong'  text longer than the field length; value is the full text
      'invalid'  cannot be stored; value is None
    """
    if is_null(raw):
        return "ok", NULL, ""
    kind = field_kind(field)

    if kind == "string":
        text = temporal_text(raw)
        if text is None:
            text = str(raw)
        try:
            limit = int(field.length())
        except Exception:
            limit = 0
        if limit > 0 and len(text) > limit:
            return "toolong", text, "超过字段长度 %s" % limit
        return "ok", text, ""

    if kind in ("int", "real"):
        if isinstance(raw, bool):
            num = int(raw)
        elif isinstance(raw, (int, float)):
            num = raw
        elif isinstance(raw, str):
            if raw.strip() == "":
                return "ok", NULL, ""
            num = _parse_number_text(raw)
            if num is None:
                return "invalid", None, "不是数字"
        else:
            return "invalid", None, "不是数字"
        if kind == "real":
            return "ok", float(num), ""
        if isinstance(num, float):
            if num != num or num in (float("inf"), float("-inf")):
                return "invalid", None, "不是有效数字"
            rounded = int(round(num))
            status = "ok" if rounded == num else "rounded"
            num = rounded
        else:
            status = "ok"
        try:
            if field.type() == QVariant.Int and not (-(2 ** 31) <= num < 2 ** 31):
                return "invalid", None, "超出整数范围"
        except Exception:
            pass
        return status, int(num), ("小数已四舍五入" if status == "rounded" else "")

    if kind == "bool":
        if isinstance(raw, bool):
            return "ok", raw, ""
        if isinstance(raw, (int, float)):
            if raw in (0, 1):
                return "ok", bool(raw), ""
            return "invalid", None, "不是真/假"
        text = str(raw).strip().lower()
        if text == "":
            return "ok", NULL, ""
        if text in _TRUE_TEXT:
            return "ok", True, ""
        if text in _FALSE_TEXT:
            return "ok", False, ""
        return "invalid", None, "不是真/假"

    if kind in ("date", "datetime", "time"):
        if kind == "date":
            if isinstance(raw, QDateTime):
                return "ok", raw.date(), ""
            if isinstance(raw, QDate):
                return "ok", raw, ""
        elif kind == "datetime":
            if isinstance(raw, QDateTime):
                return "ok", raw, ""
            if isinstance(raw, QDate):
                return "ok", QDateTime(raw, QTime(0, 0, 0)), ""
        else:
            if isinstance(raw, QTime):
                return "ok", raw, ""
            if isinstance(raw, QDateTime):
                return "ok", raw.time(), ""
        text = str(raw).strip()
        if text == "":
            return "ok", NULL, ""
        if kind == "date":
            parsed = _parse_date(text)
        elif kind == "datetime":
            parsed = _parse_datetime(text)
        else:
            parsed = _parse_time(text)
        if parsed is None:
            return "invalid", None, "不是有效日期/时间"
        return "ok", parsed, ""

    if isinstance(raw, str):
        text = raw.strip()
        if text == "":
            return "ok", NULL, ""
        num = _parse_number_text(text)
        return "ok", (num if num is not None else text), ""
    return "ok", raw, ""
