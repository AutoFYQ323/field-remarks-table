# -*- coding: utf-8 -*-
from ...i18n import tr
"""Single local config for field-mapping copy."""

import json
import os

from qgis.core import QgsApplication

CONFIG_FILENAME = "field_map.json"


def config_path():
    base = QgsApplication.qgisSettingsDirPath()
    folder = os.path.join(base, "AttributeTablePlus")
    return os.path.join(folder, CONFIG_FILENAME)


def load_mapping_config():
    path = config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_mapping_config(data):
    path = config_path()
    folder = os.path.dirname(path)
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return True, ""
    except Exception as exc:
        return False, str(exc)
