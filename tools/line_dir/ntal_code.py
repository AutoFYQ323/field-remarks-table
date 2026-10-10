# -*- coding: utf-8 -*-
from ...i18n import tr
import math
import re

_DIGITS = re.compile(r"^[0-9]+$")
DEFAULT_BOX_PREFIX = "PBO"
DEFAULT_CABLE_PREFIX = "CDI"
DEFAULT_SPLICE_PREFIX = "BPE"


def parse_splice_code(name):
    text = str(name or "").strip()
    if not text:
        return None
    parts = [item.strip() for item in text.split("-")]
    if len(parts) != 6:
        return None
    if not all(parts[:3]):
        return None
    if not all(_DIGITS.match(item) for item in parts[3:]):
        return None
    odf = int(parts[3])
    n4 = int(parts[4])
    n5 = int(parts[5])
    return {
        "parts": parts,
        "city": parts[1],
        "pm": parts[2],
        "odf": odf,
        "n4": n4,
        "n5": n5,
        "width3": max(len(parts[3]), 2),
        "width4": max(len(parts[-2]), 2),
        "width5": max(len(parts[-1]), 2),
    }


def city_pm_ok(parsed, city, pm):
    if not parsed:
        return False
    return str(parsed.get("city") or "") == str(city or "").strip() and str(
        parsed.get("pm") or ""
    ) == str(pm or "").strip()


def apply_prefix_city_pm(code, prefix, city, pm):
    parsed = parse_splice_code(code)
    if parsed is None:
        return None
    parts = list(parsed["parts"])
    parts[0] = str(prefix or "").strip() or parts[0]
    parts[1] = str(city or "").strip() or parts[1]
    parts[2] = str(pm or "").strip() or parts[2]
    return "-".join(parts)


def format_splice_code(prefix, city, pm, odf, link, fat=1, width=2):
    text = str(prefix or "").strip() or DEFAULT_SPLICE_PREFIX
    city = str(city or "").strip()
    pm = str(pm or "").strip()
    size = max(int(width or 2), 2)
    return "{}-{}-{}-{}-{}-{}".format(
        text,
        city,
        pm,
        str(int(odf)).zfill(size),
        str(int(link)).zfill(size),
        str(int(fat)).zfill(size),
    )


def format_fat_code(parsed, dir_index, fat_index, prefix=None, city=None, pm=None):
    """旧公式，当前命名不调用。分纤盒第六段见 format_ranked_fat_code，一律从 01 起。"""
    parts = list(parsed["parts"])
    parts[0] = str(prefix or "").strip() or DEFAULT_BOX_PREFIX
    if str(city or "").strip():
        parts[1] = str(city).strip()
    if str(pm or "").strip():
        parts[2] = str(pm).strip()
    n4 = parsed["n4"] + int(dir_index)
    if int(dir_index) == 0:
        n5 = parsed["n5"] + 1 + int(fat_index)
    else:
        n5 = 1 + int(fat_index)
    parts[-2] = str(n4).zfill(parsed["width4"])
    parts[-1] = str(n5).zfill(parsed["width5"])
    return "-".join(parts)


def format_ranked_fat_code(parsed, link, fat_no, prefix=None, city=None, pm=None):
    parts = list(parsed["parts"])
    parts[0] = str(prefix or "").strip() or DEFAULT_BOX_PREFIX
    if str(city or "").strip():
        parts[1] = str(city).strip()
    if str(pm or "").strip():
        parts[2] = str(pm).strip()
    parts[3] = str(int(parsed.get("odf") or parts[3])).zfill(parsed.get("width3") or 2)
    parts[-2] = str(int(link)).zfill(parsed["width4"])
    parts[-1] = str(int(fat_no)).zfill(parsed["width5"])
    return "-".join(parts)


def bearing_deg(origin, toward):
    dx = float(toward[0]) - float(origin[0])
    dy = float(toward[1]) - float(origin[1])
    if math.hypot(dx, dy) < 1e-9:
        return None
    return math.degrees(math.atan2(dx, dy)) % 360.0


def direction_sort_key(bearing, start_angle, clockwise):
    rel = (float(bearing) - float(start_angle)) % 360.0
    if clockwise:
        return rel
    return (360.0 - rel) % 360.0
