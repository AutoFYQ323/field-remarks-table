# -*- coding: utf-8 -*-
"""One dictionary per language. Keys are the Simplified Chinese source text."""

from ..catalog import LANG_AR, LANG_ES, LANG_FR


def load_text(lang):
    if lang == LANG_ES:
        from . import es

        return es.TEXT
    if lang == LANG_FR:
        from . import fr

        return fr.TEXT
    if lang == LANG_AR:
        from . import ar

        return ar.TEXT
    return {}
