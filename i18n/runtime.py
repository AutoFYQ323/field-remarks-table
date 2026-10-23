# -*- coding: utf-8 -*-
"""Active UI language. First launch follows QGIS, then the system locale."""

from qgis.PyQt.QtCore import QLocale, QObject, QSettings, pyqtSignal

from .catalog import LANG_EN, LANG_ZH, detect_initial_language, known_languages

_SETTINGS = "AttributeTablePlus/ui_language"
_hub = None


class LanguageHub(QObject):
    changed = pyqtSignal(str)


def hub():
    global _hub
    if _hub is None:
        _hub = LanguageHub()
    return _hub


def language_changed():
    return hub().changed


def _stored():
    try:
        return str(QSettings().value(_SETTINGS, "") or "").strip().lower()
    except Exception:
        return ""


def current_language():
    stored = _stored()
    if stored in known_languages():
        return stored
    qloc = ""
    try:
        from qgis.core import QgsApplication

        qloc = QgsApplication.locale() or ""
    except Exception:
        qloc = ""
    try:
        sysloc = QLocale.system().name()
    except Exception:
        sysloc = ""
    lang = detect_initial_language(qloc, sysloc)
    try:
        QSettings().setValue(_SETTINGS, lang)
    except Exception:
        pass  # nosec B110
    return lang


def _normalize_lang(lang):
    text = str(lang or "").strip().lower().replace("_", "-")
    primary = text.split("-", 1)[0]
    if primary in known_languages():
        return primary
    return LANG_ZH


def set_language(lang):
    lang = _normalize_lang(lang)
    try:
        QSettings().setValue(_SETTINGS, lang)
    except Exception:
        pass  # nosec B110
    try:
        from .. import theme

        theme.refresh_direction()
    except Exception:
        pass  # nosec B110
    hub().changed.emit(lang)
    return lang


def _lookup(msgid):
    lang = current_language()
    if lang == LANG_ZH or not msgid:
        return None
    if lang == LANG_EN:
        from . import messages_en

        mapped = messages_en.EN.get(msgid)
        if mapped is None:
            from . import messages_en_extra

            mapped = messages_en_extra.EXTRA.get(msgid)
        return mapped
    from .locales import load_text

    return load_text(lang).get(msgid)


def translate(msgid, *args, **kwargs):
    text = msgid if isinstance(msgid, str) else str(msgid)
    mapped = _lookup(text)
    if mapped is not None:
        text = mapped
    if args or kwargs:
        try:
            text = text % (args if args else kwargs) if args else text % kwargs
        except Exception:
            pass  # nosec B110
    return text


def tr(msgid, *args, **kwargs):
    return translate(msgid, *args, **kwargs)


def localize_button_box(box):
    """Standard OK/Cancel/Close follow the plugin language, not only the QGIS locale."""
    if box is None:
        return box
    try:
        from qgis.PyQt.QtWidgets import QDialogButtonBox
    except Exception:
        return box
    mapping = (
        (QDialogButtonBox.Ok, "确定"),
        (QDialogButtonBox.Cancel, "取消"),
        (QDialogButtonBox.Yes, "是"),
        (QDialogButtonBox.No, "否"),
        (QDialogButtonBox.Close, "关闭"),
        (QDialogButtonBox.Save, "保存"),
    )
    for flag, msgid in mapping:
        try:
            button = box.button(flag)
        except Exception:
            button = None
        if button is not None:
            button.setText(tr(msgid))
    return box
