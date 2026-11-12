# -*- coding: utf-8 -*-
"""One dictionary per language. Keys are the Simplified Chinese source text."""

from ..catalog import LANG_AR, LANG_DE, LANG_ES, LANG_FR, LANG_JA, LANG_KO


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
    if lang == LANG_DE:
        from . import de

        return de.TEXT
    if lang == LANG_JA:
        from . import ja

        return ja.TEXT
    if lang == LANG_KO:
        from . import ko

        return ko.TEXT
    return {}
