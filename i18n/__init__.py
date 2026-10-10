# -*- coding: utf-8 -*-
"""Runtime UI language (zh / en) with memory and first-run locale match."""

from .catalog import LANG_EN, LANG_ZH, available_languages, detect_initial_language, tr
from .runtime import (
    current_language,
    language_changed,
    localize_button_box,
    set_language,
    translate,
)

__all__ = [
    "LANG_EN",
    "LANG_ZH",
    "available_languages",
    "current_language",
    "detect_initial_language",
    "language_changed",
    "localize_button_box",
    "set_language",
    "tr",
    "translate",
]
