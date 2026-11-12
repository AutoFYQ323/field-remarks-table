# -*- coding: utf-8 -*-
"""Qt 5 and Qt 6 calls that QGIS still has to run on both."""

try:
    from qgis.PyQt.QtGui import QAction
except ImportError:  # Qt 5 keeps QAction on QtWidgets
    from qgis.PyQt.QtWidgets import QAction  # noqa: F401  Qt 5 fallback, re-exported


def run_exec(widget, *args):
    """QDialog and QMenu: exec on Qt 6, the older name on Qt 5."""
    runner = getattr(widget, "exec", None)
    if not callable(runner):
        runner = getattr(widget, "exec_")
    return runner(*args)


def _point(getter):
    if not callable(getter):
        return None
    try:
        point = getter()
    except AttributeError:
        return None
    to_point = getattr(point, "toPoint", None)
    if callable(to_point):
        return to_point()
    return point


def event_pos(event):
    """Local QPoint. Qt 6 mouse events no longer have pos()."""
    point = _point(getattr(event, "pos", None))
    if point is not None:
        return point
    return _point(getattr(event, "position", None))


def event_global_pos(event):
    """Global QPoint. Qt 6 mouse events no longer have globalPos()."""
    point = _point(getattr(event, "globalPos", None))
    if point is not None:
        return point
    return _point(getattr(event, "globalPosition", None))


def make_qgs_field(name, qtype, type_name="", length=0, precision=0):
    """QgsField for Qt 6 (QMetaType) and Qt 5 (QVariant type)."""
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsField

    try:
        from qgis.PyQt.QtCore import QMetaType

        mapping = {
            QVariant.Int: QMetaType.Type.Int,
            QVariant.UInt: QMetaType.Type.UInt,
            QVariant.LongLong: QMetaType.Type.LongLong,
            QVariant.ULongLong: QMetaType.Type.ULongLong,
            QVariant.Double: QMetaType.Type.Double,
            QVariant.String: QMetaType.Type.QString,
            QVariant.Bool: QMetaType.Type.Bool,
            QVariant.Date: QMetaType.Type.QDate,
            QVariant.DateTime: QMetaType.Type.QDateTime,
        }
        meta = mapping.get(qtype)
        if meta is not None:
            if type_name:
                return QgsField(name, meta, type_name, int(length), int(precision))
            return QgsField(name, meta)
    except (TypeError, AttributeError, ValueError):
        pass  # nosec B110
    if type_name:
        return QgsField(name, qtype, type_name, int(length), int(precision))
    return QgsField(name, qtype)
