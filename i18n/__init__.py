# -*- coding: utf-8 -*-
"""Runtime UI language with memory and first-run locale match."""

from .catalog import (
    LANG_AR,
    LANG_EN,
    LANG_ES,
    LANG_FR,
    LANG_ZH,
    available_languages,
    detect_initial_language,
    tr,
)
from .runtime import (
    current_language,
    language_changed,
    localize_button_box,
    set_language,
    translate,
)

__all__ = [
    "LANG_AR",
    "LANG_EN",
    "LANG_ES",
    "LANG_FR",
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
