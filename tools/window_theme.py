# -*- coding: utf-8 -*-
"""Shared UI theme registration for plugin tool windows."""


def register_tool_window(widget):
    """Apply the current pink/mint/default theme and follow future changes."""
    if widget is None:
        return
    from .. import theme

    theme.register(widget)


def resolve_tool_parent(host, fallback=None):
    """Prefer the attribute table dialog passed in from the plugin."""
    parent = getattr(host, "ui_parent", None)
    if parent is not None:
        return parent
    if fallback is not None:
        return fallback
    iface = getattr(host, "iface", None)
    if iface is not None:
        try:
            return iface.mainWindow()
        except Exception:
            pass  # nosec B110
    return host
