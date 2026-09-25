# -*- coding: utf-8 -*-
"""Field Remarks Table — QGIS plugin entry."""


def classFactory(iface):
    from .plugin import AttributeTablePlugin

    return AttributeTablePlugin(iface)
